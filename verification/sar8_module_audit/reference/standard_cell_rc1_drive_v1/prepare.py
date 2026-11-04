"""One verified HD X005 D1-to-D1P25 native master candidate; local only."""
from __future__ import annotations
import copy,json,re,sys
from pathlib import Path
OWN=Path(__file__).resolve().parent;REF=OWN.parent
sys.path.append(str(REF))
sys.path.append(str(REF/'standard_cell_bbm_hlswap_v1'))
from build_first_fixture import definitions,instances,ports,emit,flatten
from prepare_standard_cell_bbm import ROOT,TOP,binding,sha,read,save,make_config
from drive_analyze import VARIANT,validate
OLD=REF/'standard_cell_rc1_v1'
RUN='sar8audit-ref-rc1-hd-x005-d1p25-ff-v1'
BASE_RECIPE='3805b0f88e1face70a166ecc407746bb6ce41d86c6359eacc5634de5dfc3f32b'
D1='INVD1BWP12T30P140';D1P25='INVD1P25BWP12T30P140'
TARGET='XDUT.XBBM0.XD_HD.X005.XLIB'
HL=REF/'standard_cell_bbm_hlswap_v1'


def expand(d,metadata):
    flat=flatten(d,TOP,binding(d));library={}
    for path,part in list(flat.items()):
        if part['model'] not in metadata['cells']:continue
        cell=metadata['cells'][part['model']];assert len(cell['pins'])==len(part['nodes'])
        bind=dict(zip(cell['pins'],part['nodes']));del flat[path]
        for dev in cell['MOS']:
            n=path+'.'+dev['instance']
            flat[n]=dict(model=dev['master'],nodes=[bind.get(dev[t],path+'.'+dev[t]) for t in ['D','G','S','B']],
                parameters='EXTERNAL_NATIVE_FOUNDRY_PARAMETERS_NOT_COPIED')
            library[n]=dict(cell=part['model'],native_MOS=dev['instance'])
    return flat,library


def verified_metadata():
    probe=read(OWN/'library_probe.json')
    old=read(OLD/'library_metadata.json')
    assert probe['query_read_only'] and not probe['source_geometry_copied'] and probe['selected_cell']==D1P25 and probe['previous_cell']==D1
    assert probe['actual_numeric_INV_candidates'][0]==D1P25
    assert probe['sha256']=='b7b366bff01b86fbe6c9728426a1643255476f5e5e63f79b9ff14ffaa2b2fc0e' and probe['bytes']==2452584
    assert probe['next_to_D1_effective_width_ratio']=={'nch_mac':1.25,'pch_mac':1.25} and probe['same_actual_model_length_classes']
    for k in ['pins','MOS','non_MOS_statements']:assert probe['cells'][D1][k]==old['cells'][D1][k]
    cell=probe['cells'][D1P25]
    assert cell['pins']==['I','ZN','VDD','VSS'] and not cell['non_MOS_statements']
    assert {m['instance'] for m in cell['MOS']}=={'MM3_1','MM3_2','MM2_1','MM2_2'}
    for m in cell['MOS']:
        rail='VSS' if m['master']=='nch_mac' else 'VDD'
        assert m['master'] in ['nch_mac','pch_mac'] and m['D']=='ZN' and m['G']=='I' and m['S']==m['B']==rail
        assert m['dimension_units']==dict(l='n',w='n')
    # Actual connectivity is a parallel two-N/two-P inverter. Explicit DC rows.
    truth=[]
    for bit in [0,1]:
        pull_hi=any(m['master']=='pch_mac' and bit==0 for m in cell['MOS'])
        pull_lo=any(m['master']=='nch_mac' and bit==1 for m in cell['MOS'])
        assert pull_hi!=pull_lo;truth.append(dict(I=bit,ZN=1-bit))
    metadata=copy.deepcopy(old);metadata['cells'][D1P25]=cell
    metadata.update(next_strength_probe_sha256=sha(OWN/'library_probe.json'),
        selected_HD_receiver=D1P25,actual_native_truth=truth,source_geometry_copied=False)
    return metadata,probe


