"""Place the active minimal reference driver against the saved CDAC access."""

import argparse
import hashlib
import json
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from Layout.design.cdac import PORTS as CDAC_PORTS
from Layout.design.sar_timing import ACCESS, STD, SUFFIX, WIDTH, sk
from Layout.project import ROOT, write_json
from tools.saradc.candidates import definitions
from tools.saradc.rnl import instances


DRIVER = "sar8_cdac_gate_driver"
COMBINED = "sar8_cdac_with_xref"
CDAC = "sar8j_r1_cdac"
CDAC_VIEW = "layout_paired_stacked"
LIBRARY = "SAR_ADC_T28_LAYOUT"
DRIVER_SOURCE = "design/xtor/reference/minimal_msb_d2.scs"
LOGIC_SOURCE = "design/xtor/common/standard_cells.scs"
SITE = 0.14
ROW_Y = -34.8
OUTPUT_Y = -32.25
BRANCH_Y = -28.2
SUPPLIES = {"VSS": (33.5, ROW_Y), "VDD": (35.2, ROW_Y + 1.2)}
NATIVE_PINS = {
    "INVD1": ["I", "ZN", "VDD", "VSS"],
    "INVD2": ["I", "ZN", "VDD", "VSS"],
    "ND2D1": ["A1", "A2", "ZN", "VDD", "VSS"],
}
PIN_ACCESS = {**ACCESS, "INVD2": {"I": (0.095, 0.575), "ZN": (0.370, 0.540)}}
SITE_WIDTH = {**WIDTH, "INVD2": 3, **{f"FILL{n}": n for n in (2, 3, 4, 8, 16, 32)}}


@dataclass(frozen=True)
class Cell:
    model: str
    nets: dict[str, str]

    @property
    def sites(self):
        return SITE_WIDTH[self.model]


def electrical(bits):
    """Expand the source gates and bind each documented current-probe alias."""
    paths = [ROOT / DRIVER_SOURCE, ROOT / LOGIC_SOURCE]
    source = {p.relative_to(ROOT).as_posix(): p.read_bytes() for p in paths}
    definition = {}
    for data in source.values():
        definition.update(definitions(data.decode("utf-8")))
    root = definition["sar8i_refword"]
    driver_inputs = [f"CODE{b}" for b in bits] + ["PRESET"]
    outputs = [f"G{s}N{b}" for s in "NP" for b in bits]
    available = set(driver_inputs + outputs + list(SUPPLIES))
    alias = {"RST_DONE": "VSS"}
    for name, (ports, child, _) in instances(root).items():
        if child == "iprobe" and name.startswith(("WNP", "WPP")):
            left, right = ports
            alias[right] = left
    expected = {f"G{s}P{b}": f"G{s}N{b}" for s in "NP" for b in range(8)}
    if {p: n for p, n in alias.items() if p.startswith("G")} != expected:
        raise ValueError("Active CDAC gate aliases differ from the layout interface")
    cells = {}

    def expand(path, model, nets):
        plain = model.removesuffix(SUFFIX)
        if plain in NATIVE_PINS:
            cells[path] = Cell(plain, dict(zip(NATIVE_PINS[plain], nets, strict=True)))
            return
        body = definition[model]
        binding = dict(zip(body.splitlines()[0].split()[2:], nets, strict=True))
        for name, (child_nets, child, _) in instances(body).items():
            expand(path + "__" + name, child, [binding.get(n, path + "__" + n) for n in child_nets])

    for name, (nets, child, _) in instances(root).items():
        if child == "iprobe":
            continue
        if name == "XPRESET_N":
            if bits == (7,):
                continue
        elif int(re.search(r"\d+$", name)[0]) not in bits:
            continue
        expand(name, child, [alias.get(net, net) for net in nets])
    used_top_nets = {n for c in cells.values() for n in c.nets.values()}
    if not available <= used_top_nets or len(cells) != (7 if bits == (7,) else 36):
        raise ValueError("Unexpected active driver topology or standard-cell count")
    return cells, driver_inputs, outputs, alias, {p: hashlib.sha256(b).hexdigest() for p, b in source.items()}


def saved_access():
    access = {}
    receipts = []
    target = f"{LIBRARY}/{CDAC}/{CDAC_VIEW}"
    for layer in ("M5", "M6"):
        args = ["oaq", "--saved", target, "shapes", "--layer", layer, "--limit", "150"]
        query = json.loads(subprocess.check_output(args, timeout=30))
        if query["status"] != "ok" or query["context"].get("cellview") != target.split("/"):
            raise ValueError(f"OA read failed for {layer}: {query.get('reasons')}")
        receipts.append({"context": query["context"], "layer": layer})
        for shape in query["figures"]:
            port = shape.get("net")
            if port in set(CDAC_PORTS) - {"TOPN", "TOPP"} and shape["type"] == "rect":
                if port in access:
                    raise ValueError(f"Multiple access rectangles for {port}")
                lo, hi = shape["bbox"]
                access[port] = [layer, *[round((a + b) / 2, 4) for a, b in zip(lo, hi, strict=True)]]
    if access.keys() != set(CDAC_PORTS) - {"TOPN", "TOPP"}:
        raise ValueError("Incomplete saved CDAC access")
    return access, receipts


def placement(cells, outputs, aliases, access):
    blocks = []
    assigned = set()
    for output in outputs:
        final = next(name for name, cell in cells.items() if cell.nets.get("ZN") == output)
        sinks = [port for port, canonical in aliases.items() if canonical == output]
        sinks.append(output)
        if len(sinks) != 2 or any(access[p][0] != "M6" for p in sinks):
            raise ValueError(f"Unexpected CDAC gate pair for {output}")
        x = sum(access[p][1] for p in sinks) / 2
        final_site = round((x - PIN_ACCESS[cells[final].model]["ZN"][0]) / SITE)
        if output.startswith("GNN"):
            pre = next(name for name, cell in cells.items() if cell.nets.get("ZN") == cells[final].nets["I"])
            blocks.append((final_site - cells[pre].sites, (pre, final)))
            assigned.add(pre)
        else:
            blocks.append((final_site, (final,)))
        assigned.add(final)

    control = tuple(sorted(
        (name for name in cells if name not in assigned),
        key=lambda name: (cells[name].model == "ND2D1", name),
    ))
    width = sum(cells[name].sites for name in control)
    blocks.append((round(34.4 / SITE - width / 2), control))
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

    for i, (net, contacts) in enumerate(sorted(lands.items())):
        y = ROW_Y - .6 - i * .25
        xs = [x for x, _ in contacts]
        east = right - .25 if net in inputs else max(xs)
        for x, py in contacts:
            route.wire(2, net, (x, py), (x, y), .07)
            route.via(2, net, x, y)
        route.wire(3, net, (min(xs), y), (east, y), .08)
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
        route.wire(6, net, (x, y), (x, BRANCH_Y), .16)
        for port in targets:
            _, px, py = access[port]
            route.call("stCheckPin", "XCDAC", port, 6, px, py)
            route.wire(6, net, (x, BRANCH_Y), (px, BRANCH_Y), .16)
            route.wire(6, net, (px, BRANCH_Y), (px, py), .16)
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
