"""Convert the routed single-edge SAR DEF into net-bound OA build records.

Every rectangle carries its DEF net. The rendered metal and cuts are compared layer by
layer with the routing stream that Innovus wrote from the same database; any difference
stops the conversion. The LVS reference lists every placed cell that has devices.
"""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re

from Layout.design.sar_single_edge import CORE, PINS, STD, SUFFIX
from Layout.project import ROOT

LEF = ROOT / "work/layout/lef"
ORIENT = {"N": "R0", "S": "R180", "FN": "MY", "FS": "MX"}
ROUTE_LAYERS = {f"M{i}": 30 + i for i in range(1, 7)} | {f"VIA{i}": 50 + i for i in range(1, 6)}
# Physical-only cells have no devices; decaps are MOS capacitors and belong in the reference.
NO_DEVICES = ("TAPCELL", "BOUNDARY_LEFT", "BOUNDARY_RIGHT", "FILL2", "FILL3")
DECAPS = ("DCAP4", "DCAP8", "DCAP16")


def lef_tech(path):
    """Default routing widths and fixed via geometry in microns."""
    text = path.read_text(encoding="ascii", errors="replace")
    widths = {}
    for m in re.finditer(r"(?ms)^LAYER (\S+)\s*$(.*?)^END \1\b", text):
        if re.search(r"TYPE\s+ROUTING", m[2]):
            widths[m[1]] = float(re.search(r"(?m)^\s*WIDTH\s+([0-9.]+)", m[2])[1])
    vias = {}
    for m in re.finditer(r"(?ms)^VIA (\S+)[^\n]*$(.*?)^END \1\b", text):
        shapes, layer = [], None
        for line in m[2].splitlines():
            tok = line.split()
            if tok[:1] == ["LAYER"]:
                layer = tok[1]
            elif tok[:1] == ["RECT"]:
                shapes.append((layer, tuple(float(v) for v in tok[1:5])))
            elif tok[:1] == ["POLYGON"]:
                raise ValueError("Polygon via " + m[1])
        vias[m[1]] = shapes
    return widths, vias


def lef_sizes(path, masters):
    text = path.read_text(encoding="ascii", errors="replace")
    sizes = {}
    for name in masters:
        m = re.search(r"(?ms)^MACRO " + re.escape(name) + r"\s*$.*?^\s*SIZE ([0-9.]+) BY ([0-9.]+)", text)
        sizes[name] = (float(m[1]), float(m[2]))
    return sizes


def statements(section):
    return [s.strip() for s in section.split(";") if s.strip()]


def parse_def(path):
    text = path.read_text(encoding="ascii")
    units = int(re.search(r"UNITS DISTANCE MICRONS (\d+)", text)[1])
    die = [int(v) for v in re.search(r"DIEAREA \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)", text).groups()]

    def section(name):
        return re.search(r"(?ms)^" + name + r" \d+ ;(.*?)^END " + name, text)[1]

    components = {}
    for s in statements(section("COMPONENTS")):
        m = re.match(r"- (\S+) (\S+) (?:\+ SOURCE \S+ )?\+ (?:PLACED|FIXED) \( (-?\d+) (-?\d+) \) (\S+)", s)
        components[m[1]] = (m[2], int(m[3]), int(m[4]), m[5])
    pins = {}
    for s in statements(section("PINS")):
        m = re.match(r"- (\S+) \+ NET (\S+).*?\+ LAYER (\S+) \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)\s*"
                     r"\+ (?:FIXED|PLACED) \( (-?\d+) (-?\d+) \) (\S+)", s, re.S)
        pins[m[1]] = dict(net=m[2], layer=m[3], box=tuple(int(v) for v in m.groups()[3:7]),
                          at=(int(m[8]), int(m[9])), orient=m[10])
    generated = {}
    for s in statements(section("VIAS")):
        name = s.split()[1]
        fields = {f.split()[0]: f.split()[1:] for f in s.split("+")[1:]}
        generated[name] = fields
    special = statements(section("SPECIALNETS"))
    nets = statements(section("NETS"))
    return dict(units=units, die=die, components=components, pins=pins, generated=generated,
                special=special, nets=nets)


