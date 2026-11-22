"""Geometry of the partial chip assembly sar8_adc_chip/layout (Stage 5), in die coordinates (= sar8_io_ring frame).

The ring sits at the origin, R0; the ADC core (sar8_adc_core/layout_route_guard) at io_ring.json adc_placement.origin.
Routed here: the core-to-pad nets that need no undrawn chip object (io_ring.json routes VINN, VINP, VREFP_a/b,
VREFN_a/b, AVDD/AVSS_analog, AVDD/AVSS_pair, AVDD/AVSS_sar, SAMPLE), on the planned centrelines.
- Pad landings: every core pin is a set of M1/M2 fingers reaching 2.6-2.8 um into its IO cell (ring readback); the
  cell's VSS bus runs on M3 about 2.4 um behind them. So each landing extends the M2 fingers out of the cell into the
  3 um band between the cell edge and the core VSS ring outline (io_ring.json core_vss_ring, 113-647 um), joins them on
  an M2 bar and stacks up to the route layer there. SAMPLE's C pin is a 0.26 um M1-M4 square: an M4 stub and a stack.
- Layers: AVDD on M9 and AVSS on M8, the layers of the core's supply pins, so routes of one branch may overlap;
  VREF on 4 um M8 (the pin height), VIN on M5+M6, SAMPLE on 0.8 um M8. Supply routes are 10 um wide and narrow to the
  pin within 2 um of the core edge, where the core's own straps come close.
- Labels: the ring's own pin texts are repeated in the chip cell (the decks read top-level texts only), plus
  POC_dig on the ring's POC rail (io_ring.json chip_netlist XRING).
Not drawn (open): the output register and the D0-D7/ADC_D routes, DVDD and VSS_* routes, the PCLAMPC clamps, the pad
decaps, the core VSS ring, the ADC guard ring and AVSS_guard. LANDINGS names their landing points for the next step.
"""
import json

from Layout.design.toplevel_full_routes import Content
from Layout.design.toplevel_routes import snap
from Layout.project import ROOT

CORE_ORIGIN = (363.885, 449.0)
CORE_SIZE = (122.0, 111.0)
BAND = 2.4                    # landing bar depth from the IO cell edge (stays clear of the core VSS ring outline)
PSUB2 = [359.885, 445.0, 489.885, 564.0]   # ADC P-well domain marker for LVS: io_ring.json adc_guard_ring outline
M2_BAR = 1.0                  # M2 depth of the landing bar
LOW_PITCH, HIGH_PITCH = 0.4, 1.0
WIDE, NECK = 10.0, 2.0
POC_LABEL = dict(text="POC_dig", layer="M3", xy=[108.305, 140.0])
ROUTED = ("VINN", "VINP", "VREFP_a", "VREFN_a", "VREFP_b", "VREFN_b", "AVDD_analog", "AVSS_analog", "AVDD_pair",
          "AVSS_pair", "AVDD_sar", "AVSS_sar", "SAMPLE")
NOT_ROUTED = {
    "AVSS_guard": "adc_guard_ring (2 um P+ ring, AVSS_CORE) is not drawn; it lands on the ring's north-west corner and "
                  "on the core's 0_guard pin at die (485.885, 449.0 + 51.5)",
    "DVDD": "output_register is not drawn", "VSS_register": "output_register and core_vss_ring are not drawn",
    "VSS_digital": "core_vss_ring is not drawn", "VSS_analog": "core_vss_ring is not drawn",
    **{f"ADC_D{k}": "output_register is not drawn" for k in range(8)},
    **{f"D{k}": "output_register is not drawn" for k in range(8)},
}


def ring_plan():
    return json.loads((ROOT / "Layout/design/io_ring.json").read_bytes())


