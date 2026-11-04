"""One HD analog-interface topology experiment; preparation only, no remote access."""
import copy,hashlib,json,re,sys
from pathlib import Path
OWN=Path(__file__).resolve().parent
BASE=OWN.parent
REF=BASE.parent
ROOT=REF.parents[2]
sys.path.append(str(REF))
sys.path.append(str(BASE))
from build_first_fixture import definitions,instances,ports,emit
from prepare_standard_cell_bbm import binding,make_config
from prepare import expand
from interface_analyze import VARIANT,validate
RUN='sar8audit-ref-hd-io-guard-ff-v1'
TOP='sar8_realpre_unit'


def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')


def candidate():
    proposal=BASE/'ffcold/recipe_proposal.json'
    assert sha(proposal)=='5f416251a1f26ec288b2c980dbdd05c965fc56e6a6ca3659a1fdb788d29f5b3a'
    for q in read(proposal)['inputs']:assert sha(ROOT/q['source'])==q['sha256']
    d=definitions((BASE/'dut.scs').read_text());meta=read(BASE/'library_metadata.json')
    before,library=expand(d,meta)
    top={n:(ns,m,p) for n,ns,m,p in instances(d[TOP])}
    np=top['GNNCN'][2];pp=top['GNNCP'][2]
    assert top['GNNCN'][1]=='nch_18_mac' and top['GNNCP'][1]=='pch_18_mac'
    # Existing project IO device records, not copied or edited native-library MOS.
    io='sar8audit_RC_analog_IO_receiver'
    d[io]=emit(io,[('MN_IO',['Y','A','VSS','VSS'],'nch_18_mac',np),
                  ('MP_IO',['Y','A','VDD','VDD'],'pch_18_mac',pp)],['A','VDD','VSS','Y'])
    old='sar8audit_delay_bbm_HD_clear_R_D1P25';new='sar8audit_HD_RC1_IO_guard'
    rows=list(instances(d[old]));r=next(q[3] for q in rows if q[0]=='R1')
    cap=next(q[3] for q in rows if q[0]=='C1')
    assert re.search(r'\bmulti=1\b',cap)
    changed=[]
    for n,ns,m,p in rows:
        if n=='MP_CLEAR':m,p='pch_18_mac',pp
        if n=='X005':ns,m=['RC1','VDD','VSS','HD_RAW'],io
        changed.append((n,ns,m,p))
    changed += [('R_GUARD',['HD_RAW','Y'],'rupolym',r),
                ('R_GUP0',['Y','GUARD_UP'],'rupolym',r),
                ('R_GUP1',['GUARD_UP','VDD'],'rupolym',r),
                ('R_GDN0',['Y','GUARD_DN'],'rupolym',r),
                ('R_GDN1',['GUARD_DN','VSS'],'rupolym',r),
                ('C_GUARD',['Y','VSS'],'cfmom_2t',re.sub(r'\bmulti=1\b','multi=4',cap))]
    d[new]=emit(new,changed,ports(d[old]))
    d['sar8p_nonoverlap']=emit('sar8p_nonoverlap',[(n,ns,new if n=='XD_HD' else m,p)
        for n,ns,m,p in instances(d['sar8p_nonoverlap'])],ports(d['sar8p_nonoverlap']))
    after,library=expand(d,meta)
    removed=set(before)-set(after);added=set(after)-set(before)
    altered={n for n in set(before)&set(after) if before[n]!=after[n]}
    target='XDUT.XBBM0.XD_HD.'
    assert removed=={target+'X005.XLIB.'+m for m in ['MM3_1','MM3_2','MM2_1','MM2_2']}
    assert altered=={target+'MP_CLEAR'}
    assert len(added)==8 and all(n.startswith(target) for n in added)
    assert len(set(before)&set(after)-altered)==192 and len(after)==201 and len(library)==40
    for n in before:
        if not n.startswith(target):assert before[n]==after[n]
    assert all('18_mac' in after[target+'X005.'+m]['model'] for m in ['MN_IO','MP_IO'])
    delta=dict(factor='one_HD_RC1_analog_interface_topology_not_single_transistor',
        baseline_dut_sha256=sha(BASE/'dut.scs'),baseline_proposal_sha256=sha(proposal),
        removed={n:before[n] for n in sorted(removed)},added={n:after[n] for n in sorted(added)},
        changed={n:dict(before=before[n],after=after[n]) for n in altered},
        all192_other_leaf_records_exact=True,all_outside_HD_exact=True,
        no_native_library_internal_edit=True,all_pure_digital_masters_exact=True,
        guard_R_ratio=dict(series=1,upper=2,lower=2),guard_C_existing_C1_ratio=4,
        receiver_n_template='GNNCN',receiver_p_and_clear_template='GNNCP',
        new_logic_input_DC_levels_fraction_VDD=[.25,.75],
        primitive_count=201,actual_MOS=123,native_library_MOS=40,
        local_prepared_only=True,not_a_full_ADC_or_PVT_pass=True)
    return d,after,library,meta,delta


