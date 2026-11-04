"""Prepare exactly one original PDK R0 before both native library A1 gates."""
import copy
import json

import numpy as np

import prepare_first_event as base
import prepare_standard_cell as standard
from review_both_result import read_current_run

OWN, ROOT = base.OWN, base.ROOT
SRC, DEST = OWN/'standard_cell_v1', OWN/'standard_cell_r0_v1'
RUN = 'sar8audit-ctrl-stdcell-ff-v1'
HASH = '593b9ea2d3d261345eb16a21037346df3717a6c7b0781342ea09de606a611d20'
NEW_RUN = 'sar8audit-ctrl-stdcell-r0-ff-v1'
P = 'XDUT.XCTRL.XTIM.'
NEW_NODE, RESISTOR = P+'X020.A1_FILTER', P+'X020.RINPUT'
ORIGINAL_R = P+'XD_QUIET_D.R0'


def insert_resistor(text):
    leaves = base.flatten(text,'sar8audit_ctrl_first_event',{'VDD':'VDD!','VSS':'0'})
    resistor = leaves[ORIGINAL_R]
    if resistor['model']!='rupolym' or resistor['parameters']!='l=17.13u w=1u m=1 multi=(1)':
        raise ValueError('Selected original PDK R0 model/geometry differs')
    original = '    X000 (B A N VDD VSS) ND2D1BWP12T30P140'
    changed = ('    RINPUT (B A1_FILTER) '+resistor['model']+' '+resistor['parameters']+'\n'
               '    X000 (A1_FILTER A N VDD VSS) ND2D1BWP12T30P140')
    if text.count(original)!=1:
        raise ValueError('Exact standard NAND A1 boundary missing')
    return text.replace(original,changed),resistor


def source_resistance(table,names):
    at = table[:,0]
    left = table[:,names.index((P+'QUIET').lower())]
    right = table[:,names.index((P+'XD_QUIET_D.RC0').lower())]
    plus = table[:,names.index((ORIGINAL_R+':1').lower())]
    minus = table[:,names.index((ORIGINAL_R+':2').lower())]
    selected = (at>=41.4e-9)&(np.abs(plus)>1e-9)&(np.abs(minus)>1e-9)
    a,z,i,j,t = [v[selected] for v in [left,right,plus,minus,at]]
    if not len(t):
        raise ValueError('No measured original R0 late-current evidence')
    rp,rm = (a-z)/i,(a-z)/(-j)
    return dict(source_instance=ORIGINAL_R,corner='FF0.99V/-40C, original resistor section unchanged',
        requested_start_s=41.4e-9,first_native_s=float(t[0]),last_native_s=float(t[-1]),native_points=len(t),
        plus_V_over_I_ohm=dict(min=float(rp.min()),max=float(rp.max())),
        minus_V_over_I_ohm=dict(min=float(rm.min()),max=float(rm.max())),
        max_two_port_current_sum_a=float(np.abs(i+j).max()),
        voltage_drop_range_v=[float((a-z).min()),float((a-z).max())],
        terminal1_current_range_a=[float(i.min()),float(i.max())],
        last_native_witness=dict(time_s=float(t[-1]),plus_v=float(a[-1]),minus_v=float(z[-1]),
            plus_a=float(i[-1]),minus_a=float(j[-1]),apparent_r_ohm=float(rp[-1])),
        policy='Observed finite-bias V/I of existing loaded R0, not a universal linear resistance or a measurement of new RINPUT. No new simulation or model fitting.')


def make_measurement(original,leaves,library,resistor,evidence):
    m = standard.measurement(original,leaves,library)
    m['scope'] = 'FF first event: one existing native rupolym before entire standard NAND A1; source standard-cell case, not whole ADC or SS qualification'
    exp = m['standard_cell_experiment']
    exp.update(base_run=RUN,base_recipe_sha256=HASH)
    exp['historical_snload_removed_internal_capacitor'] = exp.pop('removed_old_internal_capacitor')
    exp['current_binding'] = 'Library numeric1..4 already verified in source; new RINPUT numeric1/2 follows verified identical R0 convention. Missing required traces fail.'
    # Preserve all606 physical pairs; the two legacy A1 aliases follow actual gate node.
    m['stress_voltage_pairs']['MP1_VSG']['negative_node'] = NEW_NODE
    m['stress_voltage_pairs']['MP1_VGD']['positive_node'] = NEW_NODE
    for suffix,port in [('PLUS',1),('MINUS',2)]:
        m['source_power_ports']['RINPUT_'+suffix] = dict(
            voltage_node=P+'LIVE' if port==1 else NEW_NODE,current=RESISTOR+':'+str(port))
    m['standard_cell_r0_experiment'] = dict(base_run=RUN,base_recipe_sha256=HASH,
        inserted_instance=RESISTOR,inserted_model=resistor['model'],inserted_parameters=resistor['parameters'],
        original_resistor_reference=ORIGINAL_R,source_operating_point_resistance=evidence,
        actual_LIVE_node=P+'LIVE',actual_A1_node=NEW_NODE,
        resistor_current_ports=[RESISTOR+':1',RESISTOR+':2'],
        passive_port_energy_labels=['RINPUT_PLUS','RINPUT_MINUS'],apparent_R_current_floor_a=1e-9,
        changed_gate_instances=[P+'X020.X000.MM4',P+'X020.X000.MM1'],
        only_one_external_R_and_two_gate_bindings_changed=True,
        library_internal_topology_geometry_unchanged=True,
        rationale='Mechanism test of incident negative coupling/input edge, not a presumed repair or acceptance by moving stress.',
        energy_policy='Streaming reducer observes -V*I for both R ports; dedicated wrapper removes them from five-source energy and reports absorbed passive work=-sum(port work).',
        acceptance_pass=None)
    if (len(m['voltage_saves']),len(m['current_saves']),len(m['critical_kcl_nodes']),len(m['stress_voltage_pairs']))!=(62,437,61,609):
        raise ValueError('Expected62V/437I/61KCL/609 preserved screens')
    return m


