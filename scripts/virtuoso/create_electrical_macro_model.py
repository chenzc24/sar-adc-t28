#!/usr/bin/env python3
"""Create the owned topology-aware SAR electrical macro-model OA hierarchy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

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
BLOCKS = ("sar_cdac_macro_10b", "sar_sampling_macro", "sar_comparator_macro")
TB = "tb_sar_macro_transient"
CELLS = (*BLOCKS, TB)
CU_FF = 6.86047
BIT_WEIGHTS = {9: 16, 8: 8, 7: 4, 6: 2, 5: 1, 4: 16, 3: 8, 2: 4, 1: 2, 0: 1}


def _exists(client: VirtuosoClient, cell: str, view: str | None = None) -> bool:
    suffix = f' "{view}"' if view else ""
    result = client.execute_skill(f'ddGetObj("{LIBRARY}" "{cell}"{suffix})', timeout=10)
    return (result.output or "").strip() not in {"", "nil"}


def _add_ground(sch, name: str, x: float, y: float) -> None:
    sch.add(inst("analogLib", "gnd", "symbol", name, x, y, "R0"))


def _close_owned_window(client: VirtuosoClient, cell: str, view: str = "schematic") -> None:
    """Close only this target's exact window before replacing its OA view."""
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


def _add_switch(sch, name: str, x: float, y: float, nplus: str, nminus: str, control: str) -> None:
    sch.add(inst("analogLib", "switch", "symbol", name, x, y, "R0"))
    for terminal, net in (("N+", nplus), ("N-", nminus), ("NC+", control), ("NC-", "gnd!")):
        sch.add(label_term(name, terminal, net))


def _set_switch(client: VirtuosoClient, name: str, rc: str = "1k") -> None:
    set_instance_params(
        client,
        name,
        rc=rc,
        ro="1T",
        vt1="350m",
        vt2="550m",
        param_filters=None,
        strict=True,
    )


def _create_cdac(client: VirtuosoClient) -> None:
    cell = "sar_cdac_macro_10b"
    _close_owned_window(client, cell)
    switch_names: list[str] = []
    cap_values: dict[str, str] = {}
    bit_x = {bit: -9.0 + (9 - bit) * 2.0 for bit in range(9, -1, -1)}
    # Keep each SKILL edit transaction small. A complete 92-instance CDAC in
    # one generated function exceeds the IC6.1.8 literal-stack limit.
    with client.schematic.create(LIBRARY, cell) as sch:
        _add_ground(sch, "G0", 0.0, -20.0)
        for name, x, y, direction in (
            ("TOPP", -18.0, 14.0, "inputOutput"),
            ("TOPN", -18.0, -4.0, "inputOutput"),
            ("VREFP", -18.0, 11.0, "input"),
            ("VREFN", -18.0, 10.0, "input"),
            ("VCM", -18.0, 9.0, "input"),
            ("CLK_SAMPLE", -18.0, 8.0, "input"),
            ("BASE", 18.0, 8.0, "input"),
            ("VSS", 18.0, 7.0, "input"),
        ):
            sch.add(pin(name, x, y, "R0", direction=direction))
        for index, bit in enumerate(range(9, -1, -1)):
            sch.add(pin(f"SEL0<{bit}>", -10.0 + index * 2.0, -17.0, "R90", direction="input"))
            sch.add(pin(f"SEL1<{bit}>", -10.0 + index * 2.0, -18.0, "R90", direction="input"))

    for side, top, lsb, ref0, ref1, ycap, ysw in (
        ("P", "TOPP", "LSBP", "VREFP", "VREFN", 14.0, 10.0),
        ("N", "TOPN", "LSBN", "VREFN", "VREFP", -4.0, -8.0),
    ):
        for bit_group in ((9, 8, 7, 6, 5), (4, 3, 2, 1, 0)):
            with client.schematic.modify(LIBRARY, cell) as sch:
                for bit in bit_group:
                    x = bit_x[bit]
                    plate = top if bit >= 5 else lsb
                    bottom = f"B{bit}{side}"
                    cname = f"C{bit}{side}"
                    sch.add(inst("analogLib", "cap", "symbol", cname, x, ycap, "R0"))
                    sch.add(label_term(cname, "PLUS", plate))
                    sch.add(label_term(cname, "MINUS", bottom))
                    cap_values[cname] = f"{BIT_WEIGHTS[bit] * CU_FF:.9g}f"

                    switch_specs = (
                        (f"S{bit}{side}S", "VCM", "CLK_SAMPLE", ysw),
                        (f"S{bit}{side}0", ref0, f"SEL0<{bit}>", ysw - 2.0),
                        (f"S{bit}{side}1", ref1, f"SEL1<{bit}>", ysw - 4.0),
                    )
                    for sname, target, control, sy in switch_specs:
                        _add_switch(sch, sname, x, sy, bottom, target, control)
                        switch_names.append(sname)

        with client.schematic.modify(LIBRARY, cell) as sch:
            bridge = f"CBRIDGE{side}"
            sch.add(inst("analogLib", "cap", "symbol", bridge, 11.0, ycap, "R0"))
            sch.add(label_term(bridge, "PLUS", top))
            sch.add(label_term(bridge, "MINUS", lsb))
            cap_values[bridge] = f"{(32.0 / 31.0) * CU_FF:.9g}f"

            dummy = f"CDUMMY{side}"
            dummy_bottom = f"BDUMMY{side}"
            sch.add(inst("analogLib", "cap", "symbol", dummy, 13.0, ycap, "R0"))
            sch.add(label_term(dummy, "PLUS", lsb))
            sch.add(label_term(dummy, "MINUS", dummy_bottom))
            cap_values[dummy] = f"{CU_FF:.9g}f"
            for sname, target, control, sy in (
                (f"SD{side}S", "VCM", "CLK_SAMPLE", ysw),
                (f"SD{side}0", ref0, "BASE", ysw - 2.0),
            ):
                _add_switch(sch, sname, 13.0, sy, dummy_bottom, target, control)
                switch_names.append(sname)

            reset = f"SLSBRESET{side}"
            _add_switch(sch, reset, 11.0, ysw - 6.0, lsb, "VCM", "CLK_SAMPLE")
            switch_names.append(reset)

    client.open_window(LIBRARY, cell, view="schematic")
    for name, value in cap_values.items():
        set_instance_params(client, name, c=value, param_filters=None, strict=True)
    for name in switch_names:
        _set_switch(client, name)


