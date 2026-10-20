"""Measurement math and exact saved-DUT identity; no fabricated native result."""
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts/integration"))
import r3_performance as run
from r3_performance_analyze import static_metrics,spectrum_metrics


class PerformanceMath(unittest.TestCase):
    def test_known_transition_widths_and_offset(self):
        offset=.1*run.LSB
        data=[dict(k=k,lower_v=-.9+k*run.LSB+offset-1e-8,
                   upper_v=-.9+k*run.LSB+offset+1e-8) for k in range(1,256)]
        m=static_metrics(data)
        self.assertLess(abs(m["dnl_min_lsb"]),1e-12)
        self.assertLess(abs(m["dnl_max_lsb"]),1e-12)
        self.assertAlmostEqual(m["inl_raw_abs_max_lsb"],.1,places=12)
        self.assertLess(m["inl_endpoint_abs_max_lsb"],1e-12)
        self.assertEqual(m["saturated_endpoint_code_widths_excluded"],[0,255])

    def test_ideal_quantized_sine_and_toolbox(self):
        n=1024;k=461;v=.9*10**(-1/20)*np.sin(2*np.pi*k*np.arange(n)/n+.137)
        code=np.clip(np.floor((v+.9)/run.LSB),0,255).astype(int)
        m=spectrum_metrics(code,k)
        self.assertTrue(47<m["sndr_db"]<51)
        self.assertAlmostEqual(m["enob_sndr_bits"],(m["sndr_db"]-1.76)/6.02,places=12)

    def test_prepared_decks_preserve_all_R3_subcircuits(self):
        import yaml
        cfg=yaml.safe_load((ROOT/"config/sar8_r3_performance.yaml").read_text())
        self.assertFalse(cfg["mismatch"])
        self.assertFalse(cfg["transient_noise"])
        self.assertEqual(cfg["dynamic"]["frequency_hz"],cfg["sample_rate_hz"]*461/1024)
        self.assertEqual(cfg["static"]["final_bracket_width_lsb"],.5/2**6)
        for name in ("sine_1024_k461","static_001_064","static_065_128","static_129_192","static_193_255"):
            ctx=run.r3.r1.read_json(run.OUT/f"cases/{name}.json")
            self.assertEqual(ctx["maxstep_ps"],cfg["maxstep_ps"])
            self.assertEqual(ctx["threads"],cfg["threads_per_job"])
        base=run.r3.r1.blocks((run.OUT/"exports/primary/input.scs").read_text())
        run.baseline()
        count=0
        for p in (run.OUT/"decks").glob("*.scs"):
            self.assertEqual(run.r3.r1.blocks(p.read_text()),base,p.name)
            count+=1
        self.assertGreater(count,0)
        for source in (run.MONITOR,run.STIM):
            import re
            self.assertIsNone(re.search(r"(?<![%\w\d])\.\d",source.read_text()),source.name)


if __name__=="__main__":unittest.main()
