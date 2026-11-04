"""Curate three completed short runs; fit is descriptive, never an ENOB claim."""
import csv
import gzip
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'verification/manual_adc/bootstrap_short_v1'
FIG = OUT / 'figures'
FIG.mkdir(exist_ok=True)
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False,
                     'axes.spines.right': False, 'savefig.dpi': 170})
LSB = 1.8 / 256
FREQ = 10e6 * 461 / 1024
AMP = .9 * 10**(-1/20)
cases = {}
summary = {}


def maximum(rows, key):
    return max(abs(x[key]) for x in rows)


def fit(rows, key):
    t = np.array([x['sample_close_s'] for x in rows])
    y = np.array([x[key] for x in rows])
    matrix = np.column_stack([np.ones(len(t)), np.sin(2*np.pi*FREQ*t),
                              np.cos(2*np.pi*FREQ*t)])
    b = np.linalg.lstsq(matrix, y, rcond=None)[0]
    pred = matrix @ b
    residual = y - pred
    amplitude = np.hypot(b[1], b[2])
    result = {'offset_V': float(b[0]), 'amplitude_V': float(amplitude),
              'gain_error_percent': float((amplitude / AMP - 1)*100),
              'phase_deg': float(np.degrees(np.arctan2(b[2], b[1]))),
              'effective_lag_s': float(-np.arctan2(b[2], b[1])/(2*np.pi*FREQ)),
              'residual_peak_V': float(np.max(np.abs(residual))),
              'residual_rms_V': float(np.sqrt(np.mean(residual**2))),
              'fitted_V': pred.tolist(), 'residual_V': residual.tolist()}
    return result


def wave(case):
    path = ROOT / ('output/managed_execution/runs/manual8-bootshort-' + case + '-v1/collected/derived/wave.csv.gz')
    with gzip.open(path, 'rt') as stream:
        reader = csv.reader(stream)
        header = next(reader)
        data = np.array(list(reader), dtype=float)
    return {k: data[:, i] for i, k in enumerate(header)}


def finish(fig, name, title):
    fig.suptitle(title + '\nTT | 0.9 V | 27 C | 10 MS/s | Bootstrap transistor-level; CDAC / comparator / SAR behavioral', fontsize=12)
    fig.tight_layout(rect=(0, .015, 1, .93))
    fig.savefig(FIG / (name + '.png'))
    fig.savefig(FIG / (name + '.svg'))
    plt.close(fig)


for name in ['dc', 'startup', 'sine']:
    run = 'manual8-bootshort-' + name + '-v1'
    base = ROOT / 'output/managed_execution/runs' / run / 'collected'
    path = base / 'derived/result.json'
    r = json.loads(path.read_text())
    assert r['native_state']['native_exit'] == 0
    assert r['native_state']['zero_error_footer']
    rows = r['frames']
    cases[name] = r
    k, p = max(r['terminal_pairs'].items(), key=lambda item: item[1]['peak_V'])
    devices = [{'path': dev, 'pair': pair} for dev, pairs in r['device_pairs'].items()
               for pair, key in pairs.items() if key == k]
    summary[name] = {
        'run_id': run, 'source_result_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'native': r['native_state'], 'frames': rows, 'checks': dict(r['checks']),
        'max_held_error_V': maximum(rows, 'held_diff_error_V'),
        'max_preclose_error_V': maximum(rows, 'preclose_diff_error_V'),
        'max_quiet_hold_drift_V': maximum(rows, 'quiet_hold_drift_V'),
        'max_post_step_drift_V': maximum(rows, 'post_input_step_drift_V'),
        'min_precharge_V': min(min(x['precharge_P_V'], x['precharge_N_V']) for x in rows),
        'max_abs_code_delta': maximum(rows, 'code_delta'),
        'worst_terminal': dict(p, devices=devices),
        'power_W': r['power_W'],
        'VDD_plus_clock_W': r['power_W']['vdd'] + r['power_W']['clock']}

sine = cases['sine']['frames']
fitted = fit(sine, 'held_diff_V')
ideal_fit = fit(sine, 'ideal_held_diff_V')
summary['sine']['sine_fit'] = fitted
summary['sine']['ideal_fit'] = ideal_fit
summary['sine']['fit_excluding_first_for_diagnosis'] = fit(sine[1:], 'held_diff_V')
summary['sine']['checks']['sine_residual'] = fitted['residual_peak_V'] <= .25*LSB
summary['sine']['interpretation'] = 'Single-frequency effective lag includes finite tracking bandwidth and turnoff aperture; not proven pure transport delay. Residual removes gain, phase and DC; not uncalibrated ADC error or ENOB.'

# Static errors and cancellation: no conversion redistribution counted as hold error.
rows = cases['dc']['frames']
x = np.arange(len(rows))
fig, ax = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
ax[0].bar(x, [r['held_diff_error_V']*1e3 for r in rows], color='#287c8e', label='Held differential error at close + 1 ns')
for sign in [-1, 1]:
    ax[0].axhline(sign*.25*LSB*1e3, color='#b35d48', ls='--', label='0.25 LSB budget' if sign == 1 else None)
ax[0].set(ylabel='Error (mV)', ylim=(-2, 2))
ax[0].legend(loc='upper right', fontsize=9)
ax[1].plot(x, [r['turnoff_P_change_V']*1e3 for r in rows], 'o-', label='P side')
ax[1].plot(x, [r['turnoff_N_change_V']*1e3 for r in rows], 's-', label='N side')
ax[1].plot(x, [r['turnoff_diff_change_V']*1e3 for r in rows], 'd-', label='P minus N')
ax[1].set(ylabel='Turnoff step (mV)')
ax[1].legend(ncol=3, fontsize=9)
ax[2].step(x, [r['expected_center_code'] for r in rows], where='mid', label='Expected code', color='#9faaaa', lw=3)
ax[2].plot(x, [r['actual_code'] for r in rows], 'o', label='Hybrid output', color='#287c8e')
ax[2].set(ylabel='Output code', xlabel='Frame index (large input steps between samples)', xticks=x, ylim=(-10, 265))
ax[2].legend(fontsize=9)
for a in ax: a.grid(alpha=.2)
finish(fig, '01_static', 'Static acquisition: worst held error 0.434 mV (0.062 LSB); all eight codes match')

