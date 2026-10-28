import type {BackendTrain,YardState} from '../station-state';
import type {Decision,MovementEvent,Recommendation} from '../decision-evidence';

export type Policy='ml'|'throughput'|'fifo';
export const policies:Record<Policy,string>={ml:'Random Forest V2',throughput:'Shortest-clearance heuristic',fifo:'FIFO · arrival order'};
export type Section={section_id:string;from_station:string;to_station:string;distance_km:number};
export type Network={stations:{station_code:string;station_name:string}[];sections:Section[]};
export type ControlEvent=MovementEvent&{station_id?:string};
export type Snapshot={
  session?:string;time:number;station:string;policy:Policy;trains:(BackendTrain&{entry_time_min:number})[];
  yard:YardState|null;events:ControlEvent[];occupancy:Record<string,string>;decision:Decision|null;
  metrics:{departed:number;cleared:number;queue:number;throughput_per_hour:number;average_wait_min?:number};
};
export type FeedItem={key:string;time:number;policy:Policy;recommendation:Recommendation;runLabel?:string};
export type ChartPoint={time:number;distance:number|null};

export function mergeEvents(previous:ControlEvent[],incoming:ControlEvent[]) {
  return [...new Map([...previous,...incoming].map(e=>[JSON.stringify(e),e])).values()];
}
export function decisionItems(snapshot:Snapshot):FeedItem[] {
  const steps=snapshot.decision?[...(snapshot.decision.steps??[]),snapshot.decision]:[];
  return steps.flatMap(step=>(step.recommendations??[]).map(recommendation=>{
    const policy=(step.policy??snapshot.policy) as Policy;
    return {key:JSON.stringify([step.time_min,policy,recommendation]),time:step.time_min,policy,recommendation};
  }));
}
export function safetyOverride(rec:Recommendation) {
  return rec.ml_action==='RELEASE'&&(rec.final_action==='HOLD'||rec.executed_action==='HOLD')&&!!rec.checks?.some(c=>!c.passed);
}
export function sectionPosition(snapshot:Snapshot,train:Snapshot['trains'][number],section:Section,events:ControlEvent[]):number|null {
  if(train.entry_time_min>snapshot.time)return null;
  if(train.current_section===section.section_id) {
    const p=Math.max(0,Math.min(1,train.progress));
    return (train.current_station===section.from_station?p:1-p)*section.distance_km;
  }
  if(train.status==='RUNNING')return null;
  const associated=snapshot.yard?.platforms.some(p=>p.train_id===train.train_id&&p.section===section.section_id)||
    events.some(e=>e.train_id===train.train_id&&e.section_id===section.section_id&&e.time_min<=snapshot.time);
  if(!associated)return null;
  return train.current_station===section.from_station?0:train.current_station===section.to_station?section.distance_km:null;
}
export function sectionTrace(history:Snapshot[],events:ControlEvent[],trainId:string,section:Section):ChartPoint[] {
  const points:ChartPoint[]=history.map(snapshot=>{
    const train=snapshot.trains.find(t=>t.train_id===trainId);
    return {time:snapshot.time,distance:train?sectionPosition(snapshot,train,section,events):null};
  });
  for(const event of events) {
    if(event.train_id!==trainId||event.section_id!==section.section_id)continue;
    const station=event.event==='SECTION_ENTERED'?event.from_station:event.event==='SECTION_COMPLETED'?event.station_id:null;
    if(station===section.from_station||station===section.to_station)
      points.push({time:event.time_min,distance:station===section.from_station?0:section.distance_km});
  }
  // At an event timestamp, draw the exact endpoint before a snapshot can break the line.
  return points.sort((a,b)=>a.time-b.time||Number(a.distance===null)-Number(b.distance===null));
}
export function sectionThroughput(events:ControlEvent[],sectionId:string,start:number,end:number) {
  if(end<=start)return null;
  return events.filter(e=>e.event==='SECTION_COMPLETED'&&e.section_id===sectionId&&e.time_min>start&&e.time_min<=end).length*60/(end-start);
}

// Layout uses connectivity only: the API does not provide geographic coordinates.
export function networkLayout(network:Network,root:string) {
  const levels=new Map<string,number>([[root,0]]),queue=[root];
  for(let i=0;i<queue.length;i++) {
    const code=queue[i];
    for(const edge of network.sections) {
      const next=edge.from_station===code?edge.to_station:edge.to_station===code?edge.from_station:null;
      if(next&&!levels.has(next)){levels.set(next,levels.get(code)!+1);queue.push(next);}
    }
  }
  const farthest=Math.max(1,...levels.values());
  for(const station of network.stations)if(!levels.has(station.station_code))levels.set(station.station_code,farthest+1);
  const maxLevel=Math.max(1,...levels.values());
  return network.stations.map(station=>{
    const level=levels.get(station.station_code)!;
    const peers=network.stations.filter(s=>levels.get(s.station_code)===level);
    return {...station,x:80+level/maxLevel*840,y:80+(peers.indexOf(station)+.5)/peers.length*440};
  });
}

