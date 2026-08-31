#!/usr/bin/env python3
"""Run finite-Cboot transistor-level bootstrap transients from the OA export."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import re
from pathlib import Path
from typing import Any

import yaml

from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii
from virtuoso_bridge.spectre.runner import SpectreSimulator, spectre_mode_args
from virtuoso_bridge.transport.tunnel import SSHClient


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "bootstrap_driver_screening.yaml"
DEFAULT_SOURCE = (
    ROOT / "output" / "bootstrap_driver_design" / "netlist"
    / "tb_sar_bootstrap_transient" / "input.scs"
)
DEFAULT_OUTPUT = ROOT / "output" / "bootstrap_driver_design" / "spectre"
NODES = ("PHI", "PHIB", "VDD", "VIN", "VOUT", "G", "GCLAMP", "BTOP", "BBOT", "CTRL", "P1", "P2")


def _replace_one(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE | re.IGNORECASE)
    if count != 1:
        raise ValueError(f"Could not parameterize {label}; matches={count}")
    return updated


def _format_si(value: float) -> str:
    return f"{value:.12g}"


def _build_deck(
    source: str,
    *,
    section: str,
    supply_v: float,
    temperature_c: float,
    input_v: float,
    cboot_f: float,
    main_switch_width_m: float | None,
    stop_s: float,
) -> str:
    text = _replace_one(
        source,
        r'^(include\s+"[^"\n]+"\s+section=)(?:ss|tt|ff)macro_mos_moscap\s*$',
        rf"\g<1>{section}",
        "MOS model section",
    )
    text = _replace_one(text, r'^(\s*CBOOT\s+\([^\n]+\)\s+capacitor\s+c=)\S+',
                        rf"\g<1>{_format_si(cboot_f)}", "CBOOT")
    initial_input_v = supply_v - 0.05 if input_v <= supply_v / 2.0 else 0.05
    text = _replace_one(text, r'^(VVIN\s+\([^\n]+\)\s+vsource[^\n]*val0=)\S+',
                        rf"\g<1>{_format_si(initial_input_v)}", "initial input voltage")
    text = _replace_one(text, r'^(VVIN\s+\([^\n]+\)\s+vsource[^\n]*val0=\S+\s+val1=)\S+',
                        rf"\g<1>{_format_si(input_v)}", "target input voltage")
    text = _replace_one(text, r'^(VVDD\s+\([^\n]+\)\s+vsource\s+dc=)\S+',
                        rf"\g<1>{_format_si(supply_v)}", "supply voltage")
    if main_switch_width_m is not None:
        multiplier = main_switch_width_m / 250e-9
        rounded = round(multiplier)
        if not abs(multiplier - rounded) < 1e-9 or rounded < 1:
            raise ValueError(
                "Main-switch total width must be a positive integer multiple of 250 nm"
            )
        text = _replace_one(
            text,
            r'^(\s*MN11\s+\([^\n]+\)\s+nch_mac[^\n]*\bmulti=)\S+',
            rf"\g<1>{rounded}",
            "MN11 main-switch multiplier",
        )
    text = _replace_one(text, r'^(VPHIB\s+\([^\n]+\)\s+vsource[^\n]*val0=)\S+',
                        rf"\g<1>{_format_si(supply_v)}", "PHIB high")
    text = _replace_one(text, r'^(VPHI\s+\([^\n]+\)\s+vsource[^\n]*val0=0\s+val1=)\S+',
                        rf"\g<1>{_format_si(supply_v)}", "PHI high")
    text = _replace_one(text, r'(\btemp=)\S+', rf"\g<1>{_format_si(temperature_c)}", "temperature")
    text = re.sub(r'^saveOptions\s+options\s+save=allpub\s*$', '', text,
                  count=1, flags=re.MULTILINE | re.IGNORECASE)
    save_nodes = [node if node in {"PHI", "PHIB", "VDD", "VIN", "VOUT"} else f"XBOOT.{node}"
                  for node in NODES]
    text += (
        "\n// Analysis-only wrapper statements; OA-exported circuit above is unchanged\n"
        f"tran tran stop={_format_si(stop_s)} maxstep=5p errpreset=conservative\n"
        f"save {' '.join(save_nodes)}\n"
        "saveOptions options save=selected\n"
    )
    return text


def _as_float_list(value: Any) -> list[float]:
    if isinstance(value, list):
        return [float(item.real if isinstance(item, complex) else item) for item in value]
    return [float(value.real if isinstance(value, complex) else value)]


def _find_signal(data: dict[str, Any], requested: str) -> list[float]:
    aliases = {
        requested,
        requested.lower(),
        requested.upper(),
        requested.replace(".", ":"),
        requested.replace(".", "/"),
    }
    for key, value in data.items():
        normalized = key.strip('"')
        if normalized in aliases or normalized.lower() in {item.lower() for item in aliases}:
            return _as_float_list(value)
    raise KeyError(f"Signal {requested} missing; available={sorted(data)}")


def _run_deck(deck: Path, work_dir: Path, profile: str, ssh_runner: Any) -> tuple[Any, dict[str, Any]]:
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
    paths = (raw_dir / "tran.tran", raw_dir / "tran.tran.tran")
    path = next((candidate for candidate in paths if candidate.is_file()), paths[0])
    if result.ok and path.is_file():
        parsed = parse_spectre_psf_ascii(path)
        if not parsed.ok:
            raise RuntimeError(f"Failed to parse {path}: {parsed.errors}")
        data = parsed.data
    return result, data


def _case_name(
    process: str,
    supply_v: float,
    temperature_c: float,
    input_v: float,
    cboot_f: float,
    main_switch_width_m: float | None = None,
) -> str:
    temp = f"m{abs(int(temperature_c))}" if temperature_c < 0 else f"p{int(temperature_c)}"
    name = (
        f"{process.lower()}_v{round(supply_v * 1000):03d}_{temp}"
        f"_vin{round(input_v * 1000):03d}_cb{round(cboot_f * 1e15):03d}f"
    )
    if main_switch_width_m is not None:
        name += f"_wm{round(main_switch_width_m * 1e9):04d}n"
    return name


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--case-limit", type=int)
    parser.add_argument("--case-name", help="Run only the named generated case")
    parser.add_argument(
        "--merge-summary",
        action="store_true",
        help="Replace rerun cases in an existing run_summary.json",
    )
    args = parser.parse_args()

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    source_bytes = args.source.read_bytes()
    source_text = source_bytes.decode("utf-8")
    cases = list(itertools.product(
        config["conditions"]["process"],
        config["conditions"]["supply_v"],
        config["conditions"]["temperature_c"],
        config["conditions"]["input_v"],
        config["conditions"]["cboot_f"],
        config["conditions"].get("main_switch_width_m", [None]),
    ))
    if args.case_limit is not None:
        cases = cases[:args.case_limit]
    if args.case_name:
        cases = [case for case in cases if _case_name(
            str(case[0]), float(case[1]), float(case[2]), float(case[3]), float(case[4]),
            None if case[5] is None else float(case[5]),
        ) == args.case_name]
        if not cases:
            raise ValueError(f"Unknown case name: {args.case_name}")
    args.output_root.mkdir(parents=True, exist_ok=True)
    deck_dir = args.output_root / "decks"
    deck_dir.mkdir(parents=True, exist_ok=True)

    ssh_client = SSHClient.from_env(keep_remote_files=False, profile=args.profile)
    ssh_runner = ssh_client.spectre_runner
    if ssh_runner is None:
        raise RuntimeError("Configured Spectre SSH runner is unavailable")
    records = []
    failures = 0
    for index, (process, supply_raw, temp_raw, input_raw, cboot_raw, width_raw) in enumerate(cases, start=1):
        supply_v, temperature_c = float(supply_raw), float(temp_raw)
        input_v, cboot_f = float(input_raw), float(cboot_raw)
        main_switch_width_m = None if width_raw is None else float(width_raw)
        name = _case_name(
            process, supply_v, temperature_c, input_v, cboot_f, main_switch_width_m
        )
        print(f"[case {index}/{len(cases)}] {name}", flush=True)
        deck = deck_dir / f"{name}.scs"
        deck.write_text(_build_deck(
            source_text,
            section=config["model_sections"][process],
            supply_v=supply_v,
            temperature_c=temperature_c,
            input_v=input_v,
            cboot_f=cboot_f,
            main_switch_width_m=main_switch_width_m,
            stop_s=float(config["timing"]["stop_s"]),
        ), encoding="utf-8")
        result, data = _run_deck(deck, args.output_root / name, args.profile, ssh_runner)
        if not result.ok or not data:
            failures += 1
        signals: dict[str, list[float]] = {}
        if data:
            signals["time"] = _find_signal(data, "time")
            for node in NODES:
                requested = node if node in {"PHI", "PHIB", "VDD", "VIN", "VOUT"} else f"XBOOT.{node}"
                signals[node] = _find_signal(data, requested)
        records.append({
            "name": name,
            "process": process,
            "model_section": config["model_sections"][process],
            "supply_v": supply_v,
            "temperature_c": temperature_c,
            "input_v": input_v,
            "cboot_f": cboot_f,
            "main_switch_width_m": main_switch_width_m,
            "spectre_ok": result.ok,
            "status": result.status.value,
            "errors": result.errors[:20],
            "warnings": result.warnings[:20],
            "signals": signals,
            "available_signals": sorted(data),
        })

    path = args.output_root / "run_summary.json"
    if args.merge_summary and path.is_file():
        previous = json.loads(path.read_text(encoding="utf-8"))
        previous_hash = previous.get("oa_export_sha256")
        current_hash = hashlib.sha256(source_bytes).hexdigest()
        if previous_hash != current_hash:
            raise ValueError(
                "Cannot merge summaries from different OA exports: "
                f"{previous_hash} != {current_hash}"
            )
        merged = {record["name"]: record for record in previous.get("records", [])}
        merged.update({record["name"]: record for record in records})
        records = list(merged.values())
        failures = sum(
            1 for record in records
            if not record.get("spectre_ok") or not record.get("signals")
        )

    summary = {
        "scope": config["stage"],
        "oa_export": str(args.source),
        "oa_export_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "simulator": "Spectre 21.1 via t28_io",
        "configuration": config,
        "case_count": len(records),
        "failed_case_count": failures,
        "records": records,
    }
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    ssh_client.close()
    print(json.dumps({"summary": str(path), "cases": len(cases), "failed": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
