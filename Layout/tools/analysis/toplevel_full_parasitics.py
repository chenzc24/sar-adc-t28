"""Parasitics of layout_route_full (Stage 4b phase 1) from a flat xRC extraction of its branch-labelled stream.

- The adopted route budgets of Stage 4a re-checked in the new environment (toplevel_route_parasitics).
- VINN/VINP: total capacitance by partner and the mirror difference.
- Feed resistance per supply branch: effective resistance from the boundary pin's port node to the branch's
  decoupling (all nmoscap terminals of that net shorted) and to the blocks' supply device terminals, for VDD
  and VSS; the loop value is their sum. The solve uses a Jacobi-preconditioned conjugate gradient on the
  extracted resistor network.
"""
import argparse
import json

import numpy as np

from Layout.project import ROOT
from Layout.tools.analysis.toplevel_route_parasitics import Extraction, analyze

BRANCHES = {"A": ("analog", ["comparator", "bootstrap_n", "bootstrap_p"]), "P": ("pair", ["cdac", "reference"]),
            "D": ("sar", ["sar"])}


def network(ex, net):
    nw = ex.networks[net]
    nodes = sorted({n for a, b, _ in nw["res"] for n in (a, b)} | {f for f in nw["formals"] if f != "0"})
    index = {n: i for i, n in enumerate(nodes)}
    a = np.array([index[x] for x, _, _ in nw["res"]])
    b = np.array([index[y] for _, y, _ in nw["res"]])
    g = np.array([1.0 / max(r, 1e-6) for _, _, r in nw["res"]])
    return nodes, index, a, b, g


def effective_r(nodes, a, b, g, source, sinks, tol=1e-10, iters=20000):
    """R between one source node and a set of sink nodes held at 0 V (1 A injected at the source)."""
    n = len(nodes)
    fixed = np.zeros(n, bool)
    fixed[list(sinks)] = True
    diag = np.zeros(n)
    np.add.at(diag, a, g)
    np.add.at(diag, b, g)

    def matvec(v):
        v = np.where(fixed, 0.0, v)
        out = diag * v
        np.add.at(out, a, -g * v[b])
        np.add.at(out, b, -g * v[a])
        return np.where(fixed, 0.0, out)

    rhs = np.zeros(n)
    rhs[source] = 1.0
    x = np.zeros(n)
    r = rhs - matvec(x)
    pinv = np.where(fixed | (diag == 0), 0.0, 1.0 / np.where(diag == 0, 1.0, diag))
    z = pinv * r
    p = z.copy()
    rz = r @ z
    for _ in range(iters):
        ap = matvec(p)
        alpha = rz / (p @ ap)
        x += alpha * p
        r -= alpha * ap
        if np.linalg.norm(r) < tol:
            break
        z = pinv * r
        rz_new = r @ z
        p = z + (rz_new / rz) * p
        rz = rz_new
    return float(x[source])


def port_node(ex, net):
    """Local node of the top-level port of net (the pxi maps the port name itself to a formal)."""
    for actual, (n, formal) in ex.node_local.items():
        if n == net and actual == net:
            return formal
    raise ValueError("No port node for " + net)


def feeds(ex):
    out = {}
    terms = {}
    for name, nodes_, model, block in ex.devices:
        for node in nodes_:
            hit = ex.node_local.get(node)
            if hit:
                terms.setdefault(hit[0], []).append((hit[1], block, model))
    for key, (label, blocks) in BRANCHES.items():
        row = {}
        for rail in ("VDD", "VSS"):
            net = f"{rail}_{key}"
            if net not in ex.networks:
                row[rail] = None
                continue
            nodes, index, a, b, g = network(ex, net)
            src = index[port_node(ex, net)]
            dec = {index[n] for n, blk, model in terms.get(net, []) if model == "nmoscap"}
            blk = {index[n] for n, bb, model in terms.get(net, []) if bb in blocks and model != "nmoscap"}
            row[rail] = dict(nodes=len(nodes), resistors=len(a), decap_terminals=len(dec), block_terminals=len(blk),
                             to_decap_ohm=round(effective_r(nodes, a, b, g, src, dec), 3) if dec else None,
                             to_blocks_ohm=round(effective_r(nodes, a, b, g, src, blk), 3) if blk else None)
        loop = lambda k: round(row["VDD"][k] + row["VSS"][k], 3) if row["VDD"] and row["VSS"] and \
            row["VDD"][k] is not None and row["VSS"][k] is not None else None
        row["loop_to_decap_ohm"], row["loop_to_blocks_ohm"] = loop("to_decap_ohm"), loop("to_blocks_ohm")
        out[label] = row
    return out


