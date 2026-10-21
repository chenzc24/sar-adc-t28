"""Bounded main-W-only native B sine sweep; never mutates original data or OA."""
from __future__ import annotations
import argparse
import dataclasses
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import pickle
import re
import shlex
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/b_sine_main_w"
BASE = ROOT / "output/b_sine_period"
CFG = ROOT / "config/b_sine_main_w.yaml"
REMOTE_BASE = "/tmp/virtuoso_bridge_chenzc_intern25/90590/virtuoso_bridge_spectre"
BIN = "/home/cadence/spectre/SPECTRE211Hotfix/tools/bin/spectre"
os.environ.setdefault("VB_DISABLE_CONTROL_MASTER", "1")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix+".pending")
    pending.write_text(json.dumps(value, indent=2, default=str, allow_nan=False)+"\n", encoding="utf-8")
    pending.replace(path)


def stage(path, name, **extra):
    dump(Path(path)/"flow.json", dict(stage=name, updated_utc=datetime.now(timezone.utc).isoformat(),
                                    local_pid=os.getpid(), **extra))


def main_statement(text, name="Mmain"):
    found = list(re.finditer(rf"(?m)^    {re.escape(name)} .*$(?:\n        .*$)*", text))
    assert len(found) == 1, (name, len(found))
    return found[0].group()


def params(statement):
    return dict(re.findall(r"\b(\w+)=([^\s\\]+)", statement))


def number(value):
    return float(value[:-1])*dict(n=1e-9, u=1e-6, p=1e-12, f=1e-15)[value[-1]] if value[-1] in "nupf" else float(value)


def resize(text, width):
    assert width in (1, 2, 3)
    if width == 1:
        return text
    old = main_statement(text)
    new = old
    values = dict(w=f"{width}u", ad=f"{1.55*width:.12g}e-13", **{"as":f"{1.55*width:.12g}e-13"},
                  pd=f"{2*width+.31:.12g}u", ps=f"{2*width+.31:.12g}u")
    for key, value in values.items():
        new, n = re.subn(rf"\b{key}=([^\s\\]+)", f"{key}={value}", new)
        assert n == 1
    return text.replace(old, new, 1)


def preflight():
    from virtuoso_bridge import VirtuosoClient
    import r3_b_oa as adoption
    from freeze_r0 import object_digest, schematic_surface
    assert not (OUT/"preflight.json").exists()
    c = VirtuosoClient.from_env(profile="t28_io", timeout=30, log_to_ciw=False)
    info = c.library.get(adoption.LIB)
    assert info.path == "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28"
    assert info.technology_library == "tsmcN28"
    for name in (adoption.TOP, adoption.TB):
        current = c.schematic.read(adoption.LIB, name, include_positions=True, param_filters=None)
        assert adoption.normalized(current) == adoption.normalized(read(BASE/f"oa/{name}.json")), name
    dependencies = read(ROOT/"output/r3_b_oa/dependencies.json")
    for name, expected in dependencies.items():
        current = c.schematic.read(adoption.LIB, name, include_positions=False, param_filters=None)
        assert object_digest(schematic_surface(current)) == expected, name
    from virtuoso_bridge.transport.tunnel import SSHClient
    ssh = SSHClient.from_env(profile="t28_io")
    check = ssh.spectre_runner.run_command("hostname; pwd; uptime", timeout=20)
    assert check.returncode == 0 and "thu-wei" in check.stdout
    ssh.close()
    dump(OUT/"preflight.json", dict(library=dataclasses.asdict(info), windows=c.list_windows(),
        unchanged_native_dependencies=len(dependencies), OA_writes=[], host_readback=check.stdout))
    print("READ_ONLY_CURRENT_B_PREFLIGHT_PASS", flush=True)


