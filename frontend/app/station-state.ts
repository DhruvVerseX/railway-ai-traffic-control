import type {MovementEvent} from './decision-evidence';

export type BackendTrain = {
  train_id:string; train_name:string; status:string; current_station:string;
  current_section:string|null; next_station:string|null; progress:number;
  delay_min:number; train_type?:string;
};
export type YardState = {
  platforms:{platform:number;train_id:string|null;aspect:string;held:boolean;locked:boolean;section:string|null;destination:string|null;reason:string}[];
  assignments:Record<string,number>; outside:string[];
};
export type StationTrain = {
  id:string; name:string; status:string; type:string|null; delay:number;
  sectionProgress:number; platform:number|null; destination:string|null;
  outside:boolean; departing:boolean;
  mockWarning?:string;
};
export type StationState = {
  time:number; trains:StationTrain[]; platforms:YardState['platforms'];
  signals:{platform:number;aspect:string}[]; events:MovementEvent[];
  mock?:{blockedSections:string[];failedPlatforms:number[]};
};
export function trainLabel(train:{train_id:string;train_name:string}) {
  return `${train.train_name || train.train_id} · ${train.train_id}`;
}
export function delayColor(delay:number) {
  return delay <= 0 ? '#4e8b69' : delay <= 5 ? '#b28235' : '#bd6650';
}

// The API has section progress, not station coordinates or arrival progress.
export function stationState(response:{time:number;station:string;trains:BackendTrain[];yard:YardState|null;events:MovementEvent[]}, previous?:StationState):StationState {
  const platforms=response.yard?.platforms ?? [];
  return {
    time:response.time, platforms, events:response.events,
    signals:platforms.map(p=>({platform:p.platform,aspect:p.aspect})),
    trains:response.trains.map(t=>{
      const assigned=platforms.find(p=>p.platform===response.yard?.assignments[t.train_id]);
      const prior=previous?.trains.find(p=>p.id===t.train_id);
      const departure=response.events.some(e=>e.event==='SECTION_ENTERED'&&e.train_id===t.train_id&&e.from_station===response.station&&e.time_min>=(previous?.time ?? response.time));
      const departing=!!(assigned?.locked && t.status==='RUNNING' && t.current_station===response.station && assigned.section===t.current_section);
      // Retain a departing sprite if a coarse tick has already cleared its assignment.
      const retained=!assigned && prior?.platform && (prior.departing || departure);
      return {id:t.train_id,name:t.train_name||t.train_id,status:t.status,type:t.train_type??null,
        delay:t.delay_min,sectionProgress:t.progress,platform:assigned?.platform ?? (retained?prior.platform:null),
        destination:assigned?.destination ?? (retained?prior.destination:null),
        outside:response.yard?.outside.includes(t.train_id)??false,departing:departing||!!retained};
    }),
  };
}
