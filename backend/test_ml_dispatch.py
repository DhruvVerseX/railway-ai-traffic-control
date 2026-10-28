"""ML station integration: real predictions, safety overrides and executed evidence."""
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from unittest.mock import patch

import server
from interlocking import StationInterlocking
from station_dispatch import StationDispatcher, station_simulator


class MLDispatchTests(unittest.TestCase):
    def setUp(self):
        self.sim = station_simulator(server.network, server.database, count=6)
        self.yard = StationInterlocking(self.sim, 'MTJ')
        self.dispatcher = StationDispatcher(self.sim, server.database, 'MTJ', 'ml')
        self.dispatcher.set_policy('ml')

    def test_real_model_predictions_and_inputs_are_returned(self):
        decision = self.dispatcher.make_decision()
        self.assertEqual(decision['model_file'], 'train_controller_v2.pkl')
        self.assertTrue(decision['recommendations'])
        for rec in decision['recommendations']:
            prediction = self.dispatcher.ml_controller.predict(rec['features'])
            self.assertEqual(rec['ml_action'], prediction['action'])
            self.assertEqual(rec['probabilities'], prediction['probabilities'])
            self.assertEqual(rec['features']['waiting'], 1)
            self.assertNotIn('executed_action', rec)
        self.assertFalse(any(e['event'] == 'SECTION_ENTERED' for e in self.sim.history))

    def test_red_signal_overrides_model_release(self):
        tid = next(iter(self.yard.assignments))
        self.yard.set_signal(self.yard.assignments[tid], True)
        with patch.object(self.dispatcher.ml_controller, 'predict', return_value={
            'action': 'RELEASE', 'probabilities': {'HOLD': 0.1, 'RELEASE': 0.9}}):
            decision = self.dispatcher.control_step()
        rec = next(r for r in decision['recommendations'] if r['train_id'] == tid)
        self.assertEqual((rec['ml_action'], rec['final_action'], rec['executed_action']), ('RELEASE', 'HOLD', 'HOLD'))
        self.assertIn('red', rec['conflict_reason'])
        self.assertNotIn(tid, decision['execution']['released'])

    def test_execution_rechecks_shared_switch_and_records_actual_events(self):
        with patch.object(self.dispatcher.ml_controller, 'predict', return_value={
            'action': 'RELEASE', 'probabilities': {'HOLD': 0.1, 'RELEASE': 0.9}}):
            decision = self.dispatcher.control_step()
        self.assertEqual(len(decision['execution']['released']), 1)
        rejected = [r for r in decision['selected_actions'] if r['executed_action'] == 'HOLD']
        self.assertTrue(rejected)
        self.assertIn('exit switch', rejected[0]['execution_reason'])
        entered = [e['train_id'] for e in decision['execution']['events'] if e['event'] == 'SECTION_ENTERED']
        self.assertEqual(entered, decision['execution']['released'])
        self.assertEqual(decision['metrics_after']['departed'] - decision['metrics_before']['departed'], 1)

    def test_all_model_holds_release_best_safe_train_per_clear_section(self):
        with patch.object(self.dispatcher.ml_controller, 'predict', return_value={
            'action': 'HOLD', 'probabilities': {'HOLD': 0.9, 'RELEASE': 0.1}}):
            decision = self.dispatcher.control_step()
        self.assertEqual(len(decision['execution']['released']), 1)
        selected = decision['selected_actions']
        self.assertEqual(len({r['next_section'] for r in selected}), len(selected))
        for rec in selected:
            self.assertEqual(rec['ml_action'], 'HOLD')
            self.assertTrue(all(c['passed'] for c in rec['checks'] if c['name'] != 'Execution recheck'))
            self.assertIn('dispatch override', rec['reason'])
        released = next(r for r in selected if r['executed_action'] == 'RELEASE')
        self.assertIn('dispatch override', released['execution_reason'])

    def test_occupied_section_does_not_block_other_clear_section(self):
        first = next(iter(self.yard.assignments))
        self.assertTrue(self.sim.start_train(first))
        occupied = self.sim.trains[first].current_section
        self.sim.advance_time(1)
        with patch.object(self.dispatcher.ml_controller, 'predict', return_value={
            'action': 'HOLD', 'probabilities': {'HOLD': 0.9, 'RELEASE': 0.1}}):
            decision = self.dispatcher.control_step()
        blocked = [r for r in decision['recommendations'] if r['next_section'] == occupied]
        self.assertTrue(blocked)
        self.assertTrue(all(r['final_action'] == 'HOLD' for r in blocked))
        self.assertEqual(len(decision['execution']['released']), 1)
        self.assertNotEqual(self.sim.trains[decision['execution']['released'][0]].current_section, occupied)

    def test_clear_track_override_uses_highest_model_probability(self):
        def predict(features):
            release = features['max_speed_kmph'] / 1000
            return {'action': 'HOLD', 'probabilities': {'HOLD': 1 - release, 'RELEASE': release}}
        with patch.object(self.dispatcher.ml_controller, 'predict', side_effect=predict):
            decision = self.dispatcher.make_decision()
        for selected in decision['selected_actions']:
            eligible = [r for r in decision['recommendations'] if r['safe'] and r['next_section'] == selected['next_section']]
            self.assertEqual(selected['probabilities']['RELEASE'], max(r['probabilities']['RELEASE'] for r in eligible))

    def test_model_release_is_preferred_over_hold_on_same_section(self):
        tid = next(iter(self.yard.assignments))
        speed = float(server.database.get_train(tid)['max_speed_kmph'])
        def predict(features):
            release = .8 if features['max_speed_kmph'] == speed else .2
            return {'action': 'RELEASE' if release > .5 else 'HOLD',
                    'probabilities': {'HOLD': 1 - release, 'RELEASE': release}}
        with patch.object(self.dispatcher.ml_controller, 'predict', side_effect=predict):
            decision = self.dispatcher.make_decision()
        for selected in decision['selected_actions']:
            peers = [r for r in decision['recommendations'] if r['safe'] and r['next_section'] == selected['next_section']]
            if any(r['ml_action'] == 'RELEASE' for r in peers):
                self.assertEqual(selected['ml_action'], 'RELEASE')

    def test_clear_track_override_respects_red_signals(self):
        for platform in range(1, 5):
            self.yard.set_signal(platform, True)
        with patch.object(self.dispatcher.ml_controller, 'predict', return_value={
            'action': 'HOLD', 'probabilities': {'HOLD': 0.9, 'RELEASE': 0.1}}):
            decision = self.dispatcher.control_step()
        self.assertEqual(decision['execution']['released'], [])
        self.assertTrue(all(r['final_action'] == 'HOLD' for r in decision['recommendations']))

    def test_seed_42_queue_keeps_dispatching_after_first_section_clears(self):
        sim = station_simulator(server.network, server.database, count=12, seed=42)
        StationInterlocking(sim, 'MTJ')
        dispatcher = StationDispatcher(sim, server.database, 'MTJ', 'ml')
        dispatcher.advance(28)
        departures = [e for e in sim.history if e['event'] == 'SECTION_ENTERED' and e.get('from_station') == 'MTJ']
        self.assertGreater(len(departures), 2)
        self.assertTrue(any(e['time_min'] > 15 for e in departures))

    def test_ready_approaching_train_is_encoded_as_waiting(self):
        train = next(t for t in self.sim.trains.values() if t.status == 'APPROACHING')
        self.sim.advance_time(train.entry_time_min)
        features = self.dispatcher.ml_controller.extract_features(self.sim, train.train_id)
        self.assertEqual(features['waiting'], 1)
        train.ready_time_min = self.sim.current_time_min + 10
        self.assertEqual(self.dispatcher.ml_controller.extract_features(self.sim, train.train_id)['waiting'], 0)

    def test_playback_preserves_earlier_dispatch_evidence(self):
        with patch.object(self.dispatcher.ml_controller, 'predict', return_value={
            'action': 'RELEASE', 'probabilities': {'HOLD': 0.1, 'RELEASE': 0.9}}):
            decision = self.dispatcher.advance(1)
        steps = [*decision['steps'], decision]
        self.assertTrue(any(step['execution']['executed'] for step in steps))
        json.dumps(decision)

    def test_missing_model_fails_without_changing_policy(self):
        dispatcher = StationDispatcher(self.sim, server.database, 'MTJ')
        with patch('station_dispatch.load_station_model', side_effect=FileNotFoundError('missing')):
            with self.assertRaisesRegex(RuntimeError, 'V2 model unavailable'):
                dispatcher.set_policy('ml')
        self.assertEqual(dispatcher.policy, 'throughput')

    def test_http_returns_real_ml_decision_and_request_receipt(self):
        httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        created = None
        try:
            base = f'http://127.0.0.1:{httpd.server_port}'
            def post(path, body):
                request = Request(base + path, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
                with urlopen(request, timeout=30) as response:
                    return json.load(response)
            created = post('/scenario', {'count': 6, 'policy': 'ml'})
            result = post('/execute', {'session': created['session']})
            self.assertEqual(result['backend']['path'], '/execute')
            self.assertNotEqual(result['backend']['request_id'], created['backend']['request_id'])
            self.assertEqual(result['decision']['controller'], 'Random Forest V2')
            self.assertEqual(result['policy'], 'ml')
            self.assertTrue(result['decision']['recommendations'])
            self.assertIn('events', result['decision']['execution'])
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join()
            if created:
                server.sessions.pop(created['session'], None)


if __name__ == '__main__':
    unittest.main()
