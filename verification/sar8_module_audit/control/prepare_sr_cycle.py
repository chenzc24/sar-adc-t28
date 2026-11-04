"""Prepare a paired, independently driven loaded SR cycle; never launch it."""
import copy
import itertools
import json
import re

import prepare_first_event as base
import prepare_standard_cell as standard
import prepare_standard_cell_resetnand as mapping

OWN,ROOT=base.OWN,base.ROOT
OUT=OWN/'sr_cycle_v1'
P='XDUT.XCTRL.XTIM.'
STOP=10e-9
COMMANDS=['RESET_A','RESET_B','SET_A','SET_B']
CASES={'rb_upper':('standard_cell_qbcap_v1','sar8audit_sr_rb_qbcap','sar8audit-ctrl-srcycle-rb-ff-v1'),
       'q_upper':('standard_cell_qborder_v1','sar8audit_sr_qborder','sar8audit-ctrl-srcycle-q-ff-v1')}


def truth_contract(text,sr_name,probe):
    cells=base.cells(text);equations=[]
    for name,item in base.parts(cells[sr_name]).items():
        model=item['model']
        if model=='cfmom_2t':continue
        if model=='INVD1BWP12T30P140':
            inv=probe['cells'][model]
            if len(inv)!=2 or any(x['D']!='ZN' or x['G']!='I' or x['S']!=x['B']
                or x['S']!=('VSS' if x['master'].startswith('nch_') else 'VDD') for x in inv):
                raise ValueError('Native INV connectivity is not the verified inverter')
            binding=dict(zip(standard.CELLS[model],item['nodes']))
            equations.append(dict(instance=name,op='inv',inputs=[binding['I']],output=binding['ZN']))
            continue
        header=cells[model].splitlines()[0].split()[2:];binding=dict(zip(header,item['nodes']))
        parts=base.parts(cells[model]);nmos=[v for v in parts.values() if v['model'].startswith('nch_')]
        pmos=[v for v in parts.values() if v['model'].startswith('pch_')]
        if len(nmos)==1 and len(pmos)==1:
            if nmos[0]['nodes']!=['Y','A','VSS','VSS'] or pmos[0]['nodes']!=['Y','A','VDD','VDD']:
                raise ValueError('Original INV structure differs')
            equations.append(dict(instance=name,op='inv',inputs=[binding['A']],output=binding['Y']))
        elif len(nmos)==2 and len(pmos)==2:
            upper=[v['nodes'] for v in nmos if v['nodes'][0]=='Y' and v['nodes'][2]=='MID']
            lower=[v['nodes'] for v in nmos if v['nodes'][0]=='MID' and v['nodes'][2]=='VSS']
            if (len(upper)!=1 or len(lower)!=1 or {upper[0][1],lower[0][1]}!={'A','B'}
                or any(v['nodes'][0]!='Y' or v['nodes'][2:]!=['VDD','VDD'] for v in pmos)
                or {v['nodes'][1] for v in pmos}!={'A','B'}):raise ValueError('Not the intended static NAND')
            equations.append(dict(instance=name,op='nand',inputs=[binding['A'],binding['B']],output=binding['Y']))
        else:raise ValueError('Unrecognized SR logic structure '+model)
    rows=[]
    for R,S in itertools.product([0,1],repeat=2):
        solutions=[]
        for values in itertools.product([0,1],repeat=4):
            state=dict(zip(['RB','SN','QB','Q'],values));state.update(R=R,S=S)
            if all(state[e['output']]==(1-state[e['inputs'][0]] if e['op']=='inv'
                else 1-int(all(state[n] for n in e['inputs']))) for e in equations):
                solutions.append({k:state[k] for k in ['RB','SN','QB','Q']})
        rows.append(dict(R=R,S=S,stable_solutions=solutions))
    return dict(equations=sorted(equations,key=lambda e:e['output']),truth_rows=rows,
        interpretation='Static solutions derived from actual INV/NAND connections; dynamic overlap/priority remains to be measured.')


