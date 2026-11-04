"""Prepare one GNN IO3-to-IO1 SS contrast, no execution/remote operations."""
import hashlib,json,re,sys
from pathlib import Path
OWN=Path(__file__).resolve().parent;REF=OWN.parent;ROOT=REF.parents[2]
sys.path.append(str(REF))
sys.path.append(str(REF/'standard_cell_bbm_hlswap_v1'))
from build_first_fixture import definitions,instances,ports,emit
from prepare_standard_cell_bbm import expanded,make_config
from gnn_analyze import VARIANT,validate
OLD=REF/'standard_cell_bbm_v1';TOP='sar8_realpre_unit';RUN='sar8audit-ref-gnn-io1-sscold-v1'


def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')


def candidate():
    prop=OLD/'sscold/recipe_proposal.json'
    assert sha(prop)=='f36c9d35de24675e06ee1a5a077974aeaa104d4e55c049569a2db2bdfa6cb9d4'
    for q in read(prop)['inputs']:assert sha(ROOT/q['source'])==q['sha256']
    d=definitions((OLD/'dut.scs').read_text());metadata=read(OLD/'library_metadata.json')
    before,oldlib=expanded(d,metadata);rows=list(instances(d[TOP]));names={n:(ns,m,p) for n,ns,m,p in rows}
    for polarity in ['N','P']:
        parts=[names['GNN'+stage+polarity] for stage in ['A','B','C']]
        assert all((x[1],x[2])==(parts[0][1],parts[0][2]) for x in parts)
    gone={'GNNAN','GNNAP','GNNBN','GNNBP'};changed=[]
    for n,ns,m,p in rows:
        if n in gone:continue
        if n in ['GNNCN','GNNCP']:
            assert ns[1]=='GNNB';ns=list(ns);ns[1]='PRE'
        changed.append((n,ns,m,p))
    d[TOP]=emit(TOP,changed,ports(d[TOP]));after,lib=expanded(d,metadata)
    removed=set(before)-set(after);added=set(after)-set(before)
    different={n for n in set(before)&set(after) if before[n]!=after[n]}
    assert removed=={'XDUT.'+n for n in gone} and not added and different=={'XDUT.GNNCN','XDUT.GNNCP'}
    assert len(after)==190 and len(lib)==42 and oldlib==lib
    assert len(set(before)&set(after)-different)==188 and all(before[n]==after[n] for n in set(before)&set(after)-different)
    for n in different:
        assert before[n]['model']==after[n]['model'] and before[n]['parameters']==after[n]['parameters']
        assert [before[n]['nodes'][j] for j in [0,2,3]]==[after[n]['nodes'][j] for j in [0,2,3]]
    rgate={n:x for n,x in before.items() if n.startswith('XDUT.RGNN')}
    assert len(rgate)==10 and all(after[n]==x for n,x in rgate.items())
    delta=dict(factor='only_GNN_3_identical_IO_inverters_to_existing_final_IO1',
        baseline_dut_sha256=sha(OLD/'dut.scs'),baseline_proposal_sha256=sha(prop),
        removed={n:before[n] for n in sorted(removed)},changed={n:dict(before=before[n],after=after[n]) for n in sorted(different)},added=[],
        all188_other_leaf_records_exact=True,all_native_standard_cells_exact=True,final_model_parameters_and_output_load_exact=True,
        Rgate_and_all_other_paths_exact=True,Rgate_leaves_unchanged=list(sorted(rgate)),
        all_A_B_C_nominal_gate_pair_parameters_identical=True,PRE_load_gate_charge_not_assumed_identical=True,
        inversion_stages_before=3,inversion_stages_after=1,parity_same=True,
        intrinsic_drive_dimensions_not_swept=True,actual_MOS=119,actual_primitives=190,native_library_MOS=42,
        new_C_gate_source='real native X025 PRE, not an ideal source',no_library_internal_edit=True)
    return d,after,lib,metadata,delta


