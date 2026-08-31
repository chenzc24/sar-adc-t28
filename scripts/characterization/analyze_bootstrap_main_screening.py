#!/usr/bin/env python3
"""Summarize ideal-bootstrap main-switch PVT results."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "output" / "bootstrap_main_switch_screening" / "spectre" / "run_summary.json"
DEFAULT_OUTPUT = ROOT / "output" / "bootstrap_main_switch_screening" / "analysis"


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _corner(row: dict[str, Any]) -> str:
    return f"{row['process']}/{row['supply_v']:.2f}V/{row['temperature_c']:.0f}C"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    data = json.loads(args.input.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    condition_count = int(data["expected_condition_count_per_candidate"])
    target_ron = float(data["targets"]["maximum_on_resistance_ohm"])
    capacitance_f = float(data["targets"]["effective_top_plate_capacitance_f"])
    intervals = [float(value) for value in data["targets"]["hold_intervals_s"]]

    corner_rows: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    names = sorted({row["candidate"] for row in data["on_results"]})
    for name in names:
        rows = [row for row in data["on_results"] if row["candidate"] == name]
        for row in rows:
            corner_rows.append(
                {
                    "candidate": name,
                    "family": row["family"],
                    "width_um": row["width_um"],
                    "length_nm": row["length_nm"],
                    "process": row["process"],
                    "supply_v": row["supply_v"],
                    "temperature_c": row["temperature_c"],
                    "spectre_ok": row["spectre_ok"],
                    "minimum_ron_ohm": row.get("minimum_ron_ohm"),
                    "maximum_ron_ohm": row.get("maximum_ron_ohm"),
                    "passes_ron_target": row.get("passes_ron_target", False),
                }
            )
        successful = [row for row in rows if row.get("spectre_ok") and "maximum_ron_ohm" in row]
        worst = max(successful, key=lambda row: row["maximum_ron_ohm"]) if successful else None
        leakage_rows = [
            row
            for row in data["off_results"]
            if row["candidate"] == name and row.get("absolute_leakage_a") is not None
        ]
        leakage_worst = max(leakage_rows, key=lambda row: row["absolute_leakage_a"]) if leakage_rows else None
        stress_rows = [row["commanded_terminal_stress"] for row in successful]
        base = rows[0]
        item: dict[str, Any] = {
            "name": name,
            "family": base["family"],
            "master": base["master"],
            "body_mode": base["body_mode"],
            "width_um": base["width_um"],
            "length_nm": base["length_nm"],
            "completed_corner_count": len(successful),
            "expected_corner_count": condition_count,
            "passing_corner_count": sum(bool(row.get("passes_ron_target")) for row in successful),
            "robust_ron_pass": (
                len(successful) == condition_count
                and all(row.get("passes_ron_target") for row in successful)
            ),
            "worst_ron_ohm": worst["maximum_ron_ohm"] if worst else None,
            "worst_ron_corner": _corner(worst) if worst else None,
            "worst_ron_flatness": worst["ron_flatness_peak_to_peak_over_mean"] if worst else None,
            "maximum_off_leakage_a": leakage_worst["absolute_leakage_a"] if leakage_worst else None,
            "maximum_off_leakage_corner": _corner(leakage_worst) if leakage_worst else None,
            "maximum_commanded_terminal_stress": {
                key: max(row[key] for row in stress_rows)
                for key in stress_rows[0]
            } if stress_rows else None,
        }
        if leakage_worst:
            leakage = float(leakage_worst["absolute_leakage_a"])
            item["hold_droop_v"] = {
                f"{interval:.12g}": leakage * interval / capacitance_f
                for interval in intervals
            }
        candidates.append(item)

    if not corner_rows:
        raise RuntimeError("No bootstrap main-switch results found")
    _write_csv(args.output_dir / "candidate_corner_summary.csv", corner_rows)

    passing = [item for item in candidates if item["robust_ron_pass"]]
    pareto = []
    for item in passing:
        metrics = (
            float(item["width_um"]),
            float(item["worst_ron_ohm"]),
            float(item["maximum_off_leakage_a"]),
        )
        dominated = False
        for other in passing:
            if other is item:
                continue
            other_metrics = (
                float(other["width_um"]),
                float(other["worst_ron_ohm"]),
                float(other["maximum_off_leakage_a"]),
            )
            if all(a <= b for a, b in zip(other_metrics, metrics)) and any(
                a < b for a, b in zip(other_metrics, metrics)
            ):
                dominated = True
                break
        if not dominated:
            pareto.append(item)
    pareto.sort(key=lambda item: (item["maximum_off_leakage_a"], item["worst_ron_ohm"]))
    selected = min(
        passing,
        key=lambda item: (item["width_um"], item["worst_ron_ohm"]),
        default=None,
    )
    family_selections = {
        family: min(
            [item for item in passing if item["family"] == family],
            key=lambda item: (item["width_um"], item["worst_ron_ohm"]),
            default=None,
        )
        for family in sorted({item["family"] for item in candidates})
    }
    compact = {
        "scope": data["scope"],
        "source_netlist_sha256": data["source_netlist_sha256"],
        "model_sections": data["model_sections"],
        "condition_count_per_candidate": condition_count,
        "target_maximum_ron_ohm": target_ron,
        "candidate_count": len(candidates),
        "robust_candidate_count": len(passing),
        "candidates": candidates,
        "pareto_metrics": ["width_um", "worst_ron_ohm", "maximum_off_leakage_a"],
        "pareto_candidates": pareto,
        "selected_minimum_width_ron_candidate": selected,
        "minimum_width_by_family": family_selections,
        "reliability_signoff": "not_claimed_without_foundry_limits_and_transient_driver",
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(compact, indent=2) + "\n",
        encoding="utf-8",
    )

    fig, ax = plt.subplots(figsize=(10.5, 5.8), dpi=160)
    labels = [item["name"] for item in candidates]
    values = [item["worst_ron_ohm"] or 0.0 for item in candidates]
    colors = ["#2ca02c" if item["robust_ron_pass"] else "#7f7f7f" for item in candidates]
    ax.bar(labels, values, color=colors)
    ax.axhline(target_ron, color="#d62728", linestyle="--", linewidth=1.5, label="1 kOhm target")
    ax.set_ylabel("Worst max Ron across PVT (Ohm)")
    ax.set_title("T28 ideal-bootstrap main-switch global-PVT screening")
    ax.set_yscale("log")
    ax.tick_params(axis="x", rotation=35)
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(args.output_dir / "worst_case_ron.png")
    plt.close(fig)

    print(json.dumps(compact, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
