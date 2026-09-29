#!/usr/bin/env python3
"""Summarize the OA-derived sampling comparison and ideal CDAC oracle."""

from __future__ import annotations

import csv
import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

import yaml
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii
from run_bootstrap_bottom_plate_eval import analyze


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "output" / "bootstrap_bottom_plate_eval"
CONFIG = ROOT / "config" / "bootstrap_bottom_plate_eval.yaml"
WEIGHTS = {9: 16, 8: 8, 7: 4, 6: 2, 5: 1,
           4: 16, 3: 8, 2: 4, 1: 2, 0: 1}


def solve(top_charge: float, lsb_charge: float, cm: float, cl: float,
          bridge: float) -> tuple[float, float]:
    a, d = cm + bridge, cl + bridge
    determinant = a * d - bridge * bridge
    return ((d * top_charge + bridge * lsb_charge) / determinant,
            (bridge * top_charge + a * lsb_charge) / determinant)


def ideal_cdac(cu: float) -> dict:
    cm, cl, bridge = 31 * cu, 32 * cu, 32 / 31 * cu
    # A common bottom-plate transition from VIN to VCM must invert VIN at TOP.
    unit_top, unit_lsb = solve(cu, 0.0, cm, cl, bridge)
    _, _ = solve(0.0, cu, cm, cl, bridge)
    bit_weights = {
        str(bit): WEIGHTS[bit] * (unit_top if bit >= 5 else unit_lsb)
        for bit in range(10)
    }
    ordered = [bit_weights[str(bit)] for bit in range(10)]
    assert all(math.isclose(ordered[bit], 2 ** bit / 1024, abs_tol=1e-14)
               for bit in range(10))
    common_top, common_lsb = solve(cm, cl, cm, cl, bridge)
    assert math.isclose(common_top, 1.0, abs_tol=1e-14)
    assert math.isclose(common_lsb, 1.0, abs_tol=1e-14)
    # Complementary differential reference switching yields a centered 10-bit
    # staircase whose full-scale is VREFP - VREFN = 0.9 V per side.
    levels = [sum((1 if (code >> bit) & 1 else -1) * ordered[bit]
                  for bit in range(10)) for code in range(1024)]
    ideal_step = 2 / 1024
    dnl = [(levels[i + 1] - levels[i]) / ideal_step - 1 for i in range(1023)]
    inl = [(level - (levels[0] + code * (levels[-1] - levels[0]) / 1023))
           / ideal_step for code, level in enumerate(levels)]
    assert all(levels[i] < levels[i + 1] for i in range(1023))
    return {
        "model": "ideal linear capacitors, no switch parasitics, no mismatch",
        "matrix_capacitance_f": [[cm + bridge, -bridge], [-bridge, cl + bridge]],
        "bottom_sampling_top_transfer_v_per_v": -common_top,
        "comparator_polarity": "TOPP-TOPN = -(VINP-VINN) before conversion",
        "binary_bit_weights_fraction_of_side_reference": bit_weights,
        "max_abs_dnl_lsb": max(map(abs, dnl)),
        "max_abs_endpoint_inl_lsb": max(map(abs, inl)),
        "missing_codes": 0,
        "static_transfer_is_analytical_only": True,
    }


def fit(rows: list[dict], error_field: str) -> dict:
    xs = [float(row["vdiff_v"]) for row in rows]
    ys = [float(row[error_field]) for row in rows]
    mean_x, mean_y = sum(xs) / len(xs), sum(ys) / len(ys)
    denominator = sum((x - mean_x) ** 2 for x in xs)
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denominator
    intercept = mean_y - slope * mean_x
    residual = [y - (slope * x + intercept) for x, y in zip(xs, ys)]
    return {"raw_max_abs_error_v": max(map(abs, ys)),
            "error_slope_v_per_v": slope, "error_intercept_v": intercept,
            "post_fit_max_abs_residual_v": max(map(abs, residual))}