def candidate():
    assert sha(OLD/'ffcold/recipe_proposal.json')==BASE_RECIPE
    for f in read(OLD/'ffcold/recipe_proposal.json')['inputs']:assert sha(ROOT/f['source'])==f['sha256']
    metadata,probe=verified_metadata()
    d=definitions((OLD/'dut.scs').read_text());before,oldlib=expand(d,read(OLD/'library_metadata.json'))
    master='sar8audit_delay_bbm_HD_clear_gate_R';clone='sar8audit_delay_bbm_HD_clear_R_D1P25'
    inv='sar8audit_HD_X005_native_D1P25'
    d[inv]=emit(inv,[('XLIB',['A','Y','VDD','VSS'],D1P25,'')],ports(d['sar8p_inv']))
    d[clone]=emit(clone,[(n,ns,inv if n=='X005' else m,p) for n,ns,m,p in instances(d[master])],ports(d[master]))
    d['sar8p_nonoverlap']=emit('sar8p_nonoverlap',[(n,ns,clone if n=='XD_HD' else m,p)
        for n,ns,m,p in instances(d['sar8p_nonoverlap'])],ports(d['sar8p_nonoverlap']))
    after,lib=expand(d,metadata)
    removed=set(before)-set(after);added=set(after)-set(before)
    assert removed=={TARGET+'.MM1',TARGET+'.MM0'}
    assert added=={TARGET+'.'+m for m in ['MM3_1','MM3_2','MM2_1','MM2_2']}
    retained=set(before)&set(after);assert len(retained)==193 and all(before[n]==after[n] for n in retained)
    assert len(after)==197 and len(lib)==44 and sum(p['model'].startswith(('nch_','pch_')) for p in after.values())==125
    for n in before:
        if '.XD_LD.' in n or n.endswith('.R_CLEAR_GATE'):assert before[n]==after[n]
    delta=dict(target=TARGET,old_cell=D1,new_cell=D1P25,actual_SPI_sha256=probe['sha256'],
        actual_pins=probe['cells'][D1P25]['pins'],actual_width_ratio=probe['next_to_D1_effective_width_ratio'],
        all193_other_leaf_records_exact=True,removed_native_MOS={n:before[n] for n in sorted(removed)},
        added_native_MOS={n:after[n] for n in sorted(added)},native_MOS_before=123,native_MOS_after=125,
        only_one_native_instance_master_changed=True,library_internal_and_geometry_not_edited=True,
        original_HD_clear_gate_R_and_LD_exact=True,all_external_stimulus_rails_sample_timing_loads_exact=True,
        dedicated_local_masters=[inv,clone],baseline_dut_sha256=sha(OLD/'dut.scs'),
        baseline_recipe_proposal_sha256=BASE_RECIPE,library_probe_sha256=sha(OWN/'library_probe.json'))
    return d,after,lib,metadata,delta


