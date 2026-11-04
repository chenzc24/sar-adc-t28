"""One original LIVE NMOS multi1->2; local preparation from completed R0 case."""
import copy
import json
import re

import prepare_first_event as base
import prepare_standard_cell as standard
from review_both_result import read_current_run

OWN, ROOT = base.OWN,base.ROOT
SRC, DEST = OWN/'standard_cell_r0_v1',OWN/'standard_cell_r0_mn2_v1'
RUN='sar8audit-ctrl-stdcell-r0-ff-v1'
HASH='f182531c14a57e1a6aabb8a38fb532c17b7ae56b8889ec504e8fadc8244f990a'
NEW_RUN='sar8audit-ctrl-stdcell-r0-mn2-ff-v1'
P='XDUT.XCTRL.XTIM.'
TARGET=P+'X001.X001.MN'
INPUT_NODE=P+'X001.N'
PM=P+'X001.X001.MP'


def specialize_one(text):
    blocks=base.cells(text);created={}
    def visit(master,prefix):
        if not TARGET.startswith(prefix+'.'):return master
        block=blocks[master]
        if re.search(r'(?m)^\s*(parameters|ic|nodeset|include|simulator|model|statistics)\b',block):
            raise ValueError('Unhandled non-instance statement in cloned source path')
        name=master if prefix=='XDUT' else 'sar8mn2_'+prefix.removeprefix('XDUT.').replace('.','_')
        header=block.replace('\\\n',' ').splitlines()[0].split()[2:]
        lines=['subckt '+name+' '+' '.join(header)]
        for instance,old in base.parts(block).items():
            part=copy.deepcopy(old);path=prefix+'.'+instance
            if path==TARGET:
                if part['model']!='nch_mac' or not all(re.search(r'\b'+key+'='+val+r'(?:\s|$)',part['parameters']) for key,val in [('l','30n'),('w','500n'),('nf','1'),('multi','1')]):
                    raise ValueError('Original target model/unit/multiplicity differs')
                part['parameters'],count=re.subn(r'\bmulti=1\b','multi=2',part['parameters'])
                if count!=1:raise ValueError('Exactly one multiplicity assignment required')
            elif part['model'] in blocks and TARGET.startswith(path+'.'):
                part['model']=visit(part['model'],path)
            lines.append('    '+instance+' ('+' '.join(part['nodes'])+') '+part['model']+
                (' '+part['parameters'] if part['parameters'] else ''))
        lines.append('ends '+name)
        created[name]='\n'.join(lines)
        return name
    visit('sar8audit_ctrl_first_event','XDUT')
    top='sar8audit_ctrl_first_event'
    if len(created)!=5:raise ValueError('Expected original top plus four private ancestor clones')
    changed=text.replace(blocks[top],created[top])
    changed+='\n\n'+'\n\n'.join(v for k,v in created.items() if k!=top)+'\n'
    return changed,sorted(k for k in created if k!=top)


def measurement(source):
    m=copy.deepcopy(source)
    m['scope']='FF first event: only original LIVE NMOS multi1->2, same unit geometry, R0, native standard cells and all histories; no integrated qualification'
    m['standard_cell_experiment']['observed_mos'][TARGET].update(group='changed_driver_NM',unit_multiplicity=2)
    m['standard_cell_r0_mn2_experiment']=dict(base_run=RUN,base_recipe_sha256=HASH,
        changed_instance=TARGET,unit_model='nch_mac',unit_W='500n',unit_L='30n',unit_nf=1,
        multiplicity_before=1,multiplicity_after=2,all_other_unit_parameters_unchanged=True,
        input_loading_node=INPUT_NODE,input_gate_current_ports=dict(changed_NM=TARGET+':2',unchanged_PM=PM+':2'),
        affected_input_KCL_terms=m['kcl_terms'][INPUT_NODE],
        changed_MOS_terminal_currents=[TARGET+':'+str(i) for i in range(1,5)],
        event_charge_start_s=41.075e-9,
        current_policy='Use total native returned terminal currents directly; never multiply currents by2 again. Gate exchange includes dynamic charge; no fixed C/Cgd or leakage-power inference.',
        preserved='Every terminal node, other leaf parameters, PM, RINPUT, library, source/11PWL, source/model/solver deck and external sample contract unchanged.',
        acceptance_pass=None)
    return m


def write_source_loading_reference(m,proof):
    """Apply the same loading reducer to verified, completed one-unit native rows."""
    import standard_cell_r0_mn2_analyze as observer
    folder=ROOT/'output/managed_execution/runs'/RUN/'collected'
    receipt=json.loads((folder/'collection_receipt.json').read_bytes())
    for name in ['derived/peak.native.bin','derived/peak.columns.json']:
        item=next(i for i in receipt['files'] if i['name']==name);path=folder/name
        if path.stat().st_size!=item['bytes'] or base.digest(path.read_bytes())!=item['sha256']:
            raise ValueError('Canonical source loading export does not match verified receipt')
    observed=observer.input_loading(str(folder/'derived'),m)
    base.write_json(DEST/'source_input_loading_reference.json',dict(source_run=RUN,source_recipe_sha256=HASH,
        source_proof=proof,actual_source_multiplicity=1,
        loading_observation=observed,
        policy='Read-only local reduction of completed source native rows with identical port/window definitions. No new simulation, candidate result, current scaling or source write. Ancillary, not a simulator input.'))


