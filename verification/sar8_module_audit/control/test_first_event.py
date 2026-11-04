"""First-event package/stream-reducer contracts; local synthetic data only."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

import numpy as np

import first_event_analyze as analyzer
import prepare_first_event as builder

OWN = Path(__file__).resolve().parent


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values, cls.names, cls.review = builder.collected()
        cls.fixture = OWN / 'first_event_v1'
        cls.config = json.loads((OWN / 'native_export_manifest.json').read_text())

    def test_native_receipt_and_peak_and_unchanged_devices(self):
        source = builder.ROOT / 'output/managed_execution/runs' / builder.SOURCE_RUN / 'inputs/dut.scs'
        blob = source.read_bytes()
        self.assertEqual(hashlib.sha256(blob).hexdigest(), self.config['source_input_sha256']['dut.scs'])
        text, leaves, _ = builder.construct_dut(blob.decode().replace('\r\n', '\n'))
        self.assertEqual((self.fixture / 'dut.scs').read_bytes(), text.encode())
        identity = json.loads((self.fixture / 'device_identity.json').read_text())
        self.assertEqual(identity['retained_native_devices'], {k: v for k, v in leaves.items() if v['model'] != 'vsource'})
        self.assertEqual(identity['replay_sources'], {k: v for k, v in leaves.items() if v['model'] == 'vsource'})
        self.assertEqual((identity['native_MOS'], identity['native_passives']), (97, 18))
        self.assertEqual(self.review['files'], 13)
        self.assertEqual(self.review['total_bytes'], 2863230)
        self.assertEqual(self.review['native_peak']['value_v'], 1.078642014935018)
        self.assertEqual(self.review['native_peak']['time_s'], 41.089515433655805e-9)
        self.assertFalse(self.review['current_attribution_available'])

    def test_all_seven_pwl_histories_keep_every_native_knot(self):
        self.assertEqual(len(self.values), 8746)
        text = (self.fixture / 'dut.scs').read_text()
        self.assertEqual(len(builder.check_pwl_paths(text, self.fixture)), 7)
        for label, signal in builder.REPLAYS.items():
            actual = np.loadtxt(self.fixture / 'pwl' / (label + '.pwl'))
            np.testing.assert_array_equal(actual, self.values[:, [0, self.names.index(signal)]])
        self.assertNotIn('inputs/pwl/', text)
        self.assertNotRegex(text, r'(?mi)^\s*(?:ic|nodeset)\b')

    def test_old_double_inputs_and_missing_packaged_pwl_fail(self):
        text = (self.fixture / 'dut.scs').read_text()
        with self.assertRaisesRegex(ValueError, 'package-relative'):
            builder.check_pwl_paths(text.replace('file="pwl/', 'file="inputs/pwl/'), self.fixture)
        # All temporary artifacts stay below the exclusively owned subtree.
        with tempfile.TemporaryDirectory(prefix='_pathcheck_', dir=OWN) as temp:
            self.assertTrue(Path(temp).resolve().is_relative_to(OWN))
            with self.assertRaisesRegex(ValueError, 'missing or outside'):
                builder.check_pwl_paths(text, temp)

    def test_active_outputs_single_driven_and_terminal_kcl_complete(self):
        identity = json.loads((self.fixture / 'device_identity.json').read_text())
        driven = {v['nodes'][0] for v in identity['replay_sources'].values()}
        self.assertEqual(driven, {'XDUT.SAMPLE_INT', 'XDUT.XCTRL.PHI_W', 'XDUT.PHI_U',
            'XDUT.ACTIVE', 'XDUT.XCTRL.XTIM.DEC', 'XDUT.TOPP', 'XDUT.TOPN'})
        measure = json.loads((self.fixture / 'measurement.json').read_text())
        node = 'XDUT.XCTRL.XTIM.X020.N'
        self.assertEqual(len(measure['kcl_terms'][node]), 5)
        self.assertEqual(len(measure['voltage_saves']), 57)
        self.assertEqual(len(measure['current_saves']), 416)
        catalog = measure['terminal_current_catalog']
        for name, part in identity['retained_native_devices'].items():
            if part['model'].startswith(('nch_', 'pch_')):
                for port in range(1, 5):
                    self.assertEqual(catalog[name + ':' + str(port)]['node'], part['nodes'][port - 1])
        self.assertIsNone(measure['acceptance_pass'])
        self.assertEqual(measure['proposed_reproduction_contract']['status'], 'proposal_pending_parent_review')

    def test_suggested_recipe_hashes_limits_and_include_resolution(self):
        recipe = json.loads((self.fixture / 'recipe.suggested.yaml').read_text())
        members = {item['name']: item for item in recipe['inputs']}
        self.assertEqual(len(members), 11)
        self.assertEqual(recipe['entry'], 'test.scs')
        self.assertEqual(recipe['analyzer'], 'first_event_analyze.py')
        total = 0
        for item in members.values():
            path = builder.ROOT / item['source']
            blob = path.read_bytes()
            self.assertEqual(hashlib.sha256(blob).hexdigest(), item['sha256'])
            total += len(blob)
        self.assertLess(total, 32 * 1024**2)
        self.assertEqual(recipe['resources']['simulation_rss_mib'], 1024)
        self.assertEqual(recipe['resources']['analysis_rss_mib'], 256)
        self.assertEqual(recipe['resources']['threads'], 1)
        self.assertIn('+mt=1', recipe['spectre_args'])
        self.assertEqual(recipe['expected_stop_s'], self.values[-1, 0])
        for entry in builder.check_pwl_paths((self.fixture / 'dut.scs').read_text(), self.fixture):
            self.assertIn(entry['name'], members)


def configuration():
    return dict(voltage_saves=['target', 'vdd!'], current_saves=['load:1', 'inv:2'],
        kcl_terms={'target': ['load:1', 'inv:2']}, critical_kcl_nodes=['target'],
        diagnostic_voltage_columns=['target', 'vdd!'], diagnostic_current_columns=['load:1', 'inv:2'],
        diagnostic_start_s=0., diagnostic_stop_s=2e-9, source_history_stop_s=2e-9,
        max_derived_binary_bytes=1024, expected_native_peak=dict(node='target', value_v=1.078642014935018, time_s=1e-9),
        expected_initial_state=dict(values_v={'target': 0., 'vdd!': .99}),
        expected_edges={'target': dict(direction=1, time_s=[.458910376e-9])},
        proposed_reproduction_contract={'status': 'proposal_pending_parent_review'}, scope='synthetic reducer test')


def synthetic_psf():
    names = ['target', 'vdd!', 'load:1', 'inv:2']
    rows = [(0., [0., .99, 1e-6, -1e-6]),
            (1e-9, [1.078642014935018, .99, 2e-6, -2e-6]),
            (2e-9, [.1, .99, 3e-6, -3e-6])]
    text = 'HEADER\nSWEEP\n"time" FLOAT DOUBLE\nTRACE\n'
    text += ''.join('"%s" FLOAT DOUBLE\n' % n for n in names)
    text += 'VALUE\n'
    for t, vals in rows:
        text += '"time" %.17g\n' % t
        text += ''.join('"%s" %.17g\n' % (n, v) for n, v in zip(names, vals))
    return text + 'END\n'


class ReducerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='_first_event_', dir=OWN)
        self.base = Path(self.temp.name).resolve()
        self.assertTrue(self.base.is_relative_to(OWN))
        self.addCleanup(self.temp.cleanup)

    def invoke(self, text=None, cfg=None):
        case = self.base / str(len(list(self.base.iterdir())))
        case.mkdir()
        raw = case / 'synthetic.tran.tran'
        raw.write_bytes((synthetic_psf() if text is None else text).encode('ascii'))
        result = analyzer.summarize(str(raw), configuration() if cfg is None else cfg, str(case))
        return result, case

    def test_signed_current_kcl_and_exact_native_rows(self):
        result, folder = self.invoke()
        self.assertEqual(result['native_points'], 3)
        self.assertEqual(result['peak_error_v'], 0.)
        self.assertEqual(result['peak_time_error_s'], 0.)
        self.assertEqual(result['node_kcl']['target']['max_abs_a'], 0.)
        rows = list(struct.iter_unpack('<6d', (folder / 'peak.native.bin').read_bytes()))
        self.assertEqual(rows[1], (1e-9, 1.078642014935018, .99, 2e-6, -2e-6, 0.))
        self.assertEqual(result['max_native_gap_s'], 1e-9)
        self.assertIsNone(result['acceptance_pass'])
        self.assertFalse(result['circuit_repair_claim'])

    def test_current_residual_is_reported_not_hidden(self):
        text = synthetic_psf().replace('"inv:2" -1.9999999999999999e-06', '"inv:2" -1.5e-6')
        self.assertNotEqual(text, synthetic_psf())
        result, _ = self.invoke(text)
        self.assertAlmostEqual(result['node_kcl']['target']['max_abs_a'], .5e-6)
        self.assertAlmostEqual(result['peak_snapshot']['critical_kcl_a']['target'], .5e-6)

    def test_sparse_native_updates_hold_previous_values(self):
        text = synthetic_psf()
        # Only the zero-time supply initialization is required.
        first = text.index('"vdd!" 0.98999999999999999')
        text = text[:first + 1] + text[first + 1:].replace('"vdd!" 0.98999999999999999\n', '')
        result, folder = self.invoke(text)
        rows = list(struct.iter_unpack('<6d', (folder / 'peak.native.bin').read_bytes()))
        self.assertEqual([row[2] for row in rows], [.99] * 3)
        self.assertEqual(result['held_values_from_sparse_updates'], 2)

    def test_group_alias_replays_selected_name_from_leaf(self):
        text = synthetic_psf().replace('"target" FLOAT DOUBLE', '"target" GROUP 1\n"leaf" FLOAT DOUBLE', 1)
        text = text.replace('"target" 0\n', '"leaf" 0\n')
        text = text.replace('"target" 1.078642014935018', '"leaf" 1.078642014935018')
        text = text.replace('"target" 0.10000000000000001', '"leaf" 0.10000000000000001')
        result, _ = self.invoke(text)
        self.assertEqual(result['trace_bindings']['target'], 'leaf')
        self.assertEqual(result['peak_error_v'], 0.)

    def test_missing_trace_or_initial_current_fails(self):
        with self.assertRaisesRegex(ValueError, 'TRACE'):
            self.invoke(synthetic_psf().replace('"load:1" FLOAT DOUBLE\n', ''))
        with self.assertRaisesRegex(ValueError, 'Uninitialized'):
            self.invoke(synthetic_psf().replace('"load:1" 9.9999999999999995e-07\n', '', 1))

    def test_duplicate_update_or_time_fails(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate selected'):
            self.invoke(synthetic_psf().replace('"target" 0\n', '"target" 0\n"target" 0\n', 1))
        with self.assertRaisesRegex(ValueError, 'Non-increasing'):
            self.invoke(synthetic_psf().replace('"time" 2.0000000000000001e-09', '"time" 1e-9'))

    def test_no_END_nonfinite_and_wrong_sweep_fail(self):
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            self.invoke(synthetic_psf().replace('END\n', ''))
        with self.assertRaisesRegex(ValueError, 'Invalid native scalar'):
            self.invoke(synthetic_psf().replace('"target" 0\n', '"target" nan\n', 1))
        with self.assertRaisesRegex(ValueError, 'TRACE/time'):
            self.invoke(synthetic_psf().replace('"time"', '"frequency"'))

    def test_cap_fails_without_result_or_decimation(self):
        cfg = configuration()
        cfg['max_derived_binary_bytes'] = 47
        with self.assertRaisesRegex(ValueError, 'cap'):
            self.invoke(cfg=cfg)
        self.assertFalse(list(self.base.rglob('result.json')))

    def managed(self, native_success=True):
        run = self.base / 'managed'
        (run / 'raw').mkdir(parents=True)
        (run / 'inputs').mkdir()
        (run / 'derived').mkdir()
        state = dict(status='complete', exit_code=0, native=dict(native_analysis_pass=native_success,
            zero_error_footer=native_success, warning_codes=['CMI-2011'], effective_settings={'mode': 'synthetic'}))
        (run / 'simulation.state.json').write_text(json.dumps(state))
        (run / 'raw/logStatus').write_text('tran_first PASS\n')
        (run / 'raw/synthetic.tran.tran').write_text(synthetic_psf())
        (run / 'inputs/measurement.json').write_text(json.dumps(configuration()))
        command = [sys.executable, '-B', str(OWN / 'first_event_analyze.py'), '--run-dir', str(run),
                   '--output-dir', str(run / 'derived')]
        return run, command

    def test_managed_interface_preserves_warning_and_acceptance_null(self):
        run, command = self.managed()
        completed = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads((run / 'derived/result.json').read_text())
        self.assertTrue(result['CMI_warning_present'])
        self.assertEqual(result['native_warning_codes'], ['CMI-2011'])
        self.assertIsNone(result['acceptance_pass'])
        self.assertFalse(result['circuit_repair_claim'])
        frozen = (run / 'derived/result.json').read_bytes()
        self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
        self.assertEqual((run / 'derived/result.json').read_bytes(), frozen)

    def test_native_failure_gate_writes_no_result(self):
        run, command = self.managed(native_success=False)
        self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
        self.assertFalse((run / 'derived/result.json').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
