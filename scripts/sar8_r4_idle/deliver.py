"""Curated evidence and uncluttered native-wave timing/stress figures."""
import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flow import ROOT, OUT, read, dump, sha, cells, prior

FIG=ROOT/'docs/figures/sar8_r4_idle'
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
COLORS=['#677381','#007f86','#bc6136']
ENV='T28 TT | 0.9 V | 27 C | 10 MS/s | 4.502 MHz sine, -1 dBFS\nNative MOS + RC control; ideal external input, supplies and SAMPLE'


def finish(fig,name):
    FIG.mkdir(parents=True,exist_ok=True)
    fig.savefig(FIG/name,dpi=170,bbox_inches='tight');plt.close(fig)


def timing(name):
    z=np.load(OUT/name/'wave.npz'); old=np.load(ROOT/'output/sar8_r4_staged/msb_600/wave.npz')
    t=z['time']*1e9; to=old['time']*1e9
    fig,axs=plt.subplots(5,1,figsize=(12,11),sharex=True,layout='constrained')
    fig.suptitle('Reference reset moved before the next acquisition\n'+ENV,fontsize=12)
    a=read(OUT/name/'analysis.json'); idle=a['idle_checks'][0]
    lo,hi=65,145; m=(t>=lo)&(t<=hi);mo=(to>=lo)&(to<=hi)
    axs[0].plot(t[m],z['xdut.active'][m],color=COLORS[1],label='ACTIVE (new)')
    axs[0].plot(t[m],z['xdut.xref.cap_clk'][m],color=COLORS[2],label='Reference capture clock (new)')
    axs[0].set_ylabel('Conversion (V)')
    for k,bit in enumerate([7,4,0]):
        axs[1].plot(t[m],z[f'xdut.xref.rst{bit}'][m],color=[COLORS[1],COLORS[2],COLORS[0]][k],label=f'Reset bit {bit} (new)')
    axs[1].plot(to[mo],old['xdut.xref.rst7'][mo],ls='--',lw=1,color='black',label='Reset bit 7 (old)')
    axs[1].set_ylabel('Reference reset (V)')
    axs[2].plot(to[mo],old['xdut.seq_sample'][mo],color=COLORS[0],ls='--',label='Old: reset inside acquisition')
    axs[2].plot(t[m],z['xdut.seq_sample'][m],color=COLORS[1],label='New: reset in previous idle')
    axs[2].set_ylabel('Bootstrap enable (V)')
    axs[3].plot(to[mo],old['xdut.xbootp.g'][mo],color=COLORS[0],ls='--',label='Main gate P (old)')
    axs[3].plot(t[m],z['xdut.xbootp.g'][m],color=COLORS[1],label='Main gate P (new)')
    axs[3].set_ylabel('Main MOS gate (V)')
    for data,tx,mask,label,color in [(old,to,mo,'Old output',COLORS[0]),(z,t,m,'New output',COLORS[1])]:
        code=sum((data[f'd{b}']>.45).astype(int)*(1<<b) for b in range(8))
        axs[4].plot(tx[mask],code[mask],color=color,label=label,ls='--' if data is old else '-')
    axs[4].set(ylabel='Output code',xlabel='Time (ns)',xlim=(lo,hi),ylim=(-8,263))
    for ax in axs:
        ax.axvspan(idle['first_reset_ns'],idle['last_reset_ns'],alpha=.1,color=COLORS[2])
        ax.axvline(idle['final_capture_fall_ns'],ls=':',lw=.8,color='#777')
        ax.grid(alpha=.2);ax.legend(loc='upper right',fontsize=8,ncol=2)
    finish(fig,'timing.png')
    fig,axs=plt.subplots(2,1,figsize=(10,5.5),layout='constrained')
    fig.suptitle('Sampling close-up: unchanged scheduled closing edge\n'+ENV,fontsize=11)
    for data,tx,label,color in [(old,to,'Old staged',COLORS[0]),(z,t,'Idle reset',COLORS[1])]:
        mask=(tx>140.95)&(tx<141.45)
        for ax,sig in zip(axs,['xdut.seq_sample','xdut.xbootp.g']):
            ax.plot(tx[mask],data[sig][mask],color=color,label=label)
    axs[0].set(ylabel='Bootstrap enable (V)');axs[1].set(ylabel='Main MOS gate P (V)',xlabel='Time (ns)')
    for ax in axs:ax.legend();ax.grid(alpha=.2)
    finish(fig,'closing.png')


