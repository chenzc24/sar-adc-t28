"""Connectivity of the core-internal routes from Calibre's hierarchical layout netlist.

The netlist comes from toplevel_physical.py --stages spice with every block master kept as an HCELL, so
each top-level net lists the block ports it reaches. Each routed net must reach exactly its planned
(block, port) set; every other top-level net may reach at most one block, except the common substrate
net, which must join the same blocks as in the placement view's netlist. The extraction log must
report no text shorts.
"""
import argparse
import json
import re

from Layout.project import ROOT

PLANNED = {
    "TOPN": {("cdac", "TOPN"), ("comparator", "VINN"), ("bootstrap_n", "VOUT")},
    "TOPP": {("cdac", "TOPP"), ("comparator", "VINP"), ("bootstrap_p", "VOUT")},
    "COMP_P": {("comparator", "OUTP"), ("sar", "COMP_P")},
    "COMP_N": {("comparator", "OUTN"), ("sar", "COMP_N")},
    "CMP_CLK": {("comparator", "CLK"), ("sar", "CMP_CLK")},
    "SEQ_SAMPLE": {("sar", "SEQ_SAMPLE"), ("bootstrap_n", "CLKS"), ("bootstrap_p", "CLKS")},
    **{n: {("reference", n), ("sar", n)} for n in [f"CODE{i}" for i in range(8)] + ["PRESET"]},
}
CELLS = {"sar8_se_core": "sar", "sar_strongarm_t28_core": "comparator", "sar8i_refword": "reference"}
BOOTSTRAP = "sar_bootstrap_flat_8b_p_core"
# Bootstrap placements by x of the Calibre transform (0.1 nm database units).
BOOTSTRAP_X = {"311750": "bootstrap_n", "610550": "bootstrap_p"}
TEXT_SHORT = re.compile(r"(?i)short circuit|different names|text short")


def cards(path):
    lines = []
    for raw in open(path, encoding="utf-8", errors="replace"):
        raw = raw.rstrip("\n")
        if raw.startswith("+") and lines:
            lines[-1] += " " + raw[1:].strip()
        elif raw.strip() and not raw.startswith("*"):
            lines.append(raw.strip())
    return lines


def netlist(path, hcells):
    subckts, body, current = {}, {}, None
    for line in cards(path):
        tok = line.split()
        if tok[0].upper() == ".SUBCKT":
            current = tok[1]
            subckts[current] = tok[2:]
            body[current] = []
        elif tok[0].upper() == ".ENDS":
            current = None
        elif current:
            body[current].append(tok)
    top = []
    for tok in body["sar8_adc_core"]:
        if not tok[0].upper().startswith("X"):
            continue
        params = [i for i, t in enumerate(tok) if "=" in t]
        end = params[0] if params else len(tok)
        cell = tok[end - 1]
        nets = tok[1:end - 1]
        transform = next((t.split("=")[1] for t in tok if t.startswith("$T=")), None)
        if cell not in hcells:
            cell, nets = wrapped(cell, nets, subckts, body, hcells)
        if cell not in hcells:
            continue
        if cell == BOOTSTRAP:
            block = BOOTSTRAP_X[transform]
        else:
            block = CELLS.get(cell, "cdac")
        ports = subckts[cell]
        if len(ports) != len(nets):
            raise ValueError(f"Port count of {cell} differs from its instance")
        top.append((block, cell, list(zip(ports, nets))))
    return subckts["sar8_adc_core"], top


def wrapped(cell, nets, subckts, body, hcells):
    """A wrapper whose only instance is a block master at its origin (a block placed with its own fill cell, such as
    the filled Bootstrap) stands for that block: return the block and its pins mapped to the wrapper's nets."""
    inner = [t for t in body.get(cell, []) if t[0].upper().startswith("X")]
    if len(inner) != 1:
        return cell, nets
    tok = inner[0]
    params = [i for i, t in enumerate(tok) if "=" in t]
    end = params[0] if params else len(tok)
    k = next((i for i, t in enumerate(tok) if t.startswith("$T=")), None)
    if tok[end - 1] not in hcells or k is None or tok[k] != "$T=0" or tok[k + 1:k + 4] != ["0", "0", "0"]:
        return cell, nets
    outer = dict(zip(subckts[cell], nets))
    return tok[end - 1], [outer.get(p, p) for p in tok[1:end - 1]]


def reach(top):
    nets = {}
    for block, _, pairs in top:
        for port, net in pairs:
            nets.setdefault(net, set()).add((block, port))
    return nets


def check(routed, baseline, hcells, console=None):
    ports, top = netlist(routed, hcells)
    _, base_top = netlist(baseline, hcells)
    blocks = sorted(b for b, _, _ in top)
    if blocks != sorted(["cdac", "reference", "comparator", "bootstrap_n", "bootstrap_p", "sar"]):
        raise ValueError(f"Unexpected block instances {blocks}")
    nets = reach(top)
    result = dict(routed_nets={}, top_ports=sorted(ports))
    ok = sorted(ports) == sorted(PLANNED)
    for net, want in PLANNED.items():
        got = nets.get(net, set())
        result["routed_nets"][net] = dict(reaches=sorted(map(list, got)), planned=sorted(map(list, want)),
                                          exact=got == want)
        ok &= got == want
    def joins(table):
        # Nets that already join blocks without top-level routing: the substrate and the XREF/CDAC pair's own
        # M6 connections. Numbered ports (Calibre's names for unlabeled ports) are compared by block only.
        return sorted(sorted((b, "#" if p.isdigit() else p) for b, p in s)
                      for n, s in table.items() if n not in PLANNED and len({b for b, _ in s}) > 1)
    other, base_other = joins(nets), joins(reach(base_top))
    result["multi_block_unrouted_nets"] = dict(
        routed=len(other), placement=len(base_other), same_as_placement=other == base_other,
        by_blocks={"+".join(sorted({b for b, _ in s})): sum(1 for t in other if {b for b, _ in t} == {b for b, _ in s})
                   for s in other})
    ok &= other == base_other
    if console:
        shorts = [line.strip() for line in open(console, encoding="utf-8", errors="replace")
                  if TEXT_SHORT.search(line) and "RESOLVING SHORT CIRCUIT TEXT" not in line
                  and "ISOLATE SHORTS" not in line]
        result["text_short_messages"] = shorts
        ok &= not shorts
    result["verdict"] = "PASS" if ok else "FAIL"
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("routed", help="layout.sp of the routed view")
    ap.add_argument("baseline", help="layout.sp of the placement view")
    ap.add_argument("--hcells", nargs="+", required=True)
    ap.add_argument("--console", help="spice.console of the routed extraction")
    ap.add_argument("--out")
    args = ap.parse_args()
    result = check(args.routed, args.baseline, set(args.hcells), args.console)
    text = json.dumps(result, indent=1)
    if args.out:
        (ROOT / args.out).write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
