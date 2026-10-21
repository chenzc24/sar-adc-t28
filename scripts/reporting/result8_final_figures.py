"""Curate final-design scientific figures from immutable saved results.

No simulator, bridge, OA, circuit or image-editing calls. Every visible trace
comes from a saved waveform; CM/DM and digital words are explicit algebra.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pickle

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "Obsidian_docs/assets/result8_final"
LSB = 1.8 / 256
LIMIT_MV = LSB * 250
BLUE, GREEN, RED, GRAY = "#2667a1", "#167c80", "#bd4d43", "#64748b"
INPUTS: dict[str, str] = {}
FIGURES: list[dict] = []
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.labelsize": 10, "legend.fontsize": 8.5,
                     "xtick.labelsize": 9, "ytick.labelsize": 9})


def source(path: str) -> Path:
    p = ROOT / path
    INPUTS[path] = hashlib.sha256(p.read_bytes()).hexdigest()
    return p


def read(path: str):
    return json.loads(source(path).read_text(encoding="utf-8"))


def waves(path: str):
    data = read(path)
    n = len(data["time"])
    # Scalar and malformed units metadata are not physical waveforms.
    w = {k.lower(): np.asarray(v, dtype=float) for k, v in data.items()
         if isinstance(v, list) and len(v) == n and k != "units"}
    assert np.all(np.diff(w["time"]) > 0)
    assert all(np.isfinite(v).all() for v in w.values())
    return w


def canvas(title, conditions, modules, auxiliary, ratios, *, height=9):
    fig, axes = plt.subplots(len(ratios), 1, figsize=(12, height), sharex=True,
                             gridspec_kw={"height_ratios": ratios})
    fig.subplots_adjust(left=.135, right=.975, top=.80, bottom=.07, hspace=.28)
    fig.text(.135, .965, title, fontsize=16, weight="bold", va="top")
    for y, line in zip((.925, .892, .859), (conditions, modules, auxiliary)):
        fig.text(.135, y, line, fontsize=9.2, color="#334155", va="top")
    for ax in axes:
        ax.grid(axis="x", alpha=.18)
        ax.grid(axis="y", alpha=.10)
        ax.margins(x=0)
    return fig, axes


def trace(ax, t, y, label, color=BLUE, **kwargs):
    ax.plot(t, y, color=color, lw=1.35, **kwargs)
    ax.set_ylabel(label, rotation=0, ha="right", va="center", labelpad=14)


def digital(ax, t, y, label):
    trace(ax, t, y, label)
    ax.set_ylim(min(-.08, float(np.min(y))-.025),
                max(.98, float(np.max(y))+.025))
    ax.set_yticks([0, .9])
    ax.set_ylabel(label + "\n(V)", rotation=0, ha="right", va="center", labelpad=14)


def rises(t, y, level=.45):
    i = np.flatnonzero((y[:-1] < level) & (y[1:] >= level))
    return t[i] + (level-y[i])*(t[i+1]-t[i])/(y[i+1]-y[i])


def word(w, prefix):
    return sum((w[f"{prefix}{b}"] > .45).astype(int)*(1 << b) for b in range(8))


def save(fig, name, *, sources, scope, metrics):
    DEST.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        target = DEST / f"{name}.{ext}"
        fig.savefig(target, dpi=180, facecolor="white")
        if ext == "svg":
            # Matplotlib emits trailing spaces inside multiline path data.
            # Normalize serialization only; coordinates and geometry are intact.
            target.write_text("\n".join(line.rstrip() for line in
                              target.read_text(encoding="utf-8").splitlines())+"\n",
                              encoding="utf-8")
    plt.close(fig)
    FIGURES.append(dict(file=name+".png", vector=name+".svg", scope=scope,
                        sources=sources, metrics=metrics,
                        sha256=hashlib.sha256((DEST/(name+".png")).read_bytes()).hexdigest()))


def macro():
    base = "output/eight_bit_flat/electrical/"
    assert read(base+"macro8_code_192_result.json")["ok"]
    path = base+"macro8_code_192_waveform.json"
    w = waves(path)
    row = next(r for r in read(base+"summary.json") if r["name"] == "macro8_code_192")
    case = read(base+"macro8_code_192_case.json")
    t = w["time"]*1e9
    keep = (t >= 35) & (t <= 82)
    x = t[keep]
    cm = (w["topp"]+w["topn"])/2
    dm = w["topp"]-w["topn"]
    assert np.allclose(cm+dm/2, w["topp"], rtol=0, atol=1e-14)
    assert np.allclose(cm-dm/2, w["topn"], rtol=0, atol=1e-14)
    fig, ax = canvas("Electrical macro | top-plate voltage and conversion",
        "Spectre 21.1 transient | Ideal VDD = 0.9 V, 27 C | 10 MS/s | Vin,diff = +453.515625 mV",
        "Sampling / reference switches: finite-R ideal | CDAC: ideal flat C, 1.756 pF/side",
        "Comparator: gm/C macro | SAR / clocks: ideal VA / sources | Ref: ideal sources + 50 ohm / 4 pF | Noise / mismatch: off",
        [1.15, 2.0, .60, .60, .60, .60], height=9.8)
    trace(ax[0], x, cm[keep], "Top CM\n(V)", GREEN)
    ax[0].set_ylim(.40,.50)
    ax[0].ticklabel_format(axis="y", style="plain", useOffset=False)
    ax[0].axhline(.45, ls="--", lw=.9, color=GRAY, label="VCM = 0.45 V")
    ax[0].legend(loc="upper right")
    trace(ax[1], x, dm[keep]*1000, "Top DM\n(mV)")
    for j, point in enumerate(row["trace"]):
        ax[1].plot([41+5*j, 46+5*j], [point["residual_v"]*1000]*2,
                   color=GRAY, ls="--", lw=1,
                   label="Charge-conservation target" if j == 0 else None)
    ax[1].legend(loc="upper right")
    for a, key, label in zip(ax[2:],
            ("clk_sample", "cmp_reset", "clk_latch", "valid"),
            ("SAMPLE", "CMP_RESET", "LATCH", "VALID")):
        digital(a, x, w[key][keep], label)
    ax[-1].set(xlim=(35, 82), xlabel="Time (ns)")
    final_code = sum(int(np.interp(81e-9, w["time"], w[f"dout<{b}>"]) > .45)*(1 << b) for b in range(8))
    assert final_code == 192
    save(fig, "01_macro_topplate", sources=[path, base+"macro8_code_192_case.json", base+"summary.json"],
         scope="Final nominal electrical macro, code192; not transistor ADC",
         metrics=dict(input_v=case["vdiff_v"], final_code=final_code,
                      time_window_ns=[35, 82], cm_definition="(TOPP+TOPN)/2", dm_definition="TOPP-TOPN"))


def bootstrap():
    base = "output/eight_bit_flat/bootstrap/"
    assert read(base+"boot8_w1u_only_new_vdp800_result.json")["ok"]
    path = base+"boot8_w1u_only_new_vdp800_waveform.json"
    w = waves(path); t = w["time"]*1e9
    keep = (t >= 240) & (t <= 280); x = t[keep]
    dm = w["topp_new"]-w["topn_new"]
    hold = (t >= 252.15) & (t <= 280)
    assert np.max(abs((dm[hold]-.8)*1000)) < 2, "Held detail would be clipped"
    err = (np.interp(270, t, dm)-.8)*1000
    assert abs(err-(-.126413)) < .0001
    fig, ax = canvas("Sampling | selected 1 um Bootstrap",
        "Spectre 21.1 transient | T28 TT, ideal VDD = 0.9 V, 27 C | Vin,diff = +0.8 V | 50 ohm/input | 40 ns acquisition",
        "Bootstrap: native T28 1.8-V MOS, W/L = 1 um/150 nm, ideal Cboot = 1 pF | CDAC: ideal, 1.756 pF/side",
        "Reference switches / timing: ideal | VREFP/N tied to VCM | Comparator / SAR: disconnected | Noise / mismatch: off",
        [.6, .6, 1.5, 1.2], height=8.0)
    digital(ax[0], x, w["phi"][keep], "SAMPLE")
    digital(ax[1], x, w["base"][keep], "REF_ENABLE")
    trace(ax[2], x, dm[keep]*1000, "Top DM\n(mV)")
    ax[2].axhline(800, color=GRAY, ls="--", lw=.9, label="Target = 800 mV")
    ax[2].legend(loc="lower right")
    trace(ax[3], t[hold], (dm[hold]-.8)*1000, "Held error\n(mV)", GREEN)
    ax[3].axhline(0, color=GRAY, ls="--", lw=.9)
    ax[3].fill_between([252.15,280],-LIMIT_MV,LIMIT_MV,color=GREEN,alpha=.10,label="+/-0.25 LSB")
    ax[3].plot(270, err, "o", color=GREEN, label=f"270 ns: {err:.4f} mV")
    ax[3].set_ylim(-2, 2); ax[3].legend(loc="lower right")
    ax[-1].set(xlim=(240, 280), xlabel="Time (ns); error trace begins after reference handoff")
    save(fig, "02_sampling_selected", sources=[path], scope="Selected1um final five-point sampling fixture, +0.8V representative",
         metrics=dict(held_at_270ns_mv=err, error_trace_window_ns=[252.15,280]))


def capacitors():
    path = "output/cdac8_device/banks/summary_200.json"
    d = read(path); assert d["numruns"] == 200 and d["random_variables"] == 512
    fig, ax = canvas("CDAC | selected MOM array, local mismatch result",
        "Spectre AC 1 MHz + static charge oracle | TT, 27 C, DC cap bias = 0.45 V | 200 arrays, 512 local random units/array",
        "Capacitors: T28 cfmom_2t, Cu = 4.004 fF, 1.025 pF/side | Ideal AC source, 1 V | Static-weight limit: 0.5 LSB",
        "Sampling / reference switches / comparator / SAR / clocks: disconnected | MOS mismatch / transient noise: off",
        [1, 1], height=7.0)
    for a, key, name in zip(ax, ("dnl_abs_max_lsb", "inl_abs_max_lsb"), ("DNL", "INL")):
        values = [r[key] for r in d["rows"]]
        a.hist(values, bins=16, color=GREEN, edgecolor="white")
        a.axvline(max(values), color=RED, ls="--", lw=1,
                  label=f"Worst |{name}| = {max(values):.5f} LSB")
        a.set(ylabel="Arrays"); a.legend(loc="upper right")
        a.set_xlabel(f"Maximum |{name}| per array (LSB)")
    ax[0].tick_params(labelbottom=True)
    ax[-1].set_xlim(0,.12)
    save(fig, "03_mom_result", sources=[path], scope=d["scope"],
         metrics=dict(arrays=200, dnl_worst_lsb=d["dnl_worst_lsb"], inl_worst_lsb=d["inl_worst_lsb"],
                      internal_pass_count=d["internal_pass_count"]))


def comparator():
    path = "output/strongarm8_baseline/waves/det_nom_p.json"
    w = waves(path); t = w["time"]*1e9
    keep = (t >= 4.8) & (t <= 7.2); x = t[keep]-5.01
    row = next(r for r in read("output/strongarm8_baseline/summary/deterministic.json") if r["name"] == "det_nom_p")
    assert row["timing_pass"]
    fig, ax = canvas("Comparator | adopted StrongARM initial dimensions",
        "Spectre 21.1 APS transient | T28 TT, ideal VDD = 0.9 V, 27 C | Vin,diff = +1.7578125 mV | VCM = 0.45 V",
        "Comparator: native 11-MOS StrongARM | Input: ideal DC | Load: ideal 5 fF/output | CLK: ideal source",
        "Bootstrap / CDAC / reference switches / SAR: disconnected | Noise / mismatch: off | Other corners not represented",
        [.6, 1, 1, 1.2], height=8)
    digital(ax[0], x, w["clk"][keep], "CLK")
    trace(ax[1], x, w["outp"][keep], "OUTP\n(V)")
    trace(ax[2], x, w["outn"][keep], "OUTN\n(V)", GREEN)
    for a in ax[1:]:
        a.set_ylim(-.05,.98)
        a.set_yticks([0,.45,.9])
    diff = w["outp"][keep]-w["outn"][keep]
    trace(ax[3], x, diff, "Output DM\n(V)")
    ax[3].axhline(.45, ls="--", color=GRAY, lw=1, label="Decision: VDD/2")
    ax[3].axvline(1.5, ls=":", color=RED, lw=1, label="Deadline: 1.5 ns")
    crossings = rises(t, w["clk"])
    index = int(np.argmin(abs(crossings-5.01)))
    cross = crossings[index]
    mask = (t > cross) & (t < cross+1.5)
    out_cross = rises(t[mask], (w["outp"]-w["outn"])[mask])[0]
    delay = (out_cross-cross)*1000
    assert abs(delay-row["delay_ps"][index]) < .01
    ax[3].plot(delay/1000,.45,"o", color=GREEN, label=f"Decision: {delay:.1f} ps")
    ax[3].legend(loc="lower right"); ax[-1].set(xlim=(-.21,2.19), xlabel="Time after CLK 50% rise (ns)")
    save(fig, "04_comparator_selected", sources=[path,"output/strongarm8_baseline/summary/deterministic.json"],
         scope="Final nominal representative of unchanged initial comparator; PVT/mismatch limits remain", metrics=dict(decision_ps=delay))


def async_logic():
    path = "output/sar8_simple/waves/two_cycles_simple_v2_aps.json"
    assert read("output/sar8_simple/results/two_cycles_simple_v2_aps.json")["ok"]
    w = waves(path); t = w["time"]*1e9
    keep = (t >= 35) & (t <= 80); x=t[keep]
    code=word(w,"d")
    counts={key:len(rises(t[keep],w[key][keep])) for key in ("cmp_clk","xctrl.phi_w","xctrl.phi_u")}
    assert list(counts.values()) == [8,8,8]
    assert int(np.interp(79,t,code)) == 145
    fig, ax = canvas("SAR logic | final local compare-write-update loop",
        "Spectre 21.1 APS transient | T28 TT, ideal VDD = 0.9 V, 27 C | 10 MS/s | Ideal sampled Vin,diff = +0.123 V",
        "SAR / local clocks: native CMOS with ideal RC delays | Sampling / DAC / comparator: behavioral plant",
        "Reference selects: observed digital loads, no physical reference MOS | SAMPLE: ideal | Noise / mismatch: off",
        [.6,.6,.6,.6,1.1], height=8.4)
    for a,key,label in zip(ax,("sample","cmp_clk","xctrl.phi_w","xctrl.phi_u"),
                          ("SAMPLE","CMP_CLK","WRITE","UPDATE")):
        digital(a,x,w[key][keep],label)
    trace(ax[-1],x,code[keep],"SAR word\n(unsigned)")
    ax[-1].axhline(145,color=GRAY,ls="--",lw=1,label="Expected final code = 145")
    ax[-1].legend(loc="lower right");ax[-1].set(xlim=(35,80),ylim=(-5,160),xlabel="Time (ns)")
    save(fig,"05_sar_final_timing",sources=[path],scope="Final simple_v2 native controller, first frame; ideal analog plant",
         metrics=dict(final_code=145,events=counts,time_window_ns=[35,80]))


def integrated():
    base="output/b_sine_period/"
    assert read(base+"result.json")["ok"]
    receipt=read(base+"waveform_receipt.json")
    path=source(base+"waveform.pickle")
    assert INPUTS[base+"waveform.pickle"] == receipt["sha256"]
    with path.open("rb") as stream:
        w={k.lower():np.asarray(v,dtype=float) for k,v in pickle.load(stream).items()}
    t=w["time"]*1e9
    assert len(t)==receipt["points"] and np.all(np.diff(t)>0)
    assert all(np.isfinite(v).all() and len(v)==len(t) for v in w.values())
    summary=read(base+"summary.json"); frame=summary["frames"][4]
    dm=w["topp"]-w["topn"]; cm=(w["topp"]+w["topn"])/2
    code=word(w,"d")
    keep=(t>=435)&(t<=478); x=t[keep]-400
    fig,ax=canvas("Integrated ADC | current R3 + B, main switch 1 um",
        "Spectre 21.1 APS | T28 TT, ideal VDD = 0.9 V, 27 C | 10 MS/s | 500 kHz, +/-0.8 V differential, VCM = 0.45 V",
        "Bootstrap / MOM CDAC / reference pass MOS (3x) / StrongARM / SAR: native | Cboot / logic delays: ideal C / RC",
        "Ref gates / commit / SAMPLE: ideal VA or sources | Input 50 ohm; ref ideal source + 50 ohm / 4 pF per rail | Noise / mismatch: off",
        [1.0,1.8,.55,.55,.55,.55,1.0],height=11)
    trace(ax[0],x,cm[keep],"Top CM\n(V)",GREEN)
    ax[0].axhline(.45,color=GRAY,ls="--",lw=.8,label="VCM=0.45 V");ax[0].legend(loc="upper right")
    trace(ax[1],x,dm[keep]*1000,"Top DM\n(mV)")
    points=frame["comparisons"]
    ax[1].plot([p["time_ns"]-400-.02 for p in points],
               [p["expected_residual_mv"] for p in points],"x",color=RED,ms=5,
               label="Ideal residual at actual comparison")
    ax[1].legend(loc="upper right")
    for a,key,label in zip(ax[2:6],("sample","cmp_clk","xdut.xctrl.phi_w","xdut.xctrl.phi_u"),
                           ("SAMPLE","CMP_CLK","WRITE","UPDATE")):
        digital(a,x,w[key][keep],label)
    trace(ax[-1],x,code[keep],"SAR word\n(unsigned)")
    ax[-1].axhline(frame["ideal_code"],color=GRAY,ls="--",lw=1,label=f"Expected final = {frame['ideal_code']}")
    ax[-1].legend(loc="lower right");ax[-1].set(xlim=(35,78),ylim=(-5,160),xlabel="Time within frame 5 (ns)")
    counts={key:len(rises(t[keep],w[key][keep])) for key in ("cmp_clk","xdut.xctrl.phi_w","xdut.xctrl.phi_u")}
    assert list(counts.values()) == [8,8,8]
    assert int(np.interp(498,t,code))==frame["output_code"]==142
    save(fig,"06_integrated_current",sources=[base+"waveform.pickle",base+"summary.json"],
         scope="Current adopted R3+B1um, frame5; no earlier design/candidate curves",
         metrics=dict(final_code=142,events=counts,held_error_mv=frame["held_error_mv"],
                      time_window_absolute_ns=[435,478],cm_definition="(TOPP+TOPN)/2",dm_definition="TOPP-TOPN"))

    rows=[r for r in summary["frames"] if not r["warmup"]]
    assert len(rows)==20
    sample=np.array([r["sample_ns"] for r in rows]); x=(sample-400)/1000
    held=np.array([np.interp(ns+.6,t,dm) for ns in sample])
    source_values=np.array([np.interp(ns,t,w["vinp_src"]-w["vinn_src"]) for ns in sample])
    error=(held-source_values)*1000
    assert np.max(abs(error-np.array([r["held_error_mv"] for r in rows])))<1e-6
    assert np.count_nonzero(abs(error)>LIMIT_MV)==14
    fig,ax=canvas("Integrated ADC | final baseline continuous-input result",
        "Spectre 21.1 APS | T28 TT, ideal VDD = 0.9 V, 27 C | 500 kHz, +/-0.8 V | 10 MS/s | 4 warm-up + 20 measured frames",
        "Bootstrap (1 um) / MOM CDAC / reference pass MOS (3x) / StrongARM / SAR: native | Cboot / delays: ideal C / RC",
        "Ref gates / commit / SAMPLE: ideal VA or sources | Input 50 ohm; ref ideal source + 50 ohm / 4 pF per rail | Noise / mismatch: off",
        [1.3,1.1,1.1],height=8.2)
    mask=(t>=400)&(t<=2400)
    # Decimate only the smooth ideal sine; all measured points remain explicit.
    idx=np.flatnonzero(mask)[::150]
    ax[0].plot((t[idx]-400)/1000,(w["vinp_src"]-w["vinn_src"])[idx],color=GRAY,lw=1,label="Source input")
    ax[0].plot(x,held,"o",ms=4,color=BLUE,label="Actual held samples")
    ax[0].set_ylabel("Differential\n(V)");ax[0].legend(loc="upper right")
    actual=np.array([r["output_code"] for r in rows]); ideal=np.array([r["ideal_code"] for r in rows])
    ax[1].plot(x,ideal,"x",color=GRAY,label="Ideal code at sample")
    ax[1].plot(x,actual,"o",ms=4,mfc="none",color=BLUE,label="Actual final code")
    ax[1].set_ylabel("Final code\n(unsigned)");ax[1].legend(loc="upper right")
    ax[2].axhspan(-LIMIT_MV,LIMIT_MV,color=GREEN,alpha=.11,label="+/-0.25 LSB budget")
    ax[2].axhline(0,color=GRAY,ls="--",lw=.8)
    ax[2].plot(x,error,"o",ms=4,color=BLUE,label=f"Raw error: max {max(abs(error)):.4f} mV, 14/20 outside")
    ax[2].set(ylabel="Held error\n(mV)",xlabel="Nominal sampling time from observed-period start (us)",xlim=(0,2))
    ax[2].legend(loc="lower center",fontsize=8)
    save(fig,"07_dynamic_current",sources=[base+"waveform.pickle",base+"summary.json"],
         scope="Final adopted1um baseline, 20 sample points; no fit/time correction/candidate curves",
         metrics=dict(peak_raw_held_error_mv=float(max(abs(error))),outside_budget=14,samples=20,
                      continuous_error_curve=False, sampling_reference="SAMPLE50%fall; hold at +0.6ns",
                      final_codes=actual.tolist(),sample_ns=sample.tolist()))


def main():
    macro(); bootstrap(); capacitors(); comparator(); async_logic(); integrated()
    manifest=dict(generator="scripts/reporting/result8_final_figures.py",
                  generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),source_snapshot="53722d8",
                  transformations="CM=(TOPP+TOPN)/2; DM=TOPP-TOPN; unsigned bits thresholdVDD/2; raw samples, no fit correction",
                  input_sha256=INPUTS,figures=FIGURES)
    (DEST/"manifest.json").write_text(json.dumps(manifest,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps([dict(file=f["file"],metrics=f["metrics"]) for f in FIGURES],ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
