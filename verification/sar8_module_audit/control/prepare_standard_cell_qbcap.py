"""Prepare only native XCLOCK.X003.CMID multi2->1, locally."""
import copy
import json
import re

import prepare_first_event as base
import prepare_standard_cell_resetnand as source
from review_both_result import read_current_run
from review_standard_cell_result import collected

OWN, ROOT = base.OWN, base.ROOT
SRC, DEST = OWN/'standard_cell_resetnand_v1', OWN/'standard_cell_qbcap_v1'
RUN = 'sar8audit-ctrl-stdcell-resetnand-ff-v1'
HASH = '7f60d766e2c8f6f4b964d5744cdd1442292e7f86485596b8374694a5ec616c9d'
NEW_RUN = 'sar8audit-ctrl-stdcell-qbcap-ff-v1'
P = source.P
NAND = P+'XCLOCK.X003'
TARGET = NAND+'.CMID'
MID, QB = NAND+'.MID', P+'XCLOCK.QB'


def replace_qbcap(text):
    blocks = base.cells(text)
    old = 'XCLOCK (CLOCK_Q CLOCK_RESET CLOCK_SET VDD VSS) sar8audit_sr_rb_tcb'
    timing = blocks['sar8audit_timing']
    if timing.count(old)!=1:
        raise ValueError('Exact current clock SR reference missing')
    timing = timing.replace(old,old.removesuffix('sar8audit_sr_rb_tcb')+'sar8audit_sr_rb_qbcap')
    sr = blocks['sar8audit_sr_rb_tcb']
    branch = 'X003 (RB Q VDD VSS QB) sar8p_nand2'
    if sr.count(branch)!=1:
        raise ValueError('Exact QB NAND reference missing')
    sr = sr.replace('subckt sar8audit_sr_rb_tcb ','subckt sar8audit_sr_rb_qbcap ',1)
    sr = sr.replace('ends sar8audit_sr_rb_tcb','ends sar8audit_sr_rb_qbcap',1)
    sr = sr.replace(branch,branch.removesuffix('sar8p_nand2')+'sar8audit_nand_qbcap1')
    nand = blocks['sar8p_nand2']
    nand = nand.replace('subckt sar8p_nand2 ','subckt sar8audit_nand_qbcap1 ',1)
    nand = nand.replace('ends sar8p_nand2','ends sar8audit_nand_qbcap1',1)
    nand,count = re.subn(r'(?m)^(\s*CMID\s+\(MID VSS\)[^\n]*\bmulti=)2\b',r'\g<1>1',nand)
    if count!=1:
        raise ValueError('Expected exactly one native MOM multi2->1 change')
    return text.replace(blocks['sar8audit_timing'],timing)+'\n'+sr+'\n'+nand+'\n'


def measurement(old, oldcap, newcap):
    m = copy.deepcopy(old)
    ports = dict((suffix,NAND+'.'+suffix) for suffix in
                 ['MN0:1','MN0:2','MN0:3','MN0:4','MN1:1','MP1:1','CMID:1'])
    m['scope'] = ('FF0.99V/-40C first event: only XCLOCK.X003.CMID multi2->1; '
                  'all MOS/drivers/logic/PWL/sample edges unchanged; no presumed repair')
    m['standard_cell_qbcap_experiment'] = dict(base_run=RUN,base_recipe_sha256=HASH,
        changed_component=TARGET,old_component=oldcap,new_component=newcap,
        actual_capacitor_multi=1,QB_node=QB,MID_node=MID,
        observed_MOS=[NAND+'.'+s for s in ['MN0','MN1','MP0','MP1']],
        observed_charge_ports=ports,recovery_reference_v=.99,recovery_band_v=.001,
        phase_before_RB10_s=1e-12,phase_after_minimum_s=30e-12,
        current_policy='Actual returned total terminal currents already include capacitor/model multiplicity; never multiply by2 or divide by2 in analysis.',
        energy_policy='Unchanged full-history five source/seven boundary/R0 accounting. Additional local charge and port-work integrals are diagnostic-window observations, not complete ADC power or unique dissipation.',
        region_Vth_channel_components_saved=False,acceptance_pass=None)
    return m


