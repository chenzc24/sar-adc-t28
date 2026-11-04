"""Prepare only XCLOCK.X003 series-NM gate swap; Q upper, RB lower."""
import copy
import json

import prepare_first_event as base
import prepare_standard_cell_resetnand as mapping
from review_both_result import read_current_run
from review_standard_cell_result import collected

OWN, ROOT = base.OWN, base.ROOT
SRC, DEST = OWN/'standard_cell_qbcap_v1', OWN/'standard_cell_qborder_v1'
RUN = 'sar8audit-ctrl-stdcell-qbcap-ff-q2'
HASH = 'ae800c95066a921a5df6e9101c29adecdf7a6e761cac71b1490ed0f1b30920b0'
NEW_RUN = 'sar8audit-ctrl-stdcell-qborder-ff-v1'
P = mapping.P
NAND = P+'XCLOCK.X003'
RB, Q = P+'XCLOCK.RB', P+'CLOCK_Q'


def replace_qborder(text):
    blocks=base.cells(text);timing=blocks['sar8audit_timing']
    old='XCLOCK (CLOCK_Q CLOCK_RESET CLOCK_SET VDD VSS) sar8audit_sr_rb_qbcap'
    if timing.count(old)!=1:
        raise ValueError('Exact multi1 SR reference missing')
    timing=timing.replace(old,old.removesuffix('sar8audit_sr_rb_qbcap')+'sar8audit_sr_qborder')
    sr=blocks['sar8audit_sr_rb_qbcap'];branch='X003 (RB Q VDD VSS QB) sar8audit_nand_qbcap1'
    if sr.count(branch)!=1:
        raise ValueError('Exact QB NAND reference missing')
    sr=sr.replace('subckt sar8audit_sr_rb_qbcap ','subckt sar8audit_sr_qborder ',1)
    sr=sr.replace('ends sar8audit_sr_rb_qbcap','ends sar8audit_sr_qborder',1)
    sr=sr.replace(branch,branch.removesuffix('sar8audit_nand_qbcap1')+'sar8audit_nand_qborder')
    nand=blocks['sar8audit_nand_qbcap1']
    nand=nand.replace('subckt sar8audit_nand_qbcap1 ','subckt sar8audit_nand_qborder ',1)
    nand=nand.replace('ends sar8audit_nand_qbcap1','ends sar8audit_nand_qborder',1)
    for a,b in [('MN0 (Y A MID VSS) nch_mac','MN0 (Y B MID VSS) nch_mac'),
                ('MN1 (MID B VSS VSS) nch_mac','MN1 (MID A VSS VSS) nch_mac')]:
        if nand.count(a)!=1:
            raise ValueError('Exact NM gate binding missing: '+a)
        nand=nand.replace(a,b)
    return text.replace(blocks['sar8audit_timing'],timing)+'\n'+sr+'\n'+nand+'\n'


def complete_gate_ports(cfg,node):
    return {p.removeprefix(P).replace('.','_').replace(':','_'):p
            for p,item in sorted(cfg['terminal_current_catalog'].items())
            if item['node']==node and item['terminal']=='G'}


def bind_gate_observers(cfg):
    observers=cfg['standard_cell_rb_experiment']['load_observers']
    ports=[p for p,item in cfg['terminal_current_catalog'].items() if p.startswith(NAND+'.')
           and item['terminal']=='G' and item['node']==RB
           and cfg['standard_cell_experiment']['observed_mos'][item['instance']]['model'].startswith('nch_')]
    if len(ports)!=1:
        raise ValueError('Expected one QB-NAND NM gate driven by RB')
    observers['RB']['ports']['QB_NM_gate']=ports[0]
    observers['CLOCK_Q']['ports']=complete_gate_ports(cfg,Q)
    observers['CLOCK_Q']['role']='Actual SR output: complete four-gate Q fanout, no imposed clock edge'
    if len(observers['CLOCK_Q']['ports'])!=4 or set(observers['RB']['ports'].values())!=set(complete_gate_ports(cfg,RB).values()):
        raise ValueError('Complete RB/Q gate-fanout coverage differs')


