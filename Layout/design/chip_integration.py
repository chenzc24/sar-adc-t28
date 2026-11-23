"""Integration of the chip-level objects into the chip cell (chenzc24/sar-adc-t28#12, #18).

sar8_adc_chip/layout_full = a copy of the partial chip assembly sar8_adc_chip/layout (Layout/design/chip_assembly.py,
left unchanged) plus the eight object cells of Layout/design/chip_objects.py at the origin, R0, and the io_ring.json
routes that end on them, in die coordinates:
- ADC_D0-7: the core's M7 D tracks continue over the guard ring to a stack down to the register's M3 D pins.
- CK: an M4 stub from the register's CK pin up to a stack onto the SAMPLE M8 route above the register.
- D0-D7 (D0_CORE-D7_CORE): an M4 stub below each Q pin, a stack to M6, M6 down the planned column, M5 along the
  planned row, M6 down (bottom pads) and a stack onto the pad's M4 I pin (an M4 stub on the 0.26 um pin).
- DVDD: the right_4 landing (M2 fingers onto a bar, plates to M6), 4 um M6 along y 380 through the DVDD decap's M6
  port pad, up x 524-528 (4 um west of the planned x 530, clear of the register's M6 ring) onto its VDD M5 ring.
- VSS_register: 2 um M7 from the register's east VSS ring (VIA6) via x 540 and y 420 (VIA6 onto the DVDD decap's VSS
  port) into the core VSS ring. VSS_digital / VSS_analog: the PVSS1DGZ / PVSS2AC M2 fingers extended across the ring
  band, with M3-M6 plates and via fields up to each M7 strip.
- AVSS_guard: the left_0 landing up to M9, 2 um M9 along x 116 and y 563, a stack down to the guard ring's M2 corner.
- Decap ports: via stacks from the branch trunks (AVDD M9, AVSS M8) onto each decap's M6 landing pad.
- Clamps: via stacks from the trunks onto the clamp bars (analog, SAR), or M9/M8 straps from the trunks to the bars
  (pair: AVDD_pair runs above at y 320, AVSS_pair below at y 260).
"""
import argparse
import json

from Layout.design import chip_objects_geometry as geo
from Layout.design.chip_routes import landing
from Layout.design.toplevel_full_routes import Content
from Layout.design.toplevel_routes import snap
from Layout.project import ROOT, config, write_json

CHIP = "sar8_adc_chip"
SOURCE_VIEW, VIEW = "layout", "layout_full"
OBJECT_CELLS = ["sar8_out_reg", "sar8_esd_clamps", "sar8_decap_analog", "sar8_decap_pair", "sar8_decap_sar",
                "sar8_decap_dvdd", "sar8_core_vss_ring", "sar8_adc_guard_ring"]
AVDD, AVSS, DVDD, VSS = geo.AVDD, geo.AVSS, geo.DVDD, geo.VSS


def plan():
    return geo.plan()


def g(v):
    return snap(round(round(v / 0.005) * 0.005, 3))


def via_fields(c, net, box, lo, hi, pitch=0.6):
    """Plates M(lo+1)..M(hi) on box and 2 x 2 via clusters between every pair of metals lo..hi (lo, hi <= 7)."""
    for m in range(lo + 1, hi + 1):
        c.rect(net, f"M{m}", *box)
    inner = (box[0] + 0.15, box[1] + 0.15, box[2] - 0.15, box[3] - 0.15)
    n = 0
    for m in range(lo, hi):
        n += geo.via_field(c, net, m, inner, pitch)
    return n


