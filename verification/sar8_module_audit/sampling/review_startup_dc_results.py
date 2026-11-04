"""Bounded local review of the collected startup DC control; no remote actions."""
import ctypes
from ctypes import wintypes
import hashlib
import json
from pathlib import Path
import re

import numpy as np
import yaml

import builder as b
import review_power_on as review
from unpack_power_on import digest

HERE = Path(__file__).resolve().parent
OUT = HERE / 'power_on_results/dc_core'
RUN_ID = 'sar8audit-sample-start-dc-sscold-v1'


def peak_working_set():
    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ['PeakWorkingSetSize', 'WorkingSetSize',
                'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
                'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage']]
    info = Counters()
    info.cb = ctypes.sizeof(info)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(info), info.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    assert info.PeakWorkingSetSize <= 256 * 1024**2, 'local analysis exceeded256MiB'
    return info.PeakWorkingSetSize / 1024**2


def review_case(run_id=RUN_ID, out=OUT):
    peak_working_set()
    run = b.ROOT / 'output/managed_execution/runs' / run_id
    source = run / 'collected'
    decoded = out / 'decoded'
    receipt = json.loads((source / 'collection_receipt.json').read_text())
    assert not receipt['skipped'] and receipt['total_bytes'] <= 32 * 1024**2
    for item in receipt['files']:
        path = source / item['name']
        assert path.stat().st_size == item['bytes'] and digest(path) == item['sha256']
    package = json.loads((HERE / 'power_on_managed_v1/manifest.json').read_text())
    proposal = next(row for row in package['recipes'] if row['run_id'] == run_id)
    for item in proposal['inputs']:
        path = run / 'inputs' / item['name']
        assert path.stat().st_size == item['bytes'] and digest(path) == item['sha256']
    for name, key in [('unpack_power_on.py', 'unpacker_sha256'),
                      ('review_power_on.py', 'local_review_sha256'),
                      ('power_on_analyze.py', 'wrapper_sha256')]:
        assert digest(HERE / name) == package[key]
    registered = yaml.safe_load((b.ROOT / 'management/runs' / (run_id + '.yaml')).read_text())
    assert receipt['status']['registered']['recipe_hash'] == registered['recipe_hash']
    for phase in ['simulation', 'analysis']:
        assert receipt['status'][phase]['status'] == 'complete'
        assert receipt['status'][phase]['exit_code'] == 0
    log = (source / 'spectre.out').read_text(errors='replace')
    assert 'spectre completes with 0 errors' in log
    assert '+preset=cx' in log and '+mt=4' in log
    temps = [float(t) for t in re.findall(r'(?m)^\s*temp = (-?\d+(?:\.\d+)?)', log)]
    assert temps and all(t == -40 for t in temps)
    mapping = json.loads((run / 'inputs/mapping.json').read_text())
    compression = json.loads((source / 'derived/wave.compression.json').read_text())
    assert digest(decoded / 'wave.bin') == compression['uncompressed_sha256']
    assert (decoded / 'wave.bin').stat().st_size == compression['uncompressed_bytes']
    meta = json.loads((decoded / 'wave.meta.json').read_text())
    assert meta['PSF_END'] and abs(meta['last_time_s'] - 260e-9) < 1e-15
    columns = (decoded / 'wave.columns').read_text().splitlines()
    assert len(columns) == meta['columns'] == 294
    assert (decoded / 'wave.bin').stat().st_size == meta['points'] * len(columns) * 8
    wave = np.memmap(decoded / 'wave.bin', mode='r', dtype='<f8', shape=(meta['points'], len(columns)))
    try:
        index = {name: i for i, name in enumerate(columns)}
        times = wave[:, index['time']]
        assert times[0] == 0 and np.all(np.diff(times) > 0) and abs(times[-1] - 260e-9) < 1e-15
        at = lambda name, t: float(np.interp(t, times, wave[:, index[name]]))
        events = {}
        for line in (decoded / 'wave.events.tsv').read_text().splitlines():
            name, up, time = line.split()
            events.setdefault(name, []).append((float(time), int(up)))
        measurements = review.summarize(events, at, mapping)
        n = mapping['signal_map']
        for frame in measurements['frames']:
            assert frame['sampling_window_evaluable']
            pre = frame['preclose_time_ns'] * 1e-9
            held = frame['held_time_ns'] * 1e-9
            independent_pre = (at(n['top_p'], pre) - at(n['top_n'], pre)
                - at(n['vin_p_source'], pre) + at(n['vin_n_source'], pre)) * 1000
            assert abs(independent_pre - frame['preclose_error_mv']) < 1e-9
            frame['net_turnoff_error_increment_mv'] = frame['held_error_at_nominal_edge_mv'] - frame['preclose_error_mv']
            frame['preclose_top_v'] = dict(p=at(n['top_p'], pre), n=at(n['top_n'], pre))
            frame['held_top_v'] = dict(p=at(n['top_p'], held), n=at(n['top_n'], held))
        stress = np.loadtxt(decoded / 'wave.stress.tsv')
        assert stress.shape == (581, 3) and np.array_equal(stress[:, 0], np.arange(581))
        records = mapping['records']
        assert len(records) == 1422 and len({r['fixture_instance'] for r in records}) == 237
        failed = [r for r in records if stress[r['pair_index'], 1] > r['limit_v']]
        groups = {}
        for record in records:
            row = dict(record, peak_v=float(stress[record['pair_index'], 1]),
                time_ns=float(stress[record['pair_index'], 2] * 1e9))
            row['normalized_peak'] = row['peak_v'] / row['limit_v']
            group = row['group']
            if group not in groups or row['normalized_peak'] > groups[group]['normalized_peak']:
                groups[group] = row
        native = json.loads((decoded / 'native_result.json').read_text())
        assert len(failed) == native['failing_pairs']
        assert native['stress_all_native_points'] and native['events_all_native_points']
        measurements['independent_native_stress'] = dict(records=1422, unique_pairs=581,
            MOS=237, failed_records=len(failed), groups=groups,
            native_points=meta['native_points'], analog_points=meta['points'])
    finally:
        wave._mmap.close()
    evidence = dict(run_id=run_id, recipe_hash=registered['recipe_hash'],
        frozen_inputs_SHA_verified=True, collection_receipt_SHA256=digest(source / 'collection_receipt.json'),
        collected_files=len(receipt['files']), collected_bytes=receipt['total_bytes'], skipped=[],
        compression=compression, native_temperature_c=-40,
        native_warning_codes=sorted(set(re.findall(r'WARNING \(([A-Z]+-\d+)\)', log))),
        native_CMI_codes=sorted(set(re.findall(r'CMI-\d+', log))),
        actual_settings=receipt['status']['simulation']['native']['effective_settings'],
        remote_peak_RSS_mib={phase: receipt['status'][phase]['peak_rss_bytes'] / 1024**2
                             for phase in ['simulation', 'analysis']},
        local_peak_working_set_mib=peak_working_set(),
        no_remote_operation_or_new_simulation=True,
        conclusion_scope='one explicitly bound member of the existing startup DC/ramp diagnostic pair',
        native_energy_bins_ns=[[0,100],[100,200]], native_energy_after200ns_available=False)
    (out / 'measurements.json').write_text(json.dumps(measurements, indent=2) + '\n')
    (out / 'evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    for frame in measurements['frames']:
        print({key: frame[key] for key in ['index', 'actual_open_ns', 'actual_close_ns',
            'actual_acquisition_ns', 'preclose_error_mv', 'held_error_at_nominal_edge_mv',
            'net_turnoff_voltage_change_mv', 'source_endpoint_motion_mv']})
        print('before_open', frame['before_open'])
    print('power_snapshots', measurements['power_on_snapshots'])
    print('stress', len(failed), 'local_peak_MiB', evidence['local_peak_working_set_mib'])
    return measurements, evidence


if __name__ == '__main__':
    review_case()
