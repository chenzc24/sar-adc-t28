"""Bounded local package/measurement contract tests, without a simulator."""
import ast
import json
import unittest
import prepare_managed_inputs as p
import remote_reduce as r


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files=p.prepare()
        cls.mapping=json.loads(cls.files['mapping.json'])

    def test_all467_mos_have_six_terminal_pairs(self):
        records=self.mapping['records']
        self.assertEqual(len(records),467*6)
        devices={}
        for row in records:devices.setdefault(row['instance'],set()).add(row['terminal'])
        self.assertEqual(len(devices),467)
        self.assertTrue(all(v=={'ds','gs','gd','gb','bd','bs'} for v in devices.values()))
        for row in records:
            self.assertEqual(list(self.mapping['pairs'][row['pair_index']]),row['nodes'])

    def test_configs_match_frozen_saves(self):
        deck=(p.d.DEST/'tt.scs').read_text()
        saved={line.split()[1].lower() for line in deck.splitlines() if line.startswith('save ')}
        for name in self.files['selected.txt'].splitlines()+self.files['events.txt'].splitlines():
            self.assertIn(name,saved)
        for name in self.files['snapshot_nodes.txt'].splitlines():self.assertIn(name,saved)

    def test_stream_interface_full_energy_and_native_side_outputs(self):
        text=self.files['stream.cpp']
        self.assertNotIn('100e-9',text)
        self.assertEqual(text.count('260e-9'),2)
        self.assertEqual(text.count('f<1'),2)
        for name in ['.samples.tsv','.reset90.tsv','.products.tsv','.events.tsv']:
            self.assertIn(name,text)
        self.assertIn('oldtime-before*(t-oldtime)/(now-before)',text)
        self.assertIn('failing', (p.LOADED_REMOTE).read_text())

    def test_parent_proposals_no_implicit_run(self):
        proposals=json.loads(self.files['parent_recipe_inputs.json'])
        self.assertEqual([x['run_id'] for x in proposals],['sar8audit-comp-d2-tt','sar8audit-comp-d2-sscold'])
        for item in proposals:
            self.assertTrue(item['parent_only_create_recipe'])
            self.assertEqual(item['analyzer'],'remote_reduce.py')
            self.assertEqual(item['entry'],'test.scs')
            self.assertEqual(len({x['name'] for x in item['inputs']}),len(item['inputs']))
            for f in item['inputs']:
                data=self.files[f['name']].encode() if f['name'] in self.files else (p.d.ROOT/f['source']).read_bytes()
                self.assertEqual(p.d.sha(data),f['sha256'])
        package=json.loads(self.files['package_manifest.json'])
        self.assertLess(package['compact_binary_upper_bound_bytes'],8*1024*1024)
        ast.parse((p.HERE/'remote_reduce.py').read_text())

    def test_wrong_DATA_and_late_D0_are_observable_not_hidden_by_pass(self):
        mapping={'cycles':[{'index':0,'start_ns':20,'expected_DATA':1,'expected_D0':1}]}
        base={n:.9 for n in p.NAMES}
        base.update({'vdd!':.9,'d0':0.,'xdut.xctrl.data':0.,'kind':'fixed','time_s':19.9e-9})
        samples=[]
        for label in ['pre_update_0','pre_compare_0','pre_fall_0']:
            samples.append(dict(base,label=label))
        samples.append(dict(base,kind='write_rise',label='phi_w',time_s=22e-9))
        out=r.summarize(mapping,samples,[],[],[{'name':'VDD','integral':-1e-12}])
        self.assertFalse(out['cycles'][0]['writes'][0]['DATA_matches_expected_at_write'])
        self.assertFalse(out['cycles'][0]['D0_matches_expected_by_diagnostic_fall'])
        self.assertEqual(out['VDD_energy_j'],1e-12)
        self.assertIsNone(out['all_performance_pass'])


if __name__=='__main__':unittest.main()