def _create_sampling(client: VirtuosoClient) -> None:
    cell = "sar_sampling_macro"
    with client.schematic.create(LIBRARY, cell) as sch:
        _add_ground(sch, "G0", 0.0, -2.0)
        for name, x, y, direction in (
            ("VINP", -4.0, 2.0, "input"),
            ("VINN", -4.0, 0.0, "input"),
            ("TOPP", 4.0, 2.0, "inputOutput"),
            ("TOPN", 4.0, 0.0, "inputOutput"),
            ("CLK_SAMPLE", 0.0, -1.5, "input"),
            ("VSS", 2.0, -1.5, "input"),
        ):
            sch.add(pin(name, x, y, "R0", direction=direction))
        for side, yin in (("P", 2.0), ("N", 0.0)):
            sch.add(inst("analogLib", "res", "symbol", f"RSOURCE{side}", -2.0, yin, "R90"))
            sch.add(label_term(f"RSOURCE{side}", "PLUS", f"VIN{side}"))
            sch.add(label_term(f"RSOURCE{side}", "MINUS", f"VIN{side}_INT"))
            _add_switch(sch, f"SSAMPLE{side}", 1.0, yin, f"VIN{side}_INT", f"TOP{side}", "CLK_SAMPLE")
    client.open_window(LIBRARY, cell, view="schematic")
    for side in ("P", "N"):
        set_instance_params(client, f"RSOURCE{side}", r="5k", param_filters=None, strict=True)
        _set_switch(client, f"SSAMPLE{side}")


