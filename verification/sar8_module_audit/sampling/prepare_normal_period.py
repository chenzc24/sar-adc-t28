"""Prepare one finite normal-low-phase cold control; never dispatch a run."""
import argparse
import copy
from decimal import Decimal
import difflib
import json
from pathlib import Path
import re

import builder as b

HERE = Path(__file__).resolve().parent
OUT = HERE / 'normal_period'
CONTRACT = b.ROOT / 'output/sar8_physical_repair/sar8fix-loaded-both-rx2-tt/test.scs'


def clock_contract(text):
    lines = [line for line in text.splitlines() if line.startswith('VSAMPLE ')]
    assert len(lines) == 1
    line = lines[0]
    assert 'vsource type=pulse val0=SUP val1=0 ' in line
    fields = dict(re.findall(r'(delay|rise|fall|width|period)=([\d.]+[np])', line))
    assert set(fields) == {'delay', 'rise', 'fall', 'width', 'period'}
    def ns(value):
        return Decimal(value[:-1]) * (Decimal('.001') if value[-1] == 'p' else 1)
    values = {name: ns(value) for name, value in fields.items()}
    assert values == dict(delay=Decimal(41), rise=Decimal('.1'),
                         fall=Decimal('.1'), width=Decimal('59.9'), period=Decimal(100))
    # val0 is high: the pulse begins by falling to zero and ends by rising.
    fall_start = values['delay']
    fall_end = fall_start + values['rise']
    rise_start = fall_end + values['width']
    rise_end = rise_start + values['fall']
    next_fall = fall_start + values['period']
    assert rise_start == 101 and next_fall == 141
    return dict(source=CONTRACT.relative_to(b.ROOT).as_posix(),
        source_sha256=b.sha(text.encode()), VSAMPLE=line,
        period_ns=float(values['period']), rate_MSps=10,
        nominal_high_half_level_interval_ns=40,
        nominal_low_half_level_interval_ns=60,
        external_low_flat_plateau_ns=float(rise_start - fall_end),
        source_fall_start_ns=float(fall_start), source_fall_end_ns=float(fall_end),
        source_rise_start_ns=float(rise_start), source_rise_end_ns=float(rise_end),
        source_close_start_ns=float(next_fall), edge_duration_ns=.1)


def change_history(text):
    old = '0n SUP 60.9n SUP 61n 0 101n 0'
    new = '0n SUP 41n SUP 41.1n 0 101n 0'
    lines = text.splitlines(keepends=True)
    candidates = [i for i, line in enumerate(lines)
                  if line.startswith('VSAMPLE ') and old in line]
    assert len(candidates) == 1
    i = candidates[0]
    assert lines[i].count(old) == 1
    lines[i] = lines[i].replace(old, new, 1)
    changed = ''.join(lines)
    assert changed.replace(new, old, 1) == text
    return changed


def payloads():
    cold = json.loads((HERE / 'cold_controls/manifest.json').read_text())
    case = next(row for row in cold['cases'] if row['name'] == 'low40cold')
    source = HERE / 'cold_controls/low40cold/test.scs'
    original = source.read_bytes()
    assert b.sha(original) == case['deck_sha256']
    for item in cold['reused_measurement_files'].values():
        assert b.sha((b.ROOT / item['path']).read_bytes()) == item['sha256']
    analyzer = cold['analyzer']
    assert b.sha((b.ROOT / analyzer['analyzer_source']).read_bytes()) == analyzer['analyzer_sha256']
    contract = clock_contract(CONTRACT.read_bytes().decode())
    text = change_history(original.decode())
    data = text.encode()
    diff = ''.join(difflib.unified_diff(original.decode().splitlines(keepends=True),
        text.splitlines(keepends=True), fromfile=source.relative_to(b.ROOT).as_posix(),
        tofile='normal_period/low60cold/test.scs', n=1))
    template = json.loads((HERE / 'cold_controls/recipe_suggestions.json').read_text())['recipes'][0]
    assert template['run_id'] == 'sar8audit-sample-v2-low40cold'
    recipe = copy.deepcopy(template)
    recipe['run_id'] = 'sar8audit-sample-v2-low60cold'
    for item in recipe['inputs']:
        if item['name'] == 'test.scs':
            item['source'] = (OUT / 'low60cold/test.scs').relative_to(b.ROOT).as_posix()
    recipe['test_conditions'].update(history='low60cold', external_low_plateau_ns=59.9,
        source_initial_fall_start_ns=41, source_initial_fall_end_ns=41.1,
        nominal_normal_low_half_level_interval_ns=60)
    recipe['qualification_scope'] = ('Finite normal-low-phase recovery from the same high-DC state; '
        'fixed-reference/reset sampling fixture, not full-ADC normal-cycle qualification')
    manifest = dict(schema_version=1, status='local_prepared_not_registered_or_run',
        generator_sha256=b.sha(Path(__file__).read_bytes()), run_id=recipe['run_id'],
        source=source.relative_to(b.ROOT).as_posix(), source_sha256=case['deck_sha256'],
        deck_sha256=b.sha(data), diff_sha256=b.sha(diff.encode()), clock_contract=contract,
        only_delta='VSAMPLE initial fall60.9-61ns ->41-41.1ns',
        formal_source_tail_from101ns_identical=True,
        initial_SAMPLE='SUP; same natural high-DC operating point, pending native verification',
        actual_SEQ_low_interval_ns=None, actual_acquisition_ns=None,
        reused_measurement_files=cold['reused_measurement_files'], analyzer=analyzer,
        all_sources_devices_models_and_loads_otherwise_unchanged=True,
        low_DC_equilibrium_is_normal_period=False,
        finite_precharge_minimum_ns=None, full_ADC_PVT_qualified=False,
        simulator_invoked=False, remote_submission=False,
        analysis_rss_limit_mib=256, collection_limit_mib=32)
    return {'low60cold/test.scs': data, 'low60cold/source.diff': diff.encode(),
        'manifest.json': (json.dumps(manifest, indent=2) + '\n').encode(),
        'recipe_suggestions.json': (json.dumps(dict(register_only_after_parent_review=True,
            recipes=[recipe]), indent=2) + '\n').encode()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = payloads()
    for name, data in outputs.items():
        target = OUT / name
        if target.exists():
            assert target.read_bytes() == data, 'existing normal-period input differs: ' + name
        elif args.check:
            raise AssertionError('missing normal-period input: ' + name)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    print(json.dumps(dict(files=len(outputs), case='low60cold',
        nominal_low_half_level_ns=60, low_flat_plateau_ns=59.9, remote=False)))


if __name__ == '__main__':
    main()
