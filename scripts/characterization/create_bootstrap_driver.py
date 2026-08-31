#!/usr/bin/env python3
"""Create the first Abo-Gray-style transistor bootstrap OA prototype."""

from __future__ import annotations

import argparse
import json
import re
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


LIBRARY = "SAR_ADC_T28"
DUT = "sar_bootstrap"
TB = "tb_sar_bootstrap_transient"
PORTS = ("VDD", "VSS", "PHI", "PHIB", "VIN", "VOUT")


def _exists(client: VirtuosoClient, cell: str, view: str | None = None) -> bool:
    suffix = f' "{view}"' if view else ""
    result = client.execute_skill(f'ddGetObj("{LIBRARY}" "{cell}"{suffix})', timeout=10)
    return (result.output or "").strip() not in {"", "nil"}


def _close_owned_window(client: VirtuosoClient, cell: str, view: str) -> None:
    """Save and close only this target's exact editor window before rebuild."""
    skill = (
        "foreach(w hiGetWindowList() "
        "let((wcv) wcv = w~>cellView "
        f'when(wcv && wcv~>libName == "{LIBRARY}" '
        f'&& wcv~>cellName == "{cell}" && wcv~>viewName == "{view}" '
        "dbSave(wcv) hiCloseWindow(w))))"
    )
    result = client.execute_skill(skill, timeout=30)
    if result.errors:
        raise RuntimeError(f"failed to close owned window {LIBRARY}/{cell}/{view}: {result.errors}")


def _set_mos(
    client: VirtuosoClient,
    name: str,
    *,
    length: str,
    multiplier: int,
    finger_width: str = "250n",
) -> None:
    set_instance_params(
        client,
        name,
        wf=finger_width,
        l=length,
        nf="1",
        simM=str(multiplier),
        param_filters=None,
        strict=True,
    )


def _add_mos(
    sch: Any,
    name: str,
    master: str,
    x: float,
    y: float,
    nodes: dict[str, str],
    orient: str = "R0",
) -> None:
    sch.add(inst("tsmcN28", master, "symbol", name, x, y, orient))
    for terminal in ("B", "D", "G", "S"):
        sch.add(label_term(name, terminal, nodes[terminal]))


def _add_cap(sch: Any, name: str, x: float, y: float, plus: str, minus: str) -> None:
    sch.add(inst("analogLib", "cap", "symbol", name, x, y, "R0"))
    sch.add(label_term(name, "PLUS", plus))
    sch.add(label_term(name, "MINUS", minus))


def _create_dut(client: VirtuosoClient) -> None:
    _close_owned_window(client, DUT, "schematic")
    with client.schematic.create(LIBRARY, DUT) as sch:
        for name, x, y, orient, direction in (
            ("VDD", -10.0, 8.0, "R0", "input"),
            ("VSS", -10.0, -8.0, "R0", "input"),
            ("PHI", -10.0, 4.0, "R0", "input"),
            ("PHIB", -10.0, 2.0, "R0", "input"),
            ("VIN", -10.0, -3.0, "R0", "inputOutput"),
            ("VOUT", 12.0, -3.0, "R180", "inputOutput"),
        ):
            sch.add(pin(name, x, y, orient, direction=direction))

        # Abo figure-5.5 NMOS clock multiplier. During PHI=0/PHIB=1, P1 is
        # lifted toward 2*VDD and drives NM3 as a unidirectional CBOOT charger.
        _add_mos(sch, "MN1", "nch_mac", -6.0, 7.0,
                 {"B": "VSS", "D": "VDD", "G": "P2", "S": "P1"})
        _add_mos(sch, "MN2", "nch_mac", -2.0, 7.0,
                 {"B": "VSS", "D": "VDD", "G": "P1", "S": "P2"})
        _add_cap(sch, "CP1", -6.0, 4.5, "P1", "PHIB")
        _add_cap(sch, "CP2", -2.0, 4.5, "P2", "PHI")

        # Bootstrap-capacitor precharge and boosted-path isolation.
        _add_mos(sch, "MN3", "nch_mac", 2.0, 7.0,
                 {"B": "VSS", "D": "VDD", "G": "P1", "S": "BTOP"})
        _add_cap(sch, "CBOOT", 2.0, 3.5, "BTOP", "BBOT")
        _add_mos(sch, "MN12", "nch_mac", 2.0, -0.5,
                 {"B": "VSS", "D": "BBOT", "G": "PHIB", "S": "VSS"})

        # MP8 transfers the charged top plate to the main gate. Its well/body
        # follows its high-side source G, as required by the reference topology.
        _add_mos(sch, "MP8", "pch_mac", 6.0, 5.0,
                 {"B": "G", "D": "BTOP", "G": "CTRL", "S": "G"}, "R90")
        _add_mos(sch, "MP4", "pch_mac", 5.0, 7.0,
                 {"B": "VDD", "D": "CTRL", "G": "PHI", "S": "VDD"})
        _add_mos(sch, "MN5", "nch_mac", 5.0, 2.0,
                 {"B": "VSS", "D": "CTRL", "G": "PHI", "S": "BBOT"})
        _add_mos(sch, "MN13", "nch_mac", 7.0, 2.0,
                 {"B": "VSS", "D": "CTRL", "G": "G", "S": "BBOT"})

        # Protected gate discharge: MN7 shields MN10 while G is boosted.
        _add_mos(sch, "MN7", "nch_mac", 9.0, 5.0,
                 {"B": "VSS", "D": "G", "G": "VDD", "S": "GCLAMP"}, "R90")
        _add_mos(sch, "MN10", "nch_mac", 10.0, 2.0,
                 {"B": "VSS", "D": "GCLAMP", "G": "PHIB", "S": "VSS"})

        # DNW input follower and screened main sampling transistor.
        _add_mos(sch, "MN9", "nch_dnw_mac", 6.0, -1.0,
                 {"B": "VIN", "D": "BBOT", "G": "G", "S": "VIN"}, "R90")
        _add_mos(sch, "MN11", "nch_dnw_mac", 9.0, -3.0,
                 {"B": "VIN", "D": "VOUT", "G": "G", "S": "VIN"}, "R90")

    client.open_window(LIBRARY, DUT, view="schematic")
    sizes = {
        "MN1": ("30n", 2), "MN2": ("30n", 2), "MN3": ("30n", 2),
        "MP4": ("30n", 2), "MN5": ("30n", 2), "MP8": ("30n", 4),
        "MN7": ("60n", 2), "MN10": ("30n", 4), "MN13": ("30n", 2),
        "MN9": ("60n", 4), "MN12": ("30n", 4), "MN11": ("60n", 8),
    }
    for name, (length, multiplier) in sizes.items():
        _set_mos(client, name, length=length, multiplier=multiplier)
    for name, value in (("CP1", "50f"), ("CP2", "50f"), ("CBOOT", "200f")):
        set_instance_params(client, name, c=value, param_filters=None, strict=True)
    with client.schematic.modify(LIBRARY, DUT, timeout=120):
        pass


