"""Independent mathematical checks for transition and FFT analysis."""
import sys
import unittest
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts/sar8_r4_performance"))
from analyze import spectrum,static_metrics
from common import LSB,verify_source,blocks,base_deck,SOURCE


class Metrics(unittest.TestCase):
    def test_frozen_dut_identity(self):
        verify_source()
        self.assertEqual(blocks(base_deck()),blocks((SOURCE/"dut.scs").read_text()))

    def test_linear_transfer_and_missing_code_reporting(self):
        thresholds=[dict(k=k,lower_v=-.9+k*LSB-1e-6,upper_v=-.9+k*LSB+1e-6,status=0) for k in range(1,256)]
        r=static_metrics(thresholds,range(256))
        self.assertLess(r["inl_raw_abs_max_lsb"],1e-12)
        self.assertLess(abs(r["dnl_min_lsb"]),1e-12)
        self.assertTrue(r["ordered_disjoint_brackets"])
        self.assertEqual(r["unobserved_codes"],[])
        self.assertEqual(static_metrics(thresholds,range(255))["unobserved_codes"],[255])

    def test_fft_against_time_domain_projection(self):
        n=1024;k=461;t=np.arange(n)
        vin=.9*10**(-1/20)*np.sin(2*np.pi*k*t/n+.123)
        codes=np.clip(np.floor((vin+.9)/LSB),0,255)
        y=-.9+(codes+.5)*LSB;y-=y.mean()
        basis=np.column_stack((np.sin(2*np.pi*k*t/n),np.cos(2*np.pi*k*t/n)))
        fit=basis@np.linalg.lstsq(basis,y,rcond=None)[0]
        expected=10*np.log10(np.sum(fit**2)/np.sum((y-fit)**2))
        measured=spectrum(codes,k,toolbox=False)
        self.assertAlmostEqual(measured["sndr_db"],expected,places=8)
        self.assertGreater(measured["enob_sndr_bits"],7.6)
        self.assertLess(measured["enob_sndr_bits"],8.1)


if __name__=="__main__":unittest.main()
