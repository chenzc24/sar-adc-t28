"""Curate completed follow-up evidence and plot the worst saved late event."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from experiment import ROOT, OUT, read, dump


NAMES=['reset_first_c20_precise500','reset_first_c20_late4600']


def main():
    reports=[]
    for name in NAMES:
        folder=OUT/name
        if not (folder/'analysis.json').exists():
            reports.append(dict(name=name,status='awaiting verified analysis'))
            continue
        r=read(folder/'analysis.json');ctx=read(folder/'context.json')
        keys=['name','kind','all_frame_timing_pass','all_saved_stress_pass',
              'observed_electrical_pass','baseline_code_differences','groups',
              'failing_terminals','effective_settings','native_CMI','native_CMI_events','points',
              'saved_window_ns','DUT_sha256','wave_sha256','log_sha256','limits']
        s={k:r[k] for k in keys}
        s.update(status='verified',frame_count=len(r['frames']),
                 independently_checked_frames=[f['frame'] for f in r['frames'] if f['independent_wave_check']],
                 codes=[f['code'] for f in r['frames']],
                 command_options=ctx['spectre_args'],outputstart_ns=ctx['outputstart_ns'])
        s['recovery']=read(folder/'result.json').get('recovery')
        reports.append(s)
    dump(ROOT/'verification/sar8_r4_reset/followup.json',reports)
    folder=OUT/NAMES[-1]
    if not (folder/'analysis.json').exists():
        return
    r=read(folder/'analysis.json');ctx=read(folder/'context.json')
    w=np.load(folder/'wave.npz');e=np.load(folder/'stress_envelopes.npz');t=w['time']*1e9
    worst=max((s for s in r['stresses'] if s['group']=='reference'),key=lambda s:s['peak_v'])
    def v(n):return np.zeros_like(t) if n=='0' else w[n.lower()]
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(3,2,figsize=(13,9),layout='constrained')
    event_report=dict(worst=worst,events=[],windows=[])
    for col,term in enumerate(['bd','gb']):
        event=max((s for s in r['stresses'] if s['group']=='reference' and s['terminal']==term),key=lambda s:s['peak_v'])
        device=next(d for d in ctx['stress_devices'] if d['instance']==event['instance'])
        start=np.floor(event['time_ns']/100)*100+1
        m=(t>=start-.1)&(t<=start+2.15)
        for n,label,color in [('XDUT.SAMPLE_INT','Reference reset','#6759a2'),
                               ('XDUT.SEQ_SAMPLE','Bootstrap enable','#288779')]:
            ax[0,col].plot(t[m],v(n)[m],color=color,label=label,lw=1.3)
        ax[0,col].set_ylabel('Control (V)');ax[0,col].legend(fontsize=8)
        ax[0,col].set_title(f'{event["instance"].replace("XDUT.XCDAC.","")}\n|V{term}| max {event["peak_v"]*1000:.3f} mV at {event["time_ns"]:.6f} ns',fontsize=11)
        traces=[('d','Drain / bottom','#c45442'),('g','Gate','#6759a2'),('b','Body','#666666')]
        for terminal,label,color in traces:
            ax[1,col].plot(t[m],v(device['nodes'][terminal])[m],color=color,label=label,lw=1.2,
                          ls='--' if terminal=='b' else '-')
        detail=dict(event=event,device=device)
        if term=='gb':
            gate=device['nodes']['g'].split('.')[-1];bit=gate[3:]
            driver=f'XDUT.XREF.XDRV{bit}.{gate[:3]}DRV'
            ax[1,col].plot(t[m],v(driver)[m],color='#288779',label='Driver before gate R',lw=1.1)
            idx=int(np.argmax(abs(v(device['nodes']['g'])-v(device['nodes']['b']))))
            detail.update(driver_node=driver,driver_v_at_peak=float(v(driver)[idx]),
                          gate_v_at_peak=float(v(device['nodes']['g'])[idx]),
                          drain_v_at_peak=float(v(device['nodes']['d'])[idx]))
            q=v(f'XDUT.XREF.Q{bit}')
            detail.update(reference_bit=bit,q_range_v=[float(q[m].min()),float(q[m].max())],
                          reference_word_before_after=[sum(int(np.interp(x,t,v(f'XDUT.XREF.Q{i}'))>.45)*2**i for i in range(8))
                                                       for x in [start-.1,start+.2]])
        ax[1,col].set_ylabel('Node voltage (V)');ax[1,col].legend(fontsize=8,ncol=2)
        a,b=term;stress=abs(v(device['nodes'][a])-v(device['nodes'][b]))
        ax[2,col].plot(t[m],stress[m],color='#c45442',label=f'|V{term}|',lw=1.4)
        ax[2,col].axhline(.99,color='black',ls='--',lw=1,label='0.99 V screen')
        ax[2,col].set(xlabel='Time (ns)',ylabel=f'|V{term}| (V)',ylim=(.88,max(1.01,event['peak_v']+.005)))
        ax[2,col].legend(fontsize=9)
        for row in range(3):
            ax[row,col].grid(alpha=.2);ax[row,col].set_xlim(start-.1,start+2.15)
            ax[row,col].ticklabel_format(axis='x',useOffset=False)
        event_report['events'].append(detail)
    fig.suptitle('A: reset before sampling | residual bottom undershoot and gate overshoot',fontsize=14)
    fig.supxlabel('TT 0.9 V 27°C | 10 MS/s, continuous 4.501953 MHz sine, −1 dBFS | native MOS/PDK-RC sequencing\nSaved window: 2.398–4.600 µs. Earlier native CMI starts at 501.359 ns. CX, no PVT/MC.',fontsize=9)
    dest=ROOT/'docs/figures/sar8_r4_reset/late_stress.png';fig.savefig(dest,dpi=180);plt.close(fig)
    for lo,hi in [(2500,2505),(4500,4505)]:
        mask=(t>=lo)&(t<=hi);idx=np.flatnonzero(mask)[np.argmax(e['reference'][mask])]
        event_report['windows'].append(dict(window_ns=[lo,hi],reference_peak_v=float(e['reference'][idx]),time_ns=float(t[idx])))
    dump(ROOT/'verification/sar8_r4_reset/late_event.json',event_report)
    print('FOLLOWUP_CURATED',worst)


if __name__=='__main__':main()
