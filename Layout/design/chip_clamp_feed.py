"""Clamp feed along the bars (revision 4): sar8_adc_chip/layout_full_fill5_r4_seal.

A copy of the seal-ring chip view sar8_adc_chip/layout_full_fill5_r3_seal (left unchanged) plus the top-level shapes of
Layout/design/chip_integration.py clamp_feed: over each PCLAMPC_H_G M4 bar a strap on the trunk metal (AVDD M9, AVSS
M8) and a drop stack every 6 um along it, so the clamp's nine M3 terminal strips per net are fed along the whole bar
instead of from the three stacks at one place (the periphery extraction gave about 1.1 ohm from pad to clamp, against
1 ohm in the app note's Table 10.1). No cell changes; the nets are those of the source view.
"""
import argparse

from Layout.design.chip_seal_ring import CHIP, GUARDED, VIEW as SOURCE_VIEW

VIEW = "layout_full_fill5_r4_seal"


def build_script(identity):
    from Layout.design.chip_integration import clamp_feed, object_views
    from Layout.design.chip_objects import WORK, build_script as bs
    from Layout.project import write_json
    c, info = clamp_feed(1)
    data = dict(cell=CHIP, view=VIEW, copy_from=[CHIP, SOURCE_VIEW], rects=c.rects, pcells=[], terminals=[],
                labels=[], instances=[])
    out = bs(identity, data, guarded=GUARDED + [(CHIP, SOURCE_VIEW)] + list(object_views(3).items()))
    write_json(WORK / identity / "clamp_feed.json", info)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("identity")
    a = ap.parse_args()
    print(build_script(a.identity))


if __name__ == "__main__":
    main()
