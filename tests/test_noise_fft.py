import importlib.util
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/saradc/measure'))
import noise_fft_reduce as measure


class NoiseFFTTests(unittest.TestCase):
    def test_known_harmonic_and_noise_budget(self):
        # Deliberately disjoint bins: integrated SNDR includes both the harmonic
        # and an unrelated spur; this catches incorrect one-sided scaling/masks.
        n,k=1024,461
        codes=[128+100*math.sin(2*math.pi*k*i/n)+math.sin(2*math.pi*2*k*i/n)+2*math.sin(2*math.pi*17*i/n) for i in range(n)]
        out=measure.spectrum(codes,k)
        self.assertAlmostEqual(out['sndr_db'],10*math.log10(10000/5),places=8)
        self.assertAlmostEqual(out['sfdr_db'],10*math.log10(10000/4),places=8)

    def test_missing_handshake_and_late_result_fail(self):
        row=[0,127,8,8,8,0,127,1,0,100e-9,0,0,0,29e-9]
        self.assertTrue(measure.protocol_valid(row))
        for index,value in [(2,7),(5,16),(6,126),(7,0),(13,61e-9)]:
            bad=list(row);bad[index]=value
            self.assertFalse(measure.protocol_valid(bad))


if __name__ == '__main__':
    unittest.main()
