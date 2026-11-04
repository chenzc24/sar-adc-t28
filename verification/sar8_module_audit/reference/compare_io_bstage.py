"""Bounded read-only B-only FF comparison; no simulation or frozen-file writes."""
import csv,gzip,json,os
import numpy as np
from compare_io_cell import HERE,ROOT,NODES,load,digest,bounds,error_bounds,settled

OUT=HERE/'generated/io_bstage_ff_comparison'
RUN='sar8audit-refcell-iob-ffcold'
HASH='a89eda94b9e3b68db0598a21cbde394af33dd297f9c18f82d0ea9366df36aae6'


def load_candidate(corner='ffcold'):
    name='sar8audit-refcell-iob-'+corner
    expected=HASH if corner=='ffcold' else 'ad9bc0c2c590427fac6d81ca47b273f278f6a3aec353b01309f11de733fab36e'
    size,points=(3988387,8496) if corner=='ffcold' else (3948132,8087)
    folder=ROOT/'output/managed_execution/runs'/name/'collected';receipt=json.loads((folder/'collection_receipt.json').read_text())
    assert receipt['status']['registered']['recipe_hash']==expected and not receipt['skipped'] and len(receipt['files'])==11
    for x in receipt['files']:
        p=folder/x['name'];assert p.stat().st_size==x['bytes'] and digest(p)==x['sha256']
    assert receipt['total_bytes']==sum(x['bytes'] for x in receipt['files'])==size
    cfgpath=HERE/'generated/io_bstage_v1'/corner/'measurement.json';cfg=json.loads(cfgpath.read_text())
    recipe=json.loads((cfgpath.parent/'recipe_proposal.json').read_text())
    for x in recipe['inputs']:assert digest(ROOT/x['source'])==x['sha256']
    r=json.loads((folder/'derived/result.json').read_text());assert r['measurement_sha256']==digest(cfgpath) and r['analysis_complete'] and r['acceptance_pass'] is None
    state=json.loads((folder/'simulation.state.json').read_text());assert state['status']=='complete' and state['exit_code']==0 and state['native']['native_analysis_pass'] and state['native']['zero_error_footer']
    e=next(x for x in r['native_exports'] if x['file']=='cell.native.f64le.gz');data=gzip.decompress((folder/'derived'/e['file']).read_bytes())
    import hashlib
    assert hashlib.sha256(data).hexdigest()==e['uncompressed_sha256'] and len(data)==e['uncompressed_bytes']
    w=np.frombuffer(data,dtype='<f8').reshape(-1,len(e['columns']));assert w.shape==(points,94) and w[0,0]==0 and w[-1,0]==52e-9 and np.all(np.diff(w[:,0])>0)
    return dict(run=name,result=r,cfg=cfg,w=w,c={n:j for j,n in enumerate(e['columns'])},result_sha256=digest(folder/'derived/result.json'))


def gate_load(d):
    w,c=d['w'],d['c'];events={n:dict(samples=0,first_native_s=None,last_native_s=None,signed_charge_C=0.,absolute_charge_C=0.) for n in ['disable_low','enable_low']};last={}
    lo,hi=None,None;lo_t,hi_t=None,None
    for row in w:
        t=float(row[0]);i=float(row[c['xdut.gnnbn:2']])+float(row[c['xdut.gnnbp:2']])
        if lo is None or i<lo:lo,lo_t=i,t
        if hi is None or i>hi:hi,hi_t=i,t
        for name,a,b in [('disable_low',42.98e-9,45e-9),('enable_low',47.98e-9,51e-9)]:
            if a<=t<=b:
                s=events[name]
                if s['first_native_s'] is None:s['first_native_s']=t
                if name in last:
                    pt,pi=last[name];s['signed_charge_C']+=(i+pi)*(t-pt)*.5;s['absolute_charge_C']+=(abs(i)+abs(pi))*(t-pt)*.5
                last[name]=(t,i);s['samples']+=1;s['last_native_s']=t
    return dict(min_A=lo,max_A=hi,min_time_s=lo_t,max_time_s=hi_t,event_native_charge=events,
        full_signed_charge_C=sum(d['result']['current_charge_trapezoids'][n]['signed_C'] for n in ['xdut.gnnbn:2','xdut.gnnbp:2']))


