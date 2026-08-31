#!/usr/bin/env python3
"""Summarize transmission-gate PVT screening results."""

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
DEFAULT_INPUT = ROOT / "output" / "switch_pvt_screening" / "spectre" / "run_summary.json"
DEFAULT_OUTPUT = ROOT / "output" / "switch_pvt_screening" / "analysis"


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
    hold_intervals = [float(value) for value in data["targets"]["hold_intervals_s"]]

    corner_rows: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    candidate_names = sorted({row["candidate"] for row in data["on_results"]})
    for name in candidate_names:
        rows = [row for row in data["on_results"] if row["candidate"] == name]
        for row in rows:
            corner_rows.append(
                {
                    "candidate": name,
                    "family": row["family"],
                    "length_nm": row["length_nm"],
                    "nmos_width_um": row["nmos_width_um"],
                    "pmos_width_um": row["pmos_width_um"],
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
        leakage_worst = (
            max(leakage_rows, key=lambda row: row["absolute_leakage_a"])
            if leakage_rows
            else None
        )
        base = rows[0]
        summary: dict[str, Any] = {
            "name": name,
            "family": base["family"],
            "length_nm": base["length_nm"],
            "nmos_width_um": base["nmos_width_um"],
            "pmos_width_um": base["pmos_width_um"],
            "total_width_um": base["total_width_um"],
            "completed_corner_count": len(successful),
            "expected_corner_count": condition_count,
            "robust_ron_pass": (
                len(successful) == condition_count
                and all(row.get("passes_ron_target") for row in successful)
            ),
            "worst_ron_ohm": worst["maximum_ron_ohm"] if worst else None,
            "worst_ron_corner": _corner(worst) if worst else None,
            "maximum_off_leakage_a": (
                leakage_worst["absolute_leakage_a"] if leakage_worst else None
            ),
            "maximum_off_leakage_corner": _corner(leakage_worst) if leakage_worst else None,
        }
        if leakage_worst:
            leakage = float(leakage_worst["absolute_leakage_a"])
            summary["hold_droop_v"] = {
                f"{interval:.12g}": leakage * interval / capacitance_f
                for interval in hold_intervals
            }
        candidates.append(summary)

    if not corner_rows:
        raise RuntimeError("No PVT Ron results found")
    _write_csv(args.output_dir / "candidate_corner_summary.csv", corner_rows)

    passing = [item for item in candidates if item["robust_ron_pass"]]
    selected = min(
        passing,
        key=lambda item: (
            item["total_width_um"],
            item["worst_ron_ohm"],
            item["maximum_off_leakage_a"]
            if item["maximum_off_leakage_a"] is not None
            else float("inf"),
        ),
        default=None,
    )
    compact = {
        "scope": data["scope"],
        "source_netlist_sha256": data["source_netlist_sha256"],
        "model_sections": data["model_sections"],
        "condition_count_per_candidate": condition_count,
        "target_maximum_ron_ohm": target_ron,
        "candidate_count": len(candidates),
        "robust_candidate_count": len(passing),
        "candidates": candidates,
        "selected_minimum_width_robust_candidate": selected,
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(compact, indent=2) + "\n",
        encoding="utf-8",
    )

    fig, ax = plt.subplots(figsize=(10.0, 5.8), dpi=160)
    labels = [item["name"] for item in candidates]
    values = [item["worst_ron_ohm"] or 0.0 for item in candidates]
    colors = ["#2ca02c" if item["robust_ron_pass"] else "#7f7f7f" for item in candidates]
    ax.bar(labels, values, color=colors)
    ax.axhline(target_ron, color="#d62728", linestyle="--", linewidth=1.5, label="1 kOhm target")
    ax.set_ylabel("Worst max Ron across PVT (Ohm)")
    ax.set_title("T28 transmission-gate global-PVT screening")
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
