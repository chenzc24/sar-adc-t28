#!/usr/bin/env python3
"""Create the owned analogLib CDAC/reference first-order half-circuit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.schematic.ops import (
    schematic_create_inst_by_master_name as inst,
    schematic_label_instance_term as label_term,
)
from virtuoso_bridge.virtuoso.schematic.params import set_instance_params


LIBRARY = "SAR_ADC_T28"
CELL = "tb_cdac_ref_settling"


def _exists(client: VirtuosoClient) -> bool:
    result = client.execute_skill(f'ddGetObj("{LIBRARY}" "{CELL}")', timeout=10)
    return (result.output or "").strip() not in {"", "nil"}


def _compact_readback(client: VirtuosoClient) -> dict:
    data = client.schematic.read(LIBRARY, CELL, include_positions=True, param_filters=None)
    keep = {"r", "c", "v1", "v2", "td", "tr", "tf", "pw", "per"}
    return {
        "library": LIBRARY,
        "cell": CELL,
        "instances": [
            {
                "name": item.get("name"),
                "master": f'{item.get("lib")}/{item.get("cell")}',
                "position": item.get("position"),
                "params": {
                    key: value for key, value in item.get("params", {}).items() if key in keep
                },
            }
            for item in data.get("instances", [])
        ],
        "nets": data.get("nets", []),
        "pins": data.get("pins", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    client = VirtuosoClient.from_env(profile=args.profile)
    if _exists(client):
        raise SystemExit(f"Refusing to overwrite existing {LIBRARY}/{CELL}/schematic")

    with client.schematic.create(LIBRARY, CELL) as sch:
        sch.add(inst("analogLib", "vpulse", "symbol", "VSTEP", -3.0, 1.0, "R0"))
        sch.add(inst("analogLib", "res", "symbol", "RREF", -1.0, 1.0, "R0"))
        sch.add(inst("analogLib", "res", "symbol", "RSW", 1.0, 1.0, "R0"))
        sch.add(inst("analogLib", "cap", "symbol", "CDAC", 3.0, 1.0, "R0"))
        sch.add(inst("analogLib", "gnd", "symbol", "G0", 0.0, -1.0, "R0"))

        for name, terminal, net in (
            ("VSTEP", "PLUS", "VREF_SRC"),
            ("VSTEP", "MINUS", "gnd!"),
            ("RREF", "PLUS", "VREF_SRC"),
            ("RREF", "MINUS", "VREF_INT"),
            ("RSW", "PLUS", "VREF_INT"),
            ("RSW", "MINUS", "VDAC"),
            ("CDAC", "PLUS", "VDAC"),
            ("CDAC", "MINUS", "gnd!"),
        ):
            sch.add(label_term(name, terminal, net))

    client.open_window(LIBRARY, CELL, view="schematic")
    set_instance_params(
        client,
        "VSTEP",
        v1="0",
        v2="900m",
        td="1n",
        tr="1p",
        tf="1p",
        pw="20n",
        per="40n",
        param_filters=None,
        strict=True,
    )
    set_instance_params(client, "RREF", r="500", param_filters=None, strict=True)
    set_instance_params(client, "RSW", r="1k", param_filters=None, strict=True)
    set_instance_params(client, "CDAC", c="226.39551f", param_filters=None, strict=True)

    result = _compact_readback(client)
    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
