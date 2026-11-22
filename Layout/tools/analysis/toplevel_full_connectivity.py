"""Connectivity of layout_route_full (Stage 4b) from Calibre's hierarchical layout netlist.

The netlist is extracted from a copy of the view's stream whose supply pin texts are renamed per branch
(VDD_A/VSS_A north, VDD_P/VSS_P south, VDD_D/VSS_D east; toplevel_full.py branch-labels), with every block
master kept as an HCELL. Checks: the Stage 4a nets reach exactly their planned ports; every boundary signal
reaches exactly its block port and is a top-level port; every supply branch reaches exactly its blocks'
supply ports and no other branch; VREFP/VREFN are top ports that reach no block and VREFP_TRUNK/VREFN_TRUNK
reach exactly the pair ports of their rail; every nmoscap and rupolym device, flattened to top-level nets in
its model's port order, is a decap of one branch (gate on VDD), CREF (gate on VREFP_TRUNK) or an RREF segment
between a pad net and its trunk, with the counts of the drawn arrays and banks.
"""
import argparse
from collections import Counter, defaultdict
import json
import re

from Layout.project import ROOT
from Layout.tools.analysis.toplevel_route_connectivity import PLANNED, cards, netlist, reach

BOUNDARY = {**{f"D{k}": {("sar", f"D{k}")} for k in range(8)}, "SAMPLE": {("sar", "SAMPLE")},
            "VINN": {("bootstrap_n", "VIN")}, "VINP": {("bootstrap_p", "VIN")}}
SUPPLY = {
    "VDD_A": {("comparator", "VDD"), ("bootstrap_n", "VDD"), ("bootstrap_p", "VDD")},
    "VSS_A": {("comparator", "VSS"), ("bootstrap_n", "VSS"), ("bootstrap_p", "VSS")},
    "VDD_P": {("cdac", "VDD"), ("reference", "VDD")},
    "VSS_P": {("cdac", "VSS"), ("reference", "VSS")},
    "VDD_D": {("sar", "VDD")},
    "VSS_D": {("sar", "VSS")},
}
# The SAR guard ring (layout_route_guard) has its own VSS pin, labelled G: its metal reaches no block port.
GUARD = {"VSS_G": set()}
ARRAYS = {"A": ("DA_west", "DA_slot", "DA_east", "DC_W", "DC_E"), "P": ("DP_S", "DP_E", "DP_SE", "DP_C"),
          "D": ("DS_S", "DS_N")}
# Reference network (phase 2): pad nets are top ports that reach no block; the trunks reach the pair ports that
# carry VREFP/VREFN in the placement netlist; RREF banks sit between pad and trunk, CREF between the trunks.
PAD = {"VREFP": "VREFP_TRUNK", "VREFN": "VREFN_TRUNK"}
RREF_ROWS = {"VREFP": ("RREFP_A", "RREFP_B"), "VREFN": ("RREFN_A", "RREFN_B")}
CREF_ARRAYS = ("DR_W", "DR_C", "DR_SE")


def flat_devices(path, hcells, models=("nmoscap", "rupolym"), top="sar8_adc_core"):
    """Every device of the given models below the top cell (block HCELLs excluded), with its terminals mapped to
    top-level nets in the model's port order."""
    subckts, body, current = {}, defaultdict(list), None
    for line in cards(path):
        tok = line.split()
        if tok[0].upper() == ".SUBCKT":
            current = tok[1]
            subckts[current] = tok[2:]
        elif tok[0].upper() == ".ENDS":
            current = None
        elif current:
            body[current].append(tok)
    out = []

    def walk(cell, nets):
        for tok in body.get(cell, []):
            if not tok[0].upper().startswith("X"):
                continue
            params = [i for i, t in enumerate(tok) if "=" in t]
            end = params[0] if params else len(tok)
            master, pins = tok[end - 1], [nets.get(p, p) for p in tok[1:end - 1]]
            if master in models:
                out.append((master, dict(zip(subckts.get(master, ["PLUS", "MINUS"]), pins)),
                            {t.split("=")[0]: t.split("=")[1] for t in tok[end:] if "=" in t and not t.startswith("$")}))
            elif master in subckts and master not in hcells:
                walk(master, dict(zip(subckts[master], pins)))

    walk(top, {p: p for p in subckts[top]})
    return out


