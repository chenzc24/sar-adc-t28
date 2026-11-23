"""Chip-level fill of the SAR ADC chip by owner (chenzc24/sar-adc-t28#12, Layout/specs/fill-policy.md "Chip level").

One pass of the installed foundry OD/PO and metal utilities (Layout/tools/physical/toplevel_fill_physical.py, the same
private job edits as every module and core fill, dummy TCD off) over the IO ring opening, on a seed that is the chip
stream plus one exclusion cell, bounded by the seal ring keep-out. Owners that keep their own fill or no fill:

- the filled ADC core (`sar8_adc_core_filled`, which holds the pair and core fill, and the Bootstraps' own cells):
  all layers over its outline;
- the IO ring cells (pads, fillers, corners, power cuts): all layers over each cell outline up to revision 6. From
  revision 7 the utility fills inside them too (IO rows and the strip under the pads), with its own IO dummy types:
  the foundry deck excludes neither IO cells nor bond pads from the minimum-density rules, and revisions 1-6 left
  every IO-band density result open;
- the seal ring: no fill outside the band plus 3 um, (-39, -39)-(799, 799) on the 892 um die, or in the four corner
  triangles;
- the ESD clamps (`PCLAMPC_V_G` from layout_full_fill5_r8_seal, `PCLAMPC_H_G` before; IO-library masters): all
  layers over each instance, and over the pair clamp's
  feed straps;
- the output register macro (Innovus fillers and taps inside): M1-M3 over its outline and OD/PO over its standard-cell
  rows; from revision 2 the top level fills M4-M9 over it and OD/PO in its pin margin (Mx.DN.7 and PO.DN.3.1 of
  revision 1 there);
- VINN/VINP chip routes: all layers within 1 um of every route shape, as the core's TOP exclusions;
- VREFP/VREFN chip routes (stiff, double-bonded reference): their layer and the layers directly above and below
  within 1 um, as the core's comparator channel; OD/PO and other metal layers are filled.

The pad decaps and the rest of the opening are filled like the core's decap regions. `library` writes the fill
hierarchy `sar8_chip_fill<n>` (children ACH<n>*), `wrapper-gds` the wrapper `sar8_adc_chip_filled` (XCHIP, FILL and the chip
top's texts) as a stream, and `build` the same wrapper in OA (new names only, the chip view read only).
"""
import argparse
import base64
import json
import math
from pathlib import Path
import shlex
import subprocess

from Layout.design import toplevel_fill as tf
from Layout.design.toplevel_route import CADENCE, IDENTITY, STANDARD_LIBRARY, sk, ssh
from Layout.project import ROOT, config, write_json

WORK = ROOT / "work/layout/chip-fill"
CHIP, CHIP_VIEW = "sar8_adc_chip", "layout_full_fill5_r8_seal"   # 892 um die, PCLAMPC_V_G clamps, one PRCUTA_G per cut
# AVSS pad landings with the pad M1 fingers extended (layout_full_fill5_r5_seal, ESD.CD.1gU): M1/VIA1 boxes in the
# 2.4 um landing band outside the IO-cell outlines; no M1/M2 fill within LANDING_MARGIN of them.
AVSS_LANDINGS = ((432.14, 649.0, 447.86, 650.2), (109.8, 252.14, 111.0, 267.86),
                 (649.0, 612.14, 650.2, 627.86), (109.8, 612.14, 111.0, 627.86))
LANDING_MARGIN = 0.5
# The pair clamp's AVDD_CORE/AVSS_CORE feed straps run outside its region (M8 at y 260-284, M9 at y 296-320,
# x 123.5-216.5; layout_full_fill5_r4_seal), so its exclusion covers them too (chip-objects session, 2026-11-23).
CLAMP_FEED = ((120.0, 255.0, 220.0, 325.0),)
# Only M8/M9 straps (and their M7-side vias) run there; revision 4 excluded every layer and left the strips
# without OD/PO (PO.DN.3, PO.DN.3.1, OD.DN.3, OD.S.14 there). From revision 5: M7-M9 only.
CLAMP_FEED_LAYERS = (7, 8, 9)
WRAPPER = "sar8_adc_chip_filled"
REVISION, FILL_TOP, PREFIX = "fill1", "sar8_chip_fill1", "ACH1"
OWNER = "Layout/design/chip_fill.py"
OPENING = (73.05, 73.05, 686.95, 686.95)      # inner edge of the IO fillers (pads and corners reach 110 um)
# 892 um die from layout_full_fill5_r7_seal (sar8_seal_ring_892 at (-66, -66); 1000 um before: N28_TSMC_SRDMB_Mu at
# (-120, -120), die to 880, bounds -93..853, fill revisions 1-5): no fill outside
# the seal-ring band plus 3 um (CSR_DMu_S_1), and none in the four corner triangles x+y <= 125 um of each die corner.
DIE = (-66.0, -66.0, 826.0, 826.0)
BOUNDS = (-39.0, -39.0, 799.0, 799.0)
CORNER_CUT = 125.0
TILE = 100.0                  # verify works tile by tile
CORE_BOX = (363.885, 449.0, 485.885, 560.0)
CLAMP_MASTERS = ("PCLAMPC_V_G", "PCLAMPC_H_G")
RING = "sar8_io_ring"
IO_CELL_PREFIXES = ("P",)   # every TSMC IO cell name starts with P (PAD60GU, PDB3AC_*, PFILLER*, PCORNER*, ...)
OUT_REG = "sar8_out_reg"
REG_METAL = (1, 2, 3)          # the register macro routes signals on M1-M3; M4-M6 hold only its sparse straps
PR_BOUNDARY = 108
ROUTE_MARGIN = 1.0
CONTENTS = ("content_asm_a3.json", "content_f5r3.json")   # chip route rects with nets (chip-asm-a3, chip-f5r3-b1 builds)
VIN, VREF = ("VINN", "VINP"), ("VREFP", "VREFN")
IO_LIBRARY_PDK = "/home/process/tsmc28n/PDK_mmWave/iPDK_CRN28HPC+ULL_v1.8_2p2a_20190531/tsmcN28"


