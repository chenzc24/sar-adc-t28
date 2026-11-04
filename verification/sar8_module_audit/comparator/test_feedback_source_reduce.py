"""One dense export-bound/source-binding probe; synthetic data, no simulation."""
import copy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

import prepare_feedback_source_analysis as b
import test_feedback as old


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module


def hashes(root):return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}


class SourceExport(unittest.TestCase):
    def test_dense_skipped_spike_full_metrics_and_readonly_source(self):
        p=b.OUT;cfg=json.loads((p/'measurement.json').read_bytes());binding=json.loads((p/'source_binding.json').read_bytes())
        recipe=json.loads((p/'recipe_proposal.json').read_bytes())
        self.assertEqual(recipe['kind'],'analysis_only');self.assertNotIn('entry',recipe)
        self.assertEqual(recipe['source_run_id'],binding['source_run_id'])
        self.assertEqual(recipe['resources']['max_output_mib'],32)
        for n in ['feedback_analyze.py','native_support.py','measurement.json']:self.assertEqual((p/n).read_bytes(),(b.BASE/n).read_bytes())
        self.assertLessEqual(binding['export_policy']['max_export_rows']*57*8,14*1024**2)
        data=old.rows(cfg);quiet=copy.deepcopy(data[-1][1]);spike=80.517e-9
        for i in range(1,1001):
            t=(80.+i*.001)*1e-9;v=copy.deepcopy(quiet)
            if i==517:
                spike=t;v['xdut.xcomp.tail']=2.1;v[cfg['roles']['topp']]+=.02;v['xdut.xcomp.mninp:2']=1e-3
            data.append((t,v))
        data.sort(key=lambda x:x[0])
        with tempfile.TemporaryDirectory(dir=b.HERE) as temp:
            root=Path(temp);source=root/binding['source_run_id'];run=root/'new-analysis';source.mkdir();run.mkdir()
            (source/'inputs').mkdir();(source/'raw').mkdir();(run/'inputs').mkdir()
            actual_recipe=json.loads((b.SOURCE/'recipe.json').read_bytes())
            (source/'recipe.json').write_bytes((b.SOURCE/'recipe.json').read_bytes())
            (source/'registered.json').write_text(json.dumps(dict(files_complete=True,recipe_hash=b.MANAGED)),encoding='ascii')
            for f in actual_recipe['files']:(source/'inputs'/f['name']).write_bytes((b.SOURCE/'inputs'/f['name']).read_bytes())
            state=dict(status='complete',exit_code=0,native=dict(native_analysis_pass=True,zero_error_footer=True,warning_codes=['synthetic_only']))
            (source/'simulation.state.json').write_text(json.dumps(state),encoding='ascii')
            (source/'raw/logStatus').write_text('tran_feedback PASS\n',encoding='ascii')
            (source/'spectre.out').write_text('save 124 (voltage)\nsave 23 (current)\nNumber of accepted tran steps = %d\n'%(len(data)-1),encoding='ascii')
            raw=source/'raw/tran_feedback.tran.tran';raw.write_text(old.psf(cfg,data),encoding='ascii')
            for f in recipe['inputs']:(run/'inputs'/f['name']).write_bytes((p/f['name']).read_bytes())
            binding.update(native_points=len(data),native_log_sha256=hashlib.sha256((source/'spectre.out').read_bytes()).hexdigest(),
                simulation_state_sha256=hashlib.sha256((source/'simulation.state.json').read_bytes()).hexdigest())
            binding['export_policy']['baseline_row_budget']=8
            (run/'inputs/source_binding.json').write_text(json.dumps(binding),encoding='ascii')
            (run/'source_provenance.json').write_text(json.dumps(dict(run_id=binding['source_run_id'],recipe_hash=b.MANAGED,path=str(source.resolve()))),encoding='ascii')
            support=load('native_support',run/'inputs/native_support.py')
            base=load('feedback_analyze',run/'inputs/feedback_analyze.py')
            adapter=load('feedback_source_probe',run/'inputs/feedback_source_reduce.py')
            before=hashes(source)
            oracle=base.reduce(str(raw),cfg,support.Output(str(root/'oracle'),cfg['max_output_bytes']))
            result=adapter.analyze(str(run),str(run/'derived'),str(source))
            for key in ['protocol_eight_pass','event_counts','token_sequence','cycles','events','unassigned_events',
                'native_points','raw_sha256','extrema','node_kcl','full_native_signed_charge_C','fixture_VDD_energy_j',
                'mos_pair_extrema','selected_mos_screen_exceeded_records','full_mos_screen_complete','full_mos_screen_exceeded_records']:
                self.assertEqual(result[key],oracle[key],key)
            self.assertEqual(result['full_native_metric_serialized_sha256'],oracle['waveform']['uncompressed_sha256'])
            self.assertEqual(hashes(source),before)
            wave=gzip.decompress((run/'derived/wave.export.f64le.gz').read_bytes())
            ncols=len(result['waveform']['columns']);rows=list(struct.iter_unpack('<'+'d'*ncols,wave))
            exported={r[0]:r for r in rows};stride=result['waveform']['baseline_native_index_stride']
            index=next(i for i,(t,v) in enumerate(data) if t==spike)
            self.assertNotEqual(index%stride,0)  # Hidden from the baseline selection.
            self.assertIn(spike,exported)       # Preserved as current/stress/extrema witness.
            self.assertEqual(len(wave),result['waveform']['rows']*57*8)
            self.assertLess(result['waveform']['rows'],result['native_points'])
            self.assertTrue(result['two_full_native_passes_match'])
            self.assertTrue(result['waveform']['all_requested_witnesses_exported'])
            self.assertEqual(result['waveform']['range_s'][0],0.)
            self.assertAlmostEqual(result['waveform']['range_s'][1],100e-9,delta=1e-20)
            self.assertGreater(result['selected_mos_screen_exceeded_records'],0)
            self.assertFalse(result['full_mos_screen_complete']);self.assertIsNone(result['full_mos_screen_exceeded_records'])
            self.assertFalse((run/'derived/wave.native.f64le.gz').exists())
            self.assertLess(sum(f.stat().st_size for f in (run/'derived').iterdir()),29*1024**2)
            with self.assertRaisesRegex(ValueError,'disjoint'):adapter.analyze(str(source),str(source/'derived'),str(source))


if __name__=='__main__':unittest.main()
