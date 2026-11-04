"""Both-source synthetic managed interface tests; all artifacts below control/."""
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

import supplement_native_export as wrapper
import native_boundary_export as common

OWN = Path(__file__).resolve().parent


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


class SupplementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='_supplement_tests_', dir=OWN)
        cls.root = Path(cls.temp.name).resolve()
        assert cls.root.is_relative_to(OWN)
        cls.executable = cls.root / ('cached_stream.exe' if os.name == 'nt' else 'cached_stream')
        command = ['g++', '-O2', '-std=c++11', str(OWN/'stream_native_boundary.cpp'), '-o', str(cls.executable)]
        if os.name == 'nt':
            command += ['-lpsapi']
        subprocess.run(command, check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def make(self, label='source', end_at_stop=None):
        base = Path(tempfile.mkdtemp(prefix='case_', dir=self.root))
        config = json.loads((OWN/'supplement_export_v1'/label/'manifest.json').read_text())
        source = base/config['source_run_id']
        run = base/'new-analysis'
        for path in [source/'inputs/pwl', source/'raw', run/'inputs', run/'derived']:
            path.mkdir(parents=True, exist_ok=True)
        test = 'simulator lang=spectre\n%s tran stop=200n\n' % config['source_analysis_name']
        test += ''.join('save %s\n' % item['frozen_save_name'] for item in config['signals'])
        (source/'inputs/test.scs').write_text(test)
        (source/'inputs/dut.scs').write_text('// synthetic source; no transistor simulation\n')
        (source/'inputs/pwl/frozen.pwl').write_text('0 .99\n1e-9 .99\n')
        (source/'simulation.state.json').write_text(json.dumps(dict(status='complete', exit_code=0,
            native=dict(native_analysis_pass=True, zero_error_footer=True, warning_codes=['CMI-2751']))))
        (source/'raw/logStatus').write_text('%s PASS\n' % config['source_analysis_name'])
        self.bind(source, run, config)
        for name in ['native_boundary_export.py', 'stream_native_boundary.cpp']:
            shutil.copyfile(OWN/name, run/'inputs'/name)
        raw = self.psf(config, label == 'fixture' if end_at_stop is None else end_at_stop)
        (source/'raw/synthetic.tran.tran').write_text(raw)
        return source, run, config

    def bind(self, source, run, config):
        files = []
        for path in sorted((source/'inputs').rglob('*')):
            if path.is_file():
                files.append(dict(name=path.relative_to(source/'inputs').as_posix(),
                    sha256=digest(path.read_bytes()), bytes=path.stat().st_size))
        recipe = dict(run_id=config['source_run_id'], files=files, kind='simulation', synthetic_only=True)
        signature = digest(json.dumps(recipe, sort_keys=True, separators=(',', ':')).encode())
        (source/'recipe.json').write_text(json.dumps(recipe))
        (source/'registered.json').write_text(json.dumps(dict(recipe_hash=signature, files_complete=True)))
        config['source_recipe_hash'] = signature
        config['source_input_sha256'] = {name: digest((source/'inputs'/name).read_bytes()) for name in ['dut.scs','test.scs']}
        (run/'inputs/supplement_manifest.json').write_text(json.dumps(config))

    @staticmethod
    def psf(config, end_at_stop, group=False, sparse=False):
        names = [item['native_match_name'] for item in config['signals']]
        text = 'HEADER\nSWEEP\n"time" FLOAT DOUBLE\nTRACE\n'
        for j, name in enumerate(names):
            text += ('"%s" GROUP 1\n"actual_leaf" FLOAT DOUBLE\n' % name if group and j == 0
                     else '"%s" FLOAT DOUBLE\n' % name)
        times = [0., 20e-9, 40.8e-9, wrapper.STOP] if end_at_stop else [0., 20e-9, 40.8e-9, wrapper.STOP-1e-12, wrapper.STOP+1e-12, 200e-9]
        text += 'VALUE\n'
        for row, at in enumerate(times):
            text += '"time" %.17g\n' % at
            for col, name in enumerate(names):
                if sparse and row and col:
                    continue
                text += '"%s" %.17g\n' % (name, row*.1 if col == 0 else col*.01)
        return text + 'END\n'

    def invoke(self, source, run):
        def execute(command):
            if command[0] == 'g++':
                shutil.copyfile(self.executable, Path(command[command.index('-o')+1]))
            else:
                subprocess.run(command, check=True, capture_output=True)
        with mock.patch.object(wrapper.subprocess, 'check_call', side_effect=execute):
            wrapper.main(['--run-dir', str(run), '--output-dir', str(run/'derived'), '--source-run-dir', str(source)])

    def test_both_sources_interface_and_no_fabricated_endpoint(self):
        for label in ['source', 'fixture']:
            with self.subTest(label=label):
                source, run, config = self.make(label)
                before = {p.relative_to(source).as_posix(): common.sha(str(p)) for p in source.rglob('*') if p.is_file()}
                self.invoke(source, run)
                after = {p.relative_to(source).as_posix(): common.sha(str(p)) for p in source.rglob('*') if p.is_file()}
                self.assertEqual(before, after)
                output = json.loads((run/'derived/result.json').read_text())
                self.assertEqual(output['points'], 4)
                self.assertEqual(output['selected_voltage_count'], 9 if label == 'source' else 3)
                self.assertEqual(output['source_warning_codes'], ['CMI-2751'])
                self.assertFalse(output['simulation_started'])
                self.assertIsNone(output['acceptance_pass'])
                columns = json.loads((run/'derived/boundary.columns.json').read_text())['columns']
                rows = list(struct.iter_unpack('<'+'d'*len(columns), (run/'derived/boundary.native.bin').read_bytes()))
                self.assertEqual(rows[0][0], 0.)
                if label == 'source':
                    self.assertEqual(rows[-1][0], wrapper.STOP-1e-12)
                    self.assertFalse(output['source_END_scanned'])
                    self.assertFalse(output['coverage']['requested_stop_was_a_native_row'])
                    self.assertGreater(output['coverage']['first_time_marker_beyond_s'], wrapper.STOP)
                else:
                    self.assertEqual(rows[-1][0], wrapper.STOP)
                    self.assertTrue(output['source_END_scanned'])
                initial = json.loads((run/'derived/initial_state.json').read_text())
                self.assertEqual(initial['time_s'], 0)
                self.assertEqual(list(initial['values_v'][c['name']] for c in columns[1:]), list(rows[0][1:]))
                prov = json.loads((run/'derived/source_readonly_provenance.json').read_text())
                self.assertEqual(len(prov['all_registered_source_input_files']), 3)
                self.assertEqual(prov['consumed_native_prefix_sha256'], common.sha(str(source/'raw/synthetic.tran.tran'), prov['consumed_native_prefix_bytes']))
                for name, entry in output['files'].items():
                    blob = (run/'derived'/name).read_bytes()
                    self.assertEqual(digest(blob), entry['sha256'])
                self.assertLess(sum(p.stat().st_size for p in (run/'derived').iterdir()), 32*1024**2)

    def test_group_alias_sparse_native_values(self):
        source, run, config = self.make('fixture')
        (source/'raw/synthetic.tran.tran').write_text(self.psf(config, True, group=True, sparse=True))
        self.invoke(source, run)
        meta = json.loads((run/'derived/native_export.meta.json').read_text())
        self.assertEqual(meta['trace_bindings'][config['signals'][0]['native_match_name']], 'actual_leaf')
        self.assertEqual(meta['held_selected_values_from_native_sparse_updates'], 6)
        rows = list(struct.iter_unpack('<4d', (run/'derived/boundary.native.bin').read_bytes()))
        self.assertEqual([r[2:] for r in rows], [(.01,.02)]*4)

    def test_wrong_source_directory_and_recipe_hash_fail(self):
        source, run, config = self.make()
        with self.assertRaisesRegex(ValueError, 'source run identity'):
            common.source_preflight(str(source.parent), config)
        config['source_recipe_hash'] = '0'*64
        (run/'inputs/supplement_manifest.json').write_text(json.dumps(config))
        with self.assertRaisesRegex(ValueError, 'recipe/registration'):
            self.invoke(source, run)
        self.assertFalse((run/'derived/result.json').exists())

    def test_changed_nested_source_input_is_rejected(self):
        source, run, _ = self.make('fixture')
        (source/'inputs/pwl/frozen.pwl').write_text('0 .98\n1e-9 .98\n')
        with self.assertRaisesRegex(ValueError, 'Registered source input SHA'):
            self.invoke(source, run)

    def test_missing_saved_declaration_is_rejected(self):
        source, run, config = self.make()
        deck = source/'inputs/test.scs'
        deck.write_text(deck.read_text().replace('save '+config['signals'][0]['frozen_save_name']+'\n', ''))
        self.bind(source, run, config)
        with self.assertRaisesRegex(ValueError, 'not declared saved'):
            self.invoke(source, run)

    def test_missing_TRACE_and_first_value_fail(self):
        for change in ['trace','initial']:
            with self.subTest(change=change):
                source, run, config = self.make('fixture')
                path = source/'raw/synthetic.tran.tran'
                name = config['signals'][0]['native_match_name']
                removed = '"'+name+'" '+('FLOAT DOUBLE' if change=='trace' else '0')+'\n'
                path.write_text(path.read_text().replace(removed, '', 1))
                with self.assertRaises(subprocess.CalledProcessError):
                    self.invoke(source, run)
                self.assertFalse((run/'derived/result.json').exists())

    def test_END_before_stop_does_not_fabricate_coverage(self):
        source, run, config = self.make('fixture')
        path = source/'raw/synthetic.tran.tran'
        path.write_text(path.read_text().replace('"time" %.17g' % wrapper.STOP,
                                                '"time" %.17g' % (wrapper.STOP-1e-12)))
        with self.assertRaises(subprocess.CalledProcessError):
            self.invoke(source, run)
        self.assertFalse((run/'derived/result.json').exists())

    def test_exact_source_PASS_and_complete_state_required(self):
        source, run, _ = self.make()
        (source/'raw/logStatus').write_text('different_analysis PASS\n')
        with self.assertRaisesRegex(ValueError, 'Exact source native analysis PASS'):
            self.invoke(source, run)
        source2, run2, _ = self.make('fixture')
        state = source2/'simulation.state.json'
        value = json.loads(state.read_text()); value['status'] = 'running'
        state.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, 'not successfully completed'):
            self.invoke(source2, run2)

    def test_source_output_alias_and_existing_output_rejected(self):
        source, run, _ = self.make()
        with self.assertRaises(ValueError):
            common.validate_paths(str(run), str(source/'derived'), str(source))
        (run/'derived/keep.txt').write_text('preserve this attempt')
        with self.assertRaisesRegex(ValueError, 'must be empty'):
            self.invoke(source, run)
        self.assertEqual((run/'derived/keep.txt').read_text(), 'preserve this attempt')

    def test_cap_and_parser_integrity_guards(self):
        source, run, config = self.make('fixture')
        config['max_parser_output_bytes'] = 8
        (run/'inputs/supplement_manifest.json').write_text(json.dumps(config))
        with self.assertRaises(subprocess.CalledProcessError):
            self.invoke(source, run)
        source2, run2, _ = self.make()
        (run2/'inputs/stream_native_boundary.cpp').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'parser/helper source hash'):
            self.invoke(source2, run2)

    def test_production_packages_bind_different_sources_and_exact_inputs(self):
        signatures = []
        for label in ['source','fixture']:
            folder = OWN/'supplement_export_v1'/label
            config = json.loads((folder/'manifest.json').read_text())
            wrapper.validate_config(config)
            signatures.append(config['source_recipe_hash'])
            recipe = json.loads((folder/'recipe.suggested.yaml').read_text())
            self.assertEqual(recipe['kind'], 'analysis_only')
            self.assertEqual(recipe['source_run_id'], config['source_run_id'])
            self.assertEqual(recipe['resources']['analysis_rss_mib'], 256)
            self.assertEqual(recipe['resources']['threads'], 1)
            self.assertEqual(len(recipe['inputs']), 4)
            for item in recipe['inputs']:
                path = OWN.parents[2]/item['source']
                self.assertEqual(digest(path.read_bytes()), item['sha256'])
        self.assertEqual(len(set(signatures)), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
