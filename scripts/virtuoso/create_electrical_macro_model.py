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
CONTROLLER = "sar_macro_controller_10b"
TB = "tb_sar_macro_transient"
SCHEMATIC_CELLS = (*BLOCKS, TB)
CELLS = (*BLOCKS, CONTROLLER, TB)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTROLLER_SOURCE = PROJECT_ROOT / "models" / "veriloga" / "sar_macro_controller_10b.va"
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


def _close_owned_db_view(client: VirtuosoClient, cell: str, view: str) -> None:
    """Close an exact owned DB view even when it has no visible editor window."""
    result = client.execute_skill(
        f'let((cv) cv=dbFindOpenCellViewByName("{LIBRARY}" "{cell}" "{view}") '
        'if(cv then progn(dbSave(cv) dbClose(cv)) else t))',
        timeout=30,
    )
    if result.errors or (result.output or "").strip() == "nil":
        raise RuntimeError(f"failed to close owned DB view {LIBRARY}/{cell}/{view}: {result.errors}")


def _add_switch(
    sch,
    name: str,
    x: float,
    y: float,
    nplus: str,
    nminus: str,
    control: str,
    vss: str = "VSS",
) -> None:
    sch.add(inst("analogLib", "switch", "symbol", name, x, y, "R0"))
    for terminal, net in (("N+", nplus), ("N-", nminus), ("NC+", control), ("NC-", vss)):
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
    _close_owned_window(client, cell)
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
    _close_owned_window(client, cell)
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
        sch.add(label_term("VOFF", "MINUS", "VSS"))

        for side, node, x in (("P", "COMP_P", 1.5), ("N", "COMP_N", 2.5)):
            _add_switch(sch, f"SRESET{side}", x, 0.0, node, "VCM", "CMP_RESET")
            sch.add(inst("analogLib", "res", "symbol", f"RCM{side}", x, -1.0, "R0"))
            sch.add(label_term(f"RCM{side}", "PLUS", node))
            sch.add(label_term(f"RCM{side}", "MINUS", "VCM"))
            sch.add(inst("analogLib", "cap", "symbol", f"CKB{side}", -1.0 + (0.8 if side == "N" else 0.0), -1.0, "R0"))
            sch.add(label_term(f"CKB{side}", "PLUS", node))
            sch.add(label_term(f"CKB{side}", "MINUS", f"TOP{side}"))

            # Match the curated macro's rail limiting with explicit diode
            # branches. The analysis wrapper supplies the macro_clamp model
            # card; the electrical connectivity remains schematic-owned.
            for suffix, anode, cathode, y in (
                ("H", node, "VDD", 3.5),
                ("L", "VSS", node, -2.0),
            ):
                dname = f"D{suffix}{side}"
                sch.add(inst("analogLib", "diode", "symbol", dname, 3.5 + (0.8 if side == "N" else 0.0), y, "R0"))
                sch.add(label_term(dname, "PLUS", anode))
                sch.add(label_term(dname, "MINUS", cathode))

    client.open_window(LIBRARY, cell, view="schematic")
    set_instance_params(client, "GIN", ggain="60u", param_filters=None, strict=True)
    set_instance_params(client, "GREG", ggain="100u", param_filters=None, strict=True)
    set_instance_params(client, "GOFF", ggain="-60u", param_filters=None, strict=True)
    set_instance_params(client, "CCOMP", c="20f", param_filters=None, strict=True)
    set_instance_params(client, "CKBP", c="0.05f", param_filters=None, strict=True)
    set_instance_params(client, "CKBN", c="0.05f", param_filters=None, strict=True)
    set_instance_params(client, "VOFF", vdc="0", param_filters=None, strict=True)
    for side in ("P", "N"):
        for suffix in ("H", "L"):
            set_instance_params(
                client,
                f"D{suffix}{side}",
                model="macro_clamp",
                param_filters=None,
                strict=True,
            )
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


