"""Start the native SAR/timing floorplan from the active four-instance electrical hierarchy."""

import hashlib
import itertools
import json
import re
from collections import Counter
from dataclasses import dataclass

from Layout.project import ROOT
from tools.saradc.candidates import definitions
from tools.saradc.rnl import instances
from tools.saradc.quiet_delay import REFERENCE as STD_DELAY_REFERENCE, source_for_stages

CORE = "sar8_sar_timing_core"
STD = "tcbn28hpcplusbwp12t30p140"
SUFFIX = "BWP12T30P140"
OUT = ROOT / "work/layout/sar-start"
# Foundry SPICE order, using the pin names read from the corresponding OA views.
PINS = {
    "INVD1" + SUFFIX: "I ZN VDD VSS",
    "ND2D1" + SUFFIX: "A1 A2 ZN VDD VSS",
    "OR2D1" + SUFFIX: "A1 A2 Z VDD VSS",
    "DFCNQD1" + SUFFIX: "D CP CDN Q VDD VSS",
    **{name + SUFFIX: "I Z VDD VSS" for name in ("DEL075D1", "DEL200D1", "DEL250D1")},
    "rupolym": "PLUS MINUS",
    "cfmom_2t": "PLUS MINUS",
    "nch_mac": "D G S B",
    "pch_mac": "D G S B",
}
# Site widths in the native core12T LEF, 0.14 um per site, height 1.2 um.
WIDTH = {
    "INVD1": 2,
    "ND2D1": 3,
    "OR2D1": 4,
    "DFCNQD1": 18,
    "DEL075D1": 13,
    "DEL200D1": 23,
    "DEL250D1": 25,
    "TAPCELL": 4,
    "BOUNDARY_LEFT": 3,
    "BOUNDARY_RIGHT": 3,
    "DCAP4": 4,
    "DCAP8": 8,
    "DCAP16": 16,
}
GROUP = ("XCTRL", "XSEQ", "XIDLE", "XSAMPLE")
TIM = "XCTRL/XTIM"
# Resistor centre y, direction of bank growth, and MOM units per row.
BANKS = {
    "XIDLE/XD": (16.5, -1, 15),
    "XSEQ/XD": (22.5, 1, 10),
    TIM + "/XD_QUIET_D": (38.75, -1, 15),
    TIM + "/XD_WRITE_D": (47.75, -1, 4),
    TIM + "/XD_RAW_D": (53.75, 1, 1),
}


@dataclass
class Device:
    name: str
    master: str
    pins: dict
    parameters: dict


def released_sources():
    """Electrical inputs of the routed RC macro, with their original logical names."""
    record = json.loads((ROOT / "results/design/sar_timing_quiet8p5_20261118.json").read_text())
    blobs = {}
    for name, digest in record["source_sha256"].items():
        source = "frozen/quiet8p5_20261118/dut.scs" if name == "dut.scs" else name
        data = (ROOT / "design" / source).read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f"Released SAR layout input changed: {source}")
        blobs[name] = data
    return blobs


def active_sources(*, static_latch=False, quiet_stages=None, quiet_final_ps=250, sample_delay_ps=None):
    dut = ROOT / "design/dut.scs"
    entry = dut.read_bytes()
    if static_latch:
        old = b"xtor/sar/reset_data_or_std_delay.scs"
        new = b"xtor/sar/reset_data_or_std_static.scs"
        if entry.count(old) + entry.count(new) != 1:
            raise ValueError("Unexpected active SAR controller")
        entry = entry.replace(old, new)
    overrides = {}
    if quiet_stages is None and (quiet_final_ps != 250 or sample_delay_ps is not None):
        raise ValueError("Select the QUIET stage count for the timing candidate")
    if quiet_stages is not None:
        name, source = source_for_stages((dut.parent / STD_DELAY_REFERENCE).read_bytes(), quiet_stages,
                                         quiet_final_ps, sample_delay_ps=sample_delay_ps)
        entry, count = re.subn(rb'(?m)^include "xtor/clock/delays_std(?:_q[569](?:_del200)?(?:_s(?:075|200))?)?\.scs"',
                               b'include "' + name.encode() + b'"', entry)
        if count != 1:
            raise ValueError("Unexpected standard delay source")
        overrides[name] = source
    includes = re.findall(r'^include "([^"]+)"', entry.decode(), re.MULTILINE)
    return {"dut.scs": entry, **{name: overrides[name] if name in overrides else (dut.parent / name).read_bytes()
                                 for name in includes}}


