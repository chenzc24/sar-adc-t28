"""Bounded SSH-loss recovery. Never overwrite an original case or relaunch it."""
import argparse
import contextlib
import io
import re
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from common import OUT, ROOT, read, dump, sha, blocks, SOURCE
from run import prepare

MANIFEST = OUT / "recovery_20261022_r2.json"
REMOTE = "/tmp/virtuoso_bridge_chenzc_intern25/90590/virtuoso_bridge_spectre/r4_recovery_20261022_r2"
RETRY = ["static_cx_033_064", "static_cx_097_128", "static_cx_129_160",
         "static_cx_161_192", "static_cx_193_224", "static_cx_225_255"]
RECOVER = ["sine_cx_1024_k461", "static_cx_001_032"]


def client():
    from virtuoso_bridge import VirtuosoClient
    with contextlib.redirect_stdout(io.StringIO()):
        return VirtuosoClient.from_env(profile="t28_io", timeout=30, log_to_ciw=False).ssh_runner


def command(ssh, text):
    result = ssh.run_command(text, timeout=30)
    assert result.returncode == 0, (text, result.stderr)
    return result.stdout


def collect(ssh, name, remote, original=False):
    """Require native PASS, full frame coverage, closed PSF, full duration and hashes."""
    from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii
    folder = OUT / "cases" / name
    receipt = folder / ("recovered_result.json" if original else "result.json")
    if receipt.exists():
        assert read(receipt)["ok"]
        return
    ctx = read(folder / "context.json")
    assert sha(folder / (name + ".scs")) == ctx["deck_sha256"]
    dest = folder / "recovery_native"
    assert not dest.exists(), "Inspect interrupted collection; do not overwrite evidence"
    dest.mkdir()
    native_raw = remote + "/" + name + ".raw"
    for src, target, recursive in [(remote + "/spectre.out", dest / "spectre.out", False),
                                  (remote + "/" + name + ".scs", dest / "remote.scs", False),
                                  (native_raw, dest / (name + ".raw"), True)]:
        r = ssh.download(src, target, recursive=recursive, timeout=120)
        assert r.returncode == 0, r.stderr
    raw = dest / (name + ".raw")
    log = (dest / "spectre.out").read_text(errors="replace")
    native_status = (raw / "logStatus").read_text()
    assert re.search(r"tran_perf\s+PASS", native_status), native_status
    assert not re.search(r"(?im)^\s*(?:fatal|error)\s*\(|fatal error|convergence failure", log)
    assert blocks((dest / "remote.scs").read_text()) == blocks((SOURCE / "dut.scs").read_text())
    ids = [int(x) for x in re.findall(r"R4MEAS,(\d+),", log)]
    assert ids == list(range(ctx["frames"])), (name, len(ids))
    psf = raw / "tran_perf.tran.tran"
    assert psf.read_text().rstrip().endswith("END")
    parsed = parse_spectre_psf_ascii(psf)
    assert parsed.ok, parsed.errors
    wave = {str(k).strip('"').replace("\\", "").lower(): np.asarray(v)
            for k, v in parsed.data.items() if isinstance(v, (list, np.ndarray)) and str(k).lower() != "units"}
    assert np.all(np.diff(wave["time"]) > 0)
    assert wave["time"][-1] >= ctx["stop_ns"] * 1e-9 - 1e-14
    assert all(len(v) == len(wave["time"]) and np.isfinite(v).all() for v in wave.values())
    exitcode = None
    if not original:
        exitcode = int(command(ssh, "cat " + shlex.quote(remote + "/exit_code")))
        assert exitcode == 0
        assert "spectre completes with 0 errors" in log
    np.savez_compressed(folder / "wave.npz", **wave)
    dump(folder / "wave_receipt.json", dict(sha256=sha(folder / "wave.npz"), signals=list(wave), points=len(wave["time"])))
    proof = dict(native_analysis_pass=True, whole_process_exit_code=exitcode,
                 whole_process_zero_error_summary="spectre completes with 0 errors" in log,
                 original_transport_failure_preserved=original,
                 basis="native logStatus PASS, all frames, PSF END and full duration; parser.ok",
                 native_log_sha256=sha(dest / "spectre.out"), psf_sha256=sha(psf),
                 native_status=native_status, remote=remote)
    dump(receipt, dict(ok=True, errors=[], warnings=sorted(set(re.findall(r"WARNING \(([^)]+)\)", log))), elapsed_wall_s=None,
                       deck_sha256=ctx["deck_sha256"], recovery=proof,
                       metadata=dict(output_dir=str(raw), returncode=exitcode, timings=None)))
    print("COLLECTED", name, proof, flush=True)


