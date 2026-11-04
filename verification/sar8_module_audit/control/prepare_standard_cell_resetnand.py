"""Prepare only X023.X002 native NAND replacement from the completed RB case."""
import copy
import json

import prepare_first_event as base
import prepare_standard_cell as standard
import prepare_standard_cell_rb as rb
from review_both_result import read_current_run

OWN, ROOT = base.OWN, base.ROOT
SRC, DEST = OWN/'standard_cell_rb_v1', OWN/'standard_cell_resetnand_v1'
RUN = 'sar8audit-ctrl-stdcell-rb-ff-v1'
HASH = '745d10a01ded0cc487e7d2e5ff4ba57d130f7de2ec4e2959979f937375524bc4'
NEW_RUN = 'sar8audit-ctrl-stdcell-resetnand-ff-v1'
P = rb.P
OR = P+'X023'
TARGET = OR+'.X002'


def replace_resetnand(text):
    blocks = base.cells(text)
    timing = blocks['sar8audit_timing']
    boundary = 'X023 (SAMPLE PHI_U VDD VSS CLOCK_RESET) sar8p_or2'
    if timing.count(boundary)!=1:
        raise ValueError('Exact CLOCK_RESET OR boundary missing')
    timing = timing.replace(boundary,boundary.removesuffix('sar8p_or2')+'sar8audit_or_resetnand_tcb')
    cell = blocks['sar8p_or2']
    original = 'X002 (AB BB VDD VSS Y) sar8p_nand2'
    if cell.count(original)!=1:
        raise ValueError('Exact original CLOCK_RESET NAND missing')
    cell = cell.replace('subckt sar8p_or2 ','subckt sar8audit_or_resetnand_tcb ',1)
    cell = cell.replace('ends sar8p_or2','ends sar8audit_or_resetnand_tcb',1)
    cell = cell.replace(original,'X002 (AB BB Y VDD VSS) ND2D1BWP12T30P140')
    return text.replace(blocks['sar8audit_timing'],timing)+'\n'+cell+'\n'


def expand_eighteen(text, probe):
    leaves = base.flatten(text,'sar8audit_ctrl_first_event',{'VDD':'VDD!','VSS':'0'})
    library = {}
    for path,part in list(leaves.items()):
        if part['model'] not in standard.CELLS:
            continue
        pins = standard.CELLS[part['model']]
        if len(pins)!=len(part['nodes']):
            raise ValueError('Foundry pin count differs')
        binding = dict(zip(pins,part['nodes'])); del leaves[path]
        for item in probe['cells'][part['model']]:
            key = path+'.'+item['instance']
            nodes = [binding.get(item[t],path+'.'+item[t]) for t in ['D','G','S','B']]
            leaves[key] = dict(model=item['master'],nodes=nodes,
                               parameters='EXTERNAL_FOUNDRY_PARAMETERS_NOT_COPIED')
            library[key] = dict(cell=part['model'],master=item['master'],nodes=nodes,
                requested_numeric_terminal_currents=[key+':'+str(i) for i in range(1,5)],
                known_inline_primitive=item['master'],primitive_probe_path_not_assumed=key+'.'+item['master'])
    if len(library)!=18:
        raise ValueError('Expected fourteen retained plus four new library MOS')
    return leaves,library


def input_observers(foundry):
    return dict(
        AB=dict(node=OR+'.AB',ports=dict(
            NM_gate=TARGET+('.MM4:2' if foundry else '.MN0:2'),
            PM_gate=TARGET+('.MM1:2' if foundry else '.MP0:2')),
            role='Actual SAMPLE inverter output; output-adjacent NAND input A1'),
        BB=dict(node=OR+'.BB',ports=dict(
            NM_gate=TARGET+('.MM9:2' if foundry else '.MN1:2'),
            PM_gate=TARGET+('.MM2:2' if foundry else '.MP1:2')),
            role='Actual PHI_U inverter output; lower NAND input A2'))


