"""Whole-capture coherent FFT, affine/phase diagnostics and review figures."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import pickle
import shutil
import sys
import numpy as np

import b_dynamic_512 as flow

Q = 1.8 / 256
sys.path.insert(0, str(flow.ROOT.parent.parent / 'ADCToolbox/python/src'))


def spectrum(x, fs, k):
    x = np.asarray(x, float)
    n = len(x)
    power = abs(np.fft.rfft(x - x.mean()) / n)**2
    power[1:-1] *= 2
    signal = power[k]
    other = power.copy(); other[[0, k]] = 0
    nd = float(other.sum())
    largest = int(np.argmax(other))
    harmonic_bins = sorted({min((h * k) % n, n - (h * k) % n) for h in range(2, 11)} - {0, k})
    distortion = float(power[harmonic_bins].sum())
    sndr = float(10 * np.log10(signal / max(nd, 1e-300)))
    return dict(sndr_db=sndr, enob_bits=(sndr - 1.76) / 6.02,
        sfdr_dbc=float(10 * np.log10(signal / max(float(other[largest]), 1e-300))),
        snr_excluding_h2_h10_db=float(10 * np.log10(signal / max(nd - distortion, 1e-300))),
        thd_h2_h10_dbc=float(10 * np.log10(max(distortion, 1e-300) / signal)),
        fundamental_bin=int(k), dominant_bin=int(np.argmax(power[1:]) + 1), largest_spur_bin=largest,
        largest_spur_hz=largest * fs / n, harmonic_bins=harmonic_bins,
        power_spectrum_v2=list(map(float, power)), frequency_hz=list(map(float, np.fft.rfftfreq(n, 1 / fs))),
        window='rectangular_coherent_no_harmonic_removal', one_sided_Nyquist_weight=1,
        enob_amplitude_compensation_applied=False)


def fit_transfer(values, sample_ns, cfg, peak):
    phase = 2 * np.pi * cfg['input_frequency_hz'] * np.asarray(sample_ns) * 1e-9 - .4 * np.pi
    basis = np.column_stack((np.sin(phase), np.cos(phase), np.ones(len(phase))))
    coefs = np.linalg.lstsq(basis, values, rcond=None)[0]
    fitted = basis @ coefs
    residue = values - fitted
    gain = float(np.hypot(coefs[0], coefs[1]) / peak)
    return dict(gain=gain, gain_error_percent=(gain - 1) * 100, dc_v=float(coefs[2]),
        equivalent_delay_ns=float(-np.arctan2(coefs[1], coefs[0]) / (2 * np.pi * cfg['input_frequency_hz']) * 1e9),
        nonfundamental_rms_v=float(np.sqrt(np.mean(residue**2))), nonfundamental_peak_v=float(max(abs(residue))),
        gain_endpoint_error_lsb=abs(gain - 1) * .9 / Q,
        fitted_v=list(map(float, fitted)), residue_v=list(map(float, residue)))


def self_check():
    from adctoolbox.spectrum.quick_sndr import quick_sndr
    n, k, fs = 512, 231, 10e6
    t = np.arange(n) / fs
    peak = .9 * 10**(-1 / 20)
    analog = peak * np.sin(2 * np.pi * k / n * np.arange(n) + .123)
    codes = np.clip(np.floor((analog + .9) / Q), 0, 255)
    x = (codes + .5) * Q - .9
    our = spectrum(x, fs, k)
    lib = quick_sndr(x, fs=fs, win_type='rectangular', side_bin=0, max_scale_range=.9)
    assert abs(our['sndr_db'] - lib['sndr_dbc']) < 1e-8 and abs(our['enob_bits'] - lib['enob']) < 1e-8
    assert 47 < our['sndr_db'] < 51 and our['dominant_bin'] == k
    pure = .7 * np.sin(2 * np.pi * k / n * np.arange(n)) + .001 * np.sin(2 * np.pi * (2 * k) / n * np.arange(n)) + .12
    m = spectrum(pure, fs, k)
    expected = 20 * np.log10(.7 / .001)
    assert abs(m['sndr_db'] - expected) < 1e-8 and abs(m['sfdr_dbc'] - expected) < 1e-8
    assert m['largest_spur_bin'] == 50 and 50 in m['harmonic_bins']
    cfg = dict(input_frequency_hz=fs * k / n)
    ns = t * 1e9
    actual = peak * .998 * np.sin(2 * np.pi * cfg['input_frequency_hz'] * (t - 1.78e-9) - .4 * np.pi) + .0002
    fit = fit_transfer(actual, ns, cfg, peak)
    assert abs(fit['gain'] - .998) < 1e-12 and abs(fit['equivalent_delay_ns'] - 1.78) < 1e-10
    assert abs(fit['dc_v'] - .0002) < 1e-12 and fit['nonfundamental_rms_v'] < 1e-12
    nyquist = pure + .002 * (-1.)**np.arange(n)
    mm = spectrum(nyquist, fs, k)
    assert abs(mm['power_spectrum_v2'][-1] - .002**2) < 1e-15
    print('COHERENT_512_FFT_ADCTOOLBOX_DC_GAIN_DELAY_HARMONIC_NYQUIST_SELF_CHECK_PASS')


def plots(r, cfg, fft, held_fit, output_fit):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    folder = flow.OUT / 'figures'; folder.mkdir(exist_ok=True)
    rows = r['frames'][4:]
    sample = np.array([f['sample_ns'] for f in rows])
    actual = np.array([f['decoded_midbin_v'] for f in rows])
    source = np.array([f['source_v'] for f in rows])
    show = slice(0, 24)
    fig, ax = plt.subplots(2, 1, figsize=(11.5, 6.5))
    ax[0].plot(sample[show], source[show], 'kx-', ms=4, label='Ideal input at SAMPLE fall')
    ax[0].step(sample[show], actual[show], where='post', label='Decoded code; sample-aligned ZOH')
    ax[0].set_ylabel('Differential (V)'); ax[0].set_xlabel('Sample time (ns)')
    ax[0].legend(fontsize=8); ax[0].grid(alpha=.25)
    ax[1].plot(sample, np.asarray(held_fit['residue_v']) * 1e3, label='Held: DC/fundamental removed')
    ax[1].plot(sample, np.asarray(output_fit['residue_v']) * 1e3, alpha=.65, label='Decoded code: includes quantization')
    ax[1].set_xlabel('Sample time (ns)'); ax[1].set_ylabel('Nonfundamental residual (mV)')
    ax[1].legend(fontsize=8); ax[1].grid(alpha=.25)
    fig.suptitle('B / 1x / 512 observed points; read at frame +98 ns, shown sample-aligned')
    fig.tight_layout(); fig.savefig(folder / 'dynamic_time.png', dpi=160); plt.close(fig)
    fig, ax = plt.subplots(figsize=(11.5, 4.6))
    p = np.asarray(fft['power_spectrum_v2'])
    db = 10 * np.log10(np.maximum(p, 1e-30) / p[cfg['coherent_bin']])
    ax.plot(np.asarray(fft['frequency_hz']) / 1e6, db, lw=.9, label='Actual final codes; coherent rectangular FFT')
    ax.plot([cfg['input_frequency_hz'] / 1e6], [0], 'o', label='Fundamental')
    bins = fft['harmonic_bins']
    ax.plot(np.asarray(fft['frequency_hz'])[bins] / 1e6, db[bins], 'x', label='Aliased H2-H10 bins')
    ax.set(xlabel='Frequency (MHz)', ylabel='Power (dBc)', xlim=(0, 5), ylim=(-110, 5))
    ax.legend(fontsize=8); ax.grid(alpha=.25)
    ax.set_title(f"SNDR {fft['sndr_db']:.2f} dB | ENOB {fft['enob_bits']:.3f} bit | SFDR {fft['sfdr_dbc']:.2f} dBc")
    fig.tight_layout(); fig.savefig(folder / 'dynamic_spectrum.png', dpi=160); plt.close(fig)
    with (flow.OUT / 'detail_slowest.pickle').open('rb') as stream: detail = pickle.load(stream)
    w, frame = detail['wave'], detail['frame']
    ts = np.asarray(w['time']) * 1e9 - 100 * frame
    valid = (ts >= 39.7) & (ts <= 90)
    fig, ax = plt.subplots(3, 1, figsize=(11.5, 7), sharex=True)
    ax[0].plot(ts[valid], w['sample'][valid], label='SAMPLE')
    ax[0].plot(ts[valid], w['cmp_clk'][valid], label='CMP_CLK')
    ax[0].legend(fontsize=8); ax[0].set_ylabel('Clock (V)')
    actual_diff = w['topp'] - w['topn']
    ax[1].plot(ts[valid], actual_diff[valid], label='Actual TOPP-TOPN')
    hold = r['frames'][frame]['held_v']
    ideal_times = [39.7]; ideal_values = [hold]
    for comparison in r['frames'][frame]['comparisons']:
        ideal_times.append(comparison['compare_ns'] - 100 * frame)
        ideal_values.append(hold + .9 - comparison['trial'] * Q)
    ax[1].plot(ideal_times[1:], ideal_values[1:], 'kx', label='Ideal trial at each compare; based on actual held value')
    ax[1].set_ylabel('CDAC residual (V)'); ax[1].legend(fontsize=8)
    codes = sum((w['d' + str(b)] > .45).astype(int) * (1 << b) for b in range(8))
    ax[2].plot(ts[valid], codes[valid], label='Native SAR register (not an output bank)')
    ax[2].axhline(r['frames'][frame]['code'], color='#555', ls='--', label='Final code')
    ax[2].set_ylabel('Code'); ax[2].set_xlabel('Frame-relative time (ns)'); ax[2].legend(fontsize=8)
    for a in ax:
        a.axvline(41.05, ls=':', color='#777'); a.grid(alpha=.2)
    fig.suptitle(f'Longest conversion observed: frame {frame + 1}; same B/1x circuit and timing')
    fig.tight_layout(); fig.savefig(folder / 'dynamic_frame.png', dpi=160); plt.close(fig)


def analyze(curate=False):
    from adctoolbox.spectrum.quick_sndr import quick_sndr
    flow.check()
    ctx = flow.read(flow.OUT / 'context.json'); cfg = ctx['config']
    reduced = flow.read(flow.OUT / 'reduced.json')
    rows = reduced['frames'][4:]
    assert len(rows) == 512 and [r['frame'] for r in rows] == list(range(4, 516))
    ts = np.array([f['sample_ns'] for f in rows]); np.testing.assert_allclose(np.diff(ts), 100, rtol=0, atol=1e-5)
    codes = np.array([f['code'] for f in rows])
    actual = (codes + .5) * Q - .9
    fft = spectrum(actual, cfg['sample_rate_hz'], cfg['coherent_bin'])
    cross = quick_sndr(actual, fs=cfg['sample_rate_hz'], win_type='rectangular', side_bin=0, max_scale_range=.9)
    assert abs(fft['sndr_db'] - cross['sndr_dbc']) < 1e-8 and abs(fft['enob_bits'] - cross['enob']) < 1e-8
    peak = ctx['differential_peak_v']
    held_fit = fit_transfer(np.array([r['held_v'] for r in rows]), ts, cfg, peak)
    output_fit = fit_transfer(actual, ts, cfg, peak)
    common = peak * np.sin(2 * np.pi * cfg['input_frequency_hz'] * (ts - cfg['sampling_common_delay_ns']) * 1e-9 - .4 * np.pi)
    joint = np.array([r['held_v'] for r in rows]) - common
    failures = dict(functional_frames=[r['frame'] for r in reduced['frames'] if not r['functional_pass']],
        gross_code_vs_held_frames=[r['frame'] for r in rows if abs(r['code_minus_held_ideal']) > 1],
        cdac_settling_frames=[r['frame'] for r in rows if r['precompare_settling_vs_held_peak_lsb'] > .25],
        terminal_devices=[r['path'] for r in reduced['stress'] if not r['screen_pass']],
        phase_restore_count=reduced['phase_events'] != 516 * 32 or reduced['restore_events'] != 516 * 16,
        CMI=reduced['has_CMI'], LTE=reduced['has_LTE'], wrong_fundamental=fft['dominant_bin'] != cfg['coherent_bin'])
    timing_pass = not any(failures.values())
    performance_pass = fft['sndr_db'] >= cfg['sndr_target_db'] and fft['enob_bits'] >= cfg['enob_target_bits']
    plots(reduced, cfg, fft, held_fit, output_fit)
    result = dict(config=cfg, coherent_fft=fft, adctoolbox_crosscheck=cross,
        held_transfer=held_fit, decoded_output_transfer=output_fit,
        common_low_frequency_delay_ns=cfg['sampling_common_delay_ns'],
        joint_held_minus_fixed_delay_peak_lsb=float(max(abs(joint)) / Q),
        raw_held_error_peak_mv=max(abs(r['raw_held_error_mv']) for r in rows),
        failures=failures, functional_timing_voltage_screen_pass=timing_pass,
        nominal_deterministic_dynamic_target_pass=performance_pass,
        qualified_full_ADC=False, physical_total_power_qualified=False,
        report_scope='one_TT_coherent_512_point_capture_no_noise_mismatch_PVT_fullcode',
        native_result_ok=reduced['native_result_ok'], native_footer=reduced['native_footer'],
        native_warnings=reduced['native_warnings'], initial_DC_notices=reduced['initial_DC_notices'],
        frames=reduced['frames'], power=reduced['power'], stress=reduced['stress'], current_stats=reduced['current_stats'],
        phase_events=reduced['phase_events'], restore_events=reduced['restore_events'], points=reduced['points'],
        reported_solver_parameters=reduced['reported_solver_parameters'], raw_sha256=reduced['raw_sha256'],
        gzip_sha256=reduced['gzip_sha256'], full_continuous_data_retained=True,
        context_sha256=flow.sha(flow.OUT / 'context.json'), config_sha256=flow.sha(flow.CFG),
        input_deck_sha256=ctx['deck_sha256'], include_sha256={Path(p).name: h for p, h in ctx['include_sha256'].items()},
        reducer_LF_sha256=reduced['reducer_LF_sha256'],
        analysis_LF_sha256=hashlib.sha256(Path(__file__).read_text(encoding='utf-8').encode()).hexdigest(),
        figure_sha256={p.name: flow.sha(p) for p in (flow.OUT / 'figures').glob('*.png')},
        figures_visually_reviewed=curate)
    flow.dump(flow.OUT / 'summary.json', result)
    if curate:
        flow.dump(flow.ROOT / 'verification/integration/b_dynamic_512_results.json', result)
        dest = flow.ROOT / 'docs/figures/b_dynamic_512'; dest.mkdir(parents=True, exist_ok=True)
        for p in (flow.OUT / 'figures').glob('*.png'): shutil.copyfile(p, dest / p.name)
    print('DYNAMIC512_RESULTS', fft['sndr_db'], fft['enob_bits'], fft['sfdr_dbc'], 'functional=', timing_pass, 'dynamic=', performance_pass)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--self-check', action='store_true'); ap.add_argument('--curate', action='store_true')
    args = ap.parse_args()
    self_check() if args.self_check else analyze(args.curate)
