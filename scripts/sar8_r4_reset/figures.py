"""Plot the completed short A/B cases and curate their reproducible evidence."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from experiment import ROOT,OUT,read,dump,cells,TOP,sha


CASES=[('base_cx_500','R4 baseline','#c45442'),
       ('reset_first_c20_500','A: reset before sampling','#288779'),
       ('sample_first_c20_500','B: sample before reset','#6759a2')]


def main():
    dest=ROOT/'docs/figures/sar8_r4_reset';dest.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(4,1,figsize=(12,10),sharex=True,layout='constrained')
    overview=[]
    for name,label,color in CASES:
        folder=OUT/name;r=read(folder/'analysis.json');ctx=read(folder/'context.json')
        w=np.load(folder/'wave.npz');env=np.load(folder/'stress_envelopes.npz');t=w['time']*1e9
        m=(t>=400.7)&(t<=405)
        sample='xdut.seq_sample' if ctx['kind']=='reset_first' else 'xdut.sample_int'
        reset='xdut.seq_sample' if ctx['kind']=='sample_first' else 'xdut.sample_int'
        ax[0].plot(t[m],w[sample][m],label=label,color=color,lw=1.4)
        ax[1].plot(t[m],w[reset][m],color=color,lw=1.4)
        word=sum((w[f'xdut.xref.q{i}']>.45).astype(int)*(2**i) for i in range(8))
        ax[2].step(t[m],word[m],where='post',color=color,lw=1.4)
        ax[3].plot(t[m],env['reference'][m],color=color,lw=1.5)
        overview.append(dict(name=name,kind=ctx['kind'],groups=r['groups'],
           codes=[f['code'] for f in r['frames']],timing_pass=r['all_frame_timing_pass'],
           saved_stress_pass=r['all_saved_stress_pass'],settings=r['effective_settings'],
           edges=r['edges_50pct_ns'],DUT_sha256=ctx['DUT_sha256'],wave_sha256=r['wave_sha256']))
    ax[0].set_ylabel('Bootstrap enable (V)');ax[0].legend(loc='upper right',fontsize=9)
    ax[1].set_ylabel('Reference reset (V)')
    ax[2].set_ylabel('Reference word')
    ax[3].set_ylabel('Reference MOS\nmax terminal |V| (V)')
    ax[3].axhline(.99,color='black',ls='--',lw=1,label='0.99 V screen')
    ax[3].set(ylim=(.88,1.04),xlabel='Time (ns)');ax[3].legend(fontsize=9)
    for a in ax:a.grid(alpha=.2);a.set_xlim(400.7,405);a.ticklabel_format(axis='x',useOffset=False)
    fig.suptitle('R4 reset sequencing | all 32 reference MOS, all six terminal pairs',fontsize=14)
    fig.supxlabel('TT 0.9 V 27°C | 10 MS/s, continuous 4.501953 MHz sine, −1 dBFS | native MOS/PDK-RC sequencing\nExternal sources ideal; reference 50 Ω + 4 pF/rail. Same-size analog core. CX screening, not PVT qualification.',fontsize=9)
    fig.savefig(dest/'sequencing_comparison.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(12,6),sharex=True,layout='constrained')
    for side,a in zip('PN',axes):
        for j,(name,label,color) in enumerate(CASES):
            r=read(OUT/name/'analysis.json')
            peak=[max(s['peak_v'] for s in r['stresses'] if s['instance'].startswith(f'XDUT.XCDAC.XS{side}{b}.')) for b in range(8)]
            a.bar(np.arange(8)+(j-1)*.25,peak,width=.24,color=color,label=label)
        a.axhline(.99,color='black',ls='--',lw=1)
        a.set(ylabel=f'{side}-side max |V| (V)',ylim=(.85,1.04));a.grid(axis='y',alpha=.2)
    axes[0].legend(loc='upper left',fontsize=9,ncol=3)
    axes[1].set(xticks=range(8),xlabel='CDAC bit (0 = LSB, 7 = MSB)')
    fig.suptitle('Worst reference-switch stress by bit | entire 0–500 ns record, including startup',fontsize=13)
    fig.supxlabel('TT 0.9 V 27°C | all saved adaptive samples, six terminal pairs per MOS | dashed line: 0.99 V\nA falls below the screen by only 0.58 mV: no robustness claim.',fontsize=9)
    fig.savefig(dest/'stress_by_bit.png',dpi=180);plt.close(fig)
    out=ROOT/'verification/sar8_r4_reset';out.mkdir(parents=True,exist_ok=True)
    dump(out/'short_comparison.json',overview)
    # Mechanical curated fragments reference the unchanged frozen definitions.
    nd=ROOT/'netlist/sar8_r4_reset';nd.mkdir(parents=True,exist_ok=True)
    c=cells((OUT/'reset_first_c20_500/dut.scs').read_text())
    fragment='// Experimental native cells only; not exported to Virtuoso OA.\n'
    fragment+='// Include ../sar8_physical/dut.scs before this file; PDK includes remain external.\n'
    fragment+=c['sar8r_delay']+'\n'+c['sar8r_edge']+'\n'
    for name,_,_ in CASES[1:]:
        case=cells((OUT/name/'dut.scs').read_text());kind=read(OUT/name/'context.json')['kind']
        fragment+=case[TOP].replace(TOP,'sar8r_'+kind)+'\n'
    (nd/'variants.scs').write_text(fragment.rstrip()+'\n',encoding='utf-8')
    dump(nd/'provenance.json',dict(frozen_DUT_sha256=sha(ROOT/'netlist/sar8_physical/dut.scs'),
         variant_sha256=sha(nd/'variants.scs'),OA_changed=False,source_cases=[n for n,_,_ in CASES]))
    print('FIGURES_AND_PROVENANCE_COMPLETE')


if __name__=='__main__':main()
