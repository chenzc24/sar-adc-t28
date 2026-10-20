"""Scientific plots from recorded Spectre results, not drawing synthesis."""
from pathlib import Path
import json
import math
import statistics
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"output/strongarm8_baseline"
FIG=ROOT/"docs/figures/strongarm8"
FIG.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({"font.size":10,"figure.dpi":150,"savefig.bbox":"tight"})


def read(path):return json.loads((OUT/path).read_text())


def timing():
    fig,ax=plt.subplots(3,1,figsize=(10,7),sharex=True,layout="constrained")
    for name,label,color in (("det_nom_p","TT / 0.9 V / 5 fF","#287e83"),
                             ("det_ss_cold_p","SS / 0.81 V / -40 C / 20 fF","#c34d42")):
        w=read(f"waves/{name}.json");t=np.asarray(w["time"])*1e9;mask=(t>=4.8)&(t<=7.2)
        t=t[mask]-5.01;p=np.asarray(w["outp"])[mask];n=np.asarray(w["outn"])[mask]
        ax[0].plot(t,np.asarray(w["clk"])[mask],label=label,color=color)
        ax[1].plot(t,p-n,label=label,color=color)
        ax[2].plot(t,np.asarray(w["xcmp.x"])[mask]-np.asarray(w["xcmp.y"])[mask],label=label,color=color)
    ax[0].set_ylabel("CLK (V)");ax[1].set_ylabel("OUTP - OUTN (V)");ax[2].set_ylabel("X - Y (V)")
    ax[1].axhline(.45,ls="--",color="#287e83",lw=1,label="TT decision threshold: VDD/2")
    ax[1].axhline(.405,ls=":",color="#c34d42",lw=1,label="SS threshold: VDD/2")
    for a in ax:a.axvline(1.5,ls="--",color="gray",label="1.5 ns deadline" if a is ax[0] else None);a.grid(alpha=.2)
    ax[0].legend(fontsize=8,ncol=2);ax[1].legend(fontsize=8,ncol=2,loc="lower right")
    ax[2].set_xlabel("Time after CLK midpoint (ns)")
    fig.suptitle("Unchanged T28 StrongARM: +0.25 LSB (1.758 mV), no noise/mismatch")
    fig.savefig(FIG/"decision_timing.png");plt.close(fig)


def pvt():
    rows=read("summary/deterministic.json");grid=np.zeros((9,3));labels=[];texts={}
    for i,(co,sup) in enumerate((co,sup) for co in ("tt","ss","ff") for sup in (.81,.9,.99)):
        labels.append(f"{co.upper()} / {sup:.2f} V")
        for j,temp in enumerate((-40,27,125)):
            r=[r for r in rows if r["name"].startswith("det_pvt_") and r["corner"]==co and r["supply_v"]==sup and r["temperature_c"]==temp]
            if len(r)!=2:grid[i,j]=np.nan;texts[i,j]="pending";continue
            fail=any(not x["timing_pass"] for x in r)
            value=max(d for x in r for d in x["delay_ps"] if d is not None) if not fail else 1600
            grid[i,j]=value;texts[i,j]=">1500" if fail else f"{value:.0f}"
            if any(x["stress"]["cmi_printed"] for x in r):texts[i,j]+=" *"
    fig,ax=plt.subplots(figsize=(7,6),layout="constrained")
    im=ax.imshow(grid,cmap="YlOrRd",vmin=0,vmax=1600,aspect="auto")
    for (i,j),text in texts.items():ax.text(j,i,text,ha="center",va="center",color="white" if grid[i,j]>1100 else "black")
    ax.set(xticks=range(3),xticklabels=["-40 C","27 C","125 C"],yticks=range(9),yticklabels=labels,
           title="Worst signed decision delay (ps), +/-0.25 LSB, 20 fF\n* terminal stress warnings (independent failure)")
    fig.colorbar(im,ax=ax,label="Decision delay (ps)");fig.savefig(FIG/"pvt_timing.png");plt.close(fig)


