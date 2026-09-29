#!/usr/bin/env python3
"""Create/read back a separate first-pass T28 StrongARM and testbench.

Never overwrites an existing OA cell. All wiring is explicit by terminal name.
"""

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
    symbol_create_logical_label,
    symbol_create_pin,
    symbol_create_rect,
    symbol_create_selection_box,
    symbol_set_term_order,
)


LIB = "SAR_ADC_T28"
DUT = "sar_strongarm_t28"
TB = "tb_sar_strongarm_t28"
PORTS = ("VDD", "VSS", "CLK", "VINP", "VINN", "OUTP", "OUTN")
MOS = {
    # name: (master, drain, gate, source, body, finger width)
    "MNTAIL": ("nch_mac", "TAIL", "CLK", "VSS", "VSS", "1u"),
    "MNINP": ("nch_mac", "Y", "VINP", "TAIL", "VSS", "1u"),
    "MNINN": ("nch_mac", "X", "VINN", "TAIL", "VSS", "1u"),
    "MNLATP": ("nch_mac", "OUTP", "OUTN", "X", "VSS", "500n"),
    "MNLATN": ("nch_mac", "OUTN", "OUTP", "Y", "VSS", "500n"),
    "MPLATP": ("pch_mac", "OUTP", "OUTN", "VDD", "VDD", "500n"),
    "MPLATN": ("pch_mac", "OUTN", "OUTP", "VDD", "VDD", "500n"),
    "MPRSTX": ("pch_mac", "X", "CLK", "VDD", "VDD", "500n"),
    "MPRSTY": ("pch_mac", "Y", "CLK", "VDD", "VDD", "500n"),
    "MPRSTP": ("pch_mac", "OUTP", "CLK", "VDD", "VDD", "500n"),
    "MPRSTN": ("pch_mac", "OUTN", "CLK", "VDD", "VDD", "500n"),
}


def exists(client: VirtuosoClient, cell: str, view: str | None = None) -> bool:
    suffix = f' "{view}"' if view else ""
    result = client.execute_skill(f'ddGetObj("{LIB}" "{cell}"{suffix})', timeout=15)
    if result.errors:
        raise RuntimeError(result.errors)
    return (result.output or "").strip() not in {"", "nil"}


def set_params(client: VirtuosoClient, cell: str, name: str, **params: str) -> None:
    # Explicit cell binding avoids retargeting when the user's active window changes.
    _run_batched_param_update(client, LIB, cell, name, params)