def _create_controller_symbol(client: VirtuosoClient) -> None:
    """Create the symbol directly so no empty schematic shadows Verilog-A."""
    inputs = ("COMP_P", "COMP_N", "CLK_SAMPLE", "CLK_TRIAL", "CLK_LATCH", "VDD", "VSS")
    outputs = (
        *(f"SEL0_{bit}" for bit in range(9, -1, -1)),
        *(f"SEL1_{bit}" for bit in range(9, -1, -1)),
        "BASE",
        *(f"D{bit}" for bit in range(9, -1, -1)),
        "BUSY",
        "VALID",
    )
    with client.symbol.create(LIBRARY, CONTROLLER, timeout=120) as sym:
        sym.add(symbol_create_rect("device", "drawing", 0.75, -7.25, 7.25, 7.0))
        sym.add(symbol_create_selection_box(0.0, -7.5, 8.0, 7.25))
        for index, name in enumerate(inputs):
            y = 6.5 - index
            sym.add(symbol_create_pin(name, 0.0, y, direction="input", half_size=0.025,
                                      label_x=0.9, label_y=y))
        for index, name in enumerate(outputs):
            y = 6.5 - index * 0.42
            sym.add(symbol_create_pin(name, 8.0, y, direction="output", half_size=0.025,
                                      label_x=7.1, label_y=y, label_justification="centerRight"))
        sym.add(symbol_create_instance_label(2.0, 7.4))
        sym.add(symbol_create_logical_label(4.0, 0.0))
        sym.add(symbol_set_term_order([*inputs, *outputs]))


def _controller_remote_path(client: VirtuosoClient) -> str:
    result = client.execute_skill(f'ddGetObj("{LIBRARY}")~>readPath', timeout=30)
    path = (result.output or "").strip().strip('"')
    if result.errors or not path or path == "nil":
        raise RuntimeError(f"cannot resolve OA readPath for {LIBRARY}: {result.errors}")
    return f"{path}/{CONTROLLER}/veriloga/veriloga.va"


def _delete_controller_placeholder(client: VirtuosoClient) -> None:
    _close_owned_window(client, CONTROLLER)
    result = client.execute_skill(
        f'let((obj) obj=ddGetObj("{LIBRARY}" "{CONTROLLER}" "schematic") '
        'if(obj then ddDeleteObj(obj) else t))',
        timeout=30,
    )
    if result.errors or (result.output or "").strip() == "nil":
        raise RuntimeError(f"controller placeholder cleanup failed: {result.errors}")


def _create_controller_veriloga(client: VirtuosoClient) -> None:
    if not CONTROLLER_SOURCE.is_file():
        raise FileNotFoundError(CONTROLLER_SOURCE)
    if not _exists(client, CONTROLLER, "veriloga"):
        inputs = ("COMP_P", "COMP_N", "CLK_SAMPLE", "CLK_TRIAL", "CLK_LATCH", "VDD", "VSS")
        outputs = (
            *(f"SEL0_{bit}" for bit in range(9, -1, -1)),
            *(f"SEL1_{bit}" for bit in range(9, -1, -1)),
            "BASE",
            *(f"D{bit}" for bit in range(9, -1, -1)),
            "BUSY",
            "VALID",
        )
        try:
            with client.schematic.create(LIBRARY, CONTROLLER) as sch:
                for index, name in enumerate(inputs):
                    sch.add(pin(name, 0.0, -float(index), "R0", direction="input"))
                for index, name in enumerate(outputs):
                    sch.add(pin(name, 6.0, -float(index), "R0", direction="output"))
            _close_owned_db_view(client, CONTROLLER, "symbol")
            client.symbol.generate_from_schematic(
                LIBRARY,
                CONTROLLER,
                sort_pins="geometric",
                overwrite=True,
                timeout=120,
            )
            result = client.execute_skill(
                f'schViewToView("{LIBRARY}" "{CONTROLLER}" "{LIBRARY}" "{CONTROLLER}" '
                '"symbol" "veriloga" '
                '"schSymbolToPinList" "ahdlPinListToveriloga")',
                timeout=120,
            )
            if result.errors or not (result.output or "").strip() or (result.output or "").strip() == "nil":
                raise RuntimeError(f"controller Verilog-A skeleton failed: {result.errors}")
        finally:
            _delete_controller_placeholder(client)
    client.upload_file(CONTROLLER_SOURCE, _controller_remote_path(client), timeout=120)
    result = client.execute_skill(
        f'ahdlUpdateViewInfo("{LIBRARY}" ?cell "{CONTROLLER}" ?view "veriloga")',
        timeout=120,
    )
    if result.errors:
        raise RuntimeError(f"controller Verilog-A reparse failed: {result.errors}")
    # Restore the compact review symbol after Cadence has created and parsed
    # the behavioural view. It has the same terminal contract.
    _create_controller_symbol(client)


