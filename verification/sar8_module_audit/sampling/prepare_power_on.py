"""Local power-on pair draft; does not register, launch or simulate anything."""
import argparse
import copy
import difflib
import json
import math
from pathlib import Path
import re

import builder as b

HERE = Path(__file__).resolve().parent
OUT = HERE / 'power_on'
STOP = 260e-9
RAMP_START_NS = 31.1
RAMP_END_NS = 41.1


def replace_line(text, label, new):
    lines = text.splitlines(keepends=True)
    indices = [i for i, line in enumerate(lines) if line.startswith(label + ' ')]
    assert len(indices) == 1, label
    lines[indices[0]] = new + '\n'
    return ''.join(lines)


def common_startup(text):
    # Both controls receive exactly the same external analog/command prehistory.
    # No internal MOS/storage node is driven, initialized or reset artificially.
    for label, initial in [('VVINP', '0.855'), ('VVINN', '0.045')]:
        old = f'{label} ('
        line = next(line for line in text.splitlines() if line.startswith(old))
        token = 'wave=[0n ' + initial + ' '
        assert line.count(token) == 1
        new = line.replace(token, f'wave=[0n 0 31.1n 0 41.1n {initial} ', 1)
        text = replace_line(text, label, new)
    text = replace_line(text, 'VREFHIGH',
        'VREFHIGH (VREFP_SRC 0) vsource type=pwl wave=[0n 0 31.1n 0 41.1n 0.9]')
    changed = 0
    for line in list(text.splitlines()):
        if re.match(r'^VREF\d_G[NP][NP]B ', line) and 'vsource dc=SUP type=dc' in line:
            label = line.split()[0]
            text = replace_line(text, label, line.replace('vsource dc=SUP type=dc',
                'vsource type=pwl wave=[0n 0 31.1n 0 41.1n SUP]'))
            changed += 1
    assert changed == 16
    old = 'tran_startup tran stop=160n '
    assert text.count(old) == 1
    text = text.replace(old, 'tran_startup tran stop=260n ', 1)
    return text


def ramp_core(text):
    original = 'VVDD (VDD! 0) vsource dc=SUP type=dc'
    assert text.count(original) == 1
    return replace_line(text, 'VVDD',
        'VVDD (VDD! 0) vsource type=pwl wave=[0n 0 31.1n 0 41.1n SUP]')


def unified(before, after, a, z):
    return ''.join(difflib.unified_diff(before.splitlines(keepends=True),
        after.splitlines(keepends=True), fromfile=a, tofile=z, n=1))


