"""Seal ring of the chip (chenzc24/sar-adc-t28#18): the lab's 1 x 1 mm seal ring around the IO ring.

sar8_adc_chip/layout_full_fill5_r3_seal = a copy of the current chip view sar8_adc_chip/layout_full_fill5_r3
(left unchanged) plus one instance of the lab's seal ring (io_ring.json seal_ring: sealring/N28_TSMC_SRDMB_Mu/layout,
from the shared seal-ring library, not drawn here) at its origin in die coordinates, R0. The 760 um IO-cell outline
stays at 0..760, centred in the 1000 um die; nothing else in the copy moves.
"""
import argparse
import json

from Layout.project import ROOT, config

CHIP = "sar8_adc_chip"
SOURCE_VIEW, VIEW = "layout_full_fill5_r3", "layout_full_fill5_r3_seal"
# Every chip view and the masters of the source view stay unchanged.
GUARDED = [(CHIP, v) for v in ("layout", "layout_full", "layout_full_boot_r2", "layout_full_dc_fill5", SOURCE_VIEW)] + [
    ("sar8_io_ring", "layout"), ("sar8_adc_core", "layout_route_guard"), ("sar8_adc_core_filled", "layout_fill5")]


def build_script(identity):
    from Layout.design.chip_integration import object_views
    from Layout.design.chip_objects import build_script as bs
    seal = json.loads((ROOT / "Layout/design/io_ring.json").read_bytes())["seal_ring"]
    lib, cell, view = seal["master"].split("/")
    data = dict(cell=CHIP, view=VIEW, copy_from=[CHIP, SOURCE_VIEW], rects=[], pcells=[], terminals=[], labels=[],
                instances=[dict(lib=lib, cell=cell, view=view, name="XSEAL_RING", xy=seal["origin_um"],
                                orient=seal["orient"])])
    if lib == config()["library"]:
        raise ValueError("The seal ring comes from the lab's library, not the layout library")
    return bs(identity, data, guarded=GUARDED + list(object_views(3).items()))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("identity")
    a = ap.parse_args()
    print(build_script(a.identity))


if __name__ == "__main__":
    main()