def stack_hi(c, net, x, y, lo, hi, w=1.6):
    """Via stack from metal lo to metal hi (hi up to 9) at (x, y): Mx via fields on w x w plates up to M7, a 2 x 2
    VIA7 array and a 2 x 2 VIA8 array on 1.8 um M8/M9 pads."""
    h = w / 2
    top_x = min(hi, 7)
    if top_x > lo:
        via_fields(c, net, (g(x - h), g(y - h), g(x + h), g(y + h)), lo, top_x)
    if hi >= 8:
        # a VIA7 pair and a VIA8 pair 0.7 um apart along y (the core's via7(n=2) / via8; a 2 x 2 array breaks
        # VIA7.S.2 / VIA8.S.2)
        c.rect(net, "M7", g(x - 0.9), g(y - 0.9), g(x + 0.9), g(y + 0.9))
        c.rect(net, "M8", g(x - 0.9), g(y - 0.9), g(x + 0.9), g(y + 0.9))
        for sy in (-0.35, 0.35):
            c.rect(net, "VIA7", g(x - 0.18), g(y + sy - 0.18), g(x + 0.18), g(y + sy + 0.18))
    if hi >= 9:
        c.rect(net, "M9", g(x - 1.0), g(y - 1.0), g(x + 1.0), g(y + 1.0))
        for sy in (-0.35, 0.35):
            c.rect(net, "VIA8", g(x - 0.18), g(y + sy - 0.18), g(x + 0.18), g(y + sy + 0.18))


def mstack(c, net, x, y, lo, hi, axis="y"):
    """Mx via pairs with pads from metal lo up to metal hi <= 7 (no stray upper pad)."""
    for m in range(lo, hi):
        c.mx(net, x, y, m, axis, pads=(True, True))


def clamp_drop(c, net, x, yb, h):
    """One drop stack onto a clamp bar at (x, yb): M4-M7 via fields on 1.6 x 2h plates, then the VIA7 (and for AVDD the
    VIA8) pair up to the trunk metal."""
    via_fields(c, net, (g(x - 0.8), g(yb - h), g(x + 0.8), g(yb + h)), 4, 7)
    stack_hi(c, net, x, yb, 7, 9 if net == AVDD else 8)


def drop_xs(branch, net, rev=1):
    """x of the trunk drop stacks onto a clamp bar: between the pair trunks at 30/50/70 um into the clamp, else under
    the trunk."""
    x0, _ = geo.CLAMP_ORIGIN[rev][branch]
    if branch == "pair" or (branch == "analog" and rev == 2):
        return tuple(x0 + d for d in (30.0, 50.0, 70.0))
    if branch == "analog":
        return (377.0, 380.0, 383.0) if net == AVDD else (437.0, 440.0, 443.0)
    return (557.0, 560.0, 563.0) if net == AVDD else (597.0, 600.0, 603.0)


def object_views(rev=1):
    """OA view of each object cell. Revision 2: the grown pad decaps and the moved analog clamp (layout_r2).
    Revision 3: the clamps back in place (layout), the analog decap with MOM (layout_r3), the other decaps layout_r2."""
    views = {cell: "layout" for cell in OBJECT_CELLS}
    if rev >= 2:
        views.update({f"sar8_decap_{b}": geo.decap_view(b, rev) for b in geo.DECAPS})
    if rev == 2:
        views["sar8_esd_clamps"] = "layout_r2"
    return views


