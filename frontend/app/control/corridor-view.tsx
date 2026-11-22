'use client';

import {ArrowRight, TrainFront} from 'lucide-react';
import type {Recommendation} from '../decision-evidence';
import './corridor.css';

type Stop = {
  station: string;
  planned_arrival: number | null;
  actual_arrival: number | null;
  planned_departure: number | null;
  actual_departure: number | null;
};
type Train = {
  id: string; name: string; type: string; origin: string; destination: string;
  station: string; section: string | null; outgoing: string | null; next_station: string | null;
  status: 'Scheduled' | 'Queued' | 'At passing loop' | 'Running' | 'Arrived';
  reason: string; stops: Stop[]; waiting_min: number; deviation_min: number | null;
  remaining_min: number; speed: number; progress: number; ready_at: number;
};
type Section = {
  section_id: string; from_station: string; to_station: string; distance_km: number;
  minimum_headway_min: number; normal_speed_kmph: number; occupant: string | null;
  clearance_min: number; completed: number; throughput_per_hour: number;
};
export type Corridor = {
  time: number; horizon: number; trains: Train[]; sections: Section[];
  stations: {code: string; name: string; departed: number; passing_capacity: number | null}[];
  passing_slots_used: number;
  events: {event: string; train_id: string; section_id: string; time_min: number}[];
};

function clock(minutes: number | null) {
  if (minutes === null) return '—';
  const seconds = 6 * 3600 + Math.round(minutes * 60);
  return [Math.floor(seconds / 3600), Math.floor(seconds / 60) % 60, seconds % 60]
    .map(value => String(value).padStart(2, '0')).join(':');
}

function delta(planned: number | null, actual: number | null) {
  if (planned === null || actual === null) return '—';
  const difference = actual - planned;
  return Math.abs(difference) < 0.005 ? 'On time' : `${difference > 0 ? '+' : '−'}${Math.abs(difference).toFixed(2)} min`;
}

export function TrainInspector({train, state, decision}: {train: Train; state: Corridor; decision?: Recommendation}) {
  const stationName = (code: string) => state.stations.find(station => station.code === code)?.name ?? code;
  return <aside className="corridor-page corridor-inspector corridor-panel" aria-labelledby="corridor-train-heading">
    <div className="corridor-card-heading"><span className="corridor-label">Selected service · {train.id}</span><span className={`corridor-tag ${train.status === 'Running' ? 'running' : train.status === 'Queued' ? 'queued' : ''}`}>{train.status}</span></div>
    <h2 id="corridor-train-heading">{train.name}</h2>
    <p className="corridor-route">{train.type} <span>·</span> {train.origin} <ArrowRight size={14}/> {train.destination}</p>
    <dl className="corridor-train-stats">
      <div><dt>Location</dt><dd>{train.section ?? stationName(train.station)}</dd></div>
      <div><dt>Next stop</dt><dd>{train.next_station ? stationName(train.next_station) : 'Journey complete'}</dd></div>
      <div><dt>Speed</dt><dd>{train.speed} km/h</dd></div>
      <div><dt>Dispatch waiting</dt><dd>{train.waiting_min.toFixed(2)} min</dd></div>
    </dl>
    <p className="corridor-train-reason">{train.reason} {train.status === 'Running' ? `Section arrival in ${train.remaining_min.toFixed(2)} min.` : train.status === 'Scheduled' ? `Ready at ${clock(train.ready_at)}.` : ''}</p>
    {decision?.ml_action&&<p className="corridor-train-reason"><strong>Random Forest V2 · {decision.ml_action}</strong><br/>
      Dispatch: {decision.executed_action ?? decision.final_action} · {decision.execution_reason ?? decision.reason}</p>}
    <h3>Stop timetable</h3>
    <div className="corridor-table-scroll"><table className="corridor-timetable" aria-label={`${train.id} planned and actual timetable`}>
      <thead><tr><th scope="col">Stop</th><th scope="col">Movement</th><th scope="col">Planned</th><th scope="col">Actual</th><th scope="col">Δ</th></tr></thead>
      {train.stops.map(stop => {
        const rows = [
          {label: 'Arrive', planned: stop.planned_arrival, actual: stop.actual_arrival},
          {label: 'Depart', planned: stop.planned_departure, actual: stop.actual_departure},
        ].filter(row => row.planned !== null);
        return <tbody key={stop.station}>{rows.map((row, index) => <tr key={row.label}>
          {index === 0 && <th scope="rowgroup" rowSpan={rows.length}>{stop.station}</th>}
          <td>{row.label}</td><td>{clock(row.planned)}</td><td>{clock(row.actual)}</td>
          <td className={row.actual !== null && row.planned !== null && row.actual > row.planned + 0.005 ? 'late' : ''}>{delta(row.planned, row.actual)}</td>
        </tr>)}</tbody>;
      })}
    </table></div>
  </aside>;
}

