'use client';
import {mergeEvents,sectionThroughput,type Comparison} from './control-data';
import {useControl} from './control-store';

export default function KpiBar() {
  const {snapshot,events,sectionId,history,view,comparison}=useControl();
  if(view==='compare')return <ComparisonKpis pair={comparison} sectionId={sectionId}/>;
  const start=history[0]?.time??0,end=snapshot?.time??0;
  const sectionRate=snapshot?sectionThroughput(events,sectionId,start,end):null;
  const window=`Observation window: ${start.toFixed(2)}–${end.toFixed(2)} simulated minutes, since this queue was loaded.`;
  const metrics=[
    {label:'Station departures / hour',value:snapshot&&end>0?snapshot.metrics.throughput_per_hour.toFixed(2):'—',definition:`Unique trains released from ${snapshot?.station??'the station'} × 60 / elapsed simulation minutes. ${window}`},
    {label:`Section throughput / hour · ${sectionId||'—'}`,value:sectionRate?.toFixed(2)??'—',definition:`Observed SECTION_COMPLETED events on ${sectionId||'the selected section'} × 60 / observation minutes. Events are accumulated from responses, whose logs contain only the latest 100 events; missed events can undercount. ${window}`},
    {label:'Average station wait · min',value:snapshot?.metrics.average_wait_min?.toFixed(2)??'—',definition:`Backend average_wait_min: cumulative time from scheduled station entry until first departure (or now), clamped at zero, averaged across all trains in this loaded cohort. This is station wait, not total network delay. ${window}`},
    {label:'Completed journeys',value:snapshot?String(snapshot.trains.filter(t=>t.status==='ARRIVED').length):'—',definition:`Trains in this loaded cohort with status ARRIVED at their final destination. A section exit or station departure alone does not count. ${window}`},
  ];
  return <footer className="control-bottom"><div className="control-kpis">{metrics.map((metric,i)=><div className="control-kpi" key={metric.label}><span>{metric.label}<button type="button" className="control-info" aria-label={`Definition: ${metric.label}`} aria-describedby={`control-kpi-${i}`} title={metric.definition}>i<span id={`control-kpi-${i}`} role="tooltip">{metric.definition}</span></button></span><strong>{metric.value}</strong></div>)}</div><p>Simulation-based research prototype, not connected to live railway systems.</p></footer>;
}

function ComparisonKpis({pair,sectionId}:{pair:Comparison|null;sectionId:string}) {
  const aligned=!!pair&&!pair.error&&pair.left.time===pair.right.time;
  const values=(side:'left'|'right')=>{
    if(!pair)return [null,null,null,null];
    const snapshot=pair[side],events=pair.records.reduce<Parameters<typeof mergeEvents>[0]>((all,f)=>mergeEvents(all,f[side].events),[]);
    return [snapshot.time>0?snapshot.metrics.throughput_per_hour:null,sectionThroughput(events,sectionId,0,snapshot.time),snapshot.metrics.average_wait_min??null,snapshot.trains.filter(t=>t.status==='ARRIVED').length];
  };
  const a=values('left'),b=values('right');
  const labels=['Station departures / hour',`Section throughput / hour · ${sectionId}`,'Average station wait · min','Completed journeys'];
  const definitions=['Unique station departures × 60 / elapsed minutes.','Observed completed section crossings × 60 / elapsed minutes; missed backend log events can undercount.','Backend average_wait_min across the loaded cohort; lower values mean less station waiting.','Trains with ARRIVED status at their final destination, not individual section exits.'];
  const format=(n:number|null)=>n===null?'—':n.toFixed(2);
  return <footer className="control-bottom compare-kpis"><div className="control-kpis">{labels.map((label,i)=><div className="control-kpi" key={label}><span>{label}<button className="control-info" aria-label={`Comparison definition: ${label}`} title={`${definitions[i]} Window: 0–${pair?.left.time??0} min in A; 0–${pair?.right.time??0} min in B.`}>i<span role="tooltip">{definitions[i]} Observation: 0–{pair?.left.time??0} sim min (A), 0–{pair?.right.time??0} sim min (B). Delta = B − A; available only for aligned runs.</span></button></span><div className="compare-kpi-values"><strong><small>A</small>{format(a[i])}</strong><strong><small>B</small>{format(b[i])}</strong><b>Δ {aligned&&a[i]!==null&&b[i]!==null?`${b[i]!-a[i]!>=0?'+':''}${(b[i]!-a[i]!).toFixed(2)}`:'—'}</b></div></div>)}</div><p>Simulation-based research prototype, not connected to live railway systems. B − A shows tradeoffs, not a universal winner or real-world performance claim.</p></footer>;
}
