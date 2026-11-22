"""Geometry of the core-internal ADC routes (Stage 4a): the 21 planned paths that end only on block pins.

Every shape is an axis-aligned rectangle on the 5 nm grid in the core frame (= the sar8_adc_core frame).
Wires are 0.1 um wide (2x the Mx minimum), centred on the floorplan centrelines and extended by half a width
past each vertex. Layer changes use two square cuts per via level, 0.08 um apart (VIAx.S.5) along one axis, under
0.1 um pads on every metal of the stack: 0.025 um enclosure on all sides (VIAx.EN.14/15) and no single cut
near a wide plate (VIAx.R.4). Two exceptions: the CMP_CLK drop lands on the comparator's existing M3_M2
via with one VIA3 on its 0.05 um trunk (decisions.cmp_clk_north_drop), and the last 0.22 um into a pin
narrower than 0.1 um keeps that pin's width.

The VSS shields of the output channel and the corridor form one shield net. It is drawn but not tied to a
supply: the VSS feed belongs to the supply stage, which waits for the IO ring. Two shield details differ from
the floorplan: the 73.5 um channel track starts at the east edge of the TOP input fill exclusion instead of
x 47.3, and an extra M3 shield runs between the COMP_P and CMP_CLK stubs into the SAR pins.
"""
from dataclasses import dataclass
import json

from Layout.project import ROOT

FLOORPLAN = ROOT / "Layout/design/floorplan.json"
W = 0.1
CUT = 0.05
CUT_PITCH = 0.13
SHIELD = "VSS_SHIELD"
VIA_LAYER = {2: "VIA2", 3: "VIA3", 4: "VIA4"}
GDS = {"M2": (32, 0), "M3": (33, 0), "M4": (34, 0), "M5": (35, 0), "VIA2": (52, 0), "VIA3": (53, 0), "VIA4": (54, 0)}
PIN_TEXT = {"M2": (132, 0), "M3": (133, 0), "M4": (134, 0), "M5": (135, 0)}
AXIS_X = 46.115


def snap(v):
    r = round(v / 0.005) * 0.005
    if abs(r - v) > 1e-6:
        raise ValueError(f"{v} is off the 5 nm grid")
    return round(r, 3)


@dataclass(frozen=True)
class Rect:
    net: str
    layer: str
    x0: float
    y0: float
    x1: float
    y1: float
    role: str

    def __post_init__(self):
        for k in ("x0", "y0", "x1", "y1"):
            object.__setattr__(self, k, snap(getattr(self, k)))
        if not (self.x0 < self.x1 and self.y0 < self.y1):
            raise ValueError(f"Empty rectangle {self}")


@dataclass(frozen=True)
class Label:
    net: str
    layer: str
    x: float
    y: float


class Routes:
    def __init__(self):
        self.rects = []
        self.labels = []

    def rect(self, net, layer, x0, y0, x1, y1, role="wire"):
        self.rects.append(Rect(net, layer, min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1), role))

    def seg(self, net, layer, a, b, w=W, ext=None):
        """Wire along the centreline a-b, extended past both ends by ext (default half the width)."""
        (xa, ya), (xb, yb) = a, b
        e = w / 2 if ext is None else ext
        if ya == yb:
            self.rect(net, layer, min(xa, xb) - e, ya - w / 2, max(xa, xb) + e, ya + w / 2)
        elif xa == xb:
            self.rect(net, layer, xa - w / 2, min(ya, yb) - e, xa + w / 2, max(ya, yb) + e)
        else:
            raise ValueError("Non-Manhattan segment")

    def path(self, net, layer, points, w=W):
        for a, b in zip(points, points[1:]):
            self.seg(net, layer, a, b, w)

    def via(self, net, x, y, lower, upper, axis, sign=1):
        """Two cuts per level at (x, y) and CUT_PITCH along axis*sign, with 0.1 um pads on lower..upper."""
        dx, dy = (CUT_PITCH * sign, 0) if axis == "x" else (0, CUT_PITCH * sign)
        cuts = [(x, y), (x + dx, y + dy)]
        xs, ys = [c[0] for c in cuts], [c[1] for c in cuts]
        for m in range(lower, upper + 1):
            self.rect(net, f"M{m}", min(xs) - W / 2, min(ys) - W / 2, max(xs) + W / 2, max(ys) + W / 2, "via_pad")
        for m in range(lower, upper):
            for cx, cy in cuts:
                self.rect(net, VIA_LAYER[m], cx - CUT / 2, cy - CUT / 2, cx + CUT / 2, cy + CUT / 2, "cut")

    def label(self, net, layer, x, y):
        self.labels.append(Label(net, layer, snap(x), snap(y)))


