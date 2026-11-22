"""Geometry of the chip-level objects of Layout/design/io_ring.json, in die coordinates (5 nm grid).

- `clamps`: sar8_esd_clamps, the three PCLAMPC_H_G (100 x 22 um, VDDESD/VSSESD on alternating full-height M3
  strips) at their reserved origins, R0, each with an M4 bar per terminal (VIA3 onto every same-net strip). The bars
  sit where the branch trunks can drop onto them outside the core VSS ring's M7 band.
- `decap_<branch>`: sar8_decap_<branch>, thin-oxide nmoscap (the core's 2.5 / 0.8 um unit, abutted rows, PLUS = gate
  on the supply, MINUS = N-well on the ground) filling the reserved region minus the clamp; M3 straps on every
  fourth column and M4 straps on every M2 rail form the mesh; vertical M5 bars tie the mesh; each net's port is an
  M5 landing pad under its trunk, reached through an M5 neck that sets the series resistance (ESR) near 2 ohm.
- `vss_ring`: sar8_core_vss_ring, the core VSS ring on M7. DRM 9.3.4 (ESD.CD.1gU): Mx carries 81.25 mA/um under a
  100 ns TLP pulse, so the 1.3 A primary-path current needs 16 um; Mx.W.3 limits a line to 4.5 um, so four 4.0 um
  rings 0.5 um apart (Mx.S.6), tied by VIA6 onto M6 cross bars at two places per side.
- `guard_ring`: sar8_adc_guard_ring, the 2 um P+ ring (OD, PP, contacts, M1 and M2 frames) centred 3 um outside
  the ADC outline on AVSS_CORE, with an M1/M2 strap to the core's 0_guard pin. Nothing else is on M1/M2 there; routes
  cross on M3 and above (cross_min_layer).
Each content function returns (content, summary); content is the Layout/design/chip_objects.py build format.
"""
import json
import math

from Layout.design.toplevel_full_routes import PX, UNIT, Content, nm_array
from Layout.design.toplevel_routes import snap
from Layout.project import ROOT

AVDD, AVSS, DVDD, VSS = "AVDD_CORE", "AVSS_CORE", "DVDD", "VSS"
SHEET_OHM = 0.428                     # M2-M7 RPERSQ, tsmcn28_9lm6X1Z1URDL.tlef


def plan():
    return json.loads((ROOT / "Layout/design/io_ring.json").read_text(encoding="utf-8"))


def region(pid):
    return next(r for r in plan()["reserved_regions"] if r["id"] == pid)


def ring_band():
    """The M7 band of the core VSS ring: four strips from the plan's outer edge inward."""
    # The outer edge is the plan's bbox (113 / 647): the pad landings of the chip routes put M3-M9 plates in the
    # 2.4 um band inside the IO cells (Layout/design/chip_routes.py BAND), 0.6 um away.
    r = region("core_vss_ring")
    outer = r["bbox"][0][0], r["bbox"][1][0]                      # 113 .. 647
    strips = [(outer[0] + k * 4.5, outer[0] + k * 4.5 + 4.0) for k in range(4)]
    return outer, strips, outer[0] + 17.5, outer[1] - 17.5          # inner edges 130.5 / 629.5


def finish(c, cell, view="layout"):
    content = dict(cell=cell, view=view, rects=c.rects, pcells=c.pcells, terminals=c.terminals,
                   labels=c.labels, instances=getattr(c, "instances", []))
    return content


# ------------------------------------------------------------------------------------------------ clamps
CLAMP_REGIONS = {"analog": "pclampc_analog", "pair": "pclampc_pair", "sar": "pclampc_sar"}
# Clamp origins per revision (die um). Revision 1: the io_ring.json regions as first drawn (view layout). Revision 2
# (view layout_r2): the analog clamp leaves the analog decap region, which then reaches its planned capacitance; it
# sits beside the pair clamp between AVDD_pair (y 320) and AVSS_pair (y 260), as the analog region holds no other
# 100 x 22 um space and nothing outside the VINN/VINP pair may connect to the analog trunk.
CLAMP_ORIGIN = {1: {"analog": (360.0, 622.0), "pair": (120.0, 279.0), "sar": (536.0, 600.0)},
                2: {"analog": (230.0, 279.0), "pair": (120.0, 279.0), "sar": (536.0, 600.0)}}
