"""Width sweep native settling/turn-off figures, no synthetic waveforms."""
import gzip
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from width_flow import ROOT,OUT,VERIFY,NAMES,read
FIG=ROOT/'docs/figures/sar8_main_width'
COLORS=['#777777','#2676b8','#d78026','#269780']
plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})

def main():
    FIG.mkdir(parents=True,exist_ok=True)
    fig,axs=plt.subplots(3,2,figsize=(11.8,9.4),layout='constrained')
    fig.suptitle('Mmain total-width sweep: acquisition and turn-off\nT28 SS | VDD 0.81 V | -40 C | VREF 0/0.9 V, CM 0.45 V | 10 MS/s\nNative frozen ADC except parallel Mmain units | ideal external sources/SAMPLE | no mismatch/noise/PEX | CX',fontsize=10)
    for index,name in enumerate(NAMES):
        report=read(VERIFY/(name+'.json'))
        with gzip.open(OUT/name/'reduced/reduced.json.gz','rt') as f:raw=json.load(f)
        w={k:np.array(v) for k,v in raw['wave'].items()};t=w['time']*1e9
        error=(w['xdut.topp']-w['xdut.topn']-w['vinp_src']+w['vinn_src'])*1e3
        for col,frame in enumerate([1,2]):
            lo=frame*100;mask=(t>=lo)&(t<=lo+42);zoom=(t>=lo+40.5)&(t<=lo+42)
            f=report['frames'][frame];label=f'{index+1} um';color=COLORS[index]
            axs[0,col].plot(t[mask]-lo,error[mask],color=color,label=label)
            if index:
                axs[1,col].plot(t[zoom]-lo,error[zoom],color=color,label=label)
                axs[1,col].scatter([f['preclose_time_ns']-lo,41.8],[f['settling_error_mv'],f['held_error_mv']],color=color,s=14,zorder=5)
            side='p' if frame==1 else 'n'
            axs[2,col].plot(t[zoom]-lo,(w['xdut.xboot'+side+'.g']-w['vin'+side])[zoom],color=color,label=label)
    for col,title in enumerate(['P discharges: +0.81 -> -0.81 V','N discharges: -0.81 -> +0.81 V']):
        axs[0,col].set_title(title);axs[0,col].set_yscale('symlog',linthresh=1.8)
        for row in [0,1]:
            axs[row,col].axhspan(-1.7578125,1.7578125,color='#269780',alpha=.12)
            axs[row,col].axhline(0,color='#555',lw=.6)
        axs[1,col].set_title('2/3/4 um; dots = preclose / held; green = +/-0.25 LSB',fontsize=9)
        for row in range(3):
            axs[row,col].grid(alpha=.18);axs[row,col].legend(ncol=2,fontsize=8)
            axs[row,col].set_xlabel('Time from frame start (ns)')
        for row in [1,2]:
            axs[row,col].axvline(41.8,color='#777',ls=':',lw=.8)
            axs[row,col].set_xlim(40.9,42)
        axs[2,col].axhline(.81,color='#777',ls='--',lw=.8)
        axs[2,col].set_title('Dotted: held measurement 41.8 ns | dashed: VDD',fontsize=9)
    for row,label in enumerate(['Differential error (mV)','Turn-off window error (mV)','Discharging Mmain VGS (V)']):axs[row,0].set_ylabel(label)
    fig.savefig(FIG/'width_timing.png',dpi=170);plt.close(fig)
    selection=read(VERIFY/'selection.json');rows=selection['rows'];x=np.arange(len(rows))
    fig,ax=plt.subplots(figsize=(9.5,5),layout='constrained')
    ax.bar(x-.18,[r['max_abs_preclose_mv'] for r in rows],.36,label='Max |preclose settling error|',color='#2676b8')
    ax.bar(x+.18,[r['max_abs_held_mv'] for r in rows],.36,label='Max |held error|',color='#269780')
    ax.axhline(1.7578125,ls='--',color='#c94b3e',label='0.25 LSB = 1.758 mV')
    ax.set_yscale('log');ax.set_xticks(x,[f'{r["width_um"]} um' for r in rows]);ax.set_ylabel('Absolute error (mV)')
    ax.set_title('SS / 0.81 V / -40 C: frames 1-5, including both reversal directions\nSame timing and CDAC; startup reported separately; no mismatch/noise/PEX',fontsize=10)
    ax.grid(axis='y',alpha=.2);ax.legend(fontsize=8)
    fig.savefig(FIG/'width_errors.png',dpi=170);plt.close(fig)
    print('Figures saved',FIG)

if __name__=='__main__':main()
