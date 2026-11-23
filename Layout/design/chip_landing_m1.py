"""AVSS pad landings on M1 and M2 (revision 5): sar8_adc_chip/layout_full_fill5_r5_seal.

A copy of sar8_adc_chip/layout_full_fill5_r4_seal (left unchanged) plus the top-level shapes of
Layout/design/chip_integration.py avss_landing_m1: at the four PVSS3AC landings (AVSS analog top_3, pair left_6, SAR
right_8, guard left_0) the pad's M1 core-pin fingers are extended like its M2 fingers, onto an M1 bar under the
landing's M2 bar with a VIA1 grid under its VIA2 grid. Each AVSS pad then leaves on 21 um of Mx instead of 10.5 um,
against the 16 um the DRM's ESD current density asks for 1.3 A (9.3.4, ESD.CD.1gU; IO app note 8.7.3 / 10.7.3). No
cell changes; the nets are those of the source view.
"""
import argparse
import json

from Layout.design.chip_clamp_feed import VIEW as SOURCE_VIEW
from Layout.design.chip_seal_ring import CHIP, GUARDED, VIEW as SEAL_VIEW
from Layout.project import ROOT

VIEW = "layout_full_fill5_r5_seal"
READBACK = "chip-ring-readback-20261122c"


def build_script(identity):
    from Layout.design.chip_integration import avss_landing_m1, object_views
    from Layout.design.chip_objects import WORK, build_script as bs
    from Layout.project import write_json
    rb = json.loads((ROOT / "work/layout/chip" / READBACK / "ring_readback.json").read_bytes())
    c, info = avss_landing_m1(rb)
    data = dict(cell=CHIP, view=VIEW, copy_from=[CHIP, SOURCE_VIEW], rects=c.rects, pcells=[], terminals=[],
                labels=[], instances=[])
    out = bs(identity, data, guarded=GUARDED + [(CHIP, SEAL_VIEW), (CHIP, SOURCE_VIEW)] + list(object_views(3).items()))
    write_json(WORK / identity / "landing_m1.json", info)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("identity")
    a = ap.parse_args()
    print(build_script(a.identity))


if __name__ == "__main__":
    main()
