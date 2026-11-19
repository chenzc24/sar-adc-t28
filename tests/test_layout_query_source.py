import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from Layout.query_source import CACHE, CURRENT, DESIGN, PROFILE, resolve


def digest(data):
    return hashlib.sha256(data).hexdigest()


class LayoutQuerySources(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.comparator = b"comparator stream"
        self.review = b"review stream"
        self.filled = b"filled stream"
        self.cdl = b"independent CDL"
        self.write(DESIGN, {
            "technology": "T28",
            "cells": {
                "comparator": {
                    "core": "comp_core", "view": "layout", "core_evidence": "comp-current",
                    "report": "Layout/results/comparator.json",
                },
                "cdac": {
                    "filled": "cdac_top", "fill_masters": ["utility_fill"],
                    "paired_review": {
                        "view": "review_view", "physical_evidence": "dac-review",
                        "report": "Layout/results/cdac.json",
                    },
                },
            },
        })
        self.current = {
            "comparator": {"physical_evidence": "comp-current", "geometry_sha256": "a" * 64},
            "cdac": {
                "view": "stacked_view", "physical_evidence": "dac-filled",
                "trial_evidence": "dac-trial", "gds_sha256": digest(self.filled),
                "functional_geometry_sha256": "c" * 64,
            },
        }
        self.write(CURRENT, self.current)
        self.write(Path("Layout/results/comparator.json"), {
            "core": "comp_core", "library": "TEST", "physical_evidence": "comp-current",
            "gds_sha256": digest(self.comparator), "geometry_sha256": "a" * 64,
        })
        self.write(Path("Layout/results/cdac.json"), {
            "cell": "cdac_top", "library": "TEST", "view": "review_view",
            "official_verification_evidence": "dac-review",
            "published_geometry_sha256": {"cdac_top": "b" * 64},
            "independent_review_stream_sha256": digest(self.review),
            "independent_reference_cdl_sha256": digest(self.cdl),
        })
        self.write(PROFILE, {"metals": {}, "vias": {}})

    def write(self, path, data):
        absolute = self.root / path
        absolute.parent.mkdir(parents=True, exist_ok=True)
        absolute.write_text(json.dumps(data), encoding="utf-8")

    def bundle(self, directory, stream, fill=False):
        directory.mkdir(parents=True, exist_ok=True)
        if stream == self.comparator:
            top, geometry, view = "comp_core", "a" * 64, "layout"
        else:
            top = "cdac_top"
            geometry, view = ("d" * 64, "layout") if fill else ("b" * 64, "review_view")
        manifest = {
            "top": top, "library": "TRIAL" if fill else "TEST", "oa_view": view,
            "gds": {
                "sha256": digest(stream),
                "structural_sha256": {top: geometry},
                "labels": {"utility_fill": []} if fill else {},
            },
        }
        if fill:
            manifest["derived_from"] = {"stage": "combined", "plan_evidence": "dac-trial"}
            manifest["functional_geometry_sha256"] = "c" * 64
        else:
            manifest["source_sha256"] = {"design-reference.cdl": digest(self.cdl)}
        (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (directory / "fixture.gds").write_bytes(stream)
        (directory / "reference.cdl").write_bytes(self.cdl)

    def test_ambiguous_selector_lists_candidates(self):
        result, code = resolve("cdac", root=self.root)
        self.assertEqual((code, result["status"]), (3, "ambiguous"))
        self.assertEqual(result["candidates"], ["cdac/review", "cdac/filled"])

    def test_offline_lookup_reports_missing_members(self):
        with patch("Layout.query_source.fetch_bundle") as fetch:
            result, code = resolve("comparator/current", root=self.root)
        self.assertEqual((code, result["status"]), (3, "missing"))
        self.assertEqual(result["missing"], ["manifest", "gds", "cdl"])
        fetch.assert_not_called()

    def test_current_comparator_tracks_recorded_identity(self):
        self.bundle(self.root / CACHE / "comp-current", self.comparator)
        result, code = resolve("comparator/current", root=self.root)
        self.assertEqual((code, result["status"]), (0, "resolved"))
        self.assertEqual(result["files"]["gds"]["sha256"], digest(self.comparator))
        self.current["comparator"]["physical_evidence"] = "comp-replacement"
        self.write(CURRENT, self.current)
        result, code = resolve("comparator/current", root=self.root)
        self.assertEqual((code, result["status"]), (1, "mismatch"))

    def test_filled_scope_preserves_design_and_stream_identities(self):
        self.bundle(self.root / CACHE / "dac-review", self.review)
        self.bundle(self.root / CACHE / "dac-filled", self.filled, fill=True)
        review, review_code = resolve("cdac/review", root=self.root)
        filled, filled_code = resolve("cdac/current", root=self.root)
        self.assertEqual((review_code, filled_code), (0, 0))
        self.assertEqual(filled["selected"], "cdac/filled")
        self.assertEqual((review["target"]["view"], filled["target"]["view"]), ("review_view", "stacked_view"))
        self.assertEqual((filled["target"]["library"], filled["evidence"]["library"]), ("TEST", "TRIAL"))
        self.assertEqual(filled["evidence"]["geometry_sha256"], "d" * 64)
        self.assertEqual(filled["evidence"]["functional_geometry_sha256"], "c" * 64)
        (self.root / CACHE / "dac-filled/fixture.gds").write_bytes(self.review)
        result, code = resolve("cdac/filled", root=self.root)
        self.assertEqual((code, result["status"]), (1, "mismatch"))

    def test_collect_checks_inputs_and_repairs_a_missing_member(self):
        def fetch(identity, directory):
            self.assertEqual(identity, "dac-review")
            self.bundle(directory, self.review)

        def fetch_wrong_cdl(identity, directory):
            fetch(identity, directory)
            (directory / "reference.cdl").write_bytes(b"different reference")

        cache = self.root / CACHE / "dac-review"
        with patch("Layout.query_source.fetch_bundle", side_effect=fetch_wrong_cdl):
            result, code = resolve("cdac/review", root=self.root, collect=True)
        self.assertEqual((code, result["status"]), (1, "mismatch"))
        self.assertFalse(cache.exists())
        with patch("Layout.query_source.fetch_bundle", side_effect=fetch):
            result, code = resolve("cdac/review", root=self.root, collect=True)
            self.assertEqual((code, result["status"]), (0, "resolved"))
            (cache / "reference.cdl").unlink()
            result, code = resolve("cdac/review", root=self.root, collect=True)
        self.assertEqual((code, result["status"]), (0, "resolved"))
        self.assertEqual((cache / "reference.cdl").read_bytes(), self.cdl)