def via_grid(c, net, layer, box, pitch, size, margin):
    x0, y0, x1, y1 = box
    nx = int((x1 - x0 - 2 * margin - size) // pitch) + 1
    ny = int((y1 - y0 - 2 * margin - size) // pitch) + 1
    ox = x0 + (x1 - x0 - (nx - 1) * pitch) / 2
    oy = y0 + (y1 - y0 - (ny - 1) * pitch) / 2
    h = size / 2
    for i in range(nx):
        for j in range(ny):
            x, y = ox + i * pitch, oy + j * pitch
            c.rect(net, layer, x - h, y - h, x + h, y + h)


def plate_stack(c, net, box, top, m2_box):
    """M3..M<top> plates on box with via arrays between them (0.05 um cuts at 0.4 um, 0.36 um VIA7/VIA8 at 1 um); the
    M2 bar (m2_box) stays 1 um deep, below the M2 maximum width (M2.W.3) where it merges with the cell's fingers."""
    c.rect(net, "M2", *m2_box)
    for m in range(3, top + 1):
        c.rect(net, f"M{m}", *box)
    via_grid(c, net, "VIA2", m2_box, LOW_PITCH, 0.05, 0.1)
    for m in range(3, top):
        if m < 7:
            via_grid(c, net, f"VIA{m}", box, LOW_PITCH, 0.05, 0.1)
        else:
            via_grid(c, net, f"VIA{m}", box, HIGH_PITCH, 0.36, 0.4)


def landing(c, net, side, fingers, top):
    """Extend the M2 fingers of a core pin out of the IO cell and stack up on a bar in the band before the VSS ring."""
    xs0, ys0 = min(f[0] for f in fingers), min(f[1] for f in fingers)
    xs1, ys1 = max(f[2] for f in fingers), max(f[3] for f in fingers)
    if side == "top":                       # cell edge at y 650, opening below
        bar = (xs0, 650.0 - BAND, xs1, 650.0)
        m2 = (xs0, 650.0 - M2_BAR, xs1, 650.0)
        for f in fingers:
            c.rect(net, "M2", f[0], m2[1], f[2], 650.2)
    elif side == "left":                    # cell edge at x 110, opening to the east
        bar = (110.0, ys0, 110.0 + BAND, ys1)
        m2 = (110.0, ys0, 110.0 + M2_BAR, ys1)
        for f in fingers:
            c.rect(net, "M2", 109.8, f[1], m2[2], f[3])
    else:                                   # right: cell edge at x 650
        bar = (650.0 - BAND, ys0, 650.0, ys1)
        m2 = (650.0 - M2_BAR, ys0, 650.0, ys1)
        for f in fingers:
            c.rect(net, "M2", m2[0], f[1], 650.2, f[3])
    plate_stack(c, net, bar, top, m2)
    return bar


def box(c, net, layers, x0, y0, x1, y1):
    for m in layers:
        c.rect(net, m, x0, y0, x1, y1)


def core(x, y):
    return snap(CORE_ORIGIN[0] + x), snap(CORE_ORIGIN[1] + y)


def build(readback):
    """Content of the chip cell: rects with nets, labels, and the record of every landing."""
    plan = ring_plan()
    pads = {p["position"]: p for p in plan["pads"]}
    inst_at = {}
    for name, i in readback["instances"].items():
        inst_at[name] = i
    fingers = {}
    for pos in ("top_5", "top_2", "left_1", "left_2", "left_3", "left_4", "top_4", "top_3", "left_5", "left_6",
                "top_1", "right_8", "right_5"):
        p = pads[pos]
        x, y = p["core_pin_um"]
        inst = next(n for n, i in readback["instances"].items()
                    if not i["cell"].startswith(("PFILLER", "PCORNER", "PRCUT", "PAD60"))
                    and i["bbox"][0] - 1 <= x <= i["bbox"][2] + 1 and i["bbox"][1] - 1 <= y <= i["bbox"][3] + 1)
        layer = "M4" if pos == "right_5" else "M2"
        figs = sorted({tuple(q["bbox"]) for q in readback["pins"]
                       if q["inst"] == inst and q["term"] == p["core_pin"] and q["layer"] == layer
                       and (q["bbox"][1] < 650.5 if pos.startswith("top") else
                            q["bbox"][2] > 109.5 if pos.startswith("left") else q["bbox"][0] < 650.5)})
        fingers[pos] = dict(inst=inst, cell=readback["instances"][inst]["cell"], layer=layer, figs=[list(f) for f in figs])
    c = Content()
    land = {}
    # VIN: M5+M6 1 um, M5 0.3 um neck onto the core's VIN pins.
    for route, pos, cx in (("VINN", "top_5", 33.34), ("VINP", "top_2", 58.89)):
        bar = landing(c, route, "top", fingers[pos]["figs"], 6)
        px, _ = core(cx, 0)
        x = plan["routes"][route]["points_um"][0][0]
        box(c, route, ("M5", "M6"), x - 0.5, 569.5, x + 0.5, bar[1] + 0.5)
        lo, hi = sorted((x, px))
        box(c, route, ("M5", "M6"), lo - 0.5, 569.5, hi + 0.5, 570.5)
        box(c, route, ("M5", "M6"), px - 0.5, 562.0, px + 0.5, 570.5)
        c.rect(route, "M5", px - 0.15, 560.0, px + 0.15, 562.5)
        land[route] = dict(pad=pos, bar=list(bar), core_pin=[px, 560.0])
    # VREF: 4 um M8 on the planned nested L-shapes onto the 4 um M8 core pins.
    for route, pos in (("VREFP_a", "left_1"), ("VREFN_a", "left_2"), ("VREFP_b", "left_3"), ("VREFN_b", "left_4")):
        net = route.split("_")[0]
        bar = landing(c, net, "left", fingers[pos]["figs"], 8)
        (x0, y0), (x1, _), (_, y2), (x3, _) = plan["routes"][route]["points_um"]
        c.rect(net, "M8", bar[0], y0 - 2.0, x1 + 2.0, y0 + 2.0)
        c.rect(net, "M8", x1 - 2.0, min(y0, y2) - 2.0, x1 + 2.0, max(y0, y2) + 2.0)
        c.rect(net, "M8", x1 - 2.0, y2 - 2.0, x3, y2 + 2.0)
        land[route] = dict(pad=pos, bar=list(bar), core_pin=[x3, y2])
    # Analog branch: AVDD M9, AVSS M8 with an M9 neck onto the core's M9 pin.
    bar = landing(c, "AVDD_CORE", "top", fingers["top_4"]["figs"], 9)
    box(c, "AVDD_CORE", ("M9",), 375.0, 585.0, 385.0, bar[3])
    box(c, "AVDD_CORE", ("M9",), 375.0, 585.0, 409.0, 595.0)
    box(c, "AVDD_CORE", ("M9",), 403.0, 560.0 + NECK, 409.0, 595.0)
    box(c, "AVDD_CORE", ("M9",), 407.0, 560.0, 409.0, 560.0 + NECK + 0.5)
    land["AVDD_analog"] = dict(pad="top_4", bar=list(bar), core_pin=[408.0, 560.0])
    bar = landing(c, "AVSS_CORE", "top", fingers["top_3"]["figs"], 8)
    box(c, "AVSS_CORE", ("M8",), 435.0, 585.0, 445.0, bar[3])
    box(c, "AVSS_CORE", ("M8",), 411.0, 585.0, 445.0, 595.0)
    box(c, "AVSS_CORE", ("M8",), 411.0, 562.0, 417.0, 595.0)
    box(c, "AVSS_CORE", ("M9",), 411.0, 560.0, 413.0, 564.4)
    for y in (562.7, 563.7):
        c.rect("AVSS_CORE", "VIA8", 411.82, y - 0.18, 412.18, y + 0.18)
    land["AVSS_analog"] = dict(pad="top_3", bar=list(bar), core_pin=[412.0, 560.0])
    # Pair branch from the west: AVDD M9 at y 320, AVSS M8 at y 260, up to the south pins.
    bar = landing(c, "AVDD_CORE", "left", fingers["left_5"]["figs"], 9)
    box(c, "AVDD_CORE", ("M9",), bar[0], 315.0, 408.885, 325.0)
    box(c, "AVDD_CORE", ("M9",), 402.885, 315.0, 408.885, 449.0 - NECK)
    box(c, "AVDD_CORE", ("M9",), 406.885, 449.0 - NECK - 0.5, 408.885, 449.0)
    land["AVDD_pair"] = dict(pad="left_5", bar=list(bar), core_pin=[407.885, 449.0])
    bar = landing(c, "AVSS_CORE", "left", fingers["left_6"]["figs"], 8)
    box(c, "AVSS_CORE", ("M8",), bar[0], 255.0, 416.885, 265.0)
    box(c, "AVSS_CORE", ("M8",), 410.885, 255.0, 416.885, 449.0 - NECK)
    box(c, "AVSS_CORE", ("M8",), 410.885, 449.0 - NECK - 0.5, 412.885, 449.0)
    land["AVSS_pair"] = dict(pad="left_6", bar=list(bar), core_pin=[411.885, 449.0])
    # SAR branch from the north-east: AVDD M9 down x 560 onto the 2 um pin at y 522-524; AVSS M8 from right_8.
    e = CORE_ORIGIN[0] + CORE_SIZE[0]
    bar = landing(c, "AVDD_CORE", "top", fingers["top_1"]["figs"], 9)
    box(c, "AVDD_CORE", ("M9",), 555.0, 522.0, 565.0, bar[3])
    box(c, "AVDD_CORE", ("M9",), e + NECK, 522.0, 565.0, 528.0)
    box(c, "AVDD_CORE", ("M9",), e, 522.0, e + NECK + 0.5, 524.0)
    land["AVDD_sar"] = dict(pad="top_1", bar=list(bar), core_pin=[e, 523.0])
    bar = landing(c, "AVSS_CORE", "right", fingers["right_8"]["figs"], 8)
    box(c, "AVSS_CORE", ("M8",), 595.0, 615.0, bar[2], 625.0)
    # 4 um wide here: SAMPLE runs 1.7 um below (M8.S.3 asks 1.5 um next to metal wider than 4.5 um)
    box(c, "AVSS_CORE", ("M8",), 595.0, 516.5, 605.0, 625.0)
    box(c, "AVSS_CORE", ("M8",), e + NECK, 516.5, 605.0, 520.5)
    box(c, "AVSS_CORE", ("M8",), e, 519.5, e + NECK + 0.5, 520.5)
    land["AVSS_sar"] = dict(pad="right_8", bar=list(bar), core_pin=[e, 520.0])
    # SAMPLE: M4 stub on the C pin, stack to M8, 0.8 um M8 onto the core's M8 pin.
    pin = fingers["right_5"]["figs"][0]
    y = snap((pin[1] + pin[3]) / 2)
    c.rect("SAMPLE_CORE", "M4", 648.2, pin[1], pin[2], pin[3])
    c.stack("SAMPLE_CORE", 648.6, y, 4, 8, axis="x")
    c.rect("SAMPLE_CORE", "M8", 549.6, y - 0.4, 648.6, y + 0.4)
    c.rect("SAMPLE_CORE", "M8", 549.6, y - 0.4, 550.4, 514.8)
    c.rect("SAMPLE_CORE", "M8", e, 514.0, 550.4, 514.8)
    land["SAMPLE"] = dict(pad="right_5", stack=[648.6, y], core_pin=[e, 514.4])
    # PSUB2 (111;0, the deck's marker for an isolated P-well domain): the ADC substrate is AVSS_CORE, apart from the
    # ring's global VSS taps, as in the core's own LVS.
    c.rects.append(dict(net="", layer="PSUB2", purpose="drawing", box=list(PSUB2)))
    labels = [dict(text=l["text"], layer=l["layer"], xy=l["xy"]) for l in readback["labels"]] + [POC_LABEL]
    return c, labels, dict(fingers=fingers, landings=land, routed=list(ROUTED), not_routed=NOT_ROUTED)
