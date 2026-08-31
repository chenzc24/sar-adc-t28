#!/usr/bin/env python3
"""Analyze bootstrap held-error ablation and differential diagnostics."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "output" / "bootstrap_hold_ablation" / "spectre" / "run_summary.json"
DEFAULT_OUTPUT = ROOT / "output" / "bootstrap_hold_ablation" / "analysis"


def _interp(time: np.ndarray, values: np.ndarray, point: float) -> float:
    return float(np.interp(point, time, values))


def _settling_time(
    time: np.ndarray,
    values: np.ndarray,
    target: float,
    start: float,
    end: float,
    tolerance: float,
) -> float | None:
    mask = (time >= start) & (time <= end)
    local_t = time[mask]
    local_error = np.abs(values[mask] - target)
    if local_t.size == 0:
        return None
    future_bad = np.maximum.accumulate((local_error > tolerance)[::-1])[::-1]
    indices = np.flatnonzero(~future_bad)
    return float(local_t[indices[0]] - start) if indices.size else None


def _arrays(record: dict[str, Any]) -> dict[str, np.ndarray]:
    return {
        key: np.asarray(value, dtype=float)
        for key, value in record["signals"].items()
    }


def _analyze_single(record: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    signals = _arrays(record)
    timing = config["timing"]
    targets = config["targets"]
    time = signals["time"]
    sample_start = float(timing["sample_start_s"])
    sample_end = float(timing["sample_end_s"])
    pre_point = sample_end - 1e-9
    post_point = sample_end + float(record["gate_fall_s"]) + 0.5e-9
    hold_point = float(timing["hold_measure_s"])
    target = float(record["input_v"])
    vout = signals["VOUT"]
    sample_value = _interp(time, vout, pre_point)
    post_value = _interp(time, vout, post_point)
    hold_value = _interp(time, vout, hold_point)
    gate_key = "XB.G" if record["mode"] == "full_single" else "G"
    gate = signals[gate_key]
    vin = signals["VIN"]
    result = {
        "name": record["name"],
        "mode": record["mode"],
        "purpose": record["purpose"],
        "input_v": target,
        "differential_input_v": None,
        "load_f": float(record["load_f"]),
        "gate_fall_s": float(record["gate_fall_s"]),
        "spectre_ok": bool(record["spectre_ok"]),
        "settling_time_s": _settling_time(
            time, vout, target, sample_start, pre_point,
            float(targets["maximum_acquisition_error_v"]),
        ),
        "sample_value_v": sample_value,
        "acquisition_error_v": sample_value - target,
        "turnoff_step_v": post_value - sample_value,
        "post_turnoff_value_v": post_value,
        "hold_drift_v": hold_value - post_value,
        "hold_value_v": hold_value,
        "held_error_v": hold_value - target,
        "held_common_mode_error_v": None,
        "off_gate_v": _interp(time, gate, hold_point),
        "off_vgs_v": _interp(time, gate - vin, hold_point),
        "off_gate_p_v": None,
        "off_gate_n_v": None,
        "off_vgs_p_v": None,
        "off_vgs_n_v": None,
        "minimum_sample_vgs_v": float(np.min(
            (gate - vin)[(time >= sample_start + 2e-9) & (time <= pre_point)]
        )),
        "maximum_sample_vgs_v": float(np.max(
            (gate - vin)[(time >= sample_start + 2e-9) & (time <= pre_point)]
        )),
    }
    result["passes_acquisition"] = (
        abs(result["acquisition_error_v"]) <= float(targets["maximum_acquisition_error_v"])
    )
    result["passes_held_error"] = (
        abs(result["held_error_v"]) <= float(targets["maximum_held_error_v"])
    )
    return result


def _analyze_diff(record: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    signals = _arrays(record)
    timing = config["timing"]
    targets = config["targets"]
    time = signals["time"]
    sample_start = float(timing["sample_start_s"])
    sample_end = float(timing["sample_end_s"])
    pre_point = sample_end - 1e-9
    post_point = sample_end + float(record["gate_fall_s"]) + 0.5e-9
    hold_point = float(timing["hold_measure_s"])
    target = float(record["differential_input_v"])
    vout_diff = signals["VOUTP"] - signals["VOUTN"]
    vout_cm = 0.5 * (signals["VOUTP"] + signals["VOUTN"])
    sample_value = _interp(time, vout_diff, pre_point)
    post_value = _interp(time, vout_diff, post_point)
    hold_value = _interp(time, vout_diff, hold_point)
    cm_target = float(config["conditions"]["common_mode_v"])
    gate_p_key = "XBP.G" if record["mode"] == "full_diff" else "GP"
    gate_n_key = "XBN.G" if record["mode"] == "full_diff" else "GN"
    mask = (time >= sample_start + 2e-9) & (time <= pre_point)
    vgs_p = signals[gate_p_key] - signals["VINP"]
    vgs_n = signals[gate_n_key] - signals["VINN"]
    result = {
        "name": record["name"],
        "mode": record["mode"],
        "purpose": record["purpose"],
        "input_v": None,
        "differential_input_v": target,
        "load_f": float(record["load_f"]),
        "gate_fall_s": float(record["gate_fall_s"]),
        "spectre_ok": bool(record["spectre_ok"]),
        "settling_time_s": _settling_time(
            time, vout_diff, target, sample_start, pre_point,
            float(targets["maximum_acquisition_error_v"]),
        ),
        "sample_value_v": sample_value,
        "acquisition_error_v": sample_value - target,
        "turnoff_step_v": post_value - sample_value,
        "post_turnoff_value_v": post_value,
        "hold_drift_v": hold_value - post_value,
        "hold_value_v": hold_value,
        "held_error_v": hold_value - target,
        "held_common_mode_error_v": _interp(time, vout_cm, hold_point) - cm_target,
        "off_gate_v": None,
        "off_vgs_v": None,
        "off_gate_p_v": _interp(time, signals[gate_p_key], hold_point),
        "off_gate_n_v": _interp(time, signals[gate_n_key], hold_point),
        "off_vgs_p_v": _interp(time, vgs_p, hold_point),
        "off_vgs_n_v": _interp(time, vgs_n, hold_point),
        "minimum_sample_vgs_v": float(min(np.min(vgs_p[mask]), np.min(vgs_n[mask]))),
        "maximum_sample_vgs_v": float(max(np.max(vgs_p[mask]), np.max(vgs_n[mask]))),
    }
    result["passes_acquisition"] = (
        abs(result["acquisition_error_v"]) <= float(targets["maximum_acquisition_error_v"])
    )
    result["passes_held_error"] = (
        abs(result["held_error_v"]) <= float(targets["maximum_held_error_v"])
    )
    return result


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "name", "mode", "purpose", "input_v", "differential_input_v", "load_f",
        "gate_fall_s", "settling_time_s", "acquisition_error_v", "turnoff_step_v",
        "hold_drift_v", "held_error_v", "held_common_mode_error_v",
        "off_gate_v", "off_vgs_v", "off_gate_p_v", "off_gate_n_v",
        "off_vgs_p_v", "off_vgs_n_v",
        "minimum_sample_vgs_v", "maximum_sample_vgs_v", "passes_acquisition",
        "passes_held_error",
    ]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field) for field in fields} for row in rows)


def _record_map(run: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {record["name"]: record for record in run["records"]}


def _nominal_row(
    rows: list[dict[str, Any]], mode: str, signal: float
) -> dict[str, Any]:
    field = "input_v" if mode.endswith("single") else "differential_input_v"
    candidates = [
        row for row in rows
        if row["mode"] == mode and row["purpose"] == "nominal_mode_compare"
        and np.isclose(float(row[field]), signal)
    ]
    if len(candidates) != 1:
        raise ValueError(f"Expected one nominal {mode}/{signal} row, got {len(candidates)}")
    return candidates[0]


def _plot_waveforms(path: Path, run: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    records = _record_map(run)
    single_rows = [
        _nominal_row(rows, "full_single", 0.05),
        _nominal_row(rows, "isolated_single", 0.05),
        _nominal_row(rows, "absolute_single", 0.05),
    ]
    diff_rows = [
        _nominal_row(rows, "full_diff", 0.8),
        _nominal_row(rows, "isolated_diff", 0.8),
        _nominal_row(rows, "absolute_diff", 0.8),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), sharex=True)
    for row in single_rows:
        record = records[row["name"]]
        signals = _arrays(record)
        t = signals["time"] * 1e9
        label = {
            "full_single": "full driver",
            "isolated_single": "relative-off main",
            "absolute_single": "absolute-off main",
        }[row["mode"]]
        axes[0, 0].plot(t, signals["VOUT"], label=label)
        gate_key = "XB.G" if row["mode"] == "full_single" else "G"
        axes[1, 0].plot(t, signals[gate_key] - signals["VIN"], label=label)
    for row in diff_rows:
        record = records[row["name"]]
        signals = _arrays(record)
        t = signals["time"] * 1e9
        label = {
            "full_diff": "full pair",
            "isolated_diff": "relative-off pair",
            "absolute_diff": "absolute-off pair",
        }[row["mode"]]
        axes[0, 1].plot(t, signals["VOUTP"] - signals["VOUTN"], label=label)
        axes[1, 1].plot(t, 0.5 * (signals["VOUTP"] + signals["VOUTN"]), label=label)
    axes[0, 0].set_ylabel("Single-ended VOUT (V)")
    axes[1, 0].set_ylabel("Main VGS (V)")
    axes[0, 1].set_ylabel("Differential VOUT (V)")
    axes[1, 1].set_ylabel("Output common mode (V)")
    for axis in axes.ravel():
        axis.grid(True, alpha=0.25)
        axis.legend()
        axis.set_xlim(204, 274)
        axis.set_xlabel("Time (ns)")
    fig.suptitle("Bootstrap hold-error ablation, TT / 0.9 V / 27 C")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_sensitivity(path: Path, rows: list[dict[str, Any]]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    nominal_load = 2.195e-13
    nominal_edge = 1.0e-10
    for mode, mode_label in (
        ("isolated_single", "relative-off"),
        ("absolute_single", "absolute-off"),
    ):
        for input_v in (0.05, 0.85):
            load_rows = sorted([
                row for row in rows
                if row["mode"] == mode
                and np.isclose(float(row["input_v"]), input_v)
                and np.isclose(row["gate_fall_s"], nominal_edge, rtol=1e-9, atol=0.0)
            ], key=lambda row: row["load_f"])
            edge_rows = sorted([
                row for row in rows
                if row["mode"] == mode
                and np.isclose(float(row["input_v"]), input_v)
                and np.isclose(row["load_f"], nominal_load, rtol=1e-9, atol=0.0)
            ], key=lambda row: row["gate_fall_s"])
            label = f"{mode_label}, VIN={input_v:.2f} V"
            axes[0].plot(
                [row["load_f"] * 1e15 for row in load_rows],
                [row["held_error_v"] * 1e3 for row in load_rows], "o-",
                label=label,
            )
            axes[1].semilogx(
                [row["gate_fall_s"] * 1e12 for row in edge_rows],
                [row["held_error_v"] * 1e3 for row in edge_rows], "o-",
                label=label,
            )
    axes[0].set_xlabel("Hold capacitance (fF)")
    axes[1].set_xlabel("Ideal gate fall time (ps)")
    for axis in axes:
        axis.set_ylabel("Held error (mV)")
        axis.grid(True, alpha=0.25)
        axis.legend()
        axis.axhline(0.439, color="black", linestyle="--", linewidth=0.8)
        axis.axhline(-0.439, color="black", linestyle="--", linewidth=0.8)
    fig.suptitle("Isolated-main-switch held-error sensitivity")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    nominal = [row for row in rows if row["purpose"] == "nominal_mode_compare"]
    by_mode: dict[str, Any] = {}
    for mode in (
        "full_single", "isolated_single", "absolute_single",
        "full_diff", "isolated_diff", "absolute_diff",
    ):
        selected = [row for row in nominal if row["mode"] == mode]
        signal_field = "input_v" if mode.endswith("single") else "differential_input_v"
        x = np.asarray([row[signal_field] for row in selected], dtype=float)
        y = np.asarray([row["held_error_v"] for row in selected], dtype=float)
        fit = np.polyfit(x, y, 1)
        by_mode[mode] = {
            "case_count": len(selected),
            "held_pass_count": sum(bool(row["passes_held_error"]) for row in selected),
            "maximum_absolute_acquisition_error_v": max(
                abs(row["acquisition_error_v"]) for row in selected
            ),
            "maximum_absolute_turnoff_step_v": max(
                abs(row["turnoff_step_v"]) for row in selected
            ),
            "maximum_absolute_hold_drift_v": max(
                abs(row["hold_drift_v"]) for row in selected
            ),
            "maximum_absolute_held_error_v": max(
                abs(row["held_error_v"]) for row in selected
            ),
            "linear_error_gain_fraction": float(fit[0]),
            "linear_error_offset_v": float(fit[1]),
            "maximum_linear_fit_residual_v": float(
                np.max(np.abs(y - np.polyval(fit, x)))
            ),
        }
    return by_mode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    run = json.loads(args.input.read_text(encoding="utf-8"))
    config = run["configuration"]
    rows = [
        (_analyze_single(record, config) if record["mode"].endswith("single")
         else _analyze_diff(record, config))
        for record in run["records"] if record["signals"]
    ]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    aggregate = _aggregate(rows)
    full_gain = aggregate["full_diff"]["linear_error_gain_fraction"]
    absolute_gain = aggregate["absolute_diff"]["linear_error_gain_fraction"]
    full_max = aggregate["full_diff"]["maximum_absolute_held_error_v"]
    absolute_max = aggregate["absolute_diff"]["maximum_absolute_held_error_v"]
    summary = {
        "scope": run["scope"],
        "oa_export": run["oa_export"],
        "oa_export_sha256": run["oa_export_sha256"],
        "sar_bootstrap_subckt_sha256": run["sar_bootstrap_subckt_sha256"],
        "simulator": run["simulator"],
        "case_count": len(rows),
        "spectre_failure_count": int(run["failed_case_count"]),
        "aggregate": aggregate,
        "diagnostic_comparison": {
            "driver_added_differential_gain_error_fraction": full_gain - absolute_gain,
            "absolute_off_main_fraction_of_full_max_error": absolute_max / full_max,
            "relative_off_pair_max_error_v": aggregate["isolated_diff"][
                "maximum_absolute_held_error_v"
            ],
        },
        "scope_limits": config["scope_limits"],
        "cases": rows,
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    _write_csv(args.output_dir / "case_summary.csv", rows)
    _plot_waveforms(args.output_dir / "waveforms.png", run, rows)
    _plot_sensitivity(args.output_dir / "sensitivity.png", rows)
    print(json.dumps({
        "cases": len(rows),
        "spectre_failures": run["failed_case_count"],
        "aggregate": summary["aggregate"],
        "summary": str(args.output_dir / "summary.json"),
    }, indent=2))
    return 0 if rows and not run["failed_case_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
