"""Generate diffusion fill in legal channels between adjacent SAR resistor rows."""

import argparse
import itertools
import json
from hashlib import sha256
from math import isclose
from pathlib import Path

from klayout import db


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def fill_channels(core_path, utility_path, manifest_path, output):
    receipt = json.loads(manifest_path.read_text())
    if (
        digest(core_path) != receipt["source_gds_sha256"]
        or digest(utility_path) != receipt["steps"]["ODPO"]["gds_sha256"]
    ):
        raise ValueError(
            "Functional stream or foundry fill differs from the utility receipt"
        )
    core, utility = db.Layout(), db.Layout()
    core.read(str(core_path))
    utility.read(str(utility_path))
    if not isclose(core.dbu, utility.dbu, rel_tol=1e-12):
        raise ValueError("Mismatched stream units")
    scale = core.dbu

    def units(value):
        return round(value / scale)

    def shapes(layout, layer, datatype):
        idx = layout.find_layer(layer, datatype)
        return (
            db.Region()
            if idx is None
            else db.Region(layout.top_cell().begin_shapes_rec(idx)).merged()
        )

    resistors = [
        inst
        for inst in core.top_cell().each_inst()
        if inst.cell.name.split("_CDNS_")[0] == "rupolym"
    ]
    if len(resistors) != 10:
        raise ValueError("Expected ten physical delay resistors")
    rows = sorted(
        (inst.trans * inst.cell.bbox(core.layer(25, 0)) for inst in resistors),
        key=lambda b: b.bottom,
    )
    if any(row.empty() or row.width() <= row.height() for row in rows):
        raise ValueError("Resistor placement requires horizontal PP strips")
    gap, height, length = units(0.10), units(0.29), units(3.0)
    outline = core.top_cell().bbox()
    capacitor_edge = min(
        inst.bbox().left
        for inst in core.top_cell().each_inst()
        if inst.cell.name.startswith("cfmom_2t") and inst.bbox().bottom > rows[0].bottom
    )
    left, right = outline.left + gap, capacitor_edge - gap
    channels = db.Region()
    for lower, upper in itertools.pairwise(rows):
        channels.insert(db.Box(left, lower.top, right, upper.bottom))
    # Reserve resistor channels for the diffusion pattern before placing utility
    # fill. Remove whole fill polygons only, exclusively from the utility stream.
    native_masks = {
        (utility.get_info(idx).layer, utility.get_info(idx).datatype): shapes(
            utility, utility.get_info(idx).layer, utility.get_info(idx).datatype
        )
        for idx in utility.layer_indexes()
    }
    replaced = {}
    removed = {}
    for layer in (6, 17):
        pattern = native_masks.get((layer, 7), db.Region())
        conflict = pattern.inside(channels)
        if conflict.is_empty():
            continue
        keep = (pattern - conflict).merged()
        idx = utility.find_layer(layer, 7)
        for cell in utility.each_cell():
            cell.shapes(idx).clear()
        utility.top_cell().shapes(idx).insert(keep)
        removed[(layer, 7)] = conflict
        replaced[str(layer)] = conflict.area() * scale**2
    exclusion = db.Region()
    for layout in (core, utility):
        for layer, datatype, clearance in (
            (6, 0, 0.16),
            (6, 1, 0.16),
            (6, 7, 0.10),
            (17, 0, 0.05),
            (17, 1, 0.05),
            (17, 7, 0.05),
            (25, 0, 0.075),
            (30, 0, 0.10),
        ):
            exclusion += shapes(layout, layer, datatype).sized(units(clearance))
    well = shapes(core, 3, 0)
    exclusion += well.sized(units(0.10)) - well.sized(-units(0.10))
    resistor_marker = shapes(core, 117, 2)
    exclusion += resistor_marker.sized(units(0.075))
    for inst in core.top_cell().each_inst():
        if (
            inst.cell.name.startswith(("nch_", "pch_", "cfmom_"))
            or "BWP12T30P140" in inst.cell.name
        ):
            exclusion.insert(inst.bbox().enlarged(units(0.10)))
    exclusion.merge()
    emitted = db.Region()

    def fill_lane(y, avoid):
        lane = db.Region(db.Box(left, y, right, y + height))
        blocked = sorted(
            (p.bbox().left, p.bbox().right) for p in (lane & avoid).merged().each()
        )
        cursor = left
        for start, stop in blocked + [(right, right)]:
            for x in range(cursor, start, length + gap):
                end = min(x + length, start)
                if end - x >= units(0.32):
                    emitted.insert(db.Box(x, y, end, y + height))
            cursor = max(cursor, stop)

    for lower, upper in itertools.pairwise(rows):
        middle = (lower.top + upper.bottom) // 2
        if upper.bottom - lower.top < 2 * (height + units(0.075)) + gap:
            raise ValueError(
                "Insufficient dummy-diffusion channel between resistor rows"
            )
        for y in (middle - gap // 2 - height, middle + gap // 2):
            fill_lane(y, exclusion)
    # Use the legal empty ends of the bank and the shorter QUIET rows as well.
    avoid = (exclusion | emitted.sized(gap)).merged()
    bottom = rows[0].bottom - (rows[1].bottom - rows[0].bottom) // 2
    for y in range(bottom, outline.top - gap - height, height + gap):
        fill_lane(y, avoid)
    if emitted.is_empty() or not (emitted & exclusion).is_empty():
        raise ValueError("Invalid dummy diffusion coverage")
    output.mkdir(exist_ok=True, parents=True)
    utility.top_cell().shapes(utility.layer(6, 7)).insert(emitted)
    target = output / "resistor-odpo.gds"
    utility.write(str(target))
    check = db.Layout()
    check.read(str(target))
    for layer, original in native_masks.items():
        expected = original - removed.get(layer, db.Region())
        if layer == (6, 7):
            expected |= emitted
        if not (shapes(check, *layer) ^ expected).is_empty():
            raise ValueError(f"Unexpected mask change in resistor fill on {layer}")
    info = {
        "source_core_sha256": digest(core_path),
        "source_odpo_sha256": digest(utility_path),
        "completed_odpo_sha256": digest(target),
        "added_srdod_um2": emitted.area() * scale**2,
        "bars": emitted.count(),
        "replaced_native_fill_um2": replaced,
        "resistor_channels": len(rows) - 1,
    }
    (output / "resistor-odpo.json").write_text(json.dumps(info, indent=2) + "\n")
    return info


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("core", "odpo", "manifest", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    print(fill_channels(args.core, args.odpo, args.manifest, args.output))
