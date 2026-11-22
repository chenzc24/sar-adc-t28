"""Geometry of the SAR P+ guard ring (Stage 5), added to layout_route_full as sar8_adc_core/layout_route_guard.

floorplan.json reserved_regions.sar_guard_ring: a 1 um P+ substrate ring around the digital macro, with its own VSS
strap to the boundary; the corridor M3 stubs and the via stacks pass over it. The ring sits in the band between the
region outline (91.23, 51.0)-(111.725, 69.8) and the macro outline (92.23, 52.0)-(110.725, 68.8):
- OD, M1 and M2 frames 0.6 um wide, 0.2 um from the region outline and from the macro outline; PP encloses OD by
  0.1 um. The macro's own NW, PP, NP and M1 stay at least 0.455 um inside its outline.
- contacts in three rows at 0.16 um pitch, VIA1 in 2 x 2 clusters every 1 um;
- the strap: M1 and M2 from the ring's south-east corner east to the core edge, where an M2 pin carries 0. Inside the
  core it touches no other VSS metal; at chip level it lands on the ADC guard ring (io_ring.json adc_guard_ring,
  AVSS_CORE, 2-4 um outside the core edge).
"""
import math

from Layout.design.toplevel_full_routes import GND, Content
from Layout.design.toplevel_routes import snap

OUTER = (91.23, 51.0, 111.725, 69.8)
MACRO = (92.23, 52.0, 110.725, 68.8)
INSET, WIDTH, PP_ENC = 0.2, 0.6, 0.1
CO, CO_PITCH, CO_ROWS = 0.04, 0.16, (0.14, 0.30, 0.46)
VIA_STEP = 1.0
CORE_EAST = 122.0
PIN = dict(name="0_guard", box=[121.6, OUTER[1] + INSET, CORE_EAST, OUTER[1] + INSET + WIDTH])


def frame(c, layer, x0, y0, x1, y1, w, net=GND):
    """Four rectangles of width w inside the box (x0, y0)-(x1, y1)."""
    c.rect(net, layer, x0, y0, x1, y0 + w)
    c.rect(net, layer, x0, y1 - w, x1, y1)
    c.rect(net, layer, x0, y0 + w, x0 + w, y1 - w)
    c.rect(net, layer, x1 - w, y0 + w, x1, y1 - w)


def steps(a, b, pitch):
    n = int(math.floor((b - a) / pitch + 1e-9))
    return [snap(a + pitch * k) for k in range(n + 1)]


def build():
    c = Content()
    x0, y0, x1, y1 = OUTER[0] + INSET, OUTER[1] + INSET, OUTER[2] - INSET, OUTER[3] - INSET
    assert abs((MACRO[0] - x0) - (WIDTH + INSET)) < 1e-6 and abs((MACRO[1] - y0) - (WIDTH + INSET)) < 1e-6
    for layer in ("OD", "M1", "M2"):
        frame(c, layer, x0, y0, x1, y1, WIDTH)
    frame(c, "PP", x0 - PP_ENC, y0 - PP_ENC, x1 + PP_ENC, y1 + PP_ENC, WIDTH + 2 * PP_ENC)
    h = CO / 2
    cuts = []
    for off in CO_ROWS:                       # south and north sides, full length
        for x in steps(x0 + CO_ROWS[0], x1 - CO_ROWS[0], CO_PITCH):
            cuts += [(x, y0 + off), (x, y1 - off)]
    for off in CO_ROWS:                       # west and east sides, between the south and north rows
        for y in steps(y0 + WIDTH + 0.02, y1 - WIDTH - 0.02, CO_PITCH):
            cuts += [(x0 + off, y), (x1 - off, y)]
    for x, y in cuts:
        c.rect(GND, "CO", x - h, y - h, x + h, y + h)
    mid = WIDTH / 2
    vias = [(x, y0 + mid) for x in steps(x0 + mid, x1 - mid, VIA_STEP)] + \
           [(x, y1 - mid) for x in steps(x0 + mid, x1 - mid, VIA_STEP)] + \
           [(x0 + mid, y) for y in steps(y0 + mid + VIA_STEP, y1 - mid - VIA_STEP, VIA_STEP)] + \
           [(x1 - mid, y) for y in steps(y0 + mid + VIA_STEP, y1 - mid - VIA_STEP, VIA_STEP)]
    # Strap to the east edge on M1 and M2.
    sy0, sy1 = y0, y0 + WIDTH
    for layer in ("M1", "M2"):
        c.rect(GND, layer, x1, sy0, CORE_EAST, sy1)
    vias += [(x, y0 + mid) for x in steps(x1 + VIA_STEP / 2, CORE_EAST - 0.5, VIA_STEP)]
    for x, y in vias:
        c.mx(GND, x, y, 1, pads=(False, False), quad=True)
    c.pin(GND, "M2", PIN["box"])
    c.terminals[-1]["pins"][-1]["name"] = PIN["name"]
    c.summary["guard_ring"] = dict(outer=[x0, y0, x1, y1], width_um=WIDTH, contacts=len(cuts), via1_clusters=len(vias),
                                   strap=[x1, sy0, CORE_EAST, sy1], pin=PIN)
    return c
