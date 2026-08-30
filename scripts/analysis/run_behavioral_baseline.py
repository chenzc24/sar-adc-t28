"""Run the stage-1 error budget and stage-2 ideal SAR baseline."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import yaml
from adctoolbox import analyze_inl_from_ramp, analyze_spectrum


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.behavioral.sar_adc import SarAdcModel


def load_spec(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        spec = yaml.safe_load(handle)
    if not isinstance(spec, dict):
        raise ValueError("design spec must contain a YAML mapping")
    return spec


def derive_error_budget(spec: dict) -> dict[str, float]:
    bits = int(spec["converter"]["resolution_bits"])
    v_min, v_max = (float(value) for value in spec["input"]["differential_range_v"])
    span_v = v_max - v_min
    lsb_v = span_v / (1 << bits)
    test_level_dbfs = float(spec["input"]["dynamic_test_level_dbfs"])
    signal_peak_v = span_v / 2.0 * 10.0 ** (test_level_dbfs / 20.0)
    signal_rms_v = signal_peak_v / math.sqrt(2.0)

    enob_target = float(spec["targets"]["enob_min_bits"])
    sndr_target_db = 6.02 * enob_target + 1.76
    allowed_error_rms_v = signal_rms_v / 10.0 ** (sndr_target_db / 20.0)

    allocation = spec["error_budget"]
    quantization_rms_v = lsb_v / math.sqrt(12.0)
    sampling_rms_v = float(allocation["sampling_noise_rms_lsb"]) * lsb_v
    comparator_rms_v = float(allocation["comparator_noise_rms_lsb"]) * lsb_v
    reference_rms_v = float(allocation["reference_switching_noise_rms_lsb"]) * lsb_v
    unmodeled_rms_v = float(allocation["distortion_unmodeled_rms_lsb"]) * lsb_v
    jitter_s = float(allocation["clock_jitter_rms_ps"]) * 1e-12
    jitter_input_hz = float(allocation["jitter_budget_input_hz"])
    jitter_rms_v = signal_rms_v * 2.0 * math.pi * jitter_input_hz * jitter_s

    allocated_error_rms_v = math.sqrt(
        quantization_rms_v**2
        + sampling_rms_v**2
        + comparator_rms_v**2
        + reference_rms_v**2
        + unmodeled_rms_v**2
        + jitter_rms_v**2
    )
    projected_sndr_db = 20.0 * math.log10(signal_rms_v / allocated_error_rms_v)
    residual_headroom_rms_v = math.sqrt(
        max(0.0, allowed_error_rms_v**2 - allocated_error_rms_v**2)
    )

    return {
        "full_scale_span_v": span_v,
        "lsb_v": lsb_v,
        "dynamic_signal_peak_v": signal_peak_v,
        "dynamic_signal_rms_v": signal_rms_v,
        "target_sndr_db": sndr_target_db,
        "allowed_total_error_rms_v": allowed_error_rms_v,
        "allowed_total_error_rms_lsb": allowed_error_rms_v / lsb_v,
        "quantization_noise_rms_v": quantization_rms_v,
        "quantization_noise_rms_lsb": 1.0 / math.sqrt(12.0),
        "sampling_noise_rms_v": sampling_rms_v,
        "comparator_noise_rms_v": comparator_rms_v,
        "reference_switching_noise_rms_v": reference_rms_v,
        "clock_jitter_error_rms_v": jitter_rms_v,
        "clock_jitter_error_rms_lsb": jitter_rms_v / lsb_v,
        "distortion_unmodeled_rms_v": unmodeled_rms_v,
        "allocated_total_error_rms_v": allocated_error_rms_v,
        "allocated_total_error_rms_lsb": allocated_error_rms_v / lsb_v,
        "projected_sndr_db": projected_sndr_db,
        "projected_enob_bits": (projected_sndr_db - 1.76) / 6.02,
        "sndr_margin_db": projected_sndr_db - sndr_target_db,
        "residual_headroom_rms_v": residual_headroom_rms_v,
        "residual_headroom_rms_lsb": residual_headroom_rms_v / lsb_v,
    }


def _static_baseline(model: SarAdcModel, samples_per_code: int) -> tuple[dict, dict]:
    sample_count = model.code_count * samples_per_code
    v_min, _ = model.differential_range_v
    ramp = v_min + (np.arange(sample_count) + 0.5) * model.full_scale_span_v / sample_count
    bits = model.convert(ramp)
    codes = model.unsigned_codes(bits)
    result = analyze_inl_from_ramp(
        codes,
        num_bits=model.resolution_bits,
        endpoint="endpoints",
        exclude_endpoints=False,
        create_plot=False,
    )
    summary = {
        "sample_count": int(sample_count),
        "samples_per_code": int(samples_per_code),
        "observed_code_min": int(codes.min()),
        "observed_code_max": int(codes.max()),
        "missing_code_count": int(len(result["missing_codes"])),
        "dnl_min_lsb": float(result["dnl_min"]),
        "dnl_max_lsb": float(result["dnl_max"]),
        "inl_min_lsb": float(result["inl_min"]),
        "inl_max_lsb": float(result["inl_max"]),
    }
    return summary, result


def _dynamic_baseline(
    model: SarAdcModel,
    *,
    sample_rate_hz: float,
    sample_count: int,
    coherent_bin: int,
    level_dbfs: float,
    create_plot: bool,
) -> dict:
    if not 0 < coherent_bin < sample_count // 2:
        raise ValueError("coherent_bin must be between DC and Nyquist")
    n = np.arange(sample_count)
    input_frequency_hz = coherent_bin * sample_rate_hz / sample_count
    input_peak_v = model.full_scale_span_v / 2.0 * 10.0 ** (level_dbfs / 20.0)
    vin = input_peak_v * np.sin(2.0 * np.pi * coherent_bin * n / sample_count)
    bits = model.convert(vin)
    reconstructed = model.reconstruct(bits)
    centered = reconstructed - np.mean(reconstructed)
    metrics = analyze_spectrum(
        centered,
        fs=sample_rate_hz,
        max_scale_range=model.differential_range_v,
        win_type="rectangular",
        side_bin=0,
        create_plot=create_plot,
    )
    return {
        "sample_count": int(sample_count),
        "coherent_bin": int(coherent_bin),
        "input_frequency_hz": float(input_frequency_hz),
        "input_level_dbfs": float(level_dbfs),
        "sndr_db": float(metrics["sndr_dbc"]),
        "snr_db": float(metrics["snr_dbc"]),
        "sfdr_db": float(metrics["sfdr_dbc"]),
        "thd_db": float(metrics["thd_dbc"]),
        "enob_bits": float(metrics["enob"]),
    }


def _save_static_plot(result: dict, path: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(9, 6), constrained_layout=True)
    axes[0].plot(result["code"], result["dnl"], linewidth=1.0)
    axes[0].set_ylabel("DNL (LSB)")
    axes[0].grid(True, alpha=0.3)
    axes[1].plot(result["transition_code"], result["inl"], linewidth=1.0)
    axes[1].set_xlabel("Code / transition")
    axes[1].set_ylabel("INL (LSB)")
    axes[1].grid(True, alpha=0.3)
    fig.suptitle("Ideal 10-bit SAR static linearity")
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run_baseline(spec_path: Path, output_dir: Path, *, make_plots: bool = True) -> dict:
    spec = load_spec(spec_path)
    model = SarAdcModel(
        resolution_bits=int(spec["converter"]["resolution_bits"]),
        differential_range_v=tuple(float(v) for v in spec["input"]["differential_range_v"]),
    )
    settings = spec["behavioral_baseline"]
    budget = derive_error_budget(spec)
    if budget["sndr_margin_db"] <= 0.0:
        raise ValueError("declared error allocations exceed the target SNDR budget")

    static_summary, static_result = _static_baseline(
        model, int(settings["ramp_samples_per_code"])
    )
    dynamic_summary = _dynamic_baseline(
        model,
        sample_rate_hz=float(spec["converter"]["sample_rate_hz"]),
        sample_count=int(settings["fft_samples"]),
        coherent_bin=int(settings["coherent_bin"]),
        level_dbfs=float(spec["input"]["dynamic_test_level_dbfs"]),
        create_plot=make_plots,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    if make_plots:
        dynamic_figure = plt.gcf()
        dynamic_figure.savefig(output_dir / "dynamic_spectrum.png", dpi=160, bbox_inches="tight")
        plt.close(dynamic_figure)
        _save_static_plot(static_result, output_dir / "static_linearity.png")

    summary = {
        "project": spec["project"]["name"],
        "model": {
            "architecture": "ideal_fully_differential_binary_equivalent",
            "resolution_bits": model.resolution_bits,
            "sample_rate_hz": float(spec["converter"]["sample_rate_hz"]),
            "differential_range_v": list(model.differential_range_v),
            "lsb_v": model.lsb_v,
            "cdac_partition": spec["converter"]["cdac_partition"],
        },
        "error_budget": budget,
        "static": static_summary,
        "dynamic": dynamic_summary,
    }
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--spec",
        type=Path,
        default=PROJECT_ROOT / "config" / "design_spec.yaml",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "output" / "behavioral_baseline",
    )
    args = parser.parse_args()
    summary = run_baseline(args.spec, args.output)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
