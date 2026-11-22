'use client';
import {useEffect,useMemo,useRef,useState} from 'react';
import {delayColor,trainLabel} from '../station-state';
import {networkLayout,previewTrain,type Snapshot} from './control-data';
import {useControl} from './control-store';
import {MockDefinitions,MockCross} from './condition-effects';
import illustrativeNetwork from './illustrative-network.json';
import type {CorridorControl} from './corridor-view';
import {NetworkOperations} from './network-operations';

const trainLabelOffsets = [[0,-20],[30,0],[-30,0],[0,22],[30,-20],[-30,-20],[30,22],[-30,22]] as const;

export default function NetworkView({corridor}: {corridor: CorridorControl | null}) {
  const store=useControl();
  const {network,snapshot,selected,hovered,focusToken,layers,warnings,disruptions}=store;
  const illustrative=!!network&&network.stations.length<=1;
  const graph=illustrative?illustrativeNetwork:network;
  const nodes=useMemo(()=>graph?networkLayout(graph,snapshot?.station??'MTJ'):[],[graph,snapshot?.station]);
  const svg=useRef<SVGSVGElement>(null);
  const map=useRef<HTMLDivElement>(null);
  const focusedToken=useRef(focusToken);
  const [fullscreenError,setFullscreenError]=useState('');
  const [camera,setCamera]=useState({x:0,y:0,k:1});
  const [stationCode,setStationCode]=useState<string|null>(null);
  const drag=useRef<{x:number;y:number}|null>(null);
  const point=(train:Snapshot['trains'][number])=>{
    const from=nodes.find(n=>n.station_code===train.current_station);
    const to=nodes.find(n=>n.station_code===train.next_station);
    if(!from)return null;
    const p=train.status==='RUNNING'&&to?Math.max(0,Math.min(1,train.progress)):0;
    return {x:from.x+((to?.x??from.x)-from.x)*p,y:from.y+((to?.y??from.y)-from.y)*p};
  };
  useEffect(()=>{
    if(focusedToken.current===focusToken)return;
    focusedToken.current=focusToken;
    if(!selected||!focusToken)return;
    const train=snapshot?.trains.find(t=>t.train_id===selected);
    const from=nodes.find(n=>n.station_code===train?.current_station),to=nodes.find(n=>n.station_code===train?.next_station);
    if(!train||!from)return;
    const p=train.status==='RUNNING'&&to?train.progress:0;
    const x=from.x+((to?.x??from.x)-from.x)*p,y=from.y+((to?.y??from.y)-from.y)*p;
    setCamera({x:500-x*2,y:300-y*2,k:2});
    // Focus once per explicit selection; subsequent ticks must not undo manual pan/zoom.
  },[focusToken,selected,nodes]);
  useEffect(()=>{
    const target=svg.current;if(!target)return;
    const wheel=(event:WheelEvent)=>{
      event.preventDefault();
      const matrix=target.getScreenCTM();if(!matrix)return;
      const point=new DOMPoint(event.clientX,event.clientY).matrixTransform(matrix.inverse());
      setCamera(current=>{
        const k=Math.max(.5,Math.min(4,current.k*Math.exp(-event.deltaY*.002)));
        return {k,x:point.x-(point.x-current.x)*k/current.k,y:point.y-(point.y-current.y)*k/current.k};
      });
    };
    target.addEventListener('wheel',wheel,{passive:false});
    return()=>target.removeEventListener('wheel',wheel);
  },[!!graph]);
  if(!graph)return <div className="control-empty">Waiting for network JSON from the backend.</div>;
  const detailed=camera.k>=1.6,highlighted=hovered??selected;
  const zoom=(factor:number)=>setCamera(c=>{const k=Math.max(.5,Math.min(4,c.k*factor));return {k,x:500-(500-c.x)*k/c.k,y:300-(300-c.y)*k/c.k};});
  const fitCorridor=()=>{
    const stations=corridor?.state?.stations;
    const route=nodes.filter(node=>stations?.some(station=>station.code===node.station_code));
    if(!route.length)return;
    const left=Math.min(...route.map(node=>node.x)),right=Math.max(...route.map(node=>node.x));
    const top=Math.min(...route.map(node=>node.y)),bottom=Math.max(...route.map(node=>node.y));
    const k=Math.min(3.2,760/Math.max(1,right-left),430/Math.max(1,bottom-top));
    setCamera({x:500-(left+right)*k/2,y:300-(top+bottom)*k/2,k});
  };
  const observedSection=graph.sections.find(section=>section.section_id===store.sectionId);
  const observedStation=stationCode??(snapshot?.station===observedSection?.to_station?snapshot?.station:observedSection?.from_station);
  const movingTrains=(!illustrative&&layers.trains?snapshot?.trains??[]:[])
    .filter(train=>train.status==='RUNNING')
    .flatMap(train=>{
      const position=point(previewTrain(train,disruptions));
      return position?[{train,position}]:[];
    });
  const placedLabels:{x:number;y:number}[]=[];
  const trainMarkers=movingTrains.map(({train,position})=>{
    const x=position.x*camera.k+camera.x,y=position.y*camera.k+camera.y;
    const offset=trainLabelOffsets.find(([dx,dy])=>{
      const labelX=x+dx,labelY=y+dy;
      return labelX>=22&&labelX<=978&&labelY>=10&&labelY<=590
        &&!placedLabels.some(label=>Math.abs(label.x-labelX)<46&&Math.abs(label.y-labelY)<20)
        &&!nodes.some(node=>Math.abs(node.x*camera.k+camera.x-labelX)<32&&Math.abs(node.y*camera.k+camera.y-labelY)<25);
    })??trainLabelOffsets[0];
    placedLabels.push({x:x+offset[0],y:y+offset[1]});
    return {train,position,offset};
  });
  return <div className={snapshot?'network-frame network-with-timetable':'network-frame'}>
    <div ref={map} className="network-view">
    <div className="control-view-heading"><div><span className="control-kicker">REGION / {graph.stations.length} STATIONS</span><h2>Network overview</h2></div><span>{corridor?corridor.state.stations.map(station=>station.code).join(' ↔ '):illustrative?'Illustrative static network':'Backend topology · schematic layout'}</span></div>
    <div className="network-toolbar"><span>{snapshot?'Select a train, station, or section to inspect it.':'Load trains to see traffic on the map.'}</span><div><button aria-label="Zoom out" onClick={()=>zoom(.8)}>−</button><span>{Math.round(camera.k*100)}%</span><button aria-label="Zoom in" onClick={()=>zoom(1.25)}>+</button><button onClick={()=>setCamera({x:0,y:0,k:1})}>Fit network</button>{corridor&&<button onClick={fitCorridor}>Fit corridor</button>}<button className="network-expand" onClick={()=>{setFullscreenError('');void map.current?.requestFullscreen().catch(()=>setFullscreenError('Full screen is unavailable in this browser. Use Fit network to show all stations.'));}}>Expand map</button><button className="network-collapse" onClick={()=>void document.exitFullscreen()}>Exit full screen</button></div></div>
    {fullscreenError&&<p className="control-footnote" role="alert">{fullscreenError}</p>}
    <svg ref={svg} className="network-svg" viewBox="0 0 1000 600" role="group" tabIndex={0} aria-label="Zoomable railway network. Drag or use arrow keys to pan; use the wheel or zoom buttons to zoom. Home fits the network."
      onKeyDown={e=>{if(e.target!==e.currentTarget)return;const delta:Record<string,[number,number]>={ArrowLeft:[40,0],ArrowRight:[-40,0],ArrowUp:[0,40],ArrowDown:[0,-40]};if(delta[e.key]){e.preventDefault();const [x,y]=delta[e.key];setCamera(c=>({...c,x:c.x+x,y:c.y+y}));}else if(e.key==='Home'){e.preventDefault();setCamera({x:0,y:0,k:1});}}}
      onPointerDown={e=>{if(e.button!==0)return;svg.current?.setPointerCapture(e.pointerId);drag.current={x:e.clientX,y:e.clientY};}}
      onPointerMove={e=>{if(!drag.current)return;const matrix=svg.current?.getScreenCTM();if(!matrix)return;const a=new DOMPoint(drag.current.x,drag.current.y).matrixTransform(matrix.inverse()),b=new DOMPoint(e.clientX,e.clientY).matrixTransform(matrix.inverse());setCamera(c=>({...c,x:c.x+b.x-a.x,y:c.y+b.y-a.y}));drag.current={x:e.clientX,y:e.clientY};}}
      onPointerUp={()=>{drag.current=null;}} onPointerCancel={()=>{drag.current=null;}}>
      <MockDefinitions/><defs><pattern id="control-map-grid" width="40" height="40" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="#d9e1ce"/></pattern></defs><rect width="1000" height="600" fill="url(#control-map-grid)"/>
      <g transform={`translate(${camera.x},${camera.y}) scale(${camera.k})`}>
        {graph.sections.map(edge=>{
          const from=nodes.find(n=>n.station_code===edge.from_station),to=nodes.find(n=>n.station_code===edge.to_station);
          if(!from||!to)return null;
          if(corridor){
            const block=corridor.state?.sections.find(section=>section.section_id===edge.section_id);
            if(block){
            const status=block.occupant?`occupied by ${block.occupant}`:block.clearance_min?`headway ${block.clearance_min} minutes`:'clear';
            const active=corridor.sectionId===block.section_id;
            const color=layers.occupancy?(block.occupant?'#98622e':block.clearance_min?'#91632e':'#427b57'):'#69846a';
            const select=()=>{setStationCode(null);corridor.setSectionId(block.section_id);};
            return <g key={edge.section_id} className="control-train" role="button" tabIndex={0} aria-label={`${block.section_id}, ${status}`} aria-pressed={active}
              onPointerDown={event=>event.stopPropagation()} onClick={select}
              onKeyDown={event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();select();}}}>
              <title>{block.section_id} · {block.distance_km} km · {status}</title>
              <line x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke="transparent" strokeWidth="22" vectorEffect="non-scaling-stroke"/>
              {active&&<line x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke="#dcead4" strokeWidth="13" vectorEffect="non-scaling-stroke"/>}
              <line x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke={color} strokeWidth={active?6:4} strokeDasharray={layers.occupancy&&block.clearance_min?'7 4':undefined} vectorEffect="non-scaling-stroke"/>
              {layers.names&&<text className="network-corridor-section" x={(from.x+to.x)/2} y={(from.y+to.y)/2+16/camera.k} textAnchor="middle" fontSize={17/camera.k}>{block.section_id}</text>}
            </g>;
            }
          }
          const occupied=!illustrative&&!!snapshot?.occupancy[edge.section_id];
          const waiting=!illustrative&&snapshot?.yard?.platforms.filter(p=>p.section===edge.section_id&&!p.locked&&p.train_id).length;
          const headway=(snapshot?.clearance_until?.[edge.section_id]??0)>(snapshot?.time??0);
          const active=!illustrative&&store.sectionId===edge.section_id;
          const color=layers.occupancy&&occupied?(waiting?'#bd6650':'#b28235'):layers.occupancy&&headway?'#91632e':active?'#427b57':'#a7b99b';
          const select=()=>{if(!illustrative){setStationCode(null);store.setSectionId(edge.section_id);}};
          const status=occupied?'occupied':headway?'headway':'clear';
          return <g key={edge.section_id} className={!illustrative?'control-train':undefined} role={illustrative?undefined:'button'} tabIndex={illustrative?undefined:0} aria-label={`${edge.section_id}, ${edge.from_station} to ${edge.to_station}, ${status}`} aria-pressed={illustrative?undefined:active}
            onPointerDown={event=>{if(!illustrative)event.stopPropagation();}} onClick={select} onKeyDown={event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();select();}}}>
            <title>{edge.section_id} · {illustrative?'illustrative connection':`${edge.distance_km} km · ${status}`}</title>
            {!illustrative&&<line x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke="transparent" strokeWidth="18" vectorEffect="non-scaling-stroke"/>}
            {active&&<line x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke="#dcead4" strokeWidth="12" vectorEffect="non-scaling-stroke"/>}
            <line x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke={color} strokeWidth={active?6:4} strokeDasharray={layers.occupancy&&headway&&!occupied?'7 4':undefined} vectorEffect="non-scaling-stroke"/>
            {disruptions.some(d=>d.kind==='track-block'&&d.sectionId===edge.section_id)&&<line className="mock-track-block" x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke="url(#control-mock-hatch)" strokeWidth="16" vectorEffect="non-scaling-stroke"/>}
            {active&&layers.names&&<text className="network-corridor-section" x={(from.x+to.x)/2} y={(from.y+to.y)/2-12/camera.k} textAnchor="middle" fontSize={18/camera.k}>{edge.section_id}</text>}
          </g>;
        })}
        {nodes.map(node=>{
          const station=corridor?.state?.stations.find(row=>row.code===node.station_code);
          const queueCount=layers.trains?(snapshot?.trains.filter(train=>train.current_station===node.station_code&&train.status!=='RUNNING'&&train.status!=='ARRIVED'&&train.entry_time_min<=snapshot.time).length??0):0;
          const pick=()=>{
            setStationCode(node.station_code);
            document.getElementById('network-station-title')?.scrollIntoView({block:'nearest'});
          };
          const active=observedStation===node.station_code;
          return <g key={node.station_code} transform={`translate(${node.x},${node.y})`}>
          <title>{node.station_name} · {node.station_code}{station?.passing_capacity?` · ${corridor?.state?.passing_slots_used}/${station.passing_capacity} tracks in use or reserved`:''}</title>
          {station?.passing_capacity&&<circle r={13/camera.k} fill="#e3eddb" stroke="#65916b" strokeWidth="1.5" vectorEffect="non-scaling-stroke"/>}
          <g className={snapshot?'control-train':undefined} role={snapshot?'button':undefined} tabIndex={snapshot?0:undefined} aria-label={`Inspect ${node.station_name} station${queueCount?`, ${queueCount} trains waiting`:''}`} aria-pressed={snapshot?active:undefined}
            onPointerDown={event=>{if(snapshot)event.stopPropagation();}} onClick={pick} onKeyDown={event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();pick();}}}>
            {snapshot&&<circle r={13/camera.k} fill="transparent"/>}
            <circle r={station||active?7:5} fill={active?'#427b57':'#fbfcf5'} stroke="#526f44" strokeWidth="2" vectorEffect="non-scaling-stroke"/>
            {layers.names&&<text className="network-station-code" y={23/camera.k} textAnchor="middle" fontSize={19/camera.k}>{node.station_code}</text>}
            {queueCount>0&&<g transform={`translate(${15/camera.k},${-20/camera.k}) scale(${1/camera.k})`}>
              <title>{queueCount} waiting at {node.station_name}</title><rect x="-10" y="-8" width="25" height="18" rx="5" fill="#f2e4ca" stroke="#ac854f"/>
              <text className="network-waiting-train" textAnchor="middle" x="2" y="5" fontSize="13">{queueCount}</text>
            </g>}
          </g>
          {!corridor&&(detailed&&layers.signals||disruptions.some(d=>d.kind==='signal-failure'))&&node.station_code===snapshot?.station&&snapshot.yard?.platforms.filter(p=>layers.signals||disruptions.some(d=>d.kind==='signal-failure'&&d.platform===p.platform)).map((p,i)=><g key={p.platform} transform={`translate(${(i*12-18)/camera.k},${37/camera.k})`}><title>Platform {p.platform} · {p.aspect}</title><circle r={3/camera.k} fill={p.aspect==='GREEN'?'#4e8b69':'#bd6650'}/>{disruptions.some(d=>d.kind==='signal-failure'&&d.platform===p.platform)&&<g className="mock-signal-failed"><MockCross x={0} y={0} size={7/camera.k}/></g>}</g>)}
          </g>;
        })}
        {trainMarkers.map(({train,position:pos,offset:[labelX,labelY]})=>{
          const active=highlighted===train.train_id;
          return <g key={train.train_id} transform={`translate(${pos.x},${pos.y}) scale(${1/camera.k})`} className="control-train" role="button" tabIndex={0} aria-label={`Focus ${trainLabel(train)}`} aria-pressed={active}
            onPointerDown={e=>e.stopPropagation()} onClick={()=>store.focusTrain(train.train_id)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();store.focusTrain(train.train_id);}}}
            onPointerEnter={()=>store.setHovered(train.train_id)} onPointerLeave={()=>store.setHovered(null)} onFocus={()=>store.setHovered(train.train_id)} onBlur={()=>store.setHovered(null)}>
            <title>{trainLabel(train)} · {train.status}</title>
            <circle r="12" fill="transparent"/>
            {warnings.includes(train.train_id)&&<circle className="control-ai-ring" r="13"/>}
            {active&&<circle r="10" fill="none" stroke="#36654d" strokeWidth="2" vectorEffect="non-scaling-stroke"/>}
            <circle r="6" fill={delayColor(train.delay_min)} stroke="#fffef9" strokeWidth="1.5"/>{disruptions.some(d=>d.trainId===train.train_id&&(d.kind==='breakdown'||d.kind==='departure-delay'))&&<text className="mock-train-warning" x="-21" y="4" fontSize="20">⚠<title>CLIENT MOCK · stopped train</title></text>}
            {layers.names&&<g>
              <line x2={labelX} y2={labelY} stroke={active?'#365f46':'#778d76'} strokeWidth="1.2"/>
              <g transform={`translate(${labelX},${labelY})`}>
                <rect x="-20" y="-9" width="40" height="18" rx="4" fill={active?'#365f46':'#fffef9'} stroke={active?'#365f46':'#a6b7a0'}/>
                <text className={active?'network-running-train':'network-train-id'} y="4" textAnchor="middle" fontSize="13">{train.train_id}</text>
              </g>
            </g>}
          </g>;
        })}
      </g>
    </svg>
    {corridor?<div className="network-legend">
      {layers.occupancy&&<><span><i style={{background:'#427b57'}}/>Timetabled section</span><span><i style={{background:'#98622e'}}/>Occupied / headway</span></>}
      {corridor.state.stations.filter(station=>station.passing_capacity).map(station=><span key={station.code}>{station.operational_only?station.name:`${station.name} passing loop`} · {corridor.state.passing_slots_used}/{station.passing_capacity} tracks in use or reserved</span>)}
    </div>:<>
      {layers.occupancy?<div className="network-legend"><span><i style={{background:'#a7b99b'}}/>Clear</span><span><i style={{background:'#b28235'}}/>Occupied</span><span><i style={{background:'#bd6650'}}/>Occupied + waiting</span><span><i className="network-headway-key"/>Headway</span></div>:<p className="control-footnote">Occupancy colours hidden.</p>}
      <p className="control-footnote">{illustrative?'Illustrative connections only; no simulated traffic is projected onto this fallback map.':'Connectivity comes from /network JSON. Coordinates are schematic, not geographic. Signals are available only at the simulated station.'}</p>
    </>}
    {snapshot&&layers.trains&&<div className="network-legend network-traffic-key"><span><i className="network-queue-key"/>Station queue count</span><span><i className="network-moving-key"/>Moving train</span></div>}
    {selected&&<div className="network-legend network-inspector-jump"><button className="network-timetable-jump" onClick={()=>document.getElementById('network-train-heading')?.scrollIntoView({block:'start'})}>Inspect {selected}</button></div>}
    </div>
    <NetworkOperations stationCode={stationCode}/>
  </div>;
}
