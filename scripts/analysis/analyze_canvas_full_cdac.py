"""Analyze saved matched full-CDAC runs; plot raw, uncalibrated errors."""
from __future__ import annotations

import itertools
import argparse
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/canvas_full_cdac"
COLORS = {"OLD":"#ca5146", "NEW":"#16867f"}
LABELS = {"OLD":"Original Bootstrap", "NEW":"Canvas, Wmain = 0.5 um"}
LIMIT_MV = 0.439


def load(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def dump(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def rising(time, values, low=249.0, high=253.0, threshold=0.45):
    indices = np.flatnonzero((time[:-1] >= low) & (time[1:] <= high)
                            & (values[:-1] <= threshold) & (values[1:] > threshold))
    return [float(np.interp(threshold, values[i:i + 2], time[i:i + 2])) for i in indices]


def analyze(stem):
    row = load(stem + "_result.json")
    assert row["ok"], row["errors"]
    waves = {k:np.asarray(v, dtype=float) for k,v in load(stem + "_waveform.json").items()}
    time = waves["time"] * 1e9
    assert len(time) > 25000 and np.isfinite(time).all() and (np.diff(time) > 0).all()
    assert abs(time[-1] - 285.0) < 1e-6, "Truncated transient waveform"
    assert all(len(v) == len(time) and np.isfinite(v).all() for v in waves.values())
    at = lambda n, ns: float(np.interp(ns, time, waves[n]))
    row["control_edges_ns"] = {n:rising(time, waves[n]) for n in ("PHIB", "CLKB_P", "CLKB_N", "BASE")}
    phi_edges = rising(time, -waves["PHI"], threshold=-0.45)
    row["control_edges_ns"]["PHI_fall"] = phi_edges
    assert len(phi_edges) == 1 and 250.1 < phi_edges[0] < 250.2
    if row["tag"] == "matched_reset":
        assert abs(row["control_edges_ns"]["PHIB"][0] - row["control_edges_ns"]["CLKB_P"][0]) < 0.001
    else:
        assert 251.1 < row["control_edges_ns"]["PHIB"][0] < 251.2
    assert 252.0 < row["control_edges_ns"]["BASE"][0] < 252.1
    vd = row["vdiff_v"]
    checkpoints = (249.9, 250.18, 250.5, 251.0, 251.3, 251.8, 252.0, 252.4, 252.5, 253.0, 260.0, 270.0, 280.0)
    for variant in (("NEW",) if row.get("candidate_only_diagnostic") else ("OLD", "NEW")):
        delta = waves[f"TOPP_{variant}"] - waves[f"TOPN_{variant}"]
        error = 1000 * (delta - vd)
        active_hold = (time >= 260) & (time <= 280)
        row[variant].update({
            "pass_held_0p439mv":abs(row[variant]["held_error_mv"]) < LIMIT_MV,
            "hold_error_peak_to_peak_260_280_mv":float(np.ptp(error[active_hold])),
            "hold_common_mode_270_v":0.5 * (at(f"TOPP_{variant}", 270) + at(f"TOPN_{variant}", 270)),
            "single_ended_held_error_mv":{s:1000 * (at(f"TOP{s}_{variant}", 270) - (0.45 + (1 if s == "P" else -1) * vd / 2)) for s in ("P", "N")},
            "main_drain_current_270_ua":{s:1e6 * at(f"X{variant}_{s}.{'MN11' if variant == 'OLD' else 'Mmain'}:1", 270) for s in ("P", "N")},
            "checkpoint_errors_mv":{str(ns):float(np.interp(ns, time, error)) for ns in checkpoints},
        })
        acq = (time >= 211.2) & (time <= 249.9)
        bad = time[acq & (np.abs(error) > LIMIT_MV)]
        row[variant]["last_outside_acq_band_ns"] = float(bad[-1]) if len(bad) else None
        readback = load("sar_bootstrap_before.json" if variant == "OLD" else "candidate_readback.json")
        peaks = []
        for instance in readback["instances"]:
            if instance["lib"] != "tsmcN28":
                continue
            for side in ("P", "N"):
                terminal = {}
                for pin, net in instance["terms"].items():
                    if net in ("gnd!", "0", "VSS"):
                        values = np.zeros_like(time)
                    elif net in ("VDD!", "VDD"):
                        values = waves["VDD!"]
                    elif net in ("Vin", "VIN"):
                        values = waves[f"VIN{side}_{variant}"]
                    elif net == "VOUT":
                        values = waves[f"TOP{side}_{variant}"]
                    elif net in ("PHI", "CLKS"):
                        values = waves["PHI"]
                    elif net == "PHIB":
                        values = waves["PHIB"]
                    elif net == "CLKSB":
                        values = waves[f"CLKB_{side}"]
                    else:
                        values = waves[f"X{variant}_{side}.{net}"]
                    terminal[pin] = values
                for a,b in itertools.combinations(("D", "G", "S", "B"), 2):
                    diff = np.abs(terminal[a] - terminal[b])
                    idx = int(np.argmax(diff))
                    peaks.append({"instance":f"X{variant}_{side}.{instance['name']}", "pair":a+b,
                                  "peak_v":float(diff[idx]), "time_ns":float(time[idx])})
        row[variant]["sampled_terminal_peaks"] = sorted(peaks, key=lambda p:p["peak_v"], reverse=True)[:8]
    log_path = Path(row["metadata"]["output_dir"])
    log_path = log_path.parent / "spectre.out" if log_path.suffix == ".raw" else log_path / "spectre.out"
    if not log_path.exists():
        options = list((OUT / "spectre").glob(stem + "__*/spectre.out"))
        assert len(options) == 1, options
        log_path = options[0]
    log = log_path.read_text(encoding="utf-8", errors="replace")
    row["warnings"] = {
        "log_path":str(log_path),
        "cmi_count":len(re.findall(r"WARNING \(CMI-\d+\)", log)),
        "cmi_instances":sorted(set(re.findall(r"WARNING \(CMI-\d+\): ([^:]+):", log))),
        "sfe_1131_count":log.count("SFE-1131"),
        "suppressed_count":sum(map(int, re.findall(r"(\d+) warnings suppressed", log))),
        "warning_lines":[s.strip() for s in log.splitlines() if "WARNING (" in s],
    }
    dump(stem + "_metrics.json", row)
    return row, waves


def style(ax):
    ax.grid(alpha=0.18)
    ax.spines[["top", "right"]].set_visible(False)


def figures(rows, extreme):
    plt.rcParams.update({"font.size":11, "axes.titlesize":12, "figure.dpi":140})
    fig, ax = plt.subplots(figsize=(9, 4.5), layout="constrained")
    ax.axhspan(-LIMIT_MV, LIMIT_MV, color="#60a86c", alpha=0.12, label="Target: +/-0.439 mV")
    ax.axhline(0, c="black", lw=1, ls="--", label="Ideal error = 0")
    for variant in ("OLD", "NEW"):
        ax.plot([r["vdiff_v"] for r in rows], [r[variant]["held_error_mv"] for r in rows],
                "o-", color=COLORS[variant], label=LABELS[variant], lw=2)
    ax.set(xlabel="Differential input (V)", ylabel="Held differential error at 270 ns (mV)",
           title="Same full 5+5 CDAC | TT, 0.9 V, 27 C, 50 ohm / side")
    style(ax)
    ax.legend(fontsize=9)
    fig.savefig(OUT / "held_error_comparison.png")
    plt.close(fig)

    wave = extreme
    time = wave["time"] * 1e9
    fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True, layout="constrained", height_ratios=[1, 1.3, 1.3])
    fig.suptitle("Full-CDAC top-plate sampling | Vdiff = +0.8 V")
    control = axes[0]
    for name, color, ls in (("PHI", "#364f78", "-"), ("PHIB", COLORS["OLD"], "--"),
                             ("CLKB_P", COLORS["NEW"], "-"), ("BASE", "#9864a0", ":")):
        control.plot(time, wave[name], color=color, ls=ls, label={"PHI":"Sample clock", "PHIB":"Original reset", "CLKB_P":"Canvas reset (P)", "BASE":"CDAC reference"}[name])
    control.set(ylabel="Controls (V)", ylim=(-0.08, 1.05))
    control.legend(ncol=4, fontsize=9, loc="upper left")
    axes[1].axhline(0.8, color="black", ls="--", lw=1, label="Ideal held differential = 0.8 V")
    axes[2].axhspan(-LIMIT_MV, LIMIT_MV, color="#60a86c", alpha=.13, label="Target: +/-0.439 mV")
    axes[2].axhline(0, color="black", ls="--", lw=1, label="Ideal error = 0")
    for variant in ("OLD", "NEW"):
        diff = wave[f"TOPP_{variant}"] - wave[f"TOPN_{variant}"]
        axes[1].plot(time, diff, c=COLORS[variant], lw=2, label=LABELS[variant])
        error = 1000 * (diff - 0.8)
        # The full voltage panel retains the floating-node excursion. Do not
        # connect a clipped mV curve across that physically different phase.
        view = np.where((error > -3) & (error < 2), error, np.nan)
        axes[2].plot(time, view, c=COLORS[variant], lw=2, label=LABELS[variant])
    axes[1].set(ylabel="TOPP - TOPN (V)", ylim=(0.35, 0.85))
    axes[2].set(ylabel="Differential error (mV)", xlabel="Time (ns)", ylim=(-3, 2), xlim=(249, 256))
    axes[1].legend(fontsize=9, loc="best")
    axes[2].legend(fontsize=9, ncol=2, loc="lower left")
    for ax in axes:
        ax.axvline(250.15, c="gray", ls=":", lw=1)
        ax.axvline(252.05, c="gray", ls=":", lw=1)
        ax.axvspan(250.15, 252.5, facecolor="#dddddd", alpha=.25)
        ax.axvspan(252.5, 280, facecolor="#16867f", alpha=.05)
        style(ax)
    axes[0].text(251.3, .5, "Handoff", fontsize=9)
    axes[0].text(253.4, .5, "Settled hold", fontsize=10, color=COLORS["NEW"])
    axes[2].set_title("mV zoom (out-of-range excursions omitted; see voltage panel)", fontsize=10, loc="left")
    fig.savefig(OUT / "turnoff_timing.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 3.8), layout="constrained")
    ax.axhspan(-LIMIT_MV, LIMIT_MV, color="#60a86c", alpha=.12, label="Target: +/-0.439 mV")
    ax.axhline(0, c="black", lw=1, ls="--", label="Ideal error = 0")
    for variant in ("OLD", "NEW"):
        err = 1000 * (wave[f"TOPP_{variant}"] - wave[f"TOPN_{variant}"] - .8)
        ax.plot(time, err, color=COLORS[variant], label=LABELS[variant], lw=2)
        value = np.interp(270, time, err)
        ax.plot(270, value, "o", c=COLORS[variant])
        ax.annotate(f"{value:+.4f} mV", (270, value), xytext=(8, 10), textcoords="offset points", color=COLORS[variant])
    ax.set(xlim=(252.5, 280), ylim=(-1.8, 0.55), xlabel="Time (ns)", ylabel="Held differential error (mV)", title="Settled hold | Vdiff = +0.8 V")
    style(ax)
    ax.legend(fontsize=9, loc="best")
    fig.savefig(OUT / "hold_timing.png")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stem")
    args = parser.parse_args()
    if args.stem:
        row, _ = analyze(args.stem)
        print(json.dumps({"edges_ns":row["control_edges_ns"], "old":row.get("OLD"), "new":row["NEW"], "warnings":row["warnings"]}, indent=2))
        return
    rows = []
    extreme = None
    for vd in (-800, -400, 0, 400, 800):
        row, wave = analyze(f"nominal_vd{'m' if vd < 0 else 'p'}{abs(vd):03d}")
        rows.append(row)
        if vd == 800:
            extreme = wave
    summary = {"rows":rows, "worst_held_error_mv":{v:max(abs(r[v]["held_error_mv"]) for r in rows) for v in ("OLD", "NEW")},
               "worst_acquisition_error_mv":{v:max(abs(r[v]["acquisition_error_mv"]) for r in rows) for v in ("OLD", "NEW")}}
    for path in sorted(OUT.glob("tight*_result.json")):
        row, _ = analyze(path.stem.removesuffix("_result"))
        summary.setdefault("tight_rows", []).append(row)
    for path in sorted(OUT.glob("candidate_only*_result.json")):
        row, _ = analyze(path.stem.removesuffix("_result"))
        summary.setdefault("candidate_only_rows", []).append(row)
    for path in sorted(OUT.glob("matched_reset*_result.json")):
        row, _ = analyze(path.stem.removesuffix("_result"))
        summary.setdefault("matched_reset_rows", []).append(row)
    validation = {}
    for key in ("tight_rows", "candidate_only_rows", "matched_reset_rows"):
        for diagnostic in summary.get(key, []):
            nominal = next(r for r in rows if r["vdiff_v"] == diagnostic["vdiff_v"])
            for variant in ("OLD", "NEW"):
                if variant not in diagnostic:
                    continue
                change = abs(diagnostic[variant]["held_error_mv"] - nominal[variant]["held_error_mv"])
                validation[f"{diagnostic['tag']}_{diagnostic['vdiff_v']}_{variant}_held_change_mv"] = change
                if key != "matched_reset_rows":
                    assert change < 0.001, "Diagnostic held-error agreement must be within 1 uV"
            if key == "candidate_only_rows":
                assert diagnostic["warnings"]["cmi_count"] == 0 and diagnostic["warnings"]["suppressed_count"] == 0
    summary["validation"] = validation
    manifest = yaml.safe_load((ROOT / "virtuoso/cell_manifest.yaml").read_text(encoding="utf-8"))
    assert manifest["library"] == "SAR_ADC_T28"
    assert {"sar_bootstrap_canvas_cdac_t28", "tb_bootstrap_canvas_full_cdac"} <= manifest["cells"].keys()
    summary["simulation_count"] = len(rows) + sum(len(summary.get(k, [])) for k in ("tight_rows", "candidate_only_rows", "matched_reset_rows"))
    dump("analysis_summary.json", summary)
    figures(rows, extreme)
    print(json.dumps({k:v for k,v in summary.items() if not k.endswith("rows")}, indent=2))


if __name__ == "__main__":
    main()