def _create_symbol(client: VirtuosoClient) -> None:
    _close_owned_window(client, DUT, "symbol")
    with client.symbol.create(LIBRARY, DUT, timeout=120) as sym:
        sym.add(symbol_create_rect("device", "drawing", 0.75, -2.25, 5.25, 2.25))
        sym.add(symbol_create_selection_box(0.0, -2.5, 6.0, 2.5))
        for name, y in (("VDD", 1.75), ("PHI", 0.75), ("PHIB", -0.25), ("VSS", -1.75)):
            sym.add(symbol_create_pin(name, 0.0, y, direction="input", half_size=0.025,
                                      label_x=0.9, label_y=y))
        for name, y in (("VIN", 1.0), ("VOUT", -1.0)):
            sym.add(symbol_create_pin(name, 6.0, y, direction="inputOutput", half_size=0.025,
                                      label_x=5.1, label_y=y,
                                      label_justification="centerRight"))
        sym.add(symbol_create_instance_label(2.0, 2.7))
        sym.add(symbol_create_logical_label(3.0, 0.0))
        sym.add(symbol_set_term_order(list(PORTS)))


def _create_testbench(client: VirtuosoClient) -> None:
    _close_owned_window(client, TB, "schematic")
    with client.schematic.create(LIBRARY, TB) as sch:
        sch.add(inst(LIBRARY, DUT, "symbol", "XBOOT", 0.0, 2.0, "R0"))
        sch.add(inst("analogLib", "vdc", "symbol", "VVDD", -8.0, 5.0, "R0"))
        sch.add(inst("analogLib", "vpulse", "symbol", "VVIN", -8.0, 0.0, "R0"))
        sch.add(inst("analogLib", "res", "symbol", "RIN", -5.0, 0.0, "R90"))
        sch.add(inst("analogLib", "vpulse", "symbol", "VPHI", -8.0, -3.0, "R0"))
        sch.add(inst("analogLib", "vpulse", "symbol", "VPHIB", -5.0, -3.0, "R0"))
        sch.add(inst("analogLib", "cap", "symbol", "CLOAD", 7.0, 0.0, "R0"))
        sch.add(inst("analogLib", "gnd", "symbol", "G0", 3.0, -4.0, "R0"))
        for terminal in PORTS:
            sch.add(label_term("XBOOT", terminal, "gnd!" if terminal == "VSS" else terminal))
        for name, terminal, net in (
            ("VVDD", "PLUS", "VDD"), ("VVDD", "MINUS", "gnd!"),
            ("VVIN", "PLUS", "VIN_SRC"), ("VVIN", "MINUS", "gnd!"),
            ("RIN", "PLUS", "VIN_SRC"), ("RIN", "MINUS", "VIN"),
            ("VPHI", "PLUS", "PHI"), ("VPHI", "MINUS", "gnd!"),
            ("VPHIB", "PLUS", "PHIB"), ("VPHIB", "MINUS", "gnd!"),
            ("CLOAD", "PLUS", "VOUT"), ("CLOAD", "MINUS", "gnd!"),
        ):
            sch.add(label_term(name, terminal, net))

    client.open_window(LIBRARY, TB, view="schematic")
    set_instance_params(client, "VVDD", vdc="900m", param_filters=None, strict=True)
    # The input changes while the switch is off. VOUT therefore starts near
    # 50 mV and must acquire the 450-mV target during the 211-250 ns aperture.
    set_instance_params(
        client, "VVIN", v1="50m", v2="450m", td="205n", tr="100p", tf="100p",
        pw="80n", per="400n", param_filters=None, strict=True,
    )
    set_instance_params(client, "RIN", r="50", param_filters=None, strict=True)
    set_instance_params(client, "CLOAD", c="219.5f", param_filters=None, strict=True)
    set_instance_params(
        client, "VPHI", v1="0", v2="900m", td="11n", tr="100p", tf="100p",
        pw="39n", per="100n", param_filters=None, strict=True,
    )
    set_instance_params(
        client, "VPHIB", v1="900m", v2="0", td="10n", tr="100p", tf="100p",
        pw="41n", per="100n", param_filters=None, strict=True,
    )
    with client.schematic.modify(LIBRARY, TB, timeout=120):
        pass


