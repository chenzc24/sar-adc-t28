"""Audit native P/N factorial evidence and draw common-scale transient comparisons."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np

from analyze import instances
from common import ROOT, sha
from pn_ratio_experiment import OUT, SOURCE, load, dump
from run import blocks

FIG = ROOT / 'docs/figures/cdac8_pn_ratio'
LIMIT = 1.8 / 256 / 4
SOA = .99


def peak(ns, values, mask):
    indices = np.flatnonzero(mask)
    j = indices[np.argmax(np.abs(values[indices]))]
    return dict(value_v=float(abs(values[j])), signed_v=float(values[j]), time_ns=float(ns[j]))


def crossing(ns, values, start, stop, direction, level=.45):
    mask = (ns[:-1] >= start) & (ns[1:] <= stop)
    mask &= ((values[:-1] < level) & (values[1:] >= level) if direction > 0
             else (values[:-1] > level) & (values[1:] <= level))
    indices = np.flatnonzero(mask)
    if not len(indices):
        return None
    j = indices[0]
    return float(ns[j] + (level - values[j]) / (values[j + 1] - values[j]) * (ns[j + 1] - ns[j]))


def reference_ports(deck, w):
    sub = blocks(deck)
    array_nodes, master = instances(deck)['XCDAC']
    array = sub[master]
    ports = array.replace('\\\n', ' ').splitlines()[0].split()[2:]
    parent = dict(zip(ports, array_nodes, strict=True))
    zero = np.zeros_like(w['time'])

    def voltage(node):
        key = node.lower().replace('\\', '')
        return zero if key == '0' else w[key]

    for leaf, (nodes, master) in instances(array).items():
        if not leaf.startswith('XS'):
            continue
        block = sub[master]
        ports = block.replace('\\\n', ' ').splitlines()[0].split()[2:]
        mapping = dict(zip(ports, nodes, strict=True))

        def resolve(node):
            if node in mapping:
                port = mapping[node]
                return parent.get(port, 'XCDAC.' + port)
            return f'XCDAC.{leaf}.{node}'

        for device, (nodes, model) in instances(block).items():
            if model not in ['nch_mac', 'pch_mac']:
                continue
            d, g, s, b = [voltage(resolve(node)) for node in nodes]
            yield f'XCDAC.{leaf}.{device}', dict(vds=d-s, vgs=g-s, vgd=g-d, vbs=b-s, vbd=b-d)


def analyze(name):
    case = load(OUT / f'cases/{name}.json')
    result = load(OUT / f'runs/{name}_result.json')
    assert result['ok'], result['errors']
    deck_path = OUT / f'decks/{name}.scs'
    assert sha(deck_path) == case['deck_sha256'] == result['deck_sha256']
    assert sha(SOURCE / f"decks/{case['source_case']}.scs") == case['source_deck_sha256']
    for filename, digest in case['va_sha256'].items():
        assert sha(OUT / 'sources' / filename) == sha(ROOT / 'models/veriloga' / filename) == digest
    raw = load(OUT / f'runs/{name}_waveform.json')
    w = {k: np.asarray(v, dtype=float) for k, v in raw.items() if k != 'units' and isinstance(v, list)}
    ns = w['time'] * 1e9
    assert np.all(np.diff(ns) > 0) and ns[-1] >= 300 - 1e-6
    assert all(len(v) == len(ns) and np.isfinite(v).all() for v in w.values())
    at = lambda key, t: float(np.interp(t, ns, w[key]))
    word = lambda key, t: sum((at(f'{key}<{b}>', t) > .45) * (1 << b) for b in range(8))
    comparisons = []
    for j in range(8):
        t = 245.9 + 5 * j
        active = word('nh', t)
        ideal = case['vdiff_v'] + .9 - active * 1.8 / 256
        error = at('topp', t) - at('topn', t) - ideal
        comparisons.append(dict(time_ns=t, active_code=active, error_mv=error * 1000))
    gate_error = max(float(np.max(abs(w[f'xcdac.xs{s}{b}.eh_b'] - (w['vdd!'] - w[f'{s}h<{b}>']))))
                     for s in 'pn' for b in range(8))
    gate_error = max(gate_error, max(float(np.max(abs(w[f'xcdac.xs{s}{b}.el_d'] - w[f'{s}l<{b}>'])))
                                     for s in 'pn' for b in range(8)))
    assert gate_error < 1e-10
    masks = dict(all=np.ones_like(ns, dtype=bool), post_startup=ns >= 100,
                 sar=(ns % 100 >= 43) & (ns % 100 <= 83),
                 restore=(ns % 100 >= 2.9) & (ns % 100 <= 12))
    worst = {key: dict(value_v=-1) for key in masks}
    side_sar = {side: dict(value_v=-1) for side in 'pn'}
    envelope = np.zeros_like(ns)
    count = 0
    for instance, ports in reference_ports(deck_path.read_text(), w):
        count += 1
        for terminal, values in ports.items():
            envelope = np.maximum(envelope, abs(values))
            for key, mask in masks.items():
                candidate = peak(ns, values, mask)
                if candidate['value_v'] > worst[key]['value_v']:
                    worst[key] = dict(**candidate, instance=instance, terminal=terminal)
            side = 'n' if instance.startswith('XCDAC.XSN') else 'p'
            candidate = peak(ns, values, masks['sar'])
            if candidate['value_v'] > side_sar[side]['value_v']:
                side_sar[side] = dict(**candidate, instance=instance, terminal=terminal)
    assert count == 32
    log = (Path(result['metadata']['output_dir']).parent / 'spectre.out').read_text(errors='replace')
    printed_cmi = re.findall(r'WARNING \(CMI-(\d+)\):.*', log)
    actual_limits = sorted(set(re.findall(r'(v\w+_max)\(=([\d.]+) mV\)', log)))
    # No relaxed LTE or missing-observation/save warnings may be hidden in an accepted result.
    assert 'WARNING (SPECTRE-16780)' not in log
    assert not re.search(r'(?i)(?:cannot|unable|could not) (?:find|save).*XCDAC', log)
    expected = int(np.clip(np.floor((case['vdiff_v'] + .9) / (1.8 / 256)), 0, 255))
    sar = (ns >= 47.5) & (ns <= 47.85)
    restore = (ns >= 203) & (ns <= 204)
    bottoms = {}
    for s in 'pn':
        for b in range(8):
            key = f'xcdac.b{s}{b}'
            indices = np.flatnonzero(sar)
            low = indices[np.argmin(w[key][indices])]
            high = indices[np.argmax(w[key][indices])]
            bottoms[f'B{s.upper()}{b}'] = dict(min_v=float(w[key][low]), min_ns=float(ns[low]),
                                               max_v=float(w[key][high]), max_ns=float(ns[high]))
    current_keys = {}
    currents = {}
    for requested in case['current_saves']:
        prefix = requested.lower().split(':')[0]
        options = [key for key in w if key.startswith(prefix + ':')]
        assert len(options) == 1, (requested, options, [k for k in w if ':' in k])
        key = options[0]
        current_keys[prefix] = key
        indices = np.flatnonzero(sar)
        j = indices[np.argmax(abs(w[key][indices]))]
        currents[prefix] = dict(max_abs_ma=float(abs(w[key][j]) * 1000),
                                signed_ma=float(w[key][j] * 1000), time_ns=float(ns[j]))
    bn5_min = bottoms['BN5']['min_ns']
    row = dict(name=name, p_multiplier=case['p_multiplier'], n_multiplier=case['n_multiplier'],
               vdiff_v=case['vdiff_v'], code=int(word('dout', 293)), expected_code=expected,
               compare_max_error_mv=max(abs(c['error_mv']) for c in comparisons), comparisons=comparisons,
               stress=worst, side_sar=side_sar, soa_screen_pass=worst['all']['value_v'] <= SOA,
               printed_cmi=len(printed_cmi), printed_cmi_types=sorted(set(printed_cmi)),
               logged_model_limits_mv=actual_limits,
               suppressed_warnings=sum(map(int, re.findall(r'(\d+) warnings suppressed', log))),
               lte_relaxations=log.count('WARNING (SPECTRE-16780)'), result_ok=True,
               native_reference_mos_count=count, ideal_gate_max_error_v=gate_error,
               source_case=case['source_case'], source_deck_sha256=case['source_deck_sha256'],
               deck_sha256=case['deck_sha256'], va_sha256=case['va_sha256'],
               waveform_sha256=sha(OUT / f'runs/{name}_waveform.json'),
               maxstep_s=case['maxstep_s'], bottoms_first_sar=bottoms,
               bn7_fall_half_ns=crossing(ns, w['xcdac.bn7'], 47.61, 48, -1),
               bn6_rise_half_ns=crossing(ns, w['xcdac.bn6'], 47.61, 48, 1),
               currents_first_sar=currents, current_keys=current_keys,
               bn5_min_snapshot={key: at(key, bn5_min) for key in
                                ['topp', 'topn', 'vrefp', 'vrefn', 'xcdac.bn5',
                                 'xcdac.xsn5.eh_b', 'xcdac.xsn5.el_d', *current_keys.values()]},
               restore_bn5_peak_v=float(np.max(w['xcdac.bn5'][restore])),
               restore_words=[word('nh', 202.99), word('nh', 203.3)])
    row['code_pass'] = row['code'] == expected
    row['residual_pass'] = row['compare_max_error_mv'] < LIMIT * 1000
    if case['vdiff_v'] < 0:
        assert max(abs(w['xcdac.xsn5.eh_b'][sar] - .9)) < 1e-10
        assert max(abs(w['xcdac.xsn5.el_d'][sar] - .9)) < 1e-10
    dump(f'metrics/{name}.json', row)
    return row, w, envelope


def plot(results):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'Microsoft YaHei', 'font.size': 11, 'axes.unicode_minus': False})
    names = ['neg_p1n1', 'neg_p2n1', 'neg_p1n2', 'neg_p2n2']
    colors = ['#555555', '#d95f02', '#1b9e77', '#7570b3']
    styles = ['-', '--', '-.', ':']
    fig, axes = plt.subplots(5, 1, figsize=(11, 12.5), sharex=True)
    for name, color, style in zip(names, colors, styles, strict=True):
        row, w, envelope = results[name]
        ns = w['time'] * 1e9
        mask = (ns >= 47.60) & (ns <= 47.72)
        label = f"P×{row['p_multiplier']} / N×{row['n_multiplier']}"
        axes[0].plot(ns[mask], w['topn'][mask], color=color, ls=style, lw=1.7, label=label)
        axes[1].plot(ns[mask], w['xcdac.bn5'][mask] * 1000, color=color, ls=style, lw=1.7)
        axes[2].plot(ns[mask], (w['xcdac.bp5'][mask] - .9) * 1000, color=color, ls=style, lw=1.7)
        axes[3].plot(ns[mask], envelope[mask], color=color, ls=style, lw=1.7)
        key = row['current_keys']['xcdac.xsn5.mn_low']
        axes[4].plot(ns[mask], w[key][mask] * 1000, color=color, ls=style, lw=1.7)
    axes[0].axhline(.45 - (-.003515625) / 2 - .225, color='.25', lw=1, ls='--', label='换轨后理想目标')
    axes[1].axhline(0, color='.3', lw=1, label='BN5 理想低参考 0 V')
    axes[2].axhline(0, color='.3', lw=1, label='BP5 理想高参考 0.9 V')
    axes[3].axhline(SOA, color='#b2182b', ls='--', lw=1.2, label='模型 SOA 阈值 0.99 V')
    axes[4].axhline(0, color='.3', lw=1)
    for axis, label in zip(axes, ['TOPN (V)', 'BN5 (mV)', 'BP5 − 0.9 V (mV)', '参考 MOS 最坏端口 (V)', 'BN5 NMOS 漏端电流 (mA)'], strict=True):
        axis.set_ylabel(label)
        axis.grid(alpha=.2)
        axis.axvspan(47.60, 47.61, color='.5', alpha=.10)
        axis.axvline(47.61, color='.5', ls=':', lw=1)
    axes[0].legend(loc='upper right', fontsize=9, ncol=2)
    axes[1].legend(loc='lower right', fontsize=9)
    axes[2].legend(loc='upper right', fontsize=9)
    axes[3].legend(loc='upper right', fontsize=9)
    axes[-1].set_xlabel('Time (ns)')
    axes[-1].set_xlim(47.60, 47.72)
    fig.suptitle('独立 P/N 倍率：首轮 SAR 换轨（输入 −0.5 LSB）', fontsize=14)
    fig.tight_layout()
    fig.savefig(FIG / 'pn_timing.png', dpi=160, bbox_inches='tight')
    plt.close(fig)
    fig, axes = plt.subplots(2, 1, figsize=(11, 5.8), sharex=True)
    for name, color, style in zip(names, colors, styles, strict=True):
        row, w, _ = results[name]
        ns = w['time'] * 1e9
        mask = (ns >= 47.60) & (ns <= 47.85)
        label = f"P×{row['p_multiplier']} / N×{row['n_multiplier']}"
        for axis, key in zip(axes, ['xcdac.bn7', 'xcdac.bn6'], strict=True):
            axis.plot(ns[mask], w[key][mask], color=color, ls=style, lw=1.8, label=label)
    for axis, label, target in zip(axes, ['BN7：高轨 → 低轨 (V)', 'BN6：低轨 → 高轨 (V)'], [0, .9], strict=True):
        axis.axhline(target, color='.3', ls='--', lw=1, label='理想最终电位')
        axis.axvline(47.61, color='.5', ls=':', lw=1)
        axis.grid(alpha=.2)
        axis.set_ylabel(label)
    axes[0].legend(loc='upper right', fontsize=9, ncol=3)
    axes[-1].set_xlabel('Time (ns)')
    axes[-1].set_xlim(47.60, 47.85)
    fig.suptitle('正在换轨的两组底板：BN7 与 BN6', fontsize=14)
    fig.tight_layout()
    fig.savefig(FIG / 'pn_switching.png', dpi=160, bbox_inches='tight')
    plt.close(fig)
    fig, axes = plt.subplots(3, 1, figsize=(11, 7.5), sharex=True)
    for name, color, style in zip(names, colors, styles, strict=True):
        row, w, envelope = results[name]
        ns = w['time'] * 1e9
        mask = (ns >= 203.00) & (ns <= 203.24)
        label = f"P×{row['p_multiplier']} / N×{row['n_multiplier']}"
        axes[0].plot(ns[mask], w['xcdac.bn6'][mask], color=color, ls=style, lw=1.8, label=label)
        axes[1].plot(ns[mask], w['xcdac.bp6'][mask], color=color, ls=style, lw=1.8)
        axes[2].plot(ns[mask], envelope[mask], color=color, ls=style, lw=1.8)
    for axis in axes[:2]:
        axis.axhline(0, color='.3', ls='--', lw=1)
        axis.axhline(.9, color='.3', ls='--', lw=1)
    axes[2].axhline(SOA, color='#b2182b', ls='--', lw=1.2, label='模型 SOA 阈值 0.99 V')
    for axis, label in zip(axes, ['BN6 (V)', 'BP6 (V)', '参考 MOS 最坏端口 (V)'], strict=True):
        axis.set_ylabel(label)
        axis.grid(alpha=.2)
        axis.axvspan(203.01, 203.11, color='.5', alpha=.10)
        for instant in [203.01, 203.11]:
            axis.axvline(instant, color='.5', ls=':', lw=1)
    axes[0].legend(loc='upper right', fontsize=9, ncol=2)
    axes[2].legend(loc='upper right', fontsize=9)
    axes[-1].set_xlim(203.00, 203.24)
    axes[-1].set_xlabel('Time (ns)')
    fig.suptitle('下一采样内的 127 → 128 参考恢复', fontsize=14)
    fig.tight_layout()
    fig.savefig(FIG / 'pn_restore.png', dpi=160, bbox_inches='tight')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--names', nargs='+')
    parser.add_argument('--no-plot', action='store_true')
    args = parser.parse_args()
    names = args.names or [p.stem.removesuffix('_result') for p in sorted((OUT / 'runs').glob('*_result.json'))]
    results = {name: analyze(name) for name in names}
    for name, (row, _, _) in results.items():
        print(json.dumps(dict(name=name, p=row['p_multiplier'], n=row['n_multiplier'], code=row['code'],
                              error_mv=row['compare_max_error_mv'], max_port=row['stress']['all'],
                              cmi=row['printed_cmi'], bn5_min=row['bottoms_first_sar']['BN5'],
                              bn7_half=row['bn7_fall_half_ns'], bn6_half=row['bn6_rise_half_ns'])), flush=True)
    summary = dict(scope='TT native netlist diagnostics; ideal gates/sign comparator, not qualified ADC or OA baseline',
                   conditions=dict(vdd_v=.9, temperature_c=27, corner='tt', stop_ns=300,
                                   dead_time_ps=100, edge_ps=20, physical_transient_noise=False),
                   soa_warning_v=SOA, deterministic_limit_mv=LIMIT * 1000,
                   cases=[r[0] for r in results.values()], retained_replay_checks={})
    for name, retained in [('neg_p1n1', 'direct_bad'), ('neg_p2n2', 'direct_bad_double'), ('pos_p1n1', 'direct_control')]:
        if name in results:
            previous = load(SOURCE / f'metrics/{retained}.json')
            delta = (results[name][0]['stress']['all']['value_v'] - previous['stress']['all']['value_v']) * 1e6
            assert abs(delta) < 100, (name, delta)
            summary['retained_replay_checks'][name] = dict(port_delta_uv=delta)
    for name in list(results):
        if name.endswith('_fine') and name.removesuffix('_fine') in results:
            coarse = results[name.removesuffix('_fine')][0]
            fine = results[name][0]
            port_delta = (fine['stress']['all']['value_v'] - coarse['stress']['all']['value_v']) * 1e6
            error_delta = (fine['compare_max_error_mv'] - coarse['compare_max_error_mv']) * 1000
            assert abs(port_delta) < 10 and abs(error_delta) < 2, (port_delta, error_delta)
            summary.setdefault('fine_checks', {})[name] = dict(port_delta_uv=port_delta, error_delta_uv=error_delta)
    FIG.mkdir(parents=True, exist_ok=True)
    (FIG / 'metrics.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    if not args.no_plot and all(name in results for name in ['neg_p1n1', 'neg_p2n1', 'neg_p1n2', 'neg_p2n2']):
        plot(results)


if __name__ == '__main__':
    main()
