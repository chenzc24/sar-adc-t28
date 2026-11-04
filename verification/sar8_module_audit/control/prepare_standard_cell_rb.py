"""Prepare one native RB inverter replacement; no remote or foundry-body writes."""
import copy
import json

import prepare_first_event as base
import prepare_standard_cell as standard
import prepare_standard_cell_live as live
from review_both_result import read_current_run

OWN, ROOT = base.OWN, base.ROOT
SRC, DEST = OWN/'standard_cell_live_v1', OWN/'standard_cell_rb_v1'
RUN = 'sar8audit-ctrl-stdcell-live-ff-v1'
HASH = 'a99eeaad32f6fb75ac2c548ebf617690091e2175fb022aa43437e522684a9226'
NEW_RUN = 'sar8audit-ctrl-stdcell-rb-ff-v1'
P = live.P
SR = P+'XCLOCK'
TARGET = SR+'.X000'


def replace_rb(text):
    blocks = base.cells(text)
    old = 'XCLOCK (CLOCK_Q CLOCK_RESET CLOCK_SET VDD VSS) sar8p_sr'
    timing = blocks['sar8audit_timing']
    if timing.count(old) != 1:
        raise ValueError('Exact clock SR boundary missing')
    timing = timing.replace(old, old.removesuffix('sar8p_sr')+'sar8audit_sr_rb_tcb')
    sr = blocks['sar8p_sr']
    original = 'X000 (R VDD VSS RB) sar8p_inv'
    if sr.count(original) != 1:
        raise ValueError('Exact original reset inverter missing')
    sr = sr.replace('subckt sar8p_sr ', 'subckt sar8audit_sr_rb_tcb ', 1)
    sr = sr.replace('ends sar8p_sr', 'ends sar8audit_sr_rb_tcb', 1)
    sr = sr.replace(original, 'X000 (R RB VDD VSS) INVD1BWP12T30P140')
    return text.replace(blocks['sar8audit_timing'], timing)+'\n'+sr+'\n'


def expand_fourteen(text, probe):
    leaves = base.flatten(text, 'sar8audit_ctrl_first_event', {'VDD':'VDD!', 'VSS':'0'})
    library = {}
    for path, part in list(leaves.items()):
        if part['model'] not in standard.CELLS:
            continue
        pins = standard.CELLS[part['model']]
        if len(pins) != len(part['nodes']):
            raise ValueError('Library port count differs')
        binding = dict(zip(pins, part['nodes']))
        del leaves[path]
        for mos in probe['cells'][part['model']]:
            key = path+'.'+mos['instance']
            nodes = [binding.get(mos[t], path+'.'+mos[t]) for t in ['D','G','S','B']]
            leaves[key] = dict(model=mos['master'], nodes=nodes,
                               parameters='EXTERNAL_FOUNDRY_PARAMETERS_NOT_COPIED')
            library[key] = dict(cell=part['model'], master=mos['master'], nodes=nodes,
                requested_numeric_terminal_currents=[key+':'+str(i) for i in range(1,5)],
                known_inline_primitive=mos['master'], primitive_probe_path_not_assumed=key+'.'+mos['master'])
    if len(library) != 14:
        raise ValueError('Expected twelve retained library MOS and two RB library MOS')
    return leaves, library


def reset_observers(foundry):
    return dict(
        CLOCK_RESET=dict(node=P+'CLOCK_RESET', ports=dict(
            NM_gate=TARGET+('.MM1:2' if foundry else '.MN:2'),
            PM_gate=TARGET+('.MM0:2' if foundry else '.MP:2')),
            role='Real upstream OR output; reset inverter input loading'),
        RB=dict(node=SR+'.RB', ports=dict(
            QB_NM_gate=SR+'.X003.MN0:2', QB_PM_gate=SR+'.X003.MP0:2',
            SN_NM_gate=SR+'.X001.MN1:2', SN_PM_gate=SR+'.X001.MP1:2'),
            role='Actual reset-inverter output and unchanged four SR gate loads'),
        SR_QB=dict(node=SR+'.QB', ports={}, role='Cross-coupled SR receiver QB'),
        SR_SN=dict(node=SR+'.SN', ports={}, role='Reset-qualified set NAND output'),
        CLOCK_Q=dict(node=P+'CLOCK_Q', ports={}, role='Actual clock SR output, no invented edge'),
        CLOCK_SET=dict(node=P+'CLOCK_SET', ports={}, role='Actual SR set input'))


