"""Compare independent sizes with clocks frozen, including full native stress."""
import json,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from setup import W,write
from review_fall import read
from review_precharge import pulse

RUNS={'Baseline':'cmpdesign-r200-f500-a4-ff-hot-v1','Precharge x2':'cmpdesign-edge-b2-ff-hot-v1','Input x2':'cmpdesign-edge-i2-ff-hot-v1'}
STEM='edge_sizes'
if '--combined' in sys.argv:
    RUNS['Combined']='cmpdesign-edge-b2i2-ff-hot-v1'
    STEM='edge_combo'
if '--latch8' in sys.argv:
    RUNS={'Baseline':'cmpdesign-edge-b2i2-ff-hot-v1','Latch x8':'cmpdesign-combo-a8-ff-hot-v1'}
    STEM='combo_a8'
def main():
    data={};summary={};colors=dict(zip(RUNS,['#456f9e','#d17a34','#319581','#a64a87']))
    for label,run in RUNS.items():
        r,d,cfg=read(label,run);data[label]=(r,d,cfg);summary[label]={'run_id':run}
        for mode in ['held','driven']:
            c=r['contexts']['A4_'+mode]
            out={k:c[k] for k in ['max_decision_s','max_reset_s','all_correct','all_reset','peak_terminal_V','mean_comparator_supply_W','max_residual_V','screens']}
            out['reset_from_edge_start_s']=c['max_reset_s']+250e-12
            out['internal_error_at_reset_0p5ns_V']=max(x['internal_reset_max_error_V'] for x in c['rows'])
            for f in ['full_edge_diff_kick_V','full_edge_cm_kick_V']:out[f]=max(x[f] for x in c['rows'])
            for group,collection,nodes in [('reset_latch','reset_pulses',['lp','ln']),('reset_input','reset_pulses',['net1','net2']),('startup_latch','startup_pulses',['lp','ln']),('startup_input','startup_pulses',['net1','net2'])]:
                pulses=[p for p in c[collection] if p['node'] in nodes]
                out[group]={'worst_peak_pulse':max(pulses,key=lambda x:x['peak_V']) if pulses else None,'longest_pulse':max(pulses,key=lambda x:x['duration_s']) if pulses else None}
            out['worst_terminal_pairs']=sorted(c['terminal_pairs'].items(),key=lambda x:x[1]['peak_V'],reverse=True)[:6]
            summary[label][mode]=out
        # All update windows are within the reducer's full-native fall50+800ps export.
        windows=[];t=d['time']
        for idx,e in enumerate(cfg['events']):
            mask=(t>=e['t']+2.05e-9)&(t<=e['t']+2.3e-9)
            for n in ['net1','net2']:
                q=pulse(t[mask],d['xa4_held.'+n][mask],.99)
                q.update(node=n,event_index=idx)
                if q.get('window_clipped'):raise ValueError('input pulse export clipped')
                windows.append(q)
        summary[label]['held']['input_update']={'worst_peak_pulse':max(windows,key=lambda x:x['peak_V']),'windows':windows}
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    condition='FF, 0.99 V, 125 C | rise/fall 200/500 ps, fixed edge50 | ideal sources\nHeld input 1.28 pF/side; output 6.1 fF/side; no SAR receiver, noise, mismatch or PEX'
    groups=['startup_input','reset_input','reset_latch'] if STEM!='combo_a8' else ['startup_input','startup_latch','reset_input','reset_latch']
    fig,ax=plt.subplots(3,len(groups),figsize=(5*len(groups),10),layout='constrained');selected={}
    for col,group in enumerate(groups):
        case=max(RUNS,key=lambda k:summary[k]['held'][group]['worst_peak_pulse']['peak_V'] if summary[k]['held'][group]['worst_peak_pulse'] else -1)
        p=summary[case]['held'][group]['worst_peak_pulse'];idx=p['event_index'];node=p['node'];reset=group.startswith('reset')
        center=data[case][2]['events'][idx]['fall50' if reset else 'clock50'];selected[group]=dict(event_index=idx,node=node,edge50_s=center)
        for tag,(r,d,cfg) in data.items():
            t=d['time'];m=(t>=center-300e-12)&(t<=center+400e-12);x=(t[m]-center)*1e12
            ax[0,col].plot(x,d['ck'][m],color=colors[tag],label=tag)
            ax[1,col].plot(x,(d['xa4_held.'+node][m]-.99)*1e3,color=colors[tag],label=tag)
            op='opa4_held' if cfg['events'][idx]['diff']>0 else 'ona4_held'
            ax[2,col].plot(x,d[op][m],color=colors[tag])
        ax[0,col].set_title(group+' '+node+' | %.3f ns'% (center*1e9))
        ax[0,col].set_ylabel('Clock (V)');ax[1,col].set_ylabel(node+' - VDD (mV)');ax[2,col].set_ylabel('Output (V)');ax[2,col].set_xlabel('Time from edge50 (ps)')
        ax[1,col].axhline(0,color='gray',ls=':');ax[1,col].set_ylim(-8, max(5,(p['peak_V']-.99)*1e3*1.25))
        ax[0,col].legend(fontsize=8);ax[1,col].legend(fontsize=8)
        for a in ax[:,col]:a.axvline(0,color='gray',ls=':');a.grid(alpha=.15);a.set_xlim(-300,400)
    title='M2/M4 x4 versus x8 | M3/M5 & M8/M9 fixed x2' if STEM=='combo_a8' else 'Precharge x2 = M3/M5; Input x2 = M8/M9'+('; Combined = both' if STEM=='edge_combo' else '; independent changes')
    fig.suptitle(title+'\n'+condition,fontsize=11)
    fig.savefig(W/'figures'/(STEM+'_start_reset.png'),dpi=150);plt.close(fig)
    fig,ax=plt.subplots(3,1,figsize=(10,8),layout='constrained')
    for tag,(r,d,cfg) in data.items():
        m=(d['time']>=80.05e-9)&(d['time']<=80.3e-9);x=(d['time'][m]-80.1e-9)*1e12
        ax[0].plot(x,d['na4_held'][m],label=tag,color=colors[tag]);ax[1].plot(x,(d['xa4_held.net2'][m]-.99)*1e3,label=tag,color=colors[tag]);ax[2].plot(x,(d['xa4_held.net1'][m]-.99)*1e3,label=tag,color=colors[tag])
    for a in ax:a.legend();a.grid(alpha=.15);a.axvspan(0,50,color='#eee4d0',alpha=.4)
    ax[0].set_ylabel('VINN (V)');ax[1].set_ylabel('net2 - VDD (mV)');ax[2].set_ylabel('net1 - VDD (mV)');ax[2].set_xlabel('Time from80.10ns input update (ps)')
    for a in ax[1:]:a.axhline(0,color='gray',ls=':')
    fig.suptitle('Same input update, clock remains low | '+title+'\n'+condition,fontsize=10)
    fig.savefig(W/'figures'/(STEM+'_input_update.png'),dpi=150);plt.close(fig)
    summary['selected_events']=selected
    write(W/'results'/(STEM+'_comparison.json'),json.dumps(summary,indent=2)+'\n')
    for tag in RUNS:
        c=summary[tag]['held'];brief={k:c[k] for k in ['max_decision_s','max_reset_s','reset_from_edge_start_s','peak_terminal_V','mean_comparator_supply_W','full_edge_diff_kick_V','full_edge_cm_kick_V','all_correct','all_reset','screens','worst_terminal_pairs']}
        for g in ['startup_input','startup_latch','reset_input','reset_latch','input_update']:brief[g]=c[g]['worst_peak_pulse']
        print(tag,json.dumps(brief,indent=2))
if __name__=='__main__':main()
