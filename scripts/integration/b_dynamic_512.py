"""One frozen native B/1x coherent capture, bounded lossless storage and watch."""
from __future__ import annotations
import argparse
import dataclasses
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
import uuid
import yaml

import b_short_acceptance as short

ROOT = short.ROOT
OUT = ROOT / 'output/b_dynamic_512'
CFG = ROOT / 'config/b_dynamic_512.yaml'
NAME = 'b_dynamic_512'
DECK = OUT / (NAME + '.scs')
sha, read, dump = short.sha, short.read, short.dump
os.environ.setdefault('VB_DISABLE_CONTROL_MASTER', '1')
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')


def sha(path):
    """Bound memory for the full compressed capture as well as small inputs."""
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(2**20), b''): digest.update(block)
    return digest.hexdigest()


def dump(path, data):
    """Independent atomic writes for heartbeat and coordinator status readers."""
    path = OUT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(path.name + '.' + uuid.uuid4().hex + '.pending')
    pending.write_text(json.dumps(data, indent=2, default=str, allow_nan=False) + '\n', encoding='utf-8')
    for attempt in range(8):
        try:
            pending.replace(path)
            return
        except PermissionError:
            if attempt == 7: raise
            time.sleep(min(.02 * 2**attempt, .2))


def data_policy():
    path = ROOT / 'config/b_dynamic_512_data_policy.yaml'
    return yaml.safe_load(path.read_text(encoding='utf-8')) if path.exists() else {}


def require_local_waveform_permission():
    if data_policy().get('download_complete_waveform') is not True:
        raise RuntimeError('Complete local waveform transfers are disabled; analyze remotely and return metrics/figures only')


def stage(name, **details):
    dump(OUT / 'flow.json', dict(stage=name, updated_utc=datetime.now(timezone.utc).isoformat(), **details))


def preflight():
    assert not (OUT / 'context.json').exists()
    previous = short.OUT
    try:
        short.OUT = OUT
        short.preflight()
    finally:
        short.OUT = previous
    cfg = yaml.safe_load(CFG.read_text(encoding='utf-8'))
    assert shutil.disk_usage(ROOT).free > cfg['local_min_free_gib_before_launch'] * 2**30
    from virtuoso_bridge.transport.tunnel import SSHClient
    ssh = SSHClient.from_env(profile='t28_io')
    try:
        disk = ssh.spectre_runner.run_command('df -Pk /tmp; gzip --version; command -v sha256sum', timeout=25)
        ps = ssh.spectre_runner.run_command('ps -u chenzc_intern25 -ww -o pid,ppid,comm,args', timeout=20)
        assert disk.returncode == ps.returncode == 0
        free = int(disk.stdout.splitlines()[1].split()[3]) * 1024
        assert free > cfg['native_min_free_gib_before_launch'] * 2**30
        owned = [s for s in ps.stdout.splitlines() if 'virtuoso_bridge_spectre' in s and NAME + '.scs' in s]
        assert not owned, owned
        dump(OUT / 'resource_preflight.json', dict(remote_disk_text=disk.stdout,
            remote_free_bytes=free, local_free_bytes=shutil.disk_usage(ROOT).free, existing_exact_jobs=owned))
    finally:
        ssh.close()
    print('READ_ONLY_B_1X_AND_LONG_STORAGE_PREFLIGHT_PASS', flush=True)


