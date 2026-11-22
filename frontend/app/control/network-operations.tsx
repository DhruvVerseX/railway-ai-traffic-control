'use client';

import {ArrowRight, TrainFront} from 'lucide-react';
import {policies, sectionThroughput, type NetworkTrain, type Snapshot} from './control-data';
import {StopTimetable} from './corridor-view';
import {useControl} from './control-store';

function statusOf(train: NetworkTrain, snapshot: Snapshot) {
  const scheduled = snapshot.timetable?.trains.find(row => row.id === train.train_id);
  if (scheduled) return scheduled.status;
  if (train.status === 'RUNNING') return 'Running';
  if (train.status === 'ARRIVED') return 'Arrived';
  if (train.entry_time_min > snapshot.time) return 'Scheduled';
  if ((train.ready_time_min ?? 0) > snapshot.time) return 'Dwelling';
  if (snapshot.yard?.outside.includes(train.train_id)) return 'Waiting for platform';
  return 'Queued';
}

function minutes(value: number | undefined) {
  return value === undefined ? '—' : `${value.toFixed(2)} min`;
}

export function NetworkTrainInspector() {
  const {snapshot, network, selected, focusTrain, feed, policy, events} = useControl();
  const train = snapshot?.trains.find(row => row.train_id === selected);
  if (!snapshot || !train) return <aside className="corridor-page corridor-inspector corridor-panel" aria-label="Train inspector">
    <h2>Train inspector</h2><p className="corridor-train-reason">Load a scenario, then select a train on the map or service board.</p>
  </aside>;
  const stationName = (code: string | undefined | null) => network?.stations.find(station => station.station_code === code)?.station_name ?? code ?? '—';
  const schedule = snapshot.timetable?.trains.find(row => row.id === train.train_id);
  const status = statusOf(train, snapshot);
  const running = train.status === 'RUNNING';
  const arrived = train.status === 'ARRIVED';
  const currentSection = train.current_section ?? schedule?.outgoing ?? train.next_section;
  const nextStop = train.next_station ?? schedule?.next_station ?? train.next_stop;
  const route = train.route_stations ?? schedule?.stops.map(stop => stop.station) ?? [train.entry_station, train.exit_station].filter((code): code is string => !!code);
  const decision = feed.find(item => item.policy === policy && item.recommendation.train_id === selected);
  const recommendation = decision?.recommendation;
  const platform = snapshot.yard?.platforms.find(row => row.train_id === selected);
  const movements = events.filter(event => event.train_id === selected && ['SECTION_ENTERED', 'SECTION_COMPLETED'].includes(event.event));
  const progress = Math.round(train.progress * 100);
  const probability = recommendation?.ml_action ? recommendation.probabilities?.[recommendation.ml_action] : undefined;
  const readyAt = Math.max(train.entry_time_min, train.ready_time_min ?? 0);

  return <aside className="corridor-page corridor-inspector corridor-panel" aria-labelledby="network-train-heading">
    <label className="network-service-picker">Inspect train<select value={train.train_id} onChange={event => focusTrain(event.target.value)}>
      {snapshot.trains.map(row => <option key={row.train_id} value={row.train_id}>{row.train_id} · {row.train_name}</option>)}
    </select></label>
    <div className="corridor-card-heading"><span className="corridor-label">{train.train_number ? `Service ${train.train_number} · ` : ''}{train.train_id}</span><span className={`corridor-tag ${running ? 'running' : arrived ? '' : 'queued'}`}>{status}</span></div>
    <h2 id="network-train-heading">{train.train_name}</h2>
    <p className="corridor-route">{train.train_type ?? 'Train'} · {train.entry_station} <ArrowRight size={14}/> {train.exit_station}</p>
    <dl className="corridor-train-stats">
      <div><dt>Location</dt><dd>{running ? train.current_section : stationName(train.current_station)}</dd></div>
      <div><dt>Next stop</dt><dd>{arrived ? 'Journey complete' : stationName(nextStop)}</dd></div>
      <div><dt>{running ? 'Current section' : 'Next section'}</dt><dd>{currentSection ?? '—'}</dd></div>
      <div><dt>{running ? 'Time to next stop' : 'Ready at'}</dt><dd>{running ? minutes(train.remaining_time_min) : arrived ? '—' : `${readyAt.toFixed(2)} sim min`}</dd></div>
      <div><dt>Speed</dt><dd>{train.speed ?? 0} km/h</dd></div>
      <div><dt>Speed limit (train)</dt><dd>{train.max_speed_kmph == null ? '—' : `${train.max_speed_kmph} km/h`}</dd></div>
      <div><dt>Dispatch waiting</dt><dd>{minutes(train.waiting_time_min)}</dd></div>
      <div><dt>Simulated delay</dt><dd>{minutes(schedule?.deviation_min ?? train.delay_min)}</dd></div>
      <div><dt>Priority</dt><dd>{train.priority ?? '—'}</dd></div>
      <div><dt>Length</dt><dd>{train.length_m == null ? '—' : `${train.length_m} m`}</dd></div>
      {platform&&<div><dt>Platform / signal</dt><dd>P{platform.platform} · {platform.aspect}</dd></div>}
    </dl>
    {running&&<label className="network-train-progress">Section progress <strong>{progress}%</strong><progress max={100} value={progress}/></label>}
    {(schedule?.reason || (!running && !arrived && platform?.reason))&&<p className="corridor-train-reason">{schedule?.reason ?? platform?.reason}</p>}
    {decision&&recommendation&&<section className="network-dispatch-note" aria-label="Latest dispatch decision">
      <span className="corridor-label">{policies[policy]} · {decision.time.toFixed(2)} sim min</span>
      <strong>{recommendation.ml_action ? `Model ${recommendation.ml_action} → ` : ''}{recommendation.executed_action ?? recommendation.final_action}</strong>
      {probability!==undefined&&<small>Model confidence {(probability * 100).toFixed(1)}%</small>}
      <p>{recommendation.execution_reason ?? recommendation.reason}</p>
    </section>}
    {!!route.length&&<section className="network-train-route"><h3>Route through the network</h3><ol>
      {route.map((code, index) => <li key={`${code}-${index}`} aria-current={code === train.current_station ? 'location' : undefined}>{code}</li>)}
    </ol></section>}
    {schedule&&<StopTimetable id={train.train_id} stops={schedule.stops}/>}
    {!schedule&&!!route.length&&<section className="network-train-route"><h3>Recorded stop times</h3>
      <div className="corridor-table-scroll"><table aria-label="Recorded arrivals and departures in simulation minutes">
        <thead><tr><th scope="col">Stop</th><th scope="col">Arrival (min)</th><th scope="col">Departure (min)</th></tr></thead>
        <tbody>{route.map((code,index)=><tr key={`${code}-${index}`}><th scope="row">{code}</th>
          <td>{movements.find(event=>event.event==='SECTION_COMPLETED'&&event.station_id===code)?.time_min.toFixed(2)??'—'}</td>
          <td>{movements.find(event=>event.event==='SECTION_ENTERED'&&event.from_station===code)?.time_min.toFixed(2)??'—'}</td>
        </tr>)}</tbody>
      </table></div>
    </section>}
  </aside>;
}

