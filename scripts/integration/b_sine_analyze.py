"""Time-domain-only measurements and timing plots for the bounded B sine run."""
from __future__ import annotations

import json
from pathlib import Path
import pickle

import numpy as np

import b_sine_period as flow
from r3_anomaly_analyze import edges, monitor, reported_parameters

LSB = 1.8 / 256


def analyze():
    flow.check()
    result = flow.read("result.json")
    assert result["ok"], result["errors"]
    receipt = flow.read("waveform_receipt.json")
    path = flow.OUT / "waveform.pickle"
    assert flow.sha(path) == receipt["sha256"]
    with path.open("rb") as stream:
        wave = {k: np.asarray(v) for k, v in pickle.load(stream).items()}
    t = wave["time"] * 1e9
    assert np.all(np.diff(t) > 0) and t[0] == 0 and abs(t[-1] - 2400) < 1e-5
    at = lambda signal, ns: float(np.interp(ns, t, wave[signal.lower()]))
    word = lambda ns: sum(int(at(f"d{b}", ns) > .45) << b for b in range(8))
    log_path = Path(result["metadata"]["output_dir"]).parent / "spectre.out"
    log = log_path.read_text(errors="replace")
    rows = monitor(log)
    assert len(rows) == 24 and [r["frame"] for r in rows] == list(range(24)), rows
    # Use actual saved SAMPLE crossing for alignment, not final read time.
    falls = edges(t, .9 - wave["sample"])
    cmp_rises = edges(t, wave["cmp_clk"])
    write_rises = edges(t, wave["xdut.xctrl.phi_w"])
    update_rises = edges(t, wave["xdut.xctrl.phi_u"])
    assert len(falls) == 24, len(falls)
    frames = []
    group = lambda values, f: values[(values >= 100*f) & (values < 100*(f+1))]
    for f, sample_ns in enumerate(falls):
        source = at("vinp_src", sample_ns) - at("vinn_src", sample_ns)
        held = at("topp", sample_ns + .6) - at("topn", sample_ns + .6)
        code = word(100*f + 98)
        ideal = int(np.clip(np.floor((source + .9) / LSB), 0, 255))
        comparisons = []
        for ns in group(cmp_rises, f):
            trial = word(ns - .02) | sum(int(at(f"xdut.xctrl.t{b}", ns-.02) > .45) << b for b in range(8))
            comparisons.append(dict(time_ns=float(ns), trial=trial,
                residual_mv=(at("topp", ns-.02) - at("topn", ns-.02))*1e3,
                expected_residual_mv=(source + .9 - trial*LSB)*1e3))
        assert code == rows[f]["code"]
        frames.append(dict(frame=f, warmup=f < 4, sample_ns=float(sample_ns), read_ns=100*f+98,
            source_v=source, held_v=held, held_error_mv=(held-source)*1e3,
            output_code=code, ideal_code=ideal, code_error=code-ideal,
            decoded_midbin_v=(code+.5)*LSB-.9,
            compare_count=len(group(cmp_rises, f)), write_count=len(group(write_rises, f)),
            update_count=len(group(update_rises, f)), final_monitor_valid=rows[f]["valid"],
            last_update_ns=float(group(update_rises, f)[-1]) if len(group(update_rises, f)) else None,
            comparisons=comparisons))
    stress = []
    for side, gate, drain in (("P", "topp", "xdut.xcomp.y"), ("N", "topn", "xdut.xcomp.x")):
        for name, first, second in (("VGD", gate, drain), ("VGS", gate, "xdut.xcomp.tail"),
                                     ("VDS", drain, "xdut.xcomp.tail")):
            v = wave[first] - wave[second]
            i = int(np.argmax(np.abs(v)))
            stress.append(dict(side=side, terminal=name, max_abs_v=float(abs(v[i])),
                               signed_v=float(v[i]), time_ns=float(t[i]), screen_v=.99))
    measured = frames[4:]
    params = reported_parameters(log)
    previous = json.loads((flow.ROOT / "output/r3_refgate_events/b3/analysis.json").read_text())
    prior_params = previous["reported_solver_parameters"]
    # Prior analysis stores one direct dictionary of native reported parameters.
    differences = {k: dict(previous=v, current=params.get(k)) for k, v in prior_params.items()
                   if params.get(k) != v}
    delta = {k: v for k, v in differences.items() if k != "outputstart"}
    warnings = [line.strip() for line in log.splitlines() if "WARNING (" in line]
    summary = dict(purpose="one_period_time_domain_functional_screen_no_FFT", frames=frames,
        config=flow.read("context.json")["config"], waveform=receipt,
        result_ok=result["ok"], warnings=warnings, stress=stress,
        reported_solver_parameters=params, solver_parameter_differences=delta,
        output_setting_differences={k: v for k, v in differences.items() if k == "outputstart"},
        native_log_sha256=flow.sha(log_path),
        all_24_frames_8_compares=all(r["compare_count"] == 8 for r in frames),
        all_24_frames_valid=all(r["final_monitor_valid"] == 1 for r in frames),
        all_24_frames_8_writes_and_updates=all(r["write_count"] == r["update_count"] == 8 for r in frames),
        maximum_measured_held_error_mv=max(abs(r["held_error_mv"]) for r in measured),
        measured_held_within_budget=all(abs(r["held_error_mv"]) < 1.7578125 for r in measured),
        maximum_measured_code_error=max(abs(r["code_error"]) for r in measured),
        measured_gross_error_frames=[r["frame"] for r in measured if abs(r["code_error"]) > 1],
        input_pair_within_099V_screen=all(r["max_abs_v"] <= .99 for r in stress),
        has_CMI="CMI-2754" in log, has_LTE_relaxation="SPECTRE-16780" in log,
        qualified_full_ADC=False, imported_native_B=True,
        figures=["one_period.png", "one_frame.png"],
        scope="24 frames, one 500kHz period after four startup frames; not full-code/SNDR/PVT/mismatch/noise")
    flow.dump("summary.json", summary)
    plot(wave, t, frames)
    print(json.dumps({k: summary[k] for k in (
        "all_24_frames_8_compares", "all_24_frames_valid", "maximum_measured_held_error_mv",
        "maximum_measured_code_error", "measured_gross_error_frames", "has_CMI", "has_LTE_relaxation",
        "solver_parameter_differences")}, indent=2))


