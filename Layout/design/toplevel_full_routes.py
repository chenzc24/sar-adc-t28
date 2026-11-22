"""Geometry of Stage 4b on top of layout_route_int (phase 1): boundary signal routes, the three supply branches
with their decoupling and grid, and the shield tie, in the core frame (= the sar8_adc_core frame), 5 nm grid.

Supply branches meet only at the ADC boundary pins (floorplan power_plan.join). Every branch uses the top
names VDD! and 0; its in-core pieces are disjoint and LVS joins them by name at the core boundary.
- analog: north pins on M9; a VDD M8 band (y 76.2-76.6) and a VSS M8 band (y 77.0-77.4) along the Bootstrap
  cells' south edge, above the output channel and below the VIN trunk feet; via stacks onto the Bootstrap M5
  rails; region straps VSS on M8 and VDD on M9; the comparator strips are fed through the channel (VDD M8,
  VSS M7) and strap onto the comparator's top VDD bar and its P+ ring sides; the east VSS M7 drop ties the
  channel and corridor shields (VSS_SHIELD) to VSS.
- pair: south pins VDD! on M9 and 0 on M8 to the pair's M6 terminals, then east along the south strip.
- SAR: east pins into sar_decap_north, down over the macro's M6 stripes with stacks on the M7 rows between the
  D tracks, and on into sar_supply_and_decap.
Decoupling is nmoscap (gate on VDD, N-well on VSS) in abutted rows that alternate R0/MX, so facing rows share
one M2 rail. The reference network (RREF, CREF, VREF pins) is phase 2.
"""
import math

from Layout.design.toplevel_routes import plan, snap

VDD, GND, SHIELD = "VDD!", "0", "VSS_SHIELD"
VIA = {(1, 2): "VIA1", (2, 3): "VIA2", (3, 4): "VIA3", (4, 5): "VIA4", (5, 6): "VIA5", (6, 7): "VIA6", (7, 8): "VIA7",
       (8, 9): "VIA8"}
UNIT = dict(wr=2.5, lr=0.8)          # poly 2.0 um2 < PO.A.3 (3 um2); ~62 % local poly (PO.DN.4.1)
STRIP_UNIT = dict(wr=2.0, lr=0.8)    # comparator strips are 2.6 um tall
PX = 1.3                              # column pitch (NP abutted) for lr 0.8
D_ROWS = [53.4 + 1.2 * k for k in range(8)]
SAMPLE_Y = 65.4
FREE_ROWS = [52.8] + [y + 0.6 for y in D_ROWS[:-1]] + [63.3, 67.2]   # M7 rows clear of the D/SAMPLE tracks


class Content:
    def __init__(self):
        self.rects, self.pcells, self.terminals, self.labels = [], [], [], []
        self.summary = {}

    def rect(self, net, layer, x0, y0, x1, y1, purpose="drawing"):
        x0, x1 = sorted((snap(x0), snap(x1)))
        y0, y1 = sorted((snap(y0), snap(y1)))
        if not (x0 < x1 and y0 < y1):
            raise ValueError(f"Empty rect {net} {layer} {x0} {y0} {x1} {y1}")
        self.rects.append(dict(net=net, layer=layer, purpose=purpose, box=[x0, y0, x1, y1]))

    def pin(self, net, layer, box):
        t = next((t for t in self.terminals if t["net"] == net), None)
        if t is None:
            t = dict(net=net, pins=[])
            self.terminals.append(t)
        t["pins"].append(dict(layer=layer, box=[snap(v) for v in box]))

    def mx(self, net, x, y, lower, axis="y", pads=(True, True), quad=False):
        """Two 0.05 um cuts 0.13 um apart (VIAx.R.2), or a 2 x 2 cluster (VIAx.R.3, metal wider than 0.44 um);
        0.1 x 0.23 um pads (0.23 x 0.23 for a cluster)."""
        dx, dy = (0.0, 0.065) if axis == "y" else (0.065, 0.0)
        if quad:
            cuts = [(x + sx * 0.065, y + sy * 0.065) for sx in (-1, 1) for sy in (-1, 1)]
        else:
            cuts = [(x - dx, y - dy), (x + dx, y + dy)]
        for cx, cy in cuts:
            self.rect(net, VIA[(lower, lower + 1)], cx - 0.025, cy - 0.025, cx + 0.025, cy + 0.025)
        ex, ey = (0.115, 0.115) if quad else (0.05, 0.115) if axis == "y" else (0.115, 0.05)
        for m, want in zip((lower, lower + 1), pads):
            if want:
                self.rect(net, f"M{m}", x - ex, y - ey, x + ex, y + ey)

    def via7(self, net, x, y, m7_pad=True, m8_pad=True, n=1):
        """One VIA7 (0.36 um), or two 0.70 um apart along y where the M8 is wider than 1.8 um (VIA7.R.2);
        M7 0.52 x 0.40 (0.08/0.02), M8 0.76 x 0.76 (area >= 0.565)."""
        dy = 0.35 if n == 2 else 0.0
        for cy in sorted({y - dy, y + dy}):
            self.rect(net, "VIA7", x - 0.18, cy - 0.18, x + 0.18, cy + 0.18)
        if m7_pad:
            self.rect(net, "M7", x - 0.26, y - 0.2 - dy, x + 0.26, y + 0.2 + dy)
        if m8_pad:
            self.rect(net, "M8", x - 0.38, y - 0.38 - dy, x + 0.38, y + 0.38 + dy)

    def via8(self, net, x, y, axis="y", m8_pad=True):
        """Two VIA8 (0.36 um, 0.70 um pitch); M8 0.08 enclosure. The M9 above must be a >= 2 um strap."""
        dx, dy = (0.0, 0.35) if axis == "y" else (0.35, 0.0)
        for s in (-1, 1):
            cx, cy = x + s * dx, y + s * dy
            self.rect(net, "VIA8", cx - 0.18, cy - 0.18, cx + 0.18, cy + 0.18)
        if m8_pad:
            ex, ey = (0.26, 0.61) if axis == "y" else (0.61, 0.26)
            self.rect(net, "M8", x - ex, y - ey, x + ex, y + ey)

    def stack(self, net, x, y, lo, hi, axis="y", via8_axis="y", n7=1):
        """Via stack from metal lo to metal hi at (x, y): Mx cut pairs (a 2 x 2 VIA6 cluster under a VIA7 pad),
        VIA7, a VIA8 pair."""
        for m in range(lo, min(hi, 7)):
            self.mx(net, x, y, m, axis, pads=(True, m + 1 < 7), quad=(m == 6 and hi >= 8))
        if hi >= 8:
            self.via7(net, x, y, m8_pad=hi == 8, n=n7)
        else:
            self.rect(net, "M7", x - 0.05 if axis == "y" else x - 0.115, y - 0.115 if axis == "y" else y - 0.05,
                      x + 0.05 if axis == "y" else x + 0.115, y + 0.115 if axis == "y" else y + 0.05)
        if hi == 9:
            self.via8(net, x, y, via8_axis)


