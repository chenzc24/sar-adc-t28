"""Final native baseline/2k comparison; local collected data only."""
from pathlib import Path
import json
import numpy as np
import analyze

HERE=Path(__file__).resolve().parent
P='xdut.xu19.xff.'


def intervals(t,values,limit):
    out=[]
    for j in range(1,len(t)):
        a,b=float(values[j-1]),float(values[j]);cuts=[0.,1.]
        if a!=b:cuts+= [(v-a)/(b-a) for v in [-limit,limit] if 0<(v-a)/(b-a)<1]
        cuts.sort()
        for left,right in zip(cuts,cuts[1:]):
            if abs(a+(b-a)*(left+right)/2)<=limit:continue
            start=float(t[j-1]+(t[j]-t[j-1])*left);stop=float(t[j-1]+(t[j]-t[j-1])*right)
            if out and abs(start-out[-1]['stop_s'])<1e-22:
                out[-1].update(stop_s=stop,stop_native_bracket_s=[float(t[j-1]),float(t[j])])
            else:out.append(dict(start_s=start,stop_s=stop,start_native_bracket_s=[float(t[j-1]),float(t[j])],stop_native_bracket_s=[float(t[j-1]),float(t[j])]))
    return out


def main():
    data={};stats={}
    for case in ['baseline','rck2k']:
        cfg,r,a,idx,proof=analyze.load(case)
        detail=json.loads((HERE/case/'current_analysis.json').read_text())
        data[case]=(a,idx);t=a[:,0];front=(t>=5e-9)&(t<=5.06e-9)
        vds=a[:,idx[P+'mq_x']]-a[:,idx[P+'net176']]
        edges={n:[e for e in detail['actual_internal_edges'][n] if 4.9e-9<e['time_s']<5.1e-9][0] for n in detail['actual_internal_edges']}
        stats[case]=dict(proof=proof,native_points=len(t),strict_failed_pairs=sum(x['max_abs_v']>x['limit_abs_v'] for x in r['full_history_voltage_stress'].values()),
            MM64_peak=r['full_history_voltage_stress']['XDUT.XU19.XFF.MM64_VDS'],
            front_net176_min_v=float(a[front,idx[P+'net176']].min()),
            falling_event_edges=edges,MM64_over_limit_intervals=intervals(t,vds,.99),
            maximum_six_node_KCL_residual_A=max(x['max_abs_a'] for x in r['node_kcl'].values()),
            stable_hold_pass=r['storage_observations']['stable_hold_observation_pass'],Q_edge_patterns_pass=r['storage_observations']['clean_expected_Q_edge_patterns'],
            phase5_charge=next(x for x in detail['phase_charge_integrals'] if x['label']=='phase5'))
    b,c=stats['baseline'],stats['rck2k']
    delta=dict(MM64_peak_difference_v=c['MM64_peak']['max_abs_v']-b['MM64_peak']['max_abs_v'],
        MM64_peak_time_difference_s=c['MM64_peak']['max_abs_time_s']-b['MM64_peak']['max_abs_time_s'],
        edge_slew_change_percent={n:(c['falling_event_edges'][n]['slew_10_90_s']/b['falling_event_edges'][n]['slew_10_90_s']-1)*100 for n in b['falling_event_edges']})
    analyze.dump(HERE/'comparison.json',dict(cases=stats,difference=delta,all_waveform_time_axes_original=True,
        no_scope_or_model_adoption=True,no_unique_intrinsic_current_attribution=True,whole_ADC_qualified=None))
    plots(data)
    print('NATIVE_DFF_PAIR_COMPARISON_COMPLETE',json.dumps(delta,sort_keys=True))


