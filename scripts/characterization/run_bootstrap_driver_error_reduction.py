#!/usr/bin/env python3
"""Run a bounded transistor/clock screen around the exact bootstrap OA export."""

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
DEFAULT_CONFIG = ROOT / "config" / "bootstrap_driver_error_reduction.yaml"
DEFAULT_SOURCE = (
    ROOT / "output" / "bootstrap_driver_design" / "netlist"
    / "tb_sar_bootstrap_transient" / "input.scs"
)
DEFAULT_OUTPUT = ROOT / "output" / "bootstrap_driver_error_reduction" / "spectre"
EXPECTED_SOURCE_HASH = "f3818ef606de602671beac8b6728a1f5460958d03ca0299de0fc79e28132242c"
BASELINE_MULTIPLIERS = {"MN7": 2, "MN10": 4, "MP8": 4}


@dataclass(frozen=True)
class Candidate:
    name: str
    mn7_multi: int
    mn10_multi: int
    mp8_multi: int
    nonoverlap_s: float


@dataclass(frozen=True)
class Case:
    phase: str
    candidate: str
    input_kind: str
    input_v: float
    mn7_multi: int
    mn10_multi: int
    mp8_multi: int
    nonoverlap_s: float


def _fmt(value: float) -> str:
    return f"{value:.12g}"


def _extract_source(source: str) -> tuple[str, str]:
    includes = [line for line in source.splitlines() if line.startswith("include ")]
    if len(includes) < 3:
        raise ValueError("OA export model include contract changed")
    match = re.search(r"(?ms)^subckt sar_bootstrap\b.*?^ends sar_bootstrap\s*$", source)
    if not match:
        raise ValueError("sar_bootstrap subcircuit missing from OA export")
    return "simulator lang=spectre\nglobal 0\n" + "\n".join(includes) + "\n", match.group(0)


def _instance_block(subckt: str, instance: str) -> str:
    match = re.search(
        rf"(?ms)^    {re.escape(instance)}\b.*?(?=^    \S|^ends sar_bootstrap)",
        subckt,
    )
    if not match:
        raise ValueError(f"{instance} missing from sar_bootstrap")
    return match.group(0).rstrip()


def _variant_subckt(source_subckt: str, candidate: Candidate) -> tuple[str, dict[str, Any]]:
    result = source_subckt
    audit: dict[str, Any] = {}
    requested = {
        "MN7": candidate.mn7_multi,
        "MN10": candidate.mn10_multi,
        "MP8": candidate.mp8_multi,
    }
    for instance, new_multi in requested.items():
        before = _instance_block(result, instance)
        match = re.search(r"\bmulti=(\d+)\b", before)
        if not match or int(match.group(1)) != BASELINE_MULTIPLIERS[instance]:
            raise ValueError(f"{instance} baseline multiplier contract changed: {before}")
        after, count = re.subn(r"\bmulti=\d+\b", f"multi={new_multi}", before, count=1)
        if count != 1:
            raise ValueError(f"Could not edit exactly one multiplier on {instance}")
        if before != after:
            result, replace_count = result.replace(before, after, 1), result.count(before)
            if replace_count != 1:
                raise ValueError(f"Ambiguous {instance} statement replacement")
        audit[instance] = {
            "baseline_multi": BASELINE_MULTIPLIERS[instance],
            "requested_multi": new_multi,
            "statement_sha256": hashlib.sha256(after.encode()).hexdigest(),
        }
    expected_change_count = sum(
        requested[name] != BASELINE_MULTIPLIERS[name] for name in requested
    )
    actual_change_count = sum(
        _instance_block(source_subckt, name) != _instance_block(result, name)
        for name in requested
    )
    if actual_change_count != expected_change_count:
        raise ValueError("Subcircuit edit audit failed")
    return result, audit


def _candidate_from_mapping(name: str, values: dict[str, Any], base: dict[str, Any]) -> Candidate:
    return Candidate(
        name=name,
        mn7_multi=int(values.get("mn7_multi", base["mn7_multi"])),
        mn10_multi=int(values.get("mn10_multi", base["mn10_multi"])),
        mp8_multi=int(values.get("mp8_multi", base["mp8_multi"])),
        nonoverlap_s=float(values.get("nonoverlap_s", base["nonoverlap_s"])),
    )