def create_dut(client: VirtuosoClient) -> None:
    with client.schematic.create(LIB, DUT) as sch:
        for index, name in enumerate(PORTS):
            direction = "output" if name in {"OUTP", "OUTN"} else "input"
            sch.add(pin(name, -10.0 if direction == "input" else 10.0,
                        8.0 - index * 2.0, "R0" if direction == "input" else "R180",
                        direction=direction))
        for index, (name, (master, drain, gate, source, body, _)) in enumerate(MOS.items()):
            x = -8.0 + (index % 4) * 5.0
            y = 5.0 - (index // 4) * 5.0
            sch.add(inst("tsmcN28", master, "symbol", name, x, y, "R0"))
            for terminal, net in (("D", drain), ("G", gate), ("S", source), ("B", body)):
                sch.add(term(name, terminal, net))
    size_dut(client)
    with client.schematic.modify(LIB, DUT, timeout=120):
        pass


def size_dut(client: VirtuosoClient) -> None:
    for name, (_, _, _, _, _, width) in MOS.items():
        set_params(client, DUT, name, Wfg=width, l="30n", fingers="1", simM="1")


def create_symbol(client: VirtuosoClient) -> None:
    with client.symbol.create(LIB, DUT, timeout=120) as sym:
        sym.add(symbol_create_rect("device", "drawing", 0.75, -3.0, 5.25, 3.0))
        sym.add(symbol_create_selection_box(0.0, -3.25, 6.0, 3.25))
        for name, y in (("VINP", 2.0), ("VINN", 1.0), ("CLK", 0.0),
                        ("VDD", -1.0), ("VSS", -2.0)):
            sym.add(symbol_create_pin(name, 0.0, y, direction="input", half_size=0.025,
                                      label_x=0.9, label_y=y))
        for name, y in (("OUTP", 1.5), ("OUTN", -1.5)):
            sym.add(symbol_create_pin(name, 6.0, y, direction="output", half_size=0.025,
                                      label_x=5.1, label_y=y,
                                      label_justification="centerRight"))
        sym.add(symbol_create_instance_label(2.0, 3.5))
        sym.add(symbol_create_logical_label(3.0, 0.0))
        sym.add(symbol_set_term_order(list(PORTS)))


def create_tb(client: VirtuosoClient) -> None:
    with client.schematic.create(LIB, TB) as sch:
        sch.add(inst(LIB, DUT, "symbol", "XCMP", 0.0, 0.0, "R0"))
        for index, name in enumerate(("VVDD", "VCLK", "VIPP", "VNN_SRC")):
            master = "vpulse" if name == "VCLK" else "vdc"
            sch.add(inst("analogLib", master, "symbol", name, -9.0,
                         5.0 - index * 3.0, "R0"))
        for index, name in enumerate(("COUTP", "COUTN")):
            sch.add(inst("analogLib", "cap", "symbol", name, 9.0,
                         2.0 - index * 4.0, "R0"))
        sch.add(inst("analogLib", "gnd", "symbol", "G0", 0.0, -8.0, "R0"))
        for name in PORTS:
            sch.add(term("XCMP", name, "gnd!" if name == "VSS" else name))
        for source, net in (("VVDD", "VDD"), ("VCLK", "CLK"),
                            ("VIPP", "VINP"), ("VNN_SRC", "VINN")):
            sch.add(term(source, "PLUS", net))
            sch.add(term(source, "MINUS", "gnd!"))
        for cap, net in (("COUTP", "OUTP"), ("COUTN", "OUTN")):
            sch.add(term(cap, "PLUS", net))
            sch.add(term(cap, "MINUS", "gnd!"))
    set_params(client, TB, "VVDD", vdc="900m")
    set_params(client, TB, "VIPP", vdc="vinp")
    set_params(client, TB, "VNN_SRC", vdc="vinn")
    set_params(client, TB, "VCLK", v1="0", v2="900m", td="5n", tr="20p",
               tf="20p", pw="2n", per="5n")
    for name in ("COUTP", "COUTN"):
        set_params(client, TB, name, c="5f")
    with client.schematic.modify(LIB, TB, timeout=120):
        pass


def compact(data: dict) -> dict:
    return {
        "pins": data.get("pins"),
        "nets": data.get("nets"),
        "instances": [
            {"name": item.get("name"), "lib": item.get("lib"),
             "cell": item.get("cell"), "terms": item.get("terms"),
             "params": {key: value for key, value in item.get("params", {}).items()
                        if key in {"l", "Wfg", "fingers", "simM", "c", "vdc",
                                   "v1", "v2", "td", "tr", "tf", "pw", "per"}}}
            for item in data.get("instances", [])
        ],
    }


def marker_count(client: VirtuosoClient, cell: str) -> int:
    expression = (
        "let((cv n) "
        f'cv=dbOpenCellViewByType("{LIB}" "{cell}" "schematic" "" "r") '
        "n=length(cv~>markers) dbClose(cv) n)"
    )
    result = client.execute_skill(expression, timeout=30)
    if result.errors:
        raise RuntimeError(f"Marker query failed for {cell}: {result.errors}")
    numbers = re.findall(r"\b\d+\b", result.output or "")
    if not numbers:
        raise RuntimeError(f"Marker query returned no integer for {cell}")
    return int(numbers[-1])


def marker_details(client: VirtuosoClient, cell: str) -> str:
    expression = (
        "let((cv m props) "
        f'cv=dbOpenCellViewByType("{LIB}" "{cell}" "schematic" "" "r") '
        "m=car(cv~>markers) props=if(m then list(m~>msg m~>shortMsg m~>severity m~>objects m~>bBox) else nil) "
        "dbClose(cv) props)"
    )
    result = client.execute_skill(expression, timeout=30)
    if result.errors:
        raise RuntimeError(f"Marker detail query failed: {result.errors}")
    return result.output or ""


def validate_readback(result: dict) -> None:
    dut = result["dut"]
    tb = result["testbench"]
    if set(dut["pins"]) != set(PORTS):
        raise RuntimeError("DUT pins readback incomplete")
    instances = {item["name"]: item for item in dut["instances"]}
    if set(instances) != set(MOS):
        raise RuntimeError(f"DUT instance set mismatch: {set(instances)}")
    for name, (master, drain, gate, source, body, width) in MOS.items():
        item = instances[name]
        if (item["lib"], item["cell"]) != ("tsmcN28", master):
            raise RuntimeError(f"Unexpected PDK master for {name}")
        if item["terms"] != {"D": drain, "G": gate, "S": source, "B": body}:
            raise RuntimeError(f"Terminal mismatch for {name}: {item['terms']}")
        for key, expected in (("Wfg", width), ("l", "30n"),
                              ("fingers", "1"), ("simM", "1")):
            if item["params"].get(key) != expected:
                raise RuntimeError(f"Size mismatch for {name}.{key}: {item['params']}")
    tb_instances = {item["name"]: item for item in tb["instances"]}
    if set(tb_instances) != {"XCMP", "VNN_SRC", "VIPP", "VVDD", "VCLK",
                             "COUTN", "COUTP", "G0"}:
        raise RuntimeError("Unexpected testbench instance set")
    expected_cmp = {name: "gnd!" if name == "VSS" else name for name in PORTS}
    if tb_instances["XCMP"]["terms"] != expected_cmp:
        raise RuntimeError("Testbench comparator pin mismatch")
    for name, node in (("VNN_SRC", "VINN"), ("VIPP", "VINP"),
                       ("VVDD", "VDD"), ("VCLK", "CLK")):
        if tb_instances[name]["terms"] != {"PLUS": node, "MINUS": "gnd!"}:
            raise RuntimeError(f"Testbench source connection mismatch: {name}")
    for name, node in (("COUTN", "OUTN"), ("COUTP", "OUTP")):
        if tb_instances[name]["terms"] != {"PLUS": node, "MINUS": "gnd!"}:
            raise RuntimeError(f"Testbench load connection mismatch: {name}")
    if result["markers"] != {DUT: 0, TB: 0}:
        raise RuntimeError(f"Schematic check markers: {result['markers']}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument("--readback-only", action="store_true")
    parser.add_argument("--inspect-partial", action="store_true")
    parser.add_argument("--marker-detail", action="store_true")
    parser.add_argument("--rename-tb-source", action="store_true")
    parser.add_argument("--resume-owned", action="store_true")
    parser.add_argument("--output-dir", type=Path,
                        default=Path("output/strongarm_t28_first_pass/readback"))
    args = parser.parse_args()
    client = VirtuosoClient.from_env(profile=args.profile)
    info = client.library.get(LIB)
    if info.path != "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28":
        raise RuntimeError(f"Unexpected library path: {info.path}")
    if info.technology_library != "tsmcN28":
        raise RuntimeError(f"Unexpected technology: {info.technology_library}")
    found = [cell for cell in (DUT, TB) if exists(client, cell)]
    if args.rename_tb_source:
        if found != [DUT, TB]:
            raise RuntimeError(f"Unexpected OA state for targeted repair: {found}")
        data = client.schematic.read(LIB, TB, include_positions=False,
                                     param_filters=None)
        names = {item["name"] for item in data.get("instances", [])}
        if "VINN" not in names or "VNN_SRC" in names:
            raise RuntimeError(f"Unexpected source naming: {names}")
        detail = marker_details(client, TB)
        if "Instance name collides with signal name" not in detail or "VINN" not in detail:
            raise RuntimeError("Expected exact HDL-syntax marker missing")
        with client.schematic.modify(LIB, TB, timeout=120) as sch:
            sch.add('let((i) i=car(setof(x cv~>instances x~>name=="VINN")) '
                    'unless(i error("VINN source not found")) i~>name="VNN_SRC")')
        # Continue to readback and validate below.
        args.readback_only = True
    if args.marker_detail:
        for cell in (DUT, TB):
            print(f"{cell}: {marker_count(client, cell)}")
            print(marker_details(client, cell))
        return 0
    if args.inspect_partial:
        print(json.dumps({
            "found": found,
            "dut": compact(client.schematic.read(LIB, DUT, include_positions=True,
                                                  param_filters=None)) if DUT in found else None,
        }, indent=2, default=str))
        return 0
    if args.readback_only:
        if len(found) != 2:
            raise RuntimeError(f"Owned OA cells missing: {found}")
    elif args.resume_owned:
        if found != [DUT] or exists(client, DUT, "symbol"):
            raise RuntimeError(f"Unexpected partial-cell state: {found}")
        data = client.schematic.read(LIB, DUT, include_positions=False,
                                     param_filters=None)
        actual = {item["name"]: (item["lib"], item["cell"])
                  for item in data.get("instances", [])}
        expected = {name: ("tsmcN28", item[0]) for name, item in MOS.items()}
        if actual != expected:
            raise RuntimeError(f"Partial DUT device mismatch: {actual}")
        size_dut(client)
        create_symbol(client)
        create_tb(client)
    elif found:
        raise RuntimeError(f"Refusing to overwrite existing cells: {found}")
    else:
        create_dut(client)
        create_symbol(client)
        create_tb(client)
    result = {
        "library": {"name": info.name, "path": info.path,
                    "technology": info.technology_library},
        "dut": compact(client.schematic.read(LIB, DUT, include_positions=True,
                                              param_filters=None)),
        "testbench": compact(client.schematic.read(LIB, TB, include_positions=True,
                                                    param_filters=None)),
        "symbol_ports": client.symbol.read_ports(LIB, DUT),
        "markers": {cell: marker_count(client, cell) for cell in (DUT, TB)},
    }
    validate_readback(result)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    destination = args.output_dir / "readback.json"
    destination.write_text(json.dumps(result, indent=2, default=str) + "\n",
                           encoding="utf-8")
    print(json.dumps({"path": str(destination), "mos_count": len(MOS),
                      "symbol_ports": [item["name"] for item in
                                       result["symbol_ports"]["terms"]],
                      "markers": result["markers"]}, default=str, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