def _create_tb(client: VirtuosoClient) -> None:
    _close_owned_window(client, TB)
    with client.schematic.create(LIBRARY, TB) as sch:
        # Keep the tall CDAC symbol and controller pins spatially
        # separated. Connectivity is name-based and is verified by readback.
        _add_ground(sch, "G0", -22.0, -10.0)
        sch.add(inst(LIBRARY, "sar_sampling_macro", "symbol", "XSAMPLE", -14.0, 4.0, "R0"))
        sch.add(inst(LIBRARY, "sar_cdac_macro_10b", "symbol", "XCDAC", -2.0, 4.0, "R0"))
        sch.add(inst(LIBRARY, "sar_comparator_macro", "symbol", "XCOMP", 11.0, 4.0, "R0"))
        sch.add(inst(LIBRARY, CONTROLLER, "symbol", "XCTRL", 20.0, 2.0, "R0"))
        for source, x, net, value in (
            ("V_SRC_DD", -22.0, "VDD", "900m"),
            ("V_SRC_REFP", -20.0, "VREFP_IDEAL", "900m"),
            ("V_SRC_REFN", -18.0, "VREFN_IDEAL", "0"),
            ("V_SRC_CM", -16.0, "VCM", "450m"),
            ("V_SRC_INP", -14.0, "VINP", "675.439m"),
            ("V_SRC_INN", -12.0, "VINN", "224.561m"),
        ):
            sch.add(inst("analogLib", "vdc", "symbol", source, x, -9.0, "R0"))
            sch.add(label_term(source, "PLUS", net))
            sch.add(label_term(source, "MINUS", "gnd!"))
        for source, x, net in (
            ("V_CLK_SAMPLE", -8.0, "CLK_SAMPLE"),
            ("V_CLK_TRIAL", -6.0, "CLK_TRIAL"),
            ("V_CLK_LATCH", -4.0, "CLK_LATCH"),
            ("V_CMP_RESET", -2.0, "CMP_RESET"),
        ):
            sch.add(inst("analogLib", "vpulse", "symbol", source, x, -9.0, "R0"))
            sch.add(label_term(source, "PLUS", net))
            sch.add(label_term(source, "MINUS", "gnd!"))

        for side, ideal_net, local_net, x in (
            ("P", "VREFP_IDEAL", "VREFP", 1.0),
            ("N", "VREFN_IDEAL", "VREFN", 3.0),
        ):
            sch.add(inst("analogLib", "res", "symbol", f"RREF{side}", x, -7.0, "R90"))
            sch.add(label_term(f"RREF{side}", "PLUS", ideal_net))
            sch.add(label_term(f"RREF{side}", "MINUS", local_net))
            sch.add(inst("analogLib", "cap", "symbol", f"CREF{side}", x, -9.0, "R0"))
            sch.add(label_term(f"CREF{side}", "PLUS", local_net))
            sch.add(label_term(f"CREF{side}", "MINUS", "gnd!"))

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
            ("XCTRL", "COMP_P", "COMP_P"), ("XCTRL", "COMP_N", "COMP_N"),
            ("XCTRL", "CLK_SAMPLE", "CLK_SAMPLE"), ("XCTRL", "CLK_TRIAL", "CLK_TRIAL"),
            ("XCTRL", "CLK_LATCH", "CLK_LATCH"), ("XCTRL", "VDD", "VDD"),
            ("XCTRL", "VSS", "gnd!"), ("XCTRL", "BASE", "BASE"),
            ("XCTRL", "BUSY", "BUSY"),
            ("XCTRL", "VALID", "VALID"),
        ):
            sch.add(label_term(instance, terminal, net))
        for bit in range(9, -1, -1):
            sch.add(label_term("XCDAC", f"SEL0<{bit}>", f"SEL0<{bit}>"))
            sch.add(label_term("XCDAC", f"SEL1<{bit}>", f"SEL1<{bit}>"))
            sch.add(label_term("XCTRL", f"SEL0_{bit}", f"SEL0<{bit}>"))
            sch.add(label_term("XCTRL", f"SEL1_{bit}", f"SEL1<{bit}>"))
            sch.add(label_term("XCTRL", f"D{bit}", f"DOUT<{bit}>"))

        for index, net in enumerate([*(f"DOUT<{bit}>" for bit in range(10)), "BUSY", "VALID"]):
            name = f"RLOAD{index}"
            sch.add(inst("analogLib", "res", "symbol", name, 10.0 + index, -7.0, "R0"))
            sch.add(label_term(name, "PLUS", net))
            sch.add(label_term(name, "MINUS", "gnd!"))

    client.open_window(LIBRARY, TB, view="schematic")
    for source, value in (
        ("V_SRC_DD", "900m"), ("V_SRC_REFP", "900m"), ("V_SRC_REFN", "0"),
        ("V_SRC_CM", "450m"), ("V_SRC_INP", "675.439m"), ("V_SRC_INN", "224.561m"),
    ):
        set_instance_params(client, source, vdc=value, param_filters=None, strict=True)
    pulse_params = {
        "V_CLK_SAMPLE": {"v1": "900m", "v2": "0", "td": "41n", "pw": "100n", "per": "200n"},
        "V_CLK_TRIAL": {"v1": "0", "v2": "900m", "td": "46n", "pw": "200p", "per": "5n"},
        "V_CLK_LATCH": {"v1": "0", "v2": "900m", "td": "45.5n", "pw": "200p", "per": "5n"},
        "V_CMP_RESET": {"v1": "900m", "v2": "0", "td": "44n", "pw": "1.53n", "per": "5n"},
    }
    for source, values in pulse_params.items():
        set_instance_params(
            client,
            source,
            **values,
            tr="20p",
            tf="20p",
            param_filters=None,
            strict=True,
        )
    for side in ("P", "N"):
        set_instance_params(client, f"RREF{side}", r="100", param_filters=None, strict=True)
        set_instance_params(client, f"CREF{side}", c="2p", param_filters=None, strict=True)
    for index in range(12):
        set_instance_params(client, f"RLOAD{index}", r="1G", param_filters=None, strict=True)


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
    for cell in SCHEMATIC_CELLS:
        with client.schematic.modify(LIBRARY, cell, timeout=120):
            pass


