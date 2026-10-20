"""Focused invariants: reset-only variants must not alter input sampling."""
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/cdac8_reset"))
from experiment import SCREEN, configure, device_line, modify
from support import OLD, blocks, statements
from analyze import instances


class ResetDeckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = OLD / "oa_netlists/tb_cdac8_nominal/balanced/input.scs"
        if not path.exists():
            raise unittest.SkipTest("Requires private native OA export; never commit the PDK deck")
        cls.source = path.read_text()

    def test_native_statement_is_complete(self):
        line = device_line(blocks(self.source)["cdac8_ref_switch_b7"], "MN_IS")
        self.assertIn("spomb1=", line)
        self.assertGreater(len(line.splitlines()), 3)

    def test_multiline_leaf_instances_are_not_silently_skipped(self):
        original = blocks(self.source)
        array = instances(original["cdac8_device_nominal"])
        leaves = [(name, info) for name, info in array.items() if name.startswith("XS")]
        self.assertEqual(len(leaves), 18)
        count = sum(len(instances(original[master])) for _, (_, master) in leaves)
        self.assertEqual(count, 216)

    def test_bootstrap_capacitors_and_pass_devices_are_unchanged(self):
        original = blocks(self.source)
        for variant in SCREEN:
            with self.subTest(variant=variant.name):
                changed = modify(self.source, variant)
                actual = blocks(changed)
                self.assertEqual(original["sar_bootstrap_canvas_flat_8b"], actual["sar_bootstrap_canvas_flat_8b"])
                self.assertEqual(original["cdac8_device_nominal"], actual["cdac8_device_nominal"])
                for bit in range(8):
                    cell = f"cdac8_ref_switch_b{bit}"
                    for name in ("MP_CM", "MP_HIGH", "MN_LOW"):
                        self.assertEqual(device_line(original[cell], name), device_line(actual[cell], name))
                    before = device_line(original[cell], "MN_CM")
                    after = device_line(actual[cell], "MN_CM").replace("BOT ES_N ", "BOT ES ")
                    self.assertEqual(before, after)
                    added = 0 if variant.n_buffer == "none" else 2 if variant.n_buffer == "shared" else 4
                    count = sum(x.strip().startswith(("MN_", "MP_")) for x in statements(actual[cell]))
                    self.assertEqual(count, 12 + added)
                configured, values = configure(changed)
                self.assertIn("stop=300n", configured)
                self.assertNotIn(" info ", configured)
                self.assertEqual(values["SUP"], .9)


class ParserTests(unittest.TestCase):
    def test_continued_master_name_is_required(self):
        sample = "XSP0 (B0 H L ES VCM VDD VREFN VREFP VSS) " + "\\" + "\n        synthetic_switch\n"
        self.assertEqual(instances(sample)["XSP0"][1], "synthetic_switch")

    def test_tracked_evidence_does_not_promote_failed_candidate(self):
        import yaml
        cfg = yaml.safe_load((ROOT / "config/cdac8_reset.yaml").read_text(encoding="utf-8"))
        manifest = yaml.safe_load((ROOT / "virtuoso/cell_manifest.yaml").read_text(encoding="utf-8"))
        self.assertFalse(cfg["candidate_qualified"])
        self.assertEqual(cfg["evidence"]["native_aps_successful_runs"], 24)
        self.assertTrue(cfg["unchanged"]["bootstrap_phi"])
        self.assertEqual(cfg["candidate"]["vcm_p_gate_pull_down_multiplier"], 4)
        self.assertIn("tb_cdac8_reset_literal", manifest["cells"])


if __name__ == "__main__":
    unittest.main()
