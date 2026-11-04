"""Compare A4 vs A4I8 with native metrics and input kickback, no new simulation."""
import csv,gzip,json,re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from setup import W,ROOT,write
from review_precharge import pulse

RUNS={'A4':'cmpdesign-a4-start-reset-review-v1','A4I8':'cmpdesign-input-a4i8-ff-hot-v1'}

def main():
    data={};summary={};colors={'A4':'#416b9e','A4I8':'#ce713b'};labels={'A4':'M8/M9 multi4','A4I8':'M8/M9 multi8'}
    for tag,run in RUNS.items():
        p=ROOT/'output/managed_execution/runs'/run/'collected/derived'
        r=json.loads((p/'result.json').read_text())
        with gzip.open(p/'wave.csv.gz','rt') as f:
            reader=csv.DictReader(f);names=reader.fieldnames
            # No per-row dict accumulation.
            arrays=[[] for _ in names]
            for row in reader:
                for v,k in zip(arrays,names):v.append(float(row[k]))
        d={k:np.asarray(v) for k,v in zip(names,arrays)};del arrays
        src='cmpdesign-precharge-a4-ff-hot-v1' if tag=='A4' else run
        cfg=json.loads((W/'testbenches'/src/'measure.json').read_text())
        data[tag]=(r,d,cfg);summary[tag]={}
        for mode in ['held','driven']:
            c=r['contexts'][tag+'_'+mode]
            out={k:c[k] for k in ['max_decision_s','max_reset_s','peak_terminal_V','all_correct','all_reset','mean_comparator_supply_W','screens','max_residual_V']}
            out['comparisons']=len(c['rows'])
            out['internal_error_at_reset_0p5ns_V']=max(row['internal_reset_max_error_V'] for row in c['rows'])
            for field in ['max_diff_kick_V','max_cm_kick_V']:
                i=max(range(len(c['rows'])),key=lambda j:c['rows'][j][field])
                out[field]=c['rows'][i][field];out[field+'_event_index']=i
            for metric in ['decision','reset']:
                row=max(c['rows'],key=lambda x:x[metric+'_s']);out[metric+'_sample_bracket_s']=row[metric+'_since_s']-row[metric+'_last_bad_s']
            for group,keys in [('startup',['evaluate:net1','evaluate:net2']),('startup_latch',['evaluate:ln','evaluate:lp']),('reset',['reset:ln','reset:lp']),('reset_input_nodes',['reset:net1','reset:net2']),('reset_all_internal',['reset:net1','reset:net2','reset:lp','reset:ln'])]:
                key=max(keys,key=lambda k:c['phase_node_peaks'][k]['peak_V']);out[group]=dict(c['phase_node_peaks'][key],node=key.split(':')[1])
            out['startup_latch_peak_V']=max(c['phase_node_peaks'][k]['peak_V'] for k in ['evaluate:ln','evaluate:lp'])
            out['worst_pairs']=sorted(c['terminal_pairs'].items(),key=lambda z:z[1]['peak_V'],reverse=True)[:4]
            summary[tag][mode]=out
    chosen={}
    for group in ['startup','reset','startup_latch']:
        tag=max(RUNS,key=lambda k:summary[k]['held'][group]['peak_V']);e=summary[tag]['held'][group]
        chosen[group]=dict(node=e['node'],event_index=e['event_index'],edge_s=data[tag][2]['events'][e['event_index']]['t']+(1.5e-9 if group=='reset' else 0))
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(3,3,figsize=(16,9))
    for col,group in enumerate(['startup','reset','startup_latch']):
        ch=chosen[group];edge=ch['edge_s'];node=ch['node']
        axes[0,col].set_title(group.upper()+' | '+node+' | edge %.3f ns'%(edge*1e9))
        for tag,(r,d,cfg) in data.items():
            t=d['time'];mask=(t>=edge-50e-12)&(t<=edge+300e-12);tt=t[mask];x=(tt-edge)*1e12;v=d['x'+tag.lower()+'_held.'+node][mask]
            summary[tag].setdefault('matched_events',{})[group]=dict(ch,pulse=pulse(tt,v,.99))
            axes[0,col].plot(x,d['ck'][mask],color=colors[tag])
            axes[1,col].plot(x,(v-.99)*1e3,color=colors[tag],label=labels[tag])
            e=cfg['events'][ch['event_index']];output=('op' if e['diff']>0 else 'on') if group!='reset' else ('op' if node=='ln' else 'on')
            axes[2,col].plot(x,d[output+tag.lower()+'_held'][mask],color=colors[tag],label=labels[tag])
        axes[0,col].set_ylabel('Clock (V)');axes[1,col].set_ylabel(node+' minus VDD (mV)');axes[1,col].axhline(0,color='gray',ls=':')
        axes[2,col].set_ylabel(('Decision' if group!='reset' else 'Resetting')+' output (V)');axes[2,col].set_xlabel('Time from edge start (ps)')
        axes[2,col].axhline(.99*(.8 if group!='reset' else .2),color='gray',ls=':')
        for ax in axes[:,col]:ax.axvspan(0,50,color='#dae1e7',alpha=.4);ax.axvline(25,color='gray',ls=':',lw=.7);ax.set_xlim(-20,220);ax.grid(alpha=.15)
        axes[1,col].legend();axes[2,col].legend()
    for ax in axes[:2,0]:ax.set_xlim(-5,100)
    axes[1,0].set_ylim(-20,max(15,max(summary[k]['held']['startup']['peak_V']-.99 for k in RUNS)*1200))
    axes[1,0].set_xlabel('Startup zoom (ps from rising-edge start)')
    for ax in axes[:2,2]:ax.set_xlim(-5,100)
    axes[1,2].set_ylim(-20,18);axes[1,2].set_xlabel('Latch startup zoom (ps)')
    condition='FF | 0.99 V | 125 C | hold 1.28 pF/side | output 6.1 fF/side | ideal external sources'
    fig.suptitle('Only input M8/M9 multi4 -> 8; M2/M4 multi4, M3/M5 W100nm L30nm multi1\n'+condition+'\nMatched events; native points near edges. No noise, mismatch or PEX.',fontsize=11)
    fig.subplots_adjust(top=.84,bottom=.07,left=.08,right=.98,hspace=.46,wspace=.24)
    fig.savefig(W/'figures/input_a4i8_events.png',dpi=150,bbox_inches='tight');plt.close(fig)
    # Compare same event for each metric, selected from worst native kickback.
    fig,axes=plt.subplots(2,2,figsize=(12,7))
    for col,field in enumerate(['max_diff_kick_V','max_cm_kick_V']):
        tag=max(RUNS,key=lambda k:summary[k]['held'][field]);idx=summary[tag]['held'][field+'_event_index'];e=data[tag][2]['events'][idx];edge=e['t']
        for tag,(r,d,cfg) in data.items():
            t=d['time'];mask=(t>=edge-50e-12)&(t<edge+1.5e-9);x=(t[mask]-edge)*1e9
            vp=d['p'+tag.lower()+'_held'][mask];vn=d['n'+tag.lower()+'_held'][mask]
            baseline=r['contexts'][tag+'_held']['rows'][idx]['pre_eval_diff_V']
            axes[0,col].plot(x,(vp-vn-baseline)*1e3,color=colors[tag],label=labels[tag])
            axes[1,col].plot(x,((vp+vn)/2-e['cm'])*1e3,color=colors[tag],label=labels[tag])
        axes[0,col].set_title(('Worst DM' if col==0 else 'Worst CM')+' event | %.3f ns | Vin diff %.3f mV'%(edge*1e9,e['diff']*1e3))
        for ax in axes[:,col]:ax.axvspan(0,.05,color='#dae1e7',alpha=.4);ax.axvline(.025,color='gray',ls=':');ax.axhline(0,color='gray',ls=':');ax.grid(alpha=.15);ax.legend()
        axes[0,col].set_ylabel('Input DM change (mV)');axes[1,col].set_ylabel('Input CM minus nominal (mV)');axes[1,col].set_xlabel('Time from rising-edge start (ns)')
    fig.suptitle('Held-input kickback: same-event overlays; peak metrics from ALL native points\n'+condition+'\nClock edge 50ps; measured peak window starts at clock50%, ends before reset. Curves: native near edge, ~20ps later.',fontsize=10)
    fig.tight_layout(rect=[0,0,1,.88]);fig.savefig(W/'figures/input_a4i8_kickback.png',dpi=150);plt.close(fig)
    d=data['A4I8'][1];prefix='xa4i8_held.'
    for node,ports in [('ln',['m6:2','m0:2','m7:1','m1:1','m4:1','m13:2','m14:2']),('net2',['m5:1','m9:1','m7:3'])]:
        summary['A4I8'][node+'_kcl_max_A']=float(max(abs(np.sum([d[prefix+n] for n in ports],axis=0))))
    summary['selected_events']=chosen
    summary['measurement_note']='DM kick is relative to measured pre-evaluation DM; CM kick is relative to nominal CM. Native window: clock rising50% through before falling edge starts. Residual: DM immediately before reset. Not input capacitance extraction or mismatch/noise qualification.'
    write(W/'results/input_a4i8_comparison.json',json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:summary[k]['held'] for k in RUNS},indent=2))

if __name__=='__main__':main()
