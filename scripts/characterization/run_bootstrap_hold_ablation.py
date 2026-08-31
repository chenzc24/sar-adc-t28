#!/usr/bin/env python3
"""Run full-driver and isolated-main-switch held-error diagnostics."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii
from virtuoso_bridge.spectre.runner import SpectreSimulator, spectre_mode_args
from virtuoso_bridge.transport.tunnel import SSHClient


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "bootstrap_hold_ablation.yaml"
DEFAULT_SOURCE = (
    ROOT / "output" / "bootstrap_driver_design" / "netlist"
    / "tb_sar_bootstrap_transient" / "input.scs"
)
DEFAULT_OUTPUT = ROOT / "output" / "bootstrap_hold_ablation" / "spectre"
EXPECTED_SOURCE_HASH = "f3818ef606de602671beac8b6728a1f5460958d03ca0299de0fc79e28132242c"


@dataclass(frozen=True)
class Case:
    mode: str
    input_v: float | None
    differential_input_v: float | None
    load_f: float
    gate_fall_s: float
    purpose: str


def _format_si(value: float) -> str:
    return f"{value:.12g}"


def _extract_contract(source: str) -> tuple[str, str, str]:
    include_lines = [line for line in source.splitlines() if line.startswith("include ")]
    if len(include_lines) < 3:
        raise ValueError("OA export does not contain the expected model includes")
    preamble = "simulator lang=spectre\nglobal 0\n" + "\n".join(include_lines) + "\n"
    subckt_match = re.search(
        r"(?ms)^subckt sar_bootstrap\b.*?^ends sar_bootstrap\s*$", source
    )
    if not subckt_match:
        raise ValueError("OA export does not contain sar_bootstrap subcircuit")
    subckt = subckt_match.group(0)
    main_match = re.search(r"(?ms)^    MN11\b.*?(?=^    \S|^ends sar_bootstrap)", subckt)
    if not main_match:
        raise ValueError("OA export does not contain the MN11 statement")
    main = main_match.group(0).rstrip()
    if "l=60n" not in main or "multi=8" not in main:
        raise ValueError("MN11 no longer matches the screened L60/W2 seed")
    isolated = (
        "subckt isolated_main G VIN VOUT\n"
        + main.replace("    MN11 (VOUT G VIN VIN)", "    MMAIN (VOUT G VIN VIN)", 1)
        + "\nends isolated_main"
    )
    return preamble, subckt, isolated


def _case_name(case: Case) -> str:
    if case.input_v is not None:
        signal = f"vin{round(case.input_v * 1000):03d}"
    else:
        value = int(round(float(case.differential_input_v) * 1000))
        signal = f"vd{'m' if value < 0 else 'p'}{abs(value):03d}"
    return (
        f"{case.mode}_{signal}_cl{round(case.load_f * 1e15):04d}f"
        f"_ef{round(case.gate_fall_s * 1e12):04d}p"
    )


def _cases(config: dict[str, Any]) -> list[Case]:
    conditions = config["conditions"]
    load = float(conditions["nominal_load_f"])
    edge = float(conditions["nominal_gate_fall_s"])
    cases: list[Case] = []
    for value in conditions["single_input_v"]:
        for mode in ("full_single", "isolated_single", "absolute_single"):
            cases.append(Case(mode, float(value), None, load, edge, "nominal_mode_compare"))
    for value in conditions["differential_input_v"]:
        for mode in ("full_diff", "isolated_diff", "absolute_diff"):
            cases.append(Case(mode, None, float(value), load, edge, "nominal_mode_compare"))
    for value in conditions["sensitivity_endpoint_input_v"]:
        for mode in ("isolated_single", "absolute_single"):
            for swept_load in conditions["load_sweep_f"]:
                cases.append(Case(
                    mode, float(value), None, float(swept_load), edge,
                    "load_sensitivity",
                ))
            for swept_edge in conditions["isolated_gate_fall_s"]:
                cases.append(Case(
                    mode, float(value), None, load, float(swept_edge),
                    "edge_sensitivity",
                ))
    unique: dict[str, Case] = {}
    for case in cases:
        unique.setdefault(_case_name(case), case)
    return list(unique.values())


def _source_initial(target: float, supply: float) -> float:
    return supply - 0.05 if target <= supply / 2.0 else 0.05


def _pulse_source(name: str, node: str, initial: float, target: float, delay: float) -> str:
    return (
        f"{name} ({node} 0) vsource type=pulse val0={_format_si(initial)} "
        f"val1={_format_si(target)} period=400n delay={_format_si(delay)} "
        "rise=100p fall=100p width=80n"
    )


def _clock_sources(supply: float) -> str:
    return (
        f"VPHIB (PHIB 0) vsource type=pulse val0={_format_si(supply)} val1=0 "
        "period=100n delay=10n rise=100p fall=100p width=41n\n"
        f"VPHI (PHI 0) vsource type=pulse val0=0 val1={_format_si(supply)} "
        "period=100n delay=11n rise=100p fall=100p width=39n"
    )


def _relative_gate(name: str, gate: str, source: str, supply: float, fall: float) -> str:
    return (
        f"{name} ({gate} {source}) vsource type=pulse val0=0 "
        f"val1={_format_si(supply)} period=100n delay=11n rise=100p "
        f"fall={_format_si(fall)} width=39n"
    )


def _absolute_gate(name: str, gate: str, high: float, fall: float) -> str:
    return (
        f"{name} ({gate} 0) vsource type=pulse val0=0 val1={_format_si(high)} "
        f"period=100n delay=11n rise=100p fall={_format_si(fall)} width=39n"
    )


def _analysis_footer(stop: float, saves: list[str]) -> str:
    return (
        "simulatorOptions options psfversion=\"1.4.0\" reltol=1e-4 "
        "vabstol=1e-6 iabstol=1e-12 temp=27 tnom=27 gmin=1e-12 "
        "checklimitdest=psf\n"
        f"tran tran stop={_format_si(stop)} maxstep=5p errpreset=conservative\n"
        f"save {' '.join(saves)}\n"
        "saveOptions options save=selected\n"
    )


def _build_deck(
    case: Case,
    config: dict[str, Any],
    preamble: str,
    full_subckt: str,
    isolated_subckt: str,
) -> tuple[str, list[str]]:
    conditions = config["conditions"]
    timing = config["timing"]
    supply = float(conditions["supply_v"])
    step = float(timing["input_step_s"])
    header = preamble + "\n" + (full_subckt if case.mode.startswith("full") else isolated_subckt)
    lines = [header, f"VVDD (VDD 0) vsource dc={_format_si(supply)} type=dc", _clock_sources(supply)]

    if case.mode.endswith("single"):
        target = float(case.input_v)
        lines.extend([
            _pulse_source("VVIN", "VIN_SRC", _source_initial(target, supply), target, step),
            "RIN (VIN_SRC VIN) resistor r=50",
            f"CLOAD (VOUT 0) capacitor c={_format_si(case.load_f)}",
        ])
        if case.mode == "full_single":
            lines.append("XB (PHI PHIB VDD VIN VOUT 0) sar_bootstrap")
            saves = ["PHI", "PHIB", "VIN", "VOUT", "XB.G", "XB.BTOP", "XB.BBOT"]
        elif case.mode == "isolated_single":
            lines.extend([
                "XM (G VIN VOUT) isolated_main",
                _relative_gate("VGATE", "G", "VIN", supply, case.gate_fall_s),
            ])
            saves = ["PHI", "PHIB", "VIN", "VOUT", "G"]
        else:
            lines.extend([
                "XM (G VIN VOUT) isolated_main",
                _absolute_gate("VGATE", "G", target + supply, case.gate_fall_s),
            ])
            saves = ["PHI", "PHIB", "VIN", "VOUT", "G"]
    else:
        vdiff = float(case.differential_input_v)
        vcm = float(conditions["common_mode_v"])
        vinp, vinn = vcm + vdiff / 2.0, vcm - vdiff / 2.0
        lines.extend([
            _pulse_source("Vinp", "VINP_SRC", vinn, vinp, step),
            _pulse_source("Vinn", "VINN_SRC", vinp, vinn, step),
            "RINP (VINP_SRC VINP) resistor r=50",
            "RINN (VINN_SRC VINN) resistor r=50",
            f"CLOADP (VOUTP 0) capacitor c={_format_si(case.load_f)}",
            f"CLOADN (VOUTN 0) capacitor c={_format_si(case.load_f)}",
        ])
        if case.mode == "full_diff":
            lines.extend([
                "XBP (PHI PHIB VDD VINP VOUTP 0) sar_bootstrap",
                "XBN (PHI PHIB VDD VINN VOUTN 0) sar_bootstrap",
            ])
            saves = [
                "PHI", "PHIB", "VINP", "VINN", "VOUTP", "VOUTN",
                "XBP.G", "XBN.G",
            ]
        elif case.mode == "isolated_diff":
            lines.extend([
                "XMP (GP VINP VOUTP) isolated_main",
                "XMN (GN VINN VOUTN) isolated_main",
                _relative_gate("VGATEP", "GP", "VINP", supply, case.gate_fall_s),
                _relative_gate("VGATEN", "GN", "VINN", supply, case.gate_fall_s),
            ])
            saves = ["PHI", "PHIB", "VINP", "VINN", "VOUTP", "VOUTN", "GP", "GN"]
        else:
            lines.extend([
                "XMP (GP VINP VOUTP) isolated_main",
                "XMN (GN VINN VOUTN) isolated_main",
                _absolute_gate("VGATEP", "GP", vinp + supply, case.gate_fall_s),
                _absolute_gate("VGATEN", "GN", vinn + supply, case.gate_fall_s),
            ])
            saves = ["PHI", "PHIB", "VINP", "VINN", "VOUTP", "VOUTN", "GP", "GN"]
    lines.append(_analysis_footer(float(timing["stop_s"]), saves))
    return "\n".join(lines) + "\n", saves


def _as_floats(value: Any) -> list[float]:
    if isinstance(value, list):
        return [float(item.real if isinstance(item, complex) else item) for item in value]
    return [float(value.real if isinstance(value, complex) else value)]


def _find_signal(data: dict[str, Any], requested: str) -> list[float]:
    aliases = {
        requested, requested.lower(), requested.upper(),
        requested.replace(".", ":"), requested.replace(".", "/"),
    }
    lowered = {alias.lower() for alias in aliases}
    for key, value in data.items():
        if key.strip('"').lower() in lowered:
            return _as_floats(value)
    raise KeyError(f"Signal {requested} missing; available={sorted(data)}")


def _run(deck: Path, work_dir: Path, profile: str, ssh_runner: Any) -> tuple[Any, dict[str, Any]]:
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
    raw_dir = work_dir / f"{deck.stem}.raw"
    path = next(
        (candidate for candidate in (raw_dir / "tran.tran", raw_dir / "tran.tran.tran") if candidate.is_file()),
        raw_dir / "tran.tran",
    )
    if result.ok and path.is_file():
        parsed = parse_spectre_psf_ascii(path)
        if not parsed.ok:
            raise RuntimeError(f"Failed to parse {path}: {parsed.errors}")
        data = parsed.data
    return result, data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--case-limit", type=int)
    parser.add_argument("--case-name")
    parser.add_argument("--mode", action="append")
    parser.add_argument("--purpose", action="append")
    parser.add_argument("--shard-count", type=int)
    parser.add_argument("--shard-index", type=int)
    parser.add_argument(
        "--merge-shard",
        action="append",
        type=Path,
        help="Merge one completed shard summary; repeat for every shard",
    )
    args = parser.parse_args()

    source_bytes = args.source.read_bytes()
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    if source_hash != EXPECTED_SOURCE_HASH:
        raise ValueError(f"OA export hash changed: {source_hash} != {EXPECTED_SOURCE_HASH}")
    source = source_bytes.decode("utf-8")
    preamble, full_subckt, isolated_subckt = _extract_contract(source)
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    cases = _cases(config)
    if args.merge_shard:
        expected_names = {_case_name(case) for case in cases}
        merged: dict[str, dict[str, Any]] = {}
        for shard_path in args.merge_shard:
            shard = json.loads(shard_path.read_text(encoding="utf-8"))
            if shard["oa_export_sha256"] != source_hash:
                raise ValueError(f"Shard source hash mismatch: {shard_path}")
            if shard["configuration"] != config:
                raise ValueError(f"Shard configuration mismatch: {shard_path}")
            for record in shard["records"]:
                if record["name"] in merged:
                    raise ValueError(f"Duplicate shard case: {record['name']}")
                merged[record["name"]] = record
        if set(merged) != expected_names:
            missing = sorted(expected_names - set(merged))
            extra = sorted(set(merged) - expected_names)
            raise ValueError(f"Incomplete shard merge; missing={missing}, extra={extra}")
        ordered = []
        for case in cases:
            record = merged[_case_name(case)]
            record.update(asdict(case))
            ordered.append(record)
        failures = sum(
            1 for record in ordered
            if not record.get("spectre_ok") or not record.get("signals")
        )
        summary = {
            "scope": config["stage"],
            "oa_export": str(args.source),
            "oa_export_sha256": source_hash,
            "sar_bootstrap_subckt_sha256": hashlib.sha256(full_subckt.encode()).hexdigest(),
            "isolated_main_subckt_sha256": hashlib.sha256(isolated_subckt.encode()).hexdigest(),
            "simulator": "Spectre 21.1 via t28_io",
            "configuration": config,
            "case_count": len(ordered),
            "failed_case_count": failures,
            "records": ordered,
        }
        args.output_root.mkdir(parents=True, exist_ok=True)
        path = args.output_root / "run_summary.json"
        path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"summary": str(path), "cases": len(ordered), "failed": failures}, indent=2))
        return 1 if failures else 0
    if args.case_name:
        cases = [case for case in cases if _case_name(case) == args.case_name]
        if not cases:
            raise ValueError(f"Unknown case: {args.case_name}")
    if args.mode:
        cases = [case for case in cases if case.mode in set(args.mode)]
        if not cases:
            raise ValueError(f"No cases matched modes: {args.mode}")
    if args.purpose:
        cases = [case for case in cases if case.purpose in set(args.purpose)]
        if not cases:
            raise ValueError(f"No cases matched purposes: {args.purpose}")
    if args.case_limit is not None:
        cases = cases[:args.case_limit]
    if args.shard_count is not None or args.shard_index is not None:
        if args.shard_count is None or args.shard_index is None:
            raise ValueError("--shard-count and --shard-index must be provided together")
        if args.shard_count < 1 or not 0 <= args.shard_index < args.shard_count:
            raise ValueError("Invalid shard count/index")
        cases = [
            case for index, case in enumerate(cases)
            if index % args.shard_count == args.shard_index
        ]

    args.output_root.mkdir(parents=True, exist_ok=True)
    deck_dir = args.output_root / "decks"
    deck_dir.mkdir(parents=True, exist_ok=True)
    ssh_client = SSHClient.from_env(keep_remote_files=False, profile=args.profile)
    ssh_runner = ssh_client.spectre_runner
    if ssh_runner is None:
        raise RuntimeError("Configured Spectre SSH runner is unavailable")

    records = []
    failures = 0
    for index, case in enumerate(cases, start=1):
        name = _case_name(case)
        print(f"[case {index}/{len(cases)}] {name}", flush=True)
        deck_text, saves = _build_deck(case, config, preamble, full_subckt, isolated_subckt)
        deck = deck_dir / f"{name}.scs"
        deck.write_text(deck_text, encoding="utf-8")
        result, data = _run(deck, args.output_root / name, args.profile, ssh_runner)
        if not result.ok or not data:
            failures += 1
        signals = {"time": _find_signal(data, "time")} if data else {}
        if data:
            for signal in saves:
                signals[signal] = _find_signal(data, signal)
        records.append({
            "name": name,
            **asdict(case),
            "spectre_ok": result.ok,
            "status": result.status.value,
            "errors": result.errors[:20],
            "warnings": result.warnings[:30],
            "signals": signals,
            "available_signals": sorted(data),
        })

    summary = {
        "scope": config["stage"],
        "oa_export": str(args.source),
        "oa_export_sha256": source_hash,
        "sar_bootstrap_subckt_sha256": hashlib.sha256(full_subckt.encode()).hexdigest(),
        "isolated_main_subckt_sha256": hashlib.sha256(isolated_subckt.encode()).hexdigest(),
        "simulator": "Spectre 21.1 via t28_io",
        "configuration": config,
        "case_count": len(records),
        "failed_case_count": failures,
        "records": records,
    }
    path = args.output_root / "run_summary.json"
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    ssh_client.close()
    print(json.dumps({"summary": str(path), "cases": len(records), "failed": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
