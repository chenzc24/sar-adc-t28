"""Scientific figures from saved native traces; no waveform fabrication."""
import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flow import OUT,ROOT,read

FIG=ROOT/'docs/figures/sar8_r4_staged'
LABEL={'a_600':'A control','lsb_600':'LSB first','msb_600':'MSB first',
       'rhalf_600':'Gate R / 2','drive2_600':'Final driver 2x'}
COLORS=['#555b66','#3176b5','#b95638','#239078','#905fb0']
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})


def finish(fig,name):
    FIG.mkdir(parents=True,exist_ok=True)
    fig.savefig(FIG/name,dpi=170,bbox_inches='tight');plt.close(fig)


def screen():
    names=list(LABEL);data={n:read(OUT/n/'analysis.json') for n in names}
    fig,axs=plt.subplots(2,2,figsize=(12,7),layout='constrained')
    fig.suptitle('Reference reset screening | T28 TT, 0.9 V, 27 C, 10 MS/s\n'
                 '4.501953125 MHz sine, -1 dBFS | native MOS, RC drivers; ideal external sources',fontsize=12)
    for col,subset in enumerate([names[:3],[names[0],*names[3:]]]):
        for n in subset:
            w=np.load(OUT/n/'stress_envelopes.npz');t=w['time']*1e9;mask=(t>=500.8)&(t<=508)
            axs[0,col].plot(t[mask],w['reference'][mask],label=LABEL[n],color=COLORS[names.index(n)])
        axs[0,col].axhline(.99,color='#b13232',ls='--',lw=1,label='0.99 V limit')
        axs[0,col].set(xlabel='Time (ns)',ylabel='Max reference terminal stress (V)',title=['Reset order','Gate holding'][col])
        axs[0,col].legend(fontsize=9);axs[0,col].grid(alpha=.2)
    peaks=[data[n]['groups']['reference']['peak_v'] for n in names]
    bars=axs[1,0].bar(np.arange(5),peaks,color=COLORS)
    for bar,y in zip(bars,peaks):axs[1,0].text(bar.get_x()+bar.get_width()/2,y+.002,f'{y:.4f}',ha='center',fontsize=9)
    axs[1,0].axhline(.99,color='#b13232',ls='--',lw=1)
    axs[1,0].set(xticks=range(5),xticklabels=['A','LSB first','MSB first','R / 2','Drive 2x'],
                 ylabel='Peak (V)',title='All 32 reference MOS, 6 terminal pairs, 0-600 ns',ylim=(min(.9,min(peaks)-.02),max(peaks)+.025))
    widths=[min(a['duration_ns'] for a in data[n]['acquisitions']) for n in names]
    axs[1,1].bar(np.arange(5),widths,color=COLORS)
    for i,y in enumerate(widths):axs[1,1].text(i,y+.3,f'{y:.2f}',ha='center')
    axs[1,1].set(xticks=range(5),xticklabels=['A','LSB first','MSB first','R / 2','Drive 2x'],
                 ylabel='Control-high duration (ns)',title='Minimum Bootstrap acquisition command window',ylim=(0,43))
    finish(fig,'screen.png')


def detail(names,lo,hi,stem):
    fig,axs=plt.subplots(4,1,figsize=(12,10),sharex=True,layout='constrained')
    fig.suptitle('Reset transient | T28 TT, 0.9 V, 27 C | 10 MS/s, sine -1 dBFS\n'
                 'Native ADC and gate drivers; ideal external sources | 0.99 V core screen',fontsize=12)
    for j,n in enumerate(names):
        w=np.load(OUT/n/'wave.npz');t=w['time']*1e9;m=(t>=lo)&(t<=hi)
        color=COLORS[list(LABEL).index(n)] if n in LABEL else COLORS[j]
        label=LABEL.get(n,n)
        axs[0].plot(t[m],w['xdut.seq_sample'][m],label=label,color=color)
        axs[1].plot(t[m],w['xdut.xcdac.bp6'][m],color=color)
        axs[2].plot(t[m],w['xdut.gnn3'][m],color=color)
        # Positive current enters resistor at its gate end: removal from GNN3.
        axs[3].plot(t[m],w['xdut.xref.xdrv3.rgnn1_5__dmy0:2'][m]*1e6,color=color)
    axs[0].legend(fontsize=9);axs[0].set_ylabel('Bootstrap enable (V)')
    axs[1].axhline(-.09,color='#b13232',ls='--',lw=1,label='BP6 lower bound: -90 mV')
    axs[1].axhline(0,color='#888888',ls=':',lw=1);axs[1].legend(fontsize=9);axs[1].set_ylabel('P bit6 bottom plate (V)')
    axs[2].axhline(.99,color='#b13232',ls='--',lw=1,label='GNN3 upper bound: 0.99 V')
    axs[2].axhline(.9,color='#888888',ls=':',lw=1);axs[2].legend(fontsize=9);axs[2].set_ylabel('N bit3 low-switch gate (V)')
    axs[3].axhline(0,color='#888888',ls=':',lw=1);axs[3].set(ylabel='GNN3 to gate resistor (uA)',xlabel='Time (ns)',xlim=(lo,hi))
    for ax in axs:ax.grid(alpha=.2)
    finish(fig,stem+'.png')


