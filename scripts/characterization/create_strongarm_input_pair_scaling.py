#!/usr/bin/env python3
"""Create independent T28 StrongARM input-pair finger-count candidates."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from virtuoso_bridge import VirtuosoClient

import create_strongarm_t28 as base


PROJECT = Path(__file__).resolve().parents[2]
CONFIG = PROJECT / "config" / "strongarm_input_pair_scaling.yaml"
ROOT = PROJECT / "output" / "strongarm_input_pair_scaling"


def compact(data: dict) -> dict:
    return {"pins": data.get("pins"),
            "instances": [{"name": item["name"], "lib": item["lib"],
                           "cell": item["cell"], "terms": item["terms"],
                           "params": {key: item.get("params", {}).get(key)
                                      for key in ("Wfg", "l", "fingers", "simM")}}
                          for item in data["instances"]]}


def main() -> int:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    if (config["library"] != base.LIB or config["baseline_dut"] != base.DUT
            or config["baseline_testbench"] != base.TB):
        raise RuntimeError("Unexpected library or baseline")
    client = VirtuosoClient.from_env(profile=config["profile"])
    info = client.library.get(base.LIB)
    if (info.path != "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28"
            or info.technology_library != "tsmcN28"):
        raise RuntimeError(f"Unexpected OA library mapping: {info}")
    for name in (config["baseline_dut"], config["baseline_testbench"]):
        if not base.exists(client, name, "schematic") or base.marker_count(client, name):
            raise RuntimeError(f"Missing or marked baseline: {name}")
    baseline = client.schematic.read(base.LIB, config["baseline_dut"],
                                     include_positions=False, param_filters=None)
    old = {item["name"]: item for item in baseline["instances"]}
    if set(old) != set(base.MOS):
        raise RuntimeError("Baseline instance set changed")
    for candidate in config["candidates"]:
        for cell in (candidate["dut"], candidate["testbench"]):
            if base.exists(client, cell):
                raise RuntimeError(f"Refusing to overwrite existing OA cell {cell}")
    output = []
    for candidate in config["candidates"]:
        fingers = int(candidate["input_pair_fingers"])
        if fingers not in (2, 4):
            raise RuntimeError(f"Unexpected input-pair fingers: {fingers}")
        base.DUT = candidate["dut"]
        base.TB = candidate["testbench"]
        base.create_dut(client)
        for name in ("MNINP", "MNINN"):
            base.set_params(client, base.DUT, name, fingers=str(fingers))
        with client.schematic.modify(base.LIB, base.DUT, timeout=120):
            pass
        base.create_symbol(client)
        base.create_tb(client)
        dut = client.schematic.read(base.LIB, base.DUT, include_positions=False,
                                    param_filters=None)
        tb = client.schematic.read(base.LIB, base.TB, include_positions=False,
                                   param_filters=None)
        named = {item["name"]: item for item in dut["instances"]}
        if set(named) != set(old) or len(tb["instances"]) != 8:
            raise RuntimeError("Candidate instance count changed")
        for name, prior in old.items():
            now = named[name]
            if (now["lib"], now["cell"], now["terms"]) != (
                    prior["lib"], prior["cell"], prior["terms"]):
                raise RuntimeError(f"Candidate topology changed at {name}")
            for parameter in ("Wfg", "l", "simM"):
                if now["params"].get(parameter) != prior["params"].get(parameter):
                    raise RuntimeError(f"Unexpected {name}.{parameter} change")
            expected = str(fingers) if name in ("MNINP", "MNINN") else "1"
            if now["params"].get("fingers") != expected:
                raise RuntimeError(f"Incorrect {name} fingers")
        if set(dut["pins"]) != set(base.PORTS):
            raise RuntimeError("Candidate port set changed")
        if base.marker_count(client, base.DUT) or base.marker_count(client, base.TB):
            raise RuntimeError("Candidate schematic check markers")
        output.append({"candidate": candidate, "dut": compact(dut),
                       "testbench": compact(tb), "markers": 0})
        print(json.dumps({"candidate": candidate["tag"], "dut": base.DUT,
                          "testbench": base.TB, "dut_instances": len(named),
                          "tb_instances": len(tb["instances"]), "markers": 0}))
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "readback.json").write_text(json.dumps(output, indent=2) + "\n",
                                        encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