def noise():
    n=read("summary/noise.json")
    if not n["fits"]:return
    fig,ax=plt.subplots(figsize=(8,4.8),layout="constrained");norm=statistics.NormalDist()
    for f,fit in n["fits"].items():
        points=[r for r in n["rows"] if str(r["fmax_hz"])==f]
        x=np.asarray(sorted(set(r["differential_v"] for r in points)))
        y=[sum(r["positive"] for r in points if r["differential_v"]==v)/sum(r["cycles"] for r in points if r["differential_v"]==v) for v in x]
        ax.plot(x*1000,y,"o",label=f"Spectre {float(f)/1e9:g} GHz")
        fit=fit["pooled"];g=np.linspace(-3,3,201)
        ax.plot(g,[norm.cdf((v/1000-fit["threshold_v"])/fit["sigma_v"]) for v in g],label=f"fit sigma={fit['sigma_v']*1000:.3f} mV")
    x=np.linspace(-3,3,201);sigma=.001265625
    ax.plot(x,[norm.cdf(v/1000/sigma) for v in x],"--",color="gray",label="Allocation: sigma=1.266 mV")
    ax.axhline(.5,color="gray",lw=.7);ax.grid(alpha=.2);ax.legend(fontsize=9)
    ax.set(xlabel="Input differential (mV)",ylabel="P(OUTP > OUTN) at 1.5 ns",ylim=(-.02,1.02),title="Physical transient noise: unchanged nominal comparator")
    fig.savefig(FIG/"noise_cdf.png");plt.close(fig)


def offset():
    path=OUT/"summary/mc_binary_128.json"
    if not path.exists():return
    data=json.loads(path.read_text());v=[r["ascending"]["midpoint_v"]*1000 for r in data["rows"] if r["ascending"]["midpoint_v"] is not None]
    fig,ax=plt.subplots(figsize=(8,4.8),layout="constrained")
    ax.hist(v,bins=np.arange(math.floor(min(v))-1,math.ceil(max(v))+1.5,1),color="#287e83",edgecolor="white",label="Local mismatch; threshold bracket midpoints")
    ax.axvspan(-1.7578125,1.7578125,color="#71b174",alpha=.2,label="+/-1.758 mV comparison guard")
    ax.axvline(0,color="gray",ls="--",lw=1);ax.legend(fontsize=8);ax.grid(axis="y",alpha=.2)
    ax.set(xlabel="Input-referred decision threshold (mV)",ylabel="Draws",title=f"{len(v)} draws; approximate sigma={data['midpoint_sigma_v']*1000:.3f} mV; 0.25 mV grid")
    fig.savefig(FIG/"offset_distribution.png");plt.close(fig)


def kickback():
    path=OUT/"summary/cdac.json"
    if not path.exists():return
    rows=json.loads(path.read_text())
    if not rows:return
    row=next((r for r in rows if r["differential_v"]>0),rows[0]);name=row["name"];on=read(f"waves/{name}.json");off=read(f"waves/{name[:-2]}off.json")
    t=np.asarray(on["time"]);mask=(t>=45.8e-9)&(t<=48e-9);t=t[mask]
    d=np.asarray(on["topp"])-np.asarray(on["topn"]);d=d[mask]
    od=np.asarray(off["topp"])-np.asarray(off["topn"]);delta=d-np.interp(t,off["time"],od)
    fig,ax=plt.subplots(3,1,figsize=(10,7),sharex=True,layout="constrained")
    ax[0].plot(t*1e9,np.asarray(on["cmp_test"])[mask],label="Comparator CLK");ax[0].set_ylabel("CLK (V)")
    ax[1].plot(t*1e9,d*1000,label="Comparator enabled");ax[1].plot(t*1e9,np.interp(t,off["time"],od)*1000,"--",label="Clock disabled")
    ax[1].axhline(row["differential_v"]*1000,color="gray",ls=":",label="Applied input");ax[1].set_ylabel("TOPP - TOPN (mV)");ax[1].legend(fontsize=8)
    ax[2].plot(t*1e9,delta*1000,label="Enabled minus disabled");ax[2].axhline(0,color="gray",ls="--",label="Ideal: no disturbance")
    ax[2].set(ylabel="Differential disturbance (mV)",xlabel="Time (ns)");ax[2].legend(fontsize=8)
    decision=46.01+row["samples"][0]["decision_delay_ps"]/1000
    for a in ax:
        a.axvline(decision,color="#c34d42",ls="--",lw=1,label="Output reaches VDD/2" if a is ax[0] else None)
        a.axvline(47.51,color="gray",ls=":",label="1.5 ns deadline" if a is ax[0] else None);a.grid(alpha=.2)
    ax[0].legend(fontsize=8,ncol=3)
    fig.suptitle("Native current CDAC interface; first decision; fixed midpoint code")
    fig.savefig(FIG/"cdac_kickback.png");plt.close(fig)


if __name__=="__main__":
    timing();pvt();noise();offset();kickback()
