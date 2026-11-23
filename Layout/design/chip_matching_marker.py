"""MOS-matching markers on the comparator, in the chip top cell (revision 6): sar8_adc_chip/layout_full_fill5_r6_seal.

A copy of sar8_adc_chip/layout_full_fill5_r5_seal (left unchanged) plus two MATCHING (205;8) rectangles in the chip
top cell over the comparator's N and P MOS arrays (Layout/tools/physical/matching_overlay.py ARRAYS, the footprints of
run chip-match-h1), so the comparator, the cores and their streams stay byte-identical (user decision 2026-11-23,
"Add markers, write waiver": permanent MATCHING markers and a recorded deviation from high matching).
- Layer: OA PMET_CUT / drawing1, the PDK layer map's name for GDS 205;8, which the DRC deck reads as MATCHING (CAD
  marker only; the LVS and xRC decks map no 205;8, so device recognition and extraction do not change).
- Class: MATCHING (normal) switches on PO.DN.16, PO.R.28, AN.R.78.1m and clears MATCH.WARN.1; not AN.R.79.x / 80.x.
"""
import argparse

from Layout.design.chip_landing_m1 import VIEW as SOURCE_VIEW
from Layout.design.chip_seal_ring import CHIP, GUARDED, VIEW as SEAL_VIEW
from Layout.tools.physical.matching_overlay import ARRAYS

VIEW = "layout_full_fill5_r6_seal"
LAYER = ("PMET_CUT", "drawing1")           # GDS 205;8 (tsmcN28.layermap)
# sar_strongarm_t28_core in the chip (sar8_adc_core_filled / sar8_adc_core): origin and mirror about its y axis
# (GDS x_reflection with a 180 degree rotation), from the r5 stream chip-landm1-b1-chk.
COMPARATOR_ORIGIN = (410.0, 521.61)


def marker_boxes():
    ox, oy = COMPARATOR_ORIGIN
    return {k: (round(ox - a["box"][2], 3), round(oy + a["box"][1], 3), round(ox - a["box"][0], 3), round(oy + a["box"][3], 3))
            for k, a in ARRAYS.items()}


def build_script(identity):
    from Layout.design.chip_integration import object_views
    from Layout.design.chip_objects import WORK, build_script as bs
    from Layout.project import write_json
    rects = [dict(net="", layer=LAYER[0], purpose=LAYER[1], box=list(b)) for b in marker_boxes().values()]
    data = dict(cell=CHIP, view=VIEW, copy_from=[CHIP, SOURCE_VIEW], rects=rects, pcells=[], terminals=[],
                labels=[], instances=[])
    guarded = GUARDED + [(CHIP, v) for v in (SEAL_VIEW, "layout_full_fill5_r4_seal", SOURCE_VIEW)] + \
        list(object_views(3).items())
    out = bs(identity, data, guarded=guarded)
    write_json(WORK / identity / "matching_markers.json", dict(layer=list(LAYER), gds=[205, 8], boxes=marker_boxes()))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("identity")
    a = ap.parse_args()
    print(build_script(a.identity))


if __name__ == "__main__":
    main()
