"""Bounded saved-schematic adoption checks, not broad ADC qualification."""
import hashlib
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts/integration"))
import join_r3 as design
import join_r3_sim as sim


class SavedR3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=design.r1.read_json(ROOT/"verification/integration/join_r3_results.json")

    def test_saved_oa_and_native_graph(self):
        m=self.m
        self.assertEqual(m["OA_preflight"]["frozen_cells_matched"],36)
        self.assertEqual(m["OA_postflight"]["frozen_cells_matched"],36)
        self.assertTrue(m["OA_postflight"]["R2_original_2ns_20ps_readback_verified"])
        self.assertTrue(m["saved_OA_readback_audit"]["only16_gate_timing_overrides"])
        for tag in ("primary","final"):
            path=design.OUT/f"exports/{tag}/input.scs"
            audit=design.audit_export(path.read_text())
            saved=m["exact_saved_OA_export_audit" if tag=="primary" else "final_saved_OA_export_audit"]
            self.assertEqual(design.r1.sha(path),saved["export_sha256"])
            self.assertEqual(audit["explicit_timing_gate_instances"],16)
            self.assertEqual(audit["subckt_sha256"],saved["subckt_sha256"])
        self.assertEqual(m["exact_saved_OA_export_audit"]["subckt_sha256"],
                         m["final_saved_OA_export_audit"]["subckt_sha256"])
        self.assertTrue(m["saved_OA_readback_audit"]["zero_markers"])
        for n in (design.TOP,design.TB):
            d=design.r1.read_json(design.OUT/f"oa/{n}.json")
            self.assertEqual(design.object_digest(design.schematic_surface(d)),m["OA_surface_sha256"][n])

    def test_provenance_and_unmodified_dut_wrappers(self):
        m=self.m
        for rel,h in m["source_text_LF_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT/rel).read_text(encoding="utf-8").encode()).hexdigest(),h)
        self.assertEqual(m["prior_candidate_manifest_sha256"],
            design.r1.sha(ROOT/"verification/integration/reference_edge_slew_results.json"))
        expected=design.r1.blocks((design.OUT/"exports/primary/input.scs").read_text())
        old={p["name"]:p for p in m["shared_CDF_before"]}
        now={p["name"]:p for p in m["shared_CDF_after"]}
        for n,p in old.items():self.assertEqual(p,now[n])
        self.assertEqual(now["restore_guard_s"]["defValue"],"2n")
        self.assertEqual(now["edge_s"]["defValue"],"20p")
        for row in m["cases"]:
            name=row["name"];ctx=row["context"]
            path=design.OUT/f"decks/{name}.scs"
            self.assertEqual(design.r1.blocks(path.read_text()),expected)
            self.assertTrue(ctx["exact_saved_OA_DUT_unmodified"])
            self.assertEqual(design.r1.sha(path),ctx["deck_sha256"])
            self.assertEqual(design.r1.sha(design.OUT/f"runs/{name}_waveform.json"),row["waveform_sha256"])
            result=design.r1.read_json(design.OUT/f"runs/{name}_result.json")
            self.assertTrue(result["ok"])
            self.assertEqual(result["deck_sha256"],ctx["deck_sha256"])

    def test_four_fresh_confirmation_cases(self):
        m=self.m
        self.assertEqual({r["name"] for r in m["cases"]},set(sim.POINTS))
        self.assertTrue(m["all_four_fresh_cases_pass"])
        for r in m["cases"]:
            metric=r["metrics"]
            self.assertFalse(r["baseline_reused"])
            self.assertTrue(r["matches_prior_candidate_within_tolerance"])
            self.assertTrue(r["bounded_case_pass"])
            self.assertTrue(r["stimulus_check"]["passed"])
            self.assertTrue(r["sampling_error_pass"])
            for f,v in zip(metric["frames"],sim.VALUES[r["name"]]):
                self.assertTrue(f["frame_pass"])
                self.assertEqual(f["observed_codes_in_window"],[14 if v<0 else 241])
                self.assertEqual((f["comparison_count"],f["write_count"],f["update_count"]),(8,8,8))
            self.assertLessEqual(metric["reference_stress"]["value_v"],.99)
            self.assertLessEqual(metric["comparator_stress_from_saved_internal_nodes"]["value_v"],.99)
            self.assertEqual(metric["CMI_warning_count"],0)
            self.assertFalse(metric["suppression_or_LTE_lines"])
            self.assertFalse(r["gate_checks"]["overlap_above_one_percent_banks"])
            self.assertGreaterEqual(metric["minimum_opposite_rail_deadtime_ps"],99.8)
            self.assertAlmostEqual(r["restore_edges"]["old_off_ns"][0],101.17500025,places=5)
            self.assertAlmostEqual(r["restore_edges"]["new_on_ns"][0],101.27500025,places=5)
            self.assertGreater(r["gate_checks"]["restore_min_one_percent_gate_gap_ps"],0)


if __name__=="__main__":unittest.main()
