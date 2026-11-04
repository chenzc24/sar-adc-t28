"""Redraw the historical idle-reset candidate for its single-version note."""
from pathlib import Path
import argparse
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def overview(candidate, dest, title):
    from adctoolbox.aout.plot_dnl_inl import plot_dnl_inl

    s = candidate["static"]
    dnl = np.asarray(s["dnl_nominal_lsb"])
    inl = np.asarray(s["inl_endpoint_lsb"])
    fig, axes = plt.subplots(2, 1, figsize=(11, 6), layout="constrained")
    fig.suptitle(title + "\nADCToolbox plot_dnl_inl | +/-1 LSB overview", fontsize=12)
    plot_dnl_inl(np.arange(1, len(dnl) + 1), dnl, inl,
                 inl_code=np.arange(1, len(inl) + 1), axes=axes,
                 color_dnl="b", color_inl="b")
    axes[0].set(xlabel="Output code (1-254)", xlim=(0, 256))
    axes[1].set(xlabel="Transition index (1-255)", xlim=(0, 256), ylabel="Endpoint INL (LSB)")
    axes[0].set_title(f"DNL: {dnl.min():.5f} to {dnl.max():.5f} LSB (nominal LSB)")
    axes[1].set_title(f"Endpoint INL: max |INL| = {abs(inl).max():.5f} LSB (endpoint LSB)")
    for ax, values in zip(axes, (dnl, inl)):
        assert tuple(ax.get_ylim()) == (-1.0, 1.0)
        np.testing.assert_array_equal(ax.lines[0].get_ydata(), values)
    fig.supxlabel("Method: binary transition search; bracket midpoints; NOT histogram analysis\n"
                  "Search bracket: 1/128 nominal LSB = 54.93 uV; nominal LSB = 1.8 V / 256\n"
                  "Historical candidate 027b951; same data as the zoomed plot; no new simulation", fontsize=9)
    fig.savefig(dest / "static_idle_overview.png", dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--overview-only", action="store_true")
    args = parser.parse_args()
    result = json.loads((ROOT / "verification/sar8_idle_performance/results.json").read_text(encoding="utf-8"))
    assert result["candidate_commit"] == "027b951"
    candidate = result["candidate"]
    dest = ROOT / "Obsidian_docs/assets/idle_performance"
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    title = "Idle-stage staged reset (027b951) | TT, 0.9 V, 27 C | 10 MS/s"
    footer = "Ideal supply / reference / SAMPLE; Rin 50 ohm/side; Rref 50 ohm + Cref 4 pF/rail"
    color = "#167c87"
    overview(candidate, dest, title)
    if args.overview_only:
        return
    s = candidate["static"]
    fig, axes = plt.subplots(3, 1, figsize=(11, 8), layout="constrained")
    fig.suptitle(title, fontsize=12)
    for ax, key, label in zip(axes,
                             ["dnl_nominal_lsb", "inl_endpoint_lsb", "inl_raw_lsb"],
                             ["DNL (LSB)", "Endpoint INL (LSB)", "Raw transition error (LSB)"]):
        values = s[key]
        ax.plot(np.arange(1, len(values) + 1), values, color=color, lw=1.2)
        ax.set(xlabel="Code / transition index", ylabel=label, xlim=(0, 256))
        ax.axhline(0, color=".5", lw=.7)
        ax.grid(alpha=.2)
    fig.supxlabel(footer + "\n255 transitions / 256 code centers; search bracket 1/128 LSB; saturated endpoint widths excluded", fontsize=8)
    fig.savefig(dest / "static_idle.png", dpi=180)
    plt.close(fig)

    d = candidate["dynamic"]
    fig, ax = plt.subplots(figsize=(11, 4.5), layout="constrained")
    fig.suptitle(title, fontsize=12)
    ax.plot(np.array(d["frequency_axis_hz"]) / 1e6, d["spectrum_dbc"], color=color, lw=1)
    ax.set(xlabel="Frequency (MHz)", ylabel="Power (dBc)", xlim=(0, 5), ylim=(-115, 3))
    ax.set_title(f"SNDR {d['sndr_db']:.3f} dB | ENOB {d['enob_sndr_bits']:.4f} bit | SFDR {d['sfdr_db']:.3f} dB", fontsize=11)
    ax.grid(alpha=.2)
    fig.supxlabel(footer + "\nN=1024; fin=4.501953125 MHz; -1 dBFS; coherent rectangular FFT; no code calibration\nHistorical results: 2026-10-23; no transient noise / mismatch / PEX", fontsize=8)
    fig.savefig(dest / "spectrum_idle.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
