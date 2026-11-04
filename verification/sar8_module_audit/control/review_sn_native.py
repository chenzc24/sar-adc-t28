"""Local source/v1 SN and actual missing-load-bias review, no aligned traces."""
import json
import os

import numpy as np

import prepare_first_event as base
import prepare_sn_load_variants as loads
import review_first_event_v1 as first


def main():
    source,names,proof = loads.read_supplement('sar8audit-ctrl-source-sn-v1',loads.SOURCE,loads.SOURCE_SHA)
    fixture,fnames,fproof = loads.read_supplement('sar8audit-ctrl-fixture-sn-v1',loads.FIXTURE,loads.FIXTURE_SHA)
    original,original_names,_ = base.collected()
    isolated,isolated_names,_,_,_,_,_ = first.collect_readonly()
    sn = 'xdut.xctrl.xtim.sn'
    out = loads.DEST
    out.mkdir(exist_ok=True)
    def column(table,labels,name):
        return table[:,labels.index(name)]
    def at_edges(table,labels,name,rising):
        return base.edge_time(table[:,0],column(table,labels,name),.99,rising)
    metrics = {}
    for signal,direction in [(sn,True),('xdut.xctrl.xtim.x001.n',False)]:
        a=at_edges(source,names,signal,direction);b=at_edges(fixture,fnames,signal,direction)
        av,bv=column(source,names,signal),column(fixture,fnames,signal)
        metrics[signal]=dict(source_edges_s=a,fixture_edges_s=b,error_s=[y-x for x,y in zip(a,b)],
            source_min_v=float(av.min()),fixture_min_v=float(bv.min()),
            source_max_v=float(av.max()),fixture_max_v=float(bv.max()))
    metrics['xdut.xctrl.xtim.live']=dict(
        source_edges_s=at_edges(original,original_names,'xdut.xctrl.xtim.live',True),
        fixture_edges_s=at_edges(isolated,isolated_names,'xdut.xctrl.xtim.live',True))
    metrics['xdut.xctrl.xtim.live']['error_s']=[b-a for a,b in zip(
        metrics['xdut.xctrl.xtim.live']['source_edges_s'],metrics['xdut.xctrl.xtim.live']['fixture_edges_s'])]
    k=int(np.searchsorted(source[:,0],metrics[sn]['source_edges_s'][0])-1)
    event=(source[:,0]>=40.8e-9)&(source[:,0]<=41.12e-9)
    bias={n:dict(initial_v=float(source[0,j]),event_min_v=float(source[event,j].min()),
        event_max_v=float(source[event,j].max()),native_before_SN50_v=float(source[k,j]))
        for j,n in enumerate(names) if j}
    review=dict(source=proof,fixture=fproof,events=metrics,source_bias=bias,
        native_bias_snapshot_time_s=float(source[k,0]),
        interpretation='SN timing shift can now be separated from downstream LIVE delay; actual bias is replayed in full, never replaced by these summary values.',
        priority='both: add four original SN gate-connected MOS with source-native diffusion biases; not ADC circuit optimization',
        conditional_load_limitations='Drain histories remain externally conditioned, not reciprocal full X010/X014 logic. Original v1 active nodes remain naturally driven.',
        waveform_alignment=False,remote_operations=False)
    (out/'native_bias_review.json').write_text(json.dumps(review,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    os.environ.setdefault('MPLCONFIGDIR',str(base.OWN/'.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    srcstyle=dict(color='#255d83',lw=1.5)
    fixstyle=dict(color='#d16b24',lw=1.25,ls='--')
    fig,axes=plt.subplots(3,1,sharex=True,figsize=(10,7.6),layout='constrained')
    for ax,signal in zip(axes[:2],[sn,'xdut.xctrl.xtim.x001.n']):
        ax.plot(source[:,0]*1e9,column(source,names,signal),label='Original loaded ADC',**srcstyle)
        ax.plot(fixture[:,0]*1e9,column(fixture,fnames,signal),label='Isolated control v1',**fixstyle)
        ax.set(ylabel='Voltage (V)',title=signal.rsplit('.',2)[-1].upper());ax.grid(alpha=.2)
    axes[1].set_title('X001.N: internal NAND before LIVE')
    axes[2].plot(original[:,0]*1e9,column(original,original_names,'xdut.xctrl.xtim.live'),**srcstyle)
    axes[2].plot(isolated[:,0]*1e9,column(isolated,isolated_names,'xdut.xctrl.xtim.live'),**fixstyle)
    axes[2].set(xlim=(41.04,41.115),xlabel='Original time (ns); no alignment or fitting',ylabel='Voltage (V)',title='LIVE')
    axes[2].grid(alpha=.2);axes[0].legend(fontsize=8,loc='center right')
    fig.suptitle('SN native evidence: timing shift is visible before LIVE',fontsize=13)
    fig.supxlabel('FF / 0.99 V / -40 C | original ADC versus 97-MOS control v1 | before first comparison\n'
                  'Original external supply/clock ideal; v1 recorded inputs; no noise, mismatch or PEX',fontsize=8)
    fig.savefig(out/'SN_native_comparison.png',dpi=165);plt.close(fig)
    fig,axes=plt.subplots(4,1,sharex=True,figsize=(10,8.2),layout='constrained')
    for ax,signals,title in zip(axes,[['ud'],['write_req'],['x010.n','x010.x000.mid'],['x014.n','x014.x000.mid']],
                                ['UD','WRITE_REQ','X010 diffusion biases','X014 diffusion biases']):
        for signal in signals:
            ax.plot(source[:,0]*1e9,column(source,names,'xdut.xctrl.xtim.'+signal),label=signal.upper(),lw=1.3)
        ax.set(ylabel='Voltage (V)',title=title);ax.grid(alpha=.2);ax.legend(loc='center right',fontsize=8)
        ax.ticklabel_format(axis='y',style='plain',useOffset=False)
    axes[-1].set(xlim=(41.04,41.115),xlabel='Original source time (ns)')
    fig.suptitle('Actual source-native bias for the SN gate-load replicas',fontsize=13)
    fig.supxlabel('FF / 0.99 V / -40 C | completed original ADC native rows | all native knots retained\n'
                  'These are measured histories, not fixed bias assumptions; no noise, mismatch or PEX',fontsize=8)
    fig.savefig(out/'source_load_biases.png',dpi=165);plt.close(fig)
    print(json.dumps(dict(events=metrics,source_bias=bias,snapshot_time_ns=source[k,0]*1e9),indent=2))


if __name__=='__main__':
    main()
