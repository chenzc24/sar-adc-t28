"""Two-frame local measurement draft; no simulation or assumed startup pass."""
import argparse
import json
from pathlib import Path


def summarize(events, at, mapping):
    names = mapping['signal_map']
    branches = mapping['branch_signal_map']
    seq = sorted(events.get(names['seq_sample'], []))
    diff = lambda t: at(names['top_p'], t) - at(names['top_n'], t)
    source = lambda t: at(names['vin_p_source'], t) - at(names['vin_n_source'], t)

    def snapshot(ns):
        t = ns * 1e-9
        result = dict(time_ns=ns, vdd_v=at(names['vdd'], t),
            source_diff_v=source(t), seq_sample_v=at(names['seq_sample'], t),
            cmp_reset_v=at(names['cmp_reset'], t))
        for side in ['p', 'n']:
            result[side] = dict(
                cboot_v=at(names['boot_' + side + '_btop'], t) - at(names['boot_' + side + '_bbot'], t),
                bbot_v=at(names['boot_' + side + '_bbot'], t),
                ctrl_v=at(names['boot_' + side + '_ctrl'], t),
                g_minus_vin_v=at(names['boot_' + side + '_g'], t) - at(names['vin_' + side], t),
                M2_into_BTOP_ua=-at(branches[side + '_m2_drain'], t) * 1e6,
                M8_to_ground_ua=at(branches[side + '_m8_drain'], t) * 1e6,
                main_total_drain_ua=sum(at(branches[side + '_' + name + '_drain'], t)
                                        for name in ['main_a', 'main_b']) * 1e6)
        return result

    frames = []
    for frame in mapping['measurements']['frames']:
        start = frame['source_open_start_ns'] * 1e-9
        end = start + 99.5e-9
        held = frame['held_ns'] * 1e-9
        candidates = [(t, up) for t, up in seq if start <= t < end]
        opens = [t for t, up in candidates if up]
        closes = [t for t, up in candidates if not up]
        opening = opens[0] if len(opens) == 1 else None
        close = closes[0] if len(closes) == 1 else None
        pre = close - .2e-9 if close is not None else None
        ordered = opening is not None and pre is not None and opening < pre < close
        after = close is not None and close < held
        valid = ordered and after
        nominal = (frame['source_close_start_ns'] + .05) * 1e-9
        row = dict(index=frame['index'], role=frame['role'],
            native_SEQ_candidates=[dict(time_ns=t * 1e9, up=up) for t, up in candidates],
            actual_open_ns=None if opening is None else opening * 1e9,
            actual_close_ns=None if close is None else close * 1e9,
            actual_acquisition_ns=(close - opening) * 1e9 if ordered else None,
            sampling_window_evaluable=valid, held_after_actual_close=after,
            nominal_interface_half_fall_ns=nominal * 1e9, held_time_ns=frame['held_ns'],
            raw_held_diff_mv=diff(held) * 1000,
            raw_held_vs_current_source_mv=(diff(held) - source(held)) * 1000,
            held_error_at_nominal_edge_mv=(diff(held) - source(nominal)) * 1000 if valid else None,
            preclose_time_ns=None if pre is None else pre * 1e9,
            preclose_error_mv=(diff(pre) - source(pre)) * 1000 if ordered else None,
            net_turnoff_voltage_change_mv=(diff(held) - diff(pre)) * 1000 if valid else None,
            source_endpoint_motion_mv=(source(held) - source(pre)) * 1000 if valid else None,
            pure_channel_injection_measured=False, accuracy_pass=None,
            at_held=snapshot(frame['held_ns']),
            at_acquisition_probe=snapshot(frame['source_open_start_ns'] + 9),
            before_open=None if opening is None else snapshot(opening * 1e9 - .01),
            before_close=None if not ordered else snapshot(pre * 1e9))
        frames.append(row)
    return dict(status='diagnostic_measurements_only', frames=frames,
        pre_formal_SEQ_events=[dict(time_ns=t * 1e9, up=up) for t, up in seq if t < 101e-9],
        power_on_snapshots=[snapshot(ns) for ns in [0, 31.1, 41.11, 80, 100.99, 200.99]],
        startup_accuracy_pass=None, startup_valid_cycle_max=None, POR_qualified=False,
        source_contract='first formal differential=-0.81V, following=0V; source tail unchanged',
        analog_provenance='20ps compact interpolation; native events use instantaneous half-VDD',
        interpretation='external clock-low wait and common bias ramps are testbench assumptions; later frame is not automatically qualified normal operation')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('derived', type=Path)
    parser.add_argument('--mapping', type=Path, required=True)
    args = parser.parse_args()
    import numpy as np
    mapping = json.loads(args.mapping.read_text())
    meta = json.loads((args.derived / 'wave.meta.json').read_text())
    assert meta['PSF_END'] and abs(meta['last_time_s'] - mapping['stop_s']) < 1e-15
    columns = (args.derived / 'wave.columns').read_text().splitlines()
    assert len(columns) == meta['columns']
    assert (args.derived / 'wave.bin').stat().st_size == meta['points'] * len(columns) * 8
    wave = np.memmap(args.derived / 'wave.bin', mode='r', dtype='<f8', shape=(meta['points'], len(columns)))
    try:
        index = {name: i for i, name in enumerate(columns)}
        times = wave[:, index['time']]
        assert times[0] == 0 and np.all(np.diff(times) > 0) and times[-1] >= 241.8e-9
        at = lambda name, t: float(np.interp(t, times, wave[:, index[name]]))
        events = {}
        for line in (args.derived / 'wave.events.tsv').read_text().splitlines():
            name, up, time = line.split()
            events.setdefault(name, []).append((float(time), int(up)))
        result = summarize(events, at, mapping)
        stress = np.loadtxt(args.derived / 'wave.stress.tsv')
        assert stress.shape == (581, 3) and len(mapping['records']) == 1422
        assert np.array_equal(stress[:, 0], np.arange(581))
        result['native_stress_failed_records'] = int(sum(stress[r['pair_index'], 1] > r['limit_v']
            for r in mapping['records']))
        result['native_stress_checked_records'] = 1422
        result['native_energy_after200ns_available'] = False
        ramp = times <= 41.11e-9
        result['compact_source_minus_core_peak_v'] = {}
        for key in ['vin_p_source', 'vin_n_source', 'vref_p_source', 'vref_n_source']:
            delta = wave[ramp, index[mapping['signal_map'][key]]] - wave[ramp, index[mapping['signal_map']['vdd']]]
            peak = int(np.argmax(delta))
            result['compact_source_minus_core_peak_v'][key] = dict(value_v=float(delta[peak]),
                time_ns=float(times[ramp][peak] * 1e9),
                interpretation='source sequencing evidence; not a MOS terminal stress measurement')
        print(json.dumps(result, indent=2))
    finally:
        wave._mmap.close()


if __name__ == '__main__':
    main()