def measurement(source, leaves, library, removed):
    clean = copy.deepcopy(source)
    for item in source['standard_cell_experiment']['observed_mos'].values():
        for label in item['six_pair_labels'].values():
            del clean['stress_voltage_pairs'][label]
    m = standard.measurement(clean,leaves,library)
    m['source_power_ports'] = copy.deepcopy(source['source_power_ports'])
    m['stress_voltage_pairs']['MP1_VSG']['negative_node'] = P+'X020.A1_FILTER'
    m['stress_voltage_pairs']['MP1_VGD']['positive_node'] = P+'X020.A1_FILTER'
    exp = m['standard_cell_experiment']
    exp.update(base_run=RUN,base_recipe_sha256=HASH)
    exp['historical_X020_removed_internal_capacitor'] = exp.pop('removed_old_internal_capacitor')
    exp['current_binding'] = ('Actual MM numeric D/G/S/B ports1/2/3/4; same ND2D1 already '
                              'verified in X001/X020. New paths must bind natively; no zeros or guessed primitive paths.')
    for path,item in exp['observed_mos'].items():
        item['group'] = ('new_RESET_NAND_library' if path.startswith(TARGET+'.') else
                         'existing_library' if path in library else 'other_core')
    m['scope'] = ('FF0.99V/-40C first-event X023.X002 whole output NAND replacement only; '
                  'AB/A1 and BB/A2, real two INV drivers and RB/SR loads; not full-chain qualification')
    m['standard_cell_resetnand_experiment'] = dict(
        base_run=RUN,base_recipe_sha256=HASH,replacement_boundary=TARGET,
        contract='CLOCK_RESET = SAMPLE OR PHI_U, using unchanged AB=NOT SAMPLE and BB=NOT PHI_U',
        NAND_mapping=['AB/A1','BB/A2','CLOCK_RESET/ZN','VDD','VSS'],
        removed_implementation=removed,removed_explicit_capacitor=removed[TARGET+'.CMID'],
        added_explicit_capacitors=[],new_internal_node=TARGET+'.net10',retired_internal_node=TARGET+'.MID',
        load_observers=input_observers(True),event_charge_start_s=41e-9,
        classification='Whole4MOS+MID-cap implementation replacement. Dimensions/intrinsic parasitics and old explicit capacitor change together.',
        acceptance_pass=None)
    m['terminal_voltage_policy']['method'] = ('Six simultaneous native terminal pairs per101 MOS '
                                            'zero-to-END plus3 legacy aliases; all core limits0.99V unchanged.')
    if (len(m['voltage_saves']),len(m['current_saves']),len(m['critical_kcl_nodes']),len(m['stress_voltage_pairs']))!=(62,435,61,609):
        raise ValueError('Expected62V435I61KCL606physical+3aliases after one cap removal')
    return m