def _candidates(config: dict[str, Any]) -> dict[str, Candidate]:
    base = config["baseline"]
    result = {"baseline": _candidate_from_mapping("baseline", {}, base)}
    labels = {
        "mn7_multi": "mn7",
        "mn10_multi": "mn10",
        "mp8_multi": "mp8",
        "nonoverlap_s": "gap",
    }
    for field, values in config["one_factor"].items():
        for value in values:
            if float(value) == float(base[field]):
                continue
            suffix = (
                f"{int(value)}" if field.endswith("multi")
                else f"{round(float(value) * 1e12):04d}p"
            )
            name = f"{labels[field]}_{suffix}"
            result[name] = _candidate_from_mapping(name, {field: value}, base)
    for item in config.get("combination_candidates", []):
        name = str(item["name"])
        if name in result:
            raise ValueError(f"Duplicate candidate name: {name}")
        result[name] = _candidate_from_mapping(name, item, base)
    return result


def _cases(config: dict[str, Any], phase: str) -> list[Case]:
    candidates = _candidates(config)
    conditions = config["conditions"]
    if phase == "screen":
        selections = list(candidates.values())
        stimuli = [("diff", float(conditions["screen_differential_input_v"]))]
    else:
        names = ["baseline", *config.get("confirmation_candidates", [])]
        unknown = set(names) - set(candidates)
        if unknown:
            raise ValueError(f"Unknown confirmation candidates: {sorted(unknown)}")
        selections = [candidates[name] for name in names]
        stimuli = [
            *(('diff', float(value)) for value in conditions["confirm_differential_input_v"]),
            *(('single', float(value)) for value in conditions["confirm_single_input_v"]),
        ]
    return [
        Case(phase, candidate.name, kind, value, candidate.mn7_multi,
             candidate.mn10_multi, candidate.mp8_multi, candidate.nonoverlap_s)
        for candidate in selections for kind, value in stimuli
    ]


def _case_name(case: Case) -> str:
    millivolts = int(round(case.input_v * 1000))
    signal = f"vd{'m' if millivolts < 0 else 'p'}{abs(millivolts):03d}"
    if case.input_kind == "single":
        signal = f"vin{millivolts:03d}"
    return f"{case.phase}_{case.candidate}_{signal}"


def _clock_sources(supply: float, gap: float) -> str:
    # The exact baseline deck uses PHIB width=41 ns and a 1-ns nominal gap.
    phib_width = 40e-9 + gap
    return (
        f"VPHIB (PHIB 0) vsource type=pulse val0={_fmt(supply)} val1=0 "
        f"period=100n delay=10n rise=100p fall=100p width={_fmt(phib_width)}\n"
        f"VPHI (PHI 0) vsource type=pulse val0=0 val1={_fmt(supply)} "
        "period=100n delay=11n rise=100p fall=100p width=39n"
    )


def _pulse(name: str, node: str, initial: float, target: float, delay: float) -> str:
    return (
        f"{name} ({node} 0) vsource type=pulse val0={_fmt(initial)} val1={_fmt(target)} "
        f"period=400n delay={_fmt(delay)} rise=100p fall=100p width=80n"
    )


def _source_initial(target: float, supply: float) -> float:
    return supply - 0.05 if target <= supply / 2 else 0.05