def prepare():
    assert not (OUT / 'context.json').exists() and (OUT / 'preflight.json').exists()
    cfg = yaml.safe_load(CFG.read_text(encoding='utf-8'))
    assert (cfg['warmup_frames'], cfg['observed_frames'], cfg['total_frames']) == (4, 512, 516)
    assert math.gcd(cfg['coherent_bin'], cfg['observed_frames']) == 1
    assert cfg['input_frequency_hz'] == cfg['coherent_bin'] * cfg['sample_rate_hz'] / cfg['observed_frames']
    base = read(short.BASE / 'context.json')
    assert sha(base['deck']) == base['deck_sha256']
    original = Path(base['deck']).read_text(encoding='utf-8')
    peak = cfg['full_scale_differential_peak_v'] * 10**(cfg['input_level_dbfs'] / 20)
    text = original
    for side in 'PN':
        match = re.search(rf'(?m)^VVIN{side} .*$', text)
        assert match and 'ampl=.4 freq=500000' in match[0]
        text = text.replace(match[0], match[0].replace('ampl=.4 freq=500000',
            f'ampl={peak / 2:.17g} freq={cfg["input_frequency_hz"]:.17g}'), 1)
    assert text.count('r3_replay_stop stop_s=2400n') == 1
    text = text.replace('r3_replay_stop stop_s=2400n', 'r3_replay_stop stop_s=51600n')
    devices = short.native_devices(original)
    names = short.save_list(devices, False)
    assert len(names) == 136
    text, count = re.subn(r'(?m)^save .*$', 'save ' + ' '.join(names), text)
    assert count == 1
    includes = []
    for p, digest in base['include_sha256'].items():
        assert sha(p) == digest
        target = OUT / 'inputs' / Path(p).name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            assert sha(target) == digest
        else:
            target.write_bytes(Path(p).read_bytes())
        includes.append(str(target))
    DECK.write_text(text, encoding='utf-8')
    dump(OUT / 'context.json', dict(config=cfg, config_sha256=sha(CFG), deck=str(DECK), deck_sha256=sha(DECK),
        baseline_context_sha256=sha(short.BASE / 'context.json'), baseline_deck_sha256=sha(base['deck']),
        includes=includes, include_sha256={p: sha(p) for p in includes}, analog_devices=devices,
        saved_signals=names, differential_peak_v=peak, fs_hz=cfg['sample_rate_hz'],
        source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        same_native_blocks=True, no_OA_writes=True))
    stage('prepared', total_frames=516)
    check()


def check():
    ctx = read(OUT / 'context.json')
    assert sha(CFG) == ctx['config_sha256'] and sha(DECK) == ctx['deck_sha256']
    assert sha(short.BASE / 'context.json') == ctx['baseline_context_sha256']
    base = read(short.BASE / 'context.json')
    assert sha(base['deck']) == ctx['baseline_deck_sha256']
    for p, digest in ctx['include_sha256'].items(): assert sha(p) == digest
    original = Path(base['deck']).read_text(encoding='utf-8')
    text = DECK.read_text(encoding='utf-8')
    assert short.adoption.r3.r1.blocks(text) == short.adoption.r3.r1.blocks(original)
    before = text.split('VSAMPLE', 1)[1].split('ROBS_TOPN', 1)[0]
    assert before == original.split('VSAMPLE', 1)[1].split('ROBS_TOPN', 1)[0]
    assert re.search(r'(?ms)^simulatorOptions .*?^saveOptions[^\n]+', text)[0] == re.search(r'(?ms)^simulatorOptions .*?^saveOptions[^\n]+', original)[0]
    assert re.search(r'(?m)^tran_b_sine .*$', text)[0] == re.search(r'(?m)^tran_b_sine .*$', original)[0]
    assert 'strobeonly' not in text and len(ctx['saved_signals']) == 136
    assert short.hf.low.params(short.hf.low.main_statement(text))['w'] == '1u'
    assert short.hf.low.params(short.hf.low.main_statement(text))['l'] == '150.0n'
    for p in ctx['includes']:
        if Path(p).name in ('r3_sine_probe.va', 'r3_perf_monitor.va'):
            assert '<+' not in Path(p).read_text(encoding='utf-8')
    print('FROZEN_B1X_512_NATIVE_CLOCK_SOLVER_INCLUDE_IDENTITY_PASS', flush=True)


