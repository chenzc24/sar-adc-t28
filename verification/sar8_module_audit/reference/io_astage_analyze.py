"""A-only IO extension: ideal PRE work, complete timing, body polarity."""
from __future__ import print_function
import argparse,gzip,os,struct,sys
sys.dont_write_bytecode=True
import io_cell_analyze as cell
import io_bstage_analyze as bstage


def validate(cfg):
    answer=cell.validate(cfg)
    if cfg['variant']!='IO_ABC_ideal_PRE' or len(cfg['selected_mos_pair_screens'])!=450:raise ValueError('Explicit ABC-IO450-screen fixture required')
    for stage in ['A','B','C']:
        local=[p for p in cfg['selected_mos_pair_screens'] if p['instance'] in ['XDUT.GNN'+stage+t for t in ['N','P']]]
        if len(local)!=12 or any(p['model'] not in ['nch_18_mac','pch_18_mac'] or p['screen_v']!=1.98 for p in local):
            raise ValueError('Actual IO model/screen mapping required '+stage)
    return answer


def measured(original,result,cfg,out):
    m=bstage.extra_metrics(original,result,cfg,out)
    m['upstream_A_IO_direct_VDD_terminal_energy_J']=m.pop('upstream_A_core_direct_VDD_terminal_energy_J')
    m['test_cell_role']='Only A changes; PRE is still ideal. Legacy test_cell energy refers to C; A energy has explicit A_IO label.'
    junctions=[]
    for p in cfg['selected_mos_pair_screens']:
        if p['terminal'] not in ['bd','bs']:continue
        key=p['instance']+':'+p['terminal'];x=result['selected_mos_pair_extrema'][key];n_type=p['model'].startswith('nch')
        peak=x['max'] if n_type else -x['min'];time=x['max_time_s'] if n_type else x['min_time_s']
        branch=p['instance'].lower()+':4'
        junctions.append(dict(pair=key,model=p['model'],nodes=p['nodes'],forward_polarity='Vbody-Vdiffusion' if n_type else 'Vdiffusion-Vbody',
            signed_forward_min_V=x['min'] if n_type else -x['max'],signed_forward_max_V=peak,
            positive_forward_polarity_peak_V=max(0.,peak),peak_time_s=time,
            body_current_extrema=result['voltage_and_current_extrema'][branch],
            body_native_charge=result['current_charge_trapezoids'][branch],
            body_current_at_polarity_peak_A=None,
            interpretation='Positive junction voltage is forward polarity; no assumed diode threshold or proof of channel/diode-current fraction. Body current is total native port4.'))
    events=dict((p['name'],dict(samples=0,first_native_s=None,last_native_s=None,signed_charge_C=0.,absolute_charge_C=0.)) for p in cfg['PRE_input_charge_windows'])
    previous={};power=dict(net_delivered_J=0.,positive_delivered_J=0.,returned_to_source_J=0.,A_gate_port_work_J=0.)
    gate=dict(min_A=None,max_A=None,min_time_s=None,max_time_s=None,full_signed_charge_C=0.)
    last=None;max_kcl=0.;max_kcl_time=None
    settling={p['name']:dict((n,dict(samples=0,last_outside_1mV_s=None,remained_inside_from_native_s=None,last_native_s=None,final_error_V=None))
        for n in ['xdut.xcdac.bn0','xdut.xcdac.bp0']) for p in cfg['correct_on_windows']}
    e=next(x for x in result['native_exports'] if x['file']=='cell.native.f64le.gz');c=dict((n,j) for j,n in enumerate(e['columns']));fmt=struct.Struct('<'+'d'*len(c))
    with gzip.open(os.path.join(out,e['file']),'rb') as stream:
        while True:
            raw=stream.read(fmt.size)
            if not raw:break
            if len(raw)!=fmt.size:raise ValueError('Incomplete native row')
            row=fmt.unpack(raw);t=row[0];voltage=row[c['pre']];gates=row[c['xdut.gnnan:2']]+row[c['xdut.gnnap:2']];source=row[c['vpre:1']]
            delivered=-voltage*source;gate_work=voltage*gates;kcl=source+gates
            if abs(kcl)>max_kcl:max_kcl=abs(kcl);max_kcl_time=t
            for kind,less in [('min',True),('max',False)]:
                if gate[kind+'_A'] is None or (gates<gate[kind+'_A'] if less else gates>gate[kind+'_A']):gate[kind+'_A']=gates;gate[kind+'_time_s']=t
            if last is not None:
                pt,pg,pd,pw=last;dt=t-pt
                gate['full_signed_charge_C']+=(gates+pg)*dt*.5;power['net_delivered_J']+=(delivered+pd)*dt*.5
                power['positive_delivered_J']+=(max(delivered,0)+max(pd,0))*dt*.5
                power['returned_to_source_J']+=(max(-delivered,0)+max(-pd,0))*dt*.5
                power['A_gate_port_work_J']+=(gate_work+pw)*dt*.5
            last=(t,gates,delivered,gate_work)
            for p in cfg['PRE_input_charge_windows']:
                if p['start_s']<=t<=p['stop_s']:
                    s=events[p['name']]
                    if s['first_native_s'] is None:s['first_native_s']=t
                    if p['name'] in previous:
                        pt,pi=previous[p['name']];s['signed_charge_C']+=(gates+pi)*(t-pt)*.5;s['absolute_charge_C']+=(abs(gates)+abs(pi))*(t-pt)*.5
                    previous[p['name']]=(t,gates);s['samples']+=1;s['last_native_s']=t
            for p in cfg['correct_on_windows']:
                if p['start_s']<=t and (t<p['stop_s'] if p['stop_exclusive'] else t<=p['stop_s']):
                    for node in settling[p['name']]:
                        ref=('vrefp' if p['select_high'] else 'vrefn') if node.endswith('bn0') else ('vrefn' if p['select_high'] else 'vrefp')
                        error=row[c[node]]-row[c[ref]];s=settling[p['name']][node];s['samples']+=1;s['last_native_s']=t;s['final_error_V']=error
                        if abs(error)>.001:s['last_outside_1mV_s']=t;s['remained_inside_from_native_s']=None
                        elif s['remained_inside_from_native_s'] is None:s['remained_inside_from_native_s']=t
            for item in junctions:
                b=item['pair'].split(':')[0].lower()+':4'
                if b in c and abs(t-item['peak_time_s'])<1e-18:item['body_current_at_polarity_peak_A']=row[c[b]]
    if any(x['samples']<2 for x in events.values()) or any(x['samples']==0 for phase in settling.values() for x in phase.values()):raise ValueError('Required measurement window absent')
    gate.update(event_native_charge=events,interpretation='Total N/P gate currents entering A at ideal PRE; not intrinsic capacitance decomposition.')
    power.update(interval_s=[0,cfg['source_history_stop_s']],max_PRE_node_KCL_A=max_kcl,max_PRE_node_KCL_time_s=max_kcl_time,
        source_work_minus_A_gate_work_J=power['net_delivered_J']-power['A_gate_port_work_J'],
        sign='VPRE current positive into source; delivered work is integral(-VPRE*IPRE), returned work is separately positive.',
        accounting='Reported separately from ideal VDD energy; not added to it and not a fullADC power figure. Signed native trapezoids, ideal-source boundary only.')
    delays={}
    for p in cfg['PRE_input_charge_windows']:
        disable=p['name']=='disable_low';witness={}
        for node,direction in [('pre','rising' if disable else 'falling'),('xdut.gnna','falling' if disable else 'rising'),
            ('xdut.gnnb','rising' if disable else 'falling'),('xdut.gnndrv','falling' if disable else 'rising'),('xdut.gnn0','falling' if disable else 'rising')]:
            found=[x for x in result['half_vdd_events'][node] if x['direction']==direction and p['start_s']<=x['estimated_time_s']<=p['stop_s']]
            witness[node]=found[0] if len(found)==1 else None
        def delta(a,b):return None if witness[a] is None or witness[b] is None else witness[b]['estimated_time_s']-witness[a]['estimated_time_s']
        delays[p['name']]=dict(native_edge_witnesses=witness,PRE_to_A_s=delta('pre','xdut.gnna'),A_to_B_s=delta('xdut.gnna','xdut.gnnb'),
            B_to_C_s=delta('xdut.gnnb','xdut.gnndrv'),C_to_GNN0_s=delta('xdut.gnndrv','xdut.gnn0'),PRE_to_GNN0_s=delta('pre','xdut.gnn0'))
    rail={}
    for node in ['pre','xdut.gnna','xdut.gnnb','xdut.gnndrv','xdut.gnn0']:
        x=result['voltage_and_current_extrema'][node];rail[node]=dict(min_V=x['min'],max_V=x['max'],
            below_ground_V=max(0.,-x['min']),above_VDD_V=max(0.,x['max']-cfg['supply_V']),min_time_s=x['min_time_s'],max_time_s=x['max_time_s'])
    m.update(PRE_A_gate_load=gate,ideal_PRE_source_work=power,complete_chain_delays=delays,correct_ON_settling=settling,
        junction_forward_polarity_and_body_current=junctions,supply_rail_excursions=rail,
        interface_qualification='PRE remains ideal; original physical X025 and upstream fanout are not exercised; no chain acceptance.')
    return m


def analyze(run,out):
    cfg=cell.base.read_json(cell.base.safe_file(os.path.realpath(run),'inputs/measurement.json'));validate(cfg);old=cell.metrics
    try:
        cell.metrics=lambda r,c,p:measured(old,r,c,p)
        return cell.analyze(run,out)
    finally:cell.metrics=old


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
    if sys.platform.startswith('linux'):
        import resource
        _,hard=resource.getrlimit(resource.RLIMIT_AS);limit=240*cell.MIB if hard==resource.RLIM_INFINITY else min(hard,240*cell.MIB);resource.setrlimit(resource.RLIMIT_AS,(limit,hard))
    r=analyze(a.run_dir,a.output_dir);print('IO_A_STAGE_NATIVE_DIAGNOSTIC_OK',r['native_points'],'acceptance_pass=null')


if __name__=='__main__':main()
