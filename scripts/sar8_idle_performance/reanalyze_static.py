"""Recompute histogram INL/DNL from historical measured codes, not thresholds."""
from pathlib import Path
import hashlib
import inspect
import json
from importlib.metadata import version
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from adctoolbox.aout.analyze_inl_from_sine import analyze_inl_from_sine
from adctoolbox.aout.compute_inl_from_sine import compute_inl_from_sine

ROOT = Path(__file__).resolve().parents[2]


def analyze(codes):
    result = analyze_inl_from_sine(codes, num_bits=8, clip_percent=0.01, create_plot=False)
    counts = np.bincount(codes, minlength=256)
    return {**{k: v.tolist() for k, v in result.items()},
            "samples": len(codes), "observed_codes": np.flatnonzero(counts).tolist(),
            "counts": counts.tolist(), "code_min": int(codes.min()), "code_max": int(codes.max()),
            "dnl_min": float(result["dnl"].min()), "dnl_max": float(result["dnl"].max()),
            "inl_min": float(result["inl"].min()), "inl_max": float(result["inl"].max()),
            "inl_abs_max": float(np.max(abs(result["inl"]))) }


def main():
    source = ROOT / "verification/sar8_idle_performance/results.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    assert data["candidate_commit"] == "027b951"
    frames = data["candidate"]["dynamic_frames"]
    codes = np.array([f["code"] for f in frames], dtype=np.int64)
    assert len(codes) == 1024 and all(f["valid"] for f in frames)
    actual = analyze(codes)
    # Synthetic ideal ADC: same fitted sine amplitude/phase and coherent record.
    # This control diagnoses estimator behavior, not the measured ADC transfer.
    n = np.arange(len(codes))
    phase = 2 * np.pi * 461 * n / 1024
    basis = np.column_stack((np.sin(phase), np.cos(phase), np.ones(len(n))))
    coef = np.linalg.lstsq(basis, codes + 0.5, rcond=None)[0]
    ideal_codes = np.clip(np.floor(basis @ coef), 0, 255).astype(np.int64)
    ideal = analyze(ideal_codes)
    implementation = Path(inspect.getfile(compute_inl_from_sine))
    report = {
        "candidate_commit": "027b951", "source": str(source.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "codes_sha256": hashlib.sha256(codes.astype("<i8").tobytes()).hexdigest(),
        "toolbox_version": version("adctoolbox"), "function": "analyze_inl_from_sine",
        "compute_implementation_sha256": hashlib.sha256(implementation.read_bytes()).hexdigest(),
        "settings": {"num_bits": 8, "clip_percent": 0.01},
        "measured": actual, "synthetic_ideal_control": ideal,
        "synthetic_fit_coefficients_code_units": coef.tolist(),
        "qualification": "Diagnostic only: 1024 samples, -1 dBFS partial code coverage; not full-code static sign-off",
        "axis_note": "Toolbox returned code axis retained without reindexing; not the boundary-search transition axis",
    }
    (ROOT / "verification/sar8_idle_performance/reanalysis_20261028.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), layout="constrained", sharex=True)
    fig.suptitle("ADCToolbox sine-histogram RECOMPUTATION | 027b951\n"
                 "TT, 0.9 V, 27 C | 1024 codes, -1 dBFS | diagnostic only", fontsize=12)
    for ax, key in zip(axes, ("dnl", "inl")):
        ax.plot(actual["code"], actual[key], color="#167c87", lw=1, label="Measured ADC output codes")
        ax.plot(ideal["code"], ideal[key], color="#b76838", lw=.9, alpha=.8, label="Synthetic ideal ADC: finite-record control")
        ax.axhline(0, color=".5", lw=.7)
        ax.set(ylabel=key.upper() + " (LSB)", xlim=(0, 255))
        ax.grid(alpha=.2)
        ax.legend(fontsize=9)
    axes[0].set_title(f"Measured histogram DNL: {actual['dnl_min']:.4f} to {actual['dnl_max']:.4f} LSB", fontsize=10)
    axes[1].set_title(f"Measured histogram INL: {actual['inl_min']:.4f} to {actual['inl_max']:.4f} LSB", fontsize=10)
    axes[1].set_xlabel("Code axis returned by ADCToolbox")
    fig.supxlabel(f"Observed codes {actual['code_min']}-{actual['code_max']}; edge clip=1%; no full-scale coverage\n"
                  "Input: integer output codes; histogram + sine CDF inversion; no threshold-search arrays used\n"
                  "Synthetic control is NOT another circuit simulation. No filtering or smoothing.", fontsize=9)
    fig.savefig(ROOT / "Obsidian_docs/assets/idle_performance/static_sine_reanalysis.png", dpi=180)
    plt.close(fig)
    print(json.dumps({name: {k: v for k, v in r.items() if k not in ("code", "dnl", "inl", "counts", "observed_codes")}
                      for name, r in (("measured", actual), ("synthetic", ideal))}, indent=2))


if __name__ == "__main__":
    main()
