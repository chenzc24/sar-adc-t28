"""Inputs for the single-edge SAR macro: flattened cells, Innovus netlist and route script.

The macro holds the five top-level instances of the floorplan's SAR block. Every leaf is
a native standard cell, so Innovus places and routes the real netlist. The OA view, the
LVS reference and the physical checks are built from the routed DEF.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path

from Layout.project import ROOT
from tools.saradc.candidates import definitions
from tools.saradc.rnl import instances

CORE = "sar8_se_core"
STD = "tcbn28hpcplusbwp12t30p140"
SUFFIX = "BWP12T30P140"
GROUP = ("XCTRL", "XSEQ", "XDONE", "XPRESET", "XSAMPLE")
# Foundry SPICE port order without the supplies; LEF pins carry the same names.
PINS = {name + SUFFIX: ports.split() for name, ports in {
    "INVD1": "I ZN", "INVD2": "I ZN", "ND2D1": "A1 A2 ZN", "OR2D1": "A1 A2 Z", "AN2D1": "A1 A2 Z",
    "XOR2D1": "A1 A2 Z", "MUX2D1": "I0 I1 S Z", "BUFFD1": "I Z", "BUFFD2": "I Z", "CKBD1": "I Z",
    "TIEH": "Z", "DEL200D1": "I Z", "DEL250D1": "I Z", "DFCNQD1": "D CP CDN Q", "LHCNDQD1": "D E CDN Q",
}.items()}
OUTPUTS = {"Z", "ZN", "Q"}
# Width in 0.14 um sites of the native core12T LEF; row height 1.2 um.
SITES = {name + SUFFIX: n for name, n in {
    "INVD1": 2, "INVD2": 3, "ND2D1": 3, "OR2D1": 4, "AN2D1": 4, "XOR2D1": 8, "MUX2D1": 8, "BUFFD1": 3,
    "BUFFD2": 4, "CKBD1": 3, "TIEH": 2, "DEL200D1": 23, "DEL250D1": 25, "DFCNQD1": 18, "LHCNDQD1": 14,
}.items()}
SITE, ROW = 0.14, 1.2
INPUTS = ("COMP_P", "COMP_N", "SAMPLE")
# Left-edge order, bottom to top: reference-side buses first, comparator-side signals last.
PORT_ORDER = (*[f"{b}{i}" for i in range(8) for b in ("D", "CODE")],
              "PHI_U", "PRESET", "SAMPLE_INT", "SEQ_SAMPLE", "SAMPLE", "COMP_N", "COMP_P", "CMP_CLK")
TECH_LEF = ("/home/process/tsmc28n/Packages/CLN28HPC+/tf_tluplus_outmap_lef/tn28clpr002e1_1_5a/N28_PRTF_12T/"
            "PR_tech/Cadence/LefHeader/HVH/tsmcn28_9lm6X1Z1URDL.tlef")
STD_LEF = ("/home/process/tsmc28n/STD_CELL/tcbn28hpcplusbwp12t30p140_190a/TSMCHOME/digital/Back_End/lef/"
           "tcbn28hpcplusbwp12t30p140_170a/lef/tcbn28hpcplusbwp12t30p140.lef")


def electrical():
    """Flatten the SAR group of the current DUT to native cells with hierarchical names."""
    dut = ROOT / "design/dut.scs"
    entry = dut.read_text(encoding="utf-8")
    subs, files = {}, {}
    for name in re.findall(r'(?m)^include "([^"]+)"', entry):
        found = definitions((dut.parent / name).read_text(encoding="utf-8"))
        if subs.keys() & found.keys():
            raise ValueError("Duplicate subcircuit in " + name)
        subs.update(found)
        files.update(dict.fromkeys(found, dut.parent / name))
    manifest = json.loads((ROOT / "design/manifest.json").read_text(encoding="utf-8"))
    top = manifest["top"]
    parts = instances(subs[top])
    floorplan = json.loads((ROOT / "Layout/design/floorplan.json").read_text(encoding="utf-8"))
    block = next(b for b in floorplan["blocks"] if b["id"] == "sar")
    if set(block["instances"]) != set(GROUP):
        raise ValueError("The floorplan SAR block changed; review the macro group")
    public = set(subs[top].splitlines()[0].split()[2:])
    for inst, (nets, _, _) in parts.items():
        if inst not in GROUP:
            public.update(nets)
    alias = {"VDD!": "VDD", "0": "VSS"}
    cells, touched = {}, {dut, files[top]}
    # Hierarchical node path (instance path / local net) -> flattened macro net.
    names = {}

    def expand(path, master, nets):
        if master in PINS:
            pins = PINS[master] + ["VDD", "VSS"]
            if len(pins) != len(nets):
                raise ValueError("Port count of " + path)
            cells[path.replace("/", "__")] = {"master": master, "pins": dict(zip(pins, nets))}
            return
        text = subs[master]
        touched.add(files[master])
        formal = text.splitlines()[0].split()[2:]
        binding = dict(zip(formal, nets, strict=True))
        local = {}
        for name, (nodes, child, _) in instances(text).items():
            actual = [binding.get(n, path.replace("/", "__") + "__" + n) for n in nodes]
            local.update(zip(nodes, actual))
            expand(path + "/" + name, child, actual)
        for n, flat in {**local, **binding}.items():
            names[(path + "/" + n).upper()] = flat

    ports = set()
    for key in GROUP:
        nets, master, _ = parts[key]
        expand(key, master, [alias.get(n, n) for n in nets])
        ports.update(alias.get(n, n) for n in nets if n in public)
    for cell in cells.values():
        if cell["pins"]["VDD"] != "VDD" or cell["pins"]["VSS"] != "VSS":
            raise ValueError("Cell supplies must be the macro rails")
    signals = sorted(ports - {"VDD", "VSS"})
    if sorted(PORT_ORDER) != signals:
        raise ValueError("Macro ports differ from the planned edge order: " + str(signals))
    hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(touched)}
    electrical.names = names
    return cells, list(PORT_ORDER), hashes


def flat_net(path):
    """Macro net of a DUT probe such as xdut.xctrl.xtim.sn_d; top-level nets keep their names."""
    parts = path.upper().split(".")
    if parts[0] != "XDUT":
        raise ValueError("Probe outside the DUT: " + path)
    if len(parts) == 2:
        return None
    if parts[1] not in GROUP:
        raise ValueError("Probe outside the SAR macro: " + path)
    if not hasattr(electrical, "names"):
        electrical()
    key = "/".join(parts[1:])
    if key not in electrical.names:
        raise ValueError("Unknown SAR node " + path)
    return electrical.names[key]


def verilog(cells, ports):
    nets = sorted({n for c in cells.values() for p, n in c["pins"].items() if p not in ("VDD", "VSS")} - set(ports))
    lines = [f"module {CORE} (" + ", ".join(ports) + ");"]
    lines += [f"  {'input' if p in INPUTS else 'output'} {p};" for p in ports]
    lines += [f"  wire {n};" for n in nets]
    for name, c in sorted(cells.items()):
        pins = ", ".join(f".{p}({n})" for p, n in c["pins"].items() if p not in ("VDD", "VSS"))
        lines.append(f"  {c['master']} {name} ({pins});")
    return "\n".join(lines + ["endmodule", ""])


def check_drivers(cells, ports):
    drivers = {}
    for name, c in cells.items():
        for pin, net in c["pins"].items():
            if pin in OUTPUTS:
                if net in drivers:
                    raise ValueError(f"Net {net} has two drivers")
                drivers[net] = name
    loads = {n for c in cells.values() for p, n in c["pins"].items() if p not in OUTPUTS | {"VDD", "VSS"}}
    floating = sorted((loads - set(drivers)) - set(INPUTS))
    if floating:
        raise ValueError("Undriven inputs: " + str(floating))
    missing = [p for p in ports if p not in INPUTS and p not in drivers]
    if missing:
        raise ValueError("Undriven outputs: " + str(missing))


def route_script(core, rows, ports, utilization):
    """Innovus floorplan, place, power and detailed route; no timing libraries are loaded."""
    width, height = core
    margins = dict(left=1.12, bottom=0.6, right=0.56, top=0.6)
    pins = " ".join(ports)
    return f"""set init_lef_file [list {TECH_LEF} {STD_LEF}]
