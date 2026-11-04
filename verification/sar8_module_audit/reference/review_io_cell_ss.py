"""SS core read-only checkpoint; no missing IO case is fabricated."""
import json
from compare_io_cell import HERE,NODES,load,bounds,error_bounds,settled


def checkpoint():
    d=load('core','sscold');r,w,c=d['result'],d['w'],d['c'];cfg=d['cfg'];m=r['cell_measurements']
    pairs={p['instance']+':'+p['terminal']:p for p in cfg['selected_mos_pair_screens']}
    assert len(pairs)==450 and r['supply_V']==.81
    stress=[]
    for name,spec in pairs.items():
        x=r['selected_mos_pair_extrema'][name];peak=max(abs(x['min']),abs(x['max']))
        stress.append(dict(pair=name,limit_V=spec['screen_v'],peak_abs_V=peak,excess_mV=(peak-spec['screen_v'])*1e3))
    groups={}
    for stage in ['A','B','C']:
        q=[x for x in stress if x['pair'].split(':')[0] in ['XDUT.GNN'+stage+t for t in ['N','P']]];assert len(q)==12
        groups[stage]=dict(worst=max(q,key=lambda x:x['excess_mV']),strict_exceed_pairs=sum(x['excess_mV']>0 for x in q))
    out=dict(status='SS_core_only_IO_not_yet_collected',run=d['run'],source_result_sha256=d['result_sha256'],
        receipt_bytes=d['receipt_bytes'],native_points=r['native_points'],supply_V=.81,temperature_C=-40,
        scope=r['scope'],acceptance_pass=None,ADC_qualification=False,
        IO_original_queue_timeout_is_not_a_circuit_result=True,
        node_extrema={n:bounds(w,c,n) for n in NODES},group_terminal_screens=groups,
        all450_strict_exceed_pairs=sum(x['excess_mV']>0 for x in stress),
        delay_measurements=m['local_inverter_delays'],original_load_window_metrics=m['load_settling'],
        high_reference_error_observations={phase:{n:error_bounds(w,c,n,ref,start,stop) for n,ref in
            [('xdut.xcdac.bn0','vrefp'),('xdut.xcdac.bp0','vrefn')]}
            for phase,start,stop in [('stable_plateau',45e-9,46e-9),('before_off_edge',46.98e-9,46.995e-9),
                                   ('off_edge_and_BBM_gap',46.995e-9,47.995e-9)]},
        stable_on_settling={phase:{n:settled(w,c,n,ref,start,stop) for n,ref in targets}
            for phase,start,stop,targets in [
                ('high_before_off_edge',44.005e-9,46.995e-9,[('xdut.xcdac.bn0','vrefp'),('xdut.xcdac.bp0','vrefn')]),
                ('low_after_on',48.005e-9,52.000001e-9,[('xdut.xcdac.bn0','vrefn'),('xdut.xcdac.bp0','vrefp')])]},
        energy_J={k:x for k,x in m.items() if k.endswith('_J')},
        max_KCL_pA=max(x['max_abs_a'] for x in r['node_kcl'].values())*1e12,
        warning_codes=r['native_warning_codes'],effective_settings=r['native_effective_settings'])
    directory=HERE/'generated/io_cell_ss_comparison';directory.mkdir(exist_ok=True)
    (directory/'ss_core_checkpoint.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(native_points=out['native_points'],groups=groups,
        all450_strict_exceed_pairs=out['all450_strict_exceed_pairs'],settling=out['stable_on_settling'],
        off_gap=out['high_reference_error_observations']['off_edge_and_BBM_gap']),indent=2))


if __name__=='__main__':checkpoint()
