import shapefile,zipfile,numpy as np,cv2,json,math
from pathlib import Path
from scipy.optimize import least_squares
from scipy.ndimage import map_coordinates
z=zipfile.ZipFile('work/ne-coastline.zip');z.extractall('work/coastline')
r=shapefile.Reader('work/coastline/ne_10m_coastline.shp');lines=[]
for shape in r.iterShapes():
 p=np.array(shape.points);mask=(p[:,0]>-61)&(p[:,0]<-51)&(p[:,1]>46)&(p[:,1]<53)
 for ids in np.split(np.where(mask)[0],np.where(np.diff(np.where(mask)[0])>1)[0]+1):
  if len(ids)>4:lines.append(p[ids])
print('coastlines',sum(map(len,lines)))
# Geographic seeds identify distinctive capes, not the displaced town labels.
seeds={
'island':[[ -59.3,47.62,27,390],[-53.07,46.655,855,524],[-52.62,47.52,855,402],[-53.08,48.70,755,299],[-55.43,51.64,485,101],[-54.2,46.82,699,484]],
'east':[[-53.07,46.655,744,521],[-52.62,47.52,796,350],[-53.08,48.70,666,215],[-54.2,46.82,518,448],[-55.98,46.91,48,438],[-52.78,47.81,712,265]]}
def geo(p):
 p=np.radians(np.asarray(p));lat=p[:,1];lon=p[:,0];v=np.column_stack([np.cos(lat)*np.cos(lon),np.cos(lat)*np.sin(lon),np.sin(lat)])*6371
 la,lo=np.radians([49,-56]);origin=np.array([np.cos(la)*np.cos(lo),np.cos(la)*np.sin(lo),np.sin(la)])*6371
 rot=np.array([[-np.sin(lo),np.cos(lo),0],[-np.sin(la)*np.cos(lo),-np.sin(la)*np.sin(lo),np.cos(la)],[np.cos(la)*np.cos(lo),np.cos(la)*np.sin(lo),np.sin(la)]])
 return (v-origin)@rot.T
points=np.concatenate(lines);g=geo(points).astype(np.float32)
out=Path('outputs/skycam/skycam/radar');out.mkdir(exist_ok=True)
for kind,seed in seeds.items():
 src=cv2.imread('work/radar-'+kind+'.jpg');s=np.array(seed,float);K=np.array([[1200.,0,480.],[0,1200.,270.],[0,0,1.]])
 ok,r,t=cv2.solvePnP(geo(s[:,:2]),np.ascontiguousarray(s[:,2:]),K,None,flags=cv2.SOLVEPNP_SQPNP);assert ok
 initial_params=np.r_[r.ravel(),t.ravel(),math.log(1200)]
 land=cv2.imread('work/radar-'+kind+'-land.png',0)
 contours,_=cv2.findContours(land,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
 white=np.zeros_like(land);cv2.drawContours(white,contours,-1,1,1);white[:110]=0
 dist=cv2.distanceTransform(1-white,cv2.DIST_L2,3)
 def project(params,gg=g):
  k=K.copy();k[0,0]=k[1,1]=math.exp(params[6]);return cv2.projectPoints(np.asarray(gg,dtype='float64'),params[:3],params[3:6],k,None)[0].reshape(-1,2)
 initial=project(initial_params);valid=(initial[:,0]>5)&(initial[:,0]<955)&(initial[:,1]>112)&(initial[:,1]<532)
 ids=np.where(valid)[0][::3];gg=g[ids]
 def loss(params):
  p=project(params,gg);x=p[:,0].astype('float32');y=p[:,1].astype('float32');d=map_coordinates(dist,[y,x],order=1,mode='constant',cval=30)
  # Loose seed regularization prevents an unrelated white road from winning.
  controls=(project(params,geo(s[:,:2]))-s[:,2:]).ravel()*.12
  return np.r_[d,controls]
 start=initial_params;span=np.array([.7,.7,.7,300,300,1000,1.5]);fit=least_squares(loss,start,bounds=(start-span,start+span),diff_step=1e-5,x_scale='jac',loss='soft_l1',f_scale=2,max_nfev=500)
 fitted=fit.x
 px=project(fit.x);image=src.copy()
 for x,y in px[::2]:
  if 0<x<960 and 105<y<540:cv2.circle(image,(round(x),round(y)),1,(0,0,255),-1)
 cv2.imwrite('work/radar-'+kind+'-fit.jpg',image)
 errs=loss(fit.x)[:len(ids)]
 result={'kind':kind,'width':960,'height':540,'model':'spherical-camera','parameters':fitted.tolist(),'seed_controls':seed,'coast_distance_median_px':float(np.median(errs)),'coast_distance_p90_px':float(np.percentile(errs,90)),'reference':'Natural Earth 1:10m coastline','status':'approximate','seed_description':'Approximate cape locations on supplied reference image; automatic robust coastline fit. Not independently surveyed.'}
 (out/(kind+'.json')).write_text(json.dumps(result,indent=2))
 print(kind,result['coast_distance_median_px'],result['coast_distance_p90_px'])