def use_revision(n):
    global REVISION, FILL_TOP, PREFIX
    REVISION, FILL_TOP, PREFIX = f"fill{n}", f"sar8_chip_fill{n}", f"ACH{n}"


def route_rects(nets, contents=CONTENTS):
    out = []
    for name in contents:
        d = json.loads((WORK / "inputs" / name).read_text())
        out += [(r["layer"], tuple(r["box"])) for r in d["rects"] if r["net"] in nets and r["layer"].startswith("M")]
    return out


def instance_boxes(top, masters):
    """Die-frame bounding boxes of every instance of the masters directly under top or one level below it."""
    g = tf.gds()

    def bbox(ref, outer=None):
        t = g.Cell("T")
        t.add(g.Reference(ref.cell, ref.origin, ref.rotation, ref.magnification, ref.x_reflection))
        if outer is not None:
            t2 = g.Cell("T2")
            t2.add(g.Reference(t, outer.origin, outer.rotation, outer.magnification, outer.x_reflection))
            t = t2
        (x0, y0), (x1, y1) = t.bounding_box()
        return (x0, y0, x1, y1)
    boxes = []
    for r in top.references:
        if r.cell.name in masters:
            boxes.append(bbox(r))
        else:
            boxes += [bbox(i, r) for i in r.cell.references if i.cell.name in masters]
    return boxes


def io_cell_boxes(top):
    """Outlines of every IO-library cell of the ring (pads, fillers, corners, power cuts), die frame."""
    g = tf.gds()
    ring = next(r for r in top.references if r.cell.name == RING)
    boxes = []
    for i in ring.cell.references:
        if i.cell.name.startswith(IO_CELL_PREFIXES):
            t = g.Cell("T")
            t.add(g.Reference(i.cell, i.origin, i.rotation, i.magnification, i.x_reflection))
            (x0, y0), (x1, y1) = t.bounding_box()
            boxes.append((x0 + ring.origin[0], y0 + ring.origin[1], x1 + ring.origin[0], y1 + ring.origin[1]))
    return boxes


def exclusions(top):
    """[(box, layers)] in die coordinates; see the module docstring."""
    rects = [(CORE_BOX, tf.ALL)]
    if int(REVISION[4:]) < 7:
        rects += [(b, tf.ALL) for b in io_cell_boxes(top)]
    rects += [(b, tf.ALL) for b in instance_boxes(top, CLAMP_MASTERS)]
    rects += [(b, CLAMP_FEED_LAYERS) for b in CLAMP_FEED]
    rects += [(tf.bloat(b, LANDING_MARGIN), (1, 2)) for b in AVSS_LANDINGS]
    reg = [r for r in top.references if r.cell.name == OUT_REG]
    for r in reg:
        t = tf.gds().Cell("T")
        t.add(tf.gds().Reference(r.cell, r.origin))
        (x0, y0), (x1, y1) = t.bounding_box()
        rects.append(((x0, y0, x1, y1), REG_METAL))
        rows = [q for q in t.get_polygons() if q.layer == PR_BOUNDARY]   # standard-cell outlines
        rx0 = min(q.bounding_box()[0][0] for q in rows); ry0 = min(q.bounding_box()[0][1] for q in rows)
        rx1 = max(q.bounding_box()[1][0] for q in rows); ry1 = max(q.bounding_box()[1][1] for q in rows)
        rects.append(((rx0, ry0, rx1, ry1), ("OD", "PO")))
    rects += [(tf.bloat(box, ROUTE_MARGIN), tf.ALL) for layer, box in route_rects(VIN)]
    # The reference is stiff and double-bonded: floating M9 over its M8 bars is allowed (revision 5), the route layer
    # and the one below stay excluded.
    rects += [(tf.bloat(box, ROUTE_MARGIN), tuple(n for n in tf.adjacent(int(layer[1:])) if n < 9 or int(layer[1:]) == 9))
              for layer, box in route_rects(VREF)]
    return rects


def corner_polygons():
    """The four seal-ring corner triangles (die frame) in which no fill may land."""
    g = tf.gds()
    x0, y0, x1, y1 = DIE
    c = CORNER_CUT
    return [g.Polygon([(x0, y0), (x0 + c, y0), (x0, y0 + c)]), g.Polygon([(x1, y0), (x1 - c, y0), (x1, y0 + c)]),
            g.Polygon([(x0, y1), (x0 + c, y1), (x0, y1 - c)]), g.Polygon([(x1, y1), (x1 - c, y1), (x1, y1 - c)])]


def corner_exclusions():
    g = tf.gds()
    out = []
    for p in corner_polygons():
        for n in tf.ALL:
            lt = tf.ODBLK if n == "OD" else tf.POBLK if n == "PO" else tf.EXCL[n]
            q = p.copy()
            q.layer, q.datatype = lt
            out.append(q)
    return out