def main():
    table,names,result,original,proof = read_current_run(RUN,HASH)
    recipe = json.loads((SRC/'recipe.suggested.yaml').read_bytes())
    for item in recipe['inputs']:
        if base.digest((ROOT/item['source']).read_bytes())!=item['sha256']:
            raise ValueError('Frozen standard-cell source input changed')
    probe_item = next(i for i in recipe['inputs'] if i['name']=='probe_metadata.json')
    probe = json.loads((ROOT/probe_item['source']).read_bytes())
    source = (SRC/'dut.scs').read_text()
    changed,resistor = insert_resistor(source)
    old,old_library = standard.expanded_leaves(source,probe)
    new,library = standard.expanded_leaves(changed,probe)
    gates = {P+'X020.X000.MM4',P+'X020.X000.MM1'}
    if set(new)-set(old)!={RESISTOR} or set(old)-set(new):
        raise ValueError('Exactly one resistor may be added')
    if {k for k in old if old[k]!=new[k]}!=gates:
        raise ValueError('Only two actual A1 gate bindings may change')
    for k in gates:
        wanted = copy.deepcopy(old[k]);wanted['nodes'][1]=NEW_NODE
        if new[k]!=wanted:
            raise ValueError('Library geometry/topology or non-gate node changed')
    if new[RESISTOR]!=dict(model=resistor['model'],parameters=resistor['parameters'],nodes=[P+'LIVE',NEW_NODE]):
        raise ValueError('Inserted R0 differs from actual original primitive')
    evidence = source_resistance(table,names)
    m = make_measurement(original,new,library,resistor,evidence)
    base.exact_write(DEST/'dut.scs',changed)
    base.write_json(DEST/'measurement.json',m)
    deck = (SRC/'test.scs').read_text()
    strip = lambda s: ''.join(line for line in s.splitlines(True) if not line.startswith('save '))
    generated = strip(deck)+''.join('save '+n+'\n' for n in sorted(m['voltage_saves']+m['current_saves']))
    if strip(generated)!=strip(deck):
        raise ValueError('Source/model/solver/library include/sample contract changed')
    base.exact_write(DEST/'test.scs',generated)
    base.exact_write(DEST/'external_library.json',(SRC/'external_library.json').read_bytes())
    for p in sorted((SRC/'pwl').glob('*.pwl')):
        base.exact_write(DEST/'pwl'/p.name,p.read_bytes())
    recipe.update(run_id=NEW_RUN,design_id='sar8_control_standard_cell_A1_native_R0',
        analyzer='standard_cell_r0_analyze.py',qualification_scope=m['scope'])
    files = []
    for item in recipe['inputs']:
        name = item['name']
        local = DEST/name
        path = local if name in ['test.scs','dut.scs','measurement.json','external_library.json'] or name.startswith('pwl/') else ROOT/item['source']
        files.append((name,path))
    files.append(('standard_cell_r0_analyze.py',OWN/'standard_cell_r0_analyze.py'))
    recipe['inputs'] = [dict(name=n,source=p.relative_to(ROOT).as_posix(),sha256=base.digest(p.read_bytes())) for n,p in files]
    recipe['summary_signals'] = recipe['summary_signals']+[NEW_NODE.lower()]
    base.write_json(DEST/'recipe.suggested.yaml',recipe)
    manifest = dict(base_run=RUN,base_recipe_sha256=HASH,source_proof=proof,
        added_resistor=dict(instance=RESISTOR,model=resistor['model'],parameters=resistor['parameters'],nodes=new[RESISTOR]['nodes']),
        changed_gate_bindings={k:dict(before=old[k],after=new[k]) for k in sorted(gates)},
        unchanged_leaf_count=len(old)-len(gates),no_other_leaf_removed=True,
        source_loaded_R0_V_over_I=evidence,original_PWL_byte_identical=11,
        non_save_deck_byte_identical=True,library_include_and_external_identity_unchanged=True,
        total_MOS=101,total_passive=18,voltage_saves=62,current_saves=437,critical_KCL=61,
        physical_terminal_pairs=606,legacy_voltage_aliases=3,
        original_19_source_inputs_verified=True,
        reused_helper_sha256={n:base.digest(p.read_bytes()) for n,p in files if n in ['full_gate_analyze.py','standard_cell_analyze.py']},
        recipe_file_sha256=base.digest((DEST/'recipe.suggested.yaml').read_bytes()),
        declared_input_files=len(files),declared_package_bytes=sum(p.stat().st_size for _,p in files),
        remote_operations=False,simulation_completed=False,repair_claim=False)
    base.write_json(DEST/'change_manifest.json',manifest)
    base.write_json(DEST/'freeze.json',dict(recipe_sha256=manifest['recipe_file_sha256'],
        inputs=[dict(name=n,bytes=p.stat().st_size,sha256=base.digest(p.read_bytes())) for n,p in files]))
    print(json.dumps({k:v for k,v in manifest.items() if k not in
        ['source_proof','source_loaded_R0_V_over_I','changed_gate_bindings','reused_helper_sha256']},indent=2))


if __name__=='__main__':
    main()