export type CorridorControl = {
  state: Corridor;
  trainId: string | null;
  sectionId: string;
  section: Section | undefined;
  selectedTrain: Train | undefined;
  selectTrain: (train: Train) => void;
  setTrainId: (id: string) => void;
  setSectionId: (id: string) => void;
};

export function CorridorDetails({corridor}: {corridor: CorridorControl}) {
  const {state, section, trainId, sectionId, selectTrain, setTrainId, setSectionId} = corridor;
  if (!state || !section) return null;
  return <section className="corridor-page" aria-label="Timetable operations">
    <div className="corridor-shell">
          <div className="corridor-operations">
            <section className="corridor-block" aria-label="Observed section">
              <div><span className="corridor-label">Observed section</span><h3>{section.section_id} · {section.from_station} ↔ {section.to_station}</h3>
                <p>{section.occupant ? `Occupied by ${section.occupant}` : section.clearance_min > 0 ? `Headway remaining ${section.clearance_min.toFixed(2)} min` : 'Clear for an eligible movement'} · {section.minimum_headway_min} min post-clearance headway</p></div>
              <div><strong>{state.time ? section.throughput_per_hour.toFixed(2) : '—'}</strong><span>clears/hour</span></div>
              <div><strong>{section.completed}</strong><span>completed section moves</span></div>
            </section>
            <p className="corridor-method">Throughput counts completed movements in both directions over elapsed simulation time.</p>
          </div>
        <div className="corridor-workspace corridor-lower">
          <section className="corridor-panel corridor-roster" aria-labelledby="corridor-roster-heading">
            <div className="corridor-card-heading"><h2 id="corridor-roster-heading">Service board</h2><span>{state.trains.filter(train => train.status === 'Arrived').length}/{state.trains.length} journeys complete</span></div>
            <div className="corridor-table-scroll"><table className="corridor-service-table">
              <thead><tr><th scope="col">Service</th><th scope="col">Route</th><th scope="col">Status</th><th scope="col">Latest movement Δ</th></tr></thead>
              <tbody>{state.trains.map(train => <tr key={train.id} className={train.id === trainId ? 'is-selected' : ''}>
                <th scope="row"><button aria-pressed={train.id === trainId} onClick={() => selectTrain(train)}><TrainFront size={16}/><span>{train.name}<small>{train.id} · {train.type}</small></span></button></th>
                <td>{train.origin} → {train.destination}</td><td>{train.status} <small>{train.section ?? train.station}</small></td>
                <td className={(train.deviation_min ?? 0) > 0 ? 'late' : ''}>{train.deviation_min === null ? '—' : delta(0, train.deviation_min)}</td>
              </tr>)}</tbody>
            </table></div>
          </section>
          <section className="corridor-panel corridor-queues" aria-labelledby="corridor-queues-heading">
            <div className="corridor-card-heading"><h2 id="corridor-queues-heading">Station queues</h2><span>By outgoing route</span></div>
            {state.stations.map(station => {
              const queue = state.trains.filter(train => train.station === station.code && (train.status === 'Queued' || train.status === 'At passing loop'));
              const routes = state.sections.filter(row => row.from_station === station.code || row.to_station === station.code);
              return <div className="corridor-queue" key={station.code}>
                <div><strong>{station.name}</strong><span>{queue.length} at station · {station.departed} departed</span></div>
                {routes.map(route => {
                  const onward = queue.filter(train => train.outgoing === route.section_id);
                  return <div className="corridor-queue-route" key={route.section_id}>
                    <button onClick={() => setSectionId(route.section_id)} aria-pressed={sectionId === route.section_id}>{route.section_id} <ArrowRight size={12}/> {route.from_station === station.code ? route.to_station : route.from_station}</button>
                    {onward.length ? onward.map(train => <button className="corridor-queue-train" key={train.id} onClick={() => selectTrain(train)} aria-pressed={trainId === train.id}>{train.id}</button>) : <span>No trains queued</span>}
                  </div>;
                })}
              </div>;
            })}
          </section>
        </div>
        <section className="corridor-panel corridor-movement" aria-labelledby="corridor-movement-heading">
          <div className="corridor-card-heading"><h2 id="corridor-movement-heading">Recent movements</h2><span>Recorded by the Python simulator</span></div>
          {state.events.length ? <ol>{[...state.events].reverse().map(event => <li key={`${event.train_id}-${event.section_id}-${event.event}`}><time>{clock(event.time_min)}</time><button onClick={() => {setTrainId(event.train_id); setSectionId(event.section_id);}}>{event.train_id}</button><span>{event.event === 'SECTION_ENTERED' ? 'Entered' : 'Cleared'} {event.section_id}</span></li>)}</ol> : <p>Play or step to record movements.</p>}
        </section>
    </div>
  </section>;
}
