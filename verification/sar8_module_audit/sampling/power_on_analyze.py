"""Python2/3 bounded wrapper around the frozen native reducer; no simulation."""
from __future__ import print_function
import argparse
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zlib

CHUNK = 1024 * 1024
SMALL_FILES = ['failing_pairs.json', 'wave.columns', 'wave.events.tsv',
               'wave.extrema.tsv', 'wave.meta.json', 'wave.products.tsv', 'wave.stress.tsv']
ROOT_FILES = ['simulation.state.json', 'analysis.state.json', 'simulation.admission.json',
              'analysis.admission.json', 'spectre.out', 'raw/logStatus', 'source_provenance.json']


def sha(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(CHUNK), b''):
            digest.update(block)
    return digest.hexdigest()


def write_new(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)


def write_json(path, value):
    write_new(path, (json.dumps(value, indent=2, sort_keys=True) + '\n').encode('utf-8'))


def gzip_stream(source, target, compressed_cap):
    """No whole-wave array; keep source and reject before exceeding the cap."""
    encoder = zlib.compressobj(6, zlib.DEFLATED, 31)
    raw_sha, zipped_sha = hashlib.sha256(), hashlib.sha256()
    raw_bytes, zipped_bytes = 0, 0
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with open(source, 'rb') as inp, os.fdopen(fd, 'wb') as out:
        for block in iter(lambda: inp.read(CHUNK), b''):
            raw_sha.update(block)
            raw_bytes += len(block)
            encoded = encoder.compress(block)
            if zipped_bytes + len(encoded) > compressed_cap:
                raise ValueError('Compressed waveform exceeds delivery cap; retain raw work')
            out.write(encoded)
            zipped_sha.update(encoded)
            zipped_bytes += len(encoded)
        encoded = encoder.flush()
        if zipped_bytes + len(encoded) > compressed_cap:
            raise ValueError('Compressed waveform exceeds delivery cap at flush; retain raw work')
        out.write(encoded)
        zipped_sha.update(encoded)
        zipped_bytes += len(encoded)
    # Bounded independent gzip read verifies footer/CRC and exact original bytes.
    check, checked_bytes = hashlib.sha256(), 0
    with gzip.open(target, 'rb') as check_stream:
        for block in iter(lambda: check_stream.read(CHUNK), b''):
            checked_bytes += len(block)
            if checked_bytes > raw_bytes:
                raise ValueError('Gzip verification expanded beyond source')
            check.update(block)
    if checked_bytes != raw_bytes or check.hexdigest() != raw_sha.hexdigest():
        raise ValueError('Gzip roundtrip mismatch')
    if sha(source) != raw_sha.hexdigest():
        raise ValueError('Source changed during compression')
    return dict(file='wave.bin.gz', format='gzip of unchanged little-endian f64 compact binary',
        compressed_bytes=zipped_bytes, compressed_sha256=zipped_sha.hexdigest(),
        uncompressed_bytes=raw_bytes, uncompressed_sha256=raw_sha.hexdigest(),
        roundtrip_verified=True, source_retained=True, extra_decimation=False,
        analog_export_spacing_s=20e-12, full_native_analog_wave_claim=False)


def validate_inputs(inputs, config):
    for name, expected in config['input_sha256'].items():
        if '/' in name or '\\' in name or name.startswith('.'):
            raise ValueError('Unexpected input member')
        if sha(os.path.join(inputs, name)) != expected:
            raise ValueError('Frozen input hash mismatch: ' + name)
    if sha(os.path.join(inputs, 'test.scs')) not in config['allowed_test_sha256']:
        raise ValueError('Deck hash is not an accepted startup control')


