"""B-stage IO measurement extension; frozen IO-C reducer stays unchanged."""
from __future__ import print_function
import argparse,gzip,os,struct,sys
sys.dont_write_bytecode=True
import io_cell_analyze as cell


def validate(cfg):
    selected=cell.validate(cfg)
    if cfg['variant']!='IO_BC_A_core':raise ValueError('Explicit A-core/B-C-IO variant required')
    pairs=cfg['selected_mos_pair_screens']
    if len(pairs)!=450:raise ValueError('All450 screens required')
    for stage,models,limit in [('A',['nch_mac','pch_mac'],.99),('B',['nch_18_mac','pch_18_mac'],1.98),
                               ('C',['nch_18_mac','pch_18_mac'],1.98)]:
        local=[p for p in pairs if p['instance'] in ['XDUT.GNN'+stage+t for t in ['N','P']]]
        if len(local)!=12 or any(p['model'] not in models or p['screen_v']!=limit for p in local):
            raise ValueError('Stage class/terminal-screen mismatch '+stage)
    return selected


def extra_metrics(original,result,cfg,out):
    m=original(result,cfg,out)
    # B is now IO: preserve the sum under an accurate label and expose each stage.
    m['upstream_AB_direct_VDD_terminal_energy_J']=m.pop('upstream_core_direct_VDD_terminal_energy_J')
    for stage,label in [('a','upstream_A_core'),('b','test_B_IO'),('c','downstream_C_IO')]:
        m[label+'_direct_VDD_terminal_energy_J']=cfg['supply_V']*sum(
            result['current_charge_trapezoids']['xdut.gnn'+stage+'p:'+str(pin)]['signed_C'] for pin in [3,4])
    m['test_cell_role']='B is the changed cell; retained test_cell_direct_VDD_terminal_energy_J refers to downstream C for baseline compatibility.'
    gate=dict(min_A=None,max_A=None,min_time_s=None,max_time_s=None)
    windows=dict((p['name'],dict(samples=0,first_native_s=None,last_native_s=None,signed_charge_C=0.,absolute_charge_C=0.))
                 for p in cfg['B_input_charge_windows'])
    previous={}
    e=next(x for x in result['native_exports'] if x['file']=='cell.native.f64le.gz')
    c=dict((n,j) for j,n in enumerate(e['columns']));fmt=struct.Struct('<'+'d'*len(c))
    with gzip.open(os.path.join(out,e['file']),'rb') as stream:
        while True:
            raw=stream.read(fmt.size)
            if not raw:break
            if len(raw)!=fmt.size:raise ValueError('Incomplete native row')
            row=fmt.unpack(raw);t=row[0];current=row[c['xdut.gnnbn:2']]+row[c['xdut.gnnbp:2']]
            for kind,compare in [('min',lambda a,b:a<b),('max',lambda a,b:a>b)]:
                if gate[kind+'_A'] is None or compare(current,gate[kind+'_A']):gate[kind+'_A']=current;gate[kind+'_time_s']=t
            for phase in cfg['B_input_charge_windows']:
                name=phase['name'];s=windows[name]
                if phase['start_s']<=t<=phase['stop_s']:
                    if s['first_native_s'] is None:s['first_native_s']=t
                    if name in previous:
                        pt,pi=previous[name];dt=t-pt
                        s['signed_charge_C']+=(current+pi)*dt*.5
                        s['absolute_charge_C']+=(abs(current)+abs(pi))*dt*.5
                    previous[name]=(t,current);s['last_native_s']=t;s['samples']+=1
    if any(x['samples']<2 for x in windows.values()):raise ValueError('B input-load event window missing')
    gate.update(event_native_charge=windows,
        full_signed_charge_C=sum(result['current_charge_trapezoids'][n]['signed_C'] for n in ['xdut.gnnbn:2','xdut.gnnbp:2']),
        interpretation='Sum of B N/P total native gate-port currents, positive into B, loading core A; not intrinsic Cgd/channel decomposition.')
    m['B_input_load_current']=gate
    delays={}
    for phase in cfg['logic_events']:
        disable=phase['name']=='disable_low';witness={}
        for node,direction in [('pre','rising' if disable else 'falling'),('xdut.gnna','falling' if disable else 'rising'),
                               ('xdut.gnnb','rising' if disable else 'falling')]:
            found=[x for x in result['half_vdd_events'][node] if x['direction']==direction and phase['start_s']<=x['estimated_time_s']<=phase['stop_s']]
            witness[node]=found[0] if len(found)==1 else None
        def delay(a,b):
            return None if witness[a] is None or witness[b] is None else witness[b]['estimated_time_s']-witness[a]['estimated_time_s']
        delays[phase['name']]=dict(native_edge_witnesses=witness,PRE_to_A_s=delay('pre','xdut.gnna'),A_to_B_s=delay('xdut.gnna','xdut.gnnb'))
    m['upstream_stage_delays']=delays
    m['load_window_note']='Original44..47ns window includes turnoff from46.995ns. Preserve values; compare stable ON before46.995ns and off-gap separately using full native waveform.'
    return m


def analyze(run,out):
    cfg=cell.base.read_json(cell.base.safe_file(os.path.realpath(run),'inputs/measurement.json'));validate(cfg)
    original=cell.metrics
    try:
        cell.metrics=lambda result,config,path:extra_metrics(original,result,config,path)
        return cell.analyze(run,out)
    finally:cell.metrics=original


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);args=p.parse_args()
    if sys.platform.startswith('linux'):
        import resource
        _,hard=resource.getrlimit(resource.RLIMIT_AS);limit=240*cell.MIB if hard==resource.RLIM_INFINITY else min(hard,240*cell.MIB)
        resource.setrlimit(resource.RLIMIT_AS,(limit,hard))
    r=analyze(args.run_dir,args.output_dir);print('IO_B_STAGE_NATIVE_DIAGNOSTIC_OK',r['native_points'],'acceptance_pass=null')


if __name__=='__main__':main()
