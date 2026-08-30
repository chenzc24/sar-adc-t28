from __future__ import annotations

import json
import math
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.analysis.run_electrical_macro_model import (
    CONTROLLER_PATH,
    code_center_v,
    electrical_weights,
    load_config,
    macro_sar_trace,
    stage_case,
    static_metrics,
    timing_contract,
)


class ElectricalMacroModelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_config()

    def test_canonical_split_array_recovers_binary_weights(self):
        weights = electrical_weights(self.config)
        self.assertTrue(math.isclose(weights["effective_top_capacitance_units"], 32.0, abs_tol=1e-12))
        self.assertTrue(math.isclose(weights["base_coupling"], 1.0, abs_tol=1e-12))
        expected = [2.0 ** (-index) for index in range(1, 11)]
        for actual, target in zip(weights["bit_couplings_msb_to_lsb"], expected, strict=True):
            self.assertTrue(math.isclose(actual, target, abs_tol=1e-12))
        metrics = static_metrics(self.config, weights)
        self.assertEqual(metrics["missing_codes"], 0)
        self.assertLess(abs(metrics["dnl_max_lsb"]), 1e-10)
        self.assertLess(abs(metrics["inl_max_lsb"]), 1e-10)

    def test_assumed_parasitics_change_the_transfer(self):
        case = self.config["spectre_cases"]["parasitic_case"]
        weights = electrical_weights(
            self.config,
            top_plate_parasitic_ff=case["top_plate_parasitic_ff"],
            bridge_node_parasitic_ff=case["bridge_node_parasitic_ff"],
        )
        metrics = static_metrics(self.config, weights)
        self.assertLess(weights["base_coupling"], 1.0)
        self.assertGreater(metrics["inl_max_lsb"], 10.0)
        code, _ = macro_sar_trace(self.config, code_center_v(self.config, 768), weights)
        self.assertEqual(code, 774)

    def test_timing_has_ten_latches_and_nine_explicit_trial_edges(self):
        timing = timing_contract(self.config)
        self.assertEqual(len(timing["trial_times_ns"]), 10)
        self.assertEqual(len(timing["latch_times_ns"]), 10)
        self.assertEqual(timing["trial_wave"].count("0.9"), 18)
        self.assertLess(timing["conversion_latency_ns"], self.config["source_spec"]["conversion_time_budget_ns"])

    def test_controller_and_staged_deck_are_static_portable(self):
        controller = CONTROLLER_PATH.read_text(encoding="utf-8")
        self.assertIn("trial_mask = 512", controller)
        self.assertIn("trial_active = 1", controller)
        self.assertNotIn("SEL_ZERO[bit]", controller)
        self.assertNotIn("SEL_ONE[bit]", controller)
        with tempfile.TemporaryDirectory() as tmp:
            deck = stage_case(
                self.config,
                Path(tmp),
                vin_diff_v=code_center_v(self.config, 768),
            )
            text = deck.read_text(encoding="utf-8")
            self.assertNotIn("@", text)
            self.assertIn("sar_macro_10b", text)
            self.assertIn("ahdl_include", text)

    def test_saved_spectre_regression_when_available(self):
        path = ROOT / "output" / "electrical_macro_model" / "summary.json"
        if not path.exists():
            self.skipTest("generated Spectre regression is not present")
        summary = json.loads(path.read_text(encoding="utf-8"))
        nominal = [item for item in summary["spectre"] if item["name"].startswith("nominal_")]
        self.assertEqual(len(nominal), 6)
        for item in nominal:
            self.assertTrue(item["spectre_ok"])
            self.assertEqual(item["spectre_code"], item["charge_model_code"])
            self.assertLessEqual(item["maximum_pre_compare_settling_error_lsb"], 0.25)
            self.assertTrue(item["all_comparisons_resolved"])
            self.assertTrue(item["all_comparator_signs_match"])


if __name__ == "__main__":
    unittest.main()