def _create_comparator(client: VirtuosoClient) -> None:
    cell = "sar_comparator_macro"
    with client.schematic.create(LIBRARY, cell) as sch:
        _add_ground(sch, "G0", 0.0, -3.0)
        for name, x, y, direction in (
            ("TOPP", -5.0, 2.5, "input"),
            ("TOPN", -5.0, 1.5, "input"),
            ("COMP_P", 5.0, 2.5, "output"),
            ("COMP_N", 5.0, 1.5, "output"),
            ("CMP_RESET", -5.0, 0.0, "input"),
            ("VCM", -5.0, -1.0, "input"),
            ("VDD", 5.0, 0.0, "input"),
            ("VSS", 5.0, -1.0, "input"),
        ):
            sch.add(pin(name, x, y, "R0", direction=direction))

        for name, x, control_p, control_n in (
            ("GIN", -2.0, "TOPP", "TOPN"),
            ("GREG", 0.0, "COMP_P", "COMP_N"),
            ("GOFF", 2.0, "CMP_OFFSET", "gnd!"),
        ):
            sch.add(inst("analogLib", "vccs", "symbol", name, x, 2.0, "R0"))
            for terminal, net in (("PLUS", "COMP_N"), ("MINUS", "COMP_P"), ("NC+", control_p), ("NC-", control_n)):
                sch.add(label_term(name, terminal, net))

        sch.add(inst("analogLib", "cap", "symbol", "CCOMP", 3.5, 2.0, "R0"))
        sch.add(label_term("CCOMP", "PLUS", "COMP_P"))
        sch.add(label_term("CCOMP", "MINUS", "COMP_N"))
        sch.add(inst("analogLib", "vdc", "symbol", "VOFF", -3.0, -1.0, "R0"))
        sch.add(label_term("VOFF", "PLUS", "CMP_OFFSET"))
        sch.add(label_term("VOFF", "MINUS", "gnd!"))

        for side, node, x in (("P", "COMP_P", 1.5), ("N", "COMP_N", 2.5)):
            _add_switch(sch, f"SRESET{side}", x, 0.0, node, "VCM", "CMP_RESET")
            sch.add(inst("analogLib", "res", "symbol", f"RCM{side}", x, -1.0, "R0"))
            sch.add(label_term(f"RCM{side}", "PLUS", node))
            sch.add(label_term(f"RCM{side}", "MINUS", "VCM"))
            sch.add(inst("analogLib", "cap", "symbol", f"CKB{side}", -1.0 + (0.8 if side == "N" else 0.0), -1.0, "R0"))
            sch.add(label_term(f"CKB{side}", "PLUS", node))
            sch.add(label_term(f"CKB{side}", "MINUS", f"TOP{side}"))

    client.open_window(LIBRARY, cell, view="schematic")
    set_instance_params(client, "GIN", ggain="60u", param_filters=None, strict=True)
    set_instance_params(client, "GREG", ggain="100u", param_filters=None, strict=True)
    set_instance_params(client, "GOFF", ggain="-60u", param_filters=None, strict=True)
    set_instance_params(client, "CCOMP", c="20f", param_filters=None, strict=True)
    set_instance_params(client, "CKBP", c="0.05f", param_filters=None, strict=True)
    set_instance_params(client, "CKBN", c="0.05f", param_filters=None, strict=True)
    set_instance_params(client, "VOFF", vdc="0", param_filters=None, strict=True)
    for side in ("P", "N"):
        _set_switch(client, f"SRESET{side}", rc="10")
        set_instance_params(client, f"RCM{side}", r="1G", param_filters=None, strict=True)


def _create_cdac_review_symbol(client: VirtuosoClient) -> None:
    """Create a legible CDAC symbol with enough terminal pitch for OA labels.

    The generic generator uses 0.125-unit pitch.  That is acceptable for a
    compact display symbol, but attaching net labels to 28 adjacent terminals
    in the review testbench can merge neighbours on the IC6.1.8 snap grid.
    """
    cell = "sar_cdac_macro_10b"
    term_order = [
        "TOPN", "TOPP", "BASE", "CLK_SAMPLE",
        *(f"SEL0<{bit}>" for bit in range(10)),
        *(f"SEL1<{bit}>" for bit in range(10)),
        "VCM", "VREFN", "VREFP", "VSS",
    ]
    with client.symbol.create(LIBRARY, cell, timeout=120) as sym:
        sym.add(symbol_create_rect("device", "drawing", 0.75, -2.5, 5.25, 6.5))
        sym.add(symbol_create_selection_box(0.0, -2.75, 6.0, 6.75))
        for index, name in enumerate(("VSS", "VREFP", "VREFN", "VCM", "CLK_SAMPLE", "BASE")):
            y = 6.0 - 0.5 * index
            sym.add(symbol_create_pin(name, 0.0, y, direction="input", half_size=0.025,
                                      label_x=0.9, label_y=y))
        for index, bit in enumerate(range(9, -1, -1)):
            y = 2.5 - 0.5 * index
            sym.add(symbol_create_pin(f"SEL0<{bit}>", 0.0, y, direction="input", half_size=0.025,
                                      label_x=0.9, label_y=y))
            sym.add(symbol_create_pin(f"SEL1<{bit}>", 6.0, y, direction="input", half_size=0.025,
                                      label_x=5.1, label_y=y, label_justification="centerRight"))
        for name, y in (("TOPP", 5.5), ("TOPN", 5.0)):
            sym.add(symbol_create_pin(name, 6.0, y, direction="inputOutput", half_size=0.025,
                                      label_x=5.1, label_y=y, label_justification="centerRight"))
        sym.add(symbol_create_instance_label(2.0, 6.8))
        sym.add(symbol_create_logical_label(3.0, 2.0))
        sym.add(symbol_set_term_order(term_order))


