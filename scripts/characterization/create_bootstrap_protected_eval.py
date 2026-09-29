#!/usr/bin/env python3
"""Create a separate mixed-voltage bootstrap OA screening fixture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.schematic.ops import (
    schematic_create_inst_by_master_name as inst,
    schematic_create_pin as pin,
    schematic_label_instance_term as label_term,
)
from virtuoso_bridge.virtuoso.schematic.params import set_instance_params
from virtuoso_bridge.virtuoso.symbol.ops import (
    symbol_create_instance_label,
    symbol_create_logical_label,
    symbol_create_pin,
    symbol_create_rect,
    symbol_create_selection_box,
    symbol_set_term_order,
)

from create_bootstrap_driver import _add_cap, _add_mos, _marker_count, _set_mos


LIB = "SAR_ADC_T28"
DUT = "sar_bootstrap_protected_eval"
TB = "tb_sar_bootstrap_protected_eval"
PORTS = ("VDD", "VSS", "PHI", "PHIB", "VIN", "VOUT")
OUT = Path("output/bootstrap_protected_eval/readback")


def exists(client: VirtuosoClient, cell: str, view: str | None = None) -> bool:
    suffix = f' "{view}"' if view else ""
    result = client.execute_skill(f'ddGetObj("{LIB}" "{cell}"{suffix})', timeout=10)
    return (result.output or "").strip() not in {"", "nil"}


def create_dut(client: VirtuosoClient, *, full18: bool) -> None:
    with client.schematic.create(LIB, DUT) as sch:
        for name, x, y, orient, direction in (
            ("VDD", -10.0, 8.0, "R0", "input"),
            ("VSS", -10.0, -8.0, "R0", "input"),
            ("PHI", -10.0, 4.0, "R0", "input"),
            ("PHIB", -10.0, 2.0, "R0", "input"),
            ("VIN", -10.0, -3.0, "R0", "inputOutput"),
            ("VOUT", 12.0, -3.0, "R180", "inputOutput"),
        ):
            sch.add(pin(name, x, y, orient, direction=direction))

        # Preserve the baseline electrical topology. This first bounded
        # candidate changes only classes/geometries of stressed devices.
        _add_mos(sch, "MN1", "nch_18_mac", -6.0, 7.0,
                 {"B": "VSS", "D": "VDD", "G": "P2", "S": "P1"})
        _add_mos(sch, "MN2", "nch_18_mac", -2.0, 7.0,
                 {"B": "VSS", "D": "VDD", "G": "P1", "S": "P2"})
        _add_cap(sch, "CP1", -6.0, 4.5, "P1", "PHIB")
        _add_cap(sch, "CP2", -2.0, 4.5, "P2", "PHI")
        _add_mos(sch, "MN3", "nch_18_mac", 2.0, 7.0,
                 {"B": "VSS", "D": "VDD", "G": "P1", "S": "BTOP"})
        _add_cap(sch, "CBOOT", 2.0, 3.5, "BTOP", "BBOT")
        _add_mos(sch, "MN12", "nch_mac", 2.0, -0.5,
                 {"B": "VSS", "D": "BBOT", "G": "PHIB", "S": "VSS"})
        _add_mos(sch, "MP8", "pch_mac", 6.0, 5.0,
                 {"B": "G", "D": "BTOP", "G": "CTRL", "S": "G"}, "R90")
        _add_mos(sch, "MP4", "pch_18_mac" if full18 else "pch_mac", 5.0, 7.0,
                 {"B": "VDD", "D": "CTRL", "G": "PHI", "S": "VDD"})
        _add_mos(sch, "MN5", "nch_18_mac" if full18 else "nch_mac", 5.0, 2.0,
                 {"B": "VSS", "D": "CTRL", "G": "PHI", "S": "BBOT"})
        _add_mos(sch, "MN13", "nch_18_mac", 7.0, 2.0,
                 {"B": "VSS", "D": "CTRL", "G": "G", "S": "BBOT"})
        _add_mos(sch, "MN7", "nch_18_mac", 9.0, 5.0,
                 {"B": "VSS", "D": "G", "G": "VDD", "S": "GCLAMP"}, "R90")
        _add_mos(sch, "MN10", "nch_mac", 10.0, 2.0,
                 {"B": "VSS", "D": "GCLAMP", "G": "PHIB", "S": "VSS"})
        _add_mos(sch, "MN9", "nch_dnw_mac", 6.0, -1.0,
                 {"B": "VIN", "D": "BBOT", "G": "G", "S": "VIN"}, "R90")
        _add_mos(sch, "MN11", "nch_18_dnw_mac", 9.0, -3.0,
                 {"B": "VIN", "D": "VOUT", "G": "G", "S": "VIN"}, "R90")

    client.open_window(LIB, DUT, view="schematic")
    core_sizes = {
        "MP8": ("30n", 4), "MN10": ("30n", 4),
        "MN9": ("60n", 4), "MN12": ("30n", 4),
    }
    if not full18:
        core_sizes.update({"MP4": ("30n", 2), "MN5": ("30n", 2)})
    for name, (length, multiplier) in core_sizes.items():
        _set_mos(client, name, length=length, multiplier=multiplier)
    wide_sizes = [("MN1", 4), ("MN2", 4), ("MN3", 4),
                  ("MN7", 4), ("MN13", 4), ("MN11", 28)]
    if full18:
        wide_sizes.extend((("MP4", 4), ("MN5", 4)))
    for name, multiplier in wide_sizes:
        _set_mos(client, name, length="150n", multiplier=multiplier,
                 finger_width="320n")
    for name, value in (("CP1", "50f"), ("CP2", "50f"), ("CBOOT", "200f")):
        set_instance_params(client, name, c=value, param_filters=None, strict=True)
    with client.schematic.modify(LIB, DUT, timeout=120):
        pass


def create_symbol(client: VirtuosoClient) -> None:
    with client.symbol.create(LIB, DUT, timeout=120) as sym:
        sym.add(symbol_create_rect("device", "drawing", 0.75, -2.25, 5.25, 2.25))
        sym.add(symbol_create_selection_box(0.0, -2.5, 6.0, 2.5))
        for name, y in (("VDD", 1.75), ("PHI", 0.75), ("PHIB", -0.25),
                        ("VSS", -1.75)):
            sym.add(symbol_create_pin(name, 0.0, y, direction="input",
                                      half_size=0.025, label_x=0.9, label_y=y))
        for name, y in (("VIN", 1.0), ("VOUT", -1.0)):
            sym.add(symbol_create_pin(name, 6.0, y, direction="inputOutput",
                                      half_size=0.025, label_x=5.1, label_y=y,
                                      label_justification="centerRight"))
        sym.add(symbol_create_instance_label(2.0, 2.7))
        sym.add(symbol_create_logical_label(3.0, 0.0))
        sym.add(symbol_set_term_order(list(PORTS)))


def create_tb(client: VirtuosoClient) -> None:
    with client.schematic.create(LIB, TB) as sch:
        for name, x in (("XP", 0.0), ("XN", 8.0)):
            sch.add(inst(LIB, DUT, "symbol", name, x, 2.0, "R0"))
            side = name[-1]
            for terminal in PORTS:
                net = "gnd!" if terminal == "VSS" else (
                    f"{terminal}{side}" if terminal in {"VIN", "VOUT"} else terminal
                )
                sch.add(label_term(name, terminal, net))
        for name, cell, x, y in (
            ("VVDD", "vdc", -8.0, 6.0),
            ("VPHI", "vpulse", -8.0, -4.0),
            ("VPHIB", "vpulse", -5.0, -4.0),
            ("VSP", "vpulse", -8.0, 2.0),
            ("VSN", "vpulse", -8.0, 0.0),
            ("RINP", "res", -4.0, 2.0),
            ("RINN", "res", -4.0, 0.0),
            ("CLOADP", "cap", 15.0, 2.0),
            ("CLOADN", "cap", 15.0, 0.0),
        ):
            sch.add(inst("analogLib", cell, "symbol", name, x, y, "R0"))
        sch.add(inst("analogLib", "gnd", "symbol", "G0", 4.0, -5.0, "R0"))
        for name, plus, minus in (
            ("VVDD", "VDD", "gnd!"), ("VPHI", "PHI", "gnd!"),
            ("VPHIB", "PHIB", "gnd!"),
            ("VSP", "VINP_SRC", "gnd!"), ("VSN", "VINN_SRC", "gnd!"),
            ("RINP", "VINP_SRC", "VINP"), ("RINN", "VINN_SRC", "VINN"),
            ("CLOADP", "VOUTP", "gnd!"), ("CLOADN", "VOUTN", "gnd!"),
        ):
            sch.add(label_term(name, "PLUS", plus))
            sch.add(label_term(name, "MINUS", minus))

    client.open_window(LIB, TB, view="schematic")
    set_instance_params(client, "VVDD", vdc="900m", param_filters=None, strict=True)
    for name, low, high in (("VSP", "50m", "850m"), ("VSN", "850m", "50m")):
        set_instance_params(client, name, v1=low, v2=high, td="205n",
                            tr="100p", tf="100p", pw="80n", per="400n",
                            param_filters=None, strict=True)
    for name in ("RINP", "RINN"):
        set_instance_params(client, name, r="50", param_filters=None, strict=True)
    for name in ("CLOADP", "CLOADN"):
        set_instance_params(client, name, c="219.5f", param_filters=None,
                            strict=True)
    set_instance_params(client, "VPHI", v1="0", v2="900m", td="11n",
                        tr="100p", tf="100p", pw="39n", per="100n",
                        param_filters=None, strict=True)
    set_instance_params(client, "VPHIB", v1="900m", v2="0", td="10n",
                        tr="100p", tf="100p", pw="41n", per="100n",
                        param_filters=None, strict=True)
    with client.schematic.modify(LIB, TB, timeout=120):
        pass


def readback(client: VirtuosoClient, cell: str) -> dict[str, Any]:
    data = client.schematic.read(LIB, cell, include_positions=False,
                                 param_filters=None)
    return {"cell": cell, "check_marker_count": _marker_count(client, cell),
            "instances": data.get("instances", []), "nets": data.get("nets", {}),
            "pins": data.get("pins", {})}


def main() -> int:
    global DUT, TB, OUT
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument("--create", action="store_true")
    parser.add_argument("--variant", choices=("initial", "full18"), default="initial")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.variant == "full18":
        DUT = "sar_bootstrap_protected_full18_eval"
        TB = "tb_sar_bootstrap_protected_full18_eval"
    output_dir = args.output_dir or OUT.parent / f"readback_{args.variant}"
    client = VirtuosoClient.from_env(profile=args.profile)
    if args.create:
        for cell in (DUT, TB):
            if exists(client, cell):
                raise SystemExit(f"Refusing to replace existing {LIB}/{cell}")
        create_dut(client, full18=args.variant == "full18")
        create_symbol(client)
        create_tb(client)
    elif not all(exists(client, cell) for cell in (DUT, TB)):
        raise SystemExit("Experimental OA cells are not yet complete")
    result = {cell: readback(client, cell) for cell in (DUT, TB)}
    result["symbol_ports"] = client.symbol.read_ports(LIB, DUT)
    output_dir.mkdir(parents=True, exist_ok=True)
    for key, value in result.items():
        (output_dir / f"{key}.json").write_text(
            json.dumps(value, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"markers": {cell: result[cell]["check_marker_count"]
                                   for cell in (DUT, TB)},
                      "cells": [DUT, TB]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
