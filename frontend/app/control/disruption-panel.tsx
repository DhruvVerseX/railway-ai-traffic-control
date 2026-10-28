'use client';
import {useEffect,useRef,useState} from 'react';
import {motion,useReducedMotion} from 'framer-motion';
import {disruptionNames,type DisruptionKind} from './control-data';
import {useControl} from './control-store';
export default function DisruptionPanel({onClose}:{onClose:()=>void}) {
  const store=useControl(),dialog=useRef<HTMLDialogElement>(null),reduce=useReducedMotion();
  const [kind,setKind]=useState<DisruptionKind>('track-block'),[sectionId,setSection]=useState(store.sectionId),[platform,setPlatform]=useState(1),[trainId,setTrain]=useState(store.selected??store.snapshot?.trains[0]?.train_id??'');
  const eligible=store.snapshot?.trains.filter(t=>t.status!=='ARRIVED'&&(kind!=='departure-delay'||t.status!=='RUNNING'))??[];
  const effectiveTrain=eligible.some(t=>t.train_id===trainId)?trainId:eligible[0]?.train_id??'';
  useEffect(()=>{const target=dialog.current;target?.showModal();return()=>target?.close();},[]);
  return <dialog ref={dialog} className="disrupt-dialog" onCancel={onClose} aria-labelledby="disrupt-title"><motion.div initial={reduce?false:{opacity:0,y:12}} animate={{opacity:1,y:0}} transition={{duration:reduce?0:.18}}>
    <div className="disrupt-heading"><h2 id="disrupt-title">Disrupt the scene</h2><button aria-label="Close disruption injector" onClick={onClose}>×</button></div>
    <p className="mock-label">CLIENT-SIDE MOCK · needs backend support</p><p>Visual previews only. These conditions do not change Python decisions, physical movement, or backend KPIs.</p>
    <form onSubmit={e=>{e.preventDefault();if(store.inject(kind,{sectionId,platform,trainId:effectiveTrain}))onClose();}}>
      <label>Disruption<select value={kind} onChange={e=>setKind(e.target.value as DisruptionKind)}>{Object.entries(disruptionNames).filter(([key])=>key!=='fog').map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
      {kind==='track-block'&&<label>Track section<select value={sectionId} onChange={e=>setSection(e.target.value)}>{store.network?.sections.map(s=><option key={s.section_id} value={s.section_id}>{s.section_id} · {s.from_station} ↔ {s.to_station}</option>)}</select></label>}
      {kind==='signal-failure'&&<label>Departure signal<select value={platform} onChange={e=>setPlatform(Number(e.target.value))}>{store.snapshot?.yard?.platforms.map(p=><option key={p.platform} value={p.platform}>Platform {p.platform}</option>)}</select></label>}
      {(kind==='breakdown'||kind==='departure-delay')&&<label>Train<select value={effectiveTrain} onChange={e=>setTrain(e.target.value)}>{eligible.map(t=><option key={t.train_id} value={t.train_id}>{t.train_name} · {t.train_id}</option>)}</select></label>}
      {kind==='rush-hour'&&<p>Preview three additional arrivals in a clearly labelled mock queue. No trains are added to the Python simulation.</p>}
      {store.error&&<p role="alert">{store.error}</p>}
      <div className="disrupt-actions"><button type="button" onClick={onClose}>Cancel</button><button className="primary" type="submit" disabled={store.busy||store.replaying}>Add mock disruption</button></div>
    </form>
  </motion.div></dialog>;
}
