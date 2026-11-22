"""Output register XOREG of the IO ring plan as the native standard-cell macro sar8_out_reg.

The electrical source is design/chip/output_register.scs (eight DEL250D1 -> DFQD1 -> BUFFD4 bits; CP on SAMPLE_CORE).
Innovus places and routes it in the io_ring.json output_register region (40 x 40 um at die (492, 472)) with the pins
where the chip routes land: D0-D7 on the west edge at the ADC's M7 D-track rows, Q0-Q7 on the south edge at the
D_CORE route columns, CK on the north edge under the SAMPLE route, and a DVDD (VDD) / VSS ring on M5/M6.
- `generate REV` writes core.v, route.tcl and cells.json to work/layout/output-register/REV;
- `route REV` runs Innovus on the layout host (Layout/tools/physical/sar_se_route.py conventions);
- `convert REV` turns the routed DEF into an object-cell content file in die coordinates (every rectangle on its
  DEF net, rendered geometry XOR-checked against the Innovus stream) and the LVS reference sar8_out_reg.cdl.
"""
import argparse
import hashlib
import json
import re
import shlex
import subprocess

from Layout.design.sar_single_edge import STD, SUFFIX, TECH_LEF, STD_LEF
from Layout.project import ROOT, config, write_json

CELL = "sar8_out_reg"
SOURCE = ROOT / "design/chip/output_register.scs"
WORK = ROOT / "work/layout/output-register"
INNOVUS = "/home/cshrc/.cshrc.cadence.GENUS201"
# Foundry SPICE port order without the supplies (tcbn28hpcplusbwp12t30p140_170a.spi).
PINS = {"DEL250D1" + SUFFIX: ["I", "Z"], "DFQD1" + SUFFIX: ["D", "CP", "Q"], "BUFFD4" + SUFFIX: ["I", "Z"]}
OUTPUTS = {"Z", "Q"}
PORTS = [f"D{k}" for k in range(8)] + [f"Q{k}" for k in range(8)] + ["CK"]
INPUTS = [f"D{k}" for k in range(8)] + ["CK"]
ORIGIN = (492.0, 472.0)                      # io_ring.json reserved_regions output_register lower-left
DIE = 40.0
CORE_SITES, ROWS = 235, 27                   # 32.9 x 32.4 um core
MARGIN = dict(left=3.5, bottom=3.8, right=3.6, top=3.8)


def plan_pins():
    """Pin positions in cell coordinates from io_ring.json: D rows, Q columns and the CK column."""
    ring = json.loads((ROOT / "Layout/design/io_ring.json").read_text(encoding="utf-8"))
    routes = ring["routes"]
    box = next(r for r in ring["reserved_regions"] if r["id"] == "output_register")["bbox"]
    if tuple(box[0]) != ORIGIN or box[1][0] - box[0][0] != DIE or box[1][1] - box[0][1] != DIE:
        raise ValueError("The output_register region changed")
    pins = {}
    for k in range(8):
        end = routes[f"ADC_D{k}"]["points_um"][-1]
        if end[0] != ORIGIN[0]:
            raise ValueError(f"ADC_D{k} does not end on the register's west edge")
        pins[f"D{k}"] = ("Left", "M3", 0.0, round(end[1] - ORIGIN[1], 3))
        start = routes[f"D{k}"]["points_um"][0]
        if start[1] != ORIGIN[1]:
            raise ValueError(f"D{k} does not start on the register's south edge")
        pins[f"Q{k}"] = ("Bottom", "M4", round(start[0] - ORIGIN[0], 3), 0.0)
    # CK: the north edge, under the SAMPLE route (y 514.4), west of the column the SAMPLE route turns at.
    pins["CK"] = ("Top", "M4", 20.0, DIE)
    return pins