def measurement(old,leaves):
    m=copy.deepcopy(old)
    for path in [NAND+'.MN0',NAND+'.MN1']:
        nodes=leaves[path]['nodes'];item=m['standard_cell_experiment']['observed_mos'][path]
        item['nodes']=nodes
        for port,node in enumerate(nodes,1):
            m['terminal_current_catalog'][path+':'+str(port)]['node']=node
        d,g,s,b=nodes
        for suffix,(a,z) in dict(VGS=(g,s),VGD=(g,d),VDS=(d,s),VGB=(g,b),VDB=(d,b),VSB=(s,b)).items():
            pair=m['stress_voltage_pairs'][item['six_pair_labels'][suffix]]
            pair.update(positive_node=a,negative_node=z)
    m['kcl_terms']={n:[p.lower() for p,item in m['terminal_current_catalog'].items() if item['node']==n]
                    for n in m['voltage_saves'] if n!='VDD!'}
    m['critical_kcl_nodes']=sorted(m['kcl_terms'])
    bind_gate_observers(m)
    internal={n.lower() for n in [RB,Q,P+'XCLOCK.QB',NAND+'.MID']}
    if internal & set(m['expected_initial_state']['values_v']):
        raise ValueError('Do not impose original internal initial state')
    m['scope']=('FF0.99V/-40C first-event NM gate-order comparison in XCLOCK.X003 only; '
                'Q upper/RB lower, same PM/MIDmulti1/sources/history; full SR set/reset not exercised')
    m['standard_cell_qborder_experiment']=dict(base_run=RUN,base_recipe_sha256=HASH,
        changed_instances=[NAND+'.MN0',NAND+'.MN1'],
        source_gate_bindings={NAND+'.MN0':RB,NAND+'.MN1':Q},
        candidate_gate_bindings={NAND+'.MN0':Q,NAND+'.MN1':RB},
        unchanged_D_S_B_geometry_PM_and_MID=True,
        actual_RB_gate_load_ports=m['standard_cell_rb_experiment']['load_observers']['RB']['ports'],
        actual_Q_gate_load_ports=m['standard_cell_rb_experiment']['load_observers']['CLOCK_Q']['ports'],
        natural_initial_state_policy='No added ic/nodeset/internal replay or peak reproduction requirement; only original imposed-source initial witnesses.',
        acceptance_gaps=['Full CLOCK_SET assertion: Q rise/QB fall and latch persistence not covered.',
                         'Reset assertion starting from Qhigh: QB rise/Q clear and reset priority not covered.'],
        scope='First sample-close/reset-release observation only, not both-direction SR qualification.',acceptance_pass=None)
    return m


