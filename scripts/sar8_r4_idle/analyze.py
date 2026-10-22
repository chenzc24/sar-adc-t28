"""Independent idle reset ordering, data retention, aperture-control and stress audit."""
import argparse
import importlib.util
import re
import numpy as np
from flow import ROOT, OUT, read, dump, sha

spec=importlib.util.spec_from_file_location('staged_analyze',ROOT/'scripts/sar8_r4_staged/analyze.py')
staged=importlib.util.module_from_spec(spec);spec.loader.exec_module(staged)


def analyze(name):
    # Reuse established per-MOS six-pair stress, native log and independent clock checks.
    # Its current-cycle reset assumption is explicitly replaced for this architecture.
    report=staged.analyze(name)
    z=np.load(OUT/name/'wave.npz'); t=z['time']*1e9
    def v(n):return z[n.lower()]
    def edges(n,up=True):
        x=v(n); k=np.flatnonzero((x[:-1]<.45)&(x[1:]>=.45) if up else (x[:-1]>.45)&(x[1:]<=.45))
        return t[k]+(.45-x[k])*(t[k+1]-t[k])/(x[k+1]-x[k])
    ref=read(ROOT/'output/sar8_r4_staged/msb_4600/analysis.json')
    # Reference falling edges are periodic and independent of input to within native variation.
    ref_falls=np.array(ref['edges_50pct_ns']['XDUT.SEQ_SAMPLE']['fall'])
    idlechecks=[]
    rises={b:edges(f'XDUT.XREF.RST{b}') for b in range(8)}
    capfall=edges('XDUT.XREF.CAP_CLK',False)
    sample_rises=edges('XDUT.SAMPLE_INT')
    for f in report['frames']:
        i=f['frame'];lo=i*100;hi=lo+100
        resets=[rises[b][(rises[b]>lo+41)&(rises[b]<hi)] for b in range(8)]
        lastcap=capfall[(capfall>lo+41)&(capfall<hi)]
        ordered=all(len(x)==1 for x in resets) and bool(np.all(np.diff([resets[b][0] for b in reversed(range(8))])>0))
        first=float(resets[7][0]) if len(resets[7])==1 else None
        last=float(resets[0][0]) if len(resets[0])==1 else None
        next_sample=sample_rises[sample_rises>lo+41]
        stable_until=min(float(next_sample[0])-.05,float(t[-1])) if len(next_sample) else float(t[-1])
        mask=(t>=first-1)&(t<=stable_until) if first is not None else np.zeros(len(t),dtype=bool)
        stable=bool(mask.any()) and all(np.all((v(f'D{b}')[mask]>.45)==bool(f['code']&(1<<b))) for b in range(8))
        word=int(sum((np.interp(hi-1,t,v(f'XDUT.XREF.Q{b}'))>.45)*(1<<b) for b in range(8)))
        idlechecks.append(dict(frame=i,first_reset_ns=first,last_reset_ns=last,
            final_capture_fall_ns=float(lastcap[-1]) if len(lastcap) else None,
            after_final_capture=bool(first is not None and len(lastcap) and first>lastcap[-1]),
            ordered_msb_to_lsb=ordered,data_unchanged_during_reset=stable,
            data_checked_until_ns=stable_until,
            word_before_next_cycle=word,
            pass_idle=bool(ordered and stable and word==128 and len(lastcap) and first>lastcap[-1])))
    acquisitions=report['acquisitions']
    for a in acquisitions:
        cycle=int(a['start_ns']//100)
        a.pop('reset_current_cycle_pass',None)
        a['reset_previous_cycle_pass']=all(x is not None and (cycle-1)*100+41<x<cycle*100 for x in a['reset_rises_ns_by_bit'])
        nearest=float(ref_falls[np.argmin(abs(ref_falls-a['end_ns']))])
        a['closing_delta_vs_staged_ps']=(a['end_ns']-nearest)*1000
        a['window_restored']=a['duration_ns']>=38.2
        a['closing_preserved_50ps']=abs(a['closing_delta_vs_staged_ps'])<=50
    report['idle_checks']=idlechecks
    report['acquisition_logic_pass']=bool(acquisitions) and all(a['reference_word_at_start']==128 and a['gate_off_before_first_comparison'] and a['reset_order_pass'] and a['reset_previous_cycle_pass'] and a['all_resets_low_at_first_comparison'] for a in acquisitions)
    report['window_and_closing_pass']=bool(acquisitions) and all(a['window_restored'] and a['closing_preserved_50ps'] for a in acquisitions)
    report['idle_reset_pass']=all(x['pass_idle'] for x in idlechecks)
    startup_word=int(sum((v(f'XDUT.XREF.Q{b}')[0]>.45)*(1<<b) for b in range(8)))
    report['startup_check']=dict(time_ns=float(t[0]),reference_word=startup_word,
        all_reset_asserted=all(v(f'XDUT.XREF.RST{b}')[0]>.81 for b in range(8)),
        bootstrap_enable_v=float(v('XDUT.SEQ_SAMPLE')[0]))
    startup_ok=t[0]==0 and startup_word==128 and report['startup_check']['all_reset_asserted']
    report['observed_functional_pass']=bool(startup_ok and report['acquisition_logic_pass'] and report['all_frame_timing_pass'] and report['idle_reset_pass'] and not any(report['nonoverlap_HL_both_high_samples'].values()))
    report['control_edge_range']=dict(min_window_ns=min(a['duration_ns'] for a in acquisitions),
        max_abs_closing_delta_ps=max(abs(a['closing_delta_vs_staged_ps']) for a in acquisitions))
    report['comparisons']={}
    for label,path in [('A','sar8_r4_reset/reset_first_c20_late4600'),('staged','sar8_r4_staged/msb_4600')]:
        old=read(ROOT/'output'/path/'analysis.json')['frames']
        report['comparisons'][label]=[dict(frame=f['frame'],old=old[f['frame']]['code'],new=f['code']) for f in report['frames'] if old[f['frame']]['code']!=f['code']]
    def monitor_rows(path):
        return [[float(x) for x in line.split(',')] for line in re.findall(r'R4MEAS,([^\r\n]+)',path.read_text(errors='replace'))]
    native=monitor_rows(OUT/name/'spectre/spectre.out')
    oldnative=monitor_rows(ROOT/'output/sar8_r4_staged/msb_4600/spectre/spectre.out')
    report['changed_code_sample_diagnostics']=[dict(frame=d['frame'],
        old_held_diff_v=oldnative[d['frame']][11],new_held_diff_v=native[d['frame']][11],
        held_diff_delta_uv=(native[d['frame']][11]-oldnative[d['frame']][11])*1e6,
        measurement='Native passive monitor at the same frame-relative 41.8 ns, before first comparison; not a unique cause attribution.') for d in report['comparisons']['staged']]
    report['startup_note']='Frame 0 starts from DC-initialized SAMPLE/preset. No preceding idle pulse; all frame-0 clocks/codes/stress still audited.'
    report['extra_edges_50pct_ns']={n:dict(rise=edges(n).tolist(),fall=edges(n,False).tolist()) for n in ['XDUT.ACTIVE','XDUT.PRESET','XDUT.SAMPLE_MATCH']}
    dump(OUT/name/'analysis.json',report)
    print('IDLE_AUDIT',name,'functional',report['observed_functional_pass'],'window',report['window_and_closing_pass'],report['control_edge_range'])
    print('IDLE_TIMES',idlechecks)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('names',nargs='+');args=p.parse_args()
    for name in args.names:analyze(name)
