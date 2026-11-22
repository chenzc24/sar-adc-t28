"""Chip output register timing on the native waveform of a prepare_output_register run (Python 2.7 on the host).

Analysis-only job. sar8_out_reg captures the ADC word D0-D7 through DEL250D1 -> DFQD1 -> BUFFD4 on the rising
edge of SAMPLE, which is also its CK node (ideal route; CK at the register is read at `sample`). Levels are
fractions of the local supply: VDD! for the ADC D_i, DVDD for the register nets and CK. For every CK rising
50 % crossing and every bit:
  - capture: the Q word 5 ns after the edge against the ADC D word at the edge (the code of the frame that just
    ended), the DD and QI words, and no further Q/QI transition until the next edge;
  - setup: the CK crossing minus the last DD_i 50 % crossing before it;
  - hold: the first DD_i 50 % crossing after the edge minus the edge; the same at the ADC D_i is the hold
    without the delay cell;
  - clock-to-Q: QI_i and Q_i 50 % crossings after the edge, with the Q_i 10-90 % transition at 150 fF.
Transitions are 30-70 %, linear between native points. The DFQD1 D/CP setup_rising and hold_rising tables
of the run's corner are streamed read-only from the foundry CCS archive and interpolated, as
register_constraints.py does for the SAR registers, at the CK transition and the transition of the DD_i (or
D_i) crossing that sets the interval, both divided by the library slew derate. A bit without a crossing on one
side has an interval longer than the waveform and is not scored on that side.
"""
from __future__ import print_function, division
import argparse
import json
import os
import re
import tarfile

import native_stream
import register_constraints

BITS = range(8)
LEVELS = (.1, .3, .5, .7, .9)
SETTLE_S = 5e-9
SLEW_WINDOW_S = 2e-9
CK = 'sample'
ARCHIVE = '/home/process/tsmc28n/STD_CELL/tcbn28hpcplusbwp12t30p140_190a/tcbn28hpcplusbwp12t30p140_180a_ccs.tar.gz'
ARCHIVE_BYTES = 13657415950
CELL = 'DFQD1BWP12T30P140'
MEMBERS = {'tt': 'tt0p9v25c', 'ssc': 'ssg0p81vm40c', 'ssh': 'ssg0p81v125c', 'ffc': 'ffg0p99vm40c', 'ffh': 'ffg0p99v125c'}


def nets(bit):
    return dict(d='d%d' % bit, dd='xoreg.dd%d' % bit, qi='xoreg.qi%d' % bit, q='q%d' % bit)


def rail(net, v):
    return v['vdd!'] if re.match(r'd\d$', net) else v['dvdd']


def stream(path, ctx, needed):
    alias = ctx.get('signal_aliases', {})
    names = None
    for t, v in native_stream.samples(path):
        if names is None:
            names = dict((k, alias.get(k, k)) for k in v if alias.get(k, k) in needed)
            missing = set(needed) - set(names.values())
            if missing:
                raise ValueError('Missing signals: ' + repr(sorted(missing)))
        yield t, dict((n, v[k]) for k, n in names.items())


def words(v, kind):
    return sum(1 << b for b in BITS if v[nets(b)[kind]] > .5 * rail(nets(b)[kind], v))


def snapshot(v):
    return dict((k, words(v, k)) for k in ('d', 'dd', 'qi', 'q'))


def waveform(root, ctx):
    """Level crossings of every net and word snapshots at each CK edge and SETTLE_S after it."""
    raw = [os.path.join(p, n) for p, _, files in os.walk(root + '/raw') for n in files if n.endswith('.tran.tran')]
    if len(raw) != 1:
        raise ValueError('Expected one native transient')
    watched = [CK] + [n for b in BITS for n in sorted(nets(b).values())]
    events = dict((n, dict((lvl, []) for lvl in LEVELS)) for n in watched)
    edges, pending, prev, points = [], [], None, 0
    for t, v in stream(raw[0], ctx, watched + ['vdd!', 'dvdd']):
        points += 1
        if prev is None:
            prev = t, v
            continue
        pt, pv = prev

        def at(when):
            f = (when - pt) / (t - pt)
            return dict((k, pv[k] + f * (v[k] - pv[k])) for k in v)
        for n in watched:
            for lvl in LEVELS:
                a, b = pv[n] - lvl * rail(n, pv), v[n] - lvl * rail(n, v)
                if (a > 0) != (b > 0):
                    when = pt + (t - pt) * a / (a - b)
                    events[n][lvl].append((when, b > a))
                    if n == CK and lvl == .5 and b > a:
                        edges.append(dict(t=when, at_edge=snapshot(at(when)), after=None))
                        pending.append((when + SETTLE_S, edges[-1]))
        for when, e in [p for p in pending if p[0] <= t]:
            e['after'] = snapshot(at(when))
        pending = [p for p in pending if p[0] > t]
        prev = t, v
    if prev is None or prev[0] < ctx['expected_stop_s'] - 1e-12:
        raise ValueError('Incomplete transient')
    return events, edges, prev[0], points


