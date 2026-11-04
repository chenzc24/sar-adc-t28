"""Managed analysis-only native-voltage export; Python 2.7/3 stdlib wrapper.

Only a new run's derived directory is writable. Source native results are read
as a prefix stream, never loaded or resimulated. Parent owns remote dispatch.
"""
from __future__ import print_function

import argparse
import hashlib
import json
import os
import subprocess
import sys


def read_json(path):
    with open(path) as handle:
        return json.load(handle)


def sha(path, count=None):
    digest = hashlib.sha256()
    remaining = count
    with open(path, 'rb') as handle:
        while remaining is None or remaining > 0:
            block = handle.read(1024 * 1024 if remaining is None else min(1024 * 1024, remaining))
            if not block:
                if remaining not in (None, 0):
                    raise ValueError('Source prefix ended before declared byte count')
                break
            digest.update(block)
            if remaining is not None:
                remaining -= len(block)
    return digest.hexdigest()


def inside(root, path):
    return path.startswith(root + os.sep)


def stat_identity(path):
    value = os.stat(path)
    return dict(size_bytes=value.st_size, mtime_s=value.st_mtime,
                inode=value.st_ino, device=value.st_dev)


def write_new(path, value):
    if os.path.exists(path):
        raise ValueError('Preserve existing output: ' + path)
    with open(path, 'w') as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')


def validate_paths(run_dir, output_dir, source_run_dir):
    run, output, source = [os.path.realpath(x) for x in (run_dir, output_dir, source_run_dir)]
    if run == source or inside(source, run) or inside(run, source):
        raise ValueError('Analysis run and source must be separate directories')
    if output != os.path.join(run, 'derived') or inside(source, output):
        raise ValueError('Output must be exactly the new run derived directory')
    if not os.path.isdir(os.path.join(run, 'inputs')) or not os.path.isdir(source):
        raise ValueError('Managed input/source directory missing')
    if os.path.exists(output) and os.listdir(output):
        raise ValueError('New derived directory must be empty; preserve prior attempts')
    return run, output, source