def phases(contract):
    states=[(1,0,'reset_hold'),(0,0,'release_hold0'),(0,1,'set'),(0,0,'hold1'),
            (1,0,'reset_from_Qhigh'),(1,1,'overlap_reset_held'),(0,1,'release_R_with_Shigh'),
            (1,1,'assert_R_with_Shigh'),(1,0,'withdraw_S_before_R'),(0,0,'release_hold0_final')]
    result=[];previous=None
    for i,(R,S,name) in enumerate(states):
        row=next(r for r in contract['truth_rows'] if (r['R'],r['S'])==(R,S))
        solutions=row['stable_solutions']
        target=solutions[0] if len(solutions)==1 else next(s for s in solutions if s['Q']==previous)
        oldR,oldS=states[i-1][:2] if i else (R,S)
        changed='RESET_A' if R!=oldR else 'SET_A' if S!=oldS else None
        result.append(dict(index=i,name=name,start_s=i*1e-9,stop_s=(i+1)*1e-9,
            hold_start_s=(i+.4)*1e-9,hold_stop_s=(i+.9)*1e-9,
            commands=dict(RESET_A=R,RESET_B=0,SET_A=S,SET_B=1),R=R,S=S,Q=target['Q'],QB=target['QB'],
            previous_Q=previous,changed_command=changed,
            cause_node='CLOCK_RESET' if changed=='RESET_A' else 'CLOCK_SET' if changed else None,
            cause_direction=(1 if R>oldR else -1) if changed=='RESET_A' else (1 if S>oldS else -1) if changed else None))
        previous=target['Q']
    return result


def common_fixture(text):
    cells=base.cells(text);block=cells['sar8audit_timing']
    for before,after in [
        ('X022 (QUIET QUIET_D VDD VSS CLOCK_SET) sar8p_and2','X022 (CYCLE_SET_A CYCLE_SET_B VDD VSS CLOCK_SET) sar8p_and2'),
        ('X023 (SAMPLE PHI_U VDD VSS CLOCK_RESET) sar8audit_or_resetnand_tcb',
         'X023 (CYCLE_RESET_A CYCLE_RESET_B VDD VSS CLOCK_RESET) sar8audit_or_resetnand_tcb')]:
        if block.count(before)!=1:raise ValueError('Real input driver boundary missing')
        block=block.replace(before,after)
    lines=''.join('    VSR_'+c+' (CYCLE_'+c+' VSS) vsource type=pwl file="pwl/sr_'+c.lower()+'.pwl"\n' for c in COMMANDS)
    block=block.replace('ends sar8audit_timing',lines+'ends sar8audit_timing')
    return text.replace(cells['sar8audit_timing'],block)


