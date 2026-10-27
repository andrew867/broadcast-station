"""Native alert pages and bottom graphics. No browser, video or audio consumer."""
import asyncio,hashlib,json,time
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image,ImageDraw
from .graphics import font,fit,brand,PAPER,ORANGE
from .image_cache import valid_image
from .alert_titles import headline,display_body
from .language_policy import english

def local(value):
    d=datetime.fromtimestamp(value,ZoneInfo('America/St_Johns')) if isinstance(value,(int,float)) else datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(ZoneInfo('America/St_Johns'))
    return d.strftime('%b %d, %H:%M')

def wrap(text,size,width,bold=False):
    f=font(size,bold);lines=[]
    for paragraph in text.splitlines():
        if paragraph.strip() and set(paragraph.strip())=={'#'}:continue
        line=''
        for word in paragraph.split():
            if f.getlength((line+' '+word).strip())<=width:line=(line+' '+word).strip();continue
            if line:lines.append(line);line=''
            while f.getlength(word)>width:
                n=max(1,int(len(word)*width/f.getlength(word)))
                while n>1 and f.getlength(word[:n])>width:n-=1
                lines.append(word[:n]);word=word[n:]
            line=word
        if line:lines.append(line)
    return lines or ['More information is available from the issuing agency.']

def identity(a):
    return hashlib.sha256(json.dumps([a['sender'],a['identifier'],a['sent'],a.get('headline'),a.get('language'),body(a),a['areas'],a['expires']],ensure_ascii=False).encode()).hexdigest()[:24]

def body(a):
    return a.get('broadcast_text') or '\n'.join(filter(None,[a.get('headline'),a.get('instruction'),a.get('description')]))

def page_rows(alerts):
    rows=[]
    for a in alerts:
        if not english(a.get('language')):continue
        lines=wrap(display_body(body(a),a),72,3320)
        # All text is retained across pages, not silently ellipsized.
        chunks=[lines[i:i+9] for i in range(0,len(lines),9)]
        areas=wrap('Affected areas: '+' / '.join(a['areas']),52,3320)
        # Long area lists receive their own pages so no district is hidden.
        if len(areas)>2:chunks=[areas[i:i+9] for i in range(0,len(areas),9)]+chunks
        for i,chunk in enumerate(chunks):rows.append({'token':identity(a)+':'+str(i),'alert':a,'lines':chunk,'part':i+1,'parts':len(chunks),'areas':areas[:2] if len(areas)<=2 else ['Affected areas listed on the opening pages.']})
    return rows

def weather_image(row,fresh=True):
    im=Image.new('RGB',(3840,2160),'#0e1e29');d=ImageDraw.Draw(im)
    brand(d,192,108)
    d.text((2250,130),'NEWFOUNDLAND & LABRADOR',font=font(58),fill=PAPER)
    d.rectangle((192,330,3648,341),fill=ORANGE)
    if row is None:
        d.text((240,650),'ALERT INFORMATION',font=font(150),fill=PAPER)
        d.text((240,900),'This alert has ended.',font=font(76,False),fill=PAPER)
        return im
    a=row['alert'];severity=a.get('severity','Weather').upper()
    d.rounded_rectangle((192,400,3648,1845),radius=24,fill='#18323f')
    d.rectangle((192,400,210,1845),fill=ORANGE)
    d.text((270,445),('EMERGENCY INFORMATION' if a.get('broadcast_immediate') else 'WEATHER ADVISORY')+'  /  '+severity,font=font(48),fill='#ffb788')
    title=headline(a)
    # The complete issuer headline is also in the paged text below.
    title_lines=wrap(title,108,3300,True)
    if len(title_lines)>2:title_lines=[a['event'].upper()]
    for i,line in enumerate(title_lines):d.text((270,525+i*120),line,font=font(108),fill=PAPER)
    for i,line in enumerate(row['areas']):d.text((270,790+i*66),line,font=font(52,False),fill='#a9c8d8')
    d.line((270,950,3568,950),fill='#41606e',width=2)
    for i,line in enumerate(row['lines']):d.text((270,990+i*86),line,font=font(72,False),fill=PAPER)
    footer=f"Issued {local(a['sent'])}  |  Expires {local(a['expires'])}  |  Newfoundland time"
    d.text((270,1780),footer,font=fit(d,footer,42,3250,False),fill='#abc3cf')
    source=a.get('sender_name') or a['sender']
    label=source+' via NAADS'+('  |  Feed connection delayed' if not fresh else '')
    d.text((192,1872),label,font=fit(d,label,38,2900,False),fill='#aec5d0')
    if row['parts']>1:d.text((3260,1863),f"PAGE {row['part']} / {row['parts']}",font=font(44),fill='#ffb788')
    return im

def emergency_rows(alerts):
    rows=[]
    for a in alerts:
        if not english(a.get('language')):continue
        lines=wrap('Affected areas: '+' / '.join(a['areas'])+'\n'+display_body(body(a),a),66,3320)
        parts=[lines[i:i+4] for i in range(0,len(lines),4)]
        for i,lines in enumerate(parts):rows.append({'alert':a,'lines':lines,'part':i+1,'parts':len(parts)})
    return rows