def timing(d):
    r=d['result'];answer={}
    for name,start,disable in [('disable_low',43,True),('enable_low',48,False)]:
        witnesses={}
        for node,direction in [('pre','rising' if disable else 'falling'),('xdut.gnna','falling' if disable else 'rising'),
                               ('xdut.gnnb','rising' if disable else 'falling'),('xdut.gnndrv','falling' if disable else 'rising'),
                               ('xdut.gnn0','falling' if disable else 'rising')]:
            found=[x for x in r['half_vdd_events'][node] if x['direction']==direction and (start-.02)*1e-9<=x['estimated_time_s']<=(start+2)*1e-9]
            if len(found)!=1:raise ValueError('Ambiguous/missing edge '+node)
            witnesses[node]=found[0]
        delays={label:witnesses[b]['estimated_time_s']-witnesses[a]['estimated_time_s'] for label,a,b in
            [('PRE_to_A_s','pre','xdut.gnna'),('A_to_B_s','xdut.gnna','xdut.gnnb'),('B_to_C_s','xdut.gnnb','xdut.gnndrv'),
             ('B_to_GNN0_s','xdut.gnnb','xdut.gnn0'),('PRE_to_GNN0_s','pre','xdut.gnn0')]}
        answer[name]=dict(delays=delays,native_edge_witnesses=witnesses)
    return answer


