#!/usr/bin/env python3
"""Export and screen the independently named bootstrap OA prototype."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii
from virtuoso_bridge.spectre.runner import SpectreSimulator, spectre_mode_args
from virtuoso_bridge.transport.tunnel import SSHClient


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config/bootstrap_protected_eval.yaml"
OUTPUT = ROOT / "output/bootstrap_protected_eval"
PAIRS = {"Vgs": ("G", "S"), "Vgd": ("G", "D"), "Vgb": ("G", "B"),
         "Vds": ("D", "S"), "Vbs": ("B", "S"), "Vbd": ("B", "D")}
INTERNAL = ("G", "GCLAMP", "CTRL", "BTOP", "BBOT", "P1", "P2")


def export_source(profile: str, config: dict[str, Any], output: Path) -> tuple[str, str, Path]:
    target = output / "netlist" / config["testbench"]
    client = VirtuosoClient.from_env(profile=profile)
    result = client.schematic.export_netlist(
        config["library"], config["testbench"], target,
        simulator="spectre", recreate_all=True, timeout=180,
    )
    source = Path(result["input_file"])
    if not source.is_file():
        raise RuntimeError(f"OA export missing: {source}")
    raw = source.read_bytes()
    return raw.decode("utf-8"), hashlib.sha256(raw).hexdigest(), source


def device_map(source: str, dut: str,
               expected: dict[str, str]) -> dict[str, dict[str, str]]:
    match = re.search(rf"(?ms)^subckt {re.escape(dut)}\b.*?^ends {re.escape(dut)}\s*$", source)
    if not match:
        raise ValueError("Expected OA DUT subcircuit is missing")
    devices: dict[str, dict[str, str]] = {}
    for name, terminals, model in re.findall(
        r"(?m)^\s+(M[NP]\d+) \(([^)]+)\) (nch_mac|pch_mac|nch_18_mac|pch_18_mac)\b",
        match.group(),
    ):
        pins = terminals.split()
        if len(pins) != 4 or name in devices:
            raise ValueError(f"Ambiguous MOS statement: {name} {terminals}")
        devices[name] = dict(zip(("D", "G", "S", "B"), pins)) | {"model": model}
    actual = {name: entry["model"] for name, entry in devices.items()}
    if actual != expected:
        raise ValueError(f"OA model/instance map differs: {actual}")
    return devices


def prepare_deck(source: str, config: dict[str, Any]) -> tuple[str, list[str]]:
    text = source
    setting = "saveOptions options save=allpub"
    if text.count(setting) != 1:
        raise ValueError("OA export save-option contract changed")
    text = text.replace(setting, "saveOptions options save=selected", 1)
    saves = ["PHI", "PHIB", "VINP", "VINN", "VOUTP", "VOUTN"]
    for prefix in ("XP", "XN"):
        saves.extend(f"{prefix}.{name}" for name in INTERNAL)
    text += (
        "\n// Analysis only; all OA device/connectivity statements above are unchanged\n"
        "tran tran stop=285n maxstep=5p errpreset=conservative\n"
        f"save {' '.join(saves)}\n"
    )
    return text, saves


def run_spectre(deck: Path, profile: str, output: Path) -> tuple[Any, dict[str, Any]]:
    work_dir = output / "spectre" / deck.stem
    transport = SSHClient.from_env(keep_remote_files=False, profile=profile)
    if transport.spectre_runner is None:
        raise RuntimeError("Configured Spectre SSH runner is unavailable")
    try:
        simulator = SpectreSimulator.from_env(
            spectre_cmd=os.getenv("SPECTRE_CMD", "spectre"),
            spectre_args=spectre_mode_args("spectre"), timeout=600,
            work_dir=work_dir, output_format="psfascii", profile=profile,
            ssh_runner=transport.spectre_runner,
        )
        result = simulator.run_simulation(deck, {})
    finally:
        transport.close()
    raw_dir = work_dir / f"{deck.stem}.raw"
    wave = next((path for path in (raw_dir / "tran.tran", raw_dir / "tran.tran.tran")
                 if path.is_file()), None)
    if not result.ok or wave is None:
        return result, {}
    parsed = parse_spectre_psf_ascii(wave)
    if not parsed.ok:
        raise RuntimeError(f"Cannot parse {wave}: {parsed.errors}")
    return result, parsed.data


def signal(data: dict[str, Any], name: str) -> np.ndarray:
    aliases = {name.lower(), name.replace(".", ":").lower(),
               name.replace(".", "/").lower()}
    for key, value in data.items():
        if key.strip('"').lower() in aliases:
            return np.asarray(value, dtype=float)
    raise KeyError(f"Signal {name} missing; available={sorted(data)}")


def analyze(data: dict[str, Any], devices: dict[str, dict[str, str]],
            config: dict[str, Any]) -> dict[str, Any]:
    condition = config["conditions"]
    levels = config["diagnostic_model_warning_levels_v"]
    time = signal(data, "time")
    if len(time) < 1000 or not np.all(np.isfinite(time)) or not np.all(np.diff(time) > 0):
        raise ValueError("Incomplete/non-monotonic transient time base")
    cache = {name: signal(data, name) for name in (
        "PHI", "PHIB", "VINP", "VINN", "VOUTP", "VOUTN",
        *(f"{side}.{node}" for side in ("XP", "XN") for node in INTERNAL),
    )}
    if any(values.size != time.size or not np.all(np.isfinite(values))
           for values in cache.values()):
        raise ValueError("Non-finite or misaligned waveform")

    def terminal(node: str, side: str) -> np.ndarray:
        if node == "VSS":
            return np.zeros_like(time)
        if node == "VDD":
            return np.full_like(time, float(condition["supply_v"]))
        if node == "VIN":
            return cache["VINP" if side == "XP" else "VINN"]
        if node == "VOUT":
            return cache["VOUTP" if side == "XP" else "VOUTN"]
        if node in {"PHI", "PHIB"}:
            return cache[node]
        return cache[f"{side}.{node}"]

    driven = (time >= 200e-9) & (time <= 285e-9)
    rows = []
    for side in ("XP", "XN"):
        for name, dev in devices.items():
            for pair, (positive, negative) in PAIRS.items():
                difference = terminal(dev[positive], side) - terminal(dev[negative], side)
                index = int(np.argmax(np.abs(difference[driven])))
                selected = np.flatnonzero(driven)[index]
                limit = float(levels[dev["model"]])
                rows.append({"side": side, "device": name, "model": dev["model"],
                             "pair": pair, "peak_abs_v": float(abs(difference[selected])),
                             "signed_peak_v": float(difference[selected]),
                             "peak_time_ns": float(time[selected] * 1e9),
                             "diagnostic_limit_v": limit,
                             "above_diagnostic_limit": bool(abs(difference[selected]) > limit)})
    rows.sort(key=lambda row: row["peak_abs_v"] / row["diagnostic_limit_v"],
              reverse=True)
    acquire = int(np.argmin(np.abs(time - float(condition["acquisition_measure_s"]))))
    hold = int(np.argmin(np.abs(time - float(condition["hold_measure_s"]))))
    target = float(condition["target_differential_v"])
    acq_error = float(cache["VOUTP"][acquire] - cache["VOUTN"][acquire] - target)
    held_error = float(cache["VOUTP"][hold] - cache["VOUTN"][hold] - target)
    return {"acquisition_error_v": acq_error, "held_error_v": held_error,
            "raw_held_error_pass": abs(held_error) <= float(condition["raw_error_limit_v"]),
            "diagnostic_terminal_pass": not any(row["above_diagnostic_limit"] for row in rows),
            "terminal_metric_count": len(rows), "ranked_terminals": rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    source, digest, source_path = export_source(args.profile, config, args.output)
    devices = device_map(source, config["dut"], config["expected_netlisted_models"])
    deck_text, saves = prepare_deck(source, config)
    deck = args.output / "decks" / "protected_vdp800.scs"
    deck.parent.mkdir(parents=True, exist_ok=True)
    deck.write_text(deck_text, encoding="utf-8")
    result, data = run_spectre(deck, args.profile, args.output)
    metrics = analyze(data, devices, config) if result.ok and data else {}
    warnings = [warning for warning in result.warnings if "CMI-275" in warning]
    summary = {
        "oa_export": str(source_path), "oa_export_sha256": digest,
        "model_include_sections": [line for line in source.splitlines()
                                   if line.startswith("include ")],
        "config": config, "saved_signals": saves, "device_map": devices,
        "simulator": "Spectre 21.1 via t28_io", "spectre_ok": result.ok,
        "status": result.status.value, "errors": result.errors[:30],
        "soa_warning_count_retained": len(warnings), "soa_warnings": warnings[:30],
        "model_warning_pass": result.ok and not warnings,
        "metrics": metrics, "reliability_qualified": False,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / "run_summary.json"
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": str(path), "source_sha256": digest,
                      "spectre_ok": result.ok, "soa_warnings": len(warnings),
                      "held_error_v": metrics.get("held_error_v"),
                      "raw_held_error_pass": metrics.get("raw_held_error_pass")}, indent=2))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
