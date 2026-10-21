"""Bounded B/1um history and directed native checks; no OA mutations."""
from __future__ import annotations
import argparse
from array import array
from concurrent.futures import ThreadPoolExecutor, as_completed
import dataclasses
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

import yaml
import b_hf_main_w as hf
import b_sine_period as sine
import r3_b_oa as adoption
from freeze_r0 import object_digest, schematic_surface

ROOT = sine.ROOT
OUT = ROOT / "output/b_short_acceptance"
CFG = ROOT / "config/b_short_acceptance.yaml"
BASE = ROOT / "output/b_sine_period"
sha, read, dump, stage = hf.sha, hf.read, hf.dump, hf.stage
os.environ.setdefault("VB_DISABLE_CONTROL_MASTER", "1")
Q = 1.8 / 256


def stream_psf(stream):
    """Real transient PSF ASCII, preserving carry-forward values at each time."""
    traces, groups = [], {}
    section, group, sweep = None, None, None
    for line in stream:
        line = line.strip()
        if line in ("HEADER", "TYPE", "SWEEP", "TRACE", "VALUE"):
            section = line
            if line == "VALUE":
                break
            continue
        if section == "SWEEP" and sweep is None:
            m = re.match(r'"([^"]+)"', line)
            if m:
                sweep = m[1]
        elif section == "TRACE":
            m = re.match(r'"([^"]+)"\s+(.*)', line)
            if not m:
                continue
            if m[2].startswith("GROUP"):
                group = m[1]
            elif m[2].startswith('"'):
                traces.append(m[1])
                if group is not None:
                    groups[group] = m[1]
                group = None
    assert section == "VALUE" and sweep == "time" and traces
    assert len(traces) == len(set(traces))
    positions = {n: i for i, n in enumerate(traces)}
    values = [math.nan] * len(traces)
    buffers = [array("d") for _ in traces]
    times = array("d")
    current_time, ended = None, False
    for line in stream:
        line = line.strip()
        if not line:
            continue
        if line == "END":
            ended = True
            break
        assert line.startswith('"'), line[:100]
        end = line.index('"', 1)
        key, value = line[1:end], float(line[end + 1:].strip())
        if key == sweep:
            if current_time is not None:
                times.append(current_time)
                for buffer, old_value in zip(buffers, values):
                    buffer.append(old_value)
            current_time = value
        else:
            values[positions[groups.get(key, key)]] = value
    assert ended and current_time is not None
    times.append(current_time)
    for buffer, value in zip(buffers, values):
        buffer.append(value)
    wave = {sweep: times}
    wave.update(dict(zip(traces, buffers)))
    assert all(b > a for a, b in zip(times, times[1:]))
    assert all(len(v) == len(times) and all(map(math.isfinite, v)) for v in wave.values())
    return wave


def parser_check():
    import io
    from virtuoso_bridge.spectre.parsers import _parse_psf_ascii_content
    synthetic = 'SWEEP\n"time" "sweep"\nTRACE\n" 1" GROUP 1\n"VOUT" "V"\n"ISRC:p" "I"\nVALUE\n"time" 0\n" 1" .9\n"ISRC:p" -.001\n"time" 1e-9\n" 1" .8\n"time" 2e-9\n"ISRC:p" -.002\nEND\n'
    for content in (synthetic,):
        streaming = stream_psf(io.StringIO(content))
        bundled = _parse_psf_ascii_content(content)
        assert streaming.keys() == bundled.keys()
        for k in streaming:
            assert list(streaming[k]) == bundled[k]
    # Bounded real PSF prefix, including all original signal types and events.
    raw = next((BASE / "spectre").rglob("*.tran.tran"))
    prefix, count = [], 0
    with raw.open(encoding="utf-8") as stream:
        for line in stream:
            if line.startswith('"time" ') and "VALUE\n" in prefix:
                count += 1
                if count == 2049:
                    break
            prefix.append(line)
    content = "".join(prefix) + "END\n"
    streaming, bundled = stream_psf(io.StringIO(content)), _parse_psf_ascii_content(content)
    assert len(streaming["time"]) == 2048
    for k in streaming:
        assert list(streaming[k]) == bundled[k]
    print("STREAMING_PSF_DELTA_CURRENT_AND_REAL_2048_POINTS_EQUIVALENCE_PASS", flush=True)


