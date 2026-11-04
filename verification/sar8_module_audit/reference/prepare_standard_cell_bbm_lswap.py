"""Prepare one L NAND pin permutation; no global gate change or remote work."""
from __future__ import annotations
import copy
import re
from pathlib import Path
from build_first_fixture import definitions,instances,ports,emit,closure
from prepare_standard_cell_bbm import HERE,ROOT,TOP,ND,expanded,sha,read,save,make_config
from standard_cell_bbm_lswap_analyze import VARIANT,validate

OLD=HERE/'standard_cell_bbm_v1'
OUT=HERE/'standard_cell_bbm_lswap_v1'
RUN='sar8audit-ref-bbm-stdcell-lswap-ff-v1'
OLD_RECIPE='f8748125aa8e3528ba6fc2767f6e6d6f20aeb0d467144d085b5a1cda415dba6c'
TARGET='XDUT.XBBM0.X004.X000.XLIB'


def candidate():
    assert sha(OLD/'ffcold/recipe_proposal.json')==OLD_RECIPE
    for f in read(OLD/'ffcold/recipe_proposal.json')['inputs']:assert sha(ROOT/f['source'])==f['sha256']
    metadata=read(OLD/'library_metadata.json')
    d=definitions((OLD/'dut.scs').read_text());before,library=expanded(d,metadata)
    n='sar8audit_nand2_Lswap'
    d[n]=emit(n,[('XLIB',['B','A','Y','VDD','VSS'],ND,'')],ports(d['sar8p_nand2']))
    a='sar8audit_and2_Lswap'
    d[a]=emit(a,[(i,ns,n if i=='X000' else m,p) for i,ns,m,p in instances(d['sar8p_and2'])],ports(d['sar8p_and2']))
    d['sar8p_nonoverlap']=emit('sar8p_nonoverlap',[(i,ns,a if i=='X004' else m,p)
        for i,ns,m,p in instances(d['sar8p_nonoverlap'])],ports(d['sar8p_nonoverlap']))
    after,lib=expanded(d,metadata)
    assert library==lib and set(before)==set(after) and len(after)==194
    changed=sorted(n for n in before if before[n]!=after[n])
    assert changed==sorted(TARGET+'.'+m for m in ['MM1','MM2','MM4','MM9'])
    gate_nodes={'MM4':('CB','LD'),'MM9':('LD','CB'),'MM1':('CB','LD'),'MM2':('LD','CB')}
    for path in changed:
        old,new=before[path],after[path];assert old['model']==new['model'] and old['parameters']==new['parameters']
        assert old['nodes'][::2]==new['nodes'][::2] and old['nodes'][3]==new['nodes'][3]
        x,y=gate_nodes[path.rsplit('.',1)[1]]
        assert old['nodes'][1]=='XDUT.XBBM0.'+x and new['nodes'][1]=='XDUT.XBBM0.'+y
    contrast=dict(target=TARGET,old_A1_A2=['CB','LD'],new_A1_A2=['LD','CB'],
        H_and_all_other_flat_records_exact=True,unchanged_leaf_records=190,
        changed_four_gate_records={n:dict(model=before[n]['model'],old_nodes=before[n]['nodes'],new_nodes=after[n]['nodes']) for n in changed},
        unchanged_D_S_B_and_native_parameters=True,all_instance_paths_unchanged=True,
        global_sar8p_nand2_unchanged=True,library_internal_not_edited=True,
        dedicated_local_masters=[a,n],external_testbench_and_saves_exact=True,
        baseline_dut_sha256=sha(OLD/'dut.scs'),baseline_recipe_proposal_sha256=OLD_RECIPE)
    return d,after,lib,contrast


