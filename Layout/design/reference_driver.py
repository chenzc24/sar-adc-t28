"""Place the single-edge D2 reference driver against the saved CDAC access."""

import argparse
import hashlib
import json
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from Layout.design.cdac import PORTS as CDAC_PORTS
from Layout.design.sar_single_edge import PINS, SITES, STD, SUFFIX
from Layout.project import ROOT, write_json
from tools.saradc.candidates import definitions
from tools.saradc.refsel import REFERENCE_PORTS, SELECTS
from tools.saradc.rnl import instances


DRIVER = "sar8i_refword"
COMBINED = "sar8_cdac_with_xref"
CDAC = "sar8j_r1_cdac"
CDAC_VIEW = "layout_paired_stacked"
LIBRARY = "SAR_ADC_T28_LAYOUT"
DRIVER_SOURCE = "design/xtor/reference/single_edge_d2.scs"
SITE = 0.14
ROW_Y = -29.1
OUTPUT_Y = -27.4
SUPPLIES = {"VSS": (33.5, ROW_Y), "VDD": (35.2, ROW_Y + 1.2)}
PIN_ACCESS = {
    "BUFFD1": {"I": (.13, .55), "Z": (.37, .54)},
    "BUFFD2": {"I": (.11, .55), "Z": (.51, .54)},
    "INVD1": {"I": (.07, .695), "ZN": (.21, .695)},
    "INVD2": {"I": (.095, .575), "ZN": (.37, .54)},
    "ND2D1": {"A1": (.25, .425), "A2": (.09, .64), "ZN": (.37, .54)},
}
NATIVE_PINS = {m: PINS[m + SUFFIX] + ["VDD", "VSS"] for m in PIN_ACCESS}
SITE_WIDTH = {**{m: SITES[m + SUFFIX] for m in PIN_ACCESS},
              "TAPCELL": 4, "BOUNDARY_LEFT": 3, "BOUNDARY_RIGHT": 3,
              **{f"FILL{n}": n for n in (2, 3, 4, 8, 16, 32)}}


def sk(value):
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, (list, tuple)):
        return "list(" + " ".join(sk(v) for v in value) + ")"
    return f"{value:.4f}"


@dataclass(frozen=True)
class Cell:
    model: str
    nets: dict[str, str]

    @property
    def sites(self):
        return SITE_WIDTH[self.model]


def electrical(bits):
    """Bind the shared schematic selects to the verified physical pin names."""
    source = (ROOT / DRIVER_SOURCE).read_bytes()
    if 'include "' + DRIVER_SOURCE.removeprefix("design/") + '"' not in (ROOT / "design/dut.scs").read_text():
        raise ValueError("DUT no longer uses the single-edge D2 reference")
    root = definitions(source.decode())["sar8i_refword"]
    driver_inputs = [f"CODE{b}" for b in bits] + ["PRESET"]
    outputs = [f"G{s}N{b}" for s in "NP" for b in bits]
    available = set(driver_inputs + outputs + list(SUPPLIES))
    parts = instances(root)
    alias = {f"G{s}P{b}": f"G{s}N{b}" for s in "NP" for b in range(8)}
    physical = dict(zip(SELECTS, (f"G{s}N{b}" for s in "NP" for b in range(8)), strict=True))
    cells = {}

    for name, (nets, child, _) in parts.items():
        if name == "XPRESET_N":
            if bits == (7,):
                continue
        elif int(re.search(r"\d+", name)[0]) not in bits:
            continue
        model = child.removesuffix(SUFFIX)
        cells[name] = Cell(model, dict(zip(NATIVE_PINS[model], (physical.get(n, n) for n in nets), strict=True)))
    used_top_nets = {n for c in cells.values() for n in c.nets.values()}
    if not available <= used_top_nets or len(cells) != (6 if bits == (7,) else 28):
        raise ValueError("Unexpected active driver topology or standard-cell count")
    if bits == tuple(range(8)):
        if tuple(root.splitlines()[0].split()[2:]) != REFERENCE_PORTS:
            raise ValueError("Physical projection differs from the source interface")
    return cells, driver_inputs, outputs, alias, {DRIVER_SOURCE: hashlib.sha256(source).hexdigest()}