def main():
    _,_,source_result,oldm,proof=read_current_run(RUN,HASH)
    recipe=json.loads((SRC/'recipe.suggested.yaml').read_bytes())
    for item in recipe['inputs']:
        if base.digest((ROOT/item['source']).read_bytes())!=item['sha256']:
            raise ValueError('Frozen multi1 source input changed')
    probe_file=next(i for i in recipe['inputs'] if i['name']=='probe_metadata.json')
    probe=json.loads((ROOT/probe_file['source']).read_bytes())
    text=(SRC/'dut.scs').read_text();changed=replace_qborder(text)
    old,oldlib=mapping.expand_eighteen(text,probe);new,library=mapping.expand_eighteen(changed,probe)
    if old.keys()!=new.keys() or library!=oldlib:
        raise ValueError('Actual leaf set/foundry library binding changed')
    differences={p for p in old if old[p]!=new[p]}
    if differences!={NAND+'.MN0',NAND+'.MN1'}:
        raise ValueError('Only two QB NAND NM gate nodes may change')
    for name,gate in [('MN0',Q),('MN1',RB)]:
        path=NAND+'.'+name;expected=copy.deepcopy(old[path]);expected['nodes'][1]=gate
        if expected!=new[path]:
            raise ValueError('NM geometry/D/S/B changed beyond gate assignment')
    m=measurement(oldm,new)
    base.exact_write(DEST/'dut.scs',changed);base.write_json(DEST/'measurement.json',m)
    for name in ['test.scs','external_library.json']:
        base.exact_write(DEST/name,(SRC/name).read_bytes())
    for p in sorted((SRC/'pwl').glob('*.pwl')):
        base.exact_write(DEST/'pwl'/p.name,p.read_bytes())
    recipe.update(run_id=NEW_RUN,design_id='sar8_control_QB_NAND_Q_upper_RB_lower',
                  analyzer='standard_cell_qborder_analyze.py',qualification_scope=m['scope'])
    files=[]
    for item in recipe['inputs']:
        n=item['name'];p=DEST/n if n in ['test.scs','dut.scs','measurement.json','external_library.json'] or n.startswith('pwl/') else ROOT/item['source']
        files.append((n,p))
    files.append(('standard_cell_qborder_analyze.py',OWN/'standard_cell_qborder_analyze.py'))
    recipe['inputs']=[dict(name=n,source=p.relative_to(ROOT).as_posix(),sha256=base.digest(p.read_bytes())) for n,p in files]
    base.write_json(DEST/'recipe.suggested.yaml',recipe)
    manifest=dict(base_run=RUN,base_recipe_sha256=HASH,source_proof=proof,
        changed_instances={p:dict(before=old[p],after=new[p]) for p in sorted(differences)},
        unchanged_leaf_count=len(old)-2,no_added_or_removed_leaves=True,
        private_masters=['sar8audit_sr_qborder','sar8audit_nand_qborder'],shared_masters_unchanged=True,
        unchanged_PM_and_MID_multi1=True,library_MOS_count=18,library_current_ports=72,
        total_MOS=101,total_passive=16,voltage_saves=62,current_saves=435,critical_KCL=61,
        physical_pairs=606,legacy_aliases=3,test_deck_byte_identical=True,unchanged_PWL=11,
        gate_catalog_changed_ports=[NAND+'.MN0:2',NAND+'.MN1:2'],
        candidate_RB_gate_ports=m['standard_cell_qborder_experiment']['actual_RB_gate_load_ports'],
        candidate_Q_gate_ports=m['standard_cell_qborder_experiment']['actual_Q_gate_load_ports'],
        no_new_internal_initial_conditions=True,full_SR_set_reset_qualification=False,
        foundry_body_copied_or_modified=False,declared_input_files=len(files),
        declared_package_bytes=sum(p.stat().st_size for _,p in files),
        recipe_file_sha256=base.digest((DEST/'recipe.suggested.yaml').read_bytes()),
        remote_operations=False,simulation_completed=False,repair_claim=False)
    base.write_json(DEST/'change_manifest.json',manifest)
    base.write_json(DEST/'freeze.json',dict(recipe_sha256=manifest['recipe_file_sha256'],
        inputs=[dict(name=n,bytes=p.stat().st_size,sha256=base.digest(p.read_bytes())) for n,p in files]))
    import standard_cell_qborder_analyze as observer
    cfg=copy.deepcopy(oldm);bind_gate_observers(cfg)
    raw=collected(RUN);folder=ROOT/'output/managed_execution/runs'/RUN/'collected/derived'
    for name in ['peak.native.bin','peak.columns.json']:
        if (folder/name).read_bytes()!=raw['derived/'+name]:
            raise ValueError('Canonical source native rows differ from verified receipt')
    reset=observer.rb.reset_observations(str(folder),cfg)
    base.write_json(DEST/'source_observation_reference.json',dict(source_run=RUN,source_recipe_sha256=HASH,
        source_proof=proof,gate_order='RB upper/Q lower, same multi1 MID',
        RB_gate_loads=reset['nodes']['RB'],Q_gate_loads=reset['nodes']['CLOCK_Q'],
        storage=source_result['QB_storage_observations'],
        scope='Read-only prior q2 native observations; complete original Q gate fanout extracted from saved currents, not a new candidate result.'))
    print(json.dumps({k:v for k,v in manifest.items() if k not in
        ['source_proof','changed_instances','candidate_RB_gate_ports','candidate_Q_gate_ports']},indent=2))


if __name__=='__main__':
    main()