def electrical(*, standard_delays=False, static_latch=False, quiet_stages=None, quiet_final_ps=250, sample_delay_ps=None):
    manifest = json.loads((ROOT / "design/manifest.json").read_text(encoding="utf-8"))
    dut = ROOT / "design/dut.scs"
    if sample_delay_ps is not None and not standard_delays:
        raise ValueError("The single-cell sample tap requires standard delays")
    blobs = active_sources(static_latch=static_latch, quiet_stages=quiet_stages, quiet_final_ps=quiet_final_ps,
                           sample_delay_ps=sample_delay_ps) if standard_delays else released_sources()
    paths = [
        dut.parent / name for name in re.findall(r'^include "([^"]+)"', blobs["dut.scs"].decode(), re.MULTILINE)
    ]
    subs, files = {}, {}
    for f in paths:
        ds = definitions(blobs[f.relative_to(dut.parent).as_posix()].decode("utf-8"))
        if subs.keys() & ds.keys():
            raise ValueError(f"Duplicate subcircuit in {f}")
        subs.update(ds)
        files.update(dict.fromkeys(ds, f))
    top = manifest["top"] if isinstance(manifest["top"], str) else manifest["top"]["master"]
    parts = instances(subs[top])
    floorplan = json.loads((ROOT / "Layout/design/floorplan.json").read_text(encoding="utf-8"))
    block = next(b for b in floorplan["blocks"] if b["id"] == "sar_timing")
    if set(block["instances"]) != set(GROUP):
        raise ValueError("Review the new floorplan group")
    public = set(subs[top].splitlines()[0].split()[2:])
    for inst, (nets, _, _) in parts.items():
        if inst not in GROUP:
            public.update(nets)
    touched = {dut, files[top]}
    leaves = {}

    def expand(path, master, nets, params=""):
        if master in PINS:
            pins = dict(zip(PINS[master].split(), nets, strict=True))
            pars = dict(re.findall(r"(\w+)\s*=\s*([^\s]+)", params))
            leaves[path] = Device(path, master, pins, pars)
            return
        text = subs[master]
        touched.add(files[master])
        binding = dict(zip(text.splitlines()[0].split()[2:], nets, strict=True))
        for name, (nodes, child, args) in instances(text).items():
            child_nets = [binding.get(n, path.replace("/", "__") + "__" + n) for n in nodes]
            expand(path + "/" + name, child, child_nets, args)

    aliases = {"VDD!": "VDD", "0": "VSS"}
    ports = {}
    for key in GROUP:
        nets, master, _ = parts[key]
        expand(key, master, [aliases.get(n, n) for n in nets])
        for n in nets:
            if n in public:
                ports[aliases.get(n, n)] = None
    hashes = {
        f.relative_to(ROOT).as_posix(): hashlib.sha256(blobs[f.relative_to(dut.parent).as_posix()]).hexdigest() for f in sorted(touched)
    }
    return leaves, list(ports), hashes