def make_delivery(native, publish, config):
    """Create a private complete delivery; caller publishes only after success."""
    if os.path.exists(publish):
        raise ValueError('Do not overwrite an existing delivery')
    os.mkdir(publish, 0o700)
    source_files = SMALL_FILES + ['result.json', 'wave.bin']
    before = {name: sha(os.path.join(native, name)) for name in source_files}
    with open(os.path.join(native, 'result.json')) as stream:
        result = json.load(stream)
    with open(os.path.join(native, 'wave.meta.json')) as stream:
        meta = json.load(stream)
    with open(os.path.join(native, 'wave.columns')) as stream:
        columns = stream.read().splitlines()
    if not (result['analysis_complete'] and meta['PSF_END'] and
            result['stress_all_native_points'] and result['events_all_native_points'] and
            result['all_MOS_pairs'] == 1422 and meta['columns'] == len(columns) == 294 and
            meta['native_points'] >= meta['points'] > 0 and
            abs(meta['last_time_s'] - config['stop_s']) < 1e-15):
        raise ValueError('Incomplete native reducer provenance')
    size = os.path.getsize(os.path.join(native, 'wave.bin'))
    if size != meta['points'] * len(columns) * 8 or size > config['binary_bound_bytes']:
        raise ValueError('Unexpected binary shape or size')
    compression = gzip_stream(os.path.join(native, 'wave.bin'),
        os.path.join(publish, 'wave.bin.gz'), config['derived_cap_bytes'])
    compression.update(rows=meta['points'], columns=len(columns),
        native_points=meta['native_points'], native_stress_records=1422,
        native_events_all_points=True, native_stress_all_points=True)
    write_json(os.path.join(publish, 'wave.compression.json'), compression)
    for name in SMALL_FILES:
        shutil.copyfile(os.path.join(native, name), os.path.join(publish, name))
    shutil.copyfile(os.path.join(native, 'result.json'), os.path.join(publish, 'native_result.json'))
    result.update(wave_compression=compression, native_energy_after200ns_available=False,
        startup_accuracy_pass=None, POR_qualified=False,
        collection_budget=dict(hard_cap_bytes=config['collection_cap_bytes'],
            derived_cap_bytes=config['derived_cap_bytes'], root_reserved_bytes=config['root_reserved_bytes'],
            require_collected_receipt_no_skips=True),
        artifact_scope='existing20ps selected binary losslessly compressed; all native stress/events retained')
    write_json(os.path.join(publish, 'result.json'), result)
    entries = [dict(name=name, bytes=os.path.getsize(os.path.join(publish, name)),
                    sha256=sha(os.path.join(publish, name))) for name in sorted(os.listdir(publish))]
    write_json(os.path.join(publish, 'delivery_manifest.json'), dict(files_excluding_this_manifest=entries,
        native_source_sha256=before, collection_cap_bytes=config['collection_cap_bytes'],
        derived_cap_bytes=config['derived_cap_bytes'], root_reserved_bytes=config['root_reserved_bytes'],
        incomplete_delivery_must_not_be_collected_as_success=True))
    total = sum(os.path.getsize(os.path.join(publish, name)) for name in os.listdir(publish))
    if total > config['derived_cap_bytes'] or total + config['root_reserved_bytes'] > config['collection_cap_bytes']:
        raise ValueError('Complete delivery exceeds32MiB budget; no evidence discarded')
    if before != {name: sha(os.path.join(native, name)) for name in source_files}:
        raise ValueError('Native generated sources changed')
    return dict(derived_bytes=total, compressed_bytes=compression['compressed_bytes'],
                uncompressed_bytes=size, native_points=meta['native_points'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-dir', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    run = os.path.realpath(args.run_dir)
    out = os.path.realpath(args.output_dir)
    if not out.startswith(run + os.sep) or os.listdir(out):
        raise ValueError('Expected empty derived directory in this new run')
    inputs = os.path.join(run, 'inputs')
    with open(os.path.join(inputs, 'compression_config.json')) as stream:
        config = json.load(stream)
    if (config['collection_cap_bytes'] != 32 * 1024**2 or
            config['derived_cap_bytes'] != 31 * 1024**2 or
            config['root_reserved_bytes'] != 1024**2):
        raise ValueError('Collection hard cap must remain32MiB')
    validate_inputs(inputs, config)
    root_bytes = sum(os.path.getsize(os.path.join(run, name)) for name in ROOT_FILES
                     if os.path.isfile(os.path.join(run, name)))
    if root_bytes + 64 * 1024 > config['root_reserved_bytes']:
        raise ValueError('Managed root evidence exceeds reserved budget')
    work = tempfile.mkdtemp(prefix='startup-reduce-', dir=run)
    native = os.path.join(work, 'native')
    os.mkdir(native, 0o700)
    subprocess.check_call([sys.executable, os.path.join(inputs, 'loaded_remote.py'),
        '--run-dir', run, '--output-dir', native])
    publish = os.path.join(work, 'delivery')
    summary = make_delivery(native, publish, config)
    # result.json is published last so an interrupted publication cannot pass.
    for name in sorted(n for n in os.listdir(publish) if n != 'result.json') + ['result.json']:
        os.rename(os.path.join(publish, name), os.path.join(out, name))
    print('PACK_OK', json.dumps(summary, sort_keys=True), 'raw_work_retained', work)


if __name__ == '__main__':
    main()
