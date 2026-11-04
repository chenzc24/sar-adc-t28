import copy
import json
import unittest

import prepare_normal_period as p


class NormalPeriodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = p.payloads()
        cls.source = (p.HERE / 'cold_controls/low40cold/test.scs').read_text()

    def test_clock_contract_and_edge_convention(self):
        contract = json.loads(self.outputs['manifest.json'])['clock_contract']
        self.assertEqual(contract['period_ns'], 100)
        self.assertEqual(contract['nominal_low_half_level_interval_ns'], 60)
        self.assertEqual(contract['external_low_flat_plateau_ns'], 59.9)
        self.assertEqual((contract['source_fall_start_ns'], contract['source_fall_end_ns']), (41, 41.1))
        self.assertEqual((contract['source_rise_start_ns'], contract['source_close_start_ns']), (101, 141))

    def test_single_line_inverse_and_identical_formal_tail(self):
        new = self.outputs['low60cold/test.scs'].decode()
        changes = [(a, b) for a, b in zip(self.source.splitlines(), new.splitlines()) if a != b]
        self.assertEqual(len(self.source.splitlines()), len(new.splitlines()))
        self.assertEqual(len(changes), 1)
        old_line, new_line = changes[0]
        self.assertTrue(old_line.startswith('VSAMPLE '))
        self.assertEqual(old_line.split('101n 0', 1)[1], new_line.split('101n 0', 1)[1])
        self.assertEqual(new.replace('0n SUP 41n SUP 41.1n 0 101n 0',
                                     '0n SUP 60.9n SUP 61n 0 101n 0', 1), self.source)

    def test_changed_contract_or_ambiguous_history_rejected(self):
        contract = p.CONTRACT.read_text()
        for bad in [contract.replace('period=100n', 'period=90n'),
                    contract.replace('width=59.9n', 'width=60n'),
                    contract + next(line for line in contract.splitlines(True) if line.startswith('VSAMPLE '))]:
            with self.assertRaises(AssertionError):
                p.clock_contract(bad)
        for bad in [self.source.replace('60.9n SUP 61n 0', '60.8n SUP 61n 0'),
                    self.source + next(line for line in self.source.splitlines(True) if line.startswith('VSAMPLE '))]:
            with self.assertRaises(AssertionError):
                p.change_history(bad)

    def test_recipe_reuses_everything_except_entry(self):
        old = json.loads((p.HERE / 'cold_controls/recipe_suggestions.json').read_text())['recipes'][0]
        new = json.loads(self.outputs['recipe_suggestions.json'])['recipes'][0]
        self.assertEqual(new['run_id'], 'sar8audit-sample-v2-low60cold')
        self.assertEqual(old['resources'], new['resources'])
        for a, b in zip(old['inputs'], new['inputs']):
            if a['name'] == 'test.scs':
                self.assertIn('normal_period/low60cold/', b['source'])
            else:
                self.assertEqual(a, b)
        expected = copy.deepcopy(old['test_conditions'])
        expected.update(history='low60cold', external_low_plateau_ns=59.9,
            source_initial_fall_start_ns=41, source_initial_fall_end_ns=41.1,
            nominal_normal_low_half_level_interval_ns=60)
        self.assertEqual(expected, new['test_conditions'])

    def test_unknowns_and_deterministic_replay(self):
        m = json.loads(self.outputs['manifest.json'])
        for key in ['actual_SEQ_low_interval_ns', 'actual_acquisition_ns', 'finite_precharge_minimum_ns']:
            self.assertIsNone(m[key])
        for key in ['simulator_invoked', 'remote_submission', 'full_ADC_PVT_qualified',
                    'low_DC_equilibrium_is_normal_period']:
            self.assertFalse(m[key])
        self.assertEqual(self.outputs, p.payloads())


if __name__ == '__main__':
    unittest.main()
