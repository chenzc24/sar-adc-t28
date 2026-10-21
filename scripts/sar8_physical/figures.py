"""Small, separated timing plots from verified native records."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from analyze import ROOT, OUT, Q, load, edge

DEST=ROOT/"docs/figures/sar8_physical"
plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False,
                    "figure.dpi":140,"savefig.dpi":180,"axes.grid":True,"grid.alpha":.16})


def unit(old,new):
    fig,ax=plt.subplots(3,1,figsize=(10,7),sharex=True,layout="constrained")
    for name,color,label in ((old,"#ce5748","Gate R: 20 kΩ / 2^bit"),(new,"#267d8a","Gate R: 100 kΩ / 2^bit")):
        folder,r,w=load(name); t=w["time"]*1e9
        gate=w["gnp0"]; bottom=w["xcdac.bn0"]
        ax[0].plot(t,gate,color=color,label=label)
        ax[1].plot(t,bottom,color=color)
        ax[2].plot(t,np.abs(gate-bottom),color=color)
    for a in ax:
        a.set_xlim(44.2,45.3)
    ax[0].axhline(.9,color=".4",ls="--",lw=.8,label="Supply / reference 0.9 V")
    ax[0].set_ylabel("LSB PMOS gate (V)");ax[0].legend(fontsize=9,ncol=2)
    ax[1].axhline(0,color=".4",ls="--",lw=.8);ax[1].axhline(.9,color=".4",ls="--",lw=.8)
    ax[1].set_ylabel("N-side LSB bottom (V)")
    ax[2].axhline(.99,color="#b44343",ls="--",lw=1,label="Core screening line 0.99 V")
    ax[2].set_ylabel("LSB PMOS |Vgd| (V)");ax[2].set_xlabel("Time (ns)");ax[2].legend(fontsize=9)
    fig.suptitle("Native reference-word driver: one LSB handoff",fontsize=14)
    fig.supxlabel("T28 TT · 0.9 V · 27 °C · real 3× reference MOS + MOM array\nUnit bench: top plates externally fixed at 0.45 V; not a complete ADC",fontsize=9)
    DEST.mkdir(parents=True,exist_ok=True);fig.savefig(DEST/"reference_driver.png");plt.close(fig)


def integrated(name):
    folder,r,w=load(name);info=json.loads((folder/"analysis.json").read_text());t=w["time"]*1e9
    fig,ax=plt.subplots(5,1,figsize=(11,10),sharex=True,layout="constrained")
    sample=w["xdut.sample_int"]; compare=w["xdut.cmp_clk"]
    ax[0].plot(t,sample,color="#267d8a",label="Buffered SAMPLE")
    ax[1].plot(t,compare,color="#7a5ca4",label="Comparator clock")
    diff=w["xdut.topp"]-w["xdut.topn"];cm=(w["xdut.topp"]+w["xdut.topn"])/2
    src=w["vinp_src"]-w["vinn_src"]
    target=src.copy()
    ref=sum((w[f"xdut.xref.q{i}"]>.45).astype(int)*2**i for i in range(8))
    rises=edge(t,sample)
    intervals=[]
    for row in info["frames"]:
        fall=row["sample_ns"];next_rise=rises[rises>fall]
        end=float(next_rise[0]) if len(next_rise) else float(t[-1])
        mask=(t>=fall)&(t<end)
        target[mask]=row["held_v"]+.9-ref[mask]*Q
        intervals.append((fall,end,fall+row["conversion_complete_ns"]))
    ax[2].plot(t,diff,color="#267d8a",label="Top-plate differential")
    ax[2].plot(t,target,color=".4",ls="--",lw=1,label="Zero-settling charge target; input while sampling")
    ax[3].plot(t,cm,color="#5f8a55",label="Top-plate common-mode")
    ax[3].axhline(.45,color=".4",ls="--",lw=1,label="Nominal input VCM")
    code=sum((w[f"d{i}"]>.45).astype(int)*2**i for i in range(8))
    ideal=np.clip(np.floor((src+.9)/Q),0,255)
    ax[4].step(t,code,where="post",color="#267d8a",label="Actual SAR register (valid after conversion)")
    ax[4].step(t,ideal,where="post",color=".4",ls="--",label="Ideal code of current source")
    for row,(fall,end,complete) in zip(info["frames"],intervals):
        for a in ax:
            a.axvspan(fall,end,color="#dfead8",alpha=.4,zorder=0)
            a.axvspan(fall,complete,color="#acd09b",alpha=.24,zorder=0)
        ax[4].plot(100*row["frame"]+98,row["code"],"o",color="#ce5748",ms=5)
    for a in ax:a.legend(loc="lower left",bbox_to_anchor=(0,1.02),borderaxespad=0,fontsize=8,ncol=2)
    for a,label in zip(ax,["SAMPLE (V)","CMP CLK (V)","Top differential (V)","Top VCM (V)","Output code"]):a.set_ylabel(label)
    ax[4].set_xlabel("Time (ns); green = HOLD, darker = conversion, red dots = final 98 ns readout")
    ax[-1].set_xlim(0,float(t[-1]))
    fig.suptitle("R4 native transistor/device-level ADC",fontsize=15)
    fig.supxlabel("T28 TT · 0.9 V · 27 °C · 10 MS/s · real Bootstrap / CDAC / StrongARM / SAR / reference control\nExternal ideal sources: supply, references, input, SAMPLE; input/reference 50 Ω, reference decoupling 4 pF/rail",fontsize=9)
    DEST.mkdir(parents=True,exist_ok=True);fig.savefig(DEST/(name+".png"));plt.close(fig)


def two_phase(name):
    folder,r,w=load(name);t=w["time"]*1e9
    info=json.loads((folder/"analysis.json").read_text())
    complete="xdut.sample_int" in w
    prefix="xdut." if complete else ""
    first=next(x for x in info["two_phase_reference_steps"] if 140<x["update_ns"]<160) if complete else info["two_phase_checks"][0]
    initial=first["previous"] if complete else first["previous_expected"]
    committed=first["committed"] if complete else first["commit_expected"]
    trial=first["trial"] if complete else first["target_expected"]
    fig,ax=plt.subplots(4,1,figsize=(10,7),sharex=True,layout="constrained")
    ax[0].plot(t,w[prefix+"phi_u"],color="#7a5ca4",label="Actual UPDATE")
    ax[1].plot(t,w[prefix+"xref.cap_clk"],color="#267d8a",label="Real capture clock: commit, then next trial")
    q=sum((w[f"{prefix}xref.q{i}"]>.45).astype(int)*2**i for i in range(8))
    expected=np.full(len(t),initial)
    expected[t>=first["first_clock_ns"]]=committed
    expected[t>=first["late_clock_ns"]]=trial
    ax[2].step(t,q,where="post",color="#267d8a",label="Stored reference word")
    ax[2].step(t,expected,where="post",color=".4",ls="--",label=f"Zero-delay target: {initial} → committed {committed} → trial {trial}")
    ax[3].plot(t,w[prefix+"xcdac.bn7"],color="#267d8a",label="N MSB bottom (first handoff)")
    ax[3].plot(t,w[prefix+"xcdac.bn6"],color="#b77b35",label="N bit6 bottom (later handoff)")
    ax[3].axhline(0,color=".4",ls="--",lw=.8);ax[3].axhline(.9,color=".4",ls="--",lw=.8)
    for a,label in zip(ax,["UPDATE (V)","Capture CLK (V)","Reference word","Bottoms (V)"]):
        a.set_ylabel(label);a.set_xlim(first["update_ns"]-.15,first["update_ns"]+1.95)
        a.legend(loc="lower left",bbox_to_anchor=(0,1.02),borderaxespad=0,fontsize=8,ncol=2)
    ax[-1].set_xlabel("Time (ns)")
    fig.suptitle("Native reference control: decided word before next trial",fontsize=14)
    condition="Complete native ADC; floating top plates, input differential −0.8 V, VCM 0.45 V." if complete else "Loaded unit bench; top plates externally fixed at 0.45 V; arbitrary-word truth test."
    fig.supxlabel("T28 TT · 0.9 V · 27 °C · CMOS DFF/SR/buffers + PDK RC + 3× reference MOS + MOM\n"+condition,fontsize=9)
    DEST.mkdir(parents=True,exist_ok=True);fig.savefig(DEST/"reference_two_phase.png");plt.close(fig)


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("name");p.add_argument("--old");p.add_argument("--two-phase",action="store_true");a=p.parse_args()
    two_phase(a.name) if a.two_phase else unit(a.old,a.name) if a.old else integrated(a.name)
