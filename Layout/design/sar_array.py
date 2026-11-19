"""Regular bit rows, folded resistor bank and a common MOM array for the SAR/timing core."""

import itertools
from collections import Counter, defaultdict
from dataclasses import dataclass
from math import ceil

from Layout.design.sar_reference import ARRAY_DECAPS, source_cdl
from Layout.design.sar_timing import (
    MOM,
    TIM,
    Drawing,
    Floorplan,
    electrical,
    write_design,
)
from Layout.project import ROOT


@dataclass(frozen=True)
class ArrayPlan:
    columns: int = 20
    site: float = 0.14
    row_height: float = 1.20
    mom_pitch_x: float = 0.92
    mom_pitch_y: float = 3.14
    mom_height: float = 2.92
    resistor_pitch: float = 2.90
    supply_width: float = 0.40
    channel: float = 0.84
    margin: float = 0.84
    switch_well_clearance: float = 0.56


def delay_groups():
    return (
        "XIDLE/XD",
        "XSEQ/XD",
        TIM + "/XD_QUIET_D",
        TIM + "/XD_WRITE_D",
        TIM + "/XD_RAW_D",
    )


def place_logic(f, plan):
    logic = []
    for first in range(0, 8, 2):
        groups = []
        for bit in (first, first + 1):
            groups.extend((f"XCTRL/XBIT{bit}", f"XCTRL/XSEQ/XF{bit}"))
        logic.append((f"bits{first}_{first + 1}", groups))

    def timing(*names):
        return [TIM + "/" + s for s in names]

    logic.extend(
        (
            (
                "comp_p",
                timing(
                    "X002",
                    "X006",
                    "X008",
                    "X009",
                    "X010",
                    "X011",
                    "X015",
                    "X016",
                    "X017",
                    "X018",
                    "X019",
                    "X020",
                ),
            ),
            (
                "control",
                ["XCTRL/XSEQ/X001"]
                + [f"XCTRL/X{i:03}" for i in (15, 14, 13, 12, 17, 16, 18)],
            ),
            ("comp_n", timing("X003", "X004", "X005", "X000", "X001", "X013", "X014")),
            (
                "clock",
                timing("X025/X001", "X025/X000", "XCLOCK", "X023", "X022")
                + [
                    "XSAMPLE",
                    "XIDLE/XA",
                    "XIDLE/XB",
                    "XIDLE/XN",
                    "XIDLE/XP",
                    "XSEQ/XA",
                    "XSEQ/XB",
                ],
            ),
        )
    )
    for index, (name, groups) in enumerate(logic):
        flipped = bool(index % 2)
        y = plan.margin + (index + int(flipped)) * plan.row_height
        f.row(
            name,
            plan.margin,
            round(y, 3),
            groups,
            mx=flipped,
            decap=ARRAY_DECAPS.get(name),
        )
    return plan.margin + len(logic) * plan.row_height