def plot(w, t, frames):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    out = flow.OUT / "figures"
    out.mkdir(parents=True, exist_ok=True)
    rows = frames[4:]
    sample = np.array([r["sample_ns"] for r in rows])
    x = (sample-400)/1000
    selected = (t >= 400) & (t <= 2400)
    fig, ax = plt.subplots(3, 1, figsize=(11.5, 8.5), sharex=True)
    ax[0].plot((t[selected]-400)/1000, (w["vinp_src"][selected]-w["vinn_src"][selected])*1e3,
               color="#3669ac", label="Continuous input")
    ax[0].scatter(x, [r["source_v"]*1e3 for r in rows], color="#222222", s=22, label="Sampled input", zorder=4)
    ax[0].step(x, [r["decoded_midbin_v"]*1e3 for r in rows], where="post", color="#d36a27",
               label="Decoded output, aligned to sampling")
    ax[0].set_ylabel("Differential (mV)")
    ax[0].legend(fontsize=9, loc="lower left")
    reads = (np.array([r["read_ns"] for r in rows])-400)/1000
    ax[1].step(reads, [r["ideal_code"] for r in rows], where="post", linestyle="--",
               color="#222222", label="Ideal code for sampled input")
    ax[1].plot(reads, [r["output_code"] for r in rows], "o-", color="#d36a27", label="Final ADC code")
    ax[1].set_ylabel("Code at readout")
    ax[1].legend(fontsize=9)
    ax[2].axhspan(-1, 1, color="#dfeee2", label="Adjacent-code screening band")
    ax[2].axhline(0, color="#555555", linestyle="--", linewidth=1)
    ax[2].plot(reads, [r["code_error"] for r in rows], "o-", color="#a83c38", label="Actual - ideal code")
    ax[2].set_ylabel("Code error (LSB)")
    ax[2].set_xlabel("Time from observed-period start (us)")
    ax[2].legend(fontsize=9)
    for a in ax:
        a.set_xlim(0, 2)
        a.grid(alpha=.22)
    fig.tight_layout()
    fig.savefig(out / "one_period.png", dpi=170)
    plt.close(fig)

    # Inspect the worst measured held-error frame, without cherry-picking a clean frame.
    r = max(rows, key=lambda item: abs(item["held_error_mv"]))
    f = r["frame"]
    window = (t >= 100*f) & (t <= 100*(f+1))
    tt = t[window]-100*f
    fig, ax = plt.subplots(3, 1, figsize=(11.5, 8.5), sharex=True)
    ax[0].plot(tt, w["sample"][window], label="SAMPLE", color="#3669ac")
    ax[0].plot(tt, w["cmp_clk"][window], label="CMP_CLK", color="#d36a27")
    ax[0].set_ylabel("Clock (V)")
    ax[0].legend(fontsize=9)
    ax[1].plot(tt, (w["topp"][window]-w["topn"][window])*1e3, label="CDAC differential", color="#3669ac")
    comps = r["comparisons"]
    ax[1].scatter([c["time_ns"]-100*f for c in comps], [c["expected_residual_mv"] for c in comps],
                  marker="x", color="#bb3932", label="Expected pre-compare residual", zorder=4)
    ax[1].axhline(0, linestyle="--", color="#555555", linewidth=1)
    ax[1].set_ylabel("Residual (mV)")
    ax[1].legend(fontsize=9)
    code = sum((w[f"d{b}"][window] > .45).astype(int) << b for b in range(8))
    ax[2].plot(tt, code, color="#d36a27", label="Native SAR word")
    last = (r["last_update_ns"] or 100*f+90)-100*f
    ax[2].plot([last, 100], [r["ideal_code"]]*2, "--", color="#222222", label="Final ideal code")
    ax[2].set_ylabel("SAR word")
    ax[2].set_xlabel(f"Time in frame {f+1} (ns)")
    ax[2].legend(fontsize=9)
    hold = r["sample_ns"]-100*f
    for a in ax:
        a.axvspan(1.05, hold, color="#ededed", alpha=.65)
        a.axvline(hold, color="#777777", linestyle=":")
        a.set_xlim(0, 100)
        a.grid(alpha=.22)
    fig.tight_layout()
    fig.savefig(out / "one_frame.png", dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    analyze()
