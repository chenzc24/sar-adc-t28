"""TSMC N28 standard seal ring re-tiled for a smaller die (DRM T-N28-CL-DR-002 v2.3, 4.5.66.2, seal ring added by
the customer).

The TSMC sample N28_TSMC_SRDMB_Mu_1P10M_002_20160711_SR_BKM.gds (and the lab's sealring/N28_TSMC_SRDMB_Mu, the same
cells with the metal and via layers of the 1P9M 6X1Z1U stack) is a 1000 um square of four cells, as the DRM's
procedure asks: two corner cells (CSR2DMY at the lower-left and upper-right corners, CSR1DMY at the other two, 185.6
um square), one UCSRN_NOVIA_DPO_DOD per edge 182.6 um from its corner, and a row of UCSRN_DPO_DOD repeat cells (24 x
5.4 um) from 188 um to the next corner. This keeps every relative position of the sample and changes only the
number of repeat cells n per edge, so the die is 373.6 + 5.4 n um (n = 116 is the sample's 1000 um).

Smallest die for the 9 x 9 IO ring (760 um outline, centred): CSR.R.1 keeps layout out of a 74 um triangle at each
prime-chip corner, x + y < 122 um in the seal-ring frame, and the IO corner cells draw up to their outline corner, at
x + y = die - 760. So die >= 882 um; n = 96 gives 892 um with 10 um to spare.
"""
import argparse
import json
import math

TILE, CORNER, NOVIA_AT, FIRST = 5.4, 185.6, 182.6, 188.0
LIB = "sealring"                       # the lab's shared seal-ring library (shared cds.lib)
SAMPLE_TILES = 116
IO_OUTLINE, CSR_TRIANGLE = 760.0, 2 * 24.0 + 74.0


def die(n):
    return round(FIRST + n * TILE + CORNER, 4)


def placements(n):
    """(cell, x, y, orient) of every instance of the n-tile seal ring, origin at its lower-left corner."""
    d = die(n)
    out = [("CSR2DMY", 0.0, 0.0, "R0"), ("CSR2DMY", d, d, "R180"), ("CSR1DMY", d, 0.0, "R90"), ("CSR1DMY", 0.0, d, "R270"),
           ("UCSRN_NOVIA_DPO_DOD", 0.0, NOVIA_AT, "R0"), ("UCSRN_NOVIA_DPO_DOD", NOVIA_AT, d, "R270"),
           ("UCSRN_NOVIA_DPO_DOD", d, d - NOVIA_AT, "R180"), ("UCSRN_NOVIA_DPO_DOD", d - NOVIA_AT, 0.0, "R90")]
    for k in range(n):
        s = FIRST + k * TILE
        out += [("UCSRN_DPO_DOD", 0.0, s, "R0"), ("UCSRN_DPO_DOD", s, d, "R270"),
                ("UCSRN_DPO_DOD", d, d - s, "R180"), ("UCSRN_DPO_DOD", d - s, 0.0, "R90")]
    return sorted((c, round(x, 3), round(y, 3), o) for c, x, y, o in out)


def smallest_tiles(io=IO_OUTLINE, margin=0.0):
    """Fewest repeat cells whose centred IO outline clears the CSR.R.1 triangles by margin."""
    return math.ceil((io + CSR_TRIANGLE + margin - FIRST - CORNER) / TILE)


def stream_placements(path, top):
    """Expanded (cell, x, y, orient) of the top cell of a GDS stream (references and arrays)."""
    import gdstk
    cell = next(c for c in gdstk.read_gds(path).cells if c.name == top)
    out = []
    for r in cell.references:
        if r.x_reflection:
            raise ValueError("Unexpected mirrored seal-ring cell")
        orient = "R%d" % (round(math.degrees(r.rotation)) % 360)
        offs = [(0.0, 0.0)] if r.repetition is None or r.repetition.size == 0 else r.repetition.get_offsets()
        for dx, dy in offs:
            out.append((r.cell.name, round(r.origin[0] + dx, 3), round(r.origin[1] + dy, 3), orient))
    return sorted(out)


def content(n, cell, view="layout"):
    """chip_objects build content of the n-tile seal ring cell (instances of the lab library's cells)."""
    inst = [dict(lib=LIB, cell=c, view="layout", name=f"X{k}", xy=[x, y], orient=o)
            for k, (c, x, y, o) in enumerate(placements(n))]
    return dict(cell=cell, view=view, rects=[], pcells=[], terminals=[], labels=[], instances=inst)


def cell_name(n):
    return "sar8_seal_ring_%d" % round(die(n) * 10) if die(n) % 1 else "sar8_seal_ring_%d" % die(n)


