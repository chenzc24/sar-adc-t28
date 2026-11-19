"""Synthesize the paired-row CDAC from electrical weights and native unit pins."""
from collections import Counter, defaultdict
from itertools import groupby
from pathlib import Path
import json
import math

from Layout.design.cdac import PORTS, independent_reference

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "work/layout/cdac-paired"
HALF, CORE, TOP = "sar8_cdac_half", "sar8j_r1_cdac_core", "sar8j_r1_cdac"
FILL = "sar8_cdac_fill_plan"
PX, PY, MOM_H, ARRAY_X = 0.96, 2.92, 2.42, 1.92
MIRROR, TOP_X, TOP_Y = 68.8, 33.84, 25.78
GATE_EDGE = -23.95
M4_BOTTOM_WIDTH = {'B7': .41, 'B6': .40, 'B5': .37}
M4_FAR_WIDTH = {'B7': .33, 'B6': .30, 'B5': .25}
SUPPLY = {"VSS": [33.50], "VDD": [-0.45], "VREFN": [0.50, 30.10], "VREFP": [1.16, 30.74]}
GLOBAL_Y = {"VSS": -24.45, "VDD": -24.88, "VREFN": -25.31, "VREFP": -25.74}


def col(c):
    return ARRAY_X + c * PX


# Center columns 15/16, rows 0..7 bottom to top, and the column gap of each small-bit
# trunk. "inverted" is the published balanced layout: central inversion like the major
# bits, so every small-bit pair needs a trunk through nearly the full array height.
# "stacked" orders the small bits by weight from the switch side. A bottom-plate trunk
# couples to TOP by about 0.08 fF per array row it passes (native PDB, all bits alike),
# so trunk length then follows the unit count: B0 0.5, B1 1.5, B2 3.5 and the shared
# B3 trunk 7.5 rows for 1/2/4/8 units, like the ~0.07 fF/unit of B4..B7.
CENTER = {
    "inverted": {"rows": None, "gaps": {"B3": 15, "B2": 13, "B1": 12, "B0": 9, "TERM": 9}},
    "stacked": {"rows": [("B0", "TERM"), ("B1", "B1"), ("B2", "B2"), ("B2", "B2"),
                         ("B3", "B3"), ("B3", "B3"), ("B3", "B3"), ("B3", "B3")],
                "gaps": {"B3": 16, "B2": 15, "B1": 17, "B0": 13, "TERM": 19}},
}


def assignment(center="inverted"):
    # Each major bit occupies several continuous column groups. Both array axes
    # have reflection symmetry for B4..B7. Smaller bits use the chosen center layout.
    sequence = [7, 7, 7, 6, 6, 5, 5, 4, 7, 7, 7, 7, 7, 6, 6]
    outer = [f"B{bit}" for bit in sequence]
    grid = {}
    for r, small in enumerate(["B2", "B1", "B2", "B0"]):
        row = outer + ["B3", small] + outer[::-1]
        for c, net in enumerate(row):
            grid[c, r] = net
            grid[31-c, 7-r] = "TERM" if net == "B0" else net
    if CENTER[center]["rows"]:
        for r, pair in enumerate(CENTER[center]["rows"]):
            grid[15, r], grid[16, r] = pair
    assert Counter(grid.values()) == {**{f"B{b}": 2**b for b in range(8)}, "TERM": 1}
    symmetric = range(1, 8) if center == "inverted" else range(4, 8)
    for net in (f"B{b}" for b in symmetric):
        sites = {s for s, n in grid.items() if n == net}
        assert {(31-c, 7-r) for c, r in sites} == sites
    return grid


