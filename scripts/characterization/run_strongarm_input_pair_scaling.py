#!/usr/bin/env python3
"""Exact-OA-netlist Spectre screen for input-pair-finger StrongARM variants."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml
from virtuoso_bridge import VirtuosoClient

import verify_strongarm_t28 as verify


PROJECT = Path(__file__).resolve().parents[2]
CONFIG = PROJECT / "config" / "strongarm_input_pair_scaling.yaml"
BASE_CONFIG = PROJECT / "config" / "strongarm_t28_verification.yaml"
ROOT = PROJECT / "output" / "strongarm_input_pair_scaling"
BASELINE = (PROJECT / "output" / "strongarm_t28_verification" / "netlist"
            / "tb_sar_strongarm_t28" / "input.scs")


def digest(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def block(source: str, name: str) -> str:
    start, end = f"subckt {name} ", f"ends {name}"
    if source.count(start) != 1 or source.count(end) != 1:
        raise RuntimeError(f"Missing/repeated subckt {name}")
    return start + source.split(start, 1)[1].split(end, 1)[0] + end


def devices(subckt: str) -> dict[str, str]:
    pieces = re.split(r"(?=^    M[A-Z0-9_]+ \()", subckt, flags=re.MULTILINE)
    result: dict[str, str] = {}
    for piece in pieces[1:]:
        match = re.match(r"    (M[A-Z0-9_]+) \(", piece)
        if match:
            result[match.group(1)] = piece.split("ends ", 1)[0]
    return result


def validate_export(source: str, candidate: dict[str, Any]) -> dict[str, Any]:
    if not BASELINE.is_file():
        raise FileNotFoundError("Previous exact baseline export missing")
    baseline = BASELINE.read_text(encoding="utf-8")
    old = devices(block(baseline, "sar_strongarm_t28"))
    new = devices(block(source, candidate["dut"]))
    if set(old) != set(new) or len(new) != 11:
        raise RuntimeError("Comparator device set changed")
    for name in old:
        if name not in {"MNINP", "MNINN"}:
            if new[name] != old[name]:
                raise RuntimeError(f"Unexpected netlist change at {name}")
        else:
            prior = re.search(r"^    [^\n]+", old[name]).group()
            current = re.search(r"^    [^\n]+", new[name]).group()
            pin_pattern = r"\([^)]*\) nch_mac l=30n "
            old_pin = re.search(pin_pattern, prior)
            new_pin = re.search(pin_pattern, current)
            if (not old_pin or not new_pin or old_pin.group() != new_pin.group()
                    or "w=1u multi=1 nf=1" not in prior
                    or f"w={candidate['input_pair_fingers']}u multi=1 "
                       f"nf={candidate['input_pair_fingers']}" not in current):
                raise RuntimeError(f"Unexpected pair netlist at {name}: {current}")
    if f"XCMP (CLK OUTN OUTP VDD VINN VINP 0) {candidate['dut']}" not in source:
        raise RuntimeError("Standalone testbench comparator connection changed")
    return {"source_sha256": digest(source),
            "dut_sha256": digest(block(source, candidate["dut"])),
            "baseline_dut_sha256": digest(block(baseline, "sar_strongarm_t28")),
            "device_count": len(new), "only_input_pair_changed": True,
            "cellview": f"SAR_ADC_T28/{candidate['testbench']}/schematic",
            "model_section": "ttmacro_mos_moscap", "simulator": "Spectre 21.1"}


def get_candidate(tag: str) -> tuple[dict[str, Any], dict[str, Any]]:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    if config["library"] != "SAR_ADC_T28" or config["profile"] != "t28_io":
        raise RuntimeError("Unexpected library/profile")
    matches = [item for item in config["candidates"] if item["tag"] == tag]
    if len(matches) != 1:
        raise RuntimeError(f"Unknown/ambiguous candidate {tag}")
    return config, matches[0]


def export(config: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    client = VirtuosoClient.from_env(profile=config["profile"])
    info = client.library.get(config["library"])
    if (info.path != "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28"
            or info.technology_library != "tsmcN28"):
        raise RuntimeError(f"Unexpected OA library: {info}")
    place = ROOT / candidate["tag"] / "netlist" / candidate["testbench"]
    result = client.schematic.export_netlist(config["library"],
                                             candidate["testbench"], place,
                                             simulator="spectre", recreate_all=True,
                                             timeout=180)
    source = Path(result["input_file"]).read_text(encoding="utf-8")
    provenance = validate_export(source, candidate)
    provenance["source_file"] = str(result["input_file"])
    provenance["profile"] = config["profile"]
    location = ROOT / candidate["tag"] / "provenance.json"
    location.parent.mkdir(parents=True, exist_ok=True)
    location.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    return provenance


def read_source(candidate: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    folder = ROOT / candidate["tag"]
    source = (folder / "netlist" / candidate["testbench"] / "input.scs").read_text(
        encoding="utf-8")
    provenance = json.loads((folder / "provenance.json").read_text(encoding="utf-8"))
    if validate_export(source, candidate)["source_sha256"] != provenance["source_sha256"]:
        raise RuntimeError("Exact OA export changed after provenance capture")
    return source, provenance


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", choices=("f2", "f4"), required=True)
    parser.add_argument("--stage", choices=("export", "pvt", "noise", "mismatch"),
                        required=True)
    args = parser.parse_args()
    config, candidate = get_candidate(args.candidate)
    if args.stage == "export":
        print(json.dumps(export(config, candidate), indent=2))
        return 0
    source, provenance = read_source(candidate)
    base_config = yaml.safe_load(BASE_CONFIG.read_text(encoding="utf-8"))
    base_config["noise"]["cycles"] = int(config["noise"]["cycles"])
    base_config["noise"]["differential_inputs_v"] = [
        float(value) for value in config["conditions"]["differential_inputs_v"]]
    base_config["mismatch"]["numruns"] = int(config["mismatch"]["numruns"])
    base_config["mismatch"]["differential_inputs_v"] = [
        float(value) for value in config["conditions"]["differential_inputs_v"]]
    verify.ROOT = ROOT / candidate["tag"]
    verify.dut_block = lambda text: block(text, candidate["dut"])
    if args.stage == "pvt":
        result = verify.pvt_stage(source, base_config, config["profile"],
                                  condition_name="tt_nominal",
                                  differential_override_v=None)
    elif args.stage == "noise":
        result = verify.noise_stage(source, base_config, config["profile"],
                                    smoke=False, cycles_override=None,
                                    differential_override_v=None)
    else:
        result = verify.mismatch_stage(source, base_config, config["profile"],
                                       numruns=int(config["mismatch"]["numruns"]),
                                       smoke=False)
    out = {"candidate": candidate, "stage": args.stage,
           "provenance": provenance, "result": result}
    location = ROOT / candidate["tag"] / f"{args.stage}_summary.json"
    location.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"summary: {location}")
    if args.stage == "pvt":
        return 0 if all(case["ok"] and case.get("nominal_window_pass")
                        for case in result["cases"]) else 1
    if args.stage == "noise":
        return 0 if len(result["cases"]) == 2 and all(case["ok"] and
                    not case.get("parse_errors") for case in result["cases"]) else 1
    return 0 if (result.get("paired_samples_same_statistics") and
                 len(result["cases"]) == 2 and
                 all(case["ok"] and case.get("waveform_variation_observed")
                     and not case.get("parse_error") for case in result["cases"])) else 1


if __name__ == "__main__":
    raise SystemExit(main())