def generated_via(fields, units):
    bot, cut, top = fields["LAYERS"]
    cx, cy = (int(v) for v in fields["CUTSIZE"])
    sx, sy = (int(v) for v in fields.get("CUTSPACING", ["0", "0"]))
    ebx, eby, etx, ety = (int(v) for v in fields["ENCLOSURE"])
    rows, cols = (int(v) for v in fields.get("ROWCOL", ["1", "1"]))
    ox, oy = (int(v) for v in fields.get("ORIGIN", ["0", "0"]))
    obx, oby, otx, oty = (int(v) for v in fields.get("OFFSET", ["0", "0", "0", "0"]))
    if "PATTERN" in fields:
        raise ValueError("Via cut patterns are not supported")
    w, h = cols * cx + (cols - 1) * sx, rows * cy + (rows - 1) * sy
    x0, y0 = ox - w / 2, oy - h / 2
    shapes = [(cut, (x0 + c * (cx + sx), y0 + r * (cy + sy), x0 + c * (cx + sx) + cx, y0 + r * (cy + sy) + cy))
              for r in range(rows) for c in range(cols)]
    shapes.append((bot, (x0 - ebx + obx, y0 - eby + oby, x0 + w + ebx + obx, y0 + h + eby + oby)))
    shapes.append((top, (x0 - etx + otx, y0 - ety + oty, x0 + w + etx + otx, y0 + h + ety + oty)))
    return [(layer, tuple(v / units for v in box)) for layer, box in shapes]


def wiring(statement, units, widths, vias, special):
    """Rectangles in DEF units from one net's routing statements."""
    m = re.match(r"-\s+(\S+)", statement)
    net = m[1]
    body = statement.split("+ ROUTED", 1)
    if len(body) == 1:
        return net, []
    tokens = re.findall(r"\(|\)|[^\s()]+", body[1].replace("NEW", " NEW "))
    rects = []
    i, layer, width, last = 0, None, None, None

    def via(name, at):
        if not vias.get(name):
            raise ValueError("Unknown or empty via " + name)
        for lay, (a, b, c, d) in vias[name]:
            if lay in ROUTE_LAYERS:
                rects.append((lay, (at[0] + a * units, at[1] + b * units, at[0] + c * units, at[1] + d * units)))

    points = []

    def flush():
        for (p, ep), (q, eq) in zip(points, points[1:]):
            half = width / 2
            # Regular wires extend half a width past each point; special wires end flush.
            default = 0 if special else half
            e0 = default if ep is None else ep
            e1 = default if eq is None else eq
            if p[1] == q[1]:
                lo, hi = (p, q) if p[0] <= q[0] else (q, p)
                elo, ehi = (e0, e1) if p[0] <= q[0] else (e1, e0)
                rects.append((layer, (lo[0] - elo, p[1] - half, hi[0] + ehi, p[1] + half)))
            elif p[0] == q[0]:
                lo, hi = (p, q) if p[1] <= q[1] else (q, p)
                elo, ehi = (e0, e1) if p[1] <= q[1] else (e1, e0)
                rects.append((layer, (p[0] - half, lo[1] - elo, p[0] + half, hi[1] + ehi)))
            else:
                raise ValueError("Diagonal wire on " + net)
        points.clear()

    while i < len(tokens):
        t = tokens[i]
        if t == "NEW" or i == 0:
            flush()
            if t == "NEW":
                i += 1
            layer = tokens[i]
            i += 1
            width = widths[layer] * units
            if special and tokens[i].isdigit():
                width = int(tokens[i])
                i += 1
            last = None
            continue
        if t == "+":
            if tokens[i + 1] == "SHAPE":
                i += 3
                continue
            if tokens[i + 1] in ("USE", "SOURCE", "WEIGHT"):
                break
            raise ValueError(f"Unsupported wiring option {tokens[i + 1]} on {net}")
        if t == "(":
            x, y = tokens[i + 1], tokens[i + 2]
            x = last[0] if x == "*" else int(x)
            y = last[1] if y == "*" else int(y)
            ext = None
            if tokens[i + 3] != ")":
                ext = int(tokens[i + 3])
                i += 1
            last = (x, y)
            points.append((last, ext))
            i += 4
            continue
        if t == "RECT":
            dx0, dy0, dx1, dy1 = (int(tokens[i + k]) for k in (2, 3, 4, 5))
            rects.append((layer, (last[0] + dx0, last[1] + dy0, last[0] + dx1, last[1] + dy1)))
            i += 7
            continue
        if t == "VIRTUAL":
            flush()
            i += 5
            last = None
            continue
        via(t, last)
        i += 1
        if i < len(tokens) and tokens[i] in ORIENT:
            raise ValueError("Rotated via on " + net)
        # A path continues from the via on its other metal layer.
        flush()
        metals = [lay for lay, _ in vias[t] if lay.startswith("M") and lay != layer]
        if metals:
            layer = metals[0]
            if not special:
                width = widths[layer] * units
        points.append((last, None))
    flush()
    return net, [(lay, b) for lay, b in rects if b[2] > b[0] and b[3] > b[1]]


