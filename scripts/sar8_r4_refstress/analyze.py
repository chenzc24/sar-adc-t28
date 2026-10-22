"""Map native terminal stress to circuit nodes and timing; no circuit changes."""
from pathlib import Path
import sys,json,re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
from common import sha,read,dump,records,blocks,SOURCE

def main():
    folder=ROOT/'output/sar8_r4_refstress/replay01'
    result=read(folder/'result.json');assert result['ok'],result['errors']
    assert sha(folder/'refstress.scs')==result['deck_sha256']
    assert blocks((folder/'refstress.scs').read_text())==blocks((SOURCE/'dut.scs').read_text())
    assert sha(folder/'wave.npz')==read(folder/'wave_receipt.json')['sha256']
    w=dict(np.load(folder/'wave.npz'));t=w['time']*1e9
    log=(Path(result['metadata']['output_dir']).parent/'spectre.out').read_text(errors='replace')
    assert 'spectre completes with 0 errors' in log and 'WARNING (CMI-' in log
    assert t[-1]>=450-1e-5
    rows=records(log,'R4MEAS')
    ref=read(ROOT/'output/sar8_r4_performance/cases/sine_cx_1024_k461/analysis.json')['frames']
    assert len(rows)==4 and [int(x[1]) for x in rows]==[x['code'] for x in ref[:4]]
    mask=(t>=400.8)&(t<=403)
    x=t[mask]
    def v(name):return w[name.lower()][mask]
    vals={name:v(name) for name in ['XDUT.SAMPLE_INT','XDUT.CMP_CLK','XDUT.XREF.Q6','XDUT.XREF.Q7',
        'XDUT.XREF.CAP_CLK','XDUT.GNP6','XDUT.GNN6','XDUT.GPP6','XDUT.GPN6',
        'XDUT.XCDAC.BN6','XDUT.XCDAC.BP6','XDUT.TOPP','XDUT.TOPN','VREFP','VREFN','VDD!',
        'VINP','VINN','XDUT.XBOOTP.G','XDUT.XBOOTN.G']}
    stresses={
      'XSN6 MN_LOW |Vbd|':abs(v('XDUT.XCDAC.BN6')),
      'XSN6 MN_LOW |Vds|':abs(v('XDUT.XCDAC.BN6')-v('VREFN')),
      'XSP6 MP_HIGH |Vbd|':abs(v('VDD!')-v('XDUT.XCDAC.BP6')),
      'XSP6 MP_HIGH |Vds|':abs(v('XDUT.XCDAC.BP6')-v('VREFP')),
      'XSN6 MN_LOW |Vgb|':abs(v('XDUT.GNN6')),
    }
    peaks={}
    for name,arr in stresses.items():
        i=int(np.argmax(arr));bad=arr>.99
        peaks[name]=dict(peak_v=float(arr[i]),time_ns=float(x[i]),
             first_saved_exceed_ns=float(x[bad][0]) if bad.any() else None,
             last_saved_exceed_ns=float(x[bad][-1]) if bad.any() else None)
    primary=stresses['XSN6 MN_LOW |Vbd|'];im=int(np.argmax(primary));tp=x[im]
    def crosses(arr,level,direction):
        ids=np.where((arr[:-1]<level)&(arr[1:]>=level) if direction>0 else (arr[:-1]>level)&(arr[1:]<=level))[0]
        return [float(x[i]+(level-arr[i])*(x[i+1]-x[i])/(arr[i+1]-arr[i])) for i in ids]
    edges={}
    for name,direction in [('XDUT.SAMPLE_INT',1),('XDUT.XREF.Q6',-1),('XDUT.XREF.Q7',1),('XDUT.GNN6',1),('XDUT.GNP6',1)]:
        edges[name]=crosses(vals[name],.45,direction)
    samples={str(time):{name:float(np.interp(time,x,arr)) for name,arr in vals.items()} for time in (401.0,401.15,float(tp),401.6,402.0)}
    near=(x[:-1]>tp-.025)&(x[:-1]<tp+.025)
    settings={key:(re.findall(r'(?m)^\s*'+re.escape(key)+r' = (.+)$',log) or [None])[-1] for key in ('maxstep','reltol','abstol(V)','abstol(I)','method','relref','outputstart')}
    out=dict(source='replay01; unchanged R4; full-sine history until450ns',peaks=peaks,edges_50pct_ns=edges,
         node_values_at_peak={name:float(arr[im]) for name,arr in vals.items()},selected_samples=samples,
         saved_max_gap_near_peak_ps=float(np.max(np.diff(x)[near])*1e3),
         first4codes=[int(r[1]) for r in rows],matches_long_run=True,effective_settings=settings,
         DUT_sha256=sha(SOURCE/'dut.scs'),deck_sha256=sha(folder/'refstress.scs'),log_sha256=sha(Path(result['metadata']['output_dir']).parent/'spectre.out'),
         native_CMI_lines=[line.strip() for line in log.splitlines() if 'WARNING (CMI-' in line],
         result_sha256=sha(folder/'result.json'),wave_sha256=sha(folder/'wave.npz'))
    dump(ROOT/'verification/sar8_r4_refstress/results.json',out)
    print(json.dumps(out,indent=2))
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(5,1,figsize=(12,11),sharex=True,layout='constrained',height_ratios=[1.3,1,1,1.2,1.2])
    fig.suptitle('R4 reference-switch stress | TT, 0.9 V, 27 C | continuous 4.501953 MHz sine, -1 dBFS',fontsize=12)
    colors=['#247e89','#c86143','#8464a0','#5a6c7d']
    for i,(name,label) in enumerate([('XDUT.CMP_CLK','CMP_CLK'),('XDUT.XREF.Q6','Q6'),('XDUT.XREF.Q7','Q7'),('XDUT.SAMPLE_INT','SAMPLE_INT')]):
        axes[0].plot(x,vals[name]/.9+i*1.3,color=colors[i],lw=1.4)
    axes[0].set_yticks([.45+i*1.3 for i in range(4)],['CMP_CLK','Q6','Q7','SAMPLE_INT'])
    axes[0].set_ylabel('Separate logic traces\n(each 0 to 0.9 V)')
    for name,label,col in [('XDUT.GNN6','N6 low-side NMOS gate',colors[0]),('XDUT.GNP6','N6 high-side PMOS gate',colors[1])]:
        axes[1].plot(x,vals[name],label=label,color=col)
    axes[1].set_ylabel('Gate voltage (V)');axes[1].legend(loc='upper right',fontsize=9)
    for name,label,col in [('XDUT.TOPP','TOPP',colors[0]),('XDUT.TOPN','TOPN',colors[1])]:axes[2].plot(x,vals[name],label=label,color=col)
    axes[2].set_ylabel('Top plate (V)');axes[2].legend(loc='upper right',fontsize=9)
    for name,label,col in [('XDUT.XCDAC.BN6','BN6',colors[0]),('XDUT.XCDAC.BP6','BP6',colors[1])]:axes[3].plot(x,vals[name],label=label,color=col)
    axes[3].plot(x,v('VREFP'),'--',color='.45',label='VREFP');axes[3].plot(x,v('VREFN'),':',color='.45',label='VREFN')
    axes[3].set_ylabel('Bottom / reference (V)');axes[3].legend(loc='center right',ncol=2,fontsize=9)
    for (name,arr),col in zip(list(stresses.items())[:3],colors):axes[4].plot(x,arr,label=name,color=col)
    axes[4].axhline(.99,color='#b32828',ls='--',label='Model limit: 0.99 V')
    axes[4].set(ylabel='Terminal stress (V)',xlabel='Time (ns)',ylim=(.85, max(1.02,max(p['peak_v'] for p in peaks.values())+.025)))
    axes[4].legend(loc='lower right',fontsize=8)
    axes[4].annotate(f'{primary[im]:.4f} V\n{tp:.4f} ns',xy=(tp,primary[im]),xytext=(tp+.3,primary[im]+.008),arrowprops={'arrowstyle':'->'},fontsize=9)
    bad=np.any(np.array(list(stresses.values()))>.99,axis=0)
    for ax in axes:
        ax.grid(alpha=.18);ax.set_xlim(400.9,402.1)
        if bad.any():ax.axvspan(x[bad][0],x[bad][-1],color='#d97a49',alpha=.16)
        for edge in edges['XDUT.SAMPLE_INT'][:1]:ax.axvline(edge,color='.5',ls=':',lw=.8)
    fig.supxlabel('Shading: sampled >0.99 V interval. Dotted line: acquisition starts. Native adaptive samples.\nUnchanged transistor R4; short CX1 replay. Ideal sources; reference network: 50 ohm + 4 pF per rail.',fontsize=9)
    dest=ROOT/'docs/figures/sar8_r4_refstress';dest.mkdir(parents=True,exist_ok=True)
    fig.savefig(dest/'reference_reset_stress.png',dpi=170);plt.close(fig)
    fig,ax=plt.subplots(2,1,figsize=(10,6),sharex=True,layout='constrained')
    fig.suptitle('Acquisition / reference-reset overlap | same R4 replay, TT 0.9 V 27 C',fontsize=12)
    for name,label,col in [('XDUT.XCDAC.BN6','BN6',colors[0]),('XDUT.XCDAC.BP6','BP6',colors[1]),('VREFP','VREFP','#888888'),('VREFN','VREFN','#aaaaaa')]:
        ax[0].plot(x,vals[name],label=label,color=col)
    ax[0].axhline(.9,color='.5',ls=':',lw=.7);ax[0].axhline(0,color='.5',ls=':',lw=.7)
    ax[0].set_ylabel('Node voltage (V)');ax[0].legend(loc='center left',ncol=2,fontsize=9)
    for name,col in [('XSN6 MN_LOW |Vbd|',colors[0]),('XSP6 MP_HIGH |Vbd|',colors[1])]:
        arr=stresses[name];i=int(np.argmax(arr));ax[1].plot(x,arr,'.-',label=name,color=col,ms=3)
        ax[1].annotate(f'{arr[i]:.4f} V',xy=(x[i],arr[i]),xytext=(401.341 if 'XSN' in name else 401.366,arr[i]+.003),fontsize=9,arrowprops={'arrowstyle':'->','color':col})
    ax[1].axhline(.99,color='#b32828',ls='--',label='0.99 V model limit')
    ax[1].set(xlabel='Time (ns)',ylabel='Terminal stress (V)',ylim=(.92,1.03))
    ax[1].legend(loc='lower left',fontsize=8)
    for a in ax:
        a.set_xlim(401.33,401.39);a.grid(alpha=.18)
        a.ticklabel_format(axis='x',style='plain',useOffset=False)
        a.axvspan(x[bad][0],x[bad][-1],color='#d97a49',alpha=.16)
    fig.supxlabel('Dots: saved adaptive samples; linear joins, no smoothing. This event is not a whole-run worst-case bound.',fontsize=9)
    fig.savefig(dest/'reference_reset_stress_zoom.png',dpi=170);plt.close(fig)

if __name__=='__main__':main()
