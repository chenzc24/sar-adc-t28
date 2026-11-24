"""Export read-only LayoutML Core geometry from the recorded unfilled chip stream."""

import argparse
from collections import Counter
from functools import lru_cache
import gzip
import hashlib
import json
import math
from pathlib import Path
import re

import gdstk


SITE = Path(__file__).resolve().parent
TOP = "sar8_adc_chip"
LAYERS = [
    ((3, 0), "NW", "well"),
    ((6, 0), "OD", "active"),
    ((17, 0), "PO", "conductor"),
    ((25, 0), "PP", "implant"),
    ((26, 0), "NP", "implant"),
    ((30, 0), "CO", "cut"),
    # This 1P9M stream uses the thick-metal and pin purposes documented in toplevel_fill.py.
    *(((30 + n, 0), f"M{n}", "conductor") for n in range(1, 8)),
    ((38, 40), "M8", "conductor"),
    ((39, 60), "M9", "conductor"),
    *(((50 + n, 0), f"VIA{n}", "cut") for n in range(1, 7)),
    ((57, 40), "VIA7", "cut"),
    ((58, 60), "VIA8", "cut"),
    *(((130 + n, 0), f"M{n}.pin", "conductor") for n in range(1, 10)),
]
DRAWING = {spec: name for spec, name, _ in LAYERS}
LANDMARKS = {
    "sar8_io_ring": "IO ring",
    "sar8_adc_core": "ADC core",
    "sar8_cdac_with_xref": "CDAC and reference",
    "sar_bootstrap_flat_8b_p_core": "Bootstrap pair",
    "sar_strongarm_t28_core": "StrongARM",
    "sar8_se_core": "SAR controller",
    "sar8_out_reg": "Output register",
}
FILL = re.compile(r"^sar8_adc_core_fill5(?:_|$)|^sar8_cdac_fill_plan$|^sar_bootstrap_flat_8b_p_fill$")
VIA_MASTER = re.compile(r"M[2-9]_M[1-8]_CDNS_\d+")


def nm(value):
    scaled = value * 1000
    result = round(scaled)
    if not math.isclose(scaled, result, rel_tol=0, abs_tol=1e-4):
        raise ValueError(f"Coordinate is off the 1 nm source grid: {value}")
    return result


def point(x, y):
    return f"({x},{y})"


def bounds(box):
    if box is None:
        return None
    return [nm(v) for corner in box for v in corner]


def orientation(ref):
    quarter_turns = round(ref.rotation / (math.pi / 2))
    if ref.magnification != 1 or not math.isclose(ref.rotation, quarter_turns * math.pi / 2, abs_tol=1e-8):
        raise ValueError(f"Unsupported instance transform for {ref.cell_name}")
    return (('MX', 'MXR90', 'MY', 'MYR90') if ref.x_reflection else ('R0', 'R90', 'R180', 'R270'))[quarter_turns % 4]


def origin_and_array(ref):
    ox, oy = map(nm, ref.origin)
    offsets = ref.repetition.get_offsets()
    if not len(offsets):
        return [(ox, oy, "")]
    points = {(nm(x), nm(y)) for x, y in offsets}
    xs, ys = (sorted({p[axis] for p in points}) for axis in (0, 1))
    dx = xs[1] - xs[0] if len(xs) > 1 else 0
    dy = ys[1] - ys[0] if len(ys) > 1 else 0
    regular = len(points) == len(xs) * len(ys) and all(
        values[i] == values[0] + i * step for values, step in ((xs, dx), (ys, dy)) for i in range(len(values))
    )
    if regular and len(points) > 1:
        return [(ox + xs[0], oy + ys[0], f" array=({len(xs)},{len(ys)}) step=({dx},{dy})")]
    return [(ox + x, oy + y, "") for x, y in sorted(points)]


def polygon_line(poly):
    layer = DRAWING[poly.layer, poly.datatype]
    vertices = [(nm(x), nm(y)) for x, y in poly.points]
    if vertices and vertices[0] == vertices[-1]:
        vertices.pop()
    if len(vertices) < 3 or len(vertices) != len(set(vertices)):
        raise ValueError(f"Expected a simple source polygon on {layer}")
    if len(vertices) == 4:
        xs, ys = (sorted({p[axis] for p in vertices}) for axis in (0, 1))
        if len(xs) == len(ys) == 2:
            return f"rect {layer} {point(xs[0], ys[0])} {point(xs[1], ys[1])}"
    twice_area = 0
    for a, b in zip(vertices, vertices[1:] + vertices[:1]):
        dx, dy = abs(a[0]-b[0]), abs(a[1]-b[1])
        if dx and dy and dx != dy:
            raise ValueError(f"Off-angle source polygon on {layer}")
        twice_area += a[0]*b[1] - a[1]*b[0]
    if not twice_area:
        raise ValueError(f"Degenerate source polygon on {layer}")
    if twice_area < 0:
        vertices.reverse()
    points = " ".join(point(*p) for p in vertices)
    return f"polygon {layer} {points}"


