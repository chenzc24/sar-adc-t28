"""Read actual native joint timing, charge errors and reference terminal stress."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from join_r1 import ROOT, OUT, dump, read_json, sha

LSB=1.8/256
LIMIT_MV=LSB/4*1e3
FIG=ROOT/"docs/figures/sar8_join_r1"


def edges(t,v,level=.45,rising=True):
    mask=(v[:-1]<level)&(v[1:]>=level) if rising else (v[:-1]>level)&(v[1:]<=level)
    ii=np.flatnonzero(mask)
    return t[ii]+(level-v[ii])*(t[ii+1]-t[ii])/(v[ii+1]-v[ii])


def analyze(name,plot=True):
    ctx=read_json(OUT/f"cases/{name}.json");result=read_json(OUT/f"runs/{name}_result.json")
    assert sha(OUT/f"decks/{name}.scs")==ctx["deck_sha256"]==result["deck_sha256"]
    if not result["ok"]:
        return dict(name=name,result_ok=False,errors=result["errors"],bounded_join_pass=False)
    w={k:np.asarray(v,dtype=float) for k,v in read_json(OUT/f"runs/{name}_waveform.json").items()}
    t=w["time"]*1e9
    assert t[-1]>=200-1e-6 and np.all(np.diff(t)>0)
    at=lambda k,ns:float(np.interp(ns,t,w[k.lower()]))
    word=lambda prefix,ns:sum(int(at(prefix+str(b),ns)>.45)*(1<<b) for b in range(8))
    falls=edges(t,w["sample"],rising=False)
    compare=edges(t,w["cmp_clk"])
    writes=edges(t,w["xdut.xctrl.phi_w"])
    updates=edges(t,w["xdut.xctrl.phi_u"])
    diff=w["topp"]-w["topn"]
    frames=[]
    for f,hold in enumerate(falls):
        if f>=2:break
        a,b=95+100*f,99+100*f
        v=ctx["stimulus_vdiff_by_frame"][f]
        ideal_code=int(np.clip(np.floor((v+.9)/LSB),0,255))
        cs=compare[(compare>=hold)&(compare<100*(f+1))]
        ws=writes[(writes>=hold)&(writes<100*(f+1))]
        us=updates[(updates>=hold)&(updates<100*(f+1))]
        rows=[]
        for j,c in enumerate(cs):
            instant=c-.02
            code=word("xdut.xctrl.code",instant)
            actual=at("topp",instant)-at("topn",instant)
            ideal=v+.9-code*LSB
            later=ws[j]-.02 if j<len(ws) else c+.3
            p,n=at("comp_p",later),at("comp_n",later)
            resolved=(p>.8 and n<.1) or (n>.8 and p<.1)
            token=word("xdut.xctrl.t",later)
            phys={s:sum(int(at(f"xdut.g{s}p{k}",instant)<.45)*(1<<k) for k in range(8)) for s in "pn"}
            rows.append(dict(bit=7-j,compare_ns=float(c),write_ns=float(ws[j]) if j<len(ws) else None,
                             trial_code=code,ideal_residual_mv=ideal*1e3,actual_residual_mv=actual*1e3,
                             error_mv=(actual-ideal)*1e3,common_mode_v=(at("topp",instant)+at("topn",instant))/2,
                             resolved=bool(resolved),decision_p=p>.45,
                             sign_agrees=bool((p>n)==(actual>=0)),outp_v=p,outn_v=n,
                             token_at_write=token,token_order_ok=bool(j<8 and token==(1<<(7-j))),
                             physical_high_words=phys,physical_mapping_ok=bool(phys==dict(p=255-code,n=code))))
        mask=(t>=a)&(t<=b)
        codes=np.zeros_like(t,dtype=int)
        for bit in range(8):codes+=(w[f"d{bit}"]>.45).astype(int)*(1<<bit)
        observed=sorted(int(x) for x in np.unique(codes[mask]))
        errmax=max((abs(r["error_mv"]) for r in rows),default=float("inf"))
        midpoint={s:sum(int(at(f"xdut.g{s}p{k}",hold-.1)<.45)*(1<<k) for k in range(8)) for s in "pn"}
        passed=(len(rows)==len(ws)==len(us)==8 and all(r["resolved"] and r["sign_agrees"] and
                    r["token_order_ok"] and r["physical_mapping_ok"] for r in rows)
                and observed==[ideal_code] and errmax<LIMIT_MV and midpoint==dict(p=127,n=128))
        frames.append(dict(frame=f+1,hold_start_ns=float(hold),read_window_ns=[a,b],
                           expected_code=ideal_code,observed_codes_in_window=observed,
                           comparison_count=len(cs),write_count=len(ws),update_count=len(us),
                           last_write_ns=float(ws[-1]) if len(ws) else None,
                           high_words_before_hold=midpoint,
                           acquisition_error_before_off_mv=(at("topp",hold-.1)-at("topn",hold-.1)-v)*1e3,
                           post_off_held_error_mv=(at("topp",hold+.5)-at("topn",hold+.5)-v)*1e3,
                           max_compare_error_mv=errmax,comparisons=rows,frame_pass=bool(passed)))

    worst=dict(value_v=-1)
    envelope=np.zeros_like(t)
    gates=[]
    for s in "pn":
        for bit in range(8):
            gp=w[f"xdut.g{s}p{bit}"];gn=w[f"xdut.g{s}n{bit}"]
            bot=w[f"xdut.xcdac.b{s}{bit}"]
            gates.append(dict(bank=s.upper()+str(bit),gate_enables_overlap=bool(np.any((gp<.45)&(gn>.45)))))
            for device,gate,ref,body in (("MP_HIGH",gp,w["vrefp"],w["vdd!"]),
                                        ("MN_LOW",gn,w["vrefn"],np.zeros_like(t))):
                for terminal,value in (("VDS",bot-ref),("VGS",gate-ref),("VGD",gate-bot),
                                        ("VDB",bot-body),("VSB",ref-body),("VGB",gate-body)):
                    envelope=np.maximum(envelope,abs(value));j=int(np.argmax(abs(value)))
                    if abs(value[j])>worst["value_v"]:
                        worst=dict(value_v=float(abs(value[j])),signed_v=float(value[j]),time_ns=float(t[j]),
                                   bank=s.upper()+str(bit),device=device,terminal=terminal)
            ev=[]
            for rail,voltage in (("H",.9-gp),("L",gn)):
                ev += [(float(x),rail,True) for x in edges(t,voltage)]
                ev += [(float(x),rail,False) for x in edges(t,voltage,rising=False)]
            ev.sort()
            last_off=None;gap=[]
            for instant,rail,on in ev:
                if not on:last_off=(instant,rail)
                elif last_off and last_off[1]!=rail:
                    gap.append((instant-last_off[0])*1000)
                    last_off=None
            gates[-1]["opposite_rail_deadtime_ps"]=gap
    gaps=[x for bank in gates for x in bank["opposite_rail_deadtime_ps"]]
    # Source requests remain observable even when safe ideal drives suppress
    # illegal overlap. Never call such suppression native-logic correctness.
    raw_overlap=[]
    for bank in "pn":
        for bit in range(8):
            h=w[f"xdut.b{bank}_h{bit}"];l=w[f"xdut.b{bank}_l{bit}"]
            if np.any((h>.45)&(l>.45)):raw_overlap.append(bank.upper()+str(bit))
    logpath=Path(result["metadata"]["output_dir"]).parent/"spectre.out"
    log=logpath.read_text(errors="replace")
    cmi=re.findall(r"WARNING \(CMI-\d+\):[^\n]*",log)
    suppressed=re.findall(r"(?im)^.*(?:suppressed|\bLTE\b|blowup|convergence failure).*$",log)
    warning_codes={code:len(re.findall(r"WARNING \("+re.escape(code)+r"\)",log))
                   for code in sorted(set(re.findall(r"WARNING \(([^)]+)\)",log)))}
    compstress=None
    if "xdut.xcomp.tail" in w:
        nodes={"VINP":w["topp"],"VINN":w["topn"],"OUTP":w["comp_p"],"OUTN":w["comp_n"],
               "CLK":w["cmp_clk"],"VDD":w["vdd!"],"VSS":np.zeros_like(t),
               **{n:w["xdut.xcomp."+n.lower()] for n in ("X","Y","TAIL")}}
        compstress=dict(value_v=-1)
        source=read_json(OUT/"dependencies/sar_strongarm_t28.json")
        for part in source["instances"]:
            for a,b in (("D","S"),("G","S"),("G","D"),("D","B"),("S","B"),("G","B")):
                values=nodes[part["terms"][a]]-nodes[part["terms"][b]]
                j=int(np.argmax(abs(values)))
                if abs(values[j])>compstress["value_v"]:
                    compstress=dict(value_v=float(abs(values[j])),signed_v=float(values[j]),time_ns=float(t[j]),
                                    instance=part["name"],terminal="V"+a+b,
                                    sample_v=float(w["sample"][j]),cmp_clock_v=float(w["cmp_clk"][j]))
    entry=dict(name=name,result_ok=True,context=ctx,frames=frames,reference_stress=worst,
               minimum_opposite_rail_deadtime_ps=min(gaps) if gaps else None,
               simultaneous_gate_enable_banks=[g["bank"] for g in gates if g["gate_enables_overlap"]],
               raw_both_on_banks=raw_overlap,reference_gate_checks=gates,
               CMI_warning_count=len(cmi),CMI_warnings=cmi,suppression_or_LTE_lines=suppressed,
               warning_codes=warning_codes,
               comparator_stress_from_saved_internal_nodes=compstress,
               deck_sha256=ctx["deck_sha256"],export_sha256=ctx["export_sha256"],
               bounded_join_pass=bool(len(frames)==2 and all(f["frame_pass"] for f in frames)
                    and not raw_overlap and not any(g["gate_enables_overlap"] for g in gates)
                    and gaps and min(gaps)>=99.8 and worst["value_v"]<=.99 and not cmi and not suppressed
                    and (compstress is None or compstress["value_v"]<=.99)))
    entry["top_node_ranges"]={}
    for node in ("topp","topn"):
        j=int(np.argmax(w[node]));k=int(np.argmin(w[node]))
        entry["top_node_ranges"][node]=dict(max_v=float(w[node][j]),max_ns=float(t[j]),min_v=float(w[node][k]),
            min_ns=float(t[k]),sample_at_max_v=float(w["sample"][j]),cmp_clock_at_max_v=float(w["cmp_clk"][j]))
    dump(f"analysis/{name}.json",entry)
    if plot:
        figures(name,t,w,frames,envelope)
        stress_figure(name,t,w,worst)
    return entry


def figures(name,t,w,frames,envelope):
    FIG.mkdir(parents=True,exist_ok=True)
    fig,axes=plt.subplots(5,1,figsize=(11,11),sharex=True)
    colors={"sample":"#3664a5","cmp_clk":"#e09e38"}
    axes[0].plot(t,w["sample"],label="SAMPLE",color=colors["sample"])
    axes[0].plot(t,w["cmp_clk"],label="CMP_CLK",color=colors["cmp_clk"])
    axes[0].set_ylabel("Clock (V)")
    axes[1].plot(t,w["topp"],label="TOPP")
    axes[1].plot(t,w["topn"],label="TOPN")
    axes[1].axhline(.45,color=".5",ls="--",lw=.8,label="VCM = 0.45 V")
    axes[1].set_ylabel("CDAC top (V)")
    axes[2].plot(t,w["comp_p"],label="COMP_P")
    axes[2].plot(t,w["comp_n"],label="COMP_N")
    axes[2].set_ylabel("Decision (V)")
    code=np.zeros_like(t,dtype=int)
    for b in range(8):code+=(w[f"d{b}"]>.45).astype(int)*(1<<b)
    axes[3].step(t,code,where="post",label="Native stored code",color="#257e76")
    axes[3].set_ylabel("Output code")
    axes[4].plot(t,envelope,label="Reference pass-MOS max |terminal pair|",color="#9a568e")
    axes[4].axhline(.99,color="#b64036",ls="--",label="Core model check = 0.99 V")
    axes[4].set_ylabel("Stress (V)")
    for f in frames:
        start=f["hold_start_ns"];end=101.05+100*(f["frame"]-1)
        for ax in axes:
            ax.axvspan(start,min(end,200),color="#e9edf0",alpha=.4)
            ax.axvspan(*f["read_window_ns"],color="#b9ddc4",alpha=.55)
        axes[3].hlines(f["expected_code"],start,min(end,200),colors="#b64036",linestyles="--",
                       label="Expected code" if f["frame"]==1 else None)
    axes[0].plot([],[],lw=7,color="#e9edf0",label="Hold / conversion")
    axes[0].plot([],[],lw=7,color="#b9ddc4",label="Read window")
    for ax in axes:
        ax.grid(alpha=.2);ax.legend(loc="upper right",fontsize=8,ncol=2)
    axes[-1].set_xlabel("Time (ns)");axes[-1].set_xlim(0,200)
    fig.tight_layout();fig.savefig(FIG/f"{name}_timing.png",dpi=160);plt.close(fig)

    fig,axes=plt.subplots(2,1,figsize=(10,6),sharex=True)
    for f in frames:
        rows=f["comparisons"]
        if not rows:continue
        x=[r["compare_ns"]-100*(f["frame"]-1) for r in rows]
        axes[0].plot(x,[r["actual_residual_mv"] for r in rows],"o-",label=f"Frame {f['frame']}: measured")
        axes[0].plot(x,[r["ideal_residual_mv"] for r in rows],"x--",label=f"Frame {f['frame']}: ideal charge equation")
        axes[1].plot(x,[r["error_mv"] for r in rows],"o-",label=f"Frame {f['frame']}")
    axes[0].set_ylabel("Pre-compare residual (mV)")
    axes[1].axhspan(-LIMIT_MV,LIMIT_MV,color="#b9ddc4",alpha=.5,label="±0.25 LSB")
    axes[1].axhline(0,color=".5",lw=.8);axes[1].set_ylabel("Measured − ideal (mV)")
    axes[1].set_xlabel("Time within frame (ns)")
    for ax in axes:ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.tight_layout();fig.savefig(FIG/f"{name}_errors.png",dpi=160);plt.close(fig)


def stress_figure(name,t,w,worst):
    side=worst["bank"][0].lower();bit=int(worst["bank"][1:]);instant=worst["time_ns"]
    gp=w[f"xdut.g{side}p{bit}"];gn=w[f"xdut.g{side}n{bit}"]
    bot=w[f"xdut.xcdac.b{side}{bit}"]
    # Expected bottom voltage is meaningful only while a path is commanded ON.
    expected=np.full_like(t,np.nan)
    expected[gp<.45]=.9;expected[gn>.45]=0
    selected=(t>=instant-.6)&(t<=instant+.6)
    fig,axes=plt.subplots(4,1,figsize=(10,9),sharex=True)
    for node,label in (("sample","SAMPLE"),("xdut.xctrl.phi_w","WRITE"),("xdut.xctrl.phi_u","UPDATE")):
        axes[0].plot(t[selected],w[node][selected],label=label)
    axes[0].set_ylabel("Phase (V)")
    axes[1].plot(t[selected],(.9-gp)[selected],label="High path enable = VDD - GP")
    axes[1].plot(t[selected],gn[selected],label="Low path enable = GN")
    axes[1].set_ylabel("Enable (V)")
    axes[2].plot(t[selected],bot[selected],color="#a8433a",label=worst["bank"]+" bottom")
    axes[2].plot(t[selected],expected[selected],color="#287e76",ls="--",label="Selected nominal rail (blank during BBM)")
    axes[2].axhline(.9,color=".5",ls=":",lw=.7);axes[2].axhline(0,color=".5",ls=":",lw=.7)
    axes[2].set_ylabel("Bottom (V)")
    axes[3].plot(t[selected],w["topp"][selected],label="TOPP")
    axes[3].plot(t[selected],w["topn"][selected],label="TOPN")
    axes[3].axhline(.99,color="#a8433a",ls="--",label="Input VGB check = 0.99 V")
    axes[3].set_ylabel("CDAC top (V)")
    off=(gp>.45)&(gn<.45)
    for ax in axes:
        ax.fill_between(t[selected],0,1,where=off[selected],transform=ax.get_xaxis_transform(),color="#dfe4e8",alpha=.6)
        ax.axvline(instant,color="#a8433a",ls=":",lw=.9)
        ax.legend(fontsize=8,loc="upper right",ncol=2);ax.grid(alpha=.2)
    axes[-1].set_xlabel("Time (ns)")
    axes[-1].set_xlim(instant-.6,instant+.6)
    fig.tight_layout();fig.savefig(FIG/f"{name}_stress.png",dpi=160);plt.close(fig)


def main():
    ap=argparse.ArgumentParser();ap.add_argument("names",nargs="+");ap.add_argument("--no-plots",action="store_true");a=ap.parse_args()
    results=[analyze(name,not a.no_plots) for name in a.names]
    dump("analysis/summary.json",dict(scope="bounded TT nominal joint R1, no PVT/MC/noise",cases=results))
    for r in results:
        print("ANALYSIS",r["name"],"EXEC",r["result_ok"],"JOIN",r["bounded_join_pass"],flush=True)
        for f in r.get("frames",[]):
            print("FRAME",f["frame"],"CODE",f["observed_codes_in_window"],"EXPECTED",f["expected_code"],
                  "CMP",f["comparison_count"],"ERROR_MV",f["max_compare_error_mv"],flush=True)


if __name__=="__main__":main()
