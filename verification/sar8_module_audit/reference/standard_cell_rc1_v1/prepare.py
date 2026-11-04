"""Prepare one HD MP_CLEAR gate series resistor; local ownership only."""
from __future__ import annotations
import copy,re,sys
from pathlib import Path
OWN=Path(__file__).resolve().parent
REF=OWN.parent
sys.path.append(str(REF));sys.path.append(str(REF/'standard_cell_bbm_hlswap_v1'))
from build_first_fixture import definitions,instances,ports,emit
from prepare_standard_cell_bbm import ROOT,TOP,expanded,sha,read,save,make_config
from rc1_analyze import VARIANT,validate

OLD=REF/'standard_cell_bbm_hlswap_v1'
OUT=OWN
RUN='sar8audit-ref-rc1-hd-cleargater-ff-v1'
BASE_RECIPE='739a937ac526501d15922f09de3babc87a4dc9270e9845a5731bfe50d26874e4'
TARGET='XDUT.XBBM0.XD_HD.MP_CLEAR'


def candidate():
    assert sha(OLD/'ffcold/recipe_proposal.json')==BASE_RECIPE
    for q in read(OLD/'ffcold/recipe_proposal.json')['inputs']:assert sha(ROOT/q['source'])==q['sha256']
    metadata=read(OLD/'library_metadata.json');d=definitions((OLD/'dut.scs').read_text())
    before,library=expanded(d,metadata)
    master='sar8p_delay_bbm';clone='sar8audit_delay_bbm_HD_clear_gate_R'
    rows=[];reference=None
    for n,ns,m,p in instances(d[master]):
        if n=='R0':reference=(m,p)
        if n=='MP_CLEAR':
            assert ns==['RC1','A','VDD','VDD'];ns=['RC1','CLEAR_G','VDD','VDD']
        rows.append((n,ns,m,p))
    assert reference and reference[0]=='rupolym'
    rows.append(('R_CLEAR_GATE',['A','CLEAR_G'],reference[0],reference[1]))
    d[clone]=emit(clone,rows,ports(d[master]))
    d['sar8p_nonoverlap']=emit('sar8p_nonoverlap',[(n,ns,clone if n=='XD_HD' else m,p)
        for n,ns,m,p in instances(d['sar8p_nonoverlap'])],ports(d['sar8p_nonoverlap']))
    after,lib=expanded(d,metadata)
    assert library==lib and set(after)-set(before)=={'XDUT.XBBM0.XD_HD.R_CLEAR_GATE'}
    assert set(before)-set(after)==set()
    changed=[n for n in before if before[n]!=after[n]];assert changed==[TARGET]
    assert before[TARGET]['model']==after[TARGET]['model'] and before[TARGET]['parameters']==after[TARGET]['parameters']
    assert [v for j,v in enumerate(before[TARGET]['nodes']) if j!=1]==[v for j,v in enumerate(after[TARGET]['nodes']) if j!=1]
    assert before[TARGET]['nodes'][1]=='CODE' and after[TARGET]['nodes'][1]=='XDUT.XBBM0.XD_HD.CLEAR_G'
    for n,x in before.items():
        if n!=TARGET:assert after[n]==x
    added=after['XDUT.XBBM0.XD_HD.R_CLEAR_GATE'];reference=before['XDUT.XBBM0.XD_HD.R0']
    assert added['model']==reference['model'] and added['parameters']==reference['parameters']
    assert len(after)==195 and sum(x['model'].startswith(('nch_','pch_')) for x in after.values())==123
    delta=dict(target=TARGET,new_resistor='XDUT.XBBM0.XD_HD.R_CLEAR_GATE',
        old_gate_node='CODE',new_gate_node='XDUT.XBBM0.XD_HD.CLEAR_G',
        LD_and_all_other_existing_leaf_records_exact=True,unchanged_existing_leaf_records=193,
        original_primitives=194,candidate_primitives=195,all123_MOS_models_dimensions_DSB_exact=True,
        changed_existing={TARGET:dict(old=before[TARGET],new=after[TARGET])},
        added_passive=dict(instance='XDUT.XBBM0.XD_HD.R_CLEAR_GATE',**added),
        resistor_geometry_source='XDUT.XBBM0.XD_HD.R0',resistor_parameters_identical_to_existing_native_passed_R0=True,
        native_library_and_BBM_boolean_cells_exact=True,cloned_only_HD_delay_master=clone,
        no_supply_or_sampling_clock_change=True,baseline_dut_sha256=sha(OLD/'dut.scs'),
        baseline_recipe_proposal_sha256=BASE_RECIPE,
        rationale='Existing HL native RC1 charge closure identifies MP_CLEAR D as dominant source/sink for both polarities. One existing-R0-geometry gate resistor slows only HD analog clear edge, keeps DC strength; LD untouched control. MeasuredR1~9790.7ohm and eventQg/0.99~1.99fF imply~19.5ps first estimate, not a pass prediction.')
    return d,after,lib,delta


