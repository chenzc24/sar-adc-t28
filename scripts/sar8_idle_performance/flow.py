"""Immutable idle-reset characterization using unchanged R4 testbench/analysis."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import contextlib
import importlib.util
import json
import re
import shlex
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts/sar8_r4_performance'))
import common
import run as original_run
import analyze
import recover

OUT = ROOT/'output/sar8_idle_performance'
VERIFY = ROOT/'verification/sar8_idle_performance'
REMOTE = '/tmp/virtuoso_bridge_chenzc_intern25/90590/sar8_idle_performance_20261022'
EXPECTED = 'ef0fc74a3df306a366261bd5ce6bbe01f6b4386007c0b86c3150e09c28f976ea'
read, dump, sha, blocks = common.read, common.dump, common.sha, common.blocks
for module in (original_run, analyze, recover):
    module.OUT = OUT
SINE = 'sine_cx_1024_k461'
STATICS = [f'static_cx_{i:03d}_{min(i+31,255):03d}' for i in range(1,256,32)]
SMOKE = 'smoke_static_128_128'


def candidate():
    """Reconstruct from curated source, not a dependency on disposable raw output."""
    provenance = read(ROOT/'netlist/sar8_r4_idle/provenance.json')
    frozen = ROOT/'netlist/sar8_physical/dut.scs'
    fragment = ROOT/'netlist/sar8_r4_idle/idle_cells.scs'
    assert sha(frozen) == provenance['frozen_sha256']
    assert sha(fragment) == provenance['curated_sha256']
    # The generator preserves exact bytes (including cell order and whitespace).
    spec = importlib.util.spec_from_file_location('idle_candidate_flow', ROOT/'scripts/sar8_r4_idle/flow.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    text, _ = module.design('msb', 1, 1, 6)
    import hashlib
    # Prior native DUT was written with Windows text newline translation.
    raw = text.replace('\n', '\r\n').encode('utf-8')
    assert hashlib.sha256(raw).hexdigest() == EXPECTED == provenance['candidate_DUT_sha256']
    return text, raw


def preflight():
    from virtuoso_bridge.spectre.runner import SpectreSimulator
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT/'preflight.log').open('w') as log, contextlib.redirect_stdout(log):
        sim = SpectreSimulator.from_env(profile='t28_io', work_dir=OUT/'preflight', timeout=60)
        lic = sim.check_license(); ssh = recover.client()
        resources = recover.command(ssh, 'hostname; uptime; free -m; df -h /tmp; pgrep -a -u chenzc_intern25 -x spectre || true')
    result = dict(profile='t28_io', simulator={k:lic.get(k) for k in ['ok','spectre_path','version']},
                  resources=resources, OA_mutations=False, CIW_required=False)
    dump(OUT/'preflight.json', result); print(json.dumps(result, indent=2)); assert lic.get('ok')


def prepare(name, kind, **kwargs):
    dut, raw = candidate()
    original_run.prepare(name, kind, mode='cx', **kwargs)
    folder = OUT/'cases'/name; deck = folder/(name+'.scs')
    old = deck.read_text(); frozen = (common.SOURCE/'dut.scs').read_text()
    assert old.count(frozen) == 1
    text = old.replace(frozen, dut)
    assert blocks(text) == blocks(dut)
    assert text.replace(dut, frozen) == old
    deck.write_text(text, encoding='utf-8')
    ctx = read(folder/'context.json')
    ctx.update(source=dict(candidate_commit='027b951', candidate_DUT_sha256=EXPECTED,
                           frozen_R4=common.verify_source(), curated_provenance=read(ROOT/'netlist/sar8_r4_idle/provenance.json')),
               DUT_unchanged=False, candidate_DUT_unchanged=True, testbench_unchanged_vs_R4=True,
               deck_sha256=sha(deck), OA_changed=False,
               final_top_diff_is_conversion_residue=False)
    dump(folder/'context.json', ctx)
    snapshot = OUT/'candidate_dut.scs'
    if snapshot.exists(): assert snapshot.read_bytes() == raw
    else: snapshot.write_bytes(raw)
    return ctx


def setup():
    assert not (VERIFY/'setup.json').exists(), 'Already initialized; use status/collect'
    candidate(); common.verify_source()
    smoke = prepare(SMOKE, 'static', first=128, last=128)
    dump(VERIFY/'setup.json', dict(status='smoke_prepared', candidate_commit='027b951', candidate_DUT_sha256=EXPECTED,
        original_R4_results_sha256=sha(ROOT/'verification/sar8_r4_performance/results.json'),
        scope='TT/0.9V/27C, no PVT/mismatch/transient noise/PEX', OA_changed=False,
        solver='Spectre X CX', threads_per_job=4, max_concurrent_jobs=4,
        smoke=SMOKE, sine=SINE, static_cases=STATICS,
        static_method='255 transitions, 256 centers, 7 bisections, bracket 1/128 LSB',
        dynamic=dict(samples=1024, warmup=4, coherent_bin=461, frequency_hz=4501953.125,
                     level_dbfs=-1, window='rectangular', calibration=False),
        testbench_sources={p.name:sha(p) for p in common.MODELS.glob('*.va')},
        acquisition='restored idle-tail candidate; no changed closing command',
        output_read_ns=98, idle_residual_excluded=True, preflight=read(OUT/'preflight.json')))
    print('SETUP', smoke['frames'], 'smoke frames')


def schedule(jobs, concurrency):
    assert 1 <= concurrency <= 4
    lanes = [[] for _ in range(concurrency)]; loads = [0]*concurrency
    for job in sorted(jobs, key=lambda j:j['frames'], reverse=True):
        index = min(range(concurrency), key=lambda i:loads[i])
        lanes[index].append(job); loads[index] += job['frames']
    return lanes


def launch(batch, names, concurrency=4):
    assert re.fullmatch(r'[a-z0-9_]+', batch)
    manifest_path = OUT/(batch+'_launch.json')
    assert not manifest_path.exists(), 'Already dispatched/unknown dispatch; inspect status, never repeat'
    ssh = recover.client(); jobs = []
    for name in names:
        folder = OUT/'cases'/name; ctx = read(folder/'context.json'); remote = REMOTE+'/'+name
        assert sha(folder/(name+'.scs')) == ctx['deck_sha256']
        recover.command(ssh, 'test ! -e '+shlex.quote(remote)+' && mkdir -p '+shlex.quote(remote))
        paths = [folder/(name+'.scs')] + [Path(i['path']) for i in ctx['includes']]
        for path in paths:
            r = ssh.upload(path, remote+'/'+path.name, timeout=60); assert r.returncode == 0, r.stderr
        native = (f'source /home/cshrc/.cshrc.cadence.IC618SP201; cd {remote}; '
                  f'/home/cadence/spectre/SPECTRE211Hotfix/tools/bin/spectre -64 {remote}/{name}.scs '
                  f'+escchars +log {remote}/spectre.out -format psfascii -raw {remote}/{name}.raw '
                  '+preset=cx +mt=4 +lqtimeout 60 -maxw 5 -maxn 5 +logstatus')
        wrapper = (f'#!/bin/sh\ncd {shlex.quote(remote)} || exit 98\n'
                   'HOSTNAME=$(hostname); export HOSTNAME\nLD_LIBRARY_PATH=${LD_LIBRARY_PATH:-}; export LD_LIBRARY_PATH\n'
                   f'csh -c {shlex.quote(native)} > console.log 2>&1\n'
                   'perf_rc=$?\nprintf "%s\\n" "$perf_rc" > exit_code\nexit "$perf_rc"\n')
        r = ssh.upload_text(wrapper, remote+'/run.sh', timeout=30); assert r.returncode == 0, r.stderr
        jobs.append(dict(name=name, remote=remote, deck_sha256=ctx['deck_sha256'], frames=ctx['frames']))
    # Fixed independent lanes: at most four native jobs; no client-owned subprocess.
    lanes = schedule(jobs, concurrency)
    script = '#!/bin/sh\n'
    for lane in lanes:
        if not lane: continue
        script += '(\n'+''.join('sh '+shlex.quote(j['remote']+'/run.sh')+'\n' for j in lane)+') &\n'
    script += 'wait\nprintf "finished\\n" > '+shlex.quote(REMOTE+'/'+batch+'_done')+'\n'
    batch_path = REMOTE+'/'+batch+'.sh'
    r = ssh.upload_text(script, batch_path, timeout=30); assert r.returncode == 0, r.stderr
    manifest = dict(created_utc=datetime.now(timezone.utc).isoformat(), jobs=jobs, batch=batch,
                    concurrency=concurrency, lanes=[[j['name'] for j in lane] for lane in lanes],
                    dispatch_state='persisted_before_dispatch')
    dump(manifest_path, manifest)
    pid = recover.command(ssh, f'nohup sh {shlex.quote(batch_path)} > {shlex.quote(REMOTE+"/"+batch+".log")} 2>&1 < /dev/null & echo $!')
    manifest.update(pid=pid.strip(), dispatch_state='dispatched'); dump(manifest_path, manifest)
    dump(OUT/'flow_status.json', dict(stage=batch+'_running', manifest=str(manifest_path)))
    print('DISPATCHED', batch, pid.strip(), [j['name'] for j in jobs], flush=True)


def collect_case(ssh, job):
    """Use original verified lean PSF collector, with candidate identity assertion."""
    # The original collector validates blocks against SOURCE/dut.scs. Give it the
    # isolated hash-verified candidate snapshot directory, never the old source.
    assert sha(OUT/'candidate_dut.scs') == EXPECTED
    folder = OUT/'cases'/job['name']
    receipt = folder/'transfer_integrity.json'
    if receipt.exists():
        assert read(receipt)['match'] and read(folder/'result.json')['ok']
        return
    candidate_dir = OUT/'source'; candidate_dir.mkdir(exist_ok=True)
    snapshot = candidate_dir/'dut.scs'
    if not snapshot.exists(): snapshot.write_bytes((OUT/'candidate_dut.scs').read_bytes())
    assert sha(snapshot) == EXPECTED
    recover.SOURCE = candidate_dir
    recover.collect(ssh, job['name'], job['remote'])
    assert sha(folder/'recovery_native/remote.scs') == job['deck_sha256']
    # Preserve comparison of the actual downloaded native wave against remote hash.
    psf = folder/'recovery_native'/(job['name']+'.raw')/'tran_perf.tran.tran'
    expected = recover.command(ssh, 'sha256sum '+shlex.quote(job['remote']+'/'+job['name']+'.raw/tran_perf.tran.tran')).split()[0]
    assert sha(psf) == expected
    dump(folder/'transfer_integrity.json', dict(remote_psf_sha256=expected, local_psf_sha256=sha(psf),
                                              deck_sha256=job['deck_sha256'], match=True))


def status(batch, collect=False):
    manifest = read(OUT/(batch+'_launch.json')); ssh = recover.client(); states = []
    for job in manifest['jobs']:
        remote = job['remote']
        command = (f'if test -f {shlex.quote(remote+"/exit_code")}; then printf "EXIT "; cat {shlex.quote(remote+"/exit_code")}; '
                   f'elif test -f {shlex.quote(remote+"/spectre.out")}; then printf "RUNNING\\n"; '
                   f'grep -c "R4MEAS," {shlex.quote(remote+"/spectre.out")}; '
                   f'tail -n 3 {shlex.quote(remote+"/spectre.out")}; else printf "QUEUED\\n"; fi')
        raw = recover.command(ssh, command); done = raw.strip() == 'EXIT 0'
        item = dict(name=job['name'], completed=done, status=raw.strip())
        if done and collect:
            collect_case(ssh, job); item['collected'] = True
        states.append(item); print(json.dumps(item), flush=True)
    dump(OUT/(batch+'_status.json'), dict(checked_utc=datetime.now(timezone.utc).isoformat(), cases=states))
    return all(s['completed'] for s in states)


def smoke_gate():
    report, _ = analyze.load(SMOKE)
    assert report['frame_integrity_pass'] and all(f['valid'] for f in report['frames'])
    assert report['all_brackets_pass'] and all(c['expected']==c['code'] for c in report['centers'])
    assert not report['CMI'] and not report['numerical_diagnostics']
    dump(VERIFY/'smoke.json', {k:v for k,v in report.items() if k not in ('frames','searches')})
    print('SMOKE_PASS', len(report['frames']), report['thresholds'])


def full():
    smoke_gate()
    prepare(SINE, 'sine')
    for first, name in zip(range(1,256,32), STATICS):
        prepare(name, 'static', first=first, last=min(first+31,255))
    launch('full', [SINE, *STATICS])
    setup_path = VERIFY/'setup.json'; data = read(setup_path); data['status']='full_running'; dump(setup_path,data)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('action', choices=['preflight','setup','smoke','smoke_gate','full','status','collect'])
    p.add_argument('--batch', choices=['smoke','full'], default='full'); a = p.parse_args()
    if a.action=='preflight': preflight()
    elif a.action=='setup': setup()
    elif a.action=='smoke':
        with (OUT/'dispatch_smoke.log').open('x') as log, contextlib.redirect_stdout(log):
            launch('smoke',[SMOKE],1)
        print('SMOKE_DISPATCHED')
    elif a.action=='smoke_gate': smoke_gate()
    elif a.action=='full':
        with (OUT/'dispatch_full.log').open('x') as log, contextlib.redirect_stdout(log): full()
        print('FULL_DISPATCHED', SINE, STATICS)
    else: status(a.batch, a.action=='collect')