def main():
    _,_,result,source_m,proof=read_current_run(RUN,HASH)
    recipe=json.loads((SRC/'recipe.suggested.yaml').read_bytes())
    for item in recipe['inputs']:
        if base.digest((ROOT/item['source']).read_bytes())!=item['sha256']:
            raise ValueError('Frozen R0 source input changed')
    probe_item=next(i for i in recipe['inputs'] if i['name']=='probe_metadata.json')
    probe=json.loads((ROOT/probe_item['source']).read_bytes())
    text=(SRC/'dut.scs').read_text();changed,clones=specialize_one(text)
    old,_=standard.expanded_leaves(text,probe);new,_=standard.expanded_leaves(changed,probe)
    if set(old)!=set(new) or {k for k in old if old[k]!=new[k]}!={TARGET}:
        raise ValueError('Electrical leaf changes exceed one exact original NMOS')
    wanted=copy.deepcopy(old[TARGET]);wanted['parameters']=re.sub(r'\bmulti=1\b','multi=2',wanted['parameters'])
    if new[TARGET]!=wanted:raise ValueError('Per-unit geometry/node/model parameter changed')
    m=measurement(source_m)
    for key in ['voltage_saves','current_saves','terminal_current_catalog','kcl_terms','critical_kcl_nodes',
                'stress_voltage_pairs','source_power_ports','expected_initial_state']:
        if m[key]!=source_m[key]:raise ValueError('Existing measurements or imposed witness changed: '+key)
    base.exact_write(DEST/'dut.scs',changed)
    base.write_json(DEST/'measurement.json',m)
    for name in ['test.scs','external_library.json']:
        base.exact_write(DEST/name,(SRC/name).read_bytes())
    for p in sorted((SRC/'pwl').glob('*.pwl')):
        base.exact_write(DEST/'pwl'/p.name,p.read_bytes())
    recipe.update(run_id=NEW_RUN,design_id='sar8_control_R0_LIVE_NM_multiplicity2',
        analyzer='standard_cell_r0_mn2_analyze.py',qualification_scope=m['scope'])
    files=[]
    for item in recipe['inputs']:
        name=item['name'];local=DEST/name
        path=local if name in ['test.scs','dut.scs','measurement.json','external_library.json'] or name.startswith('pwl/') else ROOT/item['source']
        files.append((name,path))
    files.append(('standard_cell_r0_mn2_analyze.py',OWN/'standard_cell_r0_mn2_analyze.py'))
    recipe['inputs']=[dict(name=n,source=p.relative_to(ROOT).as_posix(),sha256=base.digest(p.read_bytes())) for n,p in files]
    recipe['summary_signals']=recipe['summary_signals']+[INPUT_NODE.lower()]
    base.write_json(DEST/'recipe.suggested.yaml',recipe)
    input_ports={label:trace.lower() for label,trace in m['standard_cell_r0_mn2_experiment']['input_gate_current_ports'].items()}
    manifest=dict(base_run=RUN,base_recipe_sha256=HASH,source_proof=proof,
        exact_changed_leaf=dict(instance=TARGET,before=old[TARGET],after=new[TARGET]),
        unchanged_leaf_count=len(old)-1,leaf_count=len(old),new_or_removed_leaves=0,
        private_ancestor_clones=clones,instance_and_node_paths_unchanged=True,
        test_deck_byte_identical=True,original_PWL_byte_identical=11,
        entire_existing_voltage_current_KCL_stress_and_power_catalogs_identical=True,
        total_MOS_instances=101,total_passive=18,voltage_saves=62,current_saves=437,critical_KCL=61,
        physical_terminal_pairs=606,legacy_aliases=3,
        source_input_loading_full_history_reference=dict(node=result['voltage_and_current_extrema'][INPUT_NODE.lower()],
            gate_current_extrema={label:result['voltage_and_current_extrema'][trace] for label,trace in input_ports.items()},
            caution='Reference for actual source only; new multi2 loading must be measured, not presumed2x.'),
        reused_helper_sha256={n:base.digest(p.read_bytes()) for n,p in files if n.endswith('_analyze.py') and n!='standard_cell_r0_mn2_analyze.py'},
        declared_input_files=len(files),declared_package_bytes=sum(p.stat().st_size for _,p in files),
        recipe_file_sha256=base.digest((DEST/'recipe.suggested.yaml').read_bytes()),
        remote_operations=False,simulation_completed=False,repair_claim=False)
    base.write_json(DEST/'change_manifest.json',manifest)
    base.write_json(DEST/'freeze.json',dict(recipe_sha256=manifest['recipe_file_sha256'],
        inputs=[dict(name=n,bytes=p.stat().st_size,sha256=base.digest(p.read_bytes())) for n,p in files]))
    write_source_loading_reference(m,proof)
    print(json.dumps({k:v for k,v in manifest.items() if k not in
        ['source_proof','exact_changed_leaf','source_input_loading_full_history_reference','reused_helper_sha256']},indent=2))


if __name__=='__main__':
    main()