def place_floor(devices, plan):
    f = Floorplan(devices)
    logic_top = place_logic(f, plan)
    delays = delay_groups()
    quiet = TIM + "/XD_QUIET_D"
    lengths = {
        d + f"/R{i}": float(devices[d + f"/R{i}"].parameters["l"].removesuffix("u"))
        for d in delays
        for i in (0, 1)
    }
    bay_width = max(max(row["width"] for row in f.rows), max(lengths.values()) + 0.74)
    long_right = plan.margin + max(lengths.values()) + 0.74
    lane_x = ceil((long_right + plan.channel / 2) / plan.site) * plan.site
    r_bottom = logic_top + 1.5 * plan.channel
    quiet_bottom = r_bottom + 4 * plan.resistor_pitch
    quiet_end = plan.margin + max(lengths[quiet + f"/R{i}"] + 0.74 for i in (0, 1))
    lane_y = logic_top + plan.channel
    for kind, members in (
        ("row", delays[:1]),
        ("clear", delays[:2]),
        ("row", delays[1:2]),
        ("row", delays[2:3]),
        ("clear", delays[2:3]),
        ("row", delays[3:4]),
        ("clear", delays[3:]),
        ("row", delays[4:]),
    ):
        if kind == "row":
            sx = (
                ceil((quiet_end + plan.channel) / plan.site) * plan.site
                if members == (quiet,)
                else lane_x
            )
            sy = quiet_bottom + plan.row_height if members == (quiet,) else lane_y
            name = "detect" + str(delays.index(members[0]))
            f.row(
                name,
                round(sx, 3),
                round(sy, 4),
                members,
                decap=ARRAY_DECAPS.get(name),
            )
            lane_y += plan.row_height + plan.channel
        else:
            cx = (
                long_right - plan.channel - plan.switch_well_clearance
                if members == (quiet,)
                else lane_x + 1.12
            )
            cy = (
                quiet_bottom + plan.row_height / 2 - plan.switch_well_clearance
                if members == (quiet,)
                else lane_y + plan.switch_well_clearance
            )
            f.clear_row(members, round(cy, 4), center=cx)
            lane_y += 3.0 + 2 * plan.channel

    cap_x = (
        max(plan.margin + bay_width, max(row["x"] + row["width"] for row in f.rows))
        + plan.channel
        - plan.site / 2
    )
    cap_y = plan.margin
    resistor_row = 0
    banks = []
    for group in delays:
        for stage in (0, 1):
            rkey, ckey = group + f"/R{stage}", group + f"/C{stage}"
            rp, cp = devices[rkey].parameters, devices[ckey].parameters
            if (
                rp["w"] != "1u"
                or devices[rkey].pins["MINUS"] != devices[ckey].pins["PLUS"]
            ):
                raise ValueError("Review delay resistor " + rkey)
            r_width = lengths[rkey] + 0.74
            rx = plan.margin + r_width - 0.19
            ry = r_bottom + resistor_row * plan.resistor_pitch + 0.53
            orient = "MY"
            rname = f.place(rkey, rx, ry, orient, {"l": rp["l"], "w": rp["w"]})
            resistor_row += 1
            banks.append(
                {
                    "name": ckey,
                    "resistor": rname,
                    "units": int(cp["multi"]),
                    "columns": plan.columns,
                    "x": round(rx + (0.04 if orient == "R0" else -0.04), 4),
                    "y": round(ry + 0.5, 4),
                }
            )
    occupied = set()
    cursor = 0
    last_row = ceil(sum(bank["units"] for bank in banks) / plan.columns) - 1
    for bank in sorted(banks, key=lambda b: b["units"] > 4):
        qty = bank.pop("units")
        if qty <= 4:
            row = round((bank["y"] - cap_y - plan.mom_height / 2) / plan.mom_pitch_y)
            row = min(last_row, max(0, row))
            slots = next(
                list(range(row * plan.columns + c, row * plan.columns + c + qty))
                for c in range(plan.columns - qty + 1)
                if not occupied.intersection(
                    range(row * plan.columns + c, row * plan.columns + c + qty)
                )
            )
        else:
            slots = []
            while len(slots) < qty:
                if cursor not in occupied:
                    slots.append(cursor)
                cursor += 1
        occupied.update(slots)
        bank["instances"] = []
        for unit, slot in enumerate(slots):
            row, col = divmod(slot, plan.columns)
            flip = bool(row % 2)
            name = f.place(
                bank["name"],
                cap_x + col * plan.mom_pitch_x,
                cap_y + row * plan.mom_pitch_y + flip * plan.mom_height,
                "MX" if flip else "R0",
                MOM,
                copy=unit,
            )
            bank["instances"].append(name)
    f.banks = banks
    # Keep the dynamic clock storage capacitor at its receiver, outside the delay array.
    clock = next(r for r in f.rows if r["name"] == "clock")
    f.place(
        TIM + "/XCLOCK/CQB",
        clock["x"] + clock["width"] + plan.channel + plan.mom_height,
        clock["y"] - plan.row_height,
        "R90",
        MOM,
    )
    expected = Counter(
        {
            k: int(d.parameters["multi"]) if d.master == "cfmom_2t" else 1
            for k, d in devices.items()
        }
    )
    actual = Counter(q["source"] for q in f.placed.values() if q["source"])
    if expected != actual:
        raise ValueError("Array placement does not cover the electrical reference")
    height = max(
        r_bottom + (resistor_row - 1) * plan.resistor_pitch + 2.06,
        lane_y,
        cap_y + (max(occupied) // plan.columns + 1) * plan.mom_pitch_y,
    )
    width = cap_x + (plan.columns - 1) * plan.mom_pitch_x + 0.76
    return (
        f,
        cap_x,
        (
            ceil((width + plan.margin) / plan.site) * plan.site,
            ceil((height + plan.margin) / plan.row_height) * plan.row_height,
        ),
    )


def local_plates(f, g, plan, cap_x):
    rows = defaultdict(list)
    for b in f.banks:
        for name in b["instances"]:
            q = f.placed[name]
            x, y = q["xy"]
            direction = 1 if q["orient"] == "R0" else -1
            py, gy = round(y + direction * 2.865, 4), round(y + direction * 0.055, 4)
            col = round((x - cap_x) / plan.mom_pitch_x)
            rows[py, gy].append((col, x + 0.38, q["pins"]["PLUS"], name))
    spine = round(cap_x - plan.channel / 2, 3)
    groups = defaultdict(list)
    grounds = []
    for (py, gy), cells in sorted(rows.items()):
        cells.sort()
        for col, x, net, name in cells:
            g.checked(name, "PLUS", 3, x, py)
            g.checked(name, "MINUS", 3, x, gy)
        for left, right in itertools.pairwise(cells):
            for y, net in ((gy, "VSS"), (py, left[2])):
                if y == gy or left[2] == right[2]:
                    g.rect(
                        "M3",
                        net,
                        left[1] + 0.365,
                        y - 0.055,
                        right[1] - 0.365,
                        y + 0.055,
                    )
        g.wire(3, "VSS", spine, gy, cells[0][1], gy, 0.10)
        g.call("stPowerVia", 3, "VSS", spine, gy, 1)
        grounds.append(gy)
        for net in {c[2] for c in cells}:
            cols = [c[0] for c in cells if c[2] == net]
            groups[net].append((min(cols), max(cols), py))
    for net, segments in groups.items():
        tapped = set()
        for a, b in zip(segments, segments[1:] or segments):
            col = max(a[0], b[0])
            if col > min(a[1], b[1]):
                raise ValueError("No common plate between successive rows of " + net)
            x = round(cap_x + col * plan.mom_pitch_x + 0.38, 4)
            for y in {a[2], b[2]}:
                if (x, y) not in tapped:
                    g.via(3, x, y, net)
                    tapped.add((x, y))
            if a[2] == b[2]:
                g.rect("M4", net, x - 0.05, a[2] - 0.125, x + 0.05, a[2] + 0.125)
            else:
                g.wire(4, net, x, a[2], x, b[2], 0.10)
        # Put a legal router landing on the plate nearest its resistor terminal.
        bank = next(
            b for b in f.banks if f.placed[b["instances"][0]]["pins"]["PLUS"] == net
        )
        landings = [
            (round(cap_x + left * plan.mom_pitch_x + 0.38, 4), y)
            for left, _, y in segments
        ]
        x, y = min(
            landings,
            key=lambda point: abs(point[0] - bank["x"]) + abs(point[1] - bank["y"]),
        )
        if (x, y) not in tapped:
            g.via(3, x, y, net)
            g.rect("M4", net, x - 0.05, y - 0.125, x + 0.05, y + 0.125)
    storage = (TIM + "/XCLOCK/CQB").replace("/", "__")
    q = f.placed[storage]
    for pin, dx in (("PLUS", 2.865), ("MINUS", 0.055)):
        x, y = q["xy"][0] - dx, q["xy"][1] + 0.38
        net = q["pins"][pin]
        g.checked(storage, pin, 3, x, y)
        g.via(3, x, y, net)
        g.rect("M4", net, x - 0.05, y - 0.125, x + 0.05, y + 0.125)
    g.wire(4, "VSS", spine, min(grounds), spine, max(grounds), 0.26)
    return spine


def reset_contacts(f, g):
    for seam in f.seams:
        x, y, w = seam["x"], seam["y"], seam["width"]
        net = seam["net"]
        tap = x + (-0.61 if net == "VSS" else 0.61)
        source = x if seam["shared"] else x - 0.065
        g.call("stBody", net, source, tap, y, w, int(seam["shared"]))
        cy = y + 0.945
        for cx in (source, tap):
            g.via(1, cx, cy, net, horizontal=True)
        g.wire(2, net, source, cy, tap, cy, 0.08)
        for i, name in enumerate(seam["devices"]):
            q = f.placed[name]
            gx = q["xy"][0] + (0.015 if q["orient"] == "R0" else -0.015)
            g.call(
                "stGate",
                q["pins"]["G"],
                gx,
                y + (w if i else 0),
                1 if i else -1,
                "NP" if net == "VSS" else "PP",
            )


def power(f, g, plan, spine, height):
    # Digital-row and threshold-detector rails have separate vertical feeds to the header.
    left = plan.margin
    right = max(
        r["x"] + r["width"] for r in f.rows if not r["name"].startswith("detect")
    )
    drops = defaultdict(set)
    for r in f.rows:
        for rail in ("VDD", "VSS"):
            y = r["y"] + (
                (1 if r["orient"] == "R0" else -1) * plan.row_height
                if rail == "VDD"
                else 0
            )
            coords = drops[rail, round(y, 4), r["name"].startswith("detect")]
            coords.update(
                (round(r["x"] + 0.21, 4), round(r["x"] + r["width"] - 0.21, 4))
            )
            for ident, q in f.placed.items():
                if ident.startswith("ROW_" + r["name"] + "_TAPCELL_"):
                    coords.add(round(q["xy"][0] + 0.28, 4))
    for rail in ("VDD", "VSS"):
        offset = 0.0 if rail == "VDD" else plan.channel
        columns = [left + plan.channel + offset, right - 2 * plan.channel + offset]
        sense = right + plan.channel / 2 + offset
        # A short row has a direct upper-metal feed to each end of its M1 rail.
        feed_y = height - plan.margin - (plan.channel if rail == "VSS" else 0)
        ys = defaultdict(list)
        for (net, y, detector), points in drops.items():
            if net != rail:
                continue
            feeds = [sense] if detector else columns
            extent = list(points) + feeds
            if detector and rail == "VSS":
                extent.append(spine)
                g.call("stPowerVia", 4, rail, spine, y)
            g.wire(5, rail, min(extent), y, max(extent), y, 0.32)
            for x in sorted(points):
                for level in range(1, 5):
                    g.call("stPowerVia", level, rail, x, y)
            for x in feeds:
                g.call("stPowerVia", 5, rail, x, y)
                ys[x].append(y)
        for x, starts in ys.items():
            g.wire(6, rail, x, min(starts), x, feed_y, plan.supply_width)
            g.call("stPowerVia", 5, rail, x, feed_y)
        g.wire(5, rail, min(ys), feed_y, max(ys), feed_y, plan.supply_width)
        g.pin(rail, 5, min(ys), feed_y, plan.supply_width, plan.supply_width)


def ports(f, g, plan):
    for net, path, term in (
        ("COMP_P", "X002/X000", "I"),
        ("COMP_N", "X003/X000", "I"),
        ("CMP_CLK", "X025/X001", "ZN"),
    ):
        name = (TIM + "/" + path + "/XLIB").replace("/", "__")
        q = f.placed[name]
        x = q["xy"][0] + (0.21 if net == "CMP_CLK" else 0.07)
        dy = 0.86 if net == "CMP_CLK" else 0.695
        y = q["xy"][1] + (dy if q["orient"] == "R0" else -dy)
        edge = plan.site * 2
        g.checked(name, term, 1, x, y)
        g.via(1, x, y, net, horizontal=True)
        g.wire(2, net, edge, y, x, y, 0.07)
        g.pin(net, 2, edge, y, 0.07, 0.07)
    for bit in range(8):
        # Both flip-flop clock pins have a narrow native M1 contact enclosure.
        # Use the same single-cut entrance at every receiver and route the clocks on M2 and above.
        for instance in (
            f"XCTRL__XSEQ__XF{bit}__XFF",
            f"XCTRL__XBIT{bit}__XSTORE__XFF",
        ):
            _, x, y = g.access(instance, "CP")
            net = f.placed[instance]["pins"]["CP"]
            g.via(1, x, y, net, horizontal=True)
            g.rect("M2", net, x - 0.105, y - 0.035, x + 0.105, y + 0.035)
        r = f.rows[bit // 2]
        low = r["y"] - (plan.row_height if r["orient"] == "MX" else 0)
        g.pin(
            f"D{bit}",
            3,
            plan.site * 2,
            low + (0.32 if bit % 2 == 0 else 0.88),
            0.28,
            0.08,
        )
        g.pin(
            f"CODE{bit}",
            3,
            plan.margin + (bit + 0.5) * f.rows[0]["width"] / 8,
            plan.site * 2,
            0.08,
            0.28,
        )
    for i, n in enumerate(("PHI_U", "PRESET", "SEQ_SAMPLE", "SAMPLE", "SAMPLE_INT")):
        g.pin(
            n,
            3,
            plan.site * 2,
            plan.margin + plan.row_height * (4.0 + 0.55 * i),
            0.28,
            0.08,
        )


def generate(destination=None, plan=ArrayPlan()):
    devices, interface, hashes = electrical()
    f, cap_x, outline = place_floor(devices, plan)
    g = Drawing(f)
    spine = local_plates(f, g, plan, cap_x)
    reset_contacts(f, g)
    power(f, g, plan, spine, outline[1])
    ports(f, g, plan)
    if set(interface) != set(g.port_locations):
        raise ValueError("Changed SAR interface")
    out = destination or ROOT / "work/layout/sar-refinement/seed"
    write_design(
        f,
        g,
        hashes,
        interface,
        out,
        [round(x, 3) for x in outline],
        mom_route_clearance=0.12,
    )
    (out / "array-leaves.cdl").write_text(
        source_cdl(array_decaps=True), encoding="ascii", newline="\n"
    )


if __name__ == "__main__":
    generate()
