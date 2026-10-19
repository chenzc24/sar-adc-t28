"""Summarize saved native-T28 bootstrap runs and draw timing comparisons."""
from pathlib import Path
import json
import re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"output/canvas_bootstrap_t28"
NAMES=("baseline","main_500n","main_320n","main_320n_reset_2u","selected")


def load(name):
    return json.loads((OUT/name).read_text(encoding="utf-8"))


def main():
    series={n:load(n+"_summary.json") for n in NAMES}
    summary={}
    for name,rows in series.items():
        assert all(r["ok"] for r in rows)
        summary[name]={"input_count":len(rows),
            "maximum_absolute_acquisition_error_mv":max(abs(r["acquisition_error_mv"]) for r in rows),
            "maximum_absolute_held_error_mv":max(abs(r["held_error_mv"]) for r in rows)}
    summary["baseline_to_selected_worst_absolute_hold_improvement_percent"]=100*(1-summary["selected"]["maximum_absolute_held_error_mv"]/summary["baseline"]["maximum_absolute_held_error_mv"])
    # Fully differential diagnostic formed from independent single-ended cases.
    selected={r["vin_v"]:r for r in series["selected"]}
    summary["paired_single_ended_differential_error_mv"]={
        "vdiff_0p8":selected[0.85]["held_error_mv"]-selected[0.05]["held_error_mv"],
        "vdiff_0p4":selected[0.65]["held_error_mv"]-selected[0.25]["held_error_mv"],
    }
    warnings=[]
    for name in NAMES:
        for row in series[name]:
            path=Path(row["metadata"]["output_dir"]).parent/"spectre.out"
            text=path.read_text(encoding="utf-8",errors="replace")
            warnings.append({"candidate":name,"vin_v":row["vin_v"],
                "printed_cmi":len(re.findall(r"CMI-\d+",text)),
                "printed_warning_codes":dict((c,len(re.findall(re.escape(c),text))) for c in sorted(set(re.findall(r"(?:SFE|SPECTRE)-\d+",text)))),
                "suppressed_counts":re.findall(r"(\d+) (?:additional )?warnings suppressed",text)})
    (OUT/"warning_inventory.json").write_text(json.dumps(warnings,indent=2),encoding="utf-8")
    # Reconstruct terminal voltages from the saved schematic nets, not node peaks alone.
    sizes=load("selected_sizes.json")
    peaks={}
    for row in series["selected"]:
        w=load(f"selected_v{round(row['vin_v']*1000):03d}_waveform.json")
        t=np.asarray(w["time"])
        assert np.all(np.isfinite(t)) and np.all(np.diff(t)>0)
        assert all(np.all(np.isfinite(v)) for v in w.values())
        node={"gnd!":np.zeros_like(t),"VDD!":np.full_like(t,0.9)}
        node.update({n:np.asarray(w[n]) for n in ("Vin","VOUT","CLKS","CLKSB")})
        node.update({n:np.asarray(w["XBOOT."+n]) for n in ("G","BTOP","BBOT","CTRL","GRESET")})
        for device in sizes["instances"]:
            if device["lib"]!="tsmcN28":continue
            terms=device["terms"]
            for a,b in (("G","S"),("G","D"),("D","S"),("B","S"),("B","D")):
                key=device["name"]+".V"+a+b
                peak=float(np.max(np.abs(node[terms[a]]-node[terms[b]])))
                if peak>peaks.get(key,{}).get("absolute_peak_v",-1):
                    peaks[key]={"absolute_peak_v":peak,"vin_v":row["vin_v"]}
    (OUT/"selected_terminal_peaks.json").write_text(json.dumps(peaks,indent=2),encoding="utf-8")
    summary["maximum_sampled_mos_terminal_difference_v"]=max(x["absolute_peak_v"] for x in peaks.values())
    (OUT/"analysis_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")

    font_manager.fontManager.addfont("C:/Windows/Fonts/msyh.ttc")
    plt.rcParams.update({"font.family":"Microsoft YaHei","font.size":10,"axes.unicode_minus":False})
    fig,axes=plt.subplots(3,1,figsize=(11,9))
    fig.subplots_adjust(left=.105,right=.98,bottom=.08,top=.91,hspace=.43)
    fig.suptitle("T28 原生器件 Bootstrap · VIN = 0.05 V",fontsize=15)
    colors={"baseline":"#7c818c","selected":"#167d77","main_320n":"#ba633f"}
    labels={"baseline":"主采样管 W=1 µm","selected":"选定 W=0.5 µm","main_320n":"W=0.32 µm"}
    for name in colors:
        w=load(f"{name}_v050_waveform.json")
        t=np.asarray(w["time"])*1e9
        v=np.asarray(w["VOUT"])
        mask=(t>=211)&(t<=250)
        axes[0].plot(t[mask],v[mask],color=colors[name],label=labels[name])
        mask=(t>=249.7)&(t<=253)
        axes[2].plot(t[mask],1000*(v[mask]-.05),color=colors[name],label=labels[name])
    axes[0].axhline(.05,color="black",ls="--",lw=1,label="理想采样值 0.05 V")
    axes[0].set(xlim=(211,250),ylabel="VOUT（V）",xlabel="时间（ns）",title="A  采样建立")
    axes[0].legend(frameon=False,fontsize=9)
    w=load("selected_v050_waveform.json")
    t=np.asarray(w["time"])*1e9
    falling=np.flatnonzero((t>249)&(np.asarray(w["CLKS"])<.45))
    clock_mid=t[falling[0]]
    mask=(t>=249.7)&(t<=251.2)
    for signal,color,label in (("CLKS","#7c818c","CLKS"),("CLKSB","#ba633f","CLKSB"),("XBOOT.G","#167d77","主栅 G")):
        axes[1].plot(t[mask],np.asarray(w[signal])[mask],color=color,label=label)
    axes[1].axvline(clock_mid,color="0.5",ls=":",lw=1)
    axes[1].set(xlim=(249.7,251.2),ylabel="电压（V）",xlabel="时间（ns）",title="B  选定版关断时序 · 真实 T28 反相器")
    axes[1].legend(frameon=False,ncol=3)
    axes[2].axhspan(-.439,.439,color="#2d8b64",alpha=.12,label="单端检查范围 ±0.439 mV")
    axes[2].axhline(0,color="black",ls="--",lw=1,label="理想误差 0 mV")
    axes[2].axvline(clock_mid,color="0.5",ls=":",lw=1)
    axes[2].axvspan(250.5,253,color="#386da8",alpha=.035)
    axes[2].text(251.6,.95,"保持观察区",transform=axes[2].get_xaxis_transform(),va="top",ha="center",fontsize=9,color="#386da8")
    axes[2].set(xlim=(249.7,253),ylabel="VOUT − VIN（mV）",xlabel="时间（ns）",title="C  关断扰动与保持平台")
    axes[2].legend(handles=[Patch(facecolor="#2d8b64",alpha=.12,label="单端检查范围 ±0.439 mV"),
                          Line2D([],[],color="black",ls="--",lw=1,label="理想误差 0 mV"),
                          Line2D([],[],color="0.5",ls=":",lw=1,label=f"CLKS 50%：约 {clock_mid:.2f} ns")],
                   frameon=False,fontsize=9,loc="center right")
    for ax in axes:ax.grid(alpha=.17)
    fig.savefig(OUT/"timing_comparison.png",dpi=170)
    plt.close(fig)
    print(json.dumps(summary,indent=2))


if __name__=="__main__":main()
