"""Prepare two local YAML recipes and a32MiB bounded compression wrapper package."""
import argparse
import copy
import json
from pathlib import Path

import yaml
import builder as b

HERE = Path(__file__).resolve().parent
OUT = HERE / 'power_on_managed_v1'


def payloads():
    draft = json.loads((HERE / 'power_on/manifest.json').read_text())
    for name, row in draft['files'].items():
        assert b.sha((HERE / 'power_on' / name).read_bytes()) == row['sha256'], name
    for name, row in draft['reused'].items():
        assert b.sha((b.ROOT / row['path']).read_bytes()) == row['sha256'], name
    old = draft['reused_analyzer']
    assert b.sha((b.ROOT / old['analyzer_source']).read_bytes()) == old['analyzer_sha256']
    frozen = {name: row['sha256'] for name, row in draft['reused'].items()}
    frozen['mapping.json'] = draft['files']['common/mapping.json']['sha256']
    frozen['loaded_remote.py'] = old['analyzer_sha256']
    config = dict(schema_version=1, stop_s=260e-9,
        input_sha256=frozen,
        allowed_test_sha256=[draft['files'][case + '/test.scs']['sha256'] for case in ['dc_core', 'ramp_core']],
        binary_bound_bytes=draft['compact_binary_upper_bound_bytes'],
        collection_cap_bytes=32 * 1024**2, derived_cap_bytes=31 * 1024**2,
        root_reserved_bytes=1024**2,
        accepted_diagnostic_ramp_ns=[31.1, 41.1], external_low_clock_prelude=True,
        analog_binary='frozen20ps selected representation; no added decimation',
        all_native_stress_and_events=True, native_energy_after200ns_available=False)
    outputs = {'compression_config.json': (json.dumps(config, indent=2) + '\n').encode()}
    recipes = []
    for case, suffix in [('dc_core', 'dc'), ('ramp_core', 'ramp')]:
        inputs = [dict(source=row['path'], name=name) for name, row in draft['reused'].items()]
        inputs.extend([
            dict(source=(HERE / 'power_on/common/mapping.json').relative_to(b.ROOT).as_posix(), name='mapping.json'),
            dict(source=old['analyzer_source'], name='loaded_remote.py'),
            dict(source=(HERE / 'power_on_analyze.py').relative_to(b.ROOT).as_posix(), name='power_on_analyze.py'),
            dict(source=(OUT / 'compression_config.json').relative_to(b.ROOT).as_posix(), name='compression_config.json'),
            dict(source=(HERE / 'power_on' / case / 'test.scs').relative_to(b.ROOT).as_posix(), name='test.scs')])
        recipe = dict(schema_version=1, run_id='sar8audit-sample-start-' + suffix + '-sscold-v1',
            design_id='sar8_compact_sampling_power_on_v1', entry='test.scs', inputs=inputs,
            analyzer='power_on_analyze.py', expected_stop_s=260e-9,
            spectre_args=['+preset=cx', '+mt=4', '+lqtimeout', '60', '-preset_override'],
            summary_signals=['XF.XDUT__SEQ_SAMPLE', 'XF.XDUT__TOPP', 'XF.XDUT__TOPN', 'VDD!'],
            qualification_scope='Startup diagnostic with accepted external ramps/low-clock prelude, fixed Q128/N4 reset; no POR or first-valid-frame qualification',
            oa_parity='netlist_only',
            test_conditions=dict(corner='ss', passives='tt', vdd=.81, supply_operating_contract_v=[.81,.99],
                temperature_c=-40, noise=False, mismatch=False, PEX=False, history=case,
                core_supply_profile='DC SUP' if case == 'dc_core' else '0 until31.1ns; linear toSUP at41.1ns',
                common_external_bias_ramp_ns=[31.1,41.1], external_SAMPLE_low_until_ns=101,
                formal_source_windows_ns=[[101,141],[201,241]], edge_duration_ns=.1,
                first_source_diff_v=-.81, second_source_diff_v=0, POR_implemented=False,
                startup_valid_frame_specified=False),
            resources=dict(threads=4, simulation_rss_mib=1024, simulation_virtual_mib=8192,
                analysis_rss_mib=256, analysis_virtual_mib=1024, max_output_mib=8192,
                simulation_wall_seconds=1800, analysis_wall_seconds=1200, queue_timeout_seconds=600))
        recipes.append(recipe)
        outputs['recipes/' + case + '.yaml'] = yaml.safe_dump(recipe, allow_unicode=True, sort_keys=False).encode()
    manifest = dict(status='local_managed_proposal_not_registered_or_run',
        parent_accepted_diagnostic_timing_and_bias_assumptions=True,
        collection_hard_cap_mib=32, overrides_previous_draft40MiB_suggestion=True,
        previous_draft_files_unchanged=True, simulator_invoked=False,
        compression_config_sha256=b.sha(outputs['compression_config.json']),
        generator_sha256=b.sha(Path(__file__).read_bytes()),
        wrapper_sha256=b.sha((HERE / 'power_on_analyze.py').read_bytes()),
        unpacker_sha256=b.sha((HERE / 'unpack_power_on.py').read_bytes()),
        local_review_sha256=b.sha((HERE / 'review_power_on.py').read_bytes()),
        shared_remote_analyzer_sha256=old['analyzer_sha256'],
        no_whole_wave_array=True, native_energy_bins_ns=[[0,100],[100,200]],
        qualification='quantify startup only; no POR/startup accuracy pass inferred', recipes=[])
    for recipe in recipes:
        rows = []
        for item in recipe['inputs']:
            data = outputs['compression_config.json'] if item['name'] == 'compression_config.json' else (b.ROOT / item['source']).read_bytes()
            rows.append(dict(item, bytes=len(data), sha256=b.sha(data)))
        native_summary = b.ROOT / 'scripts/management/native_summary.py'
        total = sum(row['bytes'] for row in rows) + native_summary.stat().st_size
        assert total < 32 * 1024**2
        manifest['recipes'].append(dict(run_id=recipe['run_id'], inputs=rows,
            package_bytes_with_current_auto_native_summary=total,
            recipe_sha256=b.sha(outputs['recipes/' + recipe['test_conditions']['history'] + '.yaml'])))
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
            assert target.read_bytes() == data, 'managed proposal differs: ' + name
        elif args.check:
            raise AssertionError('missing managed proposal: ' + name)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    print(json.dumps(dict(files=len(outputs), recipes=2, collection_cap_mib=32,
        registered=False, remote=False)))


if __name__ == '__main__':
    main()