export type DisruptionKind='track-block'|'signal-failure'|'breakdown'|'departure-delay'|'rush-hour'|'fog';
export const disruptionNames:Record<DisruptionKind,string>={'track-block':'Track block','signal-failure':'Signal failure',breakdown:'Train breakdown','departure-delay':'Departure +5 min','rush-hour':'Rush-hour +3 trains',fog:'Fog · 40 km/h preview'};
export type Disruption={id:string;kind:DisruptionKind;time:number;source:'client-mock';sectionId:string;platform:number;trainId:string;frozen?:Snapshot['trains'][number]};
export type TimelineMarker={kind:'disruption'|'hold'|'override'|'failure';label:string;source:'backend'|'client-mock'};
export type ReplayFrame={snapshot:Snapshot;disruptions:Disruption[];markers:TimelineMarker[]};
export type PairFrame={left:Snapshot;right:Snapshot;disruptions:Disruption[];markers:TimelineMarker[];error?:string};
export type Comparison={left:Snapshot;right:Snapshot;records:PairFrame[];policies:[Policy,Policy];verified:boolean;error?:string};
export function activeDisruptions(disruptions:Disruption[],time:number) {
  return disruptions.filter(d=>d.time<=time&&(d.kind!=='departure-delay'||time<d.time+5));
}
export function pairedAdvanceResult(left:Snapshot,right:Snapshot,results:PromiseSettledResult<Snapshot>[]) {
  const a=results[0].status==='fulfilled'?{...results[0].value,session:left.session}:left;
  const b=results[1].status==='fulfilled'?{...results[1].value,session:right.session}:right;
  const failures=results.flatMap((r,i)=>r.status==='rejected'?[`${i===0?'A':'B'}: ${r.reason instanceof Error?r.reason.message:String(r.reason)}`]:[]);
  if(a.time!==b.time)failures.push('Run clocks diverged. Deltas are unavailable; restart both runs.');
  return {left:a,right:b,error:failures.join(' ')||undefined};
}

export function initialSignature(snapshot:Snapshot) {
  return JSON.stringify([snapshot.station,snapshot.time,[...snapshot.trains].sort((a,b)=>a.train_id.localeCompare(b.train_id)),snapshot.yard,snapshot.occupancy,snapshot.metrics]);
}
export function decisionMarkers(snapshot:Snapshot):TimelineMarker[] {
  const items=[...new Map(decisionItems(snapshot).map(i=>[i.key,i])).values()];
  const held=items.filter(i=>(i.recommendation.executed_action??i.recommendation.final_action)==='HOLD').length;
  const overridden=items.filter(i=>safetyOverride(i.recommendation)).length;
  return [...(held?[{kind:'hold' as const,label:`${held} HOLD recommendations · ${snapshot.policy}`,source:'backend' as const}]:[]),
    ...(overridden?[{kind:'override' as const,label:`${overridden} safety overrides · ${snapshot.policy}`,source:'backend' as const}]:[])];
}
export function previewTrain(train:Snapshot['trains'][number],disruptions:Disruption[]) {
  const stopped=disruptions.find(d=>d.trainId===train.train_id&&(d.kind==='breakdown'||d.kind==='departure-delay'));
  return stopped?.frozen?{...train,...stopped.frozen}:train;
}
export function recordedView(records:ReplayFrame[],index:number) {
  if(!Number.isInteger(index)||index<0||index>=records.length)throw new Error('Choose a recorded frame.');
  const frames=records.slice(0,index+1);
  const events=frames.reduce<ControlEvent[]>((all,f)=>mergeEvents(all,f.snapshot.events),[]);
  const feed=[...new Map(frames.flatMap(f=>decisionItems(f.snapshot)).map(item=>[item.key,item])).values()];
  return {snapshot:records[index].snapshot,disruptions:records[index].disruptions,events,feed,history:frames.map(f=>f.snapshot)};
}
export function comparisonStats(snapshots:Snapshot[]) {
  const last=snapshots.at(-1);
  const items=[...new Map(snapshots.flatMap(decisionItems).map(i=>[i.key,i])).values()];
  const events=snapshots.reduce<ControlEvent[]>((all,s)=>mergeEvents(all,s.events),[]);
  const movement=events.filter(e=>e.event==='SECTION_ENTERED'||e.event==='SECTION_COMPLETED');
  const lastMovement=Math.max(snapshots[0]?.time??0,...movement.map(e=>e.time_min));
  return {holds:items.filter(i=>(i.recommendation.executed_action??i.recommendation.final_action)==='HOLD').length,
    overrides:items.filter(i=>safetyOverride(i.recommendation)).length,
    rejected:items.filter(i=>i.recommendation.final_action==='RELEASE'&&i.recommendation.executed_action==='HOLD').length,
    unfinished:last?.trains.filter(t=>t.status!=='ARRIVED').length??0,
    stalled:!!last&&last.time-lastMovement>=10&&last.trains.some(t=>t.entry_time_min<=last.time&&t.status!=='ARRIVED')};
}
