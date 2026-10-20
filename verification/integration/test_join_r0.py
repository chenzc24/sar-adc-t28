"""Contract/algebra checks, not an implementation of the ideal-gate adapter."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/integration"))
from freeze_r0 import config, ideal_gates, map_conversion, physical_words, sample_events


class JoinR0(unittest.TestCase):
    def test_selected_3x_and_native_blocks(self):
        cfg = config(); mods = cfg["modules"]
        self.assertEqual(mods["reference_switch"]["p_ratio"], 3)
        self.assertEqual(mods["reference_switch"]["n_ratio"], 3)
        self.assertEqual(mods["controller"]["cell"], "sar_logic_8b_async_simple")
        self.assertEqual(mods["comparator"]["cell"], "sar_strongarm_t28")
        self.assertFalse(cfg["physical_integration_implemented"])
        self.assertFalse(cfg["interface_adapter_implemented"])
        self.assertFalse(cfg["qualified"])

    def test_every_code_mapping_and_charge_equation(self):
        for code in range(256):
            native = {"BP_H": code, "BP_L": 255-code, "BN_H": 255-code, "BN_L": code}
            physical = map_conversion(native)
            self.assertEqual(physical, physical_words(code))
            self.assertEqual(physical["PH"] + physical["PL"], 255)
            self.assertEqual(physical["NH"] + physical["NL"], 255)
            self.assertEqual(physical["PH"] + physical["NH"], 255)
            differential_dac = .9 * ((physical["PH"] + 1) - physical["NH"]) / 256
            self.assertAlmostEqual(differential_dac, .9 - code * 1.8 / 256)
            # Code-center SAR decision convention, not an integrated ADC run.
            vin = -.9 + (code+.375)*1.8/256;stored = 0
            for bit in range(7, -1, -1):
                trial = stored | (1 << bit);words = physical_words(trial)
                residual = vin + .9*((words["PH"]+1)-words["NH"])/256
                if residual >= 0:stored |= 1 << bit
            self.assertEqual(stored, code)

    def test_gate_enable_polarities_and_nonoverlap(self):
        self.assertEqual(ideal_gates(0, 0), {"p_gate": .9, "n_gate": 0.})
        self.assertEqual(ideal_gates(1, 0), {"p_gate": 0., "n_gate": 0.})
        self.assertEqual(ideal_gates(0, 1), {"p_gate": .9, "n_gate": .9})
        with self.assertRaises(AssertionError):ideal_gates(1, 1)

    def test_sampling_and_conversion_start_same_midpoint(self):
        expected = {"PH": 127, "PL": 128, "NH": 128, "NL": 127}
        cfg = config();timing = cfg["timing"]
        # Spectre pulse width excludes rising edge, so width+rise gives the
        # interval between the two 50% crossings for equal rise/fall times.
        acquired = timing["sample_width_ns"] + timing["sample_edge_ps"]/1000
        self.assertAlmostEqual(acquired, 40.)
        for rise in (1.05, 101.05, 201.05):
            events = sample_events(rise)
            self.assertEqual(events["physical_midpoint_words"], expected)
            self.assertAlmostEqual(events["reference_restore_request_ns"]-rise, 2.)
            self.assertAlmostEqual(events["earliest_new_rail_command_ns"]-rise, 2.1)
            self.assertLess(events["earliest_new_rail_command_ns"], rise+acquired)
        self.assertEqual(physical_words(128), expected)
        self.assertNotEqual(expected, {k: 0 for k in expected})


if __name__ == "__main__":
    unittest.main()
