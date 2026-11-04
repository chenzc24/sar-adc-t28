"""Single unchanged GNN IO final stage; actual ports, full electrical checks."""
from __future__ import print_function
import argparse,gzip,os,struct
import io_cell_analyze as cell
import standard_cell_bbm_analyze as standard
from standard_cell_bbm_hlswap_analyze import full_stress_time
from gnn_measure import measure
VARIANT='original_stdcell_BBM_GNN_IO3_to_existing_IO1_ideal_CODE'


def validate(cfg):
    norm=cell.base.norm;v=list(map(norm,cfg['voltage_saves']));i=list(map(norm,cfg['current_saves']))
    cat=dict((norm(n),x) for n,x in cfg['terminal_current_catalog'].items());eq=dict((norm(n),list(map(norm,q))) for n,q in cfg['kcl_terms'].items())
    if len(set(v))!=len(v) or len(set(i))!=len(i) or set(v)&set(i) or set(cat)!=set(i):raise ValueError('Complete unique actual catalog required')
    inv=cfg['boundary_inventory']
    if (len(v),len(i),len(eq))!=(114,636,34) or (inv['all_actual_MOS'],inv['all_primitives'],inv['native_library_MOS'],inv['BBM_primitive_count'])!=(119,190,42,38):raise ValueError('Exact single-stage inventory required')
    if (inv['voltage_count'],inv['mandatory_currents'],inv['KCL_nodes'])!=(len(v),len(i),len(eq)):raise ValueError('Declared inventory mismatch')
    for n,terms in eq.items():
        if not terms or len(terms)!=len(set(terms)) or set(terms)!=set(b for b,x in cat.items() if norm(x['node'])==n):raise ValueError('Incomplete actual incidence '+n)
    if set(eq)!=set(map(norm,cfg['required_kcl_nodes'])) or set(map(norm,cfg['diagnostic_voltage_columns']))!=set(v):raise ValueError('Full native voltage/KCL coverage required')
    pairs=cfg['selected_mos_pair_screens'];keys=set()
    for p in pairs:
        key=p['instance']+':'+p['terminal'];keys.add(key)
        if p['screen_v']!=(.99 if p['model'] in ['nch_mac','pch_mac'] else 1.98):raise ValueError('Actual-model screen changed')
        ports=dict((t,cat[norm(p['instance']+':'+str(j))]['node']) for j,t in enumerate('dgsb',1));a,b=p['terminal']
        if p['nodes']!=[ports[a],ports[b]] or not set(norm(n) for n in p['nodes'] if n!='0')<=set(v):raise ValueError('Actual terminal map differs')
    if len(pairs)!=714 or len(keys)!=714:raise ValueError('All119 actual MOS714 pairs required')
    if any('gnnan:' in n or 'gnnap:' in n or 'gnnbn:' in n or 'gnnbp:' in n for n in i) or set(v)&set(['xdut.gnna','xdut.gnnb']):raise ValueError('Removed stage aliases forbidden')
    if cfg['variant']!=VARIANT or cfg['source_node']!='code' or cfg['source_current']!='vcode:1':raise ValueError('One GNN-stage-count factor and CODE boundary required')
    if any(n.startswith(('vpre:','vl0:','vgpp:','vgnn:','vgnp:','vgpn:')) for n in i):raise ValueError('Ideal internal force forbidden')
    if cfg['source_peaks'] or cfg['diagnostic_start_s']!=0 or cfg['diagnostic_stop_s']!=52e-9 or cfg['max_total_output_bytes']!=30*cell.MIB:raise ValueError('Full52ns/fixed byte budget required')
    d=cfg['single_GNN_stage_count_delta']
    if not d['all188_other_leaf_records_exact'] or not d['final_model_parameters_and_output_load_exact'] or not d['Rgate_and_all_other_paths_exact']:raise ValueError('Single topology factor exterior changed')
    for name,model,rail in [('GNNCN','nch_18_mac','0'),('GNNCP','pch_18_mac','VDD!')]:
        for j,node in enumerate(['XDUT.GNNDRV','XDUT.PRE',rail,rail],1):
            x=cat[norm('XDUT.'+name+':'+str(j))]
            if x['node']!=node or x['model']!=model:raise ValueError('Final physical IO mapping differs')
    if set(eq['xdut.pre'])!=set(['xdut.x025.xlib.mm0:1','xdut.x025.xlib.mm1:1','xdut.gnncn:2','xdut.gnncp:2']):raise ValueError('Real native X025 and actual PRE load missing')
    return sorted(v+i),sorted(i),eq