def preflight():
    from virtuoso_bridge import VirtuosoClient
    assert not (OUT / "preflight.json").exists()
    c = VirtuosoClient.from_env(profile="t28_io", timeout=30, log_to_ciw=False)
    info = c.library.get(adoption.LIB)
    assert info.path == "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28"
    assert info.technology_library == "tsmcN28"
    windows = c.list_windows()
    assert not any("dialog" in w["name"].lower() for w in windows)
    for name in (adoption.TOP, adoption.TB):
        data = c.schematic.read(adoption.LIB, name, include_positions=True, param_filters=None, timeout=30)
        assert adoption.normalized(data) == adoption.normalized(read(BASE / f"oa/{name}.json")), name
        dump(OUT / f"oa/{name}.json", data)
    deps = read(ROOT / "output/r3_b_oa/dependencies.json")
    for name, expected in deps.items():
        data = c.schematic.read(adoption.LIB, name, include_positions=False, param_filters=None, timeout=30)
        assert object_digest(schematic_surface(data)) == expected, name
    # Supported file download reads current VA text; never edits OA files.
    expected = read(BASE / "context.json")
    gate = next(Path(p) for p in expected["include_files"] if Path(p).stem == adoption.NEW)
    dest = OUT / "inputs" / gate.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    result = c.download_file(f"{info.path}/{adoption.NEW}/veriloga/veriloga.va", dest)
    assert result.ok and sha(dest) == sha(gate)
    dump(OUT / "preflight.json", dict(library=dataclasses.asdict(info), windows=windows,
         dependencies_unchanged=len(deps), current_B_VA_sha256=sha(dest), OA_writes=[], profile="t28_io"))
    print("READ_ONLY_B_1X_TOP_TB_36_DEPENDENCIES_PASS", flush=True)


def native_devices(text):
    """Relevant analog primitive MOS, preserving exact exported connectivity."""
    blocks = {m[1]: re.sub(r"\\\n\s*", " ", m[2]) for m in
              re.finditer(r"(?ms)^subckt (\w+) (.*?)^ends \1", text)}
    root_ports = set(blocks[adoption.TOP].splitlines()[0].split())
    qualify_root = lambda n: n if n in root_ports or n in ("0", "VDD!") else "XDUT." + n
    devices = []
    for block_name, body in blocks.items():
        if block_name == "sar_bootstrap_canvas_flat_8b":
            paths = ["XDUT.XBOOTP", "XDUT.XBOOTN"]
            category = "bootstrap_io"
        elif block_name == "sar_strongarm_t28":
            paths = ["XDUT.XCOMP"]
            category = "comparator_core"
        elif re.fullmatch(r"sar8j_r1_sw_b[0-7]", block_name):
            bit = block_name[-1]
            paths = [f"XDUT.XCDAC.XSP{bit}", f"XDUT.XCDAC.XSN{bit}"]
            category = "reference_core"
        else:
            continue
        ports = body.splitlines()[0].split()
        # Maps below are derived from top/array instance declarations, not PDK internals.
        for path in paths:
            if category == "bootstrap_io":
                inst = re.search(r"\b" + path.split(".")[-1] + r" \(([^)]+)\)", blocks[adoption.TOP])
                assert inst
                mapping = dict(zip(ports, map(qualify_root, inst[1].split())))
            elif category == "comparator_core":
                inst = re.search(r"XCOMP \(([^)]+)\)", blocks[adoption.TOP].replace("\\\n", " "))
                assert inst
                mapping = dict(zip(ports, inst[1].split()))
            else:
                side = "P" if ".XSP" in path else "N"
                mapping = dict(zip(ports, [f"XDUT.XCDAC.B{side}{bit}", f"XDUT.G{side}N{bit}",
                    f"XDUT.G{side}P{bit}", "VDD!", "VREFN", "VREFP", "0"]))
            mapping.update({"0": "0", "VDD!": "VDD!"})
            for m in re.finditer(r"(?m)^\s+(\w+) \(([^)]+)\) ((?:nch|pch)(?:_18)?_mac)\b", body):
                terms = m[2].split()
                assert len(terms) == 4
                nodes = [mapping.get(n, path + "." + n) for n in terms]
                devices.append(dict(path=path + "." + m[1], model=m[3], nodes=nodes, category=category))
    assert len([d for d in devices if d["category"] == "reference_core"]) == 32
    assert len([d for d in devices if d["category"] == "comparator_core"]) == 11
    return devices


def directed_values(name):
    if name == "directed_a16":
        return [.5 * Q] * 4 + [-.8, .8, -.8, .8, -.9 + .5 * Q, .9 - .5 * Q,
            -.9 + .5 * Q, .9 - .5 * Q, .5 * Q, -.5 * Q, .5 * Q, -.5 * Q]
    return [-.9 + 64.5 * Q] * 4 + [
        -.9 + k * Q + sign * .25 * Q for k in (1, 32, 64, 128, 192, 255) for sign in (-1, 1)]


