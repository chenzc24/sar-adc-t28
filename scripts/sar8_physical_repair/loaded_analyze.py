"""Real-load review: exact native events/energy/stress; compact-wave estimates."""
import argparse,hashlib,json,re
import numpy as np
import yaml
from prepare import ROOT
from analyze import load

BAND=1.8/256/4
VERIFY=ROOT/'verification/sar8_physical_repair'

def resolve(run):
    folder=ROOT/'output/managed_execution/runs'/run/'collected'
    receipt=json.loads((folder/'collection_receipt.json').read_text());paths={}
    assert not receipt['skipped'],receipt['skipped']
    for item in receipt['files']:
        p=folder/item['name']
        sha=lambda q:hashlib.sha256(q.read_bytes()).hexdigest()
        if not p.exists() or sha(p)!=item['sha256']:p=p.with_name(p.stem+'.'+item['sha256'][:12]+p.suffix)
        assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256'];paths[item['name']]=p
    return folder,paths,receipt

def analyze(run):
    folder,paths,receipt=resolve(run)
    sim=json.loads(paths['simulation.state.json'].read_text());ana=json.loads(paths['analysis.state.json'].read_text())
    assert sim['status']==ana['status']=='complete' and sim['exit_code']==ana['exit_code']==0
    log=paths['spectre.out'].read_text(errors='replace')
    assert re.search(r'tran_perf\s+PASS',paths['raw/logStatus'].read_text())
    assert 'spectre completes with 0 errors' in log and not any(x in log for x in ['Failed to find','SPECTRE-8003'])
    manifest=json.loads((VERIFY/(run+'_manifest.json')).read_text());vdd=manifest['vdd']
    recipe=yaml.safe_load((ROOT/'management/runs'/(run+'.yaml')).read_text())['recipe']
    frozen=ROOT/'output/managed_execution/runs'/run/'inputs'
    for item in recipe['files']:
        assert hashlib.sha256((frozen/item['name']).read_bytes()).hexdigest()==item['sha256'],item['name']
    result=json.loads(paths['derived/result.json'].read_text())
    m,w,t,meta=load(folder/'derived')
    steps=int(re.search(r'Number of accepted tran steps\s*=\s*(\d+)',log)[1])
    assert steps+1==meta['native_points']
    assert meta['traces']==manifest['saved_count']
    assert result['all_MOS_pairs']==manifest['records']==10998
    ev={}
    for line in paths['derived/wave.events.tsv'].read_text().splitlines():
        name,up,at=line.split();ev.setdefault((name,int(up)),[]).append(float(at)*1e9)
    def events(name,start,end,up=1):return [e for e in ev.get((name,up),[]) if start<=e<end]
    def at(name,x):return float(np.interp(x,t,w[name]))
    energy={}
    for line in paths['derived/wave.products.tsv'].read_text().splitlines():
        name,f,value=line.split();energy.setdefault(name,[0.,0.])[int(f)]=float(value)
    rows=[[float(v) for v in r.split(',')] for r in re.findall(r'R4MEAS,([^\r\n]+)',log)]
    assert [int(r[0]) for r in rows]==[0,1]
    diff=w['xdut.topp']-w['xdut.topn'];cm=(w['xdut.topp']+w['xdut.topn'])/2
    frames=[];comparisons=[];settling=[]
    for i,row in enumerate(rows):
        lo,hi=i*100,(i+1)*100;target=[.81,-.81][i]
        code=sum(int(at('d%d'%b,hi-2)>.5*vdd)*2**b for b in range(8))
        names=['xdut.cmp_clk','xdut.xctrl.phi_w','xdut.phi_u','xdut.xref.cap_clk']
        counts=[len(events(n,lo,hi)) for n in names]
        cmp=events(names[0],lo,hi);wr=events(names[1],lo,hi);upd=events(names[2],lo,hi)
        close=events('xdut.seq_sample',lo,hi,0);start=events('xdut.seq_sample',lo,hi)
        frame=dict(frame=i,code=code,expected=[243,12][i],code_pass=code==[243,12][i],counts=counts,monitor_valid=bool(row[7]),
                   monitor_code=int(row[1]),monitor_code_matches=code==int(row[1]),
                   monitor_counts=[int(x) for x in row[2:6]],native_count_match=counts==[int(x) for x in row[2:6]],
                   sample_close_ns=close,sample_start_ns=start,conversion_ns=row[-1]*1e9,
                   sample_window_ns=close[0]-start[0] if len(close)==len(start)==1 else None,
                   preclose_error_mv=None if len(close)!=1 else (float(np.interp(close[0]-.2,t,diff))-target)*1000,
                   top_diff_at_41p8ns_mv=float(np.interp(lo+41.8,t,diff))*1000,
                   monitor_held_diff_mv=row[11]*1000,monitor_held_error_mv=(row[11]-target)*1000,
                   held_41p8_before_first_compare=bool(cmp and lo+41.8<cmp[0]),
                   energy_pj={key:-energy[key][i]*1e12 for key in ['VDD','REFP','REFN','CLOCK','INPUTP','INPUTN']},
                   comparator_terminal_absorbed_energy_pj=sum(values[i] for key,values in energy.items() if key.startswith('xdut.xcomp.'))*1e12)
        # Energy in 100ns -> average uW = pJ*10. Startup and frame1 stay separate.
        frame['supply_reference_average_uw']=(frame['energy_pj']['VDD']+frame['energy_pj']['REFP']+frame['energy_pj']['REFN'])*10
        reset=events('xdut.xref.rst0',lo+41,hi)
        frame['last_ref_reset_ns']=reset
        errors=[];illegal=[]
        for s in ['p','n']:
            for b in range(8):
                non=at('xdut.g%sn%d'%(s,b),hi-.1)>.5*vdd
                pon=at('xdut.g%sp%d'%(s,b),hi-.1)<.5*vdd
                if non==pon:illegal.append('B%s%d'%(s.upper(),b))
                errors.append(abs(at('xdut.xcdac.b%s%d'%(s,b),hi-.1)-(.9 if pon else 0)))
        frame['next_sample_bottom_error_mv']=max(errors)*1000
        frame['next_sample_illegal_reference_states']=illegal
        frames.append(frame)
        for bit,rise in enumerate(cmp):
            nxt=cmp[bit+1] if bit+1<len(cmp) else hi
            writes=[x for x in wr if rise<x<nxt]
            end=writes[0]-.02 if writes else min(nxt-.02,rise+10)
            ids=(t>=rise)&(t<=end);signed=1 if float(np.interp(rise,t,diff))>=0 else -1
            delta=signed*(w['xdut.comp_p']-w['xdut.comp_n'])
            crossings=np.flatnonzero((delta[:-1]<.8*vdd)&(delta[1:]>=.8*vdd)&(t[1:]>=rise)&(t[1:]<=end))
            decided=None
            if len(crossings):
                k=crossings[0];decided=float(t[k]+(.8*vdd-delta[k])*(t[k+1]-t[k])/(delta[k+1]-delta[k]))
            qtime=np.r_[rise-.02,t[(t>rise-.02)&(t<end)],end]
            qgate={n:float(np.trapezoid(np.interp(qtime,t,w[n]),qtime*1e-9))*1e15
                   for n in ['xdut.xcomp.mninp:2','xdut.xcomp.mninn:2']}
            comparisons.append(dict(frame=i,decision=bit,clock_ns=rise,write_ns=writes[0] if writes else None,
                delay_to_0p8vdd_ns=None if decided is None else decided-rise,
                preclock_diff_mv=float(np.interp(rise-.02,t,diff))*1000,
                preclock_cm_v=float(np.interp(rise-.02,t,cm)),
                diff_change_before_write_mv=(float(np.interp(end,t,diff))-float(np.interp(rise-.02,t,diff)))*1000,
                max_abs_diff_motion_mv=float(np.max(np.abs(np.interp(qtime,t,diff)-np.interp(rise-.02,t,diff))))*1000,
                cm_peak_motion_mv=float(np.max(np.abs(np.interp(qtime,t,cm)-np.interp(rise-.02,t,cm))))*1000,
                reset_lowest_v=min(at(n,rise-.02) for n in ['xdut.comp_n','xdut.comp_p','xdut.xcomp.x','xdut.xcomp.y']),
                reset_output_delta_mv=(at('xdut.comp_p',rise-.02)-at('xdut.comp_n',rise-.02))*1000,
                input_gate_charge_fc_compact_estimate=qgate,
                input_gate_peak_ua={n:float(np.max(np.abs(w[n][ids])))*1e6 if np.any(ids) else None
                                   for n in ['xdut.xcomp.mninp:2','xdut.xcomp.mninn:2']}))
        for j,u in enumerate(upd):
            later=[x for x in cmp if x>u]
            if not later:continue
            deadline=later[0]-.01;ids=np.flatnonzero((t>=u)&(t<=deadline));ts=t[ids]
            err=np.zeros(len(ids));invalid=[]
            for s in ['p','n']:
                for b in range(8):
                    gn='xdut.g%sn%d'%(s,b);gp='xdut.g%sp%d'%(s,b);bot='xdut.xcdac.b%s%d'%(s,b)
                    non=at(gn,deadline)>.5*vdd;pon=at(gp,deadline)<.5*vdd
                    if non==pon:invalid.append(bot)
                    expected=.9 if pon else 0
                    err=np.maximum(err,np.abs(w[bot][ids]-expected))
            bad=np.flatnonzero(err>BAND)
            settled=None if not len(ids) or (len(bad) and bad[-1]==len(ids)-1) else float(ts[bad[-1]+1] if len(bad) else u)
            settling.append(dict(frame=i,update=j,deadline_ns=deadline,settle_after_update_ns=None if settled is None else settled-u,
                                 deadline_error_mv=float(err[-1])*1000 if len(err) else None,illegal_gate_states=invalid))
    result.update(run_id=run,vdd=vdd,corner=manifest['corner'],temperature_c=manifest['temp_c'],mode=manifest['modes'],frames=frames,comparisons=comparisons,settling_estimates=settling,
                  all_codes_pass=all(f['code_pass'] and f['monitor_code_matches'] for f in frames),
                  all_event_counts_pass=all(f['counts']==[8,8,8,16] and f['monitor_valid'] and f['native_count_match'] for f in frames),
                  native_DC_relaxation_warning='SPECTRE-17191' in log,
                  plot_estimate_spacing_ps=20,CMI_present='WARNING (CMI-' in log,
                  source_energy_sign='positive = supplied; comparator terminal energy positive = absorbed; time-weighted native trapezoids',
                  motion_scope='compare-phase top motion, not isolated comparator kickback; includes simultaneous circuit response',
                  collected_files=len(receipt['files']),collected_bytes=sum(x['bytes'] for x in receipt['files']),
                  simulation_peak_rss_mib=sim['peak_rss_bytes']/2**20,analysis_peak_rss_mib=ana['peak_rss_bytes']/2**20)
    result['numerical_screen_only']=manifest.get('numerical_screen_only',False)
    result['frozen_inputs_sha_verified']=True
    result['source_commit']=recipe['source_commit']
    result['simulation_elapsed_s']=sim['elapsed_seconds'];result['analysis_elapsed_s']=ana['elapsed_seconds']
    extrema={}
    for line in paths['derived/wave.extrema.tsv'].read_text().splitlines():
        n,*values=line.split();extrema[n]=list(map(float,values))
    result['bottom_min']=min((dict(node='xdut.xcdac.b%s%d'%(s,b),value_v=extrema['xdut.xcdac.b%s%d'%(s,b)][0],
        time_ns=extrema['xdut.xcdac.b%s%d'%(s,b)][1]*1e9) for s in ['p','n'] for b in range(8)),key=lambda x:x['value_v'])
    result['native_gate_extrema']={n:extrema[n] for n in ['xdut.gnn4','xdut.gpn7','xdut.gpp7']}
    off=[]
    for instant in [30.,98.,130.,198.]:
        for side,bit in [('p',7),('n',4),('p',3)]:
            bot='xdut.xcdac.b%s%d'%(side,bit)
            for pol,model,rail in [('n','mn_low','vrefn'),('p','mp_high','vrefp')]:
                gate='xdut.g%s%s%d'%(side,pol,bit);device='xdut.xcdac.xs%s%d.%s'%(side,bit,model)
                vgs=at(gate,instant)-at(rail,instant);vds=at(bot,instant)-at(rail,instant)
                off.append(dict(time_ns=instant,instance=device,vgs_v=vgs,vds_v=vds,
                    near_off_gate=bool(vgs<.1 if pol=='n' else vgs>-.1),full_swing_vds=abs(vds)>.85,
                    drain_current_na=at(device+':1',instant)*1e9,
                    gate_current_na=at(device+':2',instant)*1e9,
                    source_current_na=at(device+':3',instant)*1e9,
                    body_current_na=at(device+':4',instant)*1e9,
                    drain_motion_last_0p2ns_mv=(at(bot,instant)-at(bot,instant-.2))*1000))
    result['reference_terminal_snapshots']=off
    result['effective_settings']=sim['native']['effective_settings']
    result['warnings']=sim['native']['warning_codes']
    # Existing unchanged-circuit FF comparison has exact event timestamps.
    baseline=VERIFY/'sar8fix-loaded-base-sscold_analysis.json' if manifest['corner']=='sscold' else ROOT/'verification/sar8_stress_closure/rg1_strict200_ff_m40_stream_analysis.json' if manifest['corner']=='ffcold' else None
    if baseline and baseline.exists() and run!='sar8fix-loaded-base-sscold':
        b=json.loads(baseline.read_text());deltas=[];windows=[]
        for i,frame in enumerate(frames):
            bc=b['frames'][i]['sample_close_ns'];bc=bc[0] if isinstance(bc,list) else bc
            deltas.append((frame['sample_close_ns'][0]-bc)*1000 if len(frame['sample_close_ns'])==1 else None)
            bw=b['frames'][i].get('sample_window_ns')
            windows.append((frame['sample_window_ns']-bw)*1000 if frame['sample_window_ns'] is not None and bw is not None else None)
        result['baseline_aperture_comparison']=dict(path=str(baseline.relative_to(ROOT)),sample_close_delta_ps=deltas,sample_window_delta_ps=windows)
    (VERIFY/(run+'_analysis.json')).write_text(json.dumps(result,indent=2)+'\n')
    plot(run,w,t,result)
    print(json.dumps({k:result[k] for k in ['run_id','all_codes_pass','all_event_counts_pass','frames','groups','failing_pairs']},indent=2))

