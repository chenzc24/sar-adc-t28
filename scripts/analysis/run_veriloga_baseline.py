"""Run and analyze the clocked Verilog-A SAR ADC baseline.

Use the workspace bridge Python for remote Spectre runs and the project Python
for EVAS or analysis::

    E:/bridge-Agent-T28/.venv/Scripts/python.exe scripts/analysis/run_veriloga_baseline.py --backend spectre
    .venv/Scripts/python.exe scripts/analysis/run_veriloga_baseline.py --backend evas --cases timing
    .venv/Scripts/python.exe scripts/analysis/run_veriloga_baseline.py --backend none --analyze
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "models" / "veriloga" / "sar_adc_ideal_10b.va"
TB_DIR = PROJECT_ROOT / "netlist" / "tb"
DEFAULT_OUTPUT = PROJECT_ROOT / "output" / "veriloga_baseline"
CASES = ("timing", "static", "dynamic")
ALL_CASES = (*CASES, "allocated_noise")
TB_PATHS = {
    "timing": TB_DIR / "tb_sar_adc_ideal_timing.scs",
    "static": TB_DIR / "tb_sar_adc_ideal_static.scs",
    "dynamic": TB_DIR / "tb_sar_adc_ideal_dynamic.scs",
    "allocated_noise": TB_DIR / "tb_sar_adc_allocated_noise_dynamic.scs",
}
LOGIC_THRESHOLD_V = 0.45
OUTPUT_SETTLE_S = 100e-12
# CLK_SAMPLE starts its 20 ps falling edge at 40 ns.  The Verilog-A capture
# event is cross(CLK_SAMPLE - 0.45 V, -1), so the actual sample instant is the
# midpoint of that edge rather than the pulse source's delay parameter.
FIRST_SAMPLE_CROSSING_S = 40e-9 + 10e-12


def _stage_netlist(case: str, case_dir: Path) -> Path:
    """Create a generated run deck whose AHDL include is colocated remotely."""

    source = TB_PATHS[case].read_text(encoding="utf-8")
    source = source.replace(
        'ahdl_include "../../models/veriloga/sar_adc_ideal_10b.va"',
        'ahdl_include "sar_adc_ideal_10b.va"',
    )
    case_dir.mkdir(parents=True, exist_ok=True)
    staged = case_dir / TB_PATHS[case].name
    staged.write_text(source, encoding="utf-8")
    return staged


def _write_waveform_csv(data: dict[str, list[float]], path: Path) -> None:
    if not data:
        raise ValueError("simulation returned no waveform data")
    keys = ["time"] if "time" in data else []
    keys.extend(sorted(key for key in data if key != "time"))
    lengths = {len(data[key]) for key in keys}
    if len(lengths) != 1:
        raise ValueError(f"waveform lengths differ: {sorted(lengths)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(keys)
        writer.writerows(zip(*(data[key] for key in keys), strict=True))


def run_spectre(case: str, output_root: Path) -> dict:
    """Run one case through the configured remote Spectre bridge."""

    from virtuoso_bridge.spectre.runner import SpectreSimulator

    case_dir = output_root / case
    staged = _stage_netlist(case, case_dir)
    simulator = SpectreSimulator.from_env(
        work_dir=case_dir,
        output_format="psfascii",
        timeout=1800,
    )
    result = simulator.run_simulation(
        staged,
        {
            "include_files": [MODEL_PATH],
            "spectre_args": ["+lqtimeout", "30"],
        },
    )
    record = {
        "backend": "spectre",
        "case": case,
        "ok": bool(result.ok),
        "status": result.status.value,
        "errors": list(result.errors),
        "warnings": list(result.warnings),
        "metadata": result.metadata,
        "signals": sorted(result.data),
    }
    with (case_dir / "spectre_result.json").open("w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, sort_keys=True, default=str)
        handle.write("\n")
    if not result.ok:
        raise RuntimeError(f"Spectre {case} failed: {result.errors}")
    _write_waveform_csv(result.data, case_dir / "tran.csv")
    return record


def run_evas(case: str, output_root: Path) -> dict:
    """Run one case with the project EVAS CLI and its Python fallback engine."""

    if case != "timing":
        raise ValueError("EVAS Python fallback is intentionally limited to timing")
    executable = PROJECT_ROOT / ".venv" / "Scripts" / "evas.exe"
    if not executable.exists():
        raise FileNotFoundError(f"EVAS CLI not found: {executable}")
    case_dir = output_root / case
    command = [
        str(executable),
        "simulate",
        str(TB_PATHS[case]),
        "-o",
        str(case_dir),
        "--engine",
        "python",
        "--ahdllint",
    ]
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "evas_run.log").write_text(completed.stdout, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(f"EVAS timing failed; see {case_dir / 'evas_run.log'}")
    return {
        "backend": "evas-0.7.0-python",
        "case": case,
        "ok": True,
        "log": str(case_dir / "evas_run.log"),
    }


def _load_csv(path: Path) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(path)
    data = np.genfromtxt(path, delimiter=",", names=True)
    if data.size == 0:
        raise ValueError(f"empty waveform CSV: {path}")
    return np.atleast_1d(data)


def _column(data: np.ndarray, name: str) -> np.ndarray:
    assert data.dtype.names is not None
    matches = [item for item in data.dtype.names if item.lower() == name.lower()]
    if not matches:
        raise KeyError(f"signal {name!r} not found in {data.dtype.names}")
    return np.asarray(data[matches[0]], dtype=float)


def _decode_codes(data: np.ndarray) -> np.ndarray:
    codes = np.zeros(data.shape, dtype=np.int64)
    for bit in range(10):
        high = _column(data, f"dout_{bit}") > LOGIC_THRESHOLD_V
        codes |= high.astype(np.int64) << bit
    return codes


def _valid_samples(data: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    time = _column(data, "time")
    valid = _column(data, "valid")
    codes = _decode_codes(data)
    rising = np.flatnonzero(
        (valid[:-1] <= LOGIC_THRESHOLD_V) & (valid[1:] > LOGIC_THRESHOLD_V)
    ) + 1
    sample_indices: list[int] = []
    for edge_index in rising:
        target_time = time[edge_index] + OUTPUT_SETTLE_S
        search_tolerance = max(abs(target_time) * 1e-12, 1e-18)
        settled_index = int(
            np.searchsorted(time, target_time - search_tolerance, side="left")
        )
        if settled_index >= len(time) or valid[settled_index] <= LOGIC_THRESHOLD_V:
            raise ValueError("VALID did not remain asserted through output settling")
        sample_indices.append(settled_index)
    indices = np.asarray(sample_indices, dtype=np.int64)
    return time[indices], codes[indices]


def analyze_timing(path: Path) -> dict:
    data = _load_csv(path)
    valid_time, codes = _valid_samples(data)
    expected_codes = np.asarray([768, 256], dtype=np.int64)
    if len(codes) != 2 or not np.array_equal(codes, expected_codes):
        raise AssertionError(f"timing codes {codes.tolist()} != {expected_codes.tolist()}")

    time = _column(data, "time")
    busy = _column(data, "busy")
    busy_rise = np.flatnonzero(
        (busy[:-1] <= LOGIC_THRESHOLD_V) & (busy[1:] > LOGIC_THRESHOLD_V)
    ) + 1
    busy_fall = np.flatnonzero(
        (busy[:-1] > LOGIC_THRESHOLD_V) & (busy[1:] <= LOGIC_THRESHOLD_V)
    ) + 1
    conversion_s = time[busy_fall[:2]] - time[busy_rise[:2]]
    if len(conversion_s) != 2 or np.any(conversion_s > 60e-9):
        raise AssertionError(f"conversion durations out of range: {conversion_s}")
    return {
        "valid_count": int(len(codes)),
        "codes": codes.tolist(),
        "valid_time_ns": (valid_time * 1e9).tolist(),
        "conversion_time_ns": (conversion_s * 1e9).tolist(),
        "max_conversion_time_ns": float(np.max(conversion_s) * 1e9),
    }


def analyze_static(path: Path) -> dict:
    data = _load_csv(path)
    _, codes = _valid_samples(data)
    expected = np.repeat(np.arange(1024, dtype=np.int64), 8)
    if not np.array_equal(codes, expected):
        mismatch = int(np.flatnonzero(codes != expected)[0]) if len(codes) == len(expected) else -1
        raise AssertionError(
            f"static code correlation failed: samples={len(codes)}, mismatch={mismatch}"
        )
    histogram = np.bincount(codes, minlength=1024)
    dnl = histogram / 8.0 - 1.0
    inl = np.cumsum(dnl)
    missing = np.flatnonzero(histogram == 0)
    return {
        "sample_count": int(len(codes)),
        "missing_code_count": int(len(missing)),
        "dnl_min_lsb": float(np.min(dnl)),
        "dnl_max_lsb": float(np.max(dnl)),
        "inl_min_lsb": float(np.min(inl)),
        "inl_max_lsb": float(np.max(inl)),
    }


def analyze_dynamic(path: Path) -> dict:
    from adctoolbox import analyze_spectrum

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from models.behavioral.sar_adc import SarAdcModel

    data = _load_csv(path)
    _, codes = _valid_samples(data)
    sample_count = 16384
    coherent_bin = 7373
    sample_rate_hz = 10e6
    input_frequency_hz = sample_rate_hz * coherent_bin / sample_count
    differential_peak_v = 0.9 * 10.0 ** (-1.0 / 20.0)
    sample_time = FIRST_SAMPLE_CROSSING_S + np.arange(sample_count) / sample_rate_hz
    input_diff = differential_peak_v * np.sin(2.0 * np.pi * input_frequency_hz * sample_time)
    model = SarAdcModel(10, (-0.9, 0.9))
    expected = model.unsigned_codes(model.convert(input_diff))
    if not np.array_equal(codes, expected):
        mismatch = int(np.flatnonzero(codes != expected)[0]) if len(codes) == len(expected) else -1
        raise AssertionError(
            f"dynamic code correlation failed: samples={len(codes)}, mismatch={mismatch}"
        )
    reconstructed = -0.9 + codes.astype(float) * (1.8 / 1024.0)
    metrics = analyze_spectrum(
        reconstructed - np.mean(reconstructed),
        fs=sample_rate_hz,
        max_scale_range=(-0.9, 0.9),
        win_type="rectangular",
        side_bin=0,
        create_plot=False,
    )
    sndr_db = float(metrics["sndr_dbc"])
    enob_bits = float(metrics["enob"])
    python_sndr_db = 60.953
    if sndr_db < 55.94 or enob_bits < 9.0 or abs(sndr_db - python_sndr_db) > 0.1:
        raise AssertionError(f"dynamic gates failed: SNDR={sndr_db}, ENOB={enob_bits}")
    return {
        "sample_count": int(len(codes)),
        "coherent_bin": coherent_bin,
        "input_frequency_hz": input_frequency_hz,
        "sndr_db": sndr_db,
        "snr_db": float(metrics["snr_dbc"]),
        "sfdr_db": float(metrics["sfdr_dbc"]),
        "thd_db": float(metrics["thd_dbc"]),
        "enob_bits": enob_bits,
        "python_sndr_reference_db": python_sndr_db,
        "sndr_delta_db": sndr_db - python_sndr_db,
    }


def analyze_allocated_noise(path: Path) -> dict:
    """Analyze the fixed-seed subset of explicitly modeled random sources."""

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from adctoolbox import analyze_spectrum
    from models.behavioral.sar_adc import SarAdcModel
    from scripts.analysis.run_behavioral_baseline import derive_error_budget, load_spec

    data = _load_csv(path)
    _, codes = _valid_samples(data)
    sample_count = 16384
    if len(codes) != sample_count:
        raise AssertionError(f"allocated-noise samples={len(codes)} != {sample_count}")

    coherent_bin = 7373
    sample_rate_hz = 10e6
    input_frequency_hz = sample_rate_hz * coherent_bin / sample_count
    differential_peak_v = 0.9 * 10.0 ** (-1.0 / 20.0)
    sample_time = FIRST_SAMPLE_CROSSING_S + np.arange(sample_count) / sample_rate_hz
    input_diff = differential_peak_v * np.sin(
        2.0 * np.pi * input_frequency_hz * sample_time
    )
    model = SarAdcModel(10, (-0.9, 0.9))
    ideal_codes = model.unsigned_codes(model.convert(input_diff))
    code_error = codes.astype(float) - ideal_codes.astype(float)

    reconstructed = -0.9 + codes.astype(float) * (1.8 / 1024.0)
    metrics = analyze_spectrum(
        reconstructed - np.mean(reconstructed),
        fs=sample_rate_hz,
        max_scale_range=(-0.9, 0.9),
        win_type="rectangular",
        side_bin=0,
        create_plot=False,
    )
    sndr_db = float(metrics["sndr_dbc"])
    enob_bits = float(metrics["enob"])

    budget = derive_error_budget(
        load_spec(PROJECT_ROOT / "config" / "design_spec.yaml")
    )
    partial_error_rms_v = float(
        np.sqrt(
            budget["quantization_noise_rms_v"] ** 2
            + budget["sampling_noise_rms_v"] ** 2
            + budget["comparator_noise_rms_v"] ** 2
            + budget["reference_switching_noise_rms_v"] ** 2
        )
    )
    partial_sndr_db = float(
        20.0 * np.log10(budget["dynamic_signal_rms_v"] / partial_error_rms_v)
    )
    sndr_delta_db = sndr_db - partial_sndr_db
    if (
        sndr_db < 55.94
        or enob_bits < 9.0
        or sndr_db >= 60.95402278783933
        or abs(sndr_delta_db) > 1.0
    ):
        raise AssertionError(
            "allocated-noise gates failed: "
            f"SNDR={sndr_db}, ENOB={enob_bits}, delta={sndr_delta_db}"
        )
    return {
        "sample_count": int(len(codes)),
        "coherent_bin": coherent_bin,
        "input_frequency_hz": input_frequency_hz,
        "sampling_noise_rms_v": budget["sampling_noise_rms_v"],
        "comparator_noise_rms_v": budget["comparator_noise_rms_v"],
        "reference_noise_rms_v": budget["reference_switching_noise_rms_v"],
        "partial_rss_error_rms_v": partial_error_rms_v,
        "partial_rss_sndr_db": partial_sndr_db,
        "sndr_db": sndr_db,
        "snr_db": float(metrics["snr_dbc"]),
        "sfdr_db": float(metrics["sfdr_dbc"]),
        "thd_db": float(metrics["thd_dbc"]),
        "enob_bits": enob_bits,
        "sndr_delta_from_partial_rss_db": sndr_delta_db,
        "changed_code_count": int(np.count_nonzero(code_error)),
        "code_error_mean_lsb": float(np.mean(code_error)),
        "code_error_rms_lsb": float(np.sqrt(np.mean(code_error**2))),
        "code_error_abs_max_lsb": float(np.max(np.abs(code_error))),
    }


def analyze_cases(cases: list[str], output_root: Path) -> dict:
    analyzers = {
        "timing": analyze_timing,
        "static": analyze_static,
        "dynamic": analyze_dynamic,
        "allocated_noise": analyze_allocated_noise,
    }
    summary: dict[str, object] = {
        "model": "sar_adc_ideal_10b",
        "cases": {},
    }
    for case in cases:
        summary["cases"][case] = analyzers[case](output_root / case / "tran.csv")
    with (output_root / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("none", "evas", "spectre"), default="none")
    parser.add_argument("--cases", nargs="+", choices=ALL_CASES, default=list(CASES))
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    cases = list(dict.fromkeys(args.cases))

    run_records = []
    for case in cases:
        if args.backend == "spectre":
            run_records.append(run_spectre(case, args.output))
        elif args.backend == "evas":
            run_records.append(run_evas(case, args.output))
    if run_records:
        print(json.dumps({"runs": run_records}, indent=2, default=str))
    if args.analyze:
        print(json.dumps(analyze_cases(cases, args.output), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
