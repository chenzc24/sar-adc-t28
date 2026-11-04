"""M3/M5 sweep with fixed M2/M4=4; compare both event classes."""
import csv,gzip,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from setup import W,ROOT,write
from review_precharge import pulse

RUNS={'A4':'cmpdesign-a4-start-reset-review-v1','A4B2':'cmpdesign-precharge-a4b2-ff-hot-v1','A4B4':'cmpdesign-precharge-a4b4-ff-hot-v1'}
def main():
    data={};summary={}
    for tag,run in RUNS.items():
        p=ROOT/'output/managed_execution/runs'/run/'collected/derived';r=json.loads((p/'result.json').read_text())
        with gzip.open(p/'wave.csv.gz','rt') as f:rows=list(csv.DictReader(f))
        d={k:np.array([float(x[k]) for x in rows]) for k in rows[0]}
        src='cmpdesign-precharge-a4-ff-hot-v1' if tag=='A4' else run
        cfg=json.loads((W/'testbenches'/src/'measure.json').read_text())
        data[tag]=(r,d,cfg);summary[tag]={}
        for mode in ['held','driven']:
            c=r['contexts'][tag+'_'+mode]
            out={k:c[k] for k in ['max_decision_s','max_reset_s','peak_terminal_V','all_correct','all_reset','mean_comparator_supply_W','screens']}
            out['comparisons']=len(c['rows'])
            out['internal_error_at_reset_0p5ns_V']=max(row['internal_reset_max_error_V'] for row in c['rows'])
            for metric in ['decision','reset']:
                row=max(c['rows'],key=lambda x:x[metric+'_s']);out[metric+'_sample_bracket_s']=row[metric+'_since_s']-row[metric+'_last_bad_s']
            for group,keys in [('startup',['evaluate:net1','evaluate:net2']),('reset',['reset:ln','reset:lp'])]:
                key=max(keys,key=lambda k:c['phase_node_peaks'][k]['peak_V'])
                out[group]=dict(c['phase_node_peaks'][key],node=key.split(':')[1])
            out['startup_latch_peak_V']=max(c['phase_node_peaks'][k]['peak_V'] for k in ['evaluate:ln','evaluate:lp'])
            out['worst_pairs']=sorted(c['terminal_pairs'].items(),key=lambda z:z[1]['peak_V'],reverse=True)[:4]
            summary[tag][mode]=out
    chosen={}
    for group in ['startup','reset']:
        tag=max(RUNS,key=lambda k:summary[k]['held'][group]['peak_V']);event=summary[tag]['held'][group];cfg=data[tag][2]
        e=cfg['events'][event['event_index']];edge=e['t']+(1.5e-9 if group=='reset' else 0)
        chosen[group]=dict(node=event['node'],edge_s=edge,event_index=event['event_index'],highest_candidate=tag)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(3,2,figsize=(12,10));colors={'A4':'#416b9e','A4B2':'#ce713b','A4B4':'#258375'};labels={'A4':'M3/M5 = 1','A4B2':'M3/M5 = 2','A4B4':'M3/M5 = 4'}
    for col,group in enumerate(['startup','reset']):
        ch=chosen[group];node=ch['node'];edge=ch['edge_s']
        axes[0,col].set_title(group.upper()+' | '+node+' | edge %.3f ns'%(edge*1e9))
        for tag,(r,d,cfg) in data.items():
            t=d['time'];mask=(t>=edge-100e-12)&(t<=edge+300e-12);tt=t[mask];x=(tt-edge)*1e12;prefix='x'+tag.lower()+'_held.'
            v=d[prefix+node][mask]
            summary[tag].setdefault('matched_events',{})[group]=dict(ch,pulse=pulse(tt,v,.99))
            axes[0,col].plot(x,d['ck'][mask],color=colors[tag],lw=1.2)
            axes[1,col].plot(x,(v-.99)*1e3,color=colors[tag],label=labels[tag])
            e=cfg['events'][ch['event_index']]
            output=('op' if e['diff']>0 else 'on') if group=='startup' else ('op' if node=='ln' else 'on')
            axes[2,col].plot(x,d[output+tag.lower()+'_held'][mask],color=colors[tag],label=labels[tag])
        axes[0,col].set_ylabel('Clock (V)');axes[1,col].set_ylabel(node+' minus VDD (mV)');axes[1,col].axhline(0,color='gray',ls=':')
        axes[2,col].set_ylabel(('Decision' if group=='startup' else 'Resetting')+' output (V)');axes[2,col].set_xlabel('Time from edge start (ps)')
        axes[2,col].axhline(.99*(.8 if group=='startup' else .2),color='gray',ls=':')
        for ax in axes[:,col]:ax.axvspan(0,50,color='#dae1e7',alpha=.4);ax.axvline(25,color='gray',ls=':',lw=.7);ax.set_xlim(-20,220);ax.grid(alpha=.15)
        axes[1,col].legend(fontsize=8);axes[2,col].legend(fontsize=8)
    axes[0,0].set_xlim(-5,90);axes[1,0].set_xlim(-5,90);axes[1,0].set_ylim(-20,45)
    axes[1,0].set_ylabel('net2 minus VDD (mV)\nnear-rail zoom')
    axes[1,0].set_xlabel('Startup zoom: time from rising-edge start (ps)')
    fig.suptitle('M2/M4 fixed at 4; M3/M5 multi = 1, 2, 4; all other sizes and clocks unchanged\nFF | 0.99 V | 125 C | held input 1.28 pF/side | output 6.1 fF/side | ideal external sources\nMatched events selected from the largest peak across all three cases; full native samples. No noise, mismatch or PEX.',fontsize=11)
    fig.subplots_adjust(top=.84,bottom=.07,left=.08,right=.98,hspace=.46,wspace=.24)
    fig.savefig(W/'figures/precharge_a4b124.png',dpi=150,bbox_inches='tight');plt.close(fig)
    for tag in ['A4B2','A4B4']:
        d=data[tag][1];prefix='x'+tag.lower()+'_held.'
        for node,ports in [('ln',['m6:2','m0:2','m7:1','m1:1','m4:1','m13:2','m14:2']),('net2',['m5:1','m9:1','m7:3'])]:
            summary[tag][node+'_kcl_max_A']=float(max(abs(np.sum([d[prefix+n] for n in ports],axis=0))))
    summary['selected_events']=chosen
    write(W/'results/precharge_a4b124_comparison.json',json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:summary[k]['held'] for k in RUNS},indent=2))

if __name__=='__main__':main()