def pwl(values, positive):
    leg = lambda value: .45 + (1 if positive else -1) * value / 2
    points = [(0, leg(values[0]))]
    for f, value in enumerate(values[1:]):
        points += [(100.8 + 100 * f, leg(values[f])), (100.9 + 100 * f, leg(value))]
    return " ".join(f"{ns:.12g}n {v:.17g}" for ns, v in points)


def save_list(devices, historical):
    names = sine.signals() + [f"XDUT.XCDAC.B{s}{b}" for s in "PN" for b in range(8)]
    names += [f"XDUT.G{s}{q}{b}" for s in "PN" for q in "PN" for b in range(8)]
    names += [n for d in devices for n in d["nodes"] if n != "0"]
    names += ["VREFP_SRC", "VREFN_SRC", "VVDD:p", "VREFHIGH:p", "VREFLOW:p", "VSAMPLE:p"]
    names += (["XSTIM:VP", "XSTIM:VN"] if historical else ["VVINP:p", "VVINN:p"])
    # Element terminal currents use Spectre's existing device currents; no added meter.
    names += [f"XDUT.XG{s}{b}:{p}" for s in "PN" for b in range(8) for p in ("GP", "GN")]
    return list(dict.fromkeys(names))


def prepare():
    assert (OUT / "preflight.json").exists() and not (OUT / "context.json").exists()
    cfg = yaml.safe_load(CFG.read_text())
    base = read(BASE / "context.json")
    assert sha(base["deck"]) == base["deck_sha256"]
    original = Path(base["deck"]).read_text(encoding="utf-8")
    assert hf.low.params(hf.low.main_statement(original))["w"] == "1u"
    assert hf.low.params(hf.low.main_statement(original))["l"] == "150.0n"
    devices = native_devices(original)
    # Validate hierarchy-to-net maps against actual exported reference instances.
    blocks = adoption.r3.r1.blocks(original)
    array = next(v for k, v in blocks.items() if "XSP0" in v)
    for s in "PN":
        for b in range(8):
            assert f"XS{s}{b} (B{s}{b} G{s}N{b} G{s}P{b}" in array
    include_paths = []
    for p, h in base["include_sha256"].items():
        assert sha(p) == h
        if Path(p).name == "r3_sine_probe.va":
            continue
        target = OUT / "inputs" / Path(p).name
        if target.exists():
            assert sha(target) == h
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(Path(p).read_bytes())
        include_paths.append(str(target))
    history = read(ROOT / cfg["history_receipt"])
    stimulus = ROOT / cfg["history_source"]
    old_context = read(ROOT / "output/r3_refgate_events/b3/context.json")
    assert any(Path(p) == stimulus and sha(p) == h for p, h in old_context["include_sha256"].items())
    target = OUT / "inputs" / stimulus.name
    target.write_bytes(stimulus.read_bytes())
    include_paths.append(str(target))
    cases = {}
    for name, case_cfg in cfg["cases"].items():
        folder = OUT / name
        historical = name == "history12"
        text = re.sub(r"(?m)^XPROBE .*\n", "", original)
        text = re.sub(r'(?m)^ahdl_include "r3_sine_probe.va"\n', "", text)
        if historical:
            text = re.sub(r"(?m)^VVIN[PN] .*\n", "", text)
            text += '\nXSTIM (VINP_SRC VINN_SRC D0 D1 D2 D3 D4 D5 D6 D7) r3_transition_stim first_k=65 last_k=128 warmup=4 refine=6 half_span_lsb=0.25\n'
            text += 'ahdl_include "r3_transition_stim.va"\n'
            values = history["differential_input_v"]
        else:
            values = directed_values(name)
            for side in "PN":
                statement = f"VVIN{side} (VIN{side}_SRC 0) vsource type=pwl wave=[ {pwl(values, side == 'P')} ]"
                text, n = re.subn(rf"(?m)^VVIN{side} .*", statement, text)
                assert n == 1
        text = text.replace("stop_s=2400n", f"stop_s={case_cfg['actual_stop_ns']}n")
        saves = save_list(devices, historical)
        text, n = re.subn(r"(?m)^save .*", "save " + " ".join(saves), text)
        assert n == 1 and adoption.r3.r1.blocks(text) == blocks
        deck = folder / f"{name}.scs"
        deck.parent.mkdir(parents=True, exist_ok=True)
        deck.write_text(text, encoding="utf-8")
        cases[name] = dict(**case_cfg, deck=str(deck), deck_sha256=sha(deck), input_values_v=values,
            saved_signals=saves, includes=[p for p in include_paths if historical or Path(p).name != stimulus.name])
        stage(folder, "prepared", frames=case_cfg["frames"])
    dump(OUT / "context.json", dict(config=cfg, config_sha256=sha(CFG), cases=cases,
        analog_devices=devices, baseline_context_sha256=sha(BASE / "context.json"),
        baseline_deck_sha256=base["deck_sha256"], include_sha256={p: sha(p) for p in include_paths},
        full_original_history=history, same_native_blocks=True, no_OA_writes=True,
        source_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, cwd=ROOT).strip()))
    stage(OUT, "prepared", total_frames=44)
    check()


