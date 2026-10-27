from .branding import BRAND
"""Prepare native 4K static graphics off air; ticker stays in its own live layer."""
import hashlib,json,os
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from .sources import CAMERAS,QUADS
from .map_scenes import MAP_SCENES, DIRECT_SCENES
from .image_cache import valid_image
FONTS=Path(__file__).parent/'static'/'fonts'
DATA=Path(os.environ.get('SKYCAM_DATA',Path(__file__).parent.parent/'data'))
PAPER='#f4f0e7';INK=(16,28,37,242);ORANGE=BRAND.accent
SAFE_LEFT=192;SAFE_RIGHT=3648;TICKER_TOP=1936;TICKER_TEXT_HEIGHT=160
TICKER_HEIGHT=2160-TICKER_TOP

def font(size,bold=True):
    f=ImageFont.truetype(str(FONTS/('BarlowCondensed-Bold.ttf' if bold else 'SourceSans3.ttf')),size)
    if not bold:f.set_variation_by_axes([600])
    return f
def fit(draw,text,size,width,bold=True,minimum=28):
    while size>minimum and draw.textlength(text,font=font(size,bold))>width:size-=1
    return font(size,bold)

def brand(d,x=SAFE_LEFT,y=108,scale=1,accent=ORANGE):
    z=lambda v:round(v*scale)
    d.rectangle((x,y,x+z(124),y+z(124)),fill=accent)
    for a,b,c in [(15,109,84),(25,99,64),(40,84,44)]:d.line((x+z(a),y+z(c),x+z(b),y+z(c)),fill=PAPER,width=z(8))
    d.polygon([(x+z(62),y+z(14)),(x+z(74),y+z(34)),(x+z(50),y+z(34))],fill=PAPER)
    from .branding import logo_path
    custom=logo_path()
    if custom:
        with Image.open(custom) as source:
            logo=source.convert('RGBA');logo.thumbnail((z(124),z(124)))
            d.rectangle((x,y,x+z(124),y+z(124)),fill=accent)
            d._image.paste(logo,(x+(z(124)-logo.width)//2,y+(z(124)-logo.height)//2),logo)
    d.text((x+z(148),y-z(4)),BRAND.station_short,font=fit(d,BRAND.station_short,z(88),z(500),minimum=z(22)),fill=PAPER,stroke_width=1,stroke_fill='#101c25')
    d.text((x+z(148),y+z(88)),BRAND.tagline,font=fit(d,BRAND.tagline,z(27),z(550),False,minimum=z(12)),fill=PAPER,stroke_width=1,stroke_fill='#101c25')

def render(state):
    fields={k:getattr(state,k) for k in ['camera','scene','location','kicker','headline','subline','show_lower']}
    fields['renderer']='foundation-brand-v1';fields['branding']=BRAND.model_dump();fields['members']=QUADS.get(state.camera,[]);fields['sources']={id:CAMERAS[id] for id in QUADS.get(state.camera,[state.camera]) if id in CAMERAS}
    key=hashlib.sha256(json.dumps(fields,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:24]
    folder=DATA/'graphics';folder.mkdir(parents=True,exist_ok=True);path=folder/(key+'.png')
    if valid_image(path,(3840,2160)):return path
    im=Image.new('RGBA',(3840,2160));d=ImageDraw.Draw(im)
    camera=state.camera;quad=camera in QUADS;breaking=state.scene=='breaking';accent='#b72c30' if breaking else ORANGE
    if state.scene=='standby':
        d.rectangle((0,0,3840,2160),fill=INK)
        d.text((240,540),BRAND.station_name,font=font(56),fill=accent)
        d.text((240,850),'Live cameras unavailable',font=font(150),fill=PAPER)
    if (camera.startswith('radar-') or camera in DIRECT_SCENES) and state.scene!='standby':
        # Provider title, timestamp and legend remain fully visible.
        im.save(path,format='PNG',compress_level=2)
        return path
    x,y,scale=SAFE_LEFT,108,.8 if quad else 1
    if camera in MAP_SCENES:d.rectangle((x-20,y-16,x+680,y+150),fill=INK)
    brand(d,x,y,scale,accent)
    if not quad and camera not in ('map','map-island'):
        loc=state.location;f=fit(d,loc,38,1300,False);w=int(d.textlength(loc,font=f))+64;right=SAFE_RIGHT
        d.rectangle((right-w,110,right,210),fill=INK);d.rectangle((right-w-206,110,right-w,210),fill=accent)
        d.text((right-w+32,134),loc,font=f,fill=PAPER)
        # A static graphic must not claim a failed or held camera is live.
        tag=BRAND.station_short if state.scene=='standby' else 'LOCAL' if camera=='weather' else 'CAMERA'
        tf=font(32,False);d.text((right-w-103-d.textlength(tag,font=tf)/2,139),tag,font=tf,fill=PAPER)
    if quad and state.scene!='standby':
        for i,id in enumerate(QUADS[camera]):
            source=CAMERAS[id];name=source['name'].upper();place=source['location']
            credit=source['attribution_text'] if source['attribution_enabled'] else ''
            left=(i%2)*1920;x=SAFE_LEFT if i%2==0 else left+48
            right=1872 if i%2==0 else SAFE_RIGHT
            y=796 if i<2 else TICKER_TOP-284
            bottom=1080 if i<2 else 2160
            d.rectangle((left,y,left+1919,bottom),fill='#101c25')
            d.rectangle((x,y,x+5,bottom),fill=accent)
            title=f'{i+1:02d} / {name}'
            d.text((x+28,y+26),title,font=fit(d,title,64,right-x-56),fill=PAPER)
            f=fit(d,place,36,right-x-56,False,28)
            d.text((x+28,y+124),place,font=f,fill='#b6c5cf')
            if credit:
                f=fit(d,credit,40,right-x-56,False,28)
                d.text((x+28,y+184),credit,font=f,fill=PAPER)
    elif state.show_lower and camera not in MAP_SCENES and state.scene not in ('clean','standby'):
        kicker=state.kicker or 'CAMERA';f=font(36,False);kw=int(d.textlength(kicker,font=f))+64
        d.rectangle((192,1524,192+kw,1600),fill=accent);d.text((224,1541),kicker,font=f,fill=PAPER)
        d.rectangle((192,1600,3648,1838),fill=(63,21,26,244) if breaking else INK);d.rectangle((192,1600,198,1838),fill=accent)
        headline=state.headline or CAMERAS.get(camera,{}).get('name',BRAND.station_short).upper()
        d.text((240,1643 if not state.subline else 1623),headline,font=fit(d,headline,116,3020,True,64),fill=PAPER)
        d.text((240,1753),state.subline,font=fit(d,state.subline,46,3020,False,30),fill=PAPER)
        name=CAMERAS.get(camera,{}).get('name',BRAND.station_short).upper() if state.headline else BRAND.station_short;f=fit(d,name,52,280,True,16)
        d.line((3318,1678,3318,1758),fill='#62707b',width=2);d.text((3483-d.textlength(name,font=f)/2,1693),name,font=f,fill=PAPER)
    if state.scene!='standby' and not quad:
        for id in [camera] if camera in CAMERAS else []:
            source=CAMERAS[id]
            if not source['attribution_enabled'] or not source['attribution_text']:continue
            text=source['attribution_text'];f=fit(d,text,42,2400,False,30)
            w=round(d.textlength(text,font=f))+40;right=SAFE_RIGHT;top=1433
            d.rectangle((right-w,top,right,top+66),fill=INK)
            d.text((right-w+20,top+7),text,font=f,fill=PAPER)
    tmp=path.with_suffix('.tmp');im.save(tmp,format='PNG',compress_level=2);tmp.replace(path)
    return path


def loading_card(camera):
    folder=DATA/'graphics';folder.mkdir(parents=True,exist_ok=True)
    source=CAMERAS[camera]
    name_hash=hashlib.sha256(('reconnect-v3'+json.dumps(source,sort_keys=True)).encode()).hexdigest()[:12]
    path=folder/f'loading-{camera}-{name_hash}.png'
    if valid_image(path,(1920,1080)):return path
    image=Image.new('RGB',(1920,1080),'#101c25');d=ImageDraw.Draw(image)
    d.rectangle((96,270,104,700),fill=ORANGE)
    d.text((136,265),source['name'].upper(),font=fit(d,source['name'].upper(),64,1650),fill=PAPER)
    d.text((136,365),'CAMERA TEMPORARILY UNAVAILABLE',font=fit(d,'CAMERA TEMPORARILY UNAVAILABLE',76,1650),fill=PAPER)
    d.text((136,560),source['location'],font=fit(d,source['location'],36,1650,False),fill='#b6c5cf')
    if source['attribution_enabled'] and source['attribution_text']:
        d.text((136,625),source['attribution_text'],font=fit(d,source['attribution_text'],36,1650,False),fill='#b6c5cf')
    tmp=path.with_suffix('.tmp');image.save(tmp,format='PNG');tmp.replace(path)
    return path

def recovery_badge():
    folder=DATA/'graphics';folder.mkdir(parents=True,exist_ok=True)
    path=folder/'camera-recovery-v1.png'
    if valid_image(path,(1920,1080)):return path
    image=Image.new('RGBA',(1920,1080));d=ImageDraw.Draw(image)
    d.rounded_rectangle((96,148,645,218),radius=7,fill='#182b36')
    d.rectangle((96,148,102,218),fill='#ffb578')
    d.text((120,158),'SIGNAL RECOVERING',font=font(40),fill=PAPER)
    tmp=path.with_suffix('.tmp');image.save(tmp,format='PNG');tmp.replace(path)
    return path
