"""Compare completed SS pair and prior FF evidence; no remote or source writes."""
import csv,json,os
import numpy as np
from compare_io_cell import HERE,ROOT,NODES,load,digest,bounds,error_bounds,settled

OUT=HERE/'generated/io_cell_ss_comparison'
Q2='sar8audit-refcell-io-sscold-q2'
Q2_RECIPE='70189d38065071c2a25266856ec1eb94274817c9263b44138707956787c84e3b'


def compare():
    OUT.mkdir(exist_ok=True)
    runs={'core':load('core','sscold'),'io':load('io','sscold',Q2)}
    receipt=json.loads((ROOT/'output/managed_execution/runs'/Q2/'collected/collection_receipt.json').read_text())
    assert receipt['status']['registered']['recipe_hash']==Q2_RECIPE and receipt['status']['run_id']==Q2
    specs={v:{p['instance']+':'+p['terminal']:p for p in d['cfg']['selected_mos_pair_screens']} for v,d in runs.items()}
    assert set(specs['core'])==set(specs['io']) and len(specs['core'])==450
    rows=[]
    for pair in sorted(specs['core']):
        row=dict(pair=pair)
        for v,d in runs.items():
            spec=specs[v][pair];x=d['result']['selected_mos_pair_extrema'][pair];peak=max(abs(x['min']),abs(x['max']))
            row.update({v+'_model':spec['model'],v+'_limit_V':spec['screen_v'],v+'_abs_peak_V':peak,
                v+'_min_V':x['min'],v+'_max_V':x['max'],v+'_min_ns':x['min_time_s']*1e9,v+'_max_ns':x['max_time_s']*1e9,
                v+'_excess_mV':(peak-spec['screen_v'])*1e3})
        rows.append(row)
    with (OUT/'all_450_terminal_pairs.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    summary={}
    for v,d in runs.items():
        r,w,c=d['result'],d['w'],d['c'];m=r['cell_measurements'];groups={}
        assert r['supply_V']==.81
        for stage in ['A','B','C']:
            local=[p for p in rows if p['pair'].split(':')[0] in ['XDUT.GNN'+stage+t for t in ['N','P']]];assert len(local)==12
            worst=max(local,key=lambda x:x[v+'_excess_mV'])
            groups[stage]=dict(pairs=12,strict_exceed_pairs=sum(x[v+'_excess_mV']>0 for x in local),
                worst_pair=worst['pair'],worst_abs_V=worst[v+'_abs_peak_V'],limit_V=worst[v+'_limit_V'],worst_excess_mV=worst[v+'_excess_mV'])
        summary[v]=dict(run=d['run'],source_result_sha256=d['result_sha256'],receipt_bytes=d['receipt_bytes'],
            native_points=r['native_points'],span_s=[0,52e-9],node_extrema={n:bounds(w,c,n) for n in NODES},
            group_terminal_screens=groups,all450_strict_exceed_pairs=sum(x[v+'_excess_mV']>0 for x in rows),
            delays=m['local_inverter_delays'],original_load_window_metrics=m['load_settling'],
            original_high_reference_last_native_ns=float(w[w[:,0]<=47e-9][-1,0]*1e9),
            high_reference_error_observations={phase:{n:error_bounds(w,c,n,ref,start,stop) for n,ref in
                [('xdut.xcdac.bn0','vrefp'),('xdut.xcdac.bp0','vrefn')]}
                for phase,start,stop in [('stable_plateau',45e-9,46e-9),('before_off_edge',46.98e-9,46.995e-9),
                                       ('off_edge_and_BBM_gap',46.995e-9,47.995e-9)]},
            stable_on_settling={phase:{n:settled(w,c,n,ref,start,stop) for n,ref in targets}
                for phase,start,stop,targets in [('high_before_off_edge',44.005e-9,46.995e-9,
                    [('xdut.xcdac.bn0','vrefp'),('xdut.xcdac.bp0','vrefn')]),
                    ('low_after_on',48.005e-9,52.000001e-9,[('xdut.xcdac.bn0','vrefn'),('xdut.xcdac.bp0','vrefp')])]},
            energy_J={k:x for k,x in m.items() if k.endswith('_J')},
            static_max_rail_deviation_mV={n:max(x['logic_rail_max_deviation_V'].values())*1e3 for n,x in m['static_plateaus'].items()},
            max_KCL_pA=max(x['max_abs_a'] for x in r['node_kcl'].values())*1e12,
            warning_codes=r['native_warning_codes'],effective_settings=r['native_effective_settings'])
    ffpath=HERE/'generated/io_cell_ff_comparison/comparison.json';ff=json.loads(ffpath.read_text())
    for v,x in ff['source_runs'].items():assert digest(ROOT/'output/managed_execution/runs'/x['run']/'collected/derived/result.json')==x['result_sha256']
    matrix=[]
    for corner,source in [('FF0.99V/-40C',ff['source_runs']),('SS0.81V/-40C',summary)]:
        a,b=source['core'],source['io']
        matrix.append(dict(corner=corner,IO_C_worst_abs_V=b['group_terminal_screens']['C']['worst_abs_V'],IO_C_screen_V=1.98,
            IO_A_worst_abs_V=b['group_terminal_screens']['A']['worst_abs_V'],IO_B_worst_abs_V=b['group_terminal_screens']['B']['worst_abs_V'],
            IO_B_to_load_disable_ps=b['delays']['disable_low']['B_to_load_gate_s']*1e12,
            IO_B_to_load_enable_ps=b['delays']['enable_low']['B_to_load_gate_s']*1e12,
            delta_B_to_load_disable_ps=(b['delays']['disable_low']['B_to_load_gate_s']-a['delays']['disable_low']['B_to_load_gate_s'])*1e12,
            delta_B_to_load_enable_ps=(b['delays']['enable_low']['B_to_load_gate_s']-a['delays']['enable_low']['B_to_load_gate_s'])*1e12,
            IO_C_direct_VDD_energy_fJ=b['energy_J']['test_cell_direct_VDD_terminal_energy_J']*1e15,
            off_gap_BN0_max_mV=b['high_reference_error_observations']['off_edge_and_BBM_gap']['xdut.xcdac.bn0']['max_mV'],
            off_gap_BP0_min_mV=b['high_reference_error_observations']['off_edge_and_BBM_gap']['xdut.xcdac.bp0']['min_mV']))
    result=dict(conditions='SS,0.81V,-40C; independent logic, original physical load fixture, reset comparator; no noise/mismatch/PEX',
        acceptance_pass=None,ADC_qualification=False,same_native_time_no_shift=True,
        q2_provenance=dict(run=Q2,recipe_sha256=Q2_RECIPE,original_queue_timeout_is_not_circuit_failure=True),source_runs=summary,
        FF_source_comparison_sha256=digest(ffpath),FF_SS_route_matrix=matrix,
        route_assessment=dict(C_rated_cell_feasibility_supported_at_two_tested_points=True,final_C_geometry_adopted=False,
            full_driver_chain_closure_supported=False,
            reason='Rated C survives both tested fixtures with finite delay, but larger excursions persist; FF upstream A/B remain overstressed, SS delay grows, off-gap disturbance remains.',
            next_design_constraint='Include upstream A/B and actual interface in voltage-safe design, allocate measured SS delay in real BBM/async contract before expanding replacement. No new experiment generated.'))
    (OUT/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    figures(runs);print(json.dumps(dict(matrix=matrix,SS={v:{k:d[k] for k in ['group_terminal_screens','stable_on_settling','energy_J','high_reference_error_observations']} for v,d in summary.items()}),indent=2))


def figures(runs):
    os.environ.setdefault('MPLCONFIGDIR',str(HERE/'cache/mpl_current'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    colors={'core':'#236b9c','io':'#ce6432'}
    env='T28 SS | VDD0.81V | -40C | ideal logic/rails; physical A/B, CDAC, IO reference switches, Bootstrap; comparator reset'
    def plot(ax,node,window,reference=None):
        for v,d in runs.items():
            w,c=d['w'],d['c'];t=w[:,0]*1e9;s=(t>=window[0])&(t<=window[1]);y=w[:,c[node]]
            if reference:y=(y-w[:,c[reference]])*1e3
            ax.plot(t[s],y[s],color=colors[v],ls='-' if v=='core' else '--',label=v.upper()+' C',lw=1.5)
        ax.set_xlim(*window);ax.grid(alpha=.18);ax.ticklabel_format(useOffset=False,axis='x')
    fig,axes=plt.subplots(4,2,figsize=(12,10),layout='constrained')
    for j in range(2):
        for i,node in enumerate(NODES):
            ax=axes[i,j];window=([(42.99,43.05),(47.99,48.05)] if i<2 else [(42.99,43.35),(47.99,48.35)])[j]
            plot(ax,node,window);ax.axhline(0,color='#888',ls=':',lw=.8);ax.axhline(.81,color='#888',ls=':',lw=.8)
            ax.set_ylim(*([-.34,1.2] if i==2 else [-.1,.96]));ax.set_ylabel(['A (V)','B / C input (V)','C = GNNDRV (V)','GNN0 after Rgate (V)'][i])
        axes[0,j].set_title(['Low path disable: PRE rises at43ns','Low path enable: PRE falls at48ns'][j]);axes[-1,j].set_xlabel('Native time (ns)')
    axes[0,0].legend(loc='lower left',fontsize=9)
    fig.suptitle('SS: IO C remains functional; its output is slower and excursions are larger',fontsize=13)
    fig.supxlabel(env+'\nDotted:0/VDD rails; device terminal screens core0.99V/IO1.98V. C/GNN0 use wider time windows; no time alignment.',fontsize=8)
    fig.savefig(OUT/'ss_logic_edges.png',dpi=170);plt.close(fig)

    fig,axes=plt.subplots(2,2,figsize=(12,6.5),layout='constrained')
    for j,(window,refs,title) in enumerate([((44.35,46.994),['vrefp','vrefn'],'High reference ON; excludes turnoff edge'),
                                          ((48.5,49.5),['vrefn','vrefp'],'Low reference ON')]):
        for i,node in enumerate(['xdut.xcdac.bn0','xdut.xcdac.bp0']):
            ax=axes[i,j];plot(ax,node,window,refs[i]);ax.axhspan(-1,1,color='#258578',alpha=.09);ax.axhline(0,color='#777',lw=.8)
            for y in [-1,1]:ax.axhline(y,color='#258578',ls='--',lw=.8)
            ax.set_ylim(-3,3);ax.set_ylabel(['BN0 - selected ref (mV)','BP0 - selected ref (mV)'][i])
        axes[0,j].set_title(title);axes[-1,j].set_xlabel('Native time (ns)')
    axes[0,0].legend(fontsize=9);fig.suptitle('SS: both versions settle; low-reference BN0 is later with IO C',fontsize=13)
    fig.supxlabel(env+'\nShaded:+/-1mV diagnostic. Larger initial switching excursions fall outside the displayed vertical range.',fontsize=8)
    fig.savefig(OUT/'ss_reference_settling.png',dpi=170);plt.close(fig)

    fig,axes=plt.subplots(3,1,figsize=(12,8),sharex=True,layout='constrained');window=(46.98,49.1)
    plot(axes[0],'xdut.gnn0',window)
    d=runs['core'];w,c=d['w'],d['c'];t=w[:,0]*1e9;s=(t>=window[0])&(t<=window[1])
    for node,style,label in [('gnpdrv','--','GNPDRV: high-P gate'),('gpndrv',':','GPNDRV: low-N gate')]:
        axes[0].plot(t[s],w[s,c[node]],style,color='#6b7280',lw=1,label=label)
    axes[0].set_ylabel('Gate voltage (V)');axes[0].set_ylim(-.1,.96)
    for i,node in enumerate(['xdut.xcdac.bn0','xdut.xcdac.bp0'],1):
        plot(axes[i],node,window);hi=.9 if i==1 else 0.;lo=0. if i==1 else .9
        axes[i].plot([46.98,46.995],[hi,hi],'--',color='#258578',lw=1.2,label='Selected ideal reference')
        axes[i].plot([48.005,49.1],[lo,lo],'--',color='#258578',lw=1.2)
        axes[i].set_ylim(-.08,1.03);axes[i].set_ylabel(['BN0 (V)','BP0 (V)'][i-1])
    for ax in axes:
        ax.axvspan(47.005,47.995,color='#aaa',alpha=.13);ax.axvline(46.995,color='#999',ls=':',lw=.8);ax.axvline(48.005,color='#999',ls=':',lw=.8)
        ax.legend(loc='center right',fontsize=8)
    inset=axes[1].inset_axes([.1,.12,.28,.38]);plot(inset,'xdut.xcdac.bn0',(46.992,47.007),'vrefp')
    inset.axhline(1,color='#258578',ls='--',lw=.7);inset.axvline(47,color='#777',ls=':',lw=.8)
    inset.set_ylim(-.2,3.5);inset.set_title('BN0 - VREFP (mV)',fontsize=8);inset.tick_params(labelsize=7)
    axes[-1].set_xlabel('Native time (ns)');fig.suptitle('SS: the reference turnoff leaves a floating-node disturbance',fontsize=13)
    fig.supxlabel(env+'\nGray:both reference commands OFF.47ns endpoint lies in turnoff; stable ON-state and off-gap errors are separate.',fontsize=8)
    fig.savefig(OUT/'ss_reference_handoff.png',dpi=170);plt.close(fig)


if __name__=='__main__':compare()