def check():
    ctx = read(OUT / "context.json")
    assert sha(CFG) == ctx["config_sha256"] and sha(BASE / "context.json") == ctx["baseline_context_sha256"]
    base = read(BASE / "context.json")
    assert sha(base["deck"]) == ctx["baseline_deck_sha256"]
    baseline = Path(base["deck"]).read_text(encoding="utf-8")
    for p, h in ctx["include_sha256"].items():
        assert sha(p) == h
    for name, case in ctx["cases"].items():
        text = Path(case["deck"]).read_text(encoding="utf-8")
        assert sha(case["deck"]) == case["deck_sha256"]
        assert adoption.r3.r1.blocks(text) == adoption.r3.r1.blocks(baseline)
        assert len(case["input_values_v"]) == case["frames"]
        assert all(key in text for key in ("stop=51600n", "maxstep=10p", "errpreset=conservative", "reltol=1e-5", "vabstol=1e-8", "iabstol=1e-13"))
        assert "strobeonly" not in text
        assert text.split("VSAMPLE", 1)[1].split("ROBS_TOPN", 1)[0] == baseline.split("VSAMPLE", 1)[1].split("ROBS_TOPN", 1)[0]
    assert ctx["cases"]["history12"]["input_values_v"] == ctx["full_original_history"]["differential_input_v"]
    print("B_SHORT_SOURCE_HISTORY_NATIVE_DIMENSIONS_TIMING_PRECISION_PASS", flush=True)


def native(name):
    from virtuoso_bridge.spectre.runner import SpectreSimulator, _run_spectre_remote, spectre_mode_args
    check()
    case = OUT / name
    cfg = read(OUT / "context.json")["cases"][name]
    assert read(case / "flow.json")["stage"] == "prepared"
    stage(case, "running_native", frames=cfg["frames"])
    sim = SpectreSimulator.from_env(profile="t28_io", timeout=14400)
    assert sim._remote_host == "thu-wei" and sim._remote_user == "chenzc_intern25"
    (case / "spectre").mkdir(exist_ok=True)
    runner = hf.BoundedTransfers(sim._get_ssh_runner(), case)
    r = _run_spectre_remote(netlist=Path(cfg["deck"]), params=dict(include_files=cfg["includes"]),
        runner=runner, remote_work_dir=hf.REMOTE_BASE, base_output_dir=case / "spectre", spectre_cmd=hf.BIN,
        spectre_args=[*spectre_mode_args("aps"), "+lqtimeout", "60", "+mt=4"], output_format="psfascii",
        timeout=14400, keep_remote_files=False)
    dump(case / "run_artifacts.json", r._asdict())
    assert r.success, r.error
    stage(case, "downloaded_native", frames=cfg["frames"])


def parse(name):
    from virtuoso_bridge.spectre.runner import _SpectreRunResult, _build_simulation_result
    case = OUT / name
    assert read(case / "flow.json")["stage"] == "downloaded_native"
    record = read(case / "run_artifacts.json")
    record["output_dir"] = Path(record["output_dir"]) if record["output_dir"] else None
    stage(case, "parsing_native")
    start = time.monotonic()
    r = _build_simulation_result(_SpectreRunResult(**record), None, extra_metadata=record["metadata"])
    assert r.ok, r.errors
    raw = next(Path(record["output_dir"]).rglob("*.tran.tran"))
    with raw.open(encoding="utf-8") as stream:
        data = stream_psf(stream)
    wave = {str(k).strip('"').replace("\\", "").lower(): v for k, v in data.items()}
    assert wave["time"][0] == 0
    assert all(len(v) == len(wave["time"]) and all(math.isfinite(x) for x in v) for v in wave.values())
    with (case / "waveform.pickle").open("wb") as stream:
        pickle.dump(wave, stream, protocol=5)
    dump(case / "waveform_receipt.json", dict(sha256=sha(case / "waveform.pickle"), points=len(wave["time"]),
        signal_keys=sorted(wave), start_s=wave["time"][0], stop_s=wave["time"][-1]))
    dump(case / "result.json", dict(ok=r.ok, errors=r.errors, warnings=r.warnings,
        metadata=r.metadata, parse_seconds=time.monotonic() - start, streaming_waveform_validation=True))
    stage(case, "parsed")