def set_r(nodes, a, b, g, sources, sinks):
    """R between two node sets (each set tied by 1 MS links to a virtual node)."""
    n = len(nodes)
    src = sorted(sources)
    a2 = np.concatenate([a, np.full(len(src), n)])
    b2 = np.concatenate([b, np.array(src, dtype=int)])
    g2 = np.concatenate([g, np.full(len(src), 1e6)])
    return effective_r(nodes + ["#src"], a2, b2, g2, n, sinks)


def reference(ex):
    """Reference network: pad pin to its RREF bank (VREFP/VREFN nets); from the trunk's rail-end node to the RREF
    trunk terminals, to CREF and to the CDAC pair's switch terminals (the pair's own rail distribution), and RREF to
    CREF (VREFP_TRUNK/VREFN_TRUNK nets). Every set of device terminals is shorted; PEX books each device's contact
    and gate/M1 access outside the device, so these values include it."""
    terms = {}
    for name, nodes_, model, block in ex.devices:
        for node in nodes_:
            hit = ex.node_local.get(node)
            if hit:
                terms.setdefault(hit[0], []).append((hit[1], block, model))
    out = {}
    for pad, trunk in (("VREFP", "VREFP_TRUNK"), ("VREFN", "VREFN_TRUNK")):
        row = {}
        nodes, index, a, b, g = network(ex, pad)
        rr = {index[n] for n, _, m in terms.get(pad, []) if m == "rupolym"}
        row["rref_pad_terminals"] = len(rr)
        row["pad_pin_to_rref_ohm"] = round(effective_r(nodes, a, b, g, index[port_node(ex, pad)], rr), 4)
        nodes, index, a, b, g = network(ex, trunk)
        rt = {index[n] for n, _, m in terms.get(trunk, []) if m == "rupolym"}
        cref = {index[n] for n, _, m in terms.get(trunk, []) if m == "nmoscap"}
        sw = {index[n] for n, _, m in terms.get(trunk, []) if m not in ("rupolym", "nmoscap") and "dio" not in m}
        # The trunk label sits on the in-line M5 at the pair's rail end: the node where the trunk meets the rail.
        end = index[port_node(ex, trunk)]
        row.update(rref_trunk_terminals=len(rt), cref_terminals=len(cref), switch_terminals=len(sw),
                   rail_end_to_rref_ohm=round(effective_r(nodes, a, b, g, end, rt), 4),
                   rail_end_to_cref_ohm=round(effective_r(nodes, a, b, g, end, cref), 4),
                   rail_end_to_switches_ohm=round(effective_r(nodes, a, b, g, end, sw), 4),
                   rref_to_cref_ohm=round(set_r(nodes, a, b, g, rt, cref), 4))
        out[pad] = row
    return out


def vin(ex):
    c = ex.capacitance()
    res = {}
    for net in ("VINN", "VINP"):
        parts = {k: round(v * 1e15, 4) for k, v in sorted(c.get(net, {}).items(), key=lambda kv: -kv[1]) if v > 1e-19}
        res[net] = dict(total_fF=round(sum(c.get(net, {}).values()) * 1e15, 4), top_partners_fF=dict(list(parts.items())[:8]))
    res["mirror_difference_fF"] = round(res["VINN"]["total_fF"] - res["VINP"]["total_fF"], 4)
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("placement", help="pex/ directory of the placement extraction with NET__BLOCK labels")
    ap.add_argument("full", help="pex/ directory of the branch-labelled layout_route_full extraction")
    ap.add_argument("--out")
    args = ap.parse_args()
    ex = Extraction(args.full)
    report = dict(route_budget_nets=analyze(args.placement, args.full)["nets"], vin=vin(ex), feeds=feeds(ex))
    text = json.dumps(report, indent=1)
    if args.out:
        (ROOT / args.out).write_text(text + "\n", encoding="utf-8")
    print(text[:3000])


if __name__ == "__main__":
    main()