class Floorplan:
    def __init__(self, devices):
        self.devices = devices
        self.placed = {}
        self.rows = []
        self.banks = []
        self.seams = []

    def place(self, key, x, y, orient="R0", options=None, copy=None):
        d = self.devices[key]
        name = key.replace("/", "__") + ("" if copy is None else f"__u{copy:02d}")
        if name in self.placed:
            raise ValueError("Duplicate placement " + name)
        self.placed[name] = {
            "source": key,
            "master": d.master,
            "xy": [round(x, 4), round(y, 4)],
            "orient": orient,
            "pins": d.pins,
            "options": options or {},
        }
        return name

    def row(self, name, x, y, groups, *, mx=False, decap=None, mirror_keys=()):
        keys = []
        for prefix in groups:
            selected = [
                k
                for k in self.devices
                if (k == prefix or k.startswith(prefix + "/")) and self.devices[k].master.endswith(SUFFIX)
            ]
            if not selected:
                raise ValueError("Empty standard-cell group " + prefix)
            keys.extend(sorted(selected))
        orient = "MX" if mx else "R0"
        sites = 0

        def support(master, ident=None):
            nonlocal sites
            ident = ident or f"ROW_{name}_{master}_{sites}"
            self.placed[ident] = {
                "source": None,
                "master": master + SUFFIX,
                "xy": [round(x + 0.14 * sites, 4), y],
                "orient": orient,
                "pins": {"VDD": "VDD", "VSS": "VSS"},
                "options": {},
            }
            sites += WIDTH[master]

        support("BOUNDARY_LEFT")
        support("TAPCELL")
        last_tap = sites
        for key in keys:
            if sites - last_tap > 105:
                support("TAPCELL")
                last_tap = sites
            width = WIDTH[self.devices[key].master.removesuffix(SUFFIX)]
            flipped = key in mirror_keys
            self.place(key, x + (sites + (width if flipped else 0)) * 0.14, y,
                       ("R180" if mx else "MY") if flipped else orient)
            sites += width
        if decap:
            support(decap, "DECAP_" + name)
        support("BOUNDARY_RIGHT")
        self.rows.append(
            {
                "name": name,
                "x": x,
                "y": y,
                "orient": orient,
                "width": round(sites * 0.14, 4),
                "keys": keys,
            }
        )

    def delay_banks(self, compact=False):
        for prefix, (y, sign, ncol) in BANKS.items():
            if compact and prefix in ("XIDLE/XD", "XSEQ/XD"):
                ncol = 20
            for stage, (x, side) in enumerate(((18.25, -1), (20.65, 1))):
                r, c = (prefix + f"/{kind}{stage}" for kind in ("R", "C"))
                cp, rp = self.devices[c].parameters, self.devices[r].parameters
                if [cp[k] for k in ("nr", "lr", "w", "s", "stm", "spm")] != [
                    "8",
                    "2.5u",
                    "50n",
                    "50n",
                    "1",
                    "3",
                ]:
                    raise ValueError("Review MOM primitive " + c)
                allowed_lengths = ("17.13u", "8.5u") if prefix == "XCTRL/XTIM/XD_QUIET_D" else ("17.13u",)
                if rp["l"] not in allowed_lengths or [rp[k] for k in ("w", "m", "multi")] != [
                    "1u",
                    "1",
                    "(1)",
                ]:
                    raise ValueError("Review resistor primitive " + r)
                self.place(
                    r,
                    x - side * 0.04,
                    y - 0.5,
                    "MY" if side == -1 else "R0",
                    {"l": rp["l"], "w": rp["w"]},
                )
                count = int(cp["multi"])
                if self.devices[r].pins["MINUS"] != self.devices[c].pins["PLUS"]:
                    raise ValueError("Resistor and capacitor do not share the RC node")
                items = []
                for unit in range(count):
                    row, col = divmod(unit, ncol)
                    near = y + sign * (1.40 + 3.14 * row)
                    # Like electrodes face one another across consecutive row gaps.
                    orient = "MX" if (sign == 1) == (row % 2 == 0) else "R0"
                    low = near if sign == 1 else near - 2.92
                    name = self.place(
                        c,
                        x + side * 0.92 * col - 0.38,
                        low + (2.92 if orient == "MX" else 0),
                        orient,
                        MOM,
                        copy=unit,
                    )
                    items.append(name)
                self.banks.append(
                    {
                        "name": c,
                        "resistor": r.replace("/", "__"),
                        "instances": items,
                        "columns": ncol,
                        "side": side,
                        "x": x,
                        "y": y,
                    }
                )
        c = TIM + "/XCLOCK/CQB"
        if self.devices[c].parameters["multi"] != "1":
            raise ValueError("Review latch storage capacitor")
        self.place(c, 5.28, 51.28, "R90", MOM)

    def clear_row(self, prefixes, y, center=19.45):
        for dev, x in (("MN_CLEAR", round(center - 0.63, 4)), ("MP_CLEAR", round(center + 0.63, 4))):
            pair = len(prefixes) == 2
            placed = []
            for i, prefix in enumerate(prefixes):
                key = prefix + "/" + dev
                d = self.devices[key]
                if d.parameters["nf"] != "1" or d.parameters["multi"] != "1" or d.parameters["l"] != "30n":
                    raise ValueError("Review clear transistor " + key)
                width = "2u" if dev == "MN_CLEAR" else "3u"
                if d.parameters["w"] != width:
                    raise ValueError("Changed diffusion width " + key)
                orient = "MY" if pair and i == 0 else "R0"
                gate = x + (-0.065 if i == 0 else 0.065) if pair else x
                name = self.place(
                    key,
                    gate + (0.015 if orient == "MY" else -0.015),
                    y,
                    orient,
                    {
                        "l": "30n",
                        "Wfg": width,
                        "fingers": "1",
                        "dummyPolyWidth": "30n",
                        "dummyPolyWidth2": "30n",
                        "leftShape": "same" if pair else "normal",
                        "rightShape": "normal",
                    },
                )
                placed.append(name)
            if (
                len(
                    {
                        (
                            self.placed[n]["master"],
                            self.placed[n]["pins"]["S"],
                            self.placed[n]["pins"]["B"],
                        )
                        for n in placed
                    }
                )
                != 1
            ):
                raise ValueError("Source/body mismatch at proposed abutment")
            self.seams.append(
                {
                    "devices": placed,
                    "net": self.placed[name]["pins"]["S"],
                    "x": x,
                    "y": y,
                    "width": float(width[:-1]),
                    "shared": pair,
                }
            )


MOM = {
    "Nfinger": "8",
    "Lfinger": "2.5u",
    "Wfinger": "50n",
    "Sfinger": "50n",
    "StartMn": "1",
    "StopMn": "3",
}


def compact_placement(f):
    # Twenty columns remove one physical MOM row on both sides of each lower
    # delay. Keep their two plates, polarity and multiplicity unchanged.
    def shift(name, dx, dy):
        x, y = f.placed[name]["xy"]
        f.placed[name]["xy"] = [round(x + dx, 4), round(y + dy, 4)]

    lower, upper = -3.14, -6.98
    for bank in f.banks:
        dy = lower if bank["name"].startswith(("XIDLE/", "XSEQ/")) else upper
        for name in [bank["resistor"], *bank["instances"]]:
            shift(name, 0, dy)
        bank["y"] = round(bank["y"] + dy, 4)
    for seam in f.seams:
        dy = lower if seam["devices"][0].startswith("XIDLE__") else upper
        for name in seam["devices"]:
            shift(name, 0, dy)
        seam["y"] = round(seam["y"] + dy, 4)
    shift((TIM + "/XCLOCK/CQB").replace("/", "__"), 0, upper)
    for row in f.rows:
        name = row["name"]
        dx = 0
        dy = lower if name in {"sample", "rc0", "rc1"} else upper
        if name in ("comp_p", "comp_n"):
            # The west end of the WRITE capacitor band holds both first receivers.
            dy += {"comp_p": 43.25, "comp_n": 44.85}[name] - row["y"]
        elif name == "active":
            dx = 7.7
            dy += 56.95 - row["y"]
        elif name in ("msb", "lsb"):
            dy -= 1.45
        names = [k.replace("/", "__") for k in row["keys"]]
        names.extend(k for k in f.placed if k.startswith("ROW_" + name + "_"))
        for key in names:
            shift(key, dx, dy)
        row["x"], row["y"] = round(row["x"] + dx, 4), round(row["y"] + dy, 4)