def slew(ev, when, rising):
    """30-70 % transition of the 50 % crossing at `when` (None if the bracketing crossings are missing)."""
    lo = [t for t, r in ev[.3] if r == rising]
    hi = [t for t, r in ev[.7] if r == rising]
    first, second = (lo, hi) if rising else (hi, lo)
    before = [t for t in first if when - SLEW_WINDOW_S <= t <= when]
    after = [t for t in second if when <= t <= when + SLEW_WINDOW_S]
    return (after[0] - before[-1]) if before and after else None


def transition_10_90(ev, when, rising):
    lo = [t for t, r in ev[.1] if r == rising]
    hi = [t for t, r in ev[.9] if r == rising]
    first, second = (lo, hi) if rising else (hi, lo)
    before = [t for t in first if when - SLEW_WINDOW_S <= t <= when]
    after = [t for t in second if when <= t <= when + SLEW_WINDOW_S]
    return (after[0] - before[-1]) if before and after else None


def last_before(ev, when):
    rows = [(t, r) for t, r in ev[.5] if t < when]
    return rows[-1] if rows else None


def first_after(ev, when, until=None):
    rows = [(t, r) for t, r in ev[.5] if t >= when and (until is None or t < until)]
    return rows[0] if rows else None


def ps(x):
    return None if x is None else x * 1e12


# ---------------------------------------------------------------- Liberty (read-only CCS archive)

def group(text, pattern):
    for match in re.finditer(pattern, text, re.M):
        start, pos, depth = match.start(), match.end(), 1
        while depth and pos < len(text):
            c = text[pos]
            pos += 1
            if c == '}':
                depth -= 1
            elif c == '{':
                depth += 1
        if depth:
            raise ValueError('Incomplete Liberty group')
        yield text[start:pos]


def attr(text, key):
    m = re.search(r'\b' + key + r'\s*:\s*"?([^";\s]+)', text)
    return m.group(1) if m else None


def numbers(s):
    return [float(x) for x in s.replace('"', '').replace('\\', '').split(',') if x.strip()]


def constraint_tables(head, cell_text):
    """setup_rising / hold_rising D-to-CP tables of the cell, with the library attributes and axis order."""
    pin = next(group(cell_text, r'\bpin\s*\(\s*"?D"?\s*\)\s*\{'))
    arcs = {}
    for arc in group(pin, r'\btiming\s*\(\s*"?[^)]*"?\)\s*\{'):
        kind = attr(arc, 'timing_type')
        if kind not in ('setup_rising', 'hold_rising') or attr(arc, 'related_pin') != 'CP':
            continue
        row = dict(when=attr(arc, 'when'))
        for edge in ('rise_constraint', 'fall_constraint'):
            table = next(group(arc, r'\b' + edge + r'\s*\(\s*"?([^)"]*)"?\s*\)\s*\{'))
            template = re.match(r'\w+\s*\(\s*"?([^)"]*)"?\s*\)', table).group(1).strip()
            axes = [numbers(re.search(r'index_%d\s*\(([^)]+)\)' % i, table).group(1)) for i in (1, 2)]
            values = [numbers(x) for x in re.findall(r'"([^"]+)"', re.search(r'values\s*\(([^)]+)\)', table).group(1))]
            if len(values) != len(axes[0]) or any(len(x) != len(axes[1]) for x in values):
                raise ValueError('Liberty table shape differs from its axes')
            spec = next(group(head, r'\blu_table_template\s*\(\s*"?' + re.escape(template) + r'"?\s*\)\s*\{'))
            row[edge] = dict(axes=axes, table=values, template=template,
                             variables=[attr(spec, 'variable_1'), attr(spec, 'variable_2')])
        if kind in arcs:
            raise ValueError('More than one %s arc on D' % kind)
        arcs[kind] = row
    if sorted(arcs) != ['hold_rising', 'setup_rising']:
        raise ValueError('Missing D/CP constraint arcs')
    axis_order = arcs['setup_rising']['rise_constraint']['variables']
    if any(arcs[k][e]['variables'] != axis_order for k in arcs for e in ('rise_constraint', 'fall_constraint')) or \
            set(axis_order) != set(['related_pin_transition', 'constrained_pin_transition']):
        raise ValueError('Unexpected constraint table axes')
    keys = ('time_unit', 'slew_derate_from_library', 'input_threshold_pct_rise', 'input_threshold_pct_fall',
            'slew_lower_threshold_pct_rise', 'slew_lower_threshold_pct_fall', 'slew_upper_threshold_pct_rise',
            'slew_upper_threshold_pct_fall')
    return dict(arcs=arcs, attributes=dict((k, attr(head, k)) for k in keys), axis_order=axis_order)


