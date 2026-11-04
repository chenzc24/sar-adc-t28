"""Verify a collected compressed delivery and decode it with bounded memory."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil

CHUNK = 1024 * 1024


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(CHUNK), b''):
            h.update(block)
    return h.hexdigest()


def decode_wave(archive, target, receipt):
    if archive.stat().st_size != receipt['compressed_bytes'] or digest(archive) != receipt['compressed_sha256']:
        raise ValueError('Compressed waveform SHA/size mismatch')
    if not 0 < receipt['uncompressed_bytes'] <= 32 * 1024**2:
        raise ValueError('Unexpected uncompressed waveform budget')
    h, size = hashlib.sha256(), 0
    with gzip.open(archive, 'rb') as source, target.open('xb') as out:
        for block in iter(lambda: source.read(CHUNK), b''):
            size += len(block)
            if size > receipt['uncompressed_bytes']:
                raise ValueError('Wave expansion exceeds declared bound')
            out.write(block)
            h.update(block)
    if size != receipt['uncompressed_bytes'] or h.hexdigest() != receipt['uncompressed_sha256']:
        raise ValueError('Uncompressed waveform SHA/size mismatch')
    return dict(bytes=size, sha256=h.hexdigest(), lossless_verified=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('derived', type=Path)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    source = args.derived.resolve()
    target = args.output_dir.resolve()
    if target.exists() or target.is_relative_to(source.parent):
        raise ValueError('Use a new decode directory outside the immutable collection')
    receipt = json.loads((source.parent / 'collection_receipt.json').read_text())
    if receipt.get('skipped') or receipt['total_bytes'] > 32 * 1024**2:
        raise ValueError('Incomplete or oversized managed collection')
    for phase in ['simulation', 'analysis']:
        if receipt['status'][phase]['status'] != 'complete' or receipt['status'][phase]['exit_code'] != 0:
            raise ValueError('Managed phase incomplete: ' + phase)
    for item in receipt['files']:
        path = source.parent / item['name']
        if path.stat().st_size != item['bytes'] or digest(path) != item['sha256']:
            raise ValueError('Managed collection mismatch: ' + item['name'])
    delivery = json.loads((source / 'delivery_manifest.json').read_text())
    for item in delivery['files_excluding_this_manifest']:
        name = item['name']
        if '/' in name or '\\' in name or name.startswith('.'):
            raise ValueError('Unexpected delivery member')
        if (source / name).stat().st_size != item['bytes'] or digest(source / name) != item['sha256']:
            raise ValueError('Delivery mismatch: ' + name)
    wave = json.loads((source / 'wave.compression.json').read_text())
    if wave['file'] != 'wave.bin.gz' or wave['extra_decimation']:
        raise ValueError('Unexpected waveform representation')
    target.mkdir(parents=True)
    decoded = decode_wave(source / wave['file'], target / 'wave.bin', wave)
    for item in delivery['files_excluding_this_manifest']:
        name = item['name']
        if name != wave['file']:
            shutil.copyfile(source / name, target / name)
    print(json.dumps(decoded, indent=2))


if __name__ == '__main__':
    main()
