'use strict';
const $=id=>document.getElementById(id);let key=sessionStorage.getItem('stationDirectorKey')||'',rows=[],current='',refreshTimer=null,refreshing=false;
$('key').value=key;
async function api(path,method='GET'){
 const response=await fetch('/api/director/'+path,{method,headers:{'X-Director-Key':key,'X-Skycam-Edit':'1'},signal:AbortSignal.timeout(7000)});
 const data=await response.json();if(!response.ok)throw Error(data.detail||'Director request failed');return data;
}
function renderScenes(){
 const query=$('search').value.trim().toLocaleLowerCase();$('scenes').replaceChildren(...rows.filter(row=>(row.name+' '+row.location+' '+(row.family||'')).toLocaleLowerCase().includes(query)).map(row=>{
  const button=document.createElement('button');button.className='scene'+(row.id===current?' current':'');button.dataset.id=row.id;
  const name=document.createElement('strong');name.textContent=row.name;const meta=document.createElement('small');meta.textContent=(row.family||'Scene')+' / '+row.location;
  button.append(name,meta);button.onclick=()=>take(row.id);return button;
 }));
}
function confidence(data){
 const scenes=data.confidence?.scenes||{};$('confidence').replaceChildren(...Object.entries(scenes).filter(([,s])=>s.state!=='current').slice(0,8).map(([id,s])=>{
  const p=document.createElement('p');p.className='state-'+s.state;p.textContent=id.replaceAll('-',' ') + ': '+s.detail;return p;
 }));
 if(!$('confidence').children.length){const p=document.createElement('p');p.className='state-current';p.textContent='Scheduled data scenes are current.';$('confidence').append(p)}
}
async function refresh(){
 clearTimeout(refreshTimer);if(!key||refreshing)return;refreshing=true;
 try{const data=await api('status');$('login').hidden=true;$('controls').hidden=false;rows=data.scenes;current=data.program.camera;$('program').textContent=rows.find(row=>row.id===current)?.name||current||'No scene';$('output').textContent=(data.playout.output?.measured_fps??'Measuring')+' fps / '+(data.rundown.enabled?'Automatic rotation':'Manual hold');$('connection').textContent='Connected to '+data.station;renderScenes();confidence(data)}
 catch(error){$('connection').textContent=error.message;$('controls').hidden=true;$('login').hidden=false}
 finally{refreshing=false;if(key)refreshTimer=setTimeout(refresh,2000)}
}
async function take(scene){try{await api('take/'+encodeURIComponent(scene),'POST');await refresh()}catch(error){$('connection').textContent=error.message}}
$('connect').onclick=()=>{key=$('key').value.trim();sessionStorage.setItem('stationDirectorKey',key);refresh()};
$('search').oninput=renderScenes;
for(const action of ['start','next','pause'])$(action).onclick=async()=>{try{await api('rundown/'+action,'POST');await refresh()}catch(error){$('connection').textContent=error.message}};
$('safe').onclick=async()=>{try{await api('safe','POST');await refresh()}catch(error){$('connection').textContent=error.message}};
refresh();