def prepare():
    import yaml
    assert not (OUT/"context.json").exists(), "Immutable setup already exists"
    assert (OUT/"preflight.json").exists()
    cfg = yaml.safe_load(CFG.read_text())
    assert cfg["width_multipliers"] == [1, 2, 3]
    base = read(BASE/"context.json")
    tracked = read(ROOT/"verification/integration/b_sine_period_results.json")
    assert read(BASE/"result.json")["ok"] and read(BASE/"flow.json")["stage"] == "complete"
    assert sha(base["deck"]) == tracked["deck_sha256"] == base["deck_sha256"]
    text = Path(base["deck"]).read_text(encoding="utf-8")
    original = params(main_statement(text))
    # Validate the width geometry rule against actual prior PDK exports,
    # without mutating a PDK CDF or any library instance.
    templates = [
        (BASE/"decks/b_sine_period.scs", "Mmain"),
        (ROOT/"output/canvas_bootstrap_t28/oa_netlists/selected/input.scs", "Mmain"),
        (ROOT/"output/canvas_bootstrap_t28/oa_netlists/main_320n_reset_2u/input.scs", "Mmain"),
        (ROOT/"output/canvas_bootstrap_t28/oa_netlists/main_320n_reset_2u/input.scs", "M8")]
    geometry = []
    allowed = {"w", "ad", "as", "pd", "ps"}
    for path, name in templates:
        p = params(main_statement(path.read_text(), name))
        assert {k:v for k,v in p.items() if k not in allowed} == {k:v for k,v in original.items() if k not in allowed}
        w = number(p["w"])
        assert all(abs(number(p[k])-w*155e-9) < 1e-25 for k in ("ad", "as"))
        assert all(abs(number(p[k])-2*(w+155e-9)) < 1e-20 for k in ("pd", "ps"))
        geometry.append(dict(source=str(path.relative_to(ROOT)), instance=name, params=p, sha256=sha(path)))
    includes = []
    for path, digest in base["include_sha256"].items():
        path = Path(path)
        assert sha(path) == digest
        dest = OUT/"inputs"/path.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(path.read_bytes())
        includes.append(str(dest))
    cases = {}
    for width in (1, 2, 3):
        case = OUT/f"w{width}"
        path = case/f"b_sine_w{width}.scs"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(Path(base["deck"]).read_bytes()) if width == 1 else path.write_text(resize(text, width), encoding="utf-8")
        candidate = path.read_text(encoding="utf-8")
        altered = params(main_statement(candidate))
        changed = {k for k in original if original[k] != altered[k]}
        assert changed == (set() if width == 1 else allowed)
        assert candidate.replace(main_statement(candidate), main_statement(text), 1) == text
        assert re.search(r"XBOOTP \(.*sar_bootstrap_canvas_flat_8b", text)
        assert re.search(r"XBOOTN \(.*sar_bootstrap_canvas_flat_8b", text)
        if width == 1:
            assert sha(path) == base["deck_sha256"]
        cases[str(width)] = dict(deck=str(path), deck_sha256=sha(path), width_um=width,
            changed_parameters=sorted(changed), main_params=altered, reused=width == 1)
        stage(case, "reused_complete" if width == 1 else "prepared", frames=24)
    dump(OUT/"context.json", dict(config=cfg, config_sha256=sha(CFG), cases=cases,
        baseline_context_sha256=sha(BASE/"context.json"), baseline_deck_sha256=base["deck_sha256"],
        baseline_waveform=tracked["waveform"], includes=includes,
        include_sha256={p:sha(p) for p in includes}, geometry_templates=geometry,
        unchanged_native_topology_and_timing=True, declared_stop_preserved=True))
    stage(OUT, "prepared")
    check()


def check():
    ctx = read(OUT/"context.json")
    assert sha(CFG) == ctx["config_sha256"]
    baseline = read(BASE/"context.json")
    assert sha(BASE/"context.json") == ctx["baseline_context_sha256"]
    text = Path(baseline["deck"]).read_text(encoding="utf-8")
    for path, digest in ctx["include_sha256"].items():
        assert sha(path) == digest
    for width in (1, 2, 3):
        case = ctx["cases"][str(width)]
        assert sha(case["deck"]) == case["deck_sha256"]
        assert Path(case["deck"]).read_text(encoding="utf-8") == resize(text, width)
    print("W_ONLY_INPUT_GEOMETRY_PRECISION_IDENTITY_PASS", flush=True)


