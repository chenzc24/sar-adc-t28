"""Synthetic ASCII PSF/managed-directory tests, entirely in this control subtree."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

import native_boundary_export as wrapper

OWN = Path(__file__).resolve().parent


def fake_psf(names=("target", "vdd!"), rows=None, footer=True, header_extra="", sweep="time"):
    if rows is None:
        rows = [(0., [0., .99]), (40.8e-9, [.1, .99]), (41.089515433655805e-9, [1.078642014935018, .99]),
                (41.6e-9, [.2, .99]), (42e-9, [.1, .99])]
    text = 'HEADER\nTYPE\nSWEEP\n"%s" "floatDouble"\nTRACE\n' % sweep
    text += header_extra
    text += ''.join('"%s" "floatDouble"\n' % n for n in names)
    text += 'VALUE\n'
    for t, values in rows:
        text += '"%s" %.17g\n' % (sweep, t)
        text += ''.join('"%s" %.17g\n' % (n, v) for n, v in zip(names, values))
    return text + ('END\n' if footer else '')


class NativeExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = tempfile.TemporaryDirectory(prefix='_synthetic_native_', dir=OWN)
        cls.base = Path(cls.build.name)
        cls.exe = cls.base / ('stream.exe' if os.name == 'nt' else 'stream')
        command = ['g++', '-O2', '-std=c++11', str(OWN / 'stream_native_boundary.cpp'), '-o', str(cls.exe)]
        if os.name == 'nt':
            command += ['-lpsapi']
        subprocess.run(command, check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        cls.build.cleanup()

    def invoke(self, text=None, selected='target\nvdd!\n', budget=1024 * 1024):
        folder = Path(tempfile.mkdtemp(prefix='case_', dir=self.base))
        raw = folder / 'synthetic.tran.tran'
        raw.write_bytes((fake_psf() if text is None else text).encode())
        choice = folder / 'selected.txt'
        choice.write_text(selected)
        output = folder / 'derived'
        output.mkdir()
        result = subprocess.run([str(self.exe), str(raw), str(choice), str(output),
            '4.16e-8', '4.08e-8', '4.16e-8', str(budget), str(256 * 1024)], capture_output=True, text=True)
        return folder, output, result

    def test_native_points_are_unchanged_and_prefix_stops(self):
        _, output, result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        meta = json.loads((output / 'native_export.meta.json').read_text())
        self.assertEqual(meta['points'], 4)
        self.assertEqual(meta['diagnostic_points'], 3)
        self.assertEqual(meta['interpolated_points'], 0)
        self.assertEqual(meta['decimated_points'], 0)
        self.assertFalse(meta['source_END_observed'])
        self.assertEqual(meta['first_time_marker_beyond_s'], 42e-9)
        rows = list(struct.iter_unpack('<ddd', (output / 'boundary.native.bin').read_bytes()))
        self.assertEqual(rows[2], (41.089515433655805e-9, 1.078642014935018, .99))
        self.assertLess(meta['parser_peak_rss_kib'], 256 * 1024)

    def test_missing_required_trace_fails(self):
        _, _, result = self.invoke(selected='not_saved\n')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('missing required TRACE', result.stderr)

    def test_required_first_value_must_be_initialized(self):
        text = fake_psf().replace('"target" 0\n', '', 1)
        _, _, result = self.invoke(text)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('uninitialized selected', result.stderr)

    def test_sparse_updates_and_group_alias_preserve_native_values(self):
        text = '''HEADER
SWEEP
"time" FLOAT DOUBLE
TRACE
"group" GROUP 1
"target" FLOAT DOUBLE
"vdd!" FLOAT DOUBLE
VALUE
"time" 0
"group" 0
"vdd!" .99
"time" 4.08e-8
"group" .1
"time" 4.1089515433655805e-8
"group" 1.078642014935018
"time" 4.16e-8
"group" .2
"time" 4.2e-8
END
'''
        _, output, result = self.invoke(text)
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = list(struct.iter_unpack('<ddd', (output / 'boundary.native.bin').read_bytes()))
        self.assertEqual([row[2] for row in rows], [.99] * 4)
        meta = json.loads((output / 'native_export.meta.json').read_text())
        self.assertEqual(meta['held_selected_values_from_native_sparse_updates'], 3)
        self.assertEqual(meta['interpolated_points'], 0)

    def test_duplicate_value_fails(self):
        text = fake_psf().replace('"target" 0\n', '"target" 0\n"target" 0\n', 1)
        self.assertNotEqual(self.invoke(text)[2].returncode, 0)

    def test_duplicate_trace_fails(self):
        text = fake_psf().replace('TRACE\n', 'TRACE\n"target" "floatDouble"\n', 1)
        self.assertNotEqual(self.invoke(text)[2].returncode, 0)

    def test_nonmonotonic_time_fails(self):
        rows = [(0., [0., .99]), (1e-9, [0., .99]), (.5e-9, [0., .99])]
        self.assertNotEqual(self.invoke(fake_psf(rows=rows))[2].returncode, 0)

    def test_nonfinite_value_fails(self):
        text = fake_psf().replace('"target" 0\n', '"target" nan\n', 1)
        self.assertNotEqual(self.invoke(text)[2].returncode, 0)

    def test_source_must_cover_requested_window(self):
        text = fake_psf(rows=[(0., [0., .99]), (40e-9, [.1, .99])])
        self.assertNotEqual(self.invoke(text)[2].returncode, 0)

    def test_exact_stop_with_END_is_supported(self):
        text = fake_psf(rows=[(0., [0., .99]), (41.6e-9, [.1, .99])])
        _, output, result = self.invoke(text)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads((output / 'native_export.meta.json').read_text())['source_END_observed'])

    def test_non_time_sweep_fails(self):
        self.assertNotEqual(self.invoke(fake_psf(sweep='frequency'))[2].returncode, 0)

    def test_output_budget_failure_is_explicit(self):
        _, _, result = self.invoke(budget=40)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('output budget', result.stderr)

    def test_multiline_PROP_is_not_mistaken_for_trace(self):
        text = fake_psf().replace('"target" "floatDouble"\n',
            '"target" "floatDouble" PROP(\n"units" "V"\n)\n', 1)
        self.assertEqual(self.invoke(text)[2].returncode, 0)

    def test_inline_PROP_is_supported(self):
        text = fake_psf().replace('"target" "floatDouble"\n', '"target" "floatDouble" PROP("units" "V")\n', 1)
        self.assertEqual(self.invoke(text)[2].returncode, 0)

    def test_group_alias_resolves_and_records_actual_trace(self):
        text = fake_psf(names=('leaf', 'vdd!')).replace('TRACE\n', 'TRACE\n"target" GROUP 1\n', 1)
        _, output, result = self.invoke(text)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((output / 'native_export.meta.json').read_text())['trace_bindings']['target'], 'leaf')

    def test_zero_start_required(self):
        text = fake_psf(rows=[(1e-9, [0., .99]), (41.6e-9, [.1, .99])])
        self.assertNotEqual(self.invoke(text)[2].returncode, 0)

    def managed_fixture(self):
        base = Path(tempfile.mkdtemp(prefix='managed_', dir=self.base))
        config = json.loads((OWN / 'native_export_manifest.json').read_text())
        source = base / config['source_run_id']
        run = base / 'new-analysis-only'
        for folder in (source / 'inputs', source / 'raw', run / 'inputs', run / 'derived'):
            folder.mkdir(parents=True, exist_ok=True)
        names = [x['native_match_name'] for x in config['signals']]
        rows = [(t, [i / 100. for i in range(25)]) for t in [0., 40.8e-9, 41.089515433655805e-9, 41.6e-9, 42e-9]]
        raw = source / 'raw' / 'synthetic.tran.tran'
        raw.write_text(fake_psf(names=names, rows=rows))
        recipe = dict(run_id=config['source_run_id'], kind='simulation', synthetic_test=True)
        fingerprint = hashlib.sha256(json.dumps(recipe, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        config['source_recipe_hash'] = fingerprint
        (source / 'recipe.json').write_text(json.dumps(recipe))
        (source / 'registered.json').write_text(json.dumps(dict(recipe_hash=fingerprint, files_complete=True)))
        (source / 'simulation.state.json').write_text(json.dumps(dict(status='complete', exit_code=0,
            native=dict(native_analysis_pass=True, zero_error_footer=True))))
        (source / 'inputs' / 'dut.scs').write_text('// synthetic fixture only\n')
        (source / 'inputs' / 'test.scs').write_text(''.join('save %s\n' % x['frozen_save_name'] for x in config['signals']))
        config['source_input_sha256'] = {n: wrapper.sha(str(source / 'inputs' / n)) for n in ('dut.scs', 'test.scs')}
        (run / 'inputs' / 'native_export_manifest.json').write_text(json.dumps(config))
        shutil.copyfile(OWN / 'stream_native_boundary.cpp', run / 'inputs' / 'stream_native_boundary.cpp')
        return source, run, config

    def test_managed_wrapper_interface_and_source_unchanged(self):
        source, run, _ = self.managed_fixture()
        before = {p.relative_to(source).as_posix(): wrapper.sha(str(p)) for p in source.rglob('*') if p.is_file()}
        wrapper.main(['--run-dir', str(run), '--output-dir', str(run / 'derived'), '--source-run-dir', str(source)])
        after = {p.relative_to(source).as_posix(): wrapper.sha(str(p)) for p in source.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.assertTrue((run / 'derived' / 'result.json').is_file())
        self.assertFalse((run / 'derived' / 'export_result.json').exists())
        output = json.loads((run / 'derived' / 'result.json').read_text())
        provenance = json.loads((run / 'derived' / 'source_readonly_provenance.json').read_text())
        self.assertEqual(output['points'], 4)
        self.assertIsNone(output['acceptance_pass'])
        self.assertTrue(provenance['source_readonly_checks_pass'])
        self.assertEqual(provenance['consumed_native_prefix_sha256'], wrapper.sha(
            str(source / 'raw' / 'synthetic.tran.tran'), provenance['consumed_native_prefix_bytes']))
        self.assertLess(sum(p.stat().st_size for p in (run / 'derived').iterdir()), 32 * 1024 ** 2)

    def test_source_output_alias_is_rejected(self):
        source, run, _ = self.managed_fixture()
        with self.assertRaises(ValueError):
            wrapper.validate_paths(str(run), str(source / 'derived'), str(source))
        with self.assertRaises(ValueError):
            wrapper.validate_paths(str(source), str(source / 'derived'), str(source))

    def test_frozen_source_hash_failure_prevents_execution(self):
        source, _, config = self.managed_fixture()
        (source / 'inputs' / 'dut.scs').write_text('changed synthetic DUT')
        with self.assertRaises(ValueError):
            wrapper.source_preflight(str(source), config)

    def test_declared_missing_save_prevents_execution(self):
        source, _, config = self.managed_fixture()
        deck = source / 'inputs' / 'test.scs'
        deck.write_text(deck.read_text().replace('save XDUT.XCTRL.XTIM.DEC\n', ''))
        config['source_input_sha256']['test.scs'] = wrapper.sha(str(deck))
        with self.assertRaises(ValueError):
            wrapper.source_preflight(str(source), config)


if __name__ == '__main__':
    unittest.main(verbosity=2)
