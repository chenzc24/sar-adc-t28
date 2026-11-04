"""One FF condition of the frozen SS IO1 circuit; never rewrites SS inputs."""
import copy,difflib,hashlib,json,sys
from pathlib import Path
OWN=Path(__file__).resolve().parent;GNN=OWN.parent;REF=GNN.parent;ROOT=REF.parents[2]
sys.path.append(str(REF));sys.path.append(str(REF/'standard_cell_bbm_hlswap_v1'));sys.path.append(str(GNN))
from gnn_analyze import validate
SS=GNN/'candidate/sscold';FF=GNN/'candidate/ffcold';OLD=REF/'standard_cell_bbm_v1'
RUN='sar8audit-ref-gnn-io1-ffcold-v1'


def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
def body(p):return '\n'.join(l for l in p.read_text().splitlines() if not l.startswith('save '))+'\n'


def prepare():
    assert sha(SS/'recipe_proposal.json')=='7f75ed0953931628d7fdb2c0d72d34c5f510c8c551114e8abae0c583eef4fa88'
    ss_recipe=read(SS/'recipe_proposal.json')
    for f in ss_recipe['inputs']:assert sha(ROOT/f['source'])==f['sha256']
    assert sha(OLD/'ffcold/recipe_proposal.json')=='f8748125aa8e3528ba6fc2767f6e6d6f20aeb0d467144d085b5a1cda415dba6c'
    for f in read(OLD/'ffcold/recipe_proposal.json')['inputs']:assert sha(ROOT/f['source'])==f['sha256']
    actual_ss=ROOT/'output/managed_execution/runs/sar8audit-ref-gnn-io1-sscold-v1/collected/derived/result.json'
    r=read(actual_ss);assert r['analysis_complete'] and r['native_points']==10464 and r['native_PSF_END']
    ss_body=body(SS/'test.scs');ff_body=body(OLD/'ffcold/test.scs')
    expected=ss_body.replace('parameters SUP=0.81\n','parameters SUP=0.99\n')
    expected=expected.replace('section=ssmacro_mos_moscap','section=ffmacro_mos_moscap')
    expected=expected.replace('VVDD (VDD! 0) vsource dc=0.81\n','VVDD (VDD! 0) vsource dc=0.99\n')
    expected=expected.replace('0.81000000000000005','0.98999999999999999')
    assert expected==ff_body
    changes=[dict(before=a,after=b) for a,b in zip(ss_body.splitlines(),ff_body.splitlines()) if a!=b]
    assert len(changes)==4 and len(ss_body.splitlines())==len(ff_body.splitlines())
    FF.mkdir(exist_ok=True)
    cfg=copy.deepcopy(read(SS/'measurement.json'));original=copy.deepcopy(cfg)
    oldff=read(OLD/'ffcold/measurement.json');cfg['supply_V']=oldff['supply_V'];cfg['initial_witness_v']=oldff['initial_witness_v']
    assert cfg['supply_V']==.99
    cfg['scope']=cfg['scope'].replace('SS cold diagnostic','FF cold diagnostic')
    cfg['comparison_baseline']=dict(run='sar8audit-ref-bbm-stdcell-ffcold-v1',
        result_sha256='24265b647dd9fae4105886acb45c6eb6e1b6b966bb75f943dc77a85f1edbb7d9',
        baseline_dut_sha256=sha(OLD/'dut.scs'),exterior_and_PWL_exact=True,no_time_alignment=True,full_ADC_candidate=False)
    cfg['same_candidate_completed_SS']=dict(run='sar8audit-ref-gnn-io1-sscold-v1',native_points=10464,
        result_sha256=sha(actual_ss),proposal_sha256=sha(SS/'recipe_proposal.json'),DUT_sha256=sha(GNN/'candidate/dut.scs'))
    cfg['PVT_only_from_SS']=dict(MOS_section='ffmacro_mos_moscap',supply_V=.99,temperature_C=-40,
        actual_reference_high_V=.9,actual_reference_low_V=0.,DUT_identical=True,analyzers_and_measurement_method_identical=True,
        stimulus_edges_identical=True,external_body_changes=changes)
    (FF/'test.scs').write_text(ff_body+''.join('save '+n+'\n' for n in sorted(set(cfg['voltage_saves']+cfg['current_saves']))),encoding='utf-8')
    assert set(l for l in (FF/'test.scs').read_text().splitlines() if l.startswith('save '))==set(l for l in (SS/'test.scs').read_text().splitlines() if l.startswith('save '))
    files={f['name']:ROOT/f['source'] for f in ss_recipe['inputs']}
    files['test.scs']=FF/'test.scs';files['measurement.json']=FF/'measurement.json'
    cfg['required_input_sha256']={n:sha(p) for n,p in files.items() if n!='measurement.json'}
    allowed={'supply_V','initial_witness_v','scope','comparison_baseline','same_candidate_completed_SS','PVT_only_from_SS','required_input_sha256'}
    assert {k:v for k,v in original.items() if k not in allowed}=={k:v for k,v in cfg.items() if k not in allowed}
    validate(cfg);save(FF/'measurement.json',cfg)
    recipe=copy.deepcopy(ss_recipe);recipe.update(run_id=RUN,design_id='sar8_reference_GNN_existing_final_IO_direct_PRE_FF',qualification_scope=cfg['scope'],
        inputs=[dict(name=n,source=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for n,p in files.items()])
    recipe['test_conditions'].update(corner='ffcold',supply_V=.99,temperature_C=-40)
    save(FF/'recipe_proposal.json',recipe)
    delta=dict(same_DUT_source=str(files['dut.scs'].relative_to(ROOT)),same_DUT_sha256=sha(files['dut.scs']),
        same_analyzers={n:sha(files[n]) for n in ['gnn_analyze.py','gnn_measure.py','reference_current_analyze.py','io_cell_analyze.py','standard_cell_bbm_analyze.py','standard_cell_bbm_lswap_analyze.py','standard_cell_bbm_hlswap_analyze.py']},
        SS_proposal_sha256=sha(SS/'recipe_proposal.json'),old_FF_body_sha256=hashlib.sha256(ff_body.encode()).hexdigest(),
        SS_to_FF_body_changes=changes,measurement_metadata_changed_keys=sorted(k for k in set(original)|set(cfg) if original.get(k)!=cfg.get(k)),
        all_actual_saves_currents_screens_KCL_and_measurement_methods_identical=True,temperature_unchanged_C=-40,
        references_inputs_sampling_close_edges_Rgate_and_loads_unchanged=True,no_second_topology=True)
    save(FF/'PVT_delta.json',delta)
    case=dict(run_id=RUN,recipe=(FF/'recipe_proposal.json').relative_to(ROOT).as_posix(),recipe_sha256=sha(FF/'recipe_proposal.json'),
        staged_bytes=sum(p.stat().st_size for p in files.values()),files=[dict(name=n,source=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for n,p in files.items()],
        signals=dict(voltages=len(cfg['voltage_saves']),currents=len(cfg['current_saves']),terminal_screens=len(cfg['selected_mos_pair_screens']),KCL=len(cfg['kcl_terms']),
            native_columns=1+len(cfg['diagnostic_voltage_columns'])+len(cfg['diagnostic_current_columns'])+len(cfg['kcl_terms'])))
    save(FF/'package_review.json',dict(status='prepared_FF_condition_of_frozen_IO1_DUT_not_registered_or_executed',cases=[case],
        PVT_delta=delta,full_ADC_candidate=False,original_SS_inputs_unchanged=True,existing_runtime_test_reused=True))
    for f in ss_recipe['inputs']:assert sha(ROOT/f['source'])==f['sha256']
    print('SAME_DUT_FF_LOCAL_READY',case['recipe_sha256'],case['staged_bytes'],case['signals'])


if __name__=='__main__':prepare()
