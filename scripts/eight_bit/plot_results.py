"""Small scientific figures from accepted runs; no illustrative waveforms."""
from __future__ import annotations

import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from common import OUT, LSB, LIMIT, load
from analyze import waves


def save(fig,name):
    path=OUT/"figures"/name;path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path,dpi=160,bbox_inches="tight");plt.close(fig)
    print(path)


def bootstrap(tag):
    _,base=waves("bootstrap","boot8_initial_vdp800")
    _,selected=waves("bootstrap",f"boot8_{tag}_vdp800")
    fig,ax=plt.subplots(3,1,figsize=(11,8),sharex=True)
    t=selected["time"]*1e9
    for key,label in (("phi","Sample clock"),("clkb_p","Native reset clock"),("base","Bottoms to VCM")):
        ax[0].plot(t,selected[key],label=label,lw=1.5)
    ax[0].set(ylabel="Control (V)",title="8-bit flat CDAC: +0.8 V input, 40 ns acquisition")
    for w,variant,label,color in ((base,"new","Native W=0.5 um","#d0503d"),(selected,"new",f"Native {tag}","#167d83"),(selected,"old","Original core (SOA warnings)","#8b78aa")):
        ns=w["time"]*1e9
        err=1e3*(w[f"topp_{variant}"]-w[f"topn_{variant}"]-.8)
        for a in ax[1:]:a.plot(ns,err,label=label,color=color,lw=1.7)
    for a in ax[1:]:
        a.axhline(0,color="black",ls="--",lw=1,label="Ideal held error = 0")
        a.axhspan(-LIMIT*1e3,LIMIT*1e3,color="#63b58a",alpha=.18,label="+/- 0.25 LSB")
        a.set(ylabel="Differential error (mV)")
    ax[1].set(ylim=(-16,2),title="Acquisition tail and held error")
    ax[2].set(ylim=(-2,2),xlabel="Time (ns)",title="Same data: tolerance-scale view")
    for a in ax:
        a.axvspan(252.15,280,color="grey",alpha=.1)
        a.axvline(250.15,color="grey",ls=":",lw=1)
        a.axvline(252.05,color="grey",ls=":",lw=1)
        a.set_xlim(240,280);a.grid(alpha=.22)
    ax[0].text(264,.34,"HOLD / conversion window",ha="center",fontsize=10)
    ax[0].legend(ncol=3,fontsize=9,loc="upper right")
    ax[1].legend(ncol=2,fontsize=8,loc="lower right")
    fig.tight_layout();save(fig,"bootstrap_timing.png")

    fig,ax=plt.subplots(1,2,figsize=(10,3.8),sharex=True)
    for tag_i,label in (("initial","Native W=0.5 um"),(tag,f"Native {tag}")):
        rows=load(f"bootstrap/summary_{tag_i}.json")
        for a,key in zip(ax,("acquisition_error_mv","held_error_mv")):
            a.plot([r["input_v"] for r in rows],[r["NEW"][key] for r in rows],"o-",label=label)
    for a,title in zip(ax,("Acquisition error at 249.9 ns","Held error at 270 ns")):
        a.axhline(0,color="black",ls="--",lw=.8)
        a.axhspan(-LIMIT*1e3,LIMIT*1e3,color="#63b58a",alpha=.18,label="+/- 0.25 LSB")
        a.set(xlabel="Input differential (V)",ylabel="Error (mV)",title=title);a.grid(alpha=.25)
    ax[0].legend(fontsize=8);fig.tight_layout();save(fig,"bootstrap_size_screen.png")


def macro():
    _,w=waves("electrical","macro8_code_192")
    row=next(r for r in load("electrical/summary.json") if r["name"]=="macro8_code_192")
    fig,ax=plt.subplots(3,1,figsize=(11,8),sharex=True)
    ns=w["time"]*1e9
    ax[0].plot(ns,1e3*(w["topp"]-w["topn"]),label="Electrical TOPP - TOPN")
    for j,tr in enumerate(row["trace"]):
        start=41+5*j
        ax[0].plot([start,start+5],[tr["residual_v"]*1e3]*2,"k--",lw=1,label="Charge-conservation target" if j==0 else None)
    ax[0].axhline(0,color="grey",lw=.8);ax[0].set(ylabel="Residual (mV)",title="8-bit electrical macro: input = 0.453515625 V, output code 192")
    for key,ref,label in (("vrefp",.9,"VREFP - 0.9 V"),("vrefn",0,"VREFN - 0 V")):
        ax[1].plot(ns,(w[key]-ref)*1e3,label=label)
    ax[1].axhline(0,color="black",ls="--",lw=.8);ax[1].set(ylabel="Reference error (mV)")
    for key in ("busy","valid","clk_trial","cmp_reset"):
        ax[2].plot(ns,w[key],label=key.upper(),lw=1.2)
    for a in ax:
        a.axvspan(41.02,80.52,color="grey",alpha=.09);a.grid(alpha=.2);a.legend(fontsize=9,loc="upper right")
        a.set_xlim(39,82)
    ax[2].set(xlabel="Time (ns)",ylabel="Control (V)")
    fig.tight_layout();save(fig,"macro_conversion.png")


def main():
    p=argparse.ArgumentParser();p.add_argument("--tag",default="w1u");a=p.parse_args()
    bootstrap(a.tag);macro()


if __name__=="__main__":main()
