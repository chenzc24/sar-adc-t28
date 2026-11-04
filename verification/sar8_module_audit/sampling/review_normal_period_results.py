"""Read collected cold finite40/normal-low/DC controls; no dispatch or old writes."""
import hashlib
import json
from pathlib import Path

import numpy as np

import builder as b
from review_cold_results import inspect_case
from review_results import read_case

HERE = Path(__file__).resolve().parent
OUT = HERE / 'normal_period_results'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def frozen_snapshot():
    return {str(path.relative_to(HERE)): digest(path)
            for folder in ['cold_results', 'normal_period']
            for path in (HERE / folder).rglob('*') if path.is_file()}


def read_checked(case, expected_sha):
    # Reuse established bounded SHA/native-temperature/clock measurement reader.
    result, _ = inspect_case(case, -40, expected_sha)
    root = b.ROOT / 'output/managed_execution/runs' / ('sar8audit-sample-v2-' + case)
    collected = root / 'collected'
    receipt = json.loads((collected / 'collection_receipt.json').read_text())
    assert not receipt.get('skipped')
    assert receipt['total_bytes'] == sum(item['bytes'] for item in receipt['files'])
    package = json.loads((HERE / 'stream_package/package_manifest.json').read_text())
    for name, item in package['files'].items():
        assert digest(root / 'inputs' / name) == item['sha256'], name
    reuse = package['reuse']
    assert digest(root / 'inputs/loaded_remote.py') == reuse['analyzer_sha256']
    config = json.loads((root / 'inputs/mapping.json').read_text())
    stress = np.loadtxt(collected / 'derived/wave.stress.tsv')
    assert stress.shape == (581, 3)
    assert np.array_equal(stress[:, 0], np.arange(581))
    records = config['records']
    assert len(records) == 1422
    assert len({row['fixture_instance'] for row in records}) == 237
    failures = [row for row in records if stress[row['pair_index'], 1] > row['limit_v']]
    assert len(failures) == result['stress_failed_pairs'] == 0
    native = json.loads((collected / 'derived/result.json').read_text())
    assert native['stress_all_native_points'] and native['events_all_native_points']
    assert native['meta']['PSF_END'] and native['analysis_complete']
    result['independent_terminal_screen'] = dict(records=1422, MOS=237,
        unique_pairs=581, failures=len(failures), all_native_points=True)
    result['collection_file_count'] = len(receipt['files'])
    result['collection_no_skips'] = True
    result['all_frozen_measurement_inputs_SHA_verified'] = True
    result['native_stress_groups'] = native['groups']

    # One memmap at a time; save only the small signals needed for the new plot.
    _, w = read_case(case)
    try:
        matrix = w['matrix']
        labels = {row['instance']: row['label'].lower() for row in json.loads(
            (HERE / 'compact_v2/boundary_loads.json').read_text())['device_mapping_without_geometry']}
        x = np.linspace(35, 143, 5401)
        curve = dict(time_ns=x)
        for key in ['top_p', 'top_n', 'vin_p', 'vin_n', 'seq_sample',
                    'boot_p_btop', 'boot_p_bbot', 'boot_p_g', 'boot_p_ctrl']:
            curve[key] = np.interp(x * 1e-9, w['t'], matrix[:, w['indices'][w['names'][key]]])
        curve['main_p_ua'] = sum(np.interp(x * 1e-9, w['t'], matrix[:, w['indices'][
            'xf.' + labels['XDUT.XBOOTP.' + name] + ':1']]) * 1e6
            for name in ['Mmain', 'Mmain_U1'])
        m2node = 'xf.' + labels['XDUT.XBOOTP.M2'] + ':1'
        curve['m2_p_into_btop_ua'] = -np.interp(x * 1e-9, w['t'],
            matrix[:, w['indices'][m2node]]) * 1e6
        snapshots = {}
        for label, t in [('at80ns', 80e-9), ('at100ns', 100e-9),
                         ('before_open', result['actual_open_ns'] * 1e-9 - .01e-9)]:
            snapshots[label] = dict(time_ns=t * 1e9)
            for side in ['p', 'n']:
                stem = 'xf.xdut__xboot' + side + '__'
                current = lambda name: w['at']('xf.' + labels['XDUT.XBOOT' + side.upper() + '.' + name] + ':1', t) * 1e6
                snapshots[label][side] = dict(
                    cboot_v=w['at'](stem + 'btop', t) - w['at'](stem + 'bbot', t),
                    bbot_v=w['at'](stem + 'bbot', t), ctrl_v=w['at'](stem + 'ctrl', t),
                    M2_into_BTOP_ua=-current('M2'), M8_BBOT_to_ground_ua=current('M8'))
        result['recovery_snapshots'] = snapshots
        start_ns = result['precharge_low_start_ns']
        if start_ns is not None:
            start = start_ns * 1e-9
            end = result['actual_open_ns'] * 1e-9 - .01e-9
            t = np.r_[start, w['t'][(w['t'] > start) & (w['t'] < end)], end]
            i = -np.interp(t, w['t'], matrix[:, w['indices'][m2node]])
            result['finite_recovery_M2_signed_charge_fc'] = float(np.trapezoid(i, t) * 1e15)
            result['recovery_current_integral_scope'] = 'P M2 terminal1 sign reversed; compact estimate, includes displacement; not Cboot charge alone'
        else:
            result['finite_recovery_M2_signed_charge_fc'] = None
        return result, curve
    finally:
        w['matrix']._mmap.close()