def validation():
    name='msb_4600';a=read(OUT/name/'analysis.json');w=np.load(OUT/name/'stress_envelopes.npz');t=w['time']*1e9
    fig,axs=plt.subplots(3,1,figsize=(12,8),layout='constrained')
    fig.suptitle('MSB-first validation | T28 TT, 0.9 V, 27 C, 10 MS/s\n'
                 'Native MOS; ideal external sources | continuous sine, 4.501953125 MHz, -1 dBFS',fontsize=12)
    for group,label,color in [('reference','32 reference switches','#b95638'),('reference_driver','224 reference-driver MOS','#3176b5')]:
        peaks=[float(w[group][(t>=i*100)&(t<(i+1)*100)].max()) for i in range(46)]
        axs[0].plot(range(46),peaks,'.-',ms=3,label=label,color=color)
    axs[0].axhline(.99,color='#b13232',ls='--',lw=1,label='0.99 V limit')
    axs[0].set(xlabel='Frame index',ylabel='Per-frame peak stress (V)',title='Complete 0-4.6 us adaptive record');axs[0].legend(fontsize=9)
    for n,label,color in [('msb_600','CX, 600 ns','#b95638'),('msb_precise300','Honored settings, 300 ns','#3176b5')]:
        e=np.load(OUT/n/'stress_envelopes.npz');tt=e['time']*1e9;m=(tt>=201.1)&(tt<=201.8)
        axs[1].plot(tt[m],e['reference'][m],label=label,color=color,
                    lw=2.6 if n=='msb_600' else 1.3,ls='-' if n=='msb_600' else '--')
    axs[1].axhline(.99,color='#b13232',ls='--',lw=1);axs[1].set(xlabel='Time (ns)',ylabel='Reference stress (V)',title='Numerical cross-check at short-screen worst event');axs[1].legend(fontsize=9)
    old=read(ROOT/'output/sar8_r4_reset/reset_first_c20_late4600/analysis.json')
    from flow import prior
    baseline=read(prior.SOURCE/'analysis.json')
    extent=1
    for source,label,color,offset in [(old,'vs A reset-first','#555b66',-.16),(baseline,'vs frozen R4','#3176b5',.16)]:
        diff=[f['code']-source['frames'][f['frame']]['code'] for f in a['frames']]
        extent=max(extent,max(abs(x) for x in diff))
        axs[2].bar(np.arange(len(diff))+offset,diff,width=.3,label=label,color=color)
    axs[2].set(xlabel='Frame index',ylabel='Output code difference',title='Diagnostic comparison; acquisition timing is not identical',yticks=range(-extent,extent+1),ylim=(-extent-.3,extent+.3));axs[2].legend(fontsize=9)
    for ax in axs:ax.grid(alpha=.2)
    finish(fig,'validation.png')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['screen','detail','validation']);p.add_argument('names',nargs='*')
    p.add_argument('--lo',type=float,default=500.8);p.add_argument('--hi',type=float,default=504)
    p.add_argument('--stem',default='detail');a=p.parse_args()
    if a.mode=='screen':screen()
    elif a.mode=='validation':validation()
    else:detail(a.names,a.lo,a.hi,a.stem)