def regions():
    return {g["id"]: g["bbox"] for g in plan()["reserved_regions"]}


# ------------------------------------------------------------------------------------------------ decap arrays
def nm_array(c, name, box, plus, minus, unit=UNIT, first="R0", phase_x=None):
    """Abutted nmoscap rows in box; columns on the PX grid anchored at phase_x. Returns rows, rails and columns."""
    wr, lr = unit["wr"], unit["lr"]
    h = wr + 0.29
    (bx0, by0), (bx1, by1) = box
    start = bx0 + 0.28
    if phase_x is not None:
        start = phase_x + math.ceil((start - phase_x) / PX - 1e-9) * PX
    xs = []
    x = start
    while x + lr + 0.28 <= bx1 + 1e-9:
        xs.append(snap(x))
        x += PX
    nrow = int(math.floor((by1 - by0 - 0.03) / h + 1e-9))
    if not xs or nrow < 1:
        return None
    rows, y = [], by0 + 0.015
    for k in range(nrow):
        orient = first if k % 2 == 0 else ("MX" if first == "R0" else "R0")
        if orient == "R0":
            oy = y + 0.115
            pb, mb = (oy - 0.05, oy), (oy + wr - 0.06, oy + wr)
        else:
            oy = y + wr + 0.175
            pb, mb = (oy, oy + 0.05), (oy - wr, oy - wr + 0.06)
        rows.append((orient, snap(oy), pb, mb))
        y += h
    for k, (orient, oy, _, _) in enumerate(rows):
        for j, x in enumerate(xs):
            c.pcells.append(dict(cell="nmoscap", name=f"{name}_{k}_{j}", xy=[x, oy], orient=orient,
                                 # One dummy per device keeps local poly near 62 % (PO.DN.4.1); the first column
                                 # keeps both, so every varactor gate has poly within 0.8 um on both sides (PO.S.35).
                                 params=dict(wr=f"{wr}u", lr=f"{lr}u", m="1", dummyPoly="Both" if j == 0 else "Right"),
                                 nets=dict(PLUS=plus, MINUS=minus)))
    bars = sorted([(plus, pb) for _, _, pb, _ in rows] + [(minus, mb) for _, _, _, mb in rows], key=lambda b: b[1][0])
    groups = []
    for net, (lo, hi) in bars:
        if groups and groups[-1][0] == net and lo - groups[-1][2] < 0.6:
            groups[-1][2] = hi
            groups[-1][3].append((lo, hi))
        else:
            groups.append([net, lo, hi, [(lo, hi)]])
    xl, xr = xs[0] - 0.09, xs[-1] + lr + 0.09
    rails = []
    for net, lo, hi, members in groups:
        c.rect(net, "M2", xl, lo - 0.05, xr, hi + 0.05)
        rails.append((net, lo - 0.05, hi + 0.05))
        for blo, bhi in members:
            cy = (blo + bhi) / 2
            for x in xs:
                for off in (-0.195, -0.065, 0.065, 0.195):
                    cx = x + lr / 2 + off
                    c.rect(net, "VIA1", cx - 0.025, cy - 0.025, cx + 0.025, cy + 0.025)
    cols = [snap(x + lr / 2) for x in xs]
    c.summary[name] = dict(devices=len(xs) * nrow, gate_um2=round(len(xs) * nrow * wr * lr, 3), cols=len(xs), rows=nrow,
                           box=[xl, rails[0][1], xr, rails[-1][2]])
    return dict(rows=rows, rails=rails, cols=cols, xs=xs, x=(xl, xr), plus=plus, minus=minus, lr=lr,
                phase=phase_x if phase_x is not None else start)


