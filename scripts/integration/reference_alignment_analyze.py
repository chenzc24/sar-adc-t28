"""Read-only R1 comparison, common-edge measurements and full-rate plots."""
from __future__ import annotations
import argparse
import hashlib
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import join_r1_analyze as native_analysis
from reference_alignment import ROOT,BASE,OUT,VA,dump,r1

FIG=ROOT/"docs/figures/sar8_reference_alignment"


def load_wave(path):
    return {k:np.asarray(v) for k,v in r1.read_json(path).items()}


def handoffs(w):
    t=w["time"]*1e9
    us=native_analysis.edges(t,w["xdut.xctrl.phi_u"])
    rows=[]
    for u in us:
        if not (41<u<99 or 141<u<199):continue
        ons=[];offs=[];banks=[]
        for s in "pn":
            for bit in range(8):
                gp=w[f"xdut.g{s}p{bit}"];gn=w[f"xdut.g{s}n{bit}"]
                ev=[]
                for v in (.9-gp,gn):
                    on=native_analysis.edges(t,v);off=native_analysis.edges(t,v,rising=False)
                    ev.extend((x,True) for x in on if u<x<u+1.2)
                    ev.extend((x,False) for x in off if u<x<u+1.2)
                if ev:
                    banks.append(s.upper()+str(bit))
                    ons.extend(float(x) for x,on in ev if on)
                    offs.extend(float(x) for x,on in ev if not on)
        rows.append(dict(update_ns=float(u),banks=banks,on_ns=ons,off_ns=offs,
                         on_spread_ps=float(np.ptp(ons)*1e3) if ons else None,
                         off_spread_ps=float(np.ptp(offs)*1e3) if offs else None))
    return rows


def summary(entry):
    return {k:entry[k] for k in ("name","result_ok","frames","reference_stress",
        "minimum_opposite_rail_deadtime_ps","simultaneous_gate_enable_banks",
        "raw_both_on_banks","CMI_warning_count","CMI_warnings","warning_codes",
        "suppression_or_LTE_lines","comparator_stress_from_saved_internal_nodes",
        "top_node_ranges","bounded_join_pass")}


def phase_stress(w):
    t=w["time"]*1e9
    ref=np.zeros_like(t);comp=np.zeros_like(t)
    zeros=np.zeros_like(t)
    for side in "pn":
        for bit in range(8):
            bot=w[f"xdut.xcdac.b{side}{bit}"]
            for gate,source,body in ((w[f"xdut.g{side}p{bit}"],w["vrefp"],w["vdd!"]),
                                      (w[f"xdut.g{side}n{bit}"],w["vrefn"],zeros)):
                for a,b in ((bot,source),(gate,source),(gate,bot),(bot,body),(source,body),(gate,body)):
                    ref=np.maximum(ref,abs(a-b))
    nodes={"VINP":w["topp"],"VINN":w["topn"],"OUTP":w["comp_p"],"OUTN":w["comp_n"],
           "CLK":w["cmp_clk"],"VDD":w["vdd!"],"VSS":zeros,
           **{n:w["xdut.xcomp."+n.lower()] for n in ("X","Y","TAIL")}}
    source=r1.read_json(BASE/"dependencies/sar_strongarm_t28.json")
    for part in source["instances"]:
        for a,b in (("D","S"),("G","S"),("G","D"),("D","B"),("S","B"),("G","B")):
            comp=np.maximum(comp,abs(nodes[part["terms"][a]]-nodes[part["terms"][b]]))
    out={}
    for phase,mask in (("conversion",((t>41.1)&(t<100.9))|((t>141.1)&(t<200))),
                       ("second_acquisition",(t>=101.05)&(t<=141.05)),
                       ("first_MSB_handoff",(t>144)&(t<146))):
        indices=np.flatnonzero(mask)
        j=indices[np.argmax(ref[mask])];k=indices[np.argmax(comp[mask])]
        out[phase]=dict(reference_max_v=float(ref[j]),reference_max_ns=float(t[j]),
                        comparator_max_v=float(comp[k]),comparator_max_ns=float(t[k]),
                        TOPN_max_v=float(np.max(w["topn"][mask])),TOPP_min_v=float(np.min(w["topp"][mask])))
    return out


