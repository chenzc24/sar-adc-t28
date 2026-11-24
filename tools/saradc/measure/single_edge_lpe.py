"""Score the per-bit tap SAR on native waveforms: ordered events, registered tap handoffs,
signed settling against the nominal reference, first-compare isolation and register pins.
Compatible with the simulation host Python 2.7."""
from __future__ import print_function, division
import argparse
import json
import math
import os
import re

import native_stream
from reference_short import gate_pair


def samples(path, ctx):
    """Waveform samples; post-layout decks save macro nets that context signal_aliases maps to schematic names."""
    alias = ctx.get('signal_aliases', {})
    for t, v in native_stream.samples(path):
        yield t, dict((alias.get(k, k), x) for k, x in v.items()) if alias else v


def bottom_state(v, groups, lsb):
    words, total, maximum = [], 0., 0.
    for side in ('n', 'p'):
        gates = 0
        for bit, ports in enumerate(groups[side]):
            gn, gp = [gate > .5*v['vdd!'] for gate in gate_pair(v, side, bit)]
            if gn != gp:
                return None
            gates |= int(gn) << bit
            target = v['vrefn' if gn else 'vrefp']
            errors = [abs(v[port] - target) for port in ports]
            if any(math.isinf(x) or math.isnan(x) for x in errors):
                raise ValueError('Nonfinite physical capacitor voltage')
            total += sum(errors)
            maximum = max(maximum, max(errors))
        words.append(gates)
    if sum(words) != 255:
        return None
    # The shared audit reads max_bottom_error_v for mismatch runs; here it is the worst single terminal.
    return dict(gate_words=words, weighted_bound_lsb=total/(256*lsb), max_port_error_v=maximum,
                max_bottom_error_v=maximum)


def signed_settling(v, groups, weights, lsb, rails):
    """Signed TOPP-TOPN error from all 510 plates against the nominal (not instantaneous) rails.

    Each group contributes its standalone differential weight per volt of (P - N) deviation, so a
    drooping reference pin appears here; the 24/24 reference check matched it within 0.031 LSB."""
    span = 2.*(rails[1] - rails[0])
    total = 0.
    for bit in range(8):
        diff = 0.
        for side, sign in (('p', 1.), ('n', -1.)):
            ports = groups[side][bit]
            mean = sum(v[p] for p in ports)/len(ports)
            low = gate_pair(v, side, bit)[0] > .5*v['vdd!']
            diff += sign*(mean - (rails[0] if low else rails[1]))
        total += weights[bit]/span*diff
    return total/lsb


def word(v, prefix):
    return sum(1 << b for b in range(8) if v[prefix+str(b)] > .5*v['vdd!'])


def selector_handoffs(frame, sels):
    """Each select must rise once, after its commit and before the next compare, while both
    inputs of its multiplexer sit at the same rail across the whole 10-90% select transition."""
    bits, writes = frame['bits'], frame['writes']
    rows = []
    if not (len(bits) == len(writes) == 8 and len(frame['track']) == 2):
        return dict(passed=False, selectors=rows)
    close = frame['track'][1]['ns']
    edges, levels = frame['selector_edges'], frame['selector_levels']
    for s in sels:
        name, j = s['name'], s['commit_index']
        row = dict(name=name, passed=False)
        rows.append(row)
        q = dict((lvl, [(t, up) for t, up in edges[name+'@'+lvl] if close < t <= 98.]) for lvl in ('10', '50', '90'))
        row['q_crossings'] = dict((k, len(x)) for k, x in q.items())
        if any(len(x) != 1 or not x[0][1] for x in q.values()):
            continue
        q10, q50, q90 = q['10'][0][0], q['50'][0][0], q['90'][0][0]
        moves = sorted(t for net in s['inputs'] for t, _ in edges[net+'@10'] + edges[net+'@90'])
        before = [t for t in moves if t <= q10]
        inside = [t for t in moves if q10 < t <= q90]
        after = [t for t in moves if t > q90]
        lv = levels.get(name, {})
        same = all(len(lv.get(k, [])) == 2 and (min(lv[k]) > .9 or max(lv[k]) < .1) for k in ('q10', 'q90'))
        row.update(commit_ns=writes[j]['ns'], q50_ns=q50, select_delay_ps=(q50-writes[j]['ns'])*1e3,
                   inputs_settled_before_q10_ps=(q10-before[-1])*1e3 if before else None,
                   inputs_stable_after_q90_ps=(after[0]-q90)*1e3 if after else None, input_levels=lv,
                   order=writes[j]['ns'] < q10 <= q50 <= q90 < bits[j+1]['cmp_ns'], moves_during_select=len(inside),
                   same_level=same,
                   selected_by_compare=all(b['selects'].get(name) == (i > j) for i, b in enumerate(bits)),
                   trial_at_commit=all(w['trials'].get(name) == (i == j) for i, w in enumerate(writes)))
        row['passed'] = bool(row['order'] and not inside and same and row['selected_by_compare']
                             and row['trial_at_commit'])
    return dict(passed=len(rows) == len(sels) and all(r['passed'] for r in rows), selectors=rows)