def array_straps(c, arr, plus_layer="M9", minus_layer="M8", y_ext=None, skip=(), y_clip=None, wide=()):
    """M3 straps on every 4th column (plus at phase 0, minus at phase 2) with VIA2 onto same-net rails, a via stack
    at each same-net rail up to the M8/M9 strap above. y_ext = {layer: (lo, hi)} extends the M8/M9 straps;
    columns in skip get the stacks but no M8/M9 strap (an existing trunk covers them)."""
    out = []
    for j, xc in enumerate(arr["cols"]):
        k = round((arr["xs"][j] - arr["phase"]) / PX) % 4
        net = arr["plus"] if k == 0 else arr["minus"] if k == 2 else None
        if net is None:
            continue
        ys = [(a + b) / 2 for n, a, b in arr["rails"] if n == net]
        if not ys:
            continue
        lo = min(a for n, a, b in arr["rails"])
        hi = max(b for n, a, b in arr["rails"])
        c.rect(net, "M3", xc - 0.15, lo, xc + 0.15, hi)
        layer = plus_layer if net == arr["plus"] else minus_layer
        top = int(layer[1])
        heights = {(a + b) / 2: b - a for n, a, b in arr["rails"] if n == net}
        for y in ys:
            dys = (-0.065, 0.065) if heights[y] >= 0.28 else (0.0,)
            for cx in (xc - 0.065, xc + 0.065):
                for dy in dys:
                    c.rect(net, "VIA2", cx - 0.025, y + dy - 0.025, cx + 0.025, y + dy + 0.025)
            wide8 = any(x0 <= xc <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in wide)
            c.stack(net, xc, y, 3, top, n7=2 if wide8 else 1)
        y0, y1 = min(ys) - 0.9, max(ys) + 0.9
        lo, hi = (y_ext or {}).get(layer, (None, None))
        y0, y1 = min(y0, lo) if lo is not None else y0, max(y1, hi) if hi is not None else y1
        lo, hi = (y_clip or {}).get(layer, (None, None))
        y0, y1 = max(y0, lo) if lo is not None else y0, min(y1, hi) if hi is not None else y1
        if xc in skip:
            continue
        w = 2.0 if layer == "M9" else 0.76
        c.rect(net, layer, xc - w / 2, y0, xc + w / 2, y1)
        out.append((net, layer, xc, y0, y1))
    return out


