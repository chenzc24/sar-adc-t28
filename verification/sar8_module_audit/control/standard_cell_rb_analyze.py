"""RB reset-INVD1 observer, reusing frozen native reducers. Python2.7/3."""
from __future__ import print_function
import argparse
import os
import re
import struct
import sys

import standard_cell_live_analyze as live

series, standard, native = live.series, live.standard, live.native
P = 'xdut.xctrl.xtim.'


def excursion_widths(output, cfg):
    names = native.read(os.path.join(output,'peak.columns.json'))['names']
    exp = cfg['standard_cell_rb_experiment']
    columns = dict((label,names.index(native.norm(node))) for label,node in exp['width_nodes'].items())
    bands = dict(below_0_v=(-1.,0.), below_minus_1mV=(-1.,.001),
                 above_0p99_v=(1.,.99), above_0p991_v=(1.,.991))
    results = dict((label,dict((band,dict(cumulative_s=0.,episodes=[],over_limit_native_points=0))
                   for band in bands)) for label in columns)
    opened = {}; previous = None; first = None; count = 0
    parser = struct.Struct('<'+'d'*len(names))
    with open(os.path.join(output,'peak.native.bin'),'rb') as handle:
        while True:
            blob = handle.read(parser.size)
            if not blob:
                break
            if len(blob) != parser.size:
                raise ValueError('Incomplete native reset width row')
            row = parser.unpack(blob); count += 1
            if first is None:
                first = row[0]
            for label,index in columns.items():
                for band,(coefficient,limit) in bands.items():
                    key = (label,band); item = results[label][band]
                    z = coefficient*row[index]-limit
                    item['over_limit_native_points'] += int(z>0)
                    if previous is None:
                        if z>0:
                            opened[key] = dict(start_s=row[0],open_at_window_start=True)
                        continue
                    a = coefficient*previous[index]-limit
                    dt = row[0]-previous[0]
                    if a<=0<z:
                        crossing = previous[0]-a*dt/(z-a)
                        opened[key] = dict(start_s=crossing,open_at_window_start=False)
                    elif a>0>=z:
                        crossing = previous[0]-a*dt/(z-a)
                        event = opened.pop(key)
                        event.update(stop_s=crossing,width_s=crossing-event['start_s'],open_at_window_stop=False)
                        item['episodes'].append(event); item['cumulative_s'] += event['width_s']
            previous = row
    if count<2:
        raise ValueError('Missing native reset width history')
    for (label,band),event in opened.items():
        event.update(stop_s=previous[0],width_s=previous[0]-event['start_s'],open_at_window_stop=True)
        results[label][band]['episodes'].append(event)
        results[label][band]['cumulative_s'] += event['width_s']
    return dict(nodes=results,first_native_s=first,last_native_s=previous[0],native_points=count,
                scope=exp['width_policy'])


