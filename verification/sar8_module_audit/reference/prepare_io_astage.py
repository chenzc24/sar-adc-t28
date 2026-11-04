"""Local A-only IO pair and read-only original PRE-driver provenance."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from build_first_fixture import definitions,instances,ports,emit,flatten
from io_astage_analyze import validate

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OLD=HERE/'generated/io_bstage_v1';OUT=HERE/'generated/io_astage_v1';TOP='sar8_refcell_unit'
ORIGINAL=ROOT/'output/sar8_physical_repair/sar8fix-loaded-ref-ffcold/dut.scs'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')


def pre_boundary():
    assert sha(ORIGINAL)=='a42e44613b4b1a8a74876a4c996f5bd2bf2e74bf13da6729818ab85bde5a21de'
    defs=definitions(ORIGINAL.read_text());top='sar_adc8_join_r4';f=flatten(defs,top,{n:n for n in ports(defs[top])})
    pre='XDUT.XREF.XDRV0.GNNPRE';upstream='XDUT.XREF.L0'
    def incident(node):
        return [dict(instance=n,port=j,terminal='dgsb'[j-1],model=r['model'],nodes=r['nodes'],
            parameters_sha256=hashlib.sha256(r['parameters'].encode()).hexdigest())
            for n,r in sorted(f.items()) for j,v in enumerate(r['nodes'],1) if v==node]
    pre_ports=incident(pre);l_ports=incident(upstream)
    drivers=[dict(instance=n,**f[n]) for n in ['XDUT.XREF.XDRV0.X025.MN','XDUT.XREF.XDRV0.X025.MP']]
    assert {x['instance']+':'+str(x['port']) for x in pre_ports}=={
        'XDUT.XREF.XDRV0.X025.MN:1','XDUT.XREF.XDRV0.X025.MP:1','XDUT.XREF.XDRV0.GNNAN:2','XDUT.XREF.XDRV0.GNNAP:2'}
    assert len(l_ports)==6
    path=HERE/'pre_driver_boundary.json'
    save(path,dict(status='read_only_exact_frozen_local_export_not_current_OA_readback',source=ORIGINAL.relative_to(ROOT).as_posix(),source_sha256=sha(ORIGINAL),
        source_top=top,flat_primitive_count=len(f),unit_PRE_alias=pre,original_driver_master='sar8p_inv',
        original_driver_instance='XDUT.XREF.XDRV0.X025',original_driver_formal_ports=['A','VDD','VSS','Y'],
        original_driver_parent_connections=[upstream,'VDD!','0',pre],physical_driver_devices=drivers,
        PRE_node_incident_ports=pre_ports,PRE_original_gate_load_instances=['XDUT.XREF.XDRV0.GNNAN','XDUT.XREF.XDRV0.GNNAP'],
        PRE_original_gate_load_devices=[dict(instance=n,**f[n]) for n in ['XDUT.XREF.XDRV0.GNNAN','XDUT.XREF.XDRV0.GNNAP']],
        upstream_node=upstream,upstream_incident_ports=l_ports,
        upstream_output_driver='XDUT.XREF.XBBM0.X004.X001',
        upstream_shared_gate_loads=['XDUT.XREF.XDRV0.GPPAN:2','XDUT.XREF.XDRV0.GPPAP:2',
                                  'XDUT.XREF.XDRV0.X025.MN:2','XDUT.XREF.XDRV0.X025.MP:2'],
        logic_relation='PRE=NOT(L0); future preserved command phase would require L0 high initially, falling43ns/rising48ns, subject to real BBM dynamics.',
        future_fixture_constraints='Retain real X025 drain/body/gate terminals and upstream L0 shared GPP loading/BBM output path; current experiment does not instantiate X025.',
        current_boundary='Ideal VPRE drives IO-A gates directly; neither original core X025 stress nor true upstream input loading is qualified.'))
    return path


def prepare():
    old_review=json.loads((OLD/'package_review.json').read_text())
    for case in old_review['cases']:
        for x in case['files']:assert sha(ROOT/x['source'])==x['sha256']
    boundary=pre_boundary();source=(OLD/'dut.scs').read_text();defs=definitions(source);rows=list(instances(defs[TOP]));parts={n:(m,p) for n,_,m,p in rows};new=[]
    for n,nodes,model,params in rows:
        if n in ['GNNAN','GNNAP']:model,params=parts['GNNC'+n[-1]]
        new.append((n,nodes,model,params))
    text=source.replace(defs[TOP],emit(TOP,new,ports(defs[TOP])));pins=ports(defs[TOP]);binding={n:n for n in pins};binding.update(VDD='VDD!',VSS='0')
    a=flatten(defs,TOP,binding);b=flatten(definitions(text),TOP,binding);changed=[n for n in a if a[n]!=b[n]]
    assert set(changed)=={'XDUT.GNNAN','XDUT.GNNAP'}
    OUT.mkdir(exist_ok=True);dut=OUT/'dut.scs';dut.write_text(text);cases=[]
    for corner in ['ffcold','sscold']:
        folder=OUT/corner;folder.mkdir(exist_ok=True);prior=OLD/corner;(folder/'test.scs').write_bytes((prior/'test.scs').read_bytes())
        cfg=json.loads((prior/'measurement.json').read_text());cfg['variant']='IO_ABC_ideal_PRE';cfg['scope']='Bit0 NN: only A becomes IO; B/C and original physical loads retained; ideal PRE, no full-chain acceptance'
        cfg['PRE_input_charge_windows']=list(cfg['B_input_charge_windows'])
        cfg['correct_on_windows']=[dict(name='high_before_turnoff',start_s=44.005e-9,stop_s=46.995e-9,stop_exclusive=True,select_high=True),
                                   dict(name='low_after_turnon',start_s=48.005e-9,stop_s=52e-9,stop_exclusive=False,select_high=False)]
        for p in cfg['selected_mos_pair_screens']:
            if p['instance'] in changed:p['model']=b[p['instance']]['model'];p['screen_v']=1.98
        for info in cfg['terminal_current_catalog'].values():
            if info['instance'] in changed:info['model']=b[info['instance']]['model']
        baseline='sar8audit-refcell-iob-'+corner;result=ROOT/'output/managed_execution/runs'/baseline/'collected/derived/result.json'
        cfg['comparison_baseline']=dict(run=baseline,result_sha256=sha(result),dut_sha256=sha(OLD/'dut.scs'),only_changed_flat_instances=changed,
            original_PRE_driver_boundary_sha256=sha(boundary),ideal_PRE_preserved=True,all_commands_and_sampling_edges_identical=True)
        files={'dut.scs':dut,'test.scs':folder/'test.scs','reference_current_analyze.py':HERE/'reference_current_analyze.py',
               'io_cell_analyze.py':HERE/'io_cell_analyze.py','io_bstage_analyze.py':HERE/'io_bstage_analyze.py',
               'io_astage_analyze.py':HERE/'io_astage_analyze.py','pre_driver_boundary.json':boundary}
        cfg['required_input_sha256']={n:sha(p) for n,p in files.items()};validate(cfg);save(folder/'measurement.json',cfg);files['measurement.json']=folder/'measurement.json'
        recipe=json.loads((prior/'recipe_proposal.json').read_text());recipe.update(run_id='sar8audit-refcell-ioa-'+corner,
            design_id='sar8_reference_loaded_IO_A_stage_ideal_PRE_feasibility',analyzer='io_astage_analyze.py',qualification_scope=cfg['scope'],
            inputs=[dict(source=p.relative_to(ROOT).as_posix(),name=n,sha256=sha(p)) for n,p in files.items()])
        recipe['test_conditions']['variant']=cfg['variant'];save(folder/'recipe_proposal.json',recipe)
        cases.append(dict(run_id=recipe['run_id'],recipe=(folder/'recipe_proposal.json').relative_to(ROOT).as_posix(),recipe_sha256=sha(folder/'recipe_proposal.json'),
            staged_bytes=sum(p.stat().st_size for p in files.values()),files=[dict(name=n,source=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for n,p in files.items()],
            baseline=cfg['comparison_baseline'],resources=recipe['resources']))
    save(OUT/'package_review.json',dict(status='local_unexecuted_A_only_IO_pair_ideal_PRE',registered=False,simulation_started=False,
        original_IO_BC_dut_sha256=sha(OLD/'dut.scs'),candidate_dut_sha256=sha(dut),only_changed_flat_instances=changed,
        geometry=dict(unit_W_nm=320,L_nm=150,nf=1,N_multi=2,P_multi=4,basis='Exact existing verified C IO model/geometry/parasitic parameters'),
        A_B_C_IO_screen_V=1.98,other_model_screens_unchanged=True,primitive_count=len(b),MOS_terminal_pairs=450,mandatory_currents=447,KCL_nodes=7,full_native_columns=94,
        source_work_not_added_to_VDD=True,negative_excursions_and_signed_body_polarity_reported=True,original_PRE_driver_boundary_sha256=sha(boundary),cases=cases))
    print('A_ONLY_IO_LOCAL_PAIR_READY',sha(dut),[(c['run_id'],c['staged_bytes']) for c in cases])


if __name__=='__main__':prepare()
