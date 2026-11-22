"""Deterministic timetable and passing loop for the section-throughput demo."""
from copy import copy
from dataclasses import asdict, dataclass, replace

from input.input_state import TrafficState, TrainState
from simulation.network import Route, Station
from simulation.simulator import RailwaySimulator
from station_dispatch import StationDispatcher


STATIONS = ('MTJ', 'AGRA', 'BXN')
SECTIONS = ('S10', 'S12')
PASSING_STATION = 'AGRA'
MIDPOINT = 'LOOP'
PASSING_CAPACITY = 2
ROUTE_ID = 'CORRIDOR'
DWELL_MIN = 3
HORIZON_MIN = 340


@dataclass(frozen=True)
class Service:
    train_id: str
    name: str
    train_type: str
    stops: tuple[tuple[str, float | None, float | None], ...]
    priority: int = 2
    length_m: int = 250
    readiness_delay: int = 0


TIMETABLE_SCENARIOS = {
    'headway': ('Two trains via midpoint loop', (
        Service('C201', 'Mathura Express', 'Express', (('MTJ', None, 0), (MIDPOINT, 20.625, 26.625), ('AGRA', 47.25, None)), priority=4),
        Service('C202', 'Agra Freight', 'Freight', (('AGRA', None, 0), (MIDPOINT, 20.625, 26.625), ('MTJ', 47.25, None)), length_m=480),
    )),
    'passing': ('Opposing trains at Agra', (
        Service('C101', 'Mathura Intercity', 'Express', (('MTJ', None, 0), ('AGRA', 41.25, 51), ('BXN', 96, None))),
        Service('C102', 'Bayana Intercity', 'Express', (('BXN', None, 0), ('AGRA', 45, 48), ('MTJ', 89.25, None)), readiness_delay=8),
        Service('C103', 'Agra Link Passenger', 'Passenger', (('MTJ', None, 115), ('AGRA', 156.25, 166), ('BXN', 211, None))),
        Service('C104', 'Mathura Parcel', 'Parcel', (('BXN', None, 115), ('AGRA', 160, 163), ('MTJ', 204.25, None))),
        Service('C105', 'Bayana Freight', 'Freight', (('MTJ', None, 235), ('AGRA', 276.25, 286), ('BXN', 331, None)), length_m=480),
        Service('C106', 'Evening Passenger', 'Passenger', (('BXN', None, 235), ('AGRA', 280, 283), ('MTJ', 324.25, None))),
    )),
}


class CorridorSimulator(RailwaySimulator):
    def __init__(self, network, timetable, route, passing_station, replaced_section=None):
        super().__init__(network)
        self.timetable = timetable
        self.route = route
        self.passing_station = passing_station
        self.replaced_section = replaced_section
        self.model_section_groups = {replaced_section: route.section_sequence} if replaced_section else {}
        self.dispatch_at_stations = True

    def complete_current_section(self, train_id):
        result = super().complete_current_section(train_id)
        train = self.trains[train_id]
        if train.status == 'WAITING':
            departure = self.timetable[train_id][train.section_index]['planned_departure']
            train.ready_time_min = max(train.ready_time_min, departure)
        return result


class PassingLoop:
    def __init__(self, simulator):
        self.sim = simulator

    def slots_used(self):
        station = self.sim.passing_station
        return sum(train.next_station == station or
                   (train.current_station == station and train.status == 'WAITING')
                   for train in self.sim.trains.values())
    def slot_status(self, train_id):
        train = self.sim.trains[train_id]
        if train.next_station == self.sim.passing_station:
            return 'FREE'
        elif train.current_station == self.sim.passing_station and train.status == 'WAITING':
            return 'OCCUPIED'
        else:
            return 'BLOCKED'
            
    def blocked_reason(self, train_id):
        train = self.sim.trains[train_id]
        stops = self.sim.timetable[train_id]
        next_stop = train.section_index + 1
        if (next_stop < len(stops) and stops[next_stop]['station'] == self.sim.passing_station
                and self.slots_used() >= PASSING_CAPACITY):
            return 'Passing loop has no free receiving track.'
        return None

    def throat_release_time(self):
        # The passing loop has an independent connection to each adjacent block.
        return 0


def create_corridor(network, project_database, scenario='passing'):
    corridor_network = copy(network)
    passing_station = PASSING_STATION
    route_stations, route_sections = STATIONS, SECTIONS
    replaced_section = None
    if scenario == 'headway':
        replaced_section = 'S10'
        original = network.get_section(replaced_section)
        passing_station = MIDPOINT
        route_stations, route_sections = ('MTJ', MIDPOINT, 'AGRA'), ('S10W', 'S10E')
        corridor_network.stations = {**network.stations, MIDPOINT: Station(MIDPOINT, 'Midpoint loop', MIDPOINT, 'passing_loop')}
        corridor_network.sections = {sid: section for sid, section in network.sections.items() if sid != replaced_section}
        for sid, start, end in zip(route_sections, route_stations, route_stations[1:]):
            corridor_network.sections[sid] = replace(original, section_id=sid, from_station=start,
                                                     to_station=end, distance_km=original.distance_km / 2)
    route = Route(ROUTE_ID, 'Demonstration corridor', route_stations[0], route_stations[-1],
                  list(route_stations), list(route_sections), 'branch')
    corridor_network.routes = {**network.routes, ROUTE_ID: route}
    database = copy(project_database)
    database.trains = {}
    traffic = TrafficState()
    timetable = {}
    _, services = TIMETABLE_SCENARIOS[scenario]
    for service in services:
        origin, _, planned_start = service.stops[0]
        destination = service.stops[-1][0]
        timetable[service.train_id] = [
            {'station': station, 'planned_arrival': arrival, 'planned_departure': departure}
            for station, arrival, departure in service.stops
        ]
        database.trains[service.train_id] = {
            'train_id': service.train_id, 'train_name': service.name, 'train_type': service.train_type,
            'route_id': ROUTE_ID, 'entry_station': origin, 'exit_station': destination,
            'max_speed_kmph': 80, 'dwell_min': DWELL_MIN, 'stops_intermediate': True,
            'priority': service.priority, 'length_m': service.length_m,
        }
        direction = 'UP' if route_stations.index(origin) < route_stations.index(destination) else 'DOWN'
        traffic.add_train(TrainState(service.train_id, origin, direction, 'APPROACHING', entry_time_min=planned_start))

    sim = CorridorSimulator(corridor_network, timetable, route, passing_station, replaced_section)
    sim.load_traffic(traffic, database)
    for service in services:
        train = sim.trains[service.train_id]
        train.status = 'NOT_ENTERED'
        train.ready_time_min = train.entry_time_min + service.readiness_delay
    sim.interlocking = PassingLoop(sim)
    return StationDispatcher(sim, database, passing_station, policy='fifo')