def initial_metrics(result,cfg,out):
    # Reuse native parser, replace only the legacy metrics that require deleted
    # A/B nodes. No fabricated names or zero-valued removed-device energies.
    e=next(x for x in result['native_exports'] if x['file']=='cell.native.f64le.gz');c=dict((n,j) for j,n in enumerate(e['columns']));fmt=struct.Struct('<'+'d'*len(c))
    static=dict((p['name'],dict(samples=0,start_s=None,stop_s=None,min={},max={},sum={})) for p in cfg['static_windows'])
    settling=dict((p['name'],dict((n,dict(last_outside_1mV_s=None,remained_inside_from_native_s=None,final_error_V=None)) for n in ['xdut.xcdac.bn0','xdut.xcdac.bp0'])) for p in cfg['load_windows'])
    count=0
    with gzip.open(os.path.join(out,e['file']),'rb') as f:
        while True:
            raw=f.read(fmt.size)
            if not raw:break
            if len(raw)!=fmt.size:raise ValueError('Partial initial-metrics row')
            row=fmt.unpack(raw);t=row[0];count+=1
            for p in cfg['static_windows']:
                if p['start_s']<=t<=p['stop_s']:
                    q=static[p['name']];q['samples']+=1;q['stop_s']=t
                    if q['start_s'] is None:q['start_s']=t
                    for n in cfg['static_observations']:
                        value=row[c[n]];q['min'][n]=min(q['min'].get(n,value),value);q['max'][n]=max(q['max'].get(n,value),value);q['sum'][n]=q['sum'].get(n,0.)+value
            for p in cfg['load_windows']:
                if p['start_s']<=t<=p['stop_s']:
                    for n,q in settling[p['name']].items():
                        target=('vrefp' if p['select_high'] else 'vrefn') if n.endswith('bn0') else ('vrefn' if p['select_high'] else 'vrefp');error=row[c[n]]-row[c[target]];q['final_error_V']=error
                        if abs(error)>.001:q['last_outside_1mV_s']=t;q['remained_inside_from_native_s']=None
                        elif q['remained_inside_from_native_s'] is None:q['remained_inside_from_native_s']=t
    if count!=e['rows']:raise ValueError('Native history incomplete')
    for p in cfg['static_windows']:
        q=static[p['name']]
        if not q['samples']:raise ValueError('Missing static window')
        q['native_sample_mean']=dict((n,x/q['samples']) for n,x in q.pop('sum').items());q['independent_expected_logic']=p['expected_logic']
        q['logic_rail_max_deviation_V']=dict((n,max(abs(q['min'][n]-bit*cfg['supply_V']),abs(q['max'][n]-bit*cfg['supply_V']))) for n,bit in p['expected_logic'].items())
    return dict(static_plateaus=static,local_inverter_delays={},load_settling=settling,
        upstream_core_direct_VDD_terminal_energy_J=None,
        test_cell_direct_VDD_terminal_energy_J=cfg['supply_V']*sum(result['current_charge_trapezoids']['xdut.gnncp:'+str(j)]['signed_C'] for j in [3,4]),
        ideal_VDD_energy_J=-cfg['supply_V']*result['current_charge_trapezoids']['vvdd:1']['signed_C'],interval_s=[0.,52e-9],
        power_note='Actual external VDD, separate internal PRE work; no full ADC verdict. Deleted A/B energy is not applicable, not zero.',no_ADC_or_async_timing_or_power_qualification=True)


def measurements(result,cfg,out):
    m=standard.measurements(initial_metrics,result,cfg,out)
    m.pop('GNN_AB_IO_direct_VDD_energy_J',None)
    m['removed_A_B_stage_measurements']=dict(applicable=False,deleted_instances=['GNNAN','GNNAP','GNNBN','GNNBP'],no_zero_or_alias_replacement=True)
    m['GNN_single_IO_actual_measurements']=measure(result,cfg,out)
    m['all_terminal_native_phase_time']=full_stress_time(result,cfg,out)
    m['all_terminal_native_phase_time']['interpretation']=m['all_terminal_native_phase_time']['interpretation'].replace('All738','All714 actual candidate')
    m['boundary']=cfg['scope'];m['test_cell_role']='Unchanged final GNNCN/CP pair, now driven directly by real PRE'
    return m


def analyze(run,out):
    old_v,old_m=cell.validate,cell.metrics
    try:
        cell.validate=validate;cell.metrics=measurements
        return cell.analyze(run,out)
    finally:cell.validate,cell.metrics=old_v,old_m


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
    if os.name=='posix':
        import resource
        _,hard=resource.getrlimit(resource.RLIMIT_AS);limit=240*cell.MIB if hard==resource.RLIM_INFINITY else min(hard,240*cell.MIB);resource.setrlimit(resource.RLIMIT_AS,(limit,hard))
    r=analyze(a.run_dir,a.output_dir);print('GNN_ONE_IO_DIAGNOSTIC_READY',r['native_points'],'acceptance_pass=null')
