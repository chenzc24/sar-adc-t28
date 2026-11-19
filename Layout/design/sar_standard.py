"""Place eight identical SAR slices and fold the qualified T28 delay chains into cell rows."""

from collections import defaultdict
from math import ceil

from Layout.design.sar_reference import source_cdl
from Layout.design.sar_timing import (
    SUFFIX,
    TIM,
    Drawing,
    Floorplan,
    electrical,
    write_design,
)
from Layout.project import ROOT

SITE, HEIGHT = 0.14, 1.20
LEFT, BOTTOM = 6 * SITE, 0.48
DECAPS = {
    **{f"bit{i}": "DCAP8" for i in range(0, 8, 2)},
    "guard": "DCAP4",
    "comp_p": "DCAP8",
    "comp_n": "DCAP8",
    "clock": "DCAP8",
    "sample_b": "DCAP4",
}


def quiet_stage_count(devices):
    prefix = TIM + "/XD_QUIET_D/XD"
    return sum(name.startswith(prefix) and name[len(prefix):].isdigit() for name in devices)


def layout_rows(devices):
    floor = Floorplan(devices)

    def group(*prefixes):
        return [
            k
            for prefix in prefixes
            for k in sorted(devices)
            if (k == prefix or k.startswith(prefix + "/"))
            and devices[k].master.endswith(SUFFIX)
        ]

    def chain(branch, start, stop):
        return [
            k
            for i in range(start, stop + 1)
            for k in group(f"{branch}/XD{i}", f"{branch}/XQUAL{i}")
        ]

    def timing(*names):
        return group(*(TIM + "/" + name for name in names))

    def row(name, left, delay, reverse=False, tail=(), mirrored_tail=()):
        i = len(floor.rows)
        order = list(reversed(delay)) if reverse else delay
        floor.row(
            name,
            LEFT,
            round(BOTTOM + (i + i % 2) * HEIGHT, 4),
            [*left, *order, *tail],
            mx=bool(i % 2),
            decap=DECAPS.get(name),
            mirror_keys=(set(delay) if reverse else set()) | set(mirrored_tail),
        )

    quiet = TIM + "/XD_QUIET_D"
    quiet_length = quiet_stage_count(devices)
    compact = quiet_length in (5, 6)
    # Bit and token storage share the left columns. Keep their receiving/launching
    # gates in the same order in all eight rows and thread the idle chain beside them.
    for i in range(8):
        bit = f"XCTRL/XBIT{i}"
        slice_cells = group(
            bit + "/X002",
            bit + "/XSTORE",
            bit + "/XMUX",
            bit + "/XRESET_DATA_OR",
            f"XCTRL/XSEQ/XF{i}",
        )
        reduction = group(f"XCTRL/X{12 + i:03}") if i < 7 else group("XCTRL/XSEQ/X001")
        controls = group("XIDLE/XN") if i == 1 else group("XIDLE/XP") if i == 7 else []
        if compact and i == 5:
            controls += group("XSAMPLE") + timing("X000")
        if compact and i in (6, 7):
            controls += group("XIDLE/XA" if i == 6 else "XIDLE/XB")
        row(
            f"bit{i}",
            slice_cells + reduction + controls,
            chain("XIDLE/XD", 3 * i + 1, 3 * i + 3),
            bool(i % 2),
        )

    row(
        "guard",
        timing("X018", "X019") + (timing("X001") if quiet_length == 6 else []),
        chain("XIDLE/XD", 25, 29),
        tail=timing("X015", "X016", "X017"),
    )
    sample = "XSEQ/XD"
    single_sample = sample + "/XD2" not in devices
    final_qualifier = group(sample + "/XQUAL10") if quiet_length == 6 else []
    sample_outputs = group("XSEQ/XA", "XSEQ/XB")
    row(
        "comp_p",
        timing("X002", "X006") + final_qualifier + (sample_outputs if quiet_length == 6 and not single_sample else []),
        chain(TIM + "/XD_RAW_D", 1, 1)
        + timing("X008", "X009", "X010", "X011")
        + chain(TIM + "/XD_WRITE_D", 1, 3),
        tail=timing("X013", "X014") + ([] if quiet_length == 6 else timing("X001")),
    )
    fold = (quiet_length + 1) // 2
    row(
        "comp_n",
        timing("X003", "X004", "X005") + (timing("X023") if compact else []) + timing("X020"),
        chain(quiet, 1, fold),
        tail=chain(sample, 1, 2) if compact and not single_sample else (),
    )
    # The folded chain finishes on the left. Place its receiving buffer and
    # clock latch at that end, next to the comparator-clock output driver.
    # The two short QUIET rows have room at their outer edge for the start of
    # SAMPLE. Fold that chain across these rows and back toward its output.
    sample_turn = 4 if quiet_length == 6 else 5
    sample_return = chain(sample, 3, sample_turn) if compact else []
    row(
        "clock",
        timing("X025/X001", "X025/X000") + ([] if compact else timing("X023")) + timing("XCLOCK", "X022"),
        chain(quiet, fold + 1, quiet_length),
        True,
        tail=list(reversed(sample_return)),
        mirrored_tail=sample_return,
    )
    if not compact:
        row("sample_a", group("XSAMPLE", "XIDLE/XA", "XIDLE/XB") + timing("X000"), [] if single_sample else chain(sample, 1, 5))
    sample_last = [key for key in chain(sample, sample_turn + 1, 10) if key not in final_qualifier]
    if single_sample:
        row("sample_b", chain(sample, 1, 1), sample_outputs)
    else:
        row("sample_b", [] if quiet_length == 6 else sample_outputs, sample_last, True)
    if {p["source"] for p in floor.placed.values() if p["source"]} != set(devices):
        raise ValueError("Placement and active transistor netlist differ")
    return floor


