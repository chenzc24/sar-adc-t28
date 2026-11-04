"""Local-only B IO substitution from the completed immutable IO-C fixture."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from build_first_fixture import definitions,instances,ports,emit,flatten
from io_bstage_analyze import validate

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OLD=HERE/'generated/io_cell_v1';OUT=HERE/'generated/io_bstage_v1'
TOP='sar8_refcell_unit'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')


def prepare():
    old_review=json.loads((OLD/'package_review.json').read_text())
    for case in old_review['cases']:
        for item in case['files']:assert sha(ROOT/item['source'])==item['sha256']
    source=(OLD/'io_dut.scs').read_text();defs=definitions(source);rows=list(instances(defs[TOP]));parts={n:(model,params) for n,_,model,params in rows}
    new=[]
    for name,nodes,model,params in rows:
        if name in ['GNNBN','GNNBP']:model,params=parts['GNNC'+name[-1]]
        new.append((name,nodes,model,params))
    text=source.replace(defs[TOP],emit(TOP,new,ports(defs[TOP])));after_defs=definitions(text)
    pins=ports(defs[TOP]);binding={n:n for n in pins};binding.update(VDD='VDD!',VSS='0')
    before=flatten(defs,TOP,binding);after=flatten(after_defs,TOP,binding)
    changed=[n for n in before if before[n]!=after[n]];assert set(changed)=={'XDUT.GNNBN','XDUT.GNNBP'}
    OUT.mkdir(exist_ok=True);dut=OUT/'dut.scs';dut.write_text(text);cases=[]
    for corner in ['ffcold','sscold']:
        folder=OUT/corner;folder.mkdir(exist_ok=True);prior=OLD/('io_'+corner)
        (folder/'test.scs').write_bytes((prior/'test.scs').read_bytes())
        cfg=json.loads((prior/'measurement.json').read_text());cfg['variant']='IO_BC_A_core'
        cfg['scope']='Bit0 NN branch: only B changes from core to native-accepted IO; A remains core, C remains IO; physical original load, not ADC'
        cfg['B_input_charge_windows']=[dict(name='disable_low',start_s=42.98e-9,stop_s=45e-9),
                                      dict(name='enable_low',start_s=47.98e-9,stop_s=51e-9)]
        for pair in cfg['selected_mos_pair_screens']:
            if pair['instance'] in changed:pair['model']=after[pair['instance']]['model'];pair['screen_v']=1.98
        for info in cfg['terminal_current_catalog'].values():
            if info['instance'] in changed:info['model']=after[info['instance']]['model']
        baseline='sar8audit-refcell-io-'+corner+('-q2' if corner=='sscold' else '')
        result=ROOT/'output/managed_execution/runs'/baseline/'collected/derived/result.json'
        cfg['comparison_baseline']=dict(run=baseline,result_sha256=sha(result),dut_sha256=sha(OLD/'io_dut.scs'),
            only_changed_flat_instances=changed,all_commands_and_sampling_edges_identical=True)
        files={'dut.scs':dut,'test.scs':folder/'test.scs','reference_current_analyze.py':HERE/'reference_current_analyze.py',
            'io_cell_analyze.py':HERE/'io_cell_analyze.py','io_bstage_analyze.py':HERE/'io_bstage_analyze.py'}
        cfg['required_input_sha256']={n:sha(p) for n,p in files.items()};validate(cfg)
        save(folder/'measurement.json',cfg);files['measurement.json']=folder/'measurement.json'
        recipe=json.loads((prior/'recipe_proposal.json').read_text())
        recipe.update(run_id='sar8audit-refcell-iob-'+corner,design_id='sar8_reference_loaded_IO_B_stage_feasibility',
            analyzer='io_bstage_analyze.py',qualification_scope=cfg['scope'],
            inputs=[dict(source=p.relative_to(ROOT).as_posix(),name=n,sha256=sha(p)) for n,p in files.items()],
            summary_signals=['PRE','XDUT.GNNA','XDUT.GNNB','XDUT.GNNDRV','XDUT.GNN0','XDUT.XCDAC.BN0'])
        recipe['test_conditions']['variant']=cfg['variant'];save(folder/'recipe_proposal.json',recipe)
        cases.append(dict(run_id=recipe['run_id'],recipe=(folder/'recipe_proposal.json').relative_to(ROOT).as_posix(),
            recipe_sha256=sha(folder/'recipe_proposal.json'),staged_bytes=sum(p.stat().st_size for p in files.values()),
            files=[dict(name=n,source=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for n,p in files.items()],
            baseline=cfg['comparison_baseline'],resources=recipe['resources']))
    save(OUT/'package_review.json',dict(status='local_unexecuted_two_corner_B_only_change',registered=False,simulation_started=False,
        source_IO_C_dut_sha256=sha(OLD/'io_dut.scs'),candidate_dut_sha256=sha(dut),only_changed_flat_instances=changed,
        geometry=dict(unit_W_nm=320,L_nm=150,nf=1,N_multi=2,P_multi=4,basis='Exact complete model/geometry/parasitic parameters of existing native-accepted C IO pair'),
        A_core_limit_V=.99,B_IO_limit_V=1.98,C_IO_limit_V=1.98,primitive_count=len(after),
        MOS_terminal_pairs=450,mandatory_currents=447,KCL_nodes=7,full_native_columns=94,cases=cases))
    print('B_IO_LOCAL_TWO_CASES_READY',sha(dut),[(x['run_id'],x['staged_bytes']) for x in cases])


if __name__=='__main__':prepare()
