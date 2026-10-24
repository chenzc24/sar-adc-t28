"""Native-point waveforms: both rails and all staged reset events."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from control import ROOT,OUT,VERIFY,read,dump,sha
FIG=ROOT/'docs/figures/sar8_ref_symmetric_hold'
FIG.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':170})
COLORS=['#7c7c7c','#c3782b','#087f89']
LABELS=['No added hold','Previous: high-only hold','Symmetric hold, full idle']

def load(corner):
    result=[]
    for folder,name in [(OUT,'null_ff_'+corner),(ROOT/'output/sar8_ref_gate_controls','hold25_ff_'+corner),(OUT,'symmetric25_ff_'+corner)]:
        vf=ROOT/'verification'/folder.name
        m=read(vf/(name+'_metrics.json'));p=folder/(name+'_window.npz')
        assert sha(p)==m['cache_sha256']
        result.append((m,dict(np.load(p))))
    return result

def bottom_error(w):
    return np.max([abs(w[f'xdut.xcdac.b{s}{b}']-w['vrefp' if ((s=='n' and b==7) or (s=='p' and b!=7)) else 'vrefn']) for b in range(8) for s in ['p','n']],axis=0)*1000

def main():
    files={}
    fig,ax=plt.subplots(4,2,figsize=(12.5,11),layout='constrained')
    for col,corner in enumerate(['m40','125']):
        data=load(corner);base=data[0][0];origin=base['rst7_ns'];nxt=base['next_sample_open_ns']-origin
        for (m,w),color,label in zip(data,COLORS,LABELS):
            t=w['time']*1e9;x=t-origin
            gates=np.array([w[f'xdut.{g}{b}'] for b in range(8) for g in ['gnn','gnp','gpn','gpp']])
            ax[0,col].plot(x,np.max(gates-w['vdd!'],axis=0)*1000,color=color,label=label)
            ax[1,col].plot(x,np.min(gates,axis=0)*1000,color=color,label=label)
            mask=(x>=0)&(x<nxt-.02)
            ax[2,col].plot(x[mask],bottom_error(w)[mask],color=color,label=label)
        for row in [0,1]:
            a=ax[row,col];a.axhline(0,color='#444',ls='--',lw=1,label='Rail / zero excursion')
            a.set_xlim(-.2,5)
            for event in base['reset_events']:
                xx=event['start_ns']-origin
                a.axvline(xx,color='#aaa',ls=':',lw=.8)
                if row==0:a.text(xx,1.01,str(event['bit']),transform=a.get_xaxis_transform(),ha='center',fontsize=8)
        ax[0,col].set_ylabel('Max gate above VDD (mV)')
        ax[1,col].set_ylabel('Min gate below VSS (mV)')
        ax[0,col].set_title(f"FF {base['temperature_c']:+g} C | RST7 = {origin:.3f} ns",pad=24)
        a=ax[2,col];a.set_yscale('symlog',linthresh=1)
        a.axhline(1.7578125,color='#555',ls='--',lw=1,label='0.25 LSB = 1.758 mV')
        a.axvline(nxt,color='#555',ls=':',label='Next sample opens')
        a.set(xlim=(0,nxt+1),ylim=(-.05,2000),ylabel='Max bottom-to-rail error (mV)')
        m,w=data[-1];x=w['time']*1e9-origin
        hi=sum(w[f'xdut.xref.xdrv{b}.enh_{g}'] for b in range(8) for g in ['gnn','gnp','gpn','gpp'])
        lo=sum(w[f'xdut.xref.xdrv{b}.enl_{g}'] for b in range(8) for g in ['gnn','gnp','gpn','gpp'])
        a=ax[3,col];a.plot(x,hi,color='#a9473b',label='High-rail holds enabled')
        a.plot(x,lo,color='#395f9a',ls='--',label='Low-rail holds enabled')
        a.plot(x,hi+lo,color=COLORS[-1],label='Total (32 gates)')
        a.axvline(nxt,color='#555',ls=':',label='Next sample opens')
        a.axvline(m['hold_release_sample_request_ns']-origin,color='#777',ls='--',label='SAMPLE_INT request: release')
        a.set(xlim=(-.2,nxt+1),ylim=(-1,34),ylabel='Enabled gate count')
        for a in ax[:,col]:
            a.grid(alpha=.18);a.legend(fontsize=8,loc='best');a.set_xlabel('Time from baseline RST7 (ns)')
    fig.suptitle('Complementary holding across bit7 → bit0 reset (dotted markers)\nT28 native ADC + ideal diagnostic holds | VDD 0.99 V, reference L90, Mmain 2 um\nFrame 1 idle, input -0.81 V; fixed sampling source; no noise / mismatch / PEX',fontsize=11)
    p=FIG/'reset_overview.png';fig.savefig(p);plt.close(fig);files['overview']={'path':str(p.relative_to(ROOT)),'sha256':sha(p)}

    fig,ax=plt.subplots(3,2,figsize=(12.5,8.5),layout='constrained')
    for col,corner in enumerate(['m40','125']):
        data=load(corner);base=data[0][0];origin=base['rst7_ns']
        for (m,w),color,label in zip(data,COLORS,LABELS):
            x=w['time']*1e9-origin
            ax[0,col].plot(x,(w['xdut.gnn4']-w['vdd!'])*1000,color=color,label=label)
            ax[1,col].plot(x,w['xdut.gpp4']*1000,color=color,label=label)
        m,w=data[-1];x=w['time']*1e9-origin
        ax[2,col].plot(x,w['xdut.xref.xdrv4.enh_gnn'],color='#a9473b',label='New GNN4 high hold')
        ax[2,col].plot(x,w['xdut.xref.xdrv4.enl_gpp'],color='#395f9a',ls='--',label='New GPP4 low hold')
        _,ow=data[1];ax[2,col].plot(ow['time']*1e9-origin,ow['xdut.xref.en_gnn4'],color=COLORS[1],ls=':',label='Previous GNN4 hold')
        for event in base['reset_events']:
            xx=event['start_ns']-origin
            for a in ax[:,col]:a.axvline(xx,color='#aaa',ls=':',lw=.8)
            ax[0,col].text(xx,1.01,str(event['bit']),transform=ax[0,col].get_xaxis_transform(),ha='center',fontsize=8)
        ax[0,col].set_title(f"FF {base['temperature_c']:+g} C",pad=24)
        ax[0,col].set_ylabel('GNN4 - VDD (mV)');ax[1,col].set_ylabel('GPP4 - VSS (mV)')
        ax[0,col].set_ylim(-20,70);ax[1,col].set_ylim(-70,25)
        ax[2,col].set(ylabel='Hold enable',ylim=(-.1,1.1))
        for row,a in enumerate(ax[:,col]):
            if row<2:a.axhline(0,color='#444',ls='--',lw=1,label='Expected rail')
            a.set(xlim=(-.2,5),xlabel='Time from baseline RST7 (ns)');a.grid(alpha=.18);a.legend(fontsize=8)
    fig.suptitle('Bit4 remains held while subsequent bits reset\nGNN4 and GPP4 do not need a gate transition at RST4 in this stimulus\nSame test environment as overview; native points, no waveform smoothing',fontsize=11)
    p=FIG/'bit4_continuity.png';fig.savefig(p);plt.close(fig);files['continuity']={'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
    fig,ax=plt.subplots(3,2,figsize=(12.5,8.5),layout='constrained')
    for col,corner in enumerate(['m40','125']):
        name='symmetric25_ff_'+corner;m=read(VERIFY/(name+'_metrics.json'))
        w=dict(np.load(OUT/(name+'_peak.npz')));peak=m['reference_peak'];t=w['time']*1e9
        def node(w,n):return w[n] if n!='0' else np.zeros(len(w['time']))
        a,b=peak['nodes'];v=abs(node(w,a)-node(w,b))
        ax[0,col].plot(t,v,color='#a9473b',label=f"{peak['instance'].replace('XDUT.XCDAC.','')} |V{peak['terminal']}|")
        ax[0,col].axhline(.99,color='#444',ls='--',label='0.99 V limit')
        ax[0,col].set(xlim=(peak['time_ns']-.35,peak['time_ns']+.35),ylim=(.97,1.06),ylabel='Conversion stress (V)',title=f"FF {m['temperature_c']:+g} C | worst over 600 ns")
        w=dict(np.load(OUT/(name+'_idle_peak.npz')));peak=m['phase_reference_peaks']['idle'];t=w['time']*1e9
        a,b=peak['nodes'];assert a=='vdd!' and 'xcdac.b' in b
        ax[1,col].plot(t,node(w,b)*1000,color='#087f89',label=b.replace('xdut.xcdac.','').upper())
        ax[1,col].plot(t,w['vrefn']*1000,color='#c3782b',ls='--',label='VREFN (actual)')
        ax[1,col].axhline(0,color='#444',ls=':',label='Nominal low reference')
        ax[1,col].set(xlim=(peak['time_ns']-.35,peak['time_ns']+.35),ylim=(-65,20),ylabel='Idle bottom (mV, rail zoom)')
        ax[2,col].plot(t,abs(node(w,a)-node(w,b)),color='#a9473b',label=f"{peak['instance'].replace('XDUT.XCDAC.','')} |V{peak['terminal']}|")
        ax[2,col].axhline(.99,color='#444',ls='--',label='0.99 V limit')
        ax[2,col].set(xlim=(peak['time_ns']-.35,peak['time_ns']+.35),ylim=(.97,1.06),ylabel='Idle body-drain stress (V)')
        for row in range(3):
            ax[row,col].grid(alpha=.18);ax[row,col].legend(fontsize=8);ax[row,col].set_xlabel('Absolute simulation time (ns)')
    fig.suptitle('Remaining reference-switch stress with symmetric idle holding\nDifferent worst events: conversion (top), idle reset (middle / bottom)\nSame FF0.99V native ADC + ideal helpers; six static frames, no noise / mismatch / PEX',fontsize=11)
    p=FIG/'remaining_stress.png';fig.savefig(p);plt.close(fig);files['remaining']={'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
    dump(VERIFY/'figures.json',files)

if __name__=='__main__':main()