def add_power(floor, drawing, width):
    drops = defaultdict(set)
    for row in floor.rows:
        for rail in ("VDD", "VSS"):
            sign = 1 if row["orient"] == "R0" else -1
            y = round(row["y"] + (sign * HEIGHT if rail == "VDD" else 0), 4)
            pts = drops[rail, y]
            pts.update(
                (round(row["x"] + 0.21, 4), round(row["x"] + row["width"] - 0.21, 4))
            )
            pts.update(
                round(q["xy"][0] + 0.28, 4)
                for n, q in floor.placed.items()
                if n.startswith("ROW_" + row["name"] + "_TAPCELL_")
            )
    for rail in ("VDD", "VSS"):
        # Two edge feeds and a feed at the bit/delay boundary, joined on every shared row rail.
        offset = 0 if rail == "VDD" else 5 * SITE
        feeds = [
            LEFT + 5 * SITE + offset,
            LEFT + 64 * SITE + offset,
            width - 12 * SITE + offset,
        ]
        ys = sorted(y for net, y in drops if net == rail)
        for y in ys:
            points = []
            for x in sorted(drops[rail, y]):
                # Neighboring rows already share the M1 rail. Keep one ladder where
                # their candidate taps would overlap on the same rail.
                if not points or x - points[-1] >= 3 * SITE - 1e-6:
                    points.append(x)
            extrema = points + feeds
            drawing.wire(5, rail, min(extrema), y, max(extrema), y, 0.32)
            for x in points:
                for lower in range(1, 5):
                    drawing.call("stPowerVia", lower, rail, x, y)
            for x in feeds:
                drawing.call("stPowerVia", 5, rail, x, y)
        for x in feeds:
            drawing.wire(6, rail, x, min(ys), x, max(ys), 0.40)
        drawing.pin(rail, 5, feeds[0], max(ys), 0.32, 0.32)


def add_ports(f, g):
    edge = 2 * SITE
    for net, path, term in (
        ("COMP_P", "X002/X000", "I"),
        ("COMP_N", "X003/X000", "I"),
        ("CMP_CLK", "X025/X001", "ZN"),
    ):
        name = (TIM + "/" + path + "/XLIB").replace("/", "__")
        q = f.placed[name]
        dx, dy = (0.21, 0.86) if net == "CMP_CLK" else (0.07, 0.695)
        x, y = q["xy"][0] + dx, q["xy"][1] + (dy if q["orient"] == "R0" else -dy)
        g.checked(name, term, 1, x, y)
        g.via(1, x, y, net, horizontal=True)
        g.wire(2, net, edge, y, x, y)
        g.pin(net, 2, edge, y, 0.07, 0.07)
    for bit in range(8):
        for instance in (
            f"XCTRL__XSEQ__XF{bit}__XFF",
            f"XCTRL__XBIT{bit}__XSTORE__XFF",
        ):
            _, x, y = g.access(instance, "CP")
            net = f.placed[instance]["pins"]["CP"]
            g.via(1, x, y, net, horizontal=True)
            g.rect("M2", net, x - 0.105, y - 0.035, x + 0.105, y + 0.035)
        low = BOTTOM + bit * HEIGHT
        for n, offset in ((f"D{bit}", 0.35), (f"CODE{bit}", 0.85)):
            g.pin(n, 3, edge, low + offset, 0.28, 0.08)
    for i, n in enumerate(("PHI_U", "SAMPLE_INT", "PRESET", "SAMPLE", "SEQ_SAMPLE")):
        g.pin(n, 3, edge, BOTTOM + (8.45 + i) * HEIGHT, 0.28, 0.08)


def generate(destination=None, *, quiet_stages=None, quiet_final_ps=250, sample_delay_ps=None):
    timing = dict(standard_delays=True, static_latch=True, quiet_stages=quiet_stages,
                  quiet_final_ps=quiet_final_ps, sample_delay_ps=sample_delay_ps)
    devices, ports, hashes = electrical(**timing)
    f = layout_rows(devices)
    right = max(r["x"] + r["width"] for r in f.rows)
    width = round(ceil((right + 3 * SITE) / SITE) * SITE, 3)
    height = round(BOTTOM + len(f.rows) * HEIGHT + 0.48, 3)
    g = Drawing(f)
    add_power(f, g, width)
    add_ports(f, g)
    if set(g.port_locations) != set(ports):
        raise ValueError("Routed ports disagree with the default SAR interface")
    stages = quiet_stage_count(devices)
    directory = "sar-standard" if stages == 9 and quiet_stages is None else f"sar-standard-q{stages}"
    last_cell = devices[f"{TIM}/XD_QUIET_D/XD{stages}"].master.removesuffix("D1" + SUFFIX)
    if last_cell != "DEL250":
        directory += "-" + last_cell.lower()
    if sample_delay_ps is not None:
        directory += "-sample%03d" % sample_delay_ps
    out = destination or ROOT / "work/layout" / directory / "seed"
    write_design(f, g, hashes, ports, out, [width, height], mom_route_clearance=0.12)
    (out / "standard-leaves.cdl").write_text(
        source_cdl(decaps=DECAPS, **timing),
        encoding="ascii",
        newline="\n",
    )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet-stages", type=int, choices=(5, 6, 9))
    parser.add_argument("--quiet-final-ps", type=int, choices=(200,250), default=250)
    parser.add_argument("--sample-delay-ps", type=int, choices=(75, 200))
    args = parser.parse_args()
    generate(quiet_stages=args.quiet_stages, quiet_final_ps=args.quiet_final_ps, sample_delay_ps=args.sample_delay_ps)
