"""Exact-equivalent prebound native reducer. Python2.7/3; no sampling change."""
from __future__ import print_function

import argparse
import hashlib
import json
import math
import os
import re
import struct
import sys
from stream_gzip import GzipWriter


def norm(name):
    return name.replace('\\', '').lower()


def finite(value):
    return not math.isnan(value) and not math.isinf(value)


def read(path):
    with open(path) as handle:
        return json.load(handle)


def write_new(path, data):
    if os.path.exists(path):
        raise ValueError('Preserve existing result: ' + path)
    with open(path, 'w') as handle:
        json.dump(data, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')


def summarize(path, cfg, output):
    selected = set(norm(x) for x in cfg['voltage_saves'] + cfg['current_saves'])
    current_names = set(norm(x) for x in cfg['current_saves'])
    equations = dict((norm(n), [norm(x) for x in terms]) for n, terms in cfg['kcl_terms'].items())
    critical = [norm(x) for x in cfg['critical_kcl_nodes']]
    diagnostic_currents = [norm(x) for x in cfg['diagnostic_current_columns']]
    diagnostic = [norm(x) for x in cfg['diagnostic_voltage_columns']] + diagnostic_currents
    if (any(not terms or len(terms) != len(set(terms)) or not set(terms) <= current_names
            for terms in equations.values()) or not set(critical) <= set(equations)
            or not set(diagnostic) <= selected):
        raise ValueError('Invalid current/KCL measurement catalog')
    binary_names = ['time'] + diagnostic + ['kcl:' + x for x in critical]
    window_start, window_stop = cfg['diagnostic_start_s'], cfg['diagnostic_stop_s']
    initial, stats, residuals, edges = {}, {}, {}, {}
    values, aliases, canonical, seen = {}, {}, set(), set()
    native_binding, selected_by_native = {}, {}
    section, sweep, group, property_block = None, None, None, False
    current_time, previous_time = None, None
    points, window_points, held, binary_bytes = 0, 0, 0, 0
    max_gap = 0.
    previous_edges = {}
    full_stress, source_energy, power_previous = {}, {}, {}
    for pair in cfg.get('stress_voltage_pairs', {}).values():
        for key in ('positive_node', 'negative_node'):
            if norm(pair[key]) != '0' and norm(pair[key]) not in selected:
                raise ValueError('Missing full-history stress voltage: ' + pair[key])
    for port in cfg.get('source_power_ports', {}).values():
        if norm(port['voltage_node']) not in selected or norm(port['current']) not in selected:
            raise ValueError('Missing full-history source power observation')
    # Bind immutable node spellings once and retain one statistics dict per
    # pair. Original snapshot arithmetic/comparisons and tie policy are kept.
    stress_specs = [(label, norm(pair['positive_node']), norm(pair['negative_node']),
                     pair['limit_abs_v']) for label, pair in cfg.get('stress_voltage_pairs', {}).items()]
    stress_bound = []
    power_specs = [(label, norm(port['voltage_node']), norm(port['current']))
                   for label, port in cfg.get('source_power_ports', {}).items()]
    peak_snapshot = None
    ended = False
    raw_hash = hashlib.sha256()
    native_path = os.path.join(output, 'peak.native.bin.gz')
    if os.path.exists(native_path):
        raise ValueError('Preserve existing native table')
    binary = GzipWriter(native_path,cfg['max_derived_binary_bytes'])

    def snapshot(t):
        missing = selected - set(values)
        if missing:
            raise ValueError('Uninitialized required native values: ' + ', '.join(sorted(missing)))
        row_residual = dict((node, sum(values[term] for term in terms)) for node, terms in equations.items())
        for n in selected:
            value = values[n]
            if not finite(value):
                raise ValueError('Nonfinite native value: ' + n)
            if n not in stats:
                stats[n] = dict(min=value, max=value, min_time_s=t, max_time_s=t)
            if value < stats[n]['min']:
                stats[n].update(min=value, min_time_s=t)
            if value > stats[n]['max']:
                stats[n].update(max=value, max_time_s=t)
        for node, value in row_residual.items():
            item = residuals.setdefault(node, dict(max_abs_a=0., time_s=t, diagnostic_max_abs_a=0.))
            if abs(value) > item['max_abs_a']:
                item.update(max_abs_a=abs(value), time_s=t)
            if window_start <= t <= window_stop:
                item['diagnostic_max_abs_a'] = max(item['diagnostic_max_abs_a'], abs(value))
        if not stress_bound:
            for label, positive, negative, limit in stress_specs:
                value = (0. if positive == '0' else values[positive]) - (0. if negative == '0' else values[negative])
                item = dict(min_v=value, max_v=value, min_time_s=t, max_time_s=t,
                    max_abs_v=abs(value), max_abs_time_s=t, native_points=0,
                    over_limit_native_points=0, first_over_limit_s=None,
                    last_over_limit_s=None, limit_abs_v=limit)
                full_stress[label] = item
                stress_bound.append((positive, negative, limit, item))
        for positive, negative, limit, item in stress_bound:
            value = (0. if positive == '0' else values[positive]) - (0. if negative == '0' else values[negative])
            item['native_points'] += 1
            if value < item['min_v']: item.update(min_v=value, min_time_s=t)
            if value > item['max_v']: item.update(max_v=value, max_time_s=t)
            if abs(value) > item['max_abs_v']: item.update(max_abs_v=abs(value), max_abs_time_s=t)
            if abs(value) > limit:
                item['over_limit_native_points'] += 1
                if item['first_over_limit_s'] is None: item['first_over_limit_s'] = t
                item['last_over_limit_s'] = t
        for label, voltage_node, current_node in power_specs:
            power = -values[voltage_node] * values[current_node]
            item = source_energy.setdefault(label, dict(net_delivered_j=0., min_power_w=power,
                max_power_w=power, min_power_time_s=t, max_power_time_s=t,
                first_time_s=t, last_time_s=t, native_points=0))
            previous = power_previous.get(label)
            if previous is not None:
                item['net_delivered_j'] += .5 * (previous[1] + power) * (t - previous[0])
            if power < item['min_power_w']: item.update(min_power_w=power, min_power_time_s=t)
            if power > item['max_power_w']: item.update(max_power_w=power, max_power_time_s=t)
            item['native_points'] += 1; item['last_time_s'] = t
            power_previous[label] = (t, power)
        for node, expected in cfg['expected_edges'].items():
            x = values[node] - .5 * values['vdd!']
            old = previous_edges.get(node)
            if old is not None:
                qualifies = old[1] < 0 <= x if expected['direction'] == 1 else old[1] > 0 >= x
                if qualifies:
                    at = old[0] - old[1] * (t - old[0]) / (x - old[1])
                    edges.setdefault(node, []).append(at)
            previous_edges[node] = (t, x)
        return row_residual

    try:
        with open(path, 'rb') as source:
            for raw in source:
                raw_hash.update(raw)
                line = raw.decode('ascii').strip()
                if line in ('HEADER', 'TYPE', 'SWEEP', 'TRACE', 'VALUE', 'END'):
                    section = line
                    if line == 'VALUE':
                        if sweep != 'time' or not selected <= canonical:
                            raise ValueError('Required native TRACE/time sweep missing: ' + ', '.join(sorted(selected - canonical)))
                        selected_by_native = {}
                        for name in selected:
                            selected_by_native.setdefault(native_binding[name], []).append(name)
                    if line != 'END':
                        continue
                    ended = True
                    marker = True
                else:
                    if not line or section not in ('SWEEP', 'TRACE', 'VALUE'):
                        continue
                    if section == 'TRACE' and property_block:
                        if line == ')':
                            property_block = False
                        continue
                    if not line.startswith('"'):
                        continue
                    _, key, tail = line.split('"', 2)
                    tail = tail.strip()
                    if section == 'SWEEP':
                        if sweep is None:
                            sweep = key
                        continue
                    if section == 'TRACE':
                        property_block = 'PROP(' in tail and ')' not in tail[tail.index('PROP('):]
                        if tail.startswith('GROUP'):
                            if tail != 'GROUP 1':
                                raise ValueError('Unsupported native GROUP')
                            group = key
                            continue
                        name = norm(key)
                        if name in canonical:
                            raise ValueError('Duplicate canonical TRACE: ' + name)
                        canonical.add(name); aliases[key] = name; native_binding[name] = name
                        if group is not None:
                            if norm(group) != name and norm(group) in canonical:
                                raise ValueError('Duplicate GROUP alias')
                            aliases[group] = name
                            canonical.add(norm(group)); native_binding[norm(group)] = name; group = None
                        continue
                    if section == 'VALUE' and key != sweep and key in aliases and not selected_by_native.get(aliases[key]):
                        continue  # extra named OP values are handled by field_capture, not baseline arithmetic
                    value = float(tail)
                    if not finite(value):
                        raise ValueError('Invalid native scalar')
                    marker = key == sweep
                    if not marker:
                        name = aliases.get(key)
                        if name is None:
                            raise ValueError('Unknown native value key: ' + key)
                        for selected_name in selected_by_native.get(name, []):
                            if selected_name in seen:
                                raise ValueError('Duplicate selected update at native point')
                            values[selected_name] = value; seen.add(selected_name)
                        continue
                if current_time is not None:
                    if previous_time is not None and current_time <= previous_time:
                        raise ValueError('Non-increasing native points')
                    if previous_time is not None:
                        max_gap = max(max_gap, current_time - previous_time)
                    row_residual = snapshot(current_time)
                    if not points:
                        if current_time != 0:
                            raise ValueError('Native history must start at zero')
                        initial = dict(values)
                    held += len(selected - seen)
                    points += 1
                    if window_start <= current_time <= window_stop:
                        row = [current_time] + [values[n] for n in diagnostic] + [row_residual[n] for n in critical]
                        blob = struct.pack('<' + 'd' * len(row), *row)
                        binary.write(blob); binary_bytes += len(blob); window_points += 1
                        node = norm(cfg['expected_native_peak']['node'])
                        if peak_snapshot is None or values[node] > peak_snapshot['voltage_v']:
                            peak_snapshot = dict(time_s=current_time, voltage_v=values[node],
                                selected_currents_a=dict((n, values[n]) for n in diagnostic_currents),
                                critical_kcl_a=dict((n, row_residual[n]) for n in critical))
                    previous_time = current_time
                if ended:
                    break
                if current_time is not None and value <= current_time:
                    raise ValueError('Non-increasing native time marker')
                current_time = value; seen = set()
        if (not ended or not points or not window_points
                or abs(current_time - cfg['source_history_stop_s']) > 1e-15):
            raise ValueError('Incomplete native simulation/diagnostic window')
    finally:
        binary.close()
    expected_initial = cfg['expected_initial_state']['values_v']
    initial_errors = dict((norm(name), initial[norm(name)] - v) for name, v in expected_initial.items())
    expected_peak = cfg['expected_native_peak']
    result = dict(analysis_complete=True, streaming_export=binary.proof(), scope=cfg['scope'], native_points=points,
        diagnostic_points=window_points, native_PSF_END=True, raw_sha256=raw_hash.hexdigest(),
        raw_bytes=os.path.getsize(path), held_values_from_sparse_updates=held,
        max_native_gap_s=max_gap, trace_bindings=dict((n, native_binding[n]) for n in selected),
        initial_values=initial, initial_witness_error_v=initial_errors,
        max_initial_witness_error_v=max(abs(v) for v in initial_errors.values()),
        voltage_and_current_extrema=stats, node_kcl=residuals, native_edges_s=edges,
        peak_snapshot=peak_snapshot,
        peak_error_v=peak_snapshot['voltage_v'] - expected_peak['value_v'],
        peak_time_error_s=peak_snapshot['time_s'] - expected_peak['time_s'],
        proposed_contract=cfg['proposed_reproduction_contract'], acceptance_pass=None,
        missing_required_signals=[], circuit_repair_claim=False,
        full_history_voltage_stress=full_stress, full_history_source_energy=source_energy,
        full_history_observation=dict(start_s=0., stop_s=current_time, native_points=points,
            voltage_pairs='Simultaneous native values at every parsed point, not extrema subtraction',
            energy='Trapezoid of delivered -V*I at original native points; current enters source positive terminal',
            scope='Local fixture sources including ideal bias work; no whole-ADC power qualification'),
        current_interpretation='Total native terminal currents, positive from node into device. No channel/overlap/junction split inferred.')
    write_new(os.path.join(output, 'peak.columns.json'), dict(names=binary_names,
        units=['s'] + ['V'] * len(cfg['diagnostic_voltage_columns']) + ['A'] * (len(cfg['diagnostic_current_columns']) + len(critical)),
        KCL_fields='Derived signed sums at existing native timestamps; no interpolation of waveform points'))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-dir', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    run, output = os.path.realpath(args.run_dir), os.path.realpath(args.output_dir)
    if output != os.path.join(run, 'derived') or os.path.exists(os.path.join(output, 'result.json')):
        raise ValueError('Expected fresh managed derived directory')
    state = read(os.path.join(run, 'simulation.state.json'))
    if (state['status'] != 'complete' or state['exit_code'] != 0
            or not state.get('native', {}).get('native_analysis_pass')
            or not state.get('native', {}).get('zero_error_footer')):
        raise ValueError('Native fixture simulation not complete')
    with open(os.path.join(run, 'raw', 'logStatus')) as handle:
        if not re.search(r'tran_first\s+PASS', handle.read()):
            raise ValueError('Native transient PASS missing')
    native = [os.path.join(run, 'raw', f) for f in os.listdir(os.path.join(run, 'raw')) if f.endswith('.tran.tran')]
    if len(native) != 1:
        raise ValueError('Expected one native ASCII transient')
    cfg_path = os.path.join(run, 'inputs', 'measurement.json')
    result = summarize(native[0], read(cfg_path), output)
    with open(cfg_path, 'rb') as handle:
        result['measurement_sha256'] = hashlib.sha256(handle.read()).hexdigest()
    codes = state.get('native', {}).get('warning_codes')
    result['native_warning_codes'] = codes
    result['CMI_warning_present'] = (any(code.startswith('CMI') for code in codes)
                                     if codes is not None else None)
    result['native_effective_settings'] = state.get('native', {}).get('effective_settings')
    if sys.platform.startswith('linux'):
        import resource
        result['analysis_peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        if result['analysis_peak_rss_bytes'] > 256 * 1024**2:
            raise ValueError('Analysis RSS exceeds 256 MiB cap')
    else:
        result['analysis_peak_rss_bytes'] = None
    if sum(os.path.getsize(os.path.join(output, f)) for f in os.listdir(output)) + 1024 * 1024 >= 32 * 1024**2:
        raise ValueError('Derived output cap exceeded')
    write_new(os.path.join(output, 'result.json'), result)
    print('CONTROL_FIRST_EVENT_CURRENT_KCL_OK', result['native_points'], 'acceptance remains unapproved')


if __name__ == '__main__':
    main()
