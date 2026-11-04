"""Bounded local verification of the compact sampling extraction."""
import copy
import json
import re
import unittest

import compact_builder as c
import builder as b


class CompactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proposal=json.loads(c.PROPOSAL.read_text())
        cls.spec=json.loads(b.SPEC.read_text())
        cls.original=b.flatten((b.ROOT/cls.spec['sources']['candidate_dut']['path']).read_text())
        cls.selected,cls.groups,cls.roots=c.compact_selection(cls.original,cls.proposal)
        cls.refs=c.reference_inputs(cls.original,cls.selected)
        cls.inv=c.boundary_inventory(cls.original,cls.selected,cls.groups,cls.roots,cls.refs)
        cls.fixture,cls.ports,cls.mapping=c.fixture_text(cls.selected,cls.refs)
        cls.outputs=c.payloads()

    def test_count_and_no_whole_controller(self):
        self.assertEqual(len(self.selected),591)
        self.assertEqual(sum(b.mos(d) for d in self.selected.values()),237)
        self.assertEqual(len(self.groups['direct_sample_clock']),38)
        self.assertEqual(len(self.groups['immediate_sample_gate_units']),40)
        self.assertEqual(len(self.roots),20)
        self.assertFalse(any('.XSTORE.' in n and not '.X001.' in n for n in self.selected))

    def test_direct_clock_fanout_preserved(self):
        for row in self.inv['direct_loads']:
            self.assertEqual(row['source_terminal_count'],row['retained_terminal_count'])
            self.assertTrue(row['direct_terminal_identity'])
        rows={r['node']:r for r in self.inv['direct_loads']}
        self.assertEqual(rows['XDUT.SAMPLE_INT']['retained_terminal_count'],46)
        self.assertEqual(rows['XDUT.SAMPLE_MATCH']['retained_terminal_count'],8)
        self.assertEqual(rows['XDUT.XSEQ.QUAL']['retained_terminal_count'],4)
        self.assertEqual(rows['XDUT.SEQ_SAMPLE']['retained_terminal_count'],10)

    def test_clock_sources_only_external_SAMPLE(self):
        deck=self.outputs['short_low_history.scs'].decode()
        for name in ['SAMPLE_INT','SAMPLE_MATCH','QUAL','SEQ_SAMPLE']:
            self.assertNotRegex(deck,rf'(?m)^V\w+ \([^\n]*{name}')
        self.assertFalse(any('.XIDLE.XN.' in n or '.XIDLE.XP.' in n and not '.X000.' in n
                             or '.XIDLE.XD.' in n for n in self.selected))

    def test_both_decks_only_history_differs(self):
        high=self.outputs['short_low_history.scs'].decode().splitlines()
        low=self.outputs['long_low_history.scs'].decode().splitlines()
        self.assertEqual(len(high),len(low))
        differences=[(a,b) for a,b in zip(high,low) if a!=b]
        self.assertEqual(len(differences),1)
        self.assertTrue(all(v.startswith('VSAMPLE ') for v in differences[0]))
        self.assertIn('101n 0 101.1n SUP 141n SUP 141.1n 0',differences[0][0])

    def test_source_network_preserved(self):
        old=b.source_lines((b.ROOT/self.spec['sources']['candidate_testbench']['path']).read_text())
        for name in ['short_low_history.scs','long_low_history.scs']:
            src=b.source_lines(self.outputs[name].decode())
            for key in b.PROTECTED_SOURCES:self.assertEqual(src[key],old[key])

    def test_q128_independent_oracle(self):
        t=c.q128_targets()
        self.assertEqual(t['bp_v'],[.9]*7+[0])
        self.assertEqual(t['bn_v'],[0]*7+[.9])
        self.assertEqual(t['dummy_p_v'],.9)
        self.assertEqual(t['dummy_n_v'],0)
        self.assertEqual(len(self.refs),32)

    def test_no_driven_ideal_boundary(self):
        self.assertFalse(b.native_drivers(self.selected,b.CLOCK))
        for r in self.refs:
            self.assertFalse(b.native_drivers(self.selected,r['original_node']))
            self.assertTrue(all(e['terminal']=='g' for e in b.fanout(self.selected,r['original_node'])))
        deck=self.outputs['short_low_history.scs'].decode()
        sources=re.findall(r'(?m)^(\w+) \([^\n]*\) vsource',deck)
        self.assertEqual(len(sources),39)
        self.assertNotRegex(deck,r'(?im)\b(ic|nodeset)\b')

    def test_parameters_and_native_connections(self):
        for n,d in self.selected.items():self.assertEqual(d,self.original[n])
        statements={m[1]:m for m in re.finditer(r'(?m)^(\w+) \(([^)]*)\) (\w+) (.*)$',self.fixture)}
        self.assertEqual(len(statements),len(self.selected))
        for row in self.mapping:
            m=statements[row['label']]
            self.assertEqual(m[2].split(),row['nodes'])
            self.assertEqual(m[3],row['model'])
            self.assertEqual(b.sha(m[4].encode()),row['parameter_sha256'])

    def test_missing_gate_load_rejected(self):
        bad=dict(self.selected)
        del bad[next(iter(self.groups['immediate_sample_gate_units']))]
        with self.assertRaises(AssertionError):c.boundary_inventory(self.original,bad,self.groups,self.roots,self.refs)

    def test_reference_cut_with_extra_driver_rejected(self):
        bad=copy.deepcopy(self.selected)
        r=self.refs[0]
        bad['FAULT.driver']=dict(model='nch_mac',nodes=[r['original_node'],'VDD!','0','0'],parameters='')
        with self.assertRaises(AssertionError):c.reference_inputs(self.original,bad)

    def test_unknown_time_and_no_compiled_claim(self):
        m=json.loads(self.outputs['manifest.json'])
        self.assertIsNone(m['actual_SEQ_SAMPLE_edges_ns'])
        self.assertTrue(m['observations']['normal_sample_requires_observed_open_and_close'])
        self.assertFalse(m['zero_precharge_reproduction'])
        self.assertFalse(m['QUAL_replay_required'])
        self.assertFalse(m['simulator_invoked'])
        self.assertFalse(m['whole_controller_or_reference_word_retained'])

    def test_deterministic(self):
        self.assertEqual(self.outputs,c.payloads())

    def test_large_draft_unchanged(self):
        m=json.loads((c.HERE/'fixture_manifest.json').read_text())
        for name,r in m['artifacts'].items():
            v=(c.HERE/name).read_bytes()
            self.assertEqual(b.sha(v),r['sha256'])
            self.assertEqual(len(v),r['bytes'])


if __name__=='__main__':unittest.main()