def read_cell(stream_file):
    head = stream_file.read(512 * 1024).decode('latin-1')
    pattern = re.compile(r'\bcell\s*\(\s*"?' + CELL + r'"?\s*\)\s*\{')
    buf = head
    while not pattern.search(buf):
        chunk = stream_file.read(1024 * 1024)
        if not chunk:
            raise ValueError('Cell not found: ' + CELL)
        buf = buf[-200:] + chunk.decode('latin-1')
    buf = buf[pattern.search(buf).start():]
    while not re.search(r'\bcell\s*\(', buf[12:]):
        chunk = stream_file.read(512 * 1024)
        if not chunk or len(buf) > 20000000:
            raise ValueError('Incomplete cell group')
        buf += chunk.decode('latin-1')
    return head, next(group(buf, r'\bcell\s*\(\s*"?' + CELL + r'"?\s*\)\s*\{'))


def liberty(corner):
    info = os.stat(ARCHIVE)
    if info.st_size != ARCHIVE_BYTES:
        raise ValueError('CCS archive size differs from the recorded release')
    wanted = 'tcbn28hpcplusbwp12t30p140' + MEMBERS[corner] + '_ccs.lib'
    with tarfile.open(ARCHIVE, 'r|gz', bufsize=1024 * 1024) as archive:
        for member in archive:
            if os.path.basename(member.name) == wanted and member.isreg():
                f = archive.extractfile(member)
                head, cell = read_cell(f)
                f.close()
                out = constraint_tables(head, cell)
                out.update(archive=ARCHIVE, archive_bytes=info.st_size, archive_mtime=info.st_mtime, member=member.name,
                           member_bytes=member.size, cell=CELL, corner=corner)
                return out
    raise ValueError('Liberty member not found: ' + wanted)


def requirement(lib, check, rising, ck_slew_s, data_slew_s):
    """DFQD1 requirement (ps) for the D transition direction at the given 30-70 % transitions."""
    if lib is None or ck_slew_s is None or data_slew_s is None:
        return None, None
    derate = float(lib['attributes']['slew_derate_from_library'])
    table = lib['arcs'][check + '_rising']['rise_constraint' if rising else 'fall_constraint']
    point = {'related_pin_transition': ck_slew_s * 1e9 / derate, 'constrained_pin_transition': data_slew_s * 1e9 / derate}
    value, outside = register_constraints._table_ps(table, *(point[k] for k in lib['axis_order']))
    return value, 'outside_table' if outside else 'in_table'


def check_library(lib):
    a = lib['attributes']
    if a['time_unit'] != '1ns' or float(a['slew_derate_from_library']) <= 0:
        raise ValueError('Unsupported Liberty time unit or derate')
    for edge in ('rise', 'fall'):
        if [float(a[k + '_pct_' + edge]) for k in ('slew_lower_threshold', 'input_threshold', 'slew_upper_threshold')] != [30, 50, 70]:
            raise ValueError('Liberty thresholds differ from the 30/50/70 % waveform levels')


# ---------------------------------------------------------------- measurement

