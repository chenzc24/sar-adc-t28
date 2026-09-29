#!/usr/bin/env python3
"""Create one independent W185 full-CDAC plus T28 StrongARM diagnostic bench."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.schematic.ops import (
    schematic_create_inst_by_master_name as inst,
    schematic_label_instance_term as term,
)

import create_bootstrap_bottom_plate_eval as base


PROJECT = Path(__file__).resolve().parents[2]
CONFIG = PROJECT / "config" / "strongarm_cdac_integration.yaml"
OUTPUT = PROJECT / "output" / "strongarm_cdac_integration" / "readback.json"


def compact_instance(item: dict) -> dict:
    return {key: item.get(key) for key in ("name", "lib", "cell", "terms", "params")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    args = parser.parse_args()
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    library = config["library"]
    target = config["testbench"]
    if library != "SAR_ADC_T28" or target != "tb_sar_cdac_strongarm_diag":
        raise RuntimeError("Unexpected owned OA target")
    if config["cdac"] != "sar_cdac_bottom_plate_clamp_w185_eval_10b":
        raise RuntimeError("Unexpected CDAC dependency")
    client = VirtuosoClient.from_env(profile=args.profile)
    info = client.library.get(library)
    if (info.path != "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28"
            or info.technology_library != "tsmcN28"):
        raise RuntimeError(f"Unexpected library mapping: {info}")
    if base.exists(client, target):
        raise RuntimeError(f"Refusing to overwrite {library}/{target}")
    for cell in (config["cdac"], config["comparator"]):
        if not base.exists(client, cell, "schematic") or not base.exists(client, cell, "symbol"):
            raise RuntimeError(f"Missing saved schematic/symbol: {library}/{cell}")
        if base.markers(client, cell):
            raise RuntimeError(f"Existing source has check markers: {library}/{cell}")

    # Reuse the proven 21-instance sampling fixture, but write only to the
    # independently named target. The source CDAC is never opened for writes.
    base.TB = target
    base.CDAC = config["cdac"]
    base.T28_CLAMP = True
    base.create_tb(client)
    with client.schematic.modify(library, target, timeout=120) as sch:
        sch.add(inst(library, config["comparator"], "symbol", "XCMP", 30.0, -6.0, "R0"))
        for pin_name, net in (
            ("VINP", "TOPP_BP"), ("VINN", "TOPN_BP"),
            ("VDD", "VDD"), ("VSS", "gnd!"), ("CLK", "COMP_CLK"),
            ("OUTP", "CMP_OUTP"), ("OUTN", "CMP_OUTN"),
        ):
            sch.add(term("XCMP", pin_name, net))
        sch.add(inst("analogLib", "vpulse", "symbol", "VCOMP", 31.0, -13.0, "R0"))
        sch.add(term("VCOMP", "PLUS", "COMP_CLK"))
        sch.add(term("VCOMP", "MINUS", "gnd!"))
        for name, net, x in (("COUTP", "CMP_OUTP", 39.0),
                             ("COUTN", "CMP_OUTN", 42.0)):
            sch.add(inst("analogLib", "cap", "symbol", name, x, -13.0, "R0"))
            sch.add(term(name, "PLUS", net))
            sch.add(term(name, "MINUS", "gnd!"))
    timing = config["timing"]
    base.set_owned_params(
        client, target, "VCOMP", v1="0", v2="comp_clock_high",
        td=f"{float(timing['comparator_clock_start_s'])*1e9:g}n", tr="20p",
        tf="20p", pw=f"{float(timing['comparator_clock_high_s'])*1e9:g}n",
        per="100n")
    for name in ("COUTP", "COUTN"):
        base.set_owned_params(client, target, name,
                              c=f"{float(config['conditions']['output_load_f'])*1e15:g}f")
    with client.schematic.modify(library, target, timeout=120):
        pass
    data = client.schematic.read(library, target, include_positions=False,
                                 param_filters=None)
    named = {item["name"]: item for item in data["instances"]}
    if named["XBP"]["cell"] != config["cdac"] or named["XCMP"]["cell"] != config["comparator"]:
        raise RuntimeError("CDAC/comparator master mismatch")
    if len(named) != 25 or base.markers(client, target):
        raise RuntimeError("Unexpected instance count or schematic markers")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({"library": library, "cell": target,
                                  "technology": info.technology_library,
                                  "markers": 0,
                                  "instances": [compact_instance(item)
                                                for item in data["instances"]]},
                                 indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cellview": f"{library}/{target}/schematic",
                      "instances": len(named), "markers": 0,
                      "readback": str(OUTPUT)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
