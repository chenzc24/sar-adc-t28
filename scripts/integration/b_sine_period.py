"""One bounded native B sine run, immutable inputs and read-only progress checks."""
from __future__ import annotations

import argparse
import contextlib
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

import yaml

import r3_b_oa as adoption
from freeze_r0 import object_digest, schematic_surface

ROOT = adoption.ROOT
OUT = ROOT / "output/b_sine_period"
CFG = ROOT / "config/r3_b_sine_period.yaml"
DECK = OUT / "decks/b_sine_period.scs"
MONITOR = ROOT / "models/veriloga/r3_performance/r3_perf_monitor.va"
STOPPER = ROOT / "models/veriloga/r3_anomaly_replay/r3_replay_stop.va"
PROBE = ROOT / "models/veriloga/r3_b_sine_period/r3_sine_probe.va"
os.environ.setdefault("VB_DISABLE_CONTROL_MASTER", "1")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(name, data):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".pending")
    pending.write_text(json.dumps(data, indent=2, default=str, allow_nan=False) + "\n", encoding="utf-8")
    pending.replace(path)


def read(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def stage(value, **extra):
    dump("flow.json", dict(stage=value, updated_utc=datetime.now(timezone.utc).isoformat(),
                           local_pid=os.getpid(), **extra))


def signals():
    names = ["SAMPLE", "VINP_SRC", "VINN_SRC", "VINP", "VINN", "TOPP", "TOPN",
             "CMP_CLK", "COMP_P", "COMP_N", "VREFP", "VREFN", "VDD!"]
    names += [f"D{b}" for b in range(8)]
    names += [f"XDUT.XCOMP.{n}" for n in ("X", "Y", "TAIL")]
    names += ["XDUT.GCOMMIT"]
    names += [f"XDUT.XCTRL.{n}" for n in ("PHI_W", "PHI_U", "ACTIVE")]
    names += [f"XDUT.XCTRL.T{b}" for b in range(8)]
    names += [f"XDUT.XBOOT{s}.G" for s in "PN"]
    names += [f"XDUT.G{s}{q}7" for s in "PN" for q in "PN"]
    names += [f"XDUT.XCDAC.B{s}7" for s in "PN"]
    assert len(names) == len(set(names))
    return names


def preflight():
    from virtuoso_bridge import VirtuosoClient
    assert not (OUT / "preflight.json").exists(), "Do not overwrite preflight"
    receipt = json.loads((ROOT / "verification/integration/r3_b_oa_results.json").read_text())
    c = VirtuosoClient.from_env(profile="t28_io", timeout=30, log_to_ciw=False)
    info = c.library.get(adoption.LIB)
    assert info.path == "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28"
    assert info.technology_library == "tsmcN28"
    for name, expected_path in (
        (adoption.TOP, adoption.OUT / f"after/{adoption.TOP}.json"),
        (adoption.TB, adoption.OUT / f"before/{adoption.TB}.json"),
    ):
        data = c.schematic.read(adoption.LIB, name, include_positions=True, param_filters=None)
        expected = json.loads(expected_path.read_text())
        assert adoption.normalized(data) == adoption.normalized(expected), name
        dump(f"oa/{name}.json", data)
    dependencies = json.loads((adoption.OUT / "dependencies.json").read_text())
    for name, expected in dependencies.items():
        data = c.schematic.read(adoption.LIB, name, include_positions=False, param_filters=None)
        assert object_digest(schematic_surface(data)) == expected, name
    gate_cdf = adoption.cdf(c, adoption.NEW)
    assert gate_cdf == json.loads((adoption.OUT / "old_cdf.json").read_text())
    includes = []
    for cell, expected in (
        (adoption.NEW, receipt["adoption"]["adopted_VA_sha256"]),
        ("sar8j_refcommit", sha(ROOT / "models/veriloga/sar8_join_r2/sar8j_refcommit.va")),
    ):
        path = OUT / "inputs" / f"{cell}.va"
        path.parent.mkdir(parents=True, exist_ok=True)
        result = c.download_file(f"{info.path}/{cell}/veriloga/veriloga.va", path)
        assert result.ok and sha(path) == expected, cell
        includes.append(str(path))
    exported = c.schematic.export_netlist(adoption.LIB, adoption.TB, OUT / "exports/current",
                                          simulator="spectre", timeout=300)
    dump("exports/receipt.json", exported)
    current = Path(exported["input_file"])
    prior = adoption.OUT / "exports/after/input.scs"
    assert sha(prior) == receipt["adoption"]["after_netlist_sha256"]
    assert adoption.r3.r1.blocks(current.read_text()) == adoption.r3.r1.blocks(prior.read_text())
    dump("preflight.json", dict(library=dataclasses.asdict(info), windows=c.list_windows(),
        native_dependencies_checked=len(dependencies), exact_current_B_OA_netlist=True,
        export=str(current), export_sha256=sha(current), gate_CDF=gate_cdf,
        include_files=includes, OA_mutations=[]))
    print("CURRENT_B_PREFLIGHT_PASS", flush=True)


def prepare():
    assert not DECK.exists(), "One immutable case only"
    cfg = yaml.safe_load(CFG.read_text())
    assert cfg["total_frames"] == 24 and cfg["observed_frames"] == 20
    assert cfg["input_frequency_hz"] * 20 / cfg["sample_rate_hz"] == 1
    pre = read("preflight.json")
    source = Path(pre["export"])
    assert sha(source) == pre["export_sha256"]
    text = source.read_text()
    blocks = adoption.r3.r1.blocks(text)
    text, count = re.subn(r"(?m)^parameters (.*(?:\n[ \t]+.*)*)", "parameters SUP=.9 VDIFF=.8", text)
    assert count == 1
    for side, phase in zip("PN", cfg["source_phase_degrees"]):
        statement = (f"VVIN{side} (VIN{side}_SRC 0) vsource type=sine dc=.45 sinedc=.45 "
                     f"ampl=.4 freq=500000 sinephase={phase}")
        text, count = re.subn(rf"(?m)^VVIN{side} \([^\n]+$", statement, text)
        assert count == 1
    text = text.replace("save=allpub", "save=selected").replace("reltol=1e-4", "reltol=1e-5")
    text = text.replace("vabstol=1e-6", "vabstol=1e-8").replace("iabstol=1e-12", "iabstol=1e-13")
    text = re.sub(r"(?m)^\w+ info [^\n]*\n", "", text)
    for path in pre["include_files"]:
        path = Path(path)
        text, count = re.subn(rf'(?m)^ahdl_include "[^\n"]+/{path.stem}/veriloga/veriloga.va"',
                             f'ahdl_include "{path.name}"', text)
        assert count == 1
    text += '\nXMEASURE (SAMPLE CMP_CLK VDD! D0 D1 D2 D3 D4 D5 D6 D7) r3_perf_monitor\n'
    text += 'XPROBE (VINP_SRC VINN_SRC TOPP TOPN) r3_sine_probe\n'
    text += 'XSTOP (SAMPLE) r3_replay_stop stop_s=2400n\n'
    text += ('tran_b_sine tran stop=51600n maxstep=10p errpreset=conservative '
             'strobeperiod=1n strobeoutput=all\n')
    text += "save " + " ".join(signals()) + "\n"
    snapshots = list(pre["include_files"])
    for path in (MONITOR, STOPPER, PROBE):
        dest = OUT / "inputs" / path.name
        assert not dest.exists()
        dest.write_bytes(path.read_bytes())
        snapshots.append(str(dest))
        text += f'ahdl_include "{path.name}"\n'
    assert adoption.r3.r1.blocks(text) == blocks, "DUT statements changed"
    # Compared with the previous B replay, only testbench sources/observers/
    # outputs differ. No model/pin/WL or source/reference impedance substitutions.
    prior = ROOT / "output/r3_refgate_events/b3/decks/first12_b3.scs"
    prior_text = prior.read_text()
    for key in ("reltol=1e-5", "vabstol=1e-8", "iabstol=1e-13",
                "stop=51600n", "maxstep=10p", "errpreset=conservative"):
        assert key in text and key in prior_text, key
    DECK.parent.mkdir(parents=True, exist_ok=True)
    DECK.write_text(text, encoding="utf-8")
    dump("context.json", dict(config=cfg, config_sha256=sha(CFG), deck=str(DECK),
        deck_sha256=sha(DECK), export_sha256=pre["export_sha256"],
        include_files=snapshots, include_sha256={p: sha(p) for p in snapshots},
        native_subcircuits_unmodified=True, saved_signals=signals(), source_model_commit="f115f7f",
        declared_stop_preserves_prior_B_defaults=True, full_continuous_output=True,
        no_FFT=True, no_OA_edits=True))
    stage("prepared", frames=24)
    check()
    print("PREPARED_ONE_PERIOD_24_FRAMES", flush=True)


def check():
    ctx = read("context.json")
    assert sha(CFG) == ctx["config_sha256"] and sha(DECK) == ctx["deck_sha256"]
    for path, digest in ctx["include_sha256"].items():
        assert sha(path) == digest, path
    text = DECK.read_text()
    blocks = adoption.r3.r1.blocks(Path(read("preflight.json")["export"]).read_text())
    assert blocks == adoption.r3.r1.blocks(text)
    assert text.count("r3_replay_stop stop_s=2400n") == 1
    assert all(k in text for k in ("sinephase=-72", "sinephase=108", "freq=500000", "ampl=.4"))
    assert "strobeonly" not in text and len(ctx["saved_signals"]) == 44
    assert all(token not in PROBE.read_text() for token in ("<+", "$finish", "$cds_finish"))
    print("DECK_SOURCE_IDENTITY_CHECK_PASS", flush=True)


def run():
    from virtuoso_bridge.spectre.runner import SpectreSimulator, spectre_mode_args
    assert read("flow.json")["stage"] == "prepared", "Do not duplicate or restart a run"
    check()
    ctx = read("context.json")
    stage("running_native", frames=24, started_utc=datetime.now(timezone.utc).isoformat())
    try:
        with (OUT / "runner.log").open("w", encoding="utf-8", buffering=1) as log, \
                contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            sim = SpectreSimulator.from_env(profile="t28_io", work_dir=OUT / "spectre", timeout=14400,
                    spectre_args=[*spectre_mode_args("aps"), "+lqtimeout", "60"])
            result = sim.run_simulation(DECK, dict(include_files=ctx["include_files"], spectre_args=["+mt=4"]))
        dump("result.json", dict(ok=result.ok, errors=result.errors, warnings=result.warnings,
            metadata=result.metadata, deck_sha256=ctx["deck_sha256"]))
        assert result.ok, result.errors
        stage("saving_waveforms", frames=24)
        wave = {str(k).strip('"').replace("\\", "").lower(): v for k, v in result.data.items()
                if isinstance(v, list) and str(k).lower() != "units"}
        assert "time" in wave and all(s.lower() in wave for s in signals())
        assert all(len(v) == len(wave["time"]) and all(math.isfinite(x) for x in v) for v in wave.values())
        assert wave["time"][0] == 0 and abs(wave["time"][-1] - 2400e-9) < 1e-14
        path = OUT / "waveform.pickle"
        with path.open("wb") as stream:
            pickle.dump(wave, stream, protocol=5)
        dump("waveform_receipt.json", dict(sha256=sha(path), points=len(wave["time"]),
            signals=len(wave)-1, start_s=wave["time"][0], stop_s=wave["time"][-1]))
        result.data.clear()
        del wave, result
        stage("analyzing", frames=24)
        project_python = ROOT / ".venv/Scripts/python.exe"
        subprocess.run([str(project_python), str(ROOT / "scripts/integration/b_sine_analyze.py")],
                       cwd=ROOT, check=True)
        stage("awaiting_visual_review", frames=24, report="output/b_sine_period/summary.json")
    except Exception as exc:
        stage("failed", error=repr(exc))
        raise


def status():
    state = read("flow.json")
    report = dict(local=state, checked_utc=datetime.now(timezone.utc).isoformat())
    if state["stage"] in ("prepared", "failed", "awaiting_visual_review", "complete"):
        if (OUT / "result.json").exists():
            result = read("result.json")
            report["native_result"] = {k: result[k] for k in ("ok", "errors", "warnings")}
        dump("progress.json", report)
        print(json.dumps(report, indent=2))
        return
    log_path = OUT / "runner.log"
    text = log_path.read_text(errors="replace") if log_path.exists() else ""
    commands = re.findall(r"(?m)^\[Command\] (.*)$", text)
    if not commands:
        report["note"] = "Native command not emitted yet; staging inputs or connecting"
        dump("progress.json", report)
        print(json.dumps(report, indent=2))
        return
    match = re.search(r"\+log ([^ ]+/spectre.out)", commands[-1])
    assert match
    native_log = match[1]
    assert re.fullmatch(r"/tmp/virtuoso_bridge_chenzc_intern25/90590/virtuoso_bridge_spectre/[0-9a-f]+/spectre.out", native_log)
    folder = native_log.rsplit("/", 1)[0]
    from virtuoso_bridge.transport.tunnel import SSHClient
    ssh = SSHClient.from_env(profile="t28_io")
    runner = ssh.spectre_runner
    qlog = shlex.quote(native_log)
    result = runner.run_command(f"if test -f {qlog}; then cat {qlog}; fi", timeout=30)
    assert result.returncode == 0, result.stderr
    native_text = result.stdout
    measurements = re.findall(r"R3MEAS,(\d+),(\d+),(\d+),(\d+),(\d+),([^\s,]+)", native_text)
    probes = re.findall(r"BSINE,(\d+),([^\s,]+),([^\s,]+),([^\s,]+)", native_text)
    pid_result = runner.run_command(f"if test -f {shlex.quote(folder+'/spectre.pid')}; then cat {shlex.quote(folder+'/spectre.pid')}; fi", timeout=15)
    pid = pid_result.stdout.strip()
    process = ""
    tree = []
    native_pids = []
    if pid.isdigit():
        # The shell PID receipt can be a short-lived launcher. Bind the actual
        # process to this exact immutable deck path, not to a generic spectre PID.
        # Use ordinary headers: old procps treats comma-separated empty headers
        # differently and can silently return only a single column.
        ps = runner.run_command("ps -u chenzc_intern25 -ww -o pid,ppid,etime,pcpu,comm,args", timeout=15)
        assert ps.returncode == 0, ps.stderr
        records = [line.split(None, 5) for line in ps.stdout.splitlines()]
        tree = [dict(pid=int(p[0]), parent=int(p[1]), elapsed=p[2], cpu_percent=p[3], command=p[4])
                for p in records if len(p) == 6 and p[0].isdigit() and
                folder + "/b_sine_period.scs" in p[5]]
        native_pids = [p["pid"] for p in tree if "spectre" in p["command"].lower()]
        process = "\n".join(f"{p['pid']} {p['elapsed']} {p['cpu_percent']} {p['command']}" for p in tree)
    warnings = [line.strip() for line in native_text.splitlines() if "WARNING (" in line]
    parameters = {}
    precision_differences = {}
    if "Important parameter values:" in native_text and "Output and IC/nodeset" in native_text:
        block = native_text.split("Important parameter values:", 1)[1].split("Output and IC/nodeset", 1)[0]
        parameters = dict(re.findall(r"(?m)^\s+([\w()]+) = ([^\n]+)", block))
        original = json.loads((ROOT / "output/r3_refgate_events/b3/analysis.json").read_text())["reported_solver_parameters"]
        precision_differences = {k: dict(previous=v, current=parameters.get(k)) for k, v in original.items()
                                 if k != "outputstart" and parameters.get(k) != v}
    report.update(remote_folder=folder, remote_log=native_log, wrapper_pid=pid, native_pids=native_pids,
        native_process_tree=tree,
        native_process=process, completed_frames=len(measurements), total_frames=24,
        last_measurements=measurements[-3:], last_hold_probes=probes[-3:],
        warnings=warnings, has_CMI="CMI-2754" in native_text,
        reported_solver_parameters=parameters, precision_differences=precision_differences,
        has_LTE_relaxation="SPECTRE-16780" in native_text,
        native_success_footer="spectre completes with 0 errors" in native_text,
        native_log_tail=native_text.splitlines()[-8:])
    dump("remote.json", dict(folder=folder, log=native_log, wrapper_pid=pid, native_pids=native_pids))
    dump("progress.json", report)
    print(json.dumps(report, indent=2))
    ssh.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["preflight", "prepare", "check", "run", "status"])
    args = parser.parse_args()
    globals()[args.action]()


if __name__ == "__main__":
    main()
