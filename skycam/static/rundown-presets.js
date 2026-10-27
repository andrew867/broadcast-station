'use strict';
let loadedPresetName='';
const rundownDuration=seconds=>Math.floor(seconds/60)+':'+String(seconds%60).padStart(2,'0');
function rundownEditorMatches(){
  return !!liveRundown && JSON.stringify(cues)===JSON.stringify(liveRundown.cues) &&
    $('transition').value===liveRundown.transition && $('resumeRundown').checked===!!liveRundown.resume_after_restart;
}
function updateRundownEditor(){
  if(!rundownLoaded)return;
  const matches=rundownEditorMatches(),seconds=cues.reduce((sum,c)=>sum+(Number(c.seconds)||0),0);
  $('rundownEditorStatus').textContent=(matches?'Saved rundown':(loadedPresetName||'Edited rundown')+' · UNSAVED')+
    ' · '+cues.length+' views · '+rundownDuration(seconds)+' planned hold time'+
    (matches?'':'. Save rundown, then Start automatic rotation to use these edits.');
  $('rundownEditorStatus').className=matches?'hint':'hint warn';
  $('startRundown').disabled=!matches;
  $('startRundown').title=matches?'':'Save the edited rundown before starting it';
  for(const card of $('rundownPresets').children)card.classList.toggle('selected',card.dataset.name===loadedPresetName);
}
async function loadRundownPreset(preset){
  try{
    const scenes=await deskRequest('/api/scenes'),known=new Set(scenes.map(s=>s.id));
    const missing=[...new Set(preset.cues.filter(c=>!known.has(c.camera)).map(c=>c.camera))];
    if(missing.length)throw Error('This preset needs unavailable views: '+missing.join(', ')+'. Your editor was not changed.');
    views=Object.fromEntries(scenes.map(s=>[s.id,s.name]));
    cues=structuredClone(preset.cues);$('transition').value=preset.transition;
    // Restart recovery is an operator preference, not part of a programme format.
    loadedPresetName=preset.name;cueRows();updateRundownEditor();
    $('rundownPresetMessage').textContent=preset.name+' loaded into the editor. The on-air rundown has not changed.';return true;
  }catch(error){$('rundownPresetMessage').textContent=error.message;return false;}
}
$('reloadSavedRundown').onclick=async()=>{
  try{
    const saved=await deskRequest('/api/rundown');loadedPresetName='';rundownLoaded=false;rundownStatus(saved);updateRundownEditor();
    $('rundownPresetMessage').textContent='Saved rundown restored to the editor. The on-air rundown has not changed.';
  }catch(error){$('rundownPresetMessage').textContent=error.message;return false;}
};
for(const event of ['input','change','click'])$('rundownPanel').addEventListener(event,updateRundownEditor);
async function showRundownPresets(){
  try{
    const presets=await deskRequest('/static/rundown-presets.json');
    $('rundownPresets').replaceChildren(...presets.map(preset=>{
      const card=document.createElement('button');card.type='button';card.className='presetCard';card.dataset.name=preset.name;
      card.setAttribute('aria-label','Load '+preset.name+' into editor');
      const title=document.createElement('strong');title.textContent=preset.name;
      const meta=document.createElement('small');meta.textContent=(preset.recommended?'RECOMMENDED · ':'')+rundownDuration(preset.cues.reduce((sum,c)=>sum+c.seconds,0))+' · '+preset.cues.length+' views';
      const description=document.createElement('span');description.textContent=preset.description;
      const action=document.createElement('b');action.textContent='Load into editor';
      card.append(meta,title,description,action);card.onclick=()=>loadRundownPreset(preset);return card;
    }));
    $('rundownPresetMessage').textContent='Choose a starting point, adjust any holds, then save and start. Loading a preset does not interrupt the current rotation.';
    updateRundownEditor();
  }catch(error){$('rundownPresetMessage').textContent='Presets unavailable: '+error.message;}
}
showRundownPresets();
