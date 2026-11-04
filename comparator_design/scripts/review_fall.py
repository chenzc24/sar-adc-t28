"""Fixed rise200, native fall50/100/200 comparison and reset waveform overlay."""
import csv,gzip,json
from array import array
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from setup import W,ROOT,write

RUNS={50:'cmpdesign-fall50-a4-review-v1',100:'cmpdesign-rise200-fall100-a4-ff-hot-v1',200:'cmpdesign-rise200-fall200-a4-ff-hot-v1'}

def read(ps,run):
    col=ROOT/'output/managed_execution/runs'/run/'collected/derived'
    r=json.loads((col/'result.json').read_text())
    src='cmpdesign-rise200-a4-ff-hot-v1' if ps==50 else run
    cfg=json.loads((W/'testbenches'/src/'measure.json').read_text())
    names=['time','ck','pa4_held','na4_held','opa4_held','ona4_held']+['xa4_held.'+n for n in ['net1','net2','lp','ln']]
    buf={n:array('d') for n in names}
    with gzip.open(col/'wave.csv.gz','rt') as f:
        rows=csv.reader(f);head=next(rows);ids=[head.index(n) for n in names]
        for row in rows:
            for n,i in zip(names,ids):buf[n].append(float(row[i]))
    return r,{n:np.frombuffer(v,dtype='d') for n,v in buf.items()},cfg

def main():
    data={};summary={};colors={50:'#456f9e',100:'#d17a34',200:'#319581'}
    for ps,run in RUNS.items():
        r,d,cfg=read(ps,run);data[ps]=(r,d,cfg);summary[ps]={'run_id':run}
        for mode in ['held','driven']:
            c=r['contexts']['A4_'+mode]
            out={k:c[k] for k in ['max_decision_s','max_reset_s','all_correct','all_reset','peak_terminal_V','mean_comparator_supply_W','max_residual_V','screens']}
            out['internal_error_at_reset_0p5ns_V']=max(x['internal_reset_max_error_V'] for x in c['rows'])
            out['reset_from_edge_start_s']=c['max_reset_s']+ps*1e-12/2
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
            summary[ps][mode]=out
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    condition='FF | 0.99 V | 125 C | hold 1.28 pF/side | output 6.1 fF/side | ideal sources'
    fig,axes=plt.subplots(3,2,figsize=(12,9));selected={}
    for col,group in enumerate(['reset_latch','startup_input']):
        case=max(RUNS,key=lambda ps:summary[ps]['held'][group]['worst_peak_pulse']['peak_V'])
        p=summary[case]['held'][group]['worst_peak_pulse'];idx=p['event_index'];node=p['node'];reset=group.startswith('reset')
        edge=data[case][2]['events'][idx]['fall50' if reset else 'clock50']
        selected[group]={'event_index':idx,'node':node,'edge50_s':edge}
        for ps,(r,d,cfg) in data.items():
            t=d['time'];mask=(t>=edge-125e-12)&(t<=edge+300e-12);x=(t[mask]-edge)*1e12
            label='fall %d ps'%ps
            axes[0,col].plot(x,d['ck'][mask],color=colors[ps],label=label)
            axes[1,col].plot(x,(d['xa4_held.'+node][mask]-.99)*1e3,color=colors[ps],label=label)
            # For reset, show the previously high output (both must reset low).
            op='opa4_held' if cfg['events'][idx]['diff']>0 else 'ona4_held'
            axes[2,col].plot(x,d[op][mask],color=colors[ps],label=label)
        axes[0,col].set_title(('%s reset | fall50 ' if reset else '%s startup | rise50 ')%(node)+'%.3f ns'%(edge*1e9))
        axes[0,col].set_ylabel('Clock (V)');axes[1,col].set_ylabel(node+' minus VDD (mV)');axes[2,col].set_ylabel(('Resetting' if reset else 'Decision')+' output (V)')
        axes[2,col].set_xlabel('Time from FIXED edge50 (ps)')
        axes[1,col].axhline(0,color='gray',ls=':');axes[1,col].set_ylim(-10,12 if reset else 3)
        axes[2,col].axhline((.2 if reset else .8)*.99,color='gray',ls=':')
        for ax in axes[:,col]:ax.axvline(0,color='gray',ls=':');ax.grid(alpha=.18);ax.legend();ax.set_xlim(-125,250)
    fig.suptitle('A4 fixed rise 200 ps; only fall 50 / 100 / 200 ps; all edge50 times unchanged\n'+condition+'\nM8/M9 & M2/M4 multi4; M3/M5 W100nm L30nm multi1; no noise/mismatch/PEX',fontsize=10)
    fig.tight_layout(rect=[0,0,1,.92]);fig.subplots_adjust(top=.86)
    fig.savefig(W/'figures/fall_sweep_reset.png',dpi=150);plt.close(fig)
    # Full reset-to-next-input window to identify any remaining global stress.
    fig,axes=plt.subplots(3,1,figsize=(10,7));edge=data[50][2]['events'][6]['fall50']
    for ps,(r,d,cfg) in data.items():
        t=d['time'];mask=(t>=edge-125e-12)&(t<=edge+800e-12);x=(t[mask]-edge)*1e9
        axes[0].plot(x,d['ck'][mask],color=colors[ps],label='fall %d ps'%ps)
        axes[1].plot(x,d['na4_held'][mask],color=colors[ps])
        axes[2].plot(x,(d['xa4_held.net2'][mask]-.99)*1e3,color=colors[ps])
    axes[0].set_ylabel('Clock (V)');axes[1].set_ylabel('Held VINN (V)');axes[2].set_ylabel('net2 minus VDD (mV)');axes[2].set_ylim(-15,10);axes[2].set_xlabel('Time from fall50 = 79.525 ns (ns)')
    for ax in axes:ax.axvline(0,color='gray',ls=':');ax.axvspan(.575,.625,color='#eee4d0',alpha=.7);ax.grid(alpha=.18)
    axes[0].legend();axes[2].axhline(0,color='gray',ls=':')
    fig.suptitle('Separate clock reset from next input update at 80.10-80.15 ns (shaded)\n'+condition+'\nA4 rise200 fixed; no noise/mismatch/PEX',fontsize=10)
    fig.tight_layout(rect=[0,0,1,.91]);fig.subplots_adjust(top=.84)
    fig.savefig(W/'figures/fall_sweep_next_input.png',dpi=150);plt.close(fig)
    summary['selected_events']=selected
    summary['definitions']={'fall':'0-100%, centered on fixed fall50; rise200 unchanged','reset_pulse':'fall_start to fall50+0.5ns; continuous above0.99V, native interpolated; later input-update event excluded','peak_vs_longest':'reported independently','timing':'stable first-good native sample from original edge50; evaluate ends at actual fall_start','full_terminal':'all15 MOS six pair differences over complete400ns'}
    write(W/'results/fall_sweep_comparison.json',json.dumps(summary,indent=2)+'\n')
    print(json.dumps({ps:summary[ps]['held'] for ps in RUNS},indent=2))

if __name__=='__main__':main()