def electrical():
    text = SOURCE.read_text(encoding="utf-8")
    m = re.search(r"(?ms)^subckt\s+" + CELL + r"\s+([^\n]*)\n(.*?)^ends\s+" + CELL, text)
    ports = m[1].split()
    if ports != PORTS + ["VDD", "VSS"]:
        raise ValueError("Port order of " + CELL + " changed")
    cells = {}
    for line in m[2].splitlines():
        line = line.split("//")[0].strip()
        if not line:
            continue
        inst = re.fullmatch(r"(\S+)\s+\(([^)]*)\)\s+(\S+)", line)
        name, nets, master = inst[1], inst[2].split(), inst[3]
        order = PINS[master] + ["VDD", "VSS"]
        if len(order) != len(nets):
            raise ValueError("Port count of " + name)
        cells[name] = dict(master=master, pins=dict(zip(order, nets)))
    drivers = {}
    for name, c in cells.items():
        for pin, net in c["pins"].items():
            if pin in OUTPUTS:
                if net in drivers:
                    raise ValueError(f"Net {net} has two drivers")
                drivers[net] = name
    loads = {n for c in cells.values() for p, n in c["pins"].items() if p not in OUTPUTS | {"VDD", "VSS"}}
    if (loads - set(drivers)) - set(INPUTS) or set(PORTS) - set(INPUTS) - set(drivers):
        raise ValueError("Undriven nets")
    return cells, hashlib.sha256(SOURCE.read_bytes()).hexdigest()


def verilog(cells):
    nets = sorted({n for c in cells.values() for p, n in c["pins"].items() if p not in ("VDD", "VSS")} - set(PORTS))
    lines = [f"module {CELL} (" + ", ".join(PORTS) + ");"]
    lines += [f"  {'input' if p in INPUTS else 'output'} {p};" for p in PORTS]
    lines += [f"  wire {n};" for n in nets]
    for name, c in sorted(cells.items()):
        pins = ", ".join(f".{p}({n})" for p, n in c["pins"].items() if p not in ("VDD", "VSS"))
        lines.append(f"  {c['master']} {name} ({pins});")
    return "\n".join(lines + ["endmodule", ""])


def route_script(pins):
    width, height = round(CORE_SITES * 0.14, 3), round(ROWS * 1.2, 3)
    m = MARGIN
    if abs(m["left"] + width + m["right"] - DIE) > 1e-6 or abs(m["bottom"] + height + m["top"] - DIE) > 1e-6:
        raise ValueError("Die size differs from the region")
    edit = "\n".join(f"editPin -pin {p} -side {side} -layer {layer} -assign {{{x} {y}}} -fixedPin 1 -snap USERGRID"
                     for p, (side, layer, x, y) in pins.items())
    return f"""set init_lef_file [list {TECH_LEF} {STD_LEF}]
set init_verilog core.v
set init_top_cell {CELL}
set init_pwr_net VDD
set init_gnd_net VSS
set init_design_settop 1
setMultiCpuUsage -localCpu 4
init_design
floorPlan -site core12T -s {width:.3f} {height:.3f} {m['left']} {m['bottom']} {m['right']} {m['top']}
globalNetConnect VDD -type pgpin -pin VDD -inst * -override
globalNetConnect VSS -type pgpin -pin VSS -inst * -override
addRing -nets {{VDD VSS}} -type core_rings -follow core -layer {{top M5 bottom M5 left M6 right M6}} -width 1.0 -spacing 0.4 -offset 0.4
addEndCap -preCap BOUNDARY_LEFT{SUFFIX} -postCap BOUNDARY_RIGHT{SUFFIX} -prefix ENDCAP
addWellTap -cell TAPCELL{SUFFIX} -cellInterval 14 -inRowOffset 1.4 -prefix WELLTAP
setPinAssignMode -pinEditInBatch true
{edit}
setPinAssignMode -pinEditInBatch false
setPlaceMode -place_global_cong_effort high
placeDesign
refinePlace
addStripe -nets {{VDD VSS}} -layer M6 -direction vertical -width 0.40 -spacing 0.40 -set_to_set_distance 7.0 -start_from left -start_offset 2.0 -stop_offset 2.0
sroute -connect {{corePin}} -nets {{VDD VSS}} -layerChangeRange {{M1 M6}} -allowJogging 0 -allowLayerChange 1 -crossoverViaLayerRange {{M1 M6}} -targetViaLayerRange {{M1 M6}}
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
streamOut overlay.gds -mapFile route.map -libName OREG_OVERLAY -units 1000 -mode ALL
puts "OREG_ROUTE_FINISHED"
exit
"""


