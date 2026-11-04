"""Freeze a local one-resistor candidate; parent owns managed execution."""
from __future__ import annotations
import copy
import gzip
import hashlib
import json
from pathlib import Path
import re
import numpy as np
from build_first_fixture import definitions,flatten,TOP
from reference_cinput_analyze import validate_candidate,NEW_GATE

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
OUT=HERE/'generated/cinput_r1k_v1'
V2=HERE/'generated/current_v2'
DERIVED=ROOT/'output/managed_execution/runs/sar8audit-ref-current-v2-reduce1/collected/derived'
CG='XDUT.XREF.XDRV0.GNN_CG';RES='XDUT.XREF.XDRV0.R_CIN'
MOTORS=['XDUT.XREF.XDRV0.GNNCN','XDUT.XREF.XDRV0.GNNCP']


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text())
def write(name,value):(OUT/name).write_text(json.dumps(value,indent=2)+'\n')


def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    baseline=read(DERIVED/'result.json');cfg=read(V2/'measurement.json')
    original_recipe=read(ROOT/'management/recipes/sar8audit-ref-current-v2.yaml')
    original_inputs={x['name']:x for x in original_recipe['inputs']}
    for item in original_inputs.values():
        if sha(ROOT/item['source'])!=item['sha256']:raise ValueError('Frozen v2 changed')
    source_dut=ROOT/original_inputs['dut.scs']['source'];text=source_dut.read_bytes().decode('ascii')
    match=re.search(r'(?ms)^subckt sar8p_refdrv_b0 .*?^ends sar8p_refdrv_b0',text)
    if match is None:raise ValueError('driver0 master absent')
    old=match[0]
    changed,n=re.subn(r'(?m)^(\s*GNNC[NP]\s+\(GNNDRV )GNNB( V(?:DD|SS) V(?:DD|SS)\))',r'\1GNN_CG\2',old)
    if n!=2:raise ValueError('Expected exactly two common-gate rewires')
    nl='\r\n' if '\r\n' in old else '\n'
    changed=changed.replace('ends sar8p_refdrv_b0','    R_CIN (GNNB GNN_CG) resistor r=1k'+nl+'ends sar8p_refdrv_b0')
    candidate=text[:match.start()]+changed+text[match.end():]
    (OUT/'dut.scs').write_bytes(candidate.encode('ascii'))
    source_map=read(HERE/'generated/first_reproduction/source_map.json')
    binding=source_map['replay_port_binding']
    a=flatten(definitions(text.replace('\r\n','\n')),TOP,binding)
    b=flatten(definitions(candidate.replace('\r\n','\n')),TOP,binding)
    for name,record in a.items():
        expected=copy.deepcopy(record)
        if name in MOTORS:expected['nodes'][1]=CG
        if b.get(name)!=expected:raise ValueError('Unexpected primitive change '+name)
    if set(b)-set(a)!={RES}:raise ValueError('Candidate added more than one component')
    if b[RES]['model']!='resistor' or b[RES]['parameters']!='r=1k':raise ValueError('Resistor mechanism changed')

    cfg=copy.deepcopy(cfg)
    cfg['source_run']='sar8audit-ref-current-v2'
    cfg['scope']='Driver0 final-stage common-input ideal1kOhm mechanism experiment; no whole-ADC/PDK-resistor qualification'
    cfg['voltage_saves'].append(CG)
    cfg['diagnostic_voltage_columns'].append(NEW_GATE);cfg['edge_nodes'].append(NEW_GATE)
    for name in MOTORS:cfg['terminal_current_catalog'][name+':2']['node']=CG
    for port,node in [(1,'XDUT.XREF.XDRV0.GNNB'),(2,CG)]:
        name=RES+':'+str(port);cfg['current_saves'].append(name)
        cfg['terminal_current_catalog'][name]=dict(instance=RES,port=port,node=node,model='resistor',
            terminal=str(port),instance_parameters_sha256=hashlib.sha256(b'r=1k').hexdigest())
    b_key=next(n for n in cfg['kcl_terms'] if n.lower()=='xdut.xref.xdrv0.gnnb')
    cfg['kcl_terms'][b_key]=[n for n in cfg['kcl_terms'][b_key] if n not in [x+':2' for x in MOTORS]]+[RES+':1']
    cfg['kcl_terms'][CG]=[RES+':2']+[x+':2' for x in MOTORS]
    for screen in cfg['selected_mos_pair_screens']:
        if screen['instance'] in MOTORS:
            screen['nodes']=[CG if n=='XDUT.XREF.XDRV0.GNNB' else n for n in screen['nodes']]
    cfg['initial_witness_v']={n:baseline['initial_native_values'][n.lower()] for n in cfg['initial_witness_v']}
    for peak in cfg['source_peaks']:
        measured=baseline['source_peak_reproduction_diagnostic'][peak['fixture_node']]
        peak['value_v']=measured['measured_native_peak_v'];peak['time_s']=measured['measured_native_time_s']

    rec=baseline['native_exports'][1];raw=gzip.decompress((DERIVED/rec['file']).read_bytes())
    if hashlib.sha256(raw).hexdigest()!=rec['uncompressed_sha256']:raise ValueError('Baseline native payload changed')
    values=np.frombuffer(raw,dtype='<f8').reshape((-1,len(rec['columns'])))
    names=list(cfg['source_diagnostic']['signal_mapping'].values())
    cols=['time']+names;subset=np.ascontiguousarray(values[:,[rec['columns'].index(n) for n in cols]],dtype='<f8')
    (OUT/'baseline_native.f64le').write_bytes(subset.tobytes())
    cfg['source_diagnostic']=dict(file='baseline_native.f64le',sha256=sha(OUT/'baseline_native.f64le'),
        rows=len(values),columns=cols,signal_mapping={n:n for n in names},constant_vdd_v=.99)
    late=next(e['estimated_time_s'] for e in baseline['half_vdd_events']['xdut.xref.cap_clk']
              if e['direction']=='rising' and 65.1e-9<e['estimated_time_s']<65.3e-9)
    cfg['experiment']=dict(status='unexecuted_single_variable_mechanism_candidate',parameter='R_CIN',resistance_ohm=1000,
        component_class='ideal resistor for mechanism localization, not final PDK resistor',
        baseline_run='sar8audit-ref-current-v2',baseline_analysis_run='sar8audit-ref-current-v2-reduce1',
        baseline_result_sha256=sha(DERIVED/'result.json'),baseline_fault_native_sha256=rec['sha256'],
        baseline_partial_supply_energy_J=-.99*baseline['current_charge_trapezoids']['vvdd:1']['signed_C'],
        load_diagnostic=dict(independent_command_time_s=late,expected_Q0=1,independent_command_word=243,
            command_source='Previously approved bit1 late-CODE243, independent of observed Q/gates',
            expected_bottom_mapping={'BN0':'VREFP','BP0':'VREFN'},diagnostic_tolerance_V=.001,
            tolerance_not_ADC_spec=True,interval_stop_s=cfg['source_history_stop_s']),
        circuit_delta='Only driver0 GNNCN/GNNCP gate pins moved to GNN_CG through one1kOhm R_CIN; all MOS models/geometry/other pins identical',
        fixed='External PWL, supply/sampling/closing timing, full physical CDAC/reference/comparator loads and other drivers',
        caution='Baseline gate spikes A/B remain unresolved; compare all228 screens. Replay D/CODE cannot prove closed-loop ADC codes.')
    cfg['initial_unavailable_from_source']+=' New GNN_CG has no baseline t=0 witness; it is measured, not assigned.'
    cfg['save_reduction']['candidate_new_gate_voltage_saves']=1
    cfg['save_reduction']['candidate_current_saves']=277
    validate_candidate(cfg)
    old_tb=(ROOT/original_inputs['test.scs']['source']).read_bytes()
    header=b''.join(line for line in old_tb.splitlines(keepends=True) if not line.startswith(b'save '))
    tokens=sorted(set(cfg['voltage_saves']+cfg['current_saves']))
    (OUT/'test.scs').write_bytes(header+b''.join(('save '+n+'\r\n').encode('ascii') for n in tokens))
    files={'dut.scs':OUT/'dut.scs','test.scs':OUT/'test.scs',
        'boundary_sources_approximate.scs':ROOT/original_inputs['boundary_sources_approximate.scs']['source'],
        'reference_current_analyze.py':HERE/'reference_current_analyze.py',
        'reference_cinput_analyze.py':HERE/'reference_cinput_analyze.py','baseline_native.f64le':OUT/'baseline_native.f64le'}
    cfg['required_input_sha256']={n:sha(p) for n,p in files.items()}
    write('measurement.json',cfg);files['measurement.json']=OUT/'measurement.json'
    recipe=copy.deepcopy(original_recipe)
    recipe['run_id']='sar8audit-ref-cinput-r1k-v1';recipe['analyzer']='reference_cinput_analyze.py'
    recipe['qualification_scope']=cfg['scope']
    recipe['test_conditions'].update(R_CIN_ohm=1000,resistor_class='ideal mechanism experiment',
                                    baseline_run='sar8audit-ref-current-v2')
    recipe['inputs']=[dict(source=p.relative_to(ROOT).as_posix(),name=n,sha256=sha(p)) for n,p in files.items()]
    write('recipe_proposal.json',recipe)
    total=sum(p.stat().st_size for p in files.values())
    if total>32*1024**2:raise ValueError('Candidate input package exceeds32MiB')
    write('package_review.json',dict(status='local_ready_parent_owned_execution',package_bytes=total,
        inputs=[dict(row,bytes=files[row['name']].stat().st_size) for row in recipe['inputs']],
        baseline_dut_sha256=sha(source_dut),unchanged_primitive_records=len(a)-2,
        changed_MOS_gate_pins=MOTORS,added_component=b[RES],all_MOS_parameters_unchanged=True,
        original275_current_names_preserved=True,current_saves=277,voltage_saves=139,KCL_nodes=6,incident_current_saves=17,
        full_KCL_export_columns=24,fault_export_columns=68,priority_MOS_pair_screens=228,
        original_non_save_testbench_bytes_preserved=True,resource_budgets_unchanged=recipe['resources']==original_recipe['resources'],
        external_PWL_sha256=original_inputs['boundary_sources_approximate.scs']['sha256'],
        baseline_native_table='Exact21-column subset of completed-v2 native fault data; all14293 original time points retained',
        full_time_voltage_waveforms_not_exported=True,derived_cap_bytes=30*1024**2,
        registered=False,simulation_started=False))
    print('CINPUT_R1K_LOCAL_READY',total,'V139 I277 KCL6 FULL24 FAULT68')


if __name__=='__main__':prepare()