def placement(devices, compact=False):
    f = Floorplan(devices)
    f.delay_banks(compact)
    f.clear_row(["XIDLE/XD", "XSEQ/XD"], 18.15)
    f.clear_row([TIM + "/XD_QUIET_D"], 40.10)
    f.clear_row([TIM + "/XD_WRITE_D", TIM + "/XD_RAW_D"], 49.05)

    # Separate COMP_P/N receivers on the same x and in the same physical orientation.
    def timing(*names):
        return [TIM + "/" + name for name in names]

    f.row("comp_p", 0.70, 55.3, timing("X002", "X006", "X008", "X009", "X010", "X011"))
    f.row("comp_n", 0.70, 57.5, timing("X003", "X004", "X005", "X000", "X001", "X013", "X014"))
    f.row("clock", 0.70, 49.4, timing("X025/X001", "X025/X000", "XCLOCK", "X023", "X022"))
    f.row("quiet", 0.70, 40.45, timing("X015", "X016", "X017", "X018", "X019", "X020"))
    for row, (prefix, y) in enumerate(
        (
            ("XIDLE/XD", 18.3),
            ("XSEQ/XD", 20.7),
            (TIM + "/XD_QUIET_D", 41.75),
            (TIM + "/XD_WRITE_D", 49.55),
            (TIM + "/XD_RAW_D", 51.95),
        )
    ):
        f.row(f"rc{row}", 14.28, y, [prefix], mx=row in (1, 4))
    f.row(
        "sample",
        2.1,
        19.25,
        ["XSAMPLE", "XIDLE/XA", "XIDLE/XB", "XIDLE/XN", "XIDLE/XP", "XSEQ/XA", "XSEQ/XB"],
    )
    for label, bits, y, mx in (
        ("msb", range(7, 3, -1), 60.0, False),
        ("lsb", range(4), 62.4, True),
    ):
        groups = []
        for b in bits:
            groups += [f"XCTRL/XSEQ/XF{b}", f"XCTRL/XBIT{b}"]
        f.row(label, 0.70, y, groups, mx=mx)
    f.row(
        "active",
        0.70,
        64.05,
        ["XCTRL/XSEQ/X001"]
        + [f"XCTRL/X{n:03}" for n in range(15, 11, -1)]
        + [f"XCTRL/X{n:03}" for n in (17, 16, 18)],
    )
    if compact:
        compact_placement(f)
    actual = Counter(q["source"] for q in f.placed.values() if q["source"])
    expected = Counter(
        {
            n: int(d.parameters.get("multi", "1")) if d.master == "cfmom_2t" else 1
            for n, d in devices.items()
        }
    )
    if expected != actual:
        raise ValueError(
            f"Placement coverage differs: missing={expected - actual}, extra={actual - expected}"
        )
    return f


# Access points in the installed native terminals. The OA writer checks each point against
# the evaluated master's metal before it adds a route or a parent pin.
ACCESS = {
    "INVD1": {"I": (0.07, 0.695), "ZN": (0.21, 0.695)},
    "ND2D1": {"A1": (0.25, 0.425), "A2": (0.09, 0.64), "ZN": (0.37, 0.54)},
    "OR2D1": {"A1": (0.14, 0.60), "A2": (0.28, 0.60), "Z": (0.49, 0.795)},
    "DFCNQD1": {"D": (0.525, 0.55), "CP": (0.11, 0.55), "CDN": (1.235, 0.48), "Q": (2.47, 0.65)},
}


def sk(value):
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, (list, tuple)):
        return "list(" + " ".join(sk(v) for v in value) + ")"
    return f"{value:.4f}"


