"""Polarity/history-aware native SAR8 stress and source-referred sample checks."""
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

import restore_guard_analyze as prior
from restore_cross_input import ROOT,OUT,CASES,TRANSITION_NS,candidate,dump,guard

native=prior.native
FIG=ROOT/"docs/figures/sar8_restore_cross_input"
LABELS={"pfull_g100ps":"+0.8 / +0.8 V","n_to_p_g100ps":"-0.8 / +0.8 V",
        "p_to_n_g100ps":"+0.8 / -0.8 V"}


def phase_stress(w):
    t=w["time"]*1e9;zero=np.zeros_like(t)
    ref=zero.copy();comp=zero.copy()
    for side in "pn":
        for bit in range(8):
            bot=w[f"xdut.xcdac.b{side}{bit}"]
            for gate,source,body in ((w[f"xdut.g{side}p{bit}"],w["vrefp"],w["vdd!"]),
                                      (w[f"xdut.g{side}n{bit}"],w["vrefn"],zero)):
                for a,b in ((bot,source),(gate,source),(gate,bot),(bot,body),(source,body),(gate,body)):
                    ref=np.maximum(ref,abs(a-b))
    nodes={"VINP":w["topp"],"VINN":w["topn"],"OUTP":w["comp_p"],"OUTN":w["comp_n"],
           "CLK":w["cmp_clk"],"VDD":w["vdd!"],"VSS":zero,
           **{n:w["xdut.xcomp."+n.lower()] for n in ("X","Y","TAIL")}}
    source=guard.base.r1.read_json(OUT/"dependencies/sar_strongarm_t28.json")
    assert len(source["instances"])==11
    for part in source["instances"]:
        for a,b in (("D","S"),("G","S"),("G","D"),("D","B"),("S","B"),("G","B")):
            comp=np.maximum(comp,abs(nodes[part["terms"][a]]-nodes[part["terms"][b]]))
    phases={"first_acquisition":(t>=1.05)&(t<=41.05),
            "input_transition":(t>=100.8)&(t<101.05),
            "second_restore":(t>=101.05)&(t<=103.05),
            "second_acquisition":(t>=101.05)&(t<=141.05),
            "conversion":((t>41.05)&(t<100.8))|((t>141.05)&(t<=200)),
            "whole_run":np.ones(len(t),dtype=bool)}
    rows={}
    for name,mask in phases.items():
        ii=np.flatnonzero(mask);i=ii[np.argmax(ref[mask])];j=ii[np.argmax(comp[mask])]
        row=dict(reference_max_v=float(ref[i]),reference_max_ns=float(t[i]),
                 comparator_max_v=float(comp[j]),comparator_max_ns=float(t[j]))
        for node in ("topp","topn"):
            hi=ii[np.argmax(w[node][mask])];lo=ii[np.argmin(w[node][mask])]
            row[node.upper()]=dict(max_v=float(w[node][hi]),max_ns=float(t[hi]),
                                   min_v=float(w[node][lo]),min_ns=float(t[lo]))
        rows[name]=row
    return rows


def stimulus_check(w,ctx):
    t=w["time"]*1e9;v0,v1=ctx["stimulus_vdiff_by_frame"]
    expected=v0+(v1-v0)*np.clip((t-TRANSITION_NS[0])/(TRANSITION_NS[1]-TRANSITION_NS[0]),0,1)
    err=max(float(np.max(abs(w["vinp_src"]-(.45+expected/2)))),
            float(np.max(abs(w["vinn_src"]-(.45-expected/2)))))
    return dict(max_abs_source_error_v=err,passed=err<1e-8,
                transition_ns=ctx["stimulus_transition_ns"],
                frame_targets_v=[dict(VINP=.45+v/2,VINN=.45-v/2) for v in (v0,v1)])


def analyze(name):
    native.OUT=OUT;native.dump=dump
    entry=native.analyze(name,plot=False)
    assert entry["result_ok"],entry
    ctx=entry["context"]
    w=prior.timing.load_wave(OUT/f"runs/{name}_waveform.json")
    samples=prior.sampling(w,entry["frames"])
    checks=stimulus_check(w,ctx)
    phases=phase_stress(w)
    row=dict(name=name,context=ctx,metrics=prior.timing.summary(entry),
             sampling=samples,phase_stress=phases,stimulus_check=checks,
             restore_edges=prior.restore_edges(w),
             waveform_sha256=guard.base.r1.sha(OUT/f"runs/{name}_waveform.json"))
    for label in ("pre_off","held","pre_first_compare"):
        row[f"max_abs_{label}_error_mv"]=max(abs(f[label]["differential_error_mv"]) for f in samples)
    row["sampling_error_pass"]=all(row[f"max_abs_{label}_error_mv"]<native.LIMIT_MV
                                    for label in ("pre_off","held","pre_first_compare"))
    row["bounded_case_pass"]=entry["bounded_join_pass"] and row["sampling_error_pass"] and checks["passed"]
    dump(f"comparison/{name}.json",row)
    p=phases["second_acquisition"]
    print(name,"PASS",row["bounded_case_pass"],"CODES",[f["observed_codes_in_window"] for f in entry["frames"]],
          "REF",phases["whole_run"]["reference_max_v"],"COMP",phases["whole_run"]["comparator_max_v"],
          "ACQ_COMP",p["comparator_max_v"],"HELD_MV",row["max_abs_held_error_mv"],
          "CMI",entry["CMI_warning_count"],flush=True)
    figures(row,w)
    return row


