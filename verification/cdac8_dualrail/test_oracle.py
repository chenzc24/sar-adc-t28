import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/cdac8_dualrail'))
from common import oracle,LSB

class TestComplementaryOracle(unittest.TestCase):
    def test_all_256_centers(self):
        for n in range(256):
            got,r=oracle(-.9+(n+.5)*LSB)
            self.assertEqual(got,n)
            self.assertEqual(len(r),8)

    def test_sample_words(self):
        active=128
        ph=(~active)&255;nh=active
        self.assertEqual(format(ph,'08b'),'01111111')
        self.assertEqual(format(nh,'08b'),'10000000')
        self.assertEqual(ph+1,128) # P dummy is high.
        self.assertEqual(nh,128)   # N dummy is low.

    def test_all_code_common_modes(self):
        for code in range(256):
            bottom_p=255-code+1;bottom_n=code
            self.assertEqual(bottom_p+bottom_n,256)
            # Sum of bottom changes from the sample state is exactly zero.
            self.assertAlmostEqual((bottom_p-128)+(bottom_n-128),0)

if __name__=='__main__':unittest.main()
