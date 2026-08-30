from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.analysis.run_module_first_order import (
    comparator_candidate,
    jitter_error_rms_v,
    load_config,
    lsb_v,
    sampling_candidate,
)


class ModuleFirstOrderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_config()

    def test_sampling_pass_and_fail(self):
        cases = self.config["sampling_acquisition"]["representative_spectre_cases"]
        results = {case["name"]: sampling_candidate(self.config, case) for case in cases}
        self.assertTrue(results["nominal_margin"]["settling_pass"])
        self.assertTrue(results["near_envelope_feasible"]["settling_pass"])
        self.assertFalse(results["acquisition_fail"]["settling_pass"])

    def test_comparator_pass_and_fail(self):
        cases = self.config["comparator_regeneration"]["representative_spectre_cases"]
        results = {case["name"]: comparator_candidate(self.config, case) for case in cases}
        self.assertTrue(results["nominal_feasible"]["decision_pass"])
        self.assertFalse(results["insufficient_gm"]["decision_pass"])
        self.assertTrue(results["fast_regeneration"]["decision_pass"])
        self.assertAlmostEqual(
            results["nominal_feasible"]["analytical_decision_time_ns"],
            1.3862943611198904,
            places=12,
        )

    def test_tracked_jitter_point(self):
        frequency = self.config["clock_jitter"]["tracked_budget_frequency_hz"]
        error_v = jitter_error_rms_v(self.config, frequency)
        self.assertTrue(math.isclose(error_v, 0.00032073761051881647, rel_tol=1e-12))
        self.assertTrue(math.isclose(error_v / lsb_v(self.config), 0.18246406287292669, rel_tol=1e-12))


if __name__ == "__main__":
    unittest.main()
