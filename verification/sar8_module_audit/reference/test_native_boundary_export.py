"""Synthetic native PSF fixtures only; never opens an ADC raw waveform."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
from unittest import mock
import zlib

import native_boundary_export as exporter

HERE = Path(__file__).resolve().parent
CPP = HERE / "native_boundary_stream.cpp"
COMPILER = Path("C:/Program Files/mingw64/bin/g++.exe")
if not COMPILER.exists():
    COMPILER = Path(shutil.which("g++") or "g++")

PSF = '''HEADER
SWEEP
"time" "time"
TRACE
"CAP_REQ" "V"
"g1" GROUP 1
"STATE" "V" PROP(
"units" "V"
)
VALUE
"time" 0
"CAP_REQ" 0
"g1" 1
"time" 1e-12
"CAP_REQ" 9
"g1" -2
"time" 2e-12
"CAP_REQ" 0
"time" 3e-12
"CAP_REQ" 0
END
'''


def rows(blob, columns):
    assert len(blob) % (8 * columns) == 0
    return list(struct.iter_unpack("<" + "d" * columns, blob))


class NativeExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="_native_boundary_tests_", dir=HERE)
        cls.root = Path(cls.temp.name)
        cls.exe = cls.root / ("stream.exe" if os.name == "nt" else "stream")
        subprocess.run([str(COMPILER), "-O2", "-std=c++11", str(CPP), "-o", str(cls.exe)],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.case = self.root / self._testMethodName
        self.case.mkdir()

    def parse(self, text=PSF, boundary=None, diagnostic=None, diag_limit=4096, stop=2e-12):
        source = self.case / "input.psf"
        source.write_text(text, encoding="utf-8")
        b = self.case / "boundary.list"
        d = self.case / "diagnostic.list"
        b.write_text("\n".join(boundary or ["cap_req", "state"]) + "\n")
        d.write_text(diagnostic or "1 cap_req\n0 not_saved\n")
        prefix = self.case / "native"
        process = subprocess.run([str(self.exe), str(source), str(b), str(d), str(prefix),
                                  str(stop), "0", str(stop), str(diag_limit), "2e-12"],
                                 capture_output=True)
        return process, prefix

    def test_every_native_point_and_sparse_group_values_preserved(self):
        process, prefix = self.parse()
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(rows(process.stdout, 3), [(0., 0., 1.), (1e-12, 9., -2.), (2e-12, 0., -2.)])
        meta = json.loads(prefix.with_suffix(".meta.json").read_text())
        self.assertFalse(meta["interpolated"])
        self.assertFalse(meta["decimated"])
        self.assertEqual(meta["native_points_exported"], 3)
        self.assertFalse(meta["source_PSF_END_seen"])
        self.assertEqual(meta["optional_diagnostics_absent"], ["not_saved"])
        self.assertEqual(rows(prefix.with_suffix(".diagnostic.f64le").read_bytes(), 2),
                         [(0., 0.), (1e-12, 9.), (2e-12, 0.)])

    def test_missing_required_boundary_fails(self):
        process, _ = self.parse(boundary=["cap_req", "missing_required"])
        self.assertNotEqual(process.returncode, 0)
        self.assertIn(b"missing required signal missing_required", process.stderr)
        self.assertEqual(process.stdout, b"")

    def test_missing_required_diagnostic_fails(self):
        process, _ = self.parse(diagnostic="1 missing_diagnostic\n")
        self.assertNotEqual(process.returncode, 0)
        self.assertIn(b"missing required diagnostic", process.stderr)

    def test_diagnostic_budget_fails_before_overwrite(self):
        process, prefix = self.parse(diag_limit=1)
        self.assertNotEqual(process.returncode, 0)
        self.assertIn(b"budget exceeded", process.stderr)
        self.assertEqual(prefix.with_suffix(".diagnostic.f64le").stat().st_size, 0)

    def test_no_new_endpoint_is_inserted(self):
        process, _ = self.parse(stop=2.5e-12)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual([r[0] for r in rows(process.stdout, 3)], [0, 1e-12, 2e-12])

    def test_missing_zero_initial_history_fails(self):
        process, _ = self.parse(PSF.replace('"time" 0\n', '"time" 5e-13\n', 1))
        self.assertNotEqual(process.returncode, 0)
        self.assertIn(b"initial point is not t=0", process.stderr)

    def test_uninitialized_required_value_fails(self):
        process, _ = self.parse(PSF.replace('"g1" 1\n', "", 1))
        self.assertNotEqual(process.returncode, 0)
        self.assertIn(b"uninitialized required", process.stderr)

    def test_nonfinite_native_value_fails(self):
        process, _ = self.parse(PSF.replace('"CAP_REQ" 9', '"CAP_REQ" nan'))
        self.assertNotEqual(process.returncode, 0)
        self.assertIn(b"bad native value", process.stderr)

    def test_nonmonotonic_time_fails(self):
        process, _ = self.parse(PSF.replace('"time" 1e-12', '"time" 0'))
        self.assertNotEqual(process.returncode, 0)
        self.assertIn(b"time not strictly increasing", process.stderr)

    def test_incomplete_history_fails(self):
        process, _ = self.parse(PSF[:PSF.index('"time" 1e-12')] + "END\n")
        self.assertNotEqual(process.returncode, 0)
        self.assertIn(b"incomplete extraction history", process.stderr)

    def test_source_end_exactly_at_cutoff(self):
        text = PSF[:PSF.index('"time" 3e-12')] + "END\n"
        process, prefix = self.parse(text)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertTrue(json.loads(prefix.with_suffix(".meta.json").read_text())["source_PSF_END_seen"])

    def test_output_cannot_be_source_or_ancestor(self):
        source, run = self.case / "source", self.case / "run"
        source.mkdir()
        run.mkdir()
        for output in [source, source / "derived", self.case]:
            with self.subTest(output=output), self.assertRaises(ValueError):
                exporter.validate_paths(str(run), str(output), str(source))
        self.assertEqual(list(source.iterdir()), [])

    def test_nested_run_source_rejected(self):
        source = self.case / "source"
        run = source / "new"
        run.mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "disjoint"):
            exporter.validate_paths(str(run), str(run / "derived"), str(source))

    def test_json_readback_unicode_path(self):
        source = self.case / "source"
        (source / "inputs").mkdir(parents=True)
        relative = json.loads(r'{"path":"inputs/cap_\u03c6.scs"}')["path"]
        target = source / relative
        target.write_text("// generated Unicode path fixture only\n", encoding="utf-8")
        self.assertIsInstance(relative, exporter.STRING_TYPES)
        self.assertEqual(exporter.safe_file(str(source), relative), str(target.resolve()))

    def test_output_symlink_into_source_rejected(self):
        source, run = self.case / "source", self.case / "run"
        source.mkdir()
        run.mkdir()
        link = run / "derived"
        try:
            link.symlink_to(source, target_is_directory=True)
        except OSError:
            self.skipTest("symlink creation unavailable to this Windows test account")
        with self.assertRaises(ValueError):
            exporter.validate_paths(str(run), str(link), str(source))

    def wrapper_fixture(self):
        source, run = self.case / "source_case", self.case / "new_case"
        (source / "raw").mkdir(parents=True)
        (source / "inputs").mkdir()
        (run / "inputs").mkdir(parents=True)
        (source / "raw" / "tran_perf.tran.tran").write_text(PSF)
        (source / "raw" / "logStatus").write_text("tran_perf PASS\n")
        (source / "simulation.state.json").write_text(json.dumps({"status": "complete", "exit_code": 0}))
        (source / "inputs" / "dut.scs").write_text("// synthetic source only\n")
        manifest = json.loads((HERE / "native_boundary_export.json").read_text())
        manifest.update(source_run_id=source.name, source_input_hashes={
            "inputs/dut.scs": exporter.digest(str(source / "inputs" / "dut.scs"))},
            boundary_end_s=2e-12, minimum_cover_s=2e-12, diagnostic_start_s=0.,
            diagnostic_end_s=2e-12, required_boundary_signals=["cap_req", "state"],
            diagnostic_signals=[{"name": "cap_req", "required": True}, {"name": "absent", "required": False}])
        (run / "inputs" / "native_boundary_export.json").write_text(json.dumps(manifest))
        shutil.copyfile(CPP, run / "inputs" / CPP.name)
        return source, run, manifest

    def test_wrapper_lossless_gzip_and_source_unchanged(self):
        source, run, _ = self.wrapper_fixture()
        before = {str(p.relative_to(source)): p.read_bytes() for p in source.rglob("*") if p.is_file()}
        with mock.patch.dict(os.environ, {"CXX": str(COMPILER)}):
            result = exporter.export(str(run), str(run / "derived"), str(source))
        after = {str(p.relative_to(source)): p.read_bytes() for p in source.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        archive = (run / "derived" / "boundary.f64le.gz").read_bytes()
        native = zlib.decompress(archive, 31)
        self.assertEqual(rows(native, 3), [(0., 0., 1.), (1e-12, 9., -2.), (2e-12, 0., -2.)])
        self.assertEqual(hashlib.sha256(native).hexdigest(), result["boundary_uncompressed_sha256"])
        self.assertLess(exporter.output_size(str(run / "derived")), 32 * 1024 * 1024)
        self.assertTrue(result["analysis_complete"])
        self.assertEqual(result["electrical_verdict"], "not_inferred")

    def test_frozen_source_hash_mismatch_fails_before_outputs(self):
        source, run, _ = self.wrapper_fixture()
        (source / "inputs" / "dut.scs").write_text("// changed\n")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            exporter.export(str(run), str(run / "derived"), str(source))
        self.assertFalse((run / "derived").exists())

    def test_compressed_budget_rejects_without_decimation_or_source_writes(self):
        source, run, manifest = self.wrapper_fixture()
        manifest["max_boundary_gzip_bytes"] = 32
        (run / "inputs" / "native_boundary_export.json").write_text(json.dumps(manifest))
        before = {str(p.relative_to(source)): p.read_bytes() for p in source.rglob("*") if p.is_file()}
        with mock.patch.dict(os.environ, {"CXX": str(COMPILER)}), self.assertRaisesRegex(ValueError, "budget exceeded"):
            exporter.export(str(run), str(run / "derived"), str(source))
        self.assertFalse((run / "derived" / "result.json").exists())
        self.assertLessEqual((run / "derived" / "boundary.f64le.gz").stat().st_size, 32)
        self.assertEqual(before, {str(p.relative_to(source)): p.read_bytes() for p in source.rglob("*") if p.is_file()})

    def test_manifest_forbids_32mib_or_unknown_times(self):
        m = json.loads((HERE / "native_boundary_export.json").read_text())
        exporter.validate_manifest(m)
        changed = copy.deepcopy(m)
        changed["max_total_output_bytes"] = 32 * 1024 * 1024
        with self.assertRaisesRegex(ValueError, "below32MiB"):
            exporter.validate_manifest(changed)
        changed = copy.deepcopy(m)
        changed["boundary_end_s"] = None
        with self.assertRaisesRegex(ValueError, "undefined extraction time"):
            exporter.validate_manifest(changed)


if __name__ == "__main__":
    unittest.main()
