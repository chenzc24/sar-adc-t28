"""Focused native-circuit invariance and retained-evidence checks."""
import hashlib
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts/integration"))
from reference_alignment import BASE,OUT,VA,aligned_deck,native_top,r1


class Alignment(unittest.TestCase):
    def test_native_circuit_unchanged(self):
        source=(BASE/"decks/nfull_fine.scs").read_text()
        a=r1.blocks(source);b=r1.blocks(aligned_deck(source))
        self.assertEqual(a.keys(),b.keys())
        for cell in a:
            self.assertEqual(native_top(a[cell]) if cell==r1.TOP else a[cell],
                             native_top(b[cell]) if cell==r1.TOP else b[cell],cell)
        self.assertEqual(sum("sar8j_r1_sw_b" in k for k in a),8)

    def test_frozen_R1_sources_untouched(self):
        manifest=r1.read_json(ROOT/"verification/integration/join_r1_results.json")
        for relative,digest in manifest["source_text_LF_sha256"].items():
            content=(ROOT/relative).read_text(encoding="utf-8").replace("\r\n","\n")
            self.assertEqual(hashlib.sha256(content.encode()).hexdigest(),digest,relative)
        self.assertEqual(r1.sha(r1.VA),manifest["gate_VA_exact_byte_sha256"])

    def test_only_request_timing_boundary(self):
        text=VA.read_text()
        self.assertNotIn("V(VIN",text)
        self.assertNotIn("V(TOP",text)
        self.assertIn("settle_s=200p",text)
        self.assertIn("dead_time_s=100p",text)
        self.assertIn("edge_s=20p",text)
        self.assertIn("want_h=target_h; want_l=target_l",text)

    def test_curated_evidence(self):
        path=ROOT/"verification/integration/reference_alignment_results.json"
        self.assertTrue(path.exists())
        manifest=r1.read_json(path)
        self.assertFalse(manifest["remote_OA_changed"])
        for relative,digest in manifest["sources"].items():
            self.assertEqual(hashlib.sha256((ROOT/relative).read_text(encoding="utf-8").encode()).hexdigest(),digest)
        for case in manifest["cases"]:
            name=case["name"]
            self.assertTrue(case["aligned"]["result_ok"])
            self.assertEqual(r1.sha(OUT/f"decks/{name}.scs"),case["context"]["deck_sha256"])
            self.assertEqual(r1.sha(OUT/f"runs/{name}_waveform.json"),case["waveform_sha256"])
            self.assertTrue(all(f["frame_pass"] for f in case["aligned"]["frames"]))
            self.assertFalse(case["aligned"]["simultaneous_gate_enable_banks"])
            self.assertLess(case["phase_stress"]["conversion"]["reference_max_v"],.99)
            self.assertLess(case["phase_stress"]["conversion"]["comparator_max_v"],.99)
            self.assertGreater(case["baseline"]["phase_stress"]["conversion"]["reference_max_v"],1.2)
            old=case["baseline"]["phase_stress"]["second_acquisition"]["comparator_max_v"]
            new=case["phase_stress"]["second_acquisition"]["comparator_max_v"]
            self.assertLess(abs(new-old),30e-6)
            if case["context"]["point"]=="nfull":
                self.assertFalse(case["aligned"]["bounded_join_pass"])
                self.assertGreater(new,.99)
            else:self.assertTrue(case["aligned"]["bounded_join_pass"])
            for h in case["handoffs"]:
                if h["on_spread_ps"] is not None:self.assertLess(h["on_spread_ps"],.1)
                if h["off_spread_ps"] is not None:self.assertLess(h["off_spread_ps"],.1)


if __name__=="__main__":unittest.main()