def corridor_snapshot(dispatcher):
    sim = dispatcher.simulator
    section_ids = sim.route.section_sequence
    sections = []
    arrivals, departures = {}, {}
    completed = dict.fromkeys(section_ids, 0)
    for event in sim.history:
        train_id = event['train_id']
        if event['event'] == 'SECTION_ENTERED':
            departures[train_id, event['from_station']] = event['time_min']
        elif event['event'] == 'SECTION_COMPLETED':
            arrivals[train_id, event['station_id']] = event['time_min']
            completed[event['section_id']] += 1

    for section_id in section_ids:
        section = sim.network.get_section(section_id)
        clear_at = dispatcher.detector.last_exit_time.get(section_id, -section.minimum_headway_min) + section.minimum_headway_min
        sections.append({**asdict(section), 'occupant': sim.section_occupancy.get(section_id),
                         'clearance_min': round(max(0, clear_at - sim.current_time_min), 2),
                         'completed': completed[section_id],
                         'throughput_per_hour': round(60 * completed[section_id] / sim.current_time_min, 2) if sim.current_time_min else 0})

    trains = []
    for train in sim.trains.values():
        record = dispatcher.database.get_train(train.train_id)
        stops = [{**stop, 'actual_arrival': arrivals.get((train.train_id, stop['station'])),
                  'actual_departure': departures.get((train.train_id, stop['station']))}
                 for stop in sim.timetable[train.train_id]]
        current_stop = stops[train.section_index]
        section = next((row for row in sections if row['section_id'] == train.current_section), None)
        running = section is not None
        next_stop = stops[train.section_index + 1] if train.section_index + 1 < len(stops) else None
        outgoing = next((row for row in sections if next_stop and
                         {row['from_station'], row['to_station']} == {train.current_station, next_stop['station']}), None)
        ready_at = max(train.entry_time_min, train.ready_time_min)
        status, reason = 'Arrived', 'Journey complete.'
        if running:
            status, reason = 'Running', f"Occupying {section['section_id']} toward {train.next_station}."
        elif next_stop and sim.current_time_min + 1e-8 < ready_at:
            if train.section_index:
                status, reason = 'At passing loop', 'Holding for dwell or scheduled departure.'
            else:
                status = 'Scheduled'
                reason = 'Awaiting late origin readiness.' if ready_at > train.entry_time_min else 'Awaiting its scheduled start.'
        elif outgoing:
            status = 'Queued'
            if outgoing['occupant']:
                reason = f"{outgoing['section_id']} occupied by {outgoing['occupant']}."
            elif outgoing['clearance_min']:
                reason = f"{outgoing['section_id']} clearing its minimum headway."
            else:
                reason = sim.interlocking.blocked_reason(train.train_id) or 'Ready for dispatch.'

        observed = current_stop['actual_departure'] if running else current_stop['actual_arrival']
        planned = current_stop['planned_departure'] if running else current_stop['planned_arrival']
        deviation = round(observed - planned, 2) if observed is not None and planned is not None else None
        trains.append({'id': train.train_id, 'name': train.train_name, 'type': record['train_type'],
                       'origin': record['entry_station'], 'destination': record['exit_station'],
                       'station': train.current_station, 'section': train.current_section,
                       'outgoing': None if running or not outgoing else outgoing['section_id'],
                       'next_station': next_stop['station'] if next_stop else None,
                       'status': status, 'reason': reason, 'stops': stops, 'ready_at': ready_at,
                       'waiting_min': round(train.waiting_time_min, 2), 'deviation_min': deviation,
                       'remaining_min': round(train.remaining_time_min, 2),
                       'speed': min(record['max_speed_kmph'], section['normal_speed_kmph']) if running else 0,
                       'progress': 1 - train.remaining_time_min / sim.network.get_section(train.current_section).travel_time(record['max_speed_kmph']) if running else 0})

    return {'time': sim.current_time_min, 'horizon': HORIZON_MIN, 'trains': trains, 'sections': sections,
            'replaced_section': sim.replaced_section,
            'stations': [{'code': code, 'name': sim.network.stations[code].station_name,
                          'departed': sum(station == code for _, station in departures),
                          'passing_capacity': PASSING_CAPACITY if code == sim.passing_station else None,
                          'operational_only': sim.network.stations[code].station_type == 'passing_loop'}
                         for code in sim.route.station_sequence],
            'passing_slots_used': sim.interlocking.slots_used(),
            'events': [event for event in sim.history if event['event'] in {'SECTION_ENTERED', 'SECTION_COMPLETED'}][-8:]}
