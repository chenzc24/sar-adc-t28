"""One native-accepted IO cell, four independent-command real-load cases."""
from __future__ import annotations
import copy,hashlib,json,re
from pathlib import Path
from build_first_fixture import definitions,instances,ports,emit,closure,flatten
from io_cell_analyze import validate

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=HERE/'generated/io_cell_v1'
SOURCE=HERE/'generated/approximate_replay/dut.scs'
SCREEN=ROOT/'output/sar8_physical_repair/sar8fix-ioscreen-sscold/dut.scs'
TOP='sar8_refcell_unit'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')


def build(variant):
    native=definitions(SOURCE.read_text());rows=list(instances(native['sar8p_refdrv_b0']))
    keep={n for n,_,_,_ in rows if n in ['GNNAN','GNNAP','GNNBN','GNNBP','GNNCN','GNNCP']}
    unit=[]
    io={n:re.search(r'(?m)^'+n+r' \([^)]*\) (\w+) (.+)$',SCREEN.read_text()) for n in ['F18IN','F18IP']}
    for n,args,model,params in rows:
        if n in keep:
            args=['PRE' if a=='GNNPRE' else a for a in args]
            if variant=='io' and n in ['GNNCN','GNNCP']:
                match=io['F18IN' if n=='GNNCN' else 'F18IP'];model,params=match[1],match[2]
            unit.append((n,args,model,params))
        elif model=='rupolym':
            unit.append((n,[{'GNN':'GNN0','GNP':'GNP0','GPN':'GPN0','GPP':'GPP0'}.get(a,a) for a in args],model,params))
    assert sum(model=='rupolym' for _,_,model,_ in unit)==40
    for side in ['N','P']:unit.append(('XBOOT'+side,['SAMPLE','TOP'+side,'VIN'+side], 'sar_bootstrap_flat_8b_p',''))
    cdac=[]
    for pin in ports(native['sar8j_r1_cdac']):
        if re.fullmatch(r'G(?:NN|NP|PN|PP)[1-7]',pin):
            cdac.append('VDD' if pin.startswith(('GNN','GNP')) else 'VSS')
        else:cdac.append(pin)
    unit.append(('XCDAC',cdac,'sar8j_r1_cdac',''))
    unit.append(('XCOMP',['CMP_CLK','COMP_N','COMP_P','VDD','TOPN','TOPP','VSS'],'sar_strongarm_t28',''))
    for n,args,model,params in instances(native['sar8_reference_isolation_v1']):
        if n in ['CL_COMP_N','CL_COMP_P','CL_CMP_CLK']:unit.append((n,args,model,params))
    pins=['PRE','SAMPLE','CMP_CLK','GNPDRV','GPNDRV','GPPDRV','VINN','VINP','VREFN','VREFP','VDD','VSS']
    defs=dict(native);defs[TOP]=emit(TOP,unit,pins)
    selected=closure(defs,[TOP]);text='\n\n'.join(defs[n] for n in selected)+'\n'
    binding={n:n for n in pins};binding['VDD']='VDD!';binding['VSS']='0'
    flat=flatten(defs,TOP,binding)
    return text,flat,pins,binding


def pulse(initial,events,supply):
    # Independent logic timestamps; no analog FF trace is loaded or replayed.
    points=[(0.,initial)]
    for t,bit in events:
        points.append((t-5e-12,points[-1][1]));points.append((t+5e-12,bit))
    points.append((52e-9,points[-1][1]))
    return ' '.join('%.17g %.17g'%(t,bit*supply) for t,bit in points)