def _generate_symbols(client: VirtuosoClient) -> dict[str, object]:
    _create_cdac_review_symbol(client)
    generated = {
        cell: client.symbol.generate_from_schematic(
            LIBRARY,
            cell,
            overwrite=False,
            timeout=120,
        ).__dict__
        for cell in BLOCKS
        if cell != "sar_cdac_macro_10b"
    }
    generated["sar_cdac_macro_10b"] = {"action": "custom-wide-pitch"}
    return generated


def _create_tb(client: VirtuosoClient) -> None:
    _close_owned_window(client, TB)
    with client.schematic.create(LIBRARY, TB) as sch:
        # The generated CDAC symbol has 28 pins and is intentionally tall.
        # Keep sources and neighbouring blocks well outside its bounding box:
        # a label attached to an overlapping symbol terminal is a real OA
        # connection, not merely a drawing collision.
        _add_ground(sch, "G0", -20.0, -8.0)
        sch.add(inst(LIBRARY, "sar_sampling_macro", "symbol", "XSAMPLE", -13.0, 4.0, "R0"))
        sch.add(inst(LIBRARY, "sar_cdac_macro_10b", "symbol", "XCDAC", 0.0, 4.0, "R0"))
        sch.add(inst(LIBRARY, "sar_comparator_macro", "symbol", "XCOMP", 13.0, 4.0, "R0"))
        for source, x, net, value in (
            ("VDD", -20.0, "VDD", "900m"),
            ("VREFP", -18.0, "VREFP", "900m"),
            ("VREFN", -16.0, "VREFN", "0"),
            ("VCM", -14.0, "VCM", "450m"),
            ("VINP", -12.0, "VINP", "675.439m"),
            ("VINN", -10.0, "VINN", "224.561m"),
        ):
            sch.add(inst("analogLib", "vdc", "symbol", source, x, -7.0, "R0"))
            sch.add(label_term(source, "PLUS", net))
            sch.add(label_term(source, "MINUS", "gnd!"))
        for source, x, net in (
            ("VSAMPLE", -6.0, "CLK_SAMPLE"),
            ("VTRIAL", -4.0, "CLK_TRIAL"),
            ("VLATCH", -2.0, "CLK_LATCH"),
            ("VRESET", 0.0, "CMP_RESET"),
        ):
            sch.add(inst("analogLib", "vpulse", "symbol", source, x, -7.0, "R0"))
            sch.add(label_term(source, "PLUS", net))
            sch.add(label_term(source, "MINUS", "gnd!"))

        for instance, terminal, net in (
            ("XSAMPLE", "VINP", "VINP"), ("XSAMPLE", "VINN", "VINN"),
            ("XSAMPLE", "TOPP", "TOPP"), ("XSAMPLE", "TOPN", "TOPN"),
            ("XSAMPLE", "CLK_SAMPLE", "CLK_SAMPLE"), ("XSAMPLE", "VSS", "gnd!"),
            ("XCDAC", "TOPP", "TOPP"), ("XCDAC", "TOPN", "TOPN"),
            ("XCDAC", "VREFP", "VREFP"), ("XCDAC", "VREFN", "VREFN"),
            ("XCDAC", "VCM", "VCM"), ("XCDAC", "CLK_SAMPLE", "CLK_SAMPLE"),
            ("XCDAC", "BASE", "BASE"), ("XCDAC", "VSS", "gnd!"),
            ("XCOMP", "TOPP", "TOPP"), ("XCOMP", "TOPN", "TOPN"),
            ("XCOMP", "COMP_P", "COMP_P"), ("XCOMP", "COMP_N", "COMP_N"),
            ("XCOMP", "CMP_RESET", "CMP_RESET"), ("XCOMP", "VCM", "VCM"),
            ("XCOMP", "VDD", "VDD"), ("XCOMP", "VSS", "gnd!"),
        ):
            sch.add(label_term(instance, terminal, net))
        for bit in range(9, -1, -1):
            sch.add(label_term("XCDAC", f"SEL0<{bit}>", f"SEL0<{bit}>"))
            sch.add(label_term("XCDAC", f"SEL1<{bit}>", f"SEL1<{bit}>"))

    client.open_window(LIBRARY, TB, view="schematic")
    for source, value in (
        ("VDD", "900m"), ("VREFP", "900m"), ("VREFN", "0"),
        ("VCM", "450m"), ("VINP", "675.439m"), ("VINN", "224.561m"),
    ):
        set_instance_params(client, source, vdc=value, param_filters=None, strict=True)
    for source, td in (("VSAMPLE", "41n"), ("VTRIAL", "46n"), ("VLATCH", "45.5n"), ("VRESET", "44n")):
        set_instance_params(
            client,
            source,
            v1="0",
            v2="900m",
            td=td,
            tr="20p",
            tf="20p",
            pw="200p",
            per="5n",
            param_filters=None,
            strict=True,
        )


