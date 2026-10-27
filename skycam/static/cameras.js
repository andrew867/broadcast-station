'use strict';
const $=id=>document.getElementById(id),fields=['id','name','location','media_path','width','height','enabled','attribution_enabled','attribution_text'];let catalog=null,editing=null;
async function request(path,method='GET',body){const r=await fetch(path,{method,headers:{'Content-Type':'application/json','X-Skycam-Edit':'1'},body:body===undefined?undefined:JSON.stringify(body)});const d=await r.json();if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:JSON.stringify(d.detail));return d}
function form(source){editing=source?.id||null;const d=source||{id:'',name:'',location:"ST. JOHN'S, NL",media_path:'',width:1920,height:1080,enabled:true,attribution_enabled:false,attribution_text:''};for(const key of fields)if($(key).type==='checkbox')$(key).checked=d[key];else $(key).value=d[key];$('id').disabled=!!editing;$('deleteCamera').hidden=$('deleteHelp').hidden=!editing;$('editorTitle').textContent=editing?'Edit '+source.name:'Add a camera'}
async function load(){catalog=await request('/api/source-catalog');$('capacity').textContent=catalog.cameras.length+' of '+catalog.capacity+' camera slots assigned';$('library').replaceChildren(...catalog.cameras.map(c=>{const row=document.createElement('div');row.className='camera';const img=document.createElement('img');img.src='/samples/'+c.reference;img.alt='';const text=document.createElement('div'),name=document.createElement('b'),detail=document.createElement('small'),credit=document.createElement('small');name.textContent=c.name;detail.textContent=c.media_path+' · '+c.width+' × '+c.height+' · '+(c.enabled?'Connection enabled':'Connection disabled');credit.textContent=c.attribution_enabled?c.attribution_text:'Attribution off';text.append(name,detail,credit);const edit=document.createElement('button');edit.textContent='Edit';edit.setAttribute('aria-label','Edit '+c.name);edit.onclick=()=>form(c);row.append(img,text,edit);return row}));renderQuads()}

$('editor').onsubmit=async e=>{e.preventDefault();const body=Object.fromEntries(fields.map(k=>[k,$(k).type==='checkbox'?$(k).checked:$(k).type==='number'?Number($(k).value):$(k).value]));$('saveCamera').disabled=true;try{const saved=await request('/api/source-catalog'+(editing?'/'+editing:''),editing?'PUT':'POST',body);await load();form(saved);$('status').textContent=saved.name+' saved. Live graphics and camera connections updated.'}catch(e){$('status').textContent=e.message}finally{$('saveCamera').disabled=false}};
$('newCamera').onclick=()=>form(null);
$('deleteCamera').onclick=async()=>{if(!editing)return;const id=editing;if(!confirm('Delete '+id+' from the camera library?'))return;try{await request('/api/source-catalog/'+id,'DELETE');await load();form(null);$('status').textContent='Camera deleted. Calibration history kept.'}catch(e){$('status').textContent=e.message}};
form(null);load().then(()=>$('status').textContent='Ready').catch(e=>$('status').textContent=e.message);

async function inspectCamera(action){
 if(!editing){$('status').textContent='Save this camera first';return;}
 const button=$(action==='probe'?'probeCamera':'captureCamera');button.disabled=true;$('status').textContent='Reading the live feed...';
 try{const d=await request('/api/source-catalog/'+editing+'/'+action,'POST',{});
 if(action==='probe'){$('width').value=d.width;$('height').value=d.height;$('status').textContent=`${d.width} × ${d.height}, ${d.fps?d.fps.toFixed(2)+' fps reported':'frame rate unknown'}. Save camera to apply dimensions.`;}
 else{await load();$('status').textContent='Native-size reference saved. Open calibration to place landmarks.';}
 }catch(e){$('status').textContent=e.message}finally{button.disabled=false}
}
$('probeCamera').onclick=()=>inspectCamera('probe');$('captureCamera').onclick=()=>inspectCamera('capture');
$('referenceFile').onchange=async()=>{
 const file=$('referenceFile').files[0];if(!file)return;if(!editing){$('status').textContent='Save this camera first';return;}
 try{const r=await fetch('/api/source-catalog/'+editing+'/reference',{method:'POST',headers:{'X-Skycam-Edit':'1','Content-Type':file.type},body:file});const d=await r.json();if(!r.ok)throw Error(d.detail);await load();$('status').textContent='Reference image saved for calibration.'}catch(e){$('status').textContent=e.message}finally{$('referenceFile').value=''}
};

function quadForm(id,members,creating=false){
 const group=document.createElement('section'),title=document.createElement('h3');
 title.textContent=creating?'Add a named quad':catalog.quad_names?.[id]||id;group.append(title);
 const nameLabel=document.createElement('label'),name=document.createElement('input');
 nameLabel.textContent='Scene name';name.maxLength=64;name.value=creating?'':title.textContent;nameLabel.append(name);group.append(nameLabel);
 let identity=null;
 if(creating){const label=document.createElement('label');label.textContent='Scene ID (quad- followed by a short name)';identity=document.createElement('input');identity.placeholder='quad-coast';identity.maxLength=48;label.append(identity);group.append(label)}
 const selectors=members.map((member,i)=>{const label=document.createElement('label');label.textContent=['Top left','Top right','Bottom left','Bottom right'][i];const select=document.createElement('select');select.setAttribute('aria-label',title.textContent+' '+label.textContent);for(const c of catalog.cameras)select.add(new Option(c.name,c.id));select.value=member;label.append(select);group.append(label);return select});
 const actions=document.createElement('div');actions.className='actions';const save=document.createElement('button');save.textContent=creating?'Add quad':'Save quad';actions.append(save);
 save.onclick=async()=>{try{save.disabled=true;const sceneId=creating?identity.value.trim():id;await request('/api/quad-scenes'+(creating?'':'/'+encodeURIComponent(id)),creating?'POST':'PATCH',{id:sceneId,name:name.value,cameras:selectors.map(s=>s.value)});$('status').textContent=name.value+' saved. Available in scene and rundown choices.';await load()}catch(e){$('status').textContent=e.message}finally{save.disabled=false}};
 if(!creating&&!['quad','quad2'].includes(id)){const remove=document.createElement('button');remove.textContent='Delete quad';remove.onclick=async()=>{if(!confirm('Delete '+title.textContent+'?'))return;try{await request('/api/quad-scenes/'+encodeURIComponent(id),'DELETE');await load();$('status').textContent='Quad deleted'}catch(e){$('status').textContent=e.message}};actions.append(remove)}
 group.append(actions);return group;
}
function renderQuads(){
 $('quads').replaceChildren(...Object.entries(catalog.quads).map(([id,members])=>quadForm(id,members)));
 if(Object.keys(catalog.quads).length<(catalog.quad_capacity||12))$('quads').append(quadForm('',catalog.cameras.slice(0,4).map(c=>c.id),true));
}