def compare(corner='ffcold'):
    global OUT
    OUT=HERE/('generated/io_bstage_'+('ff' if corner=='ffcold' else 'ss')+'_comparison')
    OUT.mkdir(exist_ok=True);runs={'IO_C':load('io',corner,None if corner=='ffcold' else 'sar8audit-refcell-io-sscold-q2'),'IO_BC':load_candidate(corner)};rows=[]
    specs={v:{x['instance']+':'+x['terminal']:x for x in d['cfg']['selected_mos_pair_screens']} for v,d in runs.items()}
    assert set(specs['IO_C'])==set(specs['IO_BC']) and len(specs['IO_C'])==450
    for pair in sorted(specs['IO_C']):
        row=dict(pair=pair)
        for v,d in runs.items():
            x=d['result']['selected_mos_pair_extrema'][pair];spec=specs[v][pair];peak=max(abs(x['min']),abs(x['max']))
            row.update({v+'_model':spec['model'],v+'_limit_V':spec['screen_v'],v+'_abs_peak_V':peak,v+'_excess_mV':(peak-spec['screen_v'])*1e3,
                v+'_min_V':x['min'],v+'_max_V':x['max'],v+'_min_ns':x['min_time_s']*1e9,v+'_max_ns':x['max_time_s']*1e9})
        rows.append(row)
    with (OUT/'all450_terminal_pairs.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    summary={}
    for v,d in runs.items():
        r,w,c=d['result'],d['w'],d['c'];m=r['cell_measurements'];groups={}
        for stage in ['A','B','C']:
            q=[x for x in rows if x['pair'].split(':')[0] in ['XDUT.GNN'+stage+t for t in ['N','P']]];assert len(q)==12
            worst=max(q,key=lambda x:x[v+'_excess_mV'])
            groups[stage]=dict(strict_exceed_pairs=sum(x[v+'_excess_mV']>0 for x in q),worst_pair=worst['pair'],limit_V=worst[v+'_limit_V'],
                worst_abs_V=worst[v+'_abs_peak_V'],worst_excess_mV=worst[v+'_excess_mV'])
        energies={stage:r['supply_V']*sum(r['current_charge_trapezoids']['xdut.gnn'+stage.lower()+'p:'+str(pin)]['signed_C'] for pin in [3,4]) for stage in ['A','B','C']}
        summary[v]=dict(run=d['run'],source_result_sha256=d['result_sha256'],native_points=r['native_points'],node_extrema={n:bounds(w,c,n) for n in NODES},
            group_terminal_screens=groups,all450_strict_exceed_pairs=sum(x[v+'_excess_mV']>0 for x in rows),
            all450_exceed_by_more_than1mV_pairs=sum(x[v+'_excess_mV']>1 for x in rows),timing=timing(d),B_gate_load=gate_load(d),
            direct_stage_energy_J=energies,ideal_VDD_energy_J=m['ideal_VDD_energy_J'],
            original_load_window_metrics=m['load_settling'],original_high_window_last_native_ns=float(w[w[:,0]<=47e-9][-1,0]*1e9),
            stable_on_settling={phase:{n:settled(w,c,n,ref,a,b) for n,ref in targets} for phase,a,b,targets in [
                ('high',44.005e-9,46.995e-9,[('xdut.xcdac.bn0','vrefp'),('xdut.xcdac.bp0','vrefn')]),
                ('low',48.005e-9,52.000001e-9,[('xdut.xcdac.bn0','vrefn'),('xdut.xcdac.bp0','vrefp')])]},
            high_reference_error_observations={phase:{n:error_bounds(w,c,n,ref,a,b) for n,ref in [('xdut.xcdac.bn0','vrefp'),('xdut.xcdac.bp0','vrefn')]}
                for phase,a,b in [('plateau',45e-9,46e-9),('preoff',46.98e-9,46.995e-9),('off_gap',46.995e-9,47.995e-9)]},
            max_KCL_pA=max(x['max_abs_a'] for x in r['node_kcl'].values())*1e12,
            warning_codes=r['native_warning_codes'],effective_settings=r['native_effective_settings'])
    measured=summary['IO_BC']['B_gate_load'];remote=runs['IO_BC']['result']['cell_measurements']['B_input_load_current']
    for key in ['min_A','max_A','min_time_s','max_time_s','full_signed_charge_C']:assert abs(measured[key]-remote[key])<1e-24
    for ev in measured['event_native_charge']:
        for k,x in measured['event_native_charge'][ev].items():assert abs(x-remote['event_native_charge'][ev][k])<1e-24
    result=dict(conditions=('FF0.99V' if corner=='ffcold' else 'SS0.81V')+'/-40C,original independent commands and physical load; only B class/geometry changed, A core and C IO retained',
        source_runs=summary,acceptance_pass=None,adoption_supported=False,ADC_qualification=False,
        timing_note='Remeasured from existing native edge witnesses in42.98..45/47.98..50ns; source analyzer narrow PRE event null is preserved. No waveform shift or new simulation.',
        original_candidate_upstream_delay_fields=runs['IO_BC']['result']['cell_measurements']['upstream_stage_delays'])
    (OUT/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');figures(runs,corner)
    print(json.dumps({v:{k:d[k] for k in ['group_terminal_screens','timing','B_gate_load','direct_stage_energy_J','stable_on_settling']} for v,d in summary.items()},indent=2))


def figures(runs,corner):
    os.environ.setdefault('MPLCONFIGDIR',str(HERE/'cache/mpl_current'));import matplotlib
    matplotlib.use('Agg');import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False});colors={'IO_C':'#236b9c','IO_BC':'#ce6432'}
    is_ff=corner=='ffcold';rail=.99 if is_ff else .81;prefix='ff' if is_ff else 'ss'
    env=('T28 FF | VDD0.99V' if is_ff else 'T28 SS | VDD0.81V')+' | -40C | physical CDAC/reference/Bootstrap; ideal commands/rails; comparator reset; no noise/mismatch/PEX'
    fig,axes=plt.subplots(4,2,figsize=(12,10),layout='constrained')
    for j in range(2):
        for i,n in enumerate(NODES):
            if is_ff:window=([(42.99,43.07),(47.99,48.07)] if i<3 else [(42.99,43.35),(47.99,48.3)])[j]
            else:window=([(42.99,43.06),(47.99,48.06)] if i==0 else [(42.99,43.5),(47.99,48.5)])[j]
            ax=axes[i,j]
            for v,d in runs.items():
                w,c=d['w'],d['c'];t=w[:,0]*1e9;s=(t>=window[0])&(t<=window[1]);ax.plot(t[s],w[s,c[n]],color=colors[v],ls='-' if v=='IO_C' else '--',label=v.replace('_','-'),lw=1.5)
            limits=([-.37,1.48] if i in [1,2] else [-.07,1.07]) if is_ff else ([-.3,1.2] if i in [1,2] else [-.15,.96])
            ax.set_xlim(*window);ax.set_ylim(*limits);ax.set_ylabel(['A core (V)','B (V)','C IO (V)','GNN0 after Rgate (V)'][i]);ax.grid(alpha=.18);ax.ticklabel_format(useOffset=False,axis='x')
            for y in [0,rail]:ax.axhline(y,color='#888',ls=':',lw=.8)
        axes[0,j].set_title(['Low path disable','Low path enable'][j]);axes[-1,j].set_xlabel('Native time (ns)')
    axes[0,0].legend(loc='lower left',fontsize=9);fig.suptitle('B replacement: C kick is smaller; core A remains overstressed' if is_ff else 'SS: C kick is smaller, but load-gate undershoot and total delay increase',fontsize=13)
    fig.supxlabel(env+'\nDotted:0/VDD rails; B/C IO terminal screen1.98V. Rows use indicated time windows; no time shift.',fontsize=8)
    fig.savefig(OUT/(prefix+'_bstage_node_edges.png'),dpi=170);plt.close(fig)
    fig,axes=plt.subplots(3,2,figsize=(12,8),layout='constrained')
    for j,window in enumerate([(42.98,43.14),(47.98,48.14)] if is_ff else [(42.98,43.35),(47.98,48.35)]):
        for v,d in runs.items():
            w,c=d['w'],d['c'];t=w[:,0]*1e9;s=(t>=window[0])&(t<=window[1]);times=w[s,0]
            gate=w[s,c['xdut.gnnbn:2']]+w[s,c['xdut.gnnbp:2']];cumulative=np.r_[0,np.cumsum((gate[1:]+gate[:-1])*.5*np.diff(times))]
            a=w[s,c['xdut.gnnap:3']]+w[s,c['xdut.gnnap:4']]
            for i,y in enumerate([gate*1e6,cumulative*1e15,a*1e6]):axes[i,j].plot(t[s],y,color=colors[v],ls='-' if v=='IO_C' else '--',label=v.replace('_','-'),lw=1.4)
        for i,label in enumerate(['B total gate current (uA)','B native cumulative gate Q (fC)','A direct VDD port current (uA)']):
            ax=axes[i,j];ax.set_xlim(*window);ax.set_ylabel(label);ax.axhline(0,color='#888',lw=.7);ax.grid(alpha=.18);ax.ticklabel_format(useOffset=False,axis='x')
        axes[0,j].set_title(['PRE rising: A falls','PRE falling: A rises'][j]);axes[-1,j].set_xlabel('Native time (ns)')
    axes[0,0].legend(fontsize=9);fig.suptitle('The new B cell changes the actual load on core A',fontsize=14)
    fig.supxlabel(env+'\nPositive current enters B gates or A source/bulk. Q is native trapezoidal total-port charge, not intrinsic capacitance decomposition.',fontsize=8)
    fig.savefig(OUT/(prefix+'_bstage_A_load_current.png'),dpi=170);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(12,6.5),layout='constrained')
    windows=[((44.15,46.994),['vrefp','vrefn'],'High reference ON; excludes turnoff'),((48.15,49),['vrefn','vrefp'],'Low reference ON')] if is_ff else [((44.35,46.994),['vrefp','vrefn'],'High reference ON; excludes turnoff'),((48.5,49.5),['vrefn','vrefp'],'Low reference ON')]
    for j,(window,refs,title) in enumerate(windows):
        for i,n in enumerate(['xdut.xcdac.bn0','xdut.xcdac.bp0']):
            ax=axes[i,j]
            for v,d in runs.items():
                w,c=d['w'],d['c'];t=w[:,0]*1e9;s=(t>=window[0])&(t<=window[1]);ax.plot(t[s],(w[s,c[n]]-w[s,c[refs[i]]])*1e3,color=colors[v],ls='-' if v=='IO_C' else '--',label=v.replace('_','-'),lw=1.5)
            ax.axhspan(-1,1,color='#258578',alpha=.09);ax.axhline(0,color='#777',lw=.8)
            for y in [-1,1]:ax.axhline(y,color='#258578',ls='--',lw=.8)
            ax.set(xlim=window,ylim=(-3,3),ylabel=['BN0 - selected ref (mV)','BP0 - selected ref (mV)'][i]);ax.grid(alpha=.18)
        axes[0,j].set_title(title);axes[-1,j].set_xlabel('Native time (ns)')
    axes[0,0].legend(fontsize=9);fig.suptitle('Real-load settling remains close; low-reference BN0 is later',fontsize=14)
    fig.supxlabel(env+'\nShaded:+/-1mV diagnostic. Initial large excursions are outside y-range; off-gap47..48ns is a separate observation.',fontsize=8)
    fig.savefig(OUT/(prefix+'_bstage_load_settling.png'),dpi=170);plt.close(fig)