def saved_access():
    access = {}
    receipts = []
    target = f"{LIBRARY}/{CDAC}/{CDAC_VIEW}"
    names = [p for p in CDAC_PORTS if p not in ("TOPN", "TOPP")]
    query = json.loads(subprocess.check_output(["oaq", "--saved", target, "pins", *names], timeout=120))
    if query["status"] != "ok" or query["context"]["cellview"] != target.split("/"):
        raise ValueError(f"Saved CDAC lookup failed: {query.get('reasons')}")
    receipts.append(query["context"])
    for entry in query["pins"]:
        fig, = entry["figures"]
        port = entry["terminal"]
        layer = "M6" if port.startswith("G") else "M5"
        if entry["status"] != "ok" or fig["lpp"] != [layer, "drawing"] or fig["type"] != "rect":
            raise ValueError(f"Unexpected landing on {port}")
        lo, hi = fig["bbox"]
        access[port] = [layer, *[round((a + b) / 2, 4) for a, b in zip(lo, hi, strict=True)]]
    if access.keys() != set(CDAC_PORTS) - {"TOPN", "TOPP"}:
        raise ValueError("Incomplete saved CDAC access")
    return access, receipts


def placement(cells, outputs, aliases, access):
    blocks = []
    for output in outputs:
        final, = [name for name, cell in cells.items() if output in cell.nets.values()]
        cell = cells[final]
        out_pin, = [p for p, n in cell.nets.items() if n == output]
        other, = [p for p, n in aliases.items() if n == output]
        x = (access[other][1] + access[output][1]) / 2
        final_site = round((x - PIN_ACCESS[cell.model][out_pin][0]) / SITE)
        bit = int(output[-1])
        decode = []
        if output.startswith("GPN"):
            if bit == 7:
                if "XPRESET_N" in cells:
                    decode.append("XPRESET_N")
                decode.extend(["XINITIAL7_A", "XINITIAL7_B", "XINITIAL7", "XINV7"])
            else:
                decode.append(f"XINITIAL{bit}")
        # The NAND ZN and the following inverter I would otherwise put
        # their M2-to-M3 cuts 0.12 um apart. Break that abutment by two sites.
        group = [*decode, final]
        gap_sites = 2 * sum(cells[n].model == "ND2D1" for n in decode)
        site = final_site - sum(cells[n].sites for n in decode) - gap_sites
        for n in group:
            blocks.append((site, (n,)))
            site += cells[n].sites + (2 if cells[n].model == "ND2D1" else 0)
    if sorted(n for _, group in blocks for n in group) != sorted(cells):
        raise ValueError("Each active cell must have one placement")
    blocks.sort()
    placed = {}

    def support(site, model):
        placed[f"ROW_{model}_{site}"] = (site, Cell(model, {"VDD": "VDD", "VSS": "VSS"}))
        return site + SITE_WIDTH[model]

    def fill(start, stop):
        gap = stop - start
        if gap < 0 or gap == 1:
            raise ValueError(f"Illegal standard-cell row gap of {gap} sites at {start}")
        if gap >= 36:
            middle = start + (gap - 4) // 2
            fill(start, middle)
            start = support(middle, "TAPCELL")
        while start < stop:
            remaining = stop - start
            sites = next(n for n in (32, 16, 8, 4, 3, 2) if n <= remaining and remaining - n != 1)
            start = support(start, f"FILL{sites}")

    left = blocks[0][0] - 7
    stop = support(support(left, "BOUNDARY_LEFT"), "TAPCELL")
    for start, group in blocks:
        fill(stop, start)
        for name in group:
            placed[name] = (start, cells[name])
            start += cells[name].sites
        stop = start
    right = support(support(stop, "TAPCELL"), "BOUNDARY_RIGHT")
    return placed, (left * SITE, right * SITE)


