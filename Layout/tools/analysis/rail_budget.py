"""Stage 1 reference and supply current budget for the top-level checks.

Inputs: the measured per-frame and windowed rail charge of se-xref-adc-post-b (rail_charge.py),
the single-edge switching scheme (PRESET word 0x80, the eighth COMMIT re-asserts PRESET while TOP
floats) and the Stage 6 system model chosen on 2026-11-21 (stiff reference with board bypass,
wire bonds with two per reference rail, on-chip series resistor plus VREFP-VREFN decoupling).

The reference charge model is the ideal CDAC charge plus a per-toggled-unit term fitted to the
measured frames (extracted bottom-plate, junction and switch-overlap charge). Rail responses are a
linear differential-loop model, superposed over each update's charge and read at each comparator
edge. Writes Layout/results/rail_budget.json."""
import argparse
import itertools
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
MEASURED = ['stage1-rail-charge-adc-post-b', 'stage1-rail-window-adc-post-b']
CU, VR, LSB, PRESET = 4.00407e-15, .9, 1.8 / 256, 0x80
CP_TOP = 60e-15                     # coupled-extraction fixed TOP load per side
CAPS = [CU * 2 ** k for k in range(8)] + [CU]
# Shortest measured update-to-next-compare interval per corner (sar_timing.json, filled) and the
# compare-to-update allowance from the behavioral TT intervals, scaled for the slow corner.
CORNERS = {'ffc': (2.14e-9, .83e-9), 'tt': (2.55e-9, .90e-9), 'ssc': (3.63e-9, 1.2e-9)}
FIRST_COMPARE_S = 47.6e-9
PULSES_S = (.5e-9, .8e-9)           # bracket the measured fixture droop and peak current
# VREFP and VREFN each use two bonds on adjacent, interleaved pads; the VDD/VSS pairs keep one.
# Mutual inductance between the wires is ignored, which overstates the loop inductance.
SYSTEM = dict(source_ohm=1., board_bypass_f=100e-9, board_esr_ohm=.01, board_esl_h=.5e-9,
              pin_h=1e-9, pin_ohm=.1, supply_pin_h=2e-9, supply_pin_ohm=.2, pad_f=.5e-12)
DESIGN = dict(series_ohm=15., span_cap_f=8e-12)
TOLERANCE = dict(series=(.8, 1.2), cap=(.75, 1.25), pin_h=(.5e-9, 1.5e-9))
SINGLE_BOND = dict(series_ohm=20., span_cap_f=6e-12, pin_h=2e-9, pin_ohm=.2)   # earlier choice, for comparison
CORNER_CHARGE = 1.3                 # FF 0.99 V and top-level extraction allowance on TT charge


def bottoms(code):
    """Bottom-plate voltages per bit, P side then N side; the fixed dummies come last."""
    p = [VR * (1 - (code >> k & 1)) for k in range(8)] + [VR]
    n = [VR * (code >> k & 1) for k in range(8)] + [0.]
    return p, n


def side_step(b0, b1, top):
    """Charge out of VREFP for one floating-TOP side transition, and the new TOP voltage."""
    new = top + sum(c * (y - x) for c, x, y in zip(CAPS, b0, b1)) / (sum(CAPS) + CP_TOP)
    return sum(c * ((y - new) - (x - top)) for c, x, y in zip(CAPS, b0, b1) if y == VR), new


def trajectory(final):
    code, words = PRESET, []
    for k in range(7, -1, -1):
        code = code if final >> k & 1 else code & ~(1 << k)
        words.append(code | (1 << k - 1) if k else code)
        code = words[-1]
    return words + [PRESET]


def ideal_events(final, vcm=.45):
    """Ideal VREFP charge of the eight updates and the closing preset, with toggled units."""
    vin = -.9 + (final + .5) * LSB
    tops, code, out = [vcm + vin / 2, vcm - vin / 2], PRESET, []
    for word in trajectory(final):
        q = 0.
        for side, (b0, b1) in enumerate(zip(bottoms(code), bottoms(word))):
            dq, tops[side] = side_step(b0, b1, tops[side])
            q += dq
        out.append(dict(charge_c=q, units=sum(1 << k for k in range(8) if (code ^ word) >> k & 1), trial=word))
        code = word
    return out


def load(name):
    path = ROOT / 'work/output/managed_execution/runs' / name / 'collected/derived/result.json'
    return json.loads(path.read_text())


