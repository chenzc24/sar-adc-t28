"""Selected real-load comparisons, preserving baseline versus candidate identity."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from prepare import ROOT
from analyze import load

def reference():
    run='sar8fix-loaded-ref-ffcold'
    col=ROOT/'output/managed_execution/runs'/run/'collected/derived'
    m,w,t,_=load(col)
    bm,bw,bt,_=load(ROOT/'output/sar8_stress_closure/rg1_strict200_ff_m40/stream_v1')
    r=json.loads((ROOT/'verification/sar8_physical_repair'/(run+'_analysis.json')).read_text())
    b=json.loads((ROOT/'verification/sar8_stress_closure/rg1_strict200_ff_m40_stream_analysis.json').read_text())
    fig,ax=plt.subplots(3,1,figsize=(10.5,8),layout='constrained')
    colors=['#2864a0','#c85637']
    for tt,ww,name,color in [(bt,bw,'Core L90 baseline',colors[0]),(t,w,'1.8 V reference / scale2',colors[1])]:
        for a,node,lo,hi,scale in [(ax[0],'xdut.gnn4',172.2,173.5,1),(ax[1],'xdut.xcdac.bp7',144.2,144.8,1000)]:
            ids=(tt>=lo)&(tt<=hi);a.plot(tt[ids],ww[node][ids]*scale,label=name,color=color,lw=1.5);a.set_xlim(lo,hi)
        upd=ww['xdut.phi_u'];ids=np.flatnonzero((upd[:-1]<.495)&(upd[1:]>=.495)&(tt[:-1]>140))
        k=ids[0];start=tt[k]+(.495-upd[k])*(tt[k+1]-tt[k])/(upd[k+1]-upd[k])
        select=(tt>=start)&(tt<=146.69);err=np.zeros(np.count_nonzero(select))
        for side in ['p','n']:
            for bit in range(8):
                gate='xdut.g%sp%d'%(side,bit);target=.9 if np.interp(146.69,tt,ww[gate])<.495 else 0.
                err=np.maximum(err,np.abs(ww['xdut.xcdac.b%s%d'%(side,bit)][select]-target))
        ax[2].semilogy(tt[select]-start,np.maximum(err*1000,1e-4),label=name,color=color,lw=1.5)
    ax[0].axhline(.99,color='#666',ls=':',label='VDD = 0.99 V (not IO limit)')
    ax[0].set(ylabel='GNN4 (V)',xlabel='Time (ns)')
    ax[1].axhline(0,color='#666',ls=':');ax[1].set(ylabel='BP7 (mV)',xlabel='Time (ns)',ylim=(-100,80))
    ax[1].scatter([b['bottom_min'][2]],[b['bottom_min'][0]],color=colors[0],s=20)
    ax[1].scatter([r['bottom_min']['time_ns']],[r['bottom_min']['value_v']*1000],color=colors[1],s=20)
    ax[1].text(.98,.07,'Native minima: %.2f / %.2f mV'%(b['bottom_min'][0],r['bottom_min']['value_v']*1000),transform=ax[1].transAxes,ha='right',fontsize=9)
    ax[2].axhline(1.7578125,color='#666',ls=':',label='0.25 LSB = 1.758 mV')
    ax[2].set(ylabel='Worst bottom error (mV)',xlabel='Time after bit7 update (ns)',ylim=(.1,1500))
    for a in ax:a.grid(alpha=.2);a.legend(fontsize=8,loc='best')
    fig.suptitle('Real CDAC / BBM load | FF, 0.99 V, -40 C\nOnly reference MOS changed; Bootstrap, comparator and control unchanged\n50 ohm input/reference sources, 4 pF decoupling; no noise, mismatch or PEX',fontsize=10)
    fig.savefig(ROOT/'docs/figures/sar8_physical_repair/loaded_reference_comparison.png',dpi=180);plt.close(fig)

def comparator():
    runs=['sar8fix-loaded-base-sscold','sar8fix-loaded-comp-sscold']
    data=[]
    for run in runs:
        _,w,t,_=load(ROOT/'output/managed_execution/runs'/run/'collected/derived')
        r=json.loads((ROOT/'verification/sar8_physical_repair'/(run+'_analysis.json')).read_text())
        data.append((w,t,r))
    colors=['#2864a0','#c85637'];labels=['Core baseline','N4 tolerant comparator']
    fig,ax=plt.subplots(4,2,figsize=(12,10),layout='constrained',sharex='col')
    extra=[]
    for col,decision in enumerate([0,7]):
        for (w,t,r),color,label in zip(data,colors,labels):
            q=[x for x in r['comparisons'] if x['frame']==1 and x['decision']==decision][0]
            start=q['clock_ns'];end=q['write_ns'];ids=(t>=start-.2)&(t<=end+.9);x=t[ids]-start
            diff=w['xdut.topp']-w['xdut.topn'];cm=(w['xdut.topp']+w['xdut.topn'])/2
            d0=np.interp(start-.02,t,diff);c0=np.interp(start-.02,t,cm)
            ax[0,col].plot(x,(diff[ids]-d0)*1000,color=color,label=label)
            ax[1,col].plot(x,(cm[ids]-c0)*1000,color=color,label=label)
            ax[2,col].plot(x,w['xdut.comp_p'][ids],color=color,label=label+' P')
            ax[2,col].plot(x,w['xdut.comp_n'][ids],color=color,ls='--',label=label+' N')
            ax[3,col].plot(x,w['xdut.cmp_clk'][ids],color=color,label=label+' CMP')
            for row in range(4):ax[row,col].axvline(end-start,color=color,ls=':',alpha=.7)
            ax[3,col].annotate('write',xy=(end-start,.45),color=color,rotation=90,fontsize=8)
            extra.append(dict(run= r['run_id'],decision=decision,clock_ns=start,write_ns=end,
                output_p_at_write_v=float(np.interp(end,t,w['xdut.comp_p'])),
                output_n_at_write_v=float(np.interp(end,t,w['xdut.comp_n'])),
                input_diff_at_clock_mv=float(d0*1000)))
        ax[0,col].set_title('Frame 2: '+('first comparison (bit7)' if decision==0 else 'last comparison (bit0)'))
        ax[0,col].axhline(0,color='#777',lw=.7);ax[1,col].axhline(0,color='#777',lw=.7)
        ax[2,col].axhline(.81,color='#777',ls=':',lw=.7)
        ax[3,col].set_xlabel('Time after each CMP rising edge (ns)')
        for row,label in enumerate(['Top differential change (mV)','Top common-mode change (mV)',
                                    'Raw comparator output (V)','CMP clock (V)']):
            ax[row,col].set_ylabel(label);ax[row,col].grid(alpha=.2)
        ax[0,col].legend(fontsize=8);ax[2,col].legend(fontsize=7,ncol=2)
    fig.suptitle('SS / 0.81 V / -40 C | only comparator changed; actual CDAC and downstream logic\n'+
                 '50 ohm input/reference, 4 pF reference decoupling; no noise, mismatch or PEX\n'+
                 'Aligned by CMP, not absolute time; dotted colored lines = actual write; motion includes circuit settling',fontsize=10)
    fig.savefig(ROOT/'docs/figures/sar8_physical_repair/loaded_comparator_comparison.png',dpi=180);plt.close(fig)
    (ROOT/'verification/sar8_physical_repair/loaded_comparator_write_levels.json').write_text(json.dumps(extra,indent=2)+'\n')
    fig,ax=plt.subplots(3,1,figsize=(10.5,7),sharex=True,layout='constrained')
    for (w,t,r),color,label in zip(data,colors,labels):
        ids=(t>=180)&(t<=200)
        ax[0].plot(t[ids],np.minimum(w['xdut.comp_p'][ids],w['xdut.comp_n'][ids]),color=color,label=label+' min(P,N)')
        ax[1].plot(t[ids],w['xdut.cmp_clk'][ids],color=color,label=label+' CMP')
        ax[2].plot(t[ids],w['xdut.xref.rst0'][ids],color=color,label=label+' final bit reset')
    ax[0].axhline(.81,color='#777',ls=':',label='VDD');ax[0].set_ylabel('Comparator reset (V)')
    ax[1].set_ylabel('CMP (V)');ax[2].set_ylabel('RST0 (V)');ax[2].set_xlabel('Absolute time (ns)')
    for a in ax:a.legend(fontsize=8);a.grid(alpha=.2)
    fig.suptitle('SS / 0.81 V / -40 C | actual reset recovery before next cycle\n'+
                 'Core reference and physical control unchanged; ideal external clock/supplies; no noise/mismatch/PEX',fontsize=10)
    fig.savefig(ROOT/'docs/figures/sar8_physical_repair/loaded_reset_comparison.png',dpi=180);plt.close(fig)

if __name__=='__main__':reference();comparator()
