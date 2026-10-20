"""Restore delay comparison with independent acquisition/held error reads."""
from __future__ import annotations
import argparse
import hashlib
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import join_r1_analyze as native
import reference_alignment_analyze as timing
from restore_guard import ROOT,BASE,OUT,GUARDS_PS,baseline,dump,base

FIG=ROOT/"docs/figures/sar8_restore_guard"


def sampling(w,frames):
    t=w["time"]*1e9
    at=lambda k,x:float(np.interp(x,t,w[k]))
    rows=[]
    for frame in frames:
        h=frame["hold_start_ns"]
        row=dict(frame=frame["frame"],hold_ns=h)
        for name,x in (("pre_off",h-.1),("held",h+.5),
                       ("pre_first_compare",frame["comparisons"][0]["compare_ns"]-.02)):
            tp,tn=at("topp",x),at("topn",x)
            vp,vn=at("vinp_src",x),at("vinn_src",x)
            row[name]=dict(time_ns=x,TOPP_v=tp,TOPN_v=tn,
                           P_error_mv=(tp-vp)*1e3,N_error_mv=(tn-vn)*1e3,
                           differential_error_mv=((tp-tn)-(vp-vn))*1e3,
                           common_mode_error_mv=((tp+tn-vp-vn)/2)*1e3)
        rows.append(row)
    return rows


def restore_edges(w):
    t=w["time"]*1e9
    events=[]
    for s in "pn":
        for bit in range(8):
            gp=w[f"xdut.g{s}p{bit}"];gn=w[f"xdut.g{s}n{bit}"]
            for label,v in (("H",.9-gp),("L",gn)):
                for up in (False,True):
                    for x in native.edges(t,v,rising=up):
                        if 101<x<105:events.append(dict(bank=s+str(bit),rail=label,on=up,time_ns=float(x)))
    ons=[r["time_ns"] for r in events if r["on"]]
    offs=[r["time_ns"] for r in events if not r["on"]]
    return dict(events=events,new_on_ns=sorted(set(ons)),old_off_ns=sorted(set(offs)),
                on_spread_ps=float(np.ptp(ons)*1e3) if ons else None,
                off_spread_ps=float(np.ptp(offs)*1e3) if offs else None)


def analyze(name=None):
    if name is None:
        frozen=baseline();ctx=frozen["context"]
        entry=frozen["metrics"];folder=BASE;case="nfull";guard=2000
        wave_sha=frozen["waveform_sha256"];reused=True
    else:
        native.OUT=OUT;native.dump=dump
        entry=native.analyze(name,plot=False)
        assert entry["result_ok"],entry
        ctx=entry["context"];folder=OUT;case=name;guard=ctx["restore_guard_ps"]
        wave_sha=base.r1.sha(folder/f"runs/{case}_waveform.json");reused=False
    w=timing.load_wave(folder/f"runs/{case}_waveform.json")
    sample=sampling(w,entry["frames"])
    phases=timing.phase_stress(w)
    row=dict(name=f"guard_{guard}ps",restore_guard_ps=guard,baseline_reused=reused,
             source_case=case,source_folder=folder.relative_to(ROOT).as_posix(),
             context=ctx,metrics=timing.summary(entry),phase_stress=phases,
             sampling=sample,restore_edges=restore_edges(w),waveform_sha256=wave_sha)
    row["max_abs_held_sample_error_mv"]=max(abs(f["held"]["differential_error_mv"]) for f in sample)
    row["max_abs_preoff_sample_error_mv"]=max(abs(f["pre_off"]["differential_error_mv"]) for f in sample)
    row["max_abs_first_compare_sample_error_mv"]=max(abs(f["pre_first_compare"]["differential_error_mv"]) for f in sample)
    row["sampling_error_pass"]=all(abs(f[p]["differential_error_mv"])<native.LIMIT_MV
        for f in sample for p in ("pre_off","held","pre_first_compare"))
    dump(f"comparison/{row['name']}.json",row)
    peak=phases["second_acquisition"]
    print(row["name"],"RESTORE_REF",peak["reference_max_v"],"RESTORE_COMP",peak["comparator_max_v"],
          "TOPN",peak["TOPN_max_v"],"TOPP",peak["TOPP_min_v"],
          "HELD_MV",row["max_abs_held_sample_error_mv"],"CMI",entry["CMI_warning_count"],
          "FRAME_PASS",all(f["frame_pass"] for f in entry["frames"]),flush=True)
    return row


