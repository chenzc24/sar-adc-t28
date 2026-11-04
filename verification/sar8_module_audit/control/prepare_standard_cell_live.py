"""Replace only complete X001 LIVE stage from the completed MN1+R0 source."""
import copy
import json

import prepare_first_event as base
import prepare_standard_cell as standard
from review_both_result import read_current_run

OWN,ROOT=base.OWN,base.ROOT
SRC,DEST=OWN/'standard_cell_r0_v1',OWN/'standard_cell_live_v1'
RUN='sar8audit-ctrl-stdcell-r0-ff-v1'
HASH='f182531c14a57e1a6aabb8a38fb532c17b7ae56b8889ec504e8fadc8244f990a'
NEW_RUN='sar8audit-ctrl-stdcell-live-ff-v1'
P='XDUT.XCTRL.XTIM.'
STAGE=P+'X001'


def replace_live(text):
    blocks=base.cells(text);timing=blocks['sar8audit_timing']
    original='X001 (SN ACTIVE VDD VSS LIVE) sar8p_and2'
    if timing.count(original)!=1:raise ValueError('Exact original LIVE stage boundary missing')
    timing=timing.replace(original,'X001 (SN ACTIVE VDD VSS LIVE) sar8audit_live_tcb')
    wrapper=('subckt sar8audit_live_tcb A B VDD VSS Y\n'
             '    X000 (A B N VDD VSS) ND2D1BWP12T30P140\n'
             '    X001 (N Y VDD VSS) INVD1BWP12T30P140\n'
             'ends sar8audit_live_tcb\n')
    return text.replace(blocks['sar8audit_timing'],timing)+'\n'+wrapper


def expand_twelve(text,probe):
    leaves=base.flatten(text,'sar8audit_ctrl_first_event',{'VDD':'VDD!','VSS':'0'});library={}
    for path,part in list(leaves.items()):
        if part['model'] not in standard.CELLS:continue
        pins=standard.CELLS[part['model']]
        if len(pins)!=len(part['nodes']):raise ValueError('Library port count differs')
        bindings=dict(zip(pins,part['nodes']));del leaves[path]
        for item in probe['cells'][part['model']]:
            key=path+'.'+item['instance']
            nodes=[bindings.get(item[t],path+'.'+item[t]) for t in ['D','G','S','B']]
            leaves[key]=dict(model=item['master'],nodes=nodes,parameters='EXTERNAL_FOUNDRY_PARAMETERS_NOT_COPIED')
            library[key]=dict(cell=part['model'],master=item['master'],nodes=nodes,
                requested_numeric_terminal_currents=[key+':'+str(i) for i in range(1,5)],
                known_inline_primitive=item['master'],primitive_probe_path_not_assumed=key+'.'+item['master'])
    if len(library)!=12:raise ValueError('Expected two NAND+INV library stages/twelve MOS')
    return leaves,library


def load_ports(foundry):
    nand=STAGE+'.X000.';inv=STAGE+'.X001.'
    return dict(
        SN=dict(node=P+'SN',ports=dict(NM_gate=nand+('MM4:2' if foundry else 'MN0:2'),PM_gate=nand+('MM1:2' if foundry else 'MP0:2')),role='external logical input A/SN'),
        ACTIVE=dict(node='XDUT.ACTIVE',ports=dict(NM_gate=nand+('MM9:2' if foundry else 'MN1:2'),PM_gate=nand+('MM2:2' if foundry else 'MP1:2')),role='external logical input B/ACTIVE'),
        INTERNAL_N=dict(node=STAGE+'.N',ports=dict(NM_gate=inv+('MM1:2' if foundry else 'MN:2'),PM_gate=inv+('MM0:2' if foundry else 'MP:2')),role='internal NAND output/INV input'))


