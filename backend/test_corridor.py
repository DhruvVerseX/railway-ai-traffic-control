import unittest

from server import database, network
from corridor import HORIZON_MIN, PASSING_CAPACITY, corridor_snapshot, create_corridor


class CorridorTest(unittest.TestCase):
    def test_timetable_crossing_headway_and_reproducibility(self):
        coarse = create_corridor(network, database)
        fine = create_corridor(network, database)
        initial = corridor_snapshot(coarse)
        self.assertEqual(initial, corridor_snapshot(fine))
        self.assertEqual(initial['trains'][1]['stops'][0]['planned_departure'], 0)
        self.assertEqual(initial['trains'][1]['ready_at'], 8)
        self.assertIsNone(initial['trains'][1]['stops'][0]['actual_departure'])

        simultaneous_at_loop = False
        for _ in range(HORIZON_MIN):
            fine.advance(1)
            sim = fine.simulator
            self.assertLessEqual(sim.interlocking.slots_used(), PASSING_CAPACITY)
            at_loop = [train for train in sim.trains.values()
                       if train.current_station == 'AGRA' and train.status == 'WAITING']
            simultaneous_at_loop |= {train.direction for train in at_loop} == {'UP', 'DOWN'}
            if sim.current_time_min == 55:
                self.assertEqual(len(at_loop), 2)
        self.assertTrue(simultaneous_at_loop)
        for _ in range(HORIZON_MIN // 5):
            coarse.advance(5)
        result = corridor_snapshot(fine)
        self.assertEqual(result, corridor_snapshot(coarse))
        self.assertTrue(all(train['status'] == 'Arrived' for train in result['trains']))
        self.assertEqual(result['trains'][1]['stops'][0]['actual_departure'], 8)
        self.assertEqual(result['trains'][0]['stops'][1]['actual_departure'], 59)
        self.assertEqual(result['trains'][0]['deviation_min'], 8)
        for section in result['sections']:
            self.assertEqual(section['completed'], 6)
            self.assertEqual(section['throughput_per_hour'], round(360 / HORIZON_MIN, 2))
            clear_at = 0
            occupant = None
            for event in fine.simulator.history:
                if event['section_id'] != section['section_id']:
                    continue
                if event['event'] == 'SECTION_ENTERED':
                    self.assertIsNone(occupant)
                    self.assertGreaterEqual(event['time_min'], clear_at)
                    occupant = event['train_id']
                elif event['event'] == 'SECTION_COMPLETED':
                    self.assertEqual(event['train_id'], occupant)
                    occupant = None
                    clear_at = event['time_min'] + section['minimum_headway_min']
            self.assertIsNone(occupant)


if __name__ == '__main__':
    unittest.main()