class Route:
    def __init__(self):
        self.lines = []
        self.length = defaultdict(float)
        self.vias = set()

    def call(self, function, *args):
        self.lines.append(function + "(cv " + " ".join(sk(value) for value in args) + ")")

    def rect(self, layer, net, x, y, w, h):
        self.call("stRect", f"M{layer}", net, x - w / 2, y - h / 2, x + w / 2, y + h / 2)

    def wire(self, layer, net, a, b, width):
        ax, ay = a
        bx, by = b
        dx, dy = abs(bx - ax), abs(by - ay)
        if min(dx, dy) > 1e-6:
            raise ValueError(f"Non-Manhattan route on {net}")
        if max(dx, dy) < 1e-6:
            return
        cap = max(0.055, width / 2)
        w = max(dx + 2 * cap, 0.25) if dx > dy else width
        h = max(dy + 2 * cap, 0.25) if dy > dx else width
        self.rect(layer, net, (ax + bx) / 2, (ay + by) / 2, w, h)
        self.length[net] += dx + dy

    def via(self, lower, net, x, y, horizontal=0):
        key = (lower, round(x, 4), round(y, 4), net)
        if key in self.vias:
            return
        self.vias.add(key)
        if lower <= 3:
            self.call("stVia", lower, net, x, y, horizontal)
        else:
            self.call("refUpperVia", lower, net, x, y)

    def stack(self, lower, upper, net, x, y, power=False):
        for level in range(lower, upper):
            for offset in (-.065, .065) if power else (0.,):
                self.via(level, net, x + offset, y)
        for level in range(lower + 1, upper):
            self.rect(level, net, x, y, .26 if power else .24, .16)

    def pin(self, net, layer, x, y, w, h, direction):
        self.call("refPin", net, f"M{layer}", x, y, w, h, direction)


def driver_layout(cells, inputs, outputs, alias, access):
    placed, (left, right) = placement(cells, outputs, alias, access)
    route = Route()
    nets = sorted({n for _, cell in placed.values() for n in cell.nets.values()})
    route.lines.extend(f"dbCreateNet(cv {sk(name)})" for name in nets)
    lands = defaultdict(list)
    for name, (site, cell) in placed.items():
        x = site * SITE
        route.call("stDevice", name, STD, cell.model + SUFFIX, x, ROW_Y, "R0",
                   (), tuple(cell.nets.items()))
        for terminal, (dx, dy) in PIN_ACCESS.get(cell.model, {}).items():
            net = cell.nets[terminal]
            px, py = x + dx, ROW_Y + dy
            route.call("stCheckPin", name, terminal, 1, px, py)
            route.via(1, net, px, py)
            lands[net].append((px, py))
        if cell.model == "TAPCELL":
            for net, (_, y) in SUPPLIES.items():
                route.call("stCheckPin", name, net, 1, x + .28, y)
                route.stack(1, 4, net, x + .28, y, power=True)
    for net, (x, y) in SUPPLIES.items():
        route.wire(4, net, (left + .08, y), (right - .08, y), .24)
        route.pin(net, 4, x, y, .32, .24, "inputOutput")

    output_pins = {}
    for name in outputs:
        ((px, py),) = lands.pop(name)
        other = next(port for port, net in alias.items() if net == name)
        x = round((access[name][1] + access[other][1]) / 2, 4)
        route.wire(2, name, (px, py), (px, OUTPUT_Y), .07)
        route.via(2, name, px, OUTPUT_Y)
        route.rect(3, name, (px + x) / 2, OUTPUT_Y, abs(px - x) + .24, .16)
        route.length[name] += abs(px - x)
        route.stack(3, 6, name, x, OUTPUT_Y)
        route.pin(name, 6, x, OUTPUT_Y, .16, .44, "output")
        output_pins[name] = [x, OUTPUT_Y]

    # Input access is on the SAR-facing east edge. Pack disjoint M3 spans
    # onto common tracks, including enough clearance for pads and via enclosure.
    spans = []
    for net, contacts in lands.items():
        xs = [x for x, _ in contacts]
        east = right - .25 if net in inputs else max(xs)
        spans.append((min(xs), east, net, contacts))

    # Preserve the full SAR's observed bottom-to-top CODE0..7, PRESET bus
    # order. Internal nets can share the unused west part of each input track.
    # The isolated two-input pilot has no eight-bit bus to escape.
    bus = dict(zip(reversed(inputs), range(len(inputs)))) if len(inputs) > 2 else {}
    track_limits = [next(w for w, _, n, _ in spans if n == net) for net in bus]
    track_ends = [float("-inf")] * len(bus)
    for west, east, net, contacts in sorted(spans):
        if net in bus:
            track = bus[net]
        else:
            track = next((i for i, end in enumerate(track_ends)
                          if west - end >= .42 and track_limits[i] - east >= .42), len(track_ends))
            if track == len(track_ends):
                track_limits.append(float("inf"))
                track_ends.append(east)
            else:
                track_ends[track] = east
        y = ROW_Y - .45 - track * .22
        for x, py in contacts:
            route.wire(2, net, (x, py), (x, y), .07)
            route.via(2, net, x, y)
        route.wire(3, net, (west, y), (east, y), .08)
        if net in inputs:
            route.pin(net, 3, east, y, .28, .10, "input")
    return route, output_pins