def plots(data):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    windows=[(4.995,5.06,'5 ns clock fall'),(5.06,5.985,'Negative-state recovery'),(5.985,6.05,'6 ns next clock')]
    colors={'baseline':'#256b9b','rck2k':'#d76c26'}
    fig,axes=plt.subplots(4,3,figsize=(14,10),sharex='col',layout='constrained')
    for col,(left,right,title) in enumerate(windows):
        for case,(a,idx) in data.items():
            t=a[:,0]*1e9;mask=(t>=left)&(t<=right);ts=t[mask]
            style='-' if case=='baseline' else '--';label='Baseline' if case=='baseline' else 'RCK = 2k'
            axes[0,col].plot(ts,a[mask,idx['xdut.u19_ck']],color=colors[case],ls=style,label=label)
            for node,color in [('clkb','#00857c'),('clkbb','#8257a6'),('mq','#a77c13')]:axes[1,col].plot(ts,a[mask,idx[P+node]],color=color,ls=style,label=node+' / '+label)
            axes[2,col].plot(ts,a[mask,idx[P+'net176']]*1e3,color=colors[case],ls=style,label=label)
            axes[3,col].plot(ts,a[mask,idx[P+'mq_x']]-a[mask,idx[P+'net176']],color=colors[case],ls=style,label=label)
        for row,label in enumerate(['CP (V)','Internal gates (V)','net176 (mV)','MM64 VDS (V)']):
            ax=axes[row,col];ax.set_ylabel(label);ax.grid(alpha=.18);ax.set_xlim(left,right)
            if row in [0,1]:ax.set_ylim(-.06,1.06)
            if row==3:ax.axhline(.99,color='#555555',ls=':',lw=1,label='0.99 V screen')
            elif row==2:ax.axhline(0,color='#777777',lw=.6)
        axes[0,col].set_title(title);axes[-1,col].set_xlabel('Original time (ns)')
    axes[0,0].legend(fontsize=8)
    handles,labels=axes[1,0].get_legend_handles_labels()
    axes[1,1].legend(handles,labels,fontsize=7,ncol=2,loc='center')
    axes[3,0].legend(fontsize=8)
    fig.suptitle('DFF input filtering: small CP change, internal clock edges largely retained',fontsize=14)
    fig.supxlabel('FF | 0.99 V | -40 C | native DFCNQD1 + original first-hop load | ideal supplies/commands | no noise, mismatch or PEX\nOnly RCK changes: direct connection -> ideal 2k. Native samples, original time; no phase alignment.',fontsize=9)
    fig.savefig(HERE/'paired_timing.png',dpi=170);plt.close(fig)

    fig,axes=plt.subplots(3,3,figsize=(14,9),sharex='col',layout='constrained')
    portcolors=['#256b9b','#dc8b22','#00857c','#b34a64']
    for col,(left,right,title) in enumerate(windows):
        scale=1e9 if col==1 else 1e6;unit='nA' if col==1 else 'uA'
        for row,device in enumerate([64,65,66]):
            ax=axes[row,col]
            for case,(a,idx) in data.items():
                t=a[:,0]*1e9;mask=(t>=left)&(t<=right)
                for port,color in enumerate(portcolors,1):ax.plot(t[mask],a[mask,idx[P+'mm'+str(device)+':'+str(port)]]*scale,color=color,ls='-' if case=='baseline' else '--',lw=1.1)
            ax.set_ylabel('MM'+str(device)+' I ('+unit+')');ax.grid(alpha=.18);ax.axhline(0,color='#777777',lw=.6);ax.set_xlim(left,right)
        axes[0,col].set_title(title);axes[-1,col].set_xlabel('Original time (ns)')
    handles=[Line2D([0],[0],color=c,label=p) for c,p in zip(portcolors,'DGSB')]
    handles += [Line2D([0],[0],color='#333333',ls=style,label=case) for style,case in [('-','Baseline'),('--','RCK = 2k')]]
    axes[0,0].legend(handles=handles,loc='upper right',ncol=2,fontsize=8,framealpha=.85)
    fig.suptitle('MM64 / MM65 / MM66: all four native terminal currents',fontsize=14)
    fig.supxlabel('FF | 0.99 V | -40 C | same native cell and load | ideal supply/commands | no noise, mismatch or PEX\nPositive into device; middle column uses nA. Total currents include model charge terms; no intrinsic decomposition.',fontsize=9)
    fig.savefig(HERE/'paired_currents.png',dpi=170);plt.close(fig)


if __name__=='__main__':main()