def rotate(box, orient):
    x0, y0, x1, y1 = box
    if orient == "E":
        return (y0, -x1, y1, -x0)
    if orient == "W":
        return (-y1, x0, -y0, x1)
    if orient == "N":
        return box
    if orient == "S":
        return (-x1, -y1, -x0, -y0)
    raise ValueError("Pin orientation " + orient)


def convert(route, cells_path):
    widths, fixed = lef_tech(LEF / "tsmcn28_9lm6X1Z1URDL.tlef")
    d = parse_def(route / "routed.def")
    u = d["units"]
    vias = {name: [(lay, tuple(v for v in box)) for lay, box in shapes] for name, shapes in fixed.items()}
    vias.update({name: generated_via(f, u) for name, f in d["generated"].items()})
    design = json.loads(cells_path.read_text())
    logic = design["cells"]
    sizes = lef_sizes(LEF / "tcbn28hpcplusbwp12t30p140.lef", {m for m, *_ in d["components"].values()})
    shapes = defaultdict(list)
    for s in d["special"]:
        net, rects = wiring(s, u, widths, vias, True)
        shapes[net] += rects
    for s in d["nets"]:
        net, rects = wiring(s, u, widths, vias, False)
        shapes[net] += rects
    pins = {}
    for name, p in d["pins"].items():
        x0, y0, x1, y1 = rotate(p["box"], p["orient"])
        box = (p["at"][0] + x0, p["at"][1] + y0, p["at"][0] + x1, p["at"][1] + y1)
        pins[name] = (p["layer"], box)
        shapes[p["net"]].append((p["layer"], box))
    instances, physical = [], defaultdict(int)
    for name, (master, x, y, orient) in sorted(d["components"].items()):
        w, h = (round(v * u) for v in sizes[master])
        ox, oy = {"N": (x, y), "FS": (x, y + h), "S": (x + w, y + h), "FN": (x + w, y)}[orient]
        short = master.removesuffix(SUFFIX)
        if name in logic:
            if logic[name]["master"] != master:
                raise ValueError("Placed master differs for " + name)
            binding = logic[name]["pins"]
        elif short in NO_DEVICES or short in DECAPS:
            binding = {"VDD": "VDD", "VSS": "VSS"}
            physical[short] += 1
        else:
            raise ValueError("Unexpected placed cell " + name)
        instances.append(dict(name=name, master=master, origin=[ox / u, oy / u], orient=ORIENT[orient], pins=binding))
    if {i["name"] for i in instances} & set(logic) != set(logic):
        raise ValueError("The DEF lost logical cells")
    # Power pins: the full height of each M6 stripe.
    power = {net: [b for lay, b in shapes[net] if lay == "M6" and b[3] - b[1] > 10 * u] for net in ("VDD", "VSS")}
    if not all(power.values()):
        raise ValueError("Missing M6 supply stripes")
    return d, u, shapes, pins, power, instances, dict(physical), design


def compare(route, shapes, u):
    """XOR the rendered net geometry with the Innovus routing stream on every routing layer."""
    from klayout import db

    ly = db.Layout()
    ly.read(str(route / "overlay.gds"))
    top = ly.top_cell()
    scale = 1 / ly.dbu / u
    result = {}
    for lay, num in ROUTE_LAYERS.items():
        idx = ly.find_layer(num, 0)
        ref = db.Region()
        if idx is not None:
            ref = db.Region(top.begin_shapes_rec(idx))
        mine = db.Region()
        for rects in shapes.values():
            for layer, b in rects:
                if layer == lay:
                    mine.insert(db.Box(*(round(v * scale) for v in b)))
        diff = (ref.merged() ^ mine.merged())
        result[lay] = dict(innovus_um2=ref.merged().area() * ly.dbu ** 2, rendered_um2=mine.merged().area() * ly.dbu ** 2,
                           xor_um2=diff.area() * ly.dbu ** 2, xor_polygons=diff.count())
    return result