def reset_observations(output, cfg):
    exp = cfg['standard_cell_rb_experiment']; observations = {}
    for label,item in exp['load_observers'].items():
        adapter = dict(standard_cell_r0_mn2_experiment=dict(input_loading_node=item['node'],
            input_gate_current_ports=item['ports'],affected_input_KCL_terms=cfg['kcl_terms'][item['node']],
            event_charge_start_s=exp['event_charge_start_s']))
        observations[label] = live.loading.input_loading(output,adapter)
        observations[label]['role'] = item['role']
        observations[label]['gate_loading_measured'] = bool(item['ports'])
        if not item['ports']:
            observations[label]['diagnostic_window_extrema'].pop('total_gate')
            for key in ['into_gate_devices_c','total_into_gate_devices_c',
                        'into_gate_terminal_work_j','total_into_gate_terminal_work_j']:
                observations[label]['event_exchange'][key] = None
    R,RB = observations['CLOCK_RESET'],observations['RB']
    def delays(causes,effects):
        # Halfrail propagation may be negative for unequal edge shapes. Keep
        # signed delay; unequal event counts stay unpaired rather than guessed.
        if len(causes)!=len(effects):
            return None
        return [dict(cause_s=at,effect_s=effect,delay_s=effect-at)
                for at,effect in zip(causes,effects)]
    return dict(nodes=observations,excursion_widths=excursion_widths(output,cfg),
        reset_release_R_fall_to_RB_rise=delays(R['falling_halfrail_s'],RB['rising_halfrail_s']),
        reset_assert_R_rise_to_RB_fall=delays(R['rising_halfrail_s'],RB['falling_halfrail_s']),
        scope='Actual native first-event window. Ordered halfrail pairs retain signed delay; unequal counts are unpaired. Empty edge lists are unobserved, never zero delay or full reset qualification. Voltage-only SR receivers have unavailable gate charge/work, not zero physical load.')


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--run-dir',required=True); parser.add_argument('--output-dir',required=True)
    args = parser.parse_args(); run,output = os.path.realpath(args.run_dir),os.path.realpath(args.output_dir)
    if output != os.path.join(run,'derived') or os.path.exists(os.path.join(output,'result.json')):
        raise ValueError('Expected fresh managed derived directory')
    library_identity = standard.verify_library(os.path.join(run,'inputs','external_library.json'))
    state = native.read(os.path.join(run,'simulation.state.json'))
    if (state['status']!='complete' or state['exit_code']!=0 or not state.get('native',{}).get('native_analysis_pass')
            or not state.get('native',{}).get('zero_error_footer')):
        raise ValueError('Native simulation incomplete')
    with open(os.path.join(run,'raw','logStatus')) as handle:
        if not re.search(r'tran_first\s+PASS',handle.read()):
            raise ValueError('Native PASS missing')
    paths = [os.path.join(run,'raw',s) for s in os.listdir(os.path.join(run,'raw')) if s.endswith('.tran.tran')]
    if len(paths)!=1:
        raise ValueError('Expected one native ASCII transient')
    cfg_path = os.path.join(run,'inputs','measurement.json'); cfg = native.read(cfg_path)
    result = native.summarize(paths[0],cfg,output)
    result['measurement_sha256'] = standard.file_identity(cfg_path)['sha256']
    result['external_library_identity'] = library_identity
    result['diagnostic_timing'] = standard.diagnostic_timing(output,cfg)
    result['series_resistor_metrics'] = series.resistor_measurements(output,cfg)
    result['LIVE_stage_input_loading'] = live.load_observations(output,cfg)
    result['reset_stage_observations'] = reset_observations(output,cfg)
    initial = result['initial_values']
    result['reset_receiver_initial_native_voltages_v'] = dict(
        (label,initial[native.norm(item['node'])])
        for label,item in cfg['standard_cell_rb_experiment']['load_observers'].items())
    library = cfg['standard_cell_experiment']['library_mos']
    if len(library)!=14:
        raise ValueError('Expected fourteen actual native library MOS')
    result['standard_cell_native_current_bindings'] = dict((name,dict(
        requested=item['requested_numeric_terminal_currents'],
        actual=dict((p,result['trace_bindings'][native.norm(p)]) for p in item['requested_numeric_terminal_currents']),
        nested_primitive_not_assumed=True)) for name,item in library.items())
    result['resistor_native_current_bindings'] = dict((p,result['trace_bindings'][native.norm(p)])
        for p in cfg['standard_cell_r0_experiment']['resistor_current_ports'])
    live.separate_energy(result,cfg)
    groups = {}; stress = result['full_history_voltage_stress']
    for name,item in cfg['standard_cell_experiment']['observed_mos'].items():
        g = groups.setdefault(item['group'],dict(MOS=0,pairs=0,failed_pairs=0,failed_instances=[]))
        g['MOS'] += 1; g['pairs'] += len(item['six_pair_labels'])
        failed = sum(stress[s]['over_limit_native_points']>0 for s in item['six_pair_labels'].values())
        g['failed_pairs'] += failed
        if failed:
            g['failed_instances'].append(name)
    result['physical_terminal_screen_groups'] = groups
    exp = cfg['standard_cell_rb_experiment']
    result['comparison_source'] = dict(run_id=exp['base_run'],recipe_sha256=exp['base_recipe_sha256'])
    codes = state['native'].get('warning_codes'); result['native_warning_codes'] = codes
    result['CMI_warning_present'] = any(s.startswith('CMI') for s in codes) if codes is not None else None
    result['native_effective_settings'] = state['native'].get('effective_settings')
    result['analysis_peak_rss_bytes'] = None
    if sys.platform.startswith('linux'):
        import resource
        result['analysis_peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        if result['analysis_peak_rss_bytes']>256*1024**2:
            raise ValueError('Analysis RSS exceeds256 MiB')
    if sum(os.path.getsize(os.path.join(output,s)) for s in os.listdir(output))+1024*1024>=32*1024**2:
        raise ValueError('Derived output cap exceeded')
    native.write_new(os.path.join(output,'result.json'),result)
    print('CONTROL_RB_STANDARD_CELL_NATIVE_ANALYSIS_OK',result['native_points'],'no reset or integrated acceptance')


if __name__ == '__main__':
    main()
