const $=id=>document.getElementById(id);let dirty=new Set();let state=null,sources=[],playoutEnabled=false,selectedCamera=null;

function form(s){state=s;for(const key of ['scene','kicker','headline','subline','location','ticker_speed','ticker_note','news_mix'])$(key).value=s[key];for(const key of ['show_lower','show_ticker','show_aircraft'])$(key).checked=s[key];for(const key of ['vocm','ntv','cbc_nl','cbc_canada','bbc_world','good_news','positive_news'])$(key).checked=s.news_sources.includes(key);$('speedValue').textContent=s.ticker_speed+' px/s';renderCameras()}

let cameraCardsKey=null;
function renderCameras(){const key=JSON.stringify(sources);if(cameraCardsKey===key){for(const card of $('cameras').children)card.classList.toggle('selected',card.dataset.camera===(selectedCamera||state.camera));return}cameraCardsKey=key;$('cameras').replaceChildren();for(const s of sources){const b=document.createElement('button');b.dataset.camera=s.id;b.dataset.family=s.family||'Other';b.className='card'+(s.id===(selectedCamera||state.camera)?' selected':'');const img=document.createElement('img');img.src='/samples/'+s.reference;img.alt='';const name=document.createElement('span');name.textContent=s.name;const confidence=document.createElement('small');confidence.className='sceneConfidence '+(s.confidence?.state||'current');confidence.textContent=s.confidence?.state==='unavailable'?'Unavailable':s.confidence?.state==='cached'?'Cached data':s.confidence?.state==='current'?'Current':'';b.append(img,name,confidence);b.onclick=async()=>{selectedCamera=s.id;$('preview').src='/broadcast?preview=1&camera='+s.id;renderCameras();$('feedback').textContent='Preview selected. Use Take selected camera live to change the program.'};$('cameras').append(b)}}

async function save(){try{const latest=await (await fetch('/api/broadcast')).json();const next={...latest.state};for(const key of ['scene','kicker','headline','subline','location','ticker_note','news_mix'])if(dirty.has(key))next[key]=$(key).value;next.ticker_speed=Number($('ticker_speed').value);for(const key of ['show_lower','show_ticker','show_aircraft'])next[key]=$(key).checked;next.news_sources=['vocm','ntv','cbc_nl','cbc_canada','bbc_world','good_news','positive_news'].filter(k=>$(k).checked);const r=await fetch('/api/broadcast',{method:'PUT',headers:{'Content-Type':'application/json','X-Skycam-Edit':'1'},body:JSON.stringify(next)});const d=await r.json();if(!r.ok)throw Error(JSON.stringify(d.detail));state=d.state;dirty.clear();form(d.state);renderCameras();$('feedback').textContent='Graphics saved. Active graphics pages will update within two seconds.'}catch(e){$('feedback').textContent=e.message}}

function news(d){$('newsCount').textContent=d.headlines.length+' SELECTED HEADLINES';$('news').replaceChildren();for(const item of d.headlines){const row=document.createElement('div');row.className='newsItem';const a=document.createElement('a');a.textContent=item.title;a.href=item.link;a.target='_blank';a.rel='noopener';const meta=document.createElement('small');meta.textContent=item.source+' · '+new Date(item.published_at*1000).toLocaleString();row.append(a,meta);$('news').append(row)}$('sourceStatus').replaceChildren();for(const [key,s]of Object.entries(d.sources)){const row=document.createElement('div');row.className='sourceRow '+(s.error?'warn':'good');row.textContent=s.name+': '+(s.error?s.error:s.fetched_at?'updated '+new Date(s.fetched_at*1000).toLocaleTimeString():'waiting for first refresh');$('sourceStatus').append(row)}}

