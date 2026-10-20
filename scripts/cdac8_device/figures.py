"""Scientific plots from recorded Spectre waveforms, with explicit baselines."""
from __future__ import annotations
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import sys
from analyze_system import waves,at,load,OUT,LIMIT,LSB
from common import ROOT

F=ROOT/'docs/figures/cdac8_device' if '--curate' in sys.argv else OUT/'figures'
F.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.2,'figure.dpi':150})

def mismatch():
    r=load('banks/summary_200.json');rows=r['rows']
    fig,ax=plt.subplots(1,2,figsize=(10,3.6),layout='constrained')
    for a,key,label in zip(ax,('dnl_abs_max_lsb','inl_abs_max_lsb'),('Max |DNL| (LSB)','Max |INL| (LSB)')):
        a.hist([x[key] for x in rows],bins=16,color='#278b8d',edgecolor='white',label='200 PDK local-MC arrays')
        a.axvline(.5,color='#b84439',ls='--',label='Internal limit: 0.5 LSB');a.set(xlabel=label,ylabel='Count',xlim=(0,.53));a.legend(fontsize=8)
    fig.suptitle('512 independent MOM units: static weight oracle (not switched MC)')
    fig.savefig(F/'mismatch.png');plt.close(fig)

def timing():
    _,a=waves('device_smoke_prep');_,b=waves('balanced_literal')
    fig,ax=plt.subplots(3,1,figsize=(10,7.3),sharex=True,layout='constrained')
    mask=(b['time']>=435e-9)&(b['time']<=452e-9);t=b['time'][mask]*1e9
    ax[0].plot(t,b['phi'][mask],label='Bootstrap PHI');ax[0].plot(t,b['dac_sample'][mask],label='VCM enable');ax[0].plot(t,b['base'][mask],label='Reference BASE');ax[0].legend(ncol=3);ax[0].set_ylabel('Control (V)')
    for w,label,color in ((a,'Initial sizing','#c65046'),(b,'Load-proportional sizing','#248989')):
        keep=(w['time']>=435e-9)&(w['time']<=452e-9);tt=w['time'][keep]*1e9;v=w['topp'][keep]-w['topn'][keep]
        ax[1].plot(tt,v*1000,label=label,color=color);ax[2].plot(tt,(v-.8)*1000,label=label,color=color)
    ax[1].axhline(800,color='black',ls='--',lw=1,label='Expected held differential: 800 mV')
    ax[2].axhline(0,color='black',ls='--',lw=1,label='Ideal error = 0')
    ax[2].axhspan(-LIMIT*1000,LIMIT*1000,color='#59aa7a',alpha=.12,label='+/-0.25 LSB budget')
    for a0 in ax:
        a0.axvspan(441.05,452,color='#999999',alpha=.1);a0.axvline(441.05,color='#666',ls=':',lw=1)
    ax[1].set_ylabel('TOPP - TOPN (mV)');ax[2].set(xlabel='Time (ns); shaded = held/conversion phase',ylabel='Raw error, detail (mV)',ylim=(-2.2,2.2),xlim=(435,452))
    ax[1].legend(fontsize=8);ax[2].legend(fontsize=8,ncol=2)
    fig.suptitle('Native bootstrap + PDK flat CDAC, fixed code 128, input step to +0.8 V')
    fig.savefig(F/'hold_timing.png');plt.close(fig)

def reset():
    names=[('device_smoke_prep','Initial sizing','#c65046'),('balanced_literal','Load-proportional sizing','#248989')]
    if (OUT/'transient/softreset_step_result.json').exists():names.append(('softreset_step','1 ns VCM re-enable','#7966ae'))
    fig,ax=plt.subplots(2,1,figsize=(10,5.8),sharex=True,layout='constrained')
    for name,label,color in names:
        _,w=waves(name);keep=(w['time']>=489.8e-9)&(w['time']<=494e-9)
        ax[0].plot(w['time'][keep]*1e9,w['xcdac.bn7'][keep],color=color,label=label)
        ax[1].plot(w['time'][keep]*1e9,w['dac_sample'][keep],color=color,label=label)
    ax[0].axhline(.99,color='black',ls='--',lw=1,label='Core model Vds limit: 0.99 V (BOT vs VSS)')
    ax[0].axhline(.45,color='gray',ls=':',label='Expected reset: VCM = 0.45 V')
    ax[0].set_ylabel('MSB bottom N (V)');ax[0].legend(fontsize=8,ncol=2)
    ax[1].set(xlabel='Time (ns); post-conversion reset',ylabel='VCM enable (V)',xlim=(489.8,494));ax[1].legend(fontsize=8,ncol=3)
    fig.suptitle('Reference reset: good held accuracy does not imply safe transient bias')
    fig.savefig(F/'reset_stress.png');plt.close(fig)

def dac():
    r=load('transient/summary_dac.json');fig,ax=plt.subplots(2,1,figsize=(9,5.5),sharex=True,layout='constrained')
    for a,key,label in ((ax[0],'dnl_lsb','DNL (LSB)'),(ax[1],'inl_raw_lsb','Raw INL (LSB)')):
        a.plot(r[key],color='#248989',label='Native switched DAC');a.axhline(0,color='black',lw=1,ls='--',label='Ideal');a.set_ylabel(label);a.legend()
    ax[1].set_xlabel('DAC code');fig.suptitle('256-code nominal DAC transfer; reset-SOA warnings remain open')
    fig.savefig(F/'dac_linearity.png');plt.close(fig)