def measure(events, edges, stop, ctx, lib):
    origin, period, warm = ctx['frame_origin_s'], ctx['period_s'], ctx.get('warmup_frames', 0)
    rows, glitches = [], []
    for k, e in enumerate(edges):
        te = e['t']
        nxt = edges[k + 1]['t'] if k + 1 < len(edges) else None
        frame = int((te - origin) // period) - 1
        ck_slew = slew(events[CK], te, True)
        bits = []
        for b in BITS:
            n = nets(b)
            row = dict(bit=b)
            last = last_before(events[n['dd']], te)
            s = slew(events[n['dd']], last[0], last[1]) if last else None
            req, method = requirement(lib, 'setup', last[1], ck_slew, s) if last else (None, None)
            row.update(setup_ps=ps(te - last[0]) if last else None, setup_data_rising=last[1] if last else None,
                       setup_data_slew_ps=ps(s), setup_requirement_ps=req, setup_method=method)
            row['setup_slack_ps'] = row['setup_ps'] - req if req is not None else None
            for key, net in (('hold', n['dd']), ('hold_no_delay', n['d'])):
                nxt_edge = first_after(events[net], te)
                row[key + '_ps'] = ps(nxt_edge[0] - te) if nxt_edge else None
                row[key + '_data_rising'] = nxt_edge[1] if nxt_edge else None
                s = slew(events[net], nxt_edge[0], nxt_edge[1]) if nxt_edge else None
                row[key + '_data_slew_ps'] = ps(s)
                req, method = requirement(lib, 'hold', nxt_edge[1], ck_slew, s) if nxt_edge else (None, None)
                row[key + '_requirement_ps'], row[key + '_method'] = req, method
                row[key + '_slack_ps'] = row[key + '_ps'] - req if req is not None and row[key + '_ps'] is not None else None
            for kind in ('qi', 'q'):
                hit = first_after(events[n[kind]], te, te + SETTLE_S)
                row['ck_to_%s_ps' % kind] = ps(hit[0] - te) if hit else None
                row['%s_rising' % kind] = hit[1] if hit else None
                if kind == 'q':
                    row['q_transition_10_90_ps'] = ps(transition_10_90(events[n['q']], hit[0], hit[1])) if hit else None
                    row['q_slew_30_70_ps'] = ps(slew(events[n['q']], hit[0], hit[1])) if hit else None
                late = [t for t, _ in events[n[kind]][.5] if te + SETTLE_S <= t < (nxt if nxt is not None else stop + 1)]
                early = [t for t, _ in events[n[kind]][.5] if te <= t < te + SETTLE_S]
                if late or len(early) > 1:
                    glitches.append(dict(edge_ns=te * 1e9, bit=b, net=n[kind], crossings_ns=[x * 1e9 for x in early + late]))
            bits.append(row)
        after = e['after']
        capture = bool(after is not None and after['q'] == e['at_edge']['d'] and after['qi'] == e['at_edge']['d'])
        rows.append(dict(ck_ns=te * 1e9, ck_slew_30_70_ps=ps(ck_slew), captured_frame=frame,
                         warmup=frame < warm, initial=frame < 0, d_word_at_edge=e['at_edge']['d'],
                         dd_word_at_edge=e['at_edge']['dd'], q_word_before=e['at_edge']['q'],
                         q_word_after=after['q'] if after else None, qi_word_after=after['qi'] if after else None,
                         capture_pass=capture, bits=bits))
    # The word held until the next edge is the word captured at this one.
    for a, b in zip(rows, rows[1:]):
        a['q_word_held_to_next_edge'] = b['q_word_before']
        a['capture_pass'] = a['capture_pass'] and b['q_word_before'] == a['q_word_after']
    return rows, glitches


def worst(rows, key, pick=min):
    found = [(r['ck_ns'], b['bit'], b[key]) for r in rows for b in r['bits'] if b.get(key) is not None]
    if not found:
        return None
    ck, bit, value = pick(found, key=lambda x: x[2])
    return dict(value=value, ck_ns=ck, bit=bit, observations=len(found))


def summarize(rows, glitches):
    scored = [r for r in rows if not r['warmup'] and not r['initial']]
    out = dict(scored_edges=len(scored), captured_frames=[r['captured_frame'] for r in scored],
               capture_pass=bool(scored) and all(r['capture_pass'] for r in scored) and not [
                   g for g in glitches if any(g['edge_ns'] == r['ck_ns'] for r in scored)],
               unexpected_q_transitions=glitches)
    w = {}
    for key in ('setup_ps', 'hold_ps', 'hold_no_delay_ps', 'setup_slack_ps', 'hold_slack_ps', 'hold_no_delay_slack_ps'):
        w[key] = worst(scored, key)
    for key in ('ck_to_qi_ps', 'ck_to_q_ps', 'q_transition_10_90_ps'):
        w[key + '_max'] = worst(scored, key, max)
        w[key + '_min'] = worst(scored, key, min)
    out['worst'] = w
    return out


def analyze(root, out):
    with open(root + '/inputs/context.json') as f:
        ctx = json.load(f)
    if 'output_register' not in ctx:
        raise ValueError('Not an output-register run')
    lib, lib_error = None, None
    try:
        lib = liberty(ctx['corner'])
        check_library(lib)
    except Exception as exc:  # The waveform result stands without the library limits.
        lib, lib_error = None, '%s: %s' % (type(exc).__name__, exc)
    events, edges, stop, points = waveform(root, ctx)
    rows, glitches = measure(events, edges, stop, ctx, lib)
    result = dict(run_id=ctx['run_id'], corner=ctx['corner'], vdd_v=ctx['vdd_v'], temperature_c=ctx['temperature_c'],
                  native_points=points, stop_s=stop, settle_s=SETTLE_S, q_load_F=ctx['output_register']['q_load_F'],
                  edges=rows, summary=summarize(rows, glitches), liberty=lib, liberty_error=lib_error,
                  method=__doc__.strip())
    with open(out + '/result.json', 'w') as f:
        json.dump(result, f, indent=2)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--run-dir', required=True)
    p.add_argument('--source-run-dir')
    p.add_argument('--output-dir', required=True)
    a = p.parse_args()
    analyze(a.source_run_dir or a.run_dir, a.output_dir)
