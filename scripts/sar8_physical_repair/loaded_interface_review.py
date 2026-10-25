"""Review completed receiver and input-order controls; never launch a run."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from prepare import ROOT
from analyze import load
from loaded_analyze import VERIFY, resolve
from loaded_review import data

FIG=ROOT/'docs/figures/sar8_physical_repair'


def waveform(run):
    folder,_,_=resolve(run)
    _,w,t,_=load(folder/'derived')
    return w,t


def main():
    summary=dict(scope='Completed two-frame controls only; no baseline adoption',receivers=[],startup=None)
    for corner in ['tt','sscold']:
        run='sar8fix-loaded-both-rx2-'+corner
        if not (VERIFY/(run+'_analysis.json')).exists():continue
        r=data(run);b=data('sar8fix-loaded-both-'+corner);w,t=waveform(run)
        old,bt=waveform(b['run_id'])
        q=[x for x in r['comparisons'] if x['frame']==1][-1]
        bq=[x for x in b['comparisons'] if x['frame']==1][-1]
        at=lambda n,x:float(np.interp(x,t,w[n]))
        outputs={n:at('xdut.'+n,q['write_ns']) for n in ['comp_p','comp_n',
            'xctrl.xtim.x002.n','xctrl.xtim.x003.n','xctrl.xtim.pr','xctrl.xtim.nr','xctrl.xtim.dec']}
        summary['receivers'].append(dict(run_id=run,control=b['run_id'],
            codes=[x['code'] for x in r['frames']],events_pass=r['all_event_counts_pass'],
            failed_pairs=r['failing_pairs'],original_failed_pairs=b['failing_pairs'],
            groups=r['groups'],last_write_raw_and_receiver_v=outputs,
            comparison=r['receiver_control_comparison'],
            last_ref_reset_ns=r['frames'][1]['last_ref_reset_ns'],
            power_uw=r['frames'][1]['supply_reference_average_uw'],
            settling_windows=len(r['settling_estimates']),
            settling_pass=all(x['settle_after_update_ns'] is not None and
                x['deadline_error_mv']<1.7578125 and not x['illegal_gate_states'] for x in r['settling_estimates'])))
        fig,ax=plt.subplots(4,1,figsize=(10,10),sharex=True,layout='constrained')
        for state,ww,tt,qq,color in [('Core receiver',old,bt,bq,'#c85637'),('IO receiver',w,t,q,'#2864a0')]:
            sel=(tt>=qq['clock_ns']-.2)&(tt<=qq['clock_ns']+3.3);x=tt[sel]-qq['clock_ns']
            ax[0].plot(x,ww['xdut.comp_n'][sel],color=color,label=state+' COMP_N')
            ax[0].plot(x,ww['xdut.comp_p'][sel],color=color,ls='--',label=state+' COMP_P')
            ax[3].plot(x,ww['xdut.cmp_clk'][sel],color=color,label=state+' CMP_CLK')
            for a in ax:a.axvline(qq['write_ns']-qq['clock_ns'],color=color,ls=':',lw=1)
        sel=(t>=q['clock_ns']-.2)&(t<=q['clock_ns']+3.3);x=t[sel]-q['clock_ns']
        for n in ['x002.n','x003.n']:ax[1].plot(x,w['xdut.xctrl.xtim.'+n][sel],label=n.upper()+' (IO inverter output)')
        ax[1].axhline(.99,color='#777',ls='--',label='Following core gate-body limit')
        for n in ['pr','nr','dec']:ax[2].plot(x,w['xdut.xctrl.xtim.'+n][sel],label=n.upper()+' (IO receiver)')
        ax[0].set_ylabel('Raw comparator (V)');ax[1].set_ylabel('Core input (V)');ax[2].set_ylabel('Received logic (V)')
        ax[3].set(ylabel='Compare clock (V)',xlabel='Time from each last comparison rising edge (ns)',xlim=(-.2,3.3))
        for a in ax:a.grid(alpha=.2);a.legend(fontsize=8,loc='best',ncol=2)
        fig.suptitle('%s / %.2f V / %d C | actual ADC load, IO reference + N4 comparator\n'%(corner.upper(),r['vdd'],r['temperature_c'])+
            'Only four receiver MOS changed; dotted lines = respective write events\n'+
            '20 ps display; 50 ohm input/reference; ideal external supply/clock; no noise/mismatch/PEX',fontsize=10)
        fig.savefig(FIG/('loaded_receiver_'+corner+'_comparison.png'),dpi=170);plt.close(fig)
    run='sar8fix-loaded-both-rev-sshot'
    if (VERIFY/(run+'_analysis.json')).exists():
        r=data(run);b=data('sar8fix-loaded-both-sshot');w,t=waveform(run);old,bt=waveform(b['run_id'])
        summary['startup']=dict(run_id=run,control=b['run_id'],codes=[x['code'] for x in r['frames']],
            expected=[x['expected'] for x in r['frames']],events_pass=r['all_event_counts_pass'],
            failed_pairs=r['failing_pairs'],held_errors_mv=[x['monitor_held_error_mv'] for x in r['frames']],
            original_held_errors_mv=[x['monitor_held_error_mv'] for x in b['frames']],
            high_input_gate_at_30ns_v=float(np.interp(30,t,w['xdut.xbootn.g'])),
            high_input_gate_at_130ns_v=float(np.interp(130,t,w['xdut.xbootp.g'])))
        fig,ax=plt.subplots(2,1,figsize=(10,6),sharex=True,layout='constrained')
        for label,ww,tt,pin,gate,sign,color in [('Original +.81 V first',old,bt,'vinp','xdut.xbootp.g',1,'#c85637'),
                ('Reversed -.81 V first',w,t,'vinn','xdut.xbootn.g',-1,'#2864a0')]:
            style='-' if sign==1 else '--'
            ax[0].plot(tt,ww[gate]-ww[pin],label=label,color=color,ls=style)
            # Polarity normalized, not an absolute magnitude: preserve error direction.
            target=np.where(tt<100.25,.81,-.81)
            err=sign*(ww['xdut.topp']-ww['xdut.topn'])-target
            ax[1].plot(tt,err*1000,label=label,color=color,ls=style)
        ax[0].set(ylabel='Initially high side\nG - VIN (V)',ylim=(-.95,.05))
        ax[0].axhline(0,color='#777',ls=':',lw=1)
        ax[1].axhspan(-1.7578125,1.7578125,color='#368c85',alpha=.12,label='+/- 0.25 LSB')
        ax[1].set(ylabel='Polarity-normalized\nacquisition error (mV)',ylim=(-14,3),xlabel='Time (ns)',xlim=(0,41.8))
        for a in ax:a.grid(alpha=.2);a.legend(fontsize=8)
        fig.suptitle('SS / 0.81 V / 125 C | first acquisition, same DUT and clock\n'+
            'Only input polarity order swapped; 50 ohm inputs/reference; DC-start SAMPLE high\n'+
            '20 ps display; no power ramp, noise, mismatch or PEX',fontsize=10)
        fig.savefig(FIG/'loaded_startup_polarity_control.png',dpi=170);plt.close(fig)
    (VERIFY/'loaded_interface_review.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