def widths(events, up_first):
    """Durations of the high (up_first=True) or low pulses in a list of (time, rising) edges."""
    out = []
    for (t0, r0), (t1, r1) in zip(events, events[1:]):
        if r0 == up_first and r1 != up_first:
            out.append((t1-t0)*1e12)
    return out


def analyze(root, out):
    with open(root+'/inputs/context.json') as stream:
        ctx = json.load(stream)
    raw = [os.path.join(p, n) for p, _, files in os.walk(root+'/raw') for n in files if n.endswith('.tran.tran')]
    if len(raw) != 1:
        raise ValueError('Expected one native transient')
    origin, period, lsb = ctx['frame_origin_s'], ctx['period_s'], ctx['lsb_v']
    groups, weights, rails = ctx['cdac_plate_nodes'], ctx['cdac_weights_v'], ctx['reference_v']
    sels = ctx['selectors']
    limit, target = ctx['settling_limit_lsb'], ctx['settling_target_lsb']
    for side in ('n', 'p'):
        if [len(g) for g in groups[side]] != [1 << i for i in range(8)]:
            raise ValueError('Unexpected number of physical terminals per bit')
    frames = [dict(frame=i, input_code=c, bits=[], writes=[], track=[], preset=[], public=[], track_overlaps=[],
                   code90=None, code98=None, selector_edges={}, selector_levels={})
              for i, c in enumerate(ctx['expected_codes'])]
    tim = 'xdut.xctrl.xtim.'
    cmpnet, wr, track = 'xdut.cmp_clk', 'xdut.phi_u', 'xdut.seq_sample'
    launch, delivery, setnet, clrnet = [tim+s for s in ('phase_request', 'delivered', 'set', 'clr_n')]
    bus = ['d%d' % i for i in range(8)]
    watch = [cmpnet, wr, track, launch, delivery, setnet, clrnet, 'xdut.preset'] + bus
    thresholds = []
    for s in sels:
        thresholds += [(s['name']+'@'+str(int(lvl*100)), s['q'], lvl, s) for lvl in (.1, .5, .9)]
    for net in sorted(set(n for s in sels for n in s['inputs'])):
        thresholds += [(net+'@10', net, .1, None), (net+'@90', net, .9, None)]
    for f in frames:
        f['selector_edges'] = dict((key, []) for key, _, _, _ in thresholds)
    phases = {launch: [], delivery: []}
    pulses = {setnet: [], clrnet: [], cmpnet: [], wr: []}
    prev = None
    points = 0
    for t, v in samples(raw[0], ctx):
        points += 1
        if prev is None:
            missing = set(ctx['required_signals']) - set(v)
            if missing:
                raise ValueError('Missing physical probe(s): '+repr(sorted(missing)[:10]))
            prev = t, v
            continue
        pt, pv = prev

        def at(frac):
            return dict((k, pv[k]+frac*(v[k]-pv[k])) for k in v)
        for key, net, level, s in thresholds:
            a, b = pv[net]-level*pv['vdd!'], v[net]-level*v['vdd!']
            if (a > 0) != (b > 0):
                frac = -a/(b-a)
                when = pt+frac*(t-pt)
                i = int(math.floor((when-origin)/period))
                if 0 <= i < len(frames):
                    frames[i]['selector_edges'][key].append(((when-origin-i*period)*1e9, b > a))
                    if s is not None and level != .5 and b > a:
                        sample = at(frac)
                        frames[i]['selector_levels'].setdefault(s['name'], {})['q%d' % int(level*100)] = [
                            sample[n]/sample['vdd!'] for n in s['inputs']]
        edges = []
        for net in watch:
            a, b = pv[net]-.5*pv['vdd!'], v[net]-.5*v['vdd!']
            if (a > 0) != (b > 0):
                frac = -a/(b-a)
                edges.append((pt+frac*(t-pt), net, b > a, frac))
        for when, net, up, frac in sorted(edges):
            if net in pulses:
                pulses[net].append((when, up))
            if net in phases:
                phases[net].append((when, up))
                continue
            i = int(math.floor((when-origin)/period))
            if not 0 <= i < len(frames):
                continue
            f = frames[i]
            tm = (when-origin-i*period)*1e9
            if net in bus:
                f['public'].append(tm)
            elif net == track:
                sample = at(frac)
                if up and any(sample[n] > .5*sample['vdd!'] for n in (cmpnet, wr)):
                    f['track_overlaps'].append(dict(ns=tm, event='high at opening',
                                                    nets=[n for n in (cmpnet, wr) if sample[n] > .5*sample['vdd!']],
                                                    clock_low_ns=None))
                top = sample['xdut.topp']-sample['xdut.topn']
                residual = (top-sample['vinp_src']+sample['vinn_src'])/lsb
                f['track'].append(dict(ns=tm, up=up, close_error_lsb=None if up else residual, top_diff_v=top,
                                       preset_bottom=bottom_state(sample, groups, lsb) if up else None,
                                       preset_asserted=sample['xdut.preset'] > .5*sample['vdd!']))
            elif net == 'xdut.preset' and up:
                f['preset'].append(tm)
            elif net == wr and up:
                sample = at(frac)
                if sample[track] > .5*sample['vdd!']:
                    f['track_overlaps'].append(dict(ns=tm, event='write during track'))
                pr, nr = [sample[tim+x] > .5*sample['vdd!'] for x in ('pr', 'nr')]
                f['writes'].append(dict(ns=tm, decision=int(pr) if pr != nr else None,
                                        trials=dict((s['name'], sample[s['trial']] > .5*sample['vdd!']) for s in sels)))
            elif net == cmpnet and up:
                sample = at(frac)
                if sample[track] > .5*sample['vdd!']:
                    f['track_overlaps'].append(dict(ns=tm, event='compare during track'))
                j = len(f['bits'])
                base = origin+i*period
                prior = f['writes'][-1]['ns'] if f['writes'] else next(
                    (x['ns'] for x in reversed(f['track']) if not x['up']), None)
                timing = {}
                for key, ph in (('launch', launch), ('delivery', delivery)):
                    stamps = [(s, r) for s, r in phases[ph] if prior is not None and base+prior*1e-9 < s <= when]
                    timing[key] = [dict(ns=(s-base)*1e9, rise=r) for s, r in stamps]
                top = sample['xdut.topp']-sample['xdut.topn']
                bit = dict(bit=7-j, cmp_ns=tm, window_ns=tm-prior if prior is not None else None,
                           trial=word(sample, 'xdut.code'), top_diff_v=top,
                           bottom=bottom_state(sample, groups, lsb),
                           signed_lsb=signed_settling(sample, groups, weights, lsb, rails), phase=timing,
                           selects=dict((s['name'], sample[s['q']] > .5*sample['vdd!']) for s in sels))
                if j == 0:
                    closes = [x for x in f['track'] if not x['up']]
                    gate = max(sample['xdut.xboot%s.g' % s]-min(sample['vin'+s], sample['xdut.top'+s]) for s in 'pn')
                    bit['first_compare'] = dict(
                        gate_overdrive_v=gate, after_close_ns=tm-closes[-1]['ns'] if closes else None,
                        top_drift_lsb=(top-closes[-1]['top_diff_v'])/lsb if closes else None,
                        residual_lsb=(top-sample['vinp_src']+sample['vinn_src'])/lsb)
                f['bits'].append(bit)
            elif net == cmpnet:
                # Close the duration of a comparator clock found high when tracking opened.
                for o in f['track_overlaps']:
                    if o['event'] == 'high at opening' and o.get('clock_low_ns') is None and tm >= o['ns']:
                        o['clock_low_ns'] = tm
                        o['overlap_ps'] = (tm-o['ns'])*1e3
        i = int(math.floor((t-origin)/period))
        for j in (i-1, i):
            if 0 <= j < len(frames):
                base = origin+j*period
                for ns, key in ((90, 'code90'), (98, 'code98')):
                    at_time = base+ns*1e-9
                    if pt < at_time <= t:
                        frames[j][key] = word(at((at_time-pt)/(t-pt)), 'd')
        prev = t, v
    if prev is None or prev[0] < ctx['expected_stop_s']-1e-12:
        raise ValueError('Incomplete transient')
    obs = {}
    warnings = set()
    with open(root+'/spectre.out') as stream:
        for line in stream:
            m = re.search(r'BPROBE,0,(\d+),(\d+)', line)
            if m:
                if int(m.group(1)) in obs:
                    raise ValueError('Duplicate observer frame')
                obs[int(m.group(1))] = int(m.group(2))
            warnings.update(re.findall(r'WARNING \(([^)]+)\)', line))
    gate_limit = ctx['first_compare_gate_limit_v']
    for f in frames:
        bits, writes = f['bits'], f['writes']
        ordered = len(bits) == len(writes) == 8
        decided = 0
        for j, (b, w) in enumerate(zip(bits, writes)):
            trial = decided | (128 >> j)
            ph = b['phase']
            if j == 0:
                # Tracking leaves every tap high; the first trial needs no delivered transition.
                valid = not ph['launch'] and not ph['delivery']
            else:
                valid = (len(ph['launch']) == len(ph['delivery']) == 1 and
                         ph['launch'][0]['rise'] == ph['delivery'][0]['rise'] == (j % 2 == 0) and
                         ph['launch'][0]['ns'] < ph['delivery'][0]['ns'] < b['cmp_ns'])
            b['phase_pass'] = valid
            b['decision'] = w['decision']
            b['trial_pass'] = bool(b['bottom'] and b['bottom']['gate_words'] == [255-trial, trial] and b['trial'] == trial)
            if j:
                ordered = ordered and writes[j-1]['ns'] < b['cmp_ns']
            ordered = ordered and b['cmp_ns'] < w['ns'] and b['trial_pass'] and valid and w['decision'] is not None
            if w['decision']:
                decided |= 128 >> j
        coord = ctx.get('input_code_coordinates', ctx['expected_codes'])[f['frame']]
        f['input_code_coordinate'] = coord
        ideal = max(0, min(255, 128+int(math.floor((coord+.5-128)/ctx['independent_cdac_gain']))))
        f['gain_expected'] = ideal
        f['digital_pass'] = bool(ordered and f['code90'] == f['code98'] == obs.get(f['frame']) == decided)
        tolerance = 0 if ctx.get('kind') == 'boundary' and f['frame'] >= 2 else 1
        f['analog_code_pass'] = f['code90'] is not None and abs(f['code90']-ideal) <= tolerance
        f['decision_word'] = decided if len(writes) == 8 else None
        signed = [abs(b['signed_lsb']) for b in bits]
        f['max_abs_signed_settling_lsb'] = max(signed) if signed else None
        f['settling_pass'] = len(bits) == 8 and all(b['bottom'] and b['bottom']['weighted_bound_lsb'] <= limit
                                                    for b in bits) and max(signed) <= limit
        f['settling_target_pass'] = bool(f['settling_pass'] and max(signed) <= target)
        first = bits[0].get('first_compare') if bits else None
        f['first_compare_pass'] = bool(first and first['gate_overdrive_v'] <= gate_limit)
        f['margin_ns'] = 90-max([writes[-1]['ns']]+[s for s in f['public'] if s <= 98]) if len(writes) == 8 else None
        f['routing_fraction'] = None
        if f['margin_ns'] is not None and len(f['track']) == 2:
            f['routing_fraction'] = f['margin_ns']/(90-f['track'][1]['ns'])
        f['track_pass'] = bool(len(f['track']) == 2 and [x['up'] for x in f['track']] == [True, False] and
                               f['track'][0]['preset_asserted'] and f['track'][0]['preset_bottom'] and
                               f['track'][0]['preset_bottom']['gate_words'] == [127, 128] and
                               f['track'][0]['preset_bottom']['weighted_bound_lsb'] <= limit and
                               abs(f['track'][1]['close_error_lsb']) <= limit)
        f['control_pass'] = bool(not f['track_overlaps'] and len(f['track']) == 2 and len(bits) == len(writes) == 8
                                 and f['track'][1]['ns'] < bits[0]['cmp_ns'] and len(f['preset']) == 1
                                 and writes[-1]['ns'] < f['preset'][0])
        f['handoff'] = selector_handoffs(f, sels)
        f['warmup'] = f['frame'] < ctx.get('warmup_frames', 0)
        f['pass'] = bool(f['digital_pass'] and (f['analog_code_pass'] or ctx.get('mismatch')) and f['settling_pass']
                         and f['control_pass'] and f['track_pass'] and f['margin_ns'] > 0 and f['handoff']['passed']
                         and f['first_compare_pass'])
        del f['selector_edges']
    # Warm-up frames start from the DC solution; they are reported but do not enter the verdict.
    scored = [f for f in frames if not f['warmup']]
    margins = [f['margin_ns'] for f in scored if f['margin_ns'] is not None]
    floor_ok = len(margins) == len(scored) and min(margins) >= 3
    overlaps = [dict(frame=f['frame'], warmup=f['warmup'], **o) for f in frames for o in f['track_overlaps']
                if o['event'] == 'high at opening']
    closes = [abs(f['track'][1]['close_error_lsb']) for f in frames if len(f['track']) == 2]
    recovery = [f['writes'][0]['ns']-f['track'][1]['ns'] for f in frames if f['writes'] and len(f['track']) == 2]
    removal = [100+b['track'][0]['ns']-a['writes'][-1]['ns'] for a, b in zip(frames, frames[1:])
               if a['writes'] and b['track']]
    result = dict(run_id=ctx['run_id'], cell_lpe=ctx['cell_lpe'], taps=ctx['taps'], cdac_view=ctx['cdac_view'],
                  cdac_gds=ctx['cdac_physical_gds_sha256'], native_points=points, ports=510, frames=frames,
                  min_margin_ns=min(margins) if margins else None, routing_floor_3ns_pass=floor_ok,
                  routing_target_5ns_pass=len(margins) == len(scored) and min(margins) >= 5,
                  warmup_frames=[{'frame': f['frame'], 'pass': f['pass'], 'code90': f['code90']} for f in frames if f['warmup']],
                  clock_high_at_opening=overlaps,
                  max_clock_high_at_opening_ps=max([o.get('overlap_ps') or 0 for o in overlaps] or [0]),
                  max_abs_close_error_lsb=max(closes) if closes else None,
                  max_abs_signed_settling_lsb=max(f['max_abs_signed_settling_lsb'] or 0 for f in frames),
                  settling_target_pass=all(f['settling_target_pass'] for f in frames),
                  max_first_compare_gate_overdrive_v=max(f['bits'][0]['first_compare']['gate_overdrive_v']
                                                         for f in frames if f['bits']),
                  pulse_ps=dict(set_high_min=min(widths(pulses[setnet], True) or [None]),
                                clr_n_low_min=min(widths(pulses[clrnet], False) or [None]),
                                cmp_high_min=min(widths(pulses[cmpnet], True) or [None]),
                                cmp_low_min=min(widths(pulses[cmpnet], False) or [None]),
                                commit_high_min=min(widths(pulses[wr], True) or [None])),
                  close_to_first_commit_min_ns=min(recovery) if recovery else None,
                  last_commit_to_next_open_min_ns=min(removal) if removal else None,
                  all_pass=all(f['pass'] for f in scored) and (ctx['corner'] != 'ssc' or floor_ok),
                  warnings=sorted(warnings))
    if 'min_cp_high_ps' in ctx:
        import single_edge_audit as audit
        checked = audit.analyze(root, out, os.path.join(root, 'inputs/dff.json'),
                                bottom_measure=lambda v, lsb: bottom_state(v, groups, lsb))
        ccs = checked['ccs']
        counts = ccs['observation_counts']
        write_widths = widths(pulses[wr], True)
        pin_pass = (counts['writes'] == len(frames)*8*len(checked['register_pins']) and
                    not counts.get('inactive_or_unknown_cdn') and bool(write_widths) and
                    min(write_widths) >= ctx['min_cp_high_ps'] and
                    all(ccs['minimum_slack'].get(k, {}).get('slack_ps', -1) >= 0 for k in ('setup', 'hold')))
        result.update(ccs=ccs, register_pins=checked['register_pins'], pin_pass=pin_pass,
                      min_cp_high_reference_ps=ctx['min_cp_high_ps'], all_pass=result['all_pass'] and pin_pass)
        if 'selector_ccs' in checked:
            result['selector_ccs'] = checked['selector_ccs']
    with open(out+'/result.json', 'w') as stream:
        json.dump(result, stream, indent=2)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--run-dir', required=True)
    p.add_argument('--source-run-dir')
    p.add_argument('--output-dir', required=True)
    args = p.parse_args()
    analyze(args.source_run_dir or args.run_dir, args.output_dir)
