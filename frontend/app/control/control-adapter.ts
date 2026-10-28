import {stationState,type StationState} from '../station-state';
import {initialSignature,disruptionNames,pairedAdvanceResult,type Disruption,type DisruptionKind,type Network,type Policy,type Snapshot} from './control-data';

async function request<T>(path:string,body?:object,signal?:AbortSignal):Promise<T> {
  let response:Response;
  try{response=await fetch('/api/railway/'+path,{...(body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{}),signal});}
  catch(error){if(signal?.aborted)throw error;throw new Error('Backend unreachable. Check the Python API and, if configured, the ngrok tunnel.');}
  let value;
  try{value=await response.json();}catch{throw new Error('Backend returned a non-JSON response. The API or ngrok tunnel may be unavailable.');}
  if(!response.ok)throw new Error((value?.error||`Backend request failed (${response.status}).`)+(response.status===503?' Check the API and configured ngrok tunnel.':''));
  if(!value||typeof value!=='object')throw new Error('Backend returned an invalid response.');
  return value;
}

export const controlAdapter={
  capabilities:{seededRuns:'backend',snapshots:'backend-current / client-recorded-history',inject:'client-mock',seek:'client-mock'} as const,
  request,
  network:(signal?:AbortSignal)=>request<Network>('network',undefined,signal),
  async createComparison(station:string,policies:[Policy,Policy],signal?:AbortSignal) {
    const [left,right]=await Promise.all(policies.map(policy=>request<Snapshot>('scenario',{station,count:12,seed:42,policy},signal)));
    if(initialSignature(left)!==initialSignature(right))throw new Error('Comparison stopped: seeded initial conditions did not match.');
    return {left,right};
  },
  async advanceComparison(left:Snapshot,right:Snapshot,signal?:AbortSignal) {
    const results=await Promise.allSettled([left,right].map(run=>request<Snapshot>('advance',{session:run.session,policy:run.policy,minutes:1},signal)));
    return pairedAdvanceResult(left,right,results);
  },
  inject(snapshot:Snapshot,kind:DisruptionKind,target:{sectionId:string;platform:number;trainId:string}):Disruption {
    const train=snapshot.trains.find(t=>t.train_id===target.trainId);
    if((kind==='breakdown'||kind==='departure-delay')&&(!train||train.status==='ARRIVED'))throw new Error('Choose an unfinished train.');
    if(kind==='departure-delay'&&train?.status==='RUNNING')throw new Error('Choose a waiting train for a departure delay.');
    if(kind==='signal-failure'&&!snapshot.yard?.platforms.some(p=>p.platform===target.platform))throw new Error('Choose a valid station signal.');
    if(kind==='track-block'&&!target.sectionId)throw new Error('Choose a track section.');
    return {id:crypto.randomUUID(),kind,time:snapshot.time,source:'client-mock',...target,frozen:train?{...train}:undefined};
  },
  seek<T>(frames:T[],index:number):T {
    if(!Number.isInteger(index)||index<0||index>=frames.length)throw new Error('Choose a recorded frame.');
    return frames[index];
  },
};

// shortcut: these are visual previews, not dynamics; replace inject/seek when backend mutation and restoration exist.
export function renderStation(snapshot:Snapshot,disruptions:Disruption[],previous?:StationState):StationState {
  const scene=stationState(snapshot,previous);
  return {...scene,mock:{blockedSections:disruptions.filter(d=>d.kind==='track-block').map(d=>d.sectionId),
    failedPlatforms:disruptions.filter(d=>d.kind==='signal-failure').map(d=>d.platform)},
    trains:scene.trains.map(train=>{
      const d=disruptions.find(d=>d.trainId===train.id&&(d.kind==='breakdown'||d.kind==='departure-delay'));
      return d?{...train,mockWarning:disruptionNames[d.kind],sectionProgress:d.frozen?.progress??train.sectionProgress}:train;
    })};
}