class Drawing:
    """Emit OA geometry and retain the actual intended wire/port coordinates."""
    def __init__(self):
        self.lines = []
        self.ports = {}

    def add(self, line):
        self.lines.append(line)

    def wire(self, net, layer, x0, y0, x1, y1, width=.12):
        if abs(x0-x1) + abs(y0-y1) < .001:
            return
        assert abs(x0-x1) < .001 or abs(y0-y1) < .001
        self.add(f'cmpWire(cv rdNet(cv "{net}") "M{layer}" cmpPoint({x0:.4f} {y0:.4f}) '
                 f'cmpPoint({x1:.4f} {y1:.4f}) {width})')

    def via(self, lo, hi, x, y, double=False):
        for delta in (-.065, .065) if double else (0,):
            self.add(f'rdStack(cv {lo} {hi} {x+delta:.4f} {y:.4f})')

    def port(self, name, layer, x, y, width=.16):
        assert name not in self.ports
        self.ports[name] = (layer, x, y, width)
        self.add(f'cmpPort(cv rdNet(cv "{name}") "M{layer}" cmpPoint({x:.4f} {y:.4f}) {width})')


def array(d, grid, center="inverted"):
    bottom = defaultdict(list)
    outward = {}
    terminals = defaultdict(set)
    for r in range(-1, 9):
        base = r * PY
        flip = r % 2 == 1
        bot_y = base + (2.365 if flip else .055)
        top_y = base + (.055 if flip else 2.365)
        for c in range(-1, 33):
            active = (c, r) in grid
            bot = grid.get((c, r), "VSS")
            d.add(f'rdMom(cv "C_{c+1}_{r+1}_{bot}" {col(c):.4f} {base:.4f} '
                  f'{"t" if flip else "nil"} "{"TOP" if active else "VSS"}" "{bot}")')
        if r in (-1, 8):
            for y in [bot_y, top_y]:
                d.wire("VSS", 3, col(-1)+.38, y, col(32)+.38, y, .11)
        for c in [-1, 32]:
            x = col(c)+(-.17 if c==-1 else .93)
            for y in [top_y, bot_y]:
                d.wire("VSS", 3, col(c)+.38, y, x, y, .11)
                d.via(3, 4, x, y)
                bottom["VSS", x, x].append(y)
        if r in (-1, 8):
            continue
        outward[bot_y] = 1 if flip else -1
        track_y = base - .25 if flip else base + MOM_H + .25
        for c in range(32):
            x = col(c)+.38
            d.wire("TOP", 3, x, base if flip else base+MOM_H, x, track_y, .10)
        if not flip:
            d.wire("TOP", 3, col(0)+.38, track_y, TOP_X, track_y)
        for net, members in groupby(range(32), lambda c: grid[c, r]):
            columns = list(members)
            first, last = columns[0], columns[-1]
            for a, b in zip(columns, columns[1:]):
                # Bridge the two native plate straps across their gap.
                d.wire(net, 3, col(a)+.735, bot_y, col(b)+.025, bot_y, .11)
            if first in (15, 16):
                # Escape only inside the bottom channel on M5. All active
                # columns, including the two singleton sites, keep the same pitch.
                gap = CENTER[center]["gaps"][net]
                if center == "inverted":
                    gap = gap if first == 15 else 32-gap
                trunk = col(gap)-.10
                bottom[net, col(first)+.38, trunk].append(bot_y)
                continue
            if net == 'B7':
                # Place two pickups symmetrically in each three- or five-cell MSB run.
                middle = first + len(columns)//2
                for gap in (middle, middle+1):
                    x = col(gap)-.10
                    bottom[net, x, x].append(bot_y)
                continue
            if first == last:
                x = col(first) + (-.10 if first < 16 else .86)
            else:
                x = col(first + len(columns)//2)-.10
            if x < col(first) or x > col(last)+.76:
                edge = col(first)+.025 if x < col(first) else col(last)+.735
                d.wire(net, 3, edge, bot_y, x, bot_y, .11)
            bottom[net, x, x].append(bot_y)
    levels = {n: -3.30-.26*i for i, n in enumerate(["VSS","TERM"]+[f"B{i}" for i in range(8)])}
    for (net, x, trunk), ys in bottom.items():
        # Give the high-weight runs native paired vias and wider bottom rails.
        # The rail widths set both resistance and coupling to the facing TOP rows.
        width = M4_BOTTOM_WIDTH.get(net, .14)
        ys = sorted(ys)
        taps = []
        while ys:
            a = ys.pop(0)
            if net != "VSS" and ys and ys[0]-a < .72:
                b = ys.pop(0)
                d.wire(net, 3, x, a, x, b, .10)
                a = (a+b)/2
            elif net != "VSS":
                landing = a + outward[a]*(.18 if x!=trunk else .22)
                d.wire(net, 3, x, a, x, landing, .10)
                a = landing
            if x != trunk:
                d.via(3, 5, x, a)
                d.wire(net, 5, x, a, trunk, a, .12)
                d.via(4, 5, trunk, a)
            elif net != "VSS":
                d.via(3, 4, x, a, double=width>.18)
            taps.append(a)
        if net in M4_FAR_WIDTH:
            # The switch end collects all eight rows. Taper the far half where
            # less current is collected and the metal overlaps the MOM array.
            split_y = (7*PY + MOM_H)/2
            d.wire(net, 4, trunk, levels[net], trunk, split_y, width)
            d.wire(net, 4, trunk, split_y, trunk, max(taps), M4_FAR_WIDTH[net])
        else:
            d.wire(net, 4, trunk, levels[net], trunk, max(taps), width)
        d.via(4, 5, trunk, levels[net], double=width>.18)
        terminals[net].add(trunk)
    owners = {}
    for net, xs in terminals.items():
        for x in xs:
            track = round(x, 3)
            assert track not in owners, f"M4 track {track} shared by {net} and {owners.get(track)}"
            owners[track] = net
    d.wire("TOP", 3, TOP_X, MOM_H+.25, TOP_X, TOP_Y)
    d.port("TOP", 3, TOP_X, TOP_Y)
    return levels, terminals


def bank_placement():
    rows = [[(7,64),(7,64)]]*3 + [[(6,64),(6,64)], [(5,64),(6,64)],
                                    [(5,32),(4,48),(3,24),(2,12),(1,6),(0,3)]]
    placed = []
    for row, groups in enumerate(rows):
        pitches = [nf*.19+.85 for _, nf in groups]
        split = min(range(1, len(groups)), key=lambda i: abs(sum(pitches[:i])-sum(pitches)/2))
        start = (32.8-sum(pitches)-.85)/2+.42
        taps = [-.55, start+sum(pitches[:split])+.02, 32.90]
        devices = []
        for i, (bit, nf) in enumerate(groups):
            x = start+sum(pitches[:i])+(.85 if i>=split else 0)
            devices.append((bit, nf, x))
        placed.append((-7.55-2.70*row, devices, taps))
    counts = Counter()
    for _, devices, _ in placed:
        for b, nf, x in devices:
            counts[b] += nf
    assert counts == {b: 3*2**b for b in range(8)}
    return placed


def switch_tracks(rows):
    # In the mixed row each bit gets three adjacent trunks within its own block.
    # The single-bit rows can reach these trunks without crossing other bit wires.
    used = [x for xs in SUPPLY.values() for x in xs]
    positions = {}
    for bit in [0, 1, 2, 3, 4, 5, 6, 7]:
        _, devices, _ = next(row for row in reversed(rows) if any(b==bit for b,n,x in row[1]))
        group = [(nf, x) for b, nf, x in devices if b == bit]
        center = (group[0][1]+group[-1][1]+(group[-1][0]-1)*.19+.09)/2
        for name, dx in [(f"B{bit}",0), (f"GN{bit}",-.33), (f"GP{bit}",.33)]:
            sites = [i*.16 for i in range(0, 207) if all(abs(i*.16-u)>=.30 for u in used)]
            x = min(sites, key=lambda v: abs(v-center-dx))
            positions[name] = x
            used.append(x)
    return positions


def bank(d, levels, array_tracks):
    rows = bank_placement()
    tracks = switch_tracks(rows)
    touches = defaultdict(list)
    term_x = min(array_tracks["TERM"])
    d.port("TERM", 5, term_x, levels["TERM"])
    for net, xs in array_tracks.items():
        if net == "TERM":
            continue
        x = SUPPLY[net][0] if net in SUPPLY else tracks[net]
        y = levels[net]
        d.wire(net, 5, min(*xs, x), y, max(*xs, x), y, .16)
        d.via(5, 6, x, y, double=net in SUPPLY)
        touches[net].append(y)
    for row, (yn, devices, taps) in enumerate(rows):
        yp = yn-1.10
        d.add(f'cmpRect(cv "NW" -1.02 {yp-.235:.4f} {MIRROR/2:.4f} {yp+.58:.4f})')
        contacts = defaultdict(list)
        for idx, (bit, nf, x) in enumerate(devices):
            parts = math.ceil(nf/16)
            drains = [x+.33 if nf==3 else x+.045+.19*((p+.5)*nf/parts-.5) for p in range(parts)]
            gates = [x+.045+.19*max(0, int((p+.5)*nf/parts)-2) for p in range(parts)]
            def points(xs):
                return 'list('+' '.join(f'{v:.4f}' for v in xs)+')'
            for pol, y, model, ref, body in [
                    ('N',yn,'nch_mac','VREFN','VSS'), ('P',yp,'pch_mac','VREFP','VDD')]:
                gate = f"G{pol}{bit}"
                d.add(f'rdSwitch(cv "SW_{pol}_{row}_{idx}" "{model}" {nf} {x:.4f} {y:.4f} '
                      f'"B{bit}" "{gate}" "{ref}" "{body}" {points(drains)} {points(gates)})')
                contacts[gate, y+.33].extend(gates)
            for xd in drains:
                d.wire(f"B{bit}", 3, xd, yp-.12, xd, yn-.12, .10)
                d.via(3, 4, xd, yn-.12)
            contacts[f"B{bit}", yn-.12].extend(drains)
        for (net, y), xs in contacts.items():
            x = tracks[net]
            d.wire(net, 4, min(*xs,x), y, max(*xs,x), y, .14)
            d.via(4, 6, x, y)
            touches[net].append(y)
        for ref, body, y, implant in [('VREFN','VSS',yn,'PP'),('VREFP','VDD',yp,'NP')]:
            for x in taps:
                d.add(f'rdTap(cv "{implant}" {x:.4f} {y+.11:.4f})')
                d.via(2, 4, x, y-.40)
            d.wire(ref, 2, min(taps), y-.40, max(taps), y-.40, .16)
            for net, level in [(ref,y-.40),(body,y+.11)]:
                xs = [*taps,*SUPPLY[net]]
                d.wire(net, 4, min(xs), level, max(xs), level, .16 if net==ref else .12)
                for x in SUPPLY[net]:
                    d.via(4, 6, x, level, double=True)
                touches[net].append(level)
    for net, x in tracks.items():
        ys = touches[net]
        if net.startswith("G"):
            ys.append(GATE_EDGE)
            d.port(net, 6, x, GATE_EDGE)
        d.wire(net, 6, x, min(ys), x, max(ys), .16)
    for net, xs in SUPPLY.items():
        ymax = max(touches[net] + ([levels["TERM"]] if net.startswith('VREF') else []))
        for x in xs:
            d.wire(net, 6, x, GLOBAL_Y[net], x, ymax, .24)
        d.port(net, 6, xs[0], GLOBAL_Y[net], .24)
    return rows


def fill_plan():
    """Planned OD/PO fill and fill blockages of the MOM array, in wrapper coordinates.

    Layout/specs/fill-policy.md: OD.DN.3/PO.DN.3 windows (20 um) fall inside the array,
    so the array carries its own deterministic dummy OD/PO. Every column gap holds one
    stripe, also outside both dummy columns, so each unit sees the same pattern. A native
    unit has its bottom-plate finger on the left edge and a TOP finger on the right edge;
    the stripe sits on the bottom-plate side of each gap, 15 nm clear of both neighbouring
    TOP fingers. Dummy OD breaks 0.1 um short of every TOP strap (TOP-track channels);
    the dummy poly runs through for PO density. The P half is the mirror image. ODBLK,
    POBLK and DM1..DM9EXCL over the array keep the fill utilities out; they do not
    exempt any density rule.
    """
    shapes = []
    for c in range(-1, 34):
        x = col(c)
        # Rows 2k-1 and 2k face across a bottom-plate channel; their TOP straps are outside.
        for k in range(5):
            shapes.append(("OD", "dummy", x-.19, (2*k-1)*PY+.21, x+.09, 2*k*PY+MOM_H-.21))
        shapes.append(("PO", "dummy", x-.11, -PY, x+.01, 8*PY+MOM_H))
    shapes += [(layer, purpose, MIRROR-x1, y0, MIRROR-x0, y1) for layer, purpose, x0, y0, x1, y1 in shapes]
    # The default utility leaves the bottom 20 um OD windows of the switch bank about 1%
    # short. Dummy MOS bars fill the free strip between the substrate ring and the south
    # supply buses: dummy OD 0.35 um from the ring OD, dummy poly 0.27 um from it, both
    # at least 0.2 um inside the module edge.
    for k in range(-37, 37):
        x = MIRROR/2 + .48 + k*PX
        shapes.append(("OD", "dummy", x-.25, -25.62, x+.25, -23.71))
        shapes.append(("PO", "dummy", x-.15, -25.70, x+.15, -23.63))
    # Mx.DN.7 needs one of M5/M6/M7 at 5% in every 30 um window. Floating utility fill over
    # the array lowers the wide B7 trunks' TOP coupling more than the other bits', so the
    # array keeps no metal fill. Instead one 1.2 um dummy M7 line runs above each VSS dummy
    # row (about 7% in every window), away from the active TOP straps and bottom-plate trunks.
    for y in (-PY + MOM_H/2, 8*PY + MOM_H/2):
        for x0, x1 in ((col(-1), col(32)+.76), (MIRROR-col(32)-.76, MIRROR-col(-1))):
            shapes.append(("M7", "dummy", x0, y-.60, x1, y+.60))
    block = (col(-1)-.40, -PY-.08, MIRROR-col(-1)+.40, 8*PY+MOM_H+.08)
    shapes += [(layer, purpose, *block) for layer, purpose in
               [("ODBLK", "dummy"), ("POBLK", "dummy")] + [("DMEXCL", f"dummy{k}") for k in range(1, 10)]]
    return shapes


def generate(dest=OUTPUT, planned_fill=False, center="inverted"):
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    grid = assignment(center)
    half = Drawing()
    levels, array_tracks = array(half, grid, center)
    rows = bank(half, levels, array_tracks)
    core = Drawing()
    for side, origin, orient in [('N',0,'R0'),('P',MIRROR,'MY')]:
        core.add(f'inst=rdChild(cv "{HALF}" "X{side}" {origin} "{orient}")')
        for local, (layer,x,y,w) in half.ports.items():
            xp = x if side=='N' else origin-x
            net = (f'TOP{side}' if local=='TOP' else 'G'+side+local[1:] if local.startswith('G')
                   else 'VREF'+side if local=='TERM' else local)
            core.add(f'dbCreateInstTerm(rdNet(cv "{net}") inst dbFindTermByName(inst~>master "{local}"))')
            if local=='TERM':
                refx = SUPPLY[net][-1] if side=='N' else origin-SUPPLY[net][-1]
                core.wire(net, 5, xp, y, refx, y, .16)
                core.via(5, 6, refx, y, double=True)
            elif local not in SUPPLY:
                core.port(net, layer, xp, y, w)
    for net, xs in SUPPLY.items():
        y = GLOBAL_Y[net]
        xs = xs+[MIRROR-x for x in xs]
        core.wire(net, 5, min(xs), y, max(xs), y, .32)
        for x in xs:
            core.via(5, 6, x, y, double=True)
        core.port(net, 5, MIRROR/2, y, .32)
    core.add(f'rdRing(cv -1.55 -23.27 {MIRROR+1.55:.4f} -6.45)')
    # Connect both sides of the common substrate ring to the physical body bus.
    for a, b in [(-1.55,-.55),(MIRROR+1.55,MIRROR+.55)]:
        y = rows[0][0]+.11
        core.via(1, 4, a, y, double=True)
        core.wire('VSS', 4, a, y, b, y, .12)
    assert sorted(core.ports)==sorted(PORTS)
    cells = [(HALF,half), (CORE,core)]
    wrapper = Drawing()
    if planned_fill:
        # Separate fill cell referenced by the wrapper; the functional core stays fill-free.
        plan = Drawing()
        for layer, purpose, x0, y0, x1, y1 in fill_plan():
            plan.add(f'rdLpp(cv "{layer}" "{purpose}" {x0:.4f} {y0:.4f} {x1:.4f} {y1:.4f})')
        cells.append((FILL, plan))
        wrapper.add(f'rdChild(cv "{FILL}" "XFILLPLAN" 0 "R0")')
    wrapper.add(f'inst=rdChild(cv "{CORE}" "XCORE" 0 "R0")')
    for name, args in core.ports.items():
        wrapper.add(f'dbCreateInstTerm(rdNet(cv "{name}") inst dbFindTermByName(inst~>master "{name}"))')
        wrapper.port(name, *args)
    cells.append((TOP, wrapper))
    common = (ROOT/'Layout/design/compact.il').read_text().split('procedure(cmpReadback()')[0]
    native = (ROOT/'Layout/design/cdac_paired.il').read_text()
    if planned_fill:
        native += '\n' + (ROOT/'Layout/design/cdac_fill_plan.il').read_text()
    statements = ['procedure(rdBuild() let((cv inst lib)', 'lib=ddGetObj(rdLib)',
                  'cmpRequire(lib && equal(lib~>readPath rdPath) "Wrong candidate library")']
    for cell, drawing in cells:
        statements += [f'cv=rdOpen("{cell}")', *drawing.lines,
                       f'cmpRequire(length(cv~>terminals)=={len(drawing.ports)} "Port count")',
                       'cmpRequire(dbSave(cv) "Cannot save candidate")', 'dbClose(cv)']
    statements += [f'cv=dbOpenCellViewByType(rdLib "{TOP}" rdView "" "r")',
                   f'cmpRequire(cv && length(cv~>terminals)=={len(PORTS)} "Saved interface readback")',
                   f'printf("PILOT_OA_OK {TOP} instances=%d ports=%d bbox=%L\\n" '
                   'length(cv~>instances) length(cv~>terminals) cv~>bBox)',
                   'dbClose(cv) t))', 'if(errset(rdBuild() t) then exit(0) else exit(1))']
    (dest/'paired.il').write_text(common+'\n'+native+'\n'+'\n'.join(statements)+'\n',encoding='ascii')
    reference, electrical_sha = independent_reference()
    (dest/'cdac-full-reference.cdl').write_text(reference,encoding='ascii')
    intent = {'electrical_source_sha256':electrical_sha, 'core':CORE, 'half':HALF, 'top':TOP,
              'ports':core.ports, 'pitch_um':[PX,PY], 'array_x_um':ARRAY_X,
              'mirror_um':MIRROR, 'rows_bottom_to_top':[[grid[c,r] for c in range(32)] for r in range(8)],
              'switch_rows':rows, 'major_bottom_rail_widths_um':M4_BOTTOM_WIDTH,
              'major_far_rail_widths_um':M4_FAR_WIDTH,
              'bottom_trunks_per_side':{n:sorted(xs) for n,xs in array_tracks.items()},
              'planned_fill_cell':FILL if planned_fill else None, 'center_layout':center}
    (dest/'placement.json').write_text(json.dumps(intent,indent=2)+'\n')
    return dest


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--planned-fill", action="store_true",
                        help=f"Add the planned array fill cell {FILL} to the wrapper")
    parser.add_argument("--center", choices=sorted(CENTER), default="inverted",
                        help="Small-bit layout of center columns 15/16 (stacked: trunk length follows weight)")
    parser.add_argument("--dest", default=str(OUTPUT))
    args = parser.parse_args()
    print(generate(args.dest, args.planned_fill, args.center))
