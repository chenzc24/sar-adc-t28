"""Static scientific plots: native waveforms, explicit ideal baselines and phases."""
import shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from common import ROOT, OUT, LIMIT, load
from analyze import data

FIG=ROOT/'docs/figures/cdac8_dualrail'
plt.rcParams.update({'font.size':11,'axes.grid':True,'grid.alpha':.2,'legend.frameon':False})


def save(fig,name):
    FIG.mkdir(parents=True,exist_ok=True)
    fig.savefig(FIG/name,dpi=150,bbox_inches='tight')
    plt.close(fig)


def timing():
    _,case,w=data('final_nominal');t=w['time']*1e9
    at=lambda k,x:np.interp(x,t,w[k])
    sup=case['parameters']['SUP'];vin=at('vinp_src',141.05)-at('vinn_src',141.05)
    times=np.arange(145.9,181,5)
    active=np.array([sum((at(f'nh<{b}>',x)>sup/2)*(1<<b) for b in range(8)) for x in times])
    residual=vin+sup-active*2*sup/256
    final=sum((at(f'dout<{b}>',193)>sup/2)*(1<<b) for b in range(8))
    ix=[105,147.51,152.51,157.51,162.51,167.51,172.51,177.51,182.51,195]
    iy=[*residual,vin+sup-final*2*sup/256,vin+sup-final*2*sup/256]
    fig,ax=plt.subplots(4,1,figsize=(11.5,10),sharex=True,layout='constrained',height_ratios=[1,1.3,1.4,1.2])
    for a in ax:
        a.axvspan(101.05,141.05,color='#2979a3',alpha=.07)
        a.axvspan(141.05,182.53,color='#be8a27',alpha=.07)
        a.axvspan(182.53,195,color='#31866b',alpha=.07)
        a.axvline(103.01,color='.5',ls=':',lw=1)
        a.set_xlim(100,195)
    for k,label in [('phi','Sample PHI'),('cmp_clk','Compare'),('valid','Valid')]:ax[0].plot(t,w[k],label=label,lw=1.4)
    ax[0].set_ylabel('Control (V)');ax[0].legend(ncol=3,loc='upper right')
    for x,label in [(121,'Sampling'),(161,'SAR / top plates held'),(188,'Valid')]:
        ax[0].text(x,1.04,label,transform=ax[0].get_xaxis_transform(),ha='center')
    ax[0].set_title('8-bit dual-rail CDAC | TT, 0.9 V, 27 C | input +453.516 mV',pad=32)
    ax[1].plot(t,w['topp'],label='TOPP');ax[1].plot(t,w['topn'],label='TOPN')
    ax[1].plot(t,(w['topp']+w['topn'])/2,label='Common-mode',color='#31866b')
    ax[1].axhline(.45,color='.3',ls='--',lw=1,label='Ideal common-mode 0.45 V')
    ax[1].set_ylabel('Top plates (V)');ax[1].legend(ncol=2,loc='upper right')
    ax[2].plot(t,(w['topp']-w['topn'])*1e3,label='Native TOPP - TOPN',lw=1.3)
    ax[2].step(ix,np.array(iy)*1e3,where='post',ls='--',color='.25',label='Ideal charge redistribution',lw=1.2)
    ax[2].scatter(times,residual*1e3,marker='x',color='.25',s=24,zorder=4)
    ax[2].set_ylabel('SAR residual (mV)');ax[2].legend(loc='lower right')
    for name,label,marker in [('final_nominal','Native sampler / ideal comparator','o'),
                               ('final_ideal_sample','Ideal sampler / ideal comparator','s'),
                               ('final_strongarm','Native sampler / StrongARM','^')]:
        row=load(f'metrics/{name}.json');q=row['comparisons']
        ts=np.array([x['time_ns'] for x in q]);ts-=100*np.floor(ts[0]/100)-100
        ax[3].plot(ts,[x['error_mv'] for x in q],marker=marker,ls='none',label=label)
    ax[3].axhspan(-LIMIT*1000,LIMIT*1000,color='#31866b',alpha=.1,label='+/- 0.25 LSB')
    ax[3].axhline(0,color='.4',lw=1)
    ax[3].set_ylabel('Pre-compare error (mV)');ax[3].set_xlabel('Time (ns)')
    ax[3].legend(ncol=2,loc='lower left',fontsize=10)
    ax[3].set_ylim(-2.5,2.5)
    save(fig,'timing.png')


