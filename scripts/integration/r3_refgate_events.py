"""Isolated A/B repair of R3 reference-gate sampling events; no native DUT edits."""
from __future__ import annotations

import argparse
from concurrent.futures import as_completed
import contextlib
import gc
import json
import math
from pathlib import Path
import pickle
import re
import sys

import r3_anomaly_replay as replay

ROOT = replay.ROOT
OUT = ROOT / "output/r3_refgate_events"
MODEL = ROOT / "models/veriloga/r3_refgate_events"
OLD = ROOT / "output/r3_anomaly_replay/original_stop"
OLD_NAME = "static065_originalstop_first12"
SHA = replay.parent.r3.r1.sha
CODES = [64, 64, 64, 64, 64, 65, 64, 65, 1, 65, 65, 65]


def dump(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str, allow_nan=False) + "\n", encoding="utf-8")


def history():
    """Exact binary fractions, reconstructed with the original search and codes."""
    lsb = 1.8 / 256
    lo, hi = -.9 + 65*lsb - .25*lsb, -.9 + 65*lsb + .25*lsb
    trial = lo
    values = []
    for f, code in enumerate(CODES):
        values.append(trial)
        if f < 4:
            continue
        if f == 4:
            trial = hi
        elif f == 5:
            trial = (lo+hi)/2
        else:
            if code >= 65:
                hi = trial
            else:
                lo = trial
            trial = (lo+hi)/2
    original = json.loads((OLD/"analysis.json").read_text())
    for row in original["searches"]:
        assert abs(values[row["frame"]] - row["vdiff_v"]) < 6e-13
    return values


def instrument_original(source):
    """Add only passive strobe/state copies at existing events; no new events."""
    source = source.replace("    real restore_at,turnon_at,off_at;",
        "    real restore_at,turnon_at,off_at;\n"
        "    integer debug_before_sampling,debug_before_restored;\n"
        "    real debug_before_restore_at;")
    source = source.replace("            sample_now=", "            debug_before_sampling=sampling;\n"
        "            debug_before_restored=restored; debug_before_restore_at=restore_at;\n"
        "            sample_now=", 1)
    needle = "        end\n        V(GP,VSS)"
    extra = ('            $strobe("R3ASTATE,%m,%.15g,%.17g,%d,%d,%d,%d,%d,%d,%d,%d,%.15g,%.15g",\n'
             '                $abstime,V(SAMPLE,VSS)-0.5*V(VDD,VSS),sample_now,\n'
             '                debug_before_sampling,sampling,debug_before_restored,restored,\n'
             '                overridden,on_h,on_l,debug_before_restore_at,restore_at);\n')
    assert source.count(needle) == 1
    return source.replace(needle, extra+needle)


def frozen_stim(source):
    # Keep the original circuit interface, source equations, events and 100ps
    # transition. Only testbench search branching uses its historical decisions;
    # R3SEARCH continues to print the ACTUAL ADC code, never the replay code.
    source = source.replace("integer k,phase,frame,code,status,finished;",
                            "integer k,phase,frame,code,status,finished;\n    integer history_code;")
    needle = "            if (frame>=warmup && !finished) begin"
    cases = "            case (frame)\n" + "".join(
        f"                {f}: history_code={code};\n" for f, code in enumerate(CODES))
    cases += "                default: history_code=65;\n            endcase\n"
    assert source.count(needle) == 1
    source = source.replace(needle, cases+needle)
    for before, after in (("if(code!=k-1)", "if(history_code!=k-1)"),
                          ("if(code!=k)", "if(history_code!=k)"),
                          ("if (code>=k)", "if (history_code>=k)")):
        assert source.count(before) == 1
        source = source.replace(before, after)
    return source


def signals():
    result = ["SAMPLE", "VINP_SRC", "VINN_SRC", "VINP", "VINN", "TOPP", "TOPN",
              "CMP_CLK", "COMP_P", "COMP_N", "VREFP", "VREFN", "VDD!"]
    result += [f"D{b}" for b in range(8)]
    result += [f"XDUT.XCOMP.{n}" for n in ("X", "Y", "TAIL")]
    result += ["XDUT.GCOMMIT", "XDUT.XCTRL.PHI_W", "XDUT.XCTRL.PHI_U"]
    result += [f"XDUT.XCTRL.T{b}" for b in range(8)]
    result += [f"XDUT.XCDAC.B{s}{b}" for s in "PN" for b in range(8)]
    result += [f"XDUT.G{s}{q}{b}" for s in "PN" for q in "PN" for b in range(8)]
    result += [f"XDUT.XBOOT{s}.G" for s in "PN"]
    assert len(result) == len(set(result))
    return result