def figures(row,w):
    FIG.mkdir(parents=True,exist_ok=True)
    t=w["time"]*1e9;ctx=row["context"];name=row["name"]
    fig,axes=plt.subplots(4,1,figsize=(10,9),sharex=True)
    mask=(t>=100.7)&(t<=105)
    for node,color in (("vinp_src","#2a62a7"),("vinn_src","#bf583f")):
        axes[0].plot(t[mask],w[node][mask],label=node.upper(),color=color)
    axes[1].plot(t[mask],w["sample"][mask],label="SAMPLE",color=".35")
    # A positive previous code can leave bit7 unchanged: show an actually changed bank.
    bank=sorted({e["bank"] for e in row["restore_edges"]["events"]})[0]
    side,bit=bank[0],int(bank[1:])
    axes[1].plot(t[mask],(.9-w[f"xdut.g{side}p{bit}"])[mask],label=bank.upper()+" high enable",color="#2a62a7")
    axes[1].plot(t[mask],w[f"xdut.g{side}n{bit}"][mask],label=bank.upper()+" low enable",color="#bf583f")
    for side,ax,color in (("p",axes[2],"#2a62a7"),("n",axes[3],"#bf583f")):
        ax.plot(t[mask],w["top"+side][mask],label="TOP"+side.upper(),color=color)
        ax.plot(t[mask],w["vin"+side+"_src"][mask],label="Input target",color=".4",ls=":")
        ax.axhline(.99,color="#8f4d92",ls="-.",label="Upper screen = 0.99 V")
        ax.axhline(-.09,color="#8f4d92",ls="-.",label="Approx. lower screen = -0.09 V")
        ax.axhline(.9,color=".7",lw=.7);ax.axhline(0,color=".7",lw=.7)
    for ax,label in zip(axes,("Input source (V)","Phase / enable (V)","TOPP (V)","TOPN (V)")):
        ax.set_ylabel(label);ax.axvline(101.05,color=".5",ls=":")
        ax.axvline(101.26,color=".6",ls="--");ax.grid(alpha=.2);ax.legend(fontsize=8,ncol=2)
        ax.set_xlim(100.7,105)
    axes[0].set_title(LABELS[name]+"; restore guard = 0.1 ns",fontsize=11)
    axes[1].plot([],[],color=".6",ls="--",label="New rail on = 101.26 ns")
    axes[1].legend(fontsize=8,ncol=2)
    axes[-1].set_xlabel("Time (ns); second acquisition starts at 101.05 ns")
    fig.tight_layout();fig.savefig(FIG/f"{name}_restore.png",dpi=150);plt.close(fig)

    fig,axes=plt.subplots(2,1,figsize=(10,6),sharex=True)
    for f in row["sampling"]:
        h=f["hold_ns"];end=f["pre_first_compare"]["time_ns"]
        mask=(t>=h-.15)&(t<=end);x=t[mask]-h
        axes[0].plot(x,w["sample"][mask],label=f"Frame {f['frame']}")
        error=((w["topp"]-w["topn"])-(w["vinp_src"]-w["vinn_src"]))*1e3
        axes[1].plot(x,error[mask],label=f"Frame {f['frame']}: {ctx['stimulus_vdiff_by_frame'][f['frame']-1]:+.1f} V")
        axes[1].plot(end-h,f["pre_first_compare"]["differential_error_mv"],"o",ms=4,color=".3")
    axes[0].set_ylabel("SAMPLE (V)")
    axes[1].set_ylabel("Differential sample error (mV)")
    axes[1].axhspan(-native.LIMIT_MV,native.LIMIT_MV,color="#cce3d4",alpha=.5,label="±0.25 LSB")
    axes[1].axhline(0,color=".5",lw=.8)
    for ax in axes:
        ax.axvline(.5,color=".5",ls=":",label="Held check (+0.5 ns)")
        ax.axvline(0,color=".6",ls="--",label="SAMPLE falling 50%")
        ax.legend(fontsize=8,ncol=2);ax.grid(alpha=.2)
    axes[-1].set_xlabel("Time from each frame's hold start (ns); dots = first compare - 20 ps")
    fig.tight_layout();fig.savefig(FIG/f"{name}_sample_error.png",dpi=150);plt.close(fig)


def curate():
    rows=[guard.base.r1.read_json(OUT/f"comparison/{n}.json") for n in CASES]
    for row in rows:
        result=guard.base.r1.read_json(OUT/f"runs/{row['name']}_result.json")
        log=(Path(result["metadata"]["output_dir"]).parent/"spectre.out").read_text(encoding="utf-8",errors="replace")
        total=re.search(r"spectre completes with (\d+) errors, (\d+) warnings, and (\d+) notices",log)
        assert total is not None,row["name"]
        row["simulator_totals"]=dict(zip(("errors","warnings","notices"),map(int,total.groups())))
        row["initial_DC_diagnostic_lines"]=[line.strip() for line in log.splitlines()
            if re.search(r"approximate solution|homotopy|GminDC|dV\(|Bad pivoting",line)]
    old,_=candidate()
    paths=[ROOT/f"scripts/integration/{s}.py" for s in ("restore_cross_input","restore_cross_input_analyze")]
    m=dict(scope="100ps ideal restore TT nominal, positive and cross-frame polarity inputs; no OA adoption",
           native_topology_sizes_VA_bytes_unchanged=True,remote_OA_changed=False,
           restore_guard_ps=100,prior_negative_full_case_reused_as_context=old,
           prior_manifest_sha256=guard.base.r1.sha(ROOT/"verification/integration/restore_guard_results.json"),
           source_text_LF_sha256={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest() for p in paths},
           cases=rows)
    p=ROOT/"verification/integration/restore_cross_input_results.json"
    p.write_text(json.dumps(m,indent=2,allow_nan=False)+"\n",encoding="utf-8")


if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("names",nargs="*")
    ap.add_argument("--curate",action="store_true");args=ap.parse_args()
    for n in args.names:analyze(n)
    if args.curate:curate()
