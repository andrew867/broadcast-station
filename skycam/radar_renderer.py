"""Attributed radar composites with a fitted perspective model and drift checks."""
from .bounded_http import bounded_get_sync
from .public_errors import public_error
import asyncio,hashlib,io,json,math,os,threading,time
from pathlib import Path
import cv2,httpx,numpy as np
from PIL import Image,ImageDraw
from .picture_history import PictureHistory
from .map_renderer import MapRenderer
from .graphics import font,fit,TICKER_TOP
from . import playout
from .radar_calibration import load_calibration

ASSETS=Path(__file__).parent/'radar'
URLS={'east':'https://sheerrweather.b-cdn.net/wximages/NF_RADAR_EAST.jpg','island':'https://sheerrweather.b-cdn.net/wximages/NF_RADAR.jpg'}
# Preserve the complete 16:9 provider image. Station identification is already
# in the ticker; a compact footer replaces the redundant outer header.
RADAR_SCALE=3.4;RADAR_X=288;RADAR_Y=0
RADAR_BOTTOM=round(RADAR_Y+540*RADAR_SCALE)

def image_box(x,y,right,bottom):
    return (RADAR_X+x*RADAR_SCALE,RADAR_Y+y*RADAR_SCALE,RADAR_X+right*RADAR_SCALE,RADAR_Y+bottom*RADAR_SCALE)

def ground(points):
    p=np.radians(np.asarray(points,dtype=float).reshape(-1,2));lon,lat=p[:,0],p[:,1]
    v=np.column_stack([np.cos(lat)*np.cos(lon),np.cos(lat)*np.sin(lon),np.sin(lat)])*6371
    la,lo=np.radians([49,-56]);origin=np.array([np.cos(la)*np.cos(lo),np.cos(la)*np.sin(lo),np.sin(la)])*6371
    rot=np.array([[-np.sin(lo),np.cos(lo),0],[-np.sin(la)*np.cos(lo),-np.sin(la)*np.sin(lo),np.cos(la)],[np.cos(la)*np.cos(lo),np.cos(la)*np.sin(lo),np.sin(la)]])
    return (v-origin)@rot.T

def geographic_pixels(points,calibration):
    p=np.array(calibration['parameters'],float);f=math.exp(p[6]);k=np.array([[f,0,480],[0,f,270],[0,0,1.]])
    return cv2.projectPoints(ground(points),p[:3],p[3:6],k,None)[0].reshape(-1,2)

def register_image(reference,current):
    """Accept a small, well-supported image shift; reject a changed map layout."""
    if current.shape!=reference.shape:return None,{'reason':'Image dimensions changed'}
    mask=np.zeros(reference.shape[:2],dtype='uint8');mask[110:535,8:952]=255
    orb=cv2.ORB_create(nfeatures=2500,edgeThreshold=12)
    a,da=orb.detectAndCompute(cv2.cvtColor(reference,cv2.COLOR_RGB2GRAY),mask)
    b,db=orb.detectAndCompute(cv2.cvtColor(current,cv2.COLOR_RGB2GRAY),mask)
    if da is None or db is None:return None,{'reason':'Insufficient fixed map detail'}
    pairs=cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(da,db,k=2)
    good=[m for pair in pairs if len(pair)==2 for m,n in [pair] if m.distance<.7*n.distance]
    if len(good)<30:return None,{'reason':'Too few reliable map matches','matches':len(good)}
    src=np.float32([a[m.queryIdx].pt for m in good]);dst=np.float32([b[m.trainIdx].pt for m in good])
    h,inliers=cv2.findHomography(src,dst,cv2.RANSAC,2)
    if h is None:return None,{'reason':'Map registration failed'}
    keep=inliers.ravel().astype(bool);n=int(keep.sum());coverage=np.ptp(src[keep],axis=0)
    corners=np.float32([[0,110],[960,110],[960,540],[0,540]])
    shifts=np.linalg.norm(cv2.perspectiveTransform(corners[None],h)[0]-corners,axis=1)
    residual=np.linalg.norm(cv2.perspectiveTransform(src[keep][None],h)[0]-dst[keep],axis=1)
    stats={'matches':len(good),'inliers':n,'median_error_px':round(float(np.median(residual)),3),'max_shift_px':round(float(max(shifts)),3)}
    if n<25 or n/len(good)<.55 or coverage[0]<400 or coverage[1]<200 or max(shifts)>25:
        return None,{**stats,'reason':'Map layout changed or matches too localized'}
    return h,stats

