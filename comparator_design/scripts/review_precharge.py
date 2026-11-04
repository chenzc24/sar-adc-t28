"""Compare first precharge sizing point with unchanged I4 native source."""
import argparse,csv,gzip,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from setup import W,ROOT,write

RUNS={'I4':'cmpdesign-i4-ffhot-reset-review-v1','A2':'cmpdesign-precharge-a2-ff-hot-v1'}
def read(candidate):
    run=RUNS[candidate];p=ROOT/'output/managed_execution/runs'/run/'collected/derived'
    r=json.loads((p/'result.json').read_text())
    with gzip.open(p/'wave.csv.gz','rt') as f:rows=list(csv.DictReader(f))
    d={k:np.array([float(row[k]) for row in rows]) for k in rows[0]}
    return r,d

def pulse(t,y,level):
    p=int(np.argmax(y));lo=p;hi=p
    if y[p]<=level:return {'peak_V':float(y[p]),'time_s':float(t[p]),'width_s':0.}
    while lo>0 and y[lo-1]>level:lo-=1
    while hi+1<len(t) and y[hi+1]>level:hi+=1
    start=float(t[lo]) if lo==0 else float(t[lo-1]+(level-y[lo-1])*(t[lo]-t[lo-1])/(y[lo]-y[lo-1]))
    end=float(t[hi]) if hi==len(t)-1 else float(t[hi]+(level-y[hi])*(t[hi+1]-t[hi])/(y[hi+1]-y[hi]))
    return dict(peak_V=float(y[p]),time_s=float(t[p]),start_s=start,end_s=end,width_s=end-start,window_clipped=lo==0 or hi==len(t)-1)

def main():
    p=argparse.ArgumentParser();p.add_argument('--include-a4',action='store_true');args=p.parse_args()
    if args.include_a4:RUNS['A4']='cmpdesign-precharge-a4-ff-hot-v1'
    all_data={k:read(k) for k in RUNS};summary={};events=[('ln',271.5e-9),('ln',371.5e-9)]
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(3,2,figsize=(12,9),layout='constrained');colors={'I4':'#416b9e','A2':'#ce713b','A4':'#258375'}
    for name,(r,d) in all_data.items():
        prefix='x'+name.lower()+'_held.';t=d['time'];out={}
        for mode in ['held','driven']:
            c=r['contexts'][name+'_'+mode]
            keys=['max_decision_s','max_reset_s','peak_terminal_V','all_correct','all_reset','mean_comparator_supply_W','screens']
            out[mode]={k:c[k] for k in keys}
            out[mode]['comparisons']=len(c['rows'])
            for metric in ['decision','reset']:
                row=max(c['rows'],key=lambda x:x[metric+'_s'])
                out[mode][metric+'_worst_sample_bracket_s']=row[metric+'_since_s']-row[metric+'_last_bad_s']
            out[mode]['internal_error_at_reset_0p5ns_V']=max(x['internal_reset_max_error_V'] for x in c['rows'])
            out[mode]['worst_pairs']=sorted(c['terminal_pairs'].items(),key=lambda z:z[1]['peak_V'],reverse=True)[:6]
            out[mode]['input_drain_to_body_peaks']={k:c['terminal_pairs'][k] for k in ['M8:DB','M9:DB']}
        out['reset_pulses']={}
        for col,(node,edge) in enumerate(events):
            mask=(t>=edge-100e-12)&(t<=edge+250e-12);tt=t[mask];x=(tt-edge)*1e12;y=d[prefix+node][mask]
            out['reset_pulses'][node+'@%.3fns'%(edge*1e9)]=pulse(tt,y,.99)
            axes[0,col].plot(x,(y-.99)*1e3,label=name,color=colors[name]);axes[0,col].axhline(0,color='gray',ls=':')
            axes[0,col].set_title(('Original worst event' if col==0 else ('A2/A4 worst reset' if args.include_a4 else 'A2 worst event'))+' | reset starts %.3f ns'%(edge*1e9));axes[0,col].set_ylabel(node.upper()+' minus VDD (mV)')
            other='lp' if node=='ln' else 'ln';internal='net1' if node=='ln' else 'net2'
            for n,ls in [(other,'-'),(internal,'--')]:axes[1,col].plot(x,d[prefix+n][mask],color=colors[name],ls=ls,label=name+' '+n)
            axes[1,col].set_ylabel('Opposite branch (V)')
            output='opa2_held' if node=='ln' else 'ona2_held'
            output=output.replace('a2',name.lower())
            axes[2,col].plot(x,d[output][mask],color=colors[name],label=name+' '+('OP' if node=='ln' else 'ON'))
            axes[2,col].set_ylabel('Resetting output (V)');axes[2,col].set_xlabel('Time from falling-edge start (ps)')
        summary[name]=out
    for col in range(2):
        for ax in axes[:,col]:
            ax.axvspan(0,50,color='#dae1e7',alpha=.4);ax.axvline(25,color='gray',lw=.7,ls=':');ax.set_xlim(-20,200);ax.grid(alpha=.15);ax.legend(fontsize=8)
        axes[2,col].axhline(.2*.99,color='gray',ls=':',label='20% VDD')
    title='M2/M4 multi = 1 (I4), 2 (A2), 4 (A4)' if args.include_a4 else 'First sizing point: M2/M4 multi 1 -> 2'
    fig.suptitle(title+'; all other sizes and clock unchanged\nFF | VDD 0.99 V | 125 C | 1.28 pF held inputs / 6.1 fF per output | ideal external sources\nShading: 50 ps clock fall; dotted vertical: clock 50%. No SAR cells, noise, mismatch or PEX.',fontsize=11)
    stem='precharge_a124' if args.include_a4 else 'precharge_a2'
    fig.savefig(W/('figures/'+stem+'_reset.png'),dpi=150,bbox_inches='tight');plt.close(fig)
    for candidate in ['A2','A4'] if args.include_a4 else ['A2']:
        a=all_data[candidate][1];names=['m6:2','m0:2','m7:1','m1:1','m4:1','m13:2','m14:2']
        residual=np.sum([a['x'+candidate.lower()+'_held.'+n] for n in names],axis=0)
        summary[candidate]['LN_kcl_max_residual_A']=float(max(abs(residual)))
    summary['scope']='FF hot only; native full-scan metrics, full-native reset windows. Timing is discrete conservative upper bound.'
    write(W/('results/'+stem+'_comparison.json'),json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