def stress_codes(name):
    a=read(OUT/name/'analysis.json');f=OUT/name
    z=np.load(f/'wave.npz');env=np.load(f/'stress_envelopes.npz');t=z['time']*1e9
    worst=max((s for s in a['stress'] if s['group']=='reference'),key=lambda s:s['peak_v'])
    center=worst['time_ns'];m=(t>=center-1)&(t<=center+5)
    fig,axs=plt.subplots(3,1,figsize=(12,8.5),layout='constrained')
    fig.suptitle('Idle-reset verification\n'+ENV,fontsize=12)
    for group,c in zip(['reference','reference_driver','sequencer'],COLORS):
        axs[0].plot(t[m],env[group][m],label=group.replace('_',' '),color=c)
    axs[0].axhline(.99,color='#b13232',ls='--',label='Core screen: 0.99 V')
    axs[0].set(ylabel='Max terminal-pair voltage (V)',xlabel='Time (ns)',title=f'Reference worst event: {worst["peak_v"]:.6f} V at {center:.3f} ns')
    for group,c in zip(['reference','reference_driver','comparator'],COLORS):
        peaks=[env[group][(t>=i*100)&(t<(i+1)*100)].max() for i in range(len(a['frames']))]
        axs[1].plot(range(len(peaks)),peaks,'.-',color=c,label=group.replace('_',' '))
    axs[1].axhline(.99,color='#b13232',ls='--',label='0.99 V')
    axs[1].set(ylabel='Per-frame peak (V)',xlabel='Frame index')
    oldcodes=np.array([x['code'] for x in read(ROOT/'output/sar8_r4_staged/msb_4600/analysis.json')['frames']][:len(a['frames'])])
    codes=np.array([x['code'] for x in a['frames']]);delta=codes-oldcodes
    axs[2].bar(range(len(delta)),delta,color=COLORS[1],label='Idle reset - old staged')
    axs[2].axhline(0,color=COLORS[0],ls='--',lw=1,label='Identical code')
    for i in np.flatnonzero(delta):axs[2].text(i,delta[i]+.06 if delta[i]>0 else delta[i]-.13,f'{i}: {delta[i]:+d}',ha='center',fontsize=9)
    axs[2].set(ylabel='Output difference (codes)',xlabel='Frame index',ylim=(-1.3,1.3),yticks=[-1,0,1])
    for ax in axs:ax.grid(alpha=.2);ax.legend(fontsize=8,ncol=3)
    finish(fig,'stress_codes.png')


def curate(names):
    rows=[]
    for name in names:
        f=OUT/name;a=read(f/'analysis.json');ctx=read(f/'context.json')
        row={k:v for k,v in a.items() if k!='stress'}
        row['worst_by_group']={g:max((s for s in a['stress'] if s['group']==g),key=lambda s:s['peak_v']) for g in a['groups']}
        row['configuration']={k:v for k,v in ctx.items() if k not in ['stress_devices','saved_signals']}
        row['selected_MOS_count']=len(ctx['stress_devices'])
        row['native_result']=read(f/'result.json')
        row['model_includes']=[line for line in (f/'test.scs').read_text().splitlines() if line.startswith('include ')]
        row['test_environment']=dict(supply_v=.9,temperature_c=27,sample_rate_hz=10e6,
            sine_frequency_hz=4501953.125,sine_dbfs=-1,input_resistance_ohm_per_side=50,
            reference_resistance_ohm_per_rail=50,reference_capacitance_f_per_rail=4e-12,
            ideal_external_sources=['supplies','analog input','SAMPLE'],
            transient_noise=False,mismatch=False,post_layout=False,
            simulator='Spectre21.1 X CX',threads=4,profile='t28_io')
        if (f/'transfer.json').exists():row['transfer_integrity']=read(f/'transfer.json')
        rows.append(row)
    dump(ROOT/'verification/sar8_r4_idle/results.json',rows)
    selected=OUT/names[0]/'dut.scs';orig=cells(prior.FROZEN.read_text());new=cells(selected.read_text())
    changed=[k for k in new if k not in orig or prior.compact(new[k])!=prior.compact(orig[k])]
    dest=ROOT/'netlist/sar8_r4_idle';dest.mkdir(parents=True,exist_ok=True)
    text='// Native idle-tail MSB-first reference reset candidate; not an OA export.\n// Replace frozen top; retain unchanged frozen leaf definitions.\n'
    text+='\n\n'.join(new[k].rstrip() for k in changed)+'\n'
    (dest/'idle_cells.scs').write_text(text)
    dump(dest/'provenance.json',dict(frozen_file='netlist/sar8_physical/dut.scs',frozen_sha256=sha(prior.FROZEN),candidate_DUT_sha256=sha(selected),curated_sha256=sha(dest/'idle_cells.scs'),changed_or_added_cells=changed,OA_changed=False,baseline_promoted=False,generator='scripts/sar8_r4_idle/flow.py'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('names',nargs='+');a=p.parse_args()
    curate(a.names);timing(a.names[0]);stress_codes(max(a.names,key=lambda n:read(OUT/n/'context.json')['stop_ns']))