def prepare():
    d,flat,lib,metadata,delta=candidate();out=OWN/'candidate';folder=out/'sscold';folder.mkdir(parents=True,exist_ok=True)
    dut=out/'dut.scs';dut.write_text('\n\n'.join(d[n] for n in sorted(d))+'\n',encoding='utf-8');delta['candidate_dut_sha256']=sha(dut)
    save(out/'delta.json',delta);save(out/'library_metadata.json',metadata)
    migration=dict(baseline_migration_sha256=sha(OLD/'migration.json'),single_GNN_stage_count_delta=delta,
        candidate_dut_sha256=sha(dut),native_library_MOS=lib,C0_multi=1,all_retained_records_exact=True,
        retained_record_definition='188 exact leaves; final IO gate rewiring explicitly listed in delta',external_library_only=True,geometry_copied=False)
    save(out/'migration.json',migration)
    oldtest=(OLD/'sscold/test.scs').read_text();body='\n'.join(l for l in oldtest.splitlines() if not l.startswith('save '))+'\n';external={}
    for line in body.splitlines():
        m=re.fullmatch(r'(\w+) \(([^)]*)\) (\w+)(.*)',line)
        if m and m[1]!='XDUT':external[m[1]]=dict(nodes=m[2].split(),model=m[3],parameters=m[4].strip())
    graph=dict(flat);graph.update(external);cfg=make_config(read(OLD/'sscold/measurement.json'),graph,external,lib,migration,'sscold')
    for key in ['B_input_charge_windows','logic_events','driver_implementation_contrast']:cfg.pop(key,None)
    for p in cfg['static_windows']:
        for n in ['xdut.gnna','xdut.gnnb']:p['expected_logic'].pop(n,None)
    cfg.update(variant=VARIANT,single_GNN_stage_count_delta=delta,
        scope='Only GNN3 identical IO stages -> unchanged final IO directly on real PRE; native X025/otherpaths/Rgate/PWL/complete load exact; SS cold diagnostic not full ADC/PVT pass',
        diagnostic_voltage_columns=sorted(n.lower() for n in cfg['voltage_saves']),
        mos_pair_scope='All119 actual MOS714 six-pair screens; core0.99V/IO1.98V, full0..52ns; no deleted-node aliases or limits changed',
        gnn_path_nodes=['xdut.l0','xdut.pre','xdut.gnndrv','xdut.gnn0'],
        comparison_baseline=dict(run='sar8audit-ref-bbm-stdcell-sscold-v1',result_sha256='c61c9a71f01e9485c455ec26e0424cfbd2847fae9e10d2d1618cdebb9be8615e',
            baseline_dut_sha256=sha(OLD/'dut.scs'),exterior_and_PWL_exact=True,no_time_alignment=True,full_ADC_candidate=False))
    cfg['boundary_inventory'].update(all_actual_MOS=119,all_primitives=190,native_library_MOS=42,BBM_primitive_count=38,BBM_MOS=30)
    cfg['edge_nodes']=cfg['diagnostic_voltage_columns']
    cfg['source_energy_groups']['XDUT.GNNCP']='GNN_single_IO'
    cfg['stimulus_contract']['GNN_boundary']='GNNCN/CP existing final model/params/load retained, GNNB gates replaced by real PRE, A/B deleted; inversion parity unchanged; no ideal internal force'
    (folder/'test.scs').write_text(body+''.join('save '+n+'\n' for n in sorted(set(cfg['voltage_saves']+cfg['current_saves']))),encoding='utf-8')
    files={'dut.scs':dut,'test.scs':folder/'test.scs','gnn_analyze.py':OWN/'gnn_analyze.py','gnn_measure.py':OWN/'gnn_measure.py',
        'reference_current_analyze.py':REF/'reference_current_analyze.py','io_cell_analyze.py':REF/'io_cell_analyze.py',
        'standard_cell_bbm_analyze.py':REF/'standard_cell_bbm_analyze.py','standard_cell_bbm_lswap_analyze.py':REF/'standard_cell_bbm_lswap_analyze.py',
        'standard_cell_bbm_hlswap_analyze.py':REF/'standard_cell_bbm_hlswap_v1/standard_cell_bbm_hlswap_analyze.py',
        'migration.json':out/'migration.json','library_metadata.json':out/'library_metadata.json','delta.json':out/'delta.json'}
    cfg['required_input_sha256']={n:sha(p) for n,p in files.items()};validate(cfg);save(folder/'measurement.json',cfg);files['measurement.json']=folder/'measurement.json'
    recipe=read(OLD/'sscold/recipe_proposal.json');recipe.update(run_id=RUN,design_id='sar8_reference_GNN_existing_final_IO_direct_PRE',
        analyzer='gnn_analyze.py',qualification_scope=cfg['scope'],inputs=[dict(name=n,source=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for n,p in files.items()])
    recipe['test_conditions']['variant']=VARIANT;save(folder/'recipe_proposal.json',recipe)
    case=dict(run_id=RUN,recipe=(folder/'recipe_proposal.json').relative_to(ROOT).as_posix(),recipe_sha256=sha(folder/'recipe_proposal.json'),
        staged_bytes=sum(p.stat().st_size for p in files.values()),files=[dict(name=n,source=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for n,p in files.items()],
        signals=dict(voltages=len(cfg['voltage_saves']),currents=len(cfg['current_saves']),terminal_screens=714,KCL=len(cfg['kcl_terms']),
            native_columns=1+len(cfg['diagnostic_voltage_columns'])+len(cfg['diagnostic_current_columns'])+len(cfg['kcl_terms'])))
    save(out/'package_review.json',dict(status='local_prepared_one_SS_case_not_registered_or_executed',cases=[case],
        factor=delta['factor'],native_library_unchanged=True,FF_case_prepared=False,full_ADC_candidate=False,
        resource_notes=dict(simulation_threads=4,simulation_RSS_MiB=1024,analysis_RSS_MiB=256,derived_budget_MiB=30,collection_max_MiB=32)))
    print('GNN_IO1_SS_LOCAL_READY',case['recipe_sha256'],case['staged_bytes'],case['signals'])


if __name__=='__main__':prepare()