def prepare():
    replay.parent.baseline()
    ctx = json.loads((OLD/"context.json").read_text())
    base = OLD/f"decks/{OLD_NAME}.scs"
    assert SHA(base) == ctx["deck_sha256"]
    for p, h in ctx["include_sha256"].items():
        assert SHA(Path(p)) == h
    original_gate = next(Path(p) for p in ctx["include_files"] if Path(p).name == "sar8j_aligned_refgate.va")
    a = MODEL/"a/sar8j_aligned_refgate.va"
    assert not a.exists()
    a.parent.mkdir(parents=True, exist_ok=True)
    a.write_text(instrument_original(original_gate.read_text()), encoding="utf-8")
    original_stim = next(Path(p) for p in ctx["include_files"] if Path(p).name == "r3_transition_stim.va")
    stim = MODEL/"r3_transition_stim.va"
    assert not stim.exists()
    stim.write_text(frozen_stim(original_stim.read_text()), encoding="utf-8")
    hist = history()
    dump(OUT/"history.json", dict(codes_from_original_R3=CODES, differential_input_v=hist,
         original_search_log_precision_absolute_tolerance_v=6e-13,
         source_update_ns=[100.8+100*f for f in range(11)], transition_ps=100,
         description="Frozen original testbench bisection history; actual DUT decisions remain native"))
    for variant in ("a", "b"):
        gate = MODEL/f"{variant}/sar8j_aligned_refgate.va"
        includes = [str(gate if Path(p).name == gate.name else
                        stim if Path(p).name == stim.name else Path(p)) for p in ctx["include_files"]]
        text = base.read_text()
        text, n = re.subn(r"(?m)^save .*", "save "+" ".join(signals()), text)
        assert n == 1
        assert replay.identity(text) == replay.identity(base.read_text())
        assert replay.parent.r3.r1.blocks(text) == replay.parent.r3.r1.blocks(base.read_text())
        deck = OUT/f"{variant}/decks/first12_{variant}.scs"
        assert not deck.exists()
        deck.parent.mkdir(parents=True, exist_ok=True)
        deck.write_text(text, encoding="utf-8")
        dump(OUT/f"{variant}/context.json", dict(variant=variant, original_context=ctx,
            deck=str(deck), deck_sha256=SHA(deck), native_subcircuits_and_wrapper_unchanged=True,
            same_12_frame_input_history=hist, include_files=includes,
            include_sha256={p:SHA(Path(p)) for p in includes}, saved_signals=signals(),
            outputstart_ns=800, declared_stop_ns=51600, actual_stop_ns=1200,
            remote_OA_changed=False, shared_original_sources_changed=False,
            changed_DUT_surface="passive gate logging only" if variant=="a" else "direction-specific SAMPLE state events"))
    print("PREPARED_AB", len(signals()), "signals", flush=True)


def prepare_candidate(variant):
    ctx = json.loads((OUT/"b/context.json").read_text())
    gate = MODEL/f"{variant}/sar8j_aligned_refgate.va"
    includes = [str(gate if Path(p).name==gate.name else Path(p)) for p in ctx["include_files"]]
    deck=OUT/f"{variant}/decks/first12_{variant}.scs"
    assert not deck.exists()
    deck.parent.mkdir(parents=True,exist_ok=True)
    deck.write_text(Path(ctx["deck"]).read_text(),encoding="utf-8")
    ctx.update(variant=variant,deck=str(deck),deck_sha256=SHA(deck),include_files=includes,
               include_sha256={p:SHA(Path(p)) for p in includes},
               changed_DUT_surface="event-owned SAMPLE/COMMIT/restore/turn-on callbacks; intended timings unchanged")
    dump(OUT/f"{variant}/context.json",ctx)
    print("PREPARED_CANDIDATE",variant,flush=True)


