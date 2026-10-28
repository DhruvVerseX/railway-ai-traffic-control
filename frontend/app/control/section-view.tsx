'use client';
import {useMemo} from 'react';
import {scaleLinear} from 'd3-scale';
import {line} from 'd3-shape';
import {delayColor,trainLabel} from '../station-state';
import {sectionPosition,sectionTrace,previewTrain,type ChartPoint} from './control-data';
import {useControl} from './control-store';
import {MockDefinitions,MockCross} from './condition-effects';

export default function SectionView() {
  const store=useControl();
  const {network,snapshot,history,events,sectionId,selected,hovered,layers,warnings,disruptions}=store;
  const section=network?.sections.find(s=>s.section_id===sectionId);
  const traces=useMemo(()=>section&&snapshot?snapshot.trains.map(train=>({train,points:sectionTrace(history,events,train.train_id,section)})):[],[section,snapshot,history,events]);
  if(!section)return <div className="control-empty">No section data is available from the backend.</div>;
  const start=history[0]?.time??0,end=Math.max(start+1,snapshot?.time??1);
  const x=scaleLinear().domain([start,end]).range([75,960]);
  const y=scaleLinear().domain([0,section.distance_km]).range([270,35]);
  const path=line<ChartPoint>().defined(p=>p.distance!==null).x(p=>x(p.time)).y(p=>y(p.distance!));
  const highlighted=hovered??selected;
  const diagramTrains=snapshot?.trains.flatMap(original=>{const train=previewTrain(original,disruptions);const distance=sectionPosition(snapshot,train,section,events);return distance===null?[]:[{train,distance}];})??[];
  return <div className="section-view">
    <div className="control-view-heading"><div><span className="control-kicker">SECTION / {section.section_id}</span><h2>{section.from_station} <span>↔</span> {section.to_station}</h2></div><span>{section.distance_km} km · backend distance</span></div>
    <div className="section-diagram">
      <svg viewBox={`0 0 1000 ${Math.max(220,90+diagramTrains.length*24)}`} role="group" aria-label={`Track diagram between ${section.from_station} and ${section.to_station}`}>
        <MockDefinitions/><path d="M80 105H920" stroke="#c3ccba" strokeWidth="13"/><path d="M80 105H920" stroke="#7e9175" strokeWidth="10" strokeDasharray="3 10"/><path d="M80 105H920" stroke="#f8f9f1" strokeWidth="4"/>
        {layers.occupancy&&snapshot?.occupancy[sectionId]&&<path d="M80 105H920" stroke="#b28235" strokeWidth="3"/>}{disruptions.some(d=>d.kind==='track-block'&&d.sectionId===sectionId)&&<path className="mock-track-block" d="M80 105H920" stroke="url(#control-mock-hatch)" strokeWidth="17"><title>CLIENT MOCK · track blocked</title></path>}
        {[{x:80,code:section.from_station},{x:920,code:section.to_station}].map(station=><g key={station.code}><circle cx={station.x} cy="105" r="10" fill="#f9faf3" stroke="#526f44" strokeWidth="3"/><text x={station.x} y="40" textAnchor="middle">{station.code}</text></g>)}
        {(layers.signals||disruptions.some(d=>d.kind==='signal-failure'))&&snapshot?.yard?.platforms.filter(p=>p.section===sectionId&&(layers.signals||disruptions.some(d=>d.kind==='signal-failure'&&d.platform===p.platform))).map((p,i)=><g key={p.platform} transform={`translate(${snapshot.station===section.from_station?110:850},${155+i*15})`}><circle r="4" fill={p.aspect==='GREEN'?'#4e8b69':'#bd6650'}/>{disruptions.some(d=>d.kind==='signal-failure'&&d.platform===p.platform)&&<g className="mock-signal-failed"><MockCross x={0} y={0}/></g>}<text x="11" y="5" fontSize="13">P{p.platform} · {p.aspect}</text></g>)}
        {layers.trains&&diagramTrains.map(({train,distance},index)=>{
          const tx=80+distance/section.distance_km*840,ty=65+index*24,active=highlighted===train.train_id;
          return <g key={train.train_id}><path d={`M${tx} 105V${ty}`} stroke="#b2bea6" pointerEvents="none"/><g transform={`translate(${tx},${ty})`} className="control-train" role="button" tabIndex={0} aria-label={`Focus ${trainLabel(train)}`} aria-pressed={active}
            onClick={()=>store.focusTrain(train.train_id)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();store.focusTrain(train.train_id);}}}
            onPointerEnter={()=>store.setHovered(train.train_id)} onPointerLeave={()=>store.setHovered(null)} onFocus={()=>store.setHovered(train.train_id)} onBlur={()=>store.setHovered(null)}>
            <title>{trainLabel(train)} · {distance.toFixed(1)} km</title>
            {warnings.includes(train.train_id)&&<circle className="control-ai-ring" r="19"/>}
            {active&&<circle r="15" stroke="#36654d" strokeWidth="2" fill="none"/>}
            <rect x="-10" y="-7" width="20" height="14" rx="4" fill={delayColor(train.delay_min)}/>{disruptions.some(d=>d.trainId===train.train_id&&(d.kind==='breakdown'||d.kind==='departure-delay'))&&<text className="mock-train-warning" x="-29" y="6">⚠<title>CLIENT MOCK · train stopped preview</title></text>}
            {layers.names&&<text x={distance>section.distance_km/2?-18:18} y="4" textAnchor={distance>section.distance_km/2?'end':'start'} fontSize="13">{train.train_name} · {train.train_id}</text>}
          </g></g>;
        })}
      </svg>
    </div>
    <div className="string-heading"><div><h3>Time–distance</h3><p>Diagonal = movement · flat = recorded stop. Hover a train to link both views.</p></div><span>SIMULATED · {start.toFixed(0)}–{(snapshot?.time??0).toFixed(0)} min</span></div>
    <div className="string-chart"><svg viewBox="0 0 1000 330" role="group" aria-label={`Time-distance chart: time in simulated minutes, distance from ${section.from_station} in kilometres`}>
      {y.ticks(4).map(tick=><g key={tick}><path d={`M75 ${y(tick)}H960`} stroke="#e1e7d9"/><text x="62" y={y(tick)+4} textAnchor="end" fontSize="13">{tick}</text></g>)}
      {x.ticks(6).map(tick=><g key={tick}><path d={`M${x(tick)} 35V270`} stroke="#e8ecdf"/><text x={x(tick)} y="295" textAnchor="middle" fontSize="13">{tick}</text></g>)}
      <text x="75" y="19" fontSize="13">Distance from {section.from_station} (km) · {section.to_station} at {section.distance_km} km</text><text x="520" y="322" textAnchor="middle" fontSize="13">Simulation time (minutes)</text>
      {layers.trains&&traces.map(({train,points})=>{
        if(!points.some(p=>p.distance!==null))return null;
        const active=highlighted===train.train_id;
        return <g key={train.train_id} role="button" tabIndex={0} className="control-chart-train" aria-label={`Highlight ${trainLabel(train)}`} aria-pressed={active}
          onPointerEnter={()=>store.setHovered(train.train_id)} onPointerLeave={()=>store.setHovered(null)} onFocus={()=>store.setHovered(train.train_id)} onBlur={()=>store.setHovered(null)}
          onClick={()=>store.focusTrain(train.train_id)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();store.focusTrain(train.train_id);}}}>
          <title>{trainLabel(train)} · sampled positions and recorded crossing events</title>
          <path d={path(points)??''} fill="none" stroke={delayColor(train.delay_min)} strokeWidth={active?4:2} opacity={highlighted&&!active ? .25 : 1}/>
          <path d={path(points)??''} fill="none" stroke="transparent" strokeWidth="14"/>
          {points.filter(p=>p.distance!==null).slice(-1).map(p=><circle key={p.time} cx={x(p.time)} cy={y(p.distance!)} r={active?6:3} fill={delayColor(train.delay_min)}/>)}
        </g>;
      })}
    </svg></div>
    <div className="control-chart-key" role="group" aria-label="String-line train legend">{traces.filter(({points})=>points.some(p=>p.distance!==null)).map(({train})=><button key={train.train_id} aria-pressed={highlighted===train.train_id} onPointerEnter={()=>store.setHovered(train.train_id)} onPointerLeave={()=>store.setHovered(null)} onFocus={()=>store.setHovered(train.train_id)} onBlur={()=>store.setHovered(null)} onClick={()=>store.focusTrain(train.train_id)}><i style={{background:delayColor(train.delay_min)}}/>{trainLabel(train)}</button>)}</div>
    <p className="control-footnote">Observed positions only; unknown intervals are gaps. No predicted trajectories. Train colour shows recorded delay; use the legend to distinguish overlapping holds.</p>
  </div>;
}
