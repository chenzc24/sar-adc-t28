#!/usr/bin/env python3
"""Create separate OA bottom-plate CDAC and same-stimulus comparison fixture."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.schematic.ops import (
    schematic_create_inst_by_master_name as inst,
    schematic_create_pin as pin,
    schematic_label_instance_term as term,
)
from virtuoso_bridge.virtuoso.schematic.params import _run_batched_param_update
from virtuoso_bridge.virtuoso.symbol.ops import (
    symbol_create_instance_label,
    symbol_create_pin,
    symbol_create_rect,
    symbol_create_selection_box,
    symbol_set_term_order,
)


LIB = "SAR_ADC_T28"
CDAC = "sar_cdac_bottom_plate_eval_10b"
TB = "tb_sar_bottom_plate_eval"
T28_CLAMP = False
CU = 6.86047
WEIGHT = {9: 16, 8: 8, 7: 4, 6: 2, 5: 1, 4: 16, 3: 8, 2: 4, 1: 2, 0: 1}
PORTS = (
    "VINP", "VINN", "VDD", "VSS", "VREFP", "VREFN", "VCM",
    "PHI", "PHIB", "CLAMP", "BASE", "TOPP", "TOPN",
    *(f"SEL0<{bit}>" for bit in range(10)),
    *(f"SEL1<{bit}>" for bit in range(10)),
)


def exists(client: VirtuosoClient, cell: str, view: str | None = None) -> bool:
    suffix = f' "{view}"' if view else ""
    result = client.execute_skill(f'ddGetObj("{LIB}" "{cell}"{suffix})', timeout=10)
    if result.errors:
        raise RuntimeError(result.errors)
    return (result.output or "").strip() not in {"", "nil"}


def add_switch(sch, name: str, x: float, y: float, a: str, b: str, control: str) -> None:
    sch.add(inst("analogLib", "switch", "symbol", name, x, y, "R0"))
    for pin_name, net in (("N+", a), ("N-", b), ("NC+", control), ("NC-", "VSS")):
        sch.add(term(name, pin_name, net))


def set_owned_params(client: VirtuosoClient, cell: str, name: str, **params: str) -> None:
    # The public helper resolves the user's active editor, which may change
    # while this script runs. Bind CDF updates to the exact owned cell instead.
    _run_batched_param_update(client, LIB, cell, name, params)


def set_switch(client: VirtuosoClient, name: str, resistance: str = "1k") -> None:
    set_owned_params(client, CDAC, name, rc=resistance, ro="1T", vt1="350m", vt2="550m")


def add_boot(sch, name: str, x: float, y: float, vin: str, vout: str,
             vss: str = "VSS") -> None:
    sch.add(inst(LIB, "sar_bootstrap", "symbol", name, x, y, "R0"))
    for pin_name, net in (("VDD", "VDD"), ("VSS", vss), ("PHI", "PHI"),
                          ("PHIB", "PHIB"), ("VIN", vin), ("VOUT", vout)):
        sch.add(term(name, pin_name, net))


def add_t28_clamp(sch, name: str, x: float, y: float, node: str) -> None:
    sch.add(inst("tsmcN28", "nch_mac", "symbol", name, x, y, "R0"))
    for pin_name, net in (("B", "VSS"), ("D", node),
                          ("G", "CLAMP"), ("S", "VCM")):
        sch.add(term(name, pin_name, net))


def create_cdac(client: VirtuosoClient) -> None:
    capacitors: dict[str, str] = {}
    switches: list[str] = []
    with client.schematic.create(LIB, CDAC) as sch:
        for index, name in enumerate(PORTS):
            sch.add(pin(name, -22.0 + (index % 10) * 2.0, 22.0 - (index // 10) * 2.0,
                        "R0", direction="inputOutput" if name in {"TOPP", "TOPN"} else "input"))
        sch.add(inst("analogLib", "gnd", "symbol", "G0", 0.0, -21.0, "R0"))
    for side, ybase, ref0, ref1 in (("P", 10.0, "VREFP", "VREFN"),
                                    ("N", -8.0, "VREFN", "VREFP")):
        top, lsb, vin = f"TOP{side}", f"LSB{side}", f"VIN{side}"
        for group in ((9, 8, 7, 6, 5), (4, 3, 2, 1, 0)):
            with client.schematic.modify(LIB, CDAC) as sch:
                for bit in group:
                    x = -50.0 + (9 - bit) * 10.0
                    plate = top if bit >= 5 else lsb
                    bottom = f"B{bit}{side}"
                    cap = f"C{bit}{side}"
                    sch.add(inst("analogLib", "cap", "symbol", cap, x, ybase, "R0"))
                    sch.add(term(cap, "PLUS", plate))
                    sch.add(term(cap, "MINUS", bottom))
                    capacitors[cap] = f"{WEIGHT[bit] * CU:.9g}f"
                    add_boot(sch, f"XB{bit}{side}", x, ybase - 4.0, vin, bottom)
                    for suffix, reference, control, ys in (
                        ("0", ref0, f"SEL0<{bit}>", ybase - 8.0),
                        ("1", ref1, f"SEL1<{bit}>", ybase - 10.0),
                    ):
                        name = f"S{bit}{side}{suffix}"
                        add_switch(sch, name, x, ys, bottom, reference, control)
                        switches.append(name)
        with client.schematic.modify(LIB, CDAC) as sch:
            bridge = f"CBRIDGE{side}"
            sch.add(inst("analogLib", "cap", "symbol", bridge, 52.0, ybase, "R0"))
            sch.add(term(bridge, "PLUS", top))
            sch.add(term(bridge, "MINUS", lsb))
            capacitors[bridge] = f"{(32.0 / 31.0) * CU:.9g}f"
            dummy = f"CDUMMY{side}"
            b_dummy = f"BDUMMY{side}"
            sch.add(inst("analogLib", "cap", "symbol", dummy, 64.0, ybase, "R0"))
            sch.add(term(dummy, "PLUS", lsb))
            sch.add(term(dummy, "MINUS", b_dummy))
            capacitors[dummy] = f"{CU:.9g}f"
            add_boot(sch, f"XBDUMMY{side}", 64.0, ybase - 4.0, vin, b_dummy)
            add_switch(sch, f"SD{side}0", 64.0, ybase - 8.0, b_dummy, ref0, "BASE")
            switches.append(f"SD{side}0")
            for name, node, x in ((f"SCLAMPTOP{side}", top, 75.0),
                                  (f"SCLAMPLSB{side}", lsb, 85.0)):
                if T28_CLAMP:
                    add_t28_clamp(sch, name, x, ybase - 12.0, node)
                else:
                    add_switch(sch, name, x, ybase - 12.0, node, "VCM", "CLAMP")
                    switches.append(name)
    client.open_window(LIB, CDAC, view="schematic")
    for name, value in capacitors.items():
        set_owned_params(client, CDAC, name, c=value)
    for name in switches:
        set_switch(client, name, "10" if name.startswith("SCLAMP") else "1k")
    if T28_CLAMP:
        for side in ("P", "N"):
            for stem in ("SCLAMPTOP", "SCLAMPLSB"):
                set_owned_params(client, CDAC, f"{stem}{side}",
                                 Wfg="250n", l="30n", fingers="1", simM="4")
    with client.schematic.modify(LIB, CDAC, timeout=120):
        pass


def create_symbol(client: VirtuosoClient) -> None:
    with client.symbol.create(LIB, CDAC, timeout=120) as sym:
        sym.add(symbol_create_rect("device", "drawing", 0.75, -6.25, 5.25, 18.25))
        sym.add(symbol_create_selection_box(0.0, -6.5, 6.0, 18.5))
        for index, name in enumerate(PORTS):
            if index < 13:
                x, y = (6.0, 17.0 - index) if name in {"TOPP", "TOPN"} else (0.0, 17.0 - index)
            elif index < 23:
                x, y = 0.0, 4.0 - (index - 13) * 1.0
            else:
                x, y = 6.0, 4.0 - (index - 23) * 1.0
            sym.add(symbol_create_pin(name, x, y, direction="inputOutput" if name in {"TOPP", "TOPN"} else "input",
                                      half_size=0.025, label_x=0.9 if x == 0.0 else 5.1,
                                      label_y=y, label_justification="centerLeft" if x == 0.0 else "centerRight"))
        sym.add(symbol_create_instance_label(2.0, 18.7))
        sym.add(symbol_set_term_order(list(PORTS)))


def create_tb(client: VirtuosoClient) -> None:
    with client.schematic.create(LIB, TB) as sch:
        sch.add(inst(LIB, CDAC, "symbol", "XBP", 0.0, 5.0, "R0"))
        sch.add(inst(LIB, "sar_cdac_macro_10b", "symbol", "XTOP", 20.0, 5.0, "R0"))
        add_boot(sch, "XTOPBOOT_P", 12.0, 8.0, "VINP_TOP", "TOPP_TOP", "gnd!")
        add_boot(sch, "XTOPBOOT_N", 12.0, -4.0, "VINN_TOP", "TOPN_TOP", "gnd!")
        for name, x, y, cell in (
            ("VVDD", -22.0, 15.0, "vdc"), ("VVCM", -20.0, 15.0, "vdc"),
            ("VPHI", -18.0, 15.0, "vpulse"), ("VPHIB", -16.0, 15.0, "vpulse"),
            ("VCLAMP", -14.0, 15.0, "vpulse"), ("VBASE", -12.0, 15.0, "vpulse"),
            ("VVP_TOP", -22.0, 10.0, "vpulse"), ("VVN_TOP", -20.0, 10.0, "vpulse"),
            ("VVP_BP", -18.0, 10.0, "vpulse"), ("VVN_BP", -16.0, 10.0, "vpulse"),
        ):
            sch.add(inst("analogLib", cell, "symbol", name, x, y, "R0"))
        for name, x, net, source in (
            ("RINP_TOP", -22.0, "VINP_TOP", "VINP_TOP_SRC"),
            ("RINN_TOP", -20.0, "VINN_TOP", "VINN_TOP_SRC"),
            ("RINP_BP", -18.0, "VINP_BP", "VINP_BP_SRC"),
            ("RINN_BP", -16.0, "VINN_BP", "VINN_BP_SRC"),
        ):
            sch.add(inst("analogLib", "res", "symbol", name, x, 7.0, "R90"))
            sch.add(term(name, "PLUS", source))
            sch.add(term(name, "MINUS", net))
        for name, x, net in (("RPROBEP", 8.0, "TOPP_BP"),
                             ("RPROBEN", 10.0, "TOPN_BP")):
            sch.add(inst("analogLib", "res", "symbol", name, x, -9.0, "R90"))
            sch.add(term(name, "PLUS", net))
            sch.add(term(name, "MINUS", "gnd!"))
        sch.add(inst("analogLib", "gnd", "symbol", "G0", -12.0, -10.0, "R0"))
        sources = {
            "VVDD": "VDD", "VVCM": "VCM", "VPHI": "PHI", "VPHIB": "PHIB",
            "VCLAMP": "CLAMP", "VBASE": "BASE", "VVP_TOP": "VINP_TOP_SRC",
            "VVN_TOP": "VINN_TOP_SRC", "VVP_BP": "VINP_BP_SRC", "VVN_BP": "VINN_BP_SRC",
        }
        for name, net in sources.items():
            sch.add(term(name, "PLUS", net))
            sch.add(term(name, "MINUS", "gnd!"))
        for pin_name, net in (
            ("VINP", "VINP_BP"), ("VINN", "VINN_BP"), ("VDD", "VDD"),
            ("VSS", "gnd!"), ("VREFP", "VCM"), ("VREFN", "VCM"),
            ("VCM", "VCM"), ("PHI", "PHI"), ("PHIB", "PHIB"),
            ("CLAMP", "CLAMP"), ("BASE", "BASE"),
            ("TOPP", "TOPP_BP"), ("TOPN", "TOPN_BP"),
        ):
            sch.add(term("XBP", pin_name, net))
        for pin_name, net in (
            ("TOPP", "TOPP_TOP"), ("TOPN", "TOPN_TOP"),
            ("VREFP", "VCM"), ("VREFN", "VCM"), ("VCM", "VCM"),
            ("CLK_SAMPLE", "PHI"), ("BASE", "BASE"), ("VSS", "gnd!"),
        ):
            sch.add(term("XTOP", pin_name, net))
        for bit in range(10):
            for suffix in ("0", "1"):
                net = "BASE" if suffix == "0" else "gnd!"
                sch.add(term("XBP", f"SEL{suffix}<{bit}>", net))
                sch.add(term("XTOP", f"SEL{suffix}<{bit}>", net))
    client.open_window(LIB, TB, view="schematic")
    for name, voltage in (("VVDD", "900m"), ("VVCM", "450m")):
        set_owned_params(client, TB, name, vdc=voltage)
    for name in ("RINP_TOP", "RINN_TOP", "RINP_BP", "RINN_BP", "RPROBEP", "RPROBEN"):
        set_owned_params(client, TB, name, r="1T" if name.startswith("RPROBE") else "50")
    for name, v1, v2 in (
        ("VVP_TOP", "vinn_target", "vinp_target"),
        ("VVN_TOP", "vinp_target", "vinn_target"),
        ("VVP_BP", "vinn_target", "vinp_target"),
        ("VVN_BP", "vinp_target", "vinn_target"),
    ):
        set_owned_params(client, TB, name, v1=v1, v2=v2, td="205n", tr="100p", tf="100p",
                         pw="80n", per="400n")
    for name, v1, v2, delay, width in (
        ("VPHI", "0", "900m", "11n", "39n"),
        ("VPHIB", "900m", "0", "10n", "41n"),
        ("VCLAMP", "0", "900m", "clamp_delay", "clamp_width"),
        ("VBASE", "0", "900m", "52n", "50n"),
    ):
        set_owned_params(client, TB, name, v1=v1, v2=v2, td=delay, tr="100p", tf="100p",
                         pw=width, per="100n")
    with client.schematic.modify(LIB, TB, timeout=120):
        pass


def markers(client: VirtuosoClient, cell: str) -> int:
    expression = (f'let((cv n) cv=dbOpenCellViewByType("{LIB}" "{cell}" "schematic" "" "r") '
                  'n=length(cv~>markers) dbClose(cv) n)')
    result = client.execute_skill(expression, timeout=30)
    if result.errors:
        raise RuntimeError(result.errors)
    match = re.search(r"\d+", result.output or "")
    if not match:
        raise RuntimeError(result.output)
    return int(match.group())


def rebuild_owned(client: VirtuosoClient) -> None:
    """Replace only the two experimental cells made by this target."""
    for cell in (TB, CDAC):
        if not exists(client, cell):
            continue
        result = client.execute_skill(f'ddGetObj("{LIB}" "{cell}")~>views~>name', timeout=15)
        if result.errors:
            raise RuntimeError(result.errors)
        views = set(re.findall(r'"([^"]+)"', result.output or ""))
        allowed = {"schematic"} if cell == TB else {"schematic", "symbol"}
        if not views or not views.issubset(allowed):
            raise RuntimeError(f"Refusing to replace {LIB}/{cell} with views {views}; allowed {allowed}")
        skill = (
            "foreach(w hiGetWindowList() "
            "let((wcv) wcv=w~>cellView "
            f'when(wcv && wcv~>libName=="{LIB}" && wcv~>cellName=="{cell}" '
            "dbSave(wcv) hiCloseWindow(w))))"
        )
        closed = client.execute_skill(skill, timeout=30)
        if closed.errors:
            raise RuntimeError(closed.errors)
        deleted = client.execute_skill(
            f'let((obj) obj=ddGetObj("{LIB}" "{cell}") if(obj then ddDeleteObj(obj) else t))',
            timeout=30,
        )
        if deleted.errors or (deleted.output or "").strip() == "nil":
            raise RuntimeError(f"Could not delete exact owned cell {LIB}/{cell}: {deleted.errors}")


def main() -> int:
    global CDAC, TB, T28_CLAMP
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument("--output-dir", type=Path, default=Path("output/bootstrap_bottom_plate_eval/readback"))
    parser.add_argument("--rebuild-owned", action="store_true",
                        help="Replace only the two target-owned experimental cells")
    parser.add_argument("--t28-clamp", action="store_true",
                        help="Create independently named variant with T28 NMOS top clamps")
    args = parser.parse_args()
    T28_CLAMP = args.t28_clamp
    if T28_CLAMP:
        CDAC = "sar_cdac_bottom_plate_t28clamp_eval_10b"
        TB = "tb_sar_bottom_plate_t28clamp_eval"
    client = VirtuosoClient.from_env(profile=args.profile)
    if args.rebuild_owned:
        rebuild_owned(client)
    for cell in (CDAC, TB):
        if exists(client, cell):
            raise RuntimeError(f"Refusing to overwrite {LIB}/{cell}")
    create_cdac(client)
    create_symbol(client)
    create_tb(client)
    result = {cell: {"schematic": client.schematic.read(LIB, cell, include_positions=False,
                                                       param_filters=None),
                     "markers": markers(client, cell)} for cell in (CDAC, TB)}
    result["symbol_ports"] = client.symbol.read_ports(LIB, CDAC)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "readback.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({cell: {"instances": len(result[cell]["schematic"]["instances"]),
                             "markers": result[cell]["markers"]} for cell in (CDAC, TB)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