def initialize():
    assert not MANIFEST.exists(), "Recovery already initialized; use status/collect"
    ssh = client()
    # No original or other Spectre may still be consuming these slots.
    assert not command(ssh, "pgrep -u chenzc_intern25 -x spectre || true").strip()
    mapping = {}
    for name in RECOVER:
        result = read(OUT / "cases" / name / "result.json")
        assert not result["ok"]
        remote = re.search(r"\+log (\S+)/spectre.out", result["metadata"]["command"])[1]
        collect(ssh, name, remote, original=True)
        mapping[name] = name
    command(ssh, "test ! -e " + shlex.quote(REMOTE) + " && mkdir -p " + shlex.quote(REMOTE))
    jobs = []
    for old in RETRY:
        ctx = read(OUT / "cases" / old / "context.json")
        name = old + "_r2"
        prepare(name, "static", mode="cx", first=ctx["first"], last=ctx["last"])
        folder = OUT / "cases" / name
        newctx = read(folder / "context.json")
        assert newctx["deck_sha256"] == ctx["deck_sha256"], "Retry deck must be byte-identical"
        remote = REMOTE + "/" + name
        command(ssh, "mkdir " + shlex.quote(remote))
        for path in [folder / (name + ".scs")] + [Path(i["path"]) for i in newctx["includes"]]:
            r = ssh.upload(path, remote + "/" + path.name, timeout=60)
            assert r.returncode == 0, r.stderr
        # Independent stdout file avoids SIGPIPE after a client SSH disconnect.
        # Cadence's csh environment changes cwd; restore it after sourcing and
        # keep every native output path absolute and task-scoped.
        native = f"source /home/cshrc/.cshrc.cadence.IC618SP201; cd {remote}; /home/cadence/spectre/SPECTRE211Hotfix/tools/bin/spectre -64 {remote}/{name}.scs +escchars +log {remote}/spectre.out -format psfascii -raw {remote}/{name}.raw +preset=cx +mt=4 +lqtimeout 60 -maxw 5 -maxn 5 +logstatus"
        wrapper = f"#!/bin/sh\ncd {shlex.quote(remote)} || exit 98\nHOSTNAME=$(hostname); export HOSTNAME\nLD_LIBRARY_PATH=${{LD_LIBRARY_PATH:-}}; export LD_LIBRARY_PATH\ncsh -c {shlex.quote(native)} > console.log 2>&1\nr4_rc=$?\nprintf '%s\\n' \"$r4_rc\" > exit_code\nexit \"$r4_rc\"\n"
        r = ssh.upload_text(wrapper, remote + "/run.sh", timeout=30)
        assert r.returncode == 0, r.stderr
        jobs.append(dict(original=old, name=name, remote=remote))
        mapping[old] = name
    mapping["static_cx_065_096"] = "static_cx_065_096"
    # Four slots; a disconnected client cannot terminate the remote batch.
    batch = "#!/bin/sh\n"
    for i, job in enumerate(jobs):
        batch += "sh " + shlex.quote(job["remote"] + "/run.sh") + " &\n"
        if (i + 1) % 4 == 0: batch += "wait\n"
    batch += "wait\nprintf 'finished\\n' > " + shlex.quote(REMOTE + "/batch_done") + "\n"
    r = ssh.upload_text(batch, REMOTE + "/batch.sh", timeout=30)
    assert r.returncode == 0, r.stderr
    manifest = dict(created_utc=datetime.now(timezone.utc).isoformat(), remote=REMOTE, jobs=jobs, mapping=mapping)
    dump(MANIFEST, manifest)  # Persist before launching: an unknown launch must never be repeated.
    launch = command(ssh, f"nohup sh {shlex.quote(REMOTE+'/batch.sh')} > {shlex.quote(REMOTE+'/batch.log')} 2>&1 < /dev/null & echo $!")
    manifest["batch_pid"] = launch.strip()
    dump(MANIFEST, manifest)
    dump(OUT / "flow_before_recovery_r2.json", read(OUT / "flow_status.json"))
    dump(OUT / "flow_status.json", dict(stage="recovery_running", recovery_manifest=str(MANIFEST), **manifest))
    print("RECOVERY_LAUNCHED", launch, flush=True)


def check(collect_ready=False):
    ssh = client(); manifest = read(MANIFEST)
    all_complete = True
    for job in manifest["jobs"]:
        remote = job["remote"]
        state = command(ssh, f"if test -f {shlex.quote(remote+'/exit_code')}; then cat {shlex.quote(remote+'/exit_code')}; elif test -f {shlex.quote(remote+'/spectre.out')}; then tail -n 8 {shlex.quote(remote+'/spectre.out')}; else printf 'queued'; fi")
        print(job["name"], state[-1200:], flush=True)
        if state.strip() != "0": all_complete = False
        elif collect_ready: collect(ssh, job["name"], remote)
    if collect_ready and all_complete:
        mapping = manifest["mapping"]
        names = [mapping[f"static_cx_{i:03d}_{min(i+31,255):03d}"] for i in range(1,256,32)]
        subprocess.run([str(ROOT / ".venv/Scripts/python.exe"), str(Path(__file__).with_name("report.py")),
                        "--static", *names, "--sine", "sine_cx_1024_k461"], cwd=ROOT, check=True)
        dump(OUT / "flow_status.json", dict(stage="complete_pending_review", recovery_manifest=str(MANIFEST)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("action", choices=["initialize", "status", "collect"])
    args = parser.parse_args()
    if args.action == "initialize": initialize()
    else: check(args.action == "collect")
