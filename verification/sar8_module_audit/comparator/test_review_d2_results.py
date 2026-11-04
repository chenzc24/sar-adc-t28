"""Targeted checks for the native reset-ready measurement, no simulator."""
import unittest
from review_d2_results import ready90, RESET


class ResetMeasure(unittest.TestCase):
    def start(self):
        return dict({'time_s':1.,'vdd!':1.},**{n:.0 for n in RESET})

    def test_all_four_nodes_are_needed(self):
        edges=[dict(node=n,up=1,time_s=1.1+i*.1) for i,n in enumerate(RESET)]
        self.assertAlmostEqual(ready90(self.start(),2.,edges),1.4)
        self.assertIsNone(ready90(self.start(),2.,edges[:-1]))

    def test_late_dip_requires_recovery_and_does_not_use_first_entry(self):
        edges=[dict(node=n,up=1,time_s=1.1) for n in RESET]
        edges += [dict(node=RESET[0],up=0,time_s=1.5),dict(node=RESET[0],up=1,time_s=1.8)]
        self.assertEqual(ready90(self.start(),2.,edges),1.8)
        self.assertIsNone(ready90(self.start(),2.,edges[:-1]))

    def test_already_high_node_needs_no_artificial_rising_crossing(self):
        state=self.start();state[RESET[0]]=1.
        edges=[dict(node=n,up=1,time_s=1.2) for n in RESET[1:]]
        self.assertEqual(ready90(state,2.,edges),1.2)


if __name__=='__main__':unittest.main()