set init_verilog core.v
set init_top_cell {CORE}
set init_pwr_net VDD
set init_gnd_net VSS
set init_design_settop 1
setMultiCpuUsage -localCpu 4
init_design
floorPlan -site core12T -s {width:.3f} {height:.3f} {margins['left']} {margins['bottom']} {margins['right']} {margins['top']}
globalNetConnect VDD -type pgpin -pin VDD -inst * -override
globalNetConnect VSS -type pgpin -pin VSS -inst * -override
addEndCap -preCap BOUNDARY_LEFT{SUFFIX} -postCap BOUNDARY_RIGHT{SUFFIX} -prefix ENDCAP
addWellTap -cell TAPCELL{SUFFIX} -cellInterval 14 -inRowOffset 1.4 -prefix WELLTAP
setPinAssignMode -pinEditInBatch true
editPin -pin {{{pins}}} -side Left -layer M3 -spreadType center -spacing 0.6 -unit MICRON -fixedPin 1 -fixOverlap 1
setPinAssignMode -pinEditInBatch false
setPlaceMode -place_global_cong_effort high -place_global_max_density {min(0.97, utilization + 0.2):.2f}
placeDesign
refinePlace
addStripe -nets {{VDD VSS}} -layer M6 -direction vertical -width 0.40 -spacing 0.40 -set_to_set_distance 7.0 -start_from left -start_offset 2.0 -stop_offset 1.0
sroute -connect {{corePin}} -nets {{VDD VSS}} -layerChangeRange {{M1 M6}} -corePinTarget {{stripe}} -allowJogging 0 -allowLayerChange 1 -crossoverViaLayerRange {{M1 M6}} -targetViaLayerRange {{M1 M6}}
setNanoRouteMode -routeWithTimingDriven false -routeWithSiDriven false
setNanoRouteMode -routeBottomRoutingLayer 1 -routeTopRoutingLayer 4 -drouteEndIteration 40
routeDesign
addFiller -cell {{DCAP16{SUFFIX} DCAP8{SUFFIX} DCAP4{SUFFIX} FILL3{SUFFIX} FILL2{SUFFIX}}} -prefix FILLER
ecoRoute
verifyConnectivity -type all -report route.conn
verify_drc -report route.drc
verifyGeometry -report route.geom
checkPlace place.rpt
defOut -routing routed.def
set map [open route.map w]
for {{set i 1}} {{$i <= 6}} {{incr i}} {{
  foreach cat {{NET SPNET PIN VIA}} {{puts $map "M$i $cat [expr {{30+$i}}] 0"}}
  if {{$i < 6}} {{puts $map "VIA$i VIA [expr {{50+$i}}] 0"; puts $map "VIA$i SPNET [expr {{50+$i}}] 0"}}
}}
close $map
streamOut overlay.gds -mapFile route.map -libName SAR_SE_OVERLAY -units 1000 -mode ALL
puts "SAR_SE_ROUTE_FINISHED"
exit
"""


def generate(revision, rows, utilization):
    cells, ports, hashes = electrical()
    check_drivers(cells, ports)
    used = sum(SITES[c["master"]] for c in cells.values())
    # Rows hold the cells, one boundary pair and taps; widen until the requested density is met.
    width = round(SITE * -(-used / rows / utilization // 1), 3)
    width = round(SITE * round(width / SITE), 3)
    height = round(rows * ROW, 3)
    out = ROOT / "work/layout/sar-se" / revision
    out.mkdir(parents=True, exist_ok=False)
    (out / "core.v").write_text(verilog(cells, ports), encoding="ascii", newline="\n")
    (out / "route.tcl").write_text(route_script((width, height), rows, ports, utilization), encoding="ascii", newline="\n")
    record = dict(core=CORE, revision=revision, group=list(GROUP), ports=ports, cell_count=len(cells),
                  logic_sites=used, rows=rows, core_um=[width, height], target_utilization=utilization,
                  source_sha256=hashes, cells=cells)
    (out / "cells.json").write_text(json.dumps(record, indent=1) + "\n", encoding="ascii", newline="\n")
    print(json.dumps({k: v for k, v in record.items() if k != "cells"}, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("revision")
    ap.add_argument("--rows", type=int, default=14)
    ap.add_argument("--utilization", type=float, default=0.6)
    a = ap.parse_args()
    generate(a.revision, a.rows, a.utilization)
