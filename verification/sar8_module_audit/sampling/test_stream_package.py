"""Small local checks for stream inputs and absent-edge interpretation."""
import json
import re
import unittest

import package_stream as p
import review_stream as r


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.common,cls.cases,cls.recipes,cls.manifest=p.build_inputs()
        cls.mapping=json.loads(cls.common['mapping.json'])
        cls.names=cls.mapping['signal_map']

    def test_native_parser_and_adapter_reused(self):
        self.assertEqual(self.common['stream.cpp'],p.STREAM.read_bytes())
        self.assertEqual(self.manifest['reuse']['analyzer_sha256'],p.b.sha(p.REMOTE.read_bytes()))

    def test_all_MOS_six_pairs(self):
        records=self.mapping['records']
        self.assertEqual(len(records),1422)
        names={x['instance'] for x in records}
        self.assertEqual(len(names),237)
        for name in names:
            self.assertEqual({x['terminal'] for x in records if x['instance']==name},
                             {'ds','gs','gd','gb','bd','bs'})
        self.assertEqual(len(self.mapping['pairs']),581)
        for record in records:
            self.assertEqual(record['nodes'],self.mapping['pairs'][record['pair_index']])

    def test_selected_nodes_and_native_case_saves(self):
        selected=self.common['selected.txt'].decode().splitlines()
        self.assertEqual(len(selected),len(set(selected)))
        for value in self.names.values():self.assertIn(value,selected)
        for deck in self.cases.values():
            text=deck.decode()
            self.assertNotRegex(text,r'(?m)^save xf\.')
            native_saves={x.lower() for x in re.findall(r'(?m)^save (\S+)$',text)}
            for signal in selected:
                if ':' in signal:self.assertIn(signal,native_saves)

    def test_events_include_no_assumed_opening(self):
        events=self.common['events.txt'].decode().splitlines()
        self.assertEqual(len(events),7)
        for k in ['sample','sample_int','sample_match','qual','seq_sample']:
            self.assertIn(self.names[k],events)
        self.assertEqual(self.mapping['measurements']['held_s'],141.8e-9)

    def test_resource_and_recipe_suggestions(self):
        self.assertEqual([x['run_id'] for x in self.recipes],
                         ['sar8audit-sample-v2-short','sar8audit-sample-v2-long'])
        for recipe in self.recipes:
            self.assertEqual(recipe['analyzer'],'loaded_remote.py')
            self.assertEqual(recipe['resources']['analysis_rss_mib'],256)
            self.assertEqual(recipe['expected_stop_s'],160e-9)
        self.assertLess(self.manifest['compact_binary_upper_bound_bytes']+4*1024**2,32*1024**2)
        self.assertEqual(self.mapping['energy_bins_s'][1],[100e-9,160e-9])

    def at(self,name,t):
        if name==self.names['vdd']:return .81
        if name==self.names['top_p']:return .045
        if name==self.names['top_n']:return .855
        if name==self.names['vin_p_source']:return .045
        if name==self.names['vin_n_source']:return .855
        return 0

    def test_filtered_pulse_keeps_missing_open_unknown(self):
        events={self.names['sample']:[(100.85e-9,0),(101.05e-9,1),(141.05e-9,0)],
                self.names['seq_sample']:[(141.16e-9,0)]}
        result=r.summarize(events,self.at,self.names)
        self.assertIsNone(result['actual_open_ns'])
        self.assertIsNone(result['actual_acquisition_ns'])
        self.assertFalse(result['normal_sampling_evaluable'])
        self.assertTrue(result['held_after_actual_close'])
        self.assertEqual(len(result['native_clock_events']['sample']),3)
        self.assertIsNone(result['startup_accuracy_pass'])

    def test_valid_open_and_close(self):
        events={self.names['seq_sample']:[(103.3e-9,1),(141.16e-9,0)]}
        result=r.summarize(events,self.at,self.names)
        self.assertTrue(result['normal_sampling_evaluable'])
        self.assertAlmostEqual(result['actual_acquisition_ns'],37.86)
        self.assertAlmostEqual(result['preclose_time_ns'],140.96)
        self.assertAlmostEqual(result['raw_held_source_error_mv'],0)

    def test_late_close_does_not_validate_held_sample(self):
        result=r.summarize({self.names['seq_sample']:[(103.3e-9,1),(142e-9,0)]},self.at,self.names)
        self.assertFalse(result['held_after_actual_close'])
        self.assertFalse(result['normal_sampling_evaluable'])
        self.assertIsNone(result['held_error_for_sampling_mv'])

    def test_missing_close_preserves_raw_observation_only(self):
        result=r.summarize({},self.at,self.names)
        self.assertIsNone(result['actual_close_ns'])
        self.assertIsNone(result['preclose_error_mv'])
        self.assertIsNone(result['net_turnoff_change_mv'])
        self.assertIsNotNone(result['raw_held_diff_mv'])


if __name__=='__main__':unittest.main()
