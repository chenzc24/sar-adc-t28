"""Focused checks for the review data contract, not a simulator regression."""
from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("review_build", ROOT / "scripts/review/build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class ReviewContractTests(unittest.TestCase):
    def setUp(self):
        self.model = build.read_yaml(ROOT / "review/model.yaml")
        self.evidence = build.read_yaml(ROOT / "review/evidence.yaml")

    def test_valid_model(self):
        build.validate(self.model, self.evidence)

    def test_duplicate_id_rejected(self):
        self.model["metrics"].append(deepcopy(self.model["metrics"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            build.validate(self.model, self.evidence)

    def test_cycle_rejected(self):
        self.model["metrics"][0]["parents"] = ["analog"]
        with self.assertRaisesRegex(ValueError, "cycle"):
            build.validate(self.model, self.evidence)

    def test_unknown_reference_rejected(self):
        self.model["steps"][0]["evidence"] = ["not-a-real-run"]
        with self.assertRaisesRegex(ValueError, "unknown step evidence"):
            build.validate(self.model, self.evidence)

    def test_no_evidence_no_claim(self):
        self.model["steps"][0]["evidence"] = []
        with self.assertRaisesRegex(ValueError, "claim requires evidence"):
            build.validate(self.model, self.evidence)

    def test_unit_mismatch_rejected(self):
        self.evidence["records"][3]["observations"][0]["unit"] = "A"
        with self.assertRaisesRegex(ValueError, "unit/reference mismatch"):
            build.validate(self.model, self.evidence)

    def test_false_pass_rejected(self):
        self.evidence["records"][3]["observations"][0]["gate"] = "pass"
        with self.assertRaisesRegex(ValueError, "contradicts"):
            build.validate(self.model, self.evidence)

    def test_stale_propagates_without_rewriting_observations(self):
        original = deepcopy(self.evidence["records"][4]["observations"])
        lock = {"sources": {k: {"path": p, "sha256": hashlib.sha256(build.source_path(p).read_bytes()).hexdigest()} for k, p in self.model["sources"].items()}}
        clean = build.snapshot(self.model, deepcopy(self.evidence), lock)
        self.assertFalse(clean["meta"]["stale_sources"])
        lock["sources"]["audit"]["sha256"] = "0" * 64
        stale = build.snapshot(self.model, deepcopy(self.evidence), lock)
        self.assertEqual(stale["meta"]["stale_sources"], ["audit"])
        record = next(r for r in stale["evidence"] if r["id"] == "current_audit")
        self.assertTrue(record["stale"])
        self.assertEqual(record["observations"], original)

    def test_source_escape_rejected(self):
        with self.assertRaisesRegex(ValueError, "escapes"):
            build.source_path("../unrelated.md")

    def test_circuit_hash_mismatch_rejected(self):
        self.model["circuits"][0]["netlist_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            build.validate(self.model, self.evidence)


if __name__ == "__main__":
    unittest.main()
