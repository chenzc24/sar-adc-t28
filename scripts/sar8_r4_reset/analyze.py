"""Offline whole-window terminal stress and independent output/timing audit."""
import argparse
import re
import numpy as np
from experiment import OUT, SOURCE, read, dump, sha


def analyze(name):
    folder=OUT/name; ctx=read(folder/'context.json'); result=read(folder/'result.json')
    assert result['ok'],result['errors']
    assert sha(folder/'wave.npz')==read(folder/'wave_receipt.json')['sha256']
    assert sha(folder/'test.scs')==ctx['deck_sha256']
    w=dict(np.load(folder/'wave.npz')); t=w['time']; tn=t*1e9
    def v(node):
        return np.zeros_like(t) if node=='0' else w[node.lower()]
    log=(folder/'spectre/spectre.out').read_text(errors='replace')
    assert 'spectre completes with 0 errors' in log
    rows=re.findall(r'R4MEAS,([^\r\n]+)',log)
    rows=[[float(x) for x in row.split(',')] for row in rows]
    assert len(rows)==int(ctx['stop_ns']//100),len(rows)
    frames=[]
    for row in rows:
        i=int(row[0]); sample_t=(i*100+98)*1e-9
        monitor_ok=bool(int(row[7])==1 and [int(x) for x in row[2:6]]==[8,8,8,16])
        if i*100 < ctx.get('outputstart_ns',0):
            frames.append(dict(frame=i,code=int(row[1]),monitor_valid=int(row[7]),
                               independent_wave_check=False,pass_timing=monitor_ok,
                               conversion_ns=row[-1]*1e9,monitor_clock_marker_ns=row[9]*1e9))
            continue
        levels=np.array([np.interp(sample_t,t,v(f'D{b}')) for b in range(8)])
        code=int(np.dot(levels>.45,2**np.arange(8)))
        counts={}
        for n in ['XDUT.CMP_CLK','XDUT.XCTRL.PHI_W','XDUT.PHI_U','XDUT.XREF.CAP_CLK']:
            x=v(n); rising=(x[:-1]<.45)&(x[1:]>=.45)
            counts[n]=int(np.sum(rising&(tn[1:]>=i*100)&(tn[1:]<(i+1)*100)))
        assert code==int(row[1]),(i,code,row[1])
        expected=[8,8,8,16]
        frame_ok=bool(monitor_ok and list(counts.values())==expected)
        # Independently verify no output transition anywhere in 90–98 ns.
        mask=(tn>=i*100+90)&(tn<=i*100+98)
        stable=all(np.all((v(f'D{b}')[mask]>.45)==bool(code&(1<<b))) for b in range(8))
        frames.append(dict(frame=i,code=code,monitor_valid=int(row[7]),edge_counts=counts,independent_wave_check=True,
                           stable_90_98ns=stable,pass_timing=frame_ok and stable,
                           conversion_ns=row[-1]*1e9,monitor_clock_marker_ns=row[9]*1e9))
    stresses=[]
    group_max={g:np.zeros_like(t) for g in ['reference','comparator','bootstrap','sequencer']}
    for d in ctx['stress_devices']:
        nodes={n:v(net) for n,net in d['nodes'].items()}
        inst=d['instance']
        group='reference' if '.XCDAC.' in inst else 'comparator' if '.XCOMP.' in inst else 'bootstrap' if '.XBOOT' in inst else 'sequencer'
        for a,b in [('d','s'),('g','s'),('g','d'),('g','b'),('b','d'),('b','s')]:
            values=np.abs(nodes[a]-nodes[b]); index=int(np.argmax(values)); bad=values>d['limit_v']
            group_max[group]=np.maximum(group_max[group],values)
            stresses.append(dict(instance=inst,terminal=a+b,model=d['model'],group=group,
                peak_v=float(values[index]),time_ns=float(tn[index]),limit_v=d['limit_v'],
                exceed=bool(bad.any()),first_saved_exceed_ns=float(tn[bad][0]) if bad.any() else None,
                last_saved_exceed_ns=float(tn[bad][-1]) if bad.any() else None))
    edges={}
    for n in ['XDUT.SAMPLE_INT']+(['XDUT.SEQ_SAMPLE'] if ctx['kind']!='baseline' else []):
        x=v(n); edges[n]={}
        for direction in ['rise','fall']:
            ids=np.where((x[:-1]<.45)&(x[1:]>=.45) if direction=='rise' else (x[:-1]>.45)&(x[1:]<=.45))[0]
            edges[n][direction]=[float(tn[i]+(.45-x[i])*(tn[i+1]-tn[i])/(x[i+1]-x[i])) for i in ids]
    groups={g:dict(peak_v=float(y.max()),time_ns=float(tn[np.argmax(y)])) for g,y in group_max.items()}
    settings={key:(re.findall(r'(?m)^\s*'+re.escape(key)+r' = (.+)$',log) or [None])[-1]
              for key in ['maxstep','reltol','abstol(V)','abstol(I)','method','relref']}
    settings={k:v.split(', default')[0] if v is not None else None for k,v in settings.items()}
    baseline=read(SOURCE/'analysis.json')['frames']
    differences=[dict(frame=f['frame'],baseline=baseline[f['frame']]['code'],candidate=f['code'])
                 for f in frames if f['code']!=baseline[f['frame']]['code']]
    cmi=[line.strip() for line in log.splitlines() if 'WARNING (CMI-' in line]
    cmi_events=[];last_warning_time=None
    for line in log.splitlines():
        match=re.search(r'Warning from spectre at time = (.+?) during',line)
        if match:last_warning_time=match[1]
        if 'WARNING (CMI-' in line:
            cmi_events.append(dict(reported_time=last_warning_time,message=line.strip()))
    report=dict(name=name,kind=ctx['kind'],frames=frames,all_frame_timing_pass=all(f['pass_timing'] for f in frames),
                groups=groups,all_saved_stress_pass=not any(s['exceed'] for s in stresses),
                observed_electrical_pass=not cmi and not any(s['exceed'] for s in stresses),
                baseline_code_differences=differences,
                failing_terminals=[s for s in stresses if s['exceed']],stresses=stresses,
                edges_50pct_ns=edges,effective_settings=settings,
                native_CMI=cmi,
                native_CMI_events=cmi_events,
                points=len(t),saved_window_ns=[float(tn[0]),float(tn[-1])],DUT_sha256=ctx['DUT_sha256'],wave_sha256=sha(folder/'wave.npz'),
                log_sha256=sha(folder/'spectre/spectre.out'),
                limits=['Nominal bounded replay only, not PVT or complete logic stress qualification.',
                        'Peaks are from saved adaptive samples, not an independent convergence proof.',
                        'Native CMI in an unsaved interval still fails electrical qualification.',
                        'Original full-sine code comparison is diagnostic: aperture and solver settings may differ.',
                        'Monitor SAMPLE refers to original internal control, not modified acquisition gate.'])
    dump(folder/'analysis.json',report)
    np.savez_compressed(folder/'stress_envelopes.npz',time=t,**group_max)
    print(name,'codes',[f['code'] for f in frames],'timing',report['all_frame_timing_pass'],
          'stress',report['all_saved_stress_pass'],'groups',groups,'failures',len(report['failing_terminals']))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('names',nargs='+');a=p.parse_args()
    for name in a.names:analyze(name)
