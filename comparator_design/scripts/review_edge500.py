"""Compare fixed-size A4 four rise/fall cases with native timing and stress."""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from setup import W,write
from review_fall import read

RUNS={'200/200':'cmpdesign-rise200-fall200-a4-ff-hot-v1','500/200':'cmpdesign-r500-f200-a4-ff-hot-v1','200/500':'cmpdesign-r200-f500-a4-ff-hot-v1','500/500':'cmpdesign-r500-f500-a4-ff-hot-v1'}

def main():
    data={};summary={};colors=dict(zip(RUNS,['#456f9e','#d17a34','#8e62a9','#319581']))
    for tag,run in RUNS.items():
        r,d,cfg=read(tag,run);data[tag]=(r,d,cfg);summary[tag]={'run_id':run}
        rp,fp=map(int,tag.split('/'))
        for mode in ['held','driven']:
            c=r['contexts']['A4_'+mode]
            out={k:c[k] for k in ['max_decision_s','max_reset_s','all_correct','all_reset','peak_terminal_V','mean_comparator_supply_W','max_residual_V','screens']}
            out['reset_from_edge_start_s']=c['max_reset_s']+fp*1e-12/2
            out['decision_from_edge_start_s']=c['max_decision_s']+rp*1e-12/2
            out['internal_error_at_reset_0p5ns_V']=max(x['internal_reset_max_error_V'] for x in c['rows'])
            for field in ['full_edge_diff_kick_V','full_edge_cm_kick_V']:
                out[field]=max(x[field] for x in c['rows'])
            for metric in ['decision','reset']:
                row=max(c['rows'],key=lambda x:x[metric+'_s'])
                out[metric+'_sample_bracket_s']=row[metric+'_since_s']-row[metric+'_last_bad_s']
            for group,collection,nodes in [('reset_latch','reset_pulses',['lp','ln']),('reset_input','reset_pulses',['net1','net2']),('startup_latch','startup_pulses',['lp','ln']),('startup_input','startup_pulses',['net1','net2'])]:
                pulses=[p for p in c[collection] if p['node'] in nodes]
                out[group]={'worst_peak_pulse':max(pulses,key=lambda x:x['peak_V']) if pulses else None,'longest_pulse':max(pulses,key=lambda x:x['duration_s']) if pulses else None}
            out['worst_terminal_pairs']=sorted(c['terminal_pairs'].items(),key=lambda x:x[1]['peak_V'],reverse=True)[:4]
            out['reset_all_node_peaks']={k:v for k,v in c['phase_node_peaks'].items() if k.startswith('reset:')}
            summary[tag][mode]=out
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    condition='FF | 0.99 V | 125 C | hold 1.28 pF/side | output 6.1 fF/side | ideal sources'
    fig,axes=plt.subplots(3,2,figsize=(13,9));selected={}
    for col,group in enumerate(['startup_input','reset_latch']):
        case=max(RUNS,key=lambda k:summary[k]['held'][group]['worst_peak_pulse']['peak_V'])
        p=summary[case]['held'][group]['worst_peak_pulse'];idx=p['event_index'];node=p['node'];reset=group.startswith('reset')
        edge=data[case][2]['events'][idx]['fall50' if reset else 'clock50']
        selected[group]={'event_index':idx,'node':node,'edge50_s':edge}
        for tag,(r,d,cfg) in data.items():
            t=d['time'];mask=(t>=edge-300e-12)&(t<=edge+500e-12);x=(t[mask]-edge)*1e12
            axes[0,col].plot(x,d['ck'][mask],color=colors[tag],label=tag+' ps')
            axes[1,col].plot(x,(d['xa4_held.'+node][mask]-.99)*1e3,color=colors[tag],label=tag+' ps')
            op='opa4_held' if cfg['events'][idx]['diff']>0 else 'ona4_held'
            axes[2,col].plot(x,d[op][mask],color=colors[tag],label=tag+' ps')
        axes[0,col].set_title(node+(' reset | fall50 ' if reset else ' startup | rise50 ')+'%.3f ns'%(edge*1e9))
        axes[0,col].set_ylabel('Clock (V)');axes[1,col].set_ylabel(node+' minus VDD (mV)');axes[2,col].set_ylabel(('Resetting' if reset else 'Decision')+' output (V)');axes[2,col].set_xlabel('Time from FIXED edge50 (ps)')
        axes[1,col].axhline(0,color='gray',ls=':');axes[1,col].set_ylim(-10,8 if reset else 3)
        axes[2,col].axhline((.2 if reset else .8)*.99,color='gray',ls=':')
        for ax in axes[:,col]:ax.axvline(0,color='gray',ls=':');ax.grid(alpha=.18);ax.set_xlim(-300,400)
        axes[0,col].legend(ncol=2,fontsize=8);axes[1,col].legend(ncol=2,fontsize=8)
    fig.suptitle('A4 clock edges to 500 ps | legends = rise / fall (0-100%); edge50 fixed\n'+condition+'\nM8/M9 & M2/M4 multi4; M3/M5 W100nm L30nm multi1; no noise/mismatch/PEX',fontsize=10)
    fig.tight_layout(rect=[0,0,1,.92]);fig.subplots_adjust(top=.86)
    fig.savefig(W/'figures/edge500_start_reset.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(3,1,figsize=(10,7));edge=data['200/200'][2]['events'][6]['fall50']
    for tag,(r,d,cfg) in data.items():
        t=d['time'];mask=(t>=edge-300e-12)&(t<=edge+800e-12);x=(t[mask]-edge)*1e9
        axes[0].plot(x,d['ck'][mask],color=colors[tag],label=tag+' ps')
        axes[1].plot(x,d['na4_held'][mask],color=colors[tag])
        axes[2].plot(x,(d['xa4_held.net2'][mask]-.99)*1e3,color=colors[tag])
    axes[0].set_ylabel('Clock (V)');axes[1].set_ylabel('Held VINN (V)');axes[2].set_ylabel('net2 minus VDD (mV)');axes[2].set_ylim(-10,7);axes[2].set_xlabel('Time from fall50 = 79.525 ns (ns)')
    for ax in axes:ax.axvline(0,color='gray',ls=':');ax.axvspan(.575,.625,color='#eee4d0',alpha=.7);ax.grid(alpha=.18)
    axes[0].legend(ncol=2);axes[2].axhline(0,color='gray',ls=':')
    fig.suptitle('Clock reset versus next input update at80.10-80.15ns (shaded)\n'+condition+'\nA4 fixed-size | legend rise/fall | no noise/mismatch/PEX',fontsize=10)
    fig.tight_layout(rect=[0,0,1,.91]);fig.subplots_adjust(top=.84)
    fig.savefig(W/'figures/edge500_next_input.png',dpi=150);plt.close(fig)
    summary['selected_events']=selected
    summary['definitions']={'edges':'0-100%, centered on original edge50','reset_pulse':'actual fall_start to fall50+0.5ns; native above0.99V pulse; later input update excluded','timing':'stable first-good native sample; decision from rise50, reset from fall50 with reset evaluation beginning at actual fall_start','negative_reset':'means output met reset threshold before fall50; from-start time also given','scope':'FF hot only; all15MOS terminal pairs across400ns; no new baseline'}
    write(W/'results/edge500_comparison.json',json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:summary[k]['held'] for k in RUNS},indent=2))

if __name__=='__main__':main()
