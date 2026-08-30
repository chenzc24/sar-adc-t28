#!/usr/bin/env python3
"""Derive and Spectre-correlate the remaining module first-order models."""

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
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "module_first_order.yaml"
TB_DIR = PROJECT_ROOT / "netlist" / "tb"
DEFAULT_OUTPUT = PROJECT_ROOT / "output" / "module_first_order"


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"configuration is not a mapping: {path}")
    return data


def lsb_v(config: dict[str, Any]) -> float:
    spec = config["source_spec"]
    return spec["differential_full_scale_v"] / (2 ** spec["resolution_bits"])


def side_capacitance_f(config: dict[str, Any], unit_capacitance_ff: float) -> float:
    sampling = config["sampling_acquisition"]
    return (
        sampling["comparator_side_units"] * unit_capacitance_ff
        + sampling["parasitic_capacitance_ff"]
    ) * 1e-15


def exponential_residual_v(step_v: float, resistance_ohm: float, capacitance_f: float, time_s: float) -> float:
    if resistance_ohm <= 0:
        return 0.0
    return step_v * math.exp(-time_s / (resistance_ohm * capacitance_f))


def sampling_candidate(config: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    spec = config["source_spec"]
    cside_f = side_capacitance_f(config, case["unit_capacitance_ff"])
    total_r = case["source_resistance_ohm"] + case["switch_resistance_ohm"]
    acquisition_s = spec["sampling_time_ns"] * 1e-9
    residual = exponential_residual_v(
        spec["differential_full_scale_v"], total_r, cside_f, acquisition_s
    )
    limit = spec["settling_abs_max_lsb"] * lsb_v(config)
    return {
        **case,
        "side_capacitance_ff": cside_f * 1e15,
        "total_resistance_ohm": total_r,
        "time_constant_ns": total_r * cside_f * 1e9,
        "bandwidth_hz": 1.0 / (2.0 * math.pi * total_r * cside_f),
        "analytical_residual_v": residual,
        "analytical_residual_lsb": residual / lsb_v(config),
        "settling_pass": residual <= limit,
    }


def sampling_maximum_resistance_ohm(config: dict[str, Any], unit_capacitance_ff: float) -> float:
    spec = config["source_spec"]
    cside_f = side_capacitance_f(config, unit_capacitance_ff)
    residual_limit = spec["settling_abs_max_lsb"] * lsb_v(config)
    return (spec["sampling_time_ns"] * 1e-9) / (
        cside_f * math.log(spec["differential_full_scale_v"] / residual_limit)
    )


def comparator_candidate(config: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    comparator = config["comparator_regeneration"]
    initial_v = case["initial_input_lsb"] * lsb_v(config)
    cnode_f = case["node_capacitance_ff"] * 1e-15
    gm_s = case["effective_gm_us"] * 1e-6
    tau_s = cnode_f / gm_s
    decision_s = tau_s * math.log(comparator["resolved_differential_v"] / initial_v)
    scale = comparator["pdk_nominal_scale_reference"]
    width_um = case["effective_gm_us"] / scale["gm_density_us_per_um"]
    current_ua = width_um * scale["id_density_ua_per_um"]
    return {
        **case,
        "initial_differential_v": initial_v,
        "regeneration_tau_ps": tau_s * 1e12,
        "analytical_decision_time_ns": decision_s * 1e9,
        "nominal_nmos_width_scale_um": width_um,
        "nominal_nmos_current_scale_ua": current_ua,
        "decision_pass": decision_s <= case["decision_time_budget_ns"] * 1e-9,
    }


def required_gm_us(config: dict[str, Any], cnode_ff: float, initial_lsb: float, decision_ns: float) -> float:
    comparator = config["comparator_regeneration"]
    log_gain = math.log(
        comparator["resolved_differential_v"] / (initial_lsb * lsb_v(config))
    )
    return cnode_ff * 1e-15 * log_gain / (decision_ns * 1e-9) * 1e6


def jitter_error_rms_v(config: dict[str, Any], frequency_hz: float) -> float:
    jitter = config["clock_jitter"]
    full_scale_peak = config["source_spec"]["differential_full_scale_v"] / 2.0
    signal_peak = full_scale_peak * 10.0 ** (jitter["input_level_dbfs"] / 20.0)
    return (
        2.0
        * math.pi
        * frequency_hz
        * signal_peak
        * jitter["rms_ps"]
        * 1e-12
        / math.sqrt(2.0)
    )


def _write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        raise ValueError(f"no records for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(dict.fromkeys(key for record in records for key in record))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def derive_tables(config: dict[str, Any], output: Path) -> dict[str, list[dict[str, Any]]]:
    sampling = config["sampling_acquisition"]
    sampling_grid = [
        sampling_candidate(
            config,
            {
                "unit_capacitance_ff": cu,
                "source_resistance_ohm": source_r,
                "switch_resistance_ohm": switch_r,
            },
        )
        for cu in sampling["unit_capacitance_ff"]
        for source_r in sampling["source_resistance_ohm"]
        for switch_r in sampling["switch_resistance_ohm"]
    ]
    sampling_envelope = [
        {
            "unit_capacitance_ff": cu,
            "side_capacitance_ff": side_capacitance_f(config, cu) * 1e15,
            "maximum_source_plus_switch_resistance_ohm": sampling_maximum_resistance_ohm(config, cu),
        }
        for cu in sampling["unit_capacitance_ff"]
    ]

    comparator = config["comparator_regeneration"]
    comparator_grid = [
        comparator_candidate(
            config,
            {
                "initial_input_lsb": initial,
                "node_capacitance_ff": cnode,
                "effective_gm_us": gm,
                "decision_time_budget_ns": budget,
            },
        )
        for initial in comparator["initial_input_lsb"]
        for cnode in comparator["node_capacitance_ff"]
        for gm in comparator["effective_gm_us"]
        for budget in comparator["decision_time_budget_ns"]
    ]
    comparator_envelope = [
        {
            "initial_input_lsb": initial,
            "node_capacitance_ff": cnode,
            "decision_time_budget_ns": budget,
            "required_effective_gm_us": required_gm_us(config, cnode, initial, budget),
        }
        for initial in comparator["initial_input_lsb"]
        for cnode in comparator["node_capacitance_ff"]
        for budget in comparator["decision_time_budget_ns"]
    ]

    jitter_grid = [
        {
            "input_frequency_hz": frequency,
            "jitter_rms_ps": config["clock_jitter"]["rms_ps"],
            "input_level_dbfs": config["clock_jitter"]["input_level_dbfs"],
            "input_referred_error_rms_v": jitter_error_rms_v(config, frequency),
            "input_referred_error_rms_lsb": jitter_error_rms_v(config, frequency) / lsb_v(config),
        }
        for frequency in config["clock_jitter"]["input_frequency_hz"]
    ]
    tables = {
        "sampling_grid": sampling_grid,
        "sampling_envelope": sampling_envelope,
        "comparator_grid": comparator_grid,
        "comparator_envelope": comparator_envelope,
        "jitter_grid": jitter_grid,
    }
    for name, records in tables.items():
        _write_csv(output / f"{name}.csv", records)
    return tables


def _replace_tokens(template: Path, replacements: dict[str, str]) -> str:
    text = template.read_text(encoding="utf-8")
    for token, value in replacements.items():
        text = text.replace(token, value)
    if "@" in text:
        raise ValueError(f"unreplaced token remains in {template}")
    return text


def _interpolate(time: list[float], value: list[float], target: float) -> float:
    if target < time[0] or target > time[-1]:
        raise ValueError("target outside waveform")
    for index in range(1, len(time)):
        if time[index] >= target:
            fraction = (target - time[index - 1]) / (time[index] - time[index - 1])
            return value[index - 1] + fraction * (value[index] - value[index - 1])
    raise ValueError("target not found")


def _crossing_time(time: list[float], value: list[float], threshold: float) -> float:
    for index in range(1, len(time)):
        if value[index - 1] < threshold <= value[index]:
            fraction = (threshold - value[index - 1]) / (value[index] - value[index - 1])
            return time[index - 1] + fraction * (time[index] - time[index - 1])
    raise ValueError(f"waveform did not cross {threshold}")


def _spectre(config: dict[str, Any], output: Path, profile: str, kind: str, case: dict[str, Any]) -> tuple[dict[str, Any], dict[str, list[float]]]:
    from virtuoso_bridge.spectre.runner import SpectreSimulator, spectre_mode_args

    sim = config["spectre"]
    case_dir = output / "spectre" / kind / case["name"]
    case_dir.mkdir(parents=True, exist_ok=True)
    if kind == "sampling":
        evaluated = sampling_candidate(config, case)
        replacements = {
            "@VSTEP@": f'{sim["single_ended_step_v"]:.12g}',
            "@TDELAY@": f'{sim["step_delay_ns"]:.12g}n',
            "@TRISE@": f'{sim["rise_time_ps"]:.12g}p',
            "@RSOURCE@": f'{case["source_resistance_ohm"]:.12g}',
            "@RSWITCH@": f'{case["switch_resistance_ohm"]:.12g}',
            "@CSIDE@": f'{evaluated["side_capacitance_ff"]:.12g}f',
            "@TSTOP@": f'{sim["sampling_stop_time_ns"]:.12g}n',
            "@MAXSTEP@": f'{sim["sampling_max_step_ps"]:.12g}p',
        }
        template = TB_DIR / "tb_sampling_acquisition.scs"
    else:
        evaluated = comparator_candidate(config, case)
        stop_ns = evaluated["analytical_decision_time_ns"] * 1.1
        replacements = {
            "@GMEFF@": f'{case["effective_gm_us"]:.12g}u',
            "@CNODE@": f'{case["node_capacitance_ff"]:.12g}f',
            "@VINITIAL@": f'{evaluated["initial_differential_v"]:.12g}',
            "@TSTOP@": f'{stop_ns:.12g}n',
            "@MAXSTEP@": f'{sim["comparator_max_step_ps"]:.12g}p',
        }
        template = TB_DIR / "tb_comparator_regeneration.scs"
    deck = case_dir / "input.scs"
    deck.write_text(_replace_tokens(template, replacements), encoding="utf-8")
    simulator = SpectreSimulator.from_env(
        spectre_cmd=os.getenv("SPECTRE_CMD", "spectre"),
        spectre_args=spectre_mode_args("spectre"),
        timeout=600,
        work_dir=case_dir,
        output_format="psfascii",
        profile=profile,
    )
    result = simulator.run_simulation(deck, {})
    record = {
        **evaluated,
        "spectre_ok": bool(result.ok),
        "spectre_status": result.status.value,
        "spectre_errors": list(result.errors),
        "spectre_warnings": list(result.warnings),
    }
    return record, result.data


def run_spectre(config: dict[str, Any], output: Path, profile: str) -> dict[str, list[dict[str, Any]]]:
    sampling_records = []
    for case in config["sampling_acquisition"]["representative_spectre_cases"]:
        record, data = _spectre(config, output, profile, "sampling", case)
        if record["spectre_ok"]:
            time = [float(item) for item in data["time"]]
            key = next(item for item in data if item.lower() == "vsample")
            values = [float(item) for item in data[key]]
            target_s = (config["spectre"]["step_delay_ns"] + config["source_spec"]["sampling_time_ns"]) * 1e-9
            sample_v = _interpolate(time, values, target_s)
            residual = 2.0 * (config["spectre"]["single_ended_step_v"] - sample_v)
            error = abs(residual - record["analytical_residual_v"])
            tolerance = max(1e-6, 0.01 * record["analytical_residual_v"])
            record.update(
                {
                    "spectre_differential_residual_v": residual,
                    "spectre_differential_residual_lsb": residual / lsb_v(config),
                    "spectre_vs_analytical_abs_error_v": error,
                    "spectre_tolerance_v": tolerance,
                    "spectre_matches_analytical": error <= tolerance,
                }
            )
        sampling_records.append(record)

    comparator_records = []
    threshold = config["comparator_regeneration"]["resolved_differential_v"]
    for case in config["comparator_regeneration"]["representative_spectre_cases"]:
        record, data = _spectre(config, output, profile, "comparator", case)
        if record["spectre_ok"]:
            time = [float(item) for item in data["time"]]
            key = next(item for item in data if item.lower() == "vdiff")
            values = [float(item) for item in data[key]]
            crossing_s = _crossing_time(time, values, threshold)
            analytical_s = record["analytical_decision_time_ns"] * 1e-9
            error_s = abs(crossing_s - analytical_s)
            tolerance_s = max(1e-12, 0.01 * analytical_s)
            record.update(
                {
                    "spectre_decision_time_ns": crossing_s * 1e9,
                    "spectre_vs_analytical_abs_error_ps": error_s * 1e12,
                    "spectre_tolerance_ps": tolerance_s * 1e12,
                    "spectre_matches_analytical": error_s <= tolerance_s,
                }
            )
        comparator_records.append(record)
    _write_csv(output / "spectre_sampling_comparison.csv", sampling_records)
    _write_csv(output / "spectre_comparator_comparison.csv", comparator_records)
    return {"sampling": sampling_records, "comparator": comparator_records}


def create_plots(config: dict[str, Any], tables: dict[str, list[dict[str, Any]]], output: Path) -> None:
    import matplotlib.pyplot as plt

    rows = tables["sampling_envelope"]
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.plot([row["unit_capacitance_ff"] for row in rows], [row["maximum_source_plus_switch_resistance_ohm"] for row in rows], marker="o")
    ax.set(xlabel="Unit capacitance Cu (fF)", ylabel="Maximum Rsource + Ron (ohm)", xscale="log", yscale="log")
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output / "sampling_resistance_envelope.png", dpi=180)
    plt.close(fig)

    comparator = config["comparator_regeneration"]
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    for budget in comparator["decision_time_budget_ns"]:
        subset = [row for row in tables["comparator_envelope"] if row["initial_input_lsb"] == 0.25 and row["decision_time_budget_ns"] == budget]
        ax.plot([row["node_capacitance_ff"] for row in subset], [row["required_effective_gm_us"] for row in subset], marker="o", label=f"{budget:g} ns")
    ax.set(xlabel="Regeneration-node capacitance (fF)", ylabel="Required effective gm (uS)")
    ax.grid(True, alpha=0.3)
    ax.legend(title="Decision budget")
    fig.tight_layout()
    fig.savefig(output / "comparator_gm_envelope.png", dpi=180)
    plt.close(fig)

    rows = tables["jitter_grid"]
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.plot([row["input_frequency_hz"] / 1e6 for row in rows], [row["input_referred_error_rms_lsb"] for row in rows], marker="o")
    ax.axhline(config["source_spec"]["sampling_noise_rms_lsb"], color="black", linestyle="--", label="0.18 LSB comparison")
    ax.set(xlabel="Input frequency (MHz)", ylabel="Jitter error (LSB RMS)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / "clock_jitter_sensitivity.png", dpi=180)
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
    tracked_frequency = config["clock_jitter"]["tracked_budget_frequency_hz"]
    summary: dict[str, Any] = {
        "scope": "sampling_acquisition_comparator_regeneration_clock_jitter",
        "sampling_representative": [sampling_candidate(config, case) for case in config["sampling_acquisition"]["representative_spectre_cases"]],
        "comparator_representative": [comparator_candidate(config, case) for case in config["comparator_regeneration"]["representative_spectre_cases"]],
        "clock_jitter_tracked": {
            "frequency_hz": tracked_frequency,
            "jitter_rms_ps": config["clock_jitter"]["rms_ps"],
            "input_referred_error_rms_v": jitter_error_rms_v(config, tracked_frequency),
            "input_referred_error_rms_lsb": jitter_error_rms_v(config, tracked_frequency) / lsb_v(config),
        },
    }
    if args.spectre:
        summary["spectre"] = run_spectre(config, args.output, args.profile)
    if not args.no_plots:
        create_plots(config, tables, args.output)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    if args.spectre:
        records = summary["spectre"]["sampling"] + summary["spectre"]["comparator"]
        if not all(record["spectre_ok"] and record.get("spectre_matches_analytical", False) for record in records):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