class Drawing:
    def __init__(self, floor):
        self.floor = floor
        self.lines = []
        self.wires = []
        self.checks = set()
        self.vias = {}
        self.port_locations = {}
        self.routed = set()

    def call(self, fn, *args):
        self.lines.append(fn + "(cv " + " ".join(sk(a) for a in args) + ")")

    def rect(self, layer, net, x0, y0, x1, y1):
        self.call("stRect", layer, net, x0, y0, x1, y1)

    def wire(self, layer, net, x0, y0, x1, y1, w=0.07):
        if abs(x0 - x1) > 0.00001 and abs(y0 - y1) > 0.00001:
            raise ValueError("Non-Manhattan route " + net)
        if abs(x0 - x1) + abs(y0 - y1) < 0.0001:
            return
        rect = [min(x0, x1) - w / 2, min(y0, y1) - w / 2, max(x0, x1) + w / 2, max(y0, y1) + w / 2]
        if layer in (2, 3, 4):
            # Cover the native via enclosure at both ends and meet island area with one rectangle.
            along_x = abs(x0 - x1) > 0.00001
            a, b = (0, 2) if along_x else (1, 3)
            extra = max(0.06 - w / 2, 0)
            rect[a] -= extra
            rect[b] += extra
            minimum = {2: 0.21, 3: 0.25, 4: 0.25}[layer]
            addition = max(minimum - (rect[b] - rect[a]), 0) / 2
            rect[a] -= addition
            rect[b] += addition
        self.rect("M" + str(layer), net, *rect)
        self.wires.append((layer, net, tuple(rect), round(abs(x0 - x1) + abs(y0 - y1), 4)))

    def via(self, lower, x, y, net, horizontal=False):
        key = (lower, round(x, 4), round(y, 4))
        if key in self.vias:
            if self.vias[key] != net:
                raise ValueError("Overlapping via cuts on different nets")
            return
        self.vias[key] = net
        self.call("stVia", lower, net, x, y, int(horizontal))

    def stack(self, x, y, start, stop, net):
        for i in range(start, stop):
            self.via(i, x, y, net)
        for i in range(start + 1, stop):
            if i == 2:
                self.rect("M2", net, x - 0.035, y - 0.105, x + 0.035, y + 0.105)
            else:
                self.rect("M3", net, x - 0.125, y - 0.035, x + 0.125, y + 0.035)

    def access(self, name, terminal):
        dev = self.floor.placed[name]
        cell = dev["master"].removesuffix(SUFFIX)
        dx, dy = ACCESS[cell][terminal]
        xx, yy = dev["xy"]
        y = yy + dy if dev["orient"] == "R0" else yy - dy
        layer = 2 if terminal == "CDN" else 1
        return self.checked(name, terminal, layer, xx + dx, y)

    def checked(self, name, term, layer, x, y):
        key = (name, term, layer, round(x, 4), round(y, 4))
        if key not in self.checks:
            self.call("stCheckPin", *key)
            self.checks.add(key)
        return layer, x, y

    def pin(self, name, layer, x, y, wx=0.04, wy=0.06):
        self.call("stPin", name, layer, x, y, wx, wy)
        self.port_locations[name] = [layer, round(x, 4), round(y, 4)]


def passive_routes(f, g):
    ground_rows = []
    spine_x = 19.45
    for bank in f.banks:
        prefix, c = bank["name"].rsplit("/", 1)
        stage = int(c[-1])
        first = bank["instances"][0]
        net = f.placed[first]["pins"]["PLUS"]
        x, ry = bank["x"], bank["y"]
        positive = []
        for idx in range(0, len(bank["instances"]), bank["columns"]):
            row = bank["instances"][idx : idx + bank["columns"]]
            origin = f.placed[row[0]]["xy"][1]
            orient = f.placed[row[0]]["orient"]
            dy = 1 if orient == "R0" else -1
            py, my = origin + dy * 2.865, origin + dy * 0.055
            positive.append(py)
            for pin, y in (("PLUS", py), ("MINUS", my)):
                bus = net if pin == "PLUS" else "VSS"
                for name in row:
                    cx = f.placed[name]["xy"][0] + 0.38
                    g.checked(name, pin, 3, cx, y)
                # Bridge just the gap between neighbouring native plate terminals.
                for left, right in itertools.pairwise(row):
                    lo, hi = sorted((f.placed[left]["xy"][0], f.placed[right]["xy"][0]))
                    g.rect("M3", bus, lo + 0.745, y - 0.055, hi + 0.015, y + 0.055)
            g.via(3, x, py, net)
            if stage == 0:
                # Both second plates face this common return in every physical row.
                g.rect("M3", "VSS", 18.25 + 0.365, my - 0.055, 20.65 - 0.365, my + 0.055)
                g.via(3, spine_x, my, "VSS")
                ground_rows.append(my)
        g.checked(bank["resistor"], "MINUS", 1, x, ry)
        g.stack(x, ry, 1, 4, net)
        sense = (prefix + ("/X002/XLIB" if stage == 0 else "/X005/XLIB")).replace("/", "__")
        _, sx, sy = g.access(sense, "I")
        if f.placed[sense]["pins"]["I"] != net:
            raise ValueError("Wrong sense inverter for " + net)
        sense_orient = 1 if f.placed[sense]["orient"] == "R0" else -1
        track = f.placed[sense]["xy"][1] + sense_orient * (
            0.295 if stage == 0 else (0.60 if sense_orient == 1 else 0.55)
        )
        g.via(1, sx, sy, net)
        g.wire(2, net, sx, sy, sx, track)
        g.via(2, sx, track, net)
        g.wire(3, net, sx, track, x, track)
        g.via(3, x, track, net)
        clear = (prefix + ("/MN_CLEAR" if stage == 0 else "/MP_CLEAR")).replace("/", "__")
        q = f.placed[clear]
        if q["pins"]["D"] != net:
            raise ValueError("Wrong clear drain for " + net)
        dx, dy = q["xy"]
        dx += 0.080 if q["orient"] == "R0" else -0.080
        seam = next(s for s in f.seams if clear in s["devices"])
        dy += 0.445 if seam["devices"].index(clear) == 0 else 1.675
        g.checked(clear, "D", 1, dx, dy)
        g.stack(dx, dy, 1, 3, net)
        g.wire(3, net, dx, dy, x, dy)
        g.via(3, x, dy, net)
        ys = positive + [track, dy, ry]
        g.wire(4, net, x, min(ys), x, max(ys), 0.10)
        g.routed.add(net)
    for seam in f.seams:
        x, y, w = seam["x"], seam["y"], seam["width"]
        is_n = seam["net"] == "VSS"
        contact = x if seam["shared"] else x - 0.065
        tap = x + (-0.61 if is_n else 0.61)
        g.call("stBody", seam["net"], contact, tap, y, w, int(seam["shared"]))
        # Attach the source and the correctly implanted body contact on M2.
        cy = y + 0.945
        g.via(1, contact, cy, seam["net"], horizontal=True)
        g.via(1, tap, cy, seam["net"], horizontal=True)
        g.wire(2, seam["net"], contact, cy, tap, cy, 0.08)
        if is_n:
            g.via(2, contact, cy, "VSS", horizontal=True)
            g.wire(3, "VSS", contact, cy, spine_x, cy)
            g.via(3, spine_x, cy, "VSS")
            ground_rows.append(cy)
    g.wire(4, "VSS", spine_x, min(ground_rows), spine_x, max(ground_rows), 0.12)


