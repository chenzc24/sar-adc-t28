#!/usr/bin/env python3
"""Analyze bootstrap-driver sizing/non-overlap screens without calibration."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = (
    ROOT / "output" / "bootstrap_driver_error_reduction" / "spectre"
    / "run_summary.json"
)
DEFAULT_OUTPUT = ROOT / "output" / "bootstrap_driver_error_reduction" / "analysis"

DEVICE_NODES = {
    "MN1": {"D": "VDD", "G": "P2", "S": "P1", "B": "VSS"},
    "MN2": {"D": "VDD", "G": "P1", "S": "P2", "B": "VSS"},
    "MN3": {"D": "VDD", "G": "P1", "S": "BTOP", "B": "VSS"},
    "MN7": {"D": "G", "G": "VDD", "S": "GCLAMP", "B": "VSS"},
    "MN10": {"D": "GCLAMP", "G": "PHIB", "S": "VSS", "B": "VSS"},
    "MP8": {"D": "BTOP", "G": "CTRL", "S": "G", "B": "G"},
}


def _arrays(record: dict[str, Any]) -> dict[str, np.ndarray]:
    return {key: np.asarray(value, dtype=float)
            for key, value in record["signals"].items()}


def _interp(time: np.ndarray, values: np.ndarray, point: float) -> float:
    return float(np.interp(point, time, values))


def _settling_time(
    time: np.ndarray, values: np.ndarray, target: float,
    start: float, end: float, tolerance: float,
) -> float | None:
    mask = (time >= start) & (time <= end)
    local_t = time[mask]
    local_error = np.abs(values[mask] - target)
    if local_t.size == 0:
        return None
    future_bad = np.maximum.accumulate((local_error > tolerance)[::-1])[::-1]
    indices = np.flatnonzero(~future_bad)
    return float(local_t[indices[0]] - start) if indices.size else None


def _side_nodes(
    signals: dict[str, np.ndarray], prefix: str, suffix: str,
    supply: float,
) -> dict[str, np.ndarray]:
    time = signals["time"]
    result = {
        "VDD": np.full_like(time, supply), "VSS": np.zeros_like(time),
        "PHI": signals["PHI"], "PHIB": signals["PHIB"],
        "VIN": signals[f"VIN{suffix}" if suffix else "VIN"],
        "VOUT": signals[f"VOUT{suffix}" if suffix else "VOUT"],
    }
    for node in ("G", "GCLAMP", "CTRL", "BTOP", "BBOT", "P1", "P2"):
        result[node] = signals[f"{prefix}.{node}"]
    return result


def _stress(nodes: dict[str, np.ndarray]) -> tuple[dict[str, Any], dict[str, Any]]:
    records: dict[str, Any] = {}
    worst = {"device": None, "metric": None, "value_v": -1.0}
    for device, mapping in DEVICE_NODES.items():
        terminal = {name: nodes[node] for name, node in mapping.items()}
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


def _analyze(record: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    signals = _arrays(record)
    timing, targets = config["timing"], config["targets"]
    supply = float(config["conditions"]["supply_v"])
    time = signals["time"]
    sample_start = float(timing["sample_start_s"])
    sample_end = float(timing["sample_end_s"])
    pre = sample_end - 1e-9
    immediate = sample_end + 0.6e-9
    discharged = sample_end + float(record["nonoverlap_s"]) + 0.8e-9
    hold = float(timing["hold_measure_s"])
    mask = (time >= sample_start + 2e-9) & (time <= pre)
    result: dict[str, Any] = {
        key: record[key] for key in (
            "name", "phase", "candidate", "input_kind", "input_v",
            "mn7_multi", "mn10_multi", "mp8_multi", "nonoverlap_s",
            "spectre_ok",
        )
    }
    if record["input_kind"] == "diff":
        sides = [
            _side_nodes(signals, "XBP", "P", supply),
            _side_nodes(signals, "XBN", "N", supply),
        ]
        output = sides[0]["VOUT"] - sides[1]["VOUT"]
        target = float(record["input_v"])
        common_mode = 0.5 * (sides[0]["VOUT"] + sides[1]["VOUT"])
        result["held_common_mode_error_v"] = (
            _interp(time, common_mode, hold)
            - float(config["conditions"]["common_mode_v"])
        )
    else:
        sides = [_side_nodes(signals, "XB", "", supply)]
        output = sides[0]["VOUT"]
        target = float(record["input_v"])
        result["held_common_mode_error_v"] = None
    sample_value = _interp(time, output, pre)
    immediate_value = _interp(time, output, immediate)
    discharged_value = _interp(time, output, discharged)
    held_value = _interp(time, output, hold)
    vgs = [side["G"] - side["VIN"] for side in sides]
    boot = [side["BTOP"] - side["BBOT"] for side in sides]
    stresses = [_stress(side) for side in sides]
    worst = max((item[1] for item in stresses), key=lambda item: item["value_v"])
    result.update({
        "sample_value_v": sample_value,
        "acquisition_error_v": sample_value - target,
        "settling_time_s": _settling_time(
            time, output, target, sample_start, pre,
            float(targets["maximum_acquisition_error_v"]),
        ),
        "immediate_turnoff_step_v": immediate_value - sample_value,
        "discharge_step_v": discharged_value - immediate_value,
        "hold_drift_v": held_value - discharged_value,
        "held_value_v": held_value,
        "held_error_v": held_value - target,
        "minimum_sample_vgs_v": min(float(np.min(value[mask])) for value in vgs),
        "maximum_sample_vgs_v": max(float(np.max(value[mask])) for value in vgs),
        "maximum_bootstrap_droop_v": max(
            float(np.max(value[mask]) - np.min(value[mask])) for value in boot
        ),
        "off_gate_p_v": _interp(time, sides[0]["G"], hold),
        "off_gate_n_v": (
            _interp(time, sides[1]["G"], hold) if len(sides) == 2 else None
        ),
        "worst_terminal_difference": worst,
        "device_stress_by_side": [item[0] for item in stresses],
    })
    result["passes_acquisition"] = (
        abs(result["acquisition_error_v"])
        <= float(targets["maximum_acquisition_error_v"])
    )
    result["passes_held_error"] = (
        abs(result["held_error_v"]) <= float(targets["maximum_held_error_v"])
    )
    result["passes_sample_vgs"] = (
        result["minimum_sample_vgs_v"] >= float(targets["minimum_sample_vgs_v"])
        and result["maximum_sample_vgs_v"] <= float(targets["maximum_sample_vgs_v"])
    )
    return result


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "name", "phase", "candidate", "input_kind", "input_v",
        "mn7_multi", "mn10_multi", "mp8_multi", "nonoverlap_s",
        "acquisition_error_v", "settling_time_s", "immediate_turnoff_step_v",
        "discharge_step_v", "hold_drift_v", "held_error_v",
        "held_common_mode_error_v", "minimum_sample_vgs_v",
        "maximum_sample_vgs_v", "maximum_bootstrap_droop_v",
        "off_gate_p_v", "off_gate_n_v", "passes_acquisition",
        "passes_held_error", "passes_sample_vgs",
    ]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field) for field in fields} for row in rows)


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["candidate"], []).append(row)
    result: dict[str, Any] = {}
    for candidate, selected in grouped.items():
        diff = [row for row in selected if row["input_kind"] == "diff"]
        signal = np.asarray([row["input_v"] for row in diff], dtype=float)
        error = np.asarray([row["held_error_v"] for row in diff], dtype=float)
        fit = np.polyfit(signal, error, 1) if len(diff) >= 2 else None
        result[candidate] = {
            "case_count": len(selected),
            "maximum_absolute_acquisition_error_v": max(
                abs(row["acquisition_error_v"]) for row in selected
            ),
            "maximum_absolute_held_error_v": max(
                abs(row["held_error_v"]) for row in selected
            ),
            "minimum_sample_vgs_v": min(row["minimum_sample_vgs_v"] for row in selected),
            "maximum_sample_vgs_v": max(row["maximum_sample_vgs_v"] for row in selected),
            "maximum_terminal_difference_v": max(
                row["worst_terminal_difference"]["value_v"] for row in selected
            ),
            "differential_error_gain_fraction": None if fit is None else float(fit[0]),
            "differential_error_offset_v": None if fit is None else float(fit[1]),
            "maximum_differential_fit_residual_v": (
                None if fit is None else float(np.max(np.abs(error - np.polyval(fit, signal))))
            ),
        }
    return result


def _plot_screen(path: Path, rows: list[dict[str, Any]]) -> None:
    selected = sorted(
        [row for row in rows if row["input_kind"] == "diff"],
        key=lambda row: abs(row["held_error_v"]), reverse=True,
    )
    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    x = np.arange(len(selected))
    axes[0].bar(x, [row["held_error_v"] * 1e3 for row in selected])
    axes[0].axhline(0.439, color="black", linestyle="--", linewidth=0.8)
    axes[0].axhline(-0.439, color="black", linestyle="--", linewidth=0.8)
    axes[0].set_ylabel("Held differential error (mV)")
    axes[1].plot(x, [row["off_gate_p_v"] * 1e3 for row in selected], "o-", label="P-side")
    axes[1].plot(x, [row["off_gate_n_v"] * 1e3 for row in selected], "o-", label="N-side")
    axes[1].set_ylabel("Gate at hold (mV)")
    axes[1].set_xticks(x, [row["candidate"] for row in selected], rotation=45, ha="right")
    axes[1].legend()
    for axis in axes:
        axis.grid(True, alpha=0.25)
    fig.suptitle("Bootstrap driver held-error reduction screen")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_confirmation(
    path: Path, run: dict[str, Any], rows: list[dict[str, Any]],
) -> None:
    records = {record["name"]: record for record in run["records"]}
    candidates = sorted({row["candidate"] for row in rows})
    fig, axes = plt.subplots(2, 1, figsize=(10, 7))
    for candidate in candidates:
        diff = sorted(
            [row for row in rows if row["candidate"] == candidate
             and row["input_kind"] == "diff"],
            key=lambda row: row["input_v"],
        )
        axes[0].plot([row["input_v"] for row in diff],
                     [row["held_error_v"] * 1e3 for row in diff], "o-",
                     label=candidate)
        endpoint = next((row for row in diff if np.isclose(row["input_v"], 0.8)), None)
        if endpoint:
            signals = _arrays(records[endpoint["name"]])
            mask = (signals["time"] >= 248e-9) & (signals["time"] <= 274e-9)
            axes[1].plot(signals["time"][mask] * 1e9,
                         (signals["VOUTP"][mask] - signals["VOUTN"][mask]
                          - endpoint["input_v"]) * 1e3,
                         label=candidate)
    axes[0].axhline(0.439, color="black", linestyle="--", linewidth=0.8)
    axes[0].axhline(-0.439, color="black", linestyle="--", linewidth=0.8)
    axes[0].set_ylabel("Held differential error (mV)")
    axes[0].set_xlabel("Differential input (V)")
    axes[1].set_xlim(248, 274)
    axes[1].set_ylabel("Instantaneous differential error (mV)")
    axes[1].set_xlabel("Time (ns)")
    for axis in axes:
        axis.grid(True, alpha=0.25)
        axis.legend()
    fig.suptitle("Bootstrap driver finalist confirmation")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    run = json.loads(args.input.read_text(encoding="utf-8"))
    if run["oa_export_sha256"] != (
        "f3818ef606de602671beac8b6728a1f5460958d03ca0299de0fc79e28132242c"
    ):
        raise ValueError("Unexpected OA export provenance")
    rows = [_analyze(record, run["configuration"])
            for record in run["records"] if record["signals"]]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    aggregate = _aggregate(rows)
    ranking = sorted(
        ({"candidate": name, **values} for name, values in aggregate.items()),
        key=lambda item: item["maximum_absolute_held_error_v"],
    )
    summary = {
        "scope": run["scope"], "phase": run["phase"],
        "oa_export": run["oa_export"],
        "oa_export_sha256": run["oa_export_sha256"],
        "source_subckt_sha256": run["source_subckt_sha256"],
        "simulator": run["simulator"], "case_count": len(rows),
        "spectre_failure_count": int(run["failed_case_count"]),
        "aggregate": aggregate, "ranking": ranking, "cases": rows,
        "scope_limits": run["configuration"]["scope_limits"],
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    _write_csv(args.output_dir / "case_summary.csv", rows)
    if run["phase"] == "screen":
        _plot_screen(args.output_dir / "screen.png", rows)
    else:
        _plot_confirmation(args.output_dir / "finalist_waveforms.png", run, rows)
    print(json.dumps({
        "phase": run["phase"], "cases": len(rows),
        "spectre_failures": run["failed_case_count"], "ranking": ranking,
        "summary": str(args.output_dir / "summary.json"),
    }, indent=2))
    return 0 if rows and not run["failed_case_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
