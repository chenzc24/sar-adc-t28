#!/usr/bin/env python3
"""Create the first PDK characterization schematics in SAR_ADC_T28.

The script owns only the three ``tb_*_char/schematic`` cellviews named below.
It refuses to overwrite an existing cell so that reruns cannot silently erase
manual work.
"""

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
CELLS = ("tb_nmos_char", "tb_pmos_char", "tb_cap_char")


def _cell_exists(client: VirtuosoClient, cell: str) -> bool:
    result = client.execute_skill(f'ddGetObj("{LIBRARY}" "{cell}")', timeout=10)
    return (result.output or "").strip() not in {"", "nil"}


def _add_ground(schematic, x: float, y: float) -> None:
    schematic.add(inst("analogLib", "gnd", "symbol", "G0", x, y, "R0"))


def _create_nmos(client: VirtuosoClient) -> None:
    with client.schematic.create(LIBRARY, "tb_nmos_char") as sch:
        sch.add(inst("tsmcN28", "nch_mac", "symbol", "MN0", 0.0, 1.0, "R0"))
        sch.add(inst("analogLib", "vdc", "symbol", "VGS", -2.0, 1.0, "R0"))
        sch.add(inst("analogLib", "vdc", "symbol", "VDS", 2.0, 1.0, "R0"))
        _add_ground(sch, 0.0, -1.0)

        for terminal, net in {"D": "VD", "G": "VG", "S": "gnd!", "B": "gnd!"}.items():
            sch.add(label_term("MN0", terminal, net))
        for source, plus in (("VGS", "VG"), ("VDS", "VD")):
            sch.add(label_term(source, "PLUS", plus))
            sch.add(label_term(source, "MINUS", "gnd!"))

    client.open_window(LIBRARY, "tb_nmos_char", view="schematic")
    set_instance_params(
        client, "MN0", wf="1u", l="30n", nf="1", simM="1",
        param_filters=None, strict=True,
    )
    set_instance_params(client, "VGS", vdc="0", param_filters=None, strict=True)
    set_instance_params(client, "VDS", vdc="0", param_filters=None, strict=True)


def _create_pmos(client: VirtuosoClient) -> None:
    with client.schematic.create(LIBRARY, "tb_pmos_char") as sch:
        sch.add(inst("tsmcN28", "pch_mac", "symbol", "MP0", 0.0, 1.0, "R0"))
        sch.add(inst("analogLib", "vdc", "symbol", "VDD", 3.0, 2.0, "R0"))
        sch.add(inst("analogLib", "vdc", "symbol", "VG", -2.0, 1.0, "R0"))
        sch.add(inst("analogLib", "vdc", "symbol", "VD", 2.0, 0.0, "R0"))
        _add_ground(sch, 0.0, -1.0)

        for terminal, net in {"D": "VD", "G": "VG", "S": "VDD", "B": "VDD"}.items():
            sch.add(label_term("MP0", terminal, net))
        for source, plus in (("VDD", "VDD"), ("VG", "VG"), ("VD", "VD")):
            sch.add(label_term(source, "PLUS", plus))
            sch.add(label_term(source, "MINUS", "gnd!"))

    client.open_window(LIBRARY, "tb_pmos_char", view="schematic")
    set_instance_params(
        client, "MP0", wf="1u", l="30n", nf="1", simM="1",
        param_filters=None, strict=True,
    )
    set_instance_params(client, "VDD", vdc="900m", param_filters=None, strict=True)
    set_instance_params(client, "VG", vdc="900m", param_filters=None, strict=True)
    set_instance_params(client, "VD", vdc="900m", param_filters=None, strict=True)


def _create_cap(client: VirtuosoClient) -> None:
    with client.schematic.create(LIBRARY, "tb_cap_char") as sch:
        sch.add(inst("tsmcN28", "cfmom_2t", "symbol", "C0", 0.0, 1.0, "R0"))
        sch.add(inst("analogLib", "vdc", "symbol", "VBIAS", 2.0, 1.0, "R0"))
        _add_ground(sch, 0.0, -1.0)

        sch.add(label_term("C0", "PLUS", "VCAP"))
        sch.add(label_term("C0", "MINUS", "gnd!"))
        sch.add(label_term("VBIAS", "PLUS", "VCAP"))
        sch.add(label_term("VBIAS", "MINUS", "gnd!"))

    client.open_window(LIBRARY, "tb_cap_char", view="schematic")
    set_instance_params(
        client,
        "C0",
        Wfinger="50n",
        Sfinger="50n",
        Lfinger="4u",
        Nfinger="32",
        StartMn="1",
        StopMn="3",
        mismatch="Model",
        param_filters=None,
        strict=True,
    )
    set_instance_params(client, "VBIAS", vdc="0", param_filters=None, strict=True)


def _compact_readback(client: VirtuosoClient, cell: str) -> dict[str, object]:
    data = client.schematic.read(LIBRARY, cell, include_positions=True, param_filters=None)
    keep = {
        "l", "Wfg", "w", "fingers", "nf", "simM", "model",
        "Wfinger", "Sfinger", "Lfinger", "Nfinger", "StartMn", "StopMn",
        "mismatch", "c", "vdc",
    }
    instances = []
    for item in data.get("instances", []):
        params = item.get("params", {})
        instances.append(
            {
                "name": item.get("name"),
                "master": f"{item.get('lib')}/{item.get('cell')}",
                "position": item.get("position"),
                "params": {key: value for key, value in params.items() if key in keep},
            }
        )
    return {
        "library": LIBRARY,
        "cell": cell,
        "instances": instances,
        "nets": data.get("nets", []),
        "pins": data.get("pins", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    client = VirtuosoClient.from_env(profile=args.profile)
    existing = [cell for cell in CELLS if _cell_exists(client, cell)]
    if existing:
        raise SystemExit(f"Refusing to overwrite existing cells: {', '.join(existing)}")

    _create_nmos(client)
    _create_pmos(client)
    _create_cap(client)

    result = {cell: _compact_readback(client, cell) for cell in CELLS}
    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
