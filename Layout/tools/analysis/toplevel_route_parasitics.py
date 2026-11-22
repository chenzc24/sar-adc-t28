"""Parasitics of the core-internal routes from two flat xRC extractions with the same deck.

`placement` extracts the placement view with every planned landing pin labelled NET__BLOCK; `routed` extracts
the routed view (net labels on the routes, VSS_SHIELD on the floating shield). The capacitance a route adds
to net N is C(N) in the routed run minus C of its pieces in the placement run, where C sums grounded and
coupling capacitance and coupling between two pieces of N is removed because it becomes internal.

Resistance and delay use each routed net's extracted RC network between real device terminals: drivers
are the drain/source terminals in the driving block, receivers the gate terminals in the receiving block
(TOP: the Bootstrap switch terminals and the CDAC capacitor terminals). Elmore delays treat coupling
capacitance as grounded and add an assumed gate load per receiver terminal; for RC trees the Elmore
delay bounds the 50% step delay from above. Both include the blocks' own pin-side wiring, so they bound
the route-only values from above.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import re

import numpy as np

from Layout.project import ROOT
from Layout.tools.analysis.toplevel_route_connectivity import PLANNED

INSTANCE = re.compile(r"^(\S+)\s*\(\s*(.*?)\s*\)\s+(\S+)(.*)$")
SCALE = {"a": 1e-18, "f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "k": 1e3}
GATE_LOAD_F = 1e-15
PLAN = json.loads((ROOT / "Layout/design/floorplan.json").read_bytes())
BLOCKS = {b["id"]: (b["origin"][0], b["origin"][1], b["origin"][0] + b["size"][0], b["origin"][1] + b["size"][1])
          for b in PLAN["blocks"]}
DELAY_PATHS = {  # net: (driver block, receiver blocks)
    "COMP_P": ("comparator", ["sar"]), "COMP_N": ("comparator", ["sar"]), "CMP_CLK": ("sar", ["comparator"]),
    "SEQ_SAMPLE": ("sar", ["bootstrap_n", "bootstrap_p"]),
    **{n: ("sar", ["reference"]) for n in [f"CODE{i}" for i in range(8)] + ["PRESET"]},
}


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def statements(path):
    parts = []
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n").rstrip()
        if line.endswith("\\"):
            parts.append(line[:-1])
            continue
        parts.append(line)
        yield " ".join(parts).strip()
        parts = []


def value(text, key):
    v = re.search(r"\b" + key + r"=(\S+)", text).group(1)
    return float(v[:-1]) * SCALE[v[-1]] if v[-1] in SCALE else float(v)


def unescape(name):
    return name.replace("\\", "")


def block_of(x, y):
    for b, (x0, y0, x1, y1) in BLOCKS.items():
        if x0 - 0.05 <= x <= x1 + 0.05 and y0 - 0.05 <= y <= y1 + 0.05:
            return b
    return None


class Extraction:
    def __init__(self, base, top="sar8_adc_core"):
        pxi = f"extracted.scs.{top}.pxi"
        self.files = {n: sha(f"{base}/{n}") for n in ("extracted.scs", "extracted.scs.pex", pxi)}
        self.networks = {}
        net = None
        for line in statements(f"{base}/extracted.scs.pex"):
            if line.startswith("subckt "):
                m = re.match(r"subckt\s+(\S+)\s*\((.*?)\)$", line)
                net = unescape(m.group(1)).split("%", 1)[1]
                self.networks[net] = dict(name=m.group(1), formals=m.group(2).split(), caps=[], res=[])
            elif line.startswith("ends"):
                net = None
            elif net:
                m = INSTANCE.match(line)
                if not m:
                    continue
                a, b = m.group(2).split()
                kind = "caps" if m.group(3) == "capacitor" else "res"
                self.networks[net][kind].append((a, b, value(m.group(4), "c" if kind == "caps" else "r")))
        by_name = {v["name"]: k for k, v in self.networks.items()}
        self.node_net = {"0": "0"}
        self.node_local = {}  # actual node -> (net, local node)
        coupling = []
        for path in (f"{base}/{pxi}", f"{base}/extracted.scs"):
            for line in statements(path):
                m = INSTANCE.match(line)
                if not m:
                    continue
                if m.group(3) in by_name:
                    net = by_name[m.group(3)]
                    nodes = m.group(2).split()
                    for formal, actual in zip(self.networks[net]["formals"], nodes):
                        if formal == "0":
                            continue
                        self.node_net[actual] = net
                        self.node_local[actual] = (net, formal)
                elif m.group(3) == "capacitor":
                    a, b = m.group(2).split()
                    coupling.append((a, b, value(m.group(4), "c")))
        self.coupling = coupling
        self.devices = []
        for line in statements(f"{base}/extracted.scs"):
            m = INSTANCE.match(line)
            if not m or m.group(3) in by_name or m.group(3) == "capacitor":
                continue
            xy = re.search(r"//x=(\S+) //y=(\S+)", line)
            if xy:
                self.devices.append((m.group(1), m.group(2).split(), m.group(3),
                                     block_of(float(xy.group(1)), float(xy.group(2)))))

    def net(self, node):
        return self.node_net.get(node, unescape(node))

    def capacitance(self):
        """Per net: grounded and coupling capacitance (F) by partner net."""
        c = defaultdict(lambda: defaultdict(float))
        for net, nw in self.networks.items():
            for a, b, v in nw["caps"]:
                if "0" in (a, b):
                    c[net]["0"] += v
        for a, b, v in self.coupling:
            na, nb = self.net(a), self.net(b)
            if na == nb:
                continue
            c[na][nb] += v
            c[nb][na] += v
        return c

    def terminals(self, net):
        """Device terminal nodes of a net: (local node, block, terminal letter, model)."""
        out = []
        for name, nodes, model, block in self.devices:
            for node in nodes:
                hit = self.node_local.get(node)
                if hit and hit[0] == net:
                    letter = node.rsplit("_", 1)[-1]
                    out.append((hit[1], block, letter, model))
        return out


def laplacian(net, nw, extra_c=None):
    nodes = sorted({n for a, b, _ in nw["res"] for n in (a, b)} | {n for a, b, _ in nw["caps"] for n in (a, b)} - {"0"}
                   | {f for f in nw["formals"] if f != "0"})
    index = {n: i for i, n in enumerate(nodes)}
    g = np.zeros((len(nodes), len(nodes)))
    for a, b, r in nw["res"]:
        if "0" in (a, b):
            raise ValueError(f"Resistor to ground in {net}")
        i, j = index[a], index[b]
        y = 1.0 / max(r, 1e-6)
        g[i, i] += y
        g[j, j] += y
        g[i, j] -= y
        g[j, i] -= y
    cap = np.zeros(len(nodes))
    for a, b, v in nw["caps"]:
        cap[index[b if a == "0" else a]] += v
    for node, v in (extra_c or {}).items():
        cap[index[node]] += v
    return nodes, index, g, cap


def merged_solve(g, keep, source, rhs):
    """Voltages with the source node set grounded (Dirichlet), solving the reduced system."""
    others = [i for i in range(len(g)) if i not in source]
    v = np.zeros(len(g))
    v[others] = np.linalg.solve(g[np.ix_(others, others)], rhs[others])
    return v


def rc_metrics(ex, net):
    nw = ex.networks[net]
    coupling_at = defaultdict(float)
    for a, b, v in ex.coupling:
        for x in (a, b):
            hit = ex.node_local.get(x)
            if hit and hit[0] == net and ex.net(a) != ex.net(b):
                coupling_at[hit[1]] += v
    terms = ex.terminals(net)
    result = dict(resistors=len(nw["res"]), total_wire_resistance_ohm=round(sum(r for _, _, r in nw["res"]), 2))
    if net in DELAY_PATHS:
        driver, receivers = DELAY_PATHS[net]
        src = sorted({n for n, b, t, _ in terms if b == driver and t in ("d", "s")})
        loads = {b: sorted({n for n, bb, t, _ in terms if bb == b and t == "g"}) for b in receivers}
        if not src or not all(loads.values()):
            raise ValueError(f"Missing driver or receiver terminals on {net}: {len(src)} {[len(v) for v in loads.values()]}")
        extra = dict(coupling_at)
        for b, ns in loads.items():
            for n in ns:
                extra[n] = extra.get(n, 0.0) + GATE_LOAD_F
        nodes, index, g, cap = laplacian(net, nw, extra)
        s = [index[n] for n in src]
        t = merged_solve(g, None, s, cap)
        r_one = {}
        for b, ns in loads.items():
            rhs = np.zeros(len(nodes))
            for n in ns:
                rhs[index[n]] = 1.0 / len(ns)
            v = merged_solve(g, None, s, rhs)
            r_one[b] = float(max(v[index[n]] for n in ns))
        result.update(driver_block=driver, driver_terminals=len(src),
                      receiver_gate_terminals={b: len(ns) for b, ns in loads.items()},
                      elmore_delay_ps={b: round(max(t[index[n]] for n in ns) * 1e12, 3) for b, ns in loads.items()},
                      driver_to_receiver_resistance_ohm={b: round(v, 2) for b, v in r_one.items()},
                      network_capacitance_fF=round(float(cap.sum()) * 1e15, 3),
                      assumed_gate_load_fF_per_receiver_terminal=GATE_LOAD_F * 1e15)
    if net in ("TOPN", "TOPP"):
        boot = "bootstrap_n" if net == "TOPN" else "bootstrap_p"
        sw = sorted({n for n, b, t, _ in terms if b == boot and t in ("d", "s")})
        plate = sorted({n for n, b, _, _ in terms if b == "cdac"})
        nodes, index, g, cap = laplacian(net, nw)
        s = [index[n] for n in plate]
        rhs = np.zeros(len(nodes))
        for n in sw:
            rhs[index[n]] = 1.0 / len(sw)
        v = merged_solve(g, None, s, rhs)
        result.update(sampler_switch_terminals=len(sw), cdac_capacitor_terminals=len(plate),
                      switch_to_cdac_plate_resistance_ohm=round(float(np.mean([v[index[n]] for n in sw])), 2),
                      switch_to_cdac_plate_resistance_max_ohm=round(float(max(v[index[n]] for n in sw)), 2))
    return result


def analyze(placement, routed):
    base, route = Extraction(placement), Extraction(routed)
    cb, cr = base.capacitance(), route.capacitance()
    routed_nets = sorted(PLANNED)
    pieces = {n: sorted(k for k in cb if k.startswith(n + "__")) for n in routed_nets}
    owner = {p: n for n, ps in pieces.items() for p in ps}
    report = dict(inputs=dict(placement=base.files, routed=route.files), nets={})
    for n in routed_nets:
        ps = pieces[n]
        if len(ps) != len(PLANNED[n]):
            raise ValueError(f"{n}: expected {len(PLANNED[n])} labelled pieces, found {ps}")
        total_base = sum(sum(cb[p].values()) for p in ps) - sum(cb[p][q] for p in ps for q in ps if p != q)
        total_route = sum(cr[n].values())
        partners = defaultdict(float)
        for m, v in cr[n].items():
            partners["ground" if m == "0" else m if m in routed_nets or m == "VSS_SHIELD" else "block_nets"] += v
        for p in ps:
            for m, v in cb[p].items():
                if m in ps:
                    continue
                key = "ground" if m == "0" else owner.get(m, "block_nets")
                partners[key] -= v
        report["nets"][n] = dict(
            placement_pieces_fF={p: round(sum(cb[p].values()) * 1e15, 3) for p in ps},
            routed_total_fF=round(total_route * 1e15, 3), added_fF=round((total_route - total_base) * 1e15, 3),
            added_by_partner_fF={k: round(v * 1e15, 4) for k, v in sorted(partners.items()) if abs(v) > 5e-19},
            **rc_metrics(route, n))
    shield = cr.get("VSS_SHIELD", {})
    report["VSS_SHIELD"] = dict(total_fF=round(sum(shield.values()) * 1e15, 3),
                                by_partner_fF={k: round(v * 1e15, 4) for k, v in sorted(shield.items()) if v > 5e-19},
                                device_terminals=len(route.terminals("VSS_SHIELD")) if "VSS_SHIELD" in route.networks else 0)
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("placement", help="pex/ directory of the placement extraction with NET__BLOCK labels")
    ap.add_argument("routed", help="pex/ directory of the routed extraction")
    ap.add_argument("--out")
    args = ap.parse_args()
    report = analyze(args.placement, args.routed)
    text = json.dumps(report, indent=1)
    if args.out:
        (ROOT / args.out).write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
