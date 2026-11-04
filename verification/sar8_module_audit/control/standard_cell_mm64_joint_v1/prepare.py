"""Freeze a small FF MM64 extraction from the exact completed native source."""
from pathlib import Path
import copy
import json
import sys
import yaml

HERE=Path(__file__).resolve().parent
OWN=HERE.parent
ROOT=OWN.parents[2]
FAST=OWN/'standard_cell_storage_fastanalysis_v1'
sys.path.insert(0,str(OWN))
import prepare_first_event as base


def main():
    collected=ROOT/'output/managed_execution/runs/sar8audit-ctrl-storage-ff-v2-fastanalysis-v1/collected'
    receipt=json.loads((collected/'collection_receipt.json').read_bytes())
    expected=next(e for e in receipt['files'] if e['name']=='derived/result.json')
    blob=(collected/'derived/result.json').read_bytes()
    if len(blob)!=expected['bytes'] or base.digest(blob)!=expected['sha256']:raise ValueError('Completed FF reference differs')
    result=json.loads(blob)
    source_id='sar8audit-ctrl-stdfull-storage-ff-v2'
    if result['source_run_id']!=source_id or not result['native_PSF_END']:raise ValueError('Wrong complete native source')
    binding=json.loads((FAST/'source_binding.json').read_bytes())
    if binding['source_recipe_hash']!=result['source_recipe_hash']:raise ValueError('Source recipe binding differs')
    rec=yaml.safe_load((ROOT/'management/runs'/(source_id+'.yaml')).read_text())
    files={x['name']:x for x in rec['recipe']['files']}
    full=json.loads((ROOT/files['measurement.json']['source']).read_bytes())
    p='XDUT.XU19.XFF.';unit='XDUT.U19_'
    roles=dict(D=p+'mq_x',G=p+'clkbb',S=p+'net176',B='0',CK=unit+'CK',DATA=unit+'D',
               RST=unit+'RST',RN='XDUT.XU19.RN',Q=unit+'Q',clkb=p+'clkb',mq=p+'mq',net184=p+'net184',VDD='VDD!')
    pairs={k:v for k,v in full['stress_voltage_pairs'].items() if k.startswith(p+'MM64_')}
    nodes=sorted({v for v in roles.values() if v!='0'})
    if len(nodes)!=12 or len(pairs)!=6 or not set(nodes)<=set(full['voltage_saves']):
        raise ValueError('Required exact native node/pair coverage differs')
    windows=[(0.,.1e-9),(4.9e-9,6.15e-9),(15.9e-9,18.15e-9)]
    windows += [((i-.1)*1e-9,(i+.1)*1e-9) for i in range(1,20)]
    merged=[]
    for a,b in sorted(windows):
        if merged and a<=merged[-1][1]:merged[-1][1]=max(b,merged[-1][1])
        else:merged.append([a,b])
    cfg=dict(scope='MM64 only joint-voltage full-history statistics and original native event-window CSV; not new simulation or full current/KCL qualification',
        voltage_saves=nodes,current_saves=[],kcl_terms={},critical_kcl_nodes=[],
        diagnostic_voltage_columns=nodes,diagnostic_current_columns=[],
        diagnostic_start_s=0.,diagnostic_stop_s=20e-9,source_history_stop_s=20e-9,
        max_derived_binary_bytes=8*1024**2,stress_voltage_pairs=pairs,source_power_ports={},expected_edges={},
        expected_initial_state=dict(values_v={'VDD!':.99}),
        expected_native_peak=dict(node=p+'mq_x',value_v=0.,time_s=0.),proposed_reproduction_contract={'status':'diagnostic_not_source_fit'},
        storage=dict(collection_cap_bytes=30*1024**2,user_collection_cap_bytes=32*1024**2,final_state_reserve_bytes=256*1024),
        joint=dict(roles=roles,windows_s=merged))
    reference=dict(source_completed_analysis_run='sar8audit-ctrl-storage-ff-v2-fastanalysis-v1',
        reference_result_sha256=expected['sha256'],reference_receipt_sha256=base.digest((collected/'collection_receipt.json').read_bytes()),
        native_points=result['native_points'],raw_sha256=result['raw_sha256'],raw_bytes=result['raw_bytes'],
        MM64_VDS_peak_time_s=result['full_history_voltage_stress'][p+'MM64_VDS']['max_abs_time_s'],
        pair_statistics={k:result['full_history_voltage_stress'][k] for k in pairs},
        native_log_identities=result['original_native_logs'])
    base.write_json(HERE/'joint_measurement.json',cfg);base.write_json(HERE/'case_reference.json',reference)
    base.write_json(HERE/'source_binding.json',binding)
    inputs=[('joint_analyze.py',HERE/'joint_analyze.py')]
    inputs += [(n,FAST/n) for n in ['fast_source_analyze.py','fast_gate_analyze.py']]
    inputs += [(n,ROOT/files[n]['source']) for n in ['full_gate_analyze.py','standard_cell_full_analyze.py',
                                                    'standard_cell_storage_v2_analyze.py','measurement.json','external_library.json']]
    inputs += [(n,HERE/n) for n in ['joint_measurement.json','case_reference.json','source_binding.json']]
    template=json.loads((FAST/'recipe.suggested.yaml').read_bytes());recipe=copy.deepcopy(template)
    recipe.update(run_id='sar8audit-ctrl-mm64-joint-ff-v1',design_id='storage_MM64_joint_voltage',
        entry='joint_analyze.py',analyzer='joint_analyze.py',qualification_scope=cfg['scope'],summary_signals=[n.lower() for n in nodes])
    recipe['resources']['max_output_mib']=64
    recipe['inputs']=[dict(name=n,source=p.relative_to(ROOT).as_posix(),sha256=base.digest(p.read_bytes())) for n,p in inputs]
    base.write_json(HERE/'recipe.suggested.yaml',recipe)
    freeze=dict(recipe_file_sha256=base.digest((HERE/'recipe.suggested.yaml').read_bytes()),
        source_run_id=source_id,source_recipe_hash=binding['source_recipe_hash'],
        inputs=[dict(name=n,bytes=p.stat().st_size,sha256=base.digest(p.read_bytes())) for n,p in inputs],
        native_voltage_nodes=12,explicit_ground_B=True,simultaneous_terminal_pairs=6,
        full_history_points_expected=result['native_points'],raw_source_SHA_expected=result['raw_sha256'],
        submitted=False,new_simulation=False,remote_actions=False)
    base.write_json(HERE/'freeze.json',freeze)
    print(json.dumps(dict(run_id=recipe['run_id'],recipe_file_sha256=freeze['recipe_file_sha256'],inputs=len(inputs),
        input_bytes=sum(p.stat().st_size for _,p in inputs),source_run=source_id,voltage_nodes=12,pairs=6),indent=2))


if __name__=='__main__':main()
