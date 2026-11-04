"""Whole original bit0 nonoverlap and real H driver; local preparation only."""
import hashlib,json,re
from pathlib import Path
from build_first_fixture import definitions,instances,ports,emit,flatten,closure
from prepare_io_cell import pulse
from real_bbm_analyze import validate

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OLD=HERE/'generated/real_l0_v1';OUT=HERE/'generated/real_bbm_v1';TOP='sar8_realpre_unit'
ORIGINAL=ROOT/'output/sar8_physical_repair/sar8fix-loaded-ref-ffcold/dut.scs'
SHA='a42e44613b4b1a8a74876a4c996f5bd2bf2e74bf13da6729818ab85bde5a21de'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')


def inventory():
    assert sha(ORIGINAL)==SHA
    native=definitions(ORIGINAL.read_text());full=flatten(native,'sar_adc8_join_r4',{p:p for p in ports(native['sar_adc8_join_r4'])})
    bbm={n:x for n,x in full.items() if n.startswith('XDUT.XREF.XBBM0.')}
    assert len(bbm)==40 and sum(x['model'] in ['nch_mac','pch_mac'] for x in bbm.values())==30
    def incident(node):return [dict(instance=n,port=j,model=x['model']) for n,x in full.items() for j,p in enumerate(x['nodes'],1) if p==node]
    fanout={s:incident('XDUT.XREF.'+s+'0') for s in ['H','L','Q']}
    for s,block,loads in [('H','X002',['GNPAN','GNPAP','X008.MN','X008.MP']),('L','X004',['GPPAN','GPPAP','X025.MN','X025.MP'])]:
        expected={'XDUT.XREF.XBBM0.'+block+'.X001.'+n+':1' for n in ['MN','MP']}
        expected|={'XDUT.XREF.XDRV0.'+n+':2' for n in loads}
        assert {x['instance']+':'+str(x['port']) for x in fanout[s]}==expected
    high=[r for r in instances(native['sar8p_refdrv_b0']) if re.fullmatch(r'G(?:NP|PN)[ABC][NP]',r[0]) or r[0]=='X008']
    assert len(high)==13
    proof=dict(source=ORIGINAL.relative_to(ROOT).as_posix(),source_sha256=SHA,original_BBM='XDUT.XREF.XBBM0',master='sar8p_nonoverlap',
        original_H_L_CODE_incident_ports=fanout,original_CODE_is='XDUT.XREF.Q0',CODE_upstream_storage_outside_declared_boundary=True,
        complete_BBM_inventory=[dict(instance=n,model=x['model'],nodes=x['nodes'],parameters_sha256=hashlib.sha256(x['parameters'].encode()).hexdigest()) for n,x in bbm.items()],
        high_driver_root_records=[dict(name=n,nodes=nodes,model=m,parameters_sha256=hashlib.sha256(p.encode()).hexdigest()) for n,nodes,m,p in high],
        original_H_and_L_each_exactly_four_gate_loads=True,no_H_L_sibling_loads_omitted=True,
        baseline_GNN_ABC_IO_and_single_IO_GPP_retained=True,BBM_MOS=30,BBM_MOM=6,BBM_resistors=4,restored_H_driver_MOS=14,
        ideal_boundary='Only CODE input; original storage/source upstream excluded. No ideal H/L or reference gate output.')
    return native,high,proof