def main():
    _,_,_,source_m,proof = read_current_run(RUN,HASH)
    recipe = json.loads((SRC/'recipe.suggested.yaml').read_bytes())
    for item in recipe['inputs']:
        if base.digest((ROOT/item['source']).read_bytes())!=item['sha256']:
            raise ValueError('Frozen RB source input differs')
    probe_file = next(i for i in recipe['inputs'] if i['name']=='probe_metadata.json')
    probe = json.loads((ROOT/probe_file['source']).read_bytes())
    text = (SRC/'dut.scs').read_text(); changed = replace_resetnand(text)
    old,_ = rb.expand_fourteen(text,probe); new,library = expand_eighteen(changed,probe)
    removed = {k:v for k,v in old.items() if k.startswith(TARGET+'.')}
    added = set(new)-set(old)
    if (len(removed)!=5 or removed[TARGET+'.CMID']['model']!='cfmom_2t'
            or set(old)-set(new)!=set(removed)
            or added!={TARGET+'.'+s for s in ['MM4','MM9','MM1','MM2']}):
        raise ValueError('Expected only original4MOS+oneMIDcap replaced by native4MOS')
    if any(old[k]!=new[k] for k in set(old)-set(removed)):
        raise ValueError('Real upstream INV/RB/SR or other retained leaf changed')
    m = measurement(source_m,new,library,removed)
    base.exact_write(DEST/'dut.scs',changed); base.write_json(DEST/'measurement.json',m)
    strip = lambda s: ''.join(line for line in s.splitlines(True) if not line.startswith('save '))
    deck = strip((SRC/'test.scs').read_text())
    base.exact_write(DEST/'test.scs',deck+''.join('save '+s+'\n' for s in sorted(m['voltage_saves']+m['current_saves'])))
    base.exact_write(DEST/'external_library.json',(SRC/'external_library.json').read_bytes())
    for path in sorted((SRC/'pwl').glob('*.pwl')):
        base.exact_write(DEST/'pwl'/path.name,path.read_bytes())
    recipe.update(run_id=NEW_RUN,design_id='sar8_control_native_CLOCK_RESET_NAND',
                  analyzer='standard_cell_resetnand_analyze.py',qualification_scope=m['scope'])
    files = []
    for item in recipe['inputs']:
        n = item['name']
        path = DEST/n if n in ['test.scs','dut.scs','measurement.json','external_library.json'] or n.startswith('pwl/') else ROOT/item['source']
        files.append((n,path))
    files.append(('standard_cell_resetnand_analyze.py',OWN/'standard_cell_resetnand_analyze.py'))
    recipe['inputs'] = [dict(name=n,source=p.relative_to(ROOT).as_posix(),sha256=base.digest(p.read_bytes())) for n,p in files]
    recipe['summary_signals'] = [(P+s).lower() for s in
        ['x023.ab','x023.bb','clock_reset','xclock.rb','xclock.qb','xclock.sn','clock_q','quiet']]
    base.write_json(DEST/'recipe.suggested.yaml',recipe)
    manifest = dict(base_run=RUN,base_recipe_sha256=HASH,source_proof=proof,
        removed_original_implementation=removed,added_library_MOS=sorted(added),unchanged_leaf_count=len(old)-5,
        private_OR_master='sar8audit_or_resetnand_tcb',shared_OR_NAND_INV_unchanged=True,
        removed_explicit_capacitor=removed[TARGET+'.CMID'],added_explicit_capacitors=[],
        new_internal_node=TARGET+'.net10',retired_internal_node=TARGET+'.MID',
        library_MOS_count=18,library_current_ports=72,total_MOS=101,total_passive=16,
        voltage_saves=62,current_saves=435,critical_KCL=61,physical_pairs=606,legacy_aliases=3,
        non_save_deck_byte_identical=True,unchanged_PWL=11,foundry_body_copied_or_modified=False,
        source_input_load_ports=input_observers(False),candidate_input_load_ports=input_observers(True),
        source_power_observations=dict(original_sources=5,other_existing_boundary_sources=7,passive_R0_ports=2),
        declared_input_files=len(files),declared_package_bytes=sum(p.stat().st_size for _,p in files),
        recipe_file_sha256=base.digest((DEST/'recipe.suggested.yaml').read_bytes()),
        remote_operations=False,simulation_completed=False,repair_claim=False)
    base.write_json(DEST/'change_manifest.json',manifest)
    base.write_json(DEST/'freeze.json',dict(recipe_sha256=manifest['recipe_file_sha256'],
        inputs=[dict(name=n,bytes=p.stat().st_size,sha256=base.digest(p.read_bytes())) for n,p in files]))
    import standard_cell_resetnand_analyze as observer
    cfg = copy.deepcopy(source_m)
    cfg['standard_cell_resetnand_experiment'] = copy.deepcopy(m['standard_cell_resetnand_experiment'])
    cfg['standard_cell_resetnand_experiment']['load_observers'] = input_observers(False)
    folder = ROOT/'output/managed_execution/runs'/RUN/'collected/derived'
    base.write_json(DEST/'source_input_load_reference.json',dict(source_run=RUN,source_recipe_sha256=HASH,
        source_proof=proof,input_loads=observer.nand_input_loading(str(folder),cfg),
        scope='Read-only existing native RB source; no new simulation or candidate result.'))
    print(json.dumps({k:v for k,v in manifest.items() if k not in
        ['source_proof','removed_original_implementation','removed_explicit_capacitor','source_input_load_ports','candidate_input_load_ports']},indent=2))


if __name__=='__main__':
    main()