def source_preflight(source, config):
    if os.path.basename(source) != config['source_run_id']:
        raise ValueError('Exact source run identity mismatch')
    recipe = read_json(os.path.join(source, 'recipe.json'))
    registration = read_json(os.path.join(source, 'registered.json'))
    state_path = os.path.join(source, 'simulation.state.json')
    state = read_json(state_path)
    fingerprint = hashlib.sha256(json.dumps(recipe, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if (recipe.get('run_id') != config['source_run_id'] or recipe.get('kind', 'simulation') != 'simulation'
            or fingerprint != config['source_recipe_hash']
            or registration.get('recipe_hash') != fingerprint or not registration.get('files_complete')):
        raise ValueError('Source immutable recipe/registration mismatch')
    native = state.get('native', {})
    if (state.get('status') != 'complete' or state.get('exit_code') != 0
            or not native.get('native_analysis_pass') or not native.get('zero_error_footer')):
        raise ValueError('Source native simulation has not successfully completed')
    inputs = {}
    for name, expected in config['source_input_sha256'].items():
        if '/' in name or '\\' in name:
            raise ValueError('Source input must be a frozen basename')
        path = os.path.realpath(os.path.join(source, 'inputs', name))
        if not inside(source, path) or sha(path) != expected:
            raise ValueError('Frozen source SHA256 mismatch: ' + name)
        inputs[name] = dict(sha256=expected, stat=stat_identity(path))
    with open(os.path.join(source, 'inputs', 'test.scs')) as handle:
        saved = set(line.split()[1] for line in handle if line.startswith('save '))
    for item in config['signals']:
        if item['frozen_save_name'] not in saved:
            raise ValueError('Required native voltage was not declared saved: ' + item['frozen_save_name'])
    raw_dir = os.path.join(source, 'raw')
    files = [os.path.realpath(os.path.join(raw_dir, x)) for x in os.listdir(raw_dir) if x.endswith('.tran.tran')]
    if len(files) != 1 or not inside(source, files[0]) or not os.path.isfile(files[0]):
        raise ValueError('Expected one contained native ASCII transient file')
    small = dict((name, sha(os.path.join(source, name))) for name in
                 ('recipe.json', 'registered.json', 'simulation.state.json'))
    return files[0], dict(run_id=config['source_run_id'], recipe_hash=fingerprint,
                         input_files=inputs, small_file_sha256=small, raw_stat_before=stat_identity(files[0]))


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-dir', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--source-run-dir', required=True)
    args = parser.parse_args(argv)
    run, output, source = validate_paths(args.run_dir, args.output_dir, args.source_run_dir)
    inp = os.path.join(run, 'inputs')
    manifest_path = os.path.join(inp, 'native_export_manifest.json')
    config = read_json(manifest_path)
    if (config['history_start_s'] != 0 or len(config['signals']) != 25
            or sum(bool(x['primary_boundary_series']) for x in config['signals']) != 10
            or len(set(x['native_match_name'] for x in config['signals'])) != len(config['signals'])):
        raise ValueError('Unexpected frozen export selection')
    if (config['max_parser_output_bytes'] > 30 * 1024 ** 2
            or config['max_collected_directory_bytes'] >= 32 * 1024 ** 2
            or config['max_runtime_rss_kib'] > 256 * 1024):
        raise ValueError('Export resource bounds exceed authorized ceiling')
    raw, provenance = source_preflight(source, config)
    if not os.path.exists(output):
        os.mkdir(output)
    selected_path = os.path.join(output, 'selected_native.txt')
    with open(selected_path, 'w') as handle:
        handle.write('\n'.join(x['native_match_name'] for x in config['signals']) + '\n')
    executable = os.path.join(output, 'native_stream.exe' if os.name == 'nt' else 'native_stream')
    cpp = os.path.join(inp, 'stream_native_boundary.cpp')
    command = ['g++', '-O2', '-std=c++11', cpp, '-o', executable]
    if os.name == 'nt':
        command += ['-lpsapi']
    subprocess.check_call(command)
    subprocess.check_call([executable, raw, selected_path, output,
        repr(config['history_stop_s']), repr(config['diagnostic_start_s']), repr(config['diagnostic_stop_s']),
        str(config['max_parser_output_bytes']), str(config['max_runtime_rss_kib'])])
    meta = read_json(os.path.join(output, 'native_export.meta.json'))
    if not meta['requested_prefix_covered'] or meta['interpolated_points'] or meta['decimated_points']:
        raise ValueError('Native-point export integrity failure')
    if meta['parser_peak_rss_kib'] > config['max_runtime_rss_kib']:
        raise ValueError('Parser RSS bound exceeded')
    row_bytes = meta['columns'] * 8
    for name, count in (('boundary.native.bin', meta['points']), ('peak.native.bin', meta['diagnostic_points'])):
        if os.path.getsize(os.path.join(output, name)) != count * row_bytes:
            raise ValueError('Native binary shape mismatch: ' + name)
    provenance.update(raw_path=raw, raw_stat_after=stat_identity(raw),
        consumed_native_prefix_bytes=meta['consumed_source_prefix_bytes'],
        consumed_native_prefix_sha256=sha(raw, meta['consumed_source_prefix_bytes']),
        prefix_hash_scope='Exact ASCII bytes consumed by parser; not the unconsumed full raw file',
        manifest_sha256=sha(manifest_path), parser_source_sha256=sha(cpp),
        wrapper_source_sha256=sha(os.path.realpath(__file__)))
    if provenance['raw_stat_before'] != provenance['raw_stat_after']:
        raise ValueError('Source raw changed during extraction')
    for name, expected in provenance['small_file_sha256'].items():
        if sha(os.path.join(source, name)) != expected:
            raise ValueError('Source metadata changed during extraction')
    for name, item in provenance['input_files'].items():
        if sha(os.path.join(source, 'inputs', name)) != item['sha256']:
            raise ValueError('Source frozen input changed during extraction')
    if stat_identity(raw) != provenance['raw_stat_after']:
        raise ValueError('Source raw changed during prefix hashing')
    provenance['source_readonly_checks_pass'] = True
    write_new(os.path.join(output, 'source_readonly_provenance.json'), provenance)
    columns = [dict(index=0, name='time', unit='s')] + [
        dict(index=i + 1, name=item['native_match_name'], unit='V',
             role=item['role'], primary_boundary_series=item['primary_boundary_series'])
        for i, item in enumerate(config['signals'])]
    write_new(os.path.join(output, 'boundary.columns.json'), dict(
        binary_format='little-endian float64 rows', columns=columns,
        input_points='Original native solver points; no interpolation or time conversion',
        witness_only_outputs=['xdut.comp_p', 'xdut.comp_n', 'xdut.xctrl.xtim.wd']))
    peak = read_json(os.path.join(output, 'peak_summary.json'))['signals'][config['expected_peak']['signal']]
    delta = dict(value_v=peak['max_v'] - config['expected_peak']['value_v'],
                 time_s=peak['max_time_s'] - config['expected_peak']['time_s'],
                 reproduction_accepted=None, reason='Acceptance tolerances remain unallocated')
    files = dict((name, dict(bytes=os.path.getsize(os.path.join(output, name)), sha256=sha(os.path.join(output, name))))
                 for name in os.listdir(output) if os.path.isfile(os.path.join(output, name)))
    total = sum(item['bytes'] for item in files.values())
    if total + 64 * 1024 > config['max_collected_directory_bytes']:
        raise ValueError('Collected export directory would exceed authorized bound')
    result = dict(analysis_complete=True, source_run_id=config['source_run_id'],
        export_only=True, circuit_changed=False, simulation_started=False,
        points=meta['points'], diagnostic_points=meta['diagnostic_points'],
        parser_peak_rss_kib=meta['parser_peak_rss_kib'], peak_difference=delta,
        files=files, source_END_scanned=meta['source_END_observed'],
        source_completed_simulation_verified=True,
        output_limit_bytes=config['max_collected_directory_bytes'],
        missing_required_signals=[], acceptance_pass=None)
    write_new(os.path.join(output, 'result.json'), result)
    print('ANALYSIS_ONLY_NATIVE_EXPORT_OK', meta['points'], 'parser_RSS_KiB', meta['parser_peak_rss_kib'])


if __name__ == '__main__':
    main()
