import json
import unittest

import prepare_cold_controls as c


class ColdControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.outputs=c.payloads()

    def test_one_temperature_line_and_inverse(self):
        pairs=[('low40cold',c.HERE/'finite_history/low40/test.scs'),
               ('longcold',c.HERE/'stream_package/long/test.scs')]
        for name,path in pairs:
            original=path.read_text();new=self.outputs[name+'/test.scs'].decode()
            differences=[(a,b) for a,b in zip(original.splitlines(),new.splitlines()) if a!=b]
            self.assertEqual(len(differences),1)
            self.assertTrue(differences[0][0].startswith('simulatorOptions '))
            self.assertEqual(new.replace(' temp=-40 ',' temp=125 ',1),original)

    def test_reuse_inputs_except_deck(self):
        recipes=json.loads(self.outputs['recipe_suggestions.json'])['recipes']
        self.assertEqual([r['run_id'] for r in recipes],
                         ['sar8audit-sample-v2-low40cold','sar8audit-sample-v2-longcold'])
        for r in recipes:
            self.assertEqual(r['test_conditions']['temperature_c'],-40)
            self.assertEqual(r['test_conditions']['corner'],'ss')
            self.assertEqual(r['test_conditions']['vdd'],.81)
            for item in r['inputs']:
                if item['name']!='test.scs':self.assertNotIn('cold_controls/',item['source'])

    def test_missing_or_duplicate_temperature_rejected(self):
        for text in ['simulatorOptions options temp=27 tnom=27\n',
                     'simulatorOptions options temp=125 tnom=27\n'*2]:
            with self.assertRaises(AssertionError):c.change_temperature(text)

    def test_no_new_qualification_claim(self):
        m=json.loads(self.outputs['manifest.json'])
        self.assertFalse(m['full_ADC_PVT_qualified'])
        self.assertIsNone(m['minimum_precharge_requirement_ns'])
        for case in m['cases']:self.assertIsNone(case['actual_SEQ_edges_ns'])

    def test_deterministic(self):self.assertEqual(self.outputs,c.payloads())


if __name__=='__main__':unittest.main()
