'use client';
import {animate,createScope} from 'animejs';
import {useEffect,useRef} from 'react';
import YardTrain from './yard-train';
import {delayColor,type StationState} from './station-state';
export default function Yard({state,station,exits,selected,onSelect,onCommand,disabled,playing,speed,aiWarnings=[],replay=false}:{state:StationState|null;station:string;exits:{destination:string;section:string}[];selected:string|null;onSelect:(id:string)=>void;onCommand:(path:string,body:object)=>void;disabled:boolean;playing:boolean;speed:number;aiWarnings?:string[];replay?:boolean}){
 const scene=useRef<HTMLDivElement>(null);
 const lockedRoutes=state?.platforms.filter(p=>p.locked).map(p=>p.platform).join(',')||'';
 useEffect(()=>{
  const scope=createScope({root:scene,mediaQueries:{reduceMotion:'(prefers-reduced-motion: reduce)'}}).add(self=>{
   if(self&&!self.matches.reduceMotion&&playing) animate('.yard-route-active',{strokeDashoffset:[24,0],duration:1200/speed,ease:'linear',loop:true});
  });
  return()=>scope.revert();
 },[lockedRoutes,playing,speed]);
 const platforms=state?.platforms.length?state.platforms:Array.from({length:4},(_,i)=>({platform:i+1,train_id:null,aspect:'RED',held:false,locked:false,section:null,destination:null,reason:'Load trains to begin.'}));
 const trains=state?.trains??[];
 const label=(id:string)=>{const t=trains.find(t=>t.id===id);return t?`${t.name} · ${t.id}`:id};
 const destinations=exits.map(e=>e.destination);
 const exitY=(index:number)=>destinations.length<=1?250:170+Math.max(0,index)*240/(destinations.length-1);
 const lastDeparture=[...(state?.events??[])].reverse().find(e=>e.event==='SECTION_ENTERED'&&platforms.some(p=>p.locked&&p.train_id===e.train_id&&p.section===e.section_id));
 const lockedExit=platforms.find(p=>p.locked&&p.train_id===lastDeparture?.train_id);
 const chosen=selected?platforms.find(p=>p.train_id===selected):undefined;
 const train=trains.find(t=>t.id===selected);
 return <div ref={scene} className="station-yard">
  <div className="yard-title"><b>Station tracks</b><span><i className="green-light"/> Clear <i className="red-light"/> Stop <i className="route-light"/> Locked route</span></div>
  <div className="yard-scroll"><svg viewBox="0 0 1100 490" role="group" aria-label="Four station platform tracks with departure signals and switch routes">
   <defs><pattern id="yard-block-hatch" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="#f8e7ca"/><path d="M-2 2L2 -2M0 10L10 0M8 12L12 8" stroke="#a36c40" strokeWidth="3"/></pattern><pattern id="yard-grass" width="35" height="35" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="#dce3cf"/></pattern><filter id="train-shadow"><feDropShadow dx="0" dy="3" stdDeviation="3" floodOpacity=".15"/></filter></defs>
   <rect width="1100" height="490" fill="#eff2e4"/><rect width="1100" height="490" fill="url(#yard-grass)"/>
   <rect x="270" y="25" width="350" height="42" rx="7" fill="#e5dcc1"/><path d="M250 25L445 5L640 25" fill="#9aa986"/><text x="445" y="53" textAnchor="middle" fill="#5d6d4e" fontSize="16" fontWeight="600">{station} · Station building</text>
   {platforms.map(p=>{
    const y=125+(p.platform-1)*85,path=`M650 ${y} C740 ${y},760 250,830 250`;
    const failed=state?.mock?.failedPlatforms.includes(p.platform);
    const aspect=failed?'RED':state?.signals.find(s=>s.platform===p.platform)?.aspect??'RED';
    return <g key={p.platform}>
     <rect x="265" y={y+15} width="355" height="29" rx="4" fill="#dad4bd"/><rect x="265" y={y+15} width="355" height="4" fill="#e2c88e"/>
     <text x="285" y={y+36} fill="#526044" fontSize="14">Platform {p.platform}</text>
     <path d={`M50 ${y}H650`} fill="none" stroke="#bfc5ae" strokeWidth="13"/><path d={`M50 ${y}H650`} fill="none" stroke="#7f907a" strokeWidth="11" strokeDasharray="2 8"/><path d={`M50 ${y}H650`} fill="none" stroke="#ebeee0" strokeWidth="4"/>
     <path className="yard-route" d={path} fill="none" stroke={p.locked?'#599272':'#bdc6b0'} strokeWidth={p.locked?10:7}/><path d={path} fill="none" stroke="#f2f5e9" strokeWidth="2"/>
     {p.locked&&<path className="yard-route-active" d={path} fill="none" stroke="#a9d4a1" strokeWidth="3" strokeDasharray="6 18"/>}
     <circle cx="650" cy={y} r="7" fill={p.locked?'#4d8b67':'#f6f7ed'} stroke="#829a70" strokeWidth="2"/>
     <g transform={`translate(650,${y})`}><path className="yard-switch" d="M-17 0H22" stroke="#365f46" strokeWidth="4" style={{transform:`rotate(${p.locked?Math.sign(250-y)*28:0}deg)`}}/></g>
     <text x="665" y={y+27} fontSize="14" fill="#526044">{p.locked?'Locked':'Switch'}</text>
     <g className={"yard-signal "+(failed?"mock-signal-failed":"")} transform={`translate(615,${y-55})`} aria-label={`Platform ${p.platform}: ${aspect}`}><rect x="7" y="28" width="4" height="30" fill="#819075"/><rect width="22" height="35" rx="6" fill="#596850"/>
      <circle className={'yard-aspect '+(aspect==='RED'?'lit-red':'')} cx="11" cy="10" r="6" fill={aspect==='RED'?'#d97866':'#394839'}/>
      <circle className={'yard-aspect '+(aspect==='GREEN'?'lit-green':'')} cx="11" cy="25" r="6" fill={aspect==='GREEN'?'#84bd78':'#394839'}/>{failed&&<g><title>CLIENT MOCK · signal failure</title><path className="mock-cross" d="M-4 -5L27 39M27 -5L-4 39"/></g>}
     </g>
     <text className="yard-train-label" x="82" y={y-23} fontSize="14" fill="#526044">{p.train_id?label(p.train_id):'Empty'}</text>
    </g>;
   })}
   {exits.map((e,i)=><g key={e.section}><path className="yard-exit-route" d={`M830 250 C900 250,900 ${exitY(i)},1050 ${exitY(i)}`} fill="none" stroke={platforms.some(p=>p.locked&&p.section===e.section)?'#599272':'#bdc6b0'} strokeWidth="7"/><path d={`M830 250 C900 250,900 ${exitY(i)},1050 ${exitY(i)}`} fill="none" stroke="#f2f5e9" strokeWidth="2"/>{state?.mock?.blockedSections.includes(e.section)&&<path className="mock-track-block" d={`M830 250 C900 250,900 ${exitY(i)},1050 ${exitY(i)}`} fill="none" stroke="url(#yard-block-hatch)" strokeWidth="18"><title>CLIENT MOCK · blocked {e.section}</title></path>}<text x="1060" y={exitY(i)-22} textAnchor="end" fill="#526044" fontSize="14">To {e.destination} · {e.section}</text></g>)}
   <g transform="translate(830,250)"><title>{lockedExit?`Exit switch aligned to ${lockedExit.destination}`:'Exit switch idle'}</title><circle r="8" fill="#f6f7ed" stroke="#829a70" strokeWidth="2"/><path className="yard-switch" d="M-15 0H27" stroke="#365f46" strokeWidth="4" style={{transform:`rotate(${lockedExit?Math.atan2(exitY(destinations.indexOf(lockedExit.destination||''))-250,100)*180/Math.PI:0}deg)`}}/></g>
   {trains.filter(t=>t.platform!==null).map(t=><YardTrain key={t.id} id={t.id} name={t.name} departing={t.departing} platform={t.platform!} exitY={exitY(destinations.indexOf(t.destination||''))} color={delayColor(t.delay)} type={t.type} aiWarning={aiWarnings.includes(t.id)} mockWarning={t.mockWarning} staticProgress={replay||t.mockWarning?(t.status==='RUNNING'?t.sectionProgress:0):undefined} selected={selected===t.id} onSelect={onSelect} playing={playing} speed={speed}/>)}
  </svg></div>
  <div className="yard-delay-legend" aria-label="Train delay colours"><span><i style={{background:delayColor(0)}}/> On time</span><span><i style={{background:delayColor(1)}}/> Slightly late · up to 5 min</span><span><i style={{background:delayColor(6)}}/> Late · over 5 min</span></div>
  <div className="yard-controls"><div className="yard-signal-controls">{platforms.map(p=><button key={p.platform} disabled={disabled||p.locked||!state} className={p.held?'signal-held':''} title={p.reason} onClick={()=>onCommand('signal',{platform:p.platform,stop:!p.held})}><i className={p.aspect==='GREEN'?'green-light':'red-light'}/> P{p.platform} · {p.locked?'Locked':p.held?'Release red hold':'Hold at red'}</button>)}</div><div className="yard-platform-control"><label htmlFor="yard-train">Selected train</label><select id="yard-train" value={selected??''} disabled={!trains.length} onChange={e=>onSelect(e.target.value)}><option value="" disabled>Select a train</option>{trains.map(t=><option key={t.id} value={t.id}>{label(t.id)}</option>)}</select><label htmlFor="yard-platform">Platform assignment</label><select id="yard-platform" value={chosen?.platform||''} disabled={disabled||!train||train.status==='RUNNING'||train.status==='ARRIVED'} onChange={e=>onCommand('platform',{train_id:selected,platform:Number(e.target.value)})}><option value="" disabled>Assign platform</option>{platforms.map(p=><option key={p.platform} value={p.platform} disabled={!!p.train_id&&p.train_id!==selected}>Platform {p.platform}{p.train_id&&p.train_id!==selected?' · occupied':''}</option>)}</select></div></div>
  {chosen&&<p className="yard-reason" role="status">P{chosen.platform} · {chosen.reason}</p>}
  {trains.some(t=>t.outside)&&<div className="yard-queue"><span>Outside station · {trains.filter(t=>t.outside).length} trains</span>{trains.filter(t=>t.outside).map(t=><button key={t.id} data-train-id={t.id} className={selected===t.id?'selected':''} aria-pressed={selected===t.id} onClick={()=>onSelect(t.id)}><i style={{background:delayColor(t.delay)}}/>{t.mockWarning&&<span className="mock-queue-warning" title={"CLIENT MOCK · "+t.mockWarning}>⚠</span>}{t.name} <small>{t.id}</small></button>)}</div>}
 </div>;
}
