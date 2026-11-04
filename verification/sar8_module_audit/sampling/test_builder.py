"""Local structural/negative tests only; no simulator or remote operations."""
import json
from pathlib import Path
import re
import unittest

import builder as b


class FixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads(b.SPEC.read_text())
        cls.dut = (b.ROOT / cls.spec['sources']['candidate_dut']['path']).read_text()
        cls.tb = (b.ROOT / cls.spec['sources']['candidate_testbench']['path']).read_text()
        cls.original = b.flatten(cls.dut)
        cls.fixture, cls.rows = b.make_fixture(cls.original)
        cls.payloads = b.payloads()
        cls.high = b.make_deck('high_dc_short_low', cls.tb)
        cls.low = b.make_deck('low_dc_precharge', cls.tb)

    def test_source_hashes(self):
        for rec in self.spec['sources'].values():
            self.assertEqual(b.sha((b.ROOT/rec['path']).read_bytes()), rec['sha256'])

    def test_exact_retained_parameters_and_nodes(self):
        self.assertEqual(len(self.rows), 2506)
        self.assertEqual(sum(b.mos(d) for d in self.rows.values()), 1831)
        for name, row in self.rows.items():
            for key in ['model','parameters','nodes']:
                self.assertEqual(row[key], self.original[name][key])
            self.assertEqual(row['fixture_nodes'], [
                'CMP_RESET' if n == b.CLOCK else b.safe_node(n) for n in row['nodes']])

    def test_generated_lines_match_inventory(self):
        flat = b.parse_cells(self.fixture)['sampling_reset_fixture'][1]
        statements = {m[1]:m for m in re.finditer(
            r'(?m)^(\w+) \(([^)]*)\) (\w+) (.*)$', flat)}
        self.assertEqual(len(statements), len(self.rows))
        for row in self.rows.values():
            m = statements[row['fixture_label']]
            self.assertEqual(m[2].split(), row['fixture_nodes'])
            self.assertEqual(m[3], row['model'])
            self.assertEqual(m[4], row['parameters'])

    def test_load_fanout_complete(self):
        kept = {n:d for n,d in self.original.items() if n not in b.DRIVERS}
        inv = b.inventory(self.original, kept, self.rows)
        for node, group in inv['loads'].items():
            if node != b.CLOCK:
                self.assertEqual(group['retained'], group['original'])
        self.assertEqual(inv['loads']['XDUT.SAMPLE_INT']['retained_count'], 46)
        self.assertEqual(inv['loads']['XDUT.SEQ_SAMPLE']['retained_count'], 10)
        self.assertEqual(inv['loads']['XDUT.PRESET']['retained_count'], 25)
        self.assertEqual(inv['loads'][b.CLOCK]['original_count'], 12)
        self.assertEqual(inv['loads'][b.CLOCK]['retained_count'], 10)

    def test_only_two_native_clock_drivers_removed(self):
        self.assertEqual(set(self.original)-set(self.rows), b.DRIVERS)
        kept = {n:d for n,d in self.original.items() if n not in b.DRIVERS}
        self.assertFalse(b.native_drivers(kept,b.CLOCK))
        self.assertNotIn('XDUT.XBOOTP.Mmain', b.DRIVERS)

    def test_retained_clock_driver_rejected(self):
        bad = dict(self.original)
        bad['FAULT.extra_driver'] = self.original[next(iter(b.DRIVERS))]
        with self.assertRaises(AssertionError): b.make_fixture(bad)

    def test_missing_sample_fanout_rejected(self):
        kept = {n:d for n,d in self.original.items() if n not in b.DRIVERS}
        victim = next(n for n,d in kept.items() if 'XDUT.SAMPLE_INT' in d['nodes'])
        del kept[victim]
        with self.assertRaises(AssertionError): b.inventory(self.original, kept, self.rows)

    def test_only_VSAMPLE_line_differs(self):
        a,both = self.high.splitlines(), self.low.splitlines()
        changes = [(x,y) for x,y in zip(a,both) if x != y]
        self.assertEqual(len(a), len(both))
        self.assertEqual(len(changes),1)
        self.assertTrue(all(s.startswith('VSAMPLE ') for s in changes[0]))

    def test_formal_waveform_matches(self):
        high = [(t,v) for t,v in b.sample_points('high_dc_short_low') if t >= 101]
        low = [(t,v) for t,v in b.sample_points('low_dc_precharge') if t >= 101]
        self.assertEqual(high, b.FORMAL_POINTS)
        self.assertEqual(high, low)
        self.assertEqual(high[:4],[(101.0,'0'),(101.1,'SUP'),(141.0,'SUP'),(141.1,'0')])
        self.assertEqual(high[4][0]-high[0][0],100)
        self.assertEqual(high[6][0]-high[2][0],100)

    def test_original_sources_unchanged(self):
        original = b.source_lines(self.tb)
        for text in [self.high,self.low]:
            actual = b.source_lines(text)
            for key in b.PROTECTED_SOURCES:
                self.assertEqual(actual[key],original[key])

    def test_only_reset_undriven_boundary_is_forced(self):
        for deck in [self.high,self.low]:
            names = re.findall(r'(?m)^(\w+) \([^\n]*\) vsource',deck)
            self.assertEqual(set(names),{'VVINP','VVINN','VREFLOW','VREFHIGH',
                                        'VVDD','VCMP_RESET','VSAMPLE'})
            self.assertIn('VCMP_RESET (CMP_RESET 0) vsource dc=0',deck)
            self.assertNotRegex(deck,r'(?im)\b(ic|nodeset)\b')

    def test_conditions_and_limits(self):
        m=json.loads(self.payloads['fixture_manifest.json'])
        self.assertEqual(m['requested_conditions']['VDD_v'],.81)
        self.assertEqual(m['requested_conditions']['temperature_c'],125)
        self.assertEqual(m['requested_conditions']['MOS_corner'],'ss')
        self.assertIsNone(m['measurement']['droop_limit_v'])
        self.assertIsNone(m['measurement']['startup_limit_v'])
        self.assertFalse(m['strict_Bootstrap_only_causality'])
        self.assertFalse(m['simulator_invoked'])
        self.assertFalse(m['cases']['high_dc_short_low']['original_high_DC_failure_reproduction'])

    def test_unknown_case_rejected(self):
        with self.assertRaises(ValueError):b.sample_points('power_ramp')

    def test_deterministic_bytes(self):
        self.assertEqual(self.payloads,b.payloads())


if __name__=='__main__':
    unittest.main()
