#!/usr/bin/env python3
"""Run nominal PDK transmission-gate Ron and leakage characterization."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from pathlib import Path
from typing import Any

import yaml

from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii
from virtuoso_bridge.spectre.runner import SpectreSimulator, spectre_mode_args


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "switch_characterization.yaml"
DEFAULT_NETLIST = (
    ROOT / "output" / "switch_characterization" / "netlist" /
    "tb_tg_switch_char" / "input.scs"
)
DEFAULT_OUTPUT = ROOT / "output" / "switch_characterization" / "spectre"


def _replace_instance_parameter(text: str, instance: str, parameter: str, value: str) -> str:
    pattern = rf"(?m)^({re.escape(instance)}\s+\([^\n]+\)[^\n]*\b{re.escape(parameter)}=)\S+"
    updated, count = re.subn(pattern, rf"\g<1>{value}", text, count=1)
    if count != 1:
        raise ValueError(f"Could not parameterize {instance}.{parameter}")
    return updated


def _replace_source_dc(text: str, source: str, value: str) -> str:
    pattern = rf"(?m)^({re.escape(source)}\s+\([^\n]+\)\s+vsource\s+dc=)\S+"
    updated, count = re.subn(pattern, rf"\g<1>{value}", text, count=1)
    if count != 1:
        raise ValueError(f"Could not parameterize source {source}")
    return updated


def _insert_analysis(text: str, statements: str) -> str:
    marker = "modelParameter info"
    if marker not in text:
        raise ValueError(f"Netlist insertion marker missing: {marker}")
    return text.replace(marker, statements.rstrip() + "\n" + marker, 1)


def _base_case(text: str, n_mult: int, p_mult: int) -> str:
    text = _replace_instance_parameter(text, "MN0", "multi", str(n_mult))
    text = _replace_instance_parameter(text, "MP0", "multi", str(p_mult))
    return text


def _on_deck(
    base: str,
    n_mult: int,
    p_mult: int,
    start_v: float,
    stop_v: float,
    step_v: float,
    probe_v: float,
) -> str:
    text = _base_case(base, n_mult, p_mult)
    text = _replace_source_dc(text, "VL", "vcm+dv/2")
    text = _replace_source_dc(text, "VR", "vcm-dv/2")
    return _insert_analysis(
        text,
        f"""
parameters vcm=450m dv={probe_v:.12g}
dc_on dc param=vcm start={start_v:.12g} stop={stop_v:.12g} step={step_v:.12g}
save VL:p VR:p MN0:id MP0:id LEFT RIGHT
""",
    )


def _off_deck(base: str, n_mult: int, p_mult: int, supply_v: float) -> str:
    text = _base_case(base, n_mult, p_mult)
    text = _replace_source_dc(text, "VGN", "0")
    text = _replace_source_dc(text, "VGP", f"{supply_v:.12g}")
    text = _replace_source_dc(text, "VL", f"{supply_v:.12g}")
    text = _replace_source_dc(text, "VR", "0")
    return _insert_analysis(
        text,
        """