def measurement(source,leaves,library,removed):
    m=standard.measurement(source,leaves,library)
    m['source_power_ports']=copy.deepcopy(source['source_power_ports'])
    m['stress_voltage_pairs']['MP1_VSG']['negative_node']=P+'X020.A1_FILTER'
    m['stress_voltage_pairs']['MP1_VGD']['positive_node']=P+'X020.A1_FILTER'
    old_exp=m['standard_cell_experiment'];old_exp.update(base_run=RUN,base_recipe_sha256=HASH)
    old_exp['historical_X020_removed_internal_capacitor']=old_exp.pop('removed_old_internal_capacitor')
    for name,item in old_exp['observed_mos'].items():
        item['group']='new_LIVE_library' if name.startswith(STAGE+'.') else 'existing_X020_library' if name in library else 'other_core'
    existing={p['current'].lower() for p in m['source_power_ports'].values()};boundary=[]
    for name,part in sorted(leaves.items()):
        if part['model']!='vsource' or (name+':1').lower() in existing:continue
        label='BOUNDARY_'+name.removeprefix('XDUT.').replace('.','_')
        m['source_power_ports'][label]=dict(voltage_node=part['nodes'][0],current=name+':1');boundary.append(label)
    if len(boundary)!=7:raise ValueError('Expected seven existing ideal command/input source observations')
    m['scope']='FF first event: whole X001 LIVE AND stage native foundry NAND+INV replacement from MN1+R0; not single-device causality or integrated qualification'
    m['standard_cell_live_experiment']=dict(base_run=RUN,base_recipe_sha256=HASH,
        replacement_boundary=STAGE,contract='LIVE = SN & ACTIVE',wrapper_ports=['A','B','VDD','VSS','Y'],
        external_mapping=dict(A=P+'SN',B='XDUT.ACTIVE',Y=P+'LIVE',VDD='VDD!',VSS='0'),
        NAND_mapping=['SN/A1','ACTIVE/A2','N/ZN','VDD','VSS'],INV_mapping=['N/I','LIVE/ZN','VDD','VSS'],
        removed_implementation=removed,load_observers=load_ports(True),event_charge_start_s=41e-9,
        boundary_source_power_labels=boundary,
        power_policy='Original five source work, seven other existing ideal PWL source work, and passive R0 absorption are separate. No added source or whole-ADC power claim.',
        classification='Whole logical stage replacement: device sizing/parasitics and explicit old MID capacitor change together.',
        acceptance_pass=None)
    if (len(m['voltage_saves']),len(m['current_saves']),len(m['critical_kcl_nodes']),len(m['stress_voltage_pairs']))!=(62,436,61,609):
        raise ValueError('Expected62V436I61KCL606physical+3aliases')
    return m


def source_reference(source_m,proof):
    import standard_cell_live_analyze as observer
    folder=ROOT/'output/managed_execution/runs'/RUN/'collected'
    receipt=json.loads((folder/'collection_receipt.json').read_bytes())
    for name in ['derived/peak.native.bin','derived/peak.columns.json']:
        item=next(i for i in receipt['files'] if i['name']==name);p=folder/name
        if p.stat().st_size!=item['bytes'] or base.digest(p.read_bytes())!=item['sha256']:raise ValueError('Source waveform identity differs')
    cfg=copy.deepcopy(source_m)
    cfg['standard_cell_live_experiment']=dict(load_observers=load_ports(False),event_charge_start_s=41e-9)
    base.write_json(DEST/'source_load_reference.json',dict(source_run=RUN,source_recipe_sha256=HASH,source_proof=proof,
        source_stage='original six custom MOS plus internal CMID, MN multi1',
        input_loads=observer.load_observations(str(folder/'derived'),cfg),
        policy='Local read-only reference from existing native diagnostic window; no new candidate result or simulation.'))