def content(readback, rev=1):
    ring = plan()
    reg = json.loads((ROOT / "work/layout/output-register/r1/content.json").read_bytes())
    regt = {t["net"]: t["pins"][0]["box"] for t in reg["terminals"]}
    routes = ring["routes"]
    c = Content()
    c.instances = [dict(lib=config()["library"], cell=cell, view=view, name="X" + cell.upper().replace("SAR8_", ""),
                        xy=[0.0, 0.0], orient="R0") for cell, view in object_views(rev).items()]
    info = {}
    # ADC_D0-7: M7 from the core edge to x 491.6, stack M7 -> M3 at x 491.2, M3 stub onto the register pin.
    for k in range(8):
        net = f"ADC_D{k}"
        y = routes[net]["points_um"][0][1]
        pin = regt[f"D{k}"]
        c.rect(net, "M7", 485.885, g(y - 0.1), 491.4, g(y + 0.1))
        for m in (3, 4, 5, 6):
            c.mx(net, 491.2, g(y), m, axis="x", pads=(True, True))
        c.rect(net, "M3", 491.0, g(y - 0.05), pin[2], g(y + 0.05))
        info[net] = dict(m7=[485.885, 491.4], stack_x=491.2, y=y)
    # CK: M4 from the pin top to y 514.4, stack M4 -> M8 onto SAMPLE (0.8 um M8, y 514.0-514.8).
    ck = regt["CK"]
    x = (ck[0] + ck[2]) / 2
    c.rect("SAMPLE_CORE", "M4", ck[0], ck[1], ck[2], 514.6)
    c.stack("SAMPLE_CORE", g(x), 514.4, 4, 8, axis="x")
    info["CK"] = dict(tap=[x, 514.4])
    # D0-D7 to the pads.
    land = json.loads((ROOT / "Layout/results/chip_assembly.json").read_bytes())["pending_objects"]["output_register"]
    for k in range(8):
        net = f"D{k}_CORE"
        pts = routes[f"D{k}"]["points_um"]
        q = regt[f"Q{k}"]
        qx = (q[0] + q[2]) / 2
        ipin = land["q_outputs"][net]
        c.rect(net, "M4", g(qx - 0.05), 470.2, g(qx + 0.05), q[3])
        mstack(c, net, g(qx), 470.6, 4, 6)
        if len(pts) == 3:                          # right pads: down the column, east along the row on M5
            (x0, _), (_, yr), _ = pts
            c.rect(net, "M6", g(qx - 0.2), g(yr - 0.2), g(qx + 0.2), 470.8)
            c.mx(net, g(qx), g(yr), 5, axis="x", pads=(True, True), quad=False)
            c.rect(net, "M5", g(qx - 0.2), g(yr - 0.2), 648.8, g(yr + 0.2))
            iy = (ipin[1] + ipin[3]) / 2
            c.rect(net, "M4", 648.2, ipin[1], ipin[2], ipin[3])
            c.mx(net, 648.6, g(iy), 4, axis="x", pads=(True, True))
            info[net] = dict(column=qx, row=yr, pin=ipin)
        else:                                      # bottom pads: column, row on M5, down on M6 to the I pin
            (x0, _), (_, yr), (xp, _), _ = pts
            c.rect(net, "M6", g(qx - 0.2), g(yr - 0.2), g(qx + 0.2), 470.8)
            c.mx(net, g(qx), g(yr), 5, axis="x", pads=(True, True))
            lo, hi = sorted((qx, xp))
            c.rect(net, "M5", g(lo - 0.2), g(yr - 0.2), g(hi + 0.2), g(yr + 0.2))
            c.mx(net, g(xp), g(yr), 5, axis="x", pads=(True, True))
            ix = (ipin[0] + ipin[2]) / 2
            c.rect(net, "M6", g(ix - 0.2), 110.4, g(ix + 0.2), g(yr + 0.2))
            c.rect(net, "M4", ipin[0], ipin[1], ipin[2], 110.9)
            mstack(c, net, g(ix), 110.6, 4, 6)
            info[net] = dict(column=qx, row=yr, pad_x=xp, pin=ipin)
    # DVDD: right_4 landing to M6, 4 um M6 along y 380 to x 524, up x 524-528 onto the register's VDD M5 ring.
    rb = readback
    fingers = sorted({tuple(p["bbox"]) for p in rb["pins"] if p["inst"] == "DVDD_right_13" and p["term"] == "VDD"
                      and p["layer"] == "M2" and p["bbox"][0] < 650.5})
    ys0, ys1 = min(f[1] for f in fingers), max(f[3] for f in fingers)
    for f in fingers:
        c.rect(DVDD, "M2", 647.6, f[1], 650.2, f[3])
    bar = (647.6, ys0, 648.6, ys1)
    c.rect(DVDD, "M2", *bar)
    via_fields(c, DVDD, bar, 2, 6, 0.4)
    vdd = regt["VDD"]                                     # M5 ring, south side
    c.rect(DVDD, "M6", 524.0, 378.5, bar[2], 381.5)
    c.rect(DVDD, "M6", 524.0, 378.5, 528.0, vdd[3])
    geo.via_field(c, DVDD, 5, (526.3, vdd[1] + 0.05, 527.8, vdd[3] - 0.05), 0.5)
    info["DVDD"] = dict(fingers=len(fingers), bar=list(bar), horizontal=[524.0, 378.5, bar[2], 381.5],
                        vertical=[524.0, 378.5, 528.0, vdd[3]])
    # VSS_register: M7 from the register's east VSS ring (M6) to the core VSS ring, VIA6 onto the DVDD decap VSS pad.
    vss = regt["VSS"]
    c.rect(VSS, "M7", vss[0], 479.0, 541.0, 481.0)
    geo.via_field(c, VSS, 6, (vss[0] + 0.05, 479.1, vss[2] - 0.05, 480.9), 0.5)
    c.rect(VSS, "M7", 539.0, 419.0, 541.0, 481.0)
    (_, _), strips, _, _ = geo.ring_band()
    c.rect(VSS, "M7", 539.0, 419.0, 647.0, 421.0)
    geo.via_field(c, VSS, 6, (598.6, 419.1, 601.4, 420.9), 0.5)
    info["VSS_register"] = dict(path=[[vss[0], 480.0], [540.0, 480.0], [540.0, 420.0], [647.0, 420.0]], width=2.0)
    # VSS_digital (left_7 PVSS1DGZ) and VSS_analog (top_7 PVSS2AC): M2 fingers across the band, plates up to M7.
    for name, inst, side in (("VSS_digital", "VSS_left_22", "left"), ("VSS_analog", "VSS_top_22", "top")):
        # M1 and M2 fingers both carry VSS: 7 x 1.5 um of each, 21 um of Mx, 1.7 A against the 1.3 A of ESD.CD.1gU.
        fs = sorted({tuple(p["bbox"]) for p in rb["pins"] if p["inst"] == inst and p["term"] == "VSS" and p["layer"] == "M2"
                     and (p["bbox"][2] > 109.5 if side == "left" else p["bbox"][1] < 650.5)})
        vias = 0
        top = 113.0 + 647.0                        # the north side of a strip (a, b) is y (top - b, top - a)
        for f in fs:
            for a, b in strips:
                box = (a, f[1], b, f[3]) if side == "left" else (f[0], top - b, f[2], top - a)
                c.rect(VSS, "M1", *box)
                vias += geo.via_field(c, VSS, 1, (box[0] + 0.15, box[1] + 0.15, box[2] - 0.15, box[3] - 0.15), 0.4)
                vias += via_fields(c, VSS, box, 2, 7, 0.4)
            ext = (109.8, f[1], strips[-1][1], f[3]) if side == "left" else (f[0], top - strips[-1][1], f[2], 650.2)
            c.rect(VSS, "M1", *ext)
            c.rect(VSS, "M2", *ext)
        info[name] = dict(fingers=len(fs), via_clusters=vias)
    # AVSS_guard: left_0 landing to M9, M9 along x 116 and y 563, stack onto the guard ring's north-west corner (M2).
    gfing = sorted({tuple(p["bbox"]) for p in rb["pins"] if p["inst"] == "AVSS_left_1" and p["term"] == "AVSS"
                    and p["layer"] == "M2" and p["bbox"][2] > 109.5})
    bar = landing(c, AVSS, "left", [list(f) for f in gfing], 9)
    c.rect(AVSS, "M9", bar[0], 619.0, 117.0, 621.0)
    c.rect(AVSS, "M9", 115.0, 562.0, 117.0, 621.0)
    c.rect(AVSS, "M9", 115.0, 562.0, 361.885, 564.0)
    stack_hi(c, AVSS, 360.885, 563.0, 2, 9, w=1.8)
    info["AVSS_guard"] = dict(fingers=len(gfing), bar=list(bar), corner=[360.885, 563.0])
    # Decap ports: AVDD trunks on M9, AVSS trunks on M8, DVDD/VSS on the routes above.
    for branch in geo.DECAPS:
        spec = geo.decap_spec(branch, rev)
        ports = [(n, p) for n, (p, _) in spec["ports"].items()] + [(n, p) for n, p, *_ in spec.get("extra_ports", [])]
        for net, (px, py) in ports:
            if branch == "sar" and (px, py) not in [p for p, _ in spec["ports"].values()]:
                # The SAR trunks pass south of the decap: a short stub north from each onto its near-pin port pad,
                # AVDD on M9 from its band (y 522-528), AVSS on M8 from its band (y 516.5-520.5), under the M9 band.
                if net == AVDD:
                    c.rect(net, "M9", px - 3.0, 527.0, px + 3.0, py + 1.5)
                else:
                    c.rect(net, "M8", px - 2.5, 520.0, px + 2.5, py + 1.5)
            if net == AVDD:
                stack_hi(c, net, px, py, 6, 9)
            elif net == AVSS:
                stack_hi(c, net, px, py, 6, 8)
        info[f"decap_{branch}"] = [[n, list(p)] for n, p in ports]
    # Clamps.
    # Revision 2 moves the analog clamp beside the pair clamp: it is fed like the pair clamp, by straps from the pair
    # trunks.
    for branch, bars in geo.clamp_bars(rev).items():
        x0, y0 = geo.CLAMP_ORIGIN[rev][branch]
        between_pair_trunks = branch == "pair" or (branch == "analog" and rev == 2)
        drops = []
        for net, (lo, hi) in bars.items():
            yb = (y0 + lo + y0 + hi) / 2
            if between_pair_trunks:
                xs = tuple(x0 + d for d in (30.0, 50.0, 70.0))
                if net == AVDD:                   # M9 straps up to AVDD_pair (y 315-325)
                    for x in xs:
                        c.rect(net, "M9", x - 1.5, yb - 1.0, x + 1.5, 320.0)
                else:                             # M8 straps down to AVSS_pair (y 255-265)
                    for x in xs:
                        c.rect(net, "M8", x - 1.5, 260.0, x + 1.5, yb + 1.0)
            else:
                xs = drop_xs(branch, net, rev)
            h = min(1.0, (hi - lo) / 2 - 0.1)       # plates 0.6 um or more from the M7 ring (Mx.S.6)
            for x in xs:
                clamp_drop(c, net, x, yb, h)
                drops.append([net, x, yb])
        info[f"clamp_{branch}"] = drops
    return c, info


