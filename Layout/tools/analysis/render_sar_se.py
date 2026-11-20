"""Draw the single-edge SAR macro from its routed DEF: cell groups, signal metal and supplies.

Only the project's own placement and routing are drawn; standard-cell interiors are not.
"""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch, Rectangle  # noqa: E402

from Layout.project import ROOT  # noqa: E402
from Layout.tools.physical.sar_se_def import convert  # noqa: E402

GROUPS = [  # (label, colour, predicate on instance name)
    ("Delay window: DEL250 chain and tap MUXes", "#c96f2d", lambda n: n.startswith("XCTRL__XTIM__XWINDOW")),
    ("Timing: phase counter, comparator clock, first compare", "#d9a441", lambda n: n.startswith("XCTRL__XTIM")),
    ("Next-word logic", "#3f7cac", lambda n: n.startswith("XCTRL__XWORD")),
    ("Bit and DONE registers", "#5b9b6b", lambda n: n.startswith(("XCTRL__XBIT", "XCTRL__XDONE"))),
    ("Sticky tap selects", "#8a63a8", lambda n: n.startswith("XCTRL__XSEL")),
    ("Other SAR control", "#7d8fa3", lambda n: n.startswith("XCTRL")),
    ("Acquire and top gates", "#b04a5a", lambda n: n.startswith(("XSEQ", "XDONE", "XPRESET", "XSAMPLE"))),
]
PHYSICAL = "#e2e2e2"
METAL = {"M2": ("#2f6db5", 0.55), "M3": ("#2b9a6a", 0.55), "M4": ("#b8572b", 0.55)}


def group(name):
    for label, colour, test in GROUPS:
        if test(name):
            return label, colour
    return None, PHYSICAL


def render(revision, out):
    route = ROOT / "work/layout/sar-se" / revision
    d, u, shapes, pins, power, instances, physical, design = convert(route, route / "cells.json")
    w, h = d["die"][2] / u, d["die"][3] / u
    fig, ax = plt.subplots(figsize=(9.5, 9.5 * h / w + 1.4), dpi=200)
    ax.add_patch(Rectangle((0, 0), w, h, fill=False, lw=1.0, ec="#333333"))
    sizes = {}
    for line in (ROOT / "work/layout/lef/tcbn28hpcplusbwp12t30p140.lef").read_text(errors="replace").split("\nMACRO ")[1:]:
        name = line.split()[0]
        if "SIZE" in line:
            parts = line.split("SIZE", 1)[1].split()
            sizes[name] = (float(parts[0]), float(parts[2]))
    for i in instances:
        cw, ch = sizes[i["master"]]
        x, y = i["origin"]
        x0 = x - cw if i["orient"] in ("MY", "R180") else x
        y0 = y - ch if i["orient"] in ("MX", "R180") else y
        _, colour = group(i["name"])
        ax.add_patch(Rectangle((x0, y0), cw, ch, fc=colour, ec="white", lw=0.25, alpha=0.9 if colour != PHYSICAL else 0.6))
    for net, rects in shapes.items():
        if net in ("VDD", "VSS"):
            continue
        for lay, (a, b, c, e) in rects:
            if lay in METAL:
                colour, alpha = METAL[lay]
                ax.add_patch(Rectangle((a / u, b / u), (c - a) / u, (e - b) / u, fc=colour, ec="none", alpha=alpha))
    for net, colour in (("VDD", "#c0392b"), ("VSS", "#34495e")):
        for lay, (a, b, c, e) in shapes[net]:
            if lay == "M6":
                ax.add_patch(Rectangle((a / u, b / u), (c - a) / u, (e - b) / u, fc=colour, ec="none", alpha=0.35))
    for name, (lay, (a, b, c, e)) in pins.items():
        ax.text(-0.15, (b + e) / 2 / u, name, ha="right", va="center", fontsize=4.2)
    ax.set_xlim(-2.2, w + 0.3)
    ax.set_ylim(-0.3, h + 0.3)
    ax.set_aspect("equal")
    ax.set_xlabel("x (µm)")
    ax.set_ylabel("y (µm)")
    logic = len(design["cells"])
    ax.set_title(f"sar8_se_core, {w:.2f} × {h:.2f} µm: {logic} logic cells, {len(instances) - logic} physical cells", fontsize=9)
    handles = [Patch(fc=c, label=label) for label, c, _ in GROUPS]
    handles += [Patch(fc=PHYSICAL, label="Boundary, tap, decap and fill cells")]
    handles += [Patch(fc=c, alpha=a, label=lay + " signal") for lay, (c, a) in METAL.items()]
    handles += [Patch(fc="#c0392b", alpha=.35, label="M6 VDD"), Patch(fc="#34495e", alpha=.35, label="M6 VSS")]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=2, fontsize=6, frameon=False)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    print(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("revision")
    ap.add_argument("--out", type=Path, default=ROOT / "Layout/results/figures/sar_se_core.png")
    a = ap.parse_args()
    render(a.revision, a.out)
