"""Restore native X025/GPP shared load; freeze local L0-boundary cases only."""
from __future__ import annotations
import hashlib,json,re
from pathlib import Path
from build_first_fixture import definitions,instances,ports,emit,flatten,closure
from prepare_io_cell import pulse
from real_pre_analyze import validate

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OLD=HERE/'generated/io_astage_v1';OUT=HERE/'generated/real_pre_v1'
TOP='sar8_realpre_unit';OLDTOP='sar8_refcell_unit';ORIGINAL=ROOT/'output/sar8_physical_repair/sar8fix-loaded-ref-ffcold/dut.scs'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')


def prepare():
    for case in json.loads((OLD/'package_review.json').read_text())['cases']:
        for x in case['files']:assert sha(ROOT/x['source'])==x['sha256']
    boundary=HERE/'pre_driver_boundary.json';proof=json.loads(boundary.read_text());assert sha(ORIGINAL)==proof['source_sha256']
    defs=definitions((OLD/'dut.scs').read_text());native=definitions(ORIGINAL.read_text());rows=list(instances(defs[OLDTOP]));oldpins=ports(defs[OLDTOP])
    originalGPP=[(n,['L0' if x=='L' else x for x in nodes],m,p) for n,nodes,m,p in instances(native['sar8p_refdrv_b0']) if re.fullmatch('GPP[ABC][NP]',n)]
    assert len(originalGPP)==6 and 'sar8p_inv' not in defs
    rows+=originalGPP+[('X025',['L0','VDD','VSS','PRE'],'sar8p_inv','')]
    pins=['L0']+[p for p in oldpins if p not in ['PRE','GPPDRV']]
    before=flatten(defs,OLDTOP,{p:('VDD!' if p=='VDD' else '0' if p=='VSS' else p) for p in oldpins})
    defs.pop(OLDTOP);defs['sar8p_inv']=native['sar8p_inv'];defs[TOP]=emit(TOP,rows,pins)
    text='\n\n'.join(defs[n] for n in closure(defs,[TOP]))+'\n'
    binding={p:('VDD!' if p=='VDD' else '0' if p=='VSS' else p) for p in pins};after=flatten(defs,TOP,binding)
    renamed={'PRE':'XDUT.PRE','GPPDRV':'XDUT.GPPDRV'}
    for n,old in before.items():assert after[n]==dict(old,nodes=[renamed.get(p,p) for p in old['nodes']])
    added=sorted(set(after)-set(before));assert len(added)==8
    OUT.mkdir(exist_ok=True);dut=OUT/'dut.scs';dut.write_text(text);cases=[]
    for corner,supply in [('ffcold',.99),('sscold',.81)]:
        folder=OUT/corner;folder.mkdir(exist_ok=True);prior=OLD/corner;oldtb=(prior/'test.scs').read_text();lines=[]
        for line in oldtb.splitlines():
            if line.startswith('save ') or line.startswith('VGPP '):continue
            if line.startswith('XDUT '):line='XDUT ('+' '.join(binding[p] for p in pins)+') '+TOP
            elif line.startswith('VPRE '):line='VL0 (L0 0) vsource type=pwl wave=['+pulse(1,[(43e-9,0),(48e-9,1)],supply)+']'
            lines.append(line)
        prefix='\n'.join(lines)+'\n';assert 'VPRE (' not in prefix and 'VGPP (' not in prefix
        external={}
        for line in lines:
            match=re.match(r'(\w+) \(([^)]*)\) (\w+)(.*)',line)
            if match and match[1]!='XDUT':external[match[1]]=dict(nodes=match[2].split(),model=match[3],parameters=match[4].strip())
        all_flat=dict(after);all_flat.update(external);volt=sorted({node for d in all_flat.values() for node in d['nodes'] if node!='0'})
        currents=sorted(n+':'+str(j) for n,d in all_flat.items() for j,node in enumerate(d['nodes'],1) if n not in external or node!='0' or j==1)
        catalog={}
        for branch in currents:
            n,j=branch.rsplit(':',1);j=int(j);d=all_flat[n];catalog[branch]=dict(instance=n,port=j,node=d['nodes'][j-1],model=d['model'])
        critical=['XDUT.PRE','L0','XDUT.GNNA','XDUT.GNNB','XDUT.GNNDRV','XDUT.GNN0','XDUT.GPPA','XDUT.GPPB','XDUT.GPPDRV','XDUT.GPP0',
                  'XDUT.XCDAC.BN0','XDUT.XCDAC.BP0','XDUT.TOPN','XDUT.TOPP']
        eq={n:[b for b,d in catalog.items() if d['node']==n] for n in critical};screens=[]
        for n,d in after.items():
            if d['model'] not in ['nch_mac','pch_mac','nch_18_mac','pch_18_mac']:continue
            nodes=dict(zip('dgsb',d['nodes']))
            for a,b in ['ds','gs','gd','gb','bd','bs']:screens.append(dict(instance=n,model=d['model'],terminal=a+b,nodes=[nodes[a],nodes[b]],
                screen_v=.99 if d['model'] in ['nch_mac','pch_mac'] else 1.98))
        cfg=json.loads((prior/'measurement.json').read_text());cfg.update(variant='real_X025_GPP_ideal_L0',scope='Original core X025 and GPP shared load restored; ABC IO/physical load retained; L0 ideal, BBM output not qualified',
            voltage_saves=volt,current_saves=currents,terminal_current_catalog=catalog,kcl_terms=eq,selected_mos_pair_screens=screens,
            required_kcl_nodes=critical,pre_node='xdut.pre',source_node='l0',source_current='vl0:1')
        cfg['diagnostic_voltage_columns']=[('xdut.pre' if n=='pre' else 'xdut.gppdrv' if n=='gppdrv' else n) for n in cfg['diagnostic_voltage_columns']]+['l0','xdut.gppa','xdut.gppb']
        diag={b.lower() for terms in eq.values() for b in terms}
        diag|={b.lower() for b in currents if re.match(r'XDUT\.(GNN[ABC][NP]|GPP[ABC][NP]|X025\.(MN|MP)):',b) or
               re.match(r'XDUT\.XCDAC\.XS[NP]0\.(MN_LOW|MP_HIGH):',b) or b.startswith(('VVDD:','RREF','VREF','VL0:'))}
        cfg['diagnostic_current_columns']=sorted(diag);cfg['edge_nodes']=list(cfg['diagnostic_voltage_columns'])
        cfg['initial_witness_v']={'vdd!':supply,'sample':supply,'cmp_clk':0.,'l0':supply}
        cfg['static_observations']=cfg['diagnostic_voltage_columns']+['vvdd:1','vl0:1','rrefn:1','rrefp:1']
        for p in cfg['static_windows']:
            old=p['expected_logic'];old['xdut.pre']=old.pop('pre');high=p['name']=='high'
            old.update(l0=0 if high else 1,**{'xdut.gppa':1 if high else 0,'xdut.gppb':0 if high else 1,
                                         'xdut.gppdrv':1 if high else 0,'xdut.gpp0':1 if high else 0})
        cfg['logical_event_windows']=cfg.pop('PRE_input_charge_windows')
        cfg['stimulus_contract'].pop('PRE_rise_ns',None);cfg['stimulus_contract'].pop('PRE_fall_ns',None)
        cfg['stimulus_contract'].pop('companion_guard_ns',None)
        cfg['stimulus_contract'].update(PRE_boundary='Physical original core X025 output; no ideal forcing or edge alignment',
            L0_fall_ns=43,L0_rise_ns=48,command_guard_ns=1,actual_control_gaps_measured_not_assumed=True,
            L0_boundary='Independent ideal inverted logic,fall43ns/rise48ns,10ps; true BBM output stage omitted',
            GPP_boundary='Original physical core3-stage GPP,shared L0 input,existing Rgate and actual P high-reference load; VGPP removed')
        cfg['mos_pair_scope']='All83 physical MOS including restored core X025/GPP and unchanged physical load; model-specific498 screens'
        cfg['required_input_sha256']={};validate(cfg)
        (folder/'test.scs').write_text(prefix+'\n'.join('save '+n for n in sorted(set(volt+currents)))+'\n')
        baseline='sar8audit-refcell-ioa-'+corner;result=ROOT/'output/managed_execution/runs'/baseline/'collected/derived/result.json'
        cfg['comparison_baseline']=dict(run=baseline,result_sha256=sha(result),dut_sha256=sha(OLD/'dut.scs'),restored_devices=added,
            removed_forcing=['VPRE','VGPP'],renamed_internal_nodes=renamed,external_sampling_source_unchanged=True,physical_PRE_edge_not_aligned=True)
        files={'dut.scs':dut,'test.scs':folder/'test.scs','reference_current_analyze.py':HERE/'reference_current_analyze.py',
               'io_cell_analyze.py':HERE/'io_cell_analyze.py','real_pre_analyze.py':HERE/'real_pre_analyze.py','pre_driver_boundary.json':boundary}
        cfg['required_input_sha256']={n:sha(p) for n,p in files.items()};save(folder/'measurement.json',cfg);files['measurement.json']=folder/'measurement.json'
        recipe=json.loads((prior/'recipe_proposal.json').read_text());recipe.update(run_id='sar8audit-refcell-realpre-'+corner,
            design_id='sar8_reference_real_X025_GPP_ideal_L0',analyzer='real_pre_analyze.py',qualification_scope=cfg['scope'],
            inputs=[dict(source=p.relative_to(ROOT).as_posix(),name=n,sha256=sha(p)) for n,p in files.items()],
            summary_signals=['L0','XDUT.PRE','XDUT.GNN0','XDUT.GPP0','XDUT.XCDAC.BN0','XDUT.XCDAC.BP0'])
        recipe['test_conditions']['variant']=cfg['variant'];save(folder/'recipe_proposal.json',recipe)
        cases.append(dict(run_id=recipe['run_id'],recipe=(folder/'recipe_proposal.json').relative_to(ROOT).as_posix(),recipe_sha256=sha(folder/'recipe_proposal.json'),
            staged_bytes=sum(p.stat().st_size for p in files.values()),files=[dict(name=n,source=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for n,p in files.items()],
            signals=dict(voltages=len(volt),mandatory_currents=len(currents),terminal_screens=len(screens),KCL=len(eq),native_columns=1+len(cfg['diagnostic_voltage_columns'])+len(diag)+len(eq))))
    save(OUT/'package_review.json',dict(status='local_unexecuted_real_PRE_shared_GPP_ideal_L0',registered=False,simulation_started=False,
        source_original_sha256=sha(ORIGINAL),baseline_ABC_sha256=sha(OLD/'dut.scs'),candidate_dut_sha256=sha(dut),restored_flat_devices=added,
        all138_baseline_records_preserved_under_explicit_node_mapping=True,shared_L0_gate_ports=['XDUT.X025.MN:2','XDUT.X025.MP:2','XDUT.GPPAN:2','XDUT.GPPAP:2'],
        removed_ideal_sources=['VPRE','VGPP'],L0_still_ideal_BBM_unqualified=True,primitive_count=len(after),cases=cases))
    print('REAL_PRE_LOCAL_PAIR_READY',len(after),[(c['run_id'],c['staged_bytes'],c['signals']) for c in cases])


if __name__=='__main__':prepare()