def build_script(identity, n):
    """build.il of the n-tile seal ring cell in the layout library; every chip view stays unchanged."""
    from Layout.design.chip_objects import build_script as bs
    from Layout.design.chip_seal_ring import CHIP, GUARDED
    chip_views = ("layout_full_fill5_r3_seal", "layout_full_fill5_r4_seal", "layout_full_fill5_r5_seal",
                  "layout_full_fill5_r6_seal")
    return bs(identity, content(n, cell_name(n)), guarded=GUARDED + [(CHIP, v) for v in chip_views])


def scratch_chip(chip_gds, ring_gds, n, out, top="sar8_adc_chip", old="N28_TSMC_SRDMB_Mu"):
    """Scratch chip stream for checking a re-tiled seal ring without any chip view: the chip stream with its seal-ring
    instance replaced by the n-tile ring (from its own stream) at -(die - 760) / 2, the IO ring still centred. The
    ring's cells must equal the chip stream's cells of the same name; nothing else changes (checked)."""
    import hashlib
    import gdstk
    from pathlib import Path

    def sig(c):
        return (sorted((p.layer, p.datatype, len(p.points), round(p.area(), 4)) for p in c.polygons),
                sorted((r.cell_name, round(r.origin[0], 4), round(r.origin[1], 4), round(r.rotation, 6), r.x_reflection,
                        0 if r.repetition is None else r.repetition.size) for r in c.references))
    lib, rlib = gdstk.read_gds(chip_gds), gdstk.read_gds(ring_gds)
    cells = {c.name: c for c in lib.cells}
    rtop = next(c for c in rlib.cells if c.name == cell_name(n))
    for c in rlib.cells:
        if c is not rtop and (c.name not in cells or sig(c) != sig(cells[c.name])):
            raise ValueError("Seal-ring cell differs from the chip stream's: " + c.name)
    ring = gdstk.Cell(rtop.name)
    for r in rtop.references:
        ref = gdstk.Reference(cells[r.cell.name], r.origin, r.rotation, r.magnification, r.x_reflection)
        ref.repetition = r.repetition
        ring.add(ref)
    chip = cells[top]
    olds = [r for r in chip.references if r.cell_name == old]
    if len(olds) != 1:
        raise ValueError("Expected one seal-ring instance")
    off = -(die(n) - IO_OUTLINE) / 2
    chip.remove(olds[0])
    chip.add(gdstk.Reference(ring, (off, off)))
    lib.remove(cells[old])
    lib.add(ring)
    lib.write_gds(out)
    before = {c.name: sig(c) for c in gdstk.read_gds(chip_gds).cells}
    after = {c.name: sig(c) for c in gdstk.read_gds(out).cells}
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    if changed != sorted({top, old, ring.name}):
        raise ValueError("Scratch stream changed more than the seal ring: %s" % changed)
    return dict(out=str(out), sha256=hashlib.sha256(Path(out).read_bytes()).hexdigest(), die_um=die(n),
                ring_origin_die_um=[off, off], die_bbox=[off, off, off + die(n), off + die(n)], changed_cells=changed)


LMARK = (109, 0)
PROBE_SUMS = (70.0, 73.0, 75.0, 78.0, 100.0, 110.0)    # x + y from the prime-chip corner


def csr_probe(scratch_gds, n, out, top="sar8_adc_chip"):
    """Stream for tool-checking CSR.R.1 with a customer seal ring. The deck derives the corner triangles
    (EMPTY_AREA_P4 = INT CHIP_NOSR_P4 < CSR_R_1 ABUT == 90) only from a chip without a seal ring, whose extent is then
    the prime chip (DRM: 'Prime Chip' of a TSMC-added seal ring = GDS extent). So: the scratch chip without its seal
    ring, plus four 0.1 um LMARK squares at the prime-chip corners (the inner edge of SEALRING_ALL, 24 um inside the
    die), which set the chip extent; and LMARK probes on the lower-left diagonal at PROBE_SUMS, whose flags show the
    triangle's shape (legs of 74 um: x + y < 74; a 74 um radius would also flag 100). CSR.R.1 on any other layer
    must be 0."""
    import hashlib
    import gdstk
    from pathlib import Path
    lib = gdstk.read_gds(scratch_gds)
    cells = {c.name: c for c in lib.cells}
    chip = cells[top]
    ring = [r for r in chip.references if r.cell_name == cell_name(n)]
    if len(ring) != 1:
        raise ValueError("Expected the n-tile seal ring in the scratch stream")
    (rx, ry) = ring[0].origin
    chip.remove(ring[0])
    lo, hi = rx + 24.0, rx + die(n) - 24.0
    s = 0.1
    corners = [(lo, lo), (hi - s, lo), (lo, hi - s), (hi - s, hi - s)]
    probes = [(lo + v / 2 - s / 2, lo + v / 2 - s / 2) for v in PROBE_SUMS]
    for x, y in corners + probes:
        chip.add(gdstk.rectangle((round(x, 3), round(y, 3)), (round(x + s, 3), round(y + s, 3)), layer=LMARK[0],
                                 datatype=LMARK[1]))
    lib.write_gds(out)
    return dict(out=str(out), sha256=hashlib.sha256(Path(out).read_bytes()).hexdigest(), prime_chip=[lo, lo, hi, hi],
                corner_markers=corners, probes=dict(zip(PROBE_SUMS, probes)))


