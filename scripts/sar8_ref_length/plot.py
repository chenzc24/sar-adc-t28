"""Minimal DC tradeoff and FF/SS integrated evidence panels."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from control import ROOT,OUT,VERIFY,read,sha
FIG=ROOT/'docs/figures/sar8_ref_length'
FIG.mkdir(parents=True,exist_ok=True)
COLORS=['#bb493c','#c48b22','#087f89']

def dc():
    rows=read(VERIFY/'dc_results.json')['rows'];x=np.arange(3)
    fig,axs=plt.subplots(2,1,figsize=(10,7))
    values=[r['estimated_array_rail_load_ua'] for r in rows]
    axs[0].bar(x,values,color=COLORS,width=.55)
    axs[0].axhline(10,color='#666',ls='--',lw=1,label='Provisional screen: 10 uA/rail')
    for i,v in enumerate(values):axs[0].text(i,v*1.12,f'{v:.2f}',ha='center',fontsize=10)
    axs[0].set(yscale='log',ylim=(1,300),ylabel='Estimated array load (uA)',xticks=x,xticklabels=['30 nm','60 nm','90 nm'])
    axs[0].legend(loc='upper right');axs[0].set_title('OFF-state leakage at common measured-hot reference/gate biases',fontsize=11)
    for key,offset,color,label in [('n',-.17,'#087f89','NMOS ON'),('p',.17,'#c48b22','PMOS ON')]:
        vals=[r['Ron_bit7_ohm'][key] for r in rows]
        axs[1].bar(x+offset,vals,width=.32,color=color,label=label)
        for i,v in enumerate(vals):axs[1].text(i+offset,v+.2,f'{v:.2f}',ha='center',fontsize=9)
    axs[1].set(ylim=(0,16),ylabel='Bit-7 Ron (ohm)',xticks=x,xticklabels=['30 nm','60 nm','90 nm'])
    axs[1].legend(loc='upper left');axs[1].set_title('ON differential resistance: slope over VDS = -1 to +1 mV',fontsize=11)
    for ax in axs:ax.grid(axis='y',alpha=.2)
    fig.suptitle('Reference switch L sweep | FF / 0.99 V / 125 C | native T28 models\n'
       'Fixed WN/WP = 150/175 nm, nf=1, bit-7 multi=384; no noise/mismatch/PEX',fontsize=11)
    fig.tight_layout();fig.savefig(FIG/'length_tradeoff.png',dpi=180);plt.close(fig)

def integrated():
    data=read(VERIFY/'integrated_comparison.json');assert data['complete']
    hot=next(p for p in data['points'] if 'ff_099_125' in p['candidate']['case'])
    cold=next(p for p in data['points'] if 'ss_081_m40' in p['candidate']['case'])
    fig,axs=plt.subplots(3,1,figsize=(11,9))
    for role,color,label in [('baseline',COLORS[0],'L = 30 nm'),('candidate',COLORS[2],'L = 90 nm')]:
        r=hot[role];path=OUT/(r['case']+'.npz');assert sha(path)==r['cache_sha256']
        w=dict(np.load(path));t=w['time']*1e9
        axs[0].plot(t,(w['vrefp']-w['vrefn'])*1000,color=color,label=f"{label}: {r['reference_span_130ns_mv']:.3f} mV")
        bit=r['bits'][5];rel=t-bit['compare_ns'];use=(rel>=-1.5)&(rel<=-.01)
        axs[1].plot(rel[use],(w['xdut.topp'][use]-w['xdut.topn'][use])*1000,color=color,
          label=f"{label}: {bit['top_before_mv']:+.3f} mV; output {r['codes'][1]}")
        r=cold[role];path=OUT/(r['case']+'.npz');assert sha(path)==r['cache_sha256']
        w=dict(np.load(path));t=w['time']*1e9;err=(w['xdut.topp']-w['xdut.topn']+.81)*1000
        axs[2].plot(t,err,color=color,ls='--' if role=='candidate' else '-',
          label=f"{label}: preclose {r['preclose_errors_mv'][1]:+.3f} mV")
        axs[2].axvline(r['sample_close_ns'],color=color,ls=':',lw=1)
    axs[0].axhline(900,color='#555',ls='--',lw=1,label='Ideal span: 900 mV')
    axs[0].set(xlim=(120,140),ylim=(882,902),ylabel='Reference span (mV)',xlabel='Time (ns)',title='FF hot: restored reference platform during sampling')
    axs[1].axhline(0,color='#555',ls='--',lw=1);axs[1].axvline(0,color='#555',ls=':',lw=1)
    axs[1].set(xlim=(-1.5,.05),ylabel='TOPP - TOPN (mV)',xlabel='Time relative to bit-2 comparison (ns)',title='FF hot: bit-2 decision, input -0.81 V, trial word 12')
    axs[2].axhspan(-data['sampling_budget_mv'],data['sampling_budget_mv'],color='#087f89',alpha=.08,label='Sampling budget: +/-0.25 LSB')
    axs[2].axhline(0,color='#555',ls='--',lw=1)
    axs[2].set(xlim=(130,142),ylim=(-2.5,3),ylabel='TOP differential error (mV)',xlabel='Time (ns)',title='SS cold: acquisition tail and turn-off (dotted = sample enable falls)')
    for ax in axs:ax.legend(fontsize=8,loc='best');ax.grid(alpha=.2)
    fig.suptitle('Integrated T28 ADC | fixed 2 um Bootstrap / W / multiplicity / timing\n'
       'FF: 0.99 V, 125 C; SS: 0.81 V, -40 C | references 0/0.9 V + 50 ohm + 4 pF | no noise/mismatch/PEX',fontsize=10)
    fig.tight_layout();fig.savefig(FIG/'integrated_ff_ss.png',dpi=180);plt.close(fig)

if __name__=='__main__':
    dc()
    if (VERIFY/'integrated_comparison.json').exists():integrated()
