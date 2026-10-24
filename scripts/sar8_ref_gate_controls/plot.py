"""Matched waveform comparisons of independent hold and slew controls."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from control import ROOT,OUT,VERIFY,read,dump,sha
FIG=ROOT/'docs/figures/sar8_ref_gate_controls';FIG.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180})
COLORS=['#555555','#087f89','#c9473b']
LABELS={'null':'Null control','hold100':'Hold 100 ohm @ bit4','hold25':'Hold 25 ohm @ bit4',
        'slew100':'Bit7 +100 ohm (idle only)','slew300':'Bit7 +300 ohm (idle only)'}

def main():
    data=read(VERIFY/'comparison.json');rows=data['cases'];files={}
    for family,tags in [('holding',['null','hold100','hold25']),('slew',['null','slew100','slew300'])]:
        if any(f'{tag}_ff_{corner}' not in rows for tag in tags for corner in ['m40','125']):continue
        fig,axs=plt.subplots(4,2,figsize=(12,11),layout='constrained')
        for col,corner in enumerate(['m40','125']):
            base=rows[f'null_ff_{corner}'];origin=base['rst7_ns']
            for tag,color in zip(tags,COLORS):
                name=f'{tag}_ff_{corner}';r=rows[name];path=OUT/(name+'_window.npz')
                assert sha(path)==r['cache_sha256'];w=dict(np.load(path));t=w['time']*1e9;x=t-origin
                axs[0,col].plot(x,w['xdut.gnn4'],color=color,label=LABELS[tag])
                pm=np.max([abs(w['vdd!']-w[f'xdut.{g}{b}']) for g in ['gnp','gpp'] for b in range(8)],axis=0)
                axs[1,col].plot(x,pm,color=color,label=LABELS[tag])
                axs[2,col].plot(x,w['xdut.xcdac.bn7'],color=color,label=LABELS[tag])
                errors=[]
                for b in range(8):
                    for side in ['p','n']:
                        high=(side=='n' and b==7) or (side=='p' and b!=7)
                        errors.append(abs(w[f'xdut.xcdac.b{side}{b}']-w['vrefp' if high else 'vrefn']))
                err=np.max(errors,axis=0)*1000
                use=(x>=0)&(t<base['next_sample_open_ns']-.02)
                axs[3,col].plot(x[use],err[use],color=color,label=LABELS[tag])
            axs[0,col].set_title(f"FF {base['temperature_c']:+g} C | baseline RST7 = {origin:.3f} ns")
            axs[0,col].axhline(.99,color='#555',ls='--',lw=1,label='0.99 V limit / high rail')
            axs[0,col].set(xlim=(-.15,1.6),ylim=(.972,1.069),ylabel='GNN4 / Vgb (V)')
            axs[1,col].axhline(.99,color='#555',ls='--',lw=1,label='0.99 V limit / low-gate baseline')
            axs[1,col].set(xlim=(-.15,1.6),ylabel='Worst PMOS |Vgb| (V)')
            axs[2,col].axhline(.9,color='#555',ls='--',lw=1,label='Nominal high reference')
            axs[2,col].set(xlim=(.18,.5),ylabel='BN7 reset edge (V)')
            a=axs[3,col];a.axhline(data['settling_band_mv'],color='#555',ls='--',lw=1,label='0.25 LSB = 1.758 mV')
            a.axvline(base['next_sample_open_ns']-origin,color='#777',ls=':',label='Next sample opens')
            a.set_yscale('symlog',linthresh=1)
            a.set(ylim=(-.05,2000),xlim=(0,base['next_sample_open_ns']-origin+1),ylabel='Max bottom-to-rail error (mV)')
            for row in range(4):
                axs[row,col].set_xlabel('Time from baseline RST7 rise (ns)');axs[row,col].grid(alpha=.18)
                axs[row,col].legend(fontsize=8,loc='best')
        fig.suptitle(f'Independent {family} experiment | L90 / Mmain 2 um / VDD 0.99 V\nNative transistor ADC + ideal diagnostic controls; sampling source unchanged\nFrame 1 idle reset, input differential -0.81 V; no noise / mismatch / PEX',fontsize=11)
        path=FIG/(family+'.png');fig.savefig(path);plt.close(fig);files[family]=dict(path=str(path.relative_to(ROOT)),sha256=sha(path))
    dump(VERIFY/'figures.json',files)

if __name__=='__main__':main()
