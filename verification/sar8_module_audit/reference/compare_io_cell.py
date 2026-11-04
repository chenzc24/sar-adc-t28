"""Read-only collected FF pair comparison; writes only new module artifacts."""
from __future__ import annotations
import csv,gzip,hashlib,json,os
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
OUT=HERE/'generated/io_cell_ff_comparison'
NODES=['xdut.gnna','xdut.gnnb','xdut.gnndrv','xdut.gnn0']


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def load(variant,corner='ffcold',run_name=None):
    name=run_name or 'sar8audit-refcell-'+variant+'-'+corner
    folder=ROOT/'output/managed_execution/runs'/name/'collected'
    receipt=json.loads((folder/'collection_receipt.json').read_text())
    assert not receipt['skipped'] and len(receipt['files'])==11
    for item in receipt['files']:
        p=folder/item['name'];assert p.stat().st_size==item['bytes'] and digest(p)==item['sha256']
    assert sum(x['bytes'] for x in receipt['files'])==receipt['total_bytes']
    cfgpath=HERE/'generated/io_cell_v1'/(variant+'_'+corner)/'measurement.json'
    cfg=json.loads(cfgpath.read_text());r=json.loads((folder/'derived/result.json').read_text())
    assert digest(cfgpath)==r['measurement_sha256'] and r['analysis_complete'] and r['acceptance_pass'] is None
    recipe=json.loads((cfgpath.parent/'recipe_proposal.json').read_text())
    for item in recipe['inputs']:assert digest(ROOT/item['source'])==item['sha256']
    state=json.loads((folder/'simulation.state.json').read_text())
    assert state['status']=='complete' and state['exit_code']==0 and state['native']['native_analysis_pass'] and state['native']['zero_error_footer']
    e=next(x for x in r['native_exports'] if x['file']=='cell.native.f64le.gz')
    raw=gzip.decompress((folder/'derived'/e['file']).read_bytes())
    assert hashlib.sha256(raw).hexdigest()==e['uncompressed_sha256'] and len(raw)==e['uncompressed_bytes']
    w=np.frombuffer(raw,dtype='<f8').reshape(-1,len(e['columns']));c={n:j for j,n in enumerate(e['columns'])}
    assert w.shape==(r['native_points'],94) and w[0,0]==0 and w[-1,0]==52e-9 and np.all(np.diff(w[:,0])>0)
    return dict(run=name,result=r,cfg=cfg,w=w,c=c,receipt_bytes=receipt['total_bytes'],
                result_sha256=digest(folder/'derived/result.json'))


def bounds(w,c,node,start=0.,stop=52e-9):
    t=w[:,0];ids=np.flatnonzero((t>=start)&(t<=stop));y=w[ids,c[node]]
    lo,hi=int(ids[np.argmin(y)]),int(ids[np.argmax(y)])
    return dict(min_V=float(w[lo,c[node]]),max_V=float(w[hi,c[node]]),min_time_ns=float(t[lo]*1e9),max_time_ns=float(t[hi]*1e9))


def settled(w,c,node,ref,start,stop):
    ids=np.flatnonzero((w[:,0]>=start)&(w[:,0]<stop));assert len(ids)
    error=w[:,c[node]]-w[:,c[ref]];bad=ids[np.abs(error[ids])>.001]
    first=None if len(bad) and bad[-1]==ids[-1] else (int(bad[-1]+1) if len(bad) else int(ids[0]))
    return dict(target=ref,interval_s=[start,stop],stop_exclusive=True,
        final_native_s=float(w[ids[-1],0]),final_error_mV=float(error[ids[-1]]*1e3),
        last_outside_s=None if not len(bad) else float(w[bad[-1],0]),
        remained_inside_from_native_s=None if first is None else float(w[first,0]),
        crossing_bracket_ps=None if first is None or not len(bad) else float((w[first,0]-w[bad[-1],0])*1e12),
        diagnostic_threshold_mV=1)