def port_routes(f, g, ports, compact=False):
    labels = {
        "COMP_P": ("XCTRL/XTIM/X002/X000/XLIB", "I"),
        "COMP_N": ("XCTRL/XTIM/X003/X000/XLIB", "I"),
        "CMP_CLK": ("XCTRL/XTIM/X025/X001/XLIB", "ZN"),
    }
    for net, (source, term) in labels.items():
        name = source.replace("/", "__")
        x, y = f.placed[name]["xy"]
        x += 0.21 if net == "CMP_CLK" else 0.07
        y += 0.86 if net == "CMP_CLK" else 0.695
        g.checked(name, term, 1, x, y)
        g.via(1, x, y, net, horizontal=True)
        g.wire(2, net, 0.28, y, x, y, 0.07)
        g.pin(net, 2, 0.28, y, 0.07, 0.07)
    for net in ports:
        if net in labels:
            continue
        if compact:
            if net in ("VSS", "VDD"):
                x = 1.26 if net == "VSS" else 2.38
                g.rect("M6", net, x - 0.14, 14.4, x + 0.14, 53.6)
                g.pin(net, 6, x, 53.46, 0.28, 0.28)
            elif re.fullmatch("CODE[0-7]|D[0-7]", net):
                x = 0.32 if net.startswith("CODE") else 38.36
                g.pin(net, 3, x, 46.0 + 0.8 * int(net[-1]), 0.30, 0.08)
            else:
                x, y = {
                    "PHI_U": (0.32, 34.2),
                    "SAMPLE": (38.36, 16.8),
                    "SAMPLE_INT": (0.32, 16.8),
                    "PRESET": (0.32, 18.0),
                    "SEQ_SAMPLE": (0.32, 17.4),
                }[net]
                g.pin(net, 3, x, y, 0.30, 0.08)
            continue
        if net in ("VSS", "VDD"):
            name = "ROW_msb_TAPCELL_3"
            x, y = f.placed[name]["xy"]
            g.checked(name, net, 1, x + 0.28, y + (1.2 if net == "VDD" else 0))
            g.pin(net, 1, x + 0.28, y + (1.2 if net == "VDD" else 0), 0.08, 0.08)
            continue
        driver = []
        for name, q in f.placed.items():
            if not q["master"].endswith(SUFFIX) or q["source"] is None:
                continue
            for terminal, n in q["pins"].items():
                if n == net and (
                    terminal in ("ZN", "Z", "Q") or net == "SAMPLE" and name.startswith("XSAMPLE__")
                ):
                    driver.append((name, terminal))
        if len(driver) != 1:
            raise ValueError(f"Expected one source/contact for {net}: {driver}")
        layer, x, y = g.access(*driver[0])
        g.pin(net, layer, x, y)


def wire_clear(g, net, layer, box):
    return all(
        layer != l
        or net == other
        or box[2] + 0.07 < r[0]
        or r[2] + 0.07 < box[0]
        or box[3] + 0.07 < r[1]
        or r[3] + 0.07 < box[1]
        for l, other, r, _ in g.wires
    )


