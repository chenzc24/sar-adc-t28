#!/usr/bin/env python3
"""Derive, run, and analyze the topology-aware SAR electrical macro-model."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "electrical_macro_model.yaml"
TB_TEMPLATE = PROJECT_ROOT / "netlist" / "tb" / "tb_sar_macro_nominal.scs"
DUT_PATH = PROJECT_ROOT / "netlist" / "dut" / "sar_macro_10b.scs"
CONTROLLER_PATH = PROJECT_ROOT / "models" / "veriloga" / "sar_macro_controller_10b.va"
DEFAULT_OUTPUT = PROJECT_ROOT / "output" / "electrical_macro_model"


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"configuration is not a mapping: {path}")
    return data


def lsb_v(config: dict[str, Any]) -> float:
    spec = config["source_spec"]
    return spec["differential_full_scale_v"] / (2 ** spec["resolution_bits"])


def ideal_code(config: dict[str, Any], vin_diff_v: float) -> int:
    spec = config["source_spec"]
    normalized = (vin_diff_v + spec["differential_full_scale_v"] / 2.0) / spec[
        "differential_full_scale_v"
    ]
    return max(0, min((1 << spec["resolution_bits"]) - 1, math.floor(normalized * (1 << spec["resolution_bits"]))))


def code_center_v(config: dict[str, Any], code: int) -> float:
    full_scale = config["source_spec"]["differential_full_scale_v"]
    return -full_scale / 2.0 + (code + 0.5) * lsb_v(config)


def electrical_weights(
    config: dict[str, Any],
    *,
    top_plate_parasitic_ff: float | None = None,
    bridge_node_parasitic_ff: float | None = None,
) -> dict[str, Any]:
    """Return exact charge-conservation weights for the two-node split array."""

    cdac = config["split_cdac"]
    cu = float(cdac["unit_capacitance_ff"])
    ctop = float(cdac["top_plate_parasitic_ff"] if top_plate_parasitic_ff is None else top_plate_parasitic_ff)
    cbridgepar = float(cdac["bridge_node_parasitic_ff"] if bridge_node_parasitic_ff is None else bridge_node_parasitic_ff)
    cmsb = sum(cdac["msb_active_weights"]) * cu
    clsb = (sum(cdac["lsb_active_weights"]) + cdac["lsb_dummy_units"]) * cu
    cbridge = cdac["bridge_units"] * cu
    matrix = np.array(
        [
            [cmsb + cbridge + ctop, -cbridge],
            [-cbridge, cbridge + clsb + cbridgepar],
        ],
        dtype=float,
    )
    inverse = np.linalg.inv(matrix)
    msb_unit_coupling = float(inverse[0, 0] * cu)
    lsb_unit_coupling = float(inverse[0, 1] * cu)
    bit_couplings = [
        *(weight * msb_unit_coupling for weight in cdac["msb_active_weights"]),
        *(weight * lsb_unit_coupling for weight in cdac["lsb_active_weights"]),
    ]
    base_coupling = sum(bit_couplings) + cdac["lsb_dummy_units"] * lsb_unit_coupling
    effective_top_cap = 1.0 / inverse[0, 0]
    return {
        "unit_capacitance_ff": cu,
        "top_plate_parasitic_ff": ctop,
        "bridge_node_parasitic_ff": cbridgepar,
        "capacitance_matrix_ff": matrix.tolist(),
        "effective_top_capacitance_ff": effective_top_cap,
        "effective_top_capacitance_units": effective_top_cap / cu,
        "msb_unit_coupling": msb_unit_coupling,
        "lsb_unit_coupling": lsb_unit_coupling,
        "bit_couplings_msb_to_lsb": bit_couplings,
        "base_coupling": base_coupling,
    }


def dac_threshold_v(config: dict[str, Any], code: int, weights: dict[str, Any]) -> float:
    full_scale = config["source_spec"]["differential_full_scale_v"]
    selected = sum(
        coupling
        for bit, coupling in zip(range(9, -1, -1), weights["bit_couplings_msb_to_lsb"], strict=True)
        if code & (1 << bit)
    )
    return -(full_scale / 2.0) * weights["base_coupling"] + full_scale * selected


def macro_sar_trace(
    config: dict[str, Any], vin_diff_v: float, weights: dict[str, Any]
) -> tuple[int, list[dict[str, Any]]]:
    code = 0
    trace: list[dict[str, Any]] = []
    for bit in range(9, -1, -1):
        trial = code | (1 << bit)
        threshold = dac_threshold_v(config, trial, weights)
        residual = vin_diff_v - threshold
        retained = residual >= 0.0
        if retained:
            code = trial
        trace.append(
            {
                "bit": bit,
                "trial_code": trial,
                "threshold_v": threshold,
                "steady_residual_v": residual,
                "retained": retained,
                "code_after_latch": code,
            }
        )
    return code, trace


def static_metrics(config: dict[str, Any], weights: dict[str, Any]) -> dict[str, Any]:
    ncode = 1 << config["source_spec"]["resolution_bits"]
    lsb = lsb_v(config)
    internal = np.array([dac_threshold_v(config, code, weights) for code in range(1, ncode)])
    boundaries = np.concatenate(([-config["source_spec"]["differential_full_scale_v"] / 2.0], internal, [config["source_spec"]["differential_full_scale_v"] / 2.0]))
    widths = np.diff(boundaries)
    dnl = widths / lsb - 1.0
    ideal_internal = -config["source_spec"]["differential_full_scale_v"] / 2.0 + np.arange(1, ncode) * lsb
    inl = (internal - ideal_internal) / lsb
    return {
        "missing_codes": int(np.count_nonzero(widths <= 0.0)),
        "dnl_min_lsb": float(np.min(dnl)),
        "dnl_max_lsb": float(np.max(dnl)),
        "inl_min_lsb": float(np.min(inl)),
        "inl_max_lsb": float(np.max(inl)),
        "endpoint_threshold_min_v": float(boundaries[0]),
        "endpoint_threshold_max_v": float(boundaries[-1]),
    }


def _pulse_wave(times_ns: list[float], high_v: float, width_ns: float, edge_ns: float, stop_ns: float) -> str:
    points: list[tuple[float, float]] = [(0.0, 0.0)]
    for time_ns in times_ns:
        points.extend(
            [
                (time_ns, 0.0),
                (time_ns + edge_ns, high_v),
                (time_ns + edge_ns + width_ns, high_v),
                (time_ns + 2.0 * edge_ns + width_ns, 0.0),
            ]
        )
    points.append((stop_ns, 0.0))
    return " ".join(f"{time:g}n {value:.12g}" for time, value in points)


def timing_contract(config: dict[str, Any]) -> dict[str, Any]:
    timing = config["timing"]
    vdd = config["source_spec"]["vdd_v"]
    edge_ns = timing["edge_time_ps"] * 1e-3
    trial_times = [timing["first_trial_ns"] + index * config["source_spec"]["bit_cycle_ns"] for index in range(10)]
    compare_starts = [item + timing["cdac_settle_ns"] for item in trial_times]
    latch_times = [item + timing["compare_window_ns"] for item in compare_starts]
    sample_wave = " ".join(
        f"{time:g}n {value:.12g}"
        for time, value in [
            (0.0, vdd),
            (timing["sample_fall_ns"], vdd),
            (timing["sample_fall_ns"] + edge_ns, 0.0),
            (timing["stop_ns"], 0.0),
        ]
    )
    reset_points: list[tuple[float, float]] = [(0.0, vdd)]
    for start, latch in zip(compare_starts, latch_times, strict=True):
        reset_points.extend(
            [
                (start, vdd),
                (start + edge_ns, 0.0),
                (latch + timing["reset_guard_ns"], 0.0),
                (latch + timing["reset_guard_ns"] + edge_ns, vdd),
            ]
        )
    reset_points.append((timing["stop_ns"], vdd))
    return {
        "trial_times_ns": trial_times,
        "compare_start_times_ns": compare_starts,
        "latch_times_ns": latch_times,
        "conversion_latency_ns": latch_times[-1] - timing["sample_fall_ns"],
        "sample_wave": sample_wave,
        # The MSB trial is applied by the sample-falling event. The explicit
        # trial clock starts with bit 8 after the first latch.
        "trial_wave": _pulse_wave(trial_times[1:], vdd, timing["pulse_width_ns"], edge_ns, timing["stop_ns"]),
        "latch_wave": _pulse_wave(latch_times, vdd, timing["pulse_width_ns"], edge_ns, timing["stop_ns"]),
        "reset_wave": " ".join(f"{time:g}n {value:.12g}" for time, value in reset_points),
    }


def _replace_tokens(source: str, replacements: dict[str, str]) -> str:
    for token, value in replacements.items():
        source = source.replace(f"@{token}@", value)
    if "@" in source:
        remaining = sorted({part.split("@", 1)[0] for part in source.split("@")[1::2]})
        raise ValueError(f"unreplaced tokens: {remaining}")
    return source


def _format_si(value: float, suffix: str) -> str:
    return f"{value:.12g}{suffix}"


def stage_case(
    config: dict[str, Any],
    case_dir: Path,
    *,
    vin_diff_v: float,
    overrides: dict[str, float] | None = None,
) -> Path:
    overrides = overrides or {}
    spec = config["source_spec"]
    cdac = config["split_cdac"]
    sample = config["sampling_switch"]
    bottom = config["bottom_plate_switch"]
    ref = config["reference_network"]
    comp = config["comparator_macro"]
    timing = config["timing"]
    clocks = timing_contract(config)
    vinp = spec["vcm_v"] + vin_diff_v / 2.0
    vinn = spec["vcm_v"] - vin_diff_v / 2.0
    replacements = {
        "VDD": f'{spec["vdd_v"]:.12g}',
        "VREFP": f'{spec["vdd_v"]:.12g}',
        "VREFN": "0",
        "VCM": f'{spec["vcm_v"]:.12g}',
        "VINP": f"{vinp:.12g}",
        "VINN": f"{vinn:.12g}",
        "SAMPLE_WAVE": clocks["sample_wave"],
        "TRIAL_WAVE": clocks["trial_wave"],
        "LATCH_WAVE": clocks["latch_wave"],
        "RESET_WAVE": clocks["reset_wave"],
        "CU": _format_si(cdac["unit_capacitance_ff"], "f"),
        "CTOPPAR": _format_si(overrides.get("top_plate_parasitic_ff", cdac["top_plate_parasitic_ff"]), "f"),
        "CBRIDGEPAR": _format_si(overrides.get("bridge_node_parasitic_ff", cdac["bridge_node_parasitic_ff"]), "f"),
        "RSAMPLE": f'{sample["closed_resistance_ohm"]:.12g}',
        "RSOURCE": f'{sample["source_resistance_ohm"]:.12g}',
        "RBOTTOM": f'{overrides.get("bottom_plate_resistance_ohm", bottom["closed_resistance_ohm"]):.12g}',
        "ROPEN": f'{float(bottom["open_resistance_ohm"]):.12g}',
        "RREF": f'{overrides.get("reference_resistance_ohm", ref["source_resistance_ohm"]):.12g}',
        "CDECAP": _format_si(overrides.get("decoupling_capacitance_pf", ref["decoupling_capacitance_pf"]), "p"),
        "GMINPUT": _format_si(comp["input_gm_us"], "u"),
        "GMREG": _format_si(comp["regeneration_gm_us"], "u"),
        "CCOMP": _format_si(comp["differential_node_capacitance_ff"], "f"),
        "RRESET": f'{comp["reset_resistance_ohm"]:.12g}',
        "RCM": f'{float(comp["common_mode_resistance_ohm"]):.12g}',
        "CKB": _format_si(overrides.get("kickback_capacitance_ff", comp["kickback_capacitance_ff"]), "f"),
        "CMPOFFSET": f'{comp["systematic_offset_v"]:.12g}',
        "VT1": f'{sample["control_vt1_v"]:.12g}',
        "VT2": f'{sample["control_vt2_v"]:.12g}',
        "TSTOP": _format_si(timing["stop_ns"], "n"),
        "MAXSTEP": _format_si(timing["max_step_ps"], "p"),
        "DUT_PATH": DUT_PATH.name,
        "CONTROLLER_PATH": CONTROLLER_PATH.name,
    }
    case_dir.mkdir(parents=True, exist_ok=True)
    deck = case_dir / "input.scs"
    deck.write_text(_replace_tokens(TB_TEMPLATE.read_text(encoding="utf-8"), replacements), encoding="utf-8")
    return deck


def _write_waveform_csv(data: dict[str, list[float]], path: Path) -> None:
    keys = ["time", *(sorted(key for key in data if key != "time"))]
    lengths = {len(data[key]) for key in keys}
    if len(lengths) != 1:
        raise ValueError(f"waveform lengths differ: {lengths}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(keys)
        writer.writerows(zip(*(data[key] for key in keys), strict=True))


def _signal(data: dict[str, list[float]], name: str) -> np.ndarray:
    matches = [key for key in data if key.lower() == name.lower()]
    if not matches:
        raise KeyError(f"missing {name}; available={sorted(data)}")
    return np.asarray(data[matches[0]], dtype=float)


def _at(time: np.ndarray, values: np.ndarray, target_s: float) -> float:
    return float(np.interp(target_s, time, values))


def _decode_final(data: dict[str, list[float]]) -> int:
    code = 0
    for bit in range(10):
        if _signal(data, f"D{bit}")[-1] > 0.45:
            code |= 1 << bit
    return code


def analyze_waveform(
    config: dict[str, Any],
    data: dict[str, list[float]],
    vin_diff_v: float,
    weights: dict[str, Any],
) -> dict[str, Any]:
    clocks = timing_contract(config)
    time = _signal(data, "time")
    top_diff = _signal(data, "TOPP") - _signal(data, "TOPN")
    comp_diff = _signal(data, "COMP_P") - _signal(data, "COMP_N")
    refp = _signal(data, "VREFP")
    refn = _signal(data, "VREFN")
    predicted_code, trace = macro_sar_trace(config, vin_diff_v, weights)
    edge_guard_s = config["timing"]["edge_time_ps"] * 1e-12
    settle_records = []
    comparator_records = []
    resolved = config["comparator_macro"]["resolved_differential_v"]
    for item, compare_ns, latch_ns in zip(
        trace,
        clocks["compare_start_times_ns"],
        clocks["latch_times_ns"],
        strict=True,
    ):
        pre_compare = _at(time, top_diff, compare_ns * 1e-9 - edge_guard_s)
        at_latch = _at(time, top_diff, latch_ns * 1e-9)
        after_enable = _at(time, top_diff, compare_ns * 1e-9 + 5.0 * edge_guard_s)
        comp_latch = _at(time, comp_diff, latch_ns * 1e-9)
        settling_error = pre_compare - item["steady_residual_v"]
        settle_records.append(
            {
                **item,
                "pre_compare_top_diff_v": pre_compare,
                "pre_compare_settling_error_v": settling_error,
                "pre_compare_settling_error_lsb": settling_error / lsb_v(config),
                "latch_top_diff_v": at_latch,
                "comparator_enable_kickback_v": after_enable - pre_compare,
                "compare_window_input_change_v": at_latch - pre_compare,
            }
        )
        comparator_records.append(
            {
                "bit": item["bit"],
                "latch_comp_diff_v": comp_latch,
                "resolved": abs(comp_latch) >= resolved,
                "sign_matches_steady_residual": (comp_latch >= 0.0) == (item["steady_residual_v"] >= 0.0),
            }
        )
    final_code = _decode_final(data)
    valid = _signal(data, "VALID")
    valid_edges = np.flatnonzero((valid[:-1] <= 0.45) & (valid[1:] > 0.45)) + 1
    valid_time_ns = float(time[valid_edges[0]] * 1e9) if valid_edges.size else None
    return {
        "vin_diff_v": vin_diff_v,
        "ideal_code": ideal_code(config, vin_diff_v),
        "charge_model_code": predicted_code,
        "spectre_code": final_code,
        "valid_time_ns": valid_time_ns,
        "conversion_latency_ns": None if valid_time_ns is None else valid_time_ns - config["timing"]["sample_fall_ns"],
        "sample_acquisition_error_v": _at(time, top_diff, config["timing"]["sample_fall_ns"] * 1e-9 - edge_guard_s) - vin_diff_v,
        "maximum_reference_droop_v": float(max(np.max(np.abs(refp - config["source_spec"]["vdd_v"])), np.max(np.abs(refn)))),
        "maximum_pre_compare_settling_error_lsb": float(max(abs(item["pre_compare_settling_error_lsb"]) for item in settle_records)),
        "maximum_comparator_enable_kickback_lsb": float(max(abs(item["comparator_enable_kickback_v"]) for item in settle_records) / lsb_v(config)),
        "maximum_compare_window_input_change_lsb": float(max(abs(item["compare_window_input_change_v"]) for item in settle_records) / lsb_v(config)),
        "all_comparisons_resolved": all(item["resolved"] for item in comparator_records),
        "all_comparator_signs_match": all(item["sign_matches_steady_residual"] for item in comparator_records),
        "settling": settle_records,
        "comparator": comparator_records,
    }


def run_spectre_case(
    config: dict[str, Any],
    output: Path,
    profile: str,
    name: str,
    vin_diff_v: float,
    overrides: dict[str, float] | None = None,
) -> dict[str, Any]:
    from virtuoso_bridge.spectre.runner import SpectreSimulator, spectre_mode_args

    case_dir = output / "spectre" / name
    deck = stage_case(config, case_dir, vin_diff_v=vin_diff_v, overrides=overrides)
    simulator = SpectreSimulator.from_env(
        spectre_cmd="spectre",
        spectre_args=spectre_mode_args("spectre"),
        timeout=900,
        work_dir=case_dir,
        output_format="psfascii",
        profile=profile,
    )
    result = simulator.run_simulation(
        deck,
        {"include_files": [DUT_PATH, CONTROLLER_PATH], "spectre_args": ["+lqtimeout", "30"]},
    )
    record: dict[str, Any] = {
        "name": name,
        "spectre_ok": bool(result.ok),
        "spectre_status": result.status.value,
        "errors": list(result.errors),
        "warnings": list(result.warnings),
        "metadata": result.metadata,
    }
    (case_dir / "spectre_result.json").write_text(json.dumps(record, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    if not result.ok:
        return record
    _write_waveform_csv(result.data, case_dir / "tran.csv")
    overrides = overrides or {}
    weights = electrical_weights(
        config,
        top_plate_parasitic_ff=overrides.get("top_plate_parasitic_ff"),
        bridge_node_parasitic_ff=overrides.get("bridge_node_parasitic_ff"),
    )
    record.update(analyze_waveform(config, result.data, vin_diff_v, weights))
    (case_dir / "analysis.json").write_text(json.dumps(record, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return record


def create_plot(case_dir: Path, output: Path) -> None:
    import matplotlib.pyplot as plt

    data = np.genfromtxt(case_dir / "tran.csv", delimiter=",", names=True)
    names = {name.lower(): name for name in data.dtype.names or ()}
    time_ns = np.asarray(data[names["time"]]) * 1e9
    derived = [
        ("CDAC differential", np.asarray(data[names["topp"]]) - np.asarray(data[names["topn"]]), "V"),
        ("Reference span error", np.asarray(data[names["vrefp"]]) - np.asarray(data[names["vrefn"]]) - 0.9, "V"),
        ("Comparator differential", np.asarray(data[names["comp_p"]]) - np.asarray(data[names["comp_n"]]), "V"),
        ("VALID", np.asarray(data[names["valid"]]), "V"),
    ]
    fig, axes = plt.subplots(4, 1, figsize=(10, 9), sharex=True)
    for ax, (title, values, unit) in zip(axes, derived, strict=True):
        ax.plot(time_ns, values)
        ax.set_ylabel(unit)
        ax.set_title(title, loc="left", fontsize=9)
        ax.grid(True, alpha=0.3)
    axes[-1].set_xlabel("Time (ns)")
    fig.tight_layout()
    fig.savefig(output, dpi=180)
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
    nominal_weights = electrical_weights(config)
    parasitic_case = config["spectre_cases"]["parasitic_case"]
    parasitic_weights = electrical_weights(
        config,
        top_plate_parasitic_ff=parasitic_case["top_plate_parasitic_ff"],
        bridge_node_parasitic_ff=parasitic_case["bridge_node_parasitic_ff"],
    )
    summary: dict[str, Any] = {
        "scope": "topology_aware_closed_loop_pre_transistor_macro",
        "timing": timing_contract(config),
        "nominal_weights": nominal_weights,
        "nominal_static": static_metrics(config, nominal_weights),
        "assumed_parasitic_weights": parasitic_weights,
        "assumed_parasitic_static": static_metrics(config, parasitic_weights),
    }
    records: list[dict[str, Any]] = []
    if args.spectre:
        for code in config["spectre_cases"]["nominal_codes"]:
            records.append(
                run_spectre_case(
                    config,
                    args.output,
                    args.profile,
                    f"nominal_code_{code:04d}",
                    code_center_v(config, code),
                )
            )
        stressed = config["spectre_cases"]["stressed_case"]
        records.append(
            run_spectre_case(
                config,
                args.output,
                args.profile,
                stressed["name"],
                code_center_v(config, stressed["code"]),
                {
                    "reference_resistance_ohm": stressed["reference_resistance_ohm"],
                    "bottom_plate_resistance_ohm": stressed["bottom_plate_resistance_ohm"],
                },
            )
        )
        for code in (256, 512, 768):
            records.append(
                run_spectre_case(
                    config,
                    args.output,
                    args.profile,
                    f"parasitic_code_{code:04d}",
                    code_center_v(config, code),
                    {
                        "top_plate_parasitic_ff": parasitic_case["top_plate_parasitic_ff"],
                        "bridge_node_parasitic_ff": parasitic_case["bridge_node_parasitic_ff"],
                    },
                )
            )
        kickback = config["spectre_cases"]["kickback_stress_case"]
        records.append(
            run_spectre_case(
                config,
                args.output,
                args.profile,
                kickback["name"],
                code_center_v(config, kickback["code"]),
                {"kickback_capacitance_ff": kickback["kickback_capacitance_ff"]},
            )
        )
        summary["spectre"] = records
        successful = [record for record in records if record["spectre_ok"]]
        if successful and not args.no_plots:
            representative = next(record for record in successful if record["name"] == "nominal_code_0768")
            create_plot(args.output / "spectre" / representative["name"], args.output / "macro_waveforms.png")

    (args.output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    if args.spectre:
        nominal = [item for item in records if item["name"].startswith("nominal_")]
        limit = config["source_spec"]["settling_abs_max_lsb"]
        if not all(
            item.get("spectre_ok")
            and item.get("spectre_code") == item.get("charge_model_code")
            and item.get("all_comparisons_resolved")
            and item.get("all_comparator_signs_match")
            and item.get("maximum_pre_compare_settling_error_lsb", math.inf) <= limit
            for item in nominal
        ):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
