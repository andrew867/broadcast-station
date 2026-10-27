(() => {
  const panel=document.createElement('section');panel.className='panel';
  panel.innerHTML='<h2>Performance over the last hour</h2><p class="hint">Output cadence, sampled every 5 seconds. <a href="/guide#monitoring">Measurement details</a>.</p><p id="perfSummary" role="status">Collecting observations</p><svg id="perfChart" viewBox="0 0 1000 150" width="100%" height="150" role="img" aria-label="Measured output cadence over time"></svg><p id="perfDetails" class="hint"></p><a href="/api/performance" download="skycam-performance.json">Download observations</a>';
  document.querySelector('main').insertBefore(panel,document.getElementById('sources'));
  const svg=panel.querySelector('svg'),summary=panel.querySelector('#perfSummary'),details=panel.querySelector('#perfDetails');
  function element(name,attrs){const n=document.createElementNS('http://www.w3.org/2000/svg',name);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);return n}
  async function refresh(){try{
    const r=await fetch('/api/performance',{signal:AbortSignal.timeout(4000)});if(!r.ok)throw Error();const d=await r.json(),s=d.summary,rows=d.samples;
    const n=v=>v==null?'Unavailable':v.toFixed(1);
    summary.textContent=`Output counter: ${n(s.average_fps)} fps average, ${n(s.minimum_fps)} to ${n(s.maximum_fps)}. ${s.fallback_cuts} fallback cuts in ${s.transitions} observed transitions. ${s.stale_samples} missing observations.`;
    svg.replaceChildren();for(const rate of[0,30,60]){const y=140-rate*2;svg.append(element('line',{x1:35,y1:y,x2:1000,y2:y,stroke:'#344d5d'}));const t=element('text',{x:0,y:y+4,fill:'#abc1ce','font-size':12});t.textContent=rate;svg.append(t)}
    if(rows.length>1){const first=rows[0].at,span=Math.max(1,rows.at(-1).at-first);let path='';for(let i=0;i<rows.length;i++){const row=rows[i];if(row.fps==null){path+=' ';continue}const previous=rows[i-1],move=!previous||previous.fps==null||row.at-previous.at>8;path+=(move?'M':'L')+(35+965*(row.at-first)/span).toFixed(1)+','+(140-Math.min(65,row.fps)*2).toFixed(1)+' ';}svg.append(element('path',{d:path,fill:'none',stroke:'#77e2bb','stroke-width':2}));}
    const last=rows.at(-1),memory=last?.memory,age=last?Math.max(0,Date.now()/1000-last.at):null;
    const link=last?.network,linkFresh=link&&Date.now()/1000-link.at<25;
    details.textContent=(linkFresh?`MediaMTX round trip: ${link.rtt_ms==null?'unavailable':link.rtt_ms.toFixed(1)+' ms'}. Host traffic: ${link.host_rx_mbps??'?'} Mb/s in, ${link.host_tx_mbps??'?'} Mb/s out. `:'Link measurements unavailable. ')+(last?`Latest sample ${age.toFixed(0)}s ago. Scene: ${last.scene||'unknown'}. `:'')+(memory?`Host memory available: ${(memory.available_bytes/1073741824).toFixed(1)} GiB. `:'')+'Download includes reported camera packet loss, native decoded queue age/skips, source delivery age and graphics-cache observations.';
  }catch{summary.textContent='Performance telemetry unavailable. No fresh measurements are being claimed.'}setTimeout(refresh,5000)}
  refresh();
})();