def _readback(client: VirtuosoClient, cell: str) -> dict[str, Any]:
    data = client.schematic.read(LIBRARY, cell, include_positions=True, param_filters=None)
    keep = {"model", "l", "Wfg", "w", "fingers", "nf", "simM", "c", "r",
            "vdc", "v1", "v2", "td", "tr", "tf", "pw", "per"}
    return {
        "library": LIBRARY,
        "cell": cell,
        "check_marker_count": _marker_count(client, cell),
        "instances": [
            {
                "name": item.get("name"),
                "master": f"{item.get('lib')}/{item.get('cell')}",
                "position": item.get("position"),
                "params": {key: value for key, value in item.get("params", {}).items() if key in keep},
            }
            for item in data.get("instances", [])
        ],
        "nets": data.get("nets", {}),
        "pins": data.get("pins", {}),
    }


def _marker_count(client: VirtuosoClient, cell: str) -> int:
    skill = (
        "let((cv n) "
        f'cv=dbOpenCellViewByType("{LIBRARY}" "{cell}" "schematic" "" "r") '
        "n=length(cv~>markers) dbClose(cv) n)"
    )
    result = client.execute_skill(skill, timeout=30)
    if result.errors:
        raise RuntimeError(f"failed to read check markers for {LIBRARY}/{cell}: {result.errors}")
    numbers = re.findall(r"\b\d+\b", result.output or "")
    if not numbers:
        raise RuntimeError(
            f"marker-count query returned no integer for {LIBRARY}/{cell}: {result.output!r}"
        )
    return int(numbers[-1])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument("--output-dir", type=Path,
                        default=Path("output/bootstrap_driver_design/readback"))
    parser.add_argument(
        "--rebuild-testbench",
        action="store_true",
        help="Replace only the exact owned transient testbench after readback repair",
    )
    parser.add_argument(
        "--rebuild-owned",
        action="store_true",
        help="Replace only this plan's exact DUT, symbol, and testbench after waveform review",
    )
    parser.add_argument(
        "--readback-only",
        action="store_true",
        help="Read the exact owned cells without modifying or rebuilding them",
    )
    args = parser.parse_args()
    client = VirtuosoClient.from_env(profile=args.profile)
    if args.readback_only:
        for cell in (DUT, TB):
            if not _exists(client, cell):
                raise SystemExit(f"Required owned cell is missing: {LIBRARY}/{cell}")
    elif args.rebuild_owned:
        _create_dut(client)
        _create_symbol(client)
        _create_testbench(client)
    elif args.rebuild_testbench:
        if not _exists(client, DUT):
            raise SystemExit(f"Required owned DUT is missing: {LIBRARY}/{DUT}")
        _create_testbench(client)
    else:
        for cell in (DUT, TB):
            if _exists(client, cell):
                raise SystemExit(f"Refusing to overwrite existing {LIBRARY}/{cell}")
        _create_dut(client)
        _create_symbol(client)
        _create_testbench(client)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result = {cell: _readback(client, cell) for cell in (DUT, TB)}
    result["symbol_ports"] = client.symbol.read_ports(LIBRARY, DUT)
    for cell in (DUT, TB):
        (args.output_dir / f"{cell}.json").write_text(
            json.dumps(result[cell], indent=2) + "\n", encoding="utf-8"
        )
    (args.output_dir / "symbol_ports.json").write_text(
        json.dumps(result["symbol_ports"], indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