def analyze(name):
    # Existing functional/stress equations, isolated output routing.
    native_analysis.OUT=OUT;native_analysis.dump=dump
    entry=native_analysis.analyze(name,plot=False)
    assert entry["result_ok"],entry
    ctx=r1.read_json(OUT/f"cases/{name}.json")
    base=ctx["baseline_case"]
    frozen=r1.read_json(ROOT/"verification/integration/join_r1_results.json")
    original=next(c for c in frozen["cases"] if c["name"]==base)
    assert r1.sha(BASE/f"decks/{base}.scs")==original["deck_sha256"]
    assert r1.sha(BASE/f"runs/{base}_waveform.json")==original["waveform_sha256"]
    old=r1.read_json(BASE/f"analysis/{base}.json")
    new=load_wave(OUT/f"runs/{name}_waveform.json")
    before=load_wave(BASE/f"runs/{base}_waveform.json")
    entry["handoffs"]=handoffs(new)
    prior=summary(old);prior["handoffs"]=handoffs(before);prior["phase_stress"]=phase_stress(before)
    row=dict(name=name,baseline=prior,aligned=summary(entry),
             handoffs=entry["handoffs"],context=ctx,
             waveform_sha256=r1.sha(OUT/f"runs/{name}_waveform.json"),
             baseline_waveform_sha256=r1.sha(BASE/f"runs/{base}_waveform.json"),
             gate_va_sha256=r1.sha(VA),phase_stress=phase_stress(new))
    dump(f"comparison/{name}.json",row)
    print(name,"codes",[f["observed_codes_in_window"] for f in entry["frames"]],
          "functional",all(f["frame_pass"] for f in entry["frames"]),
          "ref",entry["reference_stress"]["value_v"],
          "comp",entry["comparator_stress_from_saved_internal_nodes"]["value_v"],
          "CMI",entry["CMI_warning_count"],"PASS",entry["bounded_join_pass"],flush=True)
    if ctx["point"]=="nfull":plot_comparison(name,before,new)
    return row


