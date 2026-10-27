'use strict';
const $=id=>document.getElementById(id),canvas=$('still'),ctx=canvas.getContext('2d');
let landmarks=[],solution=null,photo=null,editing=-1,referenceOnly=false;
const numeric=id=>{if($(id).value.trim()==='')throw Error('Enter '+$(id).previousSibling?.textContent);const v=Number($(id).value);if(!Number.isFinite(v))throw Error('Invalid number: '+id);return v};
const optional=id=>$(id).value.trim()===''?null:numeric(id);
function message(text,error=false){$('result').textContent=text;$('result').classList.toggle('error',error)}
function invalidate(){solution=null;$('approved').checked=false;render();message('Inputs changed. Solve and review the calibration again.')}
function request(){if(photo&&(photo.naturalWidth!==numeric('width')||photo.naturalHeight!==numeric('height')))throw Error('Image dimensions must match the loaded native still');return {name:$('name').value,width:numeric('width'),height:numeric('height'),
  site:{lat:numeric('siteLat'),lon:numeric('siteLon'),altitude_msl_m:numeric('siteAlt'),geoid_separation_m:optional('geoid'),verified:$('verified').checked},
  initial_hfov_deg:numeric('hfov'),fit_distortion:$('distortion').checked,video_delay_s:numeric('delay'),approved:$('approved').checked,reference_only:$('referenceOnly').checked,landmarks};}
async function api(url,body,method='POST'){
  const r=await fetch(url,{method,headers:{'Content-Type':'application/json','X-Skycam-Edit':'1'},body:JSON.stringify(body)});
  const data=await r.json();if(!r.ok)throw Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail));return data;
}
function draw(){
  ctx.clearRect(0,0,canvas.width,canvas.height);
  if(photo)ctx.drawImage(photo,0,0,canvas.width,canvas.height);
  const scale=canvas.width/1000;
  ctx.font=`${14*scale}px Arial`;ctx.lineWidth=2*scale;
  landmarks.forEach((p,i)=>{
    ctx.strokeStyle=p.validation?'#f9d776':'#65ffe2';ctx.fillStyle=ctx.strokeStyle;
    ctx.beginPath();ctx.arc(p.x,p.y,6*scale,0,Math.PI*2);ctx.stroke();ctx.fillText(String(i+1),p.x+9*scale,p.y-8*scale);
    if(solution){const q=solution.points[i].projected;ctx.strokeStyle='#ff9d87';ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(q[0],q[1]);ctx.moveTo(q[0]-5*scale,q[1]);ctx.lineTo(q[0]+5*scale,q[1]);ctx.moveTo(q[0],q[1]-5*scale);ctx.lineTo(q[0],q[1]+5*scale);ctx.stroke()}
  });
}
function render(){
  $('points').replaceChildren();landmarks.forEach((p,i)=>{
    const row=document.createElement('tr');
    const values=[`${i+1}. ${p.name}`,`${p.x.toFixed(1)}, ${p.y.toFixed(1)}`,`${p.lat.toFixed(6)}, ${p.lon.toFixed(6)} / ${p.altitude_msl_m} m`,p.validation?'Validation':'Fit',solution?solution.points[i].error_px.toFixed(2)+' px':'Pending'];
    values.forEach(v=>{const td=document.createElement('td');td.textContent=v;row.append(td)});
    const actions=document.createElement('td');
    for(const [label,fn] of [['Edit',()=>edit(i)],['Remove',()=>{landmarks.splice(i,1);editing=-1;invalidate()}]]){const b=document.createElement('button');b.className='secondary';b.textContent=label;b.onclick=fn;actions.append(b)}row.append(actions);$('points').append(row);
  });draw();$('overlayLink').href='/overlay?camera='+encodeURIComponent($('cameraId').value);
}
function edit(i){editing=i;const p=landmarks[i];for(const [id,key] of [['pointName','name'],['px','x'],['py','y'],['lat','lat'],['lon','lon'],['alt','altitude_msl_m'],['pointGeoid','geoid_separation_m']])$(id).value=p[key]??'';$('validation').checked=p.validation;$('pointTitle').textContent='Edit landmark '+(i+1)}
$('cancel').onclick=()=>{editing=-1;$('pointTitle').textContent='New landmark';for(const id of ['pointName','px','py','lat','lon','alt','pointGeoid'])$(id).value='';$('validation').checked=false};
canvas.onclick=e=>{if(!photo)return;const rect=canvas.getBoundingClientRect();$('px').value=((e.clientX-rect.left)*canvas.width/rect.width).toFixed(2);$('py').value=((e.clientY-rect.top)*canvas.height/rect.height).toFixed(2);$('pointName').focus()};
$('add').onclick=()=>{try{const name=$('pointName').value.trim();if(!name)throw Error('Name this landmark');const p={name,x:numeric('px'),y:numeric('py'),lat:numeric('lat'),lon:numeric('lon'),altitude_msl_m:numeric('alt'),geoid_separation_m:optional('pointGeoid'),validation:$('validation').checked};if(p.x<0||p.y<0||p.x>=numeric('width')||p.y>=numeric('height')||Math.abs(p.lat)>90||Math.abs(p.lon)>180)throw Error('Check the pixel and geographic coordinates');if(editing<0)landmarks.push(p);else landmarks[editing]=p;$('cancel').click();invalidate()}catch(e){message(e.message,true)}};
function loadPhoto(url,resetDimensions=true){return new Promise((resolve,reject)=>{const img=new Image();img.onload=()=>{
  if(landmarks.length&&(img.naturalWidth!==numeric('width')||img.naturalHeight!==numeric('height'))){reject(Error('Image dimensions differ from this landmark project. Start a new camera project for a different raster.'));return}
  photo=img;canvas.width=img.naturalWidth;canvas.height=img.naturalHeight;
  if(resetDimensions){$('width').value=canvas.width;$('height').value=canvas.height;invalidate()}
  $('empty').style.display='none';$('dimensions').textContent=`${canvas.width} × ${canvas.height} native pixels`;draw();resolve();};img.onerror=()=>reject(Error('Could not load image'));img.src=url;})}