# Revision 4 clamp feed (Layout/design/chip_clamp_feed.py). The drops above feed each clamp's 99 um M4 bars at one
# place, so the far M3 terminal strips hang on the thin bar. This adds a top-metal strap over each bar (AVDD on M9,
# AVSS on M8, the trunk metals) and a drop stack every FEED_PITCH um along it: the M4-M7 via fields and the VIA7/VIA8
# pairs of the drops above. Stacks keep 0.6 um from the core VSS ring's M7 band and M6 ties, and their M8 pads clear
# the other net's M8 trunk; the pair clamp also gets straps every 10 um up to AVDD_pair (M9) and down to AVSS_pair (M8).
FEED_PITCH = 6.0
FEED_KEEP_X = {  # x ranges (die um) a stack centre stays out of, per clamp and net
    "analog": {AVDD: [(433.6, 446.4)], AVSS: []},             # AVSS trunk M8 x 435-445
    "pair": {AVDD: [(0.0, 131.9)], AVSS: [(0.0, 131.9)]},     # west M7 band x 113-130.5
    "sar": {AVDD: [(593.6, 606.4), (628.1, 999.0)], AVSS: [(628.1, 999.0)]},   # AVSS trunk x 595-605, east M7 band
}


def clamp_feed(rev=1):
    """Content of the revision 4 clamp feed: straps and drop stacks along every clamp bar (origins of revision rev)."""
    c = Content()
    info = {}
    for branch, bars in geo.clamp_bars(rev).items():
        x0, y0 = geo.CLAMP_ORIGIN[rev][branch]
        info[branch] = {}
        for net, (lo, hi) in bars.items():
            yb = (y0 + lo + y0 + hi) / 2
            strap = "M9" if net == AVDD else "M8"
            c.rect(net, strap, x0 + 0.5, y0 + lo, x0 + 99.5, y0 + hi)
            if branch == "pair":                   # straps every 10 um to the pair trunks
                for x in [x0 + 5.0 + 10.0 * k for k in range(10)]:
                    if net == AVDD:
                        c.rect(net, "M9", x - 1.5, y0 + lo, x + 1.5, 320.0)
                    else:
                        c.rect(net, "M8", x - 1.5, 260.0, x + 1.5, y0 + hi)
            h = min(1.0, (hi - lo) / 2 - 0.1)
            xs = []
            x = x0 + 2.0
            while x <= x0 + 98.0:
                if not any(a <= x <= b for a, b in FEED_KEEP_X[branch][net]) and \
                        all(abs(x - d) >= 3.0 for d in drop_xs(branch, net, rev)):
                    xs.append(round(x, 3))
                x += FEED_PITCH
            for x in xs:
                clamp_drop(c, net, x, yb, h)
            info[branch][net] = dict(strap=[strap, x0 + 0.5, y0 + lo, x0 + 99.5, y0 + hi], stacks=xs)
    return c, info