def plan():
    return json.loads(FLOORPLAN.read_bytes())


def top_side(r, side):
    """TOPN routes from the floorplan centrelines; TOPP is their mirror about the comparator axis."""
    p = plan()
    pins = p["pins_um"]
    m = (lambda x: x) if side == "N" else (lambda x: snap(2 * AXIS_X - x))
    net = "TOP" + side
    comp = p["planned_paths"][f"TOP{side}_to_comparator"]["points_um"]
    samp = p["planned_paths"][f"TOP{side}_to_sampler"]["points_um"]
    pin, tee = comp[0], comp[1]
    branch, vin = comp[3], comp[4]
    drop = samp[2]
    if m(pins["XCDAC.TOPN"][0]) != pin[0] or tee[1] != samp[1][1] or branch[0] != comp[2][0]:
        raise ValueError("TOP centrelines changed")
    ty = tee[1]
    # M3 riser from the CDAC pin and the tee; the riser stays inside the pin footprint below the CDAC edge.
    r.seg(net, "M3", pin, tee)
    r.seg(net, "M3", (drop[0], ty), (pin[0], ty))
    # Comparator branch: M3 -> M2 at the branch, M2 north, then a pin-height M2 stub into VINx.
    r.via(net, branch[0], ty, 2, 3, "y")
    r.rect(net, "M2", branch[0] - W / 2, ty - W / 2, branch[0] + W / 2, vin[1] + 0.025)
    r.rect(net, "M2", branch[0] - W / 2 if side == "N" else vin[0], vin[1] - 0.025,
           vin[0] if side == "N" else branch[0] + W / 2, vin[1] + 0.025)
    # Sampler branch: M3 -> M2 at the drop, M2 north into the Bootstrap VOUT pin (0.2 um square).
    r.via(net, drop[0], ty, 2, 3, "y")
    r.rect(net, "M2", drop[0] - W / 2, ty - W / 2, drop[0] + W / 2, samp[3][1] + 0.05)
    r.label(net, "M3", m(40.0), ty)


