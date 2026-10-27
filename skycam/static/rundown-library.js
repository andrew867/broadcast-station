'use strict';
let savedRundowns={revision:0,items:[],can_undo:false};
const librarySelection=()=>savedRundowns.items.find(item=>item.id===$('savedRundown').value);
const editorConfig=()=>({cues:structuredClone(cues),transition:$('transition').value,resume_after_restart:$('resumeRundown').checked});
function showLibrary(data,selected=$('savedRundown').value){
  savedRundowns=data;
  $('savedRundown').replaceChildren(new Option(data.items.length?'Choose a saved rundown':'No saved rundowns yet',''),...data.items.map(item=>new Option(item.name,item.id)));
  $('savedRundown').value=data.items.some(item=>item.id===selected)?selected:'';
  const hasSelection=!!librarySelection();
  for(const id of ['loadSavedRundown','replaceSavedRundown','renameSavedRundown','duplicateSavedRundown','deleteSavedRundown','exportSavedRundown'])$(id).disabled=!hasSelection;
  $('undoLibrary').disabled=!data.can_undo;
}
async function refreshLibrary(){showLibrary(await deskRequest('/api/rundown-library'))}
function libraryMessage(text){$('libraryMessage').textContent=text}
async function libraryAction(operation,message){
  try{
    const result=await operation();showLibrary(result,result.saved_id||$('savedRundown').value);
    if(librarySelection())$('rundownName').value=librarySelection().name;
    libraryMessage(message+' The on-air rundown is unchanged.');
  }catch(error){
    const name=$('rundownName').value;
    try{await refreshLibrary();$('rundownName').value=name}catch(_){}
    libraryMessage(error.message);
  }
}
function writeBody(config,name=$('rundownName').value.trim()){return {name,config,expected_revision:savedRundowns.revision}}
function spareName(base){
  const names=new Set(savedRundowns.items.map(i=>i.name.toLowerCase()));let name=base.slice(0,59)+' copy',index=2;
  while(names.has(name.toLowerCase()))name=base.slice(0,53)+' copy '+index++;
  return name;
}
$('savedRundown').onchange=()=>{const selected=librarySelection();showLibrary(savedRundowns,$('savedRundown').value);if(selected)$('rundownName').value=selected.name;};
$('saveRundownAs').onclick=()=>libraryAction(()=>deskRequest('/api/rundown-library','POST',writeBody(editorConfig())),'Editor saved as a named rundown.');
$('replaceSavedRundown').onclick=()=>libraryAction(()=>deskRequest('/api/rundown-library/'+librarySelection().id,'PUT',writeBody(editorConfig())),'Saved rundown replaced with the editor. Undo is available.');
$('renameSavedRundown').onclick=()=>libraryAction(()=>deskRequest('/api/rundown-library/'+librarySelection().id,'PUT',writeBody(librarySelection().config)),'Rundown renamed.');
$('duplicateSavedRundown').onclick=()=>libraryAction(()=>deskRequest('/api/rundown-library','POST',writeBody(librarySelection().config,spareName(librarySelection().name))),'Saved rundown duplicated.');
$('deleteSavedRundown').onclick=()=>libraryAction(()=>deskRequest('/api/rundown-library/'+librarySelection().id,'DELETE',{expected_revision:savedRundowns.revision}),'Saved rundown deleted. Use Undo library change to restore it.');
$('undoLibrary').onclick=()=>libraryAction(()=>deskRequest('/api/rundown-library/undo','POST',{expected_revision:savedRundowns.revision}),'Last library change undone.');
$('reloadLibrary').onclick=async()=>{try{await refreshLibrary();libraryMessage('Saved rundown list refreshed.')}catch(e){libraryMessage(e.message)}};
$('loadSavedRundown').onclick=async()=>{
  const item=librarySelection();if(!item)return;
  if(await loadRundownPreset({name:item.name,...item.config})){
    $('resumeRundown').checked=item.config.resume_after_restart;updateRundownEditor();
    libraryMessage(item.name+' loaded into the editor. Save rundown, then Start to put it on air.');
  }
};
$('exportSavedRundown').onclick=async()=>{
  try{
    const item=librarySelection();if(!item)return;
    const exported=await deskRequest('/api/rundown-library/'+item.id+'/export');
    const url=URL.createObjectURL(new Blob([JSON.stringify(exported,null,2)+'\n'],{type:'application/json'}));
    const a=document.createElement('a');a.href=url;a.download='skycam-rundown-'+item.name.replace(/[^a-z0-9]+/gi,'-').toLowerCase()+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    libraryMessage('Export downloaded. It contains the saved rundown, not unsaved editor changes.');
  }catch(error){libraryMessage(error.message)}
};
$('importSavedRundown').onclick=()=>$('rundownImport').click();
$('rundownImport').onchange=async event=>{
  const file=event.target.files[0];if(!file)return;
  try{
    if(file.size>262144)throw Error('Choose a rundown JSON smaller than 256 KB.');
    const imported=JSON.parse(await file.text());
    if(imported.format!=='skycam-rundown'||imported.version!==1||typeof imported.name!=='string'||!imported.config)throw Error('This is not a supported SkyCam rundown export.');
    let name=imported.name;if(savedRundowns.items.some(item=>item.name.toLowerCase()===name.toLowerCase()))name=spareName(name);
    await libraryAction(()=>deskRequest('/api/rundown-library','POST',writeBody(imported.config,name)),'Rundown imported into the library.');
  }catch(error){libraryMessage(error.message)}finally{event.target.value=''}
};
refreshLibrary().catch(error=>libraryMessage('Saved rundowns unavailable: '+error.message));

// Reordering is a draft edit, just like the existing arrow buttons.
let draggedCue=null;
$('rundownRows').addEventListener('dragstart',event=>{
  if(!event.target.classList.contains('cueDrag'))return;
  draggedCue=[...$('rundownRows').children].indexOf(event.target.closest('.cue'));
  event.dataTransfer.effectAllowed='move';event.dataTransfer.setData('text/plain',String(draggedCue));
});
$('rundownRows').addEventListener('dragover',event=>{if(draggedCue!==null&&event.target.closest('.cue')){event.preventDefault();event.dataTransfer.dropEffect='move'}});
$('rundownRows').addEventListener('drop',event=>{
  const row=event.target.closest('.cue');if(draggedCue===null||!row)return;
  event.preventDefault();const target=[...$('rundownRows').children].indexOf(row);
  const [cue]=cues.splice(draggedCue,1);cues.splice(target,0,cue);draggedCue=null;cueRows();updateRundownEditor();
});
$('rundownRows').addEventListener('dragend',()=>{draggedCue=null});
