'use client';

import './corridor.css';

export type Stop = {
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

export function StopTimetable({id, stops}: {id: string; stops: Stop[]}) {
  return <>
    <h3>Stop timetable</h3>
    <div className="corridor-table-scroll"><table className="corridor-timetable" aria-label={`${id} planned and actual timetable`}>
      <thead><tr><th scope="col">Stop</th><th scope="col">Movement</th><th scope="col">Planned</th><th scope="col">Actual</th><th scope="col">Δ</th></tr></thead>
      {stops.map(stop => {
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
  </>;
}

export type CorridorControl = {
  state: Corridor;
  sectionId: string;
  setSectionId: (id: string) => void;
};

