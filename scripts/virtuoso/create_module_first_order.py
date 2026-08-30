#!/usr/bin/env python3
"""Create the owned sampling and comparator first-order schematics."""

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
CELLS = ("tb_sampling_acquisition", "tb_comparator_regeneration")


def _exists(client: VirtuosoClient, cell: str) -> bool:
    result = client.execute_skill(f'ddGetObj("{LIBRARY}" "{cell}")', timeout=10)
    return (result.output or "").strip() not in {"", "nil"}


def _ground(schematic, name: str, x: float, y: float) -> None:
    schematic.add(inst("analogLib", "gnd", "symbol", name, x, y, "R0"))


def _create_sampling(client: VirtuosoClient) -> None:
    cell = "tb_sampling_acquisition"
    with client.schematic.create(LIBRARY, cell) as sch:
        sch.add(inst("analogLib", "vpulse", "symbol", "VIN", -3.0, 1.0, "R0"))
        sch.add(inst("analogLib", "res", "symbol", "RSOURCE", -1.0, 1.0, "R0"))
        sch.add(inst("analogLib", "res", "symbol", "RSW", 1.0, 1.0, "R0"))
        sch.add(inst("analogLib", "cap", "symbol", "CSAMPLE", 3.0, 1.0, "R0"))
        _ground(sch, "G0", 0.0, -1.0)
        for name, terminal, net in (
            ("VIN", "PLUS", "VIN_SRC"),
            ("VIN", "MINUS", "gnd!"),
            ("RSOURCE", "PLUS", "VIN_SRC"),
            ("RSOURCE", "MINUS", "VIN_PAD"),
            ("RSW", "PLUS", "VIN_PAD"),
            ("RSW", "MINUS", "VSAMPLE"),
            ("CSAMPLE", "PLUS", "VSAMPLE"),
            ("CSAMPLE", "MINUS", "gnd!"),
        ):
            sch.add(label_term(name, terminal, net))

    client.open_window(LIBRARY, cell, view="schematic")
    set_instance_params(
        client,
        "VIN",
        v1="0",
        v2="900m",
        td="1n",
        tr="1p",
        tf="1p",
        pw="100n",
        per="200n",
        param_filters=None,
        strict=True,
    )
    set_instance_params(client, "RSOURCE", r="5k", param_filters=None, strict=True)
    set_instance_params(client, "RSW", r="1k", param_filters=None, strict=True)
    set_instance_params(client, "CSAMPLE", c="226.39551f", param_filters=None, strict=True)


def _create_comparator(client: VirtuosoClient) -> None:
    cell = "tb_comparator_regeneration"
    with client.schematic.create(LIBRARY, cell) as sch:
        sch.add(inst("analogLib", "vccs", "symbol", "GREG", 0.0, 1.0, "R0"))
        sch.add(inst("analogLib", "cap", "symbol", "CREG", 2.0, 1.0, "R0"))
        _ground(sch, "G0", 0.0, -1.0)
        for name, terminal, net in (
            ("GREG", "PLUS", "VDIFF"),
            ("GREG", "MINUS", "gnd!"),
            ("GREG", "NC+", "VDIFF"),
            ("GREG", "NC-", "gnd!"),
            ("CREG", "PLUS", "VDIFF"),
            ("CREG", "MINUS", "gnd!"),
        ):
            sch.add(label_term(name, terminal, net))

    client.open_window(LIBRARY, cell, view="schematic")
    # With analogLib's output terminal order (PLUS, MINUS), negative gm makes
    # the VDIFF-controlled source regenerative rather than dissipative.
    set_instance_params(client, "GREG", ggain="-100u", param_filters=None, strict=True)
    set_instance_params(
        client,
        "CREG",
        c="20f",
        ic="439.453125u",
        param_filters=None,
        strict=True,
    )


def _readback(client: VirtuosoClient, cell: str) -> dict:
    data = client.schematic.read(LIBRARY, cell, include_positions=True, param_filters=None)
    keep = {"r", "c", "ic", "ggain", "v1", "v2", "td", "tr", "tf", "pw", "per"}
    return {
        "library": LIBRARY,
        "cell": cell,
        "instances": [
            {
                "name": item.get("name"),
                "master": f'{item.get("lib")}/{item.get("cell")}',
                "params": {key: value for key, value in item.get("params", {}).items() if key in keep},
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
    existing = [cell for cell in CELLS if _exists(client, cell)]
    if existing:
        raise SystemExit(f"Refusing to overwrite existing cells: {', '.join(existing)}")
    _create_sampling(client)
    _create_comparator(client)
    result = {cell: _readback(client, cell) for cell in CELLS}
    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
