"""Prepare a local complete managed-input PROPOSAL, never register/submit."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
from build_first_fixture import definitions,flatten,TOP
from review_recovered_native import REPLAY
from build_first_fixture import replay_node
from reference_current_analyze import validate_config

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=HERE/'generated/managed_reproduction'
BASE=HERE/'generated/first_reproduction'
APPROX=HERE/'generated/approximate_replay'
COLLECTED=ROOT/'output/managed_execution/runs/sar8audit-ref-native-v1/collected/derived'


def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name,value):(OUT/name).write_text(json.dumps(value,indent=2)+'\n')


def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    m=read(BASE/'measurement_map.json')
    source_map=read(BASE/'source_map.json')
    approximation=read(APPROX/'verification.json')
    review=read(HERE/'generated/native_review/review.json')
    native_meta=read(COLLECTED/'native.meta.json')
    columns=(COLLECTED/'native.diagnostic.columns').read_text().splitlines()
    boundary=(COLLECTED/'native.boundary.columns').read_text().splitlines()
    binding=source_map['replay_port_binding']
    physical=flatten(definitions((APPROX/'dut.scs').read_text()),TOP,binding)
    catalog={}
    for branch in m['current_saves']:
        instance,port=branch.rsplit(':',1);port=int(port)
        device=physical.get(instance)
        if device is None:
            row=re.search(r'(?m)^'+instance+r' \(([^)]*)\) (\w+)(.*)$',(APPROX/'test.scs').read_text())
            if row is None:raise ValueError('Current instance absent '+instance)
            device=dict(nodes=row[1].split(),model=row[2],parameters=row[3])
        if port>len(device['nodes']):raise ValueError('Current terminal absent '+branch)
        mos=device['model'].startswith(('nch_','pch_'))
        catalog[branch]=dict(instance=instance,port=port,node=device['nodes'][port-1],model=device['model'],
            terminal=('DGSB'[port-1] if mos else str(port)),
            instance_parameters_sha256=hashlib.sha256(device['parameters'].encode()).hexdigest())
    selected_screens=[x for x in m['MOS_terminal_screens'] if
        x['instance'].startswith(('XDUT.XREF.XDRV0.','XDUT.XCDAC.XSN0.','XDUT.XCDAC.XSP0.','XDUT.XCOMP.MNIN')) or
        (x['instance'].startswith('XDUT.XBOOT') and '.Mmain' in x['instance'])]
    mapping={name:(replay_node(name).lower() if name in REPLAY else name) for name in columns[1:]
             if name not in ['xdut.xref.req_q','xdut.xref.late_clk','xdut.xref.ack','xdut.xref.first2']}
    available=set(x.lower() for x in m['voltage_saves'])
    if not set(mapping.values())<=available:raise ValueError('Source-to-fixture voltage map incomplete')
    diag=['vdd!']+list(mapping.values())+['xdut.xref.%s%d'%(p,b) for p in ['q','h','l'] for b in range(8)]
    diag=list(dict.fromkeys(diag))
    initial={}
    for n,v in zip(boundary[1:],native_meta['first_boundary_values']):
        new=replay_node(n).lower() if n in REPLAY else n
        if new not in available:raise ValueError('Initial native boundary witness absent '+new)
        initial[new]=v
    # The source review publishes ns; the managed analyzer has an explicit SI
    # seconds interface. Do not spread source dictionaries across that boundary.
    peaks=[dict(fixture_node=n,kind='min' if n.endswith('gnnb') else 'max',
                value_v=v['value_v'],time_s=v['time_ns']*1e-9)
           for n,v in review['peaks'].items()]
    required={'dut.scs':APPROX/'dut.scs','test.scs':APPROX/'test.scs',
        'boundary_sources_approximate.scs':APPROX/'boundary_sources_approximate.scs',
        'reference_current_analyze.py':HERE/'reference_current_analyze.py',
        'source_diagnostic.f64le':COLLECTED/'native.diagnostic.f64le'}
    proposed=read(BASE/'recipe_suggestion.json')['proposed_reproduction_not_ADC_spec']
    cfg=dict(schema_version=1,scope='First FF-cold driver0 native-current reproduction diagnostic; no circuit qualification',
        source_run='sar8fix-loaded-ref-ffcold',analysis_name='tran_repro',
        source_history_stop_s=native_meta['last_native_time_s'],diagnostic_start_s=64e-9,
        diagnostic_stop_s=native_meta['last_native_time_s'],
        voltage_saves=m['voltage_saves'],current_saves=m['current_saves'],terminal_current_catalog=catalog,
        kcl_terms={n:x['branches_positive_into_component'] for n,x in m['KCL'].items()},
        diagnostic_voltage_columns=diag,edge_nodes=diag,initial_witness_v=initial,
        initial_unavailable_from_source='Only31 recovered boundary voltages have same-source t=0 witnesses; full initial internal driver/Q/TOP/load states are measured but not claimed to reproduce unseen source t=0 data.',
        source_peaks=peaks,selected_mos_pair_screens=selected_screens,
        mos_pair_scope=dict(reduced_pair_count=len(selected_screens),full_saved_catalog_pairs=len(m['MOS_terminal_screens']),
            scope='Driver0, LSB reference, comparator input and bootstrap main six-pair extrema only. Other saved-voltage MOS pairs not screened by this reducer; no whole-circuit stress verdict.'),
        source_diagnostic=dict(file='source_diagnostic.f64le',sha256=sha(required['source_diagnostic.f64le']),
            rows=native_meta['diagnostic_native_points'],columns=columns,signal_mapping=mapping,constant_vdd_v=.99),
        required_input_sha256={n:sha(p) for n,p in required.items()},
        boundary_provenance=dict(approximate=True,kind='knot-deletion PWL replay, NOT native-boundary identity',
            diagnostic_tolerance_v=approximation['tolerance_v'],max_all_native_error_v=approximation['max_abs_error_v'],
            original_boundary_uncompressed_sha256=approximation['source_boundary_uncompressed_sha256'],
            approximate_PWL_sha256=approximation['source_sha256'],
            original_knots=approximation['native_knots_total'],retained_knots=approximation['retained_knots_total'],
            all_native_fault_window_knots_retained=True),
        current_interpretation=m['current_sign']+'; D/G/S/B are PDK wrapper ports1/2/3/4; no intrinsic conduction/displacement split inferred',
        proposed_contract=dict(status='proposal_not_approved',numerical_diagnostics=proposed),acceptance_pass=None,
        max_total_output_bytes=30*1024**2,max_edge_events=10000)
    validate_config(cfg)
    write('measurement.json',cfg)
    required['measurement.json']=OUT/'measurement.json'
    entries=[dict(source=p.relative_to(ROOT).as_posix(),name=n,sha256=sha(p)) for n,p in required.items()]
    package_bytes=sum(p.stat().st_size for p in required.values())
    if package_bytes>32*1024**2:raise ValueError('Complete local input proposal exceeds32MiB')
    recipe=dict(schema_version=1,run_id='sar8audit-ref-current-v1',design_id='sar8_reference_driver0_current_diagnostic',
        entry='test.scs',analyzer='reference_current_analyze.py',inputs=entries,
        expected_stop_s=native_meta['last_native_time_s'],summary_signals=['VDD!','XDUT.XREF.XDRV0.GNNDRV','XDUT.GNN0'],
        qualification_scope=cfg['scope'],oa_parity='netlist_only',
        test_conditions=dict(corner='FF/TT-passives',vdd=.99,temperature_c=-40,noise=False,mismatch=False,PEX=False,
                             boundary_replay='approximate <=1uV at all original native knots'),
        resources=dict(threads=4,simulation_rss_mib=1024,simulation_virtual_mib=8192,
            analysis_rss_mib=256,analysis_virtual_mib=512,max_output_mib=16384,
            simulation_wall_seconds=1800,analysis_wall_seconds=1800,queue_timeout_seconds=3600))
    write('recipe_proposal.json',recipe)
    write('package_review.json',dict(status='local_proposal_only_parent_review_required',registered=False,remote_started=False,
        package_bytes=package_bytes,package_cap_bytes=32*1024**2,
        inputs=[dict(item,bytes=required[item['name']].stat().st_size) for item in entries],
        measurement_sha256=sha(OUT/'measurement.json'),analyzer_sha256=sha(HERE/'reference_current_analyze.py'),
        derived_output_cap_mib=30,managed_collection_cap_mib=32,
        current_catalog_entries=len(catalog),selected_mos_pair_screens=len(selected_screens),
        before_dispatch=['Parent reviews physical boundary/load cuts and startup comparison limits',
                         'Parent reviews analyzer/current-port realization and complete recipe',
                         'No acceptance contract approved; acceptance_pass remains null',
                         'Run serially through managed queue only; preserve original source/raw inputs']))
    print('LOCAL_CURRENT_ANALYSIS_PROPOSAL',package_bytes,len(catalog),len(selected_screens))


if __name__=='__main__':prepare()
