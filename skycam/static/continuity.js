(() => {
  const panel=document.createElement('section');panel.className='panel';
  panel.innerHTML='<h2>Continuity report, last 24 hours</h2><p class="hint">Minute averages, retained for 24 hours. Blank periods have no readings.</p><p class="continuity-summary" role="status">Collecting history</p><p class="continuity-error warn"></p><table><thead><tr><th>Scene</th><th>Observed average fps</th><th>Samples</th></tr></thead><tbody></tbody></table><p><a href="/api/performance/history" download="skycam-continuity.json">Download saved continuity report</a></p>';
  document.querySelector('main').append(panel);
  async function refresh(){
    if(!document.hidden){try{
      const r=await fetch('/api/performance/history',{signal:AbortSignal.timeout(4000)});if(!r.ok)throw Error();const d=await r.json(),s=d.summary;
      panel.querySelector('.continuity-summary').textContent=`${s.minutes_observed} observed minutes, ${s.average_fps??'unknown'} fps average. ${s.fallback_cuts} fallback cuts in ${s.transitions} observed transitions. ${s.missing_samples} missing samples.`;
      panel.querySelector('.continuity-error').textContent=d.error||'';
      const body=panel.querySelector('tbody');body.replaceChildren();
      for(const[name,row]of Object.entries(s.scenes).sort((a,b)=>a[1].average_fps-b[1].average_fps)){
        const tr=document.createElement('tr');for(const value of[name,row.average_fps.toFixed(2),row.samples]){const td=document.createElement('td');td.textContent=value;tr.append(td)}body.append(tr);
      }
    }catch{panel.querySelector('.continuity-summary').textContent='Saved history unavailable. No continuity claim is being made.'}}
    setTimeout(refresh,30000);
  }
  refresh();
})();
