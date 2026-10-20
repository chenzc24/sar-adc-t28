"""Immutable R3 anomaly replay; parent DUT/stimulus/solver precision preserved."""
from __future__ import annotations

import argparse
import contextlib
import json
import math
from pathlib import Path
import pickle
import re
import sys

import r3_performance as parent

ROOT = parent.ROOT
OUT = ROOT / "output/r3_anomaly_replay"
NAME = "static065_first12"
PARENT = "static_065_128"


def dump(name, value):
    p = OUT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, default=str, allow_nan=False) + "\n", encoding="utf-8")


def signals():
    names = ["SAMPLE", "VINP_SRC", "VINN_SRC", "VINP", "VINN", "TOPP", "TOPN",
             "CMP_CLK", "COMP_P", "COMP_N", "VREFP", "VREFN", "VDD!"]
    names += [f"D{b}" for b in range(8)]
    names += [f"XDUT.XCOMP.{n}" for n in ("X", "Y", "TAIL")]
    names += ["XDUT.GCOMMIT"]
    names += [f"XDUT.XCTRL.{n}" for n in ("PHI_W", "PHI_U", "ACTIVE", "DATA")]
    names += [f"XDUT.XCTRL.T{b}" for b in range(8)]
    names += [f"XDUT.XCTRL.CODE{b}" for b in (7, 6, 0)]
    names += [f"XDUT.XCTRL.XTIM.{n}" for n in
              ("PR", "NR", "RAW", "RAW_D", "DEC", "WRITE_REQ", "WRITE_D", "CLOCK_Q")]
    names += [f"XDUT.XCTRL.XBIT6.{n}" for n in ("NEXT_D", "XSTORE.M", "XSTORE.MQ", "XSTORE.S")]
    names += [f"XDUT.XCDAC.B{s}{b}" for s in "PN" for b in (7, 6)]
    names += [f"XDUT.G{s}{q}{b}" for s in "PN" for q in "PN" for b in (7, 6)]
    names += [f"XDUT.XBOOT{s}.G" for s in "PN"]
    return names


def identity(text):
    """Strip owned output controls and the passive early-finish observer."""
    text = re.sub(r'(?m)^(?:XSTOP \(SAMPLE\) r3_replay_stop|ahdl_include "r3_replay_stop.va").*\n?', "", text)
    return re.sub(r"(?m)^(?:tran_perf tran |save ).*\n?", "", text)


def prepare(original_stop=False):
    parent.baseline()
    ctx = parent.r3.r1.read_json(parent.OUT / f"cases/{PARENT}.json")
    source = parent.OUT / f"decks/{PARENT}.scs"
    assert parent.r3.r1.sha(source) == ctx["deck_sha256"]
    original = source.read_text(encoding="utf-8")
    # A retained comparison attempts explicit parent defaults, but APS still
    # clamps its reported step. The original-stop observer run is authoritative.
    analysis = ("tran_perf tran stop=1200n maxstep=10p errpreset=conservative "
                "step=51.6n istep=51.6n transres=51.6f "
                "strobeperiod=1n strobeoutput=all outputstart=800n")
    if original_stop:
        analysis = ("tran_perf tran stop=51600n maxstep=10p errpreset=conservative "
                    "strobeperiod=1n strobeoutput=all outputstart=800n")
    text, n = re.subn(r"(?m)^tran_perf tran .*", analysis, original)
    assert n == 1
    if original_stop:
        text += 'XSTOP (SAMPLE) r3_replay_stop stop_s=1200n\nahdl_include "r3_replay_stop.va"\n'
    assert identity(text) == identity(original)
    text, n = re.subn(r"(?m)^save .*", "save " + " ".join(signals()), text)
    assert n == 1 and identity(text) == identity(original)
    assert parent.r3.r1.blocks(text) == parent.r3.r1.blocks(original)
    assert len(signals()) == len(set(signals()))
    dest = OUT / f"decks/{NAME}.scs"
    assert not dest.exists(), "Immutable replay exists"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    includes = [str(p) for p in parent.r3.VAS.values()] + ctx["testbench_includes"]
    if original_stop:
        includes += [str(ROOT / "models/veriloga/r3_anomaly_replay/r3_replay_stop.va")]
    for f in ctx["testbench_includes"]:
        p = Path(f)
        assert parent.r3.r1.sha(p) == p.parent.name
    dump("context.json", dict(name=NAME, parent_name=PARENT, parent_context=ctx,
         parent_deck_sha256=ctx["deck_sha256"], deck_sha256=parent.r3.r1.sha(dest),
         native_DUT_and_wrapper_identical=True, frames=12, stop_ns=1200,
         original_stop_preserved=original_stop, declared_stop_ns=51600 if original_stop else 1200,
         outputstart_ns=800, saved_signals=signals(), include_files=includes,
         include_sha256={p: parent.r3.r1.sha(Path(p)) for p in includes},
         parent_stop_dependent_default_reference=dict(step_s=51.6e-9, istep_s=51.6e-9, transres_s=51.6e-15),
         effective_values_must_be_checked_in_native_log=True,
         solver=dict(mode="aps", threads=4, maxstep_ps=10, errpreset="conservative",
                     options_reltol=1e-5, expected_effective_reltol=1e-6,
                     vabstol=1e-8, iabstol=1e-13),
         corner="tt", supply_v=0.9, temperature_c=27,
         mismatch=False, transient_noise=False, remote_OA_changed=False))
    print("PREPARED", NAME, "signals", len(signals()), flush=True)