def prepare():
    for case in json.loads((OLD/'package_review.json').read_text())['cases']:
        for x in case['files']:assert sha(ROOT/x['source'])==x['sha256']
    native,high,proof=inventory();defs=definitions((OLD/'dut.scs').read_text());oldpins=ports(defs[TOP]);rows=[r for r in instances(defs[TOP]) if r[0]!='L0SRC']
    rows += [(n,['H0' if p=='H' else p for p in nodes],m,params) for n,nodes,m,params in high]
    rows.append(('XBBM0',['CODE','H0','L0','VDD','VSS'],'sar8p_nonoverlap',''))
    pins=['CODE']+[p for p in oldpins if p not in ['L0N','GNPDRV','GPNDRV']]
    for n in closure(native,['sar8p_nonoverlap']):
        if n in defs:assert defs[n]==native[n]
        else:defs[n]=native[n]
    olddefs=definitions((OLD/'dut.scs').read_text());defs[TOP]=emit(TOP,rows,pins);text='\n\n'.join(defs[n] for n in closure(defs,[TOP]))+'\n'
    bind=lambda ps:{p:'VDD!' if p=='VDD' else '0' if p=='VSS' else p for p in ps}
    before=flatten(olddefs,TOP,bind(oldpins));after=flatten(defs,TOP,bind(pins));aliases={'GNPDRV':'XDUT.GNPDRV','GPNDRV':'XDUT.GPNDRV'}
    for n,x in before.items():
        if n.startswith('XDUT.L0SRC.'):continue
        assert after[n]==dict(x,nodes=[aliases.get(p,p) for p in x['nodes']])
    for kind in ['MN','MP']:
        assert after['XDUT.XBBM0.X004.X001.'+kind]==dict(before['XDUT.L0SRC.'+kind],nodes=['XDUT.XBBM0.X004.N' if p=='L0N' else p for p in before['XDUT.L0SRC.'+kind]['nodes']])
    assert len(after)==196 and sum(x['model'] in ['nch_mac','pch_mac','nch_18_mac','pch_18_mac'] for x in after.values())==123
    OUT.mkdir(exist_ok=True);dut=OUT/'dut.scs';dut.write_text(text);save(OUT/'bbm_boundary.json',proof);cases=[]
    control={n:x for n,x in after.items() if n.startswith(('XDUT.XBBM0.','XDUT.X008.')) or re.fullmatch(r'XDUT.G(?:NP|PN)[ABC][NP]',n)}
    for corner,supply in [('ffcold',.99),('sscold',.81)]:
        prior=OLD/corner;folder=OUT/corner;folder.mkdir(exist_ok=True);lines=[]
        for line in (prior/'test.scs').read_text().splitlines():
            if line.startswith(('save ','VGNP ','VGPN ')):continue
            if line.startswith('XDUT '):line='XDUT ('+' '.join(bind(pins)[p] for p in pins)+') '+TOP
            elif line.startswith('VL0N '):line='VCODE (CODE 0) vsource type=pwl wave=['+pulse(0,[(43e-9,1),(48e-9,0)],supply)+']'
            lines.append(line)
        external={}
        for line in lines:
            m=re.match(r'(\w+) \(([^)]*)\) (\w+)(.*)',line)
            if m and m[1]!='XDUT':external[m[1]]=dict(nodes=m[2].split(),model=m[3],parameters=m[4].strip())
        graph=dict(after);graph.update(external);volts=sorted({p for x in graph.values() for p in x['nodes'] if p!='0'})
        currents=sorted(n+':'+str(j) for n,x in graph.items() for j,p in enumerate(x['nodes'],1) if n not in external or p!='0' or j==1)
        cat={}
        for branch in currents:
            n,j=branch.rsplit(':',1);j=int(j);x=graph[n];cat[branch]=dict(instance=n,port=j,node=x['nodes'][j-1],model=x['model'])
        cfg=json.loads((prior/'measurement.json').read_text());critical=set(n for x in control.values() for n in x['nodes'])-{'VDD!','0'}
        critical|={n for n in cfg['required_kcl_nodes'] if n!='L0N'}
        cfg.update(variant='full_original_bit0_BBM_real_H_driver_ideal_CODE',scope='Complete original bit0 CODE-to-H/L BBM and original high driver, tested IO low paths/physical loads; ideal CODE/rails, not wholeADC qualification',
            voltage_saves=volts,current_saves=currents,terminal_current_catalog=cat,required_kcl_nodes=sorted(critical),
            kcl_terms={n:[b for b,x in cat.items() if x['node']==n] for n in sorted(critical)},source_node='code',source_current='vcode:1')
        screens=[]
        for n,x in after.items():
            if x['model'] not in ['nch_mac','pch_mac','nch_18_mac','pch_18_mac']:continue
            nodes=dict(zip('dgsb',x['nodes']))
            for a,b in ['ds','gs','gd','gb','bd','bs']:screens.append(dict(instance=n,model=x['model'],terminal=a+b,nodes=[nodes[a],nodes[b]],screen_v=.99 if x['model'] in ['nch_mac','pch_mac'] else 1.98))
        cfg['selected_mos_pair_screens']=screens
        cfg['diagnostic_voltage_columns']=sorted(set(n.lower() for n in critical)|{('xdut.gnpdrv' if n=='gnpdrv' else 'xdut.gpndrv' if n=='gpndrv' else n) for n in cfg['diagnostic_voltage_columns'] if n!='l0n'})
        diag={b.lower() for q in cfg['kcl_terms'].values() for b in q}
        diag|={b.lower() for b,x in cat.items() if x['instance'] in control or re.match(r'XDUT\.(GNN[ABC][NP]|GPPI[NP]|X025\.(MN|MP)):',b) or
            re.match(r'XDUT\.XCDAC\.XS[NP]0\.(MN_LOW|MP_HIGH):',b) or b.startswith(('VVDD:','RREF','VREF','VCODE:'))}
        cfg['diagnostic_current_columns']=sorted(diag);cfg['edge_nodes']=list(cfg['diagnostic_voltage_columns'])
        cfg['initial_witness_v']={'vdd!':supply,'sample':supply,'cmp_clk':0.,'code':0.}
        cfg['static_observations']=cfg['diagnostic_voltage_columns']+['vvdd:1','vcode:1','rrefn:1','rrefp:1']
        for p in cfg['static_windows']:
            p['expected_logic'].pop('l0n',None);p['expected_logic'].update(code=1 if p['name']=='high' else 0,**{'xdut.h0':1 if p['name']=='high' else 0})
        cfg.pop('correct_on_windows',None)
        cfg['logical_event_windows']=[dict(name='select_high',start_s=42.98e-9,stop_s=47.98e-9),dict(name='select_low',start_s=47.98e-9,stop_s=52e-9)]
        cfg['stimulus_contract']={k:v for k,v in cfg['stimulus_contract'].items() if k not in ['upstream_N_boundary','L0_boundary','command_guard_ns']}
        cfg['stimulus_contract'].update(CODE_rise_ns=43,CODE_fall_ns=48,CODE_edge_ps=10,
            reference_control_boundary='CODE only; original complete BBM and real GNP/GPN chains, no H/L/GNP/GPN ideal forces',
            internal_guard_measured_not_assumed=True,no_internal_edge_alignment=True)
        cfg['mos_pair_scope']='All123 actual MOS/738 six-pair screens; all restored core devices0.99V, retained IO1.98V'
        cfg['boundary_inventory']=dict(BBM_primitive_count=40,BBM_MOS=30,high_driver_MOS=14,all_actual_MOS=123,all_primitives=196,
            KCL_nodes=len(critical),voltage_count=len(volts),mandatory_currents=len(currents),no_H_L_load_omitted=True,
            added_core_MOS=42,existing_L0_source_pair_relocated_not_replaced=True)
        cfg['comparison_baseline']=dict(run='sar8audit-real-l0-'+corner,result_sha256=sha(ROOT/'output/managed_execution/runs'/('sar8audit-real-l0-'+corner)/'collected/derived/result.json'),
            baseline_dut_sha256=sha(OLD/'dut.scs'),all142_retained_records_equal_under_GNP_GPN_internal_mapping=True,
            removed_forcing=['VL0N','VGNP','VGPN'],actual_H_L_guard_not_compensated=True)
        (folder/'test.scs').write_text('\n'.join(lines)+'\n'+'\n'.join('save '+n for n in sorted(set(volts+currents)))+'\n')
        files={'dut.scs':dut,'test.scs':folder/'test.scs','reference_current_analyze.py':HERE/'reference_current_analyze.py','io_cell_analyze.py':HERE/'io_cell_analyze.py',
            'real_bbm_analyze.py':HERE/'real_bbm_analyze.py','bbm_boundary.json':OUT/'bbm_boundary.json'}
        cfg['required_input_sha256']={n:sha(p) for n,p in files.items()};validate(cfg);save(folder/'measurement.json',cfg);files['measurement.json']=folder/'measurement.json'
        recipe=json.loads((prior/'recipe_proposal.json').read_text());recipe.update(run_id='sar8audit-real-bbm-'+corner,design_id='sar8_reference_complete_bit0_BBM_real_driver_load',
            analyzer='real_bbm_analyze.py',qualification_scope=cfg['scope'],summary_signals=['CODE','XDUT.H0','XDUT.L0','XDUT.GNN0','XDUT.GNP0','XDUT.GPN0','XDUT.GPP0','XDUT.XCDAC.BN0','XDUT.XCDAC.BP0'],
            inputs=[dict(source=p.relative_to(ROOT).as_posix(),name=n,sha256=sha(p)) for n,p in files.items()])
        recipe['test_conditions']['variant']=cfg['variant'];save(folder/'recipe_proposal.json',recipe)
        cases.append(dict(run_id=recipe['run_id'],recipe=(folder/'recipe_proposal.json').relative_to(ROOT).as_posix(),recipe_sha256=sha(folder/'recipe_proposal.json'),staged_bytes=sum(p.stat().st_size for p in files.values()),
            files=[dict(name=n,source=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for n,p in files.items()],
            signals=dict(voltages=len(volts),mandatory_currents=len(currents),terminal_screens=len(screens),KCL=len(critical),native_columns=1+len(cfg['diagnostic_voltage_columns'])+len(diag)+len(critical))))
    save(OUT/'package_review.json',dict(status='local_unexecuted_full_original_bit0_BBM_boundary_restore',registered=False,simulation_started=False,
        source_original_sha256=SHA,candidate_dut_sha256=sha(dut),baseline_dut_sha256=sha(OLD/'dut.scs'),primitive_count=196,MOS_count=123,
        BBM_count=40,original_H_driver_MOS=14,retained142_equal_under_mapping=True,relocated_L0_source_pair=True,
        removed_ideal_sources=['VL0N','VGNP','VGPN'],only_CODE_reference_logic_ideal=True,cases=cases))
    print('REAL_BBM_LOCAL_PAIR_READY',[(c['run_id'],c['staged_bytes'],c['signals']) for c in cases])


if __name__=='__main__':prepare()