def calibrate(measured):
    """Per-toggled-unit charge from the steady measured frames (least squares through zero)."""
    rows = []
    for f in measured['frames'][measured['context']['first_steady_frame']:]:
        ev = ideal_events(f['observed_code'])
        rows.append((sum(e['charge_c'] for e in ev), sum(e['units'] for e in ev), f['die_charge_c']['vrefp']))
    gamma = sum((m - q) * u for q, u, m in rows) / sum(u * u for _, u, _ in rows)
    return gamma, [dict(ideal_c=q, toggled_units=u, measured_c=m, model_c=q + gamma * u) for q, u, m in rows]


def events(final, gamma):
    return [dict(e, charge_c=e['charge_c'] + gamma * e['units']) for e in ideal_events(final)]


def expm(m):
    s = max(0, int(np.ceil(np.log2(max(np.abs(m).sum(axis=1).max(), 1e-300)))) + 1)
    x, e, t = m / 2. ** s, np.eye(len(m)), np.eye(len(m))
    for k in range(1, 20):
        t = t @ x / k
        e = e + t
    for _ in range(s):
        e = e @ e
    return e


def loop(series_ohm, span_cap_f, pin_h=None, pin_ohm=None, **_):
    """Two-rail loop (VREFP-VREFN or VDD-VSS): series elements doubled, shunt-to-ground halved."""
    s = SYSTEM
    pin_h = s['pin_h'] if pin_h is None else pin_h
    pin_ohm = s['pin_ohm'] if pin_ohm is None else pin_ohm
    return dict(r1=2 * s['source_ohm'], cb=s['board_bypass_f'] / 2, rb=2 * s['board_esr_ohm'], lb=2 * s['board_esl_h'],
                l2=2 * pin_h, r2=2 * pin_ohm, cpad=s['pad_f'] / 2, ron=2 * series_ohm + 1e-3, cdie=span_cap_f)


def response(n, pulse, dt=1e-12, tend=60e-9):
    """Die-node voltage and pin current for one unit-charge triangular pulse (exact ZOH steps)."""
    cn = 10e-12
    a, b = np.zeros((6, 6)), np.zeros(6)
    # x = [v_board, i_bypass, v_bypass, i_pin, v_pad, v_die]
    a[0, 0], a[0, 1], a[0, 3] = -1 / (n['r1'] * cn), -1 / cn, -1 / cn
    a[1, 0], a[1, 1], a[1, 2] = 1 / n['lb'], -n['rb'] / n['lb'], -1 / n['lb']
    a[2, 1] = 1 / n['cb']
    a[3, 0], a[3, 3], a[3, 4] = 1 / n['l2'], -n['r2'] / n['l2'], -1 / n['l2']
    a[4, 3], a[4, 4], a[4, 5] = 1 / n['cpad'], -1 / (n['ron'] * n['cpad']), 1 / (n['ron'] * n['cpad'])
    a[5, 4], a[5, 5] = 1 / (n['ron'] * n['cdie']), -1 / (n['ron'] * n['cdie'])
    b[5] = -1 / n['cdie']
    m = np.zeros((7, 7))
    m[:6, :6], m[:6, 6] = a * dt, b * dt
    e = expm(m)
    p, g = e[:6, :6], e[:6, 6]
    t = np.arange(int(tend / dt)) * dt
    u = np.where(t < pulse, 2 / pulse * (1 - np.abs(2 * t / pulse - 1)), 0.)
    um = np.append(.5 * (u[:-1] + u[1:]), 0.)
    x, v, i = np.zeros(6), np.empty(len(t)), np.empty(len(t))
    for j in range(len(t)):
        v[j], i[j] = x[5], x[3]
        x = p @ x + g * um[j]
    return t, v, i


def schedule(compare_s, write_s):
    period = compare_s + write_s
    updates = [FIRST_COMPARE_S + write_s + k * period for k in range(8)]
    return updates + [updates[-1] + .5e-9], [u + compare_s for u in updates[:7]]