export function NetworkOperations({stationCode}: {stationCode: string | null}) {
  const {network, snapshot, sectionId, events, selected, focusTrain, setSectionId} = useControl();
  const section = network?.sections.find(row => row.section_id === sectionId);
  if (!network || !snapshot || !section) return null;
  const endpoints = [section.from_station, section.to_station];
  const completions = events.filter(event => event.event === 'SECTION_COMPLETED' && event.section_id === sectionId);
  const throughput = sectionThroughput(events, sectionId, 0, snapshot.time);
  const occupant = snapshot.occupancy[sectionId];
  const lastClear = completions.at(-1)?.time_min;
  const clearAt = snapshot.clearance_until?.[sectionId] ?? (lastClear === undefined ? 0 : lastClear + (section.minimum_headway_min ?? 0));
  const headway = Math.max(0, clearAt - snapshot.time);
  const status = occupant ? 'Occupied' : headway > 0 ? 'Headway' : 'Clear';
  const waitingAt = (code: string) => snapshot.trains.filter(train => train.current_station === code && train.status !== 'RUNNING' && train.status !== 'ARRIVED' && train.entry_time_min <= snapshot.time);
  const departures = (code: string) => events.filter(event => event.event === 'SECTION_ENTERED' && event.from_station === code).length;
  const outgoing = (train: NetworkTrain) => train.next_section ?? snapshot.timetable?.trains.find(row => row.id === train.train_id)?.outgoing ?? snapshot.yard?.platforms.find(platform => platform.train_id === train.train_id)?.section;
  const stationName = (code: string) => network.stations.find(station => station.station_code === code)?.station_name ?? code;
  const local = stationCode ?? (endpoints.includes(snapshot.station) ? snapshot.station : section.from_station);
  const stationQueue = waitingAt(local);
  const stationDepartures = departures(local);
  const stationRate = snapshot.time > 0 ? stationDepartures * 60 / snapshot.time : null;

  return <section className="corridor-page network-operations" aria-label="Section and station traffic">
    <section className="network-section-summary" aria-labelledby="network-section-title">
      <div className="network-section-lead"><span className="corridor-label">{sectionId} · {section.distance_km} km · {status}</span>
        <h3 id="network-section-title">{stationName(section.from_station)} <span>↔</span> {stationName(section.to_station)}</h3>
        <p>{occupant ? `Occupied by ${occupant}.` : headway > 0 ? `Next entry in ${headway.toFixed(2)} min.` : 'Clear for eligible traffic.'} {section.minimum_headway_min !== undefined && `${section.minimum_headway_min} min post-clearance headway.`}</p>
      </div>
      <div className="network-section-number"><strong>{throughput?.toFixed(2) ?? '—'}</strong><span>Section clears / hour</span><small>Over {snapshot.time.toFixed(1)} sim min</small></div>
      <div className="network-section-number"><strong>{completions.length}</strong><span>Completed section moves</span></div>
    </section>
    <div className="network-direction-queues" aria-label="Traffic by direction">
      {endpoints.map((from, index) => {
        const to = endpoints[1 - index];
        const queue = waitingAt(from).filter(train => outgoing(train) === sectionId);
        return <div key={from}><strong>{from} <ArrowRight size={13}/> {to}</strong><span>{queue.length} waiting · {completions.filter(event => event.station_id === to).length} cleared</span></div>;
      })}
    </div>
    <div className="corridor-workspace network-ops-body">
      <section className="corridor-panel" aria-labelledby="network-station-title">
        <div className="corridor-card-heading"><h3 id="network-station-title">{stationName(local)}</h3><span>{local} · Station traffic</span></div>
        <dl className="corridor-train-stats network-station-stats"><div><dt>Waiting at station</dt><dd>{stationQueue.length}</dd></div><div><dt>Departures / hour</dt><dd>{stationRate?.toFixed(2) ?? '—'}</dd></div></dl>
        <div className="corridor-queue">
          {network.sections.filter(leg => leg.from_station === local || leg.to_station === local).map(leg => {
            const queue = stationQueue.filter(train => outgoing(train) === leg.section_id);
            return <div className="corridor-queue-route" key={leg.section_id}>
              <button aria-pressed={sectionId === leg.section_id} onClick={() => setSectionId(leg.section_id)}>{leg.section_id} <ArrowRight size={12}/> {leg.from_station === local ? leg.to_station : leg.from_station}</button>
              <span>{queue.length} waiting</span>{queue.map(train => <button key={train.train_id} aria-pressed={selected === train.train_id} onClick={() => focusTrain(train.train_id)}>{train.train_id}</button>)}
            </div>;
          })}
        </div>
      </section>
      <section className="corridor-panel" aria-labelledby="network-board-title">
        <div className="corridor-card-heading"><h3 id="network-board-title">Service board</h3><span>{snapshot.trains.filter(train => train.status === 'RUNNING').length} running · {snapshot.trains.length} loaded</span></div>
        <div className="corridor-table-scroll"><table className="corridor-service-table">
          <thead><tr><th scope="col">Train</th><th scope="col">Status</th><th scope="col">Location</th></tr></thead>
          <tbody>{snapshot.trains.map(train => <tr key={train.train_id} className={train.train_id === selected ? 'is-selected' : ''}>
            <th scope="row"><button aria-pressed={train.train_id === selected} onClick={() => focusTrain(train.train_id)}><TrainFront size={14}/><span>{train.train_id}<small>{train.train_name}</small></span></button></th>
            <td>{statusOf(train, snapshot)}</td><td>{train.current_section ?? train.current_station}</td>
          </tr>)}</tbody>
        </table></div>
      </section>
    </div>
  </section>;
}
