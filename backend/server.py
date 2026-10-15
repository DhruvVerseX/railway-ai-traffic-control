"""Local API adapter for the existing railway simulator. Run from the project root."""
import csv
import json
import sys
import uuid
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'backend/vendor'))
from simulation.network import RailwayNetwork
from simulation.simulator import RailwaySimulator
from input.input_state import TrainDatabase
from scenarios.mixed_scenario_builder import MixedScenarioBuilder
from station_dispatch import StationDispatcher, station_simulator, station_metrics, compare_station
from interlocking import StationInterlocking

network = RailwayNetwork()
database = TrainDatabase()
sessions = {}
state_lock = Lock()


class VisualScenarioBuilder(MixedScenarioBuilder):
    def _simulator_to_traffic_state(self, simulator):
        # Preserve clock and remaining section times lost by TrafficState export.
        self.simulator = simulator
        return super()._simulator_to_traffic_state(simulator)


def make_session(kind='competition', count=6, seed=42):
    builder = VisualScenarioBuilder(network, database)
    builder.generate_mixed_scenario(
        scenario_id='UI', num_trains=count, scenario_type=kind,
        decision_time_min=5.0, running_advance_min=5.0, seed=seed)
    simulator = builder.simulator
    session = {'simulator': simulator, 'controller': None, 'decision': None, 'kind': kind}
    # Attach safety tracking before any subsequent train movement.
    try:
        from controller.ai_controller import AITrainTrafficController
        session['controller'] = AITrainTrafficController(network, database)
        session['controller'].ai_safety_controller._get_conflict_detector(simulator)
        session['model_error'] = None
    except Exception as error:
        session['model_error'] = str(error)
    return session


def snapshot(session):
    sim = session['simulator']
    trains = []
    for train in sim.trains.values():
        record = database.get_train(train.train_id)
        item = asdict(train)
        item.update({key: record.get(key) for key in ['train_type', 'priority', 'entry_station', 'exit_station', 'max_speed_kmph']})
        if 'station' in session:
            item['entry_station'] = session['station']
        section = network.sections.get(train.current_section)
        item['speed'] = min(float(record['max_speed_kmph']), section.normal_speed_kmph) if section and train.status == 'RUNNING' else 0
        item['progress'] = max(0, min(1, 1 - train.remaining_time_min / section.travel_time(float(record['max_speed_kmph'])))) if section else 0
        trains.append(item)
    station = session.get('station', 'MTJ')
    return {'time': sim.current_time_min, 'trains': trains, 'events': sim.history[-100:],
            'yard': sim.interlocking.snapshot() if hasattr(sim, 'interlocking') else None,
            'station': station, 'metrics': station_metrics(sim, station),
            'automatic': isinstance(session['controller'], StationDispatcher),
            'occupancy': sim.section_occupancy, 'decision': session['decision'],
            'model_error': session['model_error'], 'kind': session['kind']}


