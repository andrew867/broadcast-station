(()=>{
 const panel=document.createElement('section');panel.className='panel';
 const title=document.createElement('h2');title.textContent='Program and prepared stills';
 const note=document.createElement('p');note.className='hint';note.textContent='Still previews. Prepared scene excludes the ticker and alert bar.';
 const status=document.createElement('p');status.setAttribute('role','status');
 const cadence=document.createElement('select');cadence.setAttribute('aria-label','Native still refresh interval');
 for(const [value,label] of [['0','Manual only'],['15','Every 15 seconds'],['30','Every 30 seconds'],['60','Every minute']])cadence.add(new Option(label,value));
 const target=document.createElement('select');target.setAttribute('aria-label','Native still refresh target');
 for(const [value,label] of [['program','Program'],['preview','Prepared scene'],['both','Alternate program and prepared scene']])target.add(new Option(label,value));
 const controls=document.createElement('label');controls.textContent='Automatic still refresh ';controls.append(cadence,target);
 const grid=document.createElement('div');grid.className='grid';
 let busy=false,timer=null,nextKind='program',lastAttempt=0;
 const views={};
 function schedule(){clearTimeout(timer);if(cadence.value!=='0'&&!document.hidden)timer=setTimeout(async()=>{const kind=target.value==='both'?nextKind:target.value;nextKind=kind==='program'?'preview':'program';await capture(kind);schedule()},Number(cadence.value)*1000)}
 async function capture(kind){
  if(busy)return;
  if(Date.now()-lastAttempt<10000){status.textContent='Wait ten seconds between native snapshots.';return}
  busy=true;lastAttempt=Date.now();for(const view of Object.values(views))view.button.disabled=true;
  status.textContent='Capturing a native still...';
  try{
   const response=await fetch('/api/confidence/rendered/'+kind,{method:'POST',headers:{'X-Skycam-Edit':'1'},signal:AbortSignal.timeout(7000)});
   const data=await response.json();if(!response.ok)throw Error(data.detail||'Snapshot unavailable');
   const view=views[kind];view.image.src=data.url;view.image.hidden=false;view.at=data.at;view.scene=data.scene;updateAges();
   status.textContent=cadence.value==='0'?'Still captured. Manual refresh selected.':'Still captured. Automatic refresh enabled.';
  }catch(error){status.textContent=error.message+' Existing pictures are older stills.'}
  finally{busy=false;for(const view of Object.values(views))view.button.disabled=false}
 }
 function updateAges(){for(const view of Object.values(views))if(view.at){const age=Math.max(0,Math.round(Date.now()/1000-view.at));view.caption.textContent=view.scene+' / still captured '+age+' seconds ago';view.caption.classList.toggle('staleBadge',age>60)}}
 for(const kind of ['program','preview']){
  const box=document.createElement('div');box.className='slide';
  const button=document.createElement('button');button.textContent=kind==='program'?'Capture program still':'Capture prepared scene';
  const image=document.createElement('img');image.hidden=true;image.alt=kind+' native composited still';
  const caption=document.createElement('p');caption.className='stamp';
  views[kind]={button,image,caption,at:null};button.onclick=async()=>{await capture(kind);schedule()};
  box.append(button,image,caption);grid.append(box);
 }
 cadence.onchange=target.onchange=schedule;document.addEventListener('visibilitychange',schedule);
 setInterval(updateAges,1000);
 panel.append(title,note,controls,status,grid);document.querySelector('main').insertBefore(panel,document.getElementById('sources'));
})();