def local_track_clear(g, net, lo, hi, access, y):
    wire_box = (lo - 0.055, y - 0.04, hi + 0.055, y + 0.04)
    meets_cut_spacing = all(
        not (abs(x - vx) < 0.13 - 1e-6 and abs(y - vy) < 0.13 - 1e-6)
        for x, py in access
        for (lev, vx, vy) in g.vias
        if lev == 2
    )
    return (
        meets_cut_spacing
        and wire_clear(g, net, 3, wire_box)
        and all(
            wire_clear(g, net, 2, (x - 0.04, min(y, py) - 0.05, x + 0.04, max(y, py) + 0.05))
            for x, py in access
        )
    )


def logic_routes(f, g):
    # Route short row-local nets on M2/M3. Multirow trunks use the next placement review.
    ends = {}
    row_by_key = {k: r for r in f.rows for k in r["keys"]}
    for name, q in f.placed.items():
        for pin, n in q["pins"].items():
            ends.setdefault(n, []).append((name, pin))
    for row in f.rows:
        candidates = []
        for net, pins in ends.items():
            if net in ("VSS", "VDD") or len(pins) < 2:
                continue
            stdpins = []
            storage = net == TIM.replace("/", "__") + "__XCLOCK__QB"
            for name, term in pins:
                q = f.placed[name]
                if storage and q["master"] == "cfmom_2t":
                    continue
                if row_by_key.get(q["source"]) is not row:
                    break
                # The flip-flop contains M2 routing. Preserve its local obstructions for detailed P&R.
                if q["master"].startswith("DFCN"):
                    break
                stdpins.append((name, term))
            else:
                if not stdpins:
                    continue
                access = [g.access(name, term)[1:] for name, term in stdpins]
                # A NAND followed by an abutting inverter can use a single M2 elbow.
                # Use the NAND's other output landing to leave room between the two cuts.
                if len(stdpins) == 2:
                    found = {term: i for i, (_, term) in enumerate(stdpins)}
                    if "ZN" in found and "I" in found:
                        j, k = found["I"], found["ZN"]
                        nand = f.placed[stdpins[k][0]]
                        if nand["master"].startswith("ND2") and 0 < access[j][0] - access[k][0] < 0.15:
                            x0 = nand["xy"][0] + 0.21
                            y0 = nand["xy"][1] + (0.80 if nand["orient"] == "R0" else -0.80)
                            x1, y1 = access[j]
                            sign = 1 if y1 > y0 else -1
                            boxes = [
                                (x0 - 0.06, y0 - 0.035, x1 + 0.035, y0 + 0.035),
                                (
                                    x1 - 0.035,
                                    min(y0 - sign * 0.035, y1 + sign * 0.06),
                                    x1 + 0.035,
                                    max(y0 - sign * 0.035, y1 + sign * 0.06),
                                ),
                            ]
                            if all(
                                all(
                                    l != 2
                                    or n == net
                                    or r[2] + 0.055 < b[0]
                                    or b[2] + 0.055 < r[0]
                                    or r[3] + 0.055 < b[1]
                                    or b[3] + 0.055 < r[1]
                                    for l, n, r, _ in g.wires
                                )
                                for b in boxes
                            ):
                                g.checked(stdpins[k][0], "ZN", 1, x0, y0)
                                g.via(1, x0, y0, net, horizontal=True)
                                g.via(1, x1, y1, net)
                                for box in boxes:
                                    g.rect("M2", net, *box)
                                    g.wires.append((2, net, box, 0))
                                g.routed.add(net)
                                continue
                            access[k] = (x0, y0)
                            g.checked(stdpins[k][0], "ZN", 1, x0, y0)
                if storage:
                    bx, by = f.placed[(TIM + "/XCLOCK/CQB").replace("/", "__")]["xy"]
                    access.append((round(bx - 2.865, 4), round(by + 0.38, 4)))
                candidates.append(
                    (max(x for x, y in access) - min(x for x, y in access), net, access, storage)
                )
        for span, net, pts, storage in sorted(candidates, key=lambda a: (not a[3], a[0], a[1])):
            lo = min(x for x, y in pts)
            hi = max(x for x, y in pts)
            if hi - lo < 0.001:
                continue

            # An adjacent inverter pair can often be joined directly on a single track.
            if not storage and len(pts) == 2 and span < 0.75 and abs(pts[0][1] - pts[1][1]) < 0.0001:
                y = pts[0][1]
                if wire_clear(g, net, 2, (lo - 0.055, y - 0.04, hi + 0.055, y + 0.04)):
                    for x, py in pts:
                        g.via(1, x, py, net, horizontal=True)
                    g.wire(2, net, lo, y, hi, y, 0.07)
                    g.routed.add(net)
                    continue
            sign = 1 if row["orient"] == "R0" else -1
            tracks = [row["y"] + sign * (0.14 + 0.17 * i) for i in range(7)]
            tracks = sorted(tracks, key=lambda y, points=pts: sum(abs(y - py) for _, py in points))
            row_pins = pts[:-1] if storage else pts
            y = next((v for v in tracks if local_track_clear(g, net, lo, hi, row_pins, v)), None)
            if y is None:
                continue
            for x, py in pts[:-1] if storage else pts:
                g.via(1, x, py, net)
                if abs(y - py) < 0.0001:
                    g.rect("M2", net, x - 0.035, y - 0.105, x + 0.035, y + 0.105)
                else:
                    g.wire(2, net, x, py, x, y)
                g.via(2, x, y, net)
            if storage:
                x, py = pts[-1]
                g.checked((TIM + "/XCLOCK/CQB").replace("/", "__"), "PLUS", 3, x, py)
                g.via(3, x, py, net)
                g.wire(4, net, x, py, x, y)
                g.via(3, x, y, net)
            g.wire(3, net, lo, y, hi, y, 0.07)
            g.routed.add(net)