let broadcastConnectionLost=true;
async function refresh(){try{const [r,c]=await Promise.all([fetch('/api/broadcast',{signal:AbortSignal.timeout(7000)}),fetch('/api/scene-confidence',{signal:AbortSignal.timeout(7000)})]);if(!r.ok)throw Error('Service unavailable');const d=await r.json();const confidence=c.ok?await c.json():{scenes:{}};if(broadcastConnectionLost){broadcastConnectionLost=false;playoutEnabled=!!d.playout_enabled;$('takeCamera').disabled=!playoutEnabled;}if(d.scenes)sources=d.scenes.map(scene=>({...scene,confidence:confidence.scenes?.[scene.id]}));if(!state){playoutEnabled=!!d.playout_enabled;$('takeCamera').disabled=!playoutEnabled;form(d.state);$('feedback').textContent='Ready';$('preview').src='/broadcast?preview=1&camera='+state.camera}if($('feedback').textContent==='Service unavailable')$('feedback').textContent='Connected';for(const key of ['scene','location'])if(!dirty.has(key))$(key).value=d.state[key];state={...d.state};renderCameras();news(d);const p=d.playout;$('programStatus').textContent=p?.enabled?(p.connected?'On air: '+(p.program?.camera||d.state.camera)+' / '+(p.output?.measured_fps??'measuring')+' fps'+(p.program?.held?' / Held picture':''):'CasparCG reconnecting: '+(p.error||'')):'Graphics-only desk';$('programSources').replaceChildren(...Object.entries(p?.cameras||{}).map(([id,c])=>{const row=document.createElement('p');row.textContent=id+': '+(c.display||(c.ready?'ready':c.state||'reconnecting'))+(c.error?' / '+c.error:'');return row}));}catch(e){broadcastConnectionLost=true;$('takeCamera').disabled=true;$('feedback').textContent='Service unavailable';$('programStatus').textContent='Connection lost: program status unavailable'}setTimeout(refresh,2000)}

let speedTimer=null,speedRevision=0;
async function saveTickerSpeed(revision){
 const speed=Number($('ticker_speed').value);
 try{
  const latest=await (await fetch('/api/broadcast')).json();
  if(revision!==speedRevision)return;
  const response=await fetch('/api/broadcast',{method:'PUT',headers:{'Content-Type':'application/json','X-Skycam-Edit':'1'},body:JSON.stringify({...latest.state,ticker_speed:speed})});
  if(!response.ok)throw Error('Ticker speed could not be saved');
  if(revision===speedRevision){dirty.delete('ticker_speed');$('feedback').textContent='On-air ticker speed: '+speed+' px/s';}
 }catch(error){$('feedback').textContent=error.message;}
}
$('take').onclick=save;$('ticker_speed').oninput=()=>{dirty.add('ticker_speed');$('speedValue').textContent=$('ticker_speed').value+' px/s';clearTimeout(speedTimer);const revision=++speedRevision;speedTimer=setTimeout(()=>saveTickerSpeed(revision),250)};fetch('/api/scenes',{signal:AbortSignal.timeout(7000)}).then(r=>{if(!r.ok)throw Error('Scenes unavailable');return r.json()}).then(s=>{sources=s;refresh()}).catch(()=>refresh());



$('takeCamera').onclick=async()=>{$('takeCamera').disabled=true;try{$('feedback').textContent='Preparing picture and graphics off air…';const camera=selectedCamera||state.camera;const r=await fetch('/api/program/take/'+camera,{method:'POST',headers:{'X-Skycam-Edit':'1'}});const d=await r.json();if(!r.ok)throw Error(d.detail);state.camera=camera;state.location=sources.find(s=>s.id===camera).location;$('location').value=sources.find(s=>s.id===camera).location;$('feedback').textContent=d.note;renderCameras()}catch(e){$('feedback').textContent=e.message}finally{$('takeCamera').disabled=!playoutEnabled}};


for(const key of ['scene','kicker','headline','subline','location','ticker_note','news_mix','show_lower','show_ticker','show_aircraft','vocm','ntv','cbc_nl','cbc_canada','bbc_world','good_news','positive_news'])$(key).addEventListener('input',()=>dirty.add(key));

async function refreshHealth(){
 try{
  const response=await fetch('/api/readiness');if(!response.ok)throw Error('Health check unavailable');
  const d=await response.json();
  $('readinessSummary').textContent={attention:'Output needs attention',limited:'On air with limitations',healthy:'Current checks healthy'}[d.state];
  $('readinessSummary').className=d.state==='healthy'?'good':'warn';
  $('readinessChecks').replaceChildren(...d.checks.map(c=>{const row=document.createElement('div');row.className='healthCheck '+(c.level==='ok'?'good':c.level==='error'?'error':'warn');const title=document.createElement('b'),detail=document.createElement('small');title.textContent=(c.level==='ok'?'● ':'! ')+c.label;detail.textContent=c.detail;row.append(title,detail);return row}));
 }catch(e){$('readinessSummary').textContent='Health information unavailable';$('readinessSummary').className='warn';$('readinessChecks').replaceChildren();}
 setTimeout(refreshHealth,3000);
}
refreshHealth();
