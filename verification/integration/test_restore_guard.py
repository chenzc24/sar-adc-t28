"""Narrow evidence checks for the three restore-delay comparison points."""
import hashlib
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts/integration"))
from restore_guard import BASE,OUT,GUARDS_PS,baseline,patch,base


class RestoreGuard(unittest.TestCase):
    def test_only16_timing_parameters_change(self):
        text=(BASE/"decks/nfull.scs").read_text(encoding="utf-8")
        for g in GUARDS_PS:
            changed=patch(text,g)
            self.assertEqual(changed.count(f"restore_guard_s={g}p"),16)
            self.assertEqual(changed.replace(f" restore_guard_s={g}p",""),text)

    def test_R2_sources_models_and_baseline_unchanged(self):
        baseline()

    def test_provenance_and_comparison_complete(self):
        m=base.r1.read_json(ROOT/"verification/integration/restore_guard_results.json")
        self.assertFalse(m["remote_OA_changed"])
        self.assertEqual(m["baseline_R2_manifest_sha256"],base.r1.sha(ROOT/"verification/integration/join_r2_results.json"))
        self.assertEqual({r["restore_guard_ps"] for r in m["cases"]},{100,500,2000})
        for rel,h in m["source_text_LF_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT/rel).read_text(encoding="utf-8").encode()).hexdigest(),h)
        for r in m["cases"]:
            folder=ROOT/r["source_folder"];name=r["source_case"]
            self.assertEqual(base.r1.sha(folder/f"decks/{name}.scs"),r["context"]["deck_sha256"])
            self.assertEqual(base.r1.sha(folder/f"runs/{name}_waveform.json"),r["waveform_sha256"])
            self.assertEqual(r["baseline_reused"],r["restore_guard_ps"]==2000)

    def test_function_sampling_and_measured_restore_edges(self):
        m=base.r1.read_json(ROOT/"verification/integration/restore_guard_results.json")
        for r in m["cases"]:
            self.assertTrue(r["metrics"]["result_ok"])
            self.assertTrue(all(f["frame_pass"] for f in r["metrics"]["frames"]))
            self.assertTrue(r["sampling_error_pass"])
            self.assertFalse(r["metrics"]["simultaneous_gate_enable_banks"])
            self.assertGreaterEqual(r["metrics"]["minimum_opposite_rail_deadtime_ps"],99.8)
            expected=r["sampling"][1]["hold_ns"]-40+r["restore_guard_ps"]/1000+.11
            self.assertEqual(len(r["restore_edges"]["new_on_ns"]),1)
            self.assertAlmostEqual(r["restore_edges"]["new_on_ns"][0],expected,places=5)
            self.assertLess(r["restore_edges"]["on_spread_ps"],.1)
            if r["restore_guard_ps"]==2000:
                self.assertFalse(r["metrics"]["bounded_join_pass"])
                self.assertGreater(r["phase_stress"]["second_acquisition"]["comparator_max_v"],.99)
            else:
                self.assertTrue(r["metrics"]["bounded_join_pass"])
                self.assertEqual(r["metrics"]["CMI_warning_count"],0)
                self.assertLessEqual(r["metrics"]["reference_stress"]["value_v"],.99)
                self.assertLessEqual(r["metrics"]["comparator_stress_from_saved_internal_nodes"]["value_v"],.99)


if __name__=="__main__":unittest.main()