def _controller_readback(client: VirtuosoClient) -> dict[str, object]:
    views = client.execute_skill(f'ddGetObj("{LIBRARY}" "{CONTROLLER}")~>views~>name', timeout=30)
    terminals = client.execute_skill(
        f'let((cv) cv=dbOpenCellViewByType("{LIBRARY}" "{CONTROLLER}" "veriloga" nil "r") '
        'prog1(when(cv cv~>terminals~>name) when(cv dbClose(cv))))',
        timeout=30,
    )
    return {
        "library": LIBRARY,
        "cell": CONTROLLER,
        "views": (views.output or "").strip(),
        "veriloga_terminals": (terminals.output or "").strip(),
        "symbol_ports": client.symbol.read_ports(LIBRARY, CONTROLLER),
        "source": str(CONTROLLER_SOURCE),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--export-root", type=Path)
    parser.add_argument("--readback-only", action="store_true")
    parser.add_argument(
        "--repair-tb",
        action="store_true",
        help="legacy alias for --repair-oa-loop",
    )
    parser.add_argument(
        "--repair-oa-loop",
        action="store_true",
        help="rebuild the owned macros, import the controller, and close the OA loop",
    )
    args = parser.parse_args()

    client = VirtuosoClient.from_env(profile=args.profile)
    existing = [cell for cell in CELLS if _exists(client, cell)]
    repair = args.repair_tb or args.repair_oa_loop
    if args.readback_only and repair:
        raise SystemExit("--readback-only and repair modes are mutually exclusive")
    if args.readback_only:
        missing = [cell for cell in CELLS if cell not in existing]
        if missing:
            raise SystemExit(f"Cannot read back missing cells: {', '.join(missing)}")
        symbols: dict[str, object] = {cell: "existing" for cell in (*BLOCKS, CONTROLLER)}
    elif repair:
        missing_blocks = [cell for cell in BLOCKS if cell not in existing]
        if missing_blocks:
            raise SystemExit(f"Cannot repair OA loop before blocks exist: {', '.join(missing_blocks)}")
        if TB not in existing:
            raise SystemExit(f"Refusing repair because exact target {LIBRARY}/{TB}/schematic is absent")
        _create_controller_veriloga(client)
        _create_cdac(client)
        _create_sampling(client)
        _create_comparator(client)
        _create_cdac_review_symbol(client)
        _create_tb(client)
        symbols = {cell: "rebuilt" for cell in (*BLOCKS, CONTROLLER)}
    else:
        if existing:
            raise SystemExit(f"Refusing to overwrite existing cells: {', '.join(existing)}")
        _create_controller_veriloga(client)
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
        "schematics": {cell: _readback(client, cell) for cell in SCHEMATIC_CELLS},
        "controller": _controller_readback(client),
        "symbols": symbols,
        "symbol_ports": {cell: client.symbol.read_ports(LIBRARY, cell) for cell in (*BLOCKS, CONTROLLER)},
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
