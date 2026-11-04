"""Source reuse and export-only reduction; all rows explicitly synthetic."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import reference_current_analyze as base
import reference_source_reduce as adapter
from test_reference_current_analyze import make_managed,raw_text

HERE=Path(__file__).resolve().parent


def reduce_with(raw,cfg,out,narrow):
    out.mkdir()
    original=base.NativeGzip
    try:
        if narrow:
            incident=sorted({base.norm(n) for terms in cfg['kcl_terms'].values() for n in terms})
            base.NativeGzip=adapter.fault_column_adapter(original,cfg,incident)
        return base.summarize(str(raw),cfg,base.Budget(str(out),cfg['max_total_output_bytes']))
    finally:base.NativeGzip=original


def decode(path,receipt):
    blob=gzip.decompress((path/receipt['file']).read_bytes());width=len(receipt['columns'])
    return [struct.unpack('<'+'d'*width,blob[i:i+8*width]) for i in range(0,len(blob),8*width)]


class ActualExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.cfg=json.loads((HERE/'generated/current_v2/measurement.json').read_text())
        cfg=self.cfg;times=sorted({0.,cfg['diagnostic_start_s'],cfg['source_history_stop_s']} |
            {x['time_s'] for x in cfg['source_peaks']})
        names={n.lower():n for n in cfg['voltage_saves']+cfg['current_saves']}
        rows=[]
        for ordinal,t in enumerate(times):
            values={n:0. for n in names.values()};values[names['vdd!']]=.99
            for index,n in enumerate(cfg['current_saves']):values[n]=(index+1)*(ordinal+1)*1e-9
            if not ordinal:
                for n,v in cfg['initial_witness_v'].items():values[names[n.lower()]]=v
            for item in cfg['source_peaks']:
                if t==item['time_s']:values[names[item['fixture_node']]]=item['value_v']
            rows.append((t,values))
        self.raw=self.root/'synthetic_actual_config.tran.tran'
        self.raw.write_text(raw_text(cfg,rows));self.rows=rows

    def tearDown(self):self.tmp.cleanup()

    def test_actual275_statistics_integrals_snapshots_and_full_KCL_bit_identical(self):
        full=reduce_with(self.raw,self.cfg,self.root/'full',False)
        slim=reduce_with(self.raw,self.cfg,self.root/'slim',True)
        for key in ['voltage_and_current_extrema','node_kcl','current_charge_trapezoids','peak_snapshots',
                    'half_vdd_events','initial_native_values','selected_mos_pair_extrema','source_peak_reproduction_diagnostic']:
            self.assertEqual(full[key],slim[key],key)
        self.assertEqual(len(slim['current_charge_trapezoids']),275)
        self.assertTrue(all(len(x['all_selected_currents_a'])==275 for x in slim['peak_snapshots'].values()))
        self.assertEqual(full['native_exports'][0],slim['native_exports'][0])
        self.assertEqual(len(slim['native_exports'][0]['columns']),27)
        self.assertEqual(len(slim['native_exports'][1]['columns']),64)
        original=full['native_exports'][1];reduced=slim['native_exports'][1]
        keep=[original['columns'].index(n) for n in reduced['columns']]
        before=decode(self.root/'full',original);after=decode(self.root/'slim',reduced)
        self.assertEqual(after,[tuple(row[i] for i in keep) for row in before])
        self.assertIsNone(slim['acceptance_pass'])

    def test_omitted_waveform_current_is_still_a_required_TRACE(self):
        incident={base.norm(n) for terms in self.cfg['kcl_terms'].values() for n in terms}
        removed=next(n for n in self.cfg['current_saves'] if base.norm(n) not in incident)
        self.raw.write_text(raw_text(self.cfg,self.rows,missing_trace=removed))
        original=base.NativeGzip
        with self.assertRaisesRegex(ValueError,'Required TRACE'):
            reduce_with(self.raw,self.cfg,self.root/'missing',True)
        self.assertIs(base.NativeGzip,original)


def staged_runs(root):
    source=root/'completed_source';source.mkdir();cfg,rows=make_managed(source)
    cfg['max_total_output_bytes']=30*1024**2
    # Two currents not used by any critical KCL still need all measurements.
    for n in ['outside:1','outside:2']:
        cfg['current_saves'].append(n)
        cfg['terminal_current_catalog'][n]=dict(instance='outside',port=int(n[-1]),node='0',model='synthetic')
        for i,(_,values) in enumerate(rows):values[n]=(i+1)*1e-8
    (source/'inputs/measurement.json').write_text(json.dumps(cfg))
    (source/'raw/tran_repro.tran.tran').write_text(raw_text(cfg,rows,group=True,sparse=True))
    (source/'analysis.state.json').write_text(json.dumps(dict(status='failed',reason='synthetic previous derived cap')))
    shutil.copyfile(HERE/'reference_current_analyze.py',source/'inputs/reference_current_analyze.py')
    files=[dict(name=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in (source/'inputs').iterdir()]
    recipe=dict(schema_version=1,run_id=source.name,files=files)
    canonical=hashlib.sha256(json.dumps(recipe,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    (source/'recipe.json').write_text(json.dumps(recipe))
    (source/'registered.json').write_text(json.dumps(dict(files_complete=True,recipe_hash=canonical)))
    analysis=root/'new_analysis';(analysis/'inputs').mkdir(parents=True)
    for p in (source/'inputs').iterdir():shutil.copyfile(p,analysis/'inputs'/p.name)
    shutil.copyfile(HERE/'reference_source_reduce.py',analysis/'inputs/reference_source_reduce.py')
    manifest=dict(schema_version=1,source_run_id=source.name,source_recipe_hash=canonical,
        source_analysis_name='tran_repro',source_raw_relative_path='raw/tran_repro.tran.tran',
        source_input_sha256={x['name']:x['sha256'] for x in files},
        measurement_sha256=hashlib.sha256((source/'inputs/measurement.json').read_bytes()).hexdigest(),
        frozen_reducer_sha256=hashlib.sha256((HERE/'reference_current_analyze.py').read_bytes()).hexdigest(),
        max_derived_bytes=30*1024**2,
        fault_current_columns=sorted({base.norm(n) for terms in cfg['kcl_terms'].values() for n in terms}))
    (analysis/'inputs/source_binding.json').write_text(json.dumps(manifest))
    (analysis/'source_provenance.json').write_text(json.dumps(dict(run_id=source.name,recipe_hash=canonical,path=str(source))))
    return analysis,source,manifest


class ManagedSourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.run,self.source,self.manifest=staged_runs(self.root)
    def tearDown(self):self.tmp.cleanup()

    def invoke(self):
        return subprocess.run([sys.executable,'-B',str(self.run/'inputs/reference_source_reduce.py'),
            '--run-dir',str(self.run),'--output-dir',str(self.run/'derived'),
            '--source-run-dir',str(self.source)],capture_output=True,text=True)

    def test_completed_source_reused_despite_old_analysis_failure_without_source_writes(self):
        before={p.relative_to(self.source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.source.rglob('*') if p.is_file()}
        proc=self.invoke();self.assertEqual(proc.returncode,0,proc.stderr)
        result=json.loads((self.run/'derived/result.json').read_text())
        self.assertEqual(result['analysis_kind'],'analysis_only_completed_source_reuse')
        self.assertEqual(result['measured_source_run_id'],self.source.name)
        self.assertEqual(result['selected_current_count'],12)
        self.assertEqual(len(result['fault_export_policy']['omitted_waveform_only_current_columns']),2)
        self.assertEqual(len(result['current_charge_trapezoids']),12)
        self.assertIsNone(result['acceptance_pass'])
        self.assertTrue(result['original_simulator_log']['CMI_present'])
        after={p.relative_to(self.source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
               for p in self.source.rglob('*') if p.is_file()}
        self.assertEqual(before,after)
        self.assertFalse(list((self.run/'inputs').rglob('*.pyc')))

    def test_changed_source_recipe_binding_rejects(self):
        p=self.source/'recipe.json';recipe=json.loads(p.read_text());recipe['run_id']='other';p.write_text(json.dumps(recipe))
        proc=self.invoke();self.assertNotEqual(proc.returncode,0)
        self.assertIn('recipe binding mismatch',proc.stderr)
        self.assertFalse((self.run/'derived/result.json').exists())

    def test_noncompleted_source_native_simulation_rejects(self):
        p=self.source/'simulation.state.json';state=json.loads(p.read_text());state['status']='running';p.write_text(json.dumps(state))
        proc=self.invoke();self.assertNotEqual(proc.returncode,0)
        self.assertIn('Completed source native simulation required',proc.stderr)

    def test_dropping_one_incident_fault_column_rejects(self):
        p=self.run/'inputs/source_binding.json';m=json.loads(p.read_text());m['fault_current_columns'].pop();p.write_text(json.dumps(m))
        proc=self.invoke();self.assertNotEqual(proc.returncode,0)
        self.assertIn('All five-node incident currents',proc.stderr)

    def test_source_and_output_overlap_reject(self):
        with self.assertRaisesRegex(ValueError,'must be disjoint'):
            adapter.paths(str(self.source),str(self.source/'derived'),str(self.source))


if __name__=='__main__':unittest.main()
