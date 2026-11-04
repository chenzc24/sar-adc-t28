"""Plot native-time reset stress, without decimation."""
import csv, gzip
import numpy as np
import matplotlib.pyplot as plt


def plot_reset(col, figdir, environment):
    with gzip.open(col/'derived/reset_native.csv.gz','rt') as f:
        rows=list(csv.DictReader(f))
    z={k:np.array([float(q[k]) for q in rows]) for k in rows[0]}
    tx=(z['time']-110e-9)*1e12
    fig,ax=plt.subplots(4,1,figsize=(10,10),sharex=True,layout='constrained')
    ax[0].plot(tx,z['clks'],label='Sample clock')
    ax[0].plot(tx,z['xadc.dn_1'],label='N-side 1C reference gate')
    ax[0].plot(tx,z['xadc.dp_7'],'--',label='N-side 64C reference gate')
    ax[0].set_ylabel('Control (V)');ax[0].legend(fontsize=8,ncol=3)
    ax[1].plot(tx,z['xadc.topn'],label='N top plate')
    ax[1].plot(tx,z['vinn'],'--',label='New N input')
    ax[1].set_ylabel('Top / input (V)');ax[1].legend(fontsize=8)
    ax[2].plot(tx,z['xadc.xn.xd.net1'],label='N bottom 1C')
    ax[2].plot(tx,z['xadc.xn.xd.net6'],'--',label='N bottom 32C')
    ax[2].plot(tx,z['refn'],':',label='Low reference')
    ax[2].axhline(-.09,color='r',ls='--',lw=.8,label='-90 mV stress boundary')
    ax[2].set_ylabel('Bottom plate (V)');ax[2].legend(fontsize=8,ncol=2)
    stress=z['refp']-z['xadc.xn.xd.net1']
    ax[3].plot(tx,stress,label='M12 |VDS| = |VBD|')
    ax[3].axhline(.99,color='r',ls='--',label='PDK 0.99 V limit')
    ax[3].fill_between(tx,.99,stress,where=stress>.99,color='r',alpha=.25)
    ax[3].set_ylabel('PMOS terminal (V)');ax[3].set_xlabel('Time relative to 110 ns (ps)');ax[3].legend(fontsize=8)
    peak=int(np.argmax(stress))
    ax[3].annotate('%.6f V at %.3f ps'%(stress[peak],tx[peak]),xy=(tx[peak],stress[peak]),xytext=(55,.80),arrowprops={'arrowstyle':'->'},fontsize=9)
    for x in ax:
        x.axvline(25,color='gray',ls=':',lw=.8);x.set_xlim(0,100);x.grid(alpha=.2)
    fig.suptitle('Reset / sampling overlap: code 0 to 255\n'+environment+'\nFull native time points; dotted line = sample clock 50% crossing',fontsize=11)
    fig.savefig(figdir/'reset_stress.png',dpi=165);plt.close(fig)
    keys=['clks','xadc.dn_1','xadc.dp_7','xadc.topn','vinn','xadc.xn.xd.net1']
    print('At stress peak:',{k:z[k][peak] for k in keys})