def measurement(source, leaves, library, removed):
    clean = copy.deepcopy(source)
    for record in source['standard_cell_experiment']['observed_mos'].values():
        for label in record['six_pair_labels'].values():
            del clean['stress_voltage_pairs'][label]
    m = standard.measurement(clean, leaves, library)
    m['source_power_ports'] = copy.deepcopy(source['source_power_ports'])
    m['stress_voltage_pairs']['MP1_VSG']['negative_node'] = P+'X020.A1_FILTER'
    m['stress_voltage_pairs']['MP1_VGD']['positive_node'] = P+'X020.A1_FILTER'
    exp = m['standard_cell_experiment']
    exp.update(base_run=RUN, base_recipe_sha256=HASH)
    exp['historical_X020_removed_internal_capacitor'] = exp.pop('removed_old_internal_capacitor')
    exp['current_binding'] = ('Actual MM instance numeric D/G/S/B ports1/2/3/4; same native INVD1 mapping '
                              'already verified in X001/X020. New target traces must bind, never substitute zeros.')
    for path, record in exp['observed_mos'].items():
        record['group'] = ('new_RB_library' if path.startswith(TARGET+'.') else
                           'existing_library' if path in library else 'other_core')
    m['scope'] = ('FF0.99V/-40C first event: only XCLOCK.X000 reset INV replaced by native INVD1; '
                  'real CLOCK_RESET driver and SR fanout preserved; not full-reset or ADC qualification')
    m['terminal_voltage_policy']['method'] = ('Six simultaneous native terminal pairs per101 MOS, '
                                            'zero-to-END, plus three legacy aliases; no tolerance relaxation.')
    m['standard_cell_rb_experiment'] = dict(
        base_run=RUN, base_recipe_sha256=HASH, replacement_boundary=TARGET,
        contract='RB = NOT CLOCK_RESET; unchanged active-high reset-priority SR network',
        INV_mapping=['CLOCK_RESET/I', 'RB/ZN', 'VDD', 'VSS'],
        removed_implementation=removed, explicit_capacitors_added_or_removed=[],
        classification='Whole INV implementation changes dimensions and intrinsic parasitics together; no single-MOS attribution.',
        load_observers=reset_observers(True), event_charge_start_s=41e-9,
        width_nodes=dict(CLOCK_RESET=P+'CLOCK_RESET', RB=SR+'.RB'),
        width_policy='Diagnostic-window native-sample crossing estimates; thresholds0/-1mV/0.99V/0.991V describe width, not relaxed physical limits.',
        full_reset_assertion_or_hold_qualification=False, acceptance_pass=None)
    if (len(m['voltage_saves']), len(m['current_saves']), len(m['critical_kcl_nodes']),
            len(m['stress_voltage_pairs'])) != (62,436,61,609):
        raise ValueError('Expected unchanged62V436I61KCL606physical+3aliases')
    return m


