"""QB NAND gate-order observer with unchanged storage/native helpers. Py2.7/3."""
from __future__ import print_function
import argparse
import os
import re
import sys

import standard_cell_qbcap_analyze as source

rb,live,series,standard,native=source.rb,source.live,source.series,source.standard,source.native


def coverage(reset,cfg):
    return dict(
        set_input_rises=reset['nodes']['CLOCK_SET']['rising_halfrail_s'],
        Q_rises=reset['nodes']['CLOCK_Q']['rising_halfrail_s'],Q_falls=reset['nodes']['CLOCK_Q']['falling_halfrail_s'],
        reset_input_rises=reset['nodes']['CLOCK_RESET']['rising_halfrail_s'],
        full_set_operation_qualified=False,full_reset_from_Qhigh_qualified=False,
        missing_acceptance=cfg['standard_cell_qborder_experiment']['acceptance_gaps'],
        scope='First-event observations only. Any edge is retained, not automatically a valid SR transition or complete both-direction test.')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-dir',required=True);parser.add_argument('--output-dir',required=True)
    args=parser.parse_args();run,output=os.path.realpath(args.run_dir),os.path.realpath(args.output_dir)
    if output!=os.path.join(run,'derived') or os.path.exists(os.path.join(output,'result.json')):
        raise ValueError('Expected fresh managed derived directory')
    library_identity=standard.verify_library(os.path.join(run,'inputs','external_library.json'))
    state=native.read(os.path.join(run,'simulation.state.json'))
    if (state['status']!='complete' or state['exit_code']!=0 or not state.get('native',{}).get('native_analysis_pass')
            or not state.get('native',{}).get('zero_error_footer')):
        raise ValueError('Native simulation incomplete')
    with open(os.path.join(run,'raw','logStatus')) as handle:
        if not re.search(r'tran_first\s+PASS',handle.read()):
            raise ValueError('Native PASS missing')
    paths=[os.path.join(run,'raw',s) for s in os.listdir(os.path.join(run,'raw')) if s.endswith('.tran.tran')]
    if len(paths)!=1:
        raise ValueError('Expected one native ASCII transient')
    cfg_path=os.path.join(run,'inputs','measurement.json');cfg=native.read(cfg_path)
    result=native.summarize(paths[0],cfg,output)
    result['measurement_sha256']=standard.file_identity(cfg_path)['sha256'];result['external_library_identity']=library_identity
    result['diagnostic_timing']=standard.diagnostic_timing(output,cfg)
    result['series_resistor_metrics']=series.resistor_measurements(output,cfg)
    result['LIVE_stage_input_loading']=live.load_observations(output,cfg)
    result['reset_stage_observations']=rb.reset_observations(output,cfg)
    result['CLOCK_RESET_NAND_input_loading']=source.source.nand_input_loading(output,cfg)
    result['QB_storage_observations']=source.storage_observations(output,cfg,result['reset_stage_observations'])
    result['gate_order_coverage']=coverage(result['reset_stage_observations'],cfg)
    result['gate_order_native_gate_bindings']=dict((label,dict((role,dict(
        requested=p,actual=result['trace_bindings'][native.norm(p)],
        actual_node=cfg['terminal_current_catalog'][p]['node'])) for role,p in
        cfg['standard_cell_rb_experiment']['load_observers'][label]['ports'].items())) for label in ['RB','CLOCK_Q'])
    result['reset_receiver_initial_native_voltages_v']=dict(
        (label,result['initial_values'][native.norm(item['node'])])
        for label,item in cfg['standard_cell_rb_experiment']['load_observers'].items())
    library=cfg['standard_cell_experiment']['library_mos']
    if len(library)!=18:
        raise ValueError('Expected eighteen actual native library MOS')
    result['standard_cell_native_current_bindings']=dict((name,dict(requested=item['requested_numeric_terminal_currents'],
        actual=dict((p,result['trace_bindings'][native.norm(p)]) for p in item['requested_numeric_terminal_currents']),
        nested_primitive_not_assumed=True)) for name,item in library.items())
    result['resistor_native_current_bindings']=dict((p,result['trace_bindings'][native.norm(p)])
        for p in cfg['standard_cell_r0_experiment']['resistor_current_ports'])
    live.separate_energy(result,cfg)
    groups={};stress=result['full_history_voltage_stress']
    for name,item in cfg['standard_cell_experiment']['observed_mos'].items():
        g=groups.setdefault(item['group'],dict(MOS=0,pairs=0,failed_pairs=0,failed_instances=[]))
        g['MOS']+=1;g['pairs']+=len(item['six_pair_labels'])
        failed=sum(stress[s]['over_limit_native_points']>0 for s in item['six_pair_labels'].values());g['failed_pairs']+=failed
        if failed:
            g['failed_instances'].append(name)
    result['physical_terminal_screen_groups']=groups
    exp=cfg['standard_cell_qborder_experiment']
    result['comparison_source']=dict(run_id=exp['base_run'],recipe_sha256=exp['base_recipe_sha256'])
    codes=state['native'].get('warning_codes');result['native_warning_codes']=codes
    result['CMI_warning_present']=any(s.startswith('CMI') for s in codes) if codes is not None else None
    result['native_effective_settings']=state['native'].get('effective_settings');result['analysis_peak_rss_bytes']=None
    if sys.platform.startswith('linux'):
        import resource
        result['analysis_peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        if result['analysis_peak_rss_bytes']>256*1024**2:
            raise ValueError('Analysis RSS exceeds256 MiB')
    if sum(os.path.getsize(os.path.join(output,s)) for s in os.listdir(output))+1024*1024>=32*1024**2:
        raise ValueError('Derived output cap exceeded')
    native.write_new(os.path.join(output,'result.json'),result)
    print('CONTROL_QB_GATE_ORDER_NATIVE_ANALYSIS_OK',result['native_points'],'full SR set/reset unqualified')


if __name__=='__main__':
    main()
