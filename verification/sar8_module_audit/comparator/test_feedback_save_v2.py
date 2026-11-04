"""One measurement-only bundle/native-reducer probe. Never run Spectre."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import prepare_feedback_save_v2 as b
import test_feedback as old


class SaveScope(unittest.TestCase):
    def test_measurement_only_native_stream_and_scope(self):
        p=b.OUT;base=b.BASE
        c=json.loads((p/'measurement.json').read_bytes());before=json.loads((base/'measurement.json').read_bytes())
        recipe=json.loads((p/'recipe_proposal.json').read_bytes());parent=json.loads((base/'recipe_proposal.json').read_bytes())
        manifest=json.loads((p/'manifest.json').read_bytes())
        self.assertEqual(recipe['resources'],parent['resources']);self.assertEqual(recipe['spectre_args'],parent['spectre_args'])
        self.assertEqual(recipe['resources']['simulation_rss_mib'],1024)
        for n in manifest['unchanged_payloads']:self.assertEqual((p/n).read_bytes(),(base/n).read_bytes())
        for item in recipe['inputs']:self.assertEqual(hashlib.sha256((b.ROOT/item['source']).read_bytes()).hexdigest(),item['sha256'])
        strip=lambda s:[line for line in s.splitlines() if not line.startswith('save ')]
        self.assertEqual(strip((p/'test.scs').read_text(encoding='utf-8')),strip((base/'test.scs').read_text(encoding='utf-8')))
        for key in ['wave_voltage_columns','wave_current_columns','roles','tokens','data_nodes','ref_q_nodes','kcl_terms','terminal_catalog','current_saves','stop_s','release_end_s','sample_fall_end_s','max_output_bytes','collection_allowance_bytes']:
            self.assertEqual(c[key],before[key],key)
        names=c['voltage_saves']+c['current_saves']
        self.assertEqual([s[5:] for s in (p/'test.scs').read_text(encoding='utf-8').splitlines() if s.startswith('save ')],names)
        self.assertTrue(set(names)<=set(before['voltage_saves']+before['current_saves']))
        self.assertEqual((len(c['voltage_saves']),len(c['current_saves']),len(c['mos_pairs'])),(124,23,990))
        self.assertTrue(all(x['instance'].startswith(b.PREFIXES) for x in c['mos_pairs']))
        self.assertEqual(manifest['circuit_MOS'],1457)
        spec=importlib.util.spec_from_file_location('feedback_v2_probe',p/'feedback_analyze.py')
        a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
        data=old.rows(c)
        node=c['mos_pairs'][0]['nodes'][0]
        for t,v in data:
            if t==99e-9:v[node]=2.1
        with tempfile.TemporaryDirectory(dir=b.HERE) as temp:
            temp=Path(temp);(temp/'inputs').mkdir();(temp/'raw').mkdir()
            for n in c['required_input_sha256']:(temp/'inputs'/n).write_bytes((p/n).read_bytes())
            (temp/'inputs/measurement.json').write_bytes((p/'measurement.json').read_bytes())
            (temp/'simulation.state.json').write_text(json.dumps(dict(status='complete',exit_code=0,native=dict(native_analysis_pass=True,zero_error_footer=True))),encoding='ascii')
            (temp/'raw/logStatus').write_text('tran_feedback PASS\n',encoding='ascii')
            (temp/'spectre.out').write_text('save 124 (voltage)\nsave 23 (current)\nNumber of accepted tran steps = %d\n'%(len(data)-1),encoding='ascii')
            (temp/'raw/probe.tran.tran').write_text(old.psf(c,data),encoding='ascii')
            result=a.analyze(str(temp),str(temp/'derived'))
            self.assertTrue(result['protocol_eight_pass'])
            self.assertEqual(result['token_sequence'],list(range(7,-1,-1)))
            self.assertEqual(len(result['waveform']['columns']),57)
            self.assertEqual(len(result['mos_pair_extrema']),990)
            self.assertGreater(result['selected_mos_screen_exceeded_records'],0)
            self.assertEqual(result['selected_mos_count'],165)
            self.assertFalse(result['full_mos_screen_complete'])
            self.assertIsNone(result['full_mos_screen_exceeded_records'])
            self.assertNotIn('mos_screen_exceeded_records',result)
            self.assertEqual(result['stress_save_scope']['deferred_pair_count'],7752)
            self.assertIn('selected165MOS/990',result['measurement_methods']['stress'])
            self.assertLess(sum(f.stat().st_size for f in (temp/'derived').iterdir()),29*1024**2)


if __name__=='__main__':unittest.main()
