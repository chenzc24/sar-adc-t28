"""Measured waveforms only; explicit expected levels, timing and stress limits."""
from __future__ import annotations

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from support import ROOT, load

COLORS = ["#c44e46", "#2a8785", "#7966ad"]


def waves(category, name):
    result = load(f"{category}/{name}_result.json")
    assert result["ok"]
    return {k: np.asarray(v) for k, v in load(f"{category}/{name}_waveform.json").items()}


def main():
    folder = ROOT / "docs/figures/cdac8_reset"
    folder.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"figure.dpi": 150, "font.size": 10, "axes.grid": True,
                         "grid.alpha": .20, "axes.spines.top": False, "axes.spines.right": False})
    a = waves("screen", "screen_baseline")
    b = waves("nominal", "oa_nominal")
    fig, axes = plt.subplots(3, 1, sharex=True, figsize=(10.5, 7.5), layout="constrained")
    for wave, label, color in ((a, "Original drive", COLORS[0]), (b, "Native 4x pull-down", COLORS[1])):
        t = wave["time"]*1e9
        keep = (t >= 189.85) & (t <= 190.65)
        t = t[keep]
        axes[0].plot(t, wave["xcdac.bp5"][keep], color=color, label=label)
        axes[1].plot(t, wave["topp"][keep], color=color, label=label)
        axes[2].plot(t, wave["xcdac.xsp5.es_b"][keep], color=color, label=label + ": P gate")
    axes[0].axhline(.99, color="#555", ls="--", label="Core terminal screen: 0.99 V")
    axes[0].axhline(.45, color="#555", ls=":", label="Reset target: VCM = 0.45 V")
    for axis in axes:
        axis.axvline(190.22, color="#888", ls=":", lw=1)
        axis.legend(fontsize=8, loc="best", ncol=2)
    axes[0].set_ylabel("P bit-5 bottom (V)")
    axes[1].set_ylabel("Common top TOPP (V)")
    axes[2].set(xlabel="Time (ns); dotted vertical = VCM command begins", ylabel="VCM PMOS gate (V)", xlim=(189.85, 190.65))
    fig.savefig(folder / "reset_timing.png")
    plt.close(fig)

    rows = load("summary_screen.json")
    names = [r["variant"]["name"] for r in rows]
    values = [r["reset_terminal_worst"]["value_v"] for r in rows]
    fig, ax = plt.subplots(figsize=(10.5, 4.2), layout="constrained")
    ax.bar(names, values, color=[COLORS[1] if v <= .990001 else COLORS[0] for v in values], label="Worst reconstructed reset terminal |V|")
    ax.axhline(.99, color="#555", ls="--", label="0.99 V core model screen")
    ax.set(ylabel="Worst reference-switch/driver terminal (V)", ylim=(.85, max(values)+.04))
    ax.tick_params(axis="x", rotation=35)
    ax.legend(fontsize=8)
    fig.savefig(folder / "screen_comparison.png")
    plt.close(fig)

    fixed = waves("nominal", "oa_fixed128")
    fig, axes = plt.subplots(2, 1, sharex=True, figsize=(10.5, 5.5), layout="constrained")
    t = fixed["time"]*1e9
    keep = (t >= 235) & (t <= 289)
    t = t[keep]
    axes[0].plot(t, fixed["phi"][keep], label="Input sample PHI (unchanged)", color="#4777ae")
    axes[0].plot(t, fixed["dac_sample"][keep], label="Bottom VCM enable", color="#dd9148")
    error = 1000*(fixed["topp"][keep]-fixed["topn"][keep]-.8)
    axes[1].plot(t, error, color=COLORS[1], label="Raw TOP differential error; fixed code 128")
    axes[1].axhline(0, color="#555", ls="--", label="Expected error = 0")
    limit = 1.8/256/4*1000
    axes[1].axhspan(-limit, limit, color="#64a56f", alpha=.16, label="+/-0.25 LSB")
    for axis in axes:
        axis.axvspan(241.05, 289, color="#999", alpha=.10)
        axis.axvline(241.05, color="#777", ls=":", lw=1)
        axis.legend(fontsize=8, ncol=2)
    axes[0].set_ylabel("Control voltage (V)")
    axes[1].set(xlabel="Time (ns); shaded = held/conversion", ylabel="Raw error (mV)", ylim=(-2.2, 2.2), xlim=(235, 289))
    fig.savefig(folder / "hold_regression.png")
    plt.close(fig)

    original = waves("ab", "ab_negative_baseline")
    candidate = waves("nominal", "oa_negative")
    fig, axes = plt.subplots(2, 1, sharex=True, figsize=(10.5, 5.8), layout="constrained")
    for wave, label, color in ((original, "Original drive", COLORS[0]), (candidate, "Native 4x pull-down", COLORS[1])):
        t = wave["time"]*1e9
        keep = (t >= 89.9) & (t <= 90.8)
        bottoms = np.stack([wave[f"xcdac.b{s}{bit}"] for s in "pn" for bit in range(9)])
        axes[0].plot(t[keep], bottoms[:, keep].max(axis=0), label=label, color=color)
        axes[1].plot(t[keep], bottoms[:, keep].min(axis=0), label=label, color=color)
    axes[0].axhline(.99, color="#555", ls="--", label="BOT-to-VSS: 0.99 V screen")
    axes[1].axhline(-.09, color="#555", ls="--", label="BOT = VDD - 0.99 V (PMOS body stress)")
    axes[0].set_ylabel("Maximum over 18 bottoms (V)")
    axes[1].set(ylabel="Minimum over 18 bottoms (V)", xlabel="Time (ns); -0.8 V differential input", xlim=(89.9, 90.8))
    for axis in axes:
        axis.axvline(90.22, color="#888", ls=":", lw=1)
        axis.legend(fontsize=8, ncol=2)
    fig.savefig(folder / "negative_input_tradeoff.png")
    plt.close(fig)
    print("FIGURES_OK", folder)


if __name__ == "__main__":
    main()