def run():
    assert read(OUT / "flow.json")["stage"] == "prepared"
    os.close(os.open(OUT / "launch.lock", os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    check()
    dump(OUT / "launch.json", dict(local_pid=os.getpid(),
         commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
         runner_LF_sha256=hashlib.sha256(Path(__file__).read_text(encoding="utf-8").encode()).hexdigest(),
         context_sha256=sha(OUT / "context.json")))
    stage(OUT, "running_batch", total_frames=44)
    def worker(name):
        with (OUT / name / "runner.log").open("w", encoding="utf-8") as log:
            return subprocess.run([sys.executable, __file__, "native", "--case", name], cwd=ROOT,
                stdout=log, stderr=subprocess.STDOUT, env=dict(os.environ, PYTHONUNBUFFERED="1"),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).returncode
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {pool.submit(worker, n): n for n in read(OUT / "context.json")["cases"]}
            for future in as_completed(futures):
                name = futures[future]
                assert future.result() == 0, f"{name} failed; no rerun"
                subprocess.run([sys.executable, __file__, "parse", "--case", name], cwd=ROOT, check=True)
        stage(OUT, "awaiting_analysis")
    except Exception as exc:
        stage(OUT, "failed", error=repr(exc))
        raise


def status():
    from virtuoso_bridge.transport.tunnel import SSHClient
    report = dict(local=read(OUT / "flow.json"), cases={})
    ssh = None
    try:
        for name, case_cfg in read(OUT / "context.json")["cases"].items():
            case = OUT / name
            state = read(case / "flow.json")
            path = case / "spectre/spectre.out"
            log = path.read_text(errors="replace") if path.exists() else ""
            error, remote, processes = None, None, []
            if state["stage"] == "running_native" and "spectre completes with" not in log:
                commands = re.findall(r"(?m)^\[Command\] (.*)$", (case / "runner.log").read_text(errors="replace"))
                if commands:
                    m = re.search(r"\+log ([^ ]+/spectre.out)", commands[-1])
                    assert m and re.fullmatch(re.escape(hf.REMOTE_BASE) + r"/[0-9a-f]{8}/spectre.out", m[1])
                    remote = m[1]
                    folder = remote.rsplit("/", 1)[0]
                    try:
                        if ssh is None:
                            ssh = SSHClient.from_env(profile="t28_io")
                        r = ssh.spectre_runner.run_command(f"if test -f {shlex.quote(remote)}; then cat {shlex.quote(remote)}; fi", timeout=25)
                        assert r.returncode == 0
                        log = r.stdout
                        ps = ssh.spectre_runner.run_command("ps -u chenzc_intern25 -ww -o pid,ppid,etime,pcpu,comm,args", timeout=20)
                        for line in ps.stdout.splitlines():
                            p = line.split(None, 5)
                            if len(p) == 6 and p[0].isdigit() and folder + f"/{name}.scs" in p[5]:
                                processes.append(dict(pid=int(p[0]), parent=int(p[1]), elapsed=p[2], cpu=p[3], command=p[4]))
                    except Exception as exc:
                        error = repr(exc)[:200]
                    dump(case / "remote.json", dict(log=remote, processes=processes, query_error=error))
            records = re.findall(r"R3MEAS,(\d+),(\d+),(\d+),(\d+),(\d+),([^\s,]+)", log)
            report["cases"][name] = dict(stage=state["stage"], completed_frames=None if error else len(records),
                total_frames=case_cfg["frames"], last_records=records[-2:], query_error=error,
                remote_log=remote, native_processes=processes,
                native_success="spectre completes with 0 errors" in log,
                has_CMI="CMI-2754" in log, has_LTE="SPECTRE-16780" in log,
                save_warnings=[s.strip() for s in log.splitlines() if "SPECTRE-8" in s or "SPECTRE-16" in s],
                numerical_or_code_failure=any(x[2] != "8" or x[4] != "1" for x in records))
    finally:
        if ssh:
            ssh.close()
    dump(OUT / "progress.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["preflight", "prepare", "check", "parser_check", "run", "native", "parse", "status"])
    ap.add_argument("--case", choices=["history12", "directed_a16", "directed_b16"])
    args = ap.parse_args()
    globals()[args.action](args.case) if args.action in ("native", "parse") else globals()[args.action]()
