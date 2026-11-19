"""Native single-edge receiver measurements, compatible with the simulation host."""
from __future__ import print_function
import argparse
import json
import math
import os

import reference_short as native
import mc_short_reduce as mc
import single_edge_audit as audit


def analyze(root, out):
    with open(os.path.join(root, 'inputs/context.json')) as f:
        ctx = json.load(f)
    pins = [n for n in ctx['required_signals'] if n.endswith('.din')]
    clock = 'xdut.phi_u'
    watch = pins + [clock, 'xdut.seq_sample', 'xdut.cmp_clk', 'xdut.preset']
    events = dict((k, []) for k in watch)
    def read(path):
        previous = None
        for t, v in native.samples(path):
            cur = dict((k, v[k] - v['vdd!'] / 2) for k in watch)
            if previous is not None:
                pt, old = previous
                for k in watch:
                    a, b = old[k], cur[k]
                    if (a > 0) != (b > 0):
                        events[k].append((pt - a * (t - pt) / (b - a), b > 0))
            previous = t, cur
            yield t, v
    result = native.analyze(root, out, frame_finisher=mc.finish if ctx['mismatch'] else None,
                            sample_reader=read)
    setup, hold, widths, cmp_low = [], [], [], []
    for frame in result['frames']:
        origin = ctx['frame_origin_s'] + frame['frame'] * ctx['period_s']
        end = origin + ctx['period_s']
        edge = [t for t, up in events[clock] if origin <= t < end and up]
        for t in edge:
            fall = next((f for f, up in events[clock] if f > t and not up), None)
            if fall is not None:
                widths.append((fall-t)*1e12)
            for pin in pins:
                before = [x for x, _ in events[pin] if x <= t]
                after = [x for x, _ in events[pin] if x >= t]
                if before:
                    setup.append((t-before[-1])*1e12)
                if after:
                    hold.append((after[0]-t)*1e12)
        cmp_edges = [(t, up) for t, up in events['xdut.cmp_clk'] if origin <= t < end]
        cmp_low.extend((b-a)*1e12 for (a,rise),(b,again) in zip(cmp_edges, cmp_edges[1:])
                       if not rise and again)
        starts = [t for t, up in cmp_edges if up]
        track_off = [t for t, up in events['xdut.seq_sample'] if origin <= t < end and not up]
        preset = [t for t, up in events['xdut.preset'] if origin <= t < end and up]
        frame['frame_control_pass'] = (len(edge) == len(starts) == 8 and len(track_off) == 1
            and starts[0] > track_off[0] and any(t > edge[-1] for t in preset)
            and not any(starts[0] < t < edge[-1] for t in preset))
        frame['margin_to_90_ns'] = 90 - (edge[-1]-origin)*1e9 if edge else None
    result['pin_minimum_ps'] = dict((name, min(values) if values else None) for name, values in
        [('setup_window', setup), ('hold_window', hold), ('write_high', widths), ('cmp_low', cmp_low)])
    result['frame_control_pass'] = all(f['frame_control_pass'] for f in result['frames'])
    result['settling_pass'] = all(f['sample_close_error_lsb'] is not None
        and abs(f['sample_close_error_lsb']) <= .25 and all(b['bottom_screen_pass'] for b in f['bits'])
        for f in result['frames'])
    result['all_screens_pass'] = result['pass_function_timing'] and result['frame_control_pass'] and result['settling_pass']
    result['limitations'] = ['Front-end schematic; receiver windows are 50-percent crossing intervals.']
    if ctx['mismatch']:
        result['mc_settling_screen_pass'] = all(not f['settling_review'] for f in result['frames'])
        labels = mc.findone(root+'/raw', 'mismatch.params')
        values = mc.findone(root+'/raw', 'mismatch.values')
        groups = ['XCTRL.XTIM.XWINDOW', 'XCTRL.XBIT0', 'XCTRL.XDONE', 'XCOMP', 'XCDAC']
        counts = dict.fromkeys(groups, 0)
        with open(labels) as names, open(values) as data:
            columns = next(names).split()
            if next(data).strip() != '#1':
                raise ValueError('Missing single draw')
            for line in names:
                name = line.strip().upper()
                if not name:
                    continue
                row = list(map(float, next(data).split()))
                if len(row) != len(columns) or any(math.isnan(v) or math.isinf(v) for v in row):
                    raise ValueError('Invalid mismatch draw')
                for group in groups:
                    if name.startswith('XDUT.' + group + '.') and any(row):
                        counts[group] += 1
            if any(line.strip() for line in data):
                raise ValueError('Unexpected extra mismatch rows')
        result['local_draw'] = dict(sha256=mc.digest(values), labels_sha256=mc.digest(labels),
                                    nonzero_device_rows=counts)
        result['all_screens_pass'] = (result['all_screens_pass'] and all(counts.values())
                                      and result['mc_settling_screen_pass'])
    checked = audit.analyze(root,out,os.path.join(root,'inputs/dff.json'))
    for f, measured in zip(result['frames'], checked['frames']):
        for key in ('digital_pass', 'decision_word', 'public_margin_ns', 'preset_ready_lead_ns'):
            f[key] = measured[key]
    result['ccs'] = checked['ccs']
    result['digital_pass'] = all(f['digital_pass'] and f['public_margin_ns'] > 0 for f in result['frames'])
    counts = result['ccs']['observation_counts']
    result['pin_screen_pass'] = (counts.get('writes') == len(pins)*8*ctx['frames']
        and not counts.get('inactive_or_unknown_cdn') and bool(widths)
        and min(widths) >= ctx['min_cp_high_ps']
        and all(result['ccs']['minimum_slack'].get(k,{}).get('slack_ps',-1)>=0 for k in ('setup','hold')))
    result['all_screens_pass'] = result['all_screens_pass'] and result['pin_screen_pass'] and result['digital_pass']
    with open(os.path.join(out, 'result.json'), 'w') as f:
        json.dump(result, f, indent=2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-dir', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    analyze(args.run_dir, args.output_dir)