def _build_deck(
    case: Case, config: dict[str, Any], preamble: str, source_subckt: str
) -> tuple[str, list[str], dict[str, Any]]:
    candidate = Candidate(
        case.candidate, case.mn7_multi, case.mn10_multi,
        case.mp8_multi, case.nonoverlap_s,
    )
    subckt, audit = _variant_subckt(source_subckt, candidate)
    conditions, timing = config["conditions"], config["timing"]
    supply = float(conditions["supply_v"])
    vcm = float(conditions["common_mode_v"])
    load = float(conditions["load_f"])
    step = float(timing["input_step_s"])
    lines = [
        preamble + "\n" + subckt,
        f"VVDD (VDD 0) vsource dc={_fmt(supply)} type=dc",
        _clock_sources(supply, case.nonoverlap_s),
    ]
    if case.input_kind == "diff":
        vinp, vinn = vcm + case.input_v / 2, vcm - case.input_v / 2
        lines.extend([
            _pulse("VINP_SRC", "VINP_PRE", vinn, vinp, step),
            _pulse("VINN_SRC", "VINN_PRE", vinp, vinn, step),
            "RINP (VINP_PRE VINP) resistor r=50",
            "RINN (VINN_PRE VINN) resistor r=50",
            f"CLOADP (VOUTP 0) capacitor c={_fmt(load)}",
            f"CLOADN (VOUTN 0) capacitor c={_fmt(load)}",
            "XBP (PHI PHIB VDD VINP VOUTP 0) sar_bootstrap",
            "XBN (PHI PHIB VDD VINN VOUTN 0) sar_bootstrap",
        ])
        saves = ["PHI", "PHIB", "VINP", "VINN", "VOUTP", "VOUTN"]
        for prefix in ("XBP", "XBN"):
            saves.extend(f"{prefix}.{node}" for node in (
                "G", "GCLAMP", "CTRL", "BTOP", "BBOT", "P1", "P2"
            ))
    else:
        target = case.input_v
        lines.extend([
            _pulse("VIN_SRC", "VIN_PRE", _source_initial(target, supply), target, step),
            "RIN (VIN_PRE VIN) resistor r=50",
            f"CLOAD (VOUT 0) capacitor c={_fmt(load)}",
            "XB (PHI PHIB VDD VIN VOUT 0) sar_bootstrap",
        ])
        saves = ["PHI", "PHIB", "VIN", "VOUT"]
        saves.extend(f"XB.{node}" for node in (
            "G", "GCLAMP", "CTRL", "BTOP", "BBOT", "P1", "P2"
        ))
    lines.extend([
        "simulatorOptions options psfversion=\"1.4.0\" reltol=1e-4 "
        "vabstol=1e-6 iabstol=1e-12 temp=27 tnom=27 gmin=1e-12 checklimitdest=psf",
        f"tran tran stop={_fmt(float(timing['stop_s']))} maxstep=5p errpreset=conservative",
        f"save {' '.join(saves)}",
        "saveOptions options save=selected",
    ])
    return "\n".join(lines) + "\n", saves, audit


def _as_floats(value: Any) -> list[float]:
    if isinstance(value, list):
        return [float(item.real if isinstance(item, complex) else item) for item in value]
    return [float(value.real if isinstance(value, complex) else value)]


def _find_signal(data: dict[str, Any], requested: str) -> list[float]:
    aliases = {requested, requested.lower(), requested.upper(),
               requested.replace(".", ":"), requested.replace(".", "/")}
    lowered = {alias.lower() for alias in aliases}
    for key, value in data.items():
        if key.strip('"').lower() in lowered:
            return _as_floats(value)
    raise KeyError(f"Signal {requested} missing; available={sorted(data)}")