def native(width):
    from virtuoso_bridge.spectre.runner import SpectreSimulator, _run_spectre_remote, spectre_mode_args
    case = OUT/f"w{width}"
    assert width in (2, 3) and read(case/"flow.json")["stage"] == "prepared"
    check()
    ctx = read(OUT/"context.json")
    stage(case, "running_native", frames=24)
    try:
        (case/"spectre").mkdir(parents=True, exist_ok=True)
        sim = SpectreSimulator.from_env(profile="t28_io", timeout=14400)
        assert sim._remote_host == "thu-wei" and sim._remote_user == "chenzc_intern25"
        result = _run_spectre_remote(netlist=Path(ctx["cases"][str(width)]["deck"]),
            params=dict(include_files=ctx["includes"]), runner=sim._get_ssh_runner(),
            remote_work_dir=REMOTE_BASE, base_output_dir=case/"spectre", spectre_cmd=BIN,
            spectre_args=[*spectre_mode_args("aps"), "+lqtimeout", "60", "+mt=4"],
            output_format="psfascii", timeout=14400, keep_remote_files=False)
        dump(case/"run_artifacts.json", result._asdict())
        assert result.success, result.error
        stage(case, "downloaded_native", frames=24)
    except Exception as exc:
        stage(case, "failed", error=repr(exc))
        raise


def parse(width):
    from virtuoso_bridge.spectre.runner import _SpectreRunResult, _build_simulation_result
    case = OUT/f"w{width}"
    assert read(case/"flow.json")["stage"] == "downloaded_native"
    record = read(case/"run_artifacts.json")
    record["output_dir"] = Path(record["output_dir"]) if record["output_dir"] else None
    stage(case, "parsing_native", frames=24)
    start = time.monotonic()
    result = _build_simulation_result(_SpectreRunResult(**record), "psfascii", extra_metadata=record["metadata"])
    dump(case/"result.json", dict(ok=result.ok, errors=result.errors, warnings=result.warnings,
        metadata=result.metadata, parse_seconds=time.monotonic()-start))
    assert result.ok, result.errors
    stage(case, "saving_waveforms", frames=24)
    wave = {str(k).strip('"').replace("\\", "").lower():v for k,v in result.data.items()
            if isinstance(v, list) and str(k).lower() != "units"}
    assert len(wave) == 45 and "time" in wave
    assert wave["time"][0] == 0 and abs(wave["time"][-1]-2400e-9) < 1e-14
    assert all(len(v) == len(wave["time"]) and all(math.isfinite(x) for x in v) for v in wave.values())
    with (case/"waveform.pickle").open("wb") as stream:
        pickle.dump(wave, stream, protocol=5)
    dump(case/"waveform_receipt.json", dict(sha256=sha(case/"waveform.pickle"),
        points=len(wave["time"]), signals=44, start_s=wave["time"][0], stop_s=wave["time"][-1]))
    stage(case, "parsed", frames=24)


