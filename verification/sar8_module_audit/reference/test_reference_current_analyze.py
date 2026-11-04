"""Focused synthetic native parser/current/KCL/budget/result-last controls."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import subprocess
import sys
import unittest
import reference_current_analyze as a


def configuration():
    nodes=['n%d'%i for i in range(5)]
    currents=['m%d:%d'%(i,p) for i in range(5) for p in [1,2]]
    return dict(schema_version=1,acceptance_pass=None,scope='synthetic only',source_run='synthetic',
        voltage_saves=['vdd!']+nodes,current_saves=currents,
        kcl_terms={n:['m%d:1'%i,'m%d:2'%i] for i,n in enumerate(nodes)},
        terminal_current_catalog={'m%d:%d'%(i,p):dict(instance='m%d'%i,port=p,node='n%d'%i,model='synthetic')
                                  for i in range(5) for p in [1,2]},
        diagnostic_voltage_columns=['vdd!']+nodes,edge_nodes=nodes,
        diagnostic_start_s=1e-9,diagnostic_stop_s=3e-9,source_history_stop_s=3e-9,
        initial_witness_v={'vdd!':.99,'n0':0.},initial_unavailable_from_source='synthetic',
        source_peaks=[dict(fixture_node='n%d'%i,kind='min' if i==1 else 'max',value_v=v,time_s=1e-9)
                      for i,v in enumerate([1.05,-.04,1.06,.991])],
        selected_mos_pair_screens=[dict(instance='m0',terminal='gs',nodes=['n0','0'],screen_v=.99)],
        mos_pair_scope='synthetic pair only',current_interpretation='positive into components, already includes multi',
        boundary_provenance=dict(approximate=True,diagnostic_tolerance_v=1e-6),
        proposed_contract={'status':'unapproved'},required_input_sha256={},analysis_name='tran_repro',
        max_edge_events=100,max_total_output_bytes=1024*1024)


def samples(cfg):
    voltages=[[.99,0,0,.99,.99,0],[.99,1.05,-.04,1.06,.991,.5],
              [.99,0,.99,0,0,.5],[.99,0,.99,0,0,.5]]
    out=[]
    for k,row in enumerate(voltages):
        values=dict(zip(cfg['voltage_saves'],row))
        for i in range(5):
            values['m%d:1'%i]=1e-6*(i+1)*(k+1)
            values['m%d:2'%i]=-values['m%d:1'%i]+(5e-9 if i==4 else 0.)
        out.append((k*1e-9,values))
    out[-1]=(3e-9,out[-1][1])
    return out


def raw_text(cfg,rows,group=False,properties=False,sparse=False,missing_trace=None,missing_initial=None,end=True):
    names=cfg['voltage_saves']+cfg['current_saves']
    lines=['HEADER','TYPE','SWEEP','"time" "sweep" FLOAT DOUBLE','TRACE']
    for n in names:
        if n==missing_trace:continue
        if group and n=='m0:2':
            lines+=['"m0:2" GROUP 1','"internal_probe" "current" FLOAT DOUBLE']
        else:lines+=['"%s" "voltage" FLOAT DOUBLE%s'%(n,' PROP(' if properties else '')]
        if properties:lines+=['"units" STRING "A"',')']
    lines+=['VALUE']
    previous={}
    for ordinal,(t,values) in enumerate(rows):
        lines+=['"time" %.17g'%t]
        for n in names:
            if n==missing_trace or (not ordinal and n==missing_initial):continue
            if sparse and ordinal and previous.get(n)==values[n]:continue
            key='internal_probe' if group and n=='m0:2' else n
            lines+=['"%s" %.17g'%(key,values[n])]
        previous=values.copy()
    if end:lines+=['END']
    return '\n'.join(lines)+'\n'


class StreamingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.cfg=configuration();self.rows=samples(self.cfg)

    def tearDown(self):self.temp.cleanup()

    def reduce(self,text,cfg=None):
        native=self.root/'native.tran.tran';native.write_text(text)
        output=self.root/'out';output.mkdir()
        return a.summarize(str(native),cfg or self.cfg,a.Budget(str(output),(cfg or self.cfg)['max_total_output_bytes']))

    def test_full_native_current_kcl_extrema_and_charge(self):
        result=self.reduce(raw_text(self.cfg,self.rows))
        self.assertIsNone(result['acceptance_pass'])
        self.assertEqual(result['native_points'],4)
        self.assertEqual(result['selected_current_count'],10)
        self.assertEqual(result['node_kcl']['n0']['max_abs_a'],0.)
        self.assertAlmostEqual(result['node_kcl']['n4']['max_abs_a'],5e-9)
        self.assertAlmostEqual(result['node_kcl']['n4']['signed_integral_C'],15e-18)
        self.assertAlmostEqual(result['current_charge_trapezoids']['m0:1']['signed_C'],7.5e-15)
        self.assertAlmostEqual(result['current_charge_trapezoids']['m0:1']['fault_signed_C'],6e-15)
        self.assertEqual(result['voltage_and_current_extrema']['n1']['min'],-.04)
        self.assertEqual(result['source_peak_reproduction_diagnostic']['n2']['error_v'],0.)
        self.assertEqual(result['initial_witness_error_v']['n0'],0.)
        self.assertTrue(result['boundary_provenance']['approximate'])
        full=result['native_exports'][0]
        blob=gzip.decompress((self.root/'out'/full['file']).read_bytes())
        self.assertEqual(hashlib.sha256(blob).hexdigest(),full['uncompressed_sha256'])
        self.assertEqual(full['rows'],4)
        width=len(full['columns']);last=struct.unpack('<'+'d'*width,blob[-8*width:])
        self.assertAlmostEqual(last[full['columns'].index('kcl:n4')],5e-9)

    def test_sparse_group_alias_and_multiline_trace_property(self):
        result=self.reduce(raw_text(self.cfg,self.rows,group=True,properties=True,sparse=True))
        self.assertEqual(result['trace_bindings']['m0:2'],'internal_probe')
        self.assertGreater(result['held_values_from_sparse_updates'],0)
        self.assertAlmostEqual(result['current_charge_trapezoids']['m0:2']['signed_C'],-7.5e-15)

    def test_missing_selected_current_trace_rejects(self):
        with self.assertRaisesRegex(ValueError,'Required TRACE'):
            self.reduce(raw_text(self.cfg,self.rows,missing_trace='m2:2'))

    def test_missing_current_initial_value_never_filled_zero(self):
        with self.assertRaisesRegex(ValueError,'Uninitialized'):
            self.reduce(raw_text(self.cfg,self.rows,missing_initial='m2:2'))

    def test_missing_native_end_rejects(self):
        with self.assertRaisesRegex(ValueError,'Incomplete native'):
            self.reduce(raw_text(self.cfg,self.rows,end=False))

    def test_wrong_stop_rejects(self):
        cfg=copy.deepcopy(self.cfg);cfg['source_history_stop_s']=4e-9
        with self.assertRaisesRegex(ValueError,'Incomplete native'):
            self.reduce(raw_text(self.cfg,self.rows),cfg)

    def test_nonzero_history_start_rejects(self):
        rows=self.rows[1:]
        with self.assertRaisesRegex(ValueError,'start at zero'):
            self.reduce(raw_text(self.cfg,rows))

    def test_duplicate_update_rejects(self):
        text=raw_text(self.cfg,self.rows).replace('VALUE\n','VALUE\n',1)
        text=text.replace('"m0:1" 9.9999999999999995e-07\n','"m0:1" 9.9999999999999995e-07\n"m0:1" 1e-6\n',1)
        self.assertIn('"m0:1" 1e-6',text)
        with self.assertRaisesRegex(ValueError,'Duplicate selected update'):
            self.reduce(text)

    def test_half_rail_events_use_native_brackets(self):
        r=self.reduce(raw_text(self.cfg,self.rows))
        e=r['half_vdd_events']['n0'][0]
        self.assertEqual(e['direction'],'rising')
        self.assertEqual(e['before_time_s'],0.)
        self.assertEqual(e['after_time_s'],1e-9)
        self.assertAlmostEqual(e['estimated_time_s'],.495/1.05*1e-9)
        self.assertEqual(r['native_exports'][1]['rows'],3)

    def test_derived_output_cap_rejects_without_decimation(self):
        cfg=copy.deepcopy(self.cfg);cfg['max_total_output_bytes']=32
        with self.assertRaisesRegex(ValueError,'byte cap'):
            self.reduce(raw_text(self.cfg,self.rows),cfg)

    def test_nonfinite_current_rejects(self):
        rows=copy.deepcopy(self.rows);rows[1][1]['m0:1']=float('nan')
        with self.assertRaisesRegex(ValueError,'Nonfinite'):
            self.reduce(raw_text(self.cfg,rows))

    def test_selected_kcl_term_missing_from_save_list_rejects(self):
        cfg=copy.deepcopy(self.cfg);cfg['current_saves'].remove('m1:2')
        with self.assertRaisesRegex(ValueError,'Five complete'):
            a.validate_config(cfg)

    def test_source_peak_ns_field_cannot_enter_seconds_interface(self):
        cfg=copy.deepcopy(self.cfg);item=cfg['source_peaks'][0]
        item['time_ns']=item.pop('time_s')*1e9
        with self.assertRaisesRegex(ValueError,'explicit SI time_s'):
            a.validate_config(cfg)

    def test_omitted_incident_branch_rejected_by_catalog(self):
        cfg=copy.deepcopy(self.cfg);cfg['kcl_terms']['n0']=['m0:1']
        with self.assertRaisesRegex(ValueError,'KCL incidence'):
            a.validate_config(cfg)

    def test_uncatalogued_terminal_current_rejected(self):
        cfg=copy.deepcopy(self.cfg);del cfg['terminal_current_catalog']['m0:2']
        with self.assertRaisesRegex(ValueError,'explicit terminal catalog'):
            a.validate_config(cfg)


def make_managed(root):
    cfg=configuration();rows=samples(cfg)
    (root/'inputs').mkdir();(root/'raw').mkdir()
    cols=['time']+cfg['voltage_saves']
    blob=b''.join(struct.pack('<'+'d'*len(cols),t,*[values[n] for n in cfg['voltage_saves']]) for t,values in rows)
    source=root/'inputs/source.f64le';source.write_bytes(blob)
    cfg['source_diagnostic']=dict(file='source.f64le',sha256=hashlib.sha256(blob).hexdigest(),
        columns=cols,rows=len(rows),signal_mapping={n:n for n in cfg['voltage_saves']},constant_vdd_v=.99)
    (root/'inputs/measurement.json').write_text(json.dumps(cfg))
    (root/'raw/tran_repro.tran.tran').write_text(raw_text(cfg,rows,group=True,sparse=True))
    (root/'raw/logStatus').write_text('tran_repro PASS\n')
    (root/'simulation.state.json').write_text(json.dumps(dict(status='complete',exit_code=0,
        native=dict(native_analysis_pass=True,zero_error_footer=True,warning_codes=['CMI-2204'],
                    version='synthetic fixture',effective_settings={'reltol':'1e-7'}))))
    (root/'spectre.out').write_bytes(b'WARNING (CMI-2204): synthetic overvoltage\n    keep the original instance context\nspectre completes with 0 errors\n')
    return cfg,rows


class ManagedTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.cfg,self.rows=make_managed(self.root)
    def tearDown(self):self.temp.cleanup()

    def test_complete_managed_run_writes_result_last_preserves_cmi_and_diagnostic_only(self):
        original=a.Budget;calls=[]
        class RecordedBudget(original):
            def json(self,name,value):
                calls.append(name);return original.json(self,name,value)
        a.Budget=RecordedBudget
        try:r=a.analyze(str(self.root),str(self.root/'derived'))
        finally:a.Budget=original
        self.assertEqual(calls[-1],'result.json')
        self.assertTrue(r['original_simulator_log']['CMI_present'])
        self.assertEqual((self.root/'spectre.out').read_bytes(),(self.root/'derived/spectre.original.log').read_bytes())
        self.assertEqual(r['source_wave_reproduction_diagnostic']['voltage_errors']['n0']['max_abs_v'],0.)
        self.assertIsNone(r['acceptance_pass'])
        self.assertIsNone(r['source_wave_reproduction_diagnostic']['acceptance_pass'])
        self.assertLess(sum(p.stat().st_size for p in (self.root/'derived').iterdir()),self.cfg['max_total_output_bytes'])

    def test_failed_current_requirement_leaves_no_result(self):
        (self.root/'raw/tran_repro.tran.tran').write_text(raw_text(self.cfg,self.rows,missing_trace='m0:2'))
        with self.assertRaises(ValueError):a.analyze(str(self.root),str(self.root/'derived'))
        self.assertFalse((self.root/'derived/result.json').exists())

    def test_existing_derived_directory_not_overwritten(self):
        (self.root/'derived').mkdir();(self.root/'derived/keep').write_text('preserve')
        with self.assertRaisesRegex(ValueError,'Preserve existing'):
            a.analyze(str(self.root),str(self.root/'derived'))
        self.assertEqual((self.root/'derived/keep').read_text(),'preserve')

    def test_historical_source_run_cannot_receive_derived_output(self):
        p=self.root/'inputs/measurement.json';cfg=json.loads(p.read_text());cfg['source_run']=self.root.name;p.write_text(json.dumps(cfg))
        with self.assertRaisesRegex(ValueError,'Historical source run is read-only'):
            a.analyze(str(self.root),str(self.root/'derived'))
        self.assertFalse((self.root/'derived').exists())

    def test_metadata_io_failure_cannot_publish_completion_result(self):
        output=self.root/'derived';output.mkdir()
        original=a.os.fsync
        def fail(_):raise OSError('synthetic metadata flush failure')
        a.os.fsync=fail
        try:
            with self.assertRaisesRegex(OSError,'flush failure'):
                a.Budget(str(output),1024).json('result.json',{'analysis_complete':True})
        finally:a.os.fsync=original
        self.assertFalse((output/'result.json').exists())
        self.assertTrue((output/'result.json.partial').exists())

    def test_incomplete_simulation_not_reduced(self):
        p=self.root/'simulation.state.json';state=json.loads(p.read_text());state['status']='running';p.write_text(json.dumps(state))
        with self.assertRaisesRegex(ValueError,'not complete'):
            a.analyze(str(self.root),str(self.root/'derived'))

    def test_exact_analysis_pass_required(self):
        (self.root/'raw/logStatus').write_text('other_analysis PASS\n')
        with self.assertRaisesRegex(ValueError,'Exact transient PASS'):
            a.analyze(str(self.root),str(self.root/'derived'))

    def test_source_hash_change_rejects(self):
        (self.root/'inputs/source.f64le').write_bytes(b'bad')
        with self.assertRaisesRegex(ValueError,'hash/size mismatch'):
            a.analyze(str(self.root),str(self.root/'derived'))

    def test_input_hash_change_rejects_before_measurement(self):
        p=self.root/'inputs/measurement.json';cfg=json.loads(p.read_text());cfg['required_input_sha256']={'source.f64le':'0'*64};p.write_text(json.dumps(cfg))
        with self.assertRaisesRegex(ValueError,'Frozen input hash mismatch'):
            a.analyze(str(self.root),str(self.root/'derived'))

    def test_frozen_source_comparison_is_diagnostic_not_forged_measurement(self):
        rows=copy.deepcopy(self.rows);rows[1][1]['n0']+=.01
        (self.root/'raw/tran_repro.tran.tran').write_text(raw_text(self.cfg,rows))
        r=a.analyze(str(self.root),str(self.root/'derived'))
        self.assertAlmostEqual(r['source_wave_reproduction_diagnostic']['voltage_errors']['n0']['max_abs_v'],.01)
        self.assertIsNone(r['acceptance_pass'])
        self.assertEqual(r['voltage_and_current_extrema']['n0']['max'],1.06)

    def test_cli_and_source_preservation(self):
        paths=list((self.root/'inputs').iterdir())+list((self.root/'raw').iterdir())+[self.root/'spectre.out']
        hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        command=[sys.executable,'-B',str(Path(a.__file__)),
                 '--run-dir',str(self.root),'--output-dir',str(self.root/'derived')]
        proc=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertIn('acceptance_pass=null',proc.stdout)
        self.assertEqual(hashes,{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
        result=json.loads((self.root/'derived/result.json').read_text())
        self.assertTrue(result['source_half_vdd_event_diagnostics']['nodes']['n0']['equal_event_count'])
        self.assertEqual(result['source_half_vdd_event_diagnostics']['nodes']['n0']['ordinal_pairs'][0]['error_time_s'],0.)


class ActualGeneratedConfigurationTests(unittest.TestCase):
    def test_real_measurement_config_to_native_peak_reduction_seconds_interface(self):
        # Exercise the real generated interface (1375 signals/275 currents),
        # not a hand-maintained source_peaks dictionary. These few rows are
        # explicitly synthetic test data, never circuit-simulation evidence.
        here=Path(__file__).resolve().parent
        cfg=json.loads((here/'generated/managed_reproduction/measurement.json').read_text())
        source=json.loads((here/'generated/native_review/review.json').read_text())['peaks']
        a.validate_config(cfg)
        times=sorted({0.,cfg['diagnostic_start_s'],cfg['source_history_stop_s']} |
                     {record['time_s'] for record in cfg['source_peaks']})
        template={n:0. for n in cfg['voltage_saves']+cfg['current_saves']}
        template['VDD!']=.99
        rows=[]
        actual_names={n.lower():n for n in template}
        for t in times:
            values=template.copy()
            if t==0.:
                for node,value in cfg['initial_witness_v'].items():values[actual_names[node.lower()]]=value
            for record in cfg['source_peaks']:
                if t==record['time_s']:values[actual_names[record['fixture_node'].lower()]]=record['value_v']
            rows.append((t,values))
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);raw=root/'synthetic_real_config.tran.tran'
            raw.write_text(raw_text(cfg,rows))
            output=root/'out';output.mkdir()
            result=a.summarize(str(raw),cfg,a.Budget(str(output),cfg['max_total_output_bytes']))
        for record in cfg['source_peaks']:
            node=record['fixture_node'].lower();original=source[node]
            self.assertNotIn('time_ns',record)
            self.assertEqual(record['time_s'],original['time_ns']*1e-9)
            measured=result['source_peak_reproduction_diagnostic'][node]
            self.assertEqual(measured['measured_native_time_s'],record['time_s'])
            self.assertEqual(measured['error_time_s'],0.)
            self.assertEqual(measured['error_v'],0.)
        self.assertIsNone(result['acceptance_pass'])


if __name__=='__main__':unittest.main()
