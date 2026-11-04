import copy
import contextlib
import gzip
import hashlib
import io
import json
from pathlib import Path
import random
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock

import yaml
import prepare_power_on_managed as p
import power_on_analyze as a
import unpack_power_on as u


class CompressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='.power-pack-test-', dir=str(p.HERE))
        self.root = Path(self.temp.name)
        assert self.root.parent == p.HERE
        self.addCleanup(self.temp.cleanup)

    def config(self):
        return dict(stop_s=260e-9, binary_bound_bytes=30580704,
            collection_cap_bytes=32 * 1024**2, derived_cap_bytes=31 * 1024**2,
            root_reserved_bytes=1024**2)

    def native(self):
        root = self.root / 'native'
        root.mkdir()
        points = 17
        blob = bytes(range(256)) * ((points * 294 * 8 + 255) // 256)
        (root / 'wave.bin').write_bytes(blob[:points * 294 * 8])
        (root / 'wave.columns').write_text('\n'.join(['time'] + ['v' + str(i) for i in range(293)]) + '\n')
        meta = dict(PSF_END=True, points=points, native_points=33, columns=294, last_time_s=260e-9)
        (root / 'wave.meta.json').write_text(json.dumps(meta))
        result = dict(analysis_complete=True, stress_all_native_points=True,
            events_all_native_points=True, all_MOS_pairs=1422, failing_pairs=0, meta=meta,
            electrical_verdict='stress_screen_pass_not_full_qualification')
        (root / 'result.json').write_text(json.dumps(result))
        for name in a.SMALL_FILES:
            if not (root / name).exists():
                (root / name).write_text('[]' if name == 'failing_pairs.json' else 'native evidence\n')
        return root

    def test_multichunk_lossless_sha_and_bounded_decode(self):
        rng = random.Random(92)
        data = rng.randbytes(2 * a.CHUNK + 71)
        source, zipped = self.root / 'wave.bin', self.root / 'wave.bin.gz'
        source.write_bytes(data)
        receipt = a.gzip_stream(str(source), str(zipped), 4 * a.CHUNK)
        self.assertEqual(gzip.decompress(zipped.read_bytes()), data)
        self.assertEqual(receipt['uncompressed_sha256'], hashlib.sha256(data).hexdigest())
        self.assertEqual(receipt['compressed_sha256'], u.digest(zipped))
        self.assertTrue(receipt['roundtrip_verified'])
        self.assertFalse(receipt['extra_decimation'])
        decoded = self.root / 'decoded.bin'
        self.assertTrue(u.decode_wave(zipped, decoded, receipt)['lossless_verified'])
        self.assertEqual(u.digest(decoded), u.digest(source))
        self.assertEqual(source.read_bytes(), data)

    def test_budget_failure_keeps_original_without_completed_delivery(self):
        native = self.native()
        before = {f.name: u.digest(f) for f in native.iterdir()}
        config = self.config()
        config['derived_cap_bytes'] = 16
        target = self.root / 'delivery'
        with self.assertRaises(ValueError):
            a.make_delivery(str(native), str(target), config)
        self.assertFalse((target / 'result.json').exists())
        self.assertEqual(before, {f.name: u.digest(f) for f in native.iterdir()})

    def test_full_delivery_preserves_all_small_native_evidence(self):
        native = self.native()
        before = {f.name: u.digest(f) for f in native.iterdir()}
        out = self.root / 'delivery'
        summary = a.make_delivery(str(native), str(out), self.config())
        self.assertLess(summary['derived_bytes'] + 1024**2, 32 * 1024**2)
        self.assertFalse((out / 'wave.bin').exists())
        self.assertEqual(gzip.decompress((out / 'wave.bin.gz').read_bytes()), (native / 'wave.bin').read_bytes())
        for name in a.SMALL_FILES:
            self.assertEqual((out / name).read_bytes(), (native / name).read_bytes())
        self.assertEqual((out / 'native_result.json').read_bytes(), (native / 'result.json').read_bytes())
        result = json.loads((out / 'result.json').read_text())
        self.assertEqual(result['wave_compression']['native_points'], 33)
        self.assertEqual(result['all_MOS_pairs'], 1422)
        self.assertTrue(result['events_all_native_points'])
        self.assertIsNone(result['startup_accuracy_pass'])
        self.assertFalse(result['native_energy_after200ns_available'])
        self.assertEqual(before, {f.name: u.digest(f) for f in native.iterdir()})

    def test_corruption_and_wrong_hash_rejected(self):
        source, zipped = self.root / 'wave.bin', self.root / 'wave.gz'
        source.write_bytes(b'unchanged waveform' * 1000)
        receipt = a.gzip_stream(str(source), str(zipped), 1024**2)
        wrong = copy.deepcopy(receipt)
        wrong['uncompressed_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            u.decode_wave(zipped, self.root / 'badraw.bin', wrong)
        blob = bytearray(zipped.read_bytes())
        blob[-1] ^= 1
        zipped.write_bytes(blob)
        with self.assertRaises(ValueError):
            u.decode_wave(zipped, self.root / 'badcompressed.bin', receipt)
        wrong = copy.deepcopy(receipt)
        wrong['compressed_sha256'] = u.digest(zipped)
        with self.assertRaises((OSError, EOFError)):
            u.decode_wave(zipped, self.root / 'badfooter.bin', wrong)

    def test_invalid_native_shape_or_coverage_rejected(self):
        native = self.native()
        result = json.loads((native / 'result.json').read_text())
        result['events_all_native_points'] = False
        (native / 'result.json').write_text(json.dumps(result))
        with self.assertRaises(ValueError):
            a.make_delivery(str(native), str(self.root / 'out1'), self.config())
        result['events_all_native_points'] = True
        (native / 'result.json').write_text(json.dumps(result))
        (native / 'wave.bin').write_bytes(b'short')
        with self.assertRaises(ValueError):
            a.make_delivery(str(native), str(self.root / 'out2'), self.config())

    def test_main_keeps_raw_work_outside_collection_and_refuses_overwrite(self):
        native = self.native()
        inputs, derived = self.root / 'inputs', self.root / 'derived'
        inputs.mkdir()
        derived.mkdir()
        (inputs / 'loaded_remote.py').write_bytes(b'frozen reducer stub')
        (inputs / 'test.scs').write_bytes(b'accepted deck')
        config = self.config()
        config.update(input_sha256={'loaded_remote.py': u.digest(inputs / 'loaded_remote.py')},
            allowed_test_sha256=[u.digest(inputs / 'test.scs')])
        (inputs / 'compression_config.json').write_text(json.dumps(config))
        def reduce(command):
            self.assertEqual(Path(command[1]), inputs / 'loaded_remote.py')
            dest = Path(command[command.index('--output-dir') + 1])
            self.assertFalse(dest.is_relative_to(derived))
            for source in native.iterdir():
                shutil.copyfile(source, dest / source.name)
        argv = ['power_on_analyze.py', '--run-dir', str(self.root), '--output-dir', str(derived)]
        with mock.patch.object(sys, 'argv', argv), mock.patch.object(a.subprocess, 'check_call', side_effect=reduce) as call:
            with contextlib.redirect_stdout(io.StringIO()):
                a.main()
            self.assertEqual(call.call_count, 1)
            self.assertTrue((derived / 'result.json').is_file())
            self.assertFalse((derived / 'wave.bin').exists())
            raw = list(self.root.glob('startup-reduce-*/native/wave.bin'))
            self.assertEqual(len(raw), 1)
            self.assertEqual(u.digest(raw[0]), u.digest(native / 'wave.bin'))
            with self.assertRaises(ValueError):
                a.main()
            self.assertEqual(call.call_count, 1)

    def test_complete_evidence_budget_checks_metadata_too(self):
        native = self.native()
        config = self.config()
        config['derived_cap_bytes'] = 1024
        out = self.root / 'overfull-private-delivery'
        with self.assertRaisesRegex(ValueError, 'Complete delivery exceeds'):
            a.make_delivery(str(native), str(out), config)
        self.assertTrue((native / 'wave.bin').is_file())


class RecipeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = p.payloads()

    def test_resource_caps_and_frozen_sources(self):
        config = json.loads(self.outputs['compression_config.json'])
        self.assertEqual(config['collection_cap_bytes'], 32 * 1024**2)
        self.assertEqual(config['derived_cap_bytes'] + config['root_reserved_bytes'], 32 * 1024**2)
        for case in ['dc_core', 'ramp_core']:
            recipe = yaml.safe_load(self.outputs['recipes/' + case + '.yaml'])
            self.assertEqual(recipe['analyzer'], 'power_on_analyze.py')
            self.assertEqual(recipe['resources']['simulation_rss_mib'], 1024)
            self.assertEqual(recipe['resources']['analysis_rss_mib'], 256)
            self.assertEqual(recipe['resources']['threads'], 4)
            self.assertEqual(recipe['expected_stop_s'], 260e-9)
            named = {row['name']: row for row in recipe['inputs']}
            self.assertEqual(named['mapping.json']['source'],
                'verification/sar8_module_audit/sampling/power_on/common/mapping.json')
            self.assertTrue(named['test.scs']['source'].endswith('power_on/' + case + '/test.scs'))
            for name, sha in config['input_sha256'].items():
                self.assertEqual(u.digest(p.b.ROOT / named[name]['source']), sha)
            source = (p.b.ROOT / named['test.scs']['source']).read_text()
            for relative in re.findall(r'(?m)^include "([^/][^"]+)"', source):
                self.assertIn(relative, named)

    def test_frozen_input_hash_and_ambiguous_name_rejected(self):
        with tempfile.TemporaryDirectory(prefix='.power-pack-test-', dir=str(p.HERE)) as root:
            root = Path(root)
            (root / 'one').write_bytes(b'frozen')
            (root / 'test.scs').write_bytes(b'case')
            config = dict(input_sha256={'one': u.digest(root / 'one')},
                          allowed_test_sha256=[u.digest(root / 'test.scs')])
            a.validate_inputs(str(root), config)
            (root / 'one').write_bytes(b'changed')
            with self.assertRaises(ValueError):
                a.validate_inputs(str(root), config)
            config['input_sha256'] = {'../one': 'bad'}
            with self.assertRaises(ValueError):
                a.validate_inputs(str(root), config)

    def test_deterministic_proposal_and_no_registration(self):
        self.assertEqual(self.outputs, p.payloads())
        manifest = json.loads(self.outputs['manifest.json'])
        self.assertFalse(manifest['simulator_invoked'])
        self.assertEqual(manifest['collection_hard_cap_mib'], 32)
        for recipe in manifest['recipes']:
            self.assertLess(recipe['package_bytes_with_current_auto_native_summary'], 32 * 1024**2)


if __name__ == '__main__':
    unittest.main()
