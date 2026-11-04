"""Source-bound supplementary native-voltage export; Python 2.7/3 stdlib.

Reuses reviewed immutable preflight/path/SHA helpers and C++ stream parser.
Writes only a fresh managed analysis run's derived directory. No simulation.
"""
from __future__ import print_function

import argparse
import hashlib
import json
import math
import os
import re
import subprocess

import native_boundary_export as common

STOP = 4.1590785650590448e-8
P = 'xdut.xctrl.xtim.'
SELECTIONS = {
    'sar8fix-loaded-both-ffcold': [P + n for n in ['sn', 'ud', 'write_req', 'x010.n',
        'x010.x000.mid', 'x014.n', 'x014.x000.mid', 'x001.n', 'x001.x000.mid']],
    'sar8audit-ctrl-first-event-v1': [P + n for n in ['sn', 'x001.n', 'x001.x000.mid']],
}


def validate_config(config):
    names = [item['native_match_name'] for item in config['signals']]
    if (config.get('schema_version') != 1 or config['source_run_id'] not in SELECTIONS
            or names != SELECTIONS[config['source_run_id']]
            or config['history_start_s'] != 0 or config['history_stop_s'] != STOP
            or not 0 <= config['diagnostic_start_s'] < config['diagnostic_stop_s'] == STOP
            or any(not item['required'] or item['role'] != 'voltage_witness_only' for item in config['signals'])):
        raise ValueError('Unexpected supplementary selection/window contract')
    if (set(config['source_input_sha256']) != {'dut.scs', 'test.scs'}
            or not re.match(r'^[a-f0-9]{64}$', config['source_recipe_hash'])
            or not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', config['source_analysis_name'])):
        raise ValueError('Invalid supplementary source binding')
    for key, ceiling in [('max_parser_output_bytes', 30 * 1024**2),
                         ('max_collected_directory_bytes', 32 * 1024**2 - 1),
                         ('max_runtime_rss_kib', 256 * 1024)]:
        if not isinstance(config[key], int) or not 0 < config[key] <= ceiling:
            raise ValueError('Export resource bound exceeds ceiling')


def all_source_inputs(source, recipe):
    """Also verify nested registered inputs such as v1's seven PWL files."""
    files = {}
    for item in recipe['files']:
        name = item['name']
        if (not re.match(r'^[A-Za-z0-9_.+/-]+$', name)
                or any(part in ('', '.', '..') for part in name.split('/')) or name in files):
            raise ValueError('Unsafe or duplicate registered source member')
        original = os.path.join(source, 'inputs', *name.split('/'))
        path = os.path.realpath(original)
        if (os.path.islink(original) or not common.inside(source, path)
                or not os.path.isfile(path) or os.path.getsize(path) != item['bytes']
                or common.sha(path) != item['sha256']):
            raise ValueError('Registered source input SHA/size mismatch: ' + name)
        files[name] = dict(sha256=item['sha256'], stat=common.stat_identity(path))
    if not files:
        raise ValueError('Source recipe has no registered inputs')
    return files


def check_coverage(meta, config):
    last, beyond = meta['last_exported_time_s'], meta['first_time_marker_beyond_s']
    stop = config['history_stop_s']
    if (not meta['requested_prefix_covered'] or meta['interpolated_points'] or meta['decimated_points']
            or not meta['points'] or not meta['diagnostic_points'] or meta['first_time_s'] != 0
            or not 0 <= last <= stop):
        raise ValueError('Supplementary native point/window integrity failure')
    if beyond is not None:
        if not beyond > stop or meta['source_END_observed']:
            raise ValueError('Invalid first-marker-beyond coverage proof')
        mode = 'native_time_marker_beyond_requested_stop'
    elif meta['source_END_observed'] and last == stop:
        mode = 'native_END_at_requested_stop'
    else:
        raise ValueError('Requested stop is not covered; do not invent an endpoint')
    return dict(requested_start_s=0., requested_stop_s=stop,
        actual_last_exported_native_time_s=last, first_time_marker_beyond_s=beyond,
        requested_stop_was_a_native_row=(last == stop), parser_END_observed=meta['source_END_observed'],
        coverage_mode=mode, all_native_rows_in_requested_interval_preserved=True,
        fabricated_endpoint=False, interpolation=False,
        note='A later marker proves prefix coverage without fabricating a stop row. A prefix marker is not a scanned full-source END.')


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-dir', required=True)
    ap.add_argument('--output-dir', required=True)
    ap.add_argument('--source-run-dir', required=True)
    args = ap.parse_args(argv)
    run, output, source = common.validate_paths(args.run_dir, args.output_dir, args.source_run_dir)
    inputs = os.path.join(run, 'inputs')
    manifest = os.path.join(inputs, 'supplement_manifest.json')
    config = common.read_json(manifest)
    validate_config(config)
    raw, provenance = common.source_preflight(source, config)
    recipe = common.read_json(os.path.join(source, 'recipe.json'))
    source_files = all_source_inputs(source, recipe)
    log = os.path.join(source, 'raw', 'logStatus')
    with open(log) as handle:
        if not re.search(r'\b' + re.escape(config['source_analysis_name']) + r'\s+PASS\b', handle.read()):
            raise ValueError('Exact source native analysis PASS missing')
    provenance['small_file_sha256']['raw/logStatus'] = common.sha(log)
    cpp = os.path.join(inputs, 'stream_native_boundary.cpp')
    helper = os.path.join(inputs, 'native_boundary_export.py')
    if (common.sha(cpp) != config['reviewed_parser_sha256']
            or common.sha(helper) != config['reviewed_helper_sha256']):
        raise ValueError('Reviewed parser/helper source hash mismatch')
    if not os.path.exists(output):
        os.mkdir(output)
    selected = os.path.join(output, 'selected_native.txt')
    with open(selected, 'w') as handle:
        handle.write('\n'.join(item['native_match_name'] for item in config['signals']) + '\n')
    executable = os.path.join(output, 'native_stream.exe' if os.name == 'nt' else 'native_stream')
    command = ['g++', '-O2', '-std=c++11', cpp, '-o', executable]
    if os.name == 'nt':
        command.append('-lpsapi')
    subprocess.check_call(command)
    subprocess.check_call([executable, raw, selected, output, repr(config['history_stop_s']),
        repr(config['diagnostic_start_s']), repr(config['diagnostic_stop_s']),
        str(config['max_parser_output_bytes']), str(config['max_runtime_rss_kib'])])
    meta = common.read_json(os.path.join(output, 'native_export.meta.json'))
    coverage = check_coverage(meta, config)
    if meta['parser_peak_rss_kib'] > config['max_runtime_rss_kib']:
        raise ValueError('Parser RSS exceeds authorized bound')
    if meta['columns'] != len(config['signals']) + 1:
        raise ValueError('Native column count mismatch')
    for name, count in [('boundary.native.bin', meta['points']), ('peak.native.bin', meta['diagnostic_points'])]:
        if os.path.getsize(os.path.join(output, name)) != count * meta['columns'] * 8:
            raise ValueError('Native binary size mismatch')
    prefix_bytes = meta['consumed_source_prefix_bytes']
    provenance.update(raw_path=raw, raw_stat_after=common.stat_identity(raw),
        all_registered_source_input_files=source_files,
        consumed_native_prefix_bytes=prefix_bytes,
        consumed_native_prefix_sha256=common.sha(raw, prefix_bytes),
        prefix_hash_scope='Exactly consumed ASCII prefix including the beyond marker or END; not a claim about unread remainder.',
        manifest_sha256=common.sha(manifest), parser_source_sha256=common.sha(cpp),
        helper_source_sha256=common.sha(helper), wrapper_source_sha256=common.sha(os.path.realpath(__file__)))
    if provenance['raw_stat_before'] != provenance['raw_stat_after']:
        raise ValueError('Source raw changed during export')
    for name, expected in provenance['small_file_sha256'].items():
        if common.sha(os.path.join(source, name)) != expected:
            raise ValueError('Source metadata changed during export')
    if source_files != all_source_inputs(source, recipe) or common.stat_identity(raw) != provenance['raw_stat_after']:
        raise ValueError('Source input/raw stat changed during export')
    provenance['source_readonly_checks_pass'] = True
    common.write_new(os.path.join(output, 'source_readonly_provenance.json'), provenance)
    common.write_new(os.path.join(output, 'coverage.json'), coverage)
    columns = [dict(index=0, name='time', unit='s')] + [dict(index=j+1,
        name=item['native_match_name'], unit='V', role='voltage_witness_only') for j, item in enumerate(config['signals'])]
    common.write_new(os.path.join(output, 'boundary.columns.json'), dict(columns=columns,
        binary_format='little-endian float64 rows; original native solver points; no interpolation/decimation',
        no_output_voltage_drive_authorized=True))
    files = {name: dict(bytes=os.path.getsize(os.path.join(output, name)), sha256=common.sha(os.path.join(output, name)))
             for name in os.listdir(output) if os.path.isfile(os.path.join(output, name))}
    if sum(item['bytes'] for item in files.values()) + 64 * 1024 > config['max_collected_directory_bytes']:
        raise ValueError('Complete derived directory would exceed collection cap')
    state = common.read_json(os.path.join(source, 'simulation.state.json'))
    result = dict(analysis_complete=True, source_run_id=config['source_run_id'],
        source_recipe_hash=config['source_recipe_hash'], source_completed_simulation_verified=True,
        source_native_analysis_PASS_verified=True, source_warning_codes=state.get('native', {}).get('warning_codes'),
        export_only=True, circuit_changed=False, simulation_started=False,
        points=meta['points'], diagnostic_points=meta['diagnostic_points'], parser_peak_rss_kib=meta['parser_peak_rss_kib'],
        selected_voltage_count=len(config['signals']), coverage=coverage, source_END_scanned=meta['source_END_observed'],
        files=files, missing_required_signals=[], acceptance_pass=None,
        scope='Supplementary native-voltage witnesses only; no physical reproduction or causal/ADC qualification')
    common.write_new(os.path.join(output, 'result.json'), result)
    print('SUPPLEMENT_NATIVE_EXPORT_OK', config['source_run_id'], meta['points'], coverage['coverage_mode'])


if __name__ == '__main__':
    main()