def run():
    from virtuoso_bridge.spectre.runner import SpectreSimulator, spectre_mode_args
    parent.baseline()
    ctx = parent.r3.r1.read_json(OUT / "context.json")
    deck = OUT / f"decks/{NAME}.scs"
    assert parent.r3.r1.sha(deck) == ctx["deck_sha256"]
    assert not (OUT / "result.json").exists()
    for p, h in ctx["include_sha256"].items():
        assert parent.r3.r1.sha(Path(p)) == h
    progress = sys.stdout
    try:
        with (OUT / "runner.log").open("a", encoding="utf-8") as log, \
                contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            sim = SpectreSimulator.from_env(profile="t28_io", work_dir=OUT / "spectre", timeout=7200,
                    spectre_args=[*spectre_mode_args("aps"), "+lqtimeout", "60"])
            with sim.parallel_pool(max_workers=1) as pool:
                r = pool.submit(deck, dict(include_files=ctx["include_files"], spectre_args=["+mt=4"])).result()
            dump("result.json", dict(ok=r.ok, errors=r.errors, warnings=r.warnings,
                 metadata=r.metadata, deck_sha256=ctx["deck_sha256"]))
            if r.ok:
                wave = {str(k).strip('"').replace("\\", "").lower(): v for k, v in r.data.items()
                        if isinstance(v, list) and str(k).lower() != "units"}
                assert "time" in wave
                for k, v in wave.items():
                    assert len(v) == len(wave["time"]) and all(math.isfinite(x) for x in v), k
                assert all(s.lower() in wave for s in signals())
                assert wave["time"][0] >= 800e-9 - 1e-14
                assert wave["time"][-1] >= 1200e-9 - 1e-14
                with (OUT / "waveform.pickle").open("wb") as stream:
                    pickle.dump(wave, stream, protocol=5)
                dump("waveform_receipt.json", dict(points=len(wave["time"]), signals=len(wave)-1,
                     start_s=wave["time"][0], stop_s=wave["time"][-1],
                     sha256=parent.r3.r1.sha(OUT / "waveform.pickle")))
            print("SPECTRE_REPLAY", r.ok, r.errors[:3], file=progress, flush=True)
            assert r.ok, r.errors
    except Exception as exc:
        dump("failure.json", dict(error=repr(exc)))
        raise


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["prepare", "run"])
    ap.add_argument("--original-stop", action="store_true")
    args = ap.parse_args()
    if args.original_stop:
        OUT = OUT / "original_stop"
        NAME = "static065_originalstop_first12"
    prepare(args.original_stop) if args.action == "prepare" else run()
