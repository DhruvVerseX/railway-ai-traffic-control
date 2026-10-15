"""Station dispatch using the existing movement and safety model."""
import copy
import random
from input.input_state import TrafficState, TrainState
from simulation.simulator import RailwaySimulator
from simulation.train_movement import TrainMovementModel
from simulation.conflict_detector import ConflictDetector


class StationDispatcher:
    def __init__(self, simulator, database, station, policy='throughput'):
        self.simulator, self.database, self.station, self.policy = simulator, database, station, policy
        self.detector = simulator._conflict_detector or ConflictDetector(simulator)

    def make_decision(self, simulator=None):
        sim = self.simulator
        candidates = []
        for train in sim.trains.values():
            if train.status not in {'WAITING', 'NOT_ENTERED', 'APPROACHING'}:
                continue
            if max(train.entry_time_min, train.ready_time_min) > sim.current_time_min + 1e-8:
                continue
            movement = sim.movement_model.build_movement(train.train_id)
            if train.section_index >= len(movement.section_sequence):
                continue
            sid = movement.section_sequence[train.section_index]
            section = sim.network.get_section(sid)
            duration = section.travel_time(float(self.database.get_train(train.train_id)['max_speed_kmph']))
            conflict = self.detector.check_section_conflict(train.train_id, sid)
            interlocking = getattr(sim, 'interlocking', None)
            station_block = interlocking.blocked_reason(train.train_id) if interlocking else None
            if station_block:
                conflict = {'conflict': True, 'reason': station_block, 'required_wait_min': 0}
            candidates.append({'train_id': train.train_id, 'next_section': sid,
                               'clearance_min': duration, 'waiting_min': train.waiting_time_min,
                               'ready': train.entry_time_min, 'safe': not conflict['conflict'],
                               'conflict_reason': conflict['reason'] if conflict['conflict'] else None,
                               'required_wait_min': conflict['required_wait_min'],
                               'at_station': train.current_station == self.station})
        if self.policy == 'fifo':
            candidates.sort(key=lambda c: (c['ready'], c['train_id']))
        else:
            # Shorter occupancy frees the constrained section sooner; aging prevents starvation.
            candidates.sort(key=lambda c: (0 if c['waiting_min'] >= 45 else 1,
                                           -c['waiting_min'] if c['waiting_min'] >= 45 else c['clearance_min'],
                                           c['ready'], c['train_id']))
        reserved = set()
        for candidate in candidates:
            if not candidate['safe']:
                candidate.update(final_action='HOLD', reason=candidate['conflict_reason'])
            elif candidate['next_section'] in reserved:
                candidate.update(final_action='HOLD', reason='Another train is selected for this track. It must clear first.')
            else:
                reserved.add(candidate['next_section'])
                reason = ('It has waited at least 45 minutes, so it gets the next safe turn.'
                          if self.policy != 'fifo' and candidate['waiting_min'] >= 45 else
                          f"It clears this section in {candidate['clearance_min']:.1f} minutes, making room for the next train sooner."
                          if self.policy != 'fifo' else 'First ready, first served on this available track.')
                candidate.update(final_action='RELEASE', reason=reason)
        releases = [c for c in candidates if c['final_action'] == 'RELEASE']
        return {'time_min': sim.current_time_min, 'recommendations': candidates,
                'selected_action': releases[0] if releases else None,
                'selected_actions': releases, 'policy': self.policy}

    def control_step(self, simulator=None):
        decision = self.make_decision()
        released = []
        for candidate in decision['selected_actions']:
            if self.simulator.start_train(candidate['train_id']):
                released.append(candidate['train_id'])
        decision['execution'] = {'executed': bool(released), 'released': released,
                                 'reason': f'{len(released)} trains dispatched safely.' if released else 'Waiting for a safe track opening.'}
        return decision

    def advance(self, minutes):
        sim = self.simulator
        target = sim.current_time_min + minutes
        last = self.control_step()
        while sim.current_time_min < target - 1e-8:
            times = [target]
            if getattr(sim, 'interlocking', None):
                times.append(sim.interlocking.throat_release_time())
            for train in sim.trains.values():
                if train.status == 'RUNNING':
                    times.append(sim.current_time_min + train.remaining_time_min)
                elif train.status != 'ARRIVED':
                    times.append(max(train.entry_time_min, train.ready_time_min))
            for sid, time in self.detector.last_exit_time.items():
                times.append(time + sim.network.get_section(sid).minimum_headway_min)
            future = [t for t in times if t > sim.current_time_min + 1e-8]
            sim.advance_time(min(future) - sim.current_time_min)
            last = self.control_step()
        return last