class RadarRenderer(MapRenderer):
    def __init__(self,data,get_data,kind,channel):
        super().__init__(data,get_data,'radar-'+kind,channel)
        self.kind=kind;self.calibration=None;self.reference=None;self.calibration_error=None
        folder=data/'radar'/'calibration'
        # Packaged pictures are synthetic offline fixtures, never live weather references.
        if not folder.exists() and os.environ.get('STATION_OFFLINE','1')!='0':folder=ASSETS
        try:self.calibration,self.reference=load_calibration(folder,kind)
        except (OSError,ValueError,KeyError,TypeError):self.calibration_error='Radar calibration missing or invalid'
        self.radar_folder=data/'radar';self.radar_folder.mkdir(exist_ok=True)
        self.cache=self.radar_folder/(kind+'.jpg');self.lock=threading.RLock();self.transform=None;self.last_download=0;self.changed_at=0;self.digest=None
        self._history=PictureHistory(self.cache.parent/'history'/self.kind,count=120,age=7200,budget=24*1024*1024)
        self.attribution='';self.status.update(alignment='unverified',source_url=URLS[kind],calibration='approximate coastline fit',calibration_error=self.calibration_error)
        self.label_background='#0b1c29';self.label_foreground='#f7fbff';self.label_outline='#ffb274'
        self.label_size=48;self.label_height=72;self.label_gap=26;self.label_limit=12
        self.protect_aircraft=True
        self.icon_outline='#101c25';self.icon_outline_width=4;self.leader_color='#ffc38a';self.leader_width=3
        self.city_boxes=[]
    def accept(self,content,downloaded=True):
        with Image.open(io.BytesIO(content),formats=('PNG','JPEG')) as img:
            img.load();raw=np.array(img.convert('RGB'))
        h,stats=register_image(self.reference,raw) if self.reference is not None else (None,{'reason':self.calibration_error})
        # Keep labels off the provider's small white town-name panels.
        hsv=cv2.cvtColor(raw,cv2.COLOR_RGB2HSV)
        white=((hsv[:,:,1]<35)&(hsv[:,:,2]>205)).astype('uint8')*255
        white[:110]=0
        white=cv2.morphologyEx(white,cv2.MORPH_CLOSE,np.ones((3,9),'uint8'))
        contours,_=cv2.findContours(white,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        cities=[]
        for contour in contours:
            x,y,w,height=cv2.boundingRect(contour)
            if 25<w<190 and 9<height<29 and w/height>1.7 and cv2.contourArea(contour)>w*height*.6:
                cities.append(image_box(x-3,y-3,x+w+3,y+height+3))
        with self.lock:
            self.city_boxes=cities
            self.transform=h;self.status['registration']=stats;self.status['alignment']='approximate' if h is not None else 'unavailable'
            digest=hashlib.sha256(content).hexdigest()
            if digest!=self.digest:self.changed_at=time.time();self.digest=digest
            self.base=Image.new('RGBA',(3840,2160),'#101c25')
            self.base.paste(Image.fromarray(raw).resize((round(960*RADAR_SCALE),round(540*RADAR_SCALE)),Image.Resampling.LANCZOS),(RADAR_X,RADAR_Y));self.built_at=time.time()
            if downloaded:self.last_download=time.time()
    @property
    def history(self):
        return self._history
    def fetch(self):
        try:
            with httpx.Client(timeout=10,follow_redirects=True) as client:
                response=bounded_get_sync(client,URLS[self.kind],max_bytes=12_000_000,headers={'User-Agent':'SkyCam247 weather display','Cache-Control':'no-cache'})
                response.raise_for_status()
                if len(response.content)>8_000_000:raise ValueError('Unexpectedly large radar image')
                self.accept(response.content)
                self.history.add(response.content, deduplicate=True)
                tmp=self.cache.with_suffix('.tmp');tmp.write_bytes(response.content);tmp.replace(self.cache)
            self.status.update(fetch_error=None,downloaded_at=self.last_download,image_changed_at=self.changed_at)
        except Exception as exc:
            self.status['fetch_error']=public_error(exc)[:160]
            if self.base is None and self.cache.exists():
                self.accept(self.cache.read_bytes(),False);self.changed_at=self.cache.stat().st_mtime
    def basemap(self):
        if self.base is None:
            self.base=Image.new('RGBA',(3840,2160),'#101c25');d=ImageDraw.Draw(self.base)
            d.text((230,650),'RADAR TEMPORARILY UNAVAILABLE',font=font(100),fill='#f4f0e7')
            self.built_at=time.time()
    def point(self,lat,lon):
        px=geographic_pixels([[lon,lat]],self.calibration)
        if self.transform is not None:px=cv2.perspectiveTransform(px[None].astype('float32'),self.transform)[0]
        x,y=px[0];return round(RADAR_X+x*RADAR_SCALE),round(RADAR_Y+y*RADAR_SCALE)
    def heading(self,p):
        a=math.radians(p.get('track') or 0);lat=p['lat'];lon=p['lon']
        x,y=self.point(lat,lon);xx,yy=self.point(lat+.02*math.cos(a),lon+.02*math.sin(a)/math.cos(math.radians(lat)))
        return math.atan2(xx-x,-(yy-y))
    def contains(self,x,y):
        px=(x-RADAR_X)/RADAR_SCALE;py=(y-RADAR_Y)/RADAR_SCALE
        return 4<px<956 and 110<py<534 and not (self.kind=='island' and 47<px<316 and 458<py<514)
    def occupied(self):
        return [(0,0,3840,RADAR_Y+110*RADAR_SCALE),(0,RADAR_BOTTOM,3840,2160),(0,0,RADAR_X,2160),(RADAR_X+960*RADAR_SCALE,0,3840,2160)]+self.city_boxes+([image_box(47,458,316,514)] if self.kind=='island' else [])
    def draw(self,data):
        with self.lock:
            stale=not self.last_download or time.time()-self.last_download>600 or time.time()-self.changed_at>1200
            planes=data['aircraft'] if self.transform is not None else []
            image,n=super().draw({**data,'aircraft':planes,'theme':{'effective':'day','show_info':False}})
            d=ImageDraw.Draw(image)
            d.rectangle((0,RADAR_BOTTOM,3840,TICKER_TOP),fill='#101c25')
            title='EASTERN NEWFOUNDLAND RADAR' if self.kind=='east' else 'NEWFOUNDLAND RADAR'
            d.text((192,RADAR_BOTTOM+4),title,font=font(46),fill='#f4f0e7')
            timing=('AIRCRAFT NOW' if data['healthy'] else 'LAST KNOWN AIRCRAFT')+'  ·  RADAR: TIME ON IMAGE'
            f=font(32,False);d.text((3648-d.textlength(timing,font=f),RADAR_BOTTOM+58),timing,font=f,fill='#b6c5cf')
            note='APPROXIMATE POSITIONS' if self.transform is not None else 'AIRCRAFT ALIGNMENT UNAVAILABLE'
            if stale:note+='  |  RADAR DELAYED / CHECK IMAGE TIME'
            if not data['healthy']:note+='  |  ADS-B RECEIVER UNAVAILABLE'
            d.text((192,RADAR_BOTTOM+58),note,font=fit(d,note,32,2300),fill='#ffb675' if stale else '#c4d3dc')
            text='RADAR COURTESY SHEERR WEATHER';f=font(34);d.text((3648-d.textlength(text,font=f),RADAR_BOTTOM+12),text,font=f,fill='#f4f0e7')
            return image,n
    async def fetch_watch(self):
        while True:
            await asyncio.to_thread(self.fetch)
            await asyncio.sleep(60)
