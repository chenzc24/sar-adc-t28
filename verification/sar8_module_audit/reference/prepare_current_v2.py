"""Local save-only v2 package. Never mutate v1 or register/submit anything."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import re
import struct
from collections import Counter
from reference_current_analyze import norm,validate_config

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DEST=HERE/'generated/current_v2'
V1=HERE/'generated/managed_reproduction'
ACTUAL_RECIPE=ROOT/'management/recipes/sar8audit-ref-current-v1.yaml'
COLLECTED=ROOT/'output/managed_execution/runs/sar8audit-ref-current-v1/collected'


def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,value):(DEST/name).write_text(json.dumps(value,indent=2)+'\n')


def dependencies(cfg):
    groups={
        'fault_diagnostic_voltages':{norm(x) for x in cfg['diagnostic_voltage_columns']},
        'half_vdd_edge_nodes':{norm(x) for x in cfg['edge_nodes']},
        'source_initial_witnesses':{norm(x) for x in cfg['initial_witness_v']},
        'five_kcl_node_voltages':{norm(x) for x in cfg['kcl_terms']},
        'four_peak_nodes':{norm(x['fixture_node']) for x in cfg['source_peaks']},
        'same_source_comparison':{norm(x) for x in cfg['source_diagnostic']['signal_mapping'].values()},
        'priority_228_terminal_pair_nodes':{norm(n) for x in cfg['selected_mos_pair_screens'] for n in x['nodes']}-{'0'},
        'vdd':{'vdd!'}}
    original={norm(x) for x in cfg['voltage_saves']}
    required=set().union(*groups.values())
    if not required<=original:raise ValueError('Mandatory voltage absent from frozen v1')
    # Keep context at EVERY already-saved selected-current port, including all
    # Rgate junctions and both plates of all CDAC capacitors. Two ideal source
    # nodes were never saved and are intentionally not invented here.
    port_nodes={norm(x['node']) for x in cfg['terminal_current_catalog'].values()}-{'0'}
    groups['all_existing_selected_current_port_nodes']=port_nodes & original
    keep=required|groups['all_existing_selected_current_port_nodes']
    return keep,groups,sorted(port_nodes-original)


def filter_save_lines(blob,keep,currents,original_v):
    output=[];removed=[];seen=[]
    for line in blob.splitlines(keepends=True):
        if line.startswith(b'save '):
            fields=line.decode('ascii').split()
            if len(fields)!=2:raise ValueError('Unexpected save statement')
            name=norm(fields[1]);seen.append(name)
            if name not in currents|original_v:raise ValueError('Unknown v1 save')
            if name in original_v and name not in keep:
                removed.append(name);continue
        output.append(line)
    if len(set(seen))!=len(seen) or set(seen)!=currents|original_v:
        raise ValueError('Frozen save inventory mismatch')
    result=b''.join(output)
    old_non_save=b''.join(x for x in blob.splitlines(keepends=True) if not x.startswith(b'save '))
    new_non_save=b''.join(x for x in result.splitlines(keepends=True) if not x.startswith(b'save '))
    if old_non_save!=new_non_save:raise ValueError('Non-save content changed')
    return result,removed


def prefix_group(n):
    for prefix,label in [('xdut.xloadctrl.','receiver_token_register_internal'),
        ('xdut.xref.xdrv0.','driver0'),('xdut.xref.xdrv','other_bit_driver_internal'),
        ('xdut.xref.xstore','capture_DFF_internal'),('xdut.xref.xbbm','BBM_internal'),
        ('xdut.xref.','reference_other'),('xdut.xboot','bootstrap'),
        ('xdut.xcomp.','comparator'),('xdut.xcdac.','CDAC')]:
        if n.startswith(prefix):return label
    return 'root_and_boundary'


def reference_native_point_ratio(until):
    path=HERE/'cache/boundary.f64le'
    meta=read(ROOT/'output/managed_execution/runs/sar8audit-ref-native-v1/collected/derived/native.meta.json')
    row_bytes=8*meta['boundary_columns'];count=meta['native_points_exported']
    if path.stat().st_size!=row_bytes*count:raise ValueError('Native cache dimensions changed')
    left,right=0,count
    with path.open('rb') as f:
        while left<right:
            middle=(left+right)//2;f.seek(middle*row_bytes);t=struct.unpack('<d',f.read(8))[0]
            if t<=until:left=middle+1
            else:right=middle
    return count,left,float(count)/left


def prepare():
    DEST.mkdir(parents=True,exist_ok=True)
    v1_cfg=read(V1/'measurement.json');recipe=read(ACTUAL_RECIPE)
    for item in recipe['inputs']:
        if sha(ROOT/item['source'])!=item['sha256']:raise ValueError('Frozen v1 input changed')
    source_entries={x['name']:copy.deepcopy(x) for x in recipe['inputs']}
    v1_test=ROOT/source_entries['test.scs']['source']
    original_v={norm(x) for x in v1_cfg['voltage_saves']}
    currents={norm(x) for x in v1_cfg['current_saves']}
    keep,groups,fixed_sources=dependencies(v1_cfg)
    blob,removed=filter_save_lines(v1_test.read_bytes(),keep,currents,original_v)
    (DEST/'test.scs').write_bytes(blob)
    cfg=copy.deepcopy(v1_cfg)
    cfg['voltage_saves']=[n for n in v1_cfg['voltage_saves'] if norm(n) in keep]
    cfg['scope']='FF-cold driver0 native-current diagnostic v2, save-only reduction; not whole-circuit qualification'
    cfg['required_input_sha256']['test.scs']=sha(DEST/'test.scs')
    cfg['mos_pair_scope']=dict(reduced_pair_count=228,source_full_catalog_pairs=9306,
        other_source_pairs_not_screened=9078,
        scope='All228 declared driver0/LSB reference/comparator-input/bootstrap-main terminal pairs retained. Other circuit internal voltage saves are reduced; no full9306-pair waveform/stress claim.')
    cfg['save_reduction']=dict(v1_measurement_sha256=sha(V1/'measurement.json'),
        original_voltage_saves=len(original_v),retained_voltage_saves=len(keep),removed_voltage_saves=len(removed),
        current_saves_unchanged=len(currents),all_non_save_testbench_bytes_identical=True,
        entire_native_history_retained=True,original_v1_failure_preserved=True)
    validate_config(cfg)
    for key in ['current_saves','kcl_terms','terminal_current_catalog','selected_mos_pair_screens',
        'diagnostic_voltage_columns','edge_nodes','initial_witness_v','source_peaks','source_diagnostic',
        'source_history_stop_s','diagnostic_start_s','diagnostic_stop_s','boundary_provenance','max_total_output_bytes']:
        if cfg[key]!=v1_cfg[key]:raise ValueError('Mandatory measurement changed: '+key)
    write('measurement.json',cfg)
    for name in ['test.scs','measurement.json']:
        p=DEST/name;source_entries[name]=dict(source=p.relative_to(ROOT).as_posix(),name=name,sha256=sha(p))
    recipe['run_id']='sar8audit-ref-current-v2'
    recipe['inputs']=[source_entries[item['name']] for item in recipe['inputs']]
    recipe['qualification_scope']=cfg['scope']
    if recipe['resources']!=read(ACTUAL_RECIPE)['resources'] or recipe['resources']['max_output_mib']!=8192:
        raise ValueError('Frozen actual8GiB resource budgets must remain unchanged')
    write('recipe_proposal.json',recipe)
    state=read(COLLECTED/'simulation.state.json');log=(COLLECTED/'spectre.out').read_text()
    if state.get('reason')!='output_size_limit' or state.get('status')!='limit_exceeded':
        raise ValueError('Expected exact preserved v1 output-limit failure')
    times=re.findall(r'Error found by spectre at time = ([0-9.]+) ns',log)
    if not times or 'ERROR (SPECTRE-27)' not in log:raise ValueError('Native output-limit failure time unavailable')
    failure_t=float(times[0])*1e-9
    original_count,proxy_prefix,point_ratio=reference_native_point_ratio(failure_t)
    def weight(names):return sum(len(n)+4+22 for n in names) # only a PSF ASCII width proxy
    scalar_ratio=float(len(keep)+len(currents))/(len(original_v)+len(currents))
    width_ratio=float(weight(keep|currents))/weight(original_v|currents)
    projected=state['output_bytes']*point_ratio*width_ratio
    input_bytes=sum((ROOT/item['source']).stat().st_size for item in recipe['inputs'])
    if input_bytes>32*1024**2:raise ValueError('v2 complete input exceeds32MiB')
    audit=dict(status='local_v2_ready_no_registration',changed_surface='only voltage save selection plus measurement/proposal metadata',
        actual_v1_recipe_sha256=sha(ACTUAL_RECIPE),v1_run='sar8audit-ref-current-v1',
        v1_failure=dict(state=state['status'],reason=state['reason'],elapsed_s=state['elapsed_seconds'],
            output_bytes=state['output_bytes'],peak_rss_bytes=state['peak_rss_bytes'],native_stop_s=failure_t,
            before_fault_window=True,not_valid_reproduction=True,spectre_log_sha256=sha(COLLECTED/'spectre.out')),
        voltage_saves_before=len(original_v),voltage_saves_after=len(keep),removed_voltage_saves=len(removed),
        unchanged_current_saves=len(currents),unchanged_kcl_nodes=len(cfg['kcl_terms']),
        unchanged_incident_kcl_currents=len(set(x for terms in cfg['kcl_terms'].values() for x in terms)),
        unchanged_terminal_pair_screens=len(cfg['selected_mos_pair_screens']),
        unchanged_fault_voltage_columns=len(cfg['diagnostic_voltage_columns']),
        unchanged_source_initial_witnesses=len(cfg['initial_witness_v']),
        unchanged_source_voltage_comparisons=len(cfg['source_diagnostic']['signal_mapping']),
        unchanged_full_time_and_fault_native_output=True,analyzer_unchanged=True,resource_budgets_unchanged=True,
        retained_by_dependency={k:sorted(v) for k,v in groups.items()},
        fixed_ideal_source_nodes_already_unsaved_in_v1=fixed_sources,
        retained_voltage_names=sorted(keep),removed_voltage_names=sorted(removed),
        removed_by_group=dict(Counter(prefix_group(n) for n in removed)),
        output_estimate=dict(status='engineering_proxy_not_v2_measurement',scalar_count_fraction=scalar_ratio,
            PSF_name_plus22_numeric_chars_width_fraction=width_ratio,
            original_reference_native_points=original_count,original_reference_prefix_points_to_v1_stop=proxy_prefix,
            remaining_point_multiplier_proxy=point_ratio,
            original_reference_is_not_actual_v1_point_count=True,
            projected_complete_v2_bytes=projected,projected_complete_v2_GiB=projected/1024**3,
            actual_output_cap_bytes=8192*1024**2,
            growth_over_projection_before_cap=(8192*1024**2)/projected,
            caveat='Assumes similar native step history/current probe realization; actual v2 bytes/points unmeasured. No convergence, accuracy, LTE or electrical pass inferred.'),
        no_window_split_needed_for_first_retry=True,complete_input_bytes=input_bytes,
        frozen_v1_inputs_verified=True,registered=False,remote_started=False)
    write('save_audit.json',audit)
    write('package_review.json',dict(status='local_v2_save_only_ready',package_bytes=input_bytes,package_cap_bytes=32*1024**2,
        inputs=[dict(item,bytes=(ROOT/item['source']).stat().st_size) for item in recipe['inputs']],
        analyzer_sha256=sha(ROOT/source_entries['reference_current_analyze.py']['source']),
        measurement_sha256=sha(DEST/'measurement.json'),test_sha256=sha(DEST/'test.scs'),
        parent_owned_execution=True,registered=False,remote_started=False))
    print('LOCAL_V2_SAVE_ONLY',len(original_v),'->',len(keep),'CURRENT',len(currents),
          'PACKAGE',input_bytes,'PROJECTED_GiB',projected/1024**3)


if __name__=='__main__':prepare()
