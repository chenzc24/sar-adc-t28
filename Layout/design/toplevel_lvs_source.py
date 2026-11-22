"""LVS source netlist of the ADC core sar8_adc_core (Stage 5), from the plan in Layout/results/toplevel_route_full.md.

The top subcircuit follows sar_adc8_join_r4 (design/top/adc_top.scs) on the physical block grouping. The layout keeps
each block master as an HCELL, and each master is described by the reference netlist it passed block LVS with:
- the SAR macro sar8_se_core holds XCTRL, XSEQ, XDONE, XPRESET and XSAMPLE (sar-se-r3-lib);
- the pair sar8_cdac_with_xref holds XCDAC and XREF (se-xref-full-b). The physical XREF has no D0-D7, PHI_U, SAMPLE_INT
  or RST_DONE ports, so PHI_U and SAMPLE_INT stay internal to the SAR macro side;
- the comparator sar_strongarm_t28_core (comp-v8-20261120-pex) and the Bootstrap sar_bootstrap_flat_8b_p_core
  (boot-core-20261121), whose supplies are explicit ports in the layout.
Left out: the three not-drawn model loads CL_COMP_P, CL_COMP_N and CL_CMP_CLK (Layout/specs/interfaces.json).
Added: the reference wrapper (constraints.json stage6_supply_model.on_chip_reference): VREFP and VREFN join ahead of
RREFP/RREFN (rupolym), which feed VREFP_TRUNK/VREFN_TRUNK; CREF (nmoscap) between the trunks; and the supply
decoupling (nmoscap, gate on VDD!). Device counts and sizes come from the build's content summary. The N-well
diodes of the nmoscaps are not listed: the installed deck filters pnwdio in the layout (LVS FILTER D(pnwdio) LAYOUT
OPEN), as in the block LVS runs. Ports: the boundary pins plus the internal nets the layout labels on pin layers
(the deck makes every pin-layer text a port).
"""
import argparse
import hashlib
import json
import re

from Layout.design.toplevel_route import WORK
from Layout.project import ROOT

TOP = "sar8_adc_core"
REFERENCES = ("sar-se-r3-lib", "se-xref-full-b", "comp-v8-20261120-pex", "boot-core-20261121")
BOUNDARY = [f"D{k}" for k in range(8)] + ["SAMPLE", "VINN", "VINP", "VREFP", "VREFN", "VDD!", "0"]
LABELLED = (["TOPN", "TOPP", "COMP_P", "COMP_N", "CMP_CLK", "SEQ_SAMPLE"] + [f"CODE{k}" for k in range(8)]
            + ["PRESET", "VREFP_TRUNK", "VREFN_TRUNK"])
CODE = {f"CODE{k}": f"CODE{k}" for k in range(8)}
BLOCKS = [   # instance, master, port -> net (sar_adc8_join_r4 nets)
    ("XSAR", "sar8_se_core", {**{f"D{k}": f"D{k}" for k in range(8)}, **CODE, "PHI_U": "PHI_U", "PRESET": "PRESET",
                              "SAMPLE_INT": "SAMPLE_INT", "SEQ_SAMPLE": "SEQ_SAMPLE", "SAMPLE": "SAMPLE",
                              "COMP_N": "COMP_N", "COMP_P": "COMP_P", "CMP_CLK": "CMP_CLK", "VDD": "VDD!", "VSS": "0"}),
    ("XCDAC", "sar8_cdac_with_xref", {**CODE, "PRESET": "PRESET", "VSS": "0", "VDD": "VDD!", "TOPN": "TOPN",
                                      "TOPP": "TOPP", "VREFN": "VREFN_TRUNK", "VREFP": "VREFP_TRUNK"}),
    ("XCOMP", "sar_strongarm_t28_core", {"CLK": "CMP_CLK", "OUTN": "COMP_N", "OUTP": "COMP_P", "VDD": "VDD!",
                                         "VINN": "TOPN", "VINP": "TOPP", "VSS": "0"}),
    ("XBOOTN", "sar_bootstrap_flat_8b_p_core", {"CLKS": "SEQ_SAMPLE", "VOUT": "TOPN", "VIN": "VINN", "VDD": "VDD!",
                                                "VSS": "0"}),
    ("XBOOTP", "sar_bootstrap_flat_8b_p_core", {"CLKS": "SEQ_SAMPLE", "VOUT": "TOPP", "VIN": "VINP", "VDD": "VDD!",
                                                "VSS": "0"}),
]
DECAP_GROUPS = ("DA_west", "DA_slot", "DA_east", "DC_W", "DC_E", "DP_S", "DP_E", "DP_SE", "DP_C", "DS_S", "DS_N")
CREF_GROUPS = ("DR_W", "DR_C", "DR_SE")
UNIT = {"DC_W": (2.0, 0.8), "DC_E": (2.0, 0.8)}      # comparator strips; every other array is wr 2.5 / lr 0.8


