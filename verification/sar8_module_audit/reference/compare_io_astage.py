"""Small completed BC->ABC comparison; read-only source formulas, no new run."""
import copy,csv,gzip,hashlib,json,os
import numpy as np
from compare_io_cell import HERE,ROOT,digest,error_bounds
from compare_io_bstage import load_candidate as load_BC
import io_cell_analyze as cell
from io_astage_analyze import measured

OUT=HERE/'generated/io_astage_comparison'
CASES={'ffcold':('f1e6dd17f97789e692fb6f9a988804048275ba32cefcbe414c9265952544f4f1',4121724,8410),
       'sscold':('327a9455d983dfa17c1d72eb7ba456af43b7539f007e80ee7633c4133413e283',4037948,7915)}


def load_ABC(corner):
    name='sar8audit-refcell-ioa-'+corner;folder=ROOT/'output/managed_execution/runs'/name/'collected'
    expected,size,count=CASES[corner];receipt=json.loads((folder/'collection_receipt.json').read_text())
    assert receipt['status']['registered']['recipe_hash']==expected and not receipt['skipped'] and len(receipt['files'])==11
    for x in receipt['files']:
        p=folder/x['name'];assert p.stat().st_size==x['bytes'] and digest(p)==x['sha256']
    assert sum(x['bytes'] for x in receipt['files'])==receipt['total_bytes']==size
    cfgpath=HERE/'generated/io_astage_v1'/corner/'measurement.json';cfg=json.loads(cfgpath.read_text());recipe=json.loads((cfgpath.parent/'recipe_proposal.json').read_text())
    for x in recipe['inputs']:assert digest(ROOT/x['source'])==x['sha256']
    r=json.loads((folder/'derived/result.json').read_text());assert r['analysis_complete'] and r['acceptance_pass'] is None and r['measurement_sha256']==digest(cfgpath)
    state=json.loads((folder/'simulation.state.json').read_text());assert state['status']=='complete' and state['exit_code']==0 and state['native']['native_analysis_pass'] and state['native']['zero_error_footer']
    e=next(x for x in r['native_exports'] if x['file']=='cell.native.f64le.gz');data=gzip.decompress((folder/'derived'/e['file']).read_bytes());assert hashlib.sha256(data).hexdigest()==e['uncompressed_sha256']
    w=np.frombuffer(data,dtype='<f8').reshape(-1,len(e['columns']));assert w.shape==(count,94) and w[0,0]==0 and w[-1,0]==52e-9
    return dict(run=name,result=r,cfg=cfg,w=w,c={n:j for j,n in enumerate(e['columns'])},result_sha256=digest(folder/'derived/result.json'))


