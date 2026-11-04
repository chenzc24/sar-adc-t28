"""Local, source-bound usage measurements; never accesses a remote host."""
from pathlib import Path
import gzip
import hashlib
import json
import struct
import sys

HERE = Path(__file__).resolve().parent
OWN = HERE.parent
ROOT = OWN.parents[2]
sys.path.insert(0, str(OWN))
from review_standard_cell_full_result import receipt_files
from review_standard_cell_storage_v2 import record


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def crossings(rows, column, level):
    result = []
    for a, b in zip(rows, rows[1:]):
        x, y = a[column] - level, b[column] - level
        direction = 1 if x < 0 <= y else -1 if x > 0 >= y else 0
        if direction:
            result.append(dict(time_s=a[0] - x * (b[0] - a[0]) / (y - x),
                               direction=direction, native_bracket_s=[a[0], b[0]]))
    return result


def edges(rows, column, vdd=.99):
    levels = {f: crossings(rows, column, f * vdd) for f in (.1, .2, .5, .8, .9)}
    result = []
    for event in levels[.5]:
        item = dict(event)
        found = {}
        for f in levels:
            candidates = [x for x in levels[f] if x['direction'] == event['direction']
                          and abs(x['time_s'] - event['time_s']) <= .25e-9]
            found[f] = candidates[0] if len(candidates) == 1 else None
        item['crossings'] = {str(f): found[f] for f in found}
        for name, a, b in [('slew_10_90_s', .1, .9), ('slew_20_80_s', .2, .8)]:
            item[name] = abs(found[b]['time_s'] - found[a]['time_s']) if found[a] and found[b] else None
        result.append(item)
    return result


def collect():
    source_identity = record('sar8audit-ctrl-stdfull-storage-ff-v2')['recipe_hash']
    assert source_identity == '351d0c4ca4e27bd33dccbe0057e92e1f2146e5f4ba2ca5619983749217407596'
    folder = ROOT / 'output/managed_execution/runs/sar8audit-ctrl-storage-ff-v2-fastanalysis-v1/collected'
    receipt, files = receipt_files(folder)
    result = json.loads((folder / 'derived/result.json').read_text(encoding='utf-8'))
    reference = json.loads((OWN / 'standard_cell_storage_v2/results/ff/summary.json').read_text(encoding='utf-8'))
    assert result['raw_sha256'] == 'f1d92da819b851c4b794937644a921d6c296b36776d6e7a3cb15e9d8cd187551'
    names = json.loads((folder / 'derived/peak.columns.json').read_text())['names']
    wanted = ['time', 'ff_ck', 'ff_d', 'ff_rst', 'xdut.u19_ck', 'xdut.u19_d', 'xdut.xu19.rn', 'xdut.u19_q']
    indices = [names.index(n) for n in wanted]
    pack = struct.Struct('<' + 'd' * len(names))
    rows = []
    digest = hashlib.sha256()
    size = 0
    with gzip.open(folder / 'derived/peak.native.bin.gz', 'rb') as handle:
        while True:
            blob = handle.read(pack.size)
            if not blob:
                break
            if len(blob) != pack.size:
                raise ValueError('Incomplete native row')
            digest.update(blob)
            size += len(blob)
            row = pack.unpack(blob)
            rows.append(tuple(row[i] for i in indices))
    assert dict(bytes=size, sha256=digest.hexdigest()) == result['returned_waveform']['uncompressed']
    assert len(rows) == result['native_points'] == 30060
    assert rows[0][0] == 0 and abs(rows[-1][0] - 20e-9) < 1e-22
    assert all(a[0] < b[0] for a, b in zip(rows, rows[1:]))
    pins = {}
    for index, name in enumerate(wanted[1:], 1):
        events = edges(rows, index)
        values = [x[index] for x in rows]
        pins[name] = dict(min_v=min(values), max_v=max(values), edges=events,
                          slew_10_90_range_s=[min(x['slew_10_90_s'] for x in events),
                                              max(x['slew_10_90_s'] for x in events)],
                          slew_20_80_range_s=[min(x['slew_20_80_s'] for x in events),
                                              max(x['slew_20_80_s'] for x in events)])
    boundaries = json.loads((OWN / 'standard_cell_full_v1/load_boundaries.json').read_text())
    loads = [x for x in boundaries['boundaries'] if x['target'] == 'XDUT.XREF.XSTORE6']
    assert len(loads) == 3
    dependencies = ['standard_cell_full_v1/library_truth.json', 'standard_cell_full_v1/library_probe.json',
                    'standard_cell_full_v1/load_boundaries.json', 'standard_cell_full_v1/storage_dut.scs',
                    'standard_cell_full_v1/full_adc/dut.scs']
    return dict(source_run='sar8audit-ctrl-stdfull-storage-ff-v2', source_managed_recipe_sha256=source_identity,
        readonly_dependency_sha256={n: sha(OWN / n) for n in dependencies},
        analysis_run='sar8audit-ctrl-storage-ff-v2-fastanalysis-v1',
        native_raw_sha256=result['raw_sha256'], native_points=len(rows),
        collection_receipt_sha256=sha(folder / 'collection_receipt.json'),
        lossless_native_history_verified=True, threshold_vdd_v=.99,
        method='Original native samples; linear threshold crossings with native brackets. No resampling, phase recentering or library timing claim.',
        input_pins=pins, output_load_boundaries=loads,
        characterized_effective_output_capacitance_f=None,
        capacitance_note='Exact transistor/RC networks are retained. No fixed or fitted capacitance substitutes a state-dependent load.',
        characterization=dict(table_slew_range_s=None, table_load_range_f=None,
            recommended_max_transition_s=None, recommended_max_capacitance_f=None,
            setup_hold_recovery_removal_s=None, absolute_transient_reliability_rule=None,
            status='unknown: local metadata verifies document filenames and compiled CCS archive, not their timing tables or reliability clauses',
            version_note='Outer190a, SPICE/doc170a and CCS180a differ; compatibility has not been demonstrated.',
            copied_library_contents=False),
        terminal_screen=dict(limit_abs_v=.99, literal_strict_comparison=True,
            scope='Existing project/PDK terminal screen, not a Liberty slew/load range or a demonstrated transient lifetime rule.'),
        previous_MM64_focus=reference['MM64_focus'])


if __name__ == '__main__':
    out = HERE / 'usage_evidence.json'
    data = collect()
    blob = (json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    if out.exists() and out.read_bytes() != blob:
        raise ValueError('Preserve prior evidence')
    out.write_bytes(blob)
    print('SOURCE_BOUND_USAGE_OK', data['native_points'])
