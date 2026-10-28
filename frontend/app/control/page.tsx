'use client';
import {useEffect,useRef,useState} from 'react';
import Link from 'next/link';
import {AnimatePresence,motion,useReducedMotion} from 'framer-motion';
import CompareView from './compare-view';
import ReplayBar from './replay-bar';
import DisruptionPanel from './disruption-panel';
import {ConditionEffects,ConditionStatus} from './condition-effects';
import {Activity,ArrowRight,GitBranch,Layers,Map,Pause,Play,RotateCcw,TrainFront} from 'lucide-react';
import Yard from '../yard';
import {trainLabel} from '../station-state';
import {policies,type Policy} from './control-data';
import {ControlProvider,useControl} from './control-store';
import SectionView from './section-view';
import NetworkView from './network-view';
import DecisionPanel from './decision-panel';
import KpiBar from './kpi-bar';
import './control.css';

function StationView() {
  const {snapshot,scene,network,selected,focusToken,focusTrain,command,busy,playing,speed,warnings,replaying}=useControl();
  const root=useRef<HTMLDivElement>(null);
  useEffect(()=>{
    if(selected)root.current?.querySelector(`[data-train-id="${CSS.escape(selected)}"]:not([aria-hidden="true"])`)?.scrollIntoView({block:'nearest',inline:'center',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
  },[selected,focusToken]);
  const station=snapshot?.station??'MTJ';
  return <div ref={root} className="control-station"><Yard state={scene} station={network?.stations.find(s=>s.station_code===station)?.station_name??station}
    exits={(network?.sections??[]).filter(s=>s.from_station===station||s.to_station===station).map(s=>({destination:s.from_station===station?s.to_station:s.from_station,section:s.section_id}))}
    selected={selected} onSelect={focusTrain} onCommand={(path,body)=>void command(path,body)} disabled={busy||playing||replaying} playing={playing&&!replaying} speed={speed} aiWarnings={warnings} replay={replaying}/></div>;
}
function ControlRoom() {
  const store=useControl();
  const [disruptOpen,setDisruptOpen]=useState(false),reduce=useReducedMotion();
  const {network,snapshot,station,policy,playing,speed,busy,error,view,layers,selected}=store;
  const chosen=snapshot?.trains.find(t=>t.train_id===selected);
  const views=[{id:'station',label:'Station',icon:TrainFront},{id:'section',label:'Section',icon:Activity},{id:'network',label:'Network',icon:Map},{id:'compare',label:'Compare',icon:GitBranch}] as const;
  const layerLabels={names:'Names & labels',trains:'Trains',signals:'Signals',occupancy:'Occupancy & routes'};
  return <main className="control-app">
    <header className="control-topbar"><div className="control-brand"><Link className="logo" href="/"><GitBranch size={23}/>railwise<span>.</span></Link><span>CONTROL ROOM</span><details className="control-help"><summary>Legend & shortcuts</summary><div><p>● Green: on time · amber: ≤5 min late · terracotta: &gt;5 min late.</p><p>× Flickering signal: mock failure · hatch: mock blocked track · ⚠: mock breakdown/delay · grey veil: mock fog.</p><p>AI-coloured ring: model RELEASE blocked by safety. No ML badges for FIFO or heuristic.</p><p>Space: play/pause · 1/2/3: Station/Section/Network · [ / ]: speed. Shortcuts pause while editing controls.</p></div></details><Link href="/" className="control-story-link">Story view <ArrowRight size={13}/></Link></div>
      <div className="control-toolbar">
        <label>Station<select aria-label="Control station" value={station} disabled={!network||busy||playing||store.replaying||view==='compare'} onChange={e=>void store.command('scenario',{station:e.target.value})}>{(network?.stations??[{station_code:'MTJ',station_name:'Mathura Junction'}]).map(s=><option key={s.station_code} value={s.station_code}>{s.station_name} · {s.station_code}</option>)}</select></label>
        <div className="control-scenario"><span>SEEDED STATION QUEUE</span><b>{snapshot?`${snapshot.trains.length} trains`:'12 trains'} · seed 42</b></div>
        <label>{view==='compare'?'Run A policy':'Dispatch mode'}<select aria-label="Control dispatch mode" value={policy} disabled={busy||playing||store.replaying||view==='compare'} onChange={e=>store.changePolicy(e.target.value as Policy)}>{Object.entries(policies).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
        <div className="control-playback"><button className="primary" disabled={!network||(busy&&!playing)} onClick={()=>snapshot?store.togglePlayback():void store.command('scenario')}>{playing?<Pause size={16}/>:<Play size={16}/>} {snapshot?playing?'Pause':'Play':'Load queue'}</button><button title="Advance one simulated minute using the selected controller" aria-label="Step one minute" disabled={!snapshot||busy||playing} onClick={store.step}><ArrowRight size={16}/>Step</button><button title="Reset the station queue with seed 42" aria-label="Reset control scenario" disabled={!snapshot||busy||playing} onClick={()=>void store.command('scenario')}><RotateCcw size={15}/></button></div>
        <label className="control-speed">Speed <b>{speed}×</b><input aria-label="Control playback speed" type="range" min="1" max="6" value={speed} onChange={e=>store.setSpeed(Number(e.target.value))}/></label>
        <button className="control-disrupt" disabled={!snapshot||busy||store.replaying} onClick={()=>setDisruptOpen(true)}>⚡ Disrupt</button><span className="control-clock" role="status" aria-live="polite"><i className={playing?'is-running':''}/>{busy?'Updating':store.replaying?'Replay':playing?'Running':snapshot?'Paused':'Ready'}<strong>{snapshot?.time.toFixed(1)??'0.0'} <small>sim min</small></strong></span>
      </div>
    </header>
    {!network&&!error&&<div className="control-connect-status" role="status">Connecting to the Python API…</div>}{error&&<div className="control-error" role="alert">{error}{(!network||/connect|unreachable|backend|ngrok|JSON|fetch/i.test(error))&&<button disabled={busy} onClick={()=>void store.connect()}>Retry connection</button>}</div>}
    <div className="control-workspace">
      <aside className="control-sidebar" aria-label="Views and layers"><span className="control-kicker">WORKSPACE</span><nav aria-label="Control room views">{views.map(({id,label,icon:Icon})=><button key={id} aria-pressed={view===id} className={view===id?'active':''} onClick={()=>{store.setHovered(null);store.setView(id);}}><Icon size={18}/>{label}</button>)}</nav>
        <div className="control-layers"><span className="control-kicker"><Layers size={13}/>LAYERS</span>{Object.entries(layerLabels).map(([key,label])=><label key={key}><input type="checkbox" checked={layers[key as keyof typeof layers]} onChange={e=>store.setLayers(previous=>({...previous,[key]:e.target.checked}))}/>{label}</label>)}</div>
        <div className="control-conditions"><span className="control-kicker">CONDITIONS · MOCK</span>{([{kind:'fog',label:'Fog · 40 km/h'},{kind:'signal-failure',label:'Signal failure'},{kind:'track-block',label:'Track block'}] as const).map(({kind,label})=><label key={kind}><input type="checkbox" checked={store.disruptions.some(d=>d.kind===kind)} disabled={!snapshot||busy||store.replaying} onChange={e=>store.condition(kind,e.target.checked)}/>{label}</label>)}<small>Visual previews; no physical effect in Python.</small></div><div className="control-sidebar-note"><span className="control-kicker">SOURCE</span><p>Python simulation<br/>Seeded project traffic<br/>No live connection</p></div>
      </aside>
      <section className="control-center" aria-label="Simulation canvas"><div className="control-canvas-toolbar"><span>{view==='station'?'STATION INTERLOCKING':view==='section'?'SECTION MOVEMENTS':view==='network'?'REGION TOPOLOGY':'PAIRED CONTROLLER RUNS'}</span><label>Observed section<select aria-label="Observed section" value={store.sectionId} onChange={e=>store.setSectionId(e.target.value)}>{network?.sections.map(s=><option value={s.section_id} key={s.section_id}>{s.section_id} · {s.from_station} ↔ {s.to_station}</option>)}</select></label></div>
        <ConditionStatus/><div className="control-canvas-surface"><div className={'control-stage '+Object.entries(layers).filter(([,enabled])=>!enabled).map(([key])=>'hide-'+key).join(' ')}>
          <AnimatePresence mode="wait" initial={false}><motion.div className="control-view-frame" key={view} initial={reduce?false:{opacity:0,y:6}} animate={{opacity:1,y:0}} exit={{opacity:0,y:-6}} transition={{duration:reduce?0:.16}}>{view==='station'?<StationView key={store.session||'preview'}/>:view==='section'?<SectionView/>:view==='network'?<NetworkView/>:<CompareView/>}</motion.div></AnimatePresence>
          {!snapshot&&view!=='compare'&&<div className="control-load-note"><TrainFront size={19}/><span>Load the seeded queue to inspect actual trains and controller decisions.</span></div>}
        </div><ConditionEffects/></div>
        <div className="control-selection"><span>{chosen?<><b>{trainLabel(chosen)}</b> · {chosen.status} · delay {chosen.delay_min.toFixed(1)} min</>:'Select a train on the canvas or in the decision feed.'}</span><button disabled={!snapshot||busy||playing||store.replaying||view==='compare'} onClick={()=>void store.command('decide')}>Analyze queue <ArrowRight size={14}/></button></div>
      </section>
      <DecisionPanel/>
    </div>
    <ReplayBar/><KpiBar/>{disruptOpen&&<DisruptionPanel onClose={()=>setDisruptOpen(false)}/>}
  </main>;
}
export default function ControlPage(){return <ControlProvider><ControlRoom/></ControlProvider>;}