def rail_stacks(c, arr, plus_top, minus_top, every=2, via8_axis="x"):
    """Direct stacks from M2 rails (single- or two-row arrays): plus on even columns, minus on odd ones."""
    for j, xc in enumerate(arr["cols"]):
        if j % every:
            continue
        net = arr["plus"] if (j // every) % 2 == 0 else arr["minus"]
        top = plus_top if net == arr["plus"] else minus_top
        for n, a, b in arr["rails"]:
            if n == net:
                c.stack(net, xc, (a + b) / 2, 2, top, via8_axis=via8_axis)


# ------------------------------------------------------------------------------------------------- boundary signals
def boundary(c):
    for k, y in enumerate(D_ROWS):
        net = f"D{k}"
        c.rect(net, "M3", 91.8, y - 0.05, 92.18, y + 0.05)
        c.rect(net, "M3", 92.18, y - 0.025, 92.4, y + 0.025)
        c.stack(net, 91.9, y, 3, 7, axis="x")
        c.rect(net, "M7", 91.785, y - 0.05, 122.0, y + 0.05)
        c.pin(net, "M7", [121.8, y - 0.05, 122.0, y + 0.05])
    y = SAMPLE_Y
    c.rect("SAMPLE", "M3", 91.8, y - 0.05, 92.18, y + 0.05)
    c.rect("SAMPLE", "M3", 92.18, y - 0.025, 92.4, y + 0.025)
    c.stack("SAMPLE", 91.9, y, 3, 7, axis="x")
    c.rect("SAMPLE", "M7", 91.785, y - 0.05, 121.3, y + 0.05)
    c.via7("SAMPLE", 121.0, y, m8_pad=False)
    c.rect("SAMPLE", "M8", 120.62, y - 0.4, 122.0, y + 0.4)
    c.pin("SAMPLE", "M8", [121.4, y - 0.4, 122.0, y + 0.4])
    # VSS neighbour tracks of SAMPLE on M7 across the macro, tied to the SAR's M6 VSS stripes.
    for yy in (y - 0.6, y + 0.6):
        c.rect(GND, "M7", 92.6, yy - 0.05, 120.4, yy + 0.05)
        for xs in (96.31, 103.31):
            c.mx(GND, xs, yy, 6, axis="x", pads=(False, False))
    for net, x in (("VINN", 33.34), ("VINP", 58.89)):
        c.rect(net, "M5", x - 0.15, 100.95, x + 0.15, 111.0)
        c.pin(net, "M5", [x - 0.15, 110.7, x + 0.15, 111.0])


# ----------------------------------------------------------------------------------------------------- analog
A_VDD_BAND = (76.2, 76.6)
A_VSS_BAND = (77.0, 77.4)
A_X = (1.5, 81.0)


def analog(c):
    r = regions()
    c.rect(VDD, "M8", A_X[0], A_VDD_BAND[0], A_X[1], A_VDD_BAND[1])
    c.rect(GND, "M8", A_X[0], A_VSS_BAND[0], A_X[1], A_VSS_BAND[1])

    def vdd_drop(xc):
        # M9 strap -> VIA8 pair (along x) onto the VDD band, widened downward locally for the 0.08 enclosure.
        c.rect(VDD, "M8", xc - 0.61, 76.08, xc + 0.61, A_VDD_BAND[1])
        c.via8(VDD, xc, 76.34, axis="x", m8_pad=False)

    # North pins and trunks down analog_decap_slot (both on M9).
    c.rect(VDD, "M9", 43.115, 75.8, 45.115, 111.0)
    c.pin(VDD, "M9", [43.115, 110.6, 45.115, 111.0])
    vdd_drop(44.115)
    c.rect(GND, "M9", 47.115, 76.75, 49.115, 111.0)
    c.pin(GND, "M9", [47.115, 110.6, 49.115, 111.0])
    c.rect(GND, "M8", 47.54, A_VSS_BAND[0], 48.76, 77.52)
    c.via8(GND, 48.15, 77.26, axis="x", m8_pad=False)
    # Bootstrap supply rails (M5): VSS y 76.485-76.725, VDD y 76.865-77.065, x 27.855-34.695 (N) and mirror.
    for side in (1, -1):
        for x in (28.4, 30.6):
            xx = x if side == 1 else snap(92.23 - x)
            c.via7(GND, xx, 77.2, m8_pad=False)
            c.rect(GND, "M7", xx - 0.26, 76.465, xx + 0.26, A_VSS_BAND[1])
            c.mx(GND, xx, 76.605, 5, axis="x", pads=(False, False))
            c.rect(GND, "M6", xx - 0.115, 76.49, xx + 0.115, 76.72)
            c.mx(GND, xx, 76.605, 6, axis="x", pads=(False, False), quad=True)
        for x in (29.5, 31.7):
            xx = x if side == 1 else snap(92.23 - x)
            c.via7(VDD, xx, 76.4, m8_pad=False)
            c.rect(VDD, "M7", xx - 0.26, A_VDD_BAND[0], xx + 0.26, 77.105)
            c.mx(VDD, xx, 76.965, 5, axis="x", pads=(False, False))
            c.rect(VDD, "M6", xx - 0.115, 76.85, xx + 0.115, 77.08)
            c.mx(VDD, xx, 76.965, 6, axis="x", pads=(False, False), quad=True)
    # Decap regions above the bands; region straps reach the bands (VSS M8 down to 77.0, VDD M9 via VIA8).
    for rid, box in (("analog_decap_west", [[1.2, 77.6], [17.3, 109.8]]),
                     ("analog_decap_slot", [[43.2, 77.6], [49.0, 109.8]]),
                     ("analog_decap_east", [[74.95, 77.6], [81.0, 109.8]])):
        # MX first: the bottom rail is VSS next to the VSS band, so no VDD stack pad lands on it.
        arr = nm_array(c, "DA_" + rid.split("_")[-1], box, VDD, GND, first="MX")
        if not arr:
            continue
        # In the slot the VDD M9 trunk is the plus strap.
        skip = tuple(x for x in arr["cols"] if 43.115 <= x <= 45.115)
        for net, layer, xc, y0, y1 in array_straps(c, arr, y_ext={"M8": (A_VSS_BAND[0], None)}, skip=skip,
                                                   y_clip={"M8": (A_VSS_BAND[0], None)}):
            if layer == "M9":
                c.rect(net, "M9", xc - 1.0, 75.8, xc + 1.0, y0)
                vdd_drop(xc)
    # Comparator strips: one MX row (VDD gate rail on top), fed through the channel; straps onto the comparator.
    for side in (1, -1):
        m = (lambda x: x) if side == 1 else (lambda x: snap(92.23 - x))
        # East columns mirror the west ones about the comparator axis (x 46.115).
        x0, x1 = (34.6, 43.4) if side == 1 else (49.17, 57.65)
        arr = nm_array(c, "DC_" + ("W" if side == 1 else "E"), [[x0, 70.6], [x1, 73.2]], VDD, GND, unit=STRIP_UNIT,
                       first="MX")
        _, prl, prh = next(r for r in arr["rails"] if r[0] == VDD)
        _, mrl, mrh = next(r for r in arr["rails"] if r[0] == GND)
        py, my = (prl + prh) / 2, (mrl + mrh) / 2
        edge = arr["x"][1] if side == 1 else arr["x"][0]
        c.rect(VDD, "M2", edge, prl, m(43.4), prh)
        c.rect(GND, "M2", edge, mrl, m(43.4), mrh)
        fx_vdd, fx_vss = m(37.08), m(39.0)
        # VDD: M8 drop from the VDD band, stack to the gate rail.
        c.rect(VDD, "M8", fx_vdd - 0.38, py - 0.38, fx_vdd + 0.38, A_VDD_BAND[1])
        c.stack(VDD, fx_vdd, py, 2, 8)
        # VSS: VIA7 from the VSS band onto an M7 drop, stack down to the N-well rail.
        c.via7(GND, fx_vss, 77.2, m8_pad=False)
        c.rect(GND, "M7", fx_vss - 0.26, my - 0.2, fx_vss + 0.26, A_VSS_BAND[1])
        for mm in range(2, 6):
            c.mx(GND, fx_vss, my, mm, pads=(True, True))
        c.rect(GND, "M6", fx_vss - 0.115, my - 0.115, fx_vss + 0.115, my + 0.115)
        c.mx(GND, fx_vss, my, 6, pads=(False, False), quad=True)
        if side == -1:
            c.mx(GND, fx_vss, 75.3, 5, axis="x", pads=(False, False))   # shield tie onto the 75.3 track
            c.rect(GND, "M6", fx_vss - 0.115, 75.185, fx_vss + 0.115, 75.415)
            c.mx(GND, fx_vss, 75.3, 6, axis="x", pads=(False, False), quad=True)
        # Straps onto the comparator: VDD bar y 73.335-73.405 (x 45.38-46.85), VSS ring M1 sides x 45.38-45.45
        # and 46.78-46.85 (y 70.045-71.975), entered above y 71.5 (floorplan comparator_decap_*).
        xe = m(43.4)
        xs = sorted((xe, m(45.45)))
        c.rect(VDD, "M2", min(xe, m(43.25)), prl, max(xe, m(43.25)), 73.405)
        c.rect(VDD, "M2", xs[0], 73.305, xs[1], 73.405)
        c.rect(GND, "M2", min(xe, m(43.25)), mrl, max(xe, m(43.25)), 71.88)
        c.rect(GND, "M2", xs[0], 71.62, xs[1], 71.88)
        rx = m(45.415)
        for cy in (71.685, 71.815):
            c.rect(GND, "VIA1", rx - 0.025, cy - 0.025, rx + 0.025, cy + 0.025)


# ------------------------------------------------------------------------------------------------------ pair
def pair(c):
    c.rect(VDD, "M9", 43.0, 0.0, 45.0, 15.8)
    c.pin(VDD, "M9", [43.0, 0.0, 45.0, 0.6])
    c.rect(VDD, "M9", 43.0, 13.8, 47.9, 15.8)
    c.via8(VDD, 46.915, 14.565, axis="x")
    c.via7(VDD, 46.915, 14.565, m8_pad=False)
    c.rect(VDD, "M7", 46.655, 14.365, 47.175, 14.765)
    c.mx(VDD, 46.915, 14.565, 6, axis="y", pads=(False, False))
    c.rect(GND, "M8", 47.0, 0.0, 49.0, 13.6)
    c.pin(GND, "M8", [47.0, 0.0, 49.0, 0.6])
    c.rect(GND, "M8", 44.5, 12.6, 49.0, 13.6)
    c.via7(GND, 45.215, 13.365, m8_pad=False)
    c.mx(GND, 45.215, 13.365, 6, axis="y", pads=(False, False))
    # South bands: VSS M8 over the shared N-well rails, VDD M9 above the gate rails.
    c.rect(GND, "M8", 42.1, 3.6, 120.8, 4.5)
    c.rect(VDD, "M9", 43.0, 6.0, 120.8, 8.0)
    phase = 49.88
    # DP_S runs under the feeds (its columns at x 44.73/47.53 merge with them); DP_C uses the empty corridor strip
    # below the CODE stubs. All pair arrays share one column grid so their straps line up down to the south bands.
    for name, box in (("DP_S", [[42.1, 1.2], [78.4, 8.8]]), ("DP_E", [[78.7, 1.2], [120.8, 8.8]]),
                      ("DP_SE", [[93.4, 10.2], [120.8, 23.3]]), ("DP_C", [[86.0, 10.2], [90.9, 52.5]])):
        arr = nm_array(c, name, box, VDD, GND, phase_x=phase)
        if arr:
            # Southeast straps run down to the south bands over the east array, on the shared column grid.
            array_straps(c, arr, y_ext={"M8": (3.6, None), "M9": (6.0, None)}, wide=[(46.9, 0.0, 49.1, 13.6)])


# ------------------------------------------------------------------------------------------------------ SAR
SAR_STRIPES = dict(vdd=(95.51, 102.51), vss=(96.31, 103.31))


def sar(c):
    c.rect(GND, "M8", 93.3, 70.5, 122.0, 71.5)
    c.pin(GND, "M8", [121.4, 70.5, 122.0, 71.5])
    c.rect(VDD, "M9", 93.3, 73.0, 122.0, 75.0)
    c.pin(VDD, "M9", [121.4, 73.0, 122.0, 75.0])
    for xv, xs in zip(SAR_STRIPES["vdd"], SAR_STRIPES["vss"]):
        c.rect(VDD, "M9", xv - 1.0, 46.0, xv + 1.0, 75.0)
        c.rect(GND, "M8", xs - 0.11, 49.0, xs + 0.29, 71.5)
        # VDD: a continuous 0.52 um M8 strip on the stripe, VIA7 on every free row, VIA8 pairs on every other one.
        c.rect(VDD, "M8", xv - 0.26, FREE_ROWS[0] - 0.7, xv + 0.26, FREE_ROWS[-1] + 0.7)
        for i, y in enumerate(FREE_ROWS):
            if i % 2 == 0:
                c.via8(VDD, xv, y, axis="y", m8_pad=False)
            c.via7(VDD, xv, y, m8_pad=False)
            c.mx(VDD, xv, y, 6, axis="x", pads=(False, False), quad=True)
            c.via7(GND, xs + 0.09, y, m8_pad=False)
            c.rect(GND, "M7", xs - 0.17, y - 0.2, xs + 0.35, y + 0.2)
            c.mx(GND, xs, y, 6, axis="x", pads=(False, False), quad=True)
    c.rect(VDD, "M9", 93.4, 46.0, 120.8, 48.0)
    c.rect(GND, "M8", 93.4, 50.2, 120.8, 50.8)
    arr = nm_array(c, "DS_S", [[93.4, 24.7], [120.8, 45.4]], VDD, GND, phase_x=49.88)
    if arr:
        array_straps(c, arr, y_ext={"M8": (None, 50.8), "M9": (None, 48.0)})
    # North array over sar_decap_north and the south part of spare_decap_northeast (the floorplan's unassigned
    # reserve); MX first so no gate rail sits under the VSS M8 band.
    arr = nm_array(c, "DS_N", [[93.4, 71.55], [120.8, 85.6]], VDD, GND, first="MX", phase_x=49.88)
    if arr:
        array_straps(c, arr, y_ext={"M8": (70.5, None), "M9": (73.0, None)})


# ------------------------------------------------------------------------------------------------- reference
VREFP, VREFN, VREFP_T, VREFN_T = "VREFP", "VREFN", "VREFP_TRUNK", "VREFN_TRUNK"
REF_PINS = {VREFP: (67.0, 55.0), VREFN: (61.0, 49.0)}     # floorplan pins_um on the west edge, 4 um tall on M8
REF_JOIN_X = {VREFP: (2.2, 4.2), VREFN: (6.2, 8.2)}       # pad-side M9 joins, down the west strip
PAD_M9_Y = {VREFP: (1.0, 4.62), VREFN: (5.62, 9.0)}       # pad-side M9 over the resistor rows
RREF_N, RREF_PITCH = 26, 1.15                           # segments per row (two rows per rail), segment pitch
RREF = dict(w="500n", l="500n", segments=str(RREF_N), connection="Parallel", segSp="180n")
RREF_X0 = round(11.5 + RREF_PITCH * RREF_N - 0.12, 3)  # R90 origin of every row: bank from x 11.50
SE_X0 = RREF_X0 + 0.53 + 0.84                           # CREF beside the banks, 0.84 um clear of their outline
SE_X1 = 41.8                                            # ... and 1.3 um clear of the pair decap's N-well (x 43.1)
RREF_ROWS = (("RREFP_A", VREFP, VREFP_T, 1.5), ("RREFP_B", VREFP, VREFP_T, 3.3),
             ("RREFN_A", VREFN, VREFN_T, 5.7), ("RREFN_B", VREFN, VREFN_T, 7.5))
RISER = {VREFP_T: (10.0, 11.4), VREFN_T: (8.3, 9.6)}      # M8 risers from the rows to the trunk buses
P_BAND = (15.4, 16.52)                                  # VREFP_TRUNK M7 bus (west strip to the rail end)
N_BAND = (17.0, 18.3)                                   # VREFN_TRUNK M4/M6 bus
P_RAIL, N_RAIL = (16.565, 16.885), (16.995, 17.315)     # pair M5 rails: VREFP from x 12.715, VREFN from 12.055
STRAP = {VREFP_T: (("M3", 0.3), ("M5", 1.0), ("M7", 1.0)), VREFN_T: (("M4", 1.0), ("M6", 1.0))}


def qstack(c, net, x, y, lo, hi):
    """2 x 2 cut clusters from metal lo to metal hi with 0.23 um pads (VIAx.R.3 next to straps wider than 0.44 um)."""
    for m in range(lo, hi):
        c.mx(net, x, y, m, pads=(True, True), quad=True)


def via7_at(c, net, x, y):
    c.rect(net, "VIA7", x - 0.18, y - 0.18, x + 0.18, y + 0.18)


def cref_straps(c, arr, skip=(), wide_m3=()):
    """CREF columns: VREFP_TRUNK on M3/M5/M7 at even columns, VREFN_TRUNK on M4/M6 at odd ones, so the two trunk nets
    only ever cross on different layers. Stacks on every same-net rail outside the skip bands (where the other net's
    bus runs on the stack's pad layers). Thin rails under wider M3 (wide_m3 bands) get an M2 pad and 2 x 2 VIA2
    (VIA2.R.3)."""
    for j, xc in enumerate(arr["cols"]):
        net = arr["plus"] if j % 2 == 0 else arr["minus"]
        rails = [((a + b) / 2, b - a) for n, a, b in arr["rails"] if n == net]
        if not rails:
            continue
        for y, h in rails:
            if any(lo <= y <= hi for lo, hi in skip):
                # Under the other net's bus only VIA2 onto this column's M3 strap (VREFP columns; no pad layers).
                if net == VREFP_T:
                    for cx in (xc - 0.065, xc + 0.065):
                        for dy in ((-0.065, 0.065) if h >= 0.28 else (0.0,)):
                            c.rect(net, "VIA2", cx - 0.025, y + dy - 0.025, cx + 0.025, y + dy + 0.025)
                continue
            if h < 0.28 and any(lo <= y <= hi for lo, hi in wide_m3):
                c.rect(net, "M2", xc - 0.115, y - 0.115, xc + 0.115, y + 0.115)
                h = 0.28
            dys = (-0.065, 0.065) if h >= 0.28 else (0.0,)
            for cx in (xc - 0.065, xc + 0.065):
                for dy in dys:
                    c.rect(net, "VIA2", cx - 0.025, y + dy - 0.025, cx + 0.025, y + dy + 0.025)
            qstack(c, net, xc, y, 3, 7 if net == VREFP_T else 6)
        y0, y1 = min(y for y, _ in rails) - 0.4, max(y for y, _ in rails) + 0.4
        for layer, w in STRAP[net]:
            c.rect(net, layer, xc - w / 2, y0, xc + w / 2, y1)


def rref_row(c, name, pad, trunk, y0, east=None):
    """One R90 rupolym bank of RREF_N parallel 0.5 x 0.5 um segments. Its M1 terminal lines (PLUS = pad side at
    y0+0.82, MINUS = trunk side at y0+0.04) run the whole bank, so each gets a strap stack along its full length:
    pad side M2-M8 strips with VIA8 pairs to the pad M9 above, trunk side M2 plus 0.8 um M3-M7 strips that end on
    the trunk riser."""
    c.pcells.append(dict(cell="rupolym", name=name, xy=[RREF_X0, y0], orient="R90", params=dict(RREF),
                         nets=dict(PLUS=pad, MINUS=trunk)))
    yp, yt = y0 + 0.82, y0 + 0.04
    xs = [RREF_X0 - RREF_PITCH * k - 0.25 for k in range(RREF_N)]            # segment centres
    gaps = [RREF_X0 - RREF_PITCH * k - 0.825 for k in range(RREF_N - 1)]     # M1 line between segment heads
    x_lo, x_hi = 11.95, RREF_X0 + 0.07
    for y in (yp, yt):
        for g in gaps:
            for cx in (g - 0.065, g + 0.065):
                net = pad if y == yp else trunk
                c.rect(net, "VIA1", cx - 0.025, y - 0.025, cx + 0.025, y + 0.025)
    # pad side
    c.rect(pad, "M2", x_lo, yp - 0.115, x_hi, yp + 0.115)
    for m in range(3, 7):
        c.rect(pad, f"M{m}", x_lo, yp - 0.115, x_hi, yp + 0.115)
    c.rect(pad, "M7", x_lo, yp - 0.2, x_hi, yp + 0.2)
    c.rect(pad, "M8", x_lo, yp - 0.38, RREF_X0 + 0.37, yp + 0.38)
    for k, x in enumerate(xs):
        for m in range(2, 7):
            c.mx(pad, x, yp, m, pads=(False, False), quad=True)
        via7_at(c, pad, x, yp)
        if k % 2 == 0 and k < RREF_N - 1:
            for cx in (x - 0.35, x + 0.35):
                c.rect(pad, "VIA8", cx - 0.18, yp - 0.18, cx + 0.18, yp + 0.18)
    # trunk side
    c.rect(trunk, "M2", x_lo, yt - 0.1, x_hi, yt + 0.2)
    west = RISER[trunk][0]
    for m in range(3, 8):
        c.rect(trunk, f"M{m}", west, yt - 0.5, x_hi, yt + 0.3)
    if east:
        for m in east["layers"]:
            c.rect(trunk, m, x_hi, yt - 0.5, east["x"], yt + 0.3)
    for k, x in enumerate(xs):
        for cx in (x - 0.065, x + 0.065):
            for cy in (yt - 0.015, yt + 0.115):
                c.rect(trunk, "VIA2", cx - 0.025, cy - 0.025, cx + 0.025, cy + 0.025)
        for m in range(3, 7):
            c.mx(trunk, x, yt - 0.1, m, pads=(False, False), quad=True)
    # onto the riser
    r0, r1 = RISER[trunk]
    for x in ((r0 + r1) / 2,) if r1 - r0 < 1.3 else ((r0 + r1) / 2 - 0.35, (r0 + r1) / 2 + 0.35):
        for m in range(3, 7):
            c.mx(trunk, x, yt - 0.1, m, pads=(False, False), quad=True)
        via7_at(c, trunk, x, yt - 0.1)
    c.summary[name] = dict(segments=RREF_N, w_um=0.5, l_um=0.5, pad=pad, trunk=trunk, origin=[RREF_X0, y0], orient="R90")


def reference(c):
    """VREF boundary pins, RREFP/RREFN (rupolym) in vref_decap_south and CREF (nmoscap, gate on VREFP_TRUNK, N-well on
    VREFN_TRUNK) in vref_decap_west, the corner below the CDAC and beside the banks; the trunks land on in-line M5
    extensions of the pair's VREFP/VREFN rail west ends."""
    # Pins and pad-side joins: each rail's two M8 pins on one M9 join; VREFP's join crosses both VREFN stubs on M9.
    for net, ys in REF_PINS.items():
        jx0, jx1 = REF_JOIN_X[net]
        for y in ys:
            c.rect(net, "M8", 0.0, y - 2.0, jx1, y + 2.0)
            c.pin(net, "M8", [0.0, y - 2.0, 0.4, y + 2.0])
            # 2 x 4 cuts at 1.0 um pitch: denser arrays fail VIA8.S.2.
            for cx in (jx0 + 0.5, jx0 + 1.5):
                for cy in (y - 1.5, y - 0.5, y + 0.5, y + 1.5):
                    c.rect(net, "VIA8", cx - 0.18, cy - 0.18, cx + 0.18, cy + 0.18)
        py0, py1 = PAD_M9_Y[net]
        c.rect(net, "M9", jx0, py0, jx1, max(ys) + 2.0)
        c.rect(net, "M9", jx0, py0, 41.9, py1)
    # Resistor rows; the first VREFP row's trunk strips continue east over the SE CREF array, the first VREFN row's
    # on M4/M6 only (the SE array's VREFP straps cross it on M3/M5/M7).
    se = SE_X1 - SE_X0 >= 0.28 + UNIT["lr"] + 0.28
    for name, pad, trunk, y0 in RREF_ROWS:
        east = {"RREFP_A": dict(x=SE_X1 - 0.5, layers=("M3", "M4", "M5", "M6", "M7")),
                "RREFN_A": dict(x=SE_X1 - 0.5, layers=("M4", "M6"))}.get(name) if se else None
        rref_row(c, name, pad, trunk, y0, east)
    # Risers (M8) up to the trunk buses.
    c.rect(VREFP_T, "M8", RISER[VREFP_T][0], 1.04, RISER[VREFP_T][1], 16.56)
    c.rect(VREFN_T, "M8", RISER[VREFN_T][0], 5.0, RISER[VREFN_T][1], 18.0)
    for x, y in ((10.35, 15.6), (11.05, 15.6), (10.7, 16.3)):     # a 2 x 2 group fails VIA7.S.2 (3 neighbours)
        via7_at(c, VREFP_T, x, y)
    # VREFP_TRUNK: M7 bus from the west strip to the rail end, a 0.32 um M5 line in line with the pair's VREFP rail
    # (tied to the plus columns' M5 straps and, at x 11.6 / 12.3, to the bus), onto the rail end at x 12.715.
    c.rect(VREFP_T, "M7", 1.18, P_BAND[0], 12.6, P_BAND[1])
    c.rect(VREFP_T, "M5", 1.18, P_RAIL[0], 12.715, P_RAIL[1])
    c.rect(VREFP_T, "M6", 10.4, 16.25, 12.5, 16.84)
    for x in (10.6, 11.1, 11.6, 12.0, 12.35):
        c.mx(VREFP_T, x, 16.38, 6, pads=(False, False), quad=True)
        c.mx(VREFP_T, x, 16.725, 5, pads=(False, False), quad=True)
    # VREFN_TRUNK: M4/M6 bus across the west strip, its riser via M7 onto the bus, an M6 strap under the pair's VDD M6
    # riser foot (y < 17.465) to two stacks onto an in-line M5 extension of the pair's VREFN rail.
    for m in ("M4", "M6"):
        c.rect(VREFN_T, m, 1.18, N_BAND[0], 10.0, N_BAND[1])
    c.rect(VREFN_T, "M7", 8.34, 17.45, 9.56, 17.85)
    for x in (8.6, 9.3):
        via7_at(c, VREFN_T, x, 17.65)
        c.mx(VREFN_T, x, 17.65, 6, pads=(False, False), quad=True)
        qstack(c, VREFN_T, x, 17.65, 4, 6)
    c.rect(VREFN_T, "M6", 9.6, 17.0, 11.9, 17.36)
    c.rect(VREFN_T, "M4", 9.6, 16.6, 11.9, 17.36)
    c.rect(VREFN_T, "M5", 9.885, N_RAIL[0], 12.055, N_RAIL[1])
    for x in (10.3, 11.0, 11.7):
        c.mx(VREFN_T, x, 17.155, 5, pads=(True, False), quad=True)
    for x in (10.2, 10.7, 11.2, 11.7):
        c.mx(VREFN_T, x, 17.155, 4, pads=(False, False), quad=True)
    # Labels at the rail ends: the node where the trunk meets the pair's rail.
    c.labels.append(dict(net=VREFP_T, layer="M5", xy=[12.6, 16.725]))
    c.labels.append(dict(net=VREFN_T, layer="M5", xy=[11.95, 17.155]))
    # CREF arrays.
    arr = nm_array(c, "DR_W", [[1.0, 1.2], [9.0, 75.0]], VREFP_T, VREFN_T)
    cref_straps(c, arr, skip=((16.9, 18.5),))
    for xc in arr["cols"][0::2]:      # VREFP columns: tie their M7 and M5 at the bus
        c.rect(VREFP_T, "M6", xc - 0.115, 16.27, xc + 0.115, 16.84)
        c.mx(VREFP_T, xc, 16.38, 6, pads=(False, False), quad=True)
        c.mx(VREFP_T, xc, 16.725, 5, pads=(False, False), quad=True)
    arr = nm_array(c, "DR_C", [[8.8, 9.2], [15.0, 16.3]], VREFP_T, VREFN_T)   # on the west array's column grid
    cref_straps(c, arr)
    top = max(b for n, a, b in arr["rails"] if n == VREFP_T)
    for xc in arr["cols"][0::2]:
        c.rect(VREFP_T, "M7", xc - 0.5, top, xc + 0.5, P_BAND[0] + 0.3)
    ym = next((a + b) / 2 for n, a, b in arr["rails"] if n == VREFN_T)
    for m in ("M4", "M6"):
        c.rect(VREFN_T, m, RISER[VREFN_T][0], ym - 0.25, arr["cols"][-1] + 0.5, ym + 0.25)
    c.mx(VREFN_T, 8.6, ym, 6, pads=(False, False), quad=True)
    c.rect(VREFN_T, "M7", 8.34, ym - 0.2, 8.86, ym + 0.2)
    via7_at(c, VREFN_T, 8.6, ym)
    if se:
        arr = nm_array(c, "DR_SE", [[SE_X0, 1.2], [SE_X1, 8.8]], VREFP_T, VREFN_T)
        cref_straps(c, arr, wide_m3=((1.04, 1.84),))      # the bottom rail lies under the RREFP_A trunk strips
        for xc in arr["cols"][1::2]:      # VREFN columns reach the first VREFN row's M4/M6 strips
            for m in ("M4", "M6"):
                c.rect(VREFN_T, m, xc - 0.5, 3.6, xc + 0.5, 5.74 + 0.3)


def build():
    c = Content()
    boundary(c)
    analog(c)
    pair(c)
    sar(c)
    reference(c)
    return c