def generate(revision):
    cells, digest = electrical()
    pins = plan_pins()
    out = WORK / revision
    out.mkdir(parents=True, exist_ok=False)
    (out / "core.v").write_text(verilog(cells), encoding="ascii", newline="\n")
    (out / "route.tcl").write_text(route_script(pins), encoding="ascii", newline="\n")
    record = dict(core=CELL, revision=revision, ports=PORTS, cell_count=len(cells), origin_um=list(ORIGIN),
                  die_um=[DIE, DIE], pins={k: list(v) for k, v in pins.items()},
                  source=dict(path=SOURCE.relative_to(ROOT).as_posix(), sha256=digest), cells=cells)
    write_json(out / "cells.json", record)
    return {k: v for k, v in record.items() if k != "cells"}


OUTPUT_FILES = ("routed.def", "overlay.gds", "route.conn", "route.drc", "route.geom", "place.rpt", "innovus.console")


def route(revision):
    c = config()
    local = WORK / revision
    remote = f"{c['remote_root']}/state/oreg-{revision}/route"
    q = shlex.quote
    subprocess.check_call(["ssh", c["host"], f"test ! -e {q(remote)} && mkdir -p {q(remote)}"], timeout=30)
    subprocess.check_call(["scp", "-q", str(local / "core.v"), str(local / "route.tcl"), f"{c['host']}:{remote}/"],
                          timeout=120)
    command = (f"cd {q(remote)} && tcsh -fc {q('source ' + INNOVUS + ' >& /dev/null; innovus -no_gui -no_logv -overwrite -init route.tcl >& innovus.console')}"
               " ; grep -q OREG_ROUTE_FINISHED innovus.console")
    rc = subprocess.call(["ssh", c["host"], command], timeout=1800)
    for name in OUTPUT_FILES:
        subprocess.call(["scp", "-q", f"{c['host']}:{remote}/{name}", str(local / name)], timeout=300)
    console = (local / "innovus.console").read_text(errors="replace") if (local / "innovus.console").exists() else ""
    drc = (local / "route.drc").read_text(errors="replace") if (local / "route.drc").exists() else ""
    geom = (local / "route.geom").read_text(errors="replace") if (local / "route.geom").exists() else ""
    summary = dict(revision=revision, remote=remote, returncode=rc,
                   errors=[l for l in console.splitlines() if l.startswith("**ERROR")],
                   drc_clean="No DRC violations were found" in drc,
                   geometry=geom.split("Total Violations :")[-1].strip()[:200],
                   def_sha256=hashlib.sha256((local / "routed.def").read_bytes()).hexdigest()
                   if (local / "routed.def").exists() else None)
    write_json(local / "route.json", summary)
    return summary


def reference(instances):
    """Transistor LVS source of the register; standard-cell bodies come from the installed SPICE."""
    from Layout.tools.physical.sar_se_def import NO_DEVICES
    rows = [f".SUBCKT {CELL} " + " ".join(PORTS + ["VDD", "VSS"])]
    for i in instances:
        short = i["master"].removesuffix(SUFFIX)
        if short in NO_DEVICES:
            continue
        order = PINS.get(i["master"], []) + ["VDD", "VSS"]
        rows.append(f"X{i['name']} " + " ".join(i["pins"][p] for p in order) + " " + i["master"])
    rows.append(f".ENDS {CELL}")
    return "\n".join(rows) + "\n"


def compare(route_dir, shapes, u):
    """XOR the rendered net geometry with the Innovus routing stream on every routing layer (gdstk; the SAR flow's
    sar_se_def.compare does the same with klayout)."""
    import gdstk
    from Layout.tools.physical.sar_se_def import ROUTE_LAYERS
    lib = gdstk.read_gds(str(route_dir / "overlay.gds"))
    top = lib.top_level()[0]
    flat = top.copy("flat").flatten()
    polygons = list(flat.polygons) + [q for path in flat.paths for q in path.to_polygons()]
    result = {}
    for lay, number in ROUTE_LAYERS.items():
        ref = [p for p in polygons if p.layer == number and p.datatype == 0]
        mine = [gdstk.rectangle((b[0] / u, b[1] / u), (b[2] / u, b[3] / u)) for rects in shapes.values()
                for layer, b in rects if layer == lay]
        ref_m = gdstk.boolean(ref, [], "or", precision=1e-4) if ref else []
        mine_m = gdstk.boolean(mine, [], "or", precision=1e-4) if mine else []
        diff = gdstk.boolean(ref_m, mine_m, "xor", precision=1e-4) if (ref_m or mine_m) else []
        result[lay] = dict(innovus_um2=sum(p.area() for p in ref_m), rendered_um2=sum(p.area() for p in mine_m),
                           xor_um2=sum(p.area() for p in diff), xor_polygons=len(diff))
    return result