def error_bounds(w,c,node,ref,start,stop):
    ids=np.flatnonzero((w[:,0]>=start)&(w[:,0]<stop));assert len(ids)
    y=(w[ids,c[node]]-w[ids,c[ref]])*1e3
    lo,hi=int(np.argmin(y)),int(np.argmax(y));last=int(ids[-1])
    return dict(interval_s=[start,stop],stop_exclusive=True,min_mV=float(y[lo]),max_mV=float(y[hi]),
        min_time_ns=float(w[ids[lo],0]*1e9),max_time_ns=float(w[ids[hi],0]*1e9),
        last_native_ns=float(w[last,0]*1e9),last_error_mV=float(y[-1]))


def compare():
    OUT.mkdir(parents=True,exist_ok=True);runs={v:load(v) for v in ['core','io']}
    rows=[];summary={}
    mapping={v:{p['instance']+':'+p['terminal']:p for p in d['cfg']['selected_mos_pair_screens']} for v,d in runs.items()}
    assert set(mapping['core'])==set(mapping['io']) and len(mapping['core'])==450
    for key in sorted(mapping['core']):
        row=dict(pair=key)
        for v,d in runs.items():
            spec=mapping[v][key];x=d['result']['selected_mos_pair_extrema'][key];peak=max(abs(x['min']),abs(x['max']))
            row.update({v+'_model':spec['model'],v+'_limit_V':spec['screen_v'],v+'_min_V':x['min'],v+'_max_V':x['max'],
                v+'_min_ns':x['min_time_s']*1e9,v+'_max_ns':x['max_time_s']*1e9,v+'_abs_peak_V':peak,
                v+'_excess_mV':(peak-spec['screen_v'])*1e3})
        rows.append(row)
    with (OUT/'all_450_terminal_pairs.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    for v,d in runs.items():
        r,w,c=d['result'],d['w'],d['c'];m=r['cell_measurements'];screens={}
        for group,insts in [('A',['GNNAN','GNNAP']),('B',['GNNBN','GNNBP']),('C',['GNNCN','GNNCP'])]:
            local=[p for p in rows if p['pair'].split(':')[0] in ['XDUT.'+x for x in insts]];assert len(local)==12
            worst=max(local,key=lambda p:p[v+'_excess_mV'])
            screens[group]=dict(pairs=12,strict_exceed_pairs=sum(p[v+'_excess_mV']>0 for p in local),
                exceed_by_more_than1mV_pairs=sum(p[v+'_excess_mV']>1 for p in local),
                worst_pair=worst['pair'],worst_abs_V=worst[v+'_abs_peak_V'],worst_excess_mV=worst[v+'_excess_mV'],
                limit_V=worst[v+'_limit_V'])
        energy={k:x for k,x in m.items() if k.endswith('_J')}
        delays={k:{n:z for n,z in val.items() if n!='interpretation'} for k,val in m['local_inverter_delays'].items()}
        summary[v]=dict(run=d['run'],result_sha256=d['result_sha256'],native_points=r['native_points'],span_s=[0,52e-9],
            receipt_bytes=d['receipt_bytes'],node_extrema={n:bounds(w,c,n) for n in NODES},group_terminal_screens=screens,
            all450_strict_exceed_pairs=sum(p[v+'_excess_mV']>0 for p in rows),
            all450_exceed_by_more_than1mV_pairs=sum(p[v+'_excess_mV']>1 for p in rows),
            counts_note='Terminal-pair records, not transistor counts.1mV grouping does not relax limits.',
            delays=delays,energy_J=energy,original_load_window_metrics=m['load_settling'],
            high_reference_error_observations={phase:{n:error_bounds(w,c,n,ref,start,stop) for n,ref in
                [('xdut.xcdac.bn0','vrefp'),('xdut.xcdac.bp0','vrefn')]}
                for phase,start,stop in [('stable_plateau',45e-9,46e-9),
                    ('before_off_edge',46.98e-9,46.995e-9),('off_edge_and_BBM_gap',46.995e-9,47.995e-9)]},
            stable_on_settling={phase:{n:settled(w,c,n,ref,start,stop) for n,ref in targets}
                for phase,start,stop,targets in [
                    ('high_before_off_edge',44.005e-9,46.995e-9,[('xdut.xcdac.bn0','vrefp'),('xdut.xcdac.bp0','vrefn')]),
                    ('low_after_on',48.005e-9,52.000001e-9,[('xdut.xcdac.bn0','vrefn'),('xdut.xcdac.bp0','vrefp')])]},
            static_max_rail_deviation_mV={n:max(p['logic_rail_max_deviation_V'].values())*1e3 for n,p in m['static_plateaus'].items()},
            max_KCL_pA=max(x['max_abs_a'] for x in r['node_kcl'].values())*1e12,
            original_warning_codes=r['native_warning_codes'],effective_settings=r['native_effective_settings'])
    result=dict(conditions='FF,0.99V,-40C;52ns; independent ideal PRE/companion commands, original physical load fixture; no noise/mismatch/PEX',
        same_time_axis_no_shift=True,acceptance_pass=None,ADC_qualification=False,
        edge_window_correction='Original high_reference window44..47ns includes companion turnoff starting46.995ns. Preserve original+1.14mV metric, but do not call it failure to settle before turnoff.',
        source_runs=summary)
    (OUT/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    figures(runs);print(json.dumps({v:{k:d[k] for k in ['group_terminal_screens','stable_on_settling','energy_J']} for v,d in summary.items()},indent=2))


def figures(runs):
    os.environ.setdefault('MPLCONFIGDIR',str(HERE/'cache/mpl_current'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    colors={'core':'#236b9c','io':'#ce6432'}
    env='T28 FF | VDD 0.99 V | -40 C | ideal logic/rails; physical A/B, CDAC, IO reference switches, Bootstrap; comparator reset'
    def draw(ax,node,window,scale=1,offset=0):
        for v,d in runs.items():
            w,c=d['w'],d['c'];t=w[:,0]*1e9;s=(t>=window[0])&(t<=window[1])
            ax.plot(t[s],(w[s,c[node]]-offset)*scale,color=colors[v],ls='-' if v=='core' else '--',lw=1.5,label=v.upper()+' C')
        ax.set_xlim(*window);ax.grid(alpha=.18);ax.ticklabel_format(useOffset=False,axis='x')
    fig,axes=plt.subplots(4,2,figsize=(12,10),layout='constrained')
    for j,window in enumerate([(42.99,43.035),(47.99,48.035)]):
        for i,n in enumerate(NODES):
            actual_window=window if i<3 else [(42.99,43.3),(47.99,48.25)][j]
            ax=axes[i,j];draw(ax,n,actual_window);ax.axhline(0,color='#888',ls=':',lw=.8);ax.axhline(.99,color='#888',ls=':',lw=.8)
            ax.set_ylim(*([-.4,1.48] if i==2 else [-.07,1.07]));ax.set_ylabel(['A (V)','B / C input (V)','C = GNNDRV (V)','GNN0 after Rgate (V)'][i])
        axes[0,j].set_title(['Low path disable: PRE rises at43ns','Low path enable: PRE falls at48ns'][j])
        axes[-1,j].set_xlabel('Native time (ns)')
    axes[0,0].legend(loc='lower left',fontsize=9)
    fig.suptitle('One IO output cell changes the transient; upstream core devices remain',fontsize=14)
    fig.supxlabel(env+'\nDotted:0/VDD rails; IO C terminal screen1.98V. GNN0 panels use a wider time window. No time alignment.',fontsize=8)
    fig.savefig(OUT/'ff_logic_edges.png',dpi=170);plt.close(fig)

    fig,axes=plt.subplots(2,2,figsize=(12,6.5),layout='constrained')
    for j,(window,refs,title) in enumerate([((44.15,46.994),['vrefp','vrefn'],'High reference ON; excludes turnoff edge'),
                                         ((48.15,49),['vrefn','vrefp'],'Low reference ON')]):
        for i,n in enumerate(['xdut.xcdac.bn0','xdut.xcdac.bp0']):
            ax=axes[i,j]
            for v,d in runs.items():
                w,c=d['w'],d['c'];t=w[:,0]*1e9;s=(t>=window[0])&(t<=window[1])
                ax.plot(t[s],(w[s,c[n]]-w[s,c[refs[i]]])*1e3,color=colors[v],ls='-' if v=='core' else '--',label=v.upper()+' C',lw=1.5)
            ax.axhspan(-1,1,color='#258578',alpha=.09);ax.axhline(0,color='#777',lw=.8)
            for y in [-1,1]:ax.axhline(y,color='#258578',ls='--',lw=.8)
            ax.set(xlim=window,ylim=(-3,3),ylabel=['BN0 - selected ref (mV)','BP0 - selected ref (mV)'][i]);ax.grid(alpha=.18)
            ax.ticklabel_format(useOffset=False,axis='x')
        axes[0,j].set_title(title);axes[-1,j].set_xlabel('Native time (ns)')
    axes[0,0].legend(fontsize=9);fig.suptitle('Both versions settle before reference turnoff',fontsize=14)
    fig.supxlabel(env+'\nShaded band:+/-1mV diagnostic; larger initial switching excursions are outside the displayed vertical range.',fontsize=8)
    fig.savefig(OUT/'ff_reference_settling.png',dpi=170);plt.close(fig)

    fig,axes=plt.subplots(3,1,figsize=(12,8),sharex=True,layout='constrained');window=(46.98,48.55)
    for v,d in runs.items():
        w,c=d['w'],d['c'];t=w[:,0]*1e9;s=(t>=window[0])&(t<=window[1])
        axes[0].plot(t[s],w[s,c['xdut.gnn0']],color=colors[v],ls='-' if v=='core' else '--',lw=1.5,label=v.upper()+' GNN0')
        for i,n in enumerate(['xdut.xcdac.bn0','xdut.xcdac.bp0'],1):axes[i].plot(t[s],w[s,c[n]],color=colors[v],ls='-' if v=='core' else '--',label=v.upper()+' C',lw=1.5)
    d=runs['core'];w,c=d['w'],d['c'];t=w[:,0]*1e9;s=(t>=window[0])&(t<=window[1])
    for n,ls,label in [('gnpdrv','--','GNPDRV: high-P gate'),('gpndrv',':','GPNDRV: low-N gate')]:
        axes[0].plot(t[s],w[s,c[n]],ls,color='#6b7280',lw=1,label=label)
    for i,n in enumerate(['BN0','BP0'],1):
        hi=.9 if i==1 else 0.;lo=0. if i==1 else .9
        axes[i].plot([46.98,46.995],[hi,hi],'--',color='#258578',lw=1.2,label='Selected ideal reference')
        axes[i].plot([48.005,48.55],[lo,lo],'--',color='#258578',lw=1.2)
        axes[i].set_ylabel(n+' (V)');axes[i].set_ylim(-.08,1.03)
    for ax in axes:
        ax.axvspan(47.005,47.995,color='#aaa',alpha=.13);ax.axvline(46.995,color='#999',ls=':',lw=.8);ax.axvline(48.005,color='#999',ls=':',lw=.8)
        ax.grid(alpha=.18);ax.set_xlim(*window);ax.legend(loc='center right',fontsize=8)
    inset=axes[1].inset_axes([.12,.12,.28,.38])
    for v,d in runs.items():
        w,c=d['w'],d['c'];t=w[:,0]*1e9;s=(t>=46.992)&(t<=47.007)
        inset.plot(t[s],(w[s,c['xdut.xcdac.bn0']]-w[s,c['vrefp']])*1e3,color=colors[v],ls='-' if v=='core' else '--',lw=1.2)
    inset.axhline(1,color='#258578',ls='--',lw=.7);inset.axvline(47,color='#777',ls=':',lw=.8)
    inset.set(xlim=(46.992,47.007),ylim=(-.2,4),title='BN0 - VREFP (mV)');inset.tick_params(labelsize=7)
    inset.title.set_fontsize(8);inset.ticklabel_format(useOffset=False,axis='x');inset.grid(alpha=.15)
    axes[0].set_ylabel('Gate voltage (V)');axes[0].set_ylim(-.07,1.07);axes[-1].set_xlabel('Native time (ns)')
    fig.suptitle('The +1.14mV endpoint falls inside high-reference turnoff',fontsize=14)
    fig.supxlabel(env+'\nGray interval:both reference commands OFF.47ns endpoint is not a stable ON-state measurement; no ADC decision is active.',fontsize=8)
    fig.savefig(OUT/'ff_reference_handoff.png',dpi=170);plt.close(fig)


if __name__=='__main__':compare()
