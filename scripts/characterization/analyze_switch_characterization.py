#!/usr/bin/env python3
"""Create compact tables and plots from switch characterization results."""

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
DEFAULT_INPUT = ROOT / "output" / "switch_characterization" / "spectre" / "run_summary.json"
DEFAULT_OUTPUT = ROOT / "output" / "switch_characterization" / "analysis"


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    data = json.loads(args.input.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    case_table: list[dict[str, Any]] = []
    for case in data["cases"]:
        if not case.get("spectre_ok") or "ron_ohm" not in case:
            continue
        case_table.append(
            {
                "name": case["name"],
                "nmos_width_um": case["nmos_width_um"],
                "pmos_width_um": case["pmos_width_um"],
                "total_width_um": case["total_width_um"],
                "minimum_ron_ohm": case["minimum_ron_ohm"],
                "maximum_ron_ohm": case["maximum_ron_ohm"],
                "mean_ron_ohm": case["mean_ron_ohm"],
                "ron_flatness_peak_to_peak_over_mean": case[
                    "ron_flatness_peak_to_peak_over_mean"
                ],
                "passes_ron_target": case["passes_ron_target"],
            }
        )
        for vcm, ron in zip(case["vcm_v"], case["ron_ohm"]):
            rows.append(
                {
                    "case": case["name"],
                    "nmos_width_um": case["nmos_width_um"],
                    "pmos_width_um": case["pmos_width_um"],
                    "common_mode_v": vcm,
                    "ron_ohm": ron,
                }
            )

    if not rows:
        raise RuntimeError("No successful Ron curves found")
    _write_csv(args.output_dir / "ron_vs_common_mode.csv", rows)
    _write_csv(args.output_dir / "case_summary.csv", case_table)

    selections = {
        key: next(
            (case for case in case_table if case["name"] == name),
            None,
        )
        for key, name in data["selection"].items()
    }
    compact = {
        "scope": data["scope"],
        "source_netlist_sha256": data["source_netlist_sha256"],
        "conditions": data["conditions"],
        "target_maximum_ron_ohm": data["target_maximum_ron_ohm"],
        "case_count": len(data["cases"]),
        "successful_case_count": sum(bool(case.get("spectre_ok")) for case in data["cases"]),
        "passing_case_count": sum(bool(case.get("passes_ron_target")) for case in data["cases"]),
        "selection": selections,
        "off_leakage": data["off_leakage"],
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(compact, indent=2) + "\n",
        encoding="utf-8",
    )

    fig, ax = plt.subplots(figsize=(9.0, 5.5), dpi=160)
    for case in data["cases"]:
        if not case.get("spectre_ok") or "ron_ohm" not in case:
            continue
        selected = case["name"] in set(data["selection"].values())
        ax.plot(
            case["vcm_v"],
            case["ron_ohm"],
            linewidth=2.4 if selected else 1.0,
            alpha=1.0 if selected else 0.45,
            label=(
                f"{case['name']} ({case['nmos_width_um']:.2f}/{case['pmos_width_um']:.2f} um)"
                if selected
                else None
            ),
        )
    ax.axhline(
        data["target_maximum_ron_ohm"],
        color="#d62728",
        linestyle="--",
        linewidth=1.5,
        label="1 kOhm target",
    )
    ax.set_xlabel("Signal common mode (V)")
    ax.set_ylabel("Transmission-gate Ron (Ohm)")
    ax.set_title("T28 standard-VT transmission gate, TT, 27 C, VDD=0.9 V")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(args.output_dir / "ron_vs_common_mode.png")
    plt.close(fig)

    print(json.dumps(compact, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