def summary_only():
    paths={n:HERE/('generated/io_bstage_'+n+'_comparison/comparison.json') for n in ['ff','ss']}
    results={n:json.loads(p.read_text()) for n,p in paths.items()};facts={}
    for corner,result in results.items():
        a,b=result['source_runs']['IO_C'],result['source_runs']['IO_BC'];facts[corner]=dict(
            candidate_A_excess_mV=b['group_terminal_screens']['A']['worst_excess_mV'],
            candidate_B_worst_abs_V=b['group_terminal_screens']['B']['worst_abs_V'],
            candidate_C_worst_abs_V=b['group_terminal_screens']['C']['worst_abs_V'],
            total_delay_ps={event:{v:d['timing'][event]['delays']['PRE_to_GNN0_s']*1e12 for v,d in result['source_runs'].items()} for event in ['disable_low','enable_low']},
            B_gate_charge_magnitude_fC={v:abs(d['B_gate_load']['event_native_charge']['enable_low']['signed_charge_C'])*1e15 for v,d in result['source_runs'].items()},
            A_energy_fJ={v:d['direct_stage_energy_J']['A']*1e15 for v,d in result['source_runs'].items()},
            low_BN0_settling_entry_ns={v:d['stable_on_settling']['low']['xdut.xcdac.bn0']['remained_inside_from_native_s']*1e9 for v,d in result['source_runs'].items()})
    index=dict(comparisons={n:dict(file=p.relative_to(HERE).as_posix(),sha256=digest(p)) for n,p in paths.items()},facts=facts,
        conclusion='B/C IO voltage feasibility retained; FF A still exceeds0.99V, loading and SS total delay increase, off-gap disturbance remains. No baseline adoption.',
        next_step='Address remaining core A and its real PRE interface voltage safety, with measured SS0.253/0.234ns end-to-end delays in the actual timing budget; no new candidate generated.')
    (HERE/'generated/io_bstage_comparison_index.json').write_text(json.dumps(index,indent=2)+'\n')
    os.environ.setdefault('MPLCONFIGDIR',str(HERE/'cache/mpl_current'));import matplotlib
    matplotlib.use('Agg');import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),sharex=True,layout='constrained')
    cases=[('FF IO-C',results['ff']['source_runs']['IO_C']),('FF IO-BC',results['ff']['source_runs']['IO_BC']),
           ('SS IO-C',results['ss']['source_runs']['IO_C']),('SS IO-BC',results['ss']['source_runs']['IO_BC'])]
    colors=['#236b9c','#cc8a36','#258578','#8d91a3']
    for j,event in enumerate(['disable_low','enable_low']):
        ax=axes[j]
        for y,(label,d) in enumerate(cases):
            t=d['timing'][event]['delays'];segments=[t['PRE_to_A_s'],t['A_to_B_s'],t['B_to_C_s'],t['B_to_GNN0_s']-t['B_to_C_s']]
            assert abs(sum(segments)-t['PRE_to_GNN0_s'])<1e-20
            left=0.
            for i,(value,name) in enumerate(zip(segments,['PRE to A','A to B','B to C','C to GNN0'])):
                ax.barh(y,value*1e12,left=left,color=colors[i],height=.58,label=name if y==0 and j==0 else None);left+=value*1e12
            ax.text(left+3,y,'%.1f'%left,va='center',fontsize=9)
        ax.set_yticks(range(4),[x[0] for x in cases]);ax.invert_yaxis();ax.set_xlim(0,285);ax.grid(axis='x',alpha=.18)
        ax.set_xlabel('PRE to GNN0 half-level delay (ps)');ax.set_title(['Low path disable','Low path enable'][j])
    axes[0].legend(loc='upper right',fontsize=9)
    fig.suptitle('The SS penalty includes the new B delay and the slower C response',fontsize=13)
    fig.supxlabel('FF0.99V / SS0.81V, -40C | unchanged physical load and ideal commands | native half-level crossings; unit fixture, not full async timing',fontsize=8)
    fig.savefig(HERE/'generated/io_bstage_timing.png',dpi=170);plt.close(fig)
    print('TWO_CORNER_B_COMPARISON_INDEX_READY')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--corner',choices=['ffcold','sscold'],default='ffcold');parser.add_argument('--summary-only',action='store_true');args=parser.parse_args()
    if args.summary_only:summary_only()
    else:compare(args.corner)
