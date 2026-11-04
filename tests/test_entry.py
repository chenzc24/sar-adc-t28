"""Exercise real package creation and identity protection without an SSH session."""
import importlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

entry = importlib.import_module('tools.saradc.__main__')


class EntryChecks(unittest.TestCase):
    def setUp(self):
        self.original_root = entry.ROOT
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def test_current_physical_sources_and_all_frozen_cases(self):
        self.assertEqual(entry.check()['exact_subcircuits'],49)
        self.assertEqual(entry.check()['locked_cases'],7)

    def test_all_case_packages_keep_declared_dependencies_and_frozen_bytes(self):
        # Package real inputs in a temporary checkout; only execution stays local.
        root = Path(self.temp.name)
        for folder in ['design','specs','tb','tools']:
            shutil.copytree(self.original_root / folder, root / folder,
                            ignore=shutil.ignore_patterns('__pycache__'))
        with patch.object(entry,'ROOT',root):
            for name in entry.read('specs/tests.json'):
                recipe = entry.prepare(name)
                data = entry.read(recipe)
                for row in data['inputs']:
                    self.assertEqual(entry.digest(root / row['source']),row['sha256'])
            path = entry.prepare('tt_short',run_id='test-split',split_design=True)
            data = entry.read(path)
            members = {r['name'] for r in data['inputs']}
            self.assertIn('top/adc_top.scs',members)
            self.assertIn('xtor/comparator/comparator.scs',members)
            path = entry.prepare('mc_comparator_tt',run_id='test-seed',seed=4501)
            deck = root / path
            self.assertIn('seed=4501',deck.with_name('test.scs').read_text())
            self.assertEqual(json.loads(deck.with_name('context.json').read_text())['seed'],4501)
            with self.assertRaisesRegex(ValueError,'differs'):
                entry.prepare('mc_comparator_tt',run_id='test-seed',seed=4502)

    def test_existing_identity_cannot_replace_a_prepared_input(self):
        # The public parser validates run IDs through the existing engine before writes.
        with self.assertRaises(ValueError):
            entry.prepare('tt_short',run_id='../escape')


if __name__ == '__main__':
    unittest.main()