def reference_check(net, gamma, compare_s, write_s, codes=range(256)):
    """Worst reference-induced decision error, span droop and pin current over codes and pulses."""
    updates, decisions = schedule(compare_s, write_s)
    grid = np.arange(0, 100e-9, 5e-12)
    worst = dict(decision_error_lsb=0., at=None, span_droop_v=0., pin_peak_a=0.)
    for pulse in PULSES_S:
        t, h, hi = response(net, pulse, tend=100e-9)
        for code in codes:
            ev = events(code, gamma)
            v = sum(e['charge_c'] * np.interp(grid - tu, t, h, left=0.) for e, tu in zip(ev, updates))
            cur = sum(e['charge_c'] * np.interp(grid - tu, t, hi, left=0.) for e, tu in zip(ev, updates))
            worst['span_droop_v'] = max(worst['span_droop_v'], float(-v.min()))
            worst['pin_peak_a'] = max(worst['pin_peak_a'], float(np.abs(cur).max()))
            for e, td in zip(ev, decisions):
                # A span error d scales the DAC output: d*(trial-128)/128 volts, i.e. d*(trial-128)/0.9 LSB.
                err = abs(float(np.interp(td, grid, v))) * abs(e['trial'] - 128) / .9
                if err > worst['decision_error_lsb']:
                    worst.update(decision_error_lsb=err, at=dict(code=code, trial=e['trial'], pulse_s=pulse))
    return worst


