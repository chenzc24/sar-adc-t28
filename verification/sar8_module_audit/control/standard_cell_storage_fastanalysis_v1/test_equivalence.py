"""One exact-field/wave equivalence check on the same synthetic native PSF."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
OWN=HERE.parent
sys.path.insert(0,str(OWN))
import full_gate_analyze as old
import standard_cell_full_analyze as observe
import standard_cell_storage_v2_analyze as coverage
import fast_gate_analyze as fast
import fast_source_analyze as source


class ExactReductionTest(unittest.TestCase):
    def test_explicit_not_started_binding_and_no_fake_state(self):
        with tempfile.TemporaryDirectory(prefix='_binding_',dir=HERE) as t:
            root=Path(t);run=root/'new_analysis';src=root/'synthetic-ss-source'
            for p in [run/'inputs',src/'inputs',src/'raw']:p.mkdir(parents=True)
            def write(path,data):path.write_text(json.dumps(data,sort_keys=True),encoding='utf-8')
            recipe=dict(run_id=src.name,kind='simulation',fixture='synthetic binding check only')
            h=hashlib.sha256(json.dumps(recipe,sort_keys=True,separators=(',',':')).encode('ascii')).hexdigest()
            write(src/'recipe.json',recipe);write(src/'registered.json',dict(recipe_hash=h,files_complete=True))
            write(src/'simulation.state.json',dict(status='complete',exit_code=0,native=dict(native_analysis_pass=True,zero_error_footer=True)))
            (src/'raw/logStatus').write_text('tran_first PASS\n')
            source_inputs={}
            for name in ['measurement.json','full_gate_analyze.py','standard_cell_full_analyze.py','standard_cell_storage_v2_analyze.py']:
                (src/'inputs'/name).write_text('SYNTHETIC_BINDING_BYTES\n');(run/'inputs'/name).write_text('SYNTHETIC_BINDING_BYTES\n')
                source_inputs[name]=observe.identity(str(src/'inputs'/name))
            (run/'inputs/fast_gate_analyze.py').write_text('SYNTHETIC_BINDING_BYTES\n')
            provenance=dict(run_id=src.name,recipe_hash=h,path=str(src))
            for relative,key in [('recipe.json','recipe_file_sha256'),('registered.json','registration_sha256'),('simulation.state.json','simulation_state_sha256')]:
                provenance[key]=observe.identity(str(src/relative))['sha256']
            write(run/'source_provenance.json',provenance)
            binding=dict(source_run_id=src.name,source_recipe_hash=h,source_inputs=source_inputs,
                         allow_analysis_not_started=True,fast_reducer_sha256=observe.identity(str(run/'inputs/fast_gate_analyze.py'))['sha256'])
            _,proof=source.verify_source(str(run),str(src),binding)
            self.assertEqual(proof['source_analysis_terminal_status'],'not_started')
            self.assertIsNone(proof['source_analysis_state_sha256'])
            self.assertFalse((src/'analysis.state.json').exists())
            self.assertFalse((run/'simulation.state.json').exists())
            binding['allow_analysis_not_started']=False
            with self.assertRaises(ValueError):source.verify_source(str(run),str(src),binding)
            binding['allow_analysis_not_started']=True
            for state in [dict(status='running'),dict(status='complete',exit_code=0)]:
                write(src/'analysis.state.json',state)
                with self.assertRaises(ValueError):source.verify_source(str(run),str(src),binding)
            binding['allow_analysis_not_started']=False
            write(src/'analysis.state.json',dict(status='failed',exit_code=-15))
            self.assertEqual(source.verify_source(str(run),str(src),binding)[1]['source_analysis_terminal_status'],'failed')
            binding['source_recipe_hash']='0'*64
            with self.assertRaises(ValueError):source.verify_source(str(run),str(src),binding)

    def test_exact_fields_columns_binary_gzip_and_activation(self):
        cfg=json.loads((OWN/'standard_cell_storage_v2/ff/measurement.json').read_bytes())
        before=json.dumps(cfg,sort_keys=True)
        with tempfile.TemporaryDirectory(prefix='_equal_',dir=HERE) as t:
            root=Path(t);raw=root/'same_synthetic.tran.tran';a=root/'old';b=root/'fast';a.mkdir();b.mkdir()
            selected=sorted({old.norm(n) for n in cfg['voltage_saves']+cfg['current_saves']})
            currents={old.norm(n) for n in cfg['current_saves']}
            rows=[0.,.25e-9,1e-9,2e-9,10e-9,20e-9]
            pattern=[.1,.1,1.3,-.05,.6,1.3]
            with raw.open('w',encoding='ascii',newline='\n') as f:
                f.write('HEADER\nTYPE\nSWEEP\n"time" FLOAT DOUBLE\nTRACE\n')
                for n in selected:
                    if n=='vdd!':f.write('"vdd!" GROUP 1\n"SUPPLY_RAW" FLOAT DOUBLE\n')
                    else:f.write('"'+n+'" FLOAT DOUBLE\n')
                f.write('VALUE\n')
                for k,at in enumerate(rows):
                    f.write('"time" %.17g\n'%at)
                    for j,n in enumerate(selected):
                        if k==1 and j%2:continue # actual sparse-update/held-value path
                        value=.99 if n=='vdd!' else ((j+1)*1e-8*(-1 if k%2 else 1)
                                if n in currents else pattern[k]+(j%3)*.05)
                        f.write('"%s" %.17g\n'%('SUPPLY_RAW' if n=='vdd!' else n,value))
                f.write('END\n')
            raw_before=hashlib.sha256(raw.read_bytes()).hexdigest()
            lhs=coverage.add_coverage(old.summarize(str(raw),cfg,str(a)),cfg)
            rhs=coverage.add_coverage(fast.summarize(str(raw),cfg,str(b)),cfg)
            lhs['storage_observations']=observe.observe_history(str(a),cfg)
            rhs['storage_observations']=observe.observe_history(str(b),cfg)
            # JSON identity also detects signed-zero representation differences.
            encode=lambda r:json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
            self.assertEqual(encode(lhs),encode(rhs))
            self.assertEqual((a/'peak.native.bin').read_bytes(),(b/'peak.native.bin').read_bytes())
            self.assertEqual((a/'peak.columns.json').read_bytes(),(b/'peak.columns.json').read_bytes())
            self.assertEqual(observe.compress_history(str(a)),observe.compress_history(str(b)))
            self.assertEqual((a/'peak.native.bin.gz').read_bytes(),(b/'peak.native.bin.gz').read_bytes())
            self.assertEqual(len(rhs['full_history_voltage_stress']),11220)
            self.assertEqual(rhs['native_points'],6)
            self.assertEqual(raw_before,hashlib.sha256(raw.read_bytes()).hexdigest())
            self.assertEqual(before,json.dumps(cfg,sort_keys=True))
            digest=hashlib.sha256(encode(lhs)).hexdigest()
        for state in [dict(status='running',exit_code=None),dict(status='complete',exit_code=0),
                      dict(status='limit_exceeded',reason='output_size_limit',exit_code=-15)]:
            with self.assertRaises(ValueError):source.activation(state)
        self.assertEqual(source.activation(dict(status='limit_exceeded',reason='wall_time_limit',exit_code=-15)),
                         'actual_source_analysis_wall_timeout')
        self.assertEqual(source.activation(dict(status='failed',exit_code=-15)),
                         'source_analysis_terminal_failure_or_parent_verified_targeted_stop')
        print('EXACT_EQUIVALENCE',digest,'11220pairs/89currents/26contexts; all result fields and wave/gzip bytes identical')


if __name__=='__main__':unittest.main()