def combined_layout(driver_ports, outputs, alias, access, output_pins, view):
    route = Route()
    cdac_binding = {p: alias.get(p, p) if alias.get(p) in outputs else p for p in CDAC_PORTS}
    combined_ports = [p for p in driver_ports if p not in outputs]
    combined_ports += [p for p in CDAC_PORTS if p not in SUPPLIES and cdac_binding[p] not in outputs]
    nets = set(combined_ports) | set(outputs)
    route.lines.extend(f"dbCreateNet(cv {sk(name)})" for name in sorted(nets))
    route.call("refChild", DRIVER, view, "XREF", tuple((p, p) for p in driver_ports))
    route.call("refChild", CDAC, CDAC_VIEW, "XCDAC", tuple(cdac_binding.items()))
    branches = {}
    for net, (x, y) in output_pins.items():
        targets = [p for p, n in cdac_binding.items() if n == net]
        route.call("stCheckPin", "XREF", net, 6, x, y)
        # The CDAC gate pair ends on one M6 line. Join the two actual
        # landing centers there, so no parallel pair of feed wires is needed.
        landing_rows = {access[p][2] for p in targets}
        if len(targets) != 2 or len(landing_rows) != 1:
            raise ValueError(f"Cannot form a direct M6 tee for {net}")
        branch_y, = landing_rows
        if net in ("GNN0", "GPN0"):
            # On B0 each gate pair straddles both native M6 reference trunks.
            # Clear the southern end of the VREFP drop before fanning out.
            branch_y = access["VREFP"][2] - .46
        route.wire(6, net, (x, y), (x, branch_y), .16)
        for port in targets:
            _, px, py = access[port]
            route.call("stCheckPin", "XCDAC", port, 6, px, py)
            route.wire(6, net, (x, branch_y), (px, branch_y), .16)
            route.wire(6, net, (px, branch_y), (px, py), .16)
            branches[port] = round(abs(y - py) + abs(px - x), 4)
    for net, (x, y) in SUPPLIES.items():
        _, px, py = access[net]
        route.call("stCheckPin", "XCDAC", net, 5, px, py)
        route.call("stCheckPin", "XREF", net, 4, x, y)
        if net == "VDD":
            route.wire(5, net, (px, py), (x, py), .26)
            for offset in (-.065, .065):
                route.via(5, net, x, py + offset)
        # The VSS trunk overlaps the existing pair of M5–M6 cuts at x=33.435/33.565.
        route.stack(4, 6, net, x, y, power=True)
        route.wire(6, net, (x, y), (x, py), .28)
        route.pin(net, 6, x, y, .28, .44, "inputOutput")
    for port in combined_ports:
        if port in SUPPLIES:
            continue
        is_input = port in driver_ports
        direction = "input" if is_input or port.startswith("G") else "inputOutput"
        route.call("refCopyPin", "XREF" if is_input else "XCDAC", port, direction)
    return route, cdac_binding, combined_ports, branches