# Bars (y offsets inside the 22 um clamp, low/high) per clamp: the trunks drop onto them outside the M7 ring band.
CLAMP_BARS = {
    "analog": {AVDD: (0.6, 3.6), AVSS: (4.4, 7.4)},     # band starts at y 630 = clamp y 8: both bars below it
    "pair": {AVSS: (0.6, 5.0), AVDD: (17.0, 21.4)},     # AVSS_pair runs below (y 260), AVDD_pair above (y 320)
    "sar": {AVDD: (0.6, 5.0), AVSS: (17.0, 21.4)},     # bars at most 4.4 um wide (M4.W.3: 4.5)
}
CLAMP_BARS_R2 = dict(CLAMP_BARS, analog=CLAMP_BARS["pair"])  # the moved analog clamp is fed like the pair clamp
CLAMP_STRIPS = {  # PCLAMPC_H_G M3 terminal strips, x in the master (readback pclamp-readback-a)
    "VDDESD": [(6.5, 11.0), (18.5, 23.0), (30.5, 35.0), (42.5, 47.0), (52.695, 55.13), (59.0, 63.5), (71.0, 75.5),
               (83.0, 87.5), (95.0, 99.5)],
    "VSSESD": [(0.5, 5.0), (12.5, 17.0), (24.5, 29.0), (36.5, 41.0), (48.5, 51.63), (55.63, 58.0), (65.0, 69.5),
               (77.0, 81.5), (89.0, 93.5)],
}


def grid(v):
    return snap(round(round(v / 0.005) * 0.005, 3))


def via_field(c, net, layer_lo, box, pitch=0.6):
    """2 x 2 VIAx clusters on a grid inside box (both metals cover the box)."""
    x0, y0, x1, y1 = box
    nx = max(1, int(math.floor((x1 - x0 - 0.36) / pitch + 1e-9)) + 1)
    ny = max(1, int(math.floor((y1 - y0 - 0.36) / pitch + 1e-9)) + 1)
    sx = (x1 - x0 - (nx - 1) * pitch) / 2
    sy = (y1 - y0 - (ny - 1) * pitch) / 2
    n = 0
    for i in range(nx):
        for j in range(ny):
            c.mx(net, grid(x0 + sx + i * pitch), grid(y0 + sy + j * pitch), layer_lo, pads=(False, False), quad=True)
            n += 1
    return n


def clamp_bars(rev=1):
    return CLAMP_BARS if rev == 1 else CLAMP_BARS_R2


def clamps(rev=1):
    from Layout.design.chip_objects import io_library
    c = Content()
    c.instances = []
    summary = {}
    for branch in CLAMP_REGIONS:
        x0, y0 = CLAMP_ORIGIN[rev][branch]
        x1, y1 = x0 + 100.0, y0 + 22.0
        c.instances.append(dict(lib=io_library(), cell="PCLAMPC_H_G", name=f"XCLAMP_{branch.upper()}", xy=[x0, y0],
                                orient="R0", nets={"VDDESD": AVDD, "VSSESD": AVSS}))
        cuts = {}
        for net, (lo, hi) in clamp_bars(rev)[branch].items():
            term = "VDDESD" if net == AVDD else "VSSESD"
            by0, by1 = y0 + lo, y0 + hi
            c.rect(net, "M4", x0 + 0.5, by0, x1 - 0.5, by1)
            cuts[net] = 0
            for sx0, sx1 in CLAMP_STRIPS[term]:
                cuts[net] += via_field(c, net, 3, (x0 + sx0 + 0.1, by0 + 0.1, x0 + sx1 - 0.1, by1 - 0.1))
            c.pin(net, "M4", [x0 + 0.5, by0, x1 - 0.5, by1])
        summary[branch] = dict(origin=[x0, y0], bars={n: [y0 + a, y0 + b] for n, (a, b) in clamp_bars(rev)[branch].items()},
                               via3_clusters=cuts)
    return finish(c, "sar8_esd_clamps", "layout" if rev == 1 else "layout_r2"), summary


