"""Compare rise-only candidates with complete native metrics, bounded CSV reads."""
import csv,gzip,json
from array import array
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from setup import W,ROOT,write

RUNS={50:'cmpdesign-rise50-a4-review-v1',100:'cmpdesign-rise100-a4-ff-hot-v1',200:'cmpdesign-rise200-a4-ff-hot-v1'}

def main():
    data={};summary={};colors={50:'#456f9e',100:'#d17a34',200:'#319581'}
    for ps,run in RUNS.items():
        p=ROOT/'output/managed_execution/runs'/run/'collected/derived'
        result=json.loads((p/'result.json').read_text())
        src='cmpdesign-precharge-a4-ff-hot-v1' if ps==50 else run
        cfg=json.loads((W/'testbenches'/src/'measure.json').read_text())
        names=['time','ck','pa4_held','na4_held','opa4_held','ona4_held','xa4_held.net1','xa4_held.net2','xa4_held.lp','xa4_held.ln']
        buffers={n:array('d') for n in names}
        with gzip.open(p/'wave.csv.gz','rt') as f:
            reader=csv.reader(f);header=next(reader);indices=[header.index(n) for n in names]
            for row in reader:
                for n,i in zip(names,indices):buffers[n].append(float(row[i]))
        d={n:np.frombuffer(b,dtype='d') for n,b in buffers.items()}
        data[ps]=(result,d,cfg);summary[ps]={'run_id':run}
        for mode in ['held','driven']:
            c=result['contexts']['A4_'+mode]
            out={k:c[k] for k in ['max_decision_s','max_reset_s','all_correct','all_reset','peak_terminal_V','mean_comparator_supply_W','max_residual_V','screens']}
            for field in ['full_edge_diff_kick_V','full_edge_cm_kick_V','max_diff_kick_V','max_cm_kick_V']:
                idx=max(range(len(c['rows'])),key=lambda j:c['rows'][j][field])
                out[field]=c['rows'][idx][field];out[field+'_event_index']=idx
            for metric in ['decision','reset']:
                row=max(c['rows'],key=lambda r:r[metric+'_s'])
                out[metric+'_sample_bracket_s']=row[metric+'_since_s']-row[metric+'_last_bad_s']
            for group,nodes in [('input_nodes',['net1','net2']),('latch_nodes',['lp','ln'])]:
                pulses=[x for x in c['startup_pulses'] if x['node'] in nodes]
                out[group]={'worst_peak_pulse':max(pulses,key=lambda x:x['peak_V']) if pulses else None,'longest_pulse':max(pulses,key=lambda x:x['duration_s']) if pulses else None}
            out['worst_terminal_pairs']=sorted(c['terminal_pairs'].items(),key=lambda x:x[1]['peak_V'],reverse=True)[:4]
            out['reset_latch_peak_V']=max(c['phase_node_peaks'][k]['peak_V'] for k in ['reset:lp','reset:ln'])
            summary[ps][mode]=out
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    condition='FF | 0.99 V | 125 C | hold 1.28 pF/side | output 6.1 fF/side | ideal sources'
    fig,axes=plt.subplots(3,2,figsize=(12,9))
    selected={}
    for col,group in enumerate(['input_nodes','latch_nodes']):
        case=max(RUNS,key=lambda ps:summary[ps]['held'][group]['worst_peak_pulse']['peak_V'])
        p=summary[case]['held'][group]['worst_peak_pulse'];idx=p['event_index'];node=p['node']
        edge=data[case][2]['events'][idx]['clock50'];selected[group]={'event_index':idx,'node':node,'clock50_s':edge}
        for ps,(r,d,cfg) in data.items():
            t=d['time'];mask=(t>=edge-125e-12)&(t<=edge+400e-12);x=(t[mask]-edge)*1e12
            axes[0,col].plot(x,d['ck'][mask],color=colors[ps],label='%d ps'%ps)
            axes[1,col].plot(x,(d['xa4_held.'+node][mask]-.99)*1e3,color=colors[ps],label='%d ps'%ps)
            op='opa4_held' if cfg['events'][idx]['diff']>0 else 'ona4_held'
            axes[2,col].plot(x,d[op][mask],color=colors[ps],label='%d ps'%ps)
        axes[0,col].set_title('%s startup | clock50 %.3f ns'%(node,edge*1e9))
        axes[0,col].set_ylabel('Clock (V)');axes[1,col].set_ylabel(node+' minus VDD (mV)');axes[2,col].set_ylabel('Correct output (V)');axes[2,col].set_xlabel('Time from FIXED clock50 (ps)')
        axes[1,col].axhline(0,color='gray',ls=':');axes[1,col].set_ylim(-15,12)
        axes[2,col].axhline(.8*.99,color='gray',ls=':')
        for ax in axes[:,col]:ax.axvline(0,color='gray',ls=':');ax.grid(alpha=.18);ax.legend();ax.set_xlim(-125,250)
    fig.suptitle('A4: clock rise 50 / 100 / 200 ps; clock50 and falling edge unchanged\n'+condition+'\nM8/M9 & M2/M4 multi4; M3/M5 W100nm L30nm multi1; no noise/mismatch/PEX',fontsize=10)
    fig.tight_layout(rect=[0,0,1,.90]);fig.savefig(W/'figures/rise_sweep_startup.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(12,7))
    for col,field in enumerate(['full_edge_diff_kick_V','full_edge_cm_kick_V']):
        case=max(RUNS,key=lambda ps:summary[ps]['held'][field]);idx=summary[case]['held'][field+'_event_index']
        edge=data[case][2]['events'][idx]['clock50']
        for ps,(r,d,cfg) in data.items():
            t=d['time'];mask=(t>=edge-150e-12)&(t<edge+1.475e-9);x=(t[mask]-edge)*1e9
            vp=d['pa4_held'][mask];vn=d['na4_held'][mask];e=cfg['events'][idx]
            dm0=r['contexts']['A4_held']['rows'][idx]['pre_eval_diff_V']
            axes[0,col].plot(x,(vp-vn-dm0)*1e3,color=colors[ps],label='%d ps'%ps)
            axes[1,col].plot(x,((vp+vn)/2-e['cm'])*1e3,color=colors[ps],label='%d ps'%ps)
        axes[0,col].set_title(('Worst DM' if col==0 else 'Worst CM')+' matched event | clock50 %.3f ns'%(edge*1e9))
        axes[0,col].set_ylabel('Input DM change (mV)');axes[1,col].set_ylabel('Input CM change (mV)');axes[1,col].set_xlabel('Time from FIXED clock50 (ns)')
        for ax in axes[:,col]:ax.axvline(0,color='gray',ls=':');ax.axhline(0,color='gray',ls=':');ax.grid(alpha=.18);ax.legend()
    fig.suptitle('A4 held-input kickback; rise only 50 / 100 / 200 ps\n'+condition+'\nPeaks: ALL native samples from rise START to before reset. No noise/mismatch/PEX.',fontsize=10)
    fig.tight_layout(rect=[0,0,1,.89]);fig.savefig(W/'figures/rise_sweep_kickback.png',dpi=150);plt.close(fig)
    summary['selected_events']=selected
    summary['definitions']={'rise':'0-100%, centered on original clock50; fall edge unchanged','pulse':'continuous node above0.99V interval during evaluation; native threshold interpolation; peak pulse and longest separately','full_edge_kick':'rise start to before fixed fall start; DM versus measured pre-rise DM; CM versus nominal','old_kick':'clock50 to before fall start retained for continuity','timing':'native stable first-good sample upper bound from fixed clock50'}
    write(W/'results/rise_sweep_comparison.json',json.dumps(summary,indent=2)+'\n')
    print(json.dumps({ps:summary[ps]['held'] for ps in RUNS},indent=2))

if __name__=='__main__':main()
