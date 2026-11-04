"""One-resistor mechanism experiment analyzer. Python2.7/3, stdlib only."""
from __future__ import print_function
import argparse
import gzip
import os
import struct
import sys
sys.dont_write_bytecode=True
import reference_current_analyze as base

FROZEN_VALIDATE=base.validate_config
NEW_GATE='xdut.xref.xdrv0.gnn_cg'
MIB=1024*1024


def validate_candidate(cfg):
    equations=cfg['kcl_terms']
    found=[n for n in equations if base.norm(n)==NEW_GATE]
    if len(equations)!=6 or len(found)!=1:
        raise ValueError('Six nodes including new common gate required')
    legacy=dict(cfg)
    legacy['kcl_terms']=dict((n,v) for n,v in equations.items() if n!=found[0])
    selected,currents,normalized=FROZEN_VALIDATE(legacy)
    terms=[base.norm(x) for x in equations[found[0]]]
    expected=set(base.norm(n) for n,item in cfg['terminal_current_catalog'].items() if base.norm(item['node'])==NEW_GATE)
    if len(terms)!=3 or len(set(terms))!=3 or set(terms)!=expected or not set(terms)<=set(currents):
        raise ValueError('New common gate KCL must include R return and both MOS gates')
    if NEW_GATE not in selected:
        raise ValueError('New gate voltage save missing')
    normalized[NEW_GATE]=terms
    return selected,currents,normalized


def writer_type(original,cfg):
    _,currents,equations=validate_candidate(cfg)
    incident=sorted(set(n for terms in equations.values() for n in terms))
    class SelectedWriter(original):
        def __init__(self,budget,name,columns):
            self.input_width=len(columns)
            if name=='kcl.full.native.f64le.gz':
                wanted=set(['time']+incident+['kcl:'+n for n in equations])
            elif name=='fault.native.f64le.gz':
                wanted=set(['time']+[base.norm(n) for n in cfg['diagnostic_voltage_columns']]+incident+['kcl:'+n for n in equations])
            else:raise ValueError('Unexpected export stream')
            if not wanted<=set(columns):raise ValueError('Native writer interface missing required column')
            self.indices=[i for i,n in enumerate(columns) if n in wanted]
            if len(self.indices)!=len(wanted):raise ValueError('Duplicate selected stream field')
            original.__init__(self,budget,name,[columns[i] for i in self.indices])
        def row(self,values):
            if len(values)!=self.input_width:raise ValueError('Native row shape mismatch')
            original.row(self,[values[i] for i in self.indices])
    return SelectedWriter


def load_and_power_metrics(result,cfg,output):
    contract=cfg['experiment']['load_diagnostic']
    export=next(x for x in result['native_exports'] if x['file']=='fault.native.f64le.gz')
    names=export['columns'];index=dict((n,i) for i,n in enumerate(names))
    pack=struct.Struct('<'+'d'*len(names))
    nodes={'xdut.xcdac.bn0':'vrefp','xdut.xcdac.bp0':'vrefn'}
    state=dict((n,dict(max_abs_error_V=0.,final_error_V=None,last_outside_tolerance_s=None,
                         remained_within_tolerance_from_native_s=None)) for n in nodes)
    rows=0
    with gzip.open(os.path.join(output,export['file']),'rb') as stream:
        while True:
            data=stream.read(pack.size)
            if not data:break
            if len(data)!=pack.size:raise ValueError('Incomplete native fault row')
            row=pack.unpack(data);rows+=1;t=row[0]
            if t<contract['independent_command_time_s']:continue
            for node,target in nodes.items():
                error=row[index[node]]-row[index[target]];item=state[node]
                item['max_abs_error_V']=max(item['max_abs_error_V'],abs(error));item['final_error_V']=error
                if abs(error)>contract['diagnostic_tolerance_V']:
                    item['last_outside_tolerance_s']=t;item['remained_within_tolerance_from_native_s']=None
                elif item['remained_within_tolerance_from_native_s'] is None:
                    item['remained_within_tolerance_from_native_s']=t
    if rows!=export['rows']:raise ValueError('Native fault rows changed')
    vdd=result['voltage_and_current_extrema']['vdd!']
    if abs(vdd['max']-vdd['min'])>1e-12:raise ValueError('Constant supply energy assumption invalid')
    energy=-vdd['max']*result['current_charge_trapezoids']['vvdd:1']['signed_C']
    return dict(load_settling=dict(contract=contract,nodes=state,
        caveat='Independent Q0=1 command sets BN0->VREFP/BP0->VREFN; no expected target is inferred from observed gate/Q.1mV is diagnostic only; no pass inferred.'),
        supply_energy=dict(interval_s=[0.,result['last_native_time_s']],delivered_J=energy,
            baseline_delivered_J=cfg['experiment']['baseline_partial_supply_energy_J'],
            change_J=energy-cfg['experiment']['baseline_partial_supply_energy_J'],
            caveat='Partial0..65.9965ns ideal-VDD energy only; not full ADC/clock/input-driver power or1mW qualification.'))


def analyze(run,output):
    cfg=base.read_json(base.safe_file(run,'inputs/measurement.json'));validate_candidate(cfg)
    original_validate,original_writer,original_budget=base.validate_config,base.NativeGzip,base.Budget
    class AnnotatedBudget(original_budget):
        def json(self,name,value):
            if name=='result.json':
                value['experiment']=cfg['experiment']
                value['export_policy']=dict(full_history='Time + all17 incident currents + all6 KCL residuals;24 columns',
                    full_history_node_voltage_waveforms='Not exported here. All139 voltage extrema/initials plus fault44-voltage waveforms and original raw retained.',
                    fault='Time+44V+17 incident currents+6KCL;68 columns',
                    all277_current_statistics_integrals_and_peak_snapshots_preserved=True)
                value['additional_measurements']=load_and_power_metrics(value,cfg,output)
            return original_budget.json(self,name,value)
    try:
        base.validate_config=validate_candidate
        base.NativeGzip=writer_type(original_writer,cfg)
        base.Budget=AnnotatedBudget
        return base.analyze(run,output)
    finally:
        base.validate_config=original_validate;base.NativeGzip=original_writer;base.Budget=original_budget


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-dir',required=True);parser.add_argument('--output-dir',required=True)
    args=parser.parse_args()
    if sys.platform.startswith('linux'):
        import resource
        _,hard=resource.getrlimit(resource.RLIMIT_AS)
        limit=240*MIB if hard==resource.RLIM_INFINITY else min(240*MIB,hard)
        resource.setrlimit(resource.RLIMIT_AS,(limit,hard))
    result=analyze(args.run_dir,args.output_dir)
    print('REFERENCE_CINPUT_R1K_DIAGNOSTIC_OK',result['native_points'],'acceptance_pass=null')


if __name__=='__main__':main()
