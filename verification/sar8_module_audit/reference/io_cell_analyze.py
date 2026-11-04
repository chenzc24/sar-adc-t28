"""Independent-command loaded inverter feasibility analysis. Python2.7/3."""
from __future__ import print_function
import argparse
import gzip
import os
import re
import struct
import sys
sys.dont_write_bytecode=True
import reference_current_analyze as base
MIB=1024*1024


def validate(cfg):
    v=[base.norm(n) for n in cfg['voltage_saves']];i=[base.norm(n) for n in cfg['current_saves']]
    if len(set(v))!=len(v) or len(set(i))!=len(i) or set(v)&set(i) or not i:
        raise ValueError('Unique selected voltage/current catalogs required')
    catalog=dict((base.norm(n),d) for n,d in cfg['terminal_current_catalog'].items())
    if set(catalog)!=set(i):raise ValueError('All selected currents require catalog entries')
    eq=dict((base.norm(n),[base.norm(t) for t in terms]) for n,terms in cfg['kcl_terms'].items())
    if len(eq)!=7:raise ValueError('Seven upstream/downstream KCL nodes required')
    for n,terms in eq.items():
        expected=set(k for k,d in catalog.items() if base.norm(d['node'])==n)
        if not terms or len(set(terms))!=len(terms) or set(terms)!=expected:
            raise ValueError('Complete KCL incidence required '+n)
    need=set(eq)|set(base.norm(n) for n in cfg['diagnostic_voltage_columns']+cfg['edge_nodes']+list(cfg['initial_witness_v']))
    need|=set(base.norm(n) for p in cfg['selected_mos_pair_screens'] for n in p['nodes'])-set(['0'])
    if not need<=set(v) or 'vdd!' not in v:raise ValueError('Required voltage missing')
    if cfg['source_peaks'] or cfg['diagnostic_start_s']!=0 or cfg['diagnostic_stop_s']!=cfg['source_history_stop_s']:
        raise ValueError('No invented reference peaks; complete independent bench history required')
    if cfg['max_total_output_bytes']!=30*MIB:raise ValueError('Fixed30MiB derived budget required')
    return sorted(v+i),sorted(i),eq


def writer(original,cfg):
    _,_,eq=validate(cfg)
    wanted=set(['time']+[base.norm(n) for n in cfg['diagnostic_voltage_columns']]+cfg['diagnostic_current_columns']+['kcl:'+n for n in eq])
    class OneTrace(original):
        def __init__(self,budget,name,columns):
            self.width=len(columns)
            if name=='fault.native.f64le.gz':
                if not wanted<=set(columns):raise ValueError('Diagnostic field absent')
                self.ids=[j for j,n in enumerate(columns) if n in wanted];name='cell.native.f64le.gz'
            elif name=='kcl.full.native.f64le.gz':
                self.ids=[columns.index('time')];name='native.time.f64le.gz'
            else:raise ValueError('Unexpected stream')
            original.__init__(self,budget,name,[columns[j] for j in self.ids])
        def row(self,values):
            if len(values)!=self.width:raise ValueError('Native record width mismatch')
            original.row(self,[values[j] for j in self.ids])
    return OneTrace


