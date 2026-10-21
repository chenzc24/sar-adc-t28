"""Reattach collection to cf76d807 only; no native launch path exists here."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time

import b_dynamic_512 as flow

REMOTE = flow.short.hf.REMOTE_BASE + '/cf76d807'
CONTROL = REMOTE + '/recovery_v1'
NATIVE_PID = 4639
RAW = REMOTE + '/b_dynamic_512.raw/tran_b_sine.tran.tran'
PACKED = CONTROL + '/full.tran.tran.gz'
BLOCK = 2**20
RANGE_BYTES = 64 * BLOCK
NO_WINDOW = dict(creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))


def now(): return datetime.now(timezone.utc).isoformat()


def client():
    from virtuoso_bridge.transport.tunnel import SSHClient
    ssh = SSHClient.from_env(profile='t28_io')
    assert (ssh.spectre_runner.host, ssh.spectre_runner.user) == ('thu-wei', 'chenzc_intern25')
    ssh.spectre_runner._verbose = False
    return ssh


def query(command):
    """Bounded reconnects for idempotent read-only queries only."""
    error = None
    for attempt in range(3):
        ssh = client()
        try:
            result = ssh.spectre_runner.run_command(command, timeout=30)
            if result.returncode == 0: return result.stdout
            error = RuntimeError(result.stderr[-1500:])
        except (OSError, subprocess.TimeoutExpired) as exc:
            error = exc
        finally: ssh.close()
        if attempt < 2: time.sleep(2)
    raise RuntimeError('Three fresh SSH query attempts failed') from error


def identity():
    ctx = flow.read(flow.OUT / 'context.json')
    expected = {Path(p).name: digest for p, digest in ctx['include_sha256'].items()}
    expected[flow.DECK.name] = ctx['deck_sha256']
    assert len(expected) == len(ctx['include_sha256']) + 1
    command = 'hostname -s; ps -p 4639 -ww -o pid=,comm=,args=; '
    command += 'if test -r /proc/4639/stat; then cat /proc/4639/stat; fi; sha256sum '
    command += ' '.join(shlex.quote(REMOTE + '/' + p) for p in expected)
    text = query(command)
    assert text.splitlines()[0] == 'thu-wei'
    hashes = {Path(p).name: h for h, p in re.findall(r'(?m)^([0-9a-f]{64})  (.+)$', text)}
    assert hashes == expected, 'Remote frozen source hash mismatch'
    proc = next((s for s in text.splitlines() if re.match(r'\s*4639\s+spectre\s', s)), None)
    if proc: assert REMOTE + '/' + flow.NAME + '.scs' in proc
    stat = next((s for s in text.splitlines() if s.startswith('4639 (')), None)
    ticks = int(stat.rsplit(')', 1)[1].split()[19]) if stat else None
    evidence = dict(checked_utc=now(), host='thu-wei', native_pid=NATIVE_PID,
        exact_root=REMOTE, native_alive=bool(proc), process_start_ticks=ticks,
        remote_source_sha256=hashes, same_native_job=True, native_restarted=False)
    flow.dump(flow.OUT / 'recovery_identity.json', evidence)
    return evidence


def complete_gate(progress, log):
    """No compression while live, incomplete, duplicated or explicitly failed."""
    assert not any(p['command'] == 'spectre' for p in progress['native_processes']), 'Native still running'
    rows = re.findall(r'R3MEAS,(\d+),(\d+),(\d+),(\d+),(\d+),([^\s,]+)', log)
    probes = re.findall(r'BSINE,(\d+),([^\s,]+),([^\s,]+),([^\s,]+)', log)
    assert [int(r[0]) for r in rows] == list(range(516)), 'Incomplete/duplicate frame history'
    assert [int(r[0]) for r in probes] == list(range(516)), 'Incomplete/duplicate probe history'
    assert all(r[2] == '8' and r[4] == '1' and r[1] == r[3] for r in rows)
    assert all(math.isfinite(float(v)) for r in probes for v in r[1:])
    assert re.search(r'(?m)^spectre completes with 0 errors,', log), 'No normal native footer'
    # Also used by the offline reducer's NumPy environment, which deliberately
    # does not install the bridge. Match the bridge's fatal/convergence gates
    # without importing a simulator runtime into offline analysis.
    lower = log.lower()
    assert not any(s in lower for s in ('spcrtrf-15044', 'failed to converge',
        'convergence failed', 'convergence failure', 'fatal error'))
    assert not re.search(r'(?im)^\s*error\s*\(', log)
    assert not progress['clear_anomaly_reasons']
    return True


def download_ranges(remote_path, target, size, digest, fetch, chunk_bytes=RANGE_BYTES):
    """Checkpoint accepted byte ranges; a disconnect never appends partial data."""
    target = Path(target)
    assert target.resolve().is_relative_to(flow.OUT.resolve())
    target.parent.mkdir(parents=True, exist_ok=True)
    state_path = target.with_suffix(target.suffix + '.checkpoint.json')
    partial = target.with_suffix(target.suffix + '.partial')
    chunk = target.with_suffix(target.suffix + '.range')
    if target.exists():
        assert target.stat().st_size == size and flow.sha(target) == digest
        return
    if state_path.exists():
        state = flow.read(state_path)
        assert (state['remote_path'], state['gzip_bytes'], state['gzip_sha256']) == (remote_path, size, digest)
        assert state['chunk_bytes'] == chunk_bytes
    else:
        assert not partial.exists(), 'Unbound partial archive must not be overwritten'
        state = dict(remote_path=remote_path, gzip_bytes=size, gzip_sha256=digest,
            chunk_bytes=chunk_bytes, downloaded_bytes=0, ranges=[])
        flow.dump(state_path, state)
    offset = 0
    if partial.exists():
        with partial.open('r+b') as stream:
            for row in state['ranges']:
                assert row['offset'] == offset
                block = stream.read(row['bytes'])
                assert len(block) == row['bytes'] and hashlib.sha256(block).hexdigest() == row['sha256']
                offset += len(block)
            assert offset == state['downloaded_bytes']
            # Discard only this bound generated archive's uncommitted crash tail.
            stream.truncate(offset)
    else:
        assert state['downloaded_bytes'] == 0
    assert shutil.disk_usage(flow.ROOT).free > size - offset + 12 * 2**30
    started = time.monotonic()
    while offset < size:
        assert time.monotonic() - started < 21600, 'Transfer time budget exhausted; checkpoint preserved'
        length = min(chunk_bytes, size - offset)
        for attempt in range(3):
            try:
                fetch(remote_path, offset, length, chunk)
                assert chunk.stat().st_size == length, 'Wrong byte-range length'
                break
            except (OSError, subprocess.TimeoutExpired, RuntimeError, AssertionError):
                if attempt == 2: raise
                time.sleep(2)
        chunk_hash = flow.sha(chunk)
        with partial.open('ab') as dest, chunk.open('rb') as source:
            shutil.copyfileobj(source, dest, length=BLOCK)
            dest.flush(); os.fsync(dest.fileno())
        state['ranges'].append(dict(offset=offset, bytes=length, sha256=chunk_hash))
        offset += length
        state.update(downloaded_bytes=offset, checked_utc=now())
        flow.dump(state_path, state)
    assert flow.sha(partial) == digest, 'Full downloaded gzip SHA differs; no analysis permitted'
    partial.replace(target)


def fetch_range(remote_path, offset, length, target):
    assert remote_path in (PACKED, CONTROL + '/fixture.bin') and offset % BLOCK == 0
    ssh = client()
    try:
        runner = ssh.spectre_runner
        assert runner.backend == 'openssh'
        # Verified bridge argv builder preserves exact profile/key/jump options.
        argv = runner._build_ssh_base()
        argv[1:1] = ['-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=3']
    finally: ssh.close()
    command = f'dd if={shlex.quote(remote_path)} bs={BLOCK} skip={offset // BLOCK} count={math.ceil(length / BLOCK)} 2>/dev/null'
    with Path(target).open('wb') as dest:
        result = subprocess.run(argv + ['sh', '-l'], input=command.encode(), stdout=dest,
            stderr=subprocess.PIPE, timeout=180, **NO_WINDOW)
    if result.returncode != 0: raise RuntimeError(result.stderr.decode(errors='replace')[-1000:])


def pack_and_collect(progress):
    log = query('cat ' + REMOTE + '/spectre.out')
    complete_gate(progress, log)
    # Raw must be stable and enough headroom must remain even for incompressible gzip.
    values = query(f'stat -c %s {RAW}; df -Pk /tmp').splitlines()
    raw_bytes = int(values[0]); free = int(values[-1].split()[3]) * 1024
    assert free > raw_bytes + 12 * 2**30
    ssh = client()
    try:
        r = ssh.spectre_runner.run_command('mkdir -p ' + CONTROL, timeout=25)
        assert r.returncode == 0
        worker = (Path(__file__).with_name('b_dynamic_512_pack.sh')).read_text(encoding='utf-8')
        r = ssh.spectre_runner.upload_text(worker, CONTROL + '/pack.sh', timeout=30)
        assert r.returncode == 0
        # Exclusive worker lock makes even an uncertain launch safe, not a gzip rerun.
        command = f'if test ! -d {CONTROL}/lock; then nohup sh {CONTROL}/pack.sh {REMOTE} {CONTROL} >> {CONTROL}/pack.log 2>&1 < /dev/null & fi'
        r = ssh.spectre_runner.run_command(command, timeout=25)
        assert r.returncode == 0, r.stderr
    finally: ssh.close()
    flow.stage('compressing_native', total_frames=516, recovered=True)
    started = time.monotonic()
    while True:
        text = query(f'if test -f {CONTROL}/done; then echo DONE; cat {CONTROL}/hashes {CONTROL}/raw_bytes {CONTROL}/gzip_bytes; '
            f'elif test -f {CONTROL}/failed; then echo FAILED; cat {CONTROL}/failed; else echo PACKING; '
            f'if test -f {CONTROL}/lock/pid; then ps -p "$(cat {CONTROL}/lock/pid)" -ww -o comm=,args=; fi; '
            f'stat -c %s {PACKED}.part 2>/dev/null; fi; true')
        if text.startswith('DONE\n'): break
        assert not text.startswith('FAILED\n'), text
        assert time.monotonic() - started < 21600, 'Packing exceeded budget; never restart automatically'
        assert time.monotonic() - started < 90 or CONTROL + '/pack.sh' in text, 'Packing worker disappeared; no automatic restart'
        flow.dump(flow.OUT / 'recovery_pack_progress.json', dict(checked_utc=now(), state=text.strip()))
        time.sleep(30)
    hashes = {p: h for h, p in re.findall(r'(?m)^([0-9a-f]{64})  (.+)$', text)}
    assert set(hashes) == {RAW, PACKED}
    raw_size, gzip_size = map(int, text.splitlines()[-2:])
    assert raw_size == raw_bytes
    target = flow.OUT / 'spectre/b_dynamic_512.raw/full.tran.tran.gz'
    flow.dump(flow.OUT / 'recovery_pack_receipt.json', dict(checked_utc=now(), remote_raw=RAW,
        remote_gzip=PACKED, raw_sha256=hashes[RAW], gzip_sha256=hashes[PACKED], gzip_bytes=gzip_size))
    flow.stage('downloading_lossless', total_frames=516, compressed_bytes=gzip_size, recovered=True)
    download_ranges(PACKED, target, gzip_size, hashes[PACKED], fetch_range)
    flow.dump(flow.OUT / 'raw_receipt.json', dict(remote_raw=RAW, remote_gzip=PACKED,
        raw_sha256=hashes[RAW], gzip_sha256=hashes[PACKED], gzip_bytes=gzip_size,
        local_gzip=str(target), lossless=True, remote_original_retained=True, recovered=True))
    (flow.OUT / 'spectre/spectre.out').write_text(log, encoding='utf-8')
    from virtuoso_bridge.spectre.runner import _SpectreRunResult, _build_simulation_result
    # The disconnected original SSH wait's OS status cannot be recovered.
    # Keep its execution contract PARTIAL, not a fabricated successful rc=0.
    metadata = dict(native_os_exit_status=None, original_transport_failed=True,
        native_normal_footer_verified=True, recovered_capture_complete=True,
        exact_root=REMOTE, native_pid=NATIVE_PID)
    assembled = _build_simulation_result(_SpectreRunResult(False, target.parent, -1,
        log, '', 'Original native OS exit status lost with SSH', metadata), None, metadata)
    flow.dump(flow.OUT / 'result.json', dict(ok=assembled.ok, errors=assembled.errors,
        warnings=assembled.warnings, metadata=assembled.metadata, recovery_capture_complete=True,
        deck_sha256=flow.read(flow.OUT / 'context.json')['deck_sha256']))
    assert not assembled.ok, 'Must not silently upgrade disconnected execution contract'


def watch():
    assert not (flow.OUT / 'interruption.json').exists()
    assert flow.read(flow.OUT / 'flow.json')['stage'] == 'failed', 'Explicit recovery only'
    os.close(os.open(flow.OUT / 'recovery_watch.lock', os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    flow.check()
    evidence = identity()
    flow.dump(flow.OUT / 'recovery_launch.json', dict(local_pid=os.getpid(), started_utc=now(),
        original_launch=flow.read(flow.OUT / 'launch.json'), identity=evidence,
        recovery_script_sha256=flow.sha(__file__), native_launch_attempted=False))
    flow.stage('running_native_recovered', total_frames=516, original_native_pid=NATIVE_PID)
    errors, started = 0, time.monotonic()
    try:
        while True:
            try:
                progress = flow.status()
                processes = [p for p in progress['native_processes'] if p['command'] == 'spectre']
                assert all(p['pid'] == NATIVE_PID for p in processes), 'Unexpected native identity'
                current = identity()
                if current['native_alive'] and evidence['native_alive']:
                    assert current['process_start_ticks'] == evidence['process_start_ticks'], 'Original PID was reused'
                errors = 0
            except Exception as exc:
                errors += 1
                flow.dump(flow.OUT / 'recovery_query_error.json', dict(utc=now(), consecutive=errors, error=repr(exc)))
                if errors >= 3: raise
                time.sleep(30); continue
            if progress['clear_anomaly_reasons']:
                if processes and not (flow.OUT / 'interruption.json').exists():
                    flow.stop_owned('; '.join(progress['clear_anomaly_reasons']))
                raise RuntimeError(progress['clear_anomaly_reasons'])
            if not processes: break
            assert time.monotonic() - started < 129600, 'Reattachment time budget exhausted; no native restart'
            time.sleep(40); time.sleep(40); time.sleep(40)
        pack_and_collect(progress)
        flow.stage('reducing_full_waveform', total_frames=516, recovered=True)
        subprocess.run([str(flow.ROOT / '.venv/Scripts/python.exe'), str(Path(__file__).with_name('b_dynamic_512_reduce.py'))], cwd=flow.ROOT, check=True, **NO_WINDOW)
        flow.stage('analyzing_batch', total_frames=516, recovered=True)
        subprocess.run([str(flow.ROOT / '.venv/Scripts/python.exe'), str(Path(__file__).with_name('b_dynamic_512_analyze.py'))], cwd=flow.ROOT, check=True, **NO_WINDOW)
        flow.stage('awaiting_visual_review', total_frames=516, recovered=True)
    except Exception as exc:
        flow.stage('failed', error=repr(exc), recovered=True, no_automatic_retry=True)
        raise


def fixture():
    """Small generated transfer only, under the exact already-owned scratch."""
    payload = 'SAR_B512_RECOVERY_FIXTURE\n' * 60000
    ssh = client()
    try:
        assert ssh.spectre_runner.run_command('mkdir -p ' + CONTROL, timeout=25).returncode == 0
        assert ssh.spectre_runner.upload_text(payload, CONTROL + '/fixture.bin', timeout=30).returncode == 0
        worker = Path(__file__).with_name('b_dynamic_512_pack.sh').read_text(encoding='utf-8')
        assert ssh.spectre_runner.upload_text(worker, CONTROL + '/syntax_check.sh', timeout=30).returncode == 0
    finally: ssh.close()
    query('sh -n ' + CONTROL + '/syntax_check.sh')
    target = flow.OUT / 'recovery_fixture.bin'
    download_ranges(CONTROL + '/fixture.bin', target, len(payload.encode()), hashlib.sha256(payload.encode()).hexdigest(), fetch_range, BLOCK)
    flow.dump(flow.OUT / 'recovery_fixture.json', dict(bytes=len(payload.encode()),
        sha256=flow.sha(target), roundtrip_pass=True, pack_shell_syntax_pass=True, native_launch_attempted=False))
    print('EXACT_SCRATCH_SMALL_RANGE_TRANSFER_AND_SHELL_SYNTAX_PASS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['inspect', 'fixture', 'watch'])
    action = parser.parse_args().action
    if action == 'inspect': print(json.dumps(identity(), indent=2))
    else: globals()[action]()