def check(routed, baseline, hcells, summary, console=None, guard=False):
    ports, top = netlist(routed, hcells)
    nets = reach(top)
    # Numbered block ports are the blocks' bulk taps: the common P-substrate. Calibre soft-connects it to one
    # VSS net through the P+ taps; report which net carries it instead of counting it as a metal connection.
    substrate = {n: sorted(p for p in s if p[1].isdigit()) for n, s in nets.items() if any(p[1].isdigit() for p in s)}
    nets = {n: {p for p in s if not p[1].isdigit()} for n, s in nets.items()}
    result = dict(top_ports=sorted(ports), substrate_ports_on=dict((n, len(v)) for n, v in substrate.items()))
    ok = len(substrate) == 1
    supply = {**SUPPLY, **(GUARD if guard else {})}
    for name, want in [*PLANNED.items(), *BOUNDARY.items(), *supply.items()]:
        got = nets.get(name, set())
        exact = got == want
        result.setdefault("nets", {})[name] = dict(reaches=sorted(map(list, got)), planned=sorted(map(list, want)),
                                                   exact=exact)
        ok &= exact
    for name in [*BOUNDARY, *supply, *PAD]:
        if name not in ports:
            result.setdefault("not_a_top_port", []).append(name)
            ok = False
    # Reference nets: the pad nets reach no block; each trunk reaches the pair ports of its rail in the placement.
    base_nets = reach(netlist(baseline, hcells)[1])
    for pad, trunk in PAD.items():
        want = set().union(*[s for s in base_nets.values() if any(p == pad for _, p in s)])
        for name, w in ((pad, set()), (trunk, want)):
            got = nets.get(name, set())
            result.setdefault("nets", {})[name] = dict(reaches=sorted(map(list, got)), planned=sorted(map(list, w)),
                                                       exact=got == w)
            ok &= got == w
        ok &= bool(want)
    # Devices, flattened to top-level nets in model port order: decaps gate (PLUS) on their branch's VDD and N-well
    # (MINUS) on its VSS; CREF gate on VREFP_TRUNK, N-well on VREFN_TRUNK; each RREF bank between pad and trunk.
    tally = Counter((m, t.get("PLUS"), t.get("MINUS")) for m, t, _ in flat_devices(routed, hcells))
    per_branch = {b: tally.pop(("nmoscap", "VDD_" + b, "VSS_" + b), 0) for b in ARRAYS}
    expected = {b: sum(summary[a]["devices"] for a in names if a in summary) for b, names in ARRAYS.items()}
    cref = tally.pop(("nmoscap", "VREFP_TRUNK", "VREFN_TRUNK"), 0)
    # A resistor's PLUS/MINUS naming is the extractor's choice; count either orientation.
    rref = {pad: tally.pop(("rupolym", pad, trunk), 0) + tally.pop(("rupolym", trunk, pad), 0)
            for pad, trunk in PAD.items()}
    stray = [dict(model=m, plus=p, minus=n, devices=k) for (m, p, n), k in tally.items()]
    result["decap_devices"] = dict(per_branch=per_branch, expected=expected, stray=stray[:20], stray_count=len(stray))
    want_cref = sum(summary[a]["devices"] for a in CREF_ARRAYS if a in summary)
    want_rref = {pad: sum(summary[r]["segments"] for r in rows if r in summary) for pad, rows in RREF_ROWS.items()}
    result["reference_devices"] = dict(cref_nmoscap=dict(found=cref, expected=want_cref),
                                       rref_rupolym_segments=dict(found=rref, expected=want_rref))
    ok &= per_branch == expected and not stray and cref == want_cref and rref == want_rref
    if console:
        shorts = [l.strip() for l in open(console, encoding="utf-8", errors="replace")
                  if re.search(r"(?i)short circuit|different names", l) and "RESOLVING SHORT CIRCUIT TEXT" not in l]
        result["text_short_messages"] = shorts[:20]
        ok &= not shorts
    result["verdict"] = "PASS" if ok else "FAIL"
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("routed")
    ap.add_argument("baseline")
    ap.add_argument("--hcells", nargs="+", required=True)
    ap.add_argument("--content", required=True, help="content.json of the build (array summary)")
    ap.add_argument("--console")
    ap.add_argument("--guard", action="store_true", help="the view has the SAR guard ring's own VSS pin")
    ap.add_argument("--out")
    args = ap.parse_args()
    summary = json.loads(open(args.content, encoding="utf-8").read())["summary"]
    result = check(args.routed, args.baseline, set(args.hcells), summary, args.console, args.guard)
    text = json.dumps(result, indent=1)
    if args.out:
        (ROOT / args.out).write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
