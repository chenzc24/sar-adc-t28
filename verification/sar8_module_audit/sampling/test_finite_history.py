import json
import re
import unittest

import finite_history as f


class FiniteHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs=f.payloads()
        cls.source=(f.FROZEN/'short/test.scs').read_text()

    def test_exact_endpoints_and_plateau(self):
        expected={2:(98.9,99),10:(90.9,91),40:(60.9,61)}
        for duration,pair in expected.items():
            _,timing=f.change_history(self.source,duration)
            self.assertEqual((timing['source_fall_start_ns'],timing['source_fall_end_ns']),pair)
            self.assertAlmostEqual(101-timing['source_fall_end_ns'],duration)
            self.assertAlmostEqual(timing['source_fall_end_ns']-timing['source_fall_start_ns'],.1)
            self.assertIsNone(timing['actual_SEQ_low_interval_ns'])

    def test_only_one_line_changed_and_formal_tail_identical(self):
        for duration in f.PLATEAUS:
            text=self.outputs[f'low{duration}/test.scs'].decode()
            pairs=list(zip(self.source.splitlines(),text.splitlines()))
            changes=[(a,b) for a,b in pairs if a!=b]
            self.assertEqual(len(changes),1)
            self.assertTrue(all(x.startswith('VSAMPLE ') for x in changes[0]))
            before=changes[0][0].split('101n 0',1)[1]
            after=changes[0][1].split('101n 0',1)[1]
            self.assertEqual(before,after)
            self.assertIn('101.1n SUP 141n SUP 141.1n 0',after)

    def test_measurement_reuse_and_run_ids(self):
        recipes=json.loads(self.outputs['recipe_suggestions.json'])['recipes']
        for duration,recipe in zip(f.PLATEAUS,recipes):
            self.assertEqual(recipe['run_id'],f'sar8audit-sample-v2-low{duration}')
            for item in recipe['inputs']:
                if item['name']!='test.scs':
                    self.assertNotIn('finite_history/',item['source'])
            self.assertEqual(recipe['resources']['analysis_rss_mib'],256)
            self.assertEqual(recipe['test_conditions']['external_low_plateau_ns'],duration)

    def test_manifest_no_invented_pass_or_effective_time(self):
        m=json.loads(self.outputs['manifest.json'])
        self.assertFalse(m['actual_SEQ_low_duration_equals_external_plateau'])
        self.assertFalse(m['low_DC_case_is_finite_duration_point'])
        self.assertIsNone(m['startup_limit_v'])
        self.assertIsNone(m['droop_limit_v'])
        for r in m['variants']:self.assertFalse(r['simulator_invoked'])

    def test_invalid_durations_rejected(self):
        for value in [0,1,3,True,2.0,-1]:
            with self.assertRaises(ValueError):f.change_history(self.source,value)

    def test_reproducible(self):self.assertEqual(self.outputs,f.payloads())


if __name__=='__main__':unittest.main()
