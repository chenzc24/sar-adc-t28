"""Offline-only sine/edge decomposition of the immutable completed B waveform.

No simulator, bridge, remote operation, circuit rewrite or input correction.
Equivalent phase/gain and nonfundamental residual are not physical attribution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import pickle
import shutil

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "output/b_sine_period"
OUT = ROOT / "output/b_sine_decomposition"
OMEGA_NS = 2*np.pi*500000*1e-9


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def basis(ns, order=1):
    theta = (np.asarray(ns)-400)*OMEGA_NS
    return np.column_stack([np.ones_like(theta)] +
        [fn(k*theta) for k in range(1, order+1) for fn in (np.sin, np.cos)])


def stats(v):
    v = np.asarray(v)
    return dict(peak_abs_uv=float(np.max(np.abs(v))*1e6),
                rms_uv=float(np.sqrt(np.mean(v*v))*1e6),
                min_uv=float(np.min(v)*1e6), max_uv=float(np.max(v)*1e6))


def fit(ns, v):
    matrix = basis(ns)
    coefficients, _, rank, _ = np.linalg.lstsq(matrix, v, rcond=None)
    assert rank == 3
    predicted = matrix @ coefficients
    residual = np.asarray(v)-predicted
    assert np.max(np.abs(matrix.T @ residual)) < 1e-11
    diagnostic = dict(dc_v=float(coefficients[0]), sin_v=float(coefficients[1]),
        cos_v=float(coefficients[2]), amplitude_v=float(np.hypot(*coefficients[1:])),
        phase_rad=float(np.arctan2(coefficients[2], coefficients[1])),
        residual=stats(residual), design_condition=float(np.linalg.cond(matrix)))
    # Diagnostic low-harmonic projections; no FFT or full-ADC dynamic metric.
    harmonics = []
    for order in range(2, 6):
        m = basis(ns, order)[:, -2:]
        ab, _, _, _ = np.linalg.lstsq(m, residual, rcond=None)
        harmonics.append(dict(order=order, amplitude_uv=float(np.hypot(*ab)*1e6)))
    diagnostic["low_harmonic_candidates"] = harmonics
    return coefficients, predicted, residual, diagnostic


def transfer(output, source):
    phase = output["phase_rad"]-source["phase_rad"]
    phase = np.arctan2(np.sin(phase), np.cos(phase))
    gain = output["amplitude_v"]/source["amplitude_v"]
    return dict(gain=float(gain), gain_error_percent=float((gain-1)*100),
        gain_error_ppm=float((gain-1)*1e6), equivalent_lag_ns=float(-phase/OMEGA_NS),
        phase_degrees=float(phase*180/np.pi),
        offset_uv=float((output["dc_v"]-gain*source["dc_v"])*1e6))


def synthetic_check():
    ns = 441.05+100*np.arange(20)
    gain, lag, offset = .9997, 1.73, 123e-6
    source = .8*np.sin((ns-400)*OMEGA_NS)
    fundamental = offset+gain*.8*np.sin((ns-400-lag)*OMEGA_NS)
    nonlinear = 13e-6*np.sin(3*(ns-400)*OMEGA_NS)+9e-6*np.cos(2*(ns-400)*OMEGA_NS)
    _, _, _, si = fit(ns, source)
    _, _, residual, hi = fit(ns, fundamental+nonlinear)
    answer = transfer(hi, si)
    assert abs(answer["gain"]-gain) < 1e-12
    assert abs(answer["equivalent_lag_ns"]-lag) < 1e-8
    assert abs(answer["offset_uv"]-123) < 1e-6
    assert np.max(np.abs(residual-nonlinear)) < 1e-12
    assert abs(hi["low_harmonic_candidates"][0]["amplitude_uv"]-9) < 1e-6
    assert abs(hi["low_harmonic_candidates"][1]["amplitude_uv"]-13) < 1e-6
    return True


def analyze():
    assert synthetic_check()
    original = read(ROOT / "verification/integration/b_sine_period_results.json")
    original_summary = read(SOURCE / "summary.json")
    context = read(SOURCE / "context.json")
    assert read(SOURCE / "result.json")["ok"]
    assert read(SOURCE / "flow.json")["stage"] == "complete"
    assert original["waveform"] == read(SOURCE / "waveform_receipt.json")
    assert context["config"]["input_frequency_hz"] == 500000
    assert context["config"]["observed_frames"] == 20
    protected = [SOURCE / name for name in ("waveform.pickle", "waveform_receipt.json",
                 "context.json", "result.json", "summary.json", "flow.json", "spectre/spectre.out",
                 "spectre/b_sine_period.raw/tran_b_sine.tran.tran")]
    protected += [Path(context["deck"]), *map(Path, context["include_sha256"])]
    protected.append(ROOT / "verification/integration/b_sine_period_results.json")
    before = {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in protected}
    assert sha(SOURCE / "waveform.pickle") == original["waveform"]["sha256"]
    assert sha(context["deck"]) == original["deck_sha256"] == context["deck_sha256"]
    for p, digest in context["include_sha256"].items():
        assert sha(p) == digest
    assert sha(SOURCE / "spectre/spectre.out") == original["native_log_sha256"]
    with (SOURCE / "waveform.pickle").open("rb") as stream:
        wave = {key: np.asarray(value) for key, value in pickle.load(stream).items()}
    time = wave["time"]*1e9
    assert len(time) == 1326793 and np.all(np.diff(time) > 0)
    assert time[0] == 0 and abs(time[-1]-2400) < 1e-6 and len(wave) == 45
    at = lambda name, ns: np.interp(ns, time, wave[name])
    differential = lambda p, n, ns: at(p, ns)-at(n, ns)
    rows = original["frames"][4:]
    ns = np.array([r["sample_ns"] for r in rows])
    assert [r["frame"] for r in rows] == list(range(4, 24))
    source = differential("vinp_src", "vinn_src", ns)
    held = differential("topp", "topn", ns+.6)
    assert np.max(abs(held-np.array([r["held_v"] for r in rows]))) < 1e-12
    source_c, source_fit, _, source_diag = fit(ns, source)
    _, _, held_remaining, held_diag = fit(ns, held)
    held_transfer = transfer(held_diag, source_diag)
    delayed_source = basis(ns-held_transfer["equivalent_lag_ns"]) @ source_c
    phase_term = delayed_source-source_fit
    gain_term = (held_transfer["gain"]-1)*delayed_source
    offset_term = np.full(20, held_transfer["offset_uv"]*1e-6)
    source_term = source_fit-source
    raw_error = held-source
    reconstructed = phase_term+gain_term+offset_term+held_remaining+source_term
    reconstruction_error = float(np.max(abs(reconstructed-raw_error)))
    assert reconstruction_error < 1e-12

    def extrapolate(window=5., degree=3, step=.01, name="diff"):
        relative = np.arange(-window, -.15+step*.25, step)
        assert np.max(abs(at("sample", ns[:, None]+relative)-.9)) < 1e-9
        m = np.polynomial.polynomial.polyvander(relative/window, degree)
        data = (differential("topp", "topn", ns[:, None]+relative) if name == "diff"
                else at(name, ns[:, None]+relative))
        coefficients = np.linalg.lstsq(m, data.T, rcond=None)[0]
        return coefficients[0], relative, data, coefficients, m

    tracking, _, _, _, _ = extrapolate()
    _, _, tracking_remaining, tracking_diag = fit(ns, tracking)
    tracking_transfer = transfer(tracking_diag, source_diag)
    turnoff = held-tracking
    _, turnoff_fit, turnoff_remaining, turnoff_diag = fit(ns, turnoff)
    assert np.max(abs(turnoff_remaining-(held_remaining-tracking_remaining))) < 1e-12
    sensitivities = []
    for window in (3., 5., 8.):
        for degree in (2, 3):
            other, *_ = extrapolate(window=window, degree=degree)
            sensitivities.append(dict(window_ns=window, degree=degree, step_ns=.01,
                max_prediction_difference_uv=float(np.max(abs(other-tracking))*1e6)))
    for step in (.005, .02):
        other, *_ = extrapolate(step=step)
        sensitivities.append(dict(window_ns=5., degree=3, step_ns=step,
            max_prediction_difference_uv=float(np.max(abs(other-tracking))*1e6)))
    p_predict, *_ = extrapolate(name="topp")
    n_predict, *_ = extrapolate(name="topn")
    p_delta = at("topp", ns+.6)-p_predict
    n_delta = at("topn", ns+.6)-n_predict
    assert np.max(abs(p_delta-n_delta-turnoff)) < 1e-12
    common_mode_delta = (p_delta+n_delta)/2
    # Only the quiet held interval before the first comparator edge, not a
    # complete-conversion leakage or kickback measurement.
    first_cmp = np.array([original_summary["frames"][r["frame"]]
                         ["comparisons"][0]["time_ns"] for r in rows])
    assert np.all(ns+2 < first_cmp-.2)
    plateau_times = ns[:, None]+np.arange(.6, 2.00001, .01)
    plateau = differential("topp", "topn", plateau_times)
    plateau_delta = plateau-held[:, None]
    edge_times = ns[:, None]+np.arange(-.15, .60001, .005)
    ref_change = {name: float(np.max(np.ptp(at(name, edge_times), axis=1))*1e6)
                  for name in ("xdut.xcdac.bp7", "xdut.xcdac.bn7", "xdut.gpp7",
                               "xdut.gpn7", "xdut.gnp7", "xdut.gnn7")}
    pre_gate = np.r_[at("xdut.xbootp.g", ns-.15)-at("vinp", ns-.15),
                     at("xdut.xbootn.g", ns-.15)-at("vinn", ns-.15)]
    frames = []
    for i, row in enumerate(rows):
        frames.append(dict(frame=row["frame"], sample_ns=float(ns[i]),
            source_v=float(source[i]), held_v=float(held[i]), raw_error_uv=float(raw_error[i]*1e6),
            phase_term_uv=float(phase_term[i]*1e6), gain_term_uv=float(gain_term[i]*1e6),
            offset_uv=float(offset_term[i]*1e6), source_fit_term_uv=float(source_term[i]*1e6),
            held_remaining_uv=float(held_remaining[i]*1e6),
            tracking_prediction_v=float(tracking[i]), tracking_remaining_uv=float(tracking_remaining[i]*1e6),
            turnoff_increment_uv=float(turnoff[i]*1e6), turnoff_remaining_uv=float(turnoff_remaining[i]*1e6),
            turnoff_p_uv=float(p_delta[i]*1e6), turnoff_n_uv=float(n_delta[i]*1e6),
            turnoff_common_mode_uv=float(common_mode_delta[i]*1e6),
            precompare_plateau_change_peak_uv=float(np.max(abs(plateau_delta[i]))*1e6)))

    result = dict(scope="offline_only_existing_500kHz_sine_20_observed_samples",
        source_result_commit="61dcdb4", no_new_simulation=True, no_OA_or_DUT_edits=True,
        source_configuration=context["config"],
        no_acceptance_reference_correction=True, original_held_budget_still_failed=True,
        original_waveform=original["waveform"], source_fit=source_diag,
        held_fit=held_diag, held_transfer=held_transfer,
        decomposition=dict(raw=stats(raw_error), phase=stats(phase_term), gain=stats(gain_term),
            dc=stats(offset_term), source_fit_term=stats(source_term), remaining=stats(held_remaining)),
        tracking_fit=tracking_diag, tracking_transfer=tracking_transfer,
        turnoff_fit=turnoff_diag, turnoff_increment=stats(turnoff),
        turnoff_common_mode_increment=stats(common_mode_delta),
        turnoff_equivalent_lag_reduction_ns=tracking_transfer["equivalent_lag_ns"]-
                                          held_transfer["equivalent_lag_ns"],
        counterfactual=dict(window_ns=[-5., -.15], degree=3, uniform_step_ns=.01,
            evaluation_ns=0, sensitivity=sensitivities, definition="held(+0.6ns)-preedge_tracking_extrapolated(0)",
            pure_charge_injection_identified=False),
        precompare_plateau_change=stats(plateau_delta),
        precompare_plateau_relative_window_ns=[.6, 2.0],
        saved_MSB_reference_node_max_edge_range_uv=ref_change,
        preedge_gate_minus_input_range_v=[float(np.min(pre_gate)), float(np.max(pre_gate))],
        reconstruction_peak_v=reconstruction_error, synthetic_fit_recovery_pass=True,
        frames=frames,
        limits=["Single frequency/amplitude: equivalent phase, not unique physical delay or RC.",
            "Nonfundamental residual includes nonlinear/history/settling/numerical components.",
            "Turnoff increment mixes aperture, channel charge, clock feedthrough and loading effects.",
            "Signal-linear injection may be absorbed into fitted gain/phase; no pure injection claim.",
            "20 analog samples are not full-ADC DNL/INL/SNDR/ENOB qualification."])
    plot(wave, time, ns, result, source, held, tracking, turnoff_fit)
    after = {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in protected}
    assert before == after, "Original evidence was modified"
    result["original_file_sha256_unchanged"] = after
    result["analysis_source_LF_sha256"] = hashlib.sha256(Path(__file__).read_text(encoding="utf-8").encode()).hexdigest()
    result["figure_sha256"] = {p.name: sha(p) for p in sorted((OUT/"figures").glob("*.png"))}
    write(OUT/"results.json", result)
    print(json.dumps({key: result[key] for key in ("held_transfer", "decomposition",
        "tracking_transfer", "turnoff_increment", "turnoff_fit", "precompare_plateau_change",
        "counterfactual")}, indent=2))


def plot(w, t, ns, result, source, held, tracking, turnoff_fit):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    target = OUT/"figures"
    target.mkdir(parents=True, exist_ok=True)
    rows = result["frames"]
    x = (ns-400)/1000
    fig, ax = plt.subplots(3, 1, figsize=(11.5, 8.8), sharex=True)
    for key, label, color in (("raw_error_uv", "Raw held error", "#333333"),
          ("phase_term_uv", "Equivalent phase term", "#3669ac"),
          ("gain_term_uv", "Gain term", "#d36a27")):
        ax[0].plot(x, [r[key]/1000 for r in rows], "o-", ms=3, label=label, color=color)
    ax[0].set_ylabel("Error (mV)")
    for key, label, color in (("held_remaining_uv", "Held remainder", "#7a5195"),
          ("tracking_remaining_uv", "Pre-edge tracking remainder", "#3669ac"),
          ("turnoff_remaining_uv", "Turnoff-increment remainder", "#d36a27")):
        ax[1].plot(x, [r[key] for r in rows], "o-", ms=3, label=label, color=color)
    ax[1].set_ylabel("After DC/fundamental fit (uV)")
    ax[2].plot(x, [r["turnoff_increment_uv"] for r in rows], "o", label="Held - predicted tracking at SAMPLE", color="#d36a27")
    ax[2].plot(x, turnoff_fit*1e6, "--", label="DC + fundamental of increment", color="#333333")
    ax[2].set_ylabel("Turnoff-related increment (uV)")
    ax[2].set_xlabel("Nominal sample time from observed-period start (us)")
    for a in ax:
        a.axhline(0, color="#777777", lw=.8)
        a.set_xlim(0, 2)
        a.grid(alpha=.22)
        a.legend(fontsize=9, loc="best")
    ax[1].legend(fontsize=9, loc="lower center", bbox_to_anchor=(.5, 1.01), ncol=3)
    fig.tight_layout()
    fig.savefig(target/"decomposition.png", dpi=170)
    plt.close(fig)

    index = int(np.argmax(abs(held-source)))
    sample = ns[index]
    relative = np.arange(-.6, .90001, .002)
    at = lambda name: np.interp(sample+relative, t, w[name])
    fit_times = np.arange(-5., -.15+.0025, .01)
    data = np.interp(sample+fit_times, t, w["topp"])-np.interp(sample+fit_times, t, w["topn"])
    c = np.polynomial.polynomial.polyfit(fit_times/5, data, 3)
    continued = np.polynomial.polynomial.polyval(relative/5, c)
    top = at("topp")-at("topn")
    fig, ax = plt.subplots(3, 1, figsize=(11.5, 8.5), sharex=True)
    for name, label in (("sample", "SAMPLE"), ("xdut.xbootp.g", "Main gate P"), ("xdut.xbootn.g", "Main gate N")):
        ax[0].plot(relative, at(name), label=label)
    ax[0].set_ylabel("Control (V)")
    ax[1].plot(relative, (at("vinp_src")-at("vinn_src"))*1e3, label="Source input", color="#333333")
    ax[1].plot(relative, top*1e3, label="Actual CDAC", color="#3669ac")
    ax[1].plot(relative, continued*1e3, "--", label="Continued-tracking extrapolation", color="#d36a27")
    ax[1].set_ylabel("Differential (mV)")
    ax[2].plot(relative, (top-tracking[index])*1e6, label="CDAC - predicted tracking at SAMPLE", color="#3669ac")
    ax[2].plot(relative, (continued-tracking[index])*1e6, "--", label="Continued tracking (not simulated)", color="#d36a27")
    ax[2].scatter([.6], [(held[index]-tracking[index])*1e6], color="#a83c38", zorder=5, label="Held measurement")
    ax[2].axhline(0, color="#777777", lw=.8)
    ax[2].set_ylabel("Relative to nominal tracking (uV)")
    ax[2].set_xlabel(f"Time from SAMPLE 50% fall in frame {rows[index]['frame']+1} (ns)")
    for a in ax:
        a.axvspan(-.05, .05, alpha=.45, color="#dddddd")
        a.axvline(0, color="#777777", linestyle=":")
        a.axvline(.6, color="#a83c38", linestyle=":", alpha=.5)
        a.set_xlim(-.6, .9)
        a.grid(alpha=.22)
        a.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(target/"turnoff_edge.png", dpi=170)
    plt.close(fig)


def curate():
    result = read(OUT/"results.json")
    assert result["synthetic_fit_recovery_pass"] and result["reconstruction_peak_v"] < 1e-12
    assert hashlib.sha256(Path(__file__).read_text(encoding="utf-8").encode()).hexdigest() == result["analysis_source_LF_sha256"]
    for name, digest in result["original_file_sha256_unchanged"].items():
        assert sha(ROOT/name) == digest
    target = ROOT/"docs/figures/b_sine_decomposition"
    target.mkdir(parents=True, exist_ok=True)
    for name, digest in result["figure_sha256"].items():
        assert sha(OUT/"figures"/name) == digest
        shutil.copyfile(OUT/"figures"/name, target/name)
    result["figures_visually_reviewed_by_agent"] = True
    write(ROOT/"verification/integration/b_sine_decomposition_results.json", result)
    print("CURATED_EXISTING_WAVEFORM_DECOMPOSITION")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--curate", action="store_true")
    options = parser.parse_args()
    curate() if options.curate else analyze()
