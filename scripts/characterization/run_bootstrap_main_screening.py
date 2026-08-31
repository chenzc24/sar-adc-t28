#!/usr/bin/env python3
"""Run batched ideal-bootstrap main-NMOS PVT screening."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import re
from pathlib import Path
from typing import Any

import yaml

from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii
from virtuoso_bridge.spectre.runner import SpectreSimulator, spectre_mode_args
from virtuoso_bridge.transport.tunnel import SSHClient


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "bootstrap_main_switch_screening.yaml"
DEFAULT_OUTPUT = ROOT / "output" / "bootstrap_main_switch_screening" / "spectre"


def _extract_header(text: str) -> str:
    marker = "// Library name:"
    if marker not in text:
        raise ValueError(f"OA netlist header marker missing: {marker}")
    return text.split(marker, 1)[0].rstrip()


def _extract_instance(text: str, instance: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith(f"{instance} "):
            continue
        statement = [line]
        while statement[-1].rstrip().endswith("\\"):
            index += 1
            if index >= len(lines):
                raise ValueError(f"Unterminated OA instance statement: {instance}")
            statement.append(lines[index])
        return "\n".join(statement)
    raise ValueError(f"OA instance statement missing: {instance}")


def _replace_mos_section(text: str, section: str) -> str:
    pattern = r"(?im)^(include\s+\"[^\"\n]+\"\s+section=)(?:ss|tt|ff)macro_mos_moscap\s*$"
    updated, count = re.subn(pattern, rf"\g<1>{section}", text, count=1)
    if count != 1:
        raise ValueError("Could not parameterize MOS/MOSCAP model section")
    return updated


def _device_copy(
    statement: str,
    new_name: str,
    nodes: tuple[str, str, str, str],
    length_nm: int,
    multiplier: int,
) -> str:
    updated, count = re.subn(
        r"^MN0\s+\([^\n)]+\)",
        f"{new_name} ({' '.join(nodes)})",
        statement,
        count=1,
    )
    if count != 1:
        raise ValueError("Could not rewrite MN0 terminal list")
    updated, count = re.subn(r"\bl=\S+", f"l={length_nm}n", updated, count=1)
    if count != 1:
        raise ValueError("Could not rewrite MN0.l")
    updated, count = re.subn(r"\bmulti=\S+", f"multi={multiplier}", updated, count=1)
    if count != 1:
        raise ValueError("Could not rewrite MN0.multi")
    return updated


def _save_statement(signals: list[str]) -> str:
    groups = [signals[index : index + 6] for index in range(0, len(signals), 6)]
    lines = []
    for index, group in enumerate(groups):
        prefix = "save " if index == 0 else "     "
        suffix = " \\" if index + 1 < len(groups) else ""
        lines.append(prefix + " ".join(group) + suffix)
    return "\n".join(lines)


def _build_batch_deck(
    header: str,
    device_statements: dict[str, str],
    candidates: list[dict[str, Any]],
    families: dict[str, dict[str, Any]],
    model_section: str,
    supply_v: float,
    temperature_c: float,
    margin_v: float,
    step_v: float,
    probe_v: float,
) -> tuple[str, dict[str, dict[str, str]]]:
    rendered = [
        _replace_mos_section(header, model_section),
        "",
        "// Isolated replicas of OA-exported main-switch device statements",
        f"parameters vdd={supply_v:.12g} vcm={supply_v / 2:.12g} dv={probe_v:.12g}",
    ]
    signal_map: dict[str, dict[str, str]] = {}
    saves: list[str] = []
    for index, candidate in enumerate(candidates):
        token = f"C{index:02d}"
        family = candidate["family"]
        body_mode = families[family]["body_mode"]
        on_left = f"ONL_{token}"
        on_right = f"ONR_{token}"
        on_gate = f"ONG_{token}"
        on_body = on_right if body_mode == "signal_low" else "0"
        off_left = f"OFFL_{token}"
        off_right = f"OFFR_{token}"
        off_body = off_right if body_mode == "signal_low" else "0"
        on_source = f"VONL_{token}"
        off_source = f"VOFFL_{token}"
        rendered.extend(
            [
                "",
                f"// {candidate['name']}: {family}, L={candidate['length_nm']} nm",
                _device_copy(
                    device_statements[family],
                    f"MN_ON_{token}",
                    (on_left, on_gate, on_right, on_body),
                    int(candidate["length_nm"]),
                    int(candidate["multiplier"]),
                ),
                f"VG_{token} ({on_gate} 0) vsource dc=vcm+vdd type=dc",
                f"{on_source} ({on_left} 0) vsource dc=vcm+dv/2 type=dc",
                f"VONR_{token} ({on_right} 0) vsource dc=vcm-dv/2 type=dc",
                _device_copy(
                    device_statements[family],
                    f"MN_OFF_{token}",
                    (off_left, "0", off_right, off_body),
                    int(candidate["length_nm"]),
                    int(candidate["multiplier"]),
                ),
                f"{off_source} ({off_left} 0) vsource dc=vdd type=dc",
                f"VOFFR_{token} ({off_right} 0) vsource dc=0 type=dc",
            ]
        )
        signal_map[candidate["name"]] = {
            "on_current": f"{on_source}:p",
            "off_current": f"{off_source}:p",
        }
        saves.extend((f"{on_source}:p", f"{off_source}:p"))

    rendered.extend(
        [
            "",
            "simulatorOptions options reltol=1e-4 vabstol=1e-6 iabstol=1e-12 \\",
            f"    temp={temperature_c:.12g} tnom=27 gmin=1e-12 maxnotes=5 maxwarns=5",
            (
                f"dc_on dc param=vcm start={margin_v:.12g} "
                f"stop={supply_v - margin_v:.12g} step={step_v:.12g}"
            ),
            _save_statement(saves),
            "saveOptions options save=selected",
            "",
        ]
    )
    return "\n".join(rendered), signal_map


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
    ssh_runner: Any,
) -> tuple[Any, dict[str, Any]]:
    simulator = SpectreSimulator.from_env(
        spectre_cmd=os.getenv("SPECTRE_CMD", "spectre"),
        spectre_args=spectre_mode_args("spectre"),
        timeout=600,
        work_dir=work_dir,
        output_format="psfascii",
        profile=profile,
        ssh_runner=ssh_runner,
    )
    result = simulator.run_simulation(deck, {})
    data: dict[str, Any] = {}
    path = work_dir / f"{deck.stem}.raw" / "dc_on.dc"
    if result.ok and path.is_file():
        parsed = parse_spectre_psf_ascii(path)
        if not parsed.ok:
            raise RuntimeError(f"Failed to parse {path}: {parsed.errors}")
        data = parsed.data
    return result, data


def _condition_name(process: str, supply_v: float, temperature_c: float) -> str:
    supply_mv = int(round(supply_v * 1000))
    temperature = f"m{abs(int(temperature_c))}" if temperature_c < 0 else f"p{int(temperature_c)}"
    return f"{process.lower()}_v{supply_mv}_{temperature}"


def _base_record(
    candidate: dict[str, Any],
    family: dict[str, Any],
    process: str,
    model_section: str,
    supply_v: float,
    temperature_c: float,
) -> dict[str, Any]:
    width_um = int(candidate["multiplier"]) * float(family["finger_width_um"])
    return {
        "candidate": candidate["name"],
        "family": candidate["family"],
        "master": family["master"],
        "body_mode": family["body_mode"],
        "length_nm": int(candidate["length_nm"]),
        "multiplier": int(candidate["multiplier"]),
        "width_um": width_um,
        "process": process,
        "model_section": model_section,
        "supply_v": supply_v,
        "temperature_c": temperature_c,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--candidate")
    parser.add_argument("--case-limit", type=int, help="Limit PVT conditions for smoke testing")
    args = parser.parse_args()

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    families = config["families"]
    source_hashes: dict[str, str] = {}
    source_text: dict[str, str] = {}
    device_statements: dict[str, str] = {}
    for family, item in families.items():
        path = ROOT / item["source_netlist"]
        payload = path.read_bytes()
        source_hashes[family] = hashlib.sha256(payload).hexdigest()
        source_text[family] = payload.decode("utf-8")
        device_statements[family] = _extract_instance(source_text[family], "MN0")

    candidates = list(config["candidates"])
    if args.candidate:
        candidates = [item for item in candidates if item["name"] == args.candidate]
        if not candidates:
            raise ValueError(f"Unknown candidate: {args.candidate}")

    conditions = list(
        itertools.product(
            config["conditions"]["process"],
            config["conditions"]["supply_v"],
            config["conditions"]["temperature_c"],
        )
    )
    if args.case_limit is not None:
        conditions = conditions[: args.case_limit]

    args.output_root.mkdir(parents=True, exist_ok=True)
    deck_dir = args.output_root / "decks"
    deck_dir.mkdir(parents=True, exist_ok=True)
    target_ron = float(config["targets"]["maximum_on_resistance_ohm"])
    header = _extract_header(source_text["core"])
    failures = 0
    on_results: list[dict[str, Any]] = []
    off_results: list[dict[str, Any]] = []

    ssh_client = SSHClient.from_env(keep_remote_files=False, profile=args.profile)
    ssh_runner = ssh_client.spectre_runner
    if ssh_runner is None:
        raise RuntimeError("Configured Spectre SSH runner is unavailable")

    for index, condition in enumerate(conditions, start=1):
        process, supply_raw, temperature_raw = condition
        supply_v = float(supply_raw)
        temperature_c = float(temperature_raw)
        model_section = config["model_sections"][process]
        name = _condition_name(process, supply_v, temperature_c)
        print(f"[PVT {index}/{len(conditions)}] {name}: {len(candidates)} candidates", flush=True)
        deck_text, signal_map = _build_batch_deck(
            header,
            device_statements,
            candidates,
            families,
            model_section,
            supply_v,
            temperature_c,
            float(config["conditions"]["signal_margin_v"]),
            float(config["conditions"]["signal_common_mode_step_v"]),
            float(config["conditions"]["differential_probe_v"]),
        )
        deck = deck_dir / f"{name}.scs"
        deck.write_text(deck_text, encoding="utf-8")
        result, data = _run_deck(deck, args.output_root / name, args.profile, ssh_runner)
        if not result.ok or not data:
            failures += 1

        for candidate in candidates:
            family = families[candidate["family"]]
            common = _base_record(
                candidate,
                family,
                process,
                model_section,
                supply_v,
                temperature_c,
            )
            status = {
                "spectre_ok": result.ok,
                "status": result.status.value,
                "errors": result.errors[:10],
                "warnings": result.warnings[:10],
            }
            on_record = {**common, **status}
            off_record = {**common, **status}
            if result.ok and data:
                vcm = _sweep_axis(data)
                on_current = _as_float_list(data[signal_map[candidate["name"]]["on_current"]])
                off_current = _as_float_list(data[signal_map[candidate["name"]]["off_current"]])
                if len(vcm) != len(on_current) or len(vcm) != len(off_current):
                    raise RuntimeError(f"Axis/current length mismatch in {name}/{candidate['name']}")
                ron = [
                    float(config["conditions"]["differential_probe_v"]) / abs(value)
                    if abs(value) > 1e-18
                    else math.inf
                    for value in on_current
                ]
                gate_abs = [value + supply_v for value in vcm]
                body_tracks = family["body_mode"] == "signal_low"
                stress = {
                    "maximum_gate_absolute_v": max(abs(value) for value in gate_abs),
                    "maximum_abs_vgs_v": max(abs(supply_v + 0.5 * float(config["conditions"]["differential_probe_v"])), supply_v),
                    "maximum_abs_vgd_v": max(abs(supply_v - 0.5 * float(config["conditions"]["differential_probe_v"])), supply_v),
                    "maximum_abs_vgb_v": (
                        max(abs(supply_v + 0.5 * float(config["conditions"]["differential_probe_v"])), supply_v)
                        if body_tracks
                        else max(max(abs(value) for value in gate_abs), 0.0)
                    ),
                    "maximum_abs_vds_v": max(float(config["conditions"]["differential_probe_v"]), supply_v),
                }
                on_record.update(
                    {
                        "vcm_v": vcm,
                        "ron_ohm": ron,
                        "minimum_ron_ohm": min(ron),
                        "maximum_ron_ohm": max(ron),
                        "mean_ron_ohm": sum(ron) / len(ron),
                        "ron_flatness_peak_to_peak_over_mean": (
                            (max(ron) - min(ron)) / (sum(ron) / len(ron))
                        ),
                        "passes_ron_target": all(math.isfinite(value) for value in ron)
                        and max(ron) <= target_ron,
                        "commanded_terminal_stress": stress,
                    }
                )
                off_record["absolute_leakage_a"] = max(abs(value) for value in off_current)
            on_results.append(on_record)
            off_results.append(off_record)

    robust_candidates = []
    expected_conditions = len(conditions)
    for candidate in candidates:
        rows = [row for row in on_results if row["candidate"] == candidate["name"]]
        if (
            len(rows) == expected_conditions
            and all(row.get("spectre_ok") for row in rows)
            and all(row.get("passes_ron_target") for row in rows)
        ):
            robust_candidates.append(candidate["name"])

    summary = {
        "scope": "ideal_bootstrap_main_switch_global_pvt_screening",
        "config": str(args.config),
        "source_netlist_sha256": source_hashes,
        "model_sections": config["model_sections"],
        "conditions": config["conditions"],
        "targets": config["targets"],
        "expected_condition_count_per_candidate": expected_conditions,
        "candidate_count": len(candidates),
        "spectre_job_count": len(conditions),
        "on_results": on_results,
        "robust_ron_candidates": robust_candidates,
        "off_results": off_results,
    }
    summary_path = args.output_root / "run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    ssh_client.close()
    print(f"summary: {summary_path}")
    print(
        json.dumps(
            {
                "spectre_jobs": len(conditions),
                "on_cases": len(on_results),
                "off_cases": len(off_results),
                "robust_ron_candidates": robust_candidates,
                "failed_jobs": failures,
            },
            indent=2,
        )
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
