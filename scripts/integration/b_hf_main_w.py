"""Isolated native B 4.5 MHz width batch; immutable old inputs and no OA writes."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import dataclasses
from datetime import datetime, timezone
import math
import os
from pathlib import Path
import pickle
import re
import shlex
import subprocess
import sys
import time

import b_sine_main_w as low

ROOT, BASE = low.ROOT, low.BASE
OUT = ROOT/"output/b_hf_main_w"
CFG = ROOT/"config/b_hf_main_w.yaml"
REMOTE_BASE, BIN = low.REMOTE_BASE, low.BIN
sha, read, dump, stage = low.sha, low.read, low.dump, low.stage
os.environ.setdefault("VB_DISABLE_CONTROL_MASTER", "1")


def stimulus(text, cfg):
    peak = cfg["full_scale_differential_peak_v"]*10**(cfg["input_level_dbfs"]/20)
    statements = []
    for side, phase in zip("PN",cfg["source_phase_degrees"]):
        old = re.search(rf"(?m)^VVIN{side} [^\n]+$",text)
        assert old and "freq=500000" in old[0] and "ampl=.4" in old[0]
        new = old[0].replace("freq=500000",f"freq={cfg['input_frequency_hz']}").replace("ampl=.4",f"ampl={peak/2:.17g}")
        text = text.replace(old[0],new,1)
        statements.append(dict(side=side,old=old[0],new=new))
    assert len(re.findall(r"\bVDIFF\b",text)) == 1, "VDIFF must remain unused"
    return text, peak, statements


def preflight():
    from virtuoso_bridge import VirtuosoClient
    import r3_b_oa as adoption
    from freeze_r0 import object_digest, schematic_surface
    assert not (OUT/"preflight.json").exists()
    c = VirtuosoClient.from_env(profile="t28_io",timeout=30,log_to_ciw=False)
    info = c.library.get(adoption.LIB)
    assert info.path == "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28"
    assert info.technology_library == "tsmcN28"
    for name in (adoption.TOP,adoption.TB):
        current = c.schematic.read(adoption.LIB,name,include_positions=True,param_filters=None,timeout=30)
        assert adoption.normalized(current) == adoption.normalized(read(BASE/f"oa/{name}.json")), name
    deps = read(ROOT/"output/r3_b_oa/dependencies.json")
    for name, expected in deps.items():
        current = c.schematic.read(adoption.LIB,name,include_positions=False,param_filters=None,timeout=30)
        assert object_digest(schematic_surface(current)) == expected, name
    dump(OUT/"preflight.json",dict(library=dataclasses.asdict(info),windows=c.list_windows(),
        unchanged_dependencies=len(deps),OA_writes=[],profile="t28_io",bridge_version="0.8.0"))
    print("READ_ONLY_CURRENT_B_HF_PREFLIGHT_PASS",flush=True)


def prepare():
    import yaml
    assert not (OUT/"context.json").exists() and (OUT/"preflight.json").exists()
    low.check()
    cfg = yaml.safe_load(CFG.read_text(encoding="utf-8"))
    assert cfg["width_multipliers"] == [1,2,3] and cfg["total_frames"] == 24
    assert cfg["input_frequency_hz"]*cfg["observed_frames"]/cfg["sample_rate_hz"] == 9
    base = read(BASE/"context.json")
    original = Path(base["deck"]).read_text(encoding="utf-8")
    template, peak, changes = stimulus(original,cfg)
    assert abs(20*math.log10(peak/.9)+1) < 1e-12
    includes = []
    for path,digest in base["include_sha256"].items():
        assert sha(path) == digest
        dest = OUT/"inputs"/Path(path).name
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(Path(path).read_bytes())
        includes.append(str(dest))
    cases = {}
    for width in (1,2,3):
        case = OUT/f"w{width}"
        case.mkdir(parents=True,exist_ok=True)
        deck = case/f"b_hf_w{width}.scs"
        deck.write_text(low.resize(template,width),encoding="utf-8")
        cases[str(width)] = dict(deck=str(deck),deck_sha256=sha(deck),width_um=width,
                                main_params=low.params(low.main_statement(deck.read_text())))
        stage(case,"prepared",frames=24)
    dump(OUT/"context.json",dict(config=cfg,config_sha256=sha(CFG),input_differential_peak_v=peak,
        input_leg_peak_v=peak/2,input_source_changes=changes,cases=cases,includes=includes,
        include_sha256={p:sha(p) for p in includes},baseline_context_sha256=sha(BASE/"context.json"),
        baseline_deck_sha256=sha(base["deck"]),low_frequency_result_sha256=sha(ROOT/cfg["low_frequency_comparison"]),
        starting_commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        all_three_cases_new_native=True,unchanged_topology_timing_precision=True,no_OA_edits=True))
    stage(OUT,"prepared",frames_per_case=24)
    check()


def check():
    ctx = read(OUT/"context.json")
    assert sha(CFG) == ctx["config_sha256"] and sha(BASE/"context.json") == ctx["baseline_context_sha256"]
    baseline = read(BASE/"context.json")
    assert sha(baseline["deck"]) == ctx["baseline_deck_sha256"]
    assert sha(ROOT/ctx["config"]["low_frequency_comparison"]) == ctx["low_frequency_result_sha256"]
    template,peak,changes = stimulus(Path(baseline["deck"]).read_text(encoding="utf-8"),ctx["config"])
    assert peak == ctx["input_differential_peak_v"] and changes == ctx["input_source_changes"]
    for path,digest in ctx["include_sha256"].items():
        assert sha(path) == digest
    for w in (1,2,3):
        case = ctx["cases"][str(w)]
        assert sha(case["deck"]) == case["deck_sha256"]
        text = Path(case["deck"]).read_text(encoding="utf-8")
        assert text == low.resize(template,w)
        assert "maxstep=10p errpreset=conservative" in text and "strobeonly" not in text
    print("HF_INPUT_SOURCE_WIDTH_GEOMETRY_PRECISION_IDENTITY_PASS",flush=True)


class BoundedTransfers:
    """Transport bounds only; do not change any native simulation argument."""
    def __init__(self,runner,case):
        self.runner,self.case = runner,case
        self.records = []
        self.required = set()

    def __getattr__(self,name):
        return getattr(self.runner,name)

    def record(self,**values):
        self.records.append(dict(utc=datetime.now(timezone.utc).isoformat(),**values))
        dump(self.case/"transfer_receipt.json",self.records)

    def download(self,remote_path,local_path,recursive=False,timeout=None):
        from virtuoso_bridge.transport.ssh import CommandResult
        optional = Path(remote_path).name in ("spectre.ic","spectre.fc")
        bound = 900 if recursive else (45 if optional else 60)
        try:
            r = self.runner.download(remote_path,local_path,recursive=recursive,timeout=bound)
        except subprocess.TimeoutExpired as exc:
            self.record(operation="download",remote=remote_path,timeout_s=bound,optional=optional,error=type(exc).__name__)
            if not optional:
                raise
            return CommandResult(1,"","Optional transfer timed out; original native data unmodified")
        self.record(operation="download",remote=remote_path,timeout_s=bound,optional=optional,returncode=r.returncode)
        if r.returncode == 0 and not optional:
            self.required.add("raw" if recursive else "log")
        return r

    def run_command(self,command,timeout=None):
        from virtuoso_bridge.transport.ssh import CommandResult
        cleanup = re.fullmatch(r"rm -rf "+re.escape(REMOTE_BASE)+r"/[0-9a-f]{8}",command)
        if cleanup:
            if self.required != {"raw","log"}:
                self.record(operation="cleanup",command=command,retained_for_recovery=True)
                return CommandResult(1,"","Retained scratch because required download incomplete")
            try:
                r = self.runner.run_command(command,timeout=30)
                self.record(operation="cleanup",command=command,returncode=r.returncode)
                return r
            except subprocess.TimeoutExpired:
                self.record(operation="cleanup",command=command,timeout_s=30,retained_for_recovery=True)
                return CommandResult(1,"","Scratch cleanup timed out")
        return self.runner.run_command(command,timeout=timeout)


def native(width):
    from virtuoso_bridge.spectre.runner import SpectreSimulator,_run_spectre_remote,spectre_mode_args
    case = OUT/f"w{width}"
    assert width in (1,2,3) and read(case/"flow.json")["stage"] == "prepared"
    check()
    stage(case,"running_native",frames=24)
    try:
        sim = SpectreSimulator.from_env(profile="t28_io",timeout=14400)
        assert sim._remote_host == "thu-wei" and sim._remote_user == "chenzc_intern25"
        ctx = read(OUT/"context.json")
        (case/"spectre").mkdir(parents=True,exist_ok=True)
        runner = BoundedTransfers(sim._get_ssh_runner(),case)
        r = _run_spectre_remote(netlist=Path(ctx["cases"][str(width)]["deck"]),
            params=dict(include_files=ctx["includes"]),runner=runner,remote_work_dir=REMOTE_BASE,
            base_output_dir=case/"spectre",spectre_cmd=BIN,
            spectre_args=[*spectre_mode_args("aps"),"+lqtimeout","60","+mt=4"],
            output_format="psfascii",timeout=14400,keep_remote_files=False)
        dump(case/"run_artifacts.json",r._asdict())
        assert r.success, r.error
        assert (case/"spectre/spectre.out").exists(), "Required native log missing"
        stage(case,"downloaded_native",frames=24)
    except Exception as exc:
        stage(case,"failed",error=repr(exc))
        raise


def parse(width):
    from virtuoso_bridge.spectre.runner import _SpectreRunResult,_build_simulation_result
    case = OUT/f"w{width}"
    assert read(case/"flow.json")["stage"] == "downloaded_native"
    record = read(case/"run_artifacts.json")
    record["output_dir"] = Path(record["output_dir"]) if record["output_dir"] else None
    stage(case,"parsing_native",frames=24)
    started = time.monotonic()
    r = _build_simulation_result(_SpectreRunResult(**record),"psfascii",extra_metadata=record["metadata"])
    dump(case/"result.json",dict(ok=r.ok,errors=r.errors,warnings=r.warnings,metadata=r.metadata,
                               parse_seconds=time.monotonic()-started))
    assert r.ok, r.errors
    stage(case,"saving_waveforms",frames=24)
    wave = {str(k).strip('"').replace("\\","").lower():v for k,v in r.data.items()
            if isinstance(v,list) and str(k).lower() != "units"}
    assert len(wave) == 45 and wave["time"][0] == 0 and abs(wave["time"][-1]-2400e-9)<1e-14
    assert all(len(v)==len(wave["time"]) and all(math.isfinite(x) for x in v) for v in wave.values())
    with (case/"waveform.pickle").open("wb") as stream:
        pickle.dump(wave,stream,protocol=5)
    dump(case/"waveform_receipt.json",dict(sha256=sha(case/"waveform.pickle"),points=len(wave["time"]),
        signals=44,start_s=wave["time"][0],stop_s=wave["time"][-1]))
    stage(case,"parsed",frames=24)


def run():
    assert read(OUT/"flow.json")["stage"] == "prepared"
    os.close(os.open(OUT/"launch.lock",os.O_CREAT|os.O_EXCL|os.O_WRONLY))
    check()
    stage(OUT,"running_batch",cases=[1,2,3],frames_per_case=24)
    def worker(w):
        with (OUT/f"w{w}/runner.log").open("w",encoding="utf-8") as log:
            return subprocess.run([sys.executable,__file__,"native","--width",str(w)],cwd=ROOT,
                stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,PYTHONUNBUFFERED="1"),
                creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0)).returncode
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {pool.submit(worker,w):w for w in (1,2,3)}
            for future in as_completed(futures):
                w = futures[future]
                assert future.result() == 0, f"W{w} native/download failed; no rerun"
                stage(OUT,"running_batch",parsing_case=w,cases=[1,2,3])
                subprocess.run([sys.executable,__file__,"parse","--width",str(w)],cwd=ROOT,check=True)
        stage(OUT,"analyzing")
        subprocess.run([str(ROOT/".venv/Scripts/python.exe"),
                        str(ROOT/"scripts/integration/b_hf_main_w_analyze.py")],cwd=ROOT,check=True)
        stage(OUT,"awaiting_visual_review")
    except Exception as exc:
        stage(OUT,"failed",error=repr(exc))
        raise


def status():
    from virtuoso_bridge.transport.tunnel import SSHClient
    reports,ssh = {},None
    try:
        for w in (1,2,3):
            case = OUT/f"w{w}"
            state = read(case/"flow.json")
            local = case/"spectre/spectre.out"
            log = local.read_text(errors="replace") if local.exists() else ""
            processes,remote,error = [],None,None
            if state["stage"] == "running_native" and "spectre completes with" not in log:
                commands = re.findall(r"(?m)^\[Command\] (.*)$",(case/"runner.log").read_text(errors="replace"))
                if commands:
                    m = re.search(r"\+log ([^ ]+/spectre.out)",commands[-1])
                    assert m and re.fullmatch(re.escape(REMOTE_BASE)+r"/[0-9a-f]{8}/spectre.out",m[1])
                    remote = m[1];folder = remote.rsplit("/",1)[0]
                    try:
                        if ssh is None:
                            ssh = SSHClient.from_env(profile="t28_io")
                        q = shlex.quote(remote)
                        r = ssh.spectre_runner.run_command(f"if test -f {q}; then cat {q}; fi",timeout=25)
                        assert r.returncode == 0
                        log = r.stdout
                        ps = ssh.spectre_runner.run_command("ps -u chenzc_intern25 -ww -o pid,ppid,etime,pcpu,comm,args",timeout=20)
                        for line in ps.stdout.splitlines():
                            p = line.split(None,5)
                            if len(p)==6 and p[0].isdigit() and folder+f"/b_hf_w{w}.scs" in p[5]:
                                processes.append(dict(pid=int(p[0]),parent=int(p[1]),elapsed=p[2],cpu=p[3],command=p[4]))
                    except Exception as exc:
                        error = type(exc).__name__+": "+str(exc)[:180]
                    if local.exists() and "spectre completes with" in local.read_text(errors="replace"):
                        log = local.read_text(errors="replace");error = None
                    state = read(case/"flow.json")
            records = re.findall(r"R3MEAS,(\d+),(\d+),(\d+),(\d+),(\d+),([^\s,]+)",log)
            parameters = {}
            if "Important parameter values:" in log and "Output and IC/nodeset" in log:
                block = log.split("Important parameter values:",1)[1].split("Output and IC/nodeset",1)[0]
                parameters = dict(re.findall(r"(?m)^\s+([\w()]+) = ([^\n]+)",block))
            original = read(ROOT/"verification/integration/b_sine_period_results.json")["reported_solver_parameters"]
            differences = {k:dict(baseline=v,current=parameters.get(k)) for k,v in original.items()
                           if parameters and parameters.get(k)!=v}
            reports[str(w)] = dict(local=state,query_error=error,completed_frames=None if error else len(records),
                total_frames=24,last_records=records[-2:],remote_log=remote,native_processes=processes,
                native_success="spectre completes with 0 errors" in log,
                completed_all_8compare_stable=bool(records) and all(x[2]=="8" and x[4]=="1" for x in records),
                has_CMI="CMI-2754" in log,has_LTE_relaxation="SPECTRE-16780" in log,
                solver_parameter_differences=differences,
                warning_lines=[x.strip() for x in log.splitlines() if "WARNING (" in x])
            if remote:
                dump(case/"remote.json",dict(log=remote,processes=processes,query_error=error))
    finally:
        if ssh:
            ssh.close()
    report = dict(local=read(OUT/"flow.json"),checked_utc=datetime.now(timezone.utc).isoformat(),cases=reports)
    dump(OUT/"progress.json",report)
    print(__import__("json").dumps(report,indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("action",choices=["preflight","prepare","check","native","parse","run","status"])
    p.add_argument("--width",type=int,choices=[1,2,3])
    args = p.parse_args()
    globals()[args.action](args.width) if args.action in ("native","parse") else globals()[args.action]()
