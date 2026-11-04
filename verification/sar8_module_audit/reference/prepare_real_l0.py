"""Restore exactly the original L0 output inverter and its complete fanout."""
import hashlib,json,re
from pathlib import Path
from build_first_fixture import definitions,instances,ports,emit,flatten
from prepare_io_cell import pulse
from real_l0_analyze import validate

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OLD=HERE/'generated/gpp_single_io_v1';OUT=HERE/'generated/real_l0_v1'
TOP='sar8_realpre_unit';ORIGINAL=ROOT/'output/sar8_physical_repair/sar8fix-loaded-ref-ffcold/dut.scs'
SOURCE_SHA='a42e44613b4b1a8a74876a4c996f5bd2bf2e74bf13da6729818ab85bde5a21de'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')


def original_boundary():
    assert sha(ORIGINAL)==SOURCE_SHA
    d=definitions(ORIGINAL.read_text());top='sar_adc8_join_r4'
    f=flatten(d,top,{p:p for p in ports(d[top])});node='XDUT.XREF.L0';inp='XDUT.XREF.XBBM0.X004.N';stem='XDUT.XREF.XBBM0.X004.X001'
    inc=[dict(instance=n,port=j,model=x['model'],nodes=x['nodes'],parameters_sha256=hashlib.sha256(x['parameters'].encode()).hexdigest()) for n,x in f.items() for j,p in enumerate(x['nodes'],1) if p==node]
    drivers={stem+'.MN:1',stem+'.MP:1'}
    fanout={'XDUT.XREF.XDRV0.'+n+':2' for n in ['GPPAN','GPPAP','X025.MN','X025.MP']}
    assert {x['instance']+':'+str(x['port']) for x in inc}==drivers|fanout
    for kind in ['MN','MP']:
        assert f[stem+'.'+kind]['nodes'][1]==inp
    upstream=[dict(instance=n,port=j,model=x['model']) for n,x in f.items() for j,p in enumerate(x['nodes'],1) if p==inp]
    assert {x['instance']+':'+str(x['port']) for x in upstream}=={stem+'.MN:2',stem+'.MP:2'}|{'XDUT.XREF.XBBM0.X004.X000.'+n+':1' for n in ['MP0','MP1','MN0']}
    return dict(source=ORIGINAL.relative_to(ROOT).as_posix(),source_sha256=SOURCE_SHA,
        original_driver=stem,master='sar8p_inv',original_output=node,original_input=inp,
        original_output_incident_ports=inc,original_input_incident_ports=upstream,
        original_output_has_only_four_gate_loads=True,no_omitted_sibling_L0_loads=True,
        local_driver='XDUT.L0SRC',local_output='XDUT.L0',local_input='L0N',
        original_GPPAN_AP_replaced_by_already_frozen_GPPI_pair=True,
        original_X025_MN_MP_retained=True,
        ideal_boundary='L0N represents original NAND output N; NAND X000 and its upstream BBM omitted, not a full BBM test'),d