# M9.DN.3 (125 um windows, >= 20 %) next to the core: the core keeps M9 off the CDAC array and out of the Bootstrap
# cells, so windows that reach into it fail with utility fill alone (15.8-19.0 % in revision 4; the utility's 3 x 3 um
# squares reach about 25 % of free area). From revision 5 the top level draws planned dummy M9 stripes there instead:
# 3 um wide, 3 um apart, 3-30 um long (each row's free intervals split evenly) (DM9.W.1/W.2, DM9.S.1, DM9.A.2), 3 um clear of drawn M9 (DM9.S.2) and
# of every M9 exclusion. The utility's M9 is blocked only 3 um around each stripe, so it still fills the gaps the
# 30 um stripes do not fit (a blanket block over the band left those empty: 15.4 % predicted in one window).
M9_BAND = (255.0, 380.0, 567.5, 630.0)
# From revision 7 also a frame along the inner edge of the IO ring: the 125 um windows from x or y 59 to 184 (and 559
# to 684) reach onto the IO cells, so the opening part needs about 28 % M9 (utility squares give 23.9-25.3 %).
# GDS trial chip-se1-drc: every side window 20-32 %, no DM9 or M9 rule.
M9_FRAME = ((113.0, 113.0, 647.0, 184.0), (113.0, 559.0, 647.0, 647.0), (113.0, 184.0, 184.0, 559.0),
            (559.0, 184.0, 647.0, 559.0))
M9_STRIPE = dict(w=3.0, s=3.0, l=30.0)
DM9_TO_MX = 3.0


def m9_band_exclusion(stripes):
    """DM9EXCL for the utility pass: each planned stripe, 3 um larger."""
    return [(tf.bloat(r, DM9_TO_MX), (9,)) for r in stripes]


def planned_m9(chip):
    """Planned dummy M9 rectangles (39;61) in M9_BAND (and M9_FRAME from revision 7), clear of drawn M9, of every M9
    exclusion and of each other (bands in order)."""
    g = tf.gds()
    # 3 um clear of every M9 exclusion too: other owners' dummy M9 (the core's, at its edge) needs DM9.S.1 spacing.
    blocked = [g.rectangle(*((b[0], b[1]), (b[2], b[3])))
               for b in (tf.bloat(b, DM9_TO_MX) for b, layers in exclusions(chip) if 9 in layers)]
    blocked += corner_polygons()
    drawn = chip.get_polygons(layer=39, datatype=60) + chip.get_polygons(layer=139, datatype=0)
    keep_out = g.boolean(blocked, g.offset(drawn, DM9_TO_MX) if drawn else [], "or")
    st = M9_STRIPE
    grid = 0.005
    out = []
    for band in (M9_BAND,) + (M9_FRAME if int(REVISION[4:]) >= 7 else ()):
        new = stripes(g, band, keep_out, st, grid)
        out += new
        keep_out = keep_out + [g.rectangle((r[0] - DM9_TO_MX, r[1] - DM9_TO_MX), (r[2] + DM9_TO_MX, r[3] + DM9_TO_MX))
                               for r in new]
    return out


def stripes(g, band, keep_out, st, grid):
    x0, y0, x1, y1 = band
    out = []
    y = y0
    # Row by row: the keep-out's x extent within the row blocks it; each free interval gets stripes of equal length,
    # at most st["l"], at least st["w"] (DM9.A.1 9 um2), st["s"] apart.
    while y + st["w"] <= y1:
        row = [g.rectangle((x0, y), (x1, y + st["w"]))]
        cut = [q for q in keep_out if q.bounding_box()[0][1] < y + st["w"] and q.bounding_box()[1][1] > y]
        spans = sorted((q.bounding_box()[0][0], q.bounding_box()[1][0]) for q in g.boolean(row, cut, "and")) if cut else []
        free, at = [], x0
        for a, b in spans:
            if a > at:
                free.append((at, a))
            at = max(at, b)
        if at < x1:
            free.append((at, x1))
        for a, b in free:
            a, b = math.ceil(a / grid - 1e-6) * grid, math.floor(b / grid + 1e-6) * grid
            length = b - a
            if length < st["w"]:
                continue
            n = math.ceil((length + st["s"]) / (st["l"] + st["s"]) - 1e-9)
            seg = math.floor((length - st["s"] * (n - 1)) / n / grid + 1e-6) * grid
            for k in range(n):
                xa = a + k * (seg + st["s"])
                out.append((round(xa, 3), round(y, 3), round(xa + seg, 3), round(y + st["w"], 3)))
        y += st["w"] + st["s"]
    return out


def seed(identity, chip_gds):
    g = tf.gds()
    lib, top = tf.read_stream(chip_gds, CHIP)
    rects = exclusions(top)
    blk = g.Cell(f"{PREFIX}_CHIP_BLOCK")
    if int(REVISION[4:]) >= 5:
        rects = rects + m9_band_exclusion(planned_m9(top))
    blk.add(*tf.exclusion_rects(rects), *corner_exclusions())
    lib.add(blk)
    top.add(g.Reference(blk))
    out = WORK / identity
    digest = tf.save(lib, out)
    summary = dict(identity=identity, chip=dict(path=str(chip_gds), sha256=tf.sha(Path(chip_gds).read_bytes())),
                   seed_gds_sha256=digest, bounds_um=BOUNDS, corner_cut_um=CORNER_CUT,
                   exclusions=[dict(box=[round(v, 4) for v in b], layers=[str(n) for n in layers]) for b, layers in rects])
    write_json(out / "seed.json", summary)
    return summary


