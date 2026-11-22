'use client';

import {ArrowLeft, ArrowRight} from 'lucide-react';
import TrainConsist from '../train-consist';
import {delayColor} from '../station-state';
import type {Corridor} from './corridor-view';
import {useControl} from './control-store';
import './station-scenario.css';

export default function StationScenario({timetable}: {timetable: Corridor}) {
  const {selected, sectionId, setSectionId, focusTrain, layers} = useControl();
  const {stations, sections, trains, time} = timetable;
  const passengerStations = stations.filter(station=>!station.operational_only);
  const stationPosition = new Map(stations.map((station, index) => [station.code, 13 + 74 * index / Math.max(1, stations.length - 1)]));
  const position = (code: string) => stationPosition.get(code) ?? 13;
  const visible = trains.filter(train => train.status !== 'Arrived' && (train.stops[0]?.planned_departure ?? 0) <= time);
  const direction = (train: Corridor['trains'][number]) => position(train.destination) > position(train.origin);

  return <section className="station-scenario" aria-label="Scenario station and track layout">
    <header className="station-scenario-header">
      <div><span className="control-kicker">{passengerStations.length} stations · {sections.length} single-track {sections.length === 1 ? 'block' : 'blocks'}</span>
        <h2>{passengerStations.map(station => station.code).join(' ↔ ')}</h2></div>
      <span>{trains.filter(train => train.status === 'Running').length} running · {trains.filter(train => train.status === 'Arrived').length}/{trains.length} journeys complete</span>
    </header>
    <div className="station-scenario-diagram">
      {stations.map(station => <div className="station-scenario-node" key={station.code} style={{left: `${position(station.code)}%`}}>
        {layers.names&&<div className={`station-scenario-building${station.operational_only?' operational-only':''}`}><b>{station.operational_only?station.name:station.code}</b>{!station.operational_only&&<span>{station.name}</span>}</div>}
        <span className="station-scenario-node-point" aria-hidden="true"/>
        {station.passing_capacity&&<div className="station-scenario-loop" aria-hidden="true"/>}
        {station.passing_capacity&&layers.names&&<small className="station-scenario-loop-note">{timetable.passing_slots_used}/{station.passing_capacity} tracks in use or reserved</small>}
      </div>)}
      {sections.map(block => {
        const left = Math.min(position(block.from_station), position(block.to_station));
        const right = Math.max(position(block.from_station), position(block.to_station));
        const status = block.occupant ? 'occupied' : block.clearance_min > 0 ? 'headway' : 'clear';
        return <div className="station-scenario-block" key={block.section_id} style={{left: `${left}%`, width: `${right-left}%`}}>
          <span aria-hidden="true" className={`station-scenario-track ${layers.occupancy ? status : 'clear'}`}/>
          <button className="station-scenario-section" aria-pressed={sectionId===block.section_id} onClick={()=>setSectionId(block.section_id)}>
            {block.section_id}<span>{block.occupant ? `Occupied · ${block.occupant}` : block.clearance_min > 0 ? `Headway · ${block.clearance_min.toFixed(1)} min` : 'Clear'}</span>
          </button>
        </div>;
      })}
      {layers.trains&&visible.map(train=>{
        const moving = train.status === 'Running';
        const origin = position(train.station);
        const destination = train.next_station ? position(train.next_station) : origin;
        const progress = Math.max(0,Math.min(1,train.progress));
        const x = moving ? origin + (destination-origin) * progress : origin;
        const isPassing = stations.some(station=>station.code===train.station&&!!station.passing_capacity);
        const terminalQueue = visible.filter(service=>service.station===train.station&&service.status!=='Running');
        const top = moving ? 143 : isPassing ? (direction(train) ? 176 : 222) : 215 + terminalQueue.indexOf(train) * 46;
        const rightbound = direction(train);
        const Arrow = rightbound ? ArrowRight : ArrowLeft;
        const color = delayColor(Math.max(0, train.deviation_min ?? train.waiting_min));
        return <button key={train.id} className={`station-scenario-train${moving?' moving':''}`} style={{left:`${x}%`,top}} aria-pressed={selected===train.id}
          aria-label={`Inspect ${train.id}, ${train.name}, ${train.status}`} onClick={()=>focusTrain(train.id)} title={`${train.name} · ${train.reason}`}>
          <span className="station-scenario-train-label">{!rightbound&&<Arrow size={12}/>} {train.id} {rightbound&&<Arrow size={12}/>}</span>
          <svg className={rightbound?'':'westbound'} viewBox="-146 -26 244 52" aria-hidden="true" focusable="false">
            <TrainConsist color={color} type={train.type} selected={selected===train.id}/>
          </svg>
        </button>;
      })}
    </div>
    <div className="station-scenario-sections" aria-label="Section throughput">
      {sections.map(block=><button key={block.section_id} aria-pressed={sectionId===block.section_id} onClick={()=>setSectionId(block.section_id)}>
        <span>{block.section_id} · {block.from_station} ↔ {block.to_station}</span><strong>{time>0?block.throughput_per_hour.toFixed(2):'—'} clears/hour</strong>
        <small>{block.completed} cleared · {block.minimum_headway_min} min headway after exit</small>
      </button>)}
    </div>
    <div className="station-scenario-services" aria-label="Scenario services">
      {trains.map(train=>{
        const Arrow = direction(train) ? ArrowRight : ArrowLeft;
        return <button aria-pressed={selected===train.id} key={train.id} onClick={()=>focusTrain(train.id)}>
          <Arrow size={15}/><span><strong>{train.id} · {train.name}</strong><small>{train.status} · {train.section ?? train.station}</small></span>
        </button>;
      })}
    </div>
  </section>;
}