def convert(revision):
    from Layout.tools.physical import sar_se_def as sd
    local = WORK / revision
    d, u, shapes, pins, power, instances, physical, design = sd.convert(local, local / "cells.json")
    check = compare(local, shapes, u)
    bad = {k: v for k, v in check.items() if v["xor_um2"] > 1e-9}
    if bad:
        raise SystemExit("Rendered routing differs from the Innovus stream on " + ", ".join(bad))
    # Innovus rounds the die width up to its M2 track grid (0.135 um pitch): 40.095 um for the 40 um request.
    if d["die"][:2] != [0, 0] or not (DIE * u <= d["die"][2] <= (DIE + 0.135) * u) or d["die"][3] != round(DIE * u):
        raise ValueError("Unexpected die " + str(d["die"]))
    ox, oy = ORIGIN

    def at(box):
        return [round(box[0] / u + ox, 4), round(box[1] / u + oy, 4), round(box[2] / u + ox, 4), round(box[3] / u + oy, 4)]

    pin_figures = {(n, p) for n, p in pins.items()}
    rects = []
    for net in sorted(shapes):
        for lay, box in shapes[net]:
            if (net, (lay, box)) in pin_figures:
                continue
            rects.append(dict(layer=lay, net=net, box=at(box)))
    terminals = [dict(net=name, direction="input" if name in INPUTS else "output",
                      pins=[dict(layer=lay, box=at(box))]) for name, (lay, box) in sorted(pins.items())]
    # Supply terminals on the ring: VDD on its south side (the DVDD route arrives at x 530 from the south), VSS on
    # its east side (the register VSS route leaves at y 480 to the east).
    ring = {net: [b for lay, b in shapes[net] if lay in ("M5", "M6") and max(b[2] - b[0], b[3] - b[1]) > 30 * u]
            for net in ("VDD", "VSS")}
    south = min((b for b in ring["VDD"] if b[2] - b[0] > 30 * u), key=lambda b: b[1], default=None)
    east = max((b for b in ring["VSS"] if b[3] - b[1] > 30 * u), key=lambda b: b[0], default=None)
    if south is None or east is None:
        raise ValueError("Ring sides not found: " + json.dumps({k: len(v) for k, v in ring.items()}))
    terminals += [dict(net="VDD", direction="inputOutput", pins=[dict(layer="M5", box=at(south))]),
                  dict(net="VSS", direction="inputOutput", pins=[dict(layer="M6", box=at(east))])]
    # The ring rectangles stay as drawing too; a pin figure on top of the same box is harmless.
    insts = [dict(lib=STD, cell=i["master"], name=i["name"], xy=[round(i["origin"][0] + ox, 4), round(i["origin"][1] + oy, 4)],
                  orient=i["orient"], nets={p: n for p, n in i["pins"].items()}) for i in instances]
    content = dict(cell=CELL, view="layout", instances=insts, rects=rects, terminals=terminals,
                   origin_um=list(ORIGIN))
    write_json(local / "content.json", content)
    (local / f"{CELL}.cdl").write_text(reference(instances), encoding="ascii", newline="\n")
    record = dict(cell=CELL, revision=revision, die_um=[DIE, DIE], origin_um=list(ORIGIN), instances=len(instances),
                  logic_cells=len(design["cells"]), physical_cells=physical, nets=len(shapes), rectangles=len(rects),
                  ring_boxes={k: len(v) for k, v in ring.items()},
                  def_sha256=hashlib.sha256((local / "routed.def").read_bytes()).hexdigest(),
                  stream_comparison=check)
    write_json(local / "convert.json", record)
    return {k: v for k, v in record.items() if k != "stream_comparison"}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=("generate", "route", "convert"))
    ap.add_argument("revision")
    a = ap.parse_args()
    print(json.dumps(dict(generate=generate, route=route, convert=convert)[a.action](a.revision), indent=1))


if __name__ == "__main__":
    main()
