from pathlib import Path
import importlib.util
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "analysis" / "run_cdac_reference_settling.py"
SPEC = importlib.util.spec_from_file_location("cdac_reference_settling", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _case(cu_ff: float, rref: float, rswitch: float, settling_ns: float = 3.0):
    return {
        "unit_capacitance_ff": cu_ff,
        "settling_time_ns": settling_ns,
        "reference_resistance_ohm": rref,
        "switch_resistance_ohm": rswitch,
    }


class CdacReferenceSettlingTest(unittest.TestCase):
    def test_derived_limits_reproduce_tracked_budgets(self):
        config = MODULE.load_config()
        limits = MODULE.derive_limits(config)
        self.assertAlmostEqual(limits["lsb_v"], 1.7578125e-3, delta=1e-15)
        self.assertAlmostEqual(
            limits["sampling_noise_limit_v_rms"], 0.31640625e-3, delta=1e-15
        )
        self.assertAlmostEqual(
            limits["settling_residual_limit_v"], 0.439453125e-3, delta=1e-15
        )

    def test_expected_noise_fail_settling_fail_and_feasible_points(self):
        config = MODULE.load_config()
        noise_fail = MODULE.evaluate_candidate(config, _case(2.0, 500.0, 1000.0))
        settling_fail = MODULE.evaluate_candidate(
            config, _case(6.86047, 500.0, 1500.0)
        )
        feasible = MODULE.evaluate_candidate(config, _case(6.86047, 500.0, 1000.0))

        self.assertFalse(noise_fail["noise_pass"])
        self.assertTrue(noise_fail["settling_pass"])
        self.assertTrue(settling_fail["noise_pass"])
        self.assertFalse(settling_fail["settling_pass"])
        self.assertTrue(feasible["noise_pass"])
        self.assertTrue(feasible["settling_pass"])
        self.assertTrue(feasible["feasible"])


if __name__ == "__main__":
    unittest.main()