def plot_all(rows):
    FIG.mkdir(parents=True,exist_ok=True)
    colors={100:"#2865a8",500:"#168274",2000:"#c54a40"}
    fig,axes=plt.subplots(3,1,figsize=(10,8),sharex=True)
    errfig,errax=plt.subplots(2,1,figsize=(10,6),sharex=True)
    first_check=max(r["sampling"][1]["pre_first_compare"]["time_ns"] for r in rows)
    for r in rows:
        guard=r["restore_guard_ps"];color=colors[guard]
        label=f"{guard/1000:g} ns"+(" (R2)" if guard==2000 else "")
        style="--" if guard==2000 else "-"
        w=timing.load_wave(ROOT/r["source_folder"]/f"runs/{r['source_case']}_waveform.json")
        t=w["time"]*1e9;mask=(t>=100.9)&(t<=106)
        axes[0].plot(t[mask],(.9-w["xdut.gnp7"])[mask],style,color=color,label=label)
        axes[1].plot(t[mask],w["topn"][mask],style,color=color,label=label)
        axes[2].plot(t[mask],w["topp"][mask],style,color=color,label=label)
        # Same comparison criteria across guards, not just a visually flat trace.
        em=(t>=140.9)&(t<=first_check)
        err=((w["topp"]-w["topn"])-(w["vinp_src"]-w["vinn_src"]))*1e3
        if guard==2000:
            errax[0].plot(t[em],w["sample"][em],color=".4",label="SAMPLE (common to all cases)")
        errax[1].plot(t[em],err[em],style,color=color,label=label)
    axes[0].axvline(101.05,color=".5",ls=":",label="SAMPLE rises")
    axes[1].axhline(.85,color=".45",ls=":",label="VINN target = 0.85 V")
    axes[1].axhline(.99,color="#8a4d92",ls="-.",label="VGB check = 0.99 V")
    axes[2].axhline(.05,color=".45",ls=":",label="VINP target = 0.05 V")
    axes[2].axhline(-.09,color="#8a4d92",ls="-.",label="Approx. input lower screen = -0.09 V")
    for ax,label in zip(axes,("N7 high enable (V)","TOPN (V)","TOPP (V)")):
        ax.set_ylabel(label);ax.set_xlim(100.9,106);ax.grid(alpha=.2)
        ax.axvspan(101.05,106,color="#edf3ed",alpha=.4)
        ax.legend(fontsize=8,loc="best",ncol=2)
    axes[-1].set_xlabel("Time (ns); reference restoration during second acquisition")
    fig.tight_layout();fig.savefig(FIG/"restore_timing.png",dpi=160);plt.close(fig)
    errax[0].set_ylabel("SAMPLE (V)")
    errax[1].axhspan(-native.LIMIT_MV,native.LIMIT_MV,color="#cce3d4",alpha=.5,label="±0.25 LSB")
    errax[1].axhline(0,color=".5",lw=.8)
    errax[1].set_ylabel("Differential sample error (mV)")
    for ax in errax:
        ax.axvline(141.55,color=".45",ls=":",label="Held check = 141.55 ns")
        ax.axvline(first_check,color=".6",ls="--",label="First compare - 20 ps")
        ax.set_xlim(140.9,first_check+.02);ax.grid(alpha=.2);ax.legend(fontsize=8,ncol=2)
    errax[-1].set_xlabel("Time (ns)")
    errfig.tight_layout();errfig.savefig(FIG/"sample_error.png",dpi=160);plt.close(errfig)


def curate():
    rows=[base.r1.read_json(OUT/f"comparison/guard_{g}ps.json") for g in (*GUARDS_PS,2000)]
    paths=[ROOT/f"scripts/integration/{s}.py" for s in ("restore_guard","restore_guard_analyze")]
    text_sha=lambda p:hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest()
    manifest=dict(scope="netlist-only restore-delay screen at -0.8V, TT/.9V/27C; no adoption or broad qualification",
                  native_topology_sizes_VA_bytes_unchanged=True,remote_OA_changed=False,
                  baseline_R2_manifest_sha256=base.r1.sha(ROOT/"verification/integration/join_r2_results.json"),
                  source_text_LF_sha256={p.relative_to(ROOT).as_posix():text_sha(p) for p in paths},cases=rows)
    p=ROOT/"verification/integration/restore_guard_results.json"
    p.write_text(json.dumps(manifest,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    plot_all(rows)


if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("names",nargs="*")
    ap.add_argument("--baseline",action="store_true");ap.add_argument("--curate",action="store_true")
    args=ap.parse_args()
    for name in args.names:analyze(name)
    if args.baseline:analyze()
    if args.curate:curate()