dc_off dc
save VL:p VR:p MN0:id MP0:id LEFT RIGHT
""",
    )


def _as_float_list(value: Any) -> list[float]:
    if isinstance(value, list):
        return [float(item.real if isinstance(item, complex) else item) for item in value]
    return [float(value.real if isinstance(value, complex) else value)]


def _sweep_axis(data: dict[str, Any]) -> list[float]:
    for key in ("vcm", "dc"):
        if key in data:
            return _as_float_list(data[key])
    raise KeyError(f"DC sweep axis missing; available signals: {sorted(data)}")


def _run_deck(
    deck: Path,
    work_dir: Path,
    profile: str,
    analysis_file: str,
) -> tuple[Any, dict[str, Any]]:
    simulator = SpectreSimulator.from_env(
        spectre_cmd=os.getenv("SPECTRE_CMD", "spectre"),
        spectre_args=spectre_mode_args("spectre"),
        timeout=600,
        work_dir=work_dir,
        output_format="psfascii",
        profile=profile,
    )
    result = simulator.run_simulation(deck, {})
    data: dict[str, Any] = {}
    path = work_dir / f"{deck.stem}.raw" / analysis_file
    if result.ok and path.is_file():
        parsed = parse_spectre_psf_ascii(path)
        if not parsed.ok:
            raise RuntimeError(f"Failed to parse {path}: {parsed.errors}")
        data = parsed.data
    return result, data


def _case_name(n_mult: int, p_mult: int) -> str:
    return f"n{n_mult:02d}_p{p_mult:02d}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--netlist", type=Path, default=DEFAULT_NETLIST)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--case-limit", type=int)
    args = parser.parse_args()

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    source = args.netlist.read_text(encoding="utf-8")
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    conditions = config["conditions"]
    devices = config["devices"]
    target_ron = float(config["targets"]["maximum_on_resistance_ohm"])
    finger_width_um = float(devices["finger_width_m"]) * 1e6

    cases = []
    for n_mult in config["sweep"]["nmos_multipliers"]:
        for ratio in config["sweep"]["pmos_to_nmos_ratios"]:
            p_mult = int(round(float(n_mult) * float(ratio)))
            cases.append((int(n_mult), p_mult))
    if args.case_limit is not None:
        cases = cases[: args.case_limit]

    args.output_root.mkdir(parents=True, exist_ok=True)
    deck_dir = args.output_root / "decks"
    deck_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    failures = 0

    for n_mult, p_mult in cases:
        name = _case_name(n_mult, p_mult)
        deck = deck_dir / f"{name}.scs"
        deck.write_text(
            _on_deck(
                source,
                n_mult,
                p_mult,
                float(conditions["signal_common_mode_start_v"]),
                float(conditions["signal_common_mode_stop_v"]),
                float(conditions["signal_common_mode_step_v"]),
                float(conditions["differential_probe_v"]),
            ),
            encoding="utf-8",
        )
        result, data = _run_deck(deck, args.output_root / name, args.profile, "dc_on.dc")
        case: dict[str, Any] = {
            "name": name,
            "nmos_multiplier": n_mult,
            "pmos_multiplier": p_mult,
            "nmos_width_um": n_mult * finger_width_um,
            "pmos_width_um": p_mult * finger_width_um,
            "total_width_um": (n_mult + p_mult) * finger_width_um,
            "spectre_ok": result.ok,
            "status": result.status.value,
            "errors": result.errors[:10],
            "warnings": result.warnings[:10],
        }
        if result.ok and data:
            vcm = _sweep_axis(data)
            current = _as_float_list(data["VL:p"])
            if len(vcm) != len(current):
                raise RuntimeError(f"Axis/current length mismatch in {name}")
            ron = [
                float(conditions["differential_probe_v"]) / abs(value)
                if abs(value) > 1e-18
                else math.inf
                for value in current
            ]
            case.update(
                {
                    "vcm_v": vcm,
                    "source_current_a": current,
                    "ron_ohm": ron,
                    "minimum_ron_ohm": min(ron),
                    "maximum_ron_ohm": max(ron),
                    "mean_ron_ohm": sum(ron) / len(ron),
                    "ron_flatness_peak_to_peak_over_mean": (
                        (max(ron) - min(ron)) / (sum(ron) / len(ron))
                    ),
                    "passes_ron_target": all(math.isfinite(value) for value in ron)
                    and max(ron) <= target_ron,
                }
            )
        else:
            failures += 1
        results.append(case)

    passing = [case for case in results if case.get("passes_ron_target")]
    minimum_area = min(
        passing,
        key=lambda case: (case["total_width_um"], case["maximum_ron_ohm"]),
        default=None,
    )
    flattest = min(
        passing,
        key=lambda case: (
            case["ron_flatness_peak_to_peak_over_mean"],
            case["total_width_um"],
        ),
        default=None,
    )

    selected_names = {
        case["name"]
        for case in (minimum_area, flattest)
        if case is not None
    }
    leakage: dict[str, Any] = {}
    for case in results:
        if case["name"] not in selected_names:
            continue
        deck = deck_dir / f"{case['name']}_off.scs"
        deck.write_text(
            _off_deck(
                source,
                int(case["nmos_multiplier"]),
                int(case["pmos_multiplier"]),
                float(conditions["supply_v"]),
            ),
            encoding="utf-8",
        )
        result, data = _run_deck(
            deck,
            args.output_root / f"{case['name']}_off",
            args.profile,
            "dc_off.dc",
        )
        current = _as_float_list(data["VL:p"])[-1] if result.ok and data else None
        leakage[case["name"]] = {
            "spectre_ok": result.ok,
            "status": result.status.value,
            "errors": result.errors[:10],
            "warnings": result.warnings[:10],
            "stress_v": float(conditions["supply_v"]),
            "absolute_leakage_a": abs(current) if current is not None else None,
        }
        if not result.ok:
            failures += 1

    summary = {
        "scope": "nominal_tt_transmission_gate_initial_sizing",
        "source_netlist": str(args.netlist),
        "source_netlist_sha256": source_hash,
        "conditions": conditions,
        "finger_width_um": finger_width_um,
        "target_maximum_ron_ohm": target_ron,
        "cases": results,
        "selection": {
            "minimum_area_case": minimum_area["name"] if minimum_area else None,
            "flattest_passing_case": flattest["name"] if flattest else None,
        },
        "off_leakage": leakage,
    }
    summary_path = args.output_root / "run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"summary: {summary_path}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