def comparator_group(r):
    p = plan()["planned_paths"]
    # COMP_P: M3 riser (pin width) with the balance stub, M3->M5 stack, M5 track, M4 corridor vertical
    # with the west jog, M4->M3, M3 into the SAR pin.
    P = p["OUTP"]["points_um"]
    stub = p["OUTP_riser_balance"]["points_um"]
    r.rect("COMP_P", "M3", P[0][0] - 0.025, P[0][1], P[0][0] + 0.025, stub[1][1] + 0.025, "riser")
    r.via("COMP_P", P[1][0], P[1][1], 3, 5, "x")
    r.seg("COMP_P", "M5", P[1], P[2])
    r.via("COMP_P", P[2][0], P[2][1], 4, 5, "y", -1)
    r.path("COMP_P", "M4", P[2:8])
    r.via("COMP_P", P[7][0], P[7][1], 3, 4, "x")
    sar_stub(r, "COMP_P", P[7], P[8])
    cb = p["OUTP_clk_balance"]["points_um"]
    r.via("COMP_P", cb[0][0], cb[0][1], 3, 4, "x")
    r.seg("COMP_P", "M3", cb[0], cb[1])
    r.label("COMP_P", "M5", 70.0, P[1][1])
    # COMP_N: M3 riser, M3->M5 stack at its top, M5 track, M4 vertical, M4->M3, M3 into the SAR pin.
    N = p["OUTN"]["points_um"]
    r.rect("COMP_N", "M3", N[0][0] - 0.025, N[0][1], N[0][0] + 0.025, N[1][1], "riser")
    r.via("COMP_N", N[1][0], N[1][1], 3, 5, "x")
    r.seg("COMP_N", "M5", N[1], N[2])
    r.via("COMP_N", N[2][0], N[2][1], 4, 5, "y", -1)
    r.seg("COMP_N", "M4", N[2], N[3])
    r.via("COMP_N", N[3][0], N[3][1], 3, 4, "x")
    sar_stub(r, "COMP_N", N[3], N[4])
    r.label("COMP_N", "M5", 70.0, N[1][1])
    # CMP_CLK: M3 from the SAR pin, M3->M4, M4 corridor vertical, M4->M5, M5 track, M5->M4, M4 drop on the
    # comparator axis (pin-trunk width over the core) and one VIA3 onto the trunk-top M3_M2 via.
    C = p["CMP_CLK"]["points_um"]
    sar_stub(r, "CMP_CLK", C[1], C[0])
    r.via("CMP_CLK", C[1][0], C[1][1], 3, 4, "y")
    r.seg("CMP_CLK", "M4", C[1], C[2])
    r.via("CMP_CLK", C[2][0], C[2][1], 4, 5, "x", -1)
    r.seg("CMP_CLK", "M5", C[2], C[3])
    r.via("CMP_CLK", C[3][0], C[3][1], 4, 5, "y", -1)
    land = C[4]
    r.rect("CMP_CLK", "M4", land[0] - 0.025, land[1] - 0.055, land[0] + 0.025, C[3][1], "drop")
    r.rect("CMP_CLK", "VIA3", land[0] - 0.025, land[1] - 0.025, land[0] + 0.025, land[1] + 0.025, "cut")
    r.label("CMP_CLK", "M5", 70.0, C[2][1])
    # SEQ_SAMPLE: M3 from the SAR pin, M4 vertical, M5 trunk to the tap, M5 jog onto the arm track, mirrored
    # M5 arms, M5->M2 stacks and M2 into the Bootstrap CLKS pins.
    S = p["SEQ_SAMPLE_trunk"]["points_um"]
    sar_stub(r, "SEQ_SAMPLE", S[1], S[0])
    r.via("SEQ_SAMPLE", S[1][0], S[1][1], 3, 4, "y")
    r.seg("SEQ_SAMPLE", "M4", S[1], S[2])
    r.via("SEQ_SAMPLE", S[2][0], S[2][1], 4, 5, "x", -1)
    r.seg("SEQ_SAMPLE", "M5", S[2], S[3])
    for name, sign in (("SEQ_SAMPLE_to_XBOOTN", 1), ("SEQ_SAMPLE_to_XBOOTP", -1)):
        A = p[name]["points_um"]
        r.seg("SEQ_SAMPLE", "M5", A[0], A[1])
        r.seg("SEQ_SAMPLE", "M5", A[1], A[2])
        r.via("SEQ_SAMPLE", A[2][0], A[2][1], 2, 5, "x", sign)
        r.rect("SEQ_SAMPLE", "M2", A[2][0] - W / 2, A[2][1] - W / 2, A[2][0] + W / 2, A[3][1] + 0.05)
    r.label("SEQ_SAMPLE", "M5", 70.0, S[3][1])


def sar_stub(r, net, corner, pin):
    """M3 from the corridor vertical into a SAR west-edge pin (0.34 x 0.05 um at x 92.23-92.57)."""
    (x, y), (px, py) = corner, pin
    if py != y or px <= x:
        raise ValueError("SAR stub must run east")
    edge = 92.23
    r.rect(net, "M3", x - W / 2, y - W / 2, edge - 0.05, y + W / 2)
    r.rect(net, "M3", edge - 0.05, y - 0.025, px, y + 0.025, "pin_entry")


def code_bus(r):
    p = plan()
    corridor = next(g for g in p["reserved_regions"] if g["id"] == "digital_corridor")["code_bus_x_um"]
    for net, x in corridor.items():
        P = p["planned_paths"][net]["points_um"]
        if P[1][0] != x:
            raise ValueError("Code bus track changed")
        # M3 continues the XREF bus track (pin height 0.1 um) to the corridor vertical.
        r.seg(net, "M3", P[0], P[1])
        r.via(net, P[1][0], P[1][1], 3, 4, "y")
        r.seg(net, "M4", P[1], P[2])
        r.via(net, P[2][0], P[2][1], 3, 4, "x")
        sar_stub(r, net, P[2], P[3])
        r.label(net, "M4", x, 30.0)