CHIP_SOURCE = "layout_full_fill5_r6_seal"
CHIP_VIEW = "layout_full_fill5_r7_seal"


def chip_build_script(identity, n):
    """build.il of the chip view with the n-tile seal ring: a copy of CHIP_SOURCE (unchanged) whose XSEAL_RING
    instance becomes the n-tile ring cell at -(die - 760) / 2, R0; nothing else changes."""
    from Layout.design.chip_integration import object_views
    from Layout.design.chip_objects import build_script as bs
    from Layout.design.chip_seal_ring import CHIP, GUARDED
    from Layout.project import config
    off = -(die(n) - IO_OUTLINE) / 2
    data = dict(cell=CHIP, view=CHIP_VIEW, copy_from=[CHIP, CHIP_SOURCE], rects=[], pcells=[], terminals=[], labels=[],
                instances=[], replace_masters=[dict(inst="XSEAL_RING", lib=config()["library"], cell=cell_name(n),
                                                    view="layout", xy=[off, off])])
    views = ("layout_full_fill5_r3_seal", "layout_full_fill5_r4_seal", "layout_full_fill5_r5_seal", CHIP_SOURCE)
    guarded = GUARDED + [(CHIP, v) for v in views] + [(cell_name(n), "layout")] + list(object_views(3).items())
    return bs(identity, data, guarded=guarded)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="action", required=True)
    a = sub.add_parser("scratch-chip", help="chip stream with the n-tile ring in place of the 1 mm ring (no OA)")
    a.add_argument("chip_gds")
    a.add_argument("ring_gds")
    a.add_argument("out")
    a.add_argument("--tiles", type=int, required=True)
    a = sub.add_parser("csr-probe", help="CSR.R.1 probe stream from a scratch chip stream (no seal ring, LMARK markers)")
    a.add_argument("scratch_gds")
    a.add_argument("out")
    a.add_argument("--tiles", type=int, required=True)
    a = sub.add_parser("chip-build-script", help="build.il of the chip view with the n-tile ring (then chip_objects build)")
    a.add_argument("identity")
    a.add_argument("--tiles", type=int, required=True)
    a = sub.add_parser("build-script", help="build.il of the n-tile seal ring cell (then chip_objects build)")
    a.add_argument("identity")
    a.add_argument("--tiles", type=int, required=True)
    a = sub.add_parser("check", help="the generator against a sample stream (n = 116)")
    a.add_argument("stream")
    a.add_argument("--top", default="N28_TSMC_SRDMB_Mu")
    a.add_argument("--tiles", type=int, default=SAMPLE_TILES)
    a = sub.add_parser("size", help="smallest tile count for the IO ring")
    a.add_argument("--margin", type=float, default=10.0)
    a = ap.parse_args()
    if a.action == "chip-build-script":
        print(chip_build_script(a.identity, a.tiles), CHIP_VIEW)
    elif a.action == "csr-probe":
        print(json.dumps(csr_probe(a.scratch_gds, a.tiles, a.out), indent=1))
    elif a.action == "scratch-chip":
        print(json.dumps(scratch_chip(a.chip_gds, a.ring_gds, a.tiles, a.out), indent=1))
    elif a.action == "build-script":
        print(build_script(a.identity, a.tiles), cell_name(a.tiles), die(a.tiles))
    elif a.action == "check":
        got, want = stream_placements(a.stream, a.top), placements(a.tiles)
        print(json.dumps(dict(instances=len(got), expected=len(want), equal=got == want, die_um=die(a.tiles),
                              only_in_stream=[p for p in got if p not in want][:5],
                              only_generated=[p for p in want if p not in got][:5]), indent=1))
    else:
        n = smallest_tiles(margin=a.margin)
        print(json.dumps(dict(tiles=n, die_um=die(n), io_corner_x_plus_y=round(die(n) - IO_OUTLINE, 3),
                              csr_triangle=CSR_TRIANGLE), indent=1))


if __name__ == "__main__":
    main()