def main():
    _,_,source_result,oldm,proof = read_current_run(RUN,HASH)
    recipe = json.loads((SRC/'recipe.suggested.yaml').read_bytes())
    for item in recipe['inputs']:
        if base.digest((ROOT/item['source']).read_bytes())!=item['sha256']:
            raise ValueError('Frozen reset-NAND source input changed')
    probe_file = next(i for i in recipe['inputs'] if i['name']=='probe_metadata.json')
    probe = json.loads((ROOT/probe_file['source']).read_bytes())
    text = (SRC/'dut.scs').read_text(); changed = replace_qbcap(text)
    old,old_library = source.expand_eighteen(text,probe)
    new,library = source.expand_eighteen(changed,probe)
    if old.keys()!=new.keys() or library!=old_library:
        raise ValueError('Actual instance/node or foundry MOS mapping changed')
    different = [k for k in old if old[k]!=new[k]]
    if different!=[TARGET] or old[TARGET]['model']!='cfmom_2t':
        raise ValueError('Only QB native MOM must change')
    expected = copy.deepcopy(old[TARGET])
    expected['parameters'],count = re.subn(r'\bmulti=2\b','multi=1',expected['parameters'])
    if count!=1 or new[TARGET]!=expected:
        raise ValueError('Cap nodes/model/unit geometry changed beyond multi2->1')
    m = measurement(oldm,old[TARGET],new[TARGET])
    base.exact_write(DEST/'dut.scs',changed);base.write_json(DEST/'measurement.json',m)
    for name in ['test.scs','external_library.json']:
        base.exact_write(DEST/name,(SRC/name).read_bytes())
    for path in sorted((SRC/'pwl').glob('*.pwl')):
        base.exact_write(DEST/'pwl'/path.name,path.read_bytes())
    recipe.update(run_id=NEW_RUN,design_id='sar8_control_QB_MID_native_MOM_multi1',
                  analyzer='standard_cell_qbcap_analyze.py',qualification_scope=m['scope'])
    files = []
    for item in recipe['inputs']:
        name = item['name']
        path = DEST/name if name in ['test.scs','dut.scs','measurement.json','external_library.json'] or name.startswith('pwl/') else ROOT/item['source']
        files.append((name,path))
    files.append(('standard_cell_qbcap_analyze.py',OWN/'standard_cell_qbcap_analyze.py'))
    recipe['inputs'] = [dict(name=n,source=p.relative_to(ROOT).as_posix(),sha256=base.digest(p.read_bytes())) for n,p in files]
    recipe['summary_signals'] = [(P+s).lower() for s in
        ['clock_reset','xclock.rb','xclock.qb','xclock.x003.mid','clock_q','xclock.sn']]
    base.write_json(DEST/'recipe.suggested.yaml',recipe)
    manifest = dict(base_run=RUN,base_recipe_sha256=HASH,source_proof=proof,
        changed_component=TARGET,old_component=old[TARGET],new_component=new[TARGET],
        unchanged_leaf_count=len(old)-1,no_added_or_removed_leaves=True,
        private_masters=['sar8audit_sr_rb_qbcap','sar8audit_nand_qbcap1'],
        shared_masters_unchanged=True,all_MOS_and_logic_unchanged=True,
        library_MOS_count=18,library_current_ports=72,total_MOS=101,total_passive=16,
        voltage_saves=62,current_saves=435,critical_KCL=61,physical_pairs=606,legacy_aliases=3,
        all_save_catalogs_and_source_power_ports_unchanged=True,test_deck_byte_identical=True,
        unchanged_PWL=11,foundry_body_copied_or_modified=False,
        declared_input_files=len(files),declared_package_bytes=sum(p.stat().st_size for _,p in files),
        recipe_file_sha256=base.digest((DEST/'recipe.suggested.yaml').read_bytes()),
        remote_operations=False,simulation_completed=False,repair_claim=False)
    base.write_json(DEST/'change_manifest.json',manifest)
    base.write_json(DEST/'freeze.json',dict(recipe_sha256=manifest['recipe_file_sha256'],
        inputs=[dict(name=n,bytes=p.stat().st_size,sha256=base.digest(p.read_bytes())) for n,p in files]))
    import standard_cell_qbcap_analyze as observer
    folder = ROOT/'output/managed_execution/runs'/RUN/'collected/derived'
    raw = collected(RUN)
    for name in ['peak.native.bin','peak.columns.json']:
        if (folder/name).read_bytes()!=raw['derived/'+name]:
            raise ValueError('Canonical source native waveform differs from verified receipt')
    cfg = copy.deepcopy(m);cfg['standard_cell_qbcap_experiment']['actual_capacitor_multi']=2
    base.write_json(DEST/'source_storage_reference.json',dict(source_run=RUN,source_recipe_sha256=HASH,
        source_proof=proof,source_actual_capacitor_multi=2,
        storage=observer.storage_observations(str(folder),cfg,source_result['reset_stage_observations']),
        scope='Read-only prior native diagnostic window; no candidate result or new simulation.'))
    print(json.dumps({k:v for k,v in manifest.items() if k not in ['source_proof','old_component','new_component']},indent=2))


if __name__=='__main__':
    main()