def library(identity, chip_gds, fill_dir):
    """The fill hierarchy FILL_TOP in die coordinates: the pass's OD/PO and metal fill and the exclusion cell."""
    g = tf.gds()
    lib = g.Library(unit=1e-6, precision=1e-9)
    top = g.Cell(FILL_TOP)
    lib.add(top)
    names = {}
    for kind, pre in (("ODPO", "CO"), ("metal", "CM")):
        c = tf.import_fill(lib, Path(fill_dir) / kind / "fill.gds", CHIP if kind == "ODPO" else CHIP + "_DM",
                           f"{FILL_TOP}_{kind.lower()}", PREFIX + pre + "_")
        if c is not None:
            top.add(g.Reference(c))
            names[kind.lower()] = c.name
    _, chip = tf.read_stream(chip_gds, CHIP)
    if int(REVISION[4:]) >= 5:
        m9 = g.Cell(f"{FILL_TOP}_m9")
        m9.add(*[g.rectangle(r[:2], r[2:], layer=39, datatype=61) for r in planned_m9(chip)])
        lib.add(m9)
        top.add(g.Reference(m9))
        names["m9"] = m9.name
    excl = g.Cell(f"{FILL_TOP}_excl")
    excl.add(*tf.exclusion_rects(exclusions(chip)), *corner_exclusions())
    lib.add(excl)
    top.add(g.Reference(excl))
    names["excl"] = excl.name
    out = WORK / identity
    digest = tf.save(lib, out, "fill_library.gds")
    cells = sorted(c.name for c in lib.cells)
    if not all(c == FILL_TOP or c.startswith((FILL_TOP + "_", PREFIX)) for c in cells):
        raise ValueError("Unexpected cell name in the fill library")
    area = {}
    for p in top.get_polygons():
        k = f"{p.layer}/{p.datatype}"
        area[k] = area.get(k, 0) + p.area()
    summary = dict(identity=identity, library_gds_sha256=digest, top=FILL_TOP, masters=names, cells=len(cells),
                   area_um2_by_layer={k: round(v, 3) for k, v in sorted(area.items())})
    write_json(out / "library.json", summary)
    (out / "cells.txt").write_text("\n".join(cells) + "\n")
    return summary


def allowed(box, margin=0.0):
    """True if the box, grown by margin, lies inside BOUNDS and clear of the four corner triangles of DIE."""
    (x0, y0), (x1, y1) = box
    x0, y0, x1, y1 = x0 - margin, y0 - margin, x1 + margin, y1 + margin
    b, d, c = BOUNDS, DIE, CORNER_CUT
    if x0 < b[0] - 1e-6 or y0 < b[1] - 1e-6 or x1 > b[2] + 1e-6 or y1 > b[3] + 1e-6:
        return False
    return min(x0 - d[0] + y0 - d[1], d[2] - x1 + y0 - d[1], x0 - d[0] + d[3] - y1, d[2] - x1 + d[3] - y1) >= c - 1e-6


