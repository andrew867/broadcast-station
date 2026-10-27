'use strict';
const $=id=>document.getElementById(id),params=new URLSearchParams(location.search),preview=params.get('preview')==='1',region=params.get('region');
document.body.className=region?'region-'+region:'';
let stageScale=1;
let activeItems=[];
let config=null,version='',animation=null,pendingTicker=null,lastTicker='',tickerCycle=0,frameTimes=[],lastFrame=0;
const cameraNames={map:'AIRSPACE',quad:'ALL FOUR VIEWS',cam1:'WEST',cam2:'NORTH',cam3:'QUIDI VIDI',cam4:'TORBAY'};
const referenceFiles={cam1:'cam1-night.png',cam2:'cam2-night.png',cam3:'cam3-reference.png',cam4:'cam4-reference.png'};
function resize(){const s=region?innerWidth/3840:Math.min(innerWidth/3840,innerHeight/2160);stageScale=s;$('stage').style.transform=`scale(${s})`;$('stage').style.left=(innerWidth-3840*s)/2+'px';$('stage').style.top=(region?(region==='ticker'?-1936*s:region==='bottom'?-1560*s:region==='quadmid'?-796*s:0):(innerHeight-2160*s)/2)+'px'}
addEventListener('resize',resize);resize();
function setText(id,value){if($(id).textContent!==value)$(id).textContent=value}
function tickerContent(items,note){const group=document.createElement('div');group.className='tickerGroup';for(const item of items.length?items:[{title:note,source:(window.stationBrand?.station_short || 'STATION')}]){const span=document.createElement('span');span.className='tickerItem';const source=document.createElement('span');source.className='tickerSource';source.textContent=(item.display_source||item.source).toUpperCase();span.append(source,document.createTextNode(item.title));group.append(span)}const gap=document.createElement('span');gap.style.width='0px';gap.style.display='inline-block';group.append(gap);return group}
function applyTicker(data){
  const group=tickerContent(data.items,data.note);$('tickerTrack').replaceChildren(group,group.cloneNode(true));
  const width=group.getBoundingClientRect().width/(stageScale||1);
  if(animation)animation.cancel();
  animation=$('tickerTrack').animate([{transform:'translate3d(0,0,0)'},{transform:`translate3d(${-width}px,0,0)`}],{duration:width/data.speed*1000,iterations:Infinity,easing:'linear'});
  tickerCycle=0;lastTicker=data.key;activeItems=data.items;
}
function applyState(data){
  const s=data.state;const speedChanged=config&&config.ticker_speed!==s.ticker_speed;config=s;const camera=params.get('camera')||s.camera;const catalog=Object.fromEntries((data.camera_sources||[]).map(c=>[c.id,c]));for(const c of Object.values(catalog)){cameraNames[c.id]=c.name.toUpperCase();referenceFiles[c.id]=c.reference}const members=data.quad_scenes?.[camera],isQuad=!!members,isCard=data.scenes?.some(s=>s.id===camera&&s.kind==='card'),isMap=isCard||['map','map-island','radar-east','radar-island','weather'].includes(camera);
  $('stage').className=(preview?'preview ':'')+(isQuad?'quad ':isMap?'map ':'')+s.scene;
  // Radar carries the provider's title and timestamp in the supplied picture.
  document.querySelector('.topline').style.display=(camera.startsWith('radar-')||isCard)?'none':'';
  document.querySelector('.locator').style.display=['map','map-island'].includes(camera)?'none':'';
  document.querySelector('.referenceTag').textContent=isMap?'GRAPHICS PREVIEW / NOT PROGRAM':'REFERENCE IMAGE / NOT LIVE';
  if(isMap)$('reference').style.display='none';
  setText('location',preview&&params.get('camera')?(data.scenes?.find(view=>view.id===camera)?.location||s.location):s.location);setText('kicker',s.kicker||'CAMERA');setText('headline',s.headline||cameraNames[camera]||(window.stationBrand?.station_short || 'STATION'));setText('subline',s.subline);
  setText('cameraPill',s.headline?(cameraNames[camera]||camera.toUpperCase()):(window.stationBrand?.station_short || 'STATION'));
  $('lower').classList.toggle('hidden',isMap||!s.show_lower||s.scene==='clean');$('footer').classList.toggle('hidden',!s.show_ticker||s.scene==='clean');
  if(isQuad){
    if(preview&&$('quadRefs').dataset.members!==JSON.stringify(members.map(id=>[id,referenceFiles[id]]))){$('quadRefs').replaceChildren(...members.map(id=>{const img=document.createElement('img');img.src='/samples/'+referenceFiles[id];return img}));$('quadRefs').dataset.members=JSON.stringify(members.map(id=>[id,referenceFiles[id]]))}
    document.querySelectorAll('.quadLabel').forEach((el,i)=>{
      const c=catalog[members[i]],credit=c.attribution_enabled?c.attribution_text:'';
      const top=i<2?796:1652,bottom=i<2?1080:2160;
      Object.assign(el.style,{top:top+'px',height:bottom-top+'px'});
      el.classList.remove('ntvBottom');
      el.querySelector('b').textContent=String(i+1).padStart(2,'0')+' / '+c.name.toUpperCase();
      el.querySelector('span').textContent=c.location;
      let courtesy=el.querySelector('.quadCourtesy');if(!courtesy){courtesy=document.createElement('small');courtesy.className='quadCourtesy';el.append(courtesy)}courtesy.textContent=credit;
    });
  }
  const source=catalog[camera],credits=!isQuad&&source?.attribution_enabled&&source.attribution_text&&s.scene!=='standby'?[source]:[];
  const creditKey=JSON.stringify(credits);if($('credits').dataset.key!==creditKey){
    $('credits').replaceChildren(...credits.map(source=>{const el=document.createElement('div');el.className='cameraCredit';el.textContent=source.attribution_text;Object.assign(el.style,{right:'192px',top:'1433px',maxWidth:'2440px',fontSize:'42px'});return el}));$('credits').dataset.key=creditKey;
  }
  if(preview&&!isQuad&&!isMap){$('reference').style.display='block';const path='/samples/'+referenceFiles[camera];if(!$('reference').src.endsWith(path))$('reference').src=path;setText('liveTag','PREVIEW');document.querySelector('.referenceTag').textContent='REFERENCE IMAGE / NOT LIVE'}
  else setText('liveTag',s.scene==='standby'?(window.stationBrand?.station_short || 'STATION'):camera==='weather'?'LOCAL':'CAMERA');
  if(preview)setText('liveTag','PREVIEW');
  $('mapPreview').style.display=preview&&isMap?'block':'none';if(preview&&isMap){const path='/map-view?scene='+encodeURIComponent(camera);if(!$('mapPreview').src.endsWith(path))$('mapPreview').src=path;}
  $('aircraft').style.display=s.show_aircraft&&!preview&&!region&&!isQuad&&!isMap?'block':'none';
  if(s.show_aircraft&&!preview&&!region&&!isQuad&&!isMap){const src='/overlay?camera='+encodeURIComponent(camera);if(!$('aircraft').src.endsWith(src)){$('aircraft').src=src;fetch('/api/cameras/'+camera).then(r=>r.json()).then(c=>{const w=c.request.width,h=c.request.height,scale=Math.max(3840/w,2160/h);Object.assign($('aircraft').style,{width:w+'px',height:h+'px',left:(3840-w*scale)/2+'px',top:(2160-h*scale)/2+'px',transform:`scale(${scale})`})})}}
  if(region==='top'||region==='quadmid')return;
  const items=data.headlines,key=JSON.stringify([items.map(p=>[p.title,p.source,p.published_at]),s.ticker_note,s.ticker_speed]);
  setText('tickerCategory',items.length?'HEADLINES':(window.stationBrand?.station_name || 'Station'));
  if(key!==lastTicker)pendingTicker={items,note:s.ticker_note,speed:s.ticker_speed,key};else pendingTicker=null;
  if(pendingTicker&&(speedChanged||!items.length||activeItems.some(old=>!items.some(fresh=>fresh.title===old.title&&fresh.source===old.source)))){applyTicker(pendingTicker);pendingTicker=null}
  if(!animation&&pendingTicker){applyTicker(pendingTicker);pendingTicker=null}
  // Long editorial text shrinks to fit, without squeezing or clipping characters.
  for(const [id,max,min] of [['headline',116,64],['subline',46,34],['cameraPill',52,16]]){const el=$(id);el.style.fontSize=max+'px';let size=max;while(el.scrollWidth>el.clientWidth&&size>min){size--;el.style.fontSize=size+'px'}}
}
async function fetchState(){try{const r=await fetch('/api/broadcast',{cache:'no-store',signal:AbortSignal.timeout(4000)});if(!r.ok)throw Error(r.status);applyState(await r.json());if(region)fetch('/api/program/heartbeat/'+region,{method:'POST',headers:{'X-Skycam-Edit':'1'}}).catch(()=>{})}catch(e){}}
async function poll(){await fetchState();setTimeout(poll,2000)}
function tick(t){
  if(lastFrame&&document.visibilityState==='visible'){frameTimes.push(t-lastFrame);if(frameTimes.length>3600)frameTimes.shift()}lastFrame=t;
  if(animation){const timing=animation.effect.getComputedTiming(),cycle=Math.floor((animation.currentTime||0)/timing.duration);if(cycle>tickerCycle){tickerCycle=cycle;if(pendingTicker){applyTicker(pendingTicker);pendingTicker=null}}}
  requestAnimationFrame(tick);
}
window.skycamPerformance=()=>{const a=[...frameTimes].sort((a,b)=>a-b);return {frames:a.length,mean_ms:a.reduce((s,x)=>s+x,0)/(a.length||1),p95_ms:a[Math.floor(a.length*.95)]||0,p99_ms:a[Math.floor(a.length*.99)]||0,over_25ms:a.filter(x=>x>25).length,ticker_compositor_animation:!!animation,ticker_px_per_second:config?.ticker_speed,viewport:[innerWidth,innerHeight]}};
window.play=()=>{$('stage').style.visibility='visible';animation?.play()};window.stop=()=>{$('stage').style.visibility='hidden';animation?.pause()};window.update=()=>fetchState();window.next=()=>{};
let stationTimezone='UTC';
fetch('/api/station-config').then(r=>r.json()).then(c=>{stationTimezone=c.location.timezone;setText('clockLabel',c.clock_label)}).catch(()=>{});
setInterval(()=>setText('clock',new Intl.DateTimeFormat('en-CA',{timeZone:stationTimezone,hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date())),1000);
poll();requestAnimationFrame(tick);


window.skycamTransition=()=>{document.body.classList.add('switching');setTimeout(()=>document.body.classList.remove('switching'),1000)};