class LosslessTransfers:
    """Keep all continuous PSF bytes, without expanding 130GiB on local E:."""
    def __init__(self, runner): self.runner = runner
    def __getattr__(self, key): return getattr(self.runner, key)

    def download(self, remote_path, local_path, recursive=False, timeout=None):
        if recursive or remote_path.endswith(('.gz', '.pickle', '.tran.tran')):
            require_local_waveform_permission()
        from virtuoso_bridge.transport.ssh import CommandResult
        if not recursive:
            return self.runner.download(remote_path, local_path, timeout=60)
        assert re.fullmatch(re.escape(short.hf.REMOTE_BASE) + r'/[0-9a-f]{8}/' + NAME + r'\.raw', remote_path)
        # A broken execution SSH connection may return while native Spectre
        # is still alive. Never start compression from a download callback alone.
        root = remote_path.rsplit('/', 1)[0]
        gate = self.runner.run_command(f'cat {shlex.quote(root + "/spectre.out")}; '
            f'ps -u chenzc_intern25 -ww -o comm,args', timeout=30)
        assert gate.returncode == 0 and 'spectre completes with 0 errors' in gate.stdout, 'Native completion not verified'
        assert not any(line.split(None, 1)[0] == 'spectre' and root + '/' + NAME + '.scs' in line
            for line in gate.stdout.splitlines() if line.strip()), 'Native still running; preserve raw'
        stage('compressing_native', total_frames=516)
        raw = remote_path + '/tran_b_sine.tran.tran'
        packed = raw + '.gz'
        cmd = f'test -f {shlex.quote(raw)} && test ! -e {shlex.quote(packed)} && gzip -1 -c -- {shlex.quote(raw)} > {shlex.quote(packed)} && sha256sum {shlex.quote(raw)} {shlex.quote(packed)} && wc -c {shlex.quote(packed)}'
        compressed = self.runner.run_command(cmd, timeout=21600)
        assert compressed.returncode == 0, compressed.stderr
        hashes = dict((p, h) for h, p in re.findall(r'(?m)^([0-9a-f]{64})  (.+)$', compressed.stdout))
        assert set(hashes) == {raw, packed}
        size = int(compressed.stdout.splitlines()[-1].split()[0])
        assert shutil.disk_usage(ROOT).free > size + 12 * 2**30, 'Insufficient local compressed-data headroom; remote retained'
        local_path = Path(local_path)
        local_path.mkdir(parents=True, exist_ok=True)
        stage('downloading_lossless', compressed_bytes=size, total_frames=516)
        target = local_path / Path(packed).name
        result = self.runner.download(packed, target, timeout=21600)
        assert result.returncode == 0 and sha(target) == hashes[packed]
        dump(OUT / 'raw_receipt.json', dict(remote_raw=raw, remote_gzip=packed, raw_sha256=hashes[raw],
            gzip_sha256=hashes[packed], gzip_bytes=size, local_gzip=str(target), lossless=True,
            remote_original_retained=True))
        return CommandResult(0, 'Full native PSF transferred losslessly as gzip', '')


def native():
    from virtuoso_bridge.spectre.runner import SpectreSimulator, _run_spectre_remote, _build_simulation_result, spectre_mode_args
    assert read(OUT / 'flow.json')['stage'] == 'launching_native', 'Only the exclusive coordinator launches native'
    check()
    ctx = read(OUT / 'context.json')
    sim = SpectreSimulator.from_env(profile='t28_io', timeout=ctx['config']['native_timeout_s'])
    assert sim._remote_host == 'thu-wei' and sim._remote_user == 'chenzc_intern25'
    (OUT / 'spectre').mkdir(exist_ok=True)
    stage('running_native', total_frames=516)
    result = _run_spectre_remote(netlist=DECK, params=dict(include_files=ctx['includes']),
        runner=LosslessTransfers(sim._get_ssh_runner()), remote_work_dir=short.hf.REMOTE_BASE,
        base_output_dir=OUT / 'spectre', spectre_cmd=short.hf.BIN,
        spectre_args=[*spectre_mode_args('aps'), '+lqtimeout', '60', '+mt=4'],
        output_format='psfascii', timeout=ctx['config']['native_timeout_s'], keep_remote_files=True)
    dump(OUT / 'run_artifacts.json', result._asdict())
    assembled = _build_simulation_result(result, None, extra_metadata=result.metadata)
    dump(OUT / 'result.json', dict(ok=assembled.ok, errors=assembled.errors, warnings=assembled.warnings,
        metadata=assembled.metadata, deck_sha256=ctx['deck_sha256']))
    assert result.success and assembled.ok, assembled.errors
    log = (OUT / 'spectre/spectre.out').read_text(errors='replace')
    assert 'spectre completes with 0 errors' in log
    stage('downloaded_native', total_frames=516)


