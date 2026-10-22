"""Independent native-waveform audit for the bounded staged-reset cases."""
import argparse
import re
import numpy as np
from flow import OUT, ROOT, prior, read, dump, sha


def analyze(name):
    folder=OUT/name;ctx=read(folder/'context.json');result=read(folder/'result.json')
    assert result['ok'] and result['native_exit_code']==0
    assert sha(folder/'wave.npz')==read(folder/'wave_receipt.json')['sha256']
    assert sha(folder/'test.scs')==ctx['deck_sha256']
    w=dict(np.load(folder/'wave.npz'));t=w['time'];tn=t*1e9
    def v(n):return np.zeros_like(t) if n=='0' else w[n.lower()]
    log=(folder/'spectre/spectre.out').read_text(errors='replace')
    rows=[[float(x) for x in row.split(',')] for row in re.findall(r'R4MEAS,([^\r\n]+)',log)]
    assert [int(r[0]) for r in rows]==list(range(int(ctx['stop_ns']//100)))
    def edges(n,up=True):
        x=v(n);ids=np.where((x[:-1]<.45)&(x[1:]>=.45) if up else (x[:-1]>.45)&(x[1:]<=.45))[0]
        return tn[ids]+(.45-x[ids])*(tn[ids+1]-tn[ids])/(x[ids+1]-x[ids])
    clocks=['XDUT.CMP_CLK','XDUT.XCTRL.PHI_W','XDUT.PHI_U','XDUT.XREF.CAP_CLK']
    clockedges={n:edges(n) for n in clocks}
    frames=[]
    for row in rows:
        i=int(row[0]);monitor_ok=int(row[7])==1 and [int(x) for x in row[2:6]]==[8,8,8,16]
        f=dict(frame=i,code=int(row[1]),monitor_valid=int(row[7]),independent_wave_check=False,
               pass_timing=bool(monitor_ok),conversion_ns=row[-1]*1e9)
        if i*100>=ctx['outputstart_ns']:
            code=int(sum((np.interp((i*100+98)*1e-9,t,v(f'D{b}'))>.45)*(1<<b) for b in range(8)))
            assert code==int(row[1])
            counts={n:int(np.sum((x>=i*100)&(x<(i+1)*100))) for n,x in clockedges.items()}
            mask=(tn>=i*100+90)&(tn<=i*100+98);assert mask.any()
            stable=all(np.all((v(f'D{b}')[mask]>.45)==bool(code&(1<<b))) for b in range(8))
            f.update(independent_wave_check=True,edge_counts=counts,stable_90_98ns=stable,
                     pass_timing=bool(monitor_ok and list(counts.values())==[8,8,8,16] and stable))
        frames.append(f)
    stress=[];envelopes={g:np.zeros_like(t) for g in sorted({d['group'] for d in ctx['stress_devices']})}
    for d in ctx['stress_devices']:
        nodes={n:v(net) for n,net in d['nodes'].items()}
        for a,b in [('d','s'),('g','s'),('g','d'),('g','b'),('b','d'),('b','s')]:
            y=np.abs(nodes[a]-nodes[b]);k=int(np.argmax(y));bad=y>d['limit_v']
            envelopes[d['group']]=np.maximum(envelopes[d['group']],y)
            stress.append(dict(instance=d['instance'],group=d['group'],terminal=a+b,model=d['model'],
                peak_v=float(y[k]),time_ns=float(tn[k]),limit_v=d['limit_v'],exceed=bool(bad.any()),
                first_exceed_ns=float(tn[bad][0]) if bad.any() else None))
    groups={g:dict(peak_v=float(y.max()),time_ns=float(tn[np.argmax(y)])) for g,y in envelopes.items()}
    signals=['XDUT.SAMPLE_INT','XDUT.SEQ_SAMPLE']
    if ctx['order']!='parallel':signals+=['XDUT.RST_DONE']+[f'XDUT.XREF.RST{i}' for i in range(8)]
    timing={n:dict(rise=edges(n).tolist(),fall=edges(n,False).tolist()) for n in signals}
    # Logic-level reset/acquisition checks, not a physical aperture measurement.
    acquisitions=[]
    for start in edges('XDUT.SEQ_SAMPLE'):
        falls=edges('XDUT.SEQ_SAMPLE',False);falls=falls[falls>start]
        if not len(falls):continue
        stop=float(falls[0]);code=int(sum((np.interp(start*1e-9,t,v(f'XDUT.XREF.Q{b}'))>.45)*(1<<b) for b in range(8)))
        entry=dict(start_ns=float(start),end_ns=stop,duration_ns=stop-float(start),reference_word_at_start=code)
        cycle=int(start//100);comparisons=clockedges['XDUT.CMP_CLK']
        comparisons=comparisons[(comparisons>=cycle*100)&(comparisons<(cycle+1)*100)]
        entry['gate_off_before_first_comparison']=bool(len(comparisons) and stop<comparisons[0])
        if ctx['order']!='parallel':
            latest=[]
            for b in range(8):
                candidates=edges(f'XDUT.XREF.RST{b}');candidates=candidates[candidates<=start]
                latest.append(float(candidates[-1]) if len(candidates) else None)
            entry['reset_rises_ns_by_bit']=latest
            expected=list(range(8)) if ctx['order']=='lsb' else list(reversed(range(8)))
            entry['reset_order_pass']=all(x is not None for x in latest) and bool(np.all(np.diff([latest[b] for b in expected])>0))
            entry['reset_current_cycle_pass']=all(x is not None and cycle*100<=x<start for x in latest)
            entry['all_resets_low_at_first_comparison']=bool(len(comparisons) and all(np.interp(comparisons[0]*1e-9,t,v(f'XDUT.XREF.RST{b}'))<.45 for b in range(8)))
        acquisitions.append(entry)
    overlap={str(b):int(np.sum((v(f'XDUT.XREF.H{b}')>.45)&(v(f'XDUT.XREF.L{b}')>.45))) for b in range(8)}
    acquisition_ok=bool(acquisitions) and all(x['reference_word_at_start']==128 and x['gate_off_before_first_comparison']
        and x.get('reset_order_pass',True) and x.get('reset_current_cycle_pass',True)
        and x.get('all_resets_low_at_first_comparison',True) for x in acquisitions)
    cmi=[];event_time=None
    for line in log.splitlines():
        m=re.search(r'Warning from spectre at time = (.+?) during',line)
        if m:event_time=m[1]
        if 'WARNING (CMI-' in line:cmi.append(dict(time=event_time,message=line.strip()))
    settings={key:(re.findall(r'(?m)^\s*'+re.escape(key)+r' = (.+)$',log) or [None])[-1]
              for key in ['maxstep','reltol','abstol(V)','abstol(I)','method','relref']}
    baseline=read(prior.SOURCE/'analysis.json')['frames']
    report=dict(name=name,DUT_sha256=ctx['DUT_sha256'],wave_sha256=sha(folder/'wave.npz'),
        groups=groups,stress=stress,failing_terminals=[x for x in stress if x['exceed']],
        frames=frames,all_frame_timing_pass=all(f['pass_timing'] for f in frames),
        observed_electrical_pass=not cmi and not any(s['exceed'] for s in stress),native_CMI=cmi,
        effective_settings=settings,edges_50pct_ns=timing,acquisitions=acquisitions,
        acquisition_logic_pass=acquisition_ok,
        observed_functional_pass=acquisition_ok and all(f['pass_timing'] for f in frames) and not any(overlap.values()),
        nonoverlap_HL_both_high_samples=overlap,
        baseline_code_differences=[dict(frame=f['frame'],baseline=baseline[f['frame']]['code'],candidate=f['code']) for f in frames if f['code']!=baseline[f['frame']]['code']],
        saved_window_ns=[float(tn[0]),float(tn[-1])],points=len(t),
        current_signals_verified=ctx['current_signals'],
        limits=['Selected MOS endpoints only; native CMI elsewhere still fails.',
                'Native adaptive samples, no intersample peak guarantee.',
                'Nominal bounded test, not FFT/PVT/mismatch/PEX qualification.',
                'Acquisition timestamps are 50% gate-control crossings, not physical aperture.'])
    dump(folder/'analysis.json',report);np.savez_compressed(folder/'stress_envelopes.npz',time=t,**envelopes)
    print(name,'codes',[f['code'] for f in frames],'timing',report['all_frame_timing_pass'],
          'electrical',report['observed_electrical_pass'],'groups',groups,'CMI',len(cmi),flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('names',nargs='+');a=p.parse_args()
    for name in a.names:analyze(name)