$('imageFile').onchange=async e=>{if(!e.target.files[0])return;const url=URL.createObjectURL(e.target.files[0]);try{await loadPhoto(url)}catch(err){message(err.message,true)}finally{URL.revokeObjectURL(url)}};
$('reference').onclick=async()=>{try{await loadPhoto('/samples/camera-reference.png');$('referenceOnly').checked=true;message('Recovered September 23 screenshot loaded. It contains two views and browser framing. Use it to try clicks, not to approve a production camera.')}catch(e){message(e.message,true)}};
const referenceFiles={cam1:'cam1-night.png',cam2:'cam2-night.png',cam3:'cam3-reference.png',cam4:'cam4-reference.png'};
for(const id of Object.keys(referenceFiles))$(id+'Still').onclick=async()=>{try{
  if(landmarks.length)throw Error('Save or export your current landmark project before switching reference images');
  const r=await fetch('/api/cameras/'+id);if(!r.ok)throw Error('Create the '+id+' camera profile first');const saved=(await r.json()).request;
  if(saved.landmarks.length)throw Error('This camera has saved landmarks. Select it under Saved camera and reload its matching still.');
  populate(saved);$('cameraId').value=id;referenceOnly=true;$('referenceOnly').checked=true;
  await loadPhoto('/samples/'+referenceFiles[id]);render();message('Reference image loaded for landmark practice. It cannot be approved for production. Use a matching native live frame for final alignment.');
  if(id==='cam3'||id==='cam4'){for(const key of ['siteLat','siteLon','siteAlt'])$(key).value='';message('Reference loaded. Enter this camera’s own location and elevation; the hilltop site does not apply here.')}
}catch(e){message(e.message,true)}};
function report(s){solution=s;render();message(`Horizontal FOV ${s.hfov_deg.toFixed(2)}° | Vertical FOV ${s.vfov_deg.toFixed(2)}°\nFit RMS ${s.rms_px.toFixed(2)} px | Validation RMS ${s.validation_rms_px===null?'not measured':s.validation_rms_px.toFixed(2)+' px'} | Maximum ${s.max_error_px.toFixed(2)} px\nRadial k1 ${s.distortion[0].toFixed(5)}, k2 ${s.distortion[1].toFixed(5)}\n${s.warnings.length?s.warnings.join('\n'):'Checks passed. Verify against the video before approving production.'}`,!s.acceptable)}
async function busy(fn){$('solve').disabled=$('save').disabled=true;try{await fn()}catch(e){message(e.message,true)}finally{$('solve').disabled=$('save').disabled=false}}
$('solve').onclick=()=>busy(async()=>{message('Solving camera orientation, FOV and lens distortion…');report(await api('/api/solve',request()))});
$('save').onclick=()=>busy(async()=>{const saved=await api('/api/cameras/'+encodeURIComponent($('cameraId').value),request(),'PUT');if(saved.calibration)report(saved.calibration);else{solution=null;render();message(saved.calibration_error||'No calibration solved.')}message($('result').textContent+'\nSaved '+($('approved').checked?'approved calibration.':'draft. Production labels are hidden.'));await refreshCameras()});
function populate(req){referenceOnly=!!req.reference_only;$('referenceOnly').checked=referenceOnly;for(const [id,key] of [['name','name'],['width','width'],['height','height'],['hfov','initial_hfov_deg'],['delay','video_delay_s']])$(id).value=req[key];for(const [id,key] of [['siteLat','lat'],['siteLon','lon'],['siteAlt','altitude_msl_m'],['geoid','geoid_separation_m']])$(id).value=req.site[key]??'';$('verified').checked=req.site.verified;$('distortion').checked=req.fit_distortion;$('approved').checked=req.approved;landmarks=req.landmarks;solution=null;photo=null;canvas.width=req.width;canvas.height=req.height;$('empty').style.display='flex';$('dimensions').textContent=`${req.width} × ${req.height}; reload the matching still`;render()}
async function refreshCameras(){const list=await (await fetch('/api/cameras')).json();$('saved').replaceChildren(new Option('New camera',''));for(const c of list)$('saved').append(new Option(c.request.name+(c.request.approved?' · approved':' · draft'),c.id))}
$('saved').onchange=async()=>{if(!$('saved').value)return;try{const c=await(await fetch('/api/cameras/'+encodeURIComponent($('saved').value))).json();$('cameraId').value=$('saved').value;populate(c.request);if(c.calibration)report(c.calibration)}catch(e){message(e.message,true)}};
$('export').onclick=()=>{try{const data={schema:1,camera_id:$('cameraId').value,request:request()};const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=$('cameraId').value+'-landmarks.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}catch(e){message(e.message,true)}};
$('import').onchange=async e=>{try{const data=JSON.parse(await e.target.files[0].text());if(data.schema!==1||!data.request||!Array.isArray(data.request.landmarks))throw Error('Unsupported landmark project');$('cameraId').value=data.camera_id;populate(data.request);$('approved').checked=false;message('Imported landmarks. Load the matching image and solve before saving.')}catch(err){message(err.message,true)}};
for(const id of ['name','width','height','siteLat','siteLon','siteAlt','geoid','verified','hfov','delay','distortion'])$(id).addEventListener('change',invalidate);
$('cameraId').oninput=render;
$('approved').onchange=()=>{$('save').textContent=$('approved').checked?'Save approved camera':'Save draft'};
async function health(){try{const h=await(await fetch('/api/health')).json();$('health').textContent=h.host+' · '+(h.healthy?`${h.aircraft_received} aircraft received · ${h.buffered_tracks} buffered tracks`:'Feed unavailable: '+(h.error||'stale snapshot'))}catch(e){$('health').textContent='Service unavailable'}setTimeout(health,2000)}
refreshCameras();health();render();

$('referenceOnly').onchange=invalidate;
const map=L.map('map').setView([47.57,-52.70],12);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(map);
let mapPoint=null;
map.on('click',e=>{const camera=$('mapMode').value==='camera';$(camera?'siteLat':'lat').value=e.latlng.lat.toFixed(7);$(camera?'siteLon':'lon').value=e.latlng.lng.toFixed(7);if(mapPoint)mapPoint.remove();mapPoint=L.circleMarker(e.latlng,{radius:7,color:'#18dec2',fillOpacity:.8}).addTo(map);$('mapStatus').textContent=(camera?'Camera origin':'Landmark')+' selected: '+e.latlng.lat.toFixed(7)+', '+e.latlng.lng.toFixed(7)+'. Elevation still requires verification.';if(camera){$('verified').checked=false;invalidate()}});