def status():
    state = read(OUT / 'flow.json')
    progress = dict(stage=state['stage'], checked_utc=datetime.now(timezone.utc).isoformat(), total_frames=516)
    local_log = OUT / 'spectre/spectre.out'
    log = local_log.read_text(errors='replace') if local_log.exists() else ''
    commands = re.findall(r'(?m)^\[Command\] (.*)$', (OUT / 'runner.log').read_text(errors='replace')) if (OUT / 'runner.log').exists() else []
    processes, folder = [], None
    if commands:
        match = re.search(r'\+log ([^ ]+/spectre.out)', commands[-1])
        assert match and re.fullmatch(re.escape(short.hf.REMOTE_BASE) + r'/[0-9a-f]{8}/spectre.out', match[1])
        folder = match[1].rsplit('/', 1)[0]
        if not log:
            from virtuoso_bridge.transport.tunnel import SSHClient
            ssh = SSHClient.from_env(profile='t28_io')
            try:
                result = ssh.spectre_runner.run_command(f'if test -f {shlex.quote(match[1])}; then cat {shlex.quote(match[1])}; fi', timeout=25)
                assert result.returncode == 0
                log = result.stdout
                ps = ssh.spectre_runner.run_command('ps -u chenzc_intern25 -ww -o pid,ppid,etime,pcpu,comm,args; df -Pk /tmp', timeout=25)
                assert ps.returncode == 0, ps.stderr
                for line in ps.stdout.splitlines():
                    parts = line.split(None, 5)
                    if len(parts) == 6 and parts[0].isdigit() and folder + '/' + NAME + '.scs' in parts[5]:
                        processes.append(dict(pid=int(parts[0]), parent=int(parts[1]), elapsed=parts[2], cpu=parts[3], command=parts[4], args=parts[5]))
                disk = next((s.split() for s in ps.stdout.splitlines() if s.startswith('/dev/')), None)
                if disk: progress['remote_free_bytes'] = int(disk[3]) * 1024
            finally:
                ssh.close()
        dump(OUT / 'remote.json', dict(log=match[1], root=folder, checked_utc=progress['checked_utc'], processes=processes))
    rows = short.re.findall(r'R3MEAS,(\d+),(\d+),(\d+),(\d+),(\d+),([^\s,]+)', log)
    cfg = read(OUT / 'context.json')['config']
    peak = read(OUT / 'context.json')['differential_peak_v']
    gross, invalid = [], []
    for row in rows:
        f, code = int(row[0]), int(row[1])
        if row[2] != '8' or row[4] != '1': invalid.append(f)
        if f >= 4:
            h = (f * 100 + 41.05 - cfg['sampling_common_delay_ns']) * 1e-9
            expected = max(0, min(255, math.floor((peak * math.sin(2 * math.pi * cfg['input_frequency_hz'] * h - .4 * math.pi) + .9) / short.Q)))
            if abs(code - expected) > cfg['gross_code_alarm_lsb']: gross.append(dict(frame=f, code=code, approximate_expected=expected))
    has_fatal = bool(re.search(r'(?im)^\s*(FATAL|ERROR)\s*\(', log)) or 'convergence failure' in log.lower()
    reasons = []
    if invalid: reasons.append('invalid conversion count/rail/stability')
    if gross: reasons.append('gross code error beyond fixed-delay guard')
    if 'CMI-2754' in log: reasons.append('CMI terminal stress')
    if has_fatal: reasons.append('native fatal/convergence error')
    if log.count('SPECTRE-16780') >= 3: reasons.append('repeated LTE precision relaxation')
    if 'remote_free_bytes' in progress and progress['remote_free_bytes'] < cfg['remote_min_free_gib_during_native'] * 2**30:
        reasons.append('remote disk headroom exhausted')
    progress.update(completed_frames=len(rows), observed_frames=max(0, len(rows) - 4), last_records=rows[-2:],
        native_success='spectre completes with 0 errors' in log, native_processes=processes,
        invalid_frames=invalid, gross_code_frames=gross, has_CMI='CMI-2754' in log,
        LTE_count=log.count('SPECTRE-16780'), clear_anomaly_reasons=reasons,
        native_footer=next((s for s in log.splitlines() if s.startswith('spectre completes with')), None))
    dump(OUT / 'progress.json', progress)
    print('B_DYNAMIC512', progress['stage'], f'{len(rows)}/516', 'alarms=', reasons, flush=True)
    return progress


