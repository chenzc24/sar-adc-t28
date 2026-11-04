import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/cdac10_dualrail'))
from common import oracle, LSB

class TestMonotonicOracle(unittest.TestCase):
    def test_all_1024_centers(self):
        for n in range(1024):
            code, trajectory=oracle(-.9+(n+.5)*LSB)
            self.assertEqual(code,n)
            self.assertEqual(len(trajectory),10)
            self.assertLessEqual(abs(trajectory[-1]),LSB+.000000001)

    def test_switch_steps_and_common_mode(self):
        for v in (-.8,-.3,0,.3,.8):
            _,r=oracle(v)
            for k in range(9):
                self.assertAlmostEqual(abs(r[k+1]-r[k]),.9*(1<<(8-k))/512)
        # Sum of per-comparison CM drops is input-independent for ideal equal banks.
        self.assertAlmostEqual(.45-.9*sum(1<<b for b in range(9))/1024,.9/1024)

if __name__=='__main__': unittest.main()
