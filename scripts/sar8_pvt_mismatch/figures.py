"""Native waveform figures for the bounded five-point screen."""
import gzip
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flow import ROOT, OUT, VERIFY, read

FIG=ROOT/'docs/figures/sar8_pvt_mismatch'
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})

def environment(r):
    return f"T28 {r['corner'].upper()} | VDD {r['vdd']:.2f} V | {r['temperature_c']} C | fixed VREF 0/0.9 V, input CM 0.45 V\nNative MOS/RC ADC | ideal external sources and SAMPLE | Spectre X CX | no mismatch/noise/PEX"

def raw(name):
    with gzip.open(OUT/name/'reduced/reduced.json.gz','rt') as f:return json.load(f)

def main():
    names=read(VERIFY/'setup.json')['cases']
    rows=[read(VERIFY/(n+'.json')) for n in names]
    FIG.mkdir(parents=True,exist_ok=True)
    worstcase=max(rows,key=lambda r:max(v['peak_v']/v['limit_v'] for v in r['groups'].values()))
    group=max(worstcase['groups'],key=lambda g:worstcase['groups'][g]['peak_v']/worstcase['groups'][g]['limit_v'])
    window=next(w for w in raw(worstcase['name'])['windows'] if w['group']==group)
    s=window['worst'];w={k:np.array(v) for k,v in window['wave'].items()};t=w['time']*1e9
    a,b=s['nodes'];va=w[a] if a!='0' else np.zeros_like(t);vb=w[b] if b!='0' else np.zeros_like(t)
    fig,axs=plt.subplots(3,1,figsize=(11,8),sharex=True,layout='constrained')
    fig.suptitle('Worst observed terminal stress\n'+environment(worstcase),fontsize=11)
    axs[0].plot(t,va,label=a);axs[0].plot(t,vb,label=b);axs[0].set_ylabel('Node voltage (V)')
    axs[1].plot(t,np.abs(va-vb),color='#c94b3e',label='|V'+s['terminal'].upper()+'|')
    axs[1].axhline(s['limit_v'],ls='--',color='#555',label=f"Core model limit {s['limit_v']:.2f} V")
    axs[1].set_ylim(s['limit_v']-.03,s['peak_v']+.02)
    axs[1].set_ylabel('Terminal stress (V)');axs[1].set_title(f"{s['instance']} | peak {s['peak_v']:.6f} V at {s['time_ns']:.3f} ns",fontsize=10)
    for n,label in [('xdut.phi_u','Update'),('xdut.cmp_clk','Compare'),('xdut.xref.cap_clk','Reference capture'),('xdut.preset','Idle reset')]:
        axs[2].plot(t,w[n],label=label,lw=1)
    axs[2].set(ylabel='Control (V)',xlabel='Time (ns)')
    for ax in axs:ax.grid(alpha=.2);ax.legend(fontsize=8,loc='best')
    fig.savefig(FIG/'worst_stress.png',dpi=160);plt.close(fig)
    case=next((r for r in rows if not r['all_timing_pass']),None)
    if case is None:
        case=max((r for r in rows if r['static_code_pass'] is not None),key=lambda r:max(abs(f['code_error_vs_ideal']) for f in r['frames'][1:]))
    data=raw(case['name'])
    w={k:np.array(v) for k,v in data['wave'].items()};t=w['time']*1e9
    f=next((f for f in case['frames'] if not f['timing_pass']),None)
    if f is None:f=max(case['frames'][1:],key=lambda f:abs(f.get('code_error_vs_ideal',0)))
    i=f['frame']
    mask=(t>=i*100)&(t<min((i+1)*100+40,t[-1]));t=t[mask];vh=case['vdd']/2
    fig,axs=plt.subplots(5,1,figsize=(11,10),sharex=True,layout='constrained')
    fig.suptitle('Critical acquisition and conversion\n'+environment(case),fontsize=11)
    for n,label in [('sample','External SAMPLE'),('xdut.seq_sample','Bootstrap enable')]:axs[0].plot(t,w[n][mask],label=label)
    for n,label in [('xdut.cmp_clk','Compare'),('xdut.xctrl.phi_w','Write')]:axs[1].plot(t,w[n][mask],label=label)
    for n,label in [('xdut.xref.cap_clk','Reference capture'),('xdut.xref.rst7','Reset bit 7'),('xdut.xref.rst0','Reset bit 0')]:axs[2].plot(t,w[n][mask],label=label)
    axs[3].plot(t,(w['xdut.topp']-w['xdut.topn'])[mask],label='CDAC differential')
    axs[3].plot(t,(w['vinp_src']-w['vinn_src'])[mask],ls='--',label='Input differential')
    codes=sum((w[f'd{b}']>vh).astype(int)*(1<<b) for b in range(8))
    axs[4].plot(t,codes[mask],label='Decoded output word')
    axs[4].text(i*100+91,max(f['code'],max(f.get('allowed_ideal_codes',[0])))+13,
                f"Held: {f['code']} / expected: {f.get('allowed_ideal_codes',['n/a'])[0]}",fontsize=9)
    if 'allowed_ideal_codes' in f:
        for k,c in enumerate(f['allowed_ideal_codes']):axs[4].hlines(c,i*100+90,(i+1)*100,ls='--',color='#c94b3e',label='Expected held code' if k==0 else None)
    for ax,label in zip(axs,['Acquire (V)','Conversion (V)','Reference (V)','Differential (V)','Code']):
        ax.set_ylabel(label);ax.grid(alpha=.2);ax.legend(fontsize=8,loc='best',ncol=2)
        ax.axvspan(i*100+90,(i+1)*100,color='#777',alpha=.08)
    axs[-1].set_xlabel('Time (ns)')
    axs[1].set_title(f"Frame {i}: compare/write/update/capture = {f['counts']}; expected 8/8/8/16",fontsize=10)
    fig.savefig(FIG/'risk_timing.png',dpi=160);plt.close(fig)
    print('Figures:',FIG)

if __name__=='__main__':main()