def analysis():
    path = ROOT / 'ml/results/controller_comparison_v2_v3.csv'
    with path.open(encoding='utf-8') as file:
        rows = list(csv.DictReader(file))
    return {'scenarios': len(rows), 'source': path.name, 'controllers': [
        {'name': label, 'throughput': sum(float(r[f'{key}_throughput']) for r in rows) / len(rows),
         'waiting': sum(float(r[f'{key}_waiting']) for r in rows) / len(rows),
         'conflicts': sum(float(r[f'{key}_conflicts']) for r in rows) / len(rows)}
        for key, label in [('baseline', 'Baseline'), ('v2', 'AI · V2'), ('v3', 'AI · V3')]]}


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(30)

    def respond(self, code, body):
        data = json.dumps(body, default=lambda value: value.item() if hasattr(value, 'item') else str(value)).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        try:
            if self.path == '/network':
                return self.respond(200, {'stations': [asdict(s) for s in network.stations.values()], 'sections': [asdict(s) for s in network.sections.values()]})
            if self.path == '/analysis':
                return self.respond(200, compare_station(network, database))
            if self.path.startswith('/state/'):
                key = self.path.split('/')[-1]
                if key not in sessions:
                    return self.respond(404, {'error': 'Session expired. Create a new scenario.'})
                return self.respond(200, snapshot(sessions[key]))
            self.respond(404, {'error': 'Unknown endpoint'})
        except Exception as error:
            self.respond(500, {'error': str(error)})

    def do_POST(self):
        # Scenario generation uses the project's shared random generator.
        with state_lock:
            self.handle_post()

    def handle_post(self):
        try:
            size = int(self.headers.get('Content-Length', 0))
            if size > 4096:
                return self.respond(413, {'error': 'Request too large'})
            body = json.loads(self.rfile.read(size) or b'{}')
            if not isinstance(body, dict):
                return self.respond(400, {'error': 'Expected a JSON object'})
            if self.path == '/compare':
                station, count, seed = body.get('station', 'MTJ'), body.get('count', 12), body.get('seed', 42)
                if station not in network.stations or type(count) is not int or not 2 <= count <= 20 or type(seed) is not int:
                    return self.respond(400, {'error': 'Choose a valid station and 2–20 trains.'})
                return self.respond(200, compare_station(network, database, station, count, seed))
            if self.path == '/scenario':
                kind, count, seed = body.get('kind', 'competition'), body.get('count', 6), body.get('seed', 42)
                if kind not in {'random', 'competition', 'occupied', 'conflict', 'delay_priority'} or type(count) is not int or not 2 <= count <= 20 or type(seed) is not int:
                    return self.respond(400, {'error': 'Choose a valid scenario and 2–20 trains.'})
                if len(sessions) >= 50:
                    sessions.pop(next(iter(sessions)))
                key = str(uuid.uuid4())
                station = body.get('station', 'MTJ')
                if station not in network.stations:
                    return self.respond(400, {'error': 'Unknown station'})
                sim = station_simulator(network, database, station, count, seed)
                StationInterlocking(sim, station)
                sessions[key] = {'simulator': sim, 'controller': StationDispatcher(sim, database, station),
                                 'decision': None, 'kind': 'station_queue', 'station': station, 'model_error': None}
                return self.respond(200, {'session': key, **snapshot(sessions[key])})
            session = sessions.get(body.get('session'))
            if session is None:
                return self.respond(404, {'error': 'Create a scenario first.'})
            sim = session['simulator']
            if self.path in {'/platform', '/signal'}:
                if self.path == '/platform':
                    sim.interlocking.change_platform(body.get('train_id'), body.get('platform'))
                else:
                    sim.interlocking.set_signal(body.get('platform'), body.get('stop'))
                session['decision'] = session['controller'].make_decision()
                return self.respond(200, snapshot(session))
            policy = body.get('policy', 'throughput')
            if policy not in {'throughput', 'fifo', 'manual'}:
                return self.respond(400, {'error': 'Unknown dispatch mode'})
            session['controller'].policy = 'fifo' if policy == 'fifo' else 'throughput'
            if self.path == '/advance':
                minutes = body.get('minutes', 1)
                if type(minutes) not in {int, float} or not 0 < minutes <= 5:
                    return self.respond(400, {'error': 'Advance must be between 0 and 5 minutes.'})
                if policy == 'manual':
                    sim.advance_time(minutes)
                    session['decision'] = session['controller'].make_decision()
                else:
                    session['decision'] = session['controller'].advance(minutes)
            elif self.path == '/release':
                train_id = body.get('train_id')
                if train_id not in sim.trains:
                    return self.respond(400, {'error': 'Select a train first.'})
                if not sim.start_train(train_id):
                    return self.respond(409, {'error': 'Train cannot move yet: check track occupancy, spacing, or readiness.'})
                session['decision'] = session['controller'].make_decision()
            elif self.path in {'/decide', '/execute'}:
                if session['controller'] is None:
                    return self.respond(503, {'error': 'AI model unavailable: ' + session['model_error']})
                session['decision'] = session['controller'].control_step(sim) if self.path == '/execute' else session['controller'].make_decision(sim)
            else:
                return self.respond(404, {'error': 'Unknown action'})
            self.respond(200, snapshot(session))
        except (ValueError, TypeError) as error:
            self.respond(400, {'error': str(error)})
        except Exception as error:
            self.respond(500, {'error': str(error)})


if __name__ == '__main__':
    print('Railway API listening on http://127.0.0.1:8000', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 8000), Handler).serve_forever()