def subckts(text):
    return {m.group(1): m.group(0).strip() for m in re.finditer(r"(?ims)^\.subckt\s+(\S+)(.*?)^\.ends[^\n]*", text)}


def ports(body):
    head = re.match(r"(?is)\.subckt\s+\S+\s+(.*?)\n(?!\+)", body + "\n").group(1)
    return head.replace("\n+", " ").split()


def build(summary, references=REFERENCES):
    lib, sources = {}, {}
    for ev in references:
        path = WORK / ev / "reference.cdl"
        blob = path.read_bytes()
        sources[ev] = hashlib.sha256(blob).hexdigest()
        for name, body in subckts(blob.decode("latin1")).items():
            if name in lib and lib[name] != body:
                raise ValueError(f"{name} differs between block references")
            lib.setdefault(name, body)
    lines = [f"* LVS source of {TOP}: Layout/design/toplevel_lvs_source.py",
             "* Block references (evidence: sha256): " + ", ".join(f"{k}: {v[:12]}" for k, v in sources.items()), ""]
    lines += [lib[n] + "\n" for n in lib]
    lines.append(f".SUBCKT {TOP} " + " ".join(BOUNDARY + LABELLED))
    for inst, master, conn in BLOCKS:
        order = ports(lib[master])
        missing = set(order) - set(conn)
        if missing or set(conn) - set(order):
            raise ValueError(f"{inst}: port map disagrees with {master}: {sorted(missing)} / {sorted(set(conn) - set(order))}")
        lines.append(f"{inst} " + " ".join(conn[p] for p in order) + f" {master}")
    counts = {}
    for pad, trunk, rows in (("VREFP", "VREFP_TRUNK", ("RREFP_A", "RREFP_B")), ("VREFN", "VREFN_TRUNK", ("RREFN_A", "RREFN_B"))):
        n = sum(summary[r]["segments"] for r in rows)
        w, l = summary[rows[0]]["w_um"], summary[rows[0]]["l_um"]
        lines += [f"XR{pad}_{k} {pad} {trunk} rupolym w={w}u l={l}u" for k in range(n)]
        counts["R" + pad[1:]] = n
    k = 0
    for g in CREF_GROUPS:
        for _ in range(summary.get(g, {}).get("devices", 0)):
            lines.append(f"XCREF_{k} VREFP_TRUNK VREFN_TRUNK nmoscap wr=2.5u lr=0.8u")
            k += 1
    counts["CREF"] = k
    k = 0
    for g in DECAP_GROUPS:
        wr, lr = UNIT.get(g, (2.5, 0.8))
        for _ in range(summary[g]["devices"]):
            lines.append(f"XDEC_{k} VDD! 0 nmoscap wr={wr}u lr={lr}u")
            k += 1
    counts["decap"] = k
    lines += [f".ENDS {TOP}", ""]
    return "\n".join(lines), dict(references=sources, blocks=[b[:2] for b in BLOCKS], devices=counts,
                                  ports=BOUNDARY + LABELLED, left_out=["CL_COMP_P", "CL_COMP_N", "CL_CMP_CLK"])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--content", required=True, help="content.json of the layout_route_full build (array summary)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--bootstrap-reference", default=REFERENCES[-1],
                    help="evidence ID whose reference.cdl describes the Bootstrap master (default: the frozen core)")
    args = ap.parse_args()
    refs = REFERENCES[:-1] + (args.bootstrap_reference,)
    text, info = build(json.loads((ROOT / args.content).read_bytes())["summary"], refs)
    (ROOT / args.out).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / args.out).write_text(text, encoding="ascii")
    info["sha256"] = hashlib.sha256(text.encode("ascii")).hexdigest()
    print(json.dumps(info, indent=1))


if __name__ == "__main__":
    main()
