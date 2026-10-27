/* Route navigation preserves the existing control DOM and pending edits. */
(() => {
  'use strict';
  const desk=document.querySelector('.studio');
  const oldMain=desk.querySelector(':scope > section');
  const oldAside=desk.querySelector(':scope > aside');
  const definitions=[['live','Live'],['rundown','Rundown'],['graphics','Graphics'],['music','Music'],['news','News'],['system','System'],['setup','Setup']];
  const pages=new Map();
  for(const [id,label] of definitions){const page=document.createElement('section');page.className='deskPage';page.id='desk-'+id;page.dataset.page=id;page.setAttribute('aria-label',label);pages.set(id,page);}
  const assignment={'Playout rundown':'rundown','Airspace map appearance':'graphics','Background music':'music','Newsroom':'news','On-air graphics':'graphics','Broadcast health':'system'};
  for(const parent of [oldMain,oldAside])for(const node of [...parent.children]){
    const title=node.classList.contains('panel')?node.querySelector('h2')?.textContent.trim():null;
    pages.get(assignment[title]||'live').append(node);
  }
  const live=pages.get('live'),previewColumn=document.createElement('div'),picker=document.createElement('div');
  previewColumn.className='previewColumn';picker.className='scenePicker';
  const sceneHeading=document.createElement('h2');sceneHeading.textContent='Scenes';
  const search=document.createElement('input');search.type='search';search.placeholder='Find a camera or slide';search.setAttribute('aria-label','Find a scene');search.dataset.previewSafe='true';
  const cards=live.querySelector('#cameras'),take=live.querySelector('#takeCamera');
  for(const child of [...live.children])if(child!==cards&&child!==take)previewColumn.append(child);
  picker.append(sceneHeading,search,cards,take);live.append(previewColumn,picker);
  function filterScenes(){const query=search.value.trim().toLocaleLowerCase();for(const card of cards.children)card.hidden=!card.textContent.toLocaleLowerCase().includes(query);}
  search.addEventListener('input',filterScenes);new MutationObserver(filterScenes).observe(cards,{childList:true});
  const links=document.querySelector('header .nav');
  const setup=document.createElement('div');setup.className='panel setupLinks';
  const title=document.createElement('h2');title.textContent='Station setup';setup.append(title);
  for(const link of [...links.children])setup.append(link);
  pages.get('setup').append(setup);
  links.replaceChildren();
  for(const [href,label] of [['/confidence','Confidence'],['/guide','Guide']]){const a=document.createElement('a');a.href=href;a.textContent=label;links.append(a);}
  const top=document.createElement('div');top.className='deskStatus';top.setAttribute('aria-label','Broadcast status');
  const status=document.createElement('span');status.id='deskProgram';status.textContent='Connecting to station';
  const changes=document.createElement('span');changes.id='deskChanges';changes.setAttribute('role','status');top.append(status,changes);
  const nav=document.createElement('nav');nav.className='deskNav';nav.setAttribute('aria-label','Studio pages');
  for(const [id,label]of definitions){const a=document.createElement('a');a.href='/studio/'+id;a.dataset.page=id;a.textContent=label;nav.append(a);}
  const content=document.createElement('main');content.className='deskContent';content.id='deskContent';content.tabIndex=-1;
  content.append(...pages.values());desk.replaceChildren(nav,content);desk.before(top);desk.classList.add('deskShell');
  const skip=document.createElement('a');skip.href='#deskContent';skip.textContent='Skip to page controls';skip.className='skipLink';document.body.prepend(skip);
  let musicDirty=false;
  function dirtyPages(){
    const list=[];
    if(typeof dirty!=='undefined' && dirty.size)list.push('Graphics');
    if(typeof rundownEditorMatches==='function' && typeof liveRundown!=='undefined' && liveRundown && !rundownEditorMatches())list.push('Rundown');
    if(musicDirty)list.push('Music');
    return list;
  }
  function updateStatus(){
    const value=document.getElementById('programStatus')?.textContent||'Connecting to station';status.textContent=value;
    const pending=dirtyPages();changes.textContent=pending.length?'Unapplied changes: '+pending.join(', '):'Changes saved';
    changes.classList.toggle('pending',!!pending.length);
  }
  function show(id,push=false,focus=false){
    if(!pages.has(id))id='live';
    for(const [key,page]of pages)page.hidden=key!==id;
    for(const a of nav.children){if(a.dataset.page===id)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');}
    if(push)history.pushState({page:id},'', '/studio/'+id);
    document.title=definitions.find(row=>row[0]===id)[1]+' | Broadcast desk';
    if(focus)content.focus({preventScroll:true});
    updateStatus();
  }
  nav.addEventListener('click',event=>{const a=event.target.closest('a[data-page]');if(!a||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;event.preventDefault();show(a.dataset.page,true,true);window.scrollTo({top:0});});
  window.addEventListener('popstate',()=>show(location.pathname.split('/')[2]||'live'));
  const pendingMusic=new Set(['musicSource','musicMood','musicSeed','musicCrossfade','musicMatchLevels','radioBpm','radioTranspose','radioDensity','radioSwing','radioRain','radioVinyl','radioMelody']);
  document.addEventListener('input',event=>{if(pendingMusic.has(event.target.id))musicDirty=true;updateStatus();});
  document.addEventListener('change',event=>{if(pendingMusic.has(event.target.id))musicDirty=true;updateStatus();});
  document.addEventListener('studio:saved',event=>{if(event.detail?.url==='/api/music' && event.detail?.body?.source)musicDirty=false;updateStatus();});
  window.addEventListener('beforeunload',event=>{if(dirtyPages().length){event.preventDefault();event.returnValue='';}});
  new MutationObserver(updateStatus).observe(document.getElementById('programStatus'),{childList:true,characterData:true,subtree:true});
  document.addEventListener('click',()=>setTimeout(updateStatus,400));
  show(location.pathname.split('/')[2]||'live');
  window.addEventListener('DOMContentLoaded',updateStatus);
})();