def run():
    assert read(OUT/"flow.json")["stage"] == "prepared"
    descriptor = os.open(OUT/"launch.lock", os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    os.close(descriptor)
    check()
    stage(OUT, "running_native", cases=[2, 3], reused_case=1)
    processes = []
    try:
        for width in (2, 3):
            case = OUT/f"w{width}"
            log = (case/"runner.log").open("w", encoding="utf-8")
            env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
            proc = subprocess.Popen([sys.executable, __file__, "native", "--width", str(width)],
                cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, env=env,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            log.close()
            processes.append(proc)
        dump(OUT/"workers.json", {str(w):p.pid for w,p in zip((2,3), processes)})
        codes = [p.wait() for p in processes]
        assert codes == [0, 0], codes
        for width in (2, 3):
            stage(OUT, "parsing_serially", case=width)
            subprocess.run([sys.executable, __file__, "parse", "--width", str(width)], cwd=ROOT, check=True)
        stage(OUT, "analyzing")
        subprocess.run([str(ROOT/".venv/Scripts/python.exe"),
            str(ROOT/"scripts/integration/b_sine_main_w_analyze.py")], cwd=ROOT, check=True)
        stage(OUT, "awaiting_visual_review")
    except Exception as exc:
        stage(OUT, "failed", error=repr(exc))
        raise


def status():
    from virtuoso_bridge.transport.tunnel import SSHClient
    reports = {"1":dict(stage="reused_complete", completed_frames=24, reused=True)}
    ssh = None
    for width in (2, 3):
        case = OUT/f"w{width}"
        state = read(case/"flow.json")
        local = case/"spectre/spectre.out"
        log = local.read_text(errors="replace") if local.exists() else ""
        process = []
        remote = None
        if state["stage"] == "running_native" and "spectre completes with" not in log:
            lines = (case/"runner.log").read_text(errors="replace")
            commands = re.findall(r"(?m)^\[Command\] (.*)$", lines)
            if commands:
                match = re.search(r"\+log ([^ ]+/spectre.out)", commands[-1])
                assert match and re.fullmatch(REMOTE_BASE+r"/[0-9a-f]+/spectre.out", match[1])
                remote = match[1]
                folder = remote.rsplit("/", 1)[0]
                if ssh is None:
                    ssh = SSHClient.from_env(profile="t28_io")
                q = shlex.quote(remote)
                fetch = ssh.spectre_runner.run_command(f"if test -f {q}; then cat {q}; fi", timeout=30)
                assert fetch.returncode == 0
                log = fetch.stdout
                ps = ssh.spectre_runner.run_command("ps -u chenzc_intern25 -ww -o pid,ppid,etime,pcpu,comm,args", timeout=20)
                for line in ps.stdout.splitlines():
                    p = line.split(None, 5)
                    if len(p) == 6 and p[0].isdigit() and folder+f"/b_sine_w{width}.scs" in p[5]:
                        process.append(dict(pid=int(p[0]), parent=int(p[1]), elapsed=p[2], cpu=p[3], command=p[4]))
                # Download/remote cleanup can finish between the first local read
                # and this query. Prefer the completed local log in that race.
                if local.exists():
                    downloaded_log = local.read_text(errors="replace")
                    if "spectre completes with" in downloaded_log:
                        log = downloaded_log
                state = read(case/"flow.json")
        records = re.findall(r"R3MEAS,(\d+),(\d+),(\d+),(\d+),(\d+),([^\s,]+)", log)
        probes = re.findall(r"BSINE,(\d+),([^\s,]+),([^\s,]+),([^\s,]+)", log)
        parameters = {}
        if "Important parameter values:" in log and "Output and IC/nodeset" in log:
            block = log.split("Important parameter values:",1)[1].split("Output and IC/nodeset",1)[0]
            parameters = dict(re.findall(r"(?m)^\s+([\w()]+) = ([^\n]+)",block))
        old_parameters = read(ROOT/"verification/integration/b_sine_period_results.json")["reported_solver_parameters"]
        differences = {k:dict(baseline=v,current=parameters.get(k)) for k,v in old_parameters.items()
                       if parameters and parameters.get(k) != v}
        reports[str(width)] = dict(local=state, completed_frames=len(records), total_frames=24,
            last_records=records[-2:], remote_log=remote, native_processes=process,
            last_hold_probes=probes[-2:], solver_parameter_differences=differences,
            completed_records_all_8compare_and_stable=bool(records) and all(r[2] == "8" and r[4] == "1" for r in records),
            native_success="spectre completes with 0 errors" in log,
            has_CMI="CMI-2754" in log, has_LTE_relaxation="SPECTRE-16780" in log,
            warning_lines=[line.strip() for line in log.splitlines() if "WARNING (" in line])
        if remote:
            dump(case/"remote.json", dict(log=remote, processes=process))
    if ssh:
        ssh.close()
    report = dict(local=read(OUT/"flow.json"), checked_utc=datetime.now(timezone.utc).isoformat(), cases=reports)
    dump(OUT/"progress.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["preflight", "prepare", "check", "native", "parse", "run", "status"])
    p.add_argument("--width", type=int, choices=[2, 3])
    a = p.parse_args()
    globals()[a.action](a.width) if a.action in ("native", "parse") else globals()[a.action]()
