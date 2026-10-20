"""Small scientific timing figures from raw native Spectre traces."""
from __future__ import annotations

import argparse
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from analyze import load
from oa import ROOT, OUT

FIG = ROOT / "docs/figures/sar8_simple"


def decode(data, prefix, level):
    return sum((1 << bit) * (data[(prefix + str(bit)).lower()] > level).astype(int) for bit in range(8))


def envelope(t, v, lo, hi, bins=1800):
    # First/min/max/last PER BIN, never average away a short excursion.
    indices = np.flatnonzero((t >= lo) & (t <= hi))
    if len(indices) < 4 * bins:
        return t[indices], v[indices]
    bucket = np.minimum(bins - 1, ((t[indices] - lo) * bins / (hi - lo)).astype(int))
    starts = np.r_[0, np.flatnonzero(np.diff(bucket)) + 1]; stops = np.r_[starts[1:], len(indices)]
    keep = []
    for a, b in zip(starts, stops):
        seg = indices[a:b]
        keep.extend((seg[0], seg[v[seg].argmin()], seg[v[seg].argmax()], seg[-1]))
    keep = np.unique(keep)
    return t[keep], v[keep]


def save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / (name + ".png"), dpi=160)
    vector = FIG / (name + ".svg")
    fig.savefig(vector)
    # Matplotlib emits spaces at SVG path line endings; normalize formatting
    # only, without modifying coordinates or waveform samples.
    vector.write_text("\n".join(line.rstrip() for line in vector.read_text(encoding="utf-8").splitlines()) + "\n", encoding="utf-8")
    plt.close(fig)


def axes(count, title):
    fig, rows = plt.subplots(count, 1, figsize=(11.5, 1.35 * count + 1.0), sharex=True, layout="constrained")
    fig.suptitle(title, fontsize=13)
    for ax in rows:
        ax.grid(alpha=.22); ax.tick_params(labelsize=9)
    rows[-1].set_xlabel("Time (ns)")
    return fig, rows


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--name", default="two_cycles_simple_v2_aps"); args = ap.parse_args()
    record, context, data, digest = load(args.name)
    t = data["time"] * 1e9; level = context["supply_v"] / 2
    summary = json.loads((OUT / "analysis" / (args.name + ".json")).read_text(encoding="utf-8"))
    fig, rows = axes(6, "Simplified asynchronous SAR | native controller, ideal ADC plant")
    for ax, net, label in zip(rows[:4], ["sample", "cmp_clk", "xctrl.phi_w", "xctrl.phi_u"],
                              ["SAMPLE (V)", "Comparator clock (V)", "Write clock (V)", "Update clock (V)"]):
        x, y = envelope(t, data[net], 0, 202)
        ax.plot(x, y, lw=1.0); ax.set_ylabel(label, fontsize=9)
        ax.set_ylim(min(-.035, float(data[net].min()) - .01), max(.94, float(data[net].max()) + .01))
    token, word = decode(data, "xctrl.t", level), decode(data, "d", level)
    rows[4].plot(t, token, lw=1); rows[4].set_ylabel("Bit token\n(integer)", fontsize=9)
    rows[5].plot(t, word, lw=1); rows[5].set_ylabel("SAR word\n(integer)", fontsize=9)
    for row in summary["frames"]:
        if row["writes"] == 8:
            when = row["write_ns"][-1]
            rows[5].annotate(str(row["word_at_read"]), (when + .15, row["word_at_read"]),
                             xytext=(10, -14), textcoords="offset points", fontsize=10)
    for ax in rows:
        for lo, hi in ((1.01, 41.03), (101.01, 141.03)):
            ax.axvspan(lo, hi, color="0.8", alpha=.25, lw=0)
        ax.set_xlim(0, 202)
    save(fig, "two_cycles")

    frame = summary["frames"][0]
    lo, hi = frame["compare_ns"][0] - .45, frame["compare_ns"][1] + .35
    fig, rows = axes(6, "One bit: write before update/reset; reset and DAC-control settling overlap")
    groups = [[("cmp_clk", "CMP_CLK")], [("comp_p", "COMP_P"), ("comp_n", "COMP_N")],
              [("xctrl.phi_w", "PHI_W"), ("xctrl.phi_u", "PHI_U")],
              [("xctrl.t7", "T7"), ("xctrl.t6", "T6")],
              [("bp_h6", "P6 high"), ("bp_l6", "P6 low")],
              [("bn_h6", "N6 high"), ("bn_l6", "N6 low")]]
    for ax, group in zip(rows, groups):
        for net, label in group:
            ax.plot(*envelope(t, data[net], lo, hi), label=label, lw=1.2)
        ax.set_ylabel("Voltage (V)", fontsize=9)
        ax.legend(loc="upper right", ncol=len(group), fontsize=8, frameon=False)
        ax.set_xlim(lo, hi)
    save(fig, "one_bit")

    fig, rows = axes(4, "P/N reference choices | actual switch-control words, not analog DAC settling")
    for ax, rail in zip(rows, ("p_h", "p_l", "n_h", "n_l")):
        values = decode(data, "b" + rail, level)
        ax.plot(t, values, lw=1)
        ax.set_ylabel(rail.upper() + "\n(integer)", fontsize=9)
        ax.set_xlim(40, 175)
    save(fig, "bottom_words")

    # Direct v1/v2 comparison at the SAME closing sampling edge and saved nodes.
    _, _, old, _ = load("two_cycles_simple_v1_aps")
    old_t = old["time"] * 1e9
    fig, rows = axes(3, "Closing sampling edge | write-clock drive repair (raw, unclipped)")
    rows[0].plot(*envelope(t, data["sample"], 200.95, 201.3), label="SAMPLE")
    rows[0].set_ylabel("SAMPLE (V)", fontsize=9)
    rows[1].plot(*envelope(old_t, old["xctrl.phi_w"], 200.95, 201.3), label="v1 original drive")
    rows[1].plot(*envelope(t, data["xctrl.phi_w"], 200.95, 201.3), label="v2 stronger drive")
    rows[1].axhline(-.09, ls="--", color="0.5", lw=.8, label="-90 mV screen")
    rows[1].set_ylabel("PHI_W (V)", fontsize=9)
    rows[2].plot(*envelope(t, data["xctrl.phi_u"], 200.95, 201.3), label="PHI_U v2")
    rows[2].set_ylabel("PHI_U (V)", fontsize=9)
    for ax in rows:
        ax.set_xlim(200.95, 201.3); ax.legend(fontsize=8, frameon=False, loc="best")
    save(fig, "sampling_boundary")
    print("PLOTS", str(FIG), digest)


if __name__ == "__main__":
    main()
