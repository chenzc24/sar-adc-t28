"""Uniform CDAC reference-switch scaling: SOA, accuracy and ideal-drive load."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np

from common import ROOT, sha
from pn_ratio_results import reference_ports, peak
from uniform_scale_experiment import OUT, SOURCE, SOURCE_CASE, POINTS, FACTORS, load, dump

FIG = ROOT / 'docs/figures/cdac8_uniform_scale'
SOA = .99
ERROR_LIMIT_MV = 1.8 / 256 / 4 * 1000


def current_key(w, request):
    prefix, number = request.lower().split(':')
    for suffix in [number, {'1': 'd', '2': 'g'}[number]]:
        key = prefix + ':' + suffix
        if key in w:
            return key
    raise AssertionError(('Missing current', request, [k for k in w if k.startswith(prefix + ':')]))


def integral_abs(t, values, start=200e-9, stop=300e-9):
    selected = (t > start) & (t < stop)
    tt = np.r_[start, t[selected], stop]
    vv = np.r_[np.interp(start, t, values), values[selected], np.interp(stop, t, values)]
    integrate = np.trapezoid if hasattr(np, 'trapezoid') else np.trapz
    return float(integrate(abs(vv), tt))


def data(name):
    case = load(OUT / f'cases/{name}.json')
    result = load(OUT / f'runs/{name}_result.json')
    assert result['ok'], result['errors']
    deck = OUT / f'decks/{name}.scs'
    assert sha(deck) == case['deck_sha256'] == result['deck_sha256']
    assert sha(SOURCE / f'decks/{SOURCE_CASE}.scs') == case['source_deck_sha256']
    for filename, digest in case['va_sha256'].items():
        assert sha(OUT / 'sources' / filename) == sha(ROOT / 'models/veriloga' / filename) == digest
    raw = load(OUT / f'runs/{name}_waveform.json')
    w = {k: np.asarray(v, dtype=float) for k, v in raw.items() if k != 'units' and isinstance(v, list)}
    t = w['time']
    assert t[-1] >= 300e-9 - 1e-15 and np.all(np.diff(t) > 0)
    assert all(len(v) == len(t) and np.isfinite(v).all() for v in w.values())
    return case, result, deck.read_text(), w


def analyze(name):
    case, result, deck, w = data(name)
    t = w['time']
    ns = t * 1e9
    at = lambda key, instant: float(np.interp(instant, ns, w[key]))
    word = lambda key, instant: sum((at(f'{key}<{b}>', instant) > .45) * (1 << b) for b in range(8))
    gate_error = max(float(np.max(abs(w[f'xcdac.xs{s}{b}.eh_b'] - (w['vdd!'] - w[f'{s}h<{b}>']))))
                     for s in 'pn' for b in range(8))
    gate_error = max(gate_error, max(float(np.max(abs(w[f'xcdac.xs{s}{b}.el_d'] - w[f'{s}l<{b}>'])))
                                     for s in 'pn' for b in range(8)))
    assert gate_error < 1e-10
    masks = dict(all=np.ones_like(t, dtype=bool), post_startup=ns >= 100,
                 sar=(ns % 100 >= 43) & (ns % 100 <= 83),
                 restore=(ns % 100 >= 2.9) & (ns % 100 <= 12))
    worst = {key: dict(value_v=-1) for key in masks}
    envelope = np.zeros_like(t)
    count = 0
    for instance, ports in reference_ports(deck, w):
        count += 1
        for terminal, values in ports.items():
            envelope = np.maximum(envelope, abs(values))
            for key, mask in masks.items():
                candidate = peak(ns, values, mask)
                if candidate['value_v'] > worst[key]['value_v']:
                    worst[key] = dict(**candidate, instance=instance, terminal=terminal)
    assert count == 32
    log = (Path(result['metadata']['output_dir']).parent / 'spectre.out').read_text(errors='replace')
    cmi = re.findall(r'WARNING \(CMI-(\d+)\):.*', log)
    limits = sorted(set(re.findall(r'(v\w+_max)\(=([\d.]+) mV\)', log)))
    assert not re.search(r'(?i)(?:cannot|unable|could not) (?:find|save).*XCDAC', log)
    comparisons = []
    for j in range(8):
        instant = 245.9 + 5 * j
        active = word('nh', instant)
        ideal = case['vdiff_v'] + .9 - active * 1.8 / 256
        actual = at('topp', instant) - at('topn', instant)
        comparisons.append(dict(time_ns=instant, active_code=active, error_mv=(actual - ideal) * 1000,
                                cm_v=(at('topp', instant) + at('topn', instant)) / 2))
    gate_charge = dict(p=0., n=0.)
    gate_sum_current = np.zeros_like(t)
    gate_peak = dict(abs_ma=-1)
    cycle = (ns >= 200) & (ns <= 300)
    current_keys = []
    for request in case['gate_current_saves']:
        key = current_key(w, request)
        current_keys.append(key)
        polarity = 'p' if '.mp_high:' in key else 'n'
        gate_charge[polarity] += integral_abs(t, w[key]) * 1e12
        gate_sum_current += abs(w[key])
        indices = np.flatnonzero(cycle)
        j = indices[np.argmax(abs(w[key][indices]))]
        if abs(w[key][j]) * 1000 > gate_peak['abs_ma']:
            gate_peak = dict(abs_ma=float(abs(w[key][j]) * 1000), time_ns=float(ns[j]), current=key)
    for request in case['drain_current_saves']:
        current_keys.append(current_key(w, request))
    assert len(current_keys) == len(set(current_keys)) == 44
    reference = {}
    for label, key, nominal, source in [('high', 'vrefp', .9, 'vrefhigh:p'),
                                        ('low', 'vrefn', 0., 'vreflow:p')]:
        deviation = w[key] - nominal
        p = peak(ns, deviation, masks['post_startup'])
        source_peak = peak(ns, w[source], masks['post_startup'])
        reference[label] = dict(max_deviation_mv=p['value_v'] * 1000,
                                signed_deviation_mv=p['signed_v'] * 1000,
                                deviation_time_ns=p['time_ns'],
                                source_peak_ma=source_peak['value_v'] * 1000,
                                source_charge_abs_pc=integral_abs(t, w[source]) * 1e12)
    error = max(abs(c['error_mv']) for c in comparisons)
    code = int(word('dout', 293))
    row = dict(name=name, point=case['point'], factor=case['factor'], vdiff_v=case['vdiff_v'],
               maxstep_s=case['maxstep_s'], result_ok=True, code=code, expected_code=case['expected_code'],
               code_pass=code == case['expected_code'], compare_max_error_mv=error,
               residual_pass=error < ERROR_LIMIT_MV, comparisons=comparisons,
               acquisition_error_mv=(at('topp', 240.9) - at('topn', 240.9) - case['vdiff_v']) * 1000,
               stress=worst, soa_screen_pass=worst['all']['value_v'] <= SOA,
               printed_cmi=len(cmi), printed_cmi_types=sorted(set(cmi)), logged_model_limits_mv=limits,
               suppressed_warnings=sum(map(int, re.findall(r'(\d+) warnings suppressed', log))),
               lte_relaxations=log.count('WARNING (SPECTRE-16780)'), native_reference_mos_count=count,
               ideal_gate_max_error_v=gate_error, gate_current_count=32, drain_current_count=12,
               gate_abs_charge_pc=gate_charge['p'] + gate_charge['n'], gate_charge_by_polarity_pc=gate_charge,
               gate_peak=gate_peak, gate_sum_current_peak_ma=float(np.max(gate_sum_current[cycle]) * 1000),
               gate_charge_interval_ns=[200, 300], reference=reference,
               reference_max_deviation_mv=max(v['max_deviation_mv'] for v in reference.values()),
               reference_source_peak_ma=max(v['source_peak_ma'] for v in reference.values()),
               deck_sha256=case['deck_sha256'], source_deck_sha256=case['source_deck_sha256'],
               va_sha256=case['va_sha256'], waveform_sha256=sha(OUT / f'runs/{name}_waveform.json'))
    row['bounded_pass'] = row['code_pass'] and row['residual_pass'] and row['soa_screen_pass'] and not row['printed_cmi'] and not row['lte_relaxations']
    dump(f'metrics/{name}.json', row)
    return row, w, envelope


def figures(rows):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'Microsoft YaHei', 'font.size': 11, 'axes.unicode_minus': False})
    order = ['nfull', 'nhalf', 'phalf', 'control', 'pfull']
    labels = ['−0.8 V', '−0.5 LSB', '+0.5 LSB', '+453.5 mV', '+0.8 V']
    lookup = {(r['point'], r['factor']): r for r in rows if not r['name'].endswith('_fine')}
    if not all((point, factor) in lookup for point in order for factor in FACTORS):
        return
    x = np.arange(5)
    colors = ['#555555', '#d95f02', '#1b9e77']
    markers = ['o', 's', '^']
    fig, axes = plt.subplots(4, 1, figsize=(11, 10), sharex=True)
    measures = ['port', 'compare_max_error_mv', 'reference_max_deviation_mv', 'gate_abs_charge_pc']
    for factor, color, marker in zip(FACTORS, colors, markers, strict=True):
        group = [lookup[point, factor] for point in order]
        for axis, measure in zip(axes, measures, strict=True):
            values = [r['stress']['all']['value_v'] if measure == 'port' else r[measure] for r in group]
            axis.plot(x, values, marker=marker, color=color, lw=1.6, label=f'P/N 同增 {factor}×')
    axes[0].axhline(SOA, color='#b2182b', ls='--', lw=1.2, label='模型 SOA 0.99 V')
    axes[1].axhline(ERROR_LIMIT_MV, color='#b2182b', ls='--', lw=1.2, label='0.25 LSB 预算')
    for axis, label in zip(axes, ['最坏端口 (V)', '比较前误差 (mV)', '参考轨最大扰动 (mV)', '绝对栅电荷 / 周期 (pC)'], strict=True):
        axis.set_ylabel(label)
        axis.grid(alpha=.2)
    axes[0].legend(loc='best', fontsize=9, ncol=2)
    axes[1].legend(loc='best', fontsize=9)
    axes[-1].set_xticks(x, labels)
    axes[-1].set_xlabel('输入测试点（横轴为类别，非等间隔电压）')
    fig.suptitle('参考开关等比例扩大：TT / 0.9 V / 27°C', fontsize=14)
    fig.tight_layout()
    fig.savefig(FIG / 'scale_summary.png', dpi=160, bbox_inches='tight')
    plt.close(fig)
    # Equal input, equal phase and common limits: zoom on the largest 2x case.
    selected = max((lookup[p, 2] for p in order), key=lambda r: r['stress']['all']['value_v'])
    point = selected['point']
    center = selected['stress']['all']['time_ns']
    frame = np.floor(center / 100) * 100
    restoring = 2.9 <= center % 100 <= 12
    command = frame + 3.01 if restoring else frame + 47.51 + 5 * np.floor((center % 100 - 47.51) / 5)
    fig, axes = plt.subplots(3, 1, figsize=(11, 7.5), sharex=True)
    for factor, color, marker in zip(FACTORS, colors, markers, strict=True):
        row = lookup[point, factor]
        _, w, envelope = analyze(row['name'])
        ns = w['time'] * 1e9
        mask = (ns >= center - .15) & (ns <= center + .35)
        axes[0].plot(ns[mask], envelope[mask], color=color, lw=1.8, label=f'P/N 同增 {factor}×')
        axes[1].plot(ns[mask], (w['vrefp'][mask] - .9) * 1000, color=color, lw=1.8)
        axes[2].plot(ns[mask], w['vrefn'][mask] * 1000, color=color, lw=1.8)
    axes[0].axhline(SOA, color='#b2182b', ls='--', lw=1.2, label='模型 SOA 0.99 V')
    for axis, label in zip(axes, ['参考 MOS 最坏端口 (V)', 'VREFP − 0.9 V (mV)', 'VREFN − 0 V (mV)'], strict=True):
        axis.set_ylabel(label)
        axis.grid(alpha=.2)
        axis.axvspan(command, command + .1, color='.5', alpha=.10)
        for instant in [command, command + .1]:
            axis.axvline(instant, color='.5', ls=':', lw=1)
    for axis in axes[1:]:
        axis.axhline(0, color='.3', ls='--', lw=1)
    axes[0].legend(loc='best', fontsize=9, ncol=2)
    axes[-1].set_xlim(center - .15, center + .35)
    axes[-1].set_xlabel('Time (ns)')
    phase = '下一采样内参考恢复' if restoring else 'SAR 换轨'
    fig.suptitle(f"{phase}｜差分输入 {selected['vdiff_v'] * 1000:+.3f} mV", fontsize=14)
    fig.tight_layout()
    fig.savefig(FIG / 'scale_timing.png', dpi=160, bbox_inches='tight')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--names', nargs='+')
    parser.add_argument('--no-plot', action='store_true')
    args = parser.parse_args()
    names = args.names or [p.stem.removesuffix('_result') for p in sorted((OUT / 'runs').glob('*_result.json'))]
    rows = []
    for name in names:
        row, _, _ = analyze(name)
        rows.append(row)
        print(json.dumps(dict(name=name, code=row['code'], expected=row['expected_code'],
                              max_port=row['stress']['all'], error_mv=row['compare_max_error_mv'],
                              cmi=row['printed_cmi'], reference_mv=row['reference_max_deviation_mv'],
                              gate_pc=row['gate_abs_charge_pc'])), flush=True)
    summary = dict(scope='five static TT inputs; ideal-gate native CDAC diagnostic, not full ADC/reliability qualification',
                   conditions=dict(vdd_v=.9, corner='tt', temperature_c=27, stop_ns=300, edge_ps=20,
                                   dead_time_ps=100, physical_transient_noise=False),
                   soa_warning_v=SOA, deterministic_limit_mv=ERROR_LIMIT_MV, cases=rows, grouped={})
    for factor in FACTORS:
        group = [r for r in rows if r['factor'] == factor and not r['name'].endswith('_fine')]
        if group:
            worst = max(group, key=lambda r: r['stress']['all']['value_v'])
            summary['grouped'][str(factor)] = dict(points=len(group), bounded_passes=sum(r['bounded_pass'] for r in group),
                worst_port_v=worst['stress']['all']['value_v'], worst_case=worst['name'],
                max_error_mv=max(r['compare_max_error_mv'] for r in group),
                max_reference_deviation_mv=max(r['reference_max_deviation_mv'] for r in group),
                max_gate_abs_charge_pc=max(r['gate_abs_charge_pc'] for r in group),
                max_reference_source_peak_ma=max(r['reference_source_peak_ma'] for r in group))
    for name, previous in [('nhalf_m2', 'neg_p2n2'), ('control_m2', 'pos_p2n2')]:
        matches = [r for r in rows if r['name'] == name]
        if matches:
            old = load(SOURCE / f'metrics/{previous}.json')
            delta = (matches[0]['stress']['all']['value_v'] - old['stress']['all']['value_v']) * 1e6
            assert abs(delta) < 100, (name, delta)
            summary.setdefault('retained_replay_checks', {})[name] = dict(port_delta_uv=delta)
    lookup = {r['name']: r for r in rows}
    for row in rows:
        parent = row['name'].removesuffix('_fine')
        if row['name'].endswith('_fine') and parent in lookup:
            previous = lookup[parent]
            summary.setdefault('fine_checks', {})[row['name']] = dict(
                port_delta_uv=(row['stress']['all']['value_v'] - previous['stress']['all']['value_v']) * 1e6,
                error_delta_uv=(row['compare_max_error_mv'] - previous['compare_max_error_mv']) * 1000,
                gate_charge_relative_delta=row['gate_abs_charge_pc'] / previous['gate_abs_charge_pc'] - 1)
    FIG.mkdir(parents=True, exist_ok=True)
    (FIG / 'metrics.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    if not args.no_plot:
        figures(rows)


if __name__ == '__main__':
    main()
