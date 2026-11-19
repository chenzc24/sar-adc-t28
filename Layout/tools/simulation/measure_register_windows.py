"""Record D/CP setup and hold intervals, local slews and sample/preset edges from a native ADC transient."""
from __future__ import print_function

import argparse
import bisect
import json
import os

import native_stream
import reference_short


def edge_slews(crossings):
    """Associate each 50% edge with its bracketing 30% and 70% crossings of the same polarity."""
    result = []
    for t, rising in crossings[1]:
        before, after = (0, 2) if rising else (2, 0)
        first = bisect.bisect_right(crossings[before], (t, True)) - 1
        last = bisect.bisect_left(crossings[after], (t, False))
        slew = None
        if first >= 0 and last < len(crossings[after]):
            a, direction_a = crossings[before][first]
            b, direction_b = crossings[after][last]
            other = bisect.bisect_right(crossings[1], (a, True))
            if direction_a == direction_b == rising and other < len(crossings[1]) and crossings[1][other][0] == t:
                if other + 1 == len(crossings[1]) or crossings[1][other+1][0] >= b:
                    slew = (b-a)*1e12
        result.append((t, rising, slew))
    return result


def analyze(run_dir, out_dir):
    with open(os.path.join(run_dir, 'inputs/context.json')) as f:
        ctx = json.load(f)
    pins = ctx['register_receivers']
    phases = ctx['phase_observers']
    rails = {}
    for bit, pair in enumerate(pins):
        supplies = (('xdut.vss_at_bit%d' % bit, 'xdut.vdd_at_bit%d' % bit)
                    if ctx.get('supply_probe_sites') else (None, 'vdd!'))
        for signal in pair.values():
            rails[signal] = supplies
    for signal in phases.values():
        rails.setdefault(signal, (None, 'vdd!'))
    signals = sorted(rails)
    crossings = {name: [[], [], []] for name in signals}
    start_end = [None, None]
    thresholds = (.3, .5, .7)

    def observed(path):
        old = None
        for t, v in native_stream.samples(path):
            if start_end[0] is None:
                start_end[0] = t
            start_end[1] = t
            normalized = []
            for signal in signals:
                low, high = rails[signal]
                gnd = v[low] if low else 0.
                span = v[high] - gnd
                normalized.append((v[signal]-gnd)/span if span > .02 else 0.)
            if old is not None:
                for name, a, b in zip(signals, old, normalized):
                    if a == b or (max(a,b) < .3 or min(a,b) > .7):
                        continue
                    for j, level in enumerate(thresholds):
                        if (a > level) != (b > level):
                            crossings[name][j].append((pt+(level-a)*(t-pt)/(b-a), b>a))
            old, pt = normalized, t
            yield t, v

    if ctx.get('pex'):
        import measure_sar_timing
        measure_sar_timing.native_samples = observed
        result = measure_sar_timing.analyze(run_dir, out_dir)
    else:
        reference_short.samples = observed
        result = reference_short.analyze(run_dir, out_dir)
    events = {name: edge_slews(series) for name, series in crossings.items()}
    clocks = {p['cp']:[(t,s) for t,up,s in events[p['cp']] if up] for p in pins}
    times = {p['d']:[edge[0] for edge in events[p['d']]] for p in pins}
    reset_times = {p['cdn']:[edge[0] for edge in events[p['cdn']]] for p in pins if 'cdn' in p}
    for frame in result['frames']:
        origin = ctx['frame_origin_s'] + frame['frame']*ctx['period_s']
        end = origin + ctx['period_s']
        sample_fall = [e['time_s'] for e in frame['events'] if e['signal']=='sample' and not e['rising']]
        rows = []
        if len(sample_fall) == 1:
            for bit, pair in enumerate(pins):
                data = events[pair['d']]
                active = [(t,s) for t,s in clocks[pair['cp']] if sample_fall[0] <= t < end]
                for ix,(t,clock_slew) in enumerate(active):
                    pos = bisect.bisect_left(times[pair['d']],t)
                    prev = data[pos-1] if pos else (start_end[0],None,None)
                    after = data[pos] if pos<len(data) else (start_end[1],None,None)
                    row = dict(bit=bit, write=ix, clock_ns=(t-origin)*1e9, clock_slew_ps=clock_slew,
                                     setup_ps=(t-prev[0])*1e12, previous_data_rise=prev[1], setup_slew_ps=prev[2],
                                     hold_ps=(after[0]-t)*1e12, following_data_rise=after[1], hold_slew_ps=after[2])
                    if 'cdn' in pair:
                        j = bisect.bisect_right(reset_times[pair['cdn']],t)
                        reset_edge = events[pair['cdn']][j-1] if j else None
                        row['cdn_high'] = reset_edge[1] if reset_edge else None
                        row['since_cdn_edge_ps'] = (t-reset_edge[0])*1e12 if reset_edge else None
                    rows.append(row)
        frame['register_pin_windows'] = rows
        frame['phase_windows_ns'] = {name:[[(t-origin)*1e9,up] for t,up,_ in events[node] if origin<=t<end]
                                     for name,node in phases.items()}
    rows = [w for f in result['frames'] for w in f['register_pin_windows']]
    result['register_pin_measurement'] = dict(
        level='50 percent of the observed supply span', slew='30 to 70 percent of the same supply span',
        per_bit_local_rails=bool(ctx.get('supply_probe_sites')), write_observations=len(rows),
        setup_min_ps=min((w['setup_ps'] for w in rows)) if rows else None,
        hold_min_ps=min((w['hold_ps'] for w in rows)) if rows else None)
    with open(os.path.join(out_dir,'result.json'),'w') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-dir', required=True)
    ap.add_argument('--output-dir', required=True)
    ap.add_argument('--source-run-dir')
    args = ap.parse_args()
    measured = analyze(args.source_run_dir or args.run_dir, args.output_dir)
    print('Register windows', measured['register_pin_measurement'])