def observations(leaves,library,background,phase_list):
    catalog={};mos={};pairs={}
    for path,item in leaves.items():
        ismos=item['model'].startswith(('nch_','pch_'));roles=['D','G','S','B'] if ismos else ['PLUS','MINUS']
        for port,node in enumerate(item['nodes'],1):
            if ismos or node!='0':catalog[path+':'+str(port)]=dict(instance=path,terminal=roles[port-1],port=port,node=node)
        if ismos:
            d,g,s,b=item['nodes'];record=dict(nodes=item['nodes'],model=item['model'],six_pair_labels={})
            for suffix,(a,z) in dict(VGS=(g,s),VGD=(g,d),VDS=(d,s),VGB=(g,b),VDB=(d,b),VSB=(s,b)).items():
                label=path+'_'+suffix;pairs[label]=dict(positive_node=a,negative_node=z,limit_abs_v=.99);record['six_pair_labels'][suffix]=label
            mos[path]=record
    catalog['VVDD:1']=dict(instance='VVDD',terminal='PLUS',port=1,node='VDD!')
    voltages=sorted({n for item in leaves.values() for n in item['nodes'] if n!='0'})
    kcl={n:[p for p,c in catalog.items() if c['node']==n] for n in voltages if n!='VDD!'}
    power={'VDD':dict(voltage_node='VDD!',current='VVDD:1')};energy=dict(supply=['VDD'],commands=[],background=[],passive=[])
    initials={'vdd!':.99}
    for path,item in leaves.items():
        if item['model']=='vsource':
            iscmd=path.startswith(P+'VSR_');label=('CMD_' if iscmd else 'BG_')+path.removeprefix('XDUT.').replace('.','_')
            power[label]=dict(voltage_node=item['nodes'][0],current=path+':1');energy['commands' if iscmd else 'background'].append(label)
            filename=re.search(r'file="([^"]+)"',item['parameters'])[1]
            key=filename.removeprefix('pwl/');value=background[key] if not iscmd else phase_list[0]['commands'][path.removeprefix(P+'VSR_')]*.99
            initials[item['nodes'][0].lower()]=value
        elif item['model'] in ['cfmom_2t','rupolym']:
            for port,node in enumerate(item['nodes'],1):
                if node!='0':
                    label='PASSIVE_'+path.removeprefix('XDUT.').replace('.','_')+'_'+str(port)
                    power[label]=dict(voltage_node=node,current=path+':'+str(port));energy['passive'].append(label)
    prefixes=[P+x for x in ['XCLOCK.','X022.','X023.','X025.']]
    core_paths=[p for p in leaves if any(p.startswith(x) for x in prefixes)]
    nodes={n for p in core_paths for n in leaves[p]['nodes'] if n not in ['0','VDD!']}
    diag={p for p,c in catalog.items() if c['instance'] in core_paths or c['node'] in nodes}
    diag.update(v['current'] for v in power.values())
    gates={node:[p for p,c in catalog.items() if c['node']==node and c['terminal']=='G'] for node in
        [P+'CLOCK_RESET',P+'CLOCK_SET',P+'CLOCK_Q',P+'XCLOCK.RB']+[P+'CYCLE_'+c for c in COMMANDS]}
    wave_currents=[P+'XCLOCK.X003.'+name+':'+str(port) for name in ['MN0','MN1','MP0','MP1'] for port in range(1,5)]
    wave_currents += [P+'XCLOCK.X003.CMID:1',P+'XCLOCK.CQB:1','VVDD:1']+[P+'VSR_'+c+':1' for c in COMMANDS]
    wave_kcl=[P+n for n in ['CLOCK_RESET','CLOCK_SET','CLOCK_Q','XCLOCK.QB','XCLOCK.RB','XCLOCK.X003.MID']]
    return dict(scope='Independent loaded SR cycle, not ADC timing or PVT qualification',
        source_history_stop_s=STOP,diagnostic_start_s=0.,diagnostic_stop_s=STOP,
        voltage_saves=voltages,current_saves=sorted(catalog),terminal_current_catalog=catalog,
        kcl_terms=kcl,critical_kcl_nodes=sorted(kcl),diagnostic_voltage_columns=voltages,
        diagnostic_current_columns=sorted(diag),max_derived_binary_bytes=64*1024**2,
        stress_voltage_pairs=pairs,source_power_ports=power,
        expected_initial_state=dict(time_s=0.,values_v=initials),expected_edges={},
        expected_native_peak=dict(node=P+'CLOCK_Q',value_v=.99,time_s=2e-9,diagnostic_only=True),
        proposed_reproduction_contract=dict(status='independent_cycle_no_source_peak_or_internal_initial_match'),
        acceptance_pass=None,library_mos=library,observed_mos=mos,
        cycle=dict(phases=phase_list,period_s=1e-9,edge_s=20e-12,low_fraction=.1,high_fraction=.9,
            input_gate_ports=gates,energy_groups=energy,core_bias_mos=[p for p in mos if any(p.startswith(x) for x in prefixes)],
            MID_node=P+'XCLOCK.X003.MID',MID_current=P+'XCLOCK.X003.CMID:1',
            output_budget_bytes=30*1024**2,collection_user_limit_bytes=32*1024**2,
            final_analysis_state_reserve_bytes=256*1024,
            final_wave_current_columns=wave_currents,final_wave_KCL_nodes=wave_kcl,
            export_policy='All439 currents and606 full-history/per-phase screens analyzed before projection. Final waveform keeps EVERY native timestamp, ALL66 voltages,23 selected currents and6 core KCL fields. Full raw PSF/all current statistics retained; no interpolation or zero filling.'),
        current_policy='Native total terminal currents, positive into device; no multiplicity scaling/region/channel decomposition.')