def generate(compact=False, destination=None):
    devices, ports, hashes = electrical()
    f = placement(devices, compact)
    g = Drawing(f)
    passive_routes(f, g)
    for seam in f.seams:
        for i, name in enumerate(seam["devices"]):
            q = f.placed[name]
            x, y = q["xy"]
            sign = -1 if i == 0 else 1
            gx = x + (0.015 if q["orient"] == "R0" else -0.015)
            g.call(
                "stGate",
                q["pins"]["G"],
                gx,
                y + (seam["width"] if sign > 0 else 0),
                sign,
                "NP" if seam["net"] == "VSS" else "PP",
            )
    port_routes(f, g, ports, compact)
    logic_routes(f, g)
    for bank in f.banks:
        resistor = f.placed[bank["resistor"]]
        length_um = float(resistor["options"]["l"][:-1])
        if length_um < 17.13:
            # Preserve the routed driver landing in the area vacated by the shorter strip.
            # The sensitive MINUS pad stays at its original position.
            direction = -1 if resistor["orient"] == "MY" else 1
            y = bank["y"]
            original_x = bank["x"] + direction * (17.13 + 0.28)
            pad_x = bank["x"] + direction * (length_um + 0.28)
            driver = resistor["pins"]["PLUS"]
            g.rect(
                "M1",
                driver,
                min(pad_x, original_x) - 0.025,
                y - 0.035,
                max(pad_x, original_x) + 0.025,
                y + 0.035,
            )
            g.rect("M1", driver, original_x - 0.025, y - 0.49, original_x + 0.025, y + 0.49)
    out = destination or (ROOT / "work/layout/sar-closure" if compact else OUT)
    write_design(f, g, hashes, ports, out)


def write_design(f, g, hashes, ports, out, routing_outline=None, mom_route_clearance=None):
    nets = sorted({n for q in f.placed.values() for n in q["pins"].values()})
    # The public cell is published by copying a verified, saved staging cell.
    # Generation only replaces a scratch view. The usual target library is never opened for write here.
    lines = [
        'load("sar_timing.il")',
        "procedure(stBuild() let((cv lib)",
        'lib=ddGetObj("SAR_PLACEMENT_WORK")',
        'stNeed(lib && techGetTechFile(lib)~>libName=="tsmcN28" "Staging library must use the T28 technology")',
        f'cv=dbOpenCellViewByType("SAR_PLACEMENT_WORK" "{CORE}" "layout" "maskLayout" "w")',
        'stNeed(cv "Could not open private staging view")',
        'dbReplaceProp(cv "generatorOwner" "string" "Layout/design/sar_timing.py")',
    ]
    lines += ["dbMakeNet(cv " + sk(n) + ")" for n in nets]
    for name, q in f.placed.items():
        options = [[k, "string", v] for k, v in q["options"].items()]
        args = [
            name,
            STD if q["master"].endswith(SUFFIX) else "tsmcN28",
            q["master"],
            *q["xy"],
            q["orient"],
            options,
            list(q["pins"].items()),
        ]
        lines.append("stDevice(cv " + " ".join(sk(a) for a in args) + ")")
    lines += g.lines + [
        'stNeed(dbSave(cv) "Failed to save staged geometry")',
        "dbClose(cv)",
        f'stAudit("SAR_PLACEMENT_WORK" "{CORE}")',
        'printf("SAR_BUILD_OK\\n") t))',
        "if(errset(stBuild() t) then exit(0) else exit(1))",
    ]
    out.mkdir(parents=True, exist_ok=True)
    (out / "build.il").write_text("\n".join(lines) + "\n", encoding="ascii")
    (out / "sar_timing.il").write_bytes((ROOT / "Layout/design/sar_timing.il").read_bytes())
    data = {
        "cell": CORE,
        "inputs": hashes,
        "instances": f.placed,
        "rows": f.rows,
        "banks": f.banks,
        "clear_rows": f.seams,
        "ports": g.port_locations,
        "access_checks": sorted(g.checks),
        "nets": nets,
        "routed_signal_candidates": sorted(g.routed),
    }
    if routing_outline:
        data["routing_outline_um"] = routing_outline
    if mom_route_clearance:
        data["mom_route_clearance_um"] = mom_route_clearance
    (out / "intent.json").write_text(json.dumps(data, indent=2) + "\n")
    print(
        f"{len(f.placed)} placed instances, {len(ports)} core ports and {len(g.routed)} signal nets selected for physical continuity checking"
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--initial", action="store_true", help="Use the initial floorplan with the current circuit"
    )
    args = parser.parse_args()
    generate(compact=not args.initial)