def prepare():
    for case in json.loads((OLD/'package_review.json').read_text())['cases']:
        for x in case['files']:assert sha(ROOT/x['source'])==x['sha256']
    proof,native=original_boundary();source=(OLD/'dut.scs').read_text();defs=definitions(source);rows=list(instances(defs[TOP]));oldpins=ports(defs[TOP])
    assert defs['sar8p_inv']==native['sar8p_inv']
    rows.append(('L0SRC',['L0N','VDD','VSS','L0'],'sar8p_inv',''));pins=['L0N' if p=='L0' else p for p in oldpins]
    text=source.replace(defs[TOP],emit(TOP,rows,pins));binding=lambda ps:{p:'VDD!' if p=='VDD' else '0' if p=='VSS' else p for p in ps}
    before=flatten(defs,TOP,binding(oldpins));after=flatten(definitions(text),TOP,binding(pins))
    assert set(after)-set(before)=={'XDUT.L0SRC.MN','XDUT.L0SRC.MP'}
    assert all(after[n]==dict(x,nodes=['XDUT.L0' if p=='L0' else p for p in x['nodes']]) for n,x in before.items())
    assert len(after)==144
    OUT.mkdir(exist_ok=True);dut=OUT/'dut.scs';dut.write_text(text);save(OUT/'l0_boundary.json',proof);cases=[]
    for corner,supply in [('ffcold',.99),('sscold',.81)]:
        prior=OLD/corner;folder=OUT/corner;folder.mkdir(exist_ok=True);lines=[]
        for line in (prior/'test.scs').read_text().splitlines():
            if line.startswith('save '):continue
            if line.startswith('XDUT '):line='XDUT ('+' '.join(binding(pins)[p] for p in pins)+') '+TOP
            elif line.startswith('VL0 '):line='VL0N (L0N 0) vsource type=pwl wave=['+pulse(0,[(43e-9,1),(48e-9,0)],supply)+']'
            lines.append(line)
        external={}
        for line in lines:
            m=re.match(r'(\w+) \(([^)]*)\) (\w+)(.*)',line)
            if m and m[1]!='XDUT':external[m[1]]=dict(nodes=m[2].split(),model=m[3],parameters=m[4].strip())
        all_flat=dict(after);all_flat.update(external);volts=sorted({n for d in all_flat.values() for n in d['nodes'] if n!='0'})
        currents=sorted(n+':'+str(j) for n,d in all_flat.items() for j,node in enumerate(d['nodes'],1) if n not in external or node!='0' or j==1)
        catalog={}
        for b in currents:
            n,j=b.rsplit(':',1);j=int(j);d=all_flat[n];catalog[b]=dict(instance=n,port=j,node=d['nodes'][j-1],model=d['model'])
        cfg=json.loads((prior/'measurement.json').read_text());cfg.update(variant='real_L0_X025_GPP_single_IO_ideal_N',
            scope='Restore original L0 output inverter/all L0 fanout on frozen singleIO load; upstream NAND output N ideal, no complete BBM/ADC acceptance',
            voltage_saves=volts,current_saves=currents,terminal_current_catalog=catalog,source_node='l0n',source_current='vl0n:1')
        cfg['required_kcl_nodes']=['XDUT.L0' if n=='L0' else n for n in cfg['required_kcl_nodes']]+['L0N']
        cfg['kcl_terms']={n:[b for b,d in catalog.items() if d['node']==n] for n in cfg['required_kcl_nodes']}
        cfg['selected_mos_pair_screens']=[]
        for n,d in after.items():
            if d['model'] not in ['nch_mac','pch_mac','nch_18_mac','pch_18_mac']:continue
            nodes=dict(zip('dgsb',d['nodes']))
            for a,b in ['ds','gs','gd','gb','bd','bs']:cfg['selected_mos_pair_screens'].append(dict(instance=n,model=d['model'],terminal=a+b,nodes=[nodes[a],nodes[b]],screen_v=.99 if d['model'] in ['nch_mac','pch_mac'] else 1.98))
        cfg['diagnostic_voltage_columns']=['xdut.l0' if n=='l0' else n for n in cfg['diagnostic_voltage_columns']]+['l0n']
        diag={b.lower() for q in cfg['kcl_terms'].values() for b in q}
        diag|={b.lower() for b in currents if re.match(r'XDUT\.(GNN[ABC][NP]|GPPI[NP]|X025\.(MN|MP)|L0SRC\.(MN|MP)):',b) or
            re.match(r'XDUT\.XCDAC\.XS[NP]0\.(MN_LOW|MP_HIGH):',b) or b.startswith(('VVDD:','RREF','VREF','VL0N:'))}
        cfg['diagnostic_current_columns']=sorted(diag);cfg['edge_nodes']=list(cfg['diagnostic_voltage_columns'])
        cfg['initial_witness_v']={'vdd!':supply,'sample':supply,'cmp_clk':0.,'l0n':0.}
        cfg['static_observations']=['xdut.l0' if n=='l0' else 'vl0n:1' if n=='vl0:1' else n for n in cfg['static_observations']]+['l0n']
        for p in cfg['static_windows']:
            bit=p['expected_logic'].pop('l0');p['expected_logic'].update({'xdut.l0':bit,'l0n':1-bit})
        for k in ['L0_fall_ns','L0_rise_ns','L0_boundary']:cfg['stimulus_contract'].pop(k,None)
        cfg['stimulus_contract'].update(L0_boundary='Original physical core inverter XBBM0.X004.X001; internal delay not aligned',
            upstream_N_boundary='Ideal complementary logic at original NAND output N; rise43ns/fall48ns,10ps, no propagation-delay compensation',
            original_L0_fanout_restored_without_sibling_omissions=True)
        cfg['mos_pair_scope']='All81 actual MOS/486 pair screens; new L0SRC and existing X025 core0.99V; prior IO1.98V screens unchanged'
        baseline='sar8audit-gpp-singleio-'+corner;result=ROOT/'output/managed_execution/runs'/baseline/'collected/derived/result.json'
        cfg['comparison_baseline']=dict(run=baseline,result_sha256=sha(result),dut_sha256=sha(OLD/'dut.scs'),
            added_original_driver=proof['original_driver'],all142_existing_records_preserved_under_L0_internal_node_mapping=True,
            all_external_sources_unchanged_except_boundary_relocation=True,internal_L0_edges_not_aligned=True)
        (folder/'test.scs').write_text('\n'.join(lines)+'\n'+'\n'.join('save '+n for n in sorted(set(volts+currents)))+'\n')
        files={'dut.scs':dut,'test.scs':folder/'test.scs','reference_current_analyze.py':HERE/'reference_current_analyze.py',
            'io_cell_analyze.py':HERE/'io_cell_analyze.py','real_l0_analyze.py':HERE/'real_l0_analyze.py','l0_boundary.json':OUT/'l0_boundary.json'}
        cfg['required_input_sha256']={n:sha(p) for n,p in files.items()};validate(cfg);save(folder/'measurement.json',cfg);files['measurement.json']=folder/'measurement.json'
        recipe=json.loads((prior/'recipe_proposal.json').read_text());recipe.update(run_id='sar8audit-real-l0-'+corner,
            design_id='sar8_reference_original_L0_driver_single_IO_GPP',analyzer='real_l0_analyze.py',qualification_scope=cfg['scope'],
            summary_signals=['L0N','XDUT.L0','XDUT.PRE','XDUT.GNN0','XDUT.GPP0','XDUT.XCDAC.BN0','XDUT.XCDAC.BP0'],
            inputs=[dict(source=p.relative_to(ROOT).as_posix(),name=n,sha256=sha(p)) for n,p in files.items()])
        recipe['test_conditions']['variant']=cfg['variant'];save(folder/'recipe_proposal.json',recipe)
        cases.append(dict(run_id=recipe['run_id'],recipe=(folder/'recipe_proposal.json').relative_to(ROOT).as_posix(),recipe_sha256=sha(folder/'recipe_proposal.json'),
            staged_bytes=sum(p.stat().st_size for p in files.values()),files=[dict(name=n,source=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for n,p in files.items()],
            signals=dict(voltages=len(volts),mandatory_currents=len(currents),terminal_screens=len(cfg['selected_mos_pair_screens']),KCL=len(cfg['kcl_terms']),native_columns=1+len(cfg['diagnostic_voltage_columns'])+len(diag)+len(cfg['kcl_terms']))))
    save(OUT/'package_review.json',dict(status='local_unexecuted_restore_L0_driver_only',registered=False,simulation_started=False,
        source_original_sha256=SOURCE_SHA,candidate_dut_sha256=sha(dut),baseline_single_IO_dut_sha256=sha(OLD/'dut.scs'),
        added_instances=['XDUT.L0SRC.MN','XDUT.L0SRC.MP'],primitive_count=144,all142_previous_records_preserved_with_L0_internal_alias=True,
        upstream_N_still_ideal=True,no_sibling_L0_fanout_omitted=True,cases=cases))
    print('REAL_L0_LOCAL_PAIR_READY',[(c['run_id'],c['staged_bytes'],c['signals']) for c in cases])


if __name__=='__main__':prepare()
