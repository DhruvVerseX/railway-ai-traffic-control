'use client';
import {useState} from 'react';
import {delayColor} from '../station-state';
import {renderStation} from './control-adapter';
import {comparisonStats,policies,type Policy,type Snapshot} from './control-data';
import {useControl} from './control-store';

export default function CompareView() {
  const store=useControl(),pair=store.comparison;
  const [left,setLeft]=useState<Policy>('fifo'),[right,setRight]=useState<Policy>('ml');
  const draw=(snapshot:Snapshot,label:string)=>{
    const scene=renderStation(snapshot,store.disruptions),history=pair?.records.map(f=>label==='A'?f.left:f.right)??[];
    const stats=comparisonStats(history);
    return <article className="compare-run"><header><div><span className="control-kicker">RUN {label} · PYTHON OUTPUT</span><h3>{policies[snapshot.policy]}</h3></div><span>{snapshot.time.toFixed(1)} min{snapshot.policy==='ml'&&<span className="control-ml">ML</span>}</span></header>
      <svg viewBox="0 0 600 250" role="group" aria-label={`Run ${label} station schematic`}><defs><pattern id={`compare-hatch-${label}`} width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="#fae9cb"/><path d="M0 10L10 0" stroke="#9b6336" strokeWidth="3"/></pattern></defs>
        {scene.platforms.map((p,i)=>{const y=45+i*52,train=scene.trains.find(t=>t.id===p.train_id),failed=scene.mock?.failedPlatforms.includes(p.platform),blocked=!!p.section&&scene.mock?.blockedSections.includes(p.section);return <g key={p.platform}><path d={`M25 ${y}H570`} stroke={blocked?`url(#compare-hatch-${label})`:'#c6d0bb'} strokeWidth={blocked?15:8}/><text x="25" y={y-17} fontSize="17">P{p.platform} · {train?.name??'Empty'}</text><circle cx="545" cy={y-15} r="7" fill={failed||p.aspect==='RED'?'#bd6650':'#4e8b69'}/>{failed&&<path className="mock-cross" d={`M533 ${y-27}L557 ${y-3}M557 ${y-27}L533 ${y-3}`}/>}{train&&(!train.departing||train.sectionProgress<.34)&&<g role="button" tabIndex={0} aria-label={`Focus ${train.name} in run ${label}`} transform={`translate(${155+(train.departing?train.sectionProgress*1000:0)},${y})`} onClick={()=>store.focusTrain(train.id)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();store.focusTrain(train.id);}}}><rect x="0" y="-9" width="93" height="18" rx="4" fill={delayColor(train.delay)}/>{train.mockWarning&&<text x="105" y="7" fontSize="24">⚠</text>}{store.selected===train.id&&<rect x="-5" y="-14" width="103" height="28" fill="none" stroke="#36654d" strokeWidth="2"/>}</g>}</g>;})}
      </svg><div className="compare-tradeoffs"><span title="Distinct returned recommendations, deduplicated across recorded responses.">HOLD recommendations <b>{stats.holds}</b></span><span>Safety overrides <b>{stats.overrides}</b></span><span>Rejected at execution <b>{stats.rejected}</b></span><span>Unfinished journeys <b>{stats.unfinished}</b></span><span>Deadlocks <b>Not reported</b></span></div>
      {stats.stalled&&<p className="compare-stall">No recorded section movement for ≥10 min. Possible stall; the backend does not confirm deadlock.</p>}
    </article>;
  };
  return <div className="compare-view"><div className="control-view-heading"><div><span className="control-kicker">PAIRED EXPERIMENT / SEED 42</span><h2>Two controllers. Same queue.</h2></div><span>12 trains · same station · synced 1 min steps</span></div>
    <div className="compare-setup"><label>Controller A<select value={left} disabled={store.busy||store.playing||store.replaying} onChange={e=>setLeft(e.target.value as Policy)}>{Object.entries(policies).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label><label>Controller B<select value={right} disabled={store.busy||store.playing||store.replaying} onChange={e=>setRight(e.target.value as Policy)}>{Object.entries(policies).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label><button className="primary" disabled={!store.network||store.busy||store.playing||store.replaying} onClick={()=>void store.command('compare',{policies:[left,right]})}>{store.busy?'Loading paired runs…':pair?'Restart paired runs':'Load paired runs'}</button></div>
    <p className="compare-honesty">Real backend runs via two seeded /scenario sessions. {pair?.verified?'Initial train, readiness, occupancy and platform states matched.':'Initial states are verified before playback.'} Visual mock disruptions do not affect this comparison’s decisions or KPIs.</p>
    {pair?.error&&<p className="control-error" role="alert">Run failure: {pair.error} Restart both runs; no delta is reported for misaligned clocks.</p>}
    {pair?<div className="compare-columns">{draw(pair.left,'A')}{draw(pair.right,'B')}</div>:<div className="control-empty">Choose two available controllers and load the same seeded initial conditions. No outcomes are fabricated.</div>}
    <p className="control-footnote">Simulation output from a research prototype. No real-world performance claims. Outcomes include waiting, blocked moves and unfinished journeys; no single efficiency score is used.</p>
  </div>;
}
