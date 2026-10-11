import unittest
import server
from station_dispatch import station_simulator, StationDispatcher
from interlocking import StationInterlocking

class InterlockingTests(unittest.TestCase):
    def setUp(self):
        self.sim=station_simulator(server.network,server.database,count=12)
        self.yard=StationInterlocking(self.sim,'MTJ')
        self.controller=StationDispatcher(self.sim,server.database,'MTJ')

    def test_red_signal_blocks_dispatch(self):
        tid=next(iter(self.yard.assignments))
        platform=self.yard.assignments[tid]
        self.yard.set_signal(platform,True)
        self.assertFalse(self.sim.start_train(tid))
        self.assertEqual(self.yard.snapshot()['platforms'][platform-1]['aspect'],'RED')
        self.yard.set_signal(platform,False)
        self.assertTrue(self.sim.start_train(tid))
        self.assertTrue(self.yard.snapshot()['platforms'][platform-1]['locked'])
        with self.assertRaises(ValueError):self.yard.set_signal(platform,True)
        with self.assertRaises(ValueError):self.yard.change_platform(tid,4)

    def test_occupied_platform_rejects_change(self):
        tid=next(iter(self.yard.assignments))
        other=next(p for t,p in self.yard.assignments.items() if t!=tid)
        with self.assertRaises(ValueError):self.yard.change_platform(tid,other)

    def test_shared_exit_switch(self):
        first, second = list(self.yard.assignments)[:2]
        self.assertTrue(self.sim.start_train(first))
        self.assertIn('exit switch', self.yard.blocked_reason(second))
        self.assertFalse(self.sim.start_train(second))
        self.sim.advance_time(1)
        self.assertIsNone(self.yard.blocked_reason(second))

    def test_outside_queue_and_platform_clearance(self):
        self.assertEqual(len(self.yard.assignments),4)
        self.assertEqual(len(self.yard.snapshot()['outside']),8)
        first=next(iter(self.yard.assignments))
        self.assertTrue(self.sim.start_train(first))
        self.sim.advance_time(self.sim.trains[first].remaining_time_min)
        self.yard.sync()
        self.assertNotIn(first,self.yard.assignments)
        self.assertEqual(len(set(self.yard.assignments.values())),len(self.yard.assignments))

    def test_free_platform_change(self):
        # Two trains provide genuinely free platform routes.
        sim=station_simulator(server.network,server.database,count=2)
        yard=StationInterlocking(sim,'MTJ')
        tid=next(iter(yard.assignments))
        yard.change_platform(tid,4)
        self.assertEqual(yard.assignments[tid],4)
        self.assertTrue(sim.start_train(tid))

if __name__=='__main__':unittest.main()
