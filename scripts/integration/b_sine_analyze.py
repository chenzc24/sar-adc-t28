"""Time-domain-only measurements and timing plots for the bounded B sine run."""
from __future__ import annotations

import json
from pathlib import Path
import pickle
import re
import shutil

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
    probes = re.findall(r"BSINE,(\d+),([^\s,]+),([^\s,]+),([^\s,]+)", log)
    assert len(probes) == 24 and [int(p[0]) for p in probes] == list(range(24))
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
        probe = [float(value) for value in probes[f][1:]]
        assert max(abs(a-b) for a, b in zip((source, held, held-source), probe)) < 1e-7
        code = word(100*f + 98)
        ideal = int(np.clip(np.floor((source + .9) / LSB), 0, 255))
        # Diagnose the existing continuous trace; never shift the acceptance
        # reference to fit the output. One ns before SAMPLE fall is tracking.
        pre_ns = float(sample_ns - 1)
        pre_source = at("vinp_src", pre_ns) - at("vinn_src", pre_ns)
        pre_pin = at("vinp", pre_ns) - at("vinn", pre_ns)
        pre_top = at("topp", pre_ns) - at("topn", pre_ns)
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
            tracking=dict(time_ns=pre_ns, source_v=pre_source, pin_v=pre_pin, top_v=pre_top,
                pin_minus_source_mv=(pre_pin-pre_source)*1e3,
                top_minus_pin_mv=(pre_top-pre_pin)*1e3,
                top_minus_source_mv=(pre_top-pre_source)*1e3,
                sample_command_v=at("sample", pre_ns),
                gate_minus_input_p_v=at("xdut.xbootp.g", pre_ns)-at("vinp", pre_ns),
                gate_minus_input_n_v=at("xdut.xbootn.g", pre_ns)-at("vinn", pre_ns)),
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
    slope = np.array([.8*2*np.pi*500000*np.cos(2*np.pi*500000*
                     (r["sample_ns"]-400)*1e-9)*1e-6 for r in measured])  # mV/ns
    error = np.array([r["held_error_mv"] for r in measured])
    lag_ns = float(-np.dot(error, slope) / np.dot(slope, slope))
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
        all_24_passive_probes_agree_with_saved_waveforms=True,
        reported_solver_parameters=params, solver_parameter_differences=delta,
        output_setting_differences={k: v for k, v in differences.items() if k == "outputstart"},
        native_log_sha256=flow.sha(log_path),
        all_24_frames_8_compares=all(r["compare_count"] == 8 for r in frames),
        all_24_frames_valid=all(r["final_monitor_valid"] == 1 for r in frames),
        all_24_frames_8_writes_and_updates=all(r["write_count"] == r["update_count"] == 8 for r in frames),
        maximum_measured_held_error_mv=max(abs(r["held_error_mv"]) for r in measured),
        measured_held_error_range_mv=[min(r["held_error_mv"] for r in measured),
                                      max(r["held_error_mv"] for r in measured)],
        measured_held_budget_exceedance_frames=[r["frame"] for r in measured
                                               if abs(r["held_error_mv"]) >= 1.7578125],
        measured_held_within_budget=all(abs(r["held_error_mv"]) < 1.7578125 for r in measured),
        maximum_measured_code_error=max(abs(r["code_error"]) for r in measured),
        slope_equivalent_lag_ns=lag_ns,
        lag_fit_residual_peak_mv=float(max(abs(error + lag_ns*slope))),
        lag_fit_is_diagnostic_only_no_acceptance_correction=True,
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
    fig, ax = plt.subplots(4, 1, figsize=(11.5, 10.5), sharex=True)
    ax[0].plot((t[selected]-400)/1000, (w["vinp_src"][selected]-w["vinn_src"][selected])*1e3,
               color="#3669ac", label="Continuous input")
    ax[0].scatter(x, [r["source_v"]*1e3 for r in rows], color="#222222", s=22, label="Sampled input", zorder=4)
    ax[0].step(np.r_[x, 2.0], [r["decoded_midbin_v"]*1e3 for r in rows] +
               [rows[-1]["decoded_midbin_v"]*1e3], where="post", color="#d36a27",
               label="Decoded output, aligned to sampling")
    ax[0].set_ylabel("Differential (mV)")
    ax[0].legend(fontsize=9, loc="lower left")
    reads = (np.array([r["read_ns"] for r in rows])-400)/1000
    ax[1].step(reads, [r["ideal_code"] for r in rows], where="post", linestyle="--",
               color="#222222", label="Ideal code for sampled input")
    ax[1].step(reads, [r["output_code"] for r in rows], where="post", color="#d36a27", label="Final ADC code")
    ax[1].scatter(reads, [r["output_code"] for r in rows], color="#d36a27", s=22, zorder=4)
    ax[1].set_ylabel("Code at readout")
    ax[1].legend(fontsize=9)
    ax[2].axhspan(-1, 1, color="#dfeee2", label="Adjacent-code screening band")
    ax[2].axhline(0, color="#555555", linestyle="--", linewidth=1)
    ax[2].plot(reads, [r["code_error"] for r in rows], "o-", color="#a83c38", label="Actual - ideal code")
    ax[2].set_ylabel("Code error (LSB)")
    ax[2].legend(fontsize=9)
    ax[3].axhspan(-1.7578125, 1.7578125, color="#dfeee2", label="Held-error budget: +/-0.25 LSB")
    ax[3].axhline(0, color="#555555", linestyle="--", linewidth=1)
    ax[3].plot(x, [r["held_error_mv"] for r in rows], "o-", color="#7a5195",
               label="Held - input at SAMPLE fall")
    ax[3].set_ylabel("Held error (mV)")
    ax[3].set_xlabel("Time from observed-period start (us)")
    ax[3].legend(fontsize=9)
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
    for i, a in enumerate(ax):
        a.axvspan(1.05, hold, color="#ededed", alpha=.65,
                  label="Acquisition" if i == 0 else None)
        a.axvline(hold, color="#777777", linestyle=":",
                  label="SAMPLE fall" if i == 0 else None)
        a.set_xlim(0, 100)
        a.grid(alpha=.22)
    ax[0].legend(fontsize=9, ncol=2)
    fig.tight_layout()
    fig.savefig(out / "one_frame.png", dpi=170)
    plt.close(fig)


