"""Full-rate native stress/error checks and low-memory three-slew overlays."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import restore_cross_input_analyze as previous
from reference_edge_slew import ROOT,OUT,POINTS,EDGES_PS,baselines,dump,guard

native=previous.native
FIG=ROOT/"docs/figures/sar8_reference_edge_slew"
COLORS={20:"#bd4f40",50:"#2778ac",100:"#168274"}
LABELS={"nfull":"-0.8 / -0.8 V","pfull":"+0.8 / +0.8 V",
        "n_to_p":"-0.8 / +0.8 V","p_to_n":"+0.8 / -0.8 V"}


def gate_checks(w):
    t=w["time"]*1e9;overlap=[];gaps=[]
    for side in "pn":
        for bit in range(8):
            high=.9-w[f"xdut.g{side}p{bit}"];low=w[f"xdut.g{side}n{bit}"]
            if np.any((high>.009)&(low>.009)):overlap.append(side+str(bit))
            ev=[]
            for rail,v in (("H",high),("L",low)):
                for on in (False,True):
                    ev.extend((float(x),rail,on) for x in native.edges(t,v,level=.009,rising=on) if 101<x<105)
            ev.sort();last=None
            for x,rail,on in ev:
                if not on:last=(x,rail)
                elif last and rail!=last[1]:gaps.append((x-last[0])*1e3)
    return dict(overlap_above_one_percent_banks=overlap,
                restore_min_one_percent_gate_gap_ps=min(gaps) if gaps else None,
                interpretation="gate voltage envelope, not measured transistor branch-current overlap")


def n3_peak(w):
    t=w["time"]*1e9
    sel=np.flatnonzero((t>=101.05)&(t<=103.05))
    vg=w["xdut.gnp3"];vd=w["xdut.xcdac.bn3"];gd=vg-vd
    j=int(sel[np.argmax(gd[sel])]);lo=int(sel[np.argmin(vd[sel])])
    return dict(VGD_max_v=float(gd[j]),time_ns=float(t[j]),GP_v=float(vg[j]),
                GN_v=float(w["xdut.gnn3"][j]),BN3_v=float(vd[j]),
                VREFN_v=float(w["vrefn"][j]),VREFP_v=float(w["vrefp"][j]),
                TOPN_v=float(w["topn"][j]),VDB_v=float(vd[j]-w["vdd!"][j]),
                BN3_min_v=float(vd[lo]),BN3_min_ns=float(t[lo]))


def process(name,point,edge,ctx,metrics,folder,case,reused=False):
    w=previous.prior.timing.load_wave(folder/f"runs/{case}_waveform.json")
    previous.OUT=OUT
    ctx=dict(ctx);ctx.setdefault("stimulus_transition_ns",None)
    samples=previous.prior.sampling(w,metrics["frames"])
    row=dict(name=name,point=point,edge_ps=edge,baseline_reused=reused,context=ctx,
             source_folder=folder.relative_to(ROOT).as_posix(),source_case=case,
             metrics=metrics,sampling=samples,phase_stress=previous.phase_stress(w),
             stimulus_check=previous.stimulus_check(w,ctx),
             restore_edges=previous.prior.restore_edges(w),gate_checks=gate_checks(w),
             N3=n3_peak(w),waveform_sha256=guard.base.r1.sha(folder/f"runs/{case}_waveform.json"))
    for label in ("pre_off","held","pre_first_compare"):
        row[f"max_abs_{label}_error_mv"]=max(abs(f[label]["differential_error_mv"]) for f in samples)
    row["sampling_error_pass"]=all(row[f"max_abs_{x}_error_mv"]<native.LIMIT_MV
                                    for x in ("pre_off","held","pre_first_compare"))
    row["bounded_case_pass"]=bool(metrics["bounded_join_pass"] and row["sampling_error_pass"]
        and row["stimulus_check"]["passed"] and not row["gate_checks"]["overlap_above_one_percent_banks"])
    result=guard.base.r1.read_json(folder/f"runs/{case}_result.json")
    log=(Path(result["metadata"]["output_dir"]).parent/"spectre.out").read_text(encoding="utf-8",errors="replace")
    total=re.search(r"spectre completes with (\d+) errors, (\d+) warnings, and (\d+) notices",log)
    assert total is not None
    row["simulator_totals"]=dict(zip(("errors","warnings","notices"),map(int,total.groups())))
    row["initial_DC_diagnostic_lines"]=[s.strip() for s in log.splitlines()
        if re.search(r"approximate solution|homotopy|GminDC|dV\(|Bad pivoting",s)]
    t=w["time"]*1e9;sel=(t>=101.1)&(t<=101.6)
    snippet={k:w[k][sel].tolist() for k in ("xdut.gnp3","xdut.gnn3","xdut.gnn0",
        "xdut.xcdac.bn3","vrefn","topn")}
    snippet["time_ns"]=t[sel].tolist()
    s=row["sampling"][1];sel=(t>=s["hold_ns"]-.15)&(t<=s["pre_first_compare"]["time_ns"])
    snippet["hold_relative_time_ns"]=(t[sel]-s["hold_ns"]).tolist()
    snippet["sample_error_mv"]=(((w["topp"]-w["topn"])-(w["vinp_src"]-w["vinn_src"]))[sel]*1e3).tolist()
    dump(f"snippets/{name}.json",snippet)
    dump(f"comparison/{name}.json",row)
    print(name,"PASS",row["bounded_case_pass"],"REF",metrics["reference_stress"]["value_v"],
          "COMP",metrics["comparator_stress_from_saved_internal_nodes"]["value_v"],
          "N3_GD",row["N3"]["VGD_max_v"],"HELD_MV",row["max_abs_held_error_mv"],
          "CMI",metrics["CMI_warning_count"],flush=True)
    return row


def analyze(name):
    native.OUT=OUT;native.dump=dump
    entry=native.analyze(name,plot=False)
    assert entry["result_ok"],entry
    ctx=entry["context"]
    return process(name,ctx["point"],ctx["edge_ps"],ctx,previous.prior.timing.summary(entry),OUT,name)


def baseline_analysis():
    for point,r in baselines().items():
        e=r["evidence"]
        process(f"{point}_e20ps",point,20,e["context"],e["metrics"],r["folder"],r["name"],True)


def figures(rows):
    FIG.mkdir(parents=True,exist_ok=True)
    for point in ("pfull","p_to_n"):
        fig,ax=plt.subplots(4,1,figsize=(10,9),sharex=True)
        for edge in (20,50,100):
            s=guard.base.r1.read_json(OUT/f"snippets/{point}_e{edge}ps.json")
            t=np.asarray(s["time_ns"]);bn=np.asarray(s["xdut.xcdac.bn3"])
            gp=np.asarray(s["xdut.gnp3"]);color=COLORS[edge]
            for a,vals in zip(ax,(s["xdut.gnn0"],bn*1e3,s["topn"],gp-bn)):
                a.plot(t,vals,color=color,label=f"edge = {edge} ps")
        ax[0].axhline(.9,color=".4",ls=":",label="N3 GP = GN = 0.9 V")
        ax[1].axhline(0,color=".4",ls=":",label="Nominal low rail = 0 mV")
        ax[1].axhline(-90,color="#8d5091",ls="-.",label="-90 mV => VGD = 0.99 V")
        ax[2].axhline(.05 if point=="pfull" else .85,color=".4",ls=":",label="VINN target")
        ax[3].axhline(.99,color="#8d5091",ls="-.",label="Model screen = 0.99 V")
        for a,label in zip(ax,("N0 low gate (V)","BN3 (mV)","TOPN (V)","N3 PMOS VGD (V)")):
            a.set_ylabel(label);a.grid(alpha=.2);a.legend(fontsize=8,ncol=2)
        ax[0].set_title(LABELS[point]+"; restore guard = 0.1 ns",fontsize=11)
        ax[-1].set_xlabel("Time (ns); common restore command, different gate ramp durations")
        ax[-1].set_xlim(101.12,101.55)
        fig.tight_layout();fig.savefig(FIG/f"{point}_N3_slew.png",dpi=160);plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(10,7),sharex=True)
    for point in POINTS:
        rs=sorted((r for r in rows if r["point"]==point),key=lambda r:r["edge_ps"])
        x=[r["edge_ps"] for r in rs]
        axes[0].plot(x,[r["metrics"]["reference_stress"]["value_v"] for r in rs],"o-",label=LABELS[point])
        axes[1].plot(x,[r["max_abs_held_error_mv"] for r in rs],"o-",label=LABELS[point])
    axes[0].axhline(.99,color="#8d5091",ls="-.",label="Model screen = 0.99 V")
    axes[0].set_ylabel("Whole-run max reference stress (V)")
    axes[1].axhline(native.LIMIT_MV,color="#8d5091",ls="-.",label="0.25 LSB = 1.758 mV")
    axes[1].set_ylabel("Max held sample error (mV)")
    for ax in axes:ax.grid(alpha=.2);ax.legend(fontsize=8,ncol=2)
    axes[-1].set_xticks([20,50,100]);axes[-1].set_xlabel("Reference gate edge_s (ps)")
    fig.tight_layout();fig.savefig(FIG/"four_input_summary.png",dpi=160);plt.close(fig)


def curate():
    rows=[guard.base.r1.read_json(OUT/f"comparison/{p}_e{e}ps.json") for e in (20,*EDGES_PS) for p in POINTS]
    for row in rows:
        # Preserve raw run contexts; prior experiment flags describe ancestry,
        # not additional changes relative to this sweep's own20ps baseline.
        row["inherited_context_history_flags"]={k:row["context"].pop(k)
            for k in ("only16_restore_parameter_overrides","only_input_stimulus_changed_from_candidate")
            if k in row["context"]}
        row["source_case_context_sha256"]=guard.base.r1.sha(
            ROOT/row["source_folder"]/f"cases/{row['source_case']}.json")
    paths=[ROOT/f"scripts/integration/{s}.py" for s in ("reference_edge_slew","reference_edge_slew_analyze")]
    m=dict(scope="native TT nominal ideal-reference slew sweep; no OA adoption or broad qualification",
           native_topology_sizes_VA_bytes_unchanged=True,remote_OA_changed=False,
           restore_guard_ps=100,logical_BBM_ps=100,
           prior_manifest_sha256={s:guard.base.r1.sha(ROOT/f"verification/integration/{s}.json")
                for s in ("restore_guard_results","restore_cross_input_results")},
           source_text_LF_sha256={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest() for p in paths},
           cases=rows)
    (ROOT/"verification/integration/reference_edge_slew_results.json").write_text(json.dumps(m,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    figures(rows)


if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("names",nargs="*")
    ap.add_argument("--baselines",action="store_true");ap.add_argument("--curate",action="store_true");a=ap.parse_args()
    for name in a.names:analyze(name)
    if a.baselines:baseline_analysis()
    if a.curate:curate()