def payloads():
    source = HERE / 'cold_controls/longcold/test.scs'
    cold = json.loads((HERE / 'cold_controls/manifest.json').read_text())
    row = next(x for x in cold['cases'] if x['name'] == 'longcold')
    original = source.read_bytes()
    assert b.sha(original) == row['deck_sha256']
    package = json.loads((HERE / 'stream_package/package_manifest.json').read_text())
    for name, record in package['files'].items():
        assert b.sha((HERE / 'stream_package/common' / name).read_bytes()) == record['sha256']
    reuse = package['reuse']
    assert b.sha((b.ROOT / reuse['analyzer_source']).read_bytes()) == reuse['analyzer_sha256']
    control = common_startup(original.decode())
    ramp = ramp_core(control)
    mapping = json.loads((HERE / 'stream_package/common/mapping.json').read_text())
    mapping['stop_s'] = STOP
    mapping['measurements'] = dict(
        frames=[dict(index=0, source_open_start_ns=101, source_close_start_ns=141,
                     held_ns=141.8, role='first formal frame after hypothetical external low prelude'),
                dict(index=1, source_open_start_ns=201, source_close_start_ns=241,
                     held_ns=241.8, role='following frame after normal low phase')],
        preclose_offset_ns=.2, event_provenance='native crossing of signal minus0.5*instantaneous VDD',
        analog_provenance='20ps compact interpolation',
        valid_normal_window_requires_unique_open_close_and_held_after_close=True,
        startup_accuracy_pass=None, startup_valid_cycle_max=None)
    branch_names = {}
    for side in ['p', 'n']:
        for name, short in [('M2', 'm2'), ('M8', 'm8'), ('Mmain', 'main_a'), ('Mmain_U1', 'main_b')]:
            record = next(r for r in mapping['records']
                          if r['instance'] == 'XDUT.XBOOT' + side.upper() + '.' + name)
            branch_names[side + '_' + short + '_drain'] = record['fixture_instance'].lower() + ':1'
    mapping['branch_signal_map'] = branch_names
    # Frozen stream.cpp integrates precisely these bins, independent of stop_s.
    mapping['energy_bins_s'] = [[0, 100e-9], [100e-9, 200e-9]]
    mapping['native_energy_after200ns_available'] = False
    outputs = {'dc_core/test.scs': control.encode(), 'ramp_core/test.scs': ramp.encode(),
        'dc_core/source.diff': unified(original.decode(), control,
            source.relative_to(b.ROOT).as_posix(), 'power_on/dc_core/test.scs').encode(),
        'ramp_core/source.diff': unified(original.decode(), ramp,
            source.relative_to(b.ROOT).as_posix(), 'power_on/ramp_core/test.scs').encode(),
        'pair.diff': unified(control, ramp, 'dc_core/test.scs', 'ramp_core/test.scs').encode(),
        'common/mapping.json': (json.dumps(mapping, indent=2) + '\n').encode()}
    binary_bound = (math.ceil(STOP / 20e-12) + 2) * (package['selected_signals'] + 1) * 8
    assert binary_bound + 4 * 1024**2 < 40 * 1024**2
    manifest = dict(schema_version=1, status='draft_parent_review_required_not_registered_or_run',
        generator_sha256=b.sha(Path(__file__).read_bytes()),
        source=dict(path=source.relative_to(b.ROOT).as_posix(), sha256=row['deck_sha256']),
        files={name: dict(sha256=b.sha(data), bytes=len(data)) for name, data in outputs.items()},
        reused={name: dict(path=(HERE / 'stream_package/common' / name).relative_to(b.ROOT).as_posix(), **record)
                for name, record in package['files'].items() if name != 'mapping.json'},
        reused_analyzer=copy.deepcopy(reuse),
        DUT_unchanged=True, forced_initial_charge=False, POR_implemented=False,
        startup_protocol_implemented_in_DUT=False, supply_operating_contract_v=[.81, .99],
        draft_condition=dict(MOS='ss', passives='tt', final_core_supply_v=.81, temperature_c=-40),
        shared_hypothetical_prelude=dict(sample_low_until_ns=101,
            analog_reference_and_input_ramp_ns=[31.1, 41.1], high_Q128_boundary_ramp_ns=[31.1, 41.1],
            clock_wait_is_external_testbench_assumption=True,
            startup_rail_order_is_not_approved_product_contract=True),
        controlled_delta='VVDD: DC SUP versus PWL0 from t0,31.1-41.1ns ramp to SUP',
        fixed_source_formal_windows_ns=[[101,141],[201,241]], source_edge_duration_ns=.1,
        after41p1ns_input_reference_Q128_levels_match_original=True,
        nominal_post_ramp_low_flat_ns=59.9,
        first_frame_source_diff_v=-.81, second_frame_source_diff_v=0,
        first_valid_sample_latency_requirement_ns=None, startup_error_limit_v=None,
        stress_records=1422, unique_pairs=581, MOS_count=237,
        native_energy_after200ns_available=False,
        compact_binary_upper_bound_bytes=binary_bound, collection_reserve_bytes=4*1024**2,
        suggested_collection_limit_mib=40, suggested_analysis_rss_mib=256,
        expected_stop_s=STOP, native_compile_or_simulation_done=False,
        suggested_managed_run_ids=['sar8audit-sample-start-dc-sscold-v1',
                                   'sar8audit-sample-start-ramp-sscold-v1'],
        unresolved_before_recipe=['parent review of10ns diagnostic ramp and31.1-41.1ns placement',
            'external low-clock prelude, analog/reference/command sequencing and first-valid-frame contract',
            'approve260ns/40MiB collection budget and managed recipes',
            'native Spectre syntax/smoke, actual DC states, convergence and startup stress'],
        qualification_scope='fixed-reference,N4-reset power-on diagnostic draft, not POR/full ADC qualification')
    outputs['manifest.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    return outputs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = payloads()
    for name, data in outputs.items():
        target = OUT / name
        if target.exists():
            assert target.read_bytes() == data, 'draft differs: ' + name
        elif args.check:
            raise AssertionError('missing draft: ' + name)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    print(json.dumps(dict(files=len(outputs), stop_ns=260, cases=2,
        recipe_created=False, remote=False, simulation=False)))


if __name__ == '__main__':
    main()