def curate():
    """Copy the reviewed, generated result evidence without changing raw data."""
    flow.check()
    assert flow.read("flow.json")["stage"] == "awaiting_visual_review"
    summary = flow.read("summary.json")
    result = flow.read("result.json")
    context = flow.read("context.json")
    assert summary["result_ok"] and len(summary["frames"]) == 24
    assert not summary["solver_parameter_differences"]
    target = flow.ROOT / "docs/figures/b_sine_period"
    target.mkdir(parents=True, exist_ok=True)
    figures = {}
    for name in summary["figures"]:
        path = target / name
        shutil.copyfile(flow.OUT / "figures" / name, path)
        figures[str(path.relative_to(flow.ROOT)).replace("\\", "/")] = flow.sha(path)
    curated = {k: v for k, v in summary.items() if k not in ("frames", "figures")}
    curated.update(
        baseline="R3_with_verified_B_reference_events",
        source_model_commit=context["source_model_commit"], launch_commit="87cbeb2",
        library="SAR_ADC_T28", top="sar_adc8_join_r3", testbench="tb_sar_adc8_join_r3",
        frames=[{k: v for k, v in r.items() if k != "comparisons"} for r in summary["frames"]],
        native_timings_s=result["metadata"]["timings"], errors=result["errors"],
        native_completion="0 errors, 7 warnings, 7 notices",
        native_log="output/b_sine_period/spectre/spectre.out",
        generated_summary="output/b_sine_period/summary.json",
        full_comparison_records_in_generated_summary=True,
        deck_sha256=context["deck_sha256"], export_sha256=context["export_sha256"],
        include_sha256={Path(k).name: v for k, v in context["include_sha256"].items()},
        analysis_source_sha256=flow.sha(Path(__file__)), figure_sha256=figures,
        visual_review_by_agent=True, raw_data_or_DUT_modified=False, FFT_performed=False)
    path = flow.ROOT / "verification/integration/b_sine_period_results.json"
    path.write_text(json.dumps(curated, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print("CURATED_REVIEWED_B_SINE_RESULTS", flush=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--curate", action="store_true")
    args = parser.parse_args()
    curate() if args.curate else analyze()