def station_simulator(network, database, station='MTJ', count=8, seed=42):
    if station not in network.stations:
        raise ValueError('Unknown station')
    movement = TrainMovementModel(network, database)
    eligible = []
    for tid, record in database.trains.items():
        cursor = record['entry_station']
        for sid in movement.build_movement(tid).section_sequence:
            if cursor == station:
                eligible.append(tid)
                break
            section = network.get_section(sid)
            cursor = section.to_station if cursor == section.from_station else section.from_station
    if not eligible:
        raise ValueError('This station has no outgoing train routes in the project data.')
    rng = random.Random(seed)
    rng.shuffle(eligible)
    traffic = TrafficState()
    for i, tid in enumerate(eligible[:count]):
        # The same seeded queue and arrival times are used by both policies.
        entry = 0.0 if i < 4 else float((i - 3) * 2)
        record = database.get_train(tid)
        route = network.get_route(record['route_id'])
        direction = 'UP' if route.station_sequence.index(record['entry_station']) < route.station_sequence.index(record['exit_station']) else 'DOWN'
        traffic.add_train(TrainState(train_id=tid, location=station, direction=direction,
                                     status='WAITING' if entry == 0 else 'APPROACHING', entry_time_min=entry))
    sim = RailwaySimulator(network)
    sim.load_traffic(traffic, database)
    sim.dispatch_at_stations = True
    ConflictDetector(sim)
    return sim


def station_metrics(sim, station):
    departures = [e for e in sim.history if e['event'] == 'SECTION_ENTERED' and e.get('from_station') == station]
    departed = {e['train_id'] for e in departures}
    cleared = {e['train_id'] for e in sim.history if e['event'] == 'SECTION_COMPLETED'
               and any(d['train_id'] == e['train_id'] and d['section_id'] == e['section_id'] for d in departures)}
    waiting = [t for t in sim.trains.values() if t.current_station == station and t.status != 'RUNNING' and t.status != 'ARRIVED'
               and t.entry_time_min <= sim.current_time_min + 1e-8]
    station_wait = 0.0
    for train in sim.trains.values():
        departure = next((e['time_min'] for e in departures if e['train_id'] == train.train_id), sim.current_time_min)
        station_wait += max(0.0, departure - train.entry_time_min)
    return {'departed': len(departed), 'cleared': len(cleared), 'queue': len(waiting),
            'throughput_per_hour': len(departed) * 60 / sim.current_time_min if sim.current_time_min else 0,
            'waiting_min': round(station_wait, 2),
            'average_wait_min': round(station_wait / len(sim.trains), 2) if sim.trains else 0}


def compare_station(network, database, station='MTJ', count=12, seed=42, horizon=120):
    initial = station_simulator(network, database, station, count, seed)
    from interlocking import StationInterlocking
    StationInterlocking(initial, station)
    results = []
    for policy, label in [('fifo', 'First come, first served'), ('throughput', 'Throughput dispatcher')]:
        sim = copy.deepcopy(initial)
        dispatcher = StationDispatcher(sim, database, station, policy)
        series = [{'minute': 0, **station_metrics(sim, station)}]
        for _ in range(horizon // 5):
            dispatcher.advance(5)
            series.append({'minute': round(sim.current_time_min, 2), **station_metrics(sim, station)})
        departures = [e for e in sim.history if e['event'] == 'SECTION_ENTERED' and e.get('from_station') == station]
        timeline = []
        for train in sim.trains.values():
            departure = next((e for e in departures if e['train_id'] == train.train_id), None)
            cleared = next((e['time_min'] for e in sim.history if departure and e['event'] == 'SECTION_COMPLETED'
                            and e['train_id'] == train.train_id and e['section_id'] == departure['section_id']), None)
            timeline.append({'train_id': train.train_id, 'name': train.train_name, 'ready': train.entry_time_min,
                             'departure': departure['time_min'] if departure else None, 'clearance': cleared})
        results.append({'policy': policy, 'name': label, **station_metrics(sim, station), 'series': series, 'timeline': timeline})
    return {'station': station, 'station_name': network.get_station(station).station_name,
            'horizon_min': horizon, 'train_count': len(initial.trains), 'seed': seed, 'controllers': results,
            'method': 'Identical initial trains, readiness times, track rules, and 120-minute window. Departures count trains leaving the selected station.',
            'limits': 'Heuristic scheduling, not a proven global optimum. Four simulated platforms, departure signals, a shared exit switch with one-minute clearance, and locked outgoing routes. One train per entire section; platforms remain reserved until that section clears. These are educational constraints, not a detailed model of the real station.'}
