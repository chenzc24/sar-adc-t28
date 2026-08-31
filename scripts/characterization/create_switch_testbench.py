#!/usr/bin/env python3
"""Create the transistor-level transmission-gate characterization fixture."""

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
CELL = "tb_tg_switch_char"


def _exists(client: VirtuosoClient) -> bool:
    result = client.execute_skill(f'ddGetObj("{LIBRARY}" "{CELL}")', timeout=10)
    return (result.output or "").strip() not in {"", "nil"}


def _compact_readback(client: VirtuosoClient) -> dict[str, object]:
    data = client.schematic.read(LIBRARY, CELL, include_positions=True, param_filters=None)
    keep = {"l", "Wfg", "w", "fingers", "nf", "simM", "model", "vdc"}
    return {
        "library": LIBRARY,
        "cell": CELL,
        "instances": [
            {
                "name": item.get("name"),
                "master": f"{item.get('lib')}/{item.get('cell')}",
                "position": item.get("position"),
                "params": {
                    key: value
                    for key, value in item.get("params", {}).items()
                    if key in keep
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
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/switch_characterization/schematic_readback.json"),
    )
    args = parser.parse_args()

    client = VirtuosoClient.from_env(profile=args.profile)
    if _exists(client):
        raise SystemExit(f"Refusing to overwrite existing {LIBRARY}/{CELL}")

    with client.schematic.create(LIBRARY, CELL) as sch:
        sch.add(inst("tsmcN28", "nch_mac", "symbol", "MN0", 0.0, 1.0, "R0"))
        sch.add(inst("tsmcN28", "pch_mac", "symbol", "MP0", 0.0, 3.0, "R0"))
        sch.add(inst("analogLib", "vdc", "symbol", "VDD", 4.0, 3.0, "R0"))
        sch.add(inst("analogLib", "vdc", "symbol", "VGN", -2.0, 0.0, "R0"))
        sch.add(inst("analogLib", "vdc", "symbol", "VGP", -2.0, 4.0, "R0"))
        sch.add(inst("analogLib", "vdc", "symbol", "VL", -4.0, 2.0, "R0"))
        sch.add(inst("analogLib", "vdc", "symbol", "VR", 4.0, 1.0, "R0"))
        sch.add(inst("analogLib", "gnd", "symbol", "G0", 2.0, -2.0, "R0"))

        for terminal, net in {"D": "LEFT", "G": "GN", "S": "RIGHT", "B": "gnd!"}.items():
            sch.add(label_term("MN0", terminal, net))
        for terminal, net in {"D": "LEFT", "G": "GP", "S": "RIGHT", "B": "VDD"}.items():
            sch.add(label_term("MP0", terminal, net))
        for source, plus, minus in (
            ("VDD", "VDD", "gnd!"),
            ("VGN", "GN", "gnd!"),
            ("VGP", "GP", "gnd!"),
            ("VL", "LEFT", "gnd!"),
            ("VR", "RIGHT", "gnd!"),
        ):
            sch.add(label_term(source, "PLUS", plus))
            sch.add(label_term(source, "MINUS", minus))

    client.open_window(LIBRARY, CELL, view="schematic")
    for device in ("MN0", "MP0"):
        set_instance_params(
            client,
            device,
            wf="250n",
            l="30n",
            nf="1",
            simM="1",
            param_filters=None,
            strict=True,
        )
    for source, value in (
        ("VDD", "900m"),
        ("VGN", "900m"),
        ("VGP", "0"),
        ("VL", "450.5m"),
        ("VR", "449.5m"),
    ):
        set_instance_params(client, source, vdc=value, param_filters=None, strict=True)

    with client.schematic.modify(LIBRARY, CELL, timeout=120):
        pass
    result = _compact_readback(client)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