def shields(r):
    """VSS shields: channel M5 tracks continued to the corridor corner, corridor M4 verticals, an M3 tie bar."""
    p = plan()
    channel = next(g for g in p["reserved_regions"] if g["id"] == "output_channel")
    corridor = next(g for g in p["reserved_regions"] if g["id"] == "digital_corridor")
    xs = corridor["vss_shield_x_um"]
    tracks = [t for t in channel["tracks"] if t["net"] == "VSS"]
    if [t["y_um"] for t in tracks] != [73.5, 74.1, 74.7, 75.3] or xs != [87.6, 88.4, 89.2, 90.0, 90.8]:
        raise ValueError("Shield tracks changed")
    bar = 64.5
    jog = plan()["planned_paths"]["OUTP"]["points_um"][3:7]  # COMP_P west jog, y 71.0 and 70.4
    (ex0, ey0), (ex1, ey1) = next(g for g in p["reserved_regions"] if g["id"] == "top_fill_exclusion_inputs")["bbox"]
    for t, x in zip(tracks, xs):
        y = t["y_um"]
        west = t["x_um"][0]
        if y - W / 2 < ey1 and west < ex1:
            # The 73.5 um track's lower edge would enter the TOP input fill exclusion; start it at its east edge.
            west = ex1
        r.rect(SHIELD, "M5", west, y - W / 2, x + W / 2, y + W / 2, "shield")
        r.via(SHIELD, x, y, 4, 5, "y", -1)
        if x == 87.6:
            # The COMP_P jog crosses this track on M4: leave 0.1 um either side of it.
            r.rect(SHIELD, "M4", x - W / 2, jog[0][1] + 0.15, x + W / 2, y + W / 2, "shield")
            r.rect(SHIELD, "M4", x - W / 2, bar - W / 2, x + W / 2, jog[2][1] - 0.15, "shield")
        else:
            r.rect(SHIELD, "M4", x - W / 2, bar - W / 2, x + W / 2, y + W / 2, "shield")
    # East of SEQ_SAMPLE: the corridor shield alone, to the top of the SEQ_SAMPLE trunk.
    seq_top = plan()["planned_paths"]["SEQ_SAMPLE_trunk"]["points_um"][2][1]
    r.rect(SHIELD, "M4", xs[4] - W / 2, bar - W / 2, xs[4] + W / 2, seq_top + W / 2, "shield")
    r.seg(SHIELD, "M3", (xs[0], bar), (xs[4], bar))
    for x in xs:
        r.via(SHIELD, x, bar, 3, 4, "x", 1 if x != xs[4] else -1)
    # Not in the plan: the frozen SAR pin order puts the COMP_P and CMP_CLK M3 stubs 0.5 um apart over about
    # 3.4 um, a CLK coupling COMP_N does not see. An M3 shield on the midline, tied to the corridor
    # shields it passes under, takes that coupling to VSS (decisions.cmp_clk_north_drop.verify).
    stubs = plan()["planned_paths"]
    y_p, y_c = stubs["OUTP"]["points_um"][8][1], stubs["CMP_CLK"]["points_um"][0][1]
    mid = snap((y_p + y_c) / 2)
    r.rect(SHIELD, "M3", xs[1] - W / 2, mid - W / 2, 92.23 - 0.1, mid + W / 2, "shield")
    for x in xs[1:]:
        r.via(SHIELD, x, mid, 3, 4, "x")


def build():
    r = Routes()
    top_side(r, "N")
    top_side(r, "P")
    comparator_group(r)
    code_bus(r)
    shields(r)
    # The two SEQ_SAMPLE arms share the tap jog; keep each rectangle once, in a stable order.
    r.rects = sorted(set(r.rects), key=lambda s: (s.net, s.layer, s.x0, s.y0, s.x1, s.y1, s.role))
    return r


def overlay(routes, base, out):
    """Merge the routes into a stream of the placement view; returns the merged top cell name."""
    import gdstk
    lib = gdstk.read_gds(str(base))
    top = next(c for c in lib.cells if c.name == "sar8_adc_core")
    for s in routes.rects:
        layer, datatype = GDS[s.layer]
        top.add(gdstk.rectangle((s.x0, s.y0), (s.x1, s.y1), layer=layer, datatype=datatype))
    for t in routes.labels:
        layer, texttype = PIN_TEXT[t.layer]
        top.add(gdstk.Label(t.net, (t.x, t.y), layer=layer, texttype=texttype))
    lib.write_gds(str(out))
    return top.name


if __name__ == "__main__":
    routes = build()
    print(len(routes.rects), "rectangles,", len(routes.labels), "labels")