def supply_check(q_event, q_repeat, cap_f, feed_ohm, compare_s=2.14e-9, write_s=.83e-9, pulse=.5e-9):
    """VDD-VSS droop of one branch behind a VDD/VSS pin pair, for one event train per frame."""
    net = loop(feed_ohm / 2., cap_f, pin_h=SYSTEM['supply_pin_h'], pin_ohm=SYSTEM['supply_pin_ohm'])
    t, h, hi = response(net, pulse, tend=100e-9)
    updates, _ = schedule(compare_s, write_s)
    qs = [q_event] + [q_repeat] * 7 + [q_event]
    grid = np.arange(0, 100e-9, 5e-12)
    v = sum(q * np.interp(grid - tu, t, h, left=0.) for q, tu in zip(qs, updates))
    cur = sum(q * np.interp(grid - tu, t, hi, left=0.) for q, tu in zip(qs, updates))
    before = max(abs(float(np.interp(tu - 50e-12, grid, v))) for tu in updates[1:])
    return dict(droop_v=float(-v.min()), residual_before_next_event_v=before, pin_peak_a=float(np.abs(cur).max()))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--box', action='store_true', help='also sweep the tolerance box at every corner (slow)')
    a = p.parse_args()
    frames, windows = load(MEASURED[0]), load(MEASURED[1])
    observed = json.loads((ROOT / 'Layout/results/single_edge_xref.json').read_text())
    codes = [f['code'] for f in observed['adc_tt']['se-xref-adc-post-b']['frames']]
    for f, code in zip(frames['frames'], codes):
        f['observed_code'] = code
    gamma, fit = calibrate(frames)
    per_code = []
    for code in range(256):
        ev = events(code, gamma)
        per_code.append(dict(code=code, conversion_c=sum(e['charge_c'] for e in ev), max_event_c=max(e['charge_c'] for e in ev)))
    amp = .9 * 10 ** (-1 / 20) * .9595
    sine = [min(255, max(0, int(128 + amp * np.sin(2 * np.pi * .1234567 * i) / LSB))) for i in range(4096)]
    mean_sine = float(np.mean([per_code[c]['conversion_c'] for c in sine]))
    design = {}
    for corner, (cmp_s, wr_s) in CORNERS.items():
        design[corner] = reference_check(loop(**DESIGN), gamma, cmp_s, wr_s)
    box = None
    if a.box:
        box = {}
        for corner, (cmp_s, wr_s) in CORNERS.items():
            worst = dict(decision_error_lsb=0.)
            peaks = dict(span_droop_v=0., pin_peak_a=0.)
            for fr, fc, lh in itertools.product(TOLERANCE['series'] + (1.,), TOLERANCE['cap'] + (1.,), TOLERANCE['pin_h'] + (SYSTEM['pin_h'],)):
                r = reference_check(loop(DESIGN['series_ohm'] * fr, DESIGN['span_cap_f'] * fc, pin_h=lh), gamma, cmp_s, wr_s, codes=range(0, 256, 5))
                peaks = dict((k, max(v, r[k])) for k, v in peaks.items())
                if r['decision_error_lsb'] > worst['decision_error_lsb']:
                    worst = dict(r, series_ohm=DESIGN['series_ohm'] * fr, span_cap_f=DESIGN['span_cap_f'] * fc, pin_h=lh)
            box[corner] = dict(worst, box_max_span_droop_v=peaks['span_droop_v'], box_max_pin_peak_a=peaks['pin_peak_a'])
    fixture = reference_check(dict(r1=1e-2, cb=1e-6, rb=1e-3, lb=1e-12, l2=1e-12, r2=1e-3, cpad=1e-15, ron=100., cdie=2e-12),
                              gamma, *CORNERS['tt'], codes=[c for c in codes])
    undamped = reference_check(loop(0., 8e-12, pin_h=SYSTEM['supply_pin_h'], pin_ohm=SYSTEM['supply_pin_ohm']),
                               gamma, *CORNERS['ffc'], codes=range(0, 256, 5))
    single_bond = reference_check(loop(**SINGLE_BOND), gamma, *CORNERS['ffc'], codes=range(0, 256, 5))
    steady = frames['frames'][frames['context']['first_steady_frame']:]
    wsteady = windows['frames'][windows['context']['first_steady_frame']:]
    vdd_event = max(f['window_charge_c']['1e-09']['vdd']['charge_c'] for f in wsteady)
    k = CORNER_CHARGE
    branches = {
        'pair_xref': dict(event_c=.48e-12, repeat_c=.25e-12, cap_f=10.07e-12, feed_ohm=12., placeholder_f=2.9239e-12,
                          basis='XREF part of the measured windowed VDD charge, 1.9 fC per toggled unit times 255 units'),
        'digital_sar': dict(event_c=.31e-12, repeat_c=.31e-12, cap_f=8.25e-12, feed_ohm=5., placeholder_f=5.554e-12,
                            basis='Rest of the largest measured 1 ns VDD event after the XREF part (SAR COMMIT and DONE)'),
        'analog_bootstrap': dict(event_c=.454e-12, repeat_c=.025e-12, cap_f=9.32e-12, feed_ohm=12., placeholder_f=1.5594e-12,
                                 basis='Upper bound: no 1 ns window at a sampling edge exceeded the 0.454 pC conversion-event maximum of frame 2'),
        'comparator_local': dict(event_c=.025e-12, repeat_c=.025e-12, cap_f=2 * .2355e-12, feed_ohm=30., placeholder_f=2 * .2355e-12,
                                 basis='Comparator charge per decision (Layout/results/comparator.md); 30 ohm in-core strap resistance'),
    }
    for b in branches.values():
        b['check'] = supply_check(b['event_c'] * k, b['repeat_c'] * k, b['cap_f'], b['feed_ohm'],
                                  pulse=.2e-9 if b['event_c'] < .1e-12 else .5e-9)
    result = dict(
        record='Stage 1 reference and supply current budget (chenzc24/sar-adc-t28#12)',
        measured_runs=MEASURED, source_run='se-xref-adc-post-b',
        measured_frames=[dict(frame=f['frame'], code=f['observed_code'], die_charge_c=f['die_charge_c'],
                              peak_source_a=f['peak_a'], span_droop_v=f['reference_span_droop_max_v'],
                              window_1ns_c=dict((r, x['charge_c']) for r, x in w['window_charge_c']['1e-09'].items()))
                         for f, w in zip(frames['frames'], windows['frames'])],
        steady_frames=frames['steady_frames'],
        reference_model=dict(gamma_c_per_toggled_unit=gamma, fit=fit,
                             conversion_c=dict(max=max(r['conversion_c'] for r in per_code), min=min(r['conversion_c'] for r in per_code),
                                               mean_uniform=float(np.mean([r['conversion_c'] for r in per_code])), mean_sine_minus1dbfs=mean_sine),
                             max_event_c=max(r['max_event_c'] for r in per_code),
                             argmax_conversion_code=max(per_code, key=lambda r: r['conversion_c'])['code']),
        supply_measured=dict(conversion_c=dict(max=max(f['die_charge_c']['vdd'] for f in steady), min=min(f['die_charge_c']['vdd'] for f in steady)),
                             peak_a=max(f['peak_a']['vdd'] for f in frames['frames']), max_event_1ns_c=vdd_event),
        system=SYSTEM, design=DESIGN, tolerance=TOLERANCE, corners=CORNERS, pulses_s=PULSES_S,
        reference_design_check=design, reference_tolerance_box=box,
        reference_fixture_check_tt=fixture, reference_undamped_single_bond_check_ffc=undamped,
        reference_single_bond_design=dict(SINGLE_BOND, check_ffc=single_bond),
        supply_branches=branches, corner_charge_allowance=k)
    (ROOT / 'Layout/results/rail_budget.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(gamma=gamma, design=design, box=box, fixture=fixture, undamped=undamped['decision_error_lsb'],
                          branches={n: b['check'] for n, b in branches.items()}), indent=1, default=str))


if __name__ == '__main__':
    main()
