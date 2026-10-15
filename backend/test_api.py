"""Small integration check against the real project, without starting HTTP."""
import unittest
from server import analysis, make_session, network, snapshot


class IntegrationTest(unittest.TestCase):
    def test_real_scenarios_and_movement(self):
        for kind in ['competition', 'conflict', 'occupied', 'delay_priority', 'random']:
            session = make_session(kind)
            state = snapshot(session)
            self.assertGreater(len(state['trains']), 0)
            self.assertGreater(state['time'], 0)
            for train in session['simulator'].trains.values():
                if train.status == 'RUNNING':
                    self.assertGreater(train.remaining_time_min, 0)
                    self.assertIn(train.current_section, network.sections)
            session['simulator'].advance_time(5)
            self.assertEqual(snapshot(session)['time'], state['time'] + 5)

    def test_ai_and_evaluation(self):
        session = make_session('competition')
        self.assertIsNone(session['model_error'])
        decision = session['controller'].make_decision(session['simulator'])
        self.assertIn('recommendations', decision)
        executed = session['controller'].control_step(session['simulator'])
        self.assertIn('execution', executed)
        results = analysis()
        self.assertGreater(results['scenarios'], 0)
        self.assertEqual(len(results['controllers']), 3)


if __name__ == '__main__':
    unittest.main()
