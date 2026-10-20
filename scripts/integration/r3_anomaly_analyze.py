"""Read-only waveform chronology for the R3 original-history anomaly replay."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import pickle
import re
import shutil

import numpy as np

from r3_anomaly_replay import ROOT, OUT, NAME, PARENT, identity, signals, parent


def dump(name, value):
    p = OUT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, default=str, allow_nan=False)+"\n",encoding="utf-8")


def monitor(log):
    return [dict(frame=int(m[1]), code=int(m[2]), compares=int(m[3]), early=int(m[4]),
                 valid=bool(int(m[5])), rail_error_v=float(m[6]))
            for m in re.finditer(r"R3MEAS,(\d+),(\d+),(\d+),(\d+),(\d+),([\d.eE+-]+)", log)]


def searches(log):
    return [dict(frame=int(m[1]), k=int(m[2]), phase=int(m[3]), vdiff_v=float(m[4]), code=int(m[5]))
            for m in re.finditer(r"R3SEARCH,(\d+),(\d+),(\d+),([\d.eE+-]+),(\d+)", log)]


def outliers(rows):
    return [r for r in rows if r["code"] not in (r["k"] - 1, r["k"])]


def reported_parameters(log):
    block = log.split("Important parameter values:", 1)[1].split("Output and IC/nodeset", 1)[0]
    return dict(re.findall(r"(?m)^\s+([\w()]+) = ([^\n]+)", block))


def edges(t, v, level=0.45, rising=True):
    m = (v[:-1] < level) & (v[1:] >= level) if rising else (v[:-1] > level) & (v[1:] <= level)
    i = np.flatnonzero(m)
    return t[i] + (level-v[i]) * (t[i+1]-t[i]) / (v[i+1]-v[i])


def analyze():
    parent.baseline()
    ctx = parent.r3.r1.read_json(OUT / "context.json")
    result = parent.r3.r1.read_json(OUT / "result.json")
    assert result["ok"], result["errors"]
    assert result["deck_sha256"] == ctx["deck_sha256"] == parent.r3.r1.sha(OUT/f"decks/{NAME}.scs")
    source = parent.OUT / f"decks/{PARENT}.scs"
    assert parent.r3.r1.sha(source) == ctx["parent_deck_sha256"]
    assert identity(source.read_text()) == identity((OUT/f"decks/{NAME}.scs").read_text())
    for p, h in ctx["include_sha256"].items():
        assert parent.r3.r1.sha(Path(p)) == h
    receipt = parent.r3.r1.read_json(OUT / "waveform_receipt.json")
    assert receipt["sha256"] == parent.r3.r1.sha(OUT / "waveform.pickle")
    # This is a hash-checked pickle produced by our own local run, never an external upload.
    with (OUT / "waveform.pickle").open("rb") as stream:
        w = {k: np.asarray(v) for k, v in pickle.load(stream).items()}
    assert all(s.lower() in w for s in signals())
    assert np.all(np.diff(w["time"]) > 0) and all(np.isfinite(v).all() for v in w.values())
    t = w["time"] * 1e9
    assert t[0] >= 800-1e-5 and t[-1] >= 1200-1e-5
    logpath = Path(result["metadata"]["output_dir"]).parent / "spectre.out"
    log = logpath.read_text(encoding="utf-8", errors="replace")
    parent_log_path = ROOT / "output/r3_anomaly_replay/parent_snapshot/spectre_2318.out"
    original_log = parent_log_path.read_text(errors="replace")
    rows = monitor(log)
    old = monitor(original_log)[:12]
    assert len(rows) == len(old) == 12 and [r["frame"] for r in rows] == list(range(12))
    same_codes = all(all(r[k] == p[k] for k in ("frame", "code", "compares", "early", "valid"))
                     for r, p in zip(rows, old))
    sr = searches(log)
    sp = [r for r in searches(original_log) if r["frame"] < 12]
    same_search = len(sr) == len(sp) and all(
        all(a[k] == b[k] for k in ("frame", "k", "phase", "code")) and abs(a["vdiff_v"]-b["vdiff_v"]) < 1e-11
        for a, b in zip(sr, sp))
    same_inputs = len(sr) == len(sp) and all(
        a["frame"] == b["frame"] and abs(a["vdiff_v"]-b["vdiff_v"]) < 1e-11 for a, b in zip(sr, sp))
    at = lambda k, ns: float(np.interp(ns, t, w[k.lower()]))
    word = lambda ns: sum(int(at(f"d{b}", ns) > .45) << b for b in range(8))
    token = lambda ns: sum(int(at(f"xdut.xctrl.t{b}", ns) > .45) << b for b in range(8))
    for f in range(8, 12):
        assert word(98+100*f) == rows[f]["code"]
        s = next(a for a in sr if a["frame"] == f)
        assert abs(at("vinp_src", 98+100*f)-at("vinn_src", 98+100*f)-s["vdiff_v"]) < 1e-10
    cr = edges(t, w["cmp_clk"])
    wr = edges(t, w["xdut.xctrl.phi_w"])
    ur = edges(t, w["xdut.xctrl.phi_u"])
    frames = []
    for f in range(8, 12):
        hold = 41.05+100*f
        subset = lambda x: x[(x >= hold) & (x < 100*(f+1))]
        cs, ws, us = map(subset, (cr, wr, ur))
        vdiff = next(a["vdiff_v"] for a in sr if a["frame"] == f)
        events = []
        for i, c in enumerate(cs):
            write = float(ws[i]) if i < len(ws) else None
            before = float(c-.02)
            trial = word(before) | token(before)
            actual = at("topp", before)-at("topn", before)
            ideal = vdiff+.9-trial*parent.LSB
            row = dict(index=i, bit_if_ordered=7-i, compare_ns=float(c),
                       write_ns=write, update_ns=float(us[i]) if i < len(us) else None,
                       token_before_compare=token(before), trial_from_D_or_T=trial,
                       ideal_residual_mv=ideal*1e3, actual_residual_mv=actual*1e3,
                       residual_error_mv=(actual-ideal)*1e3)
            if write is not None:
                row.update(token_before_write=token(write-.005), DATA_at_write_v=at("xdut.xctrl.data", write),
                    COMP_P_before_write_v=at("comp_p", write-.005),
                    COMP_N_before_write_v=at("comp_n", write-.005),
                    D6_before_write_v=at("d6", write-.02), D6_after_write_v=at("d6", write+.05),
                    NEXT_D6_at_write_v=at("xdut.xctrl.xbit6.next_d", write),
                    MQ6_at_write_v=at("xdut.xctrl.xbit6.xstore.mq", write))
            events.append(row)
        d6_edges = [dict(time_ns=float(x), rising=rising) for rising in (True, False)
                    for x in subset(edges(t, w["d6"], rising=rising))]
        expected = {"gpp7": .9, "gnp7": 0., "gpp6": 0., "gnp6": .9}
        measured = {n:at("xdut."+n, hold-.1) for n in expected}
        gp_changes = []
        for n in expected:
            for rising in (True, False):
                for instant in edges(t, w["xdut."+n], rising=rising):
                    if hold-.5 < instant < hold+1:
                        gp_changes.append(dict(node=n, time_ns=float(instant), rising=rising))
        offset = (at("topp", hold+.6)-at("topn", hold+.6))-vdiff
        frames.append(dict(frame=f, vdiff_v=vdiff, hold_ns=hold, read_ns=98+100*f,
             output_code=word(98+100*f), compare_count=len(cs), write_count=len(ws), update_count=len(us),
             comparisons=events, D6_edges=sorted(d6_edges, key=lambda r:r["time_ns"]),
             midpoint_check=dict(time_ns=hold-.1, expected_PMOS_gate_v=expected, measured_PMOS_gate_v=measured,
                  observed_MSB_midpoint_correct=all(abs(measured[n]-expected[n])<.09 for n in expected)),
             near_hold_gate_changes=sorted(gp_changes,key=lambda r:r["time_ns"]),
             acquisition_error_before_off_mv=((at("topp",hold-.1)-at("topn",hold-.1))-vdiff)*1e3,
             held_offset_0p6ns_mv=offset*1e3, held_offset_0p6ns_lsb=offset/parent.LSB,
             previous_frame_code=rows[f-1]["code"],
             predicted_offset_if_previous_reference_word_restores_late_mv=(rows[f-1]["code"]-128)*parent.LSB*1e3))
    vgd = w["topp"]-w["xdut.xcomp.y"]
    vgs = w["topp"]-w["xdut.xcomp.tail"]
    vds = w["xdut.xcomp.y"]-w["xdut.xcomp.tail"]
    stress = []
    for f in range(8, 12):
        ix = np.flatnonzero((t >= 100*f) & (t < 100*(f+1)))
        for name, voltage in (("VGD", vgd), ("VGS", vgs), ("VDS", vds)):
            j = ix[np.argmax(abs(voltage[ix]))]
            stress.append(dict(frame=f, terminal=name, signed_v=float(voltage[j]), abs_v=float(abs(voltage[j])),
                 time_ns=float(t[j]), TOPP_v=float(w["topp"][j]), Y_v=float(w["xdut.xcomp.y"][j]),
                 TAIL_v=float(w["xdut.xcomp.tail"][j]), SAMPLE_v=float(w["sample"][j]),
                 CMP_CLK_v=float(w["cmp_clk"][j])))
    ix = np.flatnonzero((t >= 840) & (t < 900) & (abs(vgd) > .99))
    exposure = dict(observed=bool(len(ix)), first_ns=float(t[ix[0]]) if len(ix) else None,
                    last_ns=float(t[ix[-1]]) if len(ix) else None)
    original_parameters = reported_parameters(original_log)
    replay_parameters = reported_parameters(log)
    parameter_differences = {k:dict(parent=v, replay=replay_parameters.get(k))
                            for k,v in original_parameters.items()
                            if k != "outputstart" and v != replay_parameters.get(k)}
    data = dict(status="analyzed", reproduced=bool(same_codes and same_inputs and rows[8]["code"] == 1),
         target_frame8_reproduced=bool(same_inputs and rows[8]["code"] == 1),
         input_voltage_history_match=bool(same_inputs),
         exact_code_history_match=bool(same_codes), exact_search_history_match=bool(same_search),
         reported_solver_parameters=dict(parent=original_parameters, replay=replay_parameters,
              differences_excluding_outputstart=parameter_differences,
              all_non_output_parameters_match=not parameter_differences),
         context=ctx, result=result, monitor=rows, searches=sr, search_outliers=outliers(sr),
         parent_search_outliers=outliers(sp), frames=frames, MNINP_stress=stress,
         frame8_VGD_screen_exposure=exposure,
         warnings=[s.strip() for s in log.splitlines() if re.search(r"WARNING \((?:CMI|SPECTRE)|\bLTE\b|suppressed", s)],
         provenance=dict(log_sha256=parent.r3.r1.sha(logpath), waveform_sha256=receipt["sha256"],
              parent_snapshot_log_sha256=parent.r3.r1.sha(parent_log_path)),
         qualifications=dict(remote_OA_changed=False, circuit_fix_attempted=False, full_ADC_performance=False,
                              search_outlier_is_not_normal_adjacent_code_ambiguity=True,
                              only_bits7_and6_physical_bottoms_and_gates_saved=True,
                              all_bit_reference_word_inferred_not_directly_measured=True,
                              VA_internal_sampling_state_not_saved=True))
    dump("analysis.json", data)
    print(json.dumps({k:data[k] for k in ("reproduced", "target_frame8_reproduced", "input_voltage_history_match",
                      "exact_code_history_match", "search_outliers", "frame8_VGD_screen_exposure")}, indent=2))
    print(json.dumps(dict(frame_summary=[{k:f[k] for k in ("frame", "output_code", "compare_count", "write_count", "update_count")} for f in frames],
        stress=[{k:r[k] for k in ("frame", "terminal", "signed_v", "time_ns")} for r in stress]), indent=2))
    return data, t, w


def probe(data, t, w, frame):
    names = ["sample", "cmp_clk", "vinp_src", "vinn_src", "vinp", "vinn", "topp", "topn",
             "xdut.xcomp.y", "xdut.xcomp.tail", "xdut.xbootp.g", "xdut.xbootn.g", "xdut.gcommit",
             "xdut.gpp7", "xdut.gnp7", "xdut.gpp6", "xdut.gnp6",
             "xdut.xcdac.bp7", "xdut.xcdac.bn7", "xdut.xcdac.bp6", "xdut.xcdac.bn6"]
    rows = []
    for rel in (.95, 1.05, 1.10, 1.15, 1.175, 1.25, 1.40, 2, 10, 40.95,
                41.05, 41.10, 41.15, 41.175, 41.20, 41.25, 41.30, 41.40, 41.50, 42, 43, 43.68):
        ns = 100*frame+rel
        rows.append(dict(time_ns=ns, **{n:float(np.interp(ns, t, w[n])) for n in names}))
    dump(f"probe_frame{frame}.json", rows)
    print("PROBE", frame)
    for r in rows:
        print(" ".join(f"{n}={r[n]:.7g}" for n in ("time_ns", "vinp", "vinn", "topp", "topn", "xdut.xcomp.y",
             "xdut.xcdac.bp7", "xdut.xcdac.bn7", "xdut.xcdac.bp6", "xdut.xcdac.bn6", "xdut.gcommit")))
    vicinity = (t >= frame*100+.9) & (t <= frame*100+1.2)
    jj = np.flatnonzero(vicinity & (abs(w["sample"]-.45)<1e-6))
    candidates = [dict(time_ns=float(t[j]), SAMPLE_v=float(w["sample"][j]),
                       threshold_v=float(w["vdd!"][j]/2),
                       strict_sample_now=bool(w["sample"][j] > w["vdd!"][j]/2)) for j in jj]
    dump(f"rise_threshold_samples_frame{frame}.json",candidates)
    print("RISE_THRESHOLD_SAMPLES",json.dumps(candidates))


def figures(data, t, w, focus=8):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    folder = OUT / "figures" / f"frame{focus}"
    folder.mkdir(parents=True, exist_ok=True)
    frame = next(f for f in data["frames"] if f["frame"] == focus)
    origin = 100*focus
    end = origin+99
    x = (t >= origin+40.9) & (t <= min(end, origin+100))
    tt = t[x]
    code = sum((w[f"d{b}"][x] > .45).astype(int)*(1 << b) for b in range(8))
    fig, axs = plt.subplots(5, 1, figsize=(11, 10), sharex=True)
    axs[0].plot(tt, w["sample"][x], label="SAMPLE")
    axs[0].plot(tt, w["cmp_clk"][x], label="CMP_CLK")
    axs[0].set_ylabel("Clock (V)")
    axs[1].plot(tt, (w["topp"][x]-w["topn"][x])*1e3, label="TOPP - TOPN")
    axs[1].scatter([r["compare_ns"]-.02 for r in frame["comparisons"]],
                   [r["ideal_residual_mv"] for r in frame["comparisons"]],
                   marker="x",s=25,color="#25886d",label="Expected for actual trial word",zorder=4)
    axs[1].axhline(0, color=".4", ls="--", label="Decision threshold")
    axs[1].set_ylabel("Residual (mV)")
    axs[2].plot(tt, w["comp_p"][x], label="COMP_P")
    axs[2].plot(tt, w["comp_n"][x], label="COMP_N")
    axs[2].set_ylabel("Comparator (V)")
    axs[3].plot(tt, w["xdut.xctrl.phi_w"][x], label="PHI_W")
    axs[3].plot(tt, w["xdut.xctrl.phi_u"][x], label="PHI_U")
    axs[3].set_ylabel("Control (V)")
    axs[4].step(tt, code, where="post", label="Stored output code")
    complete = max([r["update_ns"] or r["compare_ns"] for r in frame["comparisons"]],default=origin+75)+.05
    axs[4].fill_between([complete,end],64,65,alpha=.25,color="#2b9275",label="Expected final code 64 / 65")
    axs[4].scatter([frame["read_ns"]],[frame["output_code"]],s=18,color="#c44840",zorder=4,label="98 ns read")
    axs[4].set_ylabel("Code")
    for ax in axs:
        ax.axvline(frame["hold_ns"], color=".5", ls=":", lw=.8)
        ax.grid(alpha=.2)
        ax.legend(loc="upper right", fontsize=8, ncol=2)
    axs[-1].set_xlabel("Time (ns)")
    axs[0].set_title(f"R3 replay: frame {focus}, read at {frame['read_ns']} ns = {frame['output_code']}", fontsize=11)
    fig.tight_layout(); fig.savefig(folder / "frame8_timing.png", dpi=160); plt.close(fig)
    vg = w["topp"]-w["xdut.xcomp.y"]
    xx = (t >= origin+40.98) & (t <= origin+41.8)
    fig, axs = plt.subplots(5, 1, figsize=(10, 10), sharex=True)
    axs[0].plot(t[xx], w["cmp_clk"][xx], label="CMP_CLK")
    axs[0].plot(t[xx], w["sample"][xx], label="SAMPLE")
    axs[0].set_ylabel("Clock (V)")
    for node, label in (("xdut.gpp7", "P7 PMOS gate"), ("xdut.gnp7", "N7 PMOS gate"),
                        ("xdut.gcommit", "GCOMMIT")):
        axs[1].plot(t[xx], w[node][xx], label=label)
    axs[1].set_ylabel("Gate drive (V)")
    for side in "pn":
        for bit in (7, 6):
            axs[2].plot(t[xx], w[f"xdut.xcdac.b{side}{bit}"][xx], label=f"{side.upper()}{bit} bottom")
    axs[2].axhline(0, color=".4", ls=":", lw=.7)
    axs[2].axhline(.9, color=".4", ls=":", lw=.7, label="Nominal reference rails")
    axs[2].set_ylabel("Bottom (V)")
    axs[3].plot(t[xx], w["topp"][xx], label="MNINP gate = TOPP")
    axs[3].plot(t[xx], w["vinp_src"][xx], "--", label="Input source, acquisition baseline")
    axs[3].plot(t[xx], w["xdut.xcomp.y"][xx], label="MNINP drain = Y")
    axs[3].set_ylabel("Terminal (V)")
    axs[4].plot(t[xx], vg[xx], label="VGD = TOPP - Y")
    axs[4].axhline(-.99, color="#b8473e", ls="--", label="Model screen = -0.99 V")
    axs[4].set_ylabel("VGD (V)")
    for ax in axs:
        ax.grid(alpha=.2); ax.legend(fontsize=8, loc="best")
    axs[-1].set_xlabel("Time (ns)")
    fig.tight_layout(); fig.savefig(folder / "overvoltage_zoom.png", dpi=160); plt.close(fig)
    # Inspect bit6's own write, rather than assuming that 898ns is error onset.
    if len(frame["comparisons"]) > 1 and frame["comparisons"][1]["write_ns"] is not None:
        e = frame["comparisons"][1]
        a, b = e["compare_ns"]-.2, e["write_ns"]+.5
        x = (t >= a) & (t <= b)
        fig, axs = plt.subplots(4, 1, figsize=(10, 8), sharex=True)
        axs[0].plot(t[x], w["cmp_clk"][x], label="CMP_CLK")
        axs[0].plot(t[x], w["xdut.xctrl.phi_w"][x], label="PHI_W")
        axs[0].plot(t[x], w["xdut.xctrl.phi_u"][x], label="PHI_U")
        axs[0].set_ylabel("Control (V)")
        axs[1].plot(t[x], w["xdut.xctrl.data"][x], label="DATA")
        axs[1].plot(t[x], w["xdut.xctrl.t6"][x], label="Token T6")
        axs[1].set_ylabel("Input (V)")
        axs[2].plot(t[x], w["xdut.xctrl.xbit6.next_d"][x], label="bit6 NEXT_D")
        axs[2].plot(t[x], w["xdut.xctrl.xbit6.xstore.mq"][x], label="Master MQ")
        axs[2].set_ylabel("Storage (V)")
        axs[3].plot(t[x], w["d6"][x], label="Stored D6")
        axs[3].axhline(.9, color="#2b9275", ls="--", label="D6=1 for expected codes 64/65")
        axs[3].set_ylabel("D6 (V)")
        for ax in axs:
            ax.axvline(e["write_ns"], color=".5", ls=":", lw=.8)
            ax.grid(alpha=.2); ax.legend(loc="best", fontsize=8)
        axs[-1].set_xlabel("Time (ns)")
        fig.tight_layout(); fig.savefig(folder / "bit6_write.png", dpi=160); plt.close(fig)
    # Same native run: compare acquisition restore with the following normal frame.
    if focus < 11:
        fig, axs = plt.subplots(2, 1, figsize=(10, 5), sharex=True)
        for f, label, color in ((focus, f"Frame {focus}", "#c44840"),
                                 (focus+1, f"Frame {focus+1}", "#237f79")):
            rel = t-100*f
            x = (rel >= .8) & (rel <= 41.6)
            for ax,n in zip(axs,("gpp7","gnp7")):
                ax.plot(rel[x],w["xdut."+n][x],label=label,color=color)
        for ax,n,expected in zip(axs,("P7 PMOS gate","N7 PMOS gate"),(.9,0)):
            ax.axhline(expected,color=".4",ls="--",label="Required midpoint gate")
            ax.axvspan(1.05,41.05,color="#2b9275",alpha=.08,label="Acquisition")
            ax.axvline(41.05,color=".4",ls=":",lw=.8)
            ax.set_ylabel(n+" (V)");ax.set_ylim(-.1,1);ax.grid(alpha=.2)
            ax.legend(fontsize=8,ncol=2,loc="center right")
        axs[-1].set_xlabel("Time relative to frame start (ns)")
        fig.tight_layout();fig.savefig(folder/"sampling_restore.png",dpi=160);plt.close(fig)


def curate(data):
    assert data["reproduced"] and data["input_voltage_history_match"]
    assert data["reported_solver_parameters"]["all_non_output_parameters_match"]
    assert len(data["monitor"]) == 12 and all(r["compares"] == 8 for r in data["monitor"])
    assert data["context"]["original_stop_preserved"] and data["result"]["ok"]
    assert not data["frames"][0]["midpoint_check"]["observed_MSB_midpoint_correct"]
    assert data["frames"][1]["midpoint_check"]["observed_MSB_midpoint_correct"]
    assert "R3REPLAY_STOP,1.2e-06" in (Path(data["result"]["metadata"]["output_dir"]).parent/"spectre.out").read_text()
    contrast = parent.r3.r1.read_json(ROOT/"output/r3_anomaly_replay/analysis.json")
    paths = [ROOT/f"scripts/integration/{n}.py" for n in ("r3_anomaly_replay", "r3_anomaly_analyze")]
    paths += [ROOT/"models/veriloga/r3_anomaly_replay/r3_replay_stop.va",
              ROOT/"verification/integration/test_r3_anomaly_replay.py"]
    m = dict(baseline="SAR8_JOIN_R3_RESTORE_100PS_EDGE_50PS", R3_circuit_pass=False,
        scope="12-frame original-input-history TT/0.9V/27C native diagnostic; no circuit fix",
        source_text_LF_sha256={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest() for p in paths},
        remote_OA_changed=False, mismatch=False, transient_noise=False,
        native_DUT_and_wrapper_identical_except_analysis_saves_and_passive_stop_observer=True,
        replay_deck_sha256=data["context"]["deck_sha256"], parent_deck_sha256=data["context"]["parent_deck_sha256"],
        include_sha256={Path(p).name:h for p,h in data["context"]["include_sha256"].items()},
        exact_input_and_code_history_match=True, frames=data["monitor"], searches=data["searches"],
        reported_solver_parameters=data["reported_solver_parameters"],
        actual_stop_ns=1200, requested_parent_stop_ns=51600,
        result_ok=data["result"]["ok"], errors=data["result"]["errors"], warnings=data["warnings"],
        simulator_timings_s=data["result"]["metadata"]["timings"],
        frame8=data["frames"][0], normal_frame9=data["frames"][1],
        MNINP_stress=data["MNINP_stress"], frame8_VGD_screen_exposure=data["frame8_VGD_screen_exposure"],
        shortened_stop_comparison=dict(reproduced=contrast["reproduced"], input_history_matches=contrast["input_voltage_history_match"],
            codes=[r["code"] for r in contrast["monitor"]],
            parameter_differences=contrast["reported_solver_parameters"]["differences_excluding_outputstart"],
            provenance=contrast["provenance"], role="numerical-sensitivity comparison, NOT primary reproduction"),
        confirmed_electrical_failure="Observed MSB midpoint restore absent during acquisition and late after sample opens; held differential charge offset precedes first comparison; bit6 records a negative actual residual, not later memory loss",
        likely_software_trigger="sar8j_aligned_refgate combines both SAMPLE crossings and level-based > threshold phase inference; internal sampling/restored state not captured, so exact missed-event branch remains to instrument",
        qualifications=data["qualifications"], provenance=data["provenance"], raw_folder=str(OUT.relative_to(ROOT)))
    dest = ROOT/"docs/figures/r3_anomaly_replay"
    dest.mkdir(parents=True,exist_ok=True)
    images = {}
    for name in ("sampling_restore", "overvoltage_zoom", "bit6_write", "frame8_timing"):
        target = dest/f"{name}.png"
        shutil.copyfile(OUT/f"figures/frame8/{name}.png",target)
        images[target.relative_to(ROOT).as_posix()] = parent.r3.r1.sha(target)
    m["figures_sha256"] = images
    target = ROOT/"verification/integration/r3_anomaly_replay_results.json"
    target.write_text(json.dumps(m,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("CURATED",target)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--figures", action="store_true")
    ap.add_argument("--original-stop", action="store_true")
    ap.add_argument("--frame", type=int, choices=(8, 9, 10, 11), default=8)
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--curate", action="store_true")
    args = ap.parse_args()
    if args.original_stop:
        OUT = OUT / "original_stop"
        NAME = "static065_originalstop_first12"
    data, t, wave = analyze()
    if args.probe:
        probe(data, t, wave, args.frame)
    if args.figures:
        figures(data, t, wave, args.frame)
    if args.curate:
        curate(data)