def _run(deck: Path, work_dir: Path, profile: str, ssh_runner: Any) -> tuple[Any, dict[str, Any]]:
    simulator = SpectreSimulator.from_env(
        spectre_cmd=os.getenv("SPECTRE_CMD", "spectre"),
        spectre_args=spectre_mode_args("spectre"), timeout=600,
        work_dir=work_dir, output_format="psfascii",
        profile=profile, ssh_runner=ssh_runner,
    )
    result = simulator.run_simulation(deck, {})
    raw = work_dir / f"{deck.stem}.raw"
    path = next((item for item in (raw / "tran.tran", raw / "tran.tran.tran")
                 if item.is_file()), raw / "tran.tran")
    if not result.ok or not path.is_file():
        return result, {}
    parsed = parse_spectre_psf_ascii(path)
    if not parsed.ok:
        raise RuntimeError(f"Failed to parse {path}: {parsed.errors}")
    return result, parsed.data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--phase", choices=("screen", "confirm"), default="screen")
    parser.add_argument("--case-name")
    parser.add_argument("--candidate", action="append")
    parser.add_argument("--case-limit", type=int)
    parser.add_argument("--shard-count", type=int)
    parser.add_argument("--shard-index", type=int)
    parser.add_argument("--merge-shard", action="append", type=Path)
    args = parser.parse_args()

    source_bytes = args.source.read_bytes()
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    if source_hash != EXPECTED_SOURCE_HASH:
        raise ValueError(f"OA export hash changed: {source_hash} != {EXPECTED_SOURCE_HASH}")
    preamble, source_subckt = _extract_source(source_bytes.decode("utf-8"))
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    cases = _cases(config, args.phase)
    if args.candidate:
        requested = set(args.candidate)
        cases = [case for case in cases if case.candidate in requested]
        found = {case.candidate for case in cases}
        if found != requested:
            raise ValueError(f"Unknown candidates: {sorted(requested - found)}")
    if args.merge_shard:
        expected = {_case_name(case): case for case in cases}
        merged: dict[str, dict[str, Any]] = {}
        for shard_path in args.merge_shard:
            shard = json.loads(shard_path.read_text(encoding="utf-8"))
            if shard["oa_export_sha256"] != source_hash:
                raise ValueError(f"Shard source hash mismatch: {shard_path}")
            if shard["configuration"] != config or shard["phase"] != args.phase:
                raise ValueError(f"Shard configuration/phase mismatch: {shard_path}")
            for record in shard["records"]:
                name = record["name"]
                if name in merged:
                    previous_ok = (
                        merged[name].get("spectre_ok") and merged[name].get("signals")
                    )
                    current_ok = record.get("spectre_ok") and record.get("signals")
                    if previous_ok and not current_ok:
                        continue
                    if current_ok and not previous_ok:
                        merged[name] = record
                        continue
                    raise ValueError(f"Ambiguous duplicate shard case: {name}")
                merged[name] = record
        if set(merged) != set(expected):
            missing = sorted(set(expected) - set(merged))
            extra = sorted(set(merged) - set(expected))
            raise ValueError(f"Incomplete shard merge; missing={missing}, extra={extra}")
        records = [merged[_case_name(case)] for case in cases]
        failures = sum(
            not record.get("spectre_ok") or not record.get("signals")
            for record in records
        )
        summary = {
            "scope": config["stage"], "phase": args.phase,
            "oa_export": str(args.source), "oa_export_sha256": source_hash,
            "source_subckt_sha256": hashlib.sha256(source_subckt.encode()).hexdigest(),
            "simulator": "Spectre 21.1 via t28_io", "configuration": config,
            "case_count": len(records), "failed_case_count": failures,
            "records": records,
        }
        args.output_root.mkdir(parents=True, exist_ok=True)
        path = args.output_root / "run_summary.json"
        path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"summary": str(path), "cases": len(records),
                          "failed": failures}, indent=2))
        return 1 if failures else 0
    if args.case_name:
        cases = [case for case in cases if _case_name(case) == args.case_name]
        if not cases:
            raise ValueError(f"Unknown case: {args.case_name}")
    if args.case_limit is not None:
        cases = cases[:args.case_limit]
    if args.shard_count is not None or args.shard_index is not None:
        if args.shard_count is None or args.shard_index is None:
            raise ValueError("--shard-count and --shard-index must be paired")
        if args.shard_count < 1 or not 0 <= args.shard_index < args.shard_count:
            raise ValueError("Invalid shard count/index")
        cases = [case for index, case in enumerate(cases)
                 if index % args.shard_count == args.shard_index]

    args.output_root.mkdir(parents=True, exist_ok=True)
    decks = args.output_root / "decks"
    decks.mkdir(parents=True, exist_ok=True)
    ssh_client = SSHClient.from_env(keep_remote_files=False, profile=args.profile)
    if ssh_client.spectre_runner is None:
        raise RuntimeError("Configured Spectre SSH runner is unavailable")
    records, failures = [], 0
    try:
        for index, case in enumerate(cases, 1):
            name = _case_name(case)
            print(f"[case {index}/{len(cases)}] {name}", flush=True)
            text, saves, audit = _build_deck(case, config, preamble, source_subckt)
            deck = decks / f"{name}.scs"
            deck.write_text(text, encoding="utf-8")
            result, data = _run(deck, args.output_root / name, args.profile,
                                ssh_client.spectre_runner)
            if not result.ok or not data:
                failures += 1
            signals = {"time": _find_signal(data, "time")} if data else {}
            for signal in saves if data else []:
                signals[signal] = _find_signal(data, signal)
            records.append({
                "name": name, **asdict(case), "spectre_ok": result.ok,
                "status": result.status.value, "errors": result.errors[:20],
                "warnings": result.warnings[:40], "edit_audit": audit,
                "variant_subckt_sha256": hashlib.sha256(
                    _variant_subckt(source_subckt, Candidate(
                        case.candidate, case.mn7_multi, case.mn10_multi,
                        case.mp8_multi, case.nonoverlap_s,
                    ))[0].encode()
                ).hexdigest(),
                "signals": signals,
            })
    finally:
        ssh_client.close()
    summary = {
        "scope": config["stage"], "phase": args.phase,
        "oa_export": str(args.source), "oa_export_sha256": source_hash,
        "source_subckt_sha256": hashlib.sha256(source_subckt.encode()).hexdigest(),
        "simulator": "Spectre 21.1 via t28_io", "configuration": config,
        "case_count": len(records), "failed_case_count": failures,
        "records": records,
    }
    path = args.output_root / "run_summary.json"
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": str(path), "cases": len(records),
                      "failed": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
