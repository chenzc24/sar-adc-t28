#!/usr/bin/env python3
"""Analyze finite-Cboot bootstrap transients without hiding failure modes."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "output" / "bootstrap_driver_design" / "spectre" / "run_summary.json"
DEFAULT_OUTPUT = ROOT / "output" / "bootstrap_driver_design" / "analysis"

DEVICE_NODES = {
    "MN1": {"D": "VDD", "G": "P2", "S": "P1", "B": "VSS"},
    "MN2": {"D": "VDD", "G": "P1", "S": "P2", "B": "VSS"},
    "MN3": {"D": "VDD", "G": "P1", "S": "BTOP", "B": "VSS"},
    "MN12": {"D": "BBOT", "G": "PHIB", "S": "VSS", "B": "VSS"},
    "MP8": {"D": "BTOP", "G": "CTRL", "S": "G", "B": "G"},
    "MP4": {"D": "CTRL", "G": "PHI", "S": "VDD", "B": "VDD"},
    "MN5": {"D": "CTRL", "G": "PHI", "S": "BBOT", "B": "VSS"},
    "MN13": {"D": "CTRL", "G": "G", "S": "BBOT", "B": "VSS"},
    "MN7": {"D": "G", "G": "VDD", "S": "GCLAMP", "B": "VSS"},
    "MN10": {"D": "GCLAMP", "G": "PHIB", "S": "VSS", "B": "VSS"},
    "MN9": {"D": "BBOT", "G": "G", "S": "VIN", "B": "VIN"},
    "MN11": {"D": "VOUT", "G": "G", "S": "VIN", "B": "VIN"},
}


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


def _stress_summary(signals: dict[str, np.ndarray]) -> tuple[dict[str, Any], dict[str, Any]]:
    records: dict[str, Any] = {}
    worst = {"device": None, "metric": None, "value_v": -1.0}
    for device, nodes in DEVICE_NODES.items():
        terminal = {name: signals[node] for name, node in nodes.items()}
        metrics = {
            "max_abs_vgs_v": float(np.max(np.abs(terminal["G"] - terminal["S"]))),
            "max_abs_vgd_v": float(np.max(np.abs(terminal["G"] - terminal["D"]))),
            "max_abs_vgb_v": float(np.max(np.abs(terminal["G"] - terminal["B"]))),
            "max_abs_vds_v": float(np.max(np.abs(terminal["D"] - terminal["S"]))),
            "max_abs_vbs_v": float(np.max(np.abs(terminal["B"] - terminal["S"]))),
            "max_abs_vbd_v": float(np.max(np.abs(terminal["B"] - terminal["D"]))),
        }
        records[device] = metrics
        for metric, value in metrics.items():
            if value > worst["value_v"]:
                worst = {"device": device, "metric": metric, "value_v": value}
    return records, worst


def _analyze_case(record: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    signals = {key: np.asarray(value, dtype=float) for key, value in record["signals"].items()}
    time = signals["time"]
    signals["VSS"] = np.zeros_like(time)
    timing = config["timing"]
    targets = config["targets"]
    sample_start = float(timing["sample_start_s"])
    sample_end = float(timing["sample_end_s"])
    hold_measure = float(timing["hold_measure_s"])
    measure_start = sample_start + 2e-9
    measure_end = sample_end - 1e-9
    target = float(record["input_v"])
    sample_mask = (time >= measure_start) & (time <= measure_end)
    gate_overdrive = signals["G"] - signals["VIN"]
    boot_voltage = signals["BTOP"] - signals["BBOT"]
    sample_value = _interp(time, signals["VOUT"], measure_end)
    hold_value = _interp(time, signals["VOUT"], hold_measure)
    acquisition_error = sample_value - target
    hold_error = hold_value - target
    stress, worst_stress = _stress_summary(signals)
    settling = _settling_time(
        time,
        signals["VOUT"],
        target,
        sample_start,
        measure_end,
        float(targets["maximum_acquisition_error_v"]),
    )
    result = {
        "name": record["name"],
        "process": record["process"],
        "supply_v": float(record["supply_v"]),
        "temperature_c": float(record["temperature_c"]),
        "input_v": target,
        "cboot_f": float(record["cboot_f"]),
        "main_switch_width_m": (
            None if record.get("main_switch_width_m") is None
            else float(record["main_switch_width_m"])
        ),
        "spectre_ok": bool(record["spectre_ok"]),
        "sample_value_v": sample_value,
        "acquisition_error_v": acquisition_error,
        "absolute_acquisition_error_v": abs(acquisition_error),
        "settling_time_s": settling,
        "minimum_gate_overdrive_v": float(np.min(gate_overdrive[sample_mask])),
        "maximum_gate_overdrive_v": float(np.max(gate_overdrive[sample_mask])),
        "bootstrap_voltage_start_v": _interp(time, boot_voltage, measure_start),
        "bootstrap_voltage_end_v": _interp(time, boot_voltage, measure_end),
        "bootstrap_droop_v": float(np.max(boot_voltage[sample_mask]) - np.min(boot_voltage[sample_mask])),
        "hold_value_v": hold_value,
        "hold_step_v": hold_value - sample_value,
        "hold_error_v": hold_error,
        "peak_gate_v": float(np.max(signals["G"])),
        "off_gate_v": _interp(time, signals["G"], float(timing["precharge_end_s"])),
        "device_stress": stress,
        "worst_terminal_difference": worst_stress,
    }
    result["passes_acquisition"] = (
        result["spectre_ok"]
        and result["absolute_acquisition_error_v"] <= float(targets["maximum_acquisition_error_v"])
    )
    result["passes_gate_overdrive"] = (
        result["minimum_gate_overdrive_v"] >= float(targets["minimum_gate_overdrive_v"])
        and result["maximum_gate_overdrive_v"] <= float(targets["maximum_gate_overdrive_v"])
    )
    result["passes_bootstrap_droop"] = (
        result["bootstrap_droop_v"] <= float(targets["maximum_bootstrap_droop_v"])
    )
    result["passes_hold_error"] = (
        abs(result["hold_error_v"]) <= float(
            targets.get("maximum_hold_error_v", targets["maximum_acquisition_error_v"])
        )
    )
    result["passes_declared_dynamic_targets"] = (
        result["passes_acquisition"]
        and result["passes_gate_overdrive"]
        and result["passes_bootstrap_droop"]
        and result["passes_hold_error"]
    )
    return result


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "name", "input_v", "cboot_f", "main_switch_width_m",
        "absolute_acquisition_error_v", "settling_time_s",
        "minimum_gate_overdrive_v", "maximum_gate_overdrive_v", "bootstrap_droop_v",
        "hold_step_v", "hold_error_v", "passes_hold_error", "peak_gate_v",
        "passes_declared_dynamic_targets",
    ]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: row.get(key) for key in fields} for row in rows)


def _plot(path: Path, run: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    by_name = {record["name"]: record for record in run["records"]}
    candidates = sorted(
        rows,
        key=lambda row: (
            row["input_v"], row["cboot_f"], row.get("main_switch_width_m") or 0.0
        ),
    )
    widths = sorted({
        row["main_switch_width_m"] for row in candidates
        if row.get("main_switch_width_m") is not None
    })
    chosen = [row for row in candidates if np.isclose(row["cboot_f"], 2e-13)]
    if len(widths) > 1:
        chosen = [row for row in chosen if np.isclose(row["input_v"], 0.45)]
    fig, axes = plt.subplots(3, 1, figsize=(9, 9), sharex=True)
    for row in chosen:
        record = by_name[row["name"]]
        time_ns = np.asarray(record["signals"]["time"]) * 1e9
        vin = np.asarray(record["signals"]["VIN"])
        vout = np.asarray(record["signals"]["VOUT"])
        gate = np.asarray(record["signals"]["G"])
        btop = np.asarray(record["signals"]["BTOP"])
        bbot = np.asarray(record["signals"]["BBOT"])
        if row.get("main_switch_width_m") is None:
            label = f"VIN={row['input_v']:.2f} V"
        else:
            label = f"W={row['main_switch_width_m'] * 1e6:.2f} um"
        axes[0].plot(time_ns, vin, "--", label=f"{label} input")
        axes[0].plot(time_ns, vout, label=f"{label} output")
        axes[1].plot(time_ns, gate - vin, label=label)
        axes[2].plot(time_ns, btop - bbot, label=label)
    axes[0].set_ylabel("Input/output (V)")
    axes[1].set_ylabel("Main VGS (V)")
    axes[2].set_ylabel("CBOOT voltage (V)")
    axes[2].set_xlabel("Time (ns)")
    for axis in axes:
        axis.grid(True, alpha=0.25)
        axis.legend(fontsize=8, ncol=2)
        axis.set_xlim(195, 275)
    title = "T28 bootstrap prototype, CBOOT=200 fF"
    if len(widths) > 1:
        title += ", VIN=0.45 V width screen"
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    run = json.loads(args.input.read_text(encoding="utf-8"))
    config = run["configuration"]
    rows = [_analyze_case(record, config) for record in run["records"] if record["signals"]]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    passing = [row for row in rows if row["passes_declared_dynamic_targets"]]
    summary = {
        "scope": run["scope"],
        "oa_export": run["oa_export"],
        "oa_export_sha256": run["oa_export_sha256"],
        "simulator": run["simulator"],
        "case_count": len(rows),
        "spectre_failure_count": int(run["failed_case_count"]),
        "declared_dynamic_pass_count": len(passing),
        "scope_limits": config["scope_limits"],
        "cases": rows,
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    _write_csv(args.output_dir / "pvt_summary.csv", rows)
    _plot(args.output_dir / "waveforms.png", run, rows)
    print(json.dumps({
        "cases": len(rows),
        "spectre_failures": run["failed_case_count"],
        "declared_dynamic_passes": len(passing),
        "summary": str(args.output_dir / "summary.json"),
    }, indent=2))
    return 0 if rows and not run["failed_case_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
