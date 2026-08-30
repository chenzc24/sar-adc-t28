#!/usr/bin/env python3
"""Derive and verify the first-order CDAC/reference settling envelope.

The tracked YAML is the single source of numerical inputs.  The script writes
generated tables, plots, case decks, waveforms, and a compact JSON conclusion
under ``output/cdac_reference_settling``.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "cdac_reference_settling.yaml"
DECK_TEMPLATE = PROJECT_ROOT / "netlist" / "tb" / "tb_cdac_reference_settling.scs"
DEFAULT_OUTPUT = PROJECT_ROOT / "output" / "cdac_reference_settling"
BOLTZMANN_J_PER_K = 1.380649e-23


def lsb_v(full_scale_v: float, resolution_bits: int) -> float:
    return full_scale_v / (2**resolution_bits)


def side_capacitance_f(unit_capacitance_ff: float, side_units: float, parasitic_ff: float = 0.0) -> float:
    return (unit_capacitance_ff * side_units + parasitic_ff) * 1e-15


def differential_ktc_noise_rms_v(capacitance_f: float, temperature_k: float) -> float:
    return math.sqrt(2.0 * BOLTZMANN_J_PER_K * temperature_k / capacitance_f)


def minimum_side_capacitance_f(noise_limit_v: float, temperature_k: float) -> float:
    return 2.0 * BOLTZMANN_J_PER_K * temperature_k / (noise_limit_v**2)


def settling_residual_v(step_v: float, resistance_ohm: float, capacitance_f: float, settling_time_s: float) -> float:
    if resistance_ohm <= 0.0:
        return 0.0
    return step_v * math.exp(-settling_time_s / (resistance_ohm * capacitance_f))


def maximum_resistance_ohm(step_v: float, residual_limit_v: float, capacitance_f: float, settling_time_s: float) -> float:
    return settling_time_s / (capacitance_f * math.log(step_v / residual_limit_v))


def interpolate(time: list[float], value: list[float], target: float) -> float:
    if not time or len(time) != len(value):
        raise ValueError("invalid waveform arrays")
    if target < time[0] or target > time[-1]:
        raise ValueError(f"target time {target} outside waveform range")
    lo, hi = 0, len(time) - 1
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if time[mid] <= target:
            lo = mid
        else:
            hi = mid
    if time[hi] == time[lo]:
        return value[lo]
    fraction = (target - time[lo]) / (time[hi] - time[lo])
    return value[lo] + fraction * (value[hi] - value[lo])


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"configuration is not a mapping: {path}")
    return data


def derive_limits(config: dict[str, Any]) -> dict[str, float]:
    spec = config["source_spec"]
    split = config["split_cdac"]
    code_lsb_v = lsb_v(spec["differential_full_scale_v"], spec["resolution_bits"])
    noise_limit_v = code_lsb_v * spec["sampling_noise_rms_lsb"]
    settling_limit_v = code_lsb_v * spec["settling_abs_max_lsb"]
    cside_min_f = minimum_side_capacitance_f(noise_limit_v, spec["temperature_k"])
    return {
        "lsb_v": code_lsb_v,
        "sampling_noise_limit_v_rms": noise_limit_v,
        "settling_residual_limit_v": settling_limit_v,
        "minimum_side_capacitance_f": cside_min_f,
        "minimum_unit_capacitance_f": max(
            0.0,
            (cside_min_f - split["parasitic_capacitance_ff"] * 1e-15)
            / split["comparator_side_units"],
        ),
    }


def evaluate_candidate(config: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    limits = derive_limits(config)
    spec = config["source_spec"]
    split = config["split_cdac"]
    cside_f = side_capacitance_f(
        case["unit_capacitance_ff"],
        split["comparator_side_units"],
        split["parasitic_capacitance_ff"],
    )
    resistance_ohm = case["reference_resistance_ohm"] + case["switch_resistance_ohm"]
    settling_time_s = case["settling_time_ns"] * 1e-9
    noise_v = differential_ktc_noise_rms_v(cside_f, spec["temperature_k"])
    residual_v = settling_residual_v(
        spec["differential_full_scale_v"], resistance_ohm, cside_f, settling_time_s
    )
    return {
        **case,
        "side_capacitance_ff": cside_f * 1e15,
        "total_resistance_ohm": resistance_ohm,
        "differential_ktc_noise_rms_v": noise_v,
        "differential_ktc_noise_rms_lsb": noise_v / limits["lsb_v"],
        "analytical_settling_residual_v": residual_v,
        "analytical_settling_residual_lsb": residual_v / limits["lsb_v"],
        "noise_pass": noise_v <= limits["sampling_noise_limit_v_rms"],
        "settling_pass": residual_v <= limits["settling_residual_limit_v"],
        "feasible": (
            noise_v <= limits["sampling_noise_limit_v_rms"]
            and residual_v <= limits["settling_residual_limit_v"]
        ),
    }


def _write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        raise ValueError(f"no records for {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def derive_tables(config: dict[str, Any], output: Path) -> dict[str, Any]:
    limits = derive_limits(config)
    spec = config["source_spec"]
    split = config["split_cdac"]
    envelope: list[dict[str, Any]] = []
    for cu_ff in config["scan"]["unit_capacitance_ff"]:
        cside_f = side_capacitance_f(
            cu_ff, split["comparator_side_units"], split["parasitic_capacitance_ff"]
        )
        noise_v = differential_ktc_noise_rms_v(cside_f, spec["temperature_k"])
        for settling_ns in config["scan"]["settling_time_ns"]:
            envelope.append(
                {
                    "unit_capacitance_ff": cu_ff,
                    "side_capacitance_ff": cside_f * 1e15,
                    "settling_time_ns": settling_ns,
                    "maximum_total_resistance_ohm": maximum_resistance_ohm(
                        spec["differential_full_scale_v"],
                        limits["settling_residual_limit_v"],
                        cside_f,
                        settling_ns * 1e-9,
                    ),
                    "differential_ktc_noise_rms_mv": noise_v * 1e3,
                    "differential_ktc_noise_rms_lsb": noise_v / limits["lsb_v"],
                    "noise_pass": noise_v <= limits["sampling_noise_limit_v_rms"],
                }
            )
    _write_csv(output / "envelope.csv", envelope)

    grid: list[dict[str, Any]] = []
    for cu_ff in config["scan"]["unit_capacitance_ff"]:
        for settling_ns in config["scan"]["settling_time_ns"]:
            for rref in config["scan"]["reference_resistance_ohm"]:
                for rswitch in config["scan"]["switch_resistance_ohm"]:
                    grid.append(
                        evaluate_candidate(
                            config,
                            {
                                "unit_capacitance_ff": cu_ff,
                                "settling_time_ns": settling_ns,
                                "reference_resistance_ohm": rref,
                                "switch_resistance_ohm": rswitch,
                            },
                        )
                    )
    _write_csv(output / "grid.csv", grid)
    return {"limits": limits, "envelope": envelope, "grid": grid}


def _render_deck(config: dict[str, Any], evaluated: dict[str, Any]) -> str:
    sim = config["spectre"]
    replacements = {
        "@VSTEP@": f'{sim["single_ended_step_v"]:.12g}',
        "@TDELAY@": f'{sim["step_delay_ns"]:.12g}n',
        "@TRISE@": f'{sim["rise_time_ps"]:.12g}p',
        "@RREF@": f'{evaluated["reference_resistance_ohm"]:.12g}',
        "@RSWITCH@": f'{evaluated["switch_resistance_ohm"]:.12g}',
        "@CSIDE@": f'{evaluated["side_capacitance_ff"]:.12g}f',
        "@TSTOP@": f'{sim["stop_time_ns"]:.12g}n',
        "@MAXSTEP@": f'{sim["max_step_ps"]:.12g}p',
    }
    deck = DECK_TEMPLATE.read_text(encoding="utf-8")
    for token, value in replacements.items():
        deck = deck.replace(token, value)
    if "@" in deck:
        raise ValueError("unreplaced token remains in generated Spectre deck")
    return deck


def run_spectre_cases(config: dict[str, Any], output: Path, profile: str) -> list[dict[str, Any]]:
    from virtuoso_bridge.spectre.runner import SpectreSimulator, spectre_mode_args

    results: list[dict[str, Any]] = []
    for case in config["representative_spectre_cases"]:
        evaluated = evaluate_candidate(config, case)
        case_dir = output / "spectre" / case["name"]
        case_dir.mkdir(parents=True, exist_ok=True)
        deck = case_dir / "input.scs"
        deck.write_text(_render_deck(config, evaluated), encoding="utf-8")
        simulator = SpectreSimulator.from_env(
            spectre_cmd=os.getenv("SPECTRE_CMD", "spectre"),
            spectre_args=spectre_mode_args("spectre"),
            timeout=600,
            work_dir=case_dir,
            output_format="psfascii",
            profile=profile,
        )
        simulation = simulator.run_simulation(deck, {})
        record = {
            **evaluated,
            "spectre_ok": bool(simulation.ok),
            "spectre_status": simulation.status.value,
            "spectre_errors": list(simulation.errors),
            "spectre_warnings": list(simulation.warnings),
        }
        if not simulation.ok:
            results.append(record)
            continue
        time = [float(value) for value in simulation.data["time"]]
        signal_key = next(key for key in simulation.data if key.lower() == "vdac")
        vdac = [float(value) for value in simulation.data[signal_key]]
        target_s = (config["spectre"]["step_delay_ns"] + case["settling_time_ns"]) * 1e-9
        sampled_v = interpolate(time, vdac, target_s)
        differential_residual_v = 2.0 * (
            config["spectre"]["single_ended_step_v"] - sampled_v
        )
        comparison_error_v = abs(
            differential_residual_v - evaluated["analytical_settling_residual_v"]
        )
        comparison_tolerance_v = max(
            1e-6, 0.01 * evaluated["analytical_settling_residual_v"]
        )
        record.update(
            {
                "spectre_vdac_at_settling_end_v": sampled_v,
                "spectre_differential_residual_v": differential_residual_v,
                "spectre_differential_residual_lsb": differential_residual_v
                / derive_limits(config)["lsb_v"],
                "spectre_vs_analytical_abs_error_v": comparison_error_v,
                "spectre_comparison_tolerance_v": comparison_tolerance_v,
                "spectre_matches_analytical": comparison_error_v <= comparison_tolerance_v,
            }
        )
        _write_csv(
            case_dir / "tran.csv",
            [dict(zip(("time", signal_key), values, strict=True)) for values in zip(time, vdac, strict=True)],
        )
        results.append(record)
    _write_csv(output / "spectre_comparison.csv", results)
    return results


def create_plots(config: dict[str, Any], tables: dict[str, Any], output: Path) -> None:
    import matplotlib.pyplot as plt

    envelope = tables["envelope"]
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    for settling_ns in config["scan"]["settling_time_ns"]:
        rows = [row for row in envelope if row["settling_time_ns"] == settling_ns]
        ax.plot(
            [row["unit_capacitance_ff"] for row in rows],
            [row["maximum_total_resistance_ohm"] for row in rows],
            marker="o",
            label=f"{settling_ns:g} ns",
        )
    ax.axvline(tables["limits"]["minimum_unit_capacitance_f"] * 1e15, color="black", linestyle="--", label="kT/C minimum")
    ax.set(xlabel="Unit capacitance Cu (fF)", ylabel="Maximum Rref + Ron (ohm)", xscale="log", yscale="log")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / "resistance_envelope.png", dpi=180)
    plt.close(fig)

    rows = [row for row in envelope if row["settling_time_ns"] == config["scan"]["settling_time_ns"][0]]
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.plot([row["unit_capacitance_ff"] for row in rows], [row["differential_ktc_noise_rms_mv"] for row in rows], marker="o")
    ax.axhline(tables["limits"]["sampling_noise_limit_v_rms"] * 1e3, color="black", linestyle="--", label="0.18 LSB budget")
    ax.set(xlabel="Unit capacitance Cu (fF)", ylabel="Differential kT/C noise (mV RMS)", xscale="log")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / "noise_vs_unit_cap.png", dpi=180)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument("--spectre", action="store_true")
    parser.add_argument("--no-plots", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    args.output.mkdir(parents=True, exist_ok=True)
    tables = derive_tables(config, args.output)
    representative = [evaluate_candidate(config, case) for case in config["representative_spectre_cases"]]
    summary: dict[str, Any] = {
        "model_scope": "first_order_differential_cdac_reference_envelope",
        "limits": tables["limits"],
        "representative_cases": representative,
        "grid_points": len(tables["grid"]),
        "feasible_grid_points": sum(bool(row["feasible"]) for row in tables["grid"]),
    }
    if args.spectre:
        summary["spectre_cases"] = run_spectre_cases(config, args.output, args.profile)
    if not args.no_plots:
        create_plots(config, tables, args.output)
    (args.output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    if args.spectre and not all(
        row["spectre_ok"] and row.get("spectre_matches_analytical", False)
        for row in summary["spectre_cases"]
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
