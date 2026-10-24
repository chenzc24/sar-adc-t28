"""Native FF-vs-TT evidence, aligned to the first divergent bit decision."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analyze_bits import ROOT,OUT,VERIFY
FIG=ROOT/'docs/figures/sar8_ff_timing';FIG.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axs=plt.subplots(4,1,figsize=(11,10),layout='constrained')
fig.suptitle('First divergent decision: bit2, trial reference word = 12\nT28 | Mmain 2 um | input -0.81 V | 10 MS/s | TT 0.90 V / 27 C vs FF 0.99 V / 125 C\nSame circuit and timing parameters; ideal external sources + 50 ohm / 4 pF references; no mismatch/noise/PEX',fontsize=10)
for name,label,color in [('w2_tt_090_27_static','TT','#2776b8'),('w2_ff_099_125_static','FF hot','#cf563d')]:
    w=dict(np.load(OUT/(name+'.npz')));r=json.loads((VERIFY/(name+'.json')).read_text());b=r['rows'][5]
    sup=.9 if label=='TT' else .99;dt=w['time']*1e9-b['compare_ns'];m=(dt>=-1.4)&(dt<=.65)
    axs[0].plot(dt[m],(w['vrefp']-w['vrefn'])[m]*1e3,color=color,label=label)
    axs[1].plot(dt[m],(w['xdut.topp']-w['xdut.topn'])[m]*1e3,color=color,label=label)
    axs[1].scatter([-.01],[b['top_before_mv']],color=color,zorder=5)
    axs[2].plot(dt[m],((w['xdut.comp_p']-w['xdut.comp_n'])/sup)[m],color=color,label=label)
    axs[3].plot(dt[m],(w['xdut.xctrl.phi_w']/sup)[m],color=color,label=label+' write')
    axs[3].axvline(b['write_ns']-b['compare_ns'],color=color,ls=':',alpha=.7)
    axs[1].annotate(f'{label}: {b["top_before_mv"]:+.2f} mV',(-.01,b['top_before_mv']),xytext=(.10,b['top_before_mv']+(1 if label=='TT' else -2)),color=color)
axs[0].axhline(900,color='#555',ls='--',lw=1,label='Ideal span 900 mV')
axs[1].axhline(0,color='#333',lw=1,label='Decision boundary')
axs[1].axhline(5.625,color='#888',ls='--',lw=1,label='Ideal residual +5.625 mV')
axs[1].set_ylim(-17,10)
axs[2].axhline(0,color='#777',lw=.7)
for ax,label in zip(axs,['VREFP - VREFN (mV)','TOPP - TOPN (mV)','(COMP_P - COMP_N) / VDD','PHI_W / VDD']):
    ax.set_ylabel(label);ax.axvline(0,color='#333',ls='--',lw=.8)
    ax.set_xlim(-1.4,.65);ax.grid(alpha=.18);ax.legend(loc='best',fontsize=8,ncol=2)
axs[-1].set_xlabel('Time relative to bit2 CMP_CLK rising 50% (ns); dashed x=0 = comparison starts')
fig.savefig(FIG/'bit2_decision.png',dpi=170);plt.close(fig)

fig,axs=plt.subplots(2,1,figsize=(10,5.5),sharex=True,layout='constrained')
fig.suptitle('Reference compression exists before conversion\nSame 2-um ADC | TT 0.90 V / 27 C vs FF 0.99 V / 125 C | fixed 0/0.9-V sources + 50 ohm / 4 pF\nStatic input -0.81 V; native Spectre X CX; no mismatch/noise/PEX',fontsize=10)
for name,label,color in [('w2_tt_090_27_static','TT','#2776b8'),('w2_ff_099_125_static','FF hot','#cf563d')]:
    w=dict(np.load(OUT/(name+'.npz')));t=w['time']*1e9;m=(t>=110)&(t<=164)
    axs[0].plot(t[m],w['vrefp'][m]*1e3,color=color,label=label)
    axs[1].plot(t[m],w['vrefn'][m]*1e3,color=color,label=label)
for ax,y,lab in zip(axs,[900,0],['VREFP (mV)','VREFN (mV)']):
    ax.axhline(y,color='#555',ls='--',lw=1,label='Ideal rail')
    ax.axvspan(110,140.9,color='#aaa',alpha=.1,label='Sampling interval shown')
    ax.set_ylabel(lab);ax.grid(alpha=.18);ax.legend(ncol=4,fontsize=8)
axs[-1].set_xlabel('Absolute time (ns)')
fig.savefig(FIG/'reference_rails.png',dpi=170);plt.close(fig)
