"""Prepare an analysis-only proposal bound to completed v2; never dispatch."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import yaml
from reference_current_analyze import validate_config,norm

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DEST=HERE/'generated/source_reduce_v1'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name,value):(DEST/name).write_text(json.dumps(value,indent=2)+'\n')


def prepare():
    DEST.mkdir(parents=True,exist_ok=True)
    record=yaml.safe_load((ROOT/'management/runs/sar8audit-ref-current-v2.yaml').read_text())
    source=record['recipe']
    canonical=hashlib.sha256(json.dumps(source,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if canonical!=record['recipe_hash'] or not record['managed']:
        raise ValueError('Managed v2 source binding mismatch')
    source_files={x['name']:x for x in source['files']}
    for item in source_files.values():
        if sha(ROOT/item['source'])!=item['sha256']:raise ValueError('Frozen source input changed '+item['name'])
    measure=ROOT/source_files['measurement.json']['source']
    cfg=json.loads(measure.read_text());validate_config(cfg)
    incident=sorted(set(norm(x) for terms in cfg['kcl_terms'].values() for x in terms))
    manifest=dict(schema_version=1,source_run_id=source['run_id'],source_recipe_hash=record['recipe_hash'],
        source_analysis_name=cfg['analysis_name'],source_raw_relative_path='raw/tran_repro.tran.tran',
        source_input_sha256={n:x['sha256'] for n,x in source_files.items()},
        measurement_sha256=sha(measure),frozen_reducer_sha256=source_files['reference_current_analyze.py']['sha256'],
        max_derived_bytes=30*1024**2,fault_current_columns=incident,
        export_policy='Full27-column KCL unchanged. Fault64 columns only; all275 currents remain mandatory statistics/integrals/peak snapshots. No source/raw mutation or simulation.',
        expected_fault_columns=1+len(cfg['diagnostic_voltage_columns'])+len(incident)+len(cfg['kcl_terms']))
    write('source_binding.json',manifest)
    paths={
        'reference_source_reduce.py':HERE/'reference_source_reduce.py',
        'reference_current_analyze.py':ROOT/source_files['reference_current_analyze.py']['source'],
        'measurement.json':measure,
        'source_diagnostic.f64le':ROOT/source_files['source_diagnostic.f64le']['source'],
        'source_binding.json':DEST/'source_binding.json'}
    inputs=[dict(source=p.relative_to(ROOT).as_posix(),name=n,sha256=sha(p)) for n,p in paths.items()]
    recipe=dict(kind='analysis_only',source_run_id=source['run_id'],run_id='sar8audit-ref-current-v2-reduce1',
        design_id=source['design_id'],analyzer='reference_source_reduce.py',inputs=inputs,
        summary_signals=source['summary_signals'],expected_stop_s=source['expected_stop_s'],
        qualification_scope='Analysis-only completed-v2 current attribution; waveform columns reduced, all275 current measurements preserved; acceptance separately evaluated',
        oa_parity='completed_source_netlist_only_no_OA_change',test_conditions=dict(source_run=source['run_id'],
            source_recipe_hash=record['recipe_hash'],simulation_reused=True,fault_current_columns=len(incident),
            selected_current_statistics=275,interpolation_of_native_measurements=False),
        resources=dict(threads=1,simulation_rss_mib=1024,simulation_virtual_mib=8192,simulation_wall_seconds=1,
            analysis_rss_mib=256,analysis_virtual_mib=512,analysis_wall_seconds=1800,max_output_mib=64,queue_timeout_seconds=600))
    write('recipe_proposal.json',recipe)
    write('package_review.json',dict(status='local_analysis_only_ready_no_registration',
        completed_source_run=source['run_id'],completed_source_recipe_hash=record['recipe_hash'],
        package_bytes=sum(p.stat().st_size for p in paths.values()),
        inputs=[dict(item,bytes=paths[item['name']].stat().st_size) for item in inputs],
        unchanged_frozen_reducer_sha256=source_files['reference_current_analyze.py']['sha256'],
        unchanged_measurement_sha256=sha(measure),
        full_native_KCL_columns=27,fault_native_columns=manifest['expected_fault_columns'],
        all_selected_current_statistics_integrals_and_peak_snapshots=275,
        omitted_waveform_only_currents=275-len(incident),
        derived_cap_bytes=30*1024**2,collection_cap_bytes=32*1024**2,
        whole_analysis_run_cap_mib=64,
        cap_note='64MiB whole new run includes small inputs/state; derived30MiB and collection32MiB remain unchanged. No Spectre phase is allowed.',
        source_raw_remains_read_only=True,registered=False,remote_started=False))
    print('LOCAL_SOURCE_REDUCE_READY',sum(p.stat().st_size for p in paths.values()),
          'SOURCE',source['run_id'],'FAULT_COLUMNS',manifest['expected_fault_columns'])


if __name__=='__main__':prepare()