def metrics(result,cfg,out):
    entry=next(x for x in result['native_exports'] if x['file']=='cell.native.f64le.gz')
    c=dict((n,j) for j,n in enumerate(entry['columns']));pack=struct.Struct('<'+'d'*len(c))
    phases=cfg['static_windows'];stat=dict((p['name'],dict(samples=0,start_s=None,stop_s=None,min={},max={},sum={})) for p in phases)
    settle={}
    for p in cfg['load_windows']:
        settle[p['name']]=dict((n,dict(last_outside_1mV_s=None,remained_inside_from_native_s=None,final_error_V=None)) for n in ['xdut.xcdac.bn0','xdut.xcdac.bp0'])
    count=0
    with gzip.open(os.path.join(out,entry['file']),'rb') as stream:
        while True:
            data=stream.read(pack.size)
            if not data:break
            if len(data)!=pack.size:raise ValueError('Partial native row')
            row=pack.unpack(data);t=row[0];count+=1
            for phase in phases:
                if phase['start_s']<=t<=phase['stop_s']:
                    s=stat[phase['name']];s['samples']+=1;s['stop_s']=t
                    if s['start_s'] is None:s['start_s']=t
                    for n in cfg['static_observations']:
                        value=row[c[n]];s['min'][n]=min(s['min'].get(n,value),value);s['max'][n]=max(s['max'].get(n,value),value)
                        s['sum'][n]=s['sum'].get(n,0.)+value
            for phase in cfg['load_windows']:
                if phase['start_s']<=t<=phase['stop_s']:
                    for node in settle[phase['name']]:
                        target=('vrefp' if phase['select_high'] else 'vrefn') if node.endswith('bn0') else ('vrefn' if phase['select_high'] else 'vrefp')
                        error=row[c[node]]-row[c[target]];s=settle[phase['name']][node];s['final_error_V']=error
                        if abs(error)>.001:s['last_outside_1mV_s']=t;s['remained_inside_from_native_s']=None
                        elif s['remained_inside_from_native_s'] is None:s['remained_inside_from_native_s']=t
    if count!=entry['rows']:raise ValueError('Native table incomplete')
    for phase,s in stat.items():
        if not s['samples']:raise ValueError('Missing static plateau '+phase)
        s['native_sample_mean']=dict((n,value/s['samples']) for n,value in s.pop('sum').items())
        contract=next(p for p in phases if p['name']==phase)
        s['independent_expected_logic']=contract['expected_logic']
        s['logic_rail_max_deviation_V']=dict((n,max(abs(s['min'][n]-bit*cfg['supply_V']),abs(s['max'][n]-bit*cfg['supply_V'])))
            for n,bit in contract['expected_logic'].items())
    delays={}
    for event in cfg['logic_events']:
        observed={}
        for n,direction in event['edge_directions'].items():
            found=[e for e in result['half_vdd_events'].get(n,[]) if e['direction']==direction and event['start_s']<=e['estimated_time_s']<=event['stop_s']]
            observed[n]=found[0] if len(found)==1 else None
        inp=observed['xdut.gnnb'];output=observed['xdut.gnndrv'];gate=observed['xdut.gnn0']
        delays[event['name']]=dict(native_edge_witnesses=observed,
            B_to_C_s=None if inp is None or output is None else output['estimated_time_s']-inp['estimated_time_s'],
            B_to_load_gate_s=None if inp is None or gate is None else gate['estimated_time_s']-inp['estimated_time_s'],
            interpretation='Missing/extra edge is reported as unknown, never accepted')
    energy=-cfg['supply_V']*result['current_charge_trapezoids']['vvdd:1']['signed_C']
    def rail_energy(stages):
        return cfg['supply_V']*sum(result['current_charge_trapezoids']['xdut.gnn'+stage+'p:'+str(pin)]['signed_C']
                                   for stage in stages for pin in [3,4])
    return dict(static_plateaus=stat,local_inverter_delays=delays,load_settling=settle,
        threshold_note='1mV diagnostic only; expected rail selected by independent logical command, never observed gates',
        ideal_VDD_energy_J=energy,interval_s=[0,cfg['source_history_stop_s']],
        test_cell_direct_VDD_terminal_energy_J=rail_energy(['c']),
        upstream_core_direct_VDD_terminal_energy_J=rail_energy(['a','b']),
        power_note='Direct VDD terminal exchange includes source+bulk currents; gate/drain work and ideal command-driver energy are separate, no fullADC power verdict.',
        no_ADC_or_async_timing_or_power_qualification=True)


def analyze(run,out):
    run,out=os.path.realpath(run),os.path.realpath(out)
    if out!=os.path.join(run,'derived') or (os.path.isdir(out) and os.listdir(out)):
        raise ValueError('Fresh managed derived directory required')
    cfg=base.read_json(base.safe_file(run,'inputs/measurement.json'));validate(cfg)
    state=base.read_json(base.safe_file(run,'simulation.state.json'));native=state.get('native',{})
    if state.get('status')!='complete' or state.get('exit_code')!=0 or not native.get('native_analysis_pass') or not native.get('zero_error_footer'):
        raise ValueError('Native simulation completion/PASS/zero-error required')
    with open(base.safe_file(run,'raw/logStatus')) as f:
        if not re.search(r'\btran_cell\s+PASS\b',f.read(65536)):raise ValueError('tran_cell PASS missing')
    for name,expected in cfg['required_input_sha256'].items():
        if base.digest(base.safe_file(run,'inputs/'+name))!=expected:raise ValueError('Frozen input changed '+name)
    files=[x for x in os.listdir(os.path.join(run,'raw')) if x.endswith('.tran.tran')]
    if len(files)!=1:raise ValueError('Exactly one native scalar transient required')
    if not os.path.isdir(out):os.makedirs(out)
    budget=base.Budget(out,30*MIB);log=base.preserve_log(run,budget)
    old_v,old_w=base.validate_config,base.NativeGzip
    try:
        base.validate_config=validate;base.NativeGzip=writer(old_w,cfg)
        result=base.summarize(base.safe_file(run,'raw/'+files[0]),cfg,budget,None)
    finally:base.validate_config=old_v;base.NativeGzip=old_w
    result.update(scope=cfg['scope'],cell_measurements=metrics(result,cfg,out),stimulus_contract=cfg['stimulus_contract'],
        cell_variant=cfg['variant'],supply_V=cfg['supply_V'],original_simulator_log=log,
        native_effective_settings=native.get('effective_settings'),native_warning_codes=native.get('warning_codes'),
        measurement_sha256=base.digest(base.safe_file(run,'inputs/measurement.json')),
        waveform_note='cell.native includes complete bench history, critical voltages/currents/all7 KCL. Aux stream stores time only; no native points discarded.')
    budget.json('native.columns.json',dict(exports=result['native_exports']))
    if sys.platform.startswith('linux'):
        import resource
        result['analysis_peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        if result['analysis_peak_rss_bytes']>256*MIB:raise ValueError('RSS cap exceeded')
    else:result['analysis_peak_rss_bytes']=None
    budget.json('result.json',result);return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);args=p.parse_args()
    if sys.platform.startswith('linux'):
        import resource
        _,hard=resource.getrlimit(resource.RLIMIT_AS);limit=240*MIB if hard==resource.RLIM_INFINITY else min(hard,240*MIB)
        resource.setrlimit(resource.RLIMIT_AS,(limit,hard))
    r=analyze(args.run_dir,args.output_dir);print('IO_CELL_NATIVE_DIAGNOSTIC_OK',r['native_points'],'acceptance_pass=null')


if __name__=='__main__':main()