def prepare():
    d,flat,lib,delta=candidate();dut=OUT/'dut.scs'
    dut.write_text('\n\n'.join(d[n] for n in sorted(d))+'\n',encoding='utf-8')
    delta['candidate_dut_sha256']=sha(dut);save(OUT/'single_variable_delta.json',delta)
    migration=copy.deepcopy(read(OLD/'migration.json'))
    migration.update(candidate_dut_sha256=sha(dut),single_HD_clear_gate_R=delta,
        retained_all_RC_components_except_one_HD_gate_isolation=True)
    save(OUT/'migration.json',migration)
    (OUT/'library_metadata.json').write_bytes((OLD/'library_metadata.json').read_bytes())
    prior=OLD/'ffcold';folder=OUT/'ffcold';folder.mkdir(exist_ok=True)
    text=(prior/'test.scs').read_text();external={}
    for line in text.splitlines():
        m=re.fullmatch(r'(\w+) \(([^)]*)\) (\w+)(.*)',line)
        if m and m[1]!='XDUT':external[m[1]]=dict(nodes=m[2].split(),model=m[3],parameters=m[4].strip())
    graph=dict(flat);graph.update(external);old=read(prior/'measurement.json')
    cfg=make_config(old,graph,external,lib,migration,'ffcold')
    cfg.update(variant=VARIANT,single_HD_clear_gate_R=delta,
        scope='One HD analog MP_CLEAR gate resistor from R0 native geometry; frozenHL baseline, LD unchanged; exact external stimulus and native logic; no ADC/RC repair qualification',
        comparison_baseline=dict(run='sar8audit-ref-bbm-stdcell-hlswap-ff-v1',
            result_sha256=sha(ROOT/'output/managed_execution/runs/sar8audit-ref-bbm-stdcell-hlswap-ff-v1/collected/derived/result.json'),
            baseline_dut_sha256=sha(OLD/'dut.scs'),only_HD_analog_clear_gate_series_R_added=True,
            full_ADC_candidate=False,internal_edges_not_aligned=True))
    cfg['boundary_inventory'].update(all_primitives=195,BBM_primitive_count=39,
        voltage_count=len(cfg['voltage_saves']),mandatory_currents=len(cfg['current_saves']),
        KCL_nodes=len(cfg['kcl_terms']))
    cfg['diagnostic_voltage_columns']=sorted(n.lower() for n in cfg['voltage_saves'])
    cfg['edge_nodes']=old['edge_nodes']+['xdut.xbbm0.xd_hd.clear_g']
    cfg['stimulus_contract']['HD_analog_clear_gate_R']='Only HD MP_CLEAR gate isolated by original R0-geometry passive; no ordinary logic or input timing change'
    extra=sorted(set(cfg['voltage_saves']+cfg['current_saves'])-set(old['voltage_saves']+old['current_saves']))
    assert extra==['XDUT.XBBM0.XD_HD.CLEAR_G','XDUT.XBBM0.XD_HD.R_CLEAR_GATE:1','XDUT.XBBM0.XD_HD.R_CLEAR_GATE:2']
    text+=''.join('save '+n+'\n' for n in extra)
    (folder/'test.scs').write_text(text,encoding='utf-8')
    strip=lambda s:'\n'.join(l for l in s.splitlines() if not l.startswith('save '))
    assert strip(text)==strip((prior/'test.scs').read_text())
    files={'dut.scs':dut,'test.scs':folder/'test.scs',
        'reference_current_analyze.py':REF/'reference_current_analyze.py',
        'io_cell_analyze.py':REF/'io_cell_analyze.py',
        'standard_cell_bbm_analyze.py':REF/'standard_cell_bbm_analyze.py',
        'standard_cell_bbm_lswap_analyze.py':REF/'standard_cell_bbm_lswap_analyze.py',
        'standard_cell_bbm_hlswap_analyze.py':OLD/'standard_cell_bbm_hlswap_analyze.py',
        'rc1_event_measure.py':OUT/'rc1_event_measure.py','rc1_analyze.py':OUT/'rc1_analyze.py',
        'migration.json':OUT/'migration.json','library_metadata.json':OUT/'library_metadata.json',
        'single_variable_delta.json':OUT/'single_variable_delta.json'}
    cfg['required_input_sha256']={n:sha(p) for n,p in files.items()};validate(cfg)
    save(folder/'measurement.json',cfg);files['measurement.json']=folder/'measurement.json'
    recipe=read(prior/'recipe_proposal.json')
    recipe.update(run_id=RUN,design_id='sar8_reference_HL_HD_analog_clear_gate_R0_geometry',
        analyzer='rc1_analyze.py',qualification_scope=cfg['scope'],
        inputs=[dict(source=p.relative_to(ROOT).as_posix(),name=n,sha256=sha(p)) for n,p in files.items()])
    recipe['test_conditions']['variant']=VARIANT;save(folder/'recipe_proposal.json',recipe)
    case=dict(run_id=RUN,recipe=(folder/'recipe_proposal.json').relative_to(ROOT).as_posix(),
        recipe_sha256=sha(folder/'recipe_proposal.json'),staged_bytes=sum(p.stat().st_size for p in files.values()),
        files=[dict(name=n,source=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for n,p in files.items()],
        signals=dict(voltages=len(cfg['voltage_saves']),currents=len(cfg['current_saves']),
            terminal_screens=738,KCL=len(cfg['kcl_terms']),
            native_columns=1+len(cfg['diagnostic_voltage_columns'])+len(cfg['diagnostic_current_columns'])+len(cfg['kcl_terms'])))
    save(OUT/'package_review.json',dict(status='local_prepared_HD_clear_gate_R_native_not_executed',
        registered=False,simulation_started=False,full_ADC_candidate=False,
        source=OLD.relative_to(ROOT).as_posix(),single_variable_delta=delta,cases=[case],
        resources=dict(simulation_threads=4,simulation_RSS_MiB=1024,analysis_RSS_MiB=256,
            derived_budget_MiB=30,expected_collection_MiB_max=32)))
    print('RC1_HD_R_LOCAL_READY',case['run_id'],case['recipe_sha256'],case['staged_bytes'],case['signals'])


if __name__=='__main__':prepare()