# ------------------------------------------------------------------------------------------------ decaps
NECK_W, NECK_L = 2.0, 1.0                 # a 0.5-square M6 port neck (0.21 ohm); the mesh and collector set the ESR
PAD = 3.0
DECAPS = {
    # region, plus, minus, keep-outs (x0, y0, x1, y1), ports {net: (M6 pad centre under the trunk, neck direction)}
    # collector: M6 collector width (um), chosen with the ESR estimate of Layout/tools/analysis/chip_objects_record.py
    # (collector, bars and neck about 2 ohm per rail before the parallel M4 strap mesh)
    "analog": dict(region="analog_pad_decap", bbox=((326.0, 576.0), (494.0, 644.0)), plus=AVDD, minus=AVSS, collector=4.0,
                   keepout=[(359.0, 621.0, 461.0, 645.0)],
                   ports={AVDD: ((380.0, 606.0), "S"), AVSS: ((440.0, 606.0), "N")}),
    "pair": dict(region="pair_pad_decap", bbox=((370.0, 300.0), (450.0, 442.0)), plus=AVDD, minus=AVSS, keepout=[],
                 collector=2.0,
                 ports={AVDD: ((407.885, 390.0), "N"), AVSS: ((411.885, 360.0), "S")}),
    "sar": dict(region="sar_pad_decap", bbox=((530.0, 528.0), (644.0, 644.0)), plus=AVDD, minus=AVSS, collector=4.0,
                keepout=[(535.0, 599.0, 637.0, 623.0)],
                ports={AVDD: ((560.0, 585.0), "S"), AVSS: ((600.0, 550.0), "N")}),
    "dvdd": dict(region="dvdd_decap", bbox=((580.0, 340.0), (640.0, 426.0)), plus=DVDD, minus=VSS, keepout=[],
                 collector=2.0,
                 ports={DVDD: ((600.0, 380.0), "S"), VSS: ((600.0, 420.0), "S")}),
}


# Revision 2 (views layout_r2): each decap grown to its planned capacitance (io_ring.json planning_capacitance_pF), in
# its own branch's region. Analog: the clamp leaves (CLAMP_ORIGIN 2) and the region reaches y 646.5, 1.1 um below the
# pad landing band; nothing outside the VINN/VINP pair can join the analog trunk without crossing VIN. SAR: west to
# x 510 (9.5 um from the VINP route edge; 6 um is the plan's minimum) and to 646.5 north and east. Pair: east to 452.
# DVDD: west to 578, ports unchanged.
# Ports sit next to the ADC pins (the trunk ends) so the ring feed from the bulk to the pins stays short, the ground
# (M8) port nearest. Analog and pair: one port per net there replaces the revision 1 port; its ESR is about 2 ohm per
# rail on its own. SAR: the revision 1 ports stay, with a 2 um collector, and extra_ports (net, pad, side, collector)
# add near-pin ports at the region's south-west corner; the two in parallel give about 2 ohm per rail. The SAR trunks
# run below the region (y 516.5-528), so the chip view draws short stubs north onto these pads
# (Layout/design/chip_integration.py).
DECAPS_R2 = {
    "analog": dict(bbox=((326.0, 576.0), (494.0, 646.5)), keepout=[],
                   ports={AVSS: ((414.0, 579.0), "N"), AVDD: ((406.0, 588.0), "N")}),
    "pair": dict(bbox=((370.0, 300.0), (452.0, 442.0)),
                 ports={AVSS: ((413.885, 438.0), "S"), AVDD: ((405.885, 427.5), "N")}),
    "sar": dict(bbox=((510.0, 528.0), (646.5, 646.5)), collector=2.0,
                extra_ports=[(AVSS, (524.0, 529.5), "N", 4.0), (AVDD, (515.0, 539.0), "N", 4.0)]),
    "dvdd": dict(bbox=((578.0, 340.0), (640.0, 426.0))),
}


