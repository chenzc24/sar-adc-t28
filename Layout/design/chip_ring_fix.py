"""Vertical-gate clamps and single power cuts (revision 8): sar8_adc_chip/layout_full_fill5_r8_seal.

Two fixes on a copy of sar8_adc_chip/layout_full_fill5_r7_seal (left unchanged); every IO and clamp outline stays:
- Clamps: XESD_CLAMPS becomes sar8_esd_clamps/layout_vg, the three clamps on PCLAMPC_V_G at the same places, R0
  (Layout/design/chip_objects_geometry.py clamps_vg). The IO app note (ch. 16) needs vertical gate poly; PCLAMPC_H_G at
  R0 has horizontal gates (PO.R.5/6, PO.W.2, SR_DPO.R.4 in chip DRC). Same outline and M3 pin figures.
- Power cuts: each domain cut of the generated ring is two abutting PRCUTA_G (left_6/left_7 and right_7/right_8), whose
  abutting well and substrate islands float (ERC floating.nxwell_float / floating.psub). One cut is enough (app note
  9.8.3); the one beside the PVSS3AC_H_G stays, as 9.8.3 note 1 asks, and the one beside the digital pad becomes a
  PFILLER20_G of the digital domain, the cell of the other 20 um digital gaps, same origin and orientation. The ring
  copy is sar8_io_ring/layout_r2; sar8_io_ring/layout stays unchanged. PRCUTA_G and PFILLER20_G hold no devices, so
  the ring netlist does not change.
"""
import argparse

from Layout.design.chip_objects import build_script as bs, io_library
from Layout.design.chip_seal_ring import CHIP, GUARDED
from Layout.project import config

RING, RING_SOURCE, RING_VIEW = "sar8_io_ring", "layout", "layout_r2"
# Cut beside the digital pad -> filler (instance names from ring readback chip-ring-readback-20261122c).
CUT_TO_FILLER = {"left_6_mid_2_left_21": "west, between PVSS1DGZ_H_G (left_7) and the cut beside PVSS3AC_H_G (left_6)",
                 "right_7_mid_1_right_23": "east, between PVDD1DGZ_H_G (right_7) and the cut beside PVSS3AC_H_G (right_8)"}
FILLER = "PFILLER20_G"
CLAMPS, CLAMP_VIEW = "sar8_esd_clamps", "layout_vg"
SOURCE_VIEW, VIEW = "layout_full_fill5_r7_seal", "layout_full_fill5_r8_seal"
CHIP_VIEWS = ("layout_full_fill5_r3_seal", "layout_full_fill5_r4_seal", "layout_full_fill5_r5_seal",
              "layout_full_fill5_r6_seal", SOURCE_VIEW)


def ring_build_script(identity):
    data = dict(cell=RING, view=RING_VIEW, copy_from=[RING, RING_SOURCE], rects=[], pcells=[], terminals=[], labels=[],
                instances=[], replace_masters=[dict(inst=n, lib=io_library(), cell=FILLER, view="layout")
                                               for n in CUT_TO_FILLER])
    return bs(identity, data, guarded=GUARDED + [(CHIP, v) for v in CHIP_VIEWS])


def chip_build_script(identity):
    from Layout.design.chip_integration import object_views
    lib = config()["library"]
    data = dict(cell=CHIP, view=VIEW, copy_from=[CHIP, SOURCE_VIEW], rects=[], pcells=[], terminals=[], labels=[],
                instances=[], replace_masters=[dict(inst="XRING", lib=lib, cell=RING, view=RING_VIEW),
                                               dict(inst="XESD_CLAMPS", lib=lib, cell=CLAMPS, view=CLAMP_VIEW)])
    guarded = GUARDED + [(CHIP, v) for v in CHIP_VIEWS] + [(RING, RING_VIEW), (CLAMPS, CLAMP_VIEW)] + \
        list(object_views(3).items())
    return bs(identity, data, guarded=guarded)


def lvs_source(src, out):
    """Chip LVS source of r8: the r7 source with the clamp subcircuit on PCLAMPC_V_G (the ring netlist is unchanged)."""
    text = open(src, encoding="latin1").read()
    head, sep, rest = text.partition(".SUBCKT sar8_esd_clamps ")
    body, sep2, tail = rest.partition(".ENDS sar8_esd_clamps")
    if not (sep and sep2) or body.count(" PCLAMPC_H_G") != 3:
        raise ValueError("Unexpected clamp subcircuit in the source")
    new = head + sep + body.replace(" PCLAMPC_H_G", " PCLAMPC_V_G") + sep2 + tail
    if new.count("PCLAMPC_H_G") != text.count("PCLAMPC_H_G") - 3:
        raise ValueError("PCLAMPC_H_G used outside the clamp subcircuit")
    open(out, "w", encoding="latin1", newline="\n").write(new)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="action", required=True)
    for name in ("ring-build-script", "chip-build-script"):
        sub.add_parser(name).add_argument("identity")
    a = sub.add_parser("lvs-source")
    a.add_argument("src")
    a.add_argument("out")
    a = ap.parse_args()
    if a.action == "ring-build-script":
        print(ring_build_script(a.identity))
    elif a.action == "chip-build-script":
        print(chip_build_script(a.identity))
    else:
        print(lvs_source(a.src, a.out))


if __name__ == "__main__":
    main()
