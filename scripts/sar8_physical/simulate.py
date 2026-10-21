"""Run immutable OA-derived cases with explicit testbench-only stimuli."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import pickle
import re

import numpy as np
from virtuoso_bridge.spectre.runner import SpectreSimulator, spectre_mode_args

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/sar8_physical"
os.environ.setdefault("VB_DISABLE_CONTROL_MASTER", "1")


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def replace_instance(text, name, line):
    result, count = re.subn(rf"(?m)^{name} .*?(?=\n\S|\Z)", line, text, flags=re.S)
    assert count == 1, (name, count)
    return result


def pulse_wave(events, start=0, end=200):
    points = [(0., start)]
    for time, value in events:
        previous = points[-1][1]
        points.extend([(time, previous), (time + .1, value)])
    points.append((float(end), points[-1][1]))
    assert all(b[0] >= a[0] for a, b in zip(points, points[1:]))
    return " ".join(f"{time:.9g}n {value:.12g}" for time, value in points)


def bind_testbench_parameters(text):
    lines=re.findall(r"(?m)^parameters ([^\r\n]+)",text)
    assert len(lines)==1 and set(lines[0].split())=={"SUP","VDIFF"},lines
    text,count=re.subn(r"(?m)^parameters [^\r\n]+", "parameters SUP=0.9 VDIFF=0.123", text)
    assert count==1
    return text


def prepare(case, tag):
    cell = {"passive": "tb_sar8p_passives", "unit": "tb_sar8p_unit",
            "smoke": "tb_sar_adc8_join_r4", "transitions": "tb_sar_adc8_join_r4",
            "nominal16": "tb_sar_adc8_join_r4", "nominal4": "tb_sar_adc8_join_r4"}[case]
    source_path = OUT / "exports" / cell / tag / "input.scs"
    text = source_path.read_text(encoding="utf-8")
    assert "ahdl_include" not in text, "Candidate still has behavioral dependencies"
    text = re.sub(r"(?m)^\w+ info [^\n]*\n", "", text)
    text = text.replace("reltol=1e-4", "reltol=1e-6").replace("vabstol=1e-6", "vabstol=1e-8")
    text = text.replace("iabstol=1e-12", "iabstol=1e-13").replace("save=allpub", "save=selected")
    text = text.replace('psfversion="1.4.0"', 'psfversion="1.4.0" method=gear2only')
    if case == "passive":
        return text + "\nac_unit ac start=1M stop=1M\nsave IN VDC:p\n", dict(source=str(source_path), source_sha256=digest(source_path))
    if case not in ("passive","unit"):
        text=bind_testbench_parameters(text)
    if case == "unit":
        words = [127, 128, 255, 0, 170, 85, 85, 65]
        events = [(44.08 + 5*i + 100*f, word) for f in range(2) for i, word in enumerate(words)]
        commits=[]
        for f in range(2):
            previous=128
            for i,target in enumerate(words):
                commits.append((43.7+5*i+100*f,previous&target));previous=target
        for bit in range(8):
            wave = pulse_wave([(t, .9*((word>>bit)&1)) for t, word in events], start=.9*(bit==7))
            text = replace_instance(text, f"VCODE{bit}", f"VCODE{bit} (CODE{bit} 0) vsource type=pwl wave=[{wave}]")
            wave=pulse_wave([(t,.9*((word>>bit)&1)) for t,word in commits],start=0)
            text=replace_instance(text,f"VDREG{bit}",f"VDREG{bit} (D{bit} 0) vsource type=pwl wave=[{wave}]")
        updates = [(time, value) for f in range(2) for i in range(8)
                   for time, value in ((44 + 5*i + 100*f, .9), (44.208 + 5*i + 100*f, 0))]
        text = replace_instance(text, "VUPDATE", "VUPDATE (PHI_U 0) vsource type=pwl wave=[" + pulse_wave(updates) + "]")
        saves = ["SAMPLE", "PHI_U", "XREF.CAP_CLK"] + [f"CODE{i}" for i in range(8)] + [f"XREF.Q{i}" for i in range(8)]
        saves += [f"G{s}{q}{i}" for s in "PN" for q in "PN" for i in range(8)]
        saves += [f"XCDAC.B{s}{i}" for s in "PN" for i in range(8)]
        saves += [f"XREF.H{i}" for i in range(8)] + [f"XREF.L{i}" for i in range(8)]
        saves += [f"D{i}" for i in range(8)]+["XREF.REQ_Q","XREF.LATE_CLK","XREF.ACK","XREF.FIRST2"]
        stop = "200n"
    else:
        # Explicit startup contract: reset/acquire before the first falling
        # edge. Keep every falling threshold at41.05+100*f ns, as before.
        text=replace_instance(text,"VSAMPLE", "VSAMPLE (SAMPLE 0) vsource type=pulse val0=SUP val1=0 delay=41n rise=100p fall=100p width=59.9n period=100n")
        frames=2 if case=="smoke" else 16 if case=="nominal16" else 4
        if case in ("transitions","nominal16","nominal4"):
            spec=json.loads((ROOT/"verification/sar8_physical/stimuli.json").read_text())
            diff=spec["signed_transitions_differential_v"]
            if case=="nominal16":diff=spec["history12_differential_v"]+diff
            if case=="nominal4":diff=[.123,-.8,.8,-.8]
            assert len(diff)==frames
            for side, sign in (("P", 1), ("N", -1)):
                wave = pulse_wave([(100*f+.8, .45+sign*diff[f]/2) for f in range(1, frames)],
                                  start=.45+sign*diff[0]/2, end=100*frames)
                text = replace_instance(text, "VVIN" + side, f"VVIN{side} (VIN{side}_SRC 0) vsource type=pwl wave=[{wave}]")
        saves = ["SAMPLE", "XDUT.SAMPLE_INT", "XDUT.TOPP", "XDUT.TOPN", "VINP_SRC", "VINN_SRC", "VINP", "VINN",
                 "XDUT.CMP_CLK", "XDUT.COMP_P", "XDUT.COMP_N", "XDUT.XCTRL.PHI_W", "XDUT.PHI_U", "XDUT.XREF.CAP_CLK"]
        saves += [f"D{i}" for i in range(8)] + [f"XDUT.XCTRL.T{i}" for i in range(8)]
        saves += [f"XDUT.CODE{i}" for i in range(8)] + [f"XDUT.XREF.Q{i}" for i in range(8)]
        saves += [f"XDUT.G{s}{q}{i}" for s in "PN" for q in "PN" for i in range(8)]
        saves += [f"XDUT.XCDAC.B{s}{i}" for s in "PN" for i in range(8)]
        saves += ["VDD!", "VREFP", "VREFN", "XDUT.XCOMP.X", "XDUT.XCOMP.Y", "XDUT.XCOMP.TAIL"]
        saves += [f"XDUT.XBOOT{s}.{node}" for s in "PN" for node in ("G","BBOT","BTOP","GRESET","CTRL","CLKSB")]
        saves += ["VVDD:p","VREFHIGH:p","VREFLOW:p","VSAMPLE:p","VVINP:p","VVINN:p"]
        saves += ["XDUT.XREF.REQ_Q","XDUT.XREF.LATE_CLK","XDUT.XREF.ACK","XDUT.XREF.FIRST2"]
        stop = str(100*frames)+"n"
    text += f"\ntran_physical tran stop={stop} maxstep=10p errpreset=conservative lteratio=10\nsave {' '.join(saves)}\n"
    return text, dict(case=case, source=str(source_path), source_sha256=digest(source_path), stop=stop,
                      modifications="testbench parameters/stimulus, solver options, analyses/saves only",
                      requested_signals=saves, internal_behavioral_logic=False,
                      startup_contract="SAMPLE initially high; frame0 explicitly observed startup, full cycle before declared valid frames" if case!="unit" else "Original low-start unit clock")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("case", choices=["passive", "unit", "smoke", "transitions", "nominal16", "nominal4"])
    p.add_argument("--tag", default="initial")
    p.add_argument("--name", required=True)
    args = p.parse_args()
    folder = OUT / "runs" / args.name
    assert not folder.exists(), "Use a fresh run identity"
    folder.mkdir(parents=True)
    text, context = prepare(args.case, args.tag)
    deck = folder / f"{args.name}.scs"
    deck.write_text(text, encoding="utf-8")
    context["deck_sha256"] = digest(deck)
    (folder/"context.json").write_text(json.dumps(context, indent=2) + "\n")
    sim = SpectreSimulator.from_env(profile="t28_io", work_dir=folder/"spectre", timeout=3600,
          spectre_args=[*spectre_mode_args("aps"), "+mt=4", "+lqtimeout", "60"])
    with (folder/"runner.log").open("w", encoding="utf-8") as stream, contextlib.redirect_stdout(stream):
        result = sim.run_simulation(deck, {})
    report = dict(ok=result.ok, errors=result.errors, warnings=result.warnings,
                  metadata=result.metadata, deck_sha256=digest(deck))
    (folder/"result.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    if result.ok:
        wave = {k.lower(): np.asarray(v) for k,v in result.data.items() if isinstance(v, (list, np.ndarray))}
        if args.case != "passive":
            wanted = {s.lower() for s in context["requested_signals"]} | {"time"}
            assert wanted <= set(wave), wanted - set(wave)
            wave = {k: v for k,v in wave.items() if k in wanted}
            assert np.all(np.diff(wave["time"]) > 0)
            assert all(len(v)==len(wave["time"]) and np.isfinite(v).all() for v in wave.values())
        path = folder/"waveform.pickle"
        with path.open("wb") as stream:
            pickle.dump(wave, stream, protocol=5)
        (folder/"waveform_receipt.json").write_text(json.dumps(dict(sha256=digest(path),
             signals=list(wave),points=max((len(v) for v in wave.values()),default=0)),indent=2)+"\n")
    print("RESULT",args.name,result.ok,result.errors,flush=True)
    raise SystemExit(0 if result.ok else 1)


if __name__ == "__main__":
    main()