def clip(identity, library_id, chip_gds):
    """A fill library for a smaller die: library_id's fill without every element outside the current BOUNDS and corners.

    Nothing is reshaped or added: a leaf element (reference element or polygon) either stays where it was or is
    dropped, so every spacing to drawn geometry, exclusions and the seal ring stays as checked or grows. Crossing
    arrays are split into the elements that stay. Nested masters are each used once, untransformed, in the source
    library and get clipped copies (new cells: removing elements from a cell in place is quadratic in gdstk). The
    exclusion cell is rebuilt for the new die; the cells get this revision's names."""
    g = tf.gds()
    src = json.loads((WORK / library_id / "library.json").read_text())
    old = g.read_gds(str(WORK / library_id / "fill_library.gds"))
    cells = {c.name: c for c in old.cells}
    old_top = src["top"]
    old_prefix = "ACH" + old_top.rsplit("fill", 1)[1]
    rename = lambda n: FILL_TOP + n[len(old_top):] if n.startswith(old_top) else PREFIX + n[len(old_prefix):]
    users = {}
    for c in old.cells:
        for r in c.references:
            users[r.cell.name] = users.get(r.cell.name, 0) + 1
    # The utility draws dummy vias (5x;1) as their own elements on dummy metal lines (3x;1). A via is kept only if it is
    # one metal-line length clear of the edge, so a via never outlives the line under or over it (DMn.EN.2, DVIAn.*).
    is_via = lambda c: bool(c.polygons) and not c.references and all(51 <= q.layer <= 58 and q.datatype == 1 for q in c.polygons)
    line = [c.bounding_box() for c in old.cells if not c.references and c.polygons
            and all(31 <= q.layer <= 38 and q.datatype == 1 for q in c.polygons)]
    via_margin = max(max(b[1][0] - b[0][0], b[1][1] - b[0][1]) for b in line)
    dropped = dict(elements=0, polygons=0)
    lib = g.Library(unit=1e-6, precision=1e-9)
    leaves = {}

    def leaf(cell):
        if cell.name not in leaves:
            cell.name = rename(cell.name)
            leaves[cell.name] = cell
            lib.add(cell)
        return cell

    def walk(cell, dx, dy):
        new = g.Cell(rename(cell.name))
        polys = [q for q in cell.polygons
                 if allowed(tuple((x + dx, y + dy) for x, y in q.bounding_box()),
                            via_margin if 51 <= q.layer <= 58 and q.datatype == 1 else 0.0)]
        dropped["polygons"] += len(cell.polygons) - len(polys)
        new.add(*polys)
        for r in cell.references:
            if r.cell.references:
                if users[r.cell.name] != 1 or r.rotation or r.x_reflection or r.magnification != 1 or r.repetition.size > 1:
                    raise ValueError("Nested fill master used more than once or transformed: " + r.cell.name)
                new.add(g.Reference(walk(r.cell, dx + r.origin[0], dy + r.origin[1]), r.origin))
                continue
            m = via_margin if is_via(r.cell) else 0.0
            (a, b), (c, d) = r.bounding_box()
            if allowed(((a + dx, b + dy), (c + dx, d + dy)), m):
                ref = g.Reference(leaf(r.cell), r.origin, r.rotation, r.magnification, r.x_reflection)
                ref.repetition = r.repetition
                new.add(ref)
                continue
            (a, b), (c, d) = g.Reference(r.cell, r.origin, r.rotation, r.magnification, r.x_reflection).bounding_box()
            offsets = r.repetition.get_offsets() if r.repetition.size > 1 else [(0.0, 0.0)]
            kept = [(ox, oy) for ox, oy in offsets if allowed(((a + ox + dx, b + oy + dy), (c + ox + dx, d + oy + dy)), m)]
            dropped["elements"] += len(offsets) - len(kept)
            if kept:
                ref = g.Reference(leaf(r.cell), (r.origin[0] + kept[0][0], r.origin[1] + kept[0][1]), r.rotation,
                                  r.magnification, r.x_reflection)
                if len(kept) > 1:   # explicit offsets: the origin itself is implied
                    ref.repetition = g.Repetition(offsets=[(ox - kept[0][0], oy - kept[0][1]) for ox, oy in kept[1:]])
                new.add(ref)
        lib.add(new)
        return new

    top = g.Cell(FILL_TOP)
    for r in cells[old_top].references:
        if not r.cell.name.endswith("_excl"):
            top.add(g.Reference(walk(r.cell, 0.0, 0.0)))
    _, chip = tf.read_stream(chip_gds, CHIP)
    excl = g.Cell(FILL_TOP + "_excl")
    excl.add(*tf.exclusion_rects(exclusions(chip)), *corner_exclusions())
    top.add(g.Reference(excl))
    lib.add(top, excl)
    out = WORK / identity
    digest = tf.save(lib, out, "fill_library.gds")
    names = sorted(c.name for c in lib.cells)
    if not all(c == FILL_TOP or c.startswith((FILL_TOP + "_", PREFIX)) for c in names):
        raise ValueError("Unexpected cell name in the fill library")
    area = {}
    for q in top.get_polygons():
        k = f"{q.layer}/{q.datatype}"
        area[k] = area.get(k, 0) + q.area()
    summary = dict(identity=identity, clipped_from=library_id, source_library_gds_sha256=src["library_gds_sha256"],
                   die_um=DIE, bounds_um=BOUNDS, corner_cut_um=CORNER_CUT, via_margin_um=via_margin, dropped=dropped, library_gds_sha256=digest,
                   top=FILL_TOP, masters={k: FILL_TOP + v[len(old_top):] for k, v in src["masters"].items()},
                   cells=len(names), area_um2_by_layer={k: round(v, 3) for k, v in sorted(area.items())})
    write_json(out / "library.json", summary)
    (out / "cells.txt").write_text("\n".join(names) + "\n")
    return summary