def emergency_image(row,fresh=True):
    im=Image.new('RGB',(3840,636),'#310e16');d=ImageDraw.Draw(im);a=row['alert']
    d.rectangle((0,0,3840,115),fill='#885600' if a.get('utility') else '#b42132');d.rectangle((0,0,3840,7),fill='#ffd5ba')
    d.text((192,17),'UTILITY INFORMATION' if a.get('utility') else 'EMERGENCY INFORMATION',font=font(72),fill=PAPER)
    label=a['event'].upper();d.text((1990,25),label,font=fit(d,label,60,1658),fill=PAPER)
    for i,line in enumerate(row['lines']):d.text((192,135+i*82),line,font=font(66,False),fill=PAPER)
    source=(a.get('sender_name') or a['sender'])+(' / Restoration times are estimates' if a.get('utility') else ' via NAADS')
    d.text((192,493),source,font=fit(d,source,40,2500,False),fill='#efb9b4')
    details='UTILITY UPDATE' if a.get('utility') else 'Expires '+local(a['expires'])+' NL'
    if row['parts']>1:details+=f"  |  {row['part']} / {row['parts']}"
    if not fresh:details+='  |  Feed delayed'
    d.text((192,556),details,font=font(38,False),fill=PAPER)
    return im

class AlertPages:
    def __init__(self,data,alerts,scene='weather-alerts'):
        self.scene=scene
        self.folder=data/'runtime'/'alert-pages';self.folder.mkdir(parents=True,exist_ok=True)
        self.alerts=alerts;self.selected=None;self.last_path=None;self.cycle_offset=0;self.rows_key=None;self.cached_rows=[]
    def rows(self):
        d=self.alerts.public()
        items=d.get('immediate',[]) if self.scene=='emergency-alerts' else d['alerts']+[a for a in d.get('immediate',[]) if 'Met' in a.get('categories',[])]
        key=json.dumps(items,sort_keys=True)
        if key!=self.rows_key:self.cached_rows=page_rows(items);self.rows_key=key
        return self.cached_rows
    def followups(self,camera):
        if camera!='weather':return []
        rows=self.rows()
        if not rows:return []
        # Bound any one interlude, rotate remaining pages after the next forecast.
        start=self.cycle_offset%len(rows);chosen=(rows+rows)[start:start+min(12,len(rows))]
        self.cycle_offset=(start+len(chosen))%len(rows)
        return [{'camera':'weather-alerts','scene':'standard','seconds':30,'token':r['token']} for r in chosen]
    def select(self,token):
        if not any(r['token']==token for r in self.rows()):return False
        self.selected=token;return True
    def valid(self,token):return any(r['token']==token for r in self.rows())
    def media(self):
        rows=self.rows();row=next((r for r in rows if r['token']==self.selected),None)
        if self.selected is None and rows:row=rows[int(time.time()//22)%len(rows)]
        fresh=self.alerts.public()['fresh']
        key=hashlib.sha256(json.dumps([row,fresh,'v3-copy-cleanup'],sort_keys=True).encode()).hexdigest()[:24]
        path=self.folder/(key+'.png')
        if not valid_image(path,(3840,2160)):
            tmp=path.with_suffix('.tmp');weather_image(row,fresh).save(tmp,format='PNG',compress_level=1);tmp.replace(path)
        self.last_path=path
        for old in sorted(self.folder.glob('*.png'),key=lambda p:p.stat().st_mtime)[:-24]:
            if old!=path:old.unlink(missing_ok=True)
        return '/workspace/runtime/alert-pages/'+path.name
    async def watch(self):
        from . import playout
        previous=None
        while True:
            try:
                if playout.STATUS.get('ready') and playout._camera==self.scene:
                    path=await asyncio.to_thread(self.media)
                    if path!=previous:
                        with playout.LOCK:
                            if playout._camera==self.scene:playout.command(f'PLAY {playout._bank}-10 "{path}"');previous=path
                else:previous=None
            except Exception:previous=None
            await asyncio.sleep(1)


def summary_image(frame):
    a=frame['row']['alert'];utility=frame['kind']=='utility'
    # Same canvas position as the full presentation, but only the normal
    # lower-third footprint is opaque. The clock and crawl remain underneath.
    im=Image.new('RGBA',(3840,636));d=ImageDraw.Draw(im)
    accent='#f4ca71' if utility else '#ff8b98'
    d.rectangle((192,0,3648,314),fill='#172b36' if utility else '#310e16')
    d.rectangle((192,0,204,314),fill=accent)
    label='POWER OUTAGE' if utility else 'ACTIVE ALERT'
    d.text((240,18),label,font=font(44),fill=accent)
    text=headline(a) if not utility else a.get('headline') or a['event']
    # Full wording is retained in the recurring presentation and detail page.
    from .outages import shorten
    d.text((240,83),shorten(text,76,2750),font=font(76,False),fill=PAPER)
    detail=' / '.join(a['areas'])
    if utility:detail=' / '.join(filter(None,[detail,a.get('restoration_summary')]))
    d.text((240,211),shorten(detail,42,2750),font=font(42,False),fill='#b9cdd6')
    seconds=frame['countdown']
    d.line((3070,65,3070,265),fill='#54707d',width=2)
    d.text((3140,77),f"{seconds//60:02d}:{seconds%60:02d}",font=font(100),fill=PAPER)
    d.text((3140,211),'FULL UPDATE IN',font=font(36),fill=accent)
    return im