def plot(cases):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(4, 2, figsize=(12, 10.5), layout='constrained')
    style = [('low40cold', '#ba543c', '-', '40 ns flat low'),
             ('low60cold', '#2474a1', '-', '60 ns nominal low (59.9 ns flat)'),
             ('longcold', '#328769', '--', 'Low-DC equilibrium')]
    for name, color, line, label in style:
        r, w = cases[name]
        x = w['time_ns']
        cboot = w['boot_p_btop'] - w['boot_p_bbot']
        error = (w['top_p'] - w['top_n'] - np.interp(x,
            [0, 100.2, 100.3, 160], [.81, .81, -.81, -.81])) * 1000
        left = [w['seq_sample'], cboot, w['m2_p_into_btop_ua'], w['boot_p_bbot']]
        right = [w['boot_p_g'] - w['vin_p'], w['main_p_ua'], error, error]
        for row in range(4):
            axes[row, 0].plot(x, left[row], color=color, ls=line, lw=1.5, label=label)
            axes[row, 1].plot(x, right[row], color=color, ls=line, lw=1.5)
        axes[3, 1].scatter([r['snapshots']['preclose']['time_ns']], [r['preclose_error_mv']],
            color=color, marker='o', s=27, zorder=5)
        axes[3, 1].scatter([141.8], [r['raw_held_source_error_mv']],
            color=color, marker='s', s=27, zorder=5)
    reference = cases['low60cold'][0]
    for row in range(4):
        axes[row, 0].set_xlim(35, 104)
        axes[row, 1].set_xlim(100.5, 143)
        axes[row, 1].axvline(reference['actual_open_ns'], color='#777', ls=':', lw=.8)
        axes[row, 1].axvline(reference['actual_close_ns'], color='#777', ls=':', lw=.8)
    axes[1, 0].axhline(.81, color='#777', ls=':', lw=.8)
    axes[2, 0].axhline(0, color='#777', lw=.6)
    axes[0, 1].axhline(0, color='#777', lw=.6)
    axes[2, 1].set_yscale('symlog', linthresh=1)
    for ax in axes[2:, 1]:
        ax.axhspan(-1.7578125, 1.7578125, color='#8bb992', alpha=.18)
    axes[3, 1].set_xlim(140.5, 142.2)
    axes[3, 1].set_ylim(-2, 16)
    axes[0, 0].legend(fontsize=8, loc='center left')
    labels = [('SEQ_SAMPLE (V)', 'P G - VIN (V)'),
              ('P Cboot (V)', 'P main drain current (uA)'),
              ('P M2 current into BTOP (uA)', 'Differential error (mV)'),
              ('P BBOT (V)', 'Closing / held error (mV)')]
    for row, pair in enumerate(labels):
        for col in range(2):
            axes[row, col].set_ylabel(pair[col])
            axes[row, col].grid(alpha=.18)
    axes[3, 0].set_xlabel('Absolute time (ns)')
    axes[3, 1].set_xlabel('Time (ns); circle: close - 0.2 ns; square: 141.8 ns')
    fig.suptitle('SS / 0.81 V / -40 C | finite recovery versus low-DC control\n'
        'Same Bootstrap and full CDAC; fixed Q128 reference, N4 reset; no noise / mismatch / PEX\n'
        '20 ps compact analog estimates; dotted: native low60 SEQ edges; green: +/-0.25 LSB screen',
        fontsize=10.5)
    fig.savefig(OUT / 'cold_precharge_comparison.png', dpi=170)
    plt.close(fig)


def main():
    old = frozen_snapshot()
    cold = json.loads((HERE / 'cold_controls/manifest.json').read_text())
    normal = json.loads((HERE / 'normal_period/manifest.json').read_text())
    expected = {row['name']: row['deck_sha256'] for row in cold['cases']}
    expected['low60cold'] = normal['deck_sha256']
    cases = {case: read_checked(case, expected[case])
             for case in ['low40cold', 'low60cold', 'longcold']}
    a = cases['low40cold'][0]
    c = cases['low60cold'][0]
    assert a['snapshots']['DC'] == c['snapshots']['DC']
    OUT.mkdir(exist_ok=True)
    report = dict(scope='SS cold fixed-reference/reset compact sampling finite recovery',
        cases={name: row for name, (row, _) in cases.items()},
        finite40_and_normal60_same_checked_DC=True,
        nominal_normal_low_half_level_interval_ns=60, external_low_flat_plateau_ns=59.9,
        minimum_precharge_requirement_ns=None, true_normal_conversion_cycle_verified=False,
        startup_power_ramp_POR_verified=False, no_new_simulation_or_circuit_edit=True,
        prior_artifact_SHA=old,
        conclusion='finite normal-low history passes the existing acquisition/held diagnostic; full conversion history remains untested')
    (OUT / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    plot(cases)
    assert old == frozen_snapshot(), 'previous frozen artifacts changed'
    for case, (r, _) in cases.items():
        print(case, json.dumps({key: r[key] for key in [
            'observed_low_interval_ns', 'actual_open_ns', 'actual_close_ns',
            'actual_acquisition_ns', 'preclose_error_mv', 'net_turnoff_delta_mv',
            'raw_held_source_error_mv', 'finite_recovery_M2_signed_charge_fc']}))
        print('recovery', r['recovery_snapshots'])
        print('at110ns', r['snapshots']['at110ns'])


if __name__ == '__main__':
    main()
