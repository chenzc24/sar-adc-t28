"""Focused R2 OA-adoption checks, not full ADC signoff."""
import hashlib
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts/integration"))
from join_r2 import OUT,VAS,TOP,TB,COMMIT,GATE,top,bench,check_split,audit_export,r1


class R2(unittest.TestCase):
    def test_exact_tested_model_bodies(self):
        check_split()
        for p in VAS.values():self.assertEqual(p.read_text().count("endmodule"),1)

    def test_native_graph_and_references_unchanged(self):
        old={p.name:p for p in r1.top().parts};new={p.name:p for p in top().parts}
        self.assertEqual(set(new)-set(old),{"XGCOMMIT"})
        for name,p in old.items():
            q=new[name]
            if name.startswith(("XGP","XGN")):
                self.assertEqual(q.master,GATE);self.assertEqual(q.params,p.params)
                self.assertEqual({k:v for k,v in q.terms.items() if k!="COMMIT"},p.terms)
                self.assertEqual(q.terms["COMMIT"],"GCOMMIT")
            else:self.assertEqual(p,q)
        parts={p.name:p for p in bench().parts}
        for side in "PN":
            self.assertEqual(parts["RREF"+side].params["r"],"50")
            self.assertEqual(parts["CREF"+side].params["c"],"4p")
        self.assertEqual(parts["XDUT"].master,TOP)

    def test_saved_OA_export_and_readback(self):
        path=OUT/"exports/primary/input.scs"
        self.assertTrue(audit_export(path.read_text())["top_electrical_statements_match_tested_alignment"])
        for name in (TOP,TB):
            self.assertFalse(r1.read_json(OUT/f"oa/{name}_markers.json"))
        for name,path in VAS.items():
            self.assertEqual(r1.sha(path),r1.sha(OUT/f"oa/{name}_remote.va"))

    def test_results_and_failure_preserved(self):
        manifest=r1.read_json(ROOT/"verification/integration/join_r2_results.json")
        self.assertFalse(manifest["qualified"])
        self.assertEqual({c["name"] for c in manifest["cases"]},{"nfull","nhalf"})
        for relative,digest in manifest["source_text_LF_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT/relative).read_text(encoding="utf-8").encode()).hexdigest(),digest)
        self.assertEqual(manifest["OA_postflight"]["frozen_cells_matched"],34)
        for c in manifest["cases"]:
            self.assertTrue(c["metrics"]["result_ok"])
            self.assertTrue(all(f["frame_pass"] for f in c["metrics"]["frames"]))
            self.assertFalse(c["metrics"]["simultaneous_gate_enable_banks"])
            self.assertGreaterEqual(c["metrics"]["minimum_opposite_rail_deadtime_ps"],99.8)
            for h in c["handoffs"]:
                for k in ("on_spread_ps","off_spread_ps"):
                    if h[k] is not None:self.assertLess(h[k],.1)
            for k in ("reference_max_v","comparator_max_v"):
                self.assertLess(c["phase_stress"]["conversion"][k],.99)
            for k,delta in c["prior_alignment_deltas"].items():
                self.assertLess(abs(delta),.02 if k.endswith("mv") else 50e-6)
            if c["name"]=="nfull":
                self.assertFalse(c["metrics"]["bounded_join_pass"])
                self.assertGreater(c["phase_stress"]["second_acquisition"]["comparator_max_v"],.99)
            else:self.assertTrue(c["metrics"]["bounded_join_pass"])


if __name__=="__main__":unittest.main()