def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    old_test=(ROOT/'output/sar8_physical_repair/sar8fix-loaded-ref-ffcold/test.scs').read_text().replace('\\\n',' ')
    sampling=re.search(r'(?m)^VSAMPLE .+$',old_test)[0]
    proofs=[]
    for tag in ['ffcold','sscold']:
        folder=ROOT/'output/sar8_physical_repair'/('sar8fix-ioscreen-'+tag)
        manifest=json.loads((ROOT/'verification/sar8_physical_repair'/('sar8fix-ioscreen-'+tag+'_manifest.json')).read_text())
        state=json.loads((ROOT/'verification/sar8_physical_repair'/('sar8fix-ioscreen-'+tag+'_simulation_state.json')).read_text())
        metrics=json.loads((ROOT/'verification/sar8_physical_repair'/('sar8fix-ioscreen-'+tag+'_analysis.json')).read_text())
        assert sha(folder/'dut.scs')==manifest['files']['dut.scs']
        assert state['status']=='complete' and state['exit_code']==0 and state['native']['native_analysis_pass'] and state['native']['zero_error_footer']
        proofs.append(dict(run='sar8fix-ioscreen-'+tag,dut_sha256=manifest['files']['dut.scs'],
            fall_FO4_ps=metrics['blocks']['18']['fo4_fall_delay_ps'],rise_FO4_ps=metrics['blocks']['18']['fo4_rise_delay_ps'],
            qualification='Previously CDF-default/native-accepted primitives; not DRC or this real-load bench'))
    designs={v:build(v) for v in ['core','io']};cases=[]
    before,after=designs['core'][1],designs['io'][1]
    changed=[n for n in before if before[n]!=after.get(n)]
    assert set(changed)=={'XDUT.GNNCN','XDUT.GNNCP'}
    for variant,(text,flat,pins,binding) in designs.items():
        (OUT/(variant+'_dut.scs')).write_text(text)
        for corner,supply in [('ffcold',.99),('sscold',.81)]:
            path=OUT/(variant+'_'+corner);path.mkdir(exist_ok=True)
            run='sar8audit-refcell-'+variant+'-'+corner
            includes=[s for s in old_test.splitlines() if s.startswith('include ') and '/home/process/' in s]
            includes=[s.replace('ffmacro_mos_moscap',('ff' if corner=='ffcold' else 'ss')+'macro_mos_moscap') for s in includes]
            stimuli=['VVDD (VDD! 0) vsource dc='+str(supply),sampling,
                'VPRE (PRE 0) vsource type=pwl wave=['+pulse(0,[(43e-9,1),(48e-9,0)],supply)+']',
                'VGNP (GNPDRV 0) vsource type=pwl wave=['+pulse(1,[(44e-9,0),(47e-9,1)],supply)+']',
                'VGPN (GPNDRV 0) vsource type=pwl wave=['+pulse(0,[(44e-9,1),(47e-9,0)],supply)+']',
                'VGPP (GPPDRV 0) vsource type=pwl wave=['+pulse(0,[(43e-9,1),(48e-9,0)],supply)+']',
                'VCMP (CMP_CLK 0) vsource dc=0']
            for name in ['VVINN','VVINP','VREFLOW','VREFHIGH','RREFN','RREFP','RINN','RINP','CREFN','CREFP']:
                stimuli.append(re.search(r'(?m)^'+name+r' .+$',old_test)[0])
            external={}
            for row in stimuli:
                match=re.match(r'(\w+) \(([^)]*)\) (\w+)(.*)',row)
                external[match[1]]=dict(nodes=match[2].split(),model=match[3],parameters=match[4])
            all_flat=dict(flat);all_flat.update(external)
            volt=sorted({n for row in all_flat.values() for n in row['nodes'] if n!='0'})
            # Keep every MOS D/G/S/B and every load-wrapper terminal. Grounded
            # external-source/passive return probes are unnecessary for these
            # non-ground KCL nodes; preserve the verified positive source port.
            currents=sorted(n+':'+str(j) for n,row in all_flat.items() for j,node in enumerate(row['nodes'],1)
                            if n not in external or node!='0' or j==1)
            catalog={}
            for branch in currents:
                inst,port=branch.rsplit(':',1);port=int(port);row=all_flat[inst]
                catalog[branch]=dict(instance=inst,node=row['nodes'][port-1],port=port,model=row['model'])
            critical=['XDUT.GNNA','XDUT.GNNB','XDUT.GNNDRV','XDUT.GNN0','XDUT.XCDAC.BN0','XDUT.TOPN','XDUT.TOPP']
            eq={n:[b for b,d in catalog.items() if d['node']==n] for n in critical}
            stress=[]
            for n,row in flat.items():
                if row['model'] not in ['nch_mac','pch_mac','nch_18_mac','pch_18_mac']:continue
                pins4=dict(zip('dgsb',row['nodes']))
                for a,b in ['ds','gs','gd','gb','bd','bs']:
                    stress.append(dict(instance=n,model=row['model'],terminal=a+b,nodes=[pins4[a],pins4[b]],
                        screen_v=.99 if row['model'] in ['nch_mac','pch_mac'] else 1.98))
            diag=[n.lower() for n in ['VDD!','PRE','SAMPLE','CMP_CLK','GNPDRV','GPNDRV','GPPDRV','VINN','VINP','VREFP','VREFN',
                'XDUT.GNNA','XDUT.GNNB','XDUT.GNNDRV','XDUT.GNN0','XDUT.GNP0','XDUT.GPN0','XDUT.GPP0',
                'XDUT.TOPN','XDUT.TOPP','XDUT.XCDAC.BN0','XDUT.XCDAC.BP0','XDUT.COMP_N','XDUT.COMP_P']]
            diag_current={b.lower() for terms in eq.values() for b in terms}
            diag_current|={n.lower() for n in currents if re.match(r'XDUT\.GNN[ABC][NP]:',n) or n.startswith(('VVDD:','RREF','VREF','VPRE:'))}
            static=diag+['vvdd:1','rrefn:1','rrefp:1','xdut.gnncn:1','xdut.gnncp:1']
            static+=['xdut.gnn'+stage+'p:'+str(pin) for stage in ['a','b','c'] for pin in [3,4]]
            low={'pre':0,'xdut.gnna':1,'xdut.gnnb':0,'xdut.gnndrv':1,'xdut.gnn0':1}
            high={n:1-bit for n,bit in low.items()}
            cfg=dict(schema_version=1,variant=variant,supply_V=supply,scope='Local three-stage bit0 NN branch, only final cell class differs; not integrated ADC',
                source_run='independent_logic_cell_bench',source_history_stop_s=52e-9,diagnostic_start_s=0.,diagnostic_stop_s=52e-9,
                voltage_saves=volt,current_saves=currents,terminal_current_catalog=catalog,kcl_terms=eq,
                selected_mos_pair_screens=stress,mos_pair_scope='All affected physical MOS in branch, complete CDAC, Bootstrap and reset comparator',
                diagnostic_voltage_columns=diag,diagnostic_current_columns=sorted(diag_current),edge_nodes=diag,
                initial_witness_v={'vdd!':supply,'pre':0.,'sample':supply,'cmp_clk':0.},
                initial_unavailable_from_source='No invented internal t=0 analog witnesses; startup is measured',source_peaks=[],
                current_interpretation='Total native port currents positive into components; multiplicity already included; no intrinsic channel/capacitance split',
                boundary_provenance=dict(approximate=False,independent_logical_commands=True,no_FF_analog_replay=True),
                proposed_contract=dict(status='feasibility_diagnostic_only'),acceptance_pass=None,max_edge_events=10000,max_total_output_bytes=30*1024**2,
                static_observations=static,
                static_windows=[dict(name='low_before',start_s=41.5e-9,stop_s=42.5e-9,expected_logic=low),
                    dict(name='high',start_s=45e-9,stop_s=46e-9,expected_logic=high),
                    dict(name='low_after',start_s=50e-9,stop_s=51.5e-9,expected_logic=low)],
                logic_events=[dict(name='disable_low',start_s=43e-9,stop_s=45e-9,edge_directions={'xdut.gnnb':'rising','xdut.gnndrv':'falling','xdut.gnn0':'falling'}),
                    dict(name='enable_low',start_s=48e-9,stop_s=51e-9,edge_directions={'xdut.gnnb':'falling','xdut.gnndrv':'rising','xdut.gnn0':'rising'})],
                load_windows=[dict(name='high_reference',start_s=44e-9,stop_s=47e-9,select_high=True),
                    dict(name='low_reference',start_s=48e-9,stop_s=52e-9,select_high=False)],
                stimulus_contract=dict(PRE_rise_ns=43,PRE_fall_ns=48,logical_edge_ps=10,corner_normalized_0_VDD=True,
                    PRE_boundary='Independent ideal logic; not claimed actual SS preceding-stage waveform. Physical core A/B resolve their own corner-specific edge.',
                    companion_guard_ns=1,guard_is_unit_fixture_not_new_ADC_timing=True,sampling_source=sampling,
                    comparator='Physical comparator reset-held; no decisions',
                    other_bits='Full physical CDAC/IO reference MOS; seven other bits held by explicit ideal logic boundaries',
                    bootstrap_clock='Original external SAMPLE directly drives physical Bootstrap as load-fixture boundary; no actual internal SS sampler latency claimed'))
            validate(cfg)
            tb='// Independent logic cell characterization; not a SAR conversion.\nsimulator lang=spectre\nglobal 0 VDD!\nparameters SUP='+str(supply)+'\n'
            tb+='\n'.join(includes)+'\ninclude "dut.scs"\nXDUT ('+' '.join(binding[p] for p in pins)+') '+TOP+'\n'
            tb+='\n'.join(stimuli)+'\nsimulatorOptions options temp=-40 tnom=27 method=gear2only reltol=1e-6 vabstol=1e-8 iabstol=1e-13 gmin=1e-12\n'
            tb+='saveOptions options save=selected currents=selected subcktiprobes=no useprobes=no\ntran_cell tran stop=52n maxstep=10p errpreset=conservative\n'
            tb+='\n'.join('save '+n for n in sorted(set(volt+currents)))+'\n';(path/'test.scs').write_text(tb)
            files={'dut.scs':OUT/(variant+'_dut.scs'),'test.scs':path/'test.scs',
                'reference_current_analyze.py':HERE/'reference_current_analyze.py','io_cell_analyze.py':HERE/'io_cell_analyze.py'}
            cfg['required_input_sha256']={n:sha(p) for n,p in files.items()};save(path/'measurement.json',cfg);files['measurement.json']=path/'measurement.json'
            recipe=dict(run_id=run,design_id='sar8_reference_loaded_IO_cell_feasibility',entry='test.scs',analyzer='io_cell_analyze.py',
                inputs=[dict(source=p.relative_to(ROOT).as_posix(),name=n,sha256=sha(p)) for n,p in files.items()],
                summary_signals=['PRE','XDUT.GNNB','XDUT.GNNDRV','XDUT.GNN0','XDUT.XCDAC.BN0'],expected_stop_s=52e-9,
                qualification_scope=cfg['scope'],oa_parity='netlist_only',test_conditions=dict(corner=corner,supply_V=supply,temperature_C=-40,
                    variant=variant,logical_stimulus=True,FF_waveform_replay=False,noise=False,mismatch=False,PEX=False),
                resources=dict(threads=4,simulation_rss_mib=512,simulation_virtual_mib=8192,analysis_rss_mib=256,analysis_virtual_mib=512,
                    max_output_mib=2048,simulation_wall_seconds=900,analysis_wall_seconds=1200,queue_timeout_seconds=600))
            save(path/'recipe_proposal.json',recipe)
            cases.append(dict(run_id=run,recipe=path.relative_to(ROOT).as_posix()+'/recipe_proposal.json',
                recipe_sha256=sha(path/'recipe_proposal.json'),
                staged_bytes=sum(p.stat().st_size for p in files.values()),
                files=[dict(name=n,source=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for n,p in files.items()],
                voltage_count=len(volt),mandatory_current_count=len(currents),MOS_pair_screen_count=len(stress),
                full_native_columns=1+len(diag)+len(diag_current)+len(eq),KCL_nodes=len(eq)))
    save(OUT/'package_review.json',dict(status='local_unexecuted_four_case_package',source_dut_sha256=sha(SOURCE),
        primitive_native_proofs=proofs,IOCDF_sha256=sha(ROOT/'verification/sar8_physical_repair/io_cdf_audit.json'),
        unique_candidate=dict(N_model='nch_18_mac',P_model='pch_18_mac',L_nm=150,unit_W_nm=320,nf=1,N_multi=2,P_multi=4,
            effective_N_W_um=.64,effective_P_W_um=1.28,basis='Exact previous native-accepted ordinaryIO FO4 primitives,2:1 P/N width ratio; not equal-gm replacement'),
        only_changed_flat_instances=changed,all_other_primitive_records_unchanged=True,
        reference_switches_already_IO_unchanged=True,all40_Rgate_segments_unchanged=True,
        physical_CDAC_unchanged=True,three_inverting_stages_preserved=True,
        core_to_IO_interface='Physical original GNNB, not forced; both upstream-core and IO receiver terminal screens retained',
        corners=['FF0.99V/-40C','SS0.81V/-40C'],sampling_source_preserved=sampling,
        cases=cases,registered=False,simulation_started=False))
    print('IO_CELL_FOUR_CASES_READY',len(before),'PRIMITIVES',len(stress),'MOS_PAIR_SCREENS',len(volt),'V',len(currents),'I')


if __name__=='__main__':prepare()