def export(source, output):
    record = json.loads((SITE.parent / "Layout/results/chip_fill.json").read_text(encoding="utf-8"))
    expected = record["current"]["chip_stream"]["sha256"]
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    if source_sha != expected:
        raise ValueError("The GDS does not match the recorded unfilled r8 stream.")
    library = gdstk.read_gds(source)
    top = next(cell for cell in library.top_level() if cell.name == TOP)
    if (library.unit, library.precision) != (1e-6, 1e-9):
        raise ValueError("Expected micrometre user units and a 1 nm database grid.")
    if bounds(top.bounding_box()) != [nm(value) for value in record["current"]["die_um"]]:
        raise ValueError("The stream extent does not match the recorded die outline.")
    lines = ["layoutml 0.1 profile=core", "units user=1n dbu=1n grid=1n"]
    lines.extend(f"layer {name} gds={point(*spec)} kind={kind}" for spec, name, kind in LAYERS)
    lines.append("layer Footprint gds=(65535,65535) kind=marker fill=outline")
    cell_labels = {}
    written = set()
    excluded = set()
    shape_counts = Counter()
    cell_bounds = {}
    instance_records = 0
    names = {cell.name: f"C{index}" for index, cell in enumerate(library.cells)}

    @lru_cache(maxsize=None)
    def cell_box(cell):
        return bounds(cell.bounding_box())

    def visit(cell):
        nonlocal instance_records
        name = names[cell.name]
        if name in written:
            return
        written.add(name)
        owned = cell.name.startswith("sar")
        via = VIA_MASTER.fullmatch(cell.name)
        cell_labels[name] = cell.name if owned else "Generated via" if via else "Library cell"
        box = cell_box(cell)
        cell_bounds[name] = box
        lines.append(f"cell {name} {{")
        children = []
        if owned or via or cell.name == "PAD60GU":
            for poly in cell.get_polygons(depth=0):
                layer = DRAWING.get((poly.layer, poly.datatype))
                if not layer or (cell.name == "PAD60GU" and not layer.startswith("M")):
                    continue
                lines.append("  " + polygon_line(poly))
                shape_counts[layer] += 1
            for ref in cell.references:
                child = ref.cell
                if FILL.search(child.name) or child.name.startswith(("FILL", "PFILLER")):
                    excluded.add(child.name)
                    continue
                if cell_box(child) is None:
                    continue
                orient = orientation(ref)
                for x, y, array in origin_and_array(ref):
                    instance_records += 1
                    lines.append(f"  inst I{instance_records} of={names[child.name]} at={point(x, y)} orient={orient}{array}")
                children.append(child)
        elif box and box[0] < box[2] and box[1] < box[3]:
            lines.append(f"  rect Footprint {point(*box[:2])} {point(*box[2:])}")
            shape_counts["Footprint"] += 1
        lines.append("}")
        for child in children:
            visit(child)

    visit(top)
    missing = {name for name in ("M8", "M9", "VIA7", "VIA8") if not shape_counts[name]}
    if missing:
        raise ValueError(f"Missing 1P9M routing purposes: {', '.join(sorted(missing))}")
    lines.append(f"top {names[top.name]}")
    data = gzip.compress(("\n".join(lines) + "\n").encode(), mtime=0)
    release = {
        "stream": "chip-r8-b1-chk",
        "top": TOP,
        "source_sha256": source_sha,
        "geometry_sha256": hashlib.sha256(data).hexdigest(),
        "bounds_nm": cell_box(top),
        "cell_bounds_nm": cell_bounds,
        "cell_labels": cell_labels,
        "landmarks": {names[name]: label for name, label in LANDMARKS.items() if names.get(name) in written},
        "excluded_fill_cells": sorted(excluded),
        "gds_layer_purposes": {name: list(spec) for spec, name, _ in LAYERS},
        "shape_counts": shape_counts,
        "instance_records": instance_records,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "chip.core.lml.gz").write_bytes(data)
    (output / "release.json").write_text(json.dumps(release, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {len(written)} cells and {sum(shape_counts.values())} shapes from {release['stream']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gds", type=Path)
    parser.add_argument("--output", type=Path, default=SITE / "layout-data")
    args = parser.parse_args()
    export(args.gds, args.output)