def stress_zoom():
    _,w=waves('stress_trace');mask=(w['time']>489.8e-9)&(w['time']<491e-9)
    t=w['time'][mask]*1e9;bot=w['xcdac.bp5'][mask]
    fig,ax=plt.subplots(2,1,figsize=(10,5.8),sharex=True,layout='constrained')
    ax[0].plot(t,bot,color='#c34d42',label='P-side bit-5 bottom')
    ax[0].plot(t,np.where(t<490.22,.9,.45),'k:',lw=1.2,label='Ideal rail-to-VCM handoff')
    ax[0].axhline(.99,color='#666',ls='--',label='MN_LOW Vds limit: 0.99 V')
    ax[0].axhspan(.99,1.04,color='#d66',alpha=.1)
    peak=np.argmax(bot)
    ax[0].annotate(f'{bot[peak]:.4f} V at {t[peak]:.3f} ns',xy=(t[peak],bot[peak]),xytext=(490.43,1.015),arrowprops={'arrowstyle':'->','color':'#c34d42'},color='#a33')
    ax[0].set(ylabel='Bottom voltage (V)',ylim=(.42,1.04));ax[0].legend(fontsize=8,loc='lower right')
    for key,label in [('phi','Bootstrap PHI'),('dac_sample','VCM enable'),('base','Reference BASE')]:ax[1].plot(t,w[key][mask],label=label)
    ax[1].set(xlabel='Time (ns)',ylabel='Control (V)',xlim=(489.8,491));ax[1].legend(ncol=3,fontsize=8)
    fig.suptitle('Closed-loop +453.516 mV: post-conversion VCM reset')
    fig.savefig(F/'closed_loop_stress.png');plt.close(fig)

def cold_step():
    _,a=waves('pvt_ss_810_-40_800');_,b=waves('ideal_input_ss')
    fig,ax=plt.subplots(3,1,figsize=(10,7),sharex=True,layout='constrained')
    keep=(a['time']>=430e-9)&(a['time']<=480e-9)
    for key,label in [('phi','Input sampling PHI'),('dac_sample','VCM enable')]:ax[0].plot(a['time'][keep]*1e9,a[key][keep],label=label)
    ax[0].legend(ncol=2);ax[0].set_ylabel('Control (V)')
    for w,label,color in ((a,'Native input Bootstrap','#c34d42'),(b,'150-ohm ideal input relay','#278989')):
        keep=(w['time']>=430e-9)&(w['time']<=480e-9);t=w['time'][keep]*1e9;v=w['topp'][keep]-w['topn'][keep]
        ax[1].plot(t,v*1000,label=label,color=color);ax[2].plot(t,(v-.8)*1000,label=label,color=color)
    ax[1].axhline(800,color='black',ls='--',lw=1,label='Expected held differential: 800 mV')
    ax[2].axhline(0,color='black',ls='--',lw=1,label='Ideal error = 0')
    ax[2].axhspan(-LIMIT*1000,LIMIT*1000,color='#59aa7a',alpha=.2,label='+/-0.25 LSB budget')
    for aa in ax:aa.axvspan(441.05,480,color='#999',alpha=.10);aa.axvline(441.05,color='#666',ls=':',lw=1)
    ax[1].set(ylabel='TOPP - TOPN (mV)');ax[1].legend(fontsize=8,ncol=2)
    ax[2].set(xlabel='Time (ns); shaded = held/conversion phase',ylabel='Raw error (mV)',xlim=(430,480));ax[2].legend(fontsize=8,ncol=2)
    fig.suptitle('SS / 0.81 V / -40 C: first sample after -0.8 to +0.8 V input step at 400 ns')
    fig.savefig(F/'cold_step_isolation.png');plt.close(fig)

def spectrum():
    path=OUT/'transient/summary_dynamic.json'
    if not path.exists():return
    r=load('transient/summary_dynamic.json');code=np.asarray(r['codes']);n=len(code)
    ts=(441.05+100*np.arange(n))*1e-9;vin=.9*10**(-1/20)*np.sin(2*np.pi*(10e6*461/1024)*ts)
    ideal=np.clip(np.floor((vin+.9)/LSB),0,255)
    fig,ax=plt.subplots(figsize=(10,4.5),layout='constrained');f=np.fft.rfftfreq(n,1e-7)/1e6
    for c,label,color,width in ((ideal,'Ideal 8-bit quantizer','#aaa',.7),(code,'Native sampler + PDK CDAC + macro comparator','#248989',1.1)):
        x=-.9+(c+.5)*LSB;mag=2*np.abs(np.fft.rfft(x-x.mean()))/n/.9;mag[[0,-1]]*=.5
        ax.plot(f[1:],20*np.log10(np.maximum(mag[1:],1e-15)),label=label,color=color,lw=width)
    ax.set(xlabel='Frequency (MHz)',ylabel='FFT magnitude (dBFS)',xlim=(0,5),ylim=(-115,3))
    ax.legend(fontsize=8,loc='upper left')
    fig.suptitle(f"1024-point nominal diagnostic: SNDR {r['sndr_db']:.2f} dB, ENOB {r['enob_sndr_bits']:.2f}; no physical noise")
    fig.savefig(F/'spectrum.png');plt.close(fig)

if __name__=='__main__':
    mismatch();timing();reset();dac();stress_zoom();cold_step();spectrum()
    print(F)