def plot_comparison(name,before,after):
    FIG.mkdir(parents=True,exist_ok=True)
    fig,ax=plt.subplots(4,2,figsize=(13,10),sharex="col",sharey="row")
    for col,(w,title) in enumerate(((before,"Frozen R1"),(after,"Aligned reference gates"))):
        t=w["time"]*1e9
        u=native_analysis.edges(t,w["xdut.xctrl.phi_u"])
        u=float(u[(u>141)&(u<150)][0])
        x=t-u;mask=(x>=-.12)&(x<=.85)
        ax[0,col].set_title(title)
        for key,label,color in (("xdut.xctrl.phi_u","UPDATE",".55"),
                                ("xdut.gnp6","N6 high enable","#21877e"),
                                ("xdut.gnn7","N7 low enable","#c5493e")):
            v=.9-w[key] if key=="xdut.gnp6" else w[key]
            ax[0,col].plot(x[mask],v[mask],label=label,color=color)
        for key,label,color in (("xdut.xcdac.bn6","N6 bottom","#21877e"),
                                ("xdut.xcdac.bn7","N7 bottom","#c5493e")):
            ax[1,col].plot(x[mask],w[key][mask],label=label,color=color)
        for key,label,color in (("topp","TOPP","#21877e"),("topn","TOPN","#c5493e")):
            ax[2,col].plot(x[mask],w[key][mask],label=label,color=color)
        ax[1,col].axhline(.9,color=".5",ls="--",lw=.9,label="Nominal high = 0.90 V")
        for row in (1,2):
            ax[row,col].axhline(.99,color="#884b95",ls=":",lw=1,label="Upper screen = 0.99 V")
            ax[row,col].axhline(0,color=".5",ls="--",lw=.7)
        ax[2,col].axhline(-.09,color="#884b95",ls=":",lw=1,label="Lower screen = -0.09 V")
        ax[3,col].plot(x[mask],w["vrefp"][mask],label="VREFP",color="#21877e")
        ax[3,col].plot(x[mask],w["vrefn"][mask],label="VREFN",color="#c5493e")
        ax[3,col].axhline(.9,color=".5",ls="--",lw=.7,label="Nominal rails = 0 / 0.90 V")
        ax[3,col].axhline(0,color=".5",ls="--",lw=.7)
        for a in ax[:,col]:
            a.set_facecolor("#f4f6f8")
            a.grid(alpha=.2);a.legend(loc="upper right",fontsize=7,ncol=1)
            a.set_xlim(-.12,.85)
        ax[-1,col].set_xlabel("Time from native UPDATE (ns); entire view is hold/conversion")
    for a,label in zip(ax[:,0],("Gate / update (V)","CDAC bottom (V)","CDAC top (V)","Reference (V)")):
        a.set_ylabel(label)
    fig.tight_layout()
    fig.savefig(FIG/f"{name}_timing.png",dpi=160)
    plt.close(fig)

    fig,axes=plt.subplots(2,1,figsize=(9,6),sharex=True)
    for w,label,style in ((before,"Frozen R1","--"),(after,"Aligned","-")):
        t=w["time"]*1e9;sel=(t>=102.9)&(t<=103.65)
        for axis,key in zip(axes,("topn","topp")):
            axis.plot(t[sel],w[key][sel],style,label=label)
    axes[0].axhline(.85,color=".45",ls=":",label="Acquisition target = 0.85 V")
    axes[0].axhline(.99,color="#884b95",ls="--",label="VGB screen = 0.99 V")
    axes[1].axhline(.05,color=".45",ls=":",label="Acquisition target = 0.05 V")
    # X node remains near VDD during comparator reset; saved six-pair checks
    # decide actual VGD, not this approximate visual input boundary.
    axes[1].axhline(-.09,color="#884b95",ls="--",label="Approx. VGD boundary = -0.09 V")
    for axis,label in zip(axes,("TOPN (V)","TOPP (V)")):
        axis.axvspan(102.9,103.65,color="#e5f0e7",alpha=.4)
        axis.axvline(103.05,color=".5",ls=":",label="Midpoint restore command")
        axis.grid(alpha=.2);axis.legend(fontsize=8,ncol=2);axis.set_ylabel(label)
    axes[-1].set_xlabel("Time (ns); sampling/acquisition phase")
    fig.tight_layout();fig.savefig(FIG/f"{name}_restore.png",dpi=160);plt.close(fig)


def curate(names):
    cases=[r1.read_json(OUT/f"comparison/{n}.json") for n in names]
    source_paths=[VA,ROOT/"scripts/integration/reference_alignment.py",
                  ROOT/"scripts/integration/reference_alignment_analyze.py"]
    text_sha=lambda p:hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest()
    manifest=dict(scope="netlist-only TT nominal timing alignment, not a new freeze or SOA signoff",
                  native_topology_and_sizes_unchanged=True,remote_OA_changed=False,
                  ideal_timing_boundary_changed=True,source_hash_normalization="UTF-8 text LF",
                  sources={str(p.relative_to(ROOT)):text_sha(p) for p in source_paths},
                  cases=cases)
    path=ROOT/"verification/integration/reference_alignment_results.json"
    path.write_text(json.dumps(manifest,indent=2,allow_nan=False)+"\n",encoding="utf-8")


if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("names",nargs="+")
    ap.add_argument("--curate",action="store_true");args=ap.parse_args()
    for name in args.names:analyze(name)
    if args.curate:curate(args.names)
