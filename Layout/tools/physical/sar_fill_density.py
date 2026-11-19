"""Complete the standalone SAR M9 window with the minimum number of native fill tiles."""

import argparse
import hashlib
import json
from math import ceil, hypot
from pathlib import Path

from klayout import db
from Layout.tools.analysis.check_sar_timing import readback


def separation(a, b):
    dx = max(0, a.left - b.right, b.left - a.right)
    dy = max(0, a.bottom - b.top, b.bottom - a.top)
    return hypot(dx, dy)


def complete(fill, native, output):
    config = json.loads((fill / "manifest.json").read_text())
    source = fill / "metal.gds"
    if hashlib.sha256(source.read_bytes()).hexdigest() != config["steps"]["metal"]["gds_sha256"]:
        raise ValueError("Native utility stream digest differs")
    layout = db.Layout()
    layout.read(str(source))
    top = layout.top_cell()
    scale = layout.dbu
    bounds = config["boundary_um"]
    die = db.Box(*(round(bounds[k] / scale) for k in ("xLB", "yLB", "xRT", "yRT")))
    layer = layout.find_layer(39, 61)
    existing = db.Region(top.begin_shapes_rec(layer)).merged()
    boxes = [p.bbox() for p in existing.each()]
    shapes = {(b.width(), b.height()) for b in boxes}
    if len(shapes) != 1 or sum(b.area() for b in boxes) != existing.area():
        raise ValueError("The native M9 utility did not generate identical rectangular tiles")
    w, h = shapes.pop()
    # 20% is the installed M9.DN.3 threshold. The 125-um window encloses this complete macro.
    count = max(0, ceil((die.area() / 5 - existing.area()) / (w * h)))
    _, instances, _, _, _ = readback(native / "sar-readback.txt")
    resistors = [
        db.Box(*(round(a / scale) for a in p[4])) for p in instances.values() if p[1] == "rupolym"
    ]
    grid = round(0.1 / scale)
    margin = round(0.40 / scale)
    minimum_spacing = round(3.005 / scale)
    xs = range(die.left + margin, die.right - margin - w + 1, grid)
    ys = range(die.bottom + margin, die.top - margin - h + 1, grid)
    candidates = []
    for y in ys:
        for x in xs:
            box = db.Box(x, y, x + w, y + h)
            if all(not box.overlaps(r) for r in resistors):
                candidates.append(box)
    additions = []
    for _ in range(count):
        chosen = max(candidates, key=lambda box: min(separation(box, other) for other in boxes))
        if min(separation(chosen, other) for other in boxes) < minimum_spacing:
            raise ValueError("Insufficient free M9 space for an existing utility tile")
        additions.append(chosen)
        boxes.append(chosen)
        top.shapes(layer).insert(chosen)
    output.mkdir(parents=True, exist_ok=True)
    layout.write(str(output / "metal.gds"))
    expected = db.Region()
    for b in additions:
        expected.insert(b)
    result = db.Region(top.begin_shapes_rec(layer)).merged()
    if not ((existing ^ result) ^ expected).is_empty():
        raise ValueError("Unexpected M9 geometry delta")
    data = dict(
        layer=[39, 61],
        source=config["source_evidence"],
        source_metal_sha256=config["steps"]["metal"]["gds_sha256"],
        completed_metal_sha256=hashlib.sha256((output / "metal.gds").read_bytes()).hexdigest(),
        bounds_um=[die.left * scale, die.bottom * scale, die.right * scale, die.top * scale],
        minimum_pct=20,
        before_pct=100 * existing.area() / die.area(),
        after_pct=100 * result.area() / die.area(),
        added_rectangles_um=[
            [round(x * scale, 3) for x in (b.left, b.bottom, b.right, b.top)] for b in additions
        ],
    )
    (output / "density.json").write_text(json.dumps(data, indent=2) + "\n")
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("fill", "native", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    print(json.dumps(complete(args.fill, args.native, args.output), indent=2))