def checks():
    codes=load('metrics/static_codes.json')
    dyn=load('metrics/clean_va_dynamic_256.json')
    _,_,w=data('clean_va_dynamic_256');ns=w['time']*1e9
    code=sum((w[f'dout<{b}>']>.45).astype(int)*(1<<b) for b in range(8))
    code=code[(ns>=493-1e-5)&(ns<26000)]
    p=abs(np.fft.rfft(code-code.mean()))**2
    db=10*np.log10(np.maximum(p,1e-20)/p.max())
    fig,ax=plt.subplots(2,1,figsize=(10.5,7),layout='constrained')
    ax[0].plot(codes['expected'],codes['expected'],ls='--',color='.4',label='Ideal code centers')
    ax[0].plot(codes['expected'],codes['actual'],lw=1,label='Native CDAC / ideal comparator')
    ax[0].set(xlabel='Applied ideal center code',ylabel='Output code',title='256 code centers (not a DNL/INL measurement)')
    ax[0].legend()
    ax[1].plot(np.arange(len(db))*10/256,db,lw=1)
    ax[1].set(xlabel='Frequency (MHz)',ylabel='Power (dBc)',ylim=(-100,3),
              title=f"256-point coherent sine | SNDR {dyn['sndr_db']:.2f} dB | ENOB {dyn['enob_bits']:.2f} bits")
    fig.suptitle('TT, 0.9 V, 27 C | native Bootstrap / reference MOS / MOM; ideal sign comparator')
    save(fig,'static_dynamic.png')


def stress_failure(name='clean_va_input_-800000',side='p',bit=6,restore=False):
    # This bank is not cherry-picked as a passing point: it exposes the
    # negative-input transition that native Spectre flags as unsafe.
    _,_,w=data(name);t=w['time']*1e9
    bot=w[f'xcdac.b{side}{bit}'];gate=w[f'xcdac.xs{side}{bit}.el_d']
    peak=int(np.argmax(bot));center=t[peak]
    command=100*np.floor(center/100)+(3.01 if restore else 47.51)
    fig,ax=plt.subplots(3,1,figsize=(10.5,8),sharex=True,layout='constrained')
    for a in ax:
        a.axvline(command,color='.5',ls=':',lw=1)
        a.axvline(command+.1,color='.5',ls='--',lw=1)
        a.set_xlim(center-.7,center+1.0)
    ax[0].plot(t,w['topp'],label='TOPP');ax[0].plot(t,w['topn'],label='TOPN')
    ax[0].plot(t,(w['topp']+w['topn'])/2,label='Common-mode',color='#31866b')
    ax[0].axhline(.45,color='.3',ls='--',lw=1,label='Ideal common-mode')
    title='Input -0.5 LSB | reference restore inside sampling' if restore else 'Input -0.8 V | first SAR update'
    ax[0].set(ylabel='Top plates (V)',title=title)
    ax[0].legend(ncol=2)
    ax[1].plot(t,bot,label=f'{side.upper()}-side bit-{bit} bottom',color='#b34c3f')
    ax[1].plot(t,w['vrefp'],label='VREFP',ls='--',color='.4')
    ax[1].plot(t,w['vrefn'],label='VREFN',ls=':',color='.4')
    ax[1].plot(t,gate,label='MN_LOW gate',alpha=.8)
    ax[1].set_ylabel('Bottom / gate (V)');ax[1].legend(ncol=2)
    ax[1].annotate(f'{bot[peak]:.3f} V',xy=(center,bot[peak]),xytext=(center+.3,bot[peak]+.05),
                   arrowprops={'arrowstyle':'->','color':'.4'})
    ax[2].plot(t,abs(bot-w['vrefn']),label='MN_LOW |Vds|')
    ax[2].plot(t,abs(gate-bot),label='MN_LOW |Vgd|')
    ax[2].plot(t,abs(bot),label='MN_LOW |Vbd|',color='#b34c3f',ls=':')
    ax[2].axhline(.99,color='.3',ls='--',label='0.99 V core screen')
    ax[2].set(ylabel='Port difference (V)',xlabel='Time (ns)')
    ax[2].legend(ncol=2,loc='lower right')
    fig.supxlabel(f'Dotted: command {command:.2f} ns; dashed: new rail enable {command+.1:.2f} ns',fontsize=10)
    save(fig,'reset_failure.png' if restore else 'stress_failure.png')


if __name__=='__main__':
    timing();stress_failure()
    stress_failure('clean_va_input_-3516','n',5,True)
    # Never turn an interrupted scan into a complete static/FFT figure.
    if (OUT/'metrics/clean_va_dynamic_256.json').exists() and (OUT/'metrics/static_codes.json').exists():checks()
    for f in ['canvas_review.png','canvas_ref_leaf.png']:shutil.copy2(OUT/f,FIG/f)