def stop_owned(reason):
    from virtuoso_bridge.transport.tunnel import SSHClient
    remote = read(OUT / 'remote.json')
    root = remote['root']
    assert re.fullmatch(re.escape(short.hf.REMOTE_BASE) + r'/[0-9a-f]{8}', root)
    ssh = SSHClient.from_env(profile='t28_io')
    try:
        ps = ssh.spectre_runner.run_command('ps -u chenzc_intern25 -ww -o pid,comm,args', timeout=20)
        owned = []
        for line in ps.stdout.splitlines():
            p = line.split(None, 2)
            if len(p) == 3 and p[0].isdigit() and p[1] == 'spectre' and root + '/' + NAME + '.scs' in p[2]: owned.append(int(p[0]))
        for pid in owned:
            r = ssh.spectre_runner.run_command(f'kill -TERM {pid}', timeout=15)
            assert r.returncode == 0
        dump(OUT / 'interruption.json', dict(reason=reason, exact_root=root, terminated_native_pids=owned,
             time_utc=datetime.now(timezone.utc).isoformat(), no_rerun=True))
    finally: ssh.close()


def run():
    assert read(OUT / 'flow.json')['stage'] == 'prepared', 'Never duplicate/restart this run'
    os.close(os.open(OUT / 'launch.lock', os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    check()
    dump(OUT / 'launch.json', dict(local_pid=os.getpid(),
        commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        context_sha256=sha(OUT / 'context.json'), runner_LF_sha256=hashlib.sha256(Path(__file__).read_text(encoding='utf-8').encode()).hexdigest(),
        frozen_analysis_LF_sha256={p.name: hashlib.sha256(p.read_text(encoding='utf-8').encode()).hexdigest()
            for p in (Path(__file__).with_name('b_dynamic_512_reduce.py'), Path(__file__).with_name('b_dynamic_512_analyze.py'))},
        started_utc=datetime.now(timezone.utc).isoformat()))
    stage('launching_native', total_frames=516)
    with (OUT / 'runner.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable, __file__, 'native'], cwd=ROOT,
            stdout=log, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    try:
        while process.poll() is None:
            try:
                progress = status()
                if progress['clear_anomaly_reasons'] and not progress['native_success'] and not (OUT / 'interruption.json').exists():
                    stop_owned('; '.join(progress['clear_anomaly_reasons']))
            except Exception as exc:
                dump(OUT / 'monitor_query_error.json', dict(utc=datetime.now(timezone.utc).isoformat(), error=repr(exc)))
            time.sleep(120)
        assert process.returncode == 0 and not (OUT / 'interruption.json').exists(), 'Native failed/interrupted; no automatic retry'
        stage('reducing_full_waveform', total_frames=516)
        subprocess.run([str(ROOT / '.venv/Scripts/python.exe'), str(ROOT / 'scripts/integration/b_dynamic_512_reduce.py')], cwd=ROOT, check=True)
        stage('analyzing_batch', total_frames=516)
        subprocess.run([str(ROOT / '.venv/Scripts/python.exe'), str(ROOT / 'scripts/integration/b_dynamic_512_analyze.py')], cwd=ROOT, check=True)
        stage('awaiting_visual_review', total_frames=516, summary='output/b_dynamic_512/summary.json')
    except Exception as exc:
        stage('failed', error=repr(exc), no_automatic_retry=True)
        raise


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['preflight', 'prepare', 'check', 'native', 'run', 'status'])
    globals()[p.parse_args().action]()
