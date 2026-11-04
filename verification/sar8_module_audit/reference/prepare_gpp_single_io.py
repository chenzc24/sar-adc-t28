"""One local GPP driver-implementation contrast; no remote operations."""
from __future__ import annotations
import hashlib,json,re
from pathlib import Path
from build_first_fixture import definitions,instances,ports,emit,flatten
from gpp_single_io_analyze import validate

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OLD=HERE/'generated/real_pre_v1';OUT=HERE/'generated/gpp_single_io_v1';TOP='sar8_realpre_unit'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')


def prepare():
    for case in json.loads((OLD/'package_review.json').read_text())['cases']:
        for item in case['files']:assert sha(ROOT/item['source'])==item['sha256']
    source=(OLD/'dut.scs').read_text();defs=definitions(source);rows=list(instances(defs[TOP]));parts={n:(m,p) for n,_,m,p in rows}
    removed=[n for n,_,_,_ in rows if re.fullmatch('GPP[ABC][NP]',n)];assert len(removed)==6
    new=[row for row in rows if row[0] not in removed]
    for name,template,supply in [('GPPIN','GNNCN','VSS'),('GPPIP','GNNCP','VDD')]:
        model,params=parts[template];new.append((name,['GPPDRV','L0',supply,supply],model,params))
    text=source.replace(defs[TOP],emit(TOP,new,ports(defs[TOP])));binding={p:'VDD!' if p=='VDD' else '0' if p=='VSS' else p for p in ports(defs[TOP])}
    before=flatten(defs,TOP,binding);after=flatten(definitions(text),TOP,binding)
    gone=set(before)-set(after);added=set(after)-set(before);assert gone=={'XDUT.'+n for n in removed} and added=={'XDUT.GPPIN','XDUT.GPPIP'}
    assert all(after[n]==before[n] for n in set(before)&set(after))
    OUT.mkdir(exist_ok=True);dut=OUT/'dut.scs';dut.write_text(text);cases=[]
    for corner in ['ffcold','sscold']:
        folder=OUT/corner;folder.mkdir(exist_ok=True);prior=OLD/corner;tb=(prior/'test.scs').read_text()
        lines=[line for line in tb.splitlines() if not line.startswith('save ')];prefix='\n'.join(lines)+'\n'
        external={}
        for line in lines:
            m=re.match(r'(\w+) \(([^)]*)\) (\w+)(.*)',line)
            if m and m[1]!='XDUT':external[m[1]]=dict(nodes=m[2].split(),model=m[3],parameters=m[4].strip())
        all_flat=dict(after);all_flat.update(external);volts=sorted({n for d in all_flat.values() for n in d['nodes'] if n!='0'})
        currents=sorted(n+':'+str(j) for n,d in all_flat.items() for j,node in enumerate(d['nodes'],1) if n not in external or node!='0' or j==1)
        catalog={}
        for branch in currents:
            n,j=branch.rsplit(':',1);j=int(j);d=all_flat[n];catalog[branch]=dict(instance=n,port=j,node=d['nodes'][j-1],model=d['model'])
        cfg=json.loads((prior/'measurement.json').read_text());cfg.update(variant='real_X025_GPP_single_IO_ideal_L0',
            scope='Only bit0 GPP driver implementation changes core3-stage6MOS to singleIO2MOS; X025/ABC/load/commands unchanged; L0 ideal, no full chain acceptance',
            voltage_saves=volts,current_saves=currents,terminal_current_catalog=catalog)
        cfg['required_kcl_nodes']=[n for n in cfg['required_kcl_nodes'] if n not in ['XDUT.GPPA','XDUT.GPPB']]
        cfg['kcl_terms']={n:[b for b,d in catalog.items() if d['node']==n] for n in cfg['required_kcl_nodes']}
        cfg['selected_mos_pair_screens']=[]
        for n,d in after.items():
            if d['model'] not in ['nch_mac','pch_mac','nch_18_mac','pch_18_mac']:continue
            nodes=dict(zip('dgsb',d['nodes']))
            for a,b in ['ds','gs','gd','gb','bd','bs']:
                cfg['selected_mos_pair_screens'].append(dict(instance=n,model=d['model'],terminal=a+b,nodes=[nodes[a],nodes[b]],screen_v=.99 if d['model'] in ['nch_mac','pch_mac'] else 1.98))
        cfg['diagnostic_voltage_columns']=[n for n in cfg['diagnostic_voltage_columns'] if n not in ['xdut.gppa','xdut.gppb']]
        diag={b.lower() for terms in cfg['kcl_terms'].values() for b in terms}
        diag|={b.lower() for b in currents if re.match(r'XDUT\.(GNN[ABC][NP]|GPPI[NP]|X025\.(MN|MP)):',b) or
            re.match(r'XDUT\.XCDAC\.XS[NP]0\.(MN_LOW|MP_HIGH):',b) or b.startswith(('VVDD:','RREF','VREF','VL0:'))}
        cfg['diagnostic_current_columns']=sorted(diag);cfg['edge_nodes']=list(cfg['diagnostic_voltage_columns'])
        cfg['static_observations']=[n for n in cfg['static_observations'] if n not in ['xdut.gppa','xdut.gppb']]
        for p in cfg['static_windows']:p['expected_logic'].pop('xdut.gppa',None);p['expected_logic'].pop('xdut.gppb',None)
        cfg['stimulus_contract']['GPP_boundary']='One verified ordinaryIO INV from L0 to physical GPPDRV, original Rgate/load; no command or internal-edge compensation'
        cfg['mos_pair_scope']='All79 actual MOS/474 pair screens; core X025 remains0.99V, singleIO GPP1.98V; no historical limit changed'
        cfg['driver_implementation_contrast']=dict(old='Three identical core inverter stages,6MOS',new='One verified IO INV pair,2MOS',
            device_count_and_parasitics_change_together=True,one_transistor_causality_claim=False,ADC_architecture_changed=False)
        baseline='sar8audit-refcell-realpre-'+corner;path=ROOT/'output/managed_execution/runs'/baseline/'collected/derived/result.json'
        result=json.loads(path.read_text());x025=max(max(abs(x['min']),abs(x['max'])) for n,x in result['selected_mos_pair_extrema'].items() if n.startswith('XDUT.X025.'))
        cfg['comparison_baseline']=dict(run=baseline,result_sha256=sha(path),dut_sha256=sha(OLD/'dut.scs'),removed_instances=sorted(gone),added_instances=sorted(added),
            all140_retained_records_identical=True,commands_and_sampling_edges_identical=True,X025_baseline_max_terminal_V=x025,X025_unmodified_core_screen_V=.99)
        (folder/'test.scs').write_text(prefix+'\n'.join('save '+n for n in sorted(set(volts+currents)))+'\n')
        files={'dut.scs':dut,'test.scs':folder/'test.scs','reference_current_analyze.py':HERE/'reference_current_analyze.py',
            'io_cell_analyze.py':HERE/'io_cell_analyze.py','gpp_single_io_analyze.py':HERE/'gpp_single_io_analyze.py','pre_driver_boundary.json':HERE/'pre_driver_boundary.json'}
        cfg['required_input_sha256']={n:sha(p) for n,p in files.items()};validate(cfg);save(folder/'measurement.json',cfg);files['measurement.json']=folder/'measurement.json'
        recipe=json.loads((prior/'recipe_proposal.json').read_text());recipe.update(run_id='sar8audit-gpp-singleio-'+corner,
            design_id='sar8_reference_GPP_single_IO_driver_implementation',analyzer='gpp_single_io_analyze.py',qualification_scope=cfg['scope'],
            inputs=[dict(source=p.relative_to(ROOT).as_posix(),name=n,sha256=sha(p)) for n,p in files.items()])
        recipe['test_conditions']['variant']=cfg['variant'];save(folder/'recipe_proposal.json',recipe)
        cases.append(dict(run_id=recipe['run_id'],recipe=(folder/'recipe_proposal.json').relative_to(ROOT).as_posix(),recipe_sha256=sha(folder/'recipe_proposal.json'),
            staged_bytes=sum(p.stat().st_size for p in files.values()),files=[dict(name=n,source=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for n,p in files.items()],
            signals=dict(voltages=len(volts),mandatory_currents=len(currents),terminal_screens=len(cfg['selected_mos_pair_screens']),KCL=len(cfg['kcl_terms']),
                native_columns=1+len(cfg['diagnostic_voltage_columns'])+len(diag)+len(cfg['kcl_terms']))))
    save(OUT/'package_review.json',dict(status='local_unexecuted_one_GPP_implementation_contrast',registered=False,simulation_started=False,
        baseline_dut_sha256=sha(OLD/'dut.scs'),candidate_dut_sha256=sha(dut),removed_instances=sorted(gone),added_instances=sorted(added),
        all140_retained_records_identical=True,one_driver_implementation_variable_not_one_transistor=True,
        geometry=dict(unit_W_nm=320,L_nm=150,nf=1,N_multi=2,P_multi=4,basis='Exact existing verified GNNCN/GNNCP full IO parameters'),
        X025_core_model_and_0p99V_screen_retained=True,L0_still_ideal_BBM_not_qualified=True,primitive_count=len(after),cases=cases))
    print('SINGLE_IO_GPP_LOCAL_PAIR_READY',len(after),[(c['run_id'],c['staged_bytes'],c['signals']) for c in cases])


if __name__=='__main__':prepare()
