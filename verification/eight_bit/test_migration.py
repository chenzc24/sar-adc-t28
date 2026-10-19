"""Deterministic active/history contracts plus focused 8-bit model regression."""
from __future__ import annotations

import json
import math
from pathlib import Path
import re
import sys
import tempfile
import unittest

import numpy as np
import yaml

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from models.behavioral.sar_adc import SarAdcModel
from scripts.analysis.run_behavioral_baseline import derive_error_budget, run_baseline


class EightBitMigrationTest(unittest.TestCase):
    def test_active_and_historical_specs(self):
        active=yaml.safe_load((ROOT/"config/design_spec.yaml").read_text())
        old=yaml.safe_load((ROOT/"config/design_spec_10b.yaml").read_text())
        self.assertEqual(active["converter"]["resolution_bits"],8)
        self.assertEqual(active["converter"]["cdac_partition"],"flat_binary")
        self.assertEqual(old["converter"]["resolution_bits"],10)
        for field in ("supplies","input","timing_budget"):
            self.assertEqual(active[field],old[field])
        budget=derive_error_budget(active);before=derive_error_budget(old)
        self.assertAlmostEqual(budget["clock_jitter_error_rms_v"],before["clock_jitter_error_rms_v"],places=15)
        self.assertAlmostEqual(budget["sampling_noise_rms_v"],4*before["sampling_noise_rms_v"],places=15)
        self.assertGreater(budget["sndr_margin_db"],0)

    def test_flat_weights_dummy_and_load(self):
        cfg=yaml.safe_load((ROOT/"config/eight_bit_flat.yaml").read_text())
        self.assertEqual(cfg["cdac"]["weights_lsb_first"],[1,2,4,8,16,32,64,128])
        self.assertEqual(sum(cfg["cdac"]["weights_lsb_first"])+cfg["cdac"]["dummy_units"],256)
        self.assertEqual(cfg["cdac"]["bridge_units"],0)
        cside=256*cfg["unit_capacitance_ff"]*1e-15
        self.assertAlmostEqual(cside*1e12,1.75628032)
        self.assertLess(1.8*math.exp(-3e-9/(200*cside)),1.8/256/4)
        self.assertEqual(cfg["sampling"]["native_main_width_um"],1)

    def test_explicit_eight_bit_va_interface(self):
        ideal=(ROOT/"models/veriloga/sar_adc_ideal_8b.va").read_text()
        ctrl=(ROOT/"models/veriloga/sar_macro_controller_8b.va").read_text()
        self.assertRegex(ideal,r"DOUT\[7:0\]|\[7:0\]\s+DOUT")
        self.assertNotRegex(ideal,r"DOUT\[(?:8|9)\]")
        self.assertNotRegex(ctrl,r"\b(?:D[89]|SEL[01]_[89])\b")
        for bit in range(8):
            self.assertIn(f"SEL0_{bit}",ctrl)
            self.assertIn(f"SEL1_{bit}",ctrl)
        self.assertIn("$rdist_normal",ideal)
        self.assertIn("bit_index = 7",ideal)

    def test_full_eight_bit_behavioral_regression(self):
        m=SarAdcModel(8,(-.9,.9))
        levels=-.9+(np.arange(256)+.5)*m.lsb_v
        np.testing.assert_array_equal(m.unsigned_codes(m.convert(levels)),np.arange(256))
        with tempfile.TemporaryDirectory() as temp:
            r=run_baseline(ROOT/"config/design_spec.yaml",Path(temp),make_plots=False)
        self.assertEqual(r["static"]["missing_code_count"],0)
        self.assertGreater(r["dynamic"]["enob_bits"],7)
        self.assertAlmostEqual(r["model"]["lsb_v"],.00703125)

    @unittest.skipUnless((ROOT/"output/eight_bit_flat/electrical/summary.json").exists(),"Remote evidence not downloaded")
    def test_downloaded_macro_evidence(self):
        rows=json.loads((ROOT/"output/eight_bit_flat/electrical/summary.json").read_text())
        nominal=[r for r in rows if r["kind"]=="nominal"]
        self.assertEqual(len(nominal),10)
        self.assertTrue(all(r["pass"] and len(r["trace"])==8 for r in nominal))
        self.assertFalse(next(r for r in rows if r["name"]=="macro8_slow_reference")["pass"])

    @unittest.skipUnless((ROOT/"output/eight_bit_flat/bootstrap/summary_w1u.json").exists(),"Remote evidence not downloaded")
    def test_downloaded_native_load_qualification(self):
        get=lambda name:json.loads((ROOT/f"output/eight_bit_flat/bootstrap/summary_{name}.json").read_text())
        old,new=get("initial"),get("w1u")
        self.assertEqual(len(new),5)
        self.assertTrue(all(r["NEW"]["pass"] for r in new))
        self.assertFalse(all(r["NEW"]["pass"] for r in old))
        self.assertLess(max(abs(r["NEW"]["held_error_mv"]) for r in new),1.8/256/4*1000)


if __name__=="__main__":unittest.main()
