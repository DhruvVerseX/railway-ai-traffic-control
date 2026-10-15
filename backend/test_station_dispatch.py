"""Regression checks for movement, safe station dispatch, and fair comparisons."""
import unittest
import server
from input.input_state import TrafficState, TrainState
from simulation.simulator import RailwaySimulator
from simulation.conflict_detector import ConflictDetector
from station_dispatch import StationDispatcher, station_simulator, station_metrics, compare_station


class StationTests(unittest.TestCase):
    def test_blocked_train_resumes_next_section_at_correct_station(self):
        sim = RailwaySimulator(server.network)
        sim.load_traffic(TrafficState(trains=[TrainState(train_id='T024', location='NDLS', direction='UP', status='WAITING')]), server.database)
        detector = ConflictDetector(sim)
        self.assertTrue(sim.start_train('T024'))
        sim.add_train('blocker', 'Blocking train', 'UP', entry_time_min=1000)
        sim.section_occupancy['S02'] = 'blocker'
        sim.advance_time(6)
        train = sim.get_train_state('T024')
        self.assertEqual((train.current_station, train.section_index, train.status), ('NZM', 1, 'WAITING'))
        del sim.section_occupancy['S02']
        self.assertTrue(sim.start_train('T024'))
        self.assertEqual((train.current_section, train.current_station, train.next_station), ('S02', 'NZM', 'PWL'))
        self.assertIn('S01', detector.last_exit_time)

    def test_start_train_enforces_headway_even_without_controller(self):
        sim = station_simulator(server.network, server.database, count=12)
        dispatcher = StationDispatcher(sim, server.database, 'MTJ')
        decision = dispatcher.control_step()
        first = decision['selected_actions'][0]
        train = sim.trains[first['train_id']]
        sid = train.current_section
        sim.advance_time(train.remaining_time_min)
        candidate = next(t for t in sim.trains.values() if t.status in {'WAITING', 'APPROACHING'}
                         and sim.movement_model.build_movement(t.train_id).section_sequence[t.section_index] == sid)
        self.assertFalse(sim.start_train(candidate.train_id))
        self.assertNotEqual(candidate.current_section, sid)

    def test_automatic_dispatch_preserves_routes_occupancy_and_headway(self):
        sim = station_simulator(server.network, server.database, count=12)
        dispatcher = StationDispatcher(sim, server.database, 'MTJ')
        for _ in range(180):
            dispatcher.advance(1)
            running = [t for t in sim.trains.values() if t.status == 'RUNNING']
            self.assertEqual(len({t.current_section for t in running}), len(running))
            self.assertEqual(len(sim.section_occupancy), len(running))
            for train in running:
                movement = sim.movement_model.build_movement(train.train_id)
                self.assertEqual(train.current_section, movement.section_sequence[train.section_index])
                self.assertGreater(train.remaining_time_min, 0)
        exits, active, entered = {}, {}, {}
        for event in sim.history:
            sid, tid = event.get('section_id'), event.get('train_id')
            if event['event'] == 'SECTION_ENTERED':
                self.assertNotIn(sid, active)
                if sid in exits:
                    self.assertGreaterEqual(event['time_min'] - exits[sid] + .011, server.network.get_section(sid).minimum_headway_min)
                active[sid] = tid
                entered.setdefault(tid, []).append(sid)
            elif event['event'] == 'SECTION_COMPLETED':
                self.assertEqual(active.pop(sid), tid)
                exits[sid] = event['time_min']
        for tid, sections in entered.items():
            self.assertEqual(len(sections), len(set(sections)), f'{tid} repeats a section')
        self.assertGreater(station_metrics(sim, 'MTJ')['departed'], 0)
        self.assertTrue(any(t.waiting_time_min > 0 for t in sim.trains.values()))

    def test_two_free_sections_can_be_released_together(self):
        sim = station_simulator(server.network, server.database, count=12)
        result = StationDispatcher(sim, server.database, 'MTJ').control_step()
        self.assertEqual(len(result['execution']['released']), 2)

    def test_comparison_is_deterministic_and_uses_identical_queue(self):
        first = compare_station(server.network, server.database, count=12)
        self.assertEqual(first, compare_station(server.network, server.database, count=12))
        a, b = first['controllers']
        self.assertEqual([(t['train_id'], t['ready']) for t in a['timeline']], [(t['train_id'], t['ready']) for t in b['timeline']])
        for result in first['controllers']:
            self.assertEqual(len(result['series']), 25)
            self.assertEqual(result['throughput_per_hour'], result['departed'] / 2)
            self.assertEqual(result['series'][-1]['departed'], result['departed'])
            departures = [s['departed'] for s in result['series']]
            self.assertEqual(departures, sorted(departures))
        # Both controllers must obey the same shared exit-switch clearance.
        for result in first['controllers']:
            times = sorted(t['departure'] for t in result['timeline'] if t['departure'] is not None)
            self.assertTrue(all(y - x >= 1 - 1e-8 for x, y in zip(times, times[1:])))

    def test_waiting_train_gets_aging_priority(self):
        sim = station_simulator(server.network, server.database, count=12)
        slow = sim.trains['T030']
        slow.entry_time_min = 0
        slow.waiting_time_min = 46
        slow.status = 'WAITING'
        decision = StationDispatcher(sim, server.database, 'MTJ').make_decision()
        recommendation = next(c for c in decision['recommendations'] if c['train_id'] == 'T030')
        self.assertEqual(recommendation['final_action'], 'RELEASE')

    def test_supported_stations_and_waiting_metrics(self):
        for station in ['MTJ', 'PWL', 'NZM']:
            sim = station_simulator(server.network, server.database, station, 12)
            dispatcher = StationDispatcher(sim, server.database, station)
            dispatcher.advance(20)
            metrics = station_metrics(sim, station)
            self.assertGreater(metrics['departed'], 0)
            self.assertGreaterEqual(metrics['waiting_min'], 0)
            self.assertEqual(sim.current_time_min, 20)


if __name__ == '__main__':
    unittest.main()
