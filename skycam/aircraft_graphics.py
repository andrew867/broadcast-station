"""Approved camera labels on source layers, with an engine-timed expiry slate."""
import asyncio,time
from PIL import Image,ImageDraw
from .graphics import font
from . import playout

class AircraftGraphics:
    def __init__(self,data,broadcast,get_frame):
        self.folder=data/'runtime'/'aircraft';self.folder.mkdir(parents=True,exist_ok=True)
        self.broadcast=broadcast;self.get_frame=get_frame;self.active=set();self.status={}
        self.blank=self.folder/'transparent.png'
        Image.new('RGBA',(1920,1080)).save(self.blank)
    def clear(self,camera):
        if camera in self.active:
            playout.command(f'CLEAR {playout.source_channel(camera)}-15');self.active.discard(camera)
    def draw(self,payload):
        image=Image.new('RGBA',(1920,1080));d=ImageDraw.Draw(image);boxes=[]
        scale=max(1920/payload['width'],1080/payload['height'])
        ox=(1920-payload['width']*scale)/2;oy=(1080-payload['height']*scale)/2
        for p in payload['labels']:
            x=p['x']*scale+ox;y=p['y']*scale+oy
            if not (0<=x<1920 and 0<=y<1080):continue
            text=f"{p['callsign']}  {round(p['altitude_ft']):,} ft GNSS";f=font(28)
            width=d.textlength(text,font=f)+24
            lx=max(8,min(1912-width,x+18));ly=max(8,min(996,y-72))
            for _ in range(8):
                if not any(lx<b[2] and lx+width>b[0] and ly<b[3] and ly+68>b[1] for b in boxes):break
                ly+=74
            if ly>1000:continue
            boxes.append((lx,ly,lx+width,ly+68))
            d.ellipse((x-6,y-6,x+6,y+6),outline='#8ef5ff',width=2)
            d.line(((x,y),(lx,ly+34)),fill='#8ef5ff',width=2)
            d.rounded_rectangle(boxes[-1],radius=4,fill=(3,14,23,220))
            d.text((lx+12,ly+5),text,font=f,fill='white')
            d.text((lx+12,ly+37),f"{p['range_km']:.1f} km / {p['mode']}",font=font(19,False),fill='#b7e0e5')
        return image
    def tick(self):
        if not playout.STATUS.get('ready'):return
        with playout.LOCK:
            wanted=(playout.required(playout._camera)|playout.required(playout._prepared['camera'] if playout._prepared else None)) if self.broadcast.state.show_aircraft else set()
            for camera in self.active-wanted:self.clear(camera)
            for camera in wanted:
                payload=self.get_frame(camera)
                fresh=payload['state']=='live' and payload['labels'] and playout.STATUS['cameras'].get(camera,{}).get('native_ready')
                if not fresh:
                    self.clear(camera);self.status[camera]=payload['state'];continue
                path=self.folder/f'{camera}-{time.time_ns()}.png';self.draw(payload).save(path,compress_level=1)
                ch=playout.source_channel(camera)
                # Camera channels run at 30p. AUTO replaces this image with a
                # transparent image after 18 frames even if the controller dies.
                playout.command(f'PLAY {ch}-15 "/workspace/runtime/aircraft/{path.name}" LENGTH 18')
                playout.command(f'LOADBG {ch}-15 "/workspace/runtime/aircraft/{self.blank.name}" AUTO')
                self.active.add(camera);self.status[camera]='live'
                for old in sorted(self.folder.glob(f'{camera}-*.png'))[:-4]:old.unlink(missing_ok=True)
    async def watch(self):
        if not playout.ENABLED:return
        while True:
            try:await asyncio.to_thread(self.tick)
            except Exception as exc:self.status['error']=str(exc)[:200]
            await asyncio.sleep(.2)