def main():
    parent_report=OWN/'standard_cell_qborder_v1/results/comparison.json'
    source_proof=json.loads(parent_report.read_bytes())['cases']
    srcs={};recipes={};meta=None
    for tag,(folder,sr,run) in CASES.items():
        path=OWN/folder;recipe=json.loads((path/'recipe.suggested.yaml').read_bytes());recipes[tag]=recipe
        for item in recipe['inputs']:
            if base.digest((ROOT/item['source']).read_bytes())!=item['sha256']:raise ValueError('Frozen source changed')
        srcs[tag]=(path/'dut.scs').read_text()
        meta=json.loads((ROOT/next(i['source'] for i in recipe['inputs'] if i['name']=='probe_metadata.json')).read_bytes())
    contracts={tag:truth_contract(text,CASES[tag][1],meta) for tag,text in srcs.items()}
    original=truth_contract(srcs['rb_upper'],'sar8p_sr',meta)
    if any(c['truth_rows']!=original['truth_rows'] or c['equations']!=original['equations'] for c in contracts.values()):
        raise ValueError('Actual SR contracts differ')
    phase_list=phases(original);background={}
    for path in sorted((OWN/'standard_cell_qbcap_v1/pwl').glob('*.pwl')):
        first=path.read_text().splitlines()[0].split()
        if float(first[0])!=0:raise ValueError('Context bias lacks zero-time value')
        background[path.name]=float(first[1])
    texts={tag:common_fixture(t) for tag,t in srcs.items()}
    flat={tag:mapping.expand_eighteen(t,meta) for tag,t in texts.items()}
    a,b=[v[0] for v in flat.values()]
    delta=[p for p in a if a[p]!=b[p]]
    if a.keys()!=b.keys() or set(delta)!={P+'XCLOCK.X003.MN0',P+'XCLOCK.X003.MN1'}:
        raise ValueError('Paired benches differ beyond the two NM gates')
    for p in delta:
        x=copy.deepcopy(a[p]);x['nodes'][1]=b[p]['nodes'][1]
        if x!=b[p]:raise ValueError('Paired unit geometry/D/S/B changed')
    base.write_json(OUT/'contract.json',dict(original=original,selected=contracts,phases=phase_list,
        source_blocks_sha256={tag:base.digest(t.encode()) for tag,t in srcs.items()},
        boundary='Only X022/X023 driver inputs independently driven. Background/load shell held at source initial biases; no Q/QB/MID clamp, no ADC sampling contract edit.'))
    base.write_json(OUT/'source_provenance.json',dict(reference=parent_report.relative_to(ROOT).as_posix(),
        sha256=base.digest(parent_report.read_bytes()),proofs={k:v['proof'] for k,v in source_proof.items()}))
    outputs={}
    for tag,(folder,sr,run) in CASES.items():
        dest=OUT/tag;leaves,library=flat[tag];m=observations(leaves,library,background,phase_list)
        base.exact_write(dest/'dut.scs',texts[tag]);base.write_json(dest/'measurement.json',m)
        for name,value in background.items():base.exact_write(dest/'pwl'/name,'0 %.17g\n%.17g %.17g\n'%(value,STOP,value))
        for cmd in COMMANDS:
            initial=phase_list[0]['commands'][cmd]*.99;rows=[(0.,initial)];last=initial
            for ph in phase_list[1:]:
                value=ph['commands'][cmd]*.99
                if value!=last:rows.extend([(ph['start_s']-10e-12,last),(ph['start_s']+10e-12,value)]);last=value
            rows.append((STOP,last))
            base.exact_write(dest/'pwl'/('sr_'+cmd.lower()+'.pwl'),''.join('%.17g %.17g\n'%r for r in rows))
        source=OWN/folder;deck=(source/'test.scs').read_text();deck=''.join(l for l in deck.splitlines(True) if not l.startswith('save '))
        deck,n=re.subn(r'(tran_first tran stop=)\S+',r'\g<1>10n',deck)
        if n!=1:raise ValueError('Transient stop boundary missing')
        base.exact_write(dest/'test.scs',deck+''.join('save '+s+'\n' for s in sorted(m['voltage_saves']+m['current_saves'])))
        base.exact_write(dest/'external_library.json',(source/'external_library.json').read_bytes())
        recipe=copy.deepcopy(recipes[tag]);recipe.update(run_id=run,design_id='SR_cycle_'+tag,analyzer='sr_cycle_analyze.py',expected_stop_s=STOP,
            qualification_scope=m['scope'],summary_signals=[(P+x).lower() for x in ['CLOCK_RESET','CLOCK_SET','CLOCK_Q','XCLOCK.QB','XCLOCK.RB','XCLOCK.X003.MID']])
        recipe['resources'].update(max_output_mib=2048,analysis_wall_seconds=1200)
        files=[(n,dest/n) for n in ['test.scs','dut.scs','measurement.json','external_library.json']]
        files += [(n,OWN/n) for n in ['full_gate_analyze.py','standard_cell_analyze.py','sr_cycle_analyze.py']]
        for n in ['probe_metadata.json','master_metadata.json']:
            files.append((n,ROOT/next(i['source'] for i in recipes[tag]['inputs'] if i['name']==n)))
        files += [('contract.json',OUT/'contract.json')]+[('pwl/'+p.name,p) for p in sorted((dest/'pwl').glob('*.pwl'))]
        recipe['inputs']=[dict(name=n,source=p.relative_to(ROOT).as_posix(),sha256=base.digest(p.read_bytes())) for n,p in files]
        base.write_json(dest/'recipe.suggested.yaml',recipe)
        manifest=dict(run_id=run,variant=tag,source_folder=folder,all_actual_ports_saved=True,
            MOS=len(m['observed_mos']),physical_pairs=len(m['stress_voltage_pairs']),
            voltage_saves=len(m['voltage_saves']),current_saves=len(m['current_saves']),KCL=len(m['critical_kcl_nodes']),
            analysis_wave_currents=len(m['diagnostic_current_columns']),exported_currents=len(m['cycle']['final_wave_current_columns']),
            exported_voltages=len(m['voltage_saves']),exported_KCL=len(m['cycle']['final_wave_KCL_nodes']),
            library_current_ports=len(library)*4,
            declared_inputs=len(files),declared_bytes=sum(p.stat().st_size for _,p in files),
            recipe_file_sha256=base.digest((dest/'recipe.suggested.yaml').read_bytes()),
            remote_operations=False,simulation_completed=False,ADC_sample_contract_changed=False)
        base.write_json(dest/'freeze.json',dict(recipe_sha256=manifest['recipe_file_sha256'],
            inputs=[dict(name=n,bytes=p.stat().st_size,sha256=base.digest(p.read_bytes())) for n,p in files]))
        base.write_json(dest/'manifest.json',manifest);outputs[tag]=manifest
    base.write_json(OUT/'paired_manifest.json',dict(cases=outputs,only_paired_leaf_differences=delta,
        original_and_both_SR_truth_verified=True,independent_commands=True,background_PWL_constants=background,
        shared_input_sources=4,per_case_output_budget_mib=30,user_collection_limit_mib=32,
        analysis_work_binary_limit_mib=64,raw_budget_mib=2048))
    print(json.dumps(outputs,indent=2))


if __name__=='__main__':main()