def prepare_unit(variants=("a","b")):
    # Same external pulse shape as R3, both initial-high polarities, request
    # switches to the opposite rail during conversion and remains held until
    # the next sampling restore. Several clock offsets probe equality at cross.
    for variant in variants:
        text = ('simulator lang=spectre\nglobal 0\nVV (VDD 0) vsource dc=.9\n'
            'VH (EH 0) vsource type=pulse val0=0 val1=.9 period=100n delay=42n rise=50p fall=50p width=58n\n'
            'VL (EL 0) vsource type=pulse val0=.9 val1=0 period=100n delay=42n rise=50p fall=50p width=58n\n'
            'VC (COMMIT 0) vsource type=pulse val0=0 val1=.9 period=100n delay=42.25n rise=1p fall=1p width=50n\n')
        saves = []
        for index, delay in enumerate((1, 1.000013, 1.000071, 1.000197)):
            text += (f'VS{index} (S{index} 0) vsource type=pulse val0=0 val1=.9 period=100n delay={delay:.9g}n '
                     'rise=100p fall=100p width=39.9n\n')
            for initial in (0, 1):
                name = f"{index}_{initial}"
                text += (f'X{name} (S{index} EH EL VDD 0 GP{name} GN{name} COMMIT) sar8j_aligned_refgate '
                         f'initial_high={initial} restore_guard_s=100p dead_time_s=100p edge_s=50p\n')
                saves += [f"GP{name}", f"GN{name}"]
            saves.append(f"S{index}")
        text += ('simulatorOptions options reltol=1e-5 vabstol=1e-8 iabstol=1e-13 temp=27 tnom=27\n'
            'tran_unit tran stop=1200n maxstep=10p errpreset=conservative\n'
            'saveOptions options save=selected\nsave '+" ".join(saves)+'\n'
            'ahdl_include "sar8j_aligned_refgate.va"\n')
        path = OUT/f"unit_{variant}/decks/unit_{variant}.scs"
        assert not path.exists()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        gate = MODEL/f"{variant}/sar8j_aligned_refgate.va"
        dump(OUT/f"unit_{variant}/context.json", dict(variant=f"unit_{variant}",deck=str(path),
            deck_sha256=SHA(path),include_files=[str(gate)],include_sha256={str(gate):SHA(gate)},
            saved_signals=saves))
    print("PREPARED_GATE_UNIT_AB", flush=True)


def run(names):
    from virtuoso_bridge.spectre.runner import SpectreSimulator, spectre_mode_args
    progress = sys.stdout
    # Separate result files/streams and futures, no shared OA or campaign state.
    with (OUT/"runner.log").open("a", encoding="utf-8") as log, \
            contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        sim = SpectreSimulator.from_env(profile="t28_io", work_dir=OUT/"spectre",timeout=10800,
                spectre_args=[*spectre_mode_args("aps"), "+lqtimeout", "60"])
        with sim.parallel_pool(max_workers=2) as pool:
            futures = {}
            for name in names:
                folder = OUT/name
                assert not (folder/"result.json").exists()
                ctx = json.loads((folder/"context.json").read_text())
                assert SHA(Path(ctx["deck"])) == ctx["deck_sha256"]
                for p,h in ctx["include_sha256"].items():
                    assert SHA(Path(p)) == h
                f = pool.submit(Path(ctx["deck"]), dict(include_files=ctx["include_files"],spectre_args=["+mt=4"]))
                futures[f] = (name,ctx)
            for f in as_completed(futures):
                name,ctx = futures[f]
                folder = OUT/name
                r = f.result()
                dump(folder/"result.json", dict(ok=r.ok,errors=r.errors,warnings=r.warnings,
                    metadata=r.metadata,deck_sha256=ctx["deck_sha256"]))
                if r.ok:
                    wave = {str(k).strip('"').replace("\\","").lower():v for k,v in r.data.items()
                            if isinstance(v,list) and str(k).lower()!="units"}
                    assert "time" in wave
                    assert all(len(v)==len(wave["time"]) and all(math.isfinite(x) for x in v) for v in wave.values())
                    assert all(s.lower() in wave for s in ctx["saved_signals"])
                    with (folder/"waveform.pickle").open("wb") as stream:
                        pickle.dump(wave,stream,protocol=5)
                    dump(folder/"waveform_receipt.json",dict(points=len(wave["time"]),signals=len(wave)-1,
                        start_s=wave["time"][0],stop_s=wave["time"][-1],sha256=SHA(folder/"waveform.pickle")))
                    del wave
                print("REFGATE_SPECTRE",name,r.ok,r.errors[:3],file=progress,flush=True)
                r.data.clear(); del r; gc.collect()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("action",choices=("prepare","prepare-unit","prepare-b2","prepare-candidate","run"))
    ap.add_argument("names",nargs="*")
    args = ap.parse_args()
    if args.action=="prepare": prepare()
    elif args.action=="prepare-unit": prepare_unit()
    elif args.action=="prepare-b2":
        prepare_candidate("b2"); prepare_unit(("b2",))
    elif args.action=="prepare-candidate":
        assert len(args.names)==1 and re.fullmatch(r"b[3-9]",args.names[0])
        prepare_candidate(args.names[0]); prepare_unit((args.names[0],))
    else: run(args.names or ["a","b"])
