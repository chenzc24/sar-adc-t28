"""Bind successful SSv2q1 later; no fake old-analysis failure required."""
from pathlib import Path
import hashlib
import json
import sys
import yaml

HERE=Path(__file__).resolve().parent
OWN=HERE.parent
ROOT=OWN.parents[2]
sys.path.insert(0,str(OWN))
import prepare_first_event as base


def main():
    source_id='sar8audit-ctrl-stdfull-storage-ss-v2q1'
    record=yaml.safe_load((ROOT/'management/runs'/(source_id+'.yaml')).read_text())
    source=record['recipe'];h=hashlib.sha256(json.dumps(source,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if h!=record['recipe_hash'] or h!='3bd20be455b023474fcf80be74819b95c7fe8c7d0cb6a35db77e76486071a9f8':
        raise ValueError('Exact SSv2q1 source binding differs')
    byname={x['name']:x for x in source['files']}
    for x in source['files']:
        p=ROOT/x['source']
        if p.stat().st_size!=x['bytes'] or base.digest(p.read_bytes())!=x['sha256']:
            raise ValueError('Frozen SS input changed: '+x['name'])
    out=HERE/'ss_v2q1'
    binding=dict(schema_version=1,source_run_id=source_id,source_recipe_hash=h,
        source_inputs={x['name']:dict(bytes=x['bytes'],sha256=x['sha256']) for x in source['files']},
        fast_reducer_sha256=base.digest((HERE/'fast_gate_analyze.py').read_bytes()),
        allow_analysis_not_started=True,
        activation='Only after SSv2q1 native complete/PASS/footer. Explicit missing analysis state is not_started, never fake failed. Running/submitted/already complete source analysis refused.',
        source_simulation_must_be_complete_PASS=True,source_native_logs_copied_whole=True,
        raw_source_read_only=True,electrical_measurement_configuration_unchanged=True,
        thresholds_windows_native_samples_unchanged=True,
        excluded_source='Old SSv2 queue_timeout created no native child and is not this source')
    base.write_json(out/'source_binding.json',binding)
    inputs=[('fast_source_analyze.py',HERE/'fast_source_analyze.py'),('fast_gate_analyze.py',HERE/'fast_gate_analyze.py')]
    for name in ['full_gate_analyze.py','standard_cell_full_analyze.py','standard_cell_storage_v2_analyze.py','measurement.json','external_library.json']:
        inputs.append((name,ROOT/byname[name]['source']))
    inputs.append(('source_binding.json',out/'source_binding.json'))
    resources=dict(source['resources']);resources['max_output_mib']=128
    recipe=dict(schema_version=1,kind='analysis_only',source_run_id=source_id,
        run_id='sar8audit-ctrl-storage-ss-v2q1-fastanalysis-v1',design_id=source['design_id'],
        entry='fast_source_analyze.py',analyzer='fast_source_analyze.py',
        inputs=[dict(name=n,source=p.relative_to(ROOT).as_posix(),sha256=base.digest(p.read_bytes())) for n,p in inputs],
        expected_stop_s=source['expected_stop_s'],summary_signals=source['summary_signals'],
        qualification_scope='Exact completed SSv2q1 native source only; analysis not started allowed by explicit source binding; no simulation/full ADC qualification',
        test_conditions=source['test_conditions'],oa_parity='netlist_only',resources=resources,spectre_args=source['spectre_args'])
    base.write_json(out/'recipe.suggested.yaml',recipe)
    freeze=dict(recipe_file_sha256=base.digest((out/'recipe.suggested.yaml').read_bytes()),
        source_run_id=source_id,source_recipe_hash=h,allow_analysis_not_started=True,
        inputs=[dict(name=n,bytes=p.stat().st_size,sha256=base.digest(p.read_bytes())) for n,p in inputs],
        standby_until_native_source_complete=True,submitted=False,no_remote_actions=True)
    base.write_json(out/'freeze.json',freeze)
    print(json.dumps(dict(proposed_run=recipe['run_id'],recipe_file_sha256=freeze['recipe_file_sha256'],
        inputs=len(inputs),input_bytes=sum(p.stat().st_size for _,p in inputs),source_managed_recipe=h,
        source_native_success_verified_locally=False,standby=True),indent=2))


if __name__=='__main__':main()