def main():
    _, _, _, source_m, proof = read_current_run(RUN, HASH)
    recipe = json.loads((SRC/'recipe.suggested.yaml').read_bytes())
    for item in recipe['inputs']:
        if base.digest((ROOT/item['source']).read_bytes()) != item['sha256']:
            raise ValueError('Frozen LIVE source input changed')
    probe_file = next(i for i in recipe['inputs'] if i['name']=='probe_metadata.json')
    probe = json.loads((ROOT/probe_file['source']).read_bytes())
    text = (SRC/'dut.scs').read_text()
    changed = replace_rb(text)
    old, _ = live.expand_twelve(text, probe)
    new, library = expand_fourteen(changed, probe)
    removed = {k:v for k,v in old.items() if k.startswith(TARGET+'.')}
    added = set(new)-set(old)
    if (len(removed) != 2 or set(old)-set(new) != set(removed)
            or added != {TARGET+'.MM0', TARGET+'.MM1'}):
        raise ValueError('Expected only original two reset MOS replaced by two native INV MOS')
    if any(new[k] != old[k] for k in set(old)-set(removed)):
        raise ValueError('Real upstream driver, SR fanout or other leaf changed')
    m = measurement(source_m, new, library, removed)
    base.exact_write(DEST/'dut.scs', changed)
    base.write_json(DEST/'measurement.json', m)
    strip = lambda s: ''.join(line for line in s.splitlines(True) if not line.startswith('save '))
    deck = strip((SRC/'test.scs').read_text())
    base.exact_write(DEST/'test.scs', deck+''.join('save '+s+'\n' for s in sorted(m['voltage_saves']+m['current_saves'])))
    base.exact_write(DEST/'external_library.json', (SRC/'external_library.json').read_bytes())
    for path in sorted((SRC/'pwl').glob('*.pwl')):
        base.exact_write(DEST/'pwl'/path.name, path.read_bytes())
    recipe.update(run_id=NEW_RUN, design_id='sar8_control_native_RB_reset_inverter',
                  analyzer='standard_cell_rb_analyze.py', qualification_scope=m['scope'])
    files = []
    for item in recipe['inputs']:
        name = item['name']
        path = DEST/name if name in ['test.scs','dut.scs','measurement.json','external_library.json'] or name.startswith('pwl/') else ROOT/item['source']
        files.append((name,path))
    files.append(('standard_cell_rb_analyze.py', OWN/'standard_cell_rb_analyze.py'))
    recipe['inputs'] = [dict(name=name, source=path.relative_to(ROOT).as_posix(),
                            sha256=base.digest(path.read_bytes())) for name,path in files]
    recipe['summary_signals'] = [(P+s).lower() for s in
        ['clock_reset','xclock.rb','xclock.qb','xclock.sn','clock_q','live','x020.n','quiet']]
    base.write_json(DEST/'recipe.suggested.yaml', recipe)
    manifest = dict(base_run=RUN, base_recipe_sha256=HASH, source_proof=proof,
        removed_original_implementation=removed, added_library_MOS=sorted(added), unchanged_leaf_count=len(old)-2,
        shared_sar8p_sr_and_sar8p_inv_unchanged=True, private_SR_master='sar8audit_sr_rb_tcb',
        explicit_capacitors_added_or_removed=[], foundry_body_copied_or_modified=False,
        library_MOS_count=14, library_current_ports=56, total_MOS=101, total_passive=17,
        voltage_saves=62, current_saves=436, critical_KCL=61, physical_pairs=606, legacy_aliases=3,
        non_save_deck_byte_identical=True, unchanged_PWL=11,
        source_input_load_ports=reset_observers(False), candidate_input_load_ports=reset_observers(True),
        source_power_observations=dict(original_sources=5,other_existing_boundary_sources=7,passive_R0_ports=2),
        declared_input_files=len(files), declared_package_bytes=sum(p.stat().st_size for _,p in files),
        recipe_file_sha256=base.digest((DEST/'recipe.suggested.yaml').read_bytes()),
        remote_operations=False, simulation_completed=False, repair_claim=False)
    base.write_json(DEST/'change_manifest.json', manifest)
    base.write_json(DEST/'freeze.json', dict(recipe_sha256=manifest['recipe_file_sha256'],
        inputs=[dict(name=n,bytes=p.stat().st_size,sha256=base.digest(p.read_bytes())) for n,p in files]))
    import standard_cell_rb_analyze as observer
    cfg = copy.deepcopy(source_m)
    cfg['standard_cell_rb_experiment'] = copy.deepcopy(m['standard_cell_rb_experiment'])
    cfg['standard_cell_rb_experiment']['load_observers'] = reset_observers(False)
    folder = ROOT/'output/managed_execution/runs'/RUN/'collected/derived'
    base.write_json(DEST/'source_reset_reference.json', dict(source_run=RUN, source_recipe_sha256=HASH,
        source_proof=proof, reset=observer.reset_observations(str(folder),cfg),
        scope='Existing verified native source only; not a new simulation or candidate result.'))
    print(json.dumps({k:v for k,v in manifest.items() if k not in
        ['source_proof','removed_original_implementation','source_input_load_ports','candidate_input_load_ports']},indent=2))


if __name__ == '__main__':
    main()
