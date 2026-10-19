"""Focused regression for the executable behavioral golden model."""

from __future__ import annotations

import math
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.behavioral.sar_adc import SarAdcModel
from scripts.analysis.run_behavioral_baseline import run_baseline


class BehavioralBaselineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = SarAdcModel(10, (-0.9, 0.9))

    def test_code_boundaries_and_saturation(self) -> None:
        lsb = self.model.lsb_v
        vin = np.array(
            [-1.0, -0.9, -0.9 + 1.5 * lsb, 0.9 - 0.5 * lsb, 0.9, 1.0]
        )
        codes = self.model.unsigned_codes(self.model.convert(vin))
        np.testing.assert_array_equal(codes, [0, 0, 1, 1023, 1023, 1023])
        self.assertTrue(math.isclose(lsb, 1.8 / 1024, rel_tol=0.0, abs_tol=1e-15))

    def test_end_to_end_static_dynamic_and_budget_gates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            summary = run_baseline(
                PROJECT_ROOT / "config" / "design_spec_10b.yaml",
                Path(temp_dir),
                make_plots=False,
            )
            self.assertEqual(summary["static"]["missing_code_count"], 0)
            self.assertLess(abs(summary["static"]["dnl_min_lsb"]), 0.01)
            self.assertLess(abs(summary["static"]["dnl_max_lsb"]), 0.01)
            self.assertLess(abs(summary["static"]["inl_min_lsb"]), 0.01)
            self.assertLess(abs(summary["static"]["inl_max_lsb"]), 0.01)
            target_sndr = summary["error_budget"]["target_sndr_db"]
            target_enob = (target_sndr - 1.76) / 6.02
            self.assertGreaterEqual(summary["dynamic"]["enob_bits"], target_enob)
            self.assertGreaterEqual(summary["dynamic"]["sndr_db"], target_sndr)
            self.assertGreater(summary["error_budget"]["sndr_margin_db"], 0.0)
            self.assertGreater(summary["error_budget"]["residual_headroom_rms_lsb"], 0.0)


if __name__ == "__main__":
    unittest.main()