def decap_spec(branch, rev=1):
    return dict(DECAPS[branch], **(DECAPS_R2[branch] if rev == 2 else {}))


def subtract(box, cuts):
    """Rectangles covering box minus the keep-outs (horizontal slabs)."""
    out = [box]
    for k in cuts:
        nxt = []
        for b in out:
            x0, y0, x1, y1 = b
            kx0, ky0, kx1, ky1 = k
            if kx1 <= x0 or kx0 >= x1 or ky1 <= y0 or ky0 >= y1:
                nxt.append(b)
                continue
            if ky0 > y0:
                nxt.append((x0, y0, x1, ky0))
            if ky1 < y1:
                nxt.append((x0, ky1, x1, y1))
            if kx0 > x0:
                nxt.append((x0, max(y0, ky0), kx0, min(y1, ky1)))
            if kx1 < x1:
                nxt.append((kx1, max(y0, ky0), x1, min(y1, ky1)))
        out = nxt
    # A slab must hold M5 bars of both nets (6.5 um apart), so narrower ones stay empty.
    return [b for b in out if b[2] - b[0] >= 14 and b[3] - b[1] > 4]


def mesh(c, arr):
    """M3 straps on every fourth column (plus at phase 0, minus at phase 2) with VIA2 onto same-net rails, and an M4
    strap on every M2 rail with VIA3 where it crosses a same-net M3 strap."""
    lo = min(a for n, a, b in arr["rails"])
    hi = max(b for n, a, b in arr["rails"])
    straps = {arr["plus"]: [], arr["minus"]: []}
    for j, xc in enumerate(arr["cols"]):
        k = round((arr["xs"][j] - arr["phase"]) / PX) % 4
        net = arr["plus"] if k == 0 else arr["minus"] if k == 2 else None
        if net is None:
            continue
        c.rect(net, "M3", xc - 0.15, lo - 0.15, xc + 0.15, hi + 0.15)    # encloses the outer rails' VIA3 cuts
        straps[net].append(xc)
        for n, a, b in arr["rails"]:
            if n != net:
                continue
            y = (a + b) / 2
            dys = (-0.065, 0.065) if b - a >= 0.28 else (0.0,)
            for cx in (xc - 0.065, xc + 0.065):
                for dy in dys:
                    c.rect(net, "VIA2", cx - 0.025, y + dy - 0.025, cx + 0.025, y + dy + 0.025)
    xl, xr = arr["x"]
    m4 = []
    for n, a, b in arr["rails"]:
        y = snap((a + b) / 2)
        c.rect(n, "M4", xl, y - 0.2, xr, y + 0.2)
        m4.append((n, y))
        for xc in straps[n]:
            c.mx(n, xc, y, 3, pads=(False, False), quad=True)
    return dict(m4=m4, x=(xl, xr), y=(lo - 0.15, hi + 0.15), straps={k: len(v) for k, v in straps.items()})


