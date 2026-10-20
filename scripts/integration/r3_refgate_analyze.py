"""Hash-bound native A/B measurements and timing figures for the R3 event fix."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import pickle
import re
import shutil

import numpy as np

import r3_refgate_events as flow
from r3_anomaly_analyze import edges, monitor, searches, reported_parameters

ROOT, OUT, SHA = flow.ROOT, flow.OUT, flow.SHA
LSB = 1.8/256


def load(name):
    folder = OUT/name
    ctx = json.loads((folder/"context.json").read_text())
    result = json.loads((folder/"result.json").read_text())
    assert result["ok"], result["errors"]
    assert SHA(Path(ctx["deck"])) == result["deck_sha256"] == ctx["deck_sha256"]
    for p,h in ctx["include_sha256"].items():
        assert SHA(Path(p)) == h
    receipt = json.loads((folder/"waveform_receipt.json").read_text())
    assert SHA(folder/"waveform.pickle") == receipt["sha256"]
    # Only our own, hash-verified local generated pickle is accepted.
    with (folder/"waveform.pickle").open("rb") as stream:
        wave = {k:np.asarray(v) for k,v in pickle.load(stream).items()}
    assert all(np.isfinite(v).all() for v in wave.values())
    assert np.all(np.diff(wave["time"]) > 0)
    logpath = Path(result["metadata"]["output_dir"]).parent/"spectre.out"
    log = logpath.read_text(errors="replace")
    return ctx,result,wave,log,logpath


def state_rows(log, marker):
    rows = []
    fields = {
        "R3ASTATE": ("strobe_delta_v", "sample_now", "before_sampling", "sampling", "before_restored", "restored",
                     "overridden", "on_h", "on_l", "before_restore_at_s", "restore_at_s"),
        "R3BSTATE": ("sampling", "restored", "overridden", "on_h", "on_l", "target_h", "target_l", "restore_at_s", "turnon_at_s"),
        "R3PHASE": ("rising", "sampling", "restored", "restore_at_s"),
        "R3RESTORE": ("deadline_s", "sampling", "restored", "on_h", "on_l"),
        "R3TURNON": ("deadline_s", "on_h", "on_l"),
    }[marker]
    for line in log.splitlines():
        # Spectre progress dots/digits may precede a strobe on the same line.
        if marker+"," not in line:
            continue
        line = line[line.index(marker+","):]
        parts = line.split(",")
        assert len(parts) == len(fields)+3, line
        row = dict(instance=parts[1], time_ns=float(parts[2])*1e9)
        row.update({k:float(v) for k,v in zip(fields,parts[3:])})
        rows.append(row)
    return rows


def unit():
    report = {}
    for name in ("unit_a", "unit_b", "unit_b2", "unit_b3"):
        if not (OUT/name/"waveform_receipt.json").exists():
            continue
        ctx,result,w,log,logpath = load(name)
        t = w["time"]*1e9
        at = lambda k,ns: float(np.interp(ns,t,w[k]))
        failed, overlap,conversion_failed = [], [], []
        for i in range(4):
            for h in (0,1):
                gp,gn = f"gp{i}_{h}",f"gn{i}_{h}"
                for f in range(12):
                    ns = 100*f+30
                    if max(abs(at(gp,ns)-.9*(1-h)),abs(at(gn,ns)-.9*(1-h))) > .01:
                        failed.append(dict(index=i,initial_high=h,frame=f))
                    if max(abs(at(gp,100*f+80)),abs(at(gn,100*f+80))) > .01:
                        conversion_failed.append(dict(index=i,initial_high=h,frame=f))
                if np.any((w[gp]<.45)&(w[gn]>.45)):
                    overlap.append(dict(index=i,initial_high=h))
        phase = state_rows(log,"R3PHASE") if name!="unit_a" else []
        report[name] = dict(result_ok=result["ok"], midpoint_samples=96,
            failed_midpoint_samples=failed, high_low_overlap=overlap,
            conversion_request_samples=96,failed_conversion_request_samples=conversion_failed,
            complete_unit_pass=not failed and not overlap and not conversion_failed,
            phase_rises=sum(r["rising"]==1 for r in phase),
            phase_falls=sum(r["rising"]==0 for r in phase),
            native_log_sha256=SHA(logpath),waveform_sha256=SHA(OUT/name/"waveform.pickle"),
            warnings=result["warnings"],timings_s=result["metadata"]["timings"])
        assert not failed and not overlap
        if name!="unit_a":
            assert len(phase)==192 and all(r["rising"]==r["sampling"] for r in phase)
        if name in ("unit_a","unit_b3"):
            assert not conversion_failed
    flow.dump(OUT/"unit_analysis.json",report)
    print("UNIT_SUMMARY",json.dumps({k:dict(complete_unit_pass=v["complete_unit_pass"],
        failed_midpoint_samples=len(v["failed_midpoint_samples"]),
        failed_conversion_requests=len(v["failed_conversion_request_samples"]),
        phase_rises=v["phase_rises"],phase_falls=v["phase_falls"]) for k,v in report.items()},indent=2))
    return report


def measure(name):
    ctx,result,w,log,logpath = load(name)
    t = w["time"]*1e9
    assert t[0] >= 800-1e-5 and t[-1] >= 1200-1e-5
    at = lambda k,ns: float(np.interp(ns,t,w[k.lower()]))
    rows = monitor(log)
    sr = searches(log)
    hist = flow.history()
    assert len(rows)==12 and [r["frame"] for r in rows]==list(range(12))
    assert len(sr)==8
    assert all(abs(r["vdiff_v"]-hist[r["frame"]])<6e-13 for r in sr)
    word = lambda ns: sum(int(at(f"d{b}",ns)>.45)<<b for b in range(8))
    cmp_edges = edges(t,w["cmp_clk"])
    write_edges = edges(t,w["xdut.xctrl.phi_w"])
    update_edges = edges(t,w["xdut.xctrl.phi_u"])
    frames = []
    for f in range(8,12):
        hold = 100*f+41.05
        sample_check = hold-.1
        group = lambda a:a[(a>=hold)&(a<100*(f+1))]
        expected = {f"g{s}p{b}":.9*(1-int((s=="N")== (b==7))) for s in "PN" for b in range(8)}
        gates = {n.lower():at("xdut."+n,sample_check) for n in expected}
        expected = {k.lower():v for k,v in expected.items()}
        bad = {n:dict(expected_v=expected[n],measured_v=v) for n,v in gates.items() if abs(v-expected[n])>.09}
        nmos = {f"g{s.lower()}n{b}":at(f"xdut.g{s.lower()}n{b}",sample_check) for s in "PN" for b in range(8)}
        nmos_expected = {f"g{s.lower()}n{b}":expected[f"g{s.lower()}p{b}"] for s in "PN" for b in range(8)}
        bad.update({n:dict(expected_v=nmos_expected[n],measured_v=v) for n,v in nmos.items() if abs(v-nmos_expected[n])>.09})
        bottom_error = {f"{s}{b}":(at(f"xdut.xcdac.b{s}{b}",sample_check)-
            at("vrefp" if expected[f"g{s}p{b}"]<.45 else "vrefn",sample_check))*1e3 for s in "pn" for b in range(8)}
        source = at("vinp_src",hold+.6)-at("vinn_src",hold+.6)
        assert abs(source-hist[f])<1e-12
        comparisons = []
        for c in group(cmp_edges):
            trial = word(c-.02)|sum(int(at(f"xdut.xctrl.t{b}",c-.02)>.45)<<b for b in range(8))
            comparisons.append(dict(compare_ns=float(c),trial_word=trial,
                actual_residual_mv=(at("topp",c-.02)-at("topn",c-.02))*1e3,
                expected_residual_mv=(source+.9-trial*LSB)*1e3))
        stress = []
        for side,top,drain in (("P","topp","xdut.xcomp.y"),("N","topn","xdut.xcomp.x")):
            for terminal,a,b in (("VGD",top,drain),("VGS",top,"xdut.xcomp.tail"),
                                 ("VDS",drain,"xdut.xcomp.tail")):
                v = w[a]-w[b]
                for window,mask in (("whole_frame",(t>=100*f)&(t<100*(f+1))),
                                    ("sampling_handoff",(t>=hold-.1)&(t<=hold+.75))):
                    ix = np.flatnonzero(mask)
                    j = ix[np.argmax(np.abs(v[ix]))]
                    over = ix[np.abs(v[ix])>.99]
                    stress.append(dict(input_side=side,terminal=terminal,window=window,
                        signed_v=float(v[j]),abs_v=float(abs(v[j])),time_ns=float(t[j]),
                        gate_v=float(w[top][j]),drain_v=float(w[drain][j]),tail_v=float(w["xdut.xcomp.tail"][j]),
                        screen_exceeded=bool(len(over)),first_exceed_ns=float(t[over[0]]) if len(over) else None,
                        last_exceed_ns=float(t[over[-1]]) if len(over) else None))
        offset = (at("topp",hold+.6)-at("topn",hold+.6))-source
        row = dict(frame=f,source_diff_v=source,hold_ns=hold,output_code=word(100*f+98),
            compare_count=len(group(cmp_edges)),write_count=len(group(write_edges)),update_count=len(group(update_edges)),
            midpoint_check_ns=sample_check,midpoint_PMOS_gates_v=gates,expected_midpoint_PMOS_gates_v=expected,
            midpoint_NMOS_gates_v=nmos,expected_midpoint_NMOS_gates_v=nmos_expected,
            midpoint_bottom_reference_error_mv=bottom_error,
            bad_midpoint_banks=bad,
            midpoint_bottom_within_quarter_LSB=all(abs(v)<.25*LSB*1e3 for v in bottom_error.values()),
            all16_midpoint_banks_correct=not bad and all(abs(v)<.25*LSB*1e3 for v in bottom_error.values()),
            acquisition_error_before_off_mv=((at("topp",sample_check)-at("topn",sample_check))-source)*1e3,
            held_offset_0p6ns_mv=offset*1e3,held_offset_0p6ns_lsb=offset/LSB,
            held_error_within_quarter_LSB=bool(abs(offset)<.25*LSB),
            held_TOPP_error_mv=(at("topp",hold+.6)-(.45+source/2))*1e3,
            held_TOPN_error_mv=(at("topn",hold+.6)-(.45-source/2))*1e3,
            comparisons=comparisons,stress=stress)
        assert row["output_code"]==rows[f]["code"]
        frames.append(row)
    old = json.loads((flow.OLD/"analysis.json").read_text())
    params = reported_parameters(log)
    oldparams = old["reported_solver_parameters"]["replay"]
    diff = {k:dict(original=v,current=params.get(k)) for k,v in oldparams.items() if params.get(k)!=v}
    assert not diff,diff
    a_states = state_rows(log,"R3ASTATE")
    b_states = state_rows(log,"R3BSTATE")
    phases = state_rows(log,"R3PHASE")
    restores = state_rows(log,"R3RESTORE")
    turnons = state_rows(log,"R3TURNON")
    flow.dump(OUT/name/"state_events.json",dict(A=a_states,B=b_states,phase=phases,restore=restores,turnon=turnons))
    relevant = [r for r in a_states if 800.9 <= r["time_ns"] <= 801.4 or 840.9 <= r["time_ns"] <= 841.4]
    rejected = [dict(instance=r["instance"],time_ns=r["time_ns"],deadline_s=r["restore_at_s"],
                    early_fs=(r["restore_at_s"]-r["time_ns"]*1e-9)*1e15,
                    sampling=r["sampling"],restored=r["restored"])
                for r in a_states if r["sampling"]==1 and r["restored"]==0 and
                1e-18 < r["restore_at_s"]-r["time_ns"]*1e-9 < 1e-15]
    data = dict(variant=name,result_ok=result["ok"],codes=[r["code"] for r in rows],monitor=rows,
        original_history_codes=flow.CODES,exact_original_code_history_match=[r["code"] for r in rows]==flow.CODES,
        source_history_match=True,actual_8_logged_search_inputs_match=True,
        gross_code_outlier_frames=[r["frame"] for r in rows if r["code"] not in (64,65)],
        frames=frames,reported_solver_parameters=params,solver_differences=diff,
        state_counts=dict(A=len(a_states),B=len(b_states),phase=len(phases),restore=len(restores),turnon=len(turnons)),frame8_A_state_events=relevant,
        near_deadline_A_restore_rejections=rejected,
        timer_restore_events=restores,
        timer_restore_early_callbacks=[dict(instance=r["instance"],time_ns=r["time_ns"],
            deadline_s=r["deadline_s"],early_fs=(r["deadline_s"]-r["time_ns"]*1e-9)*1e15)
            for r in restores if r["deadline_s"]>r["time_ns"]*1e-9+1e-18],
        phase_rise_counts_by_instance={n:sum(r["instance"]==n and r["rising"]==1 for r in phases) for n in sorted({r["instance"] for r in phases})},
        phase_fall_counts_by_instance={n:sum(r["instance"]==n and r["rising"]==0 for r in phases) for n in sorted({r["instance"] for r in phases})},
        phase_values_correct=all(r["rising"]==r["sampling"] for r in phases),
        warnings=[l.strip() for l in log.splitlines() if re.search(r"WARNING \((?:CMI|SPECTRE)|\bLTE\b|suppressed",l)],
        simulator_summary=next((l for l in log.splitlines() if l.startswith("spectre completes with")),None),
        simulator_timings_s=result["metadata"]["timings"],
        context=ctx,provenance=dict(log_sha256=SHA(logpath),waveform_sha256=SHA(OUT/name/"waveform.pickle")))
    flow.dump(OUT/name/"analysis.json",data)
    print("MEASURED",name,json.dumps({k:data[k] for k in ("codes","exact_original_code_history_match","gross_code_outlier_frames","simulator_summary")},indent=2))
    print("FRAME_SUMMARY",json.dumps([{k:r[k] for k in ("frame","output_code","all16_midpoint_banks_correct","held_offset_0p6ns_mv")} for r in frames],indent=2))
    return data,t,w


def figures(a,b):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    folder = OUT/"figures"
    folder.mkdir(parents=True,exist_ok=True)
    colors = {"a":"#c74c45","b":"#157e80"}
    labels = {"a":"R3 original","b":"B repaired"}
    # The physical acquisition/hold boundary and expected baseline are shared.
    fig,axs = plt.subplots(4,1,figsize=(11,9),sharex=True)
    for name,(data,t,w) in (("a",a),("b",b)):
        x = (t>=840.95)&(t<=842.0)
        color,label = colors[name],labels[name]
        if name=="a":
            axs[0].plot(t[x],w["sample"][x],color=".25",label="SAMPLE (same A/B)")
        axs[1].plot(t[x],w["xdut.gnp7"][x],color=color,label=label)
        axs[2].plot(t[x],((w["topp"][x]-w["topn"][x])-flow.history()[8])*1e3,color=color,label=label)
        axs[3].plot(t[x],w["topp"][x]-w["xdut.xcomp.y"][x],color=color,label=label)
    axs[0].set_ylabel("SAMPLE (V)")
    axs[1].set_ylabel("N7 PMOS gate (V)"); axs[1].axhline(0,color=".35",ls="--",label="Midpoint target")
    axs[2].set_ylabel("Held error (mV)"); axs[2].axhline(0,color=".35",ls="--",label="Ideal held input")
    axs[2].axhspan(-.25*LSB*1e3,.25*LSB*1e3,color="#60a788",alpha=.14,label="+/- 0.25 LSB")
    axs[3].set_ylabel("MNINP VGD (V)");axs[3].axhline(-.99,color=".35",ls="--",label="-0.99 V screen")
    for ax in axs:
        ax.axvspan(841.05,842,color="#b2cdd8",alpha=.12,label="Hold before first comparison" if ax is axs[0] else None)
        ax.axvline(841.05,color=".4",ls=":",lw=.8)
        ax.grid(alpha=.2); ax.legend(fontsize=8,loc="best",ncol=2)
    axs[-1].set_xlabel("Time (ns)")
    fig.tight_layout();fig.savefig(folder/"frame8_handoff.png",dpi=160);plt.close(fig)
    # Zoomed scale makes the remaining small B error visible without hiding A.
    fig,axs = plt.subplots(3,1,figsize=(11,8),sharex=True)
    for name,(data,t,w) in (("a",a),("b",b)):
        x=(t>=800.8)&(t<=843.5)
        color,label=colors[name],labels[name]
        axs[0].plot(t[x],w["xdut.gnp7"][x],color=color,label=label)
        axs[1].plot(t[x],w["xdut.xcdac.bn7"][x],color=color,label=label)
        if name=="b":
            axs[2].plot(t[x],((w["topp"][x]-w["topn"][x])-flow.history()[8])*1e3,color=color,label="B residual error")
    axs[0].axhline(0,color=".35",ls="--",label="Required midpoint gate")
    axs[1].axhline(.9,color=".35",ls="--",label="Nominal N7 bottom at midpoint")
    axs[2].axhline(0,color=".35",ls="--",label="Ideal held input")
    axs[2].axhspan(-.25*LSB*1e3,.25*LSB*1e3,color="#60a788",alpha=.14,label="+/- 0.25 LSB")
    for ax in axs:
        ax.axvspan(801.05,841.05,color="#60a788",alpha=.08,label="Acquisition" if ax is axs[0] else None)
        ax.axvspan(841.05,843.5,color="#b2cdd8",alpha=.14,label="Hold before comparison" if ax is axs[0] else None)
        ax.grid(alpha=.2);ax.legend(fontsize=8,loc="best",ncol=2)
    axs[0].set_ylabel("N7 PMOS gate (V)");axs[1].set_ylabel("N7 bottom (V)")
    axs[2].set_ylabel("B error (mV)");axs[2].set_ylim(-3,3)
    axs[-1].set_xlabel("Time (ns)")
    fig.tight_layout();fig.savefig(folder/"frame8_restore.png",dpi=160);plt.close(fig)
    fig,axs=plt.subplots(3,1,figsize=(11,8),sharex=True)
    for name,(data,t,w) in (("a",a),("b",b)):
        x=(t>=841)&(t<=899)
        color,label=colors[name],labels[name]
        axs[0].plot(t[x],w["cmp_clk"][x],color=color,label=label)
        axs[1].plot(t[x],(w["topp"][x]-w["topn"][x])*1e3,color=color,label=label)
        row=data["frames"][0]
        axs[1].scatter([r["compare_ns"]-.02 for r in row["comparisons"]],
            [r["expected_residual_mv"] for r in row["comparisons"]],color=color,marker="x",s=18,label=label+" expected for actual trial")
        code=sum((w[f"d{bit}"][x]>.45).astype(int)*(1<<bit) for bit in range(8))
        axs[2].step(t[x],code,where="post",color=color,label=label)
        axs[2].scatter([898],[row["output_code"]],s=20,color=color,zorder=4)
    axs[1].axhline(0,color=".35",ls="--",label="Decision threshold")
    completed=[]
    for data,t,w in (a,b):
        ue=edges(t,w["xdut.xctrl.phi_u"])
        completed.append(float(max(ue[(ue>=841.05)&(ue<900)]))+.05)
    axs[2].fill_between([max(completed),899],64,65,color="#60a788",alpha=.3,label="Adjacent final-code range 64 / 65")
    for ax in axs:
        ax.grid(alpha=.2);ax.legend(fontsize=8,loc="best",ncol=2)
    axs[0].set_ylabel("CMP_CLK (V)");axs[1].set_ylabel("Residual (mV)");axs[2].set_ylabel("Register code")
    axs[-1].set_xlabel("Time (ns)")
    fig.tight_layout();fig.savefig(folder/"frame8_conversion.png",dpi=160);plt.close(fig)


def compare(make_figures=False,curate=False):
    unit_report=unit()
    a=measure("a"); phase_only=measure("b")[0]; b=measure("b3")
    ar,br=a[0],b[0]
    assert ar["context"]["same_12_frame_input_history"]==br["context"]["same_12_frame_input_history"]
    oldreceipt=json.loads((flow.OLD/"waveform_receipt.json").read_text())
    assert SHA(flow.OLD/"waveform.pickle")==oldreceipt["sha256"]
    with (flow.OLD/"waveform.pickle").open("rb") as stream:
        oldwave={k:np.asarray(v) for k,v in pickle.load(stream).items()}
    common=sorted((set(oldwave)&set(a[2])) - {"time"})
    same_time=np.array_equal(oldwave["time"],a[2]["time"])
    original_equivalence=dict(time_grid_identical=bool(same_time),common_signal_count=len(common),
        common_signals=common,original_waveform_sha256=oldreceipt["sha256"],
        maximum_absolute_difference= max(float(np.max(np.abs(oldwave[k]-a[2][k]))) for k in common) if same_time else None,
        all_common_signals_identical=bool(same_time and all(np.array_equal(oldwave[k],a[2][k]) for k in common)))
    del oldwave
    # An instrumented baseline that shifts numerically remains useful, but may
    # never be silently called an exact reproduction of the existing R3 run.
    report=dict(scope="12-frame TT .9V 27C reference event B experiment, unchanged native circuit",
        original_R3_reproduction_by_instrumented_A=ar["exact_original_code_history_match"],
        original_R3_common_waveform_equivalence=original_equivalence,
        inputs_identical=True,parameters_identical=True,remote_OA_changed=False,
        native_SAR_and_analog_topology_sizes_unchanged=True,shared_sources_changed=False,
        unit=unit_report,A=ar,B_phase_only_failed=phase_only,B=br,selected_B_model="b3",
        B_missing_midpoint_failure_removed=all(r["all16_midpoint_banks_correct"] for r in br["frames"]),
        B_no_gross_code_outliers=not br["gross_code_outlier_frames"],
        B_handoff_core_stress_screen_pass=not any(s["screen_exceeded"] for f in br["frames"] for s in f["stress"] if s["window"]=="sampling_handoff"),
        B_whole_observed_window_core_stress_screen_pass=not any(s["screen_exceeded"] for f in br["frames"] for s in f["stress"] if s["window"]=="whole_frame"),
        B_held_quarter_LSB_pass=all(r["held_error_within_quarter_LSB"] for r in br["frames"]),
        B_phase_events_complete=br["state_counts"]["phase"]==384 and br["phase_values_correct"] and
            all(v==12 for v in br["phase_rise_counts_by_instance"].values()) and
            all(v==12 for v in br["phase_fall_counts_by_instance"].values()),
        B_restore_events_complete=br["state_counts"]["restore"]==192 and
            all(r["sampling"]==1 and r["restored"]==1 for r in br["timer_restore_events"]),
        B_no_LTE_relaxation=not any("LTE" in s for s in br["warnings"]),
        B_no_native_CMI_warnings=not any("CMI-" in s for s in br["warnings"]),
        confirmed_cause="A entered SAMPLE correctly; a valid restore timer callback about0.159fs before its floating-point deadline was rejected by the redundant >=deadline-1e-18 guard; no later acquisition event retried it",
        repair="Direction-specific SAMPLE state, event-owned restore/turnon callbacks, edge-triggered COMMIT notification, preserved sample-fall initial-word interlock and original physical timings",
        measured_analog_frame_range=[8,9,10,11],monitor_and_state_frames=list(range(12)),
        full_ADC_performance_or_PVT_qualification=False)
    report["B_targeted_repair_pass"]=bool(report["original_R3_reproduction_by_instrumented_A"] and
        report["B_missing_midpoint_failure_removed"] and report["B_no_gross_code_outliers"] and
        report["B_handoff_core_stress_screen_pass"] and report["B_held_quarter_LSB_pass"] and
        report["B_whole_observed_window_core_stress_screen_pass"] and
        report["B_phase_events_complete"] and report["B_restore_events_complete"] and
        report["B_no_LTE_relaxation"] and report["B_no_native_CMI_warnings"] and
        all(r["compares"]==8 and r["valid"] for r in br["monitor"]) and
        unit_report["unit_b3"]["complete_unit_pass"])
    flow.dump(OUT/"comparison.json",report)
    if make_figures:
        figures(a,b)
    if curate:
        paths=[ROOT/f"scripts/integration/{n}.py" for n in ("r3_refgate_events","r3_refgate_analyze")]
        paths+=list(flow.MODEL.rglob("*.va"))+[ROOT/"verification/integration/test_r3_refgate_events.py"]
        report["source_text_LF_sha256"]={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_text().encode()).hexdigest() for p in paths}
        dest=ROOT/"docs/figures/r3_refgate_events";dest.mkdir(parents=True,exist_ok=True)
        for p in (OUT/"figures").glob("*.png"):
            shutil.copyfile(p,dest/p.name)
        report["figures_sha256"]={p.relative_to(ROOT).as_posix():SHA(p) for p in dest.glob("*.png")}
        flow.dump(ROOT/"verification/integration/r3_refgate_events_results.json",report)
    print("COMPARISON",json.dumps({k:v for k,v in report.items() if isinstance(v,bool)},indent=2))
    return report


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--unit",action="store_true")
    ap.add_argument("--figures",action="store_true")
    ap.add_argument("--curate",action="store_true")
    args=ap.parse_args()
    unit() if args.unit else compare(args.figures,args.curate)
