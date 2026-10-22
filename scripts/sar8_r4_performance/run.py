"""Prepare and execute isolated characterization decks, preserving all DUT parameters."""
import argparse
import contextlib
import json
import re
import time
import numpy as np
from common import ROOT, OUT, MODELS, SOURCE, base_deck, blocks, dump, read, sha, verify_source


def replace(text, name, line):
    text, n = re.subn(rf"(?m)^{name} .*?(?=\n\S|\Z)", line, text, flags=re.S)
    assert n == 1, (name, n)
    return text


def prepare(name, kind, mode="ax", first=1, last=255, samples=1024, coherent_bin=461, warmup=4, span=.5, refine=7, honor_options=False, threads=4, precision_options=False):
    folder = OUT / "cases" / name
    assert not folder.exists(), "Immutable case already exists: " + name
    text = base_deck()
    includes = []
    if kind == "pilot":
        frames = 4
    elif kind == "static":
        # One center per transition plus final code 255 center; two bounds + refinement.
        frames = warmup + (last-first+1)*(3+refine) + 1
        for side in "PN":
            text = replace(text, "VVIN"+side, "")
        text += f"\nXSTIM (VINP_SRC VINN_SRC D0 D1 D2 D3 D4 D5 D6 D7) r4_transition_stim first_k={first} last_k={last} warmup={warmup} refine={refine} half_span_lsb={span}\n"
        includes.append(MODELS / "r4_transition_stim.va")
    elif kind == "sine":
        frames = warmup + samples
        amplitude = .9 * 10**(-1/20)
        for side, phase in (("P", 0), ("N", 180)):
            text = replace(text, "VVIN"+side, f"VVIN{side} (VIN{side}_SRC 0) vsource type=sine dc=.45 sinedc=.45 ampl={amplitude/2:.16g} freq={10e6*coherent_bin/samples:.16g} sinephase={phase}")
    else:
        raise ValueError(kind)
    text += "\nXMEASURE (XDUT.SAMPLE_INT XDUT.CMP_CLK XDUT.XCTRL.PHI_W XDUT.PHI_U XDUT.XREF.CAP_CLK VDD! VINP_SRC VINN_SRC XDUT.TOPP XDUT.TOPN D0 D1 D2 D3 D4 D5 D6 D7) r4_perf_monitor\n"
    includes.append(MODELS / "r4_perf_monitor.va")
    saves = [f"D{i}" for i in range(8)] + ["SAMPLE", "XDUT.SAMPLE_INT", "XDUT.CMP_CLK", "XDUT.TOPP", "XDUT.TOPN", "VINP_SRC", "VINN_SRC"]
    text += f"\ntran_perf tran stop={frames*100}n maxstep=10p errpreset=conservative lteratio=10 strobeperiod=1n strobeoutput=strobeonly\nsave {' '.join(saves)}\n"
    for path in includes:
        text += f'ahdl_include "{path.name}"\n'
    assert blocks(text) == blocks((SOURCE / "dut.scs").read_text())
    folder.mkdir(parents=True)
    snapshots = []
    for path in includes:
        dest = folder / path.name
        dest.write_bytes(path.read_bytes())
        snapshots.append(dict(path=str(dest), sha256=sha(dest)))
    deck = folder / (name + ".scs")
    deck.write_text(text, encoding="utf-8")
    context = dict(name=name, kind=kind, mode=mode, honor_options=honor_options, precision_options=precision_options, threads=threads, frames=frames, stop_ns=frames*100,
        first=first,last=last,samples=samples,coherent_bin=coherent_bin,warmup=warmup,
        half_span_lsb=span,refine=refine,frequency_hz=10e6*coherent_bin/samples,
        source=verify_source(),DUT_unchanged=True,deck_sha256=sha(deck),includes=snapshots,
        corner="TT",VDD=.9,temperature_C=27,transient_noise=False,mismatch=False,
        maxstep_ps=10,requested_reltol=1e-6,strobe_period_ns=1,output_read_ns=98)
    dump(folder / "context.json", context)
    print("PREPARED", name, frames, mode, flush=True)


def run(name):
    from virtuoso_bridge.spectre.runner import SpectreSimulator, spectre_mode_args
    folder = OUT / "cases" / name
    ctx = read(folder / "context.json")
    assert not (folder / "result.json").exists()
    deck = folder / (name+".scs")
    assert sha(deck) == ctx["deck_sha256"]
    for item in ctx["includes"]:
        assert sha(item["path"]) == item["sha256"]
    args = [x for x in spectre_mode_args(ctx["mode"]) if x != "+mt"] + [f"+mt={ctx['threads']}", "+lqtimeout", "60"]
    if ctx.get("honor_options"):
        args.append("-preset_override")
    elif ctx.get("precision_options"):
        args.append("-preset_override=reltol,vabstol,iabstol")
    sim = SpectreSimulator.from_env(profile="t28_io", work_dir=folder / "spectre", timeout=172800, spectre_args=args)
    start = time.monotonic()
    with (folder / "runner.log").open("w", encoding="utf-8") as stream, contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
        result = sim.run_simulation(deck, dict(include_files=[i["path"] for i in ctx["includes"]]))
    dump(folder / "result.json", dict(ok=result.ok,errors=result.errors,warnings=result.warnings,
        metadata=result.metadata,elapsed_wall_s=time.monotonic()-start,deck_sha256=sha(deck),spectre_args=args))
    if result.ok:
        wave = {str(k).strip('"').replace("\\", "").lower():np.asarray(v) for k,v in result.data.items() if isinstance(v,(list,np.ndarray)) and str(k).lower()!="units"}
        assert "time" in wave and np.all(np.diff(wave["time"])>0)
        assert all(len(v)==len(wave["time"]) and np.isfinite(v).all() for v in wave.values())
        np.savez_compressed(folder / "wave.npz", **wave)
        dump(folder / "wave_receipt.json",dict(sha256=sha(folder / "wave.npz"),signals=list(wave),points=len(wave["time"])))
    print("RESULT",name,result.ok,result.errors,flush=True)
    return result.ok


if __name__ == "__main__":
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest="action",required=True)
    a=sub.add_parser("prepare");a.add_argument("name");a.add_argument("--kind",choices=["pilot","static","sine"],required=True)
    a.add_argument("--mode",default="ax");a.add_argument("--first",type=int,default=1);a.add_argument("--last",type=int,default=255)
    a.add_argument("--samples",type=int,default=1024);a.add_argument("--coherent-bin",type=int,default=461)
    a.add_argument("--warmup",type=int,default=4);a.add_argument("--span",type=float,default=.5);a.add_argument("--refine",type=int,default=7)
    a.add_argument("--honor-options",action="store_true")
    a.add_argument("--threads",type=int,default=4)
    a.add_argument("--precision-options",action="store_true")
    a=sub.add_parser("run");a.add_argument("name")
    a=p.parse_args();kw=vars(a);action=kw.pop("action")
    if action=="prepare":prepare(**kw)
    else:raise SystemExit(0 if run(a.name) else 1)
