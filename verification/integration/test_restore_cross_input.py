"""Focused patch/provenance and measured polarity-history checks."""
import hashlib
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts/integration"))
import restore_cross_input as exp


class RestoreCrossInput(unittest.TestCase):
    def test_only_input_sources_change(self):
        _,path=exp.candidate()
        original=path.read_text(encoding="utf-8")
        for name,values in exp.CASES.items():
            text=(exp.OUT/f"decks/{name}.scs").read_text(encoding="utf-8")
            self.assertEqual(text,exp.patch(original,name))
            self.assertEqual(exp.without_stimulus(text),exp.without_stimulus(original))
            self.assertEqual(text.count(" restore_guard_s=100p"),16)
            self.assertEqual(text.count("type=pwl"),0 if values[0]==values[1] else 2)
            ctx=exp.guard.base.r1.read_json(exp.OUT/f"cases/{name}.json")
            self.assertEqual(ctx["stimulus_vdiff_by_frame"],list(values))
            self.assertEqual(ctx["restore_guard_ps"],100)

    def test_R2_and_prior_candidate_unchanged(self):
        exp.candidate()

    def test_curated_provenance(self):
        m=exp.guard.base.r1.read_json(ROOT/"verification/integration/restore_cross_input_results.json")
        self.assertFalse(m["remote_OA_changed"])
        self.assertTrue(m["native_topology_sizes_VA_bytes_unchanged"])
        self.assertEqual(m["prior_manifest_sha256"],exp.guard.base.r1.sha(ROOT/"verification/integration/restore_guard_results.json"))
        self.assertEqual({r["name"] for r in m["cases"]},set(exp.CASES))
        for rel,h in m["source_text_LF_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT/rel).read_text(encoding="utf-8").encode()).hexdigest(),h)
        for r in m["cases"]:
            name=r["name"]
            self.assertEqual(r["context"]["deck_sha256"],exp.guard.base.r1.sha(exp.OUT/f"decks/{name}.scs"))
            self.assertEqual(r["waveform_sha256"],exp.guard.base.r1.sha(exp.OUT/f"runs/{name}_waveform.json"))

    def test_measured_function_sampling_and_stress(self):
        m=exp.guard.base.r1.read_json(ROOT/"verification/integration/restore_cross_input_results.json")
        expected={"pfull_g100ps":[241,241],"n_to_p_g100ps":[14,241],"p_to_n_g100ps":[241,14]}
        for r in m["cases"]:
            self.assertTrue(r["bounded_case_pass"],r["name"])
            self.assertTrue(r["stimulus_check"]["passed"])
            self.assertTrue(r["sampling_error_pass"])
            self.assertEqual(r["simulator_totals"]["errors"],0)
            self.assertEqual(r["simulator_totals"]["warnings"],7)
            self.assertEqual(r["simulator_totals"]["notices"],6 if r["name"]=="p_to_n_g100ps" else 5)
            self.assertEqual(any("Bad pivoting" in line for line in r["initial_DC_diagnostic_lines"]),
                             r["name"]=="p_to_n_g100ps")
            self.assertEqual([f["observed_codes_in_window"] for f in r["metrics"]["frames"]],
                             [[code] for code in expected[r["name"]]])
            self.assertTrue(all(f["frame_pass"] for f in r["metrics"]["frames"]))
            self.assertEqual(r["metrics"]["CMI_warning_count"],0)
            self.assertFalse(r["metrics"]["suppression_or_LTE_lines"])
            self.assertFalse(r["metrics"]["simultaneous_gate_enable_banks"])
            self.assertFalse(r["metrics"]["raw_both_on_banks"])
            self.assertGreaterEqual(r["metrics"]["minimum_opposite_rail_deadtime_ps"],99.8)
            self.assertLessEqual(r["phase_stress"]["whole_run"]["reference_max_v"],.99)
            self.assertLessEqual(r["phase_stress"]["whole_run"]["comparator_max_v"],.99)
            e=r["restore_edges"]
            self.assertEqual(len(e["new_on_ns"]),1)
            self.assertAlmostEqual(e["new_on_ns"][0],101.26,places=5)
            self.assertLess(e["on_spread_ps"],.1)
            self.assertLess(e["off_spread_ps"],.1)


if __name__=="__main__":unittest.main()
