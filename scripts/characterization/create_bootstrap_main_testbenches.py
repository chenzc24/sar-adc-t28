#!/usr/bin/env python3
"""Create core, DNW, and 1.8-V bootstrap-main-switch OA fixtures."""

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
FIXTURES = {
    "tb_bootstrap_core_main_char": {
        "master": "nch_mac",
        "body_net": "gnd!",
        "finger_width": "250n",
        "length": "30n",
    },
    "tb_bootstrap_dnw_main_char": {
        "master": "nch_dnw_mac",
        "body_net": "RIGHT",
        "finger_width": "250n",
        "length": "30n",
    },
    "tb_bootstrap_18_main_char": {
        "master": "nch_18_mac",
        "body_net": "gnd!",
        "finger_width": "320n",
        "length": "150n",
    },
}


def _exists(client: VirtuosoClient, cell: str) -> bool:
    result = client.execute_skill(f'ddGetObj("{LIBRARY}" "{cell}")', timeout=10)
    return (result.output or "").strip() not in {"", "nil"}


def _readback(client: VirtuosoClient, cell: str) -> dict[str, object]:
    data = client.schematic.read(LIBRARY, cell, include_positions=False, param_filters=None)
    keep = {"model", "l", "Wfg", "w", "fingers", "nf", "simM", "vdc"}
    return {
        "library": LIBRARY,
        "cell": cell,
        "instances": [
            {
                "name": item.get("name"),
                "master": f"{item.get('lib')}/{item.get('cell')}",
                "params": {
                    key: value
                    for key, value in item.get("params", {}).items()
                    if key in keep
                },
            }
            for item in data.get("instances", [])
        ],
        "nets": data.get("nets", {}),
        "pins": data.get("pins", {}),
    }


def _create_fixture(client: VirtuosoClient, cell: str, spec: dict[str, str]) -> None:
    if _exists(client, cell):
        raise RuntimeError(f"Refusing to overwrite existing {LIBRARY}/{cell}")
    with client.schematic.create(LIBRARY, cell) as sch:
        sch.add(inst("tsmcN28", spec["master"], "symbol", "MN0", 0.0, 1.0, "R0"))
        sch.add(inst("analogLib", "vdc", "symbol", "VVG", -2.0, 3.0, "R0"))
        sch.add(inst("analogLib", "vdc", "symbol", "VL", -3.0, 1.0, "R0"))
        sch.add(inst("analogLib", "vdc", "symbol", "VR", 3.0, 1.0, "R0"))
        sch.add(inst("analogLib", "gnd", "symbol", "G0", 1.5, -1.5, "R0"))
        for terminal, net in {
            "D": "LEFT",
            "G": "GATE",
            "S": "RIGHT",
            "B": spec["body_net"],
        }.items():
            sch.add(label_term("MN0", terminal, net))
        for source, plus in (("VVG", "GATE"), ("VL", "LEFT"), ("VR", "RIGHT")):
            sch.add(label_term(source, "PLUS", plus))
            sch.add(label_term(source, "MINUS", "gnd!"))

    client.open_window(LIBRARY, cell, view="schematic")
    set_instance_params(
        client,
        "MN0",
        wf=spec["finger_width"],
        l=spec["length"],
        nf="1",
        simM="1",
        param_filters=None,
        strict=True,
    )
    for source, value in (("VVG", "1350m"), ("VL", "450.5m"), ("VR", "449.5m")):
        set_instance_params(client, source, vdc=value, param_filters=None, strict=True)
    with client.schematic.modify(LIBRARY, cell, timeout=120):
        pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/bootstrap_main_switch_screening/readback"),
    )
    args = parser.parse_args()

    client = VirtuosoClient.from_env(profile=args.profile)
    for cell in FIXTURES:
        if _exists(client, cell):
            raise SystemExit(f"Refusing target: existing {LIBRARY}/{cell}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result = {}
    for cell, spec in FIXTURES.items():
        _create_fixture(client, cell, spec)
        result[cell] = _readback(client, cell)
        (args.output_dir / f"{cell}.json").write_text(
            json.dumps(result[cell], indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