def compare():
    OUT.mkdir(exist_ok=True);results={};waves={};rows=[]
    for corner in ['ffcold','sscold']:
        runs={'BC':load_BC(corner),'ABC':load_ABC(corner)};waves[corner]=runs;summary={}
        for variant,d in runs.items():
            r,cfg,w,c=d['result'],copy.deepcopy(d['cfg']),d['w'],d['c']
            if variant=='BC':
                # Read-only reuse of measurement math; discard its energy/role
                # labels, which were written for A-IO. Actual baseline class below.
                cfg['PRE_input_charge_windows']=runs['ABC']['cfg']['PRE_input_charge_windows']
                cfg['correct_on_windows']=runs['ABC']['cfg']['correct_on_windows']
                derived=ROOT/'output/managed_execution/runs'/d['run']/'collected/derived'
                m=measured(cell.metrics,r,cfg,str(derived))
            else:m=r['cell_measurements']
            groups={};strict=[];spec={p['instance']+':'+p['terminal']:p for p in cfg['selected_mos_pair_screens']}
            for key,p in spec.items():
                x=r['selected_mos_pair_extrema'][key];peak=max(abs(x['min']),abs(x['max']));excess=peak-p['screen_v']
                rows.append(dict(corner=corner,variant=variant,pair=key,model=p['model'],limit_V=p['screen_v'],abs_peak_V=peak,excess_V=excess))
                if excess>0:strict.append(dict(pair=key,excess_V=excess))
            for stage in ['A','B','C']:
                p=[x for x in rows if x['corner']==corner and x['variant']==variant and x['pair'].split(':')[0] in ['XDUT.GNN'+stage+t for t in ['N','P']]]
                assert len(p)==12;groups[stage]=dict(worst=max(x['abs_peak_V'] for x in p),strict_exceed_pairs=sum(x['excess_V']>0 for x in p),models=sorted({x['model'] for x in p}),limit_V=p[0]['limit_V'])
            logic_j=[x for x in m['junction_forward_polarity_and_body_current'] if x['pair'].split(':')[0] in ['XDUT.GNN'+s+t for s in ['A','B','C'] for t in ['N','P']]]
            assert len(logic_j)==12
            summary[variant]=dict(run=d['run'],source_result_sha256=d['result_sha256'],native_points=r['native_points'],A_class='core' if variant=='BC' else 'IO',
                stage_screens=groups,all450_strict_records=strict,reference_chain_strict_pairs=sum(g['strict_exceed_pairs'] for g in groups.values()),
                PRE_gate_load=m['PRE_A_gate_load'],ideal_PRE_source_work=m['ideal_PRE_source_work'],complete_delays=m['complete_chain_delays'],
                correct_ON_settling=m['correct_ON_settling'],supply_rail_excursions=m['supply_rail_excursions'],logic_junction_forward_polarity=logic_j,
                body_note='All150 junctions/body statistics retained in ABC original result; this comparison lists12 A/B/C junction records. Total port currents do not identify diode-current fraction.',
                off_gap={n:error_bounds(w,c,n,ref,46.995e-9,47.995e-9) for n,ref in [('xdut.xcdac.bn0','vrefp'),('xdut.xcdac.bp0','vrefn')]},
                direct_stage_VDD_energy_J={s:r['supply_V']*sum(r['current_charge_trapezoids']['xdut.gnn'+s.lower()+'p:'+str(pin)]['signed_C'] for pin in [3,4]) for s in ['A','B','C']},
                ideal_VDD_energy_J=m['ideal_VDD_energy_J'],source_power_not_added_to_VDD=True,warning_codes=r['native_warning_codes'])
        results[corner]=summary
    with (OUT/'all450_pairs_per_case.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    result=dict(status='completed_BC_to_ABC_both_cold_corners_ideal_PRE',source_runs=results,
        actual_PRE_driver='Omitted core XREF.XDRV0.X025; exact topology in pre_driver_boundary.json',
        source_work_accounting='PRE delivered/returned/net work reported separately; never added to ideal VDD energy.',
        screen_and_junction_polarity_are_separate=True,acceptance_pass=None,whole_chain_qualified=False,new_fixture_generated=False)
    (OUT/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');figure(waves)
    for corner,rr in results.items():
        print(corner)
        for v,d in rr.items():
            print(v,'QfC',{e:x['signed_charge_C']*1e15 for e,x in d['PRE_gate_load']['event_native_charge'].items()},
                'PREwork_fJ',{k:x*1e15 for k,x in d['ideal_PRE_source_work'].items() if k.endswith('_J')},
                'tPS',{e:x['PRE_to_GNN0_s']*1e12 for e,x in d['complete_delays'].items()},
                'lowBN_ns',d['correct_ON_settling']['low_after_turnon']['xdut.xcdac.bn0']['remained_inside_from_native_s']*1e9,
                'screens',d['stage_screens'])


def figure(waves):
    os.environ.setdefault('MPLCONFIGDIR',str(HERE/'cache/mpl_current'));import matplotlib
    matplotlib.use('Agg');import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(4,2,figsize=(12,9.5),layout='constrained');colors={'BC':'#236b9c','ABC':'#ce6432'}
    for j,corner in enumerate(['ffcold','sscold']):
        rail=.99 if j==0 else .81
        for i,(node,edge,label) in enumerate([('xdut.gnna',43,'A output: PRE rises'),('xdut.gnn0',43,'GNN0: low path disables'),
                                            ('xdut.gnna',48,'A output: PRE falls'),('xdut.gnn0',48,'GNN0: low path enables')]):
            ax=axes[i,j];length=(.1 if node.endswith('gnna') else .35) if j==0 else (.22 if node.endswith('gnna') else .8)
            for variant,d in waves[corner].items():
                w,c=d['w'],d['c'];t=w[:,0]*1e9;sel=(t>=edge-.01)&(t<=edge+length)
                ax.plot(t[sel],w[sel,c[node]],color=colors[variant],ls='-' if variant=='BC' else '--',lw=1.5,label='IO-'+variant)
            ax.set(xlim=(edge-.01,edge+length),ylabel=('A' if node.endswith('gnna') else 'GNN0')+(' / disable (V)' if edge==43 else ' / enable (V)'));ax.set_ylim(*((-.18,1.28) if j==0 and node.endswith('gnna') else ((-.06,1.08) if j==0 else (-.15,1.05))))
            ax.axvline(edge,color='#999',ls=':',lw=.7)
            for y in [0,rail]:ax.axhline(y,color='#888',ls=':',lw=.7)
            ax.grid(alpha=.18);ax.ticklabel_format(useOffset=False,axis='x')
        axes[0,j].set_title(['FF /0.99V /-40C','SS /0.81V /-40C'][j]);axes[-1,j].set_xlabel('Native simulation time (ns)')
    axes[0,0].legend(loc='upper right',fontsize=9);fig.suptitle('A becomes IO: terminal screen clears, input burden and delay grow',fontsize=14)
    fig.supxlabel('Same physical CDAC/reference/Bootstrap and ideal PRE/rails | comparator reset; no noise/mismatch/PEX\nDotted:command edge and0/VDD rails, not IO ratings. Each panel uses its indicated native time window; no time shift.',fontsize=8)
    fig.savefig(OUT/'BC_to_ABC_cold_timing.png',dpi=170);plt.close(fig)


if __name__=='__main__':compare()