def prepare():
    d,flat,lib,metadata,delta=candidate();dut=OWN/'dut.scs'
    dut.write_text('\n\n'.join(d[n] for n in sorted(d))+'\n',encoding='utf-8')
    delta['candidate_dut_sha256']=sha(dut);save(OWN/'single_variable_delta.json',delta)
    migration=copy.deepcopy(read(OLD/'migration.json'))
    migration.update(candidate_dut_sha256=sha(dut),native_library_MOS=lib,single_HD_X005_native_drive=delta)
    save(OWN/'migration.json',migration);save(OWN/'library_metadata.json',metadata)
    prior=OLD/'ffcold';folder=OWN/'ffcold';folder.mkdir(exist_ok=True);text=(prior/'test.scs').read_text()
    external={}
    for line in text.splitlines():
        m=re.fullmatch(r'(\w+) \(([^)]*)\) (\w+)(.*)',line)
        if m and m[1]!='XDUT':external[m[1]]=dict(nodes=m[2].split(),model=m[3],parameters=m[4].strip())
    graph=dict(flat);graph.update(external);old=read(prior/'measurement.json')
    cfg=make_config(old,graph,external,lib,migration,'ffcold')
    cfg.update(variant=VARIANT,single_HD_X005_native_drive=delta,
        scope='Only verified native HD.X005 INVD1P25 master instead ofD1; gateR/LD/other193 leaves and external timing/load retained;125MOS750screens662actualcurrents; no ADC qualification',
        comparison_baseline=dict(run='sar8audit-ref-rc1-hd-cleargater-ff-v1',
            result_sha256=sha(ROOT/'output/managed_execution/runs/sar8audit-ref-rc1-hd-cleargater-ff-v1/collected/derived/result.json'),
            baseline_dut_sha256=sha(OLD/'dut.scs'),only_one_HD_X005_master_changed=True,
            full_ADC_candidate=False,internal_edges_not_aligned=True))
    cfg['boundary_inventory'].update(all_primitives=197,all_actual_MOS=125,BBM_primitive_count=41,BBM_MOS=32,
        native_library_MOS=44,voltage_count=len(cfg['voltage_saves']),mandatory_currents=len(cfg['current_saves']),KCL_nodes=len(cfg['kcl_terms']))
    cfg['mos_pair_scope']='All125 actual MOS750 physical pairs: D1P25 has four verified native MOS; original core0.99V/IO1.98V screens unchanged'
    cfg['diagnostic_voltage_columns']=sorted(n.lower() for n in cfg['voltage_saves']);cfg['edge_nodes']=old['edge_nodes']
    cfg['receiver_gate_current_branches_by_leg']={}
    for leg in ['hd','ld']:
        stem='XDUT.XBBM0.XD_'+leg.upper()+'.X005.XLIB.'
        cfg['receiver_gate_current_branches_by_leg'][leg]=sorted(b.lower() for b,x in cfg['terminal_current_catalog'].items()
            if x['instance'].startswith(stem) and x['port']==2)
    cfg['HD_actual_port_groups']=dict(X005_output_D=sorted(b.lower() for b,x in cfg['terminal_current_catalog'].items()
        if x['instance'].startswith('XDUT.XBBM0.XD_HD.X005.XLIB.') and x['port']==1),
        NAND_input_G=sorted(b.lower() for b,x in cfg['terminal_current_catalog'].items()
        if x['node']=='XDUT.XBBM0.HD' and x['port']==2))
    groups={}
    for p in old['selected_mos_pair_screens']:
        key=p['instance']+':'+p['terminal']
        if p['instance'] in [TARGET+'.MM1',TARGET+'.MM0']:
            groups[key]=[TARGET+'.'+m['instance']+':'+p['terminal'] for m in metadata['cells'][D1P25]['MOS'] if m['master']==p['model']]
        else:groups[key]=[key]
    cfg['baseline_equivalent_terminal_groups']=groups
    cfg['stimulus_contract']['verified_native_HD_drive']='Only HD X005 native INVD1->actual INVD1P25, four MOS; existing clearR and all input timing retained'
    existing=set(old['voltage_saves']+old['current_saves']);wanted=set(cfg['voltage_saves']+cfg['current_saves'])
    lines=[]
    for line in text.splitlines():
        if line.startswith('save ') and line.split()[1] not in wanted:continue
        lines.append(line)
    added_saves=sorted(wanted-existing)
    output='\n'.join(lines)+'\n'+''.join('save '+n+'\n' for n in added_saves)
    strip=lambda s:'\n'.join(l for l in s.splitlines() if not l.startswith('save '))
    assert strip(output)==strip(text) and set(cfg['voltage_saves'])==set(old['voltage_saves'])
    assert len(existing-wanted)==8 and len(added_saves)==16
    (folder/'test.scs').write_text(output,encoding='utf-8')
    files={'dut.scs':dut,'test.scs':folder/'test.scs',
        'reference_current_analyze.py':REF/'reference_current_analyze.py','io_cell_analyze.py':REF/'io_cell_analyze.py',
        'standard_cell_bbm_analyze.py':REF/'standard_cell_bbm_analyze.py',
        'standard_cell_bbm_lswap_analyze.py':REF/'standard_cell_bbm_lswap_analyze.py',
        'standard_cell_bbm_hlswap_analyze.py':HL/'standard_cell_bbm_hlswap_analyze.py',
        'rc1_drive_event_measure.py':OWN/'rc1_drive_event_measure.py','drive_analyze.py':OWN/'drive_analyze.py',
        'migration.json':OWN/'migration.json','library_metadata.json':OWN/'library_metadata.json',
        'library_probe.json':OWN/'library_probe.json','single_variable_delta.json':OWN/'single_variable_delta.json'}
    cfg['required_input_sha256']={n:sha(p) for n,p in files.items()};validate(cfg)
    save(folder/'measurement.json',cfg);files['measurement.json']=folder/'measurement.json'
    recipe=read(prior/'recipe_proposal.json')
    recipe.update(run_id=RUN,design_id='sar8_reference_HD_native_verified_INVD1P25_after_clear_gate_R',
        analyzer='drive_analyze.py',qualification_scope=cfg['scope'],
        inputs=[dict(source=p.relative_to(ROOT).as_posix(),name=n,sha256=sha(p)) for n,p in files.items()])
    recipe['test_conditions']['variant']=VARIANT;save(folder/'recipe_proposal.json',recipe)
    case=dict(run_id=RUN,recipe=(folder/'recipe_proposal.json').relative_to(ROOT).as_posix(),
        recipe_sha256=sha(folder/'recipe_proposal.json'),staged_bytes=sum(p.stat().st_size for p in files.values()),
        files=[dict(name=n,source=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for n,p in files.items()],
        signals=dict(voltages=len(cfg['voltage_saves']),currents=len(cfg['current_saves']),terminal_screens=750,KCL=len(cfg['kcl_terms']),
            native_columns=1+len(cfg['diagnostic_voltage_columns'])+len(cfg['diagnostic_current_columns'])+len(cfg['kcl_terms'])))
    save(OWN/'package_review.json',dict(status='local_prepared_verified_HD_INVD1P25_native_not_executed',registered=False,
        simulation_started=False,full_ADC_candidate=False,single_variable_delta=delta,cases=[case]))
    print('VERIFIED_HD_DRIVE_LOCAL_READY',case['run_id'],case['recipe_sha256'],case['staged_bytes'],case['signals'])


if __name__=='__main__':prepare()

