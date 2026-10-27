'use strict';
let savingTheme=false,requestedTheme=null;
function showMapTheme(data){
 const format=value=>new Date(value).toLocaleTimeString('en-CA',{timeZone:data.timezone,hour:'numeric',minute:'2-digit'});
 $('mapTheme').value=data.mode;$('mapShowInfo').checked=data.show_info!==false;
 $('mapThemeStatus').textContent=(data.effective==='night'?'Night':'Day')+' map'+(data.mode==='auto'?' · automatic':' · manual')+' · sunrise '+format(data.sunrise)+' · sunset '+format(data.sunset)+' '+data.timezone;
}
async function refreshMapTheme(){
 try{const data=await deskRequest('/api/map/theme');if(!savingTheme&&document.activeElement!==$('mapTheme'))showMapTheme(data)}
 catch(e){if(!savingTheme)$('mapThemeStatus').textContent='Map theme unavailable: '+e.message}
 setTimeout(refreshMapTheme,3000);
}
$('mapTheme').onchange=$('mapShowInfo').onchange=async()=>{
 requestedTheme={mode:$('mapTheme').value,show_info:$('mapShowInfo').checked};if(savingTheme)return;savingTheme=true;
 try{
  while(requestedTheme){const settings=requestedTheme;requestedTheme=null;$('mapThemeStatus').textContent='Applying map theme';const data=await deskRequest('/api/map/theme','PUT',settings);if(!requestedTheme)showMapTheme(data)}
 }catch(e){requestedTheme=null;$('mapThemeStatus').textContent='Could not save map theme: '+e.message}
 finally{savingTheme=false}
};
refreshMapTheme();