def _readback(client: VirtuosoClient, cell: str) -> dict[str, object]:
    data = client.schematic.read(LIBRARY, cell, include_positions=True, param_filters=None)
    keep = {"r", "c", "ggain", "vdc", "rc", "ro", "vt1", "vt2"}
    return {
        "library": LIBRARY,
        "cell": cell,
        "instance_count": len(data.get("instances", [])),
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


def _refresh_schematic_checks(client: VirtuosoClient) -> None:
    """Check/save after parameter edits so hierarchical extraction is current."""
    for cell in CELLS:
        with client.schematic.modify(LIBRARY, cell, timeout=120):
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--export-root", type=Path)
    parser.add_argument("--readback-only", action="store_true")
    parser.add_argument(
        "--repair-tb",
        action="store_true",
        help="replace only the owned macro testbench after exact-cell preflight",
    )
    args = parser.parse_args()

    client = VirtuosoClient.from_env(profile=args.profile)
    existing = [cell for cell in CELLS if _exists(client, cell)]
    if args.readback_only and args.repair_tb:
        raise SystemExit("--readback-only and --repair-tb are mutually exclusive")
    if args.readback_only:
        missing = [cell for cell in CELLS if cell not in existing]
        if missing:
            raise SystemExit(f"Cannot read back missing cells: {', '.join(missing)}")
        symbols: dict[str, object] = {cell: "existing" for cell in BLOCKS}
    elif args.repair_tb:
        missing_blocks = [cell for cell in BLOCKS if cell not in existing]
        if missing_blocks:
            raise SystemExit(f"Cannot repair TB before blocks exist: {', '.join(missing_blocks)}")
        if TB not in existing:
            raise SystemExit(f"Refusing repair because exact target {LIBRARY}/{TB}/schematic is absent")
        _create_cdac(client)
        _create_cdac_review_symbol(client)
        _create_tb(client)
        symbols = {cell: "existing" for cell in BLOCKS}
    else:
        if existing:
            raise SystemExit(f"Refusing to overwrite existing cells: {', '.join(existing)}")
        _create_cdac(client)
        _create_sampling(client)
        _create_comparator(client)
        symbols = _generate_symbols(client)
        _create_tb(client)

    # Parameter setters save instance properties after the initial schematic
    # transaction.  A final check/save refreshes connectivityLastUpdated and
    # prevents OSSHNL-109 on the first hierarchical netlist extraction.
    if not args.readback_only or args.export_root:
        _refresh_schematic_checks(client)

    result: dict[str, object] = {
        "schematics": {cell: _readback(client, cell) for cell in CELLS},
        "symbols": symbols,
        "symbol_ports": {cell: client.symbol.read_ports(LIBRARY, cell) for cell in BLOCKS},
    }
    if args.export_root:
        exports = {}
        # Standalone blocks intentionally expose undriven control pins and are
        # not valid top-level testbenches. Export only the hierarchical review
        # testbench; the executable source-of-truth remains the curated deck.
        for cell in (TB,):
            exported = client.schematic.export_netlist(
                LIBRARY,
                cell,
                args.export_root / cell,
                simulator="spectre",
                recreate_all=True,
                timeout=180,
            )
            exports[cell] = {key: str(value) for key, value in exported.items()}
        result["exports"] = exports
    rendered = json.dumps(result, indent=2, ensure_ascii=False, default=str)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