def main():
    _,_,_,oldm,proof=read_current_run(RUN,HASH)
    recipe=json.loads((SRC/'recipe.suggested.yaml').read_bytes())
    for item in recipe['inputs']:
        if base.digest((ROOT/item['source']).read_bytes())!=item['sha256']:raise ValueError('Frozen MN1+R0 source input changed')
    probe_item=next(i for i in recipe['inputs'] if i['name']=='probe_metadata.json')
    probe=json.loads((ROOT/probe_item['source']).read_bytes())
    text=(SRC/'dut.scs').read_text();changed=replace_live(text)
    old,_=standard.expanded_leaves(text,probe);new,library=expand_twelve(changed,probe)
    removed={k:v for k,v in old.items() if k.startswith(STAGE+'.')}
    if len(removed)!=7 or set(old)-set(new)!=set(removed):raise ValueError('Expected six old MOS and one CMID removed')
    added={k for k in new if k not in old}
    if len(added)!=6 or not all(k.startswith(STAGE+'.') for k in added):raise ValueError('Exactly six new LIVE library MOS expected')
    if any(new[k]!=old[k] for k in set(old)-set(removed)):raise ValueError('Unrelated leaf/source/X020/R0 changed')
    m=measurement(oldm,new,library,removed)
    base.exact_write(DEST/'dut.scs',changed);base.write_json(DEST/'measurement.json',m)
    deck=(SRC/'test.scs').read_text();strip=lambda s:''.join(line for line in s.splitlines(True) if not line.startswith('save '))
    generated=strip(deck)+''.join('save '+s+'\n' for s in sorted(m['voltage_saves']+m['current_saves']))
    if strip(generated)!=strip(deck):raise ValueError('Non-save deck changed')
    base.exact_write(DEST/'test.scs',generated);base.exact_write(DEST/'external_library.json',(SRC/'external_library.json').read_bytes())
    for p in sorted((SRC/'pwl').glob('*.pwl')):base.exact_write(DEST/'pwl'/p.name,p.read_bytes())
    loading_helper=OWN/'standard_cell_r0_mn2_analyze.py'
    previous_freeze=json.loads((OWN/'standard_cell_r0_mn2_v1/freeze.json').read_bytes())
    if base.digest(loading_helper.read_bytes())!=next(i['sha256'] for i in previous_freeze['inputs'] if i['name']==loading_helper.name):
        raise ValueError('Frozen gate-loading helper changed')
    recipe.update(run_id=NEW_RUN,design_id='sar8_control_native_standard_cell_LIVE_stage',
        analyzer='standard_cell_live_analyze.py',qualification_scope=m['scope'])
    files=[]
    for item in recipe['inputs']:
        n=item['name'];p=DEST/n if n in ['test.scs','dut.scs','measurement.json','external_library.json'] or n.startswith('pwl/') else ROOT/item['source'];files.append((n,p))
    files += [(loading_helper.name,loading_helper),('standard_cell_live_analyze.py',OWN/'standard_cell_live_analyze.py')]
    recipe['inputs']=[dict(name=n,source=p.relative_to(ROOT).as_posix(),sha256=base.digest(p.read_bytes())) for n,p in files]
    recipe['summary_signals']=[P.lower()+s for s in ['sn','x001.n','live','x020.a1_filter','x020.n','q1','quiet']]
    base.write_json(DEST/'recipe.suggested.yaml',recipe)
    manifest=dict(base_run=RUN,base_recipe_sha256=HASH,source_proof=proof,
        removed_original_implementation=removed,added_library_MOS=sorted(added),unchanged_leaf_count=len(old)-7,
        exact_old_internal_capacitor=removed[STAGE+'.X000.CMID'],
        new_internal_node=STAGE+'.X000.net10',retired_internal_node=STAGE+'.X000.MID',
        library_MOS_count=12,library_current_ports=48,total_MOS=101,total_passive=17,
        voltage_saves=62,current_saves=436,critical_KCL=61,physical_pairs=606,legacy_aliases=3,
        non_save_deck_byte_identical=True,unchanged_PWL=11,foundry_body_copied_or_modified=False,
        source_input_load_ports=load_ports(False),candidate_input_load_ports=load_ports(True),
        source_power_observations=dict(original_sources=5,other_existing_boundary_sources=7,passive_R0_ports=2),
        declared_input_files=len(files),declared_package_bytes=sum(p.stat().st_size for _,p in files),
        recipe_file_sha256=base.digest((DEST/'recipe.suggested.yaml').read_bytes()),remote_operations=False,simulation_completed=False,repair_claim=False)
    base.write_json(DEST/'change_manifest.json',manifest)
    base.write_json(DEST/'freeze.json',dict(recipe_sha256=manifest['recipe_file_sha256'],
        inputs=[dict(name=n,bytes=p.stat().st_size,sha256=base.digest(p.read_bytes())) for n,p in files]))
    source_reference(oldm,proof)
    print(json.dumps({k:v for k,v in manifest.items() if k not in ['source_proof','removed_original_implementation','exact_old_internal_capacitor','source_input_load_ports','candidate_input_load_ports']},indent=2))


if __name__=='__main__':main()