def verify(library_id, chip_gds):
    """No fill on a drawn shape of its layer anywhere, and every exclusion empty on its layers."""
    g = tf.gds()
    _, top = tf.read_stream(WORK / library_id / "fill_library.gds", FILL_TOP)
    fill = {}
    for r in top.references:
        if r.cell.name.endswith("_excl"):
            continue
        t = g.Cell("T")
        t.add(g.Reference(r.cell))
        for p in t.get_polygons():
            k = tf.fill_layer(p)
            if k is not None:
                fill.setdefault(k, []).append(p)
    _, chip = tf.read_stream(chip_gds, CHIP)
    drawn = {}
    for p in chip.get_polygons():
        dummy = p.datatype in (1, 7, 41, 61) and p.layer < 100
        k = "OD" if (p.layer, p.datatype) == (6, 0) else "PO" if (p.layer, p.datatype) == (17, 0) else \
            None if dummy or p.layer in (6, 17) else tf.LAYER_OF.get((p.layer, p.datatype))
        if k is not None:
            drawn.setdefault(k, []).append(p)

    rects = exclusions(chip)
    boxes = lambda k: [g.rectangle(b[:2], b[2:]) for b, layers in rects if k in layers]
    opening = g.boolean([g.rectangle(BOUNDS[:2], BOUNDS[2:])], corner_polygons(), "not")

    def tiles(polys):
        """Polygons bucketed by the TILE um tiles their bounding boxes touch (whole-chip booleans run out of memory)."""
        out = {}
        for p in polys:
            (x0, y0), (x1, y1) = p.bounding_box()
            for i in range(int((x0 - DIE[0]) // TILE), int((x1 - DIE[0]) // TILE) + 1):
                for j in range(int((y0 - DIE[1]) // TILE), int((y1 - DIE[1]) // TILE) + 1):
                    out.setdefault((i, j), []).append(p)
        return out

    def area(a, b):
        """Area of a AND b, tile by tile, each tile clipped to its own square so nothing is counted twice."""
        if not a or not b:
            return 0.0
        ta, tb, total = tiles(a), tiles(b), 0.0
        for key, pa in ta.items():
            pb = tb.get(key)
            if not pb:
                continue
            x, y = DIE[0] + key[0] * TILE, DIE[1] + key[1] * TILE
            sq = [g.rectangle((x, y), (x + TILE, y + TILE))]
            total += sum(q.area() for q in g.boolean(g.boolean(pa, sq, "and"), g.boolean(pb, sq, "and"), "and"))
        return round(total, 6)
    out = dict(library=library_id, fill_polygons={str(k): len(v) for k, v in fill.items()},
               overlap_with_drawn_um2={str(k): area(v, drawn.get(k, [])) for k, v in fill.items()},
               fill_in_exclusions_um2={str(k): area(v, boxes(k)) for k, v in fill.items()},
               fill_outside_opening_um2={str(k): round(sum(p.area() for p in v) - area(v, opening), 6)
                                         for k, v in fill.items()})
    out["pass"] = max(v for key in ("overlap_with_drawn_um2", "fill_in_exclusions_um2", "fill_outside_opening_um2")
                      for v in out[key].values()) <= 1e-6
    write_json(WORK / library_id / "verify.json", out)
    return out


def wrapper_gds(identity, library_id, chip_gds):
    g = tf.gds()
    lib, chip = tf.read_stream(chip_gds, CHIP)
    _, fill = tf.read_stream(WORK / library_id / "fill_library.gds", FILL_TOP)
    cells = [fill] + list(fill.dependencies(True))
    if {c.name for c in lib.cells} & ({c.name for c in cells} | {WRAPPER}):
        raise ValueError("Cell name collision between the chip stream and the fill library")
    lib.add(*cells)
    top = g.Cell(WRAPPER)
    top.add(g.Reference(chip), g.Reference(fill))
    top.add(*[g.Label(l.text, l.origin, l.anchor, l.rotation, l.magnification, l.x_reflection, l.layer, l.texttype)
              for l in chip.labels])
    lib.add(top)
    out = WORK / identity
    digest = tf.save(lib, out, "wrapper.gds")
    summary = dict(identity=identity, wrapper=WRAPPER, chip_gds_sha256=tf.sha(Path(chip_gds).read_bytes()),
                   library=library_id, labels=len(chip.labels), gds_sha256=digest)
    write_json(out / "wrapper.json", summary)
    return summary


def build(identity, library_id, chip_view, view=None, expect_chip_oa=None):
    """strmin the fill library (new cells only) and create WRAPPER/<view> under the layout lock; the chip view is
    opened read only and its layout.oa digest is compared before and after."""
    view = view or "layout_" + REVISION
    out = WORK / library_id
    cells = (out / "cells.txt").read_text().split()
    blob = (out / "fill_library.gds").read_bytes()
    if tf.sha(blob) != json.loads((out / "library.json").read_text())["library_gds_sha256"]:
        raise ValueError("Fill library differs from its record")
    cfg = config()
    q = shlex.quote
    lib = sk(cfg["library"])
    skill = "\n".join([
        'procedure(acfNeed(ok message) unless(ok error("%s\\n" message)))',
        "procedure(acfBuild()",
        " let((dd chip fill cv inst n)",
        f"  dd=ddGetObj({lib})",
        f"  acfNeed(dd && dd~>readPath=={sk(cfg['library_path'])} \"Wrong layout library\")",
        f"  acfNeed(!ddGetObj({lib} {sk(WRAPPER)} {sk(view)}) \"Wrapper view exists\")",
        f"  chip=dbOpenCellViewByType({lib} {sk(CHIP)} {sk(chip_view)} \"maskLayout\" \"r\")",
        "  acfNeed(chip \"Missing chip view\")",
        f"  fill=dbOpenCellViewByType({lib} {sk(FILL_TOP)} \"layout\" \"maskLayout\" \"r\")",
        "  acfNeed(fill \"Missing fill hierarchy\")",
        f"  cv=dbOpenCellViewByType({lib} {sk(WRAPPER)} {sk(view)} \"maskLayout\" \"w\")",
        "  acfNeed(cv \"Cannot create the wrapper\")",
        '  inst=dbCreateInst(cv chip "XCHIP" 0:0 "R0") acfNeed(inst "Cannot place XCHIP")',
        '  inst=dbCreateInst(cv fill "FILL" 0:0 "R0") acfNeed(inst "Cannot place FILL")',
        "  n=0",
        '  foreach(s chip~>shapes when(s~>objType=="label"',
        "   acfNeed(dbCreateLabel(cv s~>lpp s~>xy s~>theLabel s~>justify s~>orient s~>font s~>height) \"Cannot copy a text\")",
        "   n=n+1))",
        f'  dbReplaceProp(cv "generatorOwner" "string" {sk(OWNER)})',
        f'  dbReplaceProp(cv "chipView" "string" {sk(chip_view)})',
        f'  dbReplaceProp(cv "fillLibrarySha256" "string" {sk(tf.sha(blob))})',
        '  acfNeed(dbSave(cv) "Cannot save the wrapper")',
        '  printf("CHIP_FILL_WRAPPER_OK instances=%d labels=%d bBox=%L\\n" length(cv~>instances) n cv~>bBox)',
        "  dbClose(cv) dbClose(fill) dbClose(chip) t))",
        "if(errset(acfBuild() t) then exit(0) else exit(1))"]) + "\n"
    files = {"build.il": skill.encode("ascii"), "cells.txt": ("\n".join(cells) + "\n").encode("ascii")}
    evidence = f"{cfg['remote_root']}/evidence/{identity}"
    # The library is sent ahead with compressed scp into the owned state folder (inline base64 times out for a chip
    # fill library), then moved into the evidence directory and hash-checked.
    staged = f"{cfg['remote_root']}/state/{identity}.fill_library.gds"
    subprocess.run(["scp", "-C", "-q", "-o", "BatchMode=yes", str(out / "fill_library.gds"), f"{cfg['host']}:{staged}"],
                   check=True, timeout=3600)
    lib_path = cfg["library_path"]
    guarded = q(f"{lib_path}/{CHIP}/{chip_view}/layout.oa")
    script = ["set -eu", "umask 077", f"test \"$(hostname -s)\" = {q(cfg['host'])}",
              f"test ! -e {q(evidence)} && test ! -e {q(cfg['legacy_root'] + '/evidence/' + identity)}",
              f"exec 9>>{q(cfg['legacy_root'] + '/layout.lock')}", "flock -w 600 9 || { echo LAYOUT_LOCK_BUSY; exit 3; }",
              f"if find {q(lib_path + '/' + CHIP)} -name '*.cdslck*' | grep -q .; then echo EDIT_LOCK_PRESENT; exit 4; fi",
              f"mkdir {q(evidence)}", f"cd {q(evidence)}", f"mv {q(staged)} fill_library.gds",
              f"test \"$(sha256sum fill_library.gds | cut -d' ' -f1)\" = {tf.sha(blob)} || {{ echo LIBRARY_HASH_DIFFERS; exit 9; }}"]
    for name, b in files.items():
        script += [f"base64 -d > {name} <<'B64'", base64.b64encode(b).decode("ascii"), "B64"]
    script += [f"while read c; do test ! -e {q(lib_path)}/\"$c\" || {{ echo CELL_EXISTS $c; exit 6; }}; done < cells.txt",
               f"test ! -e {q(lib_path + '/' + WRAPPER + '/' + view)} || {{ echo WRAPPER_EXISTS; exit 6; }}",
               f"cp {q(cfg['remote_root'] + '/runtime/cds.lib')} cds.lib",
               f"grep -q -E '^DEFINE[[:space:]]+{STANDARD_LIBRARY}[[:space:]]' cds.lib || "
               f"grep -m1 -E '^DEFINE[[:space:]]+{STANDARD_LIBRARY}[[:space:]]' /home/dmanager/shared_lib/TSMC28/cds.lib >> cds.lib",
               f"before=$(sha256sum {guarded} | cut -d' ' -f1)", "echo GUARDED_BEFORE=$before"]
    if expect_chip_oa:
        script.append(f"test \"$before\" = {q(expect_chip_oa)} || {{ echo CHIP_OA_DIFFERS_FROM_STREAM; exit 7; }}")
    strmin = (f"source {CADENCE}; exec strmin -library {cfg['library']} -strmFile fill_library.gds -topCell {FILL_TOP} "
              f"-view layout -attachTechFileOfLib tsmcN28 -layerMap {IO_LIBRARY_PDK}/tsmcN28.layermap "
              "-writeMode noOverwrite -logFile strmin.log")
    script += ["rc=0", f"timeout -k 10 900 tcsh -fc {q(strmin)} > strmin.console 2>&1 < /dev/null || rc=$?",
               "grep -E \"Translation completed|ERROR\" strmin.log | tail -n 5 || true",
               "test $rc = 0 || { echo STRMIN_FAILED=$rc; exit 8; }",
               f"timeout -k 10 900 tcsh -fc {q('source ' + CADENCE + '; exec virtuoso -nograph -nocdsinit -log build.log -restore build.il')}"
               " > oa.console 2>&1 < /dev/null || rc=$?",
               f"after=$(sha256sum {guarded} | cut -d' ' -f1)", "echo GUARDED_AFTER=$after",
               "test \"$before\" = \"$after\" || { echo READ_ONLY_VIEW_CHANGED; rc=5; }",
               f"sha256sum {q(lib_path + '/' + WRAPPER + '/' + view + '/layout.oa')} || true",
               "grep -E '^CHIP_FILL_WRAPPER_OK|\\*Error\\*' oa.console || true", "echo EXIT=$rc", "exit $rc"]
    text = ssh("\n".join(script), timeout=2400).decode("utf-8", "replace")
    receipt = dict(identity=identity, library=library_id, wrapper=f"{WRAPPER}/{view}", chip_view=chip_view,
                   stdout=text.splitlines(), ok="CHIP_FILL_WRAPPER_OK" in text and "EXIT=0" in text)
    write_json(WORK / identity / "build.json", receipt)
    if not receipt["ok"]:
        raise RuntimeError("Build failed; see " + str(WORK / identity / "build.json"))
    return receipt


# The fill-effect extraction keeps everything within CORRIDOR um of a VIN or VREF route shape, outside the core:
# fill farther away couples negligibly to the routes, and the crop stays small enough to extract.
CORRIDOR = 5.0
CROP_TOP = "sar8_chip_routes"


def route_windows():
    g = tf.gds()
    boxes = [tf.bloat(b, CORRIDOR) for _, b in route_rects(VIN + VREF)]
    union = g.boolean([g.rectangle(b[:2], b[2:]) for b in boxes], [], "or")
    return g.boolean(union, [g.rectangle(CORE_BOX[:2], CORE_BOX[2:])], "not")


def route_crop(identity, gds, top_name):
    """Flat copy of top_name clipped to ROUTE_WINDOWS, under the cell CROP_TOP, with one text per route net on a
    route shape. Extracted filled and unfilled with the same deck, it measures what the chip fill adds to the routes."""
    g = tf.gds()
    lib, top = tf.read_stream(gds, top_name)
    wins = route_windows()
    boxes = [tuple(v for xy in w.bounding_box() for v in xy) for w in wins]
    by = {}
    for p in top.get_polygons():
        (x0, y0), (x1, y1) = p.bounding_box()
        if any(x1 > w[0] and x0 < w[2] and y1 > w[1] and y0 < w[3] for w in boxes):
            by.setdefault((p.layer, p.datatype), []).append(p)
    cell = g.Cell(CROP_TOP)
    for (layer, datatype), ps in sorted(by.items()):
        cell.add(*g.boolean(ps, wins, "and", layer=layer, datatype=datatype))
    texts = {}
    for net in VIN + VREF:
        layer, box = max(route_rects((net,)), key=lambda r: (int(r[0][1:]), (r[1][2] - r[1][0]) * (r[1][3] - r[1][1])))
        n = int(layer[1:])
        xy = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
        if not any(w.contain(xy) for w in wins):
            raise ValueError("Route text outside the windows: " + net)
        cell.add(g.Label(net, xy, layer=130 + n if n < 8 else 130 + n, texttype=0))
        texts[net] = dict(layer=layer, xy=[round(v, 4) for v in xy])
    out = g.Library(unit=1e-6, precision=1e-9)
    out.add(cell)
    folder = WORK / identity
    digest = tf.save(out, folder, "crop.gds")
    summary = dict(identity=identity, source=str(gds), source_top=top_name, corridor_um=CORRIDOR,
                   window_area_um2=round(sum(w.area() for w in wins), 1), texts=texts,
                   gds_sha256=digest)
    write_json(folder / "crop.json", summary)
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--revision", type=int, default=1)
    ap.add_argument("--die", type=float, nargs=4, help="die box (um), for a smaller seal ring")
    ap.add_argument("--bounds", type=float, nargs=4, help="fill keep-in box (um), seal-ring band plus 3 um")
    ap.add_argument("--corner-cut", type=float, help="corner triangle legs (um) from each die corner")
    sub = ap.add_subparsers(dest="action", required=True)
    a = sub.add_parser("seed")
    a.add_argument("identity")
    a.add_argument("--chip-gds", required=True)
    a = sub.add_parser("fill")
    a.add_argument("identity")
    a.add_argument("--seed", required=True)
    a = sub.add_parser("library")
    a.add_argument("identity")
    a.add_argument("--chip-gds", required=True)
    a.add_argument("--fill-dir", required=True)
    a = sub.add_parser("clip")
    a.add_argument("identity")
    a.add_argument("--library", required=True)
    a.add_argument("--chip-gds", required=True)
    a = sub.add_parser("verify")
    a.add_argument("library")
    a.add_argument("--chip-gds", required=True)
    a = sub.add_parser("wrapper-gds")
    a.add_argument("identity")
    a.add_argument("--library", required=True)
    a.add_argument("--chip-gds", required=True)
    a = sub.add_parser("route-crop")
    a.add_argument("identity")
    a.add_argument("--gds", required=True)
    a.add_argument("--top", required=True)
    a = sub.add_parser("build")
    a.add_argument("identity")
    a.add_argument("--library", required=True)
    a.add_argument("--chip-view", required=True)
    a.add_argument("--view")
    a.add_argument("--expect-chip-oa")
    args = ap.parse_args()
    use_revision(args.revision)
    global DIE, BOUNDS, CORNER_CUT
    DIE = tuple(args.die) if args.die else DIE
    BOUNDS = tuple(args.bounds) if args.bounds else BOUNDS
    CORNER_CUT = args.corner_cut if args.corner_cut is not None else CORNER_CUT
    if args.action == "seed":
        r = seed(args.identity, args.chip_gds)
    elif args.action == "fill":
        tf.WORK = WORK   # launch receipts under this work folder
        r = tf.run_fill(args.identity, args.seed, CHIP, BOUNDS, turbo=8, seconds=3600, tcd=False)
    elif args.action == "library":
        r = library(args.identity, args.chip_gds, args.fill_dir)
    elif args.action == "clip":
        r = clip(args.identity, args.library, args.chip_gds)
    elif args.action == "verify":
        r = verify(args.library, args.chip_gds)
    elif args.action == "wrapper-gds":
        r = wrapper_gds(args.identity, args.library, args.chip_gds)
    elif args.action == "route-crop":
        r = route_crop(args.identity, args.gds, args.top)
    else:
        r = build(args.identity, args.library, args.chip_view, args.view, args.expect_chip_oa)
    print(json.dumps(r, indent=1)[:3000])


if __name__ == "__main__":
    main()