def prepare():
    d,flat,lib,contrast=candidate();OUT.mkdir(exist_ok=True)
    dut=OUT/'dut.scs';dut.write_text('\n\n'.join(d[n] for n in closure(d,[TOP]))+'\n',encoding='utf-8')
    contrast['candidate_dut_sha256']=sha(dut);save(OUT/'single_variable_delta.json',contrast)
    migration=copy.deepcopy(read(OLD/'migration.json'))
    migration.update(candidate_dut_sha256=sha(dut),native_A1_maps_original_output_adjacent_A=False,
        native_NAND_A2_maps_original_source_adjacent_B=False,
        native_NAND_pin_mapping=dict(L=dict(A1='LD',A2='CB'),H=dict(A1='CODE',A2='HD')),
        single_L_NAND_pin_swap=contrast)
    save(OUT/'migration.json',migration)
    (OUT/'library_metadata.json').write_bytes((OLD/'library_metadata.json').read_bytes())
    prior=OLD/'ffcold';folder=OUT/'ffcold';folder.mkdir(exist_ok=True)
    (folder/'test.scs').write_bytes((prior/'test.scs').read_bytes())
    external={}
    for line in (folder/'test.scs').read_text().splitlines():
        m=re.fullmatch(r'(\w+) \(([^)]*)\) (\w+)(.*)',line)
        if m and m[1]!='XDUT':external[m[1]]=dict(nodes=m[2].split(),model=m[3],parameters=m[4].strip())
    graph=dict(flat);graph.update(external)
    cfg=make_config(read(prior/'measurement.json'),graph,external,lib,migration,'ffcold')
    cfg.update(variant=VARIANT,single_L_NAND_pin_swap=contrast,
        scope='One L native NAND A1/A2 swap, standard-cell bit0 baseline; H/RC/clear/IO/Rgate/real load and exact52ns external stimulus retained; ideal CODE/rails, comparator reset; no ADC qualification',
        comparison_baseline=dict(run='sar8audit-ref-bbm-stdcell-ffcold-v1',
            result_sha256=sha(ROOT/'output/managed_execution/runs/sar8audit-ref-bbm-stdcell-ffcold-v1/collected/derived/result.json'),
            baseline_dut_sha256=sha(OLD/'dut.scs'),only_L_NAND_gate_connections_changed=True,
            full_ADC_candidate=False,internal_edges_not_aligned=True))
    cfg['stimulus_contract']['L_native_pin_swap']='A1=LD,A2=CB; H remains A1=CODE,A2=HD; no timing or library changes'
    files={'dut.scs':dut,'test.scs':folder/'test.scs',
        'reference_current_analyze.py':HERE/'reference_current_analyze.py',
        'io_cell_analyze.py':HERE/'io_cell_analyze.py',
        'standard_cell_bbm_analyze.py':HERE/'standard_cell_bbm_analyze.py',
        'standard_cell_bbm_lswap_analyze.py':HERE/'standard_cell_bbm_lswap_analyze.py',
        'migration.json':OUT/'migration.json','library_metadata.json':OUT/'library_metadata.json',
        'single_variable_delta.json':OUT/'single_variable_delta.json'}
    cfg['required_input_sha256']={n:sha(p) for n,p in files.items()};validate(cfg)
    oldcfg=read(prior/'measurement.json')
    assert cfg['voltage_saves']==oldcfg['voltage_saves'] and cfg['current_saves']==oldcfg['current_saves']
    assert cfg['diagnostic_voltage_columns']==oldcfg['diagnostic_voltage_columns']
    assert cfg['diagnostic_current_columns']==oldcfg['diagnostic_current_columns']
    save(folder/'measurement.json',cfg);files['measurement.json']=folder/'measurement.json'
    recipe=read(prior/'recipe_proposal.json')
    recipe.update(run_id=RUN,design_id='sar8_reference_native_BBM_single_L_NAND_pin_swap',
        analyzer='standard_cell_bbm_lswap_analyze.py',qualification_scope=cfg['scope'],
        inputs=[dict(source=p.relative_to(ROOT).as_posix(),name=n,sha256=sha(p)) for n,p in files.items()])
    recipe['test_conditions']['variant']=VARIANT;save(folder/'recipe_proposal.json',recipe)
    case=dict(run_id=RUN,recipe=(folder/'recipe_proposal.json').relative_to(ROOT).as_posix(),
        recipe_sha256=sha(folder/'recipe_proposal.json'),staged_bytes=sum(p.stat().st_size for p in files.values()),
        files=[dict(name=n,source=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for n,p in files.items()],
        signals=dict(voltages=116,currents=652,terminal_screens=738,KCL=36,native_columns=372))
    save(OUT/'package_review.json',dict(status='local_prepared_single_L_pin_swap_native_not_executed',
        registered=False,simulation_started=False,full_ADC_candidate=False,
        source=OLD.relative_to(ROOT).as_posix(),single_variable_delta=contrast,cases=[case],
        resources=dict(simulation_threads=4,simulation_RSS_MiB=1024,analysis_RSS_MiB=256,
            derived_budget_MiB=30,expected_collection_MiB_max=32)))
    print('REFERENCE_LSWAP_LOCAL_READY',case['run_id'],case['recipe_sha256'],case['staged_bytes'])


if __name__=='__main__':prepare()
