"""Display measured final ADC codes as sample/read-aligned voltage staircases."""
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
OUT = ROOT / "Obsidian_docs/assets/result8_staircase"
LSB = 1.8 / 256
INPUTS = {}


def source(path):
    p = ROOT / path
    INPUTS[path] = hashlib.sha256(p.read_bytes()).hexdigest()
    return p


def read(path):
    return json.loads(source(path).read_text(encoding="utf-8"))


def voltage(code):
    return -.9 + (np.asarray(code) + .5) * LSB


def code_axis(v):
    return (np.asarray(v) + .9) / LSB - .5


def staircase(rows, key, start=400., stop=2400.):
    """Use preceding measured code at the left edge, hold until the next one."""
    before = [r for r in rows if r[key] <= start]
    assert before
    chosen = [r for r in rows if start < r[key] < stop]
    edges = np.array([start] + [r[key] for r in chosen] + [stop])
    codes = np.array([before[-1]["output_code"]] + [r["output_code"] for r in chosen])
    assert len(edges) == len(codes)+1 and np.all(np.diff(edges) > 0)
    return (edges-start)/1000, codes


def main():
    base = "output/b_sine_period/"
    assert read(base+"result.json")["ok"]
    summary = read(base+"summary.json")
    receipt = read(base+"waveform_receipt.json")
    p = source(base+"waveform.pickle")
    assert INPUTS[base+"waveform.pickle"] == receipt["sha256"]
    with p.open("rb") as stream:
        raw = pickle.load(stream)
    names = ["time", "vinp_src", "vinn_src", "sample"] + [f"d{b}" for b in range(8)]
    w = {k: np.asarray(raw[k], dtype=float) for k in names}
    del raw
    t = w["time"] * 1e9
    assert len(t) == receipt["points"] and np.all(np.diff(t) > 0)
    assert all(np.isfinite(v).all() and len(v) == len(t) for v in w.values())
    rows = summary["frames"]
    assert len(rows) == 24 and [r["frame"] for r in rows] == list(range(24))
    codes = np.array([r["output_code"] for r in rows])
    reads = np.array([r["read_ns"] for r in rows])
    samples = np.array([r["sample_ns"] for r in rows])
    measured = sum((np.interp(reads, t, w[f"d{b}"]) > .45).astype(int) * (1 << b)
                   for b in range(8))
    assert np.array_equal(measured, codes)
    assert np.allclose(code_axis(voltage(codes)), codes, rtol=0, atol=1e-12)
    assert np.allclose(np.diff(samples), 100, rtol=0, atol=1e-8)
    assert np.allclose(reads-samples, 56.95, rtol=0, atol=1e-8)
    assert np.allclose(np.interp(samples, t, w["sample"]), .45, rtol=0, atol=1e-7)
    source_v = w["vinp_src"]-w["vinn_src"]
    assert np.allclose(np.interp(samples, t, source_v), [r["source_v"] for r in rows],
                       rtol=0, atol=1e-8)
    observed = [r for r in rows if not r["warmup"]]
    assert len(observed) == 20
    x = (samples[4:]-400)/1000
    smooth_ns = np.linspace(400, 2400, 4001)
    smooth_v = np.interp(smooth_ns, t, source_v)

    plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":10,
                         "axes.spines.top":False, "axes.spines.right":False,
                         "legend.fontsize":9})
    fig, ax = plt.subplots(2, 1, figsize=(12, 8), sharex=True, sharey=True)
    fig.subplots_adjust(left=.10, right=.90, top=.76, bottom=.08, hspace=.35)
    fig.text(.10,.96,"SAR ADC | sine input and final-code staircase",weight="bold",fontsize=16,va="top")
    fig.text(.10,.913,"Spectre 21.1 APS | T28 TT, 0.9 V, 27 C | 500 kHz, +/-0.8 V differential | 10 MS/s, 20 samples/period",fontsize=9.2)
    fig.text(.10,.880,"Native: Bootstrap (1 um) / MOM CDAC / reference pass MOS (3x) / StrongARM / SAR",fontsize=9.2)
    fig.text(.10,.847,"Ideal: VDD, SAMPLE, reference gates/commit, Cboot, delay RC | Ref source + 50 ohm / 4 pF per rail | Noise/mismatch: off",fontsize=8.8)
    fig.text(.10,.814,"Stairs: bin-center voltage reconstructed from measured final codes; zero-order hold for display.",fontsize=9.2,color="#475569")
    records = {}
    for a, key, title, color in zip(ax, ("sample_ns", "read_ns"),
            ("A. Sampling-time alignment: input versus reconstructed final code",
             "B. Read-time alignment: same codes, including the 56.95 ns read delay"),
            ("#2667a1", "#167c80")):
        edges, values = staircase(rows, key)
        a.plot((smooth_ns-400)/1000, smooth_v, color="#59616c", lw=1.5, label="Original differential input")
        a.stairs(voltage(values), edges, baseline=None, color=color, lw=1.8,
                 label="Measured final code -> input voltage")
        times = samples[4:] if key == "sample_ns" else reads[4:]
        a.plot((times-400)/1000, voltage(codes[4:]), "o", color=color, ms=3.5)
        a.set(title=title, ylabel="Differential voltage (V)", ylim=(-.95,.95), xlim=(0,2))
        a.grid(alpha=.17)
        a.axhline(0,color="#9ca3af",lw=.7)
        a.legend(loc="upper right")
        right = a.secondary_yaxis("right", functions=(code_axis,voltage))
        right.set_ylabel("Final code (unsigned)")
        right.set_yticks([0,64,128,192,255])
        records[key] = dict(edges_us=edges.tolist(), interval_codes=values.tolist(),
                            interval_voltage_v=voltage(values).tolist(), preceding_frame=3)
    ax[-1].set_xlabel("Time from observed-period start (us)")
    OUT.mkdir(parents=True,exist_ok=True)
    for ext in ("png","svg"):
        dest=OUT/("sine_staircase."+ext)
        fig.savefig(dest,dpi=180,facecolor="white")
        if ext=="svg":
            dest.write_text("\n".join(line.rstrip() for line in
                            dest.read_text(encoding="utf-8").splitlines())+"\n",encoding="utf-8")
    plt.close(fig)
    manifest=dict(source_snapshot="1fe7174",generator="scripts/reporting/result8_staircase.py",
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),input_sha256=INPUTS,
        mapping="Vdiff=-0.9+(unsigned_final_code+0.5)*(1.8/256)",
        display_only_zero_order_hold=True,internal_output_bank_added=False,
        read_delay_ns=56.95,observed_frames=20,preceding_warmup_frame=3,
        measured_code_readback_verified=True,code_voltage_roundtrip_verified=True,
        raw_held_error_metrics_unchanged=dict(peak_mv=summary["maximum_measured_held_error_mv"],
                                           exceedance_frames=summary["measured_held_budget_exceedance_frames"]),
        alignments=records,
        figure_sha256={ext:hashlib.sha256((OUT/("sine_staircase."+ext)).read_bytes()).hexdigest() for ext in ("png","svg")})
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps(dict(observed_frames=20,read_delay_ns=56.95,final_codes=codes[4:].tolist(),
                         raw_error_metrics=manifest["raw_held_error_metrics_unchanged"]),indent=2))


if __name__ == "__main__":
    main()
