"""Safety boundaries for comparator source references and OA dispatch."""
import collections
import contextlib
import io
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from Layout import __main__ as cli
from Layout.design import comparator
from Layout.project import ROOT


class ComparatorLayoutTests(unittest.TestCase):
    def test_reference_tracks_source_and_rejects_unsupported_fingers(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root/'design/xtor/comparator/comparator.scs'
            source.parent.mkdir(parents=True)
            text = (ROOT/'design/xtor/comparator/comparator.scs').read_text(encoding='utf-8')
            source.write_text(text, encoding='utf-8')
            with patch.object(comparator, 'ROOT', root), contextlib.redirect_stdout(io.StringIO()):
                comparator.generate()
                reference = (root/'work/layout/comparator/comparator-reference.cdl').read_text()
                self.assertIn('.SUBCKT sar_strongarm_t28_core CLK OUTN OUTP VDD VINN VINP VSS', reference)
                self.assertEqual(sum(line.startswith('M') for line in reference.splitlines()), 11)
                source.write_text(text.replace('nf=1', 'nf=2', 1), encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'one finger'):
                    comparator.generate()

    def test_generator_draws_each_schematic_device_as_its_named_fingers(self):
        source = (ROOT/'design/xtor/comparator/comparator.scs').read_text(encoding='utf-8')
        widths = {name: 1.0 if width == '1u' else 0.5 for name, width in
                  re.findall(r'^\s*(M\w+) \([^)]*\) \w+ l=\S+ w=(\S+)', source, re.M)}
        generator = (ROOT/'Layout/design/comparator.il').read_text(encoding='utf-8')
        # Every instance is one W=0.5u finger named DEVICE or DEVICE_k.
        fingers = collections.Counter(name for name, _ in re.findall(r'"(M[NP][A-Z]+)(_\d)?"', generator))
        self.assertEqual(len(widths), 11)
        self.assertEqual({name: count * 0.5 for name, count in fingers.items()}, widths)

    def test_default_checks_existing_oa_and_rebuild_is_explicit(self):
        config = {'host':'test','remote_root':'/owned/layout','legacy_root':'/owned/legacy'}
        with patch.object(cli, 'config', return_value=config), \
             patch.object(cli.subprocess, 'check_output', return_value=b'123\n') as run, \
             patch.object(cli, 'write_json'):
            cli.physical('comp-check', 'pex', module='comparator')
            script = run.call_args.kwargs['input'].decode()
            self.assertIn('--existing-oa', script)
            self.assertNotIn('--rebuild-comparator', script)
            cli.physical('comp-build', 'pex', module='comparator', rebuild=True)
            script = run.call_args.kwargs['input'].decode()
            self.assertIn('--rebuild-comparator', script)
            self.assertNotIn('--existing-oa', script)
            with self.assertRaisesRegex(ValueError, 'only'):
                cli.physical('bad-rebuild', 'pex', module='cdac', rebuild=True)


if __name__ == '__main__':
    unittest.main()
