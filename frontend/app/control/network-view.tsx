'use client';
import {useEffect,useMemo,useRef,useState} from 'react';
import {delayColor,trainLabel} from '../station-state';
import {networkLayout,previewTrain,type Snapshot} from './control-data';
import {useControl} from './control-store';
import {MockDefinitions,MockCross} from './condition-effects';
import illustrativeNetwork from './illustrative-network.json';

export default function NetworkView() {
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
  return <div ref={map} className="network-view">
    <div className="control-view-heading"><div><span className="control-kicker">REGION / {graph.stations.length} STATIONS</span><h2>Network overview</h2></div><span>{illustrative?'Illustrative static network':'Backend topology · schematic layout'}</span></div>
    <div className="network-toolbar"><span>{detailed?'Detailed · names & available station signals':'Overview · stations & section congestion'}</span><div><button aria-label="Zoom out" onClick={()=>zoom(.8)}>−</button><span>{Math.round(camera.k*100)}%</span><button aria-label="Zoom in" onClick={()=>zoom(1.25)}>+</button><button onClick={()=>setCamera({x:0,y:0,k:1})}>Fit network</button><button className="network-expand" onClick={()=>{setFullscreenError('');void map.current?.requestFullscreen().catch(()=>setFullscreenError('Full screen is unavailable in this browser. Use Fit network to show all stations.'));}}>Expand map</button><button className="network-collapse" onClick={()=>void document.exitFullscreen()}>Exit full screen</button></div></div>
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
          const occupied=!illustrative&&!!snapshot?.occupancy[edge.section_id];
          const waiting=!illustrative&&snapshot?.yard?.platforms.filter(p=>p.section===edge.section_id&&!p.locked&&p.train_id).length;
          const color=layers.occupancy&&occupied?(waiting?'#bd6650':'#b28235'):'#a7b99b';
          return <g key={edge.section_id}><title>{edge.section_id} · {illustrative?'illustrative connection':`${edge.distance_km} km · ${occupied?'occupied':'clear'}${waiting?' · assigned trains waiting':''}`}</title><line x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke={color} strokeWidth="5" vectorEffect="non-scaling-stroke"/>{disruptions.some(d=>d.kind==='track-block'&&d.sectionId===edge.section_id)&&<line className="mock-track-block" x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke="url(#control-mock-hatch)" strokeWidth="16" vectorEffect="non-scaling-stroke"/>}{detailed&&layers.names&&<text x={(from.x+to.x)/2} y={(from.y+to.y)/2-12} textAnchor="middle" fontSize={18/camera.k}>{edge.section_id}</text>}</g>;
        })}
        {nodes.map(node=><g key={node.station_code} transform={`translate(${node.x},${node.y})`}><title>{node.station_name} · {node.station_code}</title><circle r={node.station_code===snapshot?.station?9:6} fill="#fbfcf5" stroke="#526f44" strokeWidth="2" vectorEffect="non-scaling-stroke"/>{layers.names&&<text y={23/camera.k} textAnchor="middle" fontSize={20/camera.k}>{detailed?node.station_name:node.station_code}</text>}
          {(detailed&&layers.signals||disruptions.some(d=>d.kind==='signal-failure'))&&node.station_code===snapshot?.station&&snapshot.yard?.platforms.filter(p=>layers.signals||disruptions.some(d=>d.kind==='signal-failure'&&d.platform===p.platform)).map((p,i)=><g key={p.platform} transform={`translate(${(i*26-40)/camera.k},${45/camera.k})`}><circle r={4/camera.k} fill={p.aspect==='GREEN'?'#4e8b69':'#bd6650'}/>{disruptions.some(d=>d.kind==='signal-failure'&&d.platform===p.platform)&&<g className="mock-signal-failed"><MockCross x={0} y={0} size={9/camera.k}/></g>}<text y={16/camera.k} textAnchor="middle" fontSize={18/camera.k}>P{p.platform}</text></g>)}
        </g>)}
        {!illustrative&&layers.trains&&snapshot?.trains.filter(t=>t.entry_time_min<=snapshot.time).map((train,i)=>{
          const pos=point(previewTrain(train,disruptions));if(!pos)return null;const active=highlighted===train.train_id;
          const stack=train.status==='RUNNING'?i%3:snapshot.trains.filter(t=>t.current_station===train.current_station&&t.status!=='RUNNING'&&t.entry_time_min<=snapshot.time).findIndex(t=>t.train_id===train.train_id);
          return <g key={train.train_id} transform={`translate(${pos.x},${pos.y-(18+stack*21)/camera.k})`} className="control-train" role="button" tabIndex={0} aria-label={`Focus ${trainLabel(train)}`} aria-pressed={active}
            onPointerDown={e=>e.stopPropagation()} onClick={()=>store.focusTrain(train.train_id)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();store.focusTrain(train.train_id);}}}
            onPointerEnter={()=>store.setHovered(train.train_id)} onPointerLeave={()=>store.setHovered(null)} onFocus={()=>store.setHovered(train.train_id)} onBlur={()=>store.setHovered(null)}>
            <title>{trainLabel(train)} · {train.status}</title>
            {warnings.includes(train.train_id)&&<circle className="control-ai-ring" r={15/camera.k}/>}
            {active&&<circle r={12/camera.k} fill="none" stroke="#36654d" strokeWidth="2" vectorEffect="non-scaling-stroke"/>}
            <circle r={6/camera.k} fill={delayColor(train.delay_min)}/>{disruptions.some(d=>d.trainId===train.train_id&&(d.kind==='breakdown'||d.kind==='departure-delay'))&&<text className="mock-train-warning" x={-21/camera.k} y={4/camera.k} fontSize={22/camera.k}>⚠<title>CLIENT MOCK · stopped train</title></text>}
            {detailed&&layers.names&&<text x={15/camera.k} y={4/camera.k} fontSize={20/camera.k}>{trainLabel(train)}</text>}
          </g>;
        })}
      </g>
    </svg>
    {layers.occupancy?<div className="network-legend"><span><i style={{background:'#a7b99b'}}/>Clear</span><span><i style={{background:'#b28235'}}/>Occupied</span><span><i style={{background:'#bd6650'}}/>Occupied + waiting</span></div>:<p className="control-footnote">Occupancy colours hidden.</p>}
    <p className="control-footnote">{illustrative?'Illustrative connections only; no simulated traffic is projected onto this fallback map.':'Connectivity comes from /network JSON. Coordinates are schematic, not geographic. Signals are available only at the simulated station.'}</p>
  </div>;
}
