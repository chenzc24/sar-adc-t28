"""Focused guard for parameter-only native ramp sweep and measured evidence."""
import hashlib
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts/integration"))
import reference_edge_slew as exp


class ReferenceEdgeSlew(unittest.TestCase):
    def test_only_sixteen_edge_parameters_change(self):
        for point,r in exp.baselines().items():
            original=(r["folder"]/f"decks/{r['name']}.scs").read_text(encoding="utf-8")
            for edge in exp.EDGES_PS:
                text=(exp.OUT/f"decks/{point}_e{edge}ps.scs").read_text(encoding="utf-8")
                self.assertEqual(text,exp.patch(original,edge))
                self.assertEqual(text.replace(f" edge_s={edge}p",""),original)
                self.assertEqual(text.count("restore_guard_s=100p"),16)

    def test_baselines_and_provenance(self):
        exp.baselines()
        m=exp.guard.base.r1.read_json(ROOT/"verification/integration/reference_edge_slew_results.json")
        self.assertFalse(m["remote_OA_changed"])
        self.assertEqual(len(m["cases"]),12)
        self.assertEqual(sum(not r["baseline_reused"] for r in m["cases"]),8)
        for rel,h in m["source_text_LF_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT/rel).read_text(encoding="utf-8").encode()).hexdigest(),h)
        for stem,h in m["prior_manifest_sha256"].items():
            self.assertEqual(exp.guard.base.r1.sha(ROOT/f"verification/integration/{stem}.json"),h)
        for r in m["cases"]:
            p=ROOT/r["source_folder"];name=r["source_case"]
            self.assertEqual(exp.guard.base.r1.sha(p/f"cases/{name}.json"),r["source_case_context_sha256"])
            self.assertEqual(exp.guard.base.r1.sha(p/f"decks/{name}.scs"),r["context"]["deck_sha256"])
            self.assertEqual(exp.guard.base.r1.sha(p/f"runs/{name}_waveform.json"),r["waveform_sha256"])

    def test_measured_timing_function_and_sample_checks(self):
        m=exp.guard.base.r1.read_json(ROOT/"verification/integration/reference_edge_slew_results.json")
        for r in m["cases"]:
            self.assertTrue(r["metrics"]["result_ok"])
            self.assertTrue(all(f["frame_pass"] for f in r["metrics"]["frames"]),r["name"])
            self.assertTrue(r["stimulus_check"]["passed"])
            self.assertTrue(r["sampling_error_pass"],r["name"])
            self.assertTrue(r["bounded_case_pass"],r["name"])
            self.assertEqual(r["metrics"]["CMI_warning_count"],0)
            self.assertFalse(r["metrics"]["suppression_or_LTE_lines"])
            self.assertLessEqual(r["metrics"]["reference_stress"]["value_v"],.99)
            self.assertLessEqual(r["metrics"]["comparator_stress_from_saved_internal_nodes"]["value_v"],.99)
            self.assertAlmostEqual(r["phase_stress"]["whole_run"]["reference_max_v"],
                                   r["metrics"]["reference_stress"]["value_v"],places=12)
            self.assertFalse(r["metrics"]["simultaneous_gate_enable_banks"])
            self.assertFalse(r["gate_checks"]["overlap_above_one_percent_banks"])
            e=r["restore_edges"]
            self.assertEqual(len(e["new_on_ns"]),1)
            self.assertAlmostEqual(e["new_on_ns"][0],101.25+r["edge_ps"]/2000,places=5)
            self.assertAlmostEqual(e["old_off_ns"][0],101.15+r["edge_ps"]/2000,places=5)
            self.assertLess(e["on_spread_ps"],.1)
            self.assertLess(e["off_spread_ps"],.1)
            self.assertGreaterEqual(r["metrics"]["minimum_opposite_rail_deadtime_ps"],99.8)
            self.assertGreater(r["gate_checks"]["restore_min_one_percent_gate_gap_ps"],0)


if __name__=="__main__":unittest.main()