def build_script(identity, readback_id, view=VIEW, core_view=None, rev=1, core_cell="sar8_adc_core"):
    """build.il of the integrated chip view. With core_view, the copied XADC instance is placed on that view of
    core_cell (sar8_adc_core, or a filled wrapper of it) instead of layout_route_guard, at the same origin: the
    core's boundary pins must not move. rev selects the object views (object_views)."""
    from Layout.design.chip_objects import WORK, build_script as bs
    rb = json.loads((ROOT / "work/layout/chip" / readback_id / "ring_readback.json").read_bytes())
    c, info = content(rb, rev)
    data = dict(cell=CHIP, view=view, copy_from=[CHIP, SOURCE_VIEW], rects=c.rects, pcells=[], terminals=[],
                labels=[], instances=c.instances)
    guarded = [(CHIP, SOURCE_VIEW), ("sar8_io_ring", "layout"), ("sar8_adc_core", "layout_route_guard")]
    if view != VIEW:
        guarded.append((CHIP, VIEW))
    for other in ("layout_full_boot_r2", "layout_full_dc_fill5"):
        if view != other:
            guarded.append((CHIP, other))
    if rev >= 2:
        guarded += [(cell, v) for cell, v in object_views(2).items() if v != "layout" and (cell, v) not in
                    object_views(rev).items()]
        guarded += [(cell, "layout") for cell, v in object_views(rev).items() if v != "layout"]
    if core_view:
        data["replace_masters"] = [dict(inst="XADC", lib=config()["library"], cell=core_cell, view=core_view)]
        guarded.append((core_cell, core_view))
    out = bs(identity, data, guarded=guarded + list(object_views(rev).items()))
    write_json(WORK / identity / "routes.json", info)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("identity")
    ap.add_argument("--readback", required=True, help="ring readback directory under work/layout/chip")
    ap.add_argument("--view", default=VIEW, help="chip view to build (a new name leaves layout_full untouched)")
    ap.add_argument("--core-view", help="view for XADC instead of sar8_adc_core/layout_route_guard")
    ap.add_argument("--core-cell", default="sar8_adc_core", help="cell of --core-view (e.g. a filled core wrapper)")
    ap.add_argument("--objects-rev", type=int, choices=(1, 2, 3), default=1,
                    help="object views: 2 = grown pad decaps, 3 = clamps back in place and MOM in the analog decap")
    a = ap.parse_args()
    if a.view != VIEW and not a.core_view:
        raise SystemExit("A new chip view needs --core-view")
    print(build_script(a.identity, a.readback, a.view, a.core_view, a.objects_rev, a.core_cell))


if __name__ == "__main__":
    main()