def skill(instances, shapes, pins, power, u, die):
    lines = [f"DIE {die[2] / u} {die[3] / u}"]
    nets = sorted({n for i in instances for n in i["pins"].values()} | set(shapes))
    lines += [f"NET {n}" for n in nets]
    for i in instances:
        lines.append(f"INST {i['name']} {i['master']} {i['origin'][0]:.4f} {i['origin'][1]:.4f} {i['orient']} "
                     + " ".join(f"{p}={n}" for p, n in i["pins"].items()))
    # Pin figures are drawn by their PIN record; skip the identical routing copies.
    figures = {(name, p) for name, p in pins.items()} | {(net, ("M6", boxes[0])) for net, boxes in power.items()}
    off_grid = []
    for net in sorted(shapes):
        for lay, box in shapes[net]:
            if (net, (lay, box)) in figures:
                continue
            off_grid += [v for v in box if v % 10]
            a, b, c, e = box
            lines.append(f"RECT {lay} {net} {a / u:.4f} {b / u:.4f} {c / u:.4f} {e / u:.4f}")
    if off_grid:
        raise ValueError(f"{len(off_grid)} coordinates are off the 5 nm grid")
    for name, (lay, (a, b, c, e)) in sorted(pins.items()):
        lines.append(f"PIN {name} {lay} {a / u:.4f} {b / u:.4f} {c / u:.4f} {e / u:.4f}")
    for net, boxes in power.items():
        a, b, c, e = boxes[0]
        lines.append(f"PIN {net} M6 {a / u:.4f} {b / u:.4f} {c / u:.4f} {e / u:.4f}")
    return "\n".join(lines) + "\n"


def reference(design, instances):
    """Transistor LVS source of the macro; standard-cell bodies come from the installed SPICE."""
    ports = design["ports"] + ["VDD", "VSS"]
    rows = [f".SUBCKT {CORE} " + " ".join(ports)]
    for i in instances:
        short = i["master"].removesuffix(SUFFIX)
        if short in NO_DEVICES:
            continue
        order = PINS.get(i["master"], []) + ["VDD", "VSS"]
        rows.append(f"X{i['name']} " + " ".join(i["pins"][p] for p in order) + " " + i["master"])
    rows.append(f".ENDS {CORE}")
    return "\n".join(rows) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("revision")
    a = ap.parse_args()
    route = ROOT / "work/layout/sar-se" / a.revision
    d, u, shapes, pins, power, instances, physical, design = convert(route, route / "cells.json")
    check = compare(route, shapes, u)
    bad = {k: v for k, v in check.items() if v["xor_um2"] > 1e-9}
    (route / "build.txt").write_text(skill(instances, shapes, pins, power, u, d["die"]), encoding="ascii", newline="\n")
    (route / "sar-se-leaves.cdl").write_text(reference(design, instances), encoding="ascii", newline="\n")
    record = dict(core=CORE, library_cells=STD, die_um=[d["die"][2] / u, d["die"][3] / u],
                  instances=len(instances), logic_cells=len(design["cells"]), physical_cells=physical,
                  nets=len(shapes), rectangles=sum(len(v) for v in shapes.values()),
                  def_sha256=hashlib.sha256((route / "routed.def").read_bytes()).hexdigest(),
                  overlay_sha256=hashlib.sha256((route / "overlay.gds").read_bytes()).hexdigest(),
                  stream_comparison=check)
    (route / "convert.json").write_text(json.dumps(record, indent=1) + "\n", encoding="ascii", newline="\n")
    print(json.dumps({k: v for k, v in record.items() if k != "stream_comparison"}, indent=1))
    for k, v in check.items():
        print(k, {x: round(y, 6) if isinstance(y, float) else y for x, y in v.items()})
    if bad:
        raise SystemExit("Rendered routing differs from the Innovus stream on " + ", ".join(bad))


if __name__ == "__main__":
    main()