def phase_plot(row: dict) -> None:
    raw = BASE / "spectre" / row["name"] / f"{row['name']}.raw" / "tran.tran.tran"
    parsed = parse_spectre_psf_ascii(raw)
    if not parsed.ok:
        raise RuntimeError(parsed.errors)
    data = parsed.data
    indices = [i for i, t in enumerate(data["time"]) if 248e-9 <= t <= 254e-9]
    def series(name: str) -> list[float]:
        return [float(data[name][i]) for i in indices]
    t_ns = [float(data["time"][i]) * 1e9 for i in indices]
    top = [p - n for p, n in zip(series("TOPP_TOP"), series("TOPN_TOP"))]
    bottom = [n - p for p, n in zip(series("TOPP_BP"), series("TOPN_BP"))]
    vmin = min(top + bottom + [float(row["vdiff_v"])]) - 0.08
    vmax = max(top + bottom + [float(row["vdiff_v"])]) + 0.08
    def points(xs: list[float], ys: list[float], ymin: float, ymax: float,
               top_px: int, bottom_px: int) -> str:
        return " ".join(f"{70 + (x - 248) / 6 * 760:.2f},{bottom_px - (y - ymin) / (ymax - ymin) * (bottom_px - top_px):.2f}"
                        for x, y in zip(xs, ys))
    lines = ['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="520" viewBox="0 0 900 520">',
             '<rect width="900" height="520" fill="white"/>',
             '<style>text{font:14px sans-serif;fill:#222}.grid{stroke:#ddd;stroke-width:1}</style>',
             '<text x="70" y="28">OA/Spectre phase trace: differential input -0.8 V, 0.5 ns clamp lead</text>']
    for event, label in ((249.5, "clamp opens"), (250.0, "bootstrap opens"), (252.0, "reference connects")):
        x = 70 + (event - 248) / 6 * 760
        lines.append(f'<line x1="{x:.2f}" x2="{x:.2f}" y1="50" y2="465" class="grid"/>')
        lines.append(f'<text x="{x + 3:.2f}" y="{62 + (event - 249.5) * 12:.1f}">{label}</text>')
    for values, color, label in ((top, "#1469a3", "top-plate baseline"),
                                 (bottom, "#bd4c2c", "bottom-plate polarity corrected")):
        lines.append(f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{points(t_ns, values, vmin, vmax, 75, 320)}"/>')
        lines.append(f'<text x="72" y="{348 if label.startswith("top") else 368}" fill="{color}">{label}</text>')
    for name, color in (("PHI", "#1469a3"), ("CLAMP", "#bd4c2c"), ("BASE", "#168054")):
        lines.append(f'<polyline fill="none" stroke="{color}" stroke-width="1.5" points="{points(t_ns, series(name), -0.05, 1.0, 390, 465)}"/>')
    lines.extend(['<text x="70" y="490">248 ns</text>', '<text x="790" y="490">254 ns</text>',
                  '<text x="650" y="405">PHI / CLAMP / BASE</text>', '</svg>'])
    (BASE / "phase_trace.svg").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    global BASE
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG)
    variant = parser.add_mutually_exclusive_group()
    variant.add_argument("--t28-clamp", action="store_true")
    variant.add_argument("--clamp-width-nm", type=int, choices=(100, 185, 200, 250, 500))
    args = parser.parse_args()
    if args.t28_clamp:
        BASE = BASE / "t28_clamp"
    if args.clamp_width_nm is not None:
        BASE = ROOT / "output" / "bootstrap_bottom_plate_clamp_width_screen" / f"w{args.clamp_width_nm}"
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    rows = json.loads((BASE / "spectre" / "run_summary.json").read_text(encoding="utf-8"))
    phase_updated = False
    for row in rows:
        if not row.get("ok") or "bottom_clamp_step_v" in row:
            continue
        raw = BASE / "spectre" / row["name"] / f"{row['name']}.raw" / "tran.tran.tran"
        parsed = parse_spectre_psf_ascii(raw)
        if not parsed.ok:
            raise RuntimeError(parsed.errors)
        row.update(analyze(parsed.data, float(row["vdiff_v"]),
                           float(row["clamp_to_bootstrap_delay_s"]), config))
        phase_updated = True
    if phase_updated:
        (BASE / "spectre" / "run_summary.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    good = [r for r in rows if r.get("ok") and "top_raw_error_v" in r]
    if not good:
        raise RuntimeError("No completed Spectre cases")
    hashes = {r["oa_export_sha256"] for r in good}
    if len(hashes) != 1:
        raise RuntimeError(f"Mixed OA source revisions: {hashes}")
    fields = ["name", "vdiff_v", "clamp_to_bootstrap_delay_s",
              "top_raw_error_v", "bottom_raw_error_v", "top_acquisition_error_v",
              "bottom_b9_acquisition_error_v", "top_common_mode_v", "bottom_common_mode_v",
              "bottom_clamp_step_v", "bottom_bootstrap_step_v", "top_bootstrap_step_v",
              "bottom_reference_step_v", "top_reference_step_v",
              "bottom_hold_drift_v", "top_hold_drift_v"]
    with (BASE / "case_metrics.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field) for field in fields} for row in good)
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in good:
        groups[str(round(float(row["clamp_to_bootstrap_delay_s"]) * 1e12))].append(row)
    by_delay = {}
    for delay, group in sorted(groups.items(), key=lambda item: int(item[0])):
        group.sort(key=lambda row: row["vdiff_v"])
        entry = {"case_count": len(group), "input_v": [r["vdiff_v"] for r in group],
                 "top_max_abs_raw_error_v": max(abs(r["top_raw_error_v"]) for r in group),
                 "bottom_max_abs_raw_error_v": max(abs(r["bottom_raw_error_v"]) for r in group),
                 "bottom_max_abs_acquisition_error_v": max(abs(r["bottom_b9_acquisition_error_v"]) for r in group),
                 "max_abs_bottom_common_mode_shift_v": max(abs(r["bottom_common_mode_v"] - 0.45) for r in group),
                 "bottom_max_abs_clamp_step_v": max(abs(r["bottom_clamp_step_v"]) for r in group),
                 "bottom_max_abs_bootstrap_step_v": max(abs(r["bottom_bootstrap_step_v"]) for r in group),
                 "bottom_max_abs_hold_drift_v": max(abs(r["bottom_hold_drift_v"]) for r in group),
                 "all_cases_have_warnings": all(bool(r["warnings"]) for r in group)}
        if len(group) >= 3:
            entry["top_fit"] = fit(group, "top_raw_error_v")
            entry["bottom_fit"] = fit(group, "bottom_raw_error_v")
        by_delay[delay] = entry
    summary = {
        "oa_export_sha256": next(iter(hashes)),
        "simulated_case_count": len(good),
        "conditions": config["conditions"],
        "target_raw_error_v": config["targets"]["maximum_raw_differential_error_v"],
        "by_delay_ps": by_delay,
        "analytical_oracle": ideal_cdac(float(config["conditions"]["unit_capacitance_f"])),
        "physical_acceptance": (
            "blocked: unresolved T28 bootstrap or clamp SOA warnings"
            if args.t28_clamp or args.clamp_width_nm is not None else
            "blocked: T28 bootstrap SOA warnings and ideal top clamp"
        ),
    }
    (BASE / "analysis_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    plot_row = next((r for r in good if r["name"] == "vdm800_d0500p"), None)
    if plot_row:
        phase_plot(plot_row)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
