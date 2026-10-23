"""Offline R4 panel using ADCToolbox's 12-tool diagnostic structure.

Numerics come from installed ADCToolbox; presentation is explicit to avoid
dashboard defaults (Hann window, inferred LSB, residual self-normalization).
No simulation or code correction is performed.
"""
from pathlib import Path
import hashlib
import importlib.metadata
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import hilbert
import adctoolbox
from adctoolbox.spectrum import compute_spectrum
from adctoolbox.fundamentals import fit_sine_4param
from adctoolbox.aout import (
    analyze_error_by_value, analyze_error_by_phase, analyze_decomposition_time,
    analyze_error_pdf, analyze_error_autocorr, analyze_phase_plane,
    analyze_error_phase_plane,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "verification/sar8_r4_performance/results.json"
FIGURE = ROOT / "docs/figures/sar8_r4_performance/adctoolbox_panel.png"
RESULT = ROOT / "verification/sar8_r4_performance/toolbox_panel.json"
FS, K, N, FSR = 10e6, 461, 1024, 1.8
LSB = FSR / 256
BLUE, RED, TEAL = "#275d9f", "#c45442", "#288779"


def serial(value):
    if isinstance(value, dict):
        return {k: serial(v) for k, v in value.items()}
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def fft_power(x):
    p = np.abs(np.fft.rfft(x - np.mean(x))) ** 2 / N**2
    p[1:-1] *= 2
    return p


def polar(ax, phase, level, labels=None):
    floor = -100
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_ylim(0, -floor)
    ax.set_rticks([20, 40, 60, 80, 100], labels=["−80", "−60", "−40", "−20", "0 dBc"])
    ax.tick_params(labelsize=8)
    ax.scatter(phase, np.maximum(level - floor, 0), s=7, color=BLUE, alpha=.6)
    if labels is not None:
        for ph, lev, label in zip(phase, level, labels):
            if lev < floor:
                continue  # Below display floor; never draw a negative radius.
            ax.plot([ph, ph], [0, lev - floor], color=BLUE, lw=1)
            ax.annotate(label, (ph, lev - floor), xytext=(5, 4), textcoords="offset points", fontsize=9)


def main(source_path=SOURCE, figure_path=FIGURE, result_path=RESULT,
         source_key=None, label="R4 SAR ADC", warning=None):
    SOURCE, FIGURE, RESULT = source_path, figure_path, result_path
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    if source_key is not None:
        source = source[source_key]
    warning = warning or "CMI device-overvoltage warnings remain unresolved."
    codes = np.asarray([f["code"] for f in source["dynamic_frames"]])
    assert codes.shape == (N,) and np.all((codes >= 0) & (codes <= 255))
    assert np.all(codes == np.round(codes))
    x = -.9 + (codes + .5) * LSB
    freq = K / N
    spectrum = compute_spectrum(x - x.mean(), fs=FS, max_scale_range=(-.9, .9),
                                win_type="rectangular", side_bin=0,
                                max_harmonic=5, nf_method=3)
    metrics = spectrum["metrics"]
    fit = fit_sine_4param(x, frequency_estimate=freq, max_iterations=0)
    e = np.asarray(fit["residuals"]).flatten()
    value = analyze_error_by_value(x, norm_freq=freq, n_bins=32,
                                  max_iterations=0, create_plot=False)
    phase = analyze_error_by_phase(x, norm_freq=freq, n_bins=32,
                                  max_iterations=0, create_plot=False)
    dec = analyze_decomposition_time(x, frequency=freq, max_iterations=0, create_plot=False)
    pdf = analyze_error_pdf(x, resolution=8, full_scale=FSR, frequency=freq,
                           max_iterations=0, create_plot=False)
    acf = analyze_error_autocorr(x, frequency=freq, max_iterations=0, create_plot=False)
    p = fft_power(x)
    other = p.copy()
    other[[0, K]] = 0
    spur = int(np.argmax(other))
    hb = np.asarray([min(h * K % N, N - h * K % N) for h in range(2, 6)])
    noise = other.copy()
    noise[hb] = 0
    checks = {
        "prior_sndr_abs_difference_db": abs(metrics["sndr_dbc"] - source["dynamic"]["sndr_db"]),
        "prior_sfdr_abs_difference_db": abs(metrics["sfdr_dbc"] - source["dynamic"]["sfdr_db"]),
        "parseval_residual_power_abs_difference_v2": abs(np.mean(e**2) - other.sum()),
        "snr_direct_abs_difference_db": abs(metrics["snr_dbc"] - 10*np.log10(p[K]/noise.sum())),
        "pdf_lsb_max_difference": float(np.max(np.abs(pdf["err_lsb"] - e / LSB))),
        "decomposition_max_difference_v": float(np.max(np.abs(x - dec["fundamental_signal"]
                                                  - dec["harmonic_signal"] - dec["noise_residual"]))),
    }
    assert checks["prior_sndr_abs_difference_db"] < 1e-8
    assert checks["prior_sfdr_abs_difference_db"] < 1e-8
    assert checks["snr_direct_abs_difference_db"] < 1e-8
    assert checks["parseval_residual_power_abs_difference_v2"] < 1e-14
    assert checks["pdf_lsb_max_difference"] < 1e-10
    assert checks["decomposition_max_difference_v"] < 1e-12

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.titlesize": 12, "axes.labelsize": 10,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, axs = plt.subplots(3, 4, figsize=(22, 14))
    axes = axs.ravel()
    for index in [1, 5]:
        spec = axes[index].get_subplotspec()
        axes[index].remove()
        axes[index] = fig.add_subplot(spec, projection="polar")
    fmhz = np.fft.rfftfreq(N, 1 / FS) / 1e6
    dbc = 10*np.log10(np.maximum(p, 1e-30) / p[K])
    a = axes[0]
    a.plot(fmhz[1:], dbc[1:], color=BLUE, lw=.8)
    a.scatter([fmhz[K], fmhz[spur]], [0, dbc[spur]], color=RED, s=22)
    a.set(xlabel="Frequency (MHz)", ylabel="Power (dBc)", ylim=(-110, 4))
    a.text(.03, .96, f'SNDR {metrics["sndr_dbc"]:.2f} dB\nSFDR {metrics["sfdr_dbc"]:.2f} dB\nENOB {metrics["enob"]:.3f} bit',
           transform=a.transAxes, va="top", bbox=dict(facecolor="white", edgecolor="none", alpha=.9))
    # FFT phase is record-relative. Harmonic-relative phase is shown separately in (6).
    polar(axes[1], np.angle(np.fft.rfft(x-x.mean()))[1:], dbc[1:])
    a = axes[2]
    a.scatter(x, e / LSB, s=5, alpha=.25, color=BLUE, label="Samples")
    a.plot(value["value_bin_centers"], value["error_mean"] / LSB, color=RED, label="32-bin mean")
    a.set(xlabel="Decoded voltage (V)", ylabel="Residual (LSB)", ylim=(-.8, .8))
    a.legend(fontsize=8)
    a = axes[3]
    a.plot(np.rad2deg(phase["phase_bin_centers_rad"]), phase["bin_error_rms_v"] / LSB,
           "o-", color=BLUE, ms=3, label="32-bin RMS")
    a.axhline(1/np.sqrt(12), color=TEAL, ls="--", label="Ideal quantization RMS")
    a.set(xlabel="Fitted input phase (deg)", ylabel="Residual RMS (LSB)", xlim=(0, 360), ylim=(0, .5))
    a.legend(fontsize=8)
    a = axes[4]
    a.plot(np.arange(64), e[:64]/LSB, color=BLUE, lw=1, label="Total residual")
    a.plot(np.arange(64), dec["harmonic_signal"][:64]/LSB, color=RED, lw=1.5, label="H2–H5 component")
    a.set(xlabel="Sample index (first 64)", ylabel="Residual (LSB)")
    a.legend(fontsize=8)
    polar(axes[5], dec["phases"], 20*np.log10(dec["magnitudes"]/dec["magnitudes"][0]),
          [f"H{h}" for h in range(1, 6)])
    a = axes[6]
    a.plot(pdf["x"], pdf["pdf"], color=BLUE, label="Residual KDE")
    a.plot(pdf["x"], pdf["gauss_pdf"], color=RED, ls="--", label="Gaussian comparison")
    a.plot([-.6, -.5, -.5, .5, .5, .6], [0, 0, 1, 1, 0, 0], color=TEAL, ls=":", label="Ideal uniform ±0.5 LSB")
    a.set(xlabel="Residual (LSB)", ylabel="Probability density (1/LSB)")
    a.legend(fontsize=8)
    a = axes[7]
    a.stem(acf["lags"], acf["acf"], markerfmt=".", basefmt=" ")
    a.set(xlabel="Lag (samples)", ylabel="Normalized autocorrelation")
    # Same residual and Hilbert-envelope method as ADCToolbox, but use explicit
    # rectangular FFT and ADC full scale instead of wrapper Hann/self-scaling.
    for a, sig in [(axes[8], e), (axes[9], np.abs(hilbert(e)))]:
        ep = fft_power(sig)
        a.plot(fmhz[1:], 10*np.log10(np.maximum(ep[1:], 1e-30) / (.9**2/2)), color=BLUE, lw=.8)
        a.set(xlabel="Frequency (MHz)", ylabel="Power (dBFS)", ylim=(-115, -55))
    pp = analyze_phase_plane(x, fs=FS, ax=axes[10], title="(11) Delayed-sample plane")
    ep = analyze_error_phase_plane(x, fs=FS, ax=axes[11], unit_mode="voltage", title="(12) Rising / falling trend")
    axes[10].set_xlabel("Decoded voltage x[n] (V)")
    axes[10].set_ylabel(f'Decoded voltage x[n+{pp["lag"]}] (V)')
    axes[11].set_xlabel("Decoded voltage (V)")
    # Keep library diagnostic trends but do not call their separation proven memory.
    axes[11].legend(["Samples", "Rising fit", "Falling fit"], fontsize=8, loc="lower right")
    for text in list(axes[11].texts):
        text.remove()
    axes[11].text(.97, .97, f'Trend separation: {ep["hysteresis_gap"]*1e6:.1f} µV\nDiagnostic, not proven memory',
                  transform=axes[11].transAxes, ha="right", va="top", fontsize=8,
                  bbox=dict(facecolor="white", edgecolor="none", alpha=.9))
    titles = ["(1) Output spectrum", "(2) FFT magnitude / phase", "(3) Residual vs. value",
              "(4) Residual RMS vs. phase", "(5) Harmonic decomposition", "(6) Harmonic-relative phase",
              "(7) Residual distribution", "(8) Residual autocorrelation", "(9) Residual spectrum",
              "(10) Residual-envelope spectrum", "(11) Delayed-sample plane", "(12) Rising / falling trend"]
    for i, a in enumerate(axes):
        a.set_title(titles[i], pad=18 if i in [1, 5] else 10)
        a.grid(alpha=.18)
    fig.suptitle(label + "  |  ADCToolbox 12-panel analysis", fontsize=21, y=.987)
    fig.text(.5, .954, "8 bit · TT · 0.9 V · 27°C  |  Fs = 10 MS/s  |  Fin = 4.501953125 MHz  |  N = 1024, k = 461  |  Input = −1 dBFS", ha="center", fontsize=11)
    fig.text(.5, .026, "Native T28 ADC core · ideal external supply/reference/SAMPLE sources · no transient noise / mismatch / PVT sweep", ha="center", fontsize=11)
    fig.text(.5, .008, "Residual = decoded output − fitted sine; not clock-edge input error.  " + warning, ha="center", fontsize=11, color="#9c392c")
    fig.subplots_adjust(left=.055, right=.98, top=.902, bottom=.085, hspace=.52, wspace=.39)
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE, dpi=170, facecolor="white")
    plt.close(fig)
    result = {
        "source": str(SOURCE.relative_to(ROOT)),
        "source_key": source_key,
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "toolbox_version": importlib.metadata.version("adctoolbox"),
        "toolbox_module": str(Path(adctoolbox.__file__)),
        "settings": {"samples": N, "fs_hz": FS, "fin_hz": FS*freq, "bin": K,
                     "full_scale_vpp": FSR, "lsb_v": LSB, "window": "rectangular",
                     "side_bin": 0, "max_harmonic": 5, "nf_method": 3,
                     "fit_frequency_fixed": True, "value_phase_bins": 32,
                     "panel12_fit": "Library automatic frequency refinement, 3 iterations"},
        "spectrum": metrics,
        "residual": {"rms_mv": np.sqrt(np.mean(e**2))*1e3,
                     "rms_lsb": np.sqrt(np.mean(e**2))/LSB,
                     "peak_lsb": np.max(np.abs(e))/LSB,
                     "ideal_quantization_rms_mv": LSB/np.sqrt(12)*1e3,
                     "harmonic_h2_h5_rms_mv": np.sqrt(np.mean(dec["harmonic_signal"]**2))*1e3,
                     "remaining_rms_mv": np.sqrt(np.mean(dec["noise_residual"]**2))*1e3,
                     "pdf_sample_std_lsb": pdf["sigma"], "pdf_kl_gaussian": pdf["kl_divergence"],
                     "rising_falling_fit_gap_mv": ep["hysteresis_gap"]*1e3,
                     "acf_max_abs_nonzero_lag": np.max(np.abs(acf["acf"][acf["lags"] != 0]))},
        "spur": {"bin": spur, "frequency_hz": spur*FS/N, "dbc": dbc[spur]},
        "phase_bins": {"count": 32, "am_pm_model_r2_binned": phase["r_squared_binned"]},
        "phase_plane": pp,
        "validation": checks,
        "limits": ["No thermal-noise or jitter measurement: deterministic transient only.",
                   "Value-binned residual is not static INL/DNL.",
                   "Near-Nyquist delayed-sample geometry is not analog phase portrait.",
                   "Panel12 trend is diagnostic only, not proof of circuit memory.",
                   warning,
                   "Refer to source results for native process completion evidence."],
    }
    RESULT.write_text(json.dumps(serial(result), indent=2, ensure_ascii=False, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps(serial({"spectrum": metrics, "residual": result["residual"], "checks": checks}), indent=2))


if __name__ == "__main__":
    main()
