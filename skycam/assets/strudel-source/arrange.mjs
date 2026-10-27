// Original SkyCam arrangements, AGPL-3.0-or-later, 19 October 2026.
// Strudel performs cycle arrangement and event scheduling only. No live audio.
console.log=(...args)=>console.error(...args);
const {pure, stack, sequence}=await import('@strudel/core');
const seed=Number(process.argv[2]), song=Number(process.argv[3]);
if(!Number.isInteger(seed)||seed<0||seed>2147483647||!Number.isInteger(song)||song<0)throw Error('Invalid seed/song');
let state=(seed ^ Math.imul(song+1,2654435761))>>>0;
const rand=()=>{state=(Math.imul(state,1664525)+1013904223)>>>0;return state/4294967296};
const keys=[0,5,2,7,3,8,10], scale=[0,2,4,5,7,9,11];
const progressions=[[5,3,0,4],[1,4,0,5],[0,5,1,4],[3,2,5,1],[5,1,3,4],[3,0,1,4]];
const key=keys[(seed+song*3)%7], palette=song%3;
const pitch=d=>60+key+scale[((d%7)+7)%7]+12*Math.floor(d/7);
const progression=progressions[(Math.floor(seed/7)+song)%6];
const bridge=progressions[(Math.floor(seed/7)+song+3)%6];
const swing=.57+rand()*.045;
const motif=Array.from({length:16},(_,i)=>[0,2,4,6,5,4,2,1,0,2,3,5,4,2,1,-1][(i+song)%16]);
let previous=[55,60,64,67,71];
const bars=[];
for(let bar=0;bar<64;bar++){
 const section=Math.floor(bar/8), soft=[0,6,7].includes(section);
 const progressionHere=[3,5].includes(section)?bridge:progression;
 const degree=progressionHere[Math.floor(bar/2)%4];
 const notes=[0,2,4,6,8].map(d=>pitch(degree+d));
 const voicings=notes.map((_,inv)=>{
  let v=[...notes.slice(inv),...notes.slice(0,inv).map(n=>n+12)].sort((a,b)=>a-b);
  while(v.reduce((a,b)=>a+b,0)/v.length>64)v=v.map(n=>n-12);
  return v;
 });
 const chord=voicings.sort((a,b)=>a.reduce((s,n,i)=>s+Math.abs(n-previous[i]),0)-b.reduce((s,n,i)=>s+Math.abs(n-previous[i]),0))[0];previous=chord;
 const events=[];
 const add=(pos,kind,note,gain,pan=0,duration=3)=>events.push(pure({kind,note,gain,pan,duration}).compress(pos/4,Math.min(.9999,(pos+.025)/4)));
 const keysKind=['dustkeys','tapepiano','softorgan'][palette];
 // Broken ninth chords, anticipations and late accents vary by phrase.
 const hits=bar%4===3?[.04,1.60,3.48]:bar%2?[.08,2+swing]:[.06,2.15];
 for(const pos of hits)chord.forEach((n,i)=>add(pos+i*.012,keysKind,n,(soft?.035:.047)*(.85+rand()*.24),(i-2)*.15,3.8));
 if(bar%2===0)for(const i of [0,2,3])add(.01,'warmbed',chord[i],.009,(i-1)*.15,8);
 let root=pitch(degree)-24;while(root>45)root-=12;
 for(const [pos,interval,duration] of [[.025,0,1.3],[1+swing,7,.45],[2.08,0,1.0],[3+swing,bar%4===3?-1:12,.28]]){
  if(soft&&interval===12)continue;
  add(pos,'roundbass',root+interval,.15,0,duration*60/74);
 }
 // Motif and answer have room to breathe; accompaniment never disappears.
 if((section!==0||bar>=4)&&section!==6&&bar%4!==3){
  const rhythm=palette===1?[.22,1+swing,2.36]:[.18,1.2,2+swing,3.2];
  rhythm.forEach((pos,j)=>{
   if((bar+j)%7===0)return;
   let degreeNote=motif[(bar%4*4+j)%16];
   if([2,5].includes(section))degreeNote=6-degreeNote;
   if(j===0)degreeNote=degree+[0,2,4][bar%3];
   let n=pitch(degreeNote);while(n>76)n-=12;while(n<58)n+=12;
   const gain=(soft?.023:.035)*(.85+rand()*.25);
   add(pos,keysKind,n,gain,-.15,2.8);
   if(pos+.52<3.9)add(pos+.52,keysKind,n,gain*.17,.35,2.8);
  });
 }
 const kicks=[[0,1+swing,2.5],[0,2,3+swing],[0,.75,2+swing]][(Math.floor(bar/2)+song)%3];
 kicks.forEach(p=>add(p,'drum',0,soft?.16:.23,0,1));
 [1.035,3.035].forEach(p=>add(p,'drum',1,soft?.085:.125,.08,1));
 for(let e=0;e<8;e++){
  if(soft&&e%2)continue;
  add(Math.floor(e/2)+(e%2?swing:0)+rand()*.009,'drum',3,(e%2?.019:.027)*(.85+rand()*.25),-.2,1);
 }
 if(bar%4===2)add(3+swing,'drum',4,.022,.22,1);
 if(bar%8===7)[2+swing,3.78].forEach(p=>add(p,'drum',5,.025,.18,1));
 bars.push(stack(...events));
}
const pattern=sequence(...bars).slow(64);
const events=pattern.queryArc(0,64).filter(h=>h.hasOnset()).map(h=>({beat:Number(h.whole.begin)*4,...h.value})).sort((a,b)=>a.beat-b.beat);
process.stdout.write(JSON.stringify({version:1,key,palette,swing,events}));