# Startup compared at the SAME input on frames 0 and 2, aligned to local time.
w = wave('startup')
time_ns = w['time'] * 1e9
fig, ax = plt.subplots(4, 1, figsize=(11, 10), sharex=True)
for frame, color, label in [(0, '#ba6546', 'First frame after power ramp'), (2, '#287c8e', 'Frame 2, same input, precharged')]:
    local = time_ns - frame*100
    mask = (local >= 0) & (local <= 54)
    t = local[mask]
    if frame == 0:
        ax[0].plot(t, w['vdd'][mask], color='#777777', label='Supply: 0 to 0.9 V in 1 ns')
        ax[0].plot(t, w['clks'][mask], color='#462e80', label='External sampling clock')
    cb = w['xadc.xp.xs.net2']-w['xadc.xp.xs.net3']
    ax[1].plot(t, cb[mask], color=color, label=label)
    vg = w['xadc.xp.xs.net1']-w['inp']
    ax[2].plot(t, vg[mask], color=color, label=label)
    err = w['xadc.topp']-w['xadc.topn']-(w['vinp']-w['vinn'])
    ax[3].plot(t, err[mask]*1e3, color=color, label=label)
ax[0].set(ylabel='Supply / clock (V)')
ax[0].legend(fontsize=9, loc='lower center')
ax[1].axhline(.855, color='#888888', ls='--', label='95% VDD precharge screen')
ax[1].set(ylabel='Cboot P voltage (V)', ylim=(0, 1))
ax[1].legend(fontsize=9, loc='lower right')
ax[1].annotate('0.570 V before first opening', xy=(9.925, .57015), xytext=(18, .35), arrowprops={'arrowstyle':'->'}, fontsize=10)
ax[2].set(ylabel='Main switch P VGS (V)')
ax[3].set(ylabel='Differential error (mV)', xlabel='Time within frame (ns)', ylim=(-1, 12), xlim=(0, 54))
ax[3].axhline(.25*LSB*1e3, color='#888888', ls='--')
ax[3].text(2, 10, 'Large early tracking errors are clipped;\nlate acquisition and held error shown.', fontsize=9)
ax[3].annotate('First held error: 4.573 mV', xy=(50.975, 4.573), xytext=(25, 7), arrowprops={'arrowstyle':'->'}, fontsize=10)
for a in ax:
    a.axvspan(10.025, 49.975, alpha=.05, color='#287c8e')
    a.axvline(49.975, color='#777777', ls=':', lw=1)
    a.grid(alpha=.2)
finish(fig, '02_startup', 'Startup fails the first-frame budget: insufficient precharge reduces tracking drive')
del w

# Sparse high-frequency samples: avoid visually inventing a low-frequency sine.
t = np.array([r['sample_close_s'] for r in sine])
source = np.array([r['input_at_close_V'] for r in sine])
held = np.array([r['held_diff_V'] for r in sine])
fig, ax = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
fine = np.linspace(t[0], t[-1], 1800)
ax[0].plot(fine*1e9, AMP*np.sin(2*np.pi*FREQ*fine), color='#b5bfc2', lw=.9, label='Continuous input')
ax[0].plot(t*1e9, source, 'o', ms=6, mfc='none', color='#58636a', label='Input at clock close')
ax[0].plot(t*1e9, held, '.', ms=6, color='#287c8e', label='Bootstrap held sample')
ax[0].set(ylabel='Differential voltage (V)')
ax[0].legend(ncol=3, fontsize=9, loc='lower center')
ax[1].plot(t*1e9, (held-source)*1e3, 'o-', color='#ba6546', label='Raw error vs external close')
ax[1].plot(t*1e9, (np.array(fitted['fitted_V'])-source)*1e3, '--', color='#287c8e', label='Gain + phase + offset contribution')
for sign in [-1, 1]: ax[1].axhline(sign*.25*LSB*1e3, color='#888888', ls=':', lw=1)
ax[1].set(ylabel='Raw error (mV)')
ax[1].legend(fontsize=9, loc='upper right')
ax[2].plot(t*1e9, np.array(fitted['residual_V'])*1e6, 'o-', color='#287c8e')
ax[2].set(ylabel='Fit residual (uV)', xlabel='Sampling-close time (ns)', ylim=(-30, 30))
ax[2].text(.02, .94, '16 samples only: effective lag 472.4 ps; gain -0.0607%; residual peak 19.08 uV\nRemoving gain / phase / offset is an analysis step, not a circuit correction or ENOB result.', transform=ax[2].transAxes, va='top', fontsize=9)
for a in ax: a.grid(alpha=.2)
finish(fig, '03_sine', '4.501953125 MHz / -1 dBFS: raw error 10.659 mV, dominated by tracking phase lag')

result = {'scope': 'Bootstrap only transistor-level; original topology and dimensions; nominal TT short tests, no PVT/noise/mismatch/PEX',
          'lsb_V': LSB, 'cases': summary,
          'overall_pass': all(all(v['checks'].values()) for v in summary.values()),
          'figures': sorted(p.name for p in FIG.glob('*.png'))}
(OUT / 'results.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
print(json.dumps({k: {'checks': v['checks'], 'max_held_mV': v['max_held_error_V']*1e3} for k,v in summary.items()}, indent=2))