def prepare():
    d,flat,lib,meta,delta=candidate();folder=OWN/'candidate/ffcold';folder.mkdir(parents=True,exist_ok=True)
    out=folder.parent;dut=out/'dut.scs'
    dut.write_text('\n\n'.join(d[n] for n in sorted(d))+'\n',encoding='utf-8')
    delta['candidate_dut_sha256']=sha(dut);save(out/'delta.json',delta)
    save(out/'library_metadata.json',meta)
    migration=dict(baseline_migration_sha256=sha(BASE/'migration.json'),HD_interface_topology=delta,
        candidate_dut_sha256=sha(dut),native_library_MOS=lib,C0_multi=1,
        all_retained_records_exact=True,external_library_only=True,geometry_copied=False,
        retained_record_definition='192 unchanged leaves; changed MP_CLEAR explicitly listed in delta')
    save(out/'migration.json',migration)
    text=(BASE/'ffcold/test.scs').read_text();body='\n'.join(l for l in text.splitlines() if not l.startswith('save '))+'\n'
    external={}
    for line in body.splitlines():
        m=re.fullmatch(r'(\w+) \(([^)]*)\) (\w+)(.*)',line)
        if m and m[1]!='XDUT':external[m[1]]=dict(nodes=m[2].split(),model=m[3],parameters=m[4].strip())
    graph=dict(flat);graph.update(external)
    cfg=make_config(read(BASE/'ffcold/measurement.json'),graph,external,lib,migration,'ffcold')
    for key in ['single_HD_X005_native_drive','baseline_equivalent_terminal_groups',
            'receiver_gate_current_branches_by_leg','HD_actual_port_groups']:
        cfg.pop(key,None)
    cfg.update(variant=VARIANT,interface_delta=delta,
        scope='Single composite HD RC1 analog interface topology: IO clear/receiver plus passive guard, all other leaves/clocks/loads retained; no qualification',
        mos_pair_scope='All123 actual MOS738 pairs, core0.99V/IO1.98V unchanged; no baseline-equivalence merging',
        diagnostic_voltage_columns=sorted(v.lower() for v in cfg['voltage_saves']),
        guard_nominal_levels_stiff_source_only_V=[.99*.25,.99*.75],
        original_full_swing_HD_reset_contract_retained=True,
        interface_nodes=['xdut.xbbm0.xd_hd.rc1','xdut.xbbm0.xd_hd.hd_raw','xdut.xbbm0.hd'],
        interface_passive_resistors=['xdut.xbbm0.xd_hd.'+n.lower() for n in ['R_GUARD','R_GUP0','R_GUP1','R_GDN0','R_GDN1']],
        comparison_baseline=dict(run='sar8audit-ref-rc1-hd-x005-d1p25-ff-v1',
            baseline_dut_sha256=sha(BASE/'dut.scs'),no_time_alignment=True,full_ADC_candidate=False))
    cfg['boundary_inventory'].update(all_actual_MOS=123,all_primitives=201,native_library_MOS=40,
        BBM_primitive_count=45,BBM_MOS=30)
    cfg['edge_nodes']=cfg['diagnostic_voltage_columns']
    cfg['stimulus_contract']['HD_interface']='Only HD RC1 analog interface master; all sources/closing edges identical. HD native input is intentionally quarter/threequarter VDD, not full swing.'
    (folder/'test.scs').write_text(body+''.join('save '+n+'\n' for n in sorted(set(cfg['voltage_saves']+cfg['current_saves']))),encoding='utf-8')
    files={'dut.scs':dut,'test.scs':folder/'test.scs','interface_analyze.py':OWN/'interface_analyze.py',
        'reference_current_analyze.py':REF/'reference_current_analyze.py','io_cell_analyze.py':REF/'io_cell_analyze.py',
        'standard_cell_bbm_analyze.py':REF/'standard_cell_bbm_analyze.py',
        'standard_cell_bbm_lswap_analyze.py':REF/'standard_cell_bbm_lswap_analyze.py',
        'standard_cell_bbm_hlswap_analyze.py':REF/'standard_cell_bbm_hlswap_v1/standard_cell_bbm_hlswap_analyze.py',
        'migration.json':out/'migration.json','library_metadata.json':out/'library_metadata.json','delta.json':out/'delta.json'}
    cfg['required_input_sha256']={n:sha(p) for n,p in files.items()};validate(cfg)
    save(folder/'measurement.json',cfg);files['measurement.json']=folder/'measurement.json'
    recipe=read(BASE/'ffcold/recipe_proposal.json')
    recipe.update(run_id=RUN,design_id='sar8_HD_RC1_IO_receiver_clear_passive_guard_interface',analyzer='interface_analyze.py',
        qualification_scope=cfg['scope'],inputs=[dict(name=n,source=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for n,p in files.items()])
    recipe['test_conditions']['variant']=VARIANT
    save(folder/'recipe_proposal.json',recipe)
    case=dict(run_id=RUN,recipe=(folder/'recipe_proposal.json').relative_to(ROOT).as_posix(),recipe_sha256=sha(folder/'recipe_proposal.json'),
        staged_bytes=sum(p.stat().st_size for p in files.values()),
        files=[dict(name=n,source=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for n,p in files.items()],
        signals=dict(voltages=len(cfg['voltage_saves']),currents=len(cfg['current_saves']),screens=len(cfg['selected_mos_pair_screens']),
            KCL=len(cfg['kcl_terms']),native_columns=1+len(cfg['diagnostic_voltage_columns'])+len(cfg['diagnostic_current_columns'])+len(cfg['kcl_terms'])))
    save(out/'package_review.json',dict(status='local_prepared_not_registered_or_executed',full_ADC_candidate=False,
        factor=delta['factor'],single_transistor_attribution=False,cases=[case]))
    print('HD_INTERFACE_LOCAL_READY',case['recipe_sha256'],case['staged_bytes'],case['signals'])


if __name__=='__main__':prepare()