def generate(out, *, pilot, view, saved=None):
    bits = (7,) if pilot else tuple(range(8))
    cells, inputs, outputs, alias, hashes = electrical(bits)
    if saved:
        data = json.loads(saved.read_text(encoding="utf-8"))
        access, receipts = data["cdac_access"], data["oa_queries"]
    else:
        access, receipts = saved_access()
    driver_ports = inputs + outputs + list(SUPPLIES)
    driver, output_pins = driver_layout(cells, inputs, outputs, alias, access)
    combined, cdac_binding, combined_ports, branches = combined_layout(
        driver_ports, outputs, alias, access, output_pins, view
    )
    out.mkdir(parents=True, exist_ok=False)
    script = ['load("reference_driver.il")', "procedure(refBuild() let((cv)"]
    for name, route in ((DRIVER, driver), (COMBINED, combined)):
        script.extend([f"cv=refOpen({sk(name)} {sk(view)})", *route.lines, "refSave(cv)"])
    script.extend(['printf("REFERENCE_BUILD_OK\\n") t))',
                   "if(errset(refBuild() t) then exit(0) else exit(1))"])
    (out / "build.il").write_text("\n".join(script) + "\n", encoding="ascii")
    definitions_cdl = [f".SUBCKT {DRIVER} " + " ".join(driver_ports)]
    for name, cell in cells.items():
        definitions_cdl.append(name + " " + " ".join(cell.nets[p] for p in NATIVE_PINS[cell.model]) + " " + cell.model + SUFFIX)
    definitions_cdl.extend([
        f".ENDS {DRIVER}",
        f".SUBCKT {COMBINED} " + " ".join(combined_ports),
        "XREF " + " ".join(driver_ports) + f" {DRIVER}",
        "XCDAC " + " ".join(cdac_binding[p] for p in CDAC_PORTS) + f" {CDAC}",
        f".ENDS {COMBINED}",
    ])
    (out / "driver-leaves.cdl").write_text("\n".join(definitions_cdl) + "\n", encoding="ascii")
    write_json(out / "intent.json", {
        "view": view, "bits": bits, "driver": DRIVER, "top": COMBINED, "cdac": CDAC,
        "cdac_view": CDAC_VIEW, "driver_ports": driver_ports, "combined_ports": combined_ports,
        "cdac_pin_binding": cdac_binding, "cdac_access": access, "oa_queries": receipts,
        "source_sha256": hashes, "standard_cell_count": len(cells), "branch_um": branches,
        "driver_signal_wire_um": round(sum(n for net, n in driver.length.items() if net not in SUPPLIES), 4),
        "combined_gate_wire_um": round(sum(combined.length[n] for n in outputs), 4),
        "driver_vias": len(driver.vias), "combined_vias": len(combined.vias),
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("identity")
    parser.add_argument("--view", required=True)
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("--saved-access", type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,55}", args.identity) or not re.fullmatch(r"layout_[a-z0-9_]+", args.view):
        parser.error("Use a unique job identity and a fresh named layout view")
    generate(ROOT / "work/layout/reference-driver" / args.identity, pilot=args.pilot,
             view=args.view, saved=args.saved_access)