def decap(branch, rev=1):
    spec = decap_spec(branch, rev)
    reg = region(spec["region"])
    (rx0, ry0), (rx1, ry1) = spec["bbox"]
    plus, minus = spec["plus"], spec["minus"]
    c = Content()
    boxes = subtract((rx0 + 0.5, ry0 + 0.5, rx1 - 0.5, ry1 - 0.5), spec["keepout"])
    # Slabs that share an edge keep 1.2 um apart, so the N-wells of facing rows do not come too close (NW.S.2).
    shared = [(i, j) for i, b1 in enumerate(boxes) for j, b2 in enumerate(boxes)
              if i != j and abs(b1[3] - b2[1]) < 1e-6 and b1[0] < b2[2] and b2[0] < b1[2]]
    boxes = [list(b) for b in boxes]
    for i, j in shared:
        boxes[i][3] = min(boxes[i][3], boxes[j][1] - 0.6) if boxes[i][3] > boxes[j][1] - 0.6 else boxes[i][3]
        boxes[j][1] = max(boxes[j][1], boxes[i][3] + 1.2)
    boxes = [tuple(b) for b in boxes]
    arrays = []
    for k, (x0, y0, x1, y1) in enumerate(boxes):
        arr = nm_array(c, f"DP{branch[0].upper()}{k}", [[x0, y0], [x1, y1]], plus, minus, phase_x=rx0 + 0.5)
        if arr:
            arrays.append(mesh(c, arr) | dict(box=(x0, y0, x1, y1)))
    # Vertical M5 bars about 6.5 um apart, alternating nets, an even number spread from edge to edge: the first (plus)
    # and the last (minus) bar run beside any keep-out, so both nets reach every slab. A bar spans every array that
    # covers its x and crosses the gaps between them unless a keep-out lies in the gap; VIA4 onto same-net M4 straps.
    bars = {plus: [], minus: []}
    xmin = min(a["x"][0] for a in arrays) + 1.6
    xmax = max(a["x"][1] for a in arrays) - 1.6
    n = max(2, 2 * int(((xmax - xmin) / 6.5 + 1) // 2))
    pitch = (xmax - xmin) / (n - 1)
    for k in range(n):
        x = snap(round(round((xmin + k * pitch) / 0.005) * 0.005, 3))
        net = plus if k % 2 == 0 else minus
        spans = sorted(((a["y"][0], a["y"][1], i) for i, a in enumerate(arrays)
                        if a["x"][0] + 0.5 <= x - 1.0 + 1e-6 and x + 1.0 <= a["x"][1] - 0.5 + 1e-6))
        merged = []
        for lo, hi, i in spans:
            blocked = merged and any(kx0 < x + 1.5 and x - 1.5 < kx1 and ky0 < lo and merged[-1][1] < ky1
                                     for kx0, ky0, kx1, ky1 in spec["keepout"])
            if merged and not blocked:
                merged[-1][1] = max(merged[-1][1], hi)
                merged[-1][2].append(i)
            else:
                merged.append([lo, hi, [i]])
        for lo, hi, members in merged:
            c.rect(net, "M5", x - 1.0, lo, x + 1.0, hi)
            bars[net].append((x, lo, hi))
            for i in members:
                for n_, y in arrays[i]["m4"]:
                    if n_ == net:
                        for dx in (-0.5, 0.0, 0.5):
                            c.mx(net, snap(x + dx), y, 4, pads=(False, False), quad=True)
    # Ports: per net an M6 collector across the bars (VIA5 onto every same-net bar), an M6 neck of NECK_L x NECK_W and
    # an M6 landing pad under the trunk, where the integration drops the trunk's via stack.
    ports = {}
    used = []
    entries = [(net, net, p, spec["collector"]) for net, p in spec["ports"].items()]
    entries += [(net, f"{net}#2", (xy, side), cwidth) for net, xy, side, cwidth in spec.get("extra_ports", [])]
    for net, key, ((px, py), side), cwidth in entries:
        h = PAD / 2
        sgn = 1 if side == "N" else -1
        pad = [px - h, py - h, px + h, py + h]
        ny0, ny1 = sorted((py + sgn * h, py + sgn * (h + NECK_L)))
        neck = [px - NECK_W / 2, ny0, px + NECK_W / 2, ny1]
        cw = cwidth / 2
        yc = py + sgn * (h + NECK_L + cw)
        on = [b for b in bars[net] if b[1] + 0.5 <= yc - cw and yc + cw <= b[2] - 0.5]
        if len(on) < 2:
            raise ValueError(f"{branch} {net}: the collector at y {yc} meets fewer than two bars")
        span = [b[0] for b in bars[plus] + bars[minus] if b[1] + 0.5 <= yc - cw and yc + cw <= b[2] - 0.5]
        collector = [min(span) - 1.0, yc - cw, max(span) + 1.0, yc + cw]
        for box in (pad, neck, collector):
            for other_net, other in used:
                if other_net != net and box[0] < other[2] + 1.0 and other[0] < box[2] + 1.0 and box[1] < other[3] + 1.0 and other[1] < box[3] + 1.0:
                    raise ValueError(f"{branch} {net}: port metal too close to the other net's port")
        c.rect(net, "M6", *pad)
        c.rect(net, "M6", *neck)
        c.rect(net, "M6", *collector)
        rows = [0.0] if cw < 1.5 else [-1.2, 0.0, 1.2]
        for b in on:
            for dx in (-0.5, 0.0, 0.5):
                for dy in rows:
                    c.mx(net, snap(b[0] + dx), snap(yc + dy), 5, pads=(False, False), quad=True)
        used += [(net, pad), (net, neck), (net, collector)]
        c.pin(net, "M6", pad)
        ports[key] = dict(net=net, pad=pad, neck=neck, collector=collector, neck_ohm=round(SHEET_OHM * NECK_L / NECK_W, 3),
                          collector_bars=len(on))
    devices = sum(v["devices"] for v in c.summary.values())
    gate = sum(v["gate_um2"] for v in c.summary.values())
    summary = dict(region=spec["region"], bbox=[list(v) for v in spec["bbox"]], revision=rev,
                   planning_pF=reg.get("planning_capacitance_pF"),
                   devices=devices, gate_um2=round(gate, 1), arrays=len(arrays),
                   bars={n: len(v) for n, v in bars.items()}, ports=ports)
    return finish(c, f"sar8_decap_{branch}", "layout" if rev == 1 else "layout_r2"), summary


# ------------------------------------------------------------------------------------------------ core VSS ring
TIE_AT = (150.0, 610.0)               # tie positions along each side, clear of the routes that cross the band


def vss_ring():
    c = Content()
    (lo, hi), strips, inner_lo, inner_hi = ring_band()
    for a, b in strips:
        w = b - a
        # Each strip is a closed square ring of width w between the offsets a and (lo + hi) - a.
        A, B = a, lo + hi - a
        c.rect(VSS, "M7", A, A, B, A + w)          # south
        c.rect(VSS, "M7", A, B - w, B, B)          # north
        c.rect(VSS, "M7", A, A + w, A + w, B - w)  # west
        c.rect(VSS, "M7", B - w, A + w, B, B - w)  # east
    # Ties: straight M6 bars across the four strips of each side at two places, with VIA6 fields only where a bar
    # crosses a strip (each strip is a closed ring; the ties make the four one conductor).
    vias = 0
    for at in TIE_AT:
        for side in ("S", "N", "W", "E"):
            for a, b in strips:
                o0, o1 = (a, b) if side in ("S", "W") else (lo + hi - b, lo + hi - a)
                if side in ("S", "N"):
                    bar = (at - 1.0, lo if side == "S" else hi - 17.5, at + 1.0, lo + 17.5 if side == "S" else hi)
                    cross = (at - 1.0, o0, at + 1.0, o1)
                else:
                    bar = (lo if side == "W" else hi - 17.5, at - 1.0, lo + 17.5 if side == "W" else hi, at + 1.0)
                    cross = (o0, at - 1.0, o1, at + 1.0)
                c.rect(VSS, "M6", *bar)
                vias += via_field(c, VSS, 6, (cross[0] + 0.2, cross[1] + 0.2, cross[2] - 0.2, cross[3] - 0.2))
    for a, b in strips[:1]:
        c.pin(VSS, "M7", [lo + 20, a, lo + 24, b])
    summary = dict(layer="M7", band=[lo, hi], strips=[list(s) for s in strips], metal_width_um=4 * 4.0,
                   esd_current_A=round(4 * 4.0 * 0.08125, 3), rule="DRM 9.3.4 ESD.CD.1gU (Mx 81.25 mA/um, 1.3 A)",
                   tie_via6_clusters=vias, ties_at=list(TIE_AT), inner_edge=[inner_lo, inner_hi])
    return finish(c, "sar8_core_vss_ring"), summary


# ------------------------------------------------------------------------------------------------ guard ring
GUARD_W = 2.0
CO, CO_PITCH = 0.04, 0.16


def guard_ring():
    reg = region("adc_guard_ring")
    (x0, y0), (x1, y1) = reg["bbox"]                       # outer edge of the 2 um ring
    adc = region("adc_core")["bbox"]
    c = Content()
    w = GUARD_W

    def frame(layer, a0, b0, a1, b1, ww):
        c.rect(AVSS, layer, a0, b0, a1, b0 + ww)
        c.rect(AVSS, layer, a0, b1 - ww, a1, b1)
        c.rect(AVSS, layer, a0, b0 + ww, a0 + ww, b1 - ww)
        c.rect(AVSS, layer, a1 - ww, b0 + ww, a1, b1 - ww)

    for layer in ("OD", "M1", "M2"):
        frame(layer, x0, y0, x1, y1, w)
    frame("PP", x0 - 0.1, y0 - 0.1, x1 + 0.1, y1 + 0.1, w + 0.2)
    h = CO / 2
    rows = [0.14 + 0.43 * k for k in range(5)]               # five contact rows across the 2 um OD
    cuts = 0
    for off in rows:
        for x in [snap(x0 + 0.14 + CO_PITCH * k) for k in range(int((x1 - x0 - 0.28) / CO_PITCH) + 1)]:
            for y in (y0 + off, y1 - off):
                c.rect(AVSS, "CO", x - h, y - h, x + h, y + h)
                cuts += 2 / 2
        for y in [snap(y0 + w + 0.1 + CO_PITCH * k) for k in range(int((y1 - y0 - 2 * w - 0.2) / CO_PITCH) + 1)]:
            for x in (x0 + off, x1 - off):
                c.rect(AVSS, "CO", x - h, y - h, x + h, y + h)
                cuts += 1
    # VIA1 2 x 2 clusters every 1 um along the ring, two rows 0.8 um apart across its width.
    m = w / 2
    pts = [(x, y + d) for x in [snap(x0 + m + k) for k in range(int(x1 - x0 - w) + 1)] for y in (y0 + m, y1 - m)
           for d in (-0.4, 0.4)]
    pts += [(x + d, y) for y in [snap(y0 + w + 0.5 + k) for k in range(int(y1 - y0 - 2 * w))] for x in (x0 + m, x1 - m)
            for d in (-0.4, 0.4)]
    for x, y in pts:
        c.mx(AVSS, snap(x), snap(y), 1, pads=(False, False), quad=True)
    # Strap to the core's 0_guard pin (M2 at core x 121.6-122, y 51.2-51.8: die x 485.485-485.885, y 500.2-500.8).
    ox, oy = adc[0]
    pin = [ox + 121.6, oy + 51.2, ox + 122.0, oy + 51.8]
    for layer in ("M1", "M2"):
        c.rect(AVSS, layer, pin[0], pin[1], x1 - w + 0.01, pin[3])
    for x in (pin[2] + 0.5, pin[2] + 1.5):
        c.mx(AVSS, snap(x), snap((pin[1] + pin[3]) / 2), 1, axis="x", pads=(False, False))
    c.pin(AVSS, "M2", [x0, y1 - w, x0 + w, y1])           # north-west corner: the AVSS_guard landing
    summary = dict(outer=[x0, y0, x1, y1], width_um=w, contacts=int(cuts), via1_clusters=len(pts),
                   strap=[pin[0], pin[1], x1 - w, pin[3]], core_pin="0_guard (M2)", cross_min_layer=reg["cross_min_layer"])
    return finish(c, "sar8_adc_guard_ring"), summary


OBJECTS = {"clamps": clamps, "vss_ring": vss_ring, "guard_ring": guard_ring, "clamps_r2": lambda: clamps(2),
           **{f"decap_{b}": (lambda b=b: decap(b)) for b in DECAPS},
           **{f"decap_{b}_r2": (lambda b=b: decap(b, 2)) for b in DECAPS}}