def plot(run,w,t,r):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(5,1,figsize=(11,10),sharex=True,layout='constrained')
    for ax,names,label in zip(axes,[['xdut.seq_sample','xdut.cmp_clk'],['xdut.comp_p','xdut.comp_n'],
        ['xdut.topp','xdut.topn'],['xdut.xcomp.mninp:2','xdut.xcomp.mninn:2'],['xdut.xcdac.bp7','vrefp','vrefn']],
        ['Timing (V)','Comparator (V)','CDAC top (V)','Input gate current (uA)','Reference / BP7 (V)']):
        for n in names:ax.plot(t,w[n]*(1e6 if ':2' in n else 1),lw=1,label=n.replace('xdut.',''))
        ax.set_ylabel(label);ax.grid(alpha=.2);ax.legend(fontsize=8,loc='best',ncol=len(names))
    axes[-1].set(xlim=(138,200),xlabel='Time (ns)')
    label={'ref':'IO scale2 reference / core comparator','comp':'Core reference / N4 comparator',
           'both':'IO scale2 reference / N4 comparator','base':'Unchanged core reference and comparator'}[r['mode']]
    fig.suptitle('%s | %s, %.2f V, %d C\n'%(label,r['corner'].upper(),r['vdd'],r['temperature_c'])+
        'Physical CDAC / BBM / logic; ideal external VDD and SAMPLE; input/reference 50 ohm, decoupling 4 pF\n'+
        '20 ps display; no mismatch / PEX / noise; stress, energy and clock crossings use all native points',fontsize=10)
    out=ROOT/'docs/figures/sar8_physical_repair';out.mkdir(exist_ok=True)
    fig.savefig(out/(run+'.png'),dpi=160);plt.close(fig)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run');analyze(p.parse_args().run)
