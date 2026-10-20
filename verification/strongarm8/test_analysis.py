"""Small deterministic checks of thresholds, units, provenance and statistics."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"scripts/strongarm8"))
from analyze import cdf_fit, cross, interp
from run import base, config, dut_block, source


class BaselineChecks(unittest.TestCase):
    def test_current_eight_bit_units(self):
        cfg=config()
        self.assertEqual(cfg["resolution_bits"],8)
        self.assertAlmostEqual(cfg["targets"]["systematic_offset_abs_v"],cfg["span_v"]/256/4)
        self.assertAlmostEqual(cfg["targets"]["noise_rms_v"],cfg["span_v"]/256*.18)

    def test_dut_not_resized_or_rewired(self):
        original=dut_block(source())
        for vd in (-.0017578125,.0017578125):
            self.assertEqual(dut_block(base(vd,sup=.81,corner="ss",temp=-40,load=20e-15)),original)

    def test_linear_interpolation(self):
        self.assertAlmostEqual(interp([0.,1.,2.],[0.,2.,4.],1.5),3.)

    def test_crossing_respects_window(self):
        self.assertIsNone(cross([0.,1.,2.],[0.,0.,2.],1.,0.,1.4))
        self.assertAlmostEqual(cross([0.,1.,2.],[0.,0.,2.],1.,0.,1.6),1.5)

    def test_cdf_fit_recovers_known_distribution(self):
        import statistics
        norm=statistics.NormalDist();mu=.0002;sigma=.0008
        rows=[{"differential_v":x,"cycles":10000,"unresolved":0,
               "positive":round(10000*norm.cdf((x-mu)/sigma))}
              for x in (-.002,-.001,-.0005,0.,.0005,.001,.002)]
        got=cdf_fit(rows)
        self.assertLess(abs(got["threshold_v"]-mu),2e-6)
        self.assertLess(abs(got["sigma_v"]-sigma),2e-6)


if __name__=="__main__":unittest.main()
