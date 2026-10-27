'use strict';
let loadedSettings=false;
const el=id=>document.getElementById(id);
const date=value=>new Date(typeof value==='number'?value*1000:value).toLocaleString('en-CA',{timeZone:'America/St_Johns',dateStyle:'medium',timeStyle:'short'});
function node(tag,text,className){const n=document.createElement(tag);n.textContent=text;if(className)n.className=className;return n;}
async function refresh(){
 try{
  const r=await fetch('/api/alerts',{cache:'no-store'});if(!r.ok)throw Error('Receiver status unavailable');const d=await r.json();
  const p=d.presentation||{};if(p.config&&!loadedSettings){el('repeatMinutes').value=p.config.repeat_minutes;el('pageSeconds').value=p.config.page_seconds;el('audioEnabled').checked=p.config.audio_enabled;el('audioVolume').value=p.config.audio_volume*100;loadedSettings=true;}
  el('presentationState').textContent=(p.state||'Idle')+(p.countdown!=null?' / next full message in '+p.countdown+' seconds':'')+(p.audio?.error?' / '+p.audio.error:'');
  el('health').textContent=d.fresh?'Receiving NAADS heartbeats':'Feed not confirmed current';
  el('health').className=d.fresh?'':'warning';
  el('feedInfo').textContent='Newfoundland time · '+d.alerts.length+' active weather messages received · '+d.immediate.length+' immediate alerts';
  el('recovery').textContent=d.verification_error?'Verification: '+d.verification_error:d.archive_pending?'Checking '+d.archive_pending+' messages from the 48-hour archive':d.archive_error?'Archive recovery: '+d.archive_error:d.recovery_error?'Recovery: '+d.recovery_error:d.pending_recovery?'Recovering '+d.pending_recovery+' referenced messages':'';
  el('empty').textContent=(d.alerts.length+d.immediate.length)?'':d.fresh?'No active non-immediate weather alerts in the received data.':'Awaiting current feed data. This is not an all-clear.';
  el('cards').replaceChildren(...[...d.immediate,...d.alerts].map(a=>{
   const card=node('article','');card.append(node('span',a.broadcast_immediate?'EMERGENCY INFORMATION':a.severity||'Weather','chip'),node('span',a.display_event||a.event,'chip'),node('h2',a.display_headline||a.headline||a.event));
   card.append(node('p',a.areas.join(' · '),'meta'),node('p',(a.sender_name||a.sender)+' · Issued '+date(a.sent)+' · Expires '+date(a.expires),'meta'));
   if(a.description)card.append(node('p',a.description,'text'));
   if(a.instruction)card.append(node('h3','Instructions'),node('p',a.instruction,'text'));
   return card;
  }));
  el('details').textContent=Object.entries(d.feeds).map(([host,s])=>host+'\n'+(s.connected?'Connected':'Disconnected')+' · heartbeat '+(s.heartbeat_at?date(s.heartbeat_at):'not received')+(s.error?' · '+s.error:'')).join('\n\n')+'\n\nRecovered from heartbeat references: '+d.recovered+'\nDSS-verified this session: '+d.verified_messages+'\nVerification failures: '+d.verification_failures;
 }catch(e){el('health').textContent='Receiver connection unavailable';el('health').className='warning';el('cards').replaceChildren();el('empty').textContent='Current alerts cannot be verified. This is not an all-clear.';el('recovery').textContent=e.message;}
}
refresh();setInterval(refresh,10000);

el('presentationForm').onsubmit=async event=>{event.preventDefault();try{const r=await fetch('/api/alert-presentation',{method:'PUT',headers:{'Content-Type':'application/json','X-Skycam-Edit':'1'},body:JSON.stringify({repeat_minutes:Number(el('repeatMinutes').value),page_seconds:Number(el('pageSeconds').value),audio_enabled:el('audioEnabled').checked,audio_volume:Number(el('audioVolume').value)/100})});if(!r.ok)throw Error(JSON.stringify((await r.json()).detail));el('presentationState').textContent='Settings saved'}catch(e){el('presentationState').textContent=e.message}};
