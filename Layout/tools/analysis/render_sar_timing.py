"""Draw the saved SAR placement and two routed details from its OA readback and GDS."""

import argparse
import json
from pathlib import Path

import matplotlib
from klayout import db

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection, PolyCollection
from matplotlib.patches import Patch, Rectangle

from Layout.design.sar_timing import CORE, SUFFIX, WIDTH
from Layout.tools.analysis.check_sar_timing import readback


def detail(ax, layout, top, extent, layers):
    scale = layout.dbu
    x0, y0, x1, y1 = extent
    window = db.Region(db.Box(*(round(q / scale) for q in extent)))
    for number, color in layers:
        idx = layout.find_layer(number, 0)
        if idx is None:
            continue
        region = db.Region(top.begin_shapes_rec(idx)) & window
        shapes = [
            [(p.x * scale, p.y * scale) for p in poly.each_point_hull()] for poly in region.each()
        ]
        ax.add_collection(PolyCollection(shapes, facecolors=color, edgecolors="none"))
    ax.set(xlim=(x0, x1), ylim=(y0, y1), aspect="equal")


def render(intent_file, folder, dest):
    intent = json.loads(intent_file.read_text())
    (_lib, _, _), inst, _, _, ports = readback(folder / "sar-readback.txt")
    layout = db.Layout()
    layout.read(str(folder / "fixture.gds"))
    top = layout.cell(CORE)
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans"],
            "axes.spines.top": False,
            "axes.spines.right": False,
            "font.size": 10,
            "axes.unicode_minus": False,
            "axes.labelcolor": "#3b484f",
            "axes.edgecolor": "#85939a",
        }
    )
    fig = plt.figure(figsize=(11.4, 8.25), layout="constrained", facecolor="white")
    grid = fig.add_gridspec(2, 2, width_ratios=(1, 1.08))
    overview = fig.add_subplot(grid[:, 0])
    comp = fig.add_subplot(grid[0, 1])
    source = fig.add_subplot(grid[1, 1])
    colors = {
        "MOM": "#6ca3b2",
        "R": "#c79450",
        "logic": "#465b78",
        "tap": "#a9b3bb",
        "clear": "#9d6470",
    }
    groups = {k: [] for k in colors}
    for name, (_, m, o, (x, y), box) in inst.items():
        if m.endswith(SUFFIX):
            cell = m.removesuffix(SUFFIX)
            key = "logic" if intent["instances"][name]["source"] else "tap"
            w, h = WIDTH[cell] * 0.14, 1.2
            if o == "MX":
                y -= h
        else:
            key = "MOM" if m == "cfmom_2t" else "R" if m == "rupolym" else "clear"
            x, y, x1, y1 = box
            w = x1 - x
            h = y1 - y
        groups[key].append(Rectangle((x, y), w, h))
    for key, rects in groups.items():
        overview.add_collection(
            PatchCollection(rects, facecolor=colors[key], edgecolor="white", linewidth=0.20)
        )
    overview.add_patch(
        Rectangle((0, 0), 40, 70, fill=False, edgecolor="#687d86", linewidth=1, linestyle="--")
    )
    for y, title in (
        (66.4, "Bit slices / ACTIVE"),
        (57.5, "VALID"),
        (46.5, "WRITE"),
        (35.5, "QUIET"),
        (29, "Sample edge"),
        (12, "Idle guard"),
    ):
        overview.annotate(
            title, xy=(39.95, y), xytext=(5, 0), textcoords="offset points", va="center", fontsize=9
        )
    for n in ("COMP_N", "COMP_P", "CMP_CLK"):
        _, (x0, y0, x1, y1) = ports[n]
        overview.plot((x0 + x1) / 2, (y0 + y1) / 2, "o", ms=3, color="#af4232")
    overview.set(
        xlim=(-1.4, 54), ylim=(-1, 71), aspect="equal", xlabel="Local x (µm)", ylabel="Local y (µm)"
    )
    overview.set_title(
        "Placement within the 40 × 70 µm reservation", loc="left", fontsize=12, pad=8
    )
    overview.legend(
        handles=[
            Patch(color=colors[k], label=t)
            for k, t in (
                ("logic", "Logic"),
                ("tap", "Tap / row ends"),
                ("R", "Resistor"),
                ("MOM", "MOM"),
                ("clear", "Clear FET"),
            )
        ],
        loc="lower left",
        bbox_to_anchor=(0.73, 0.015),
        ncol=1,
        frameon=False,
        fontsize=9,
    )
    # Only local device contacts and the implemented metal on these two cut-outs.
    detail(
        comp,
        layout,
        top,
        (0.18, 55.12, 4.10, 58.85),
        [
            (6, "#d1e3d9"),
            (17, "#d2b89a"),
            (31, "#64849b"),
            (32, "#cb5543"),
            (33, "#6d538f"),
            (51, "#283e49"),
            (52, "#302637"),
        ],
    )
    comp.set_title("Comparator inputs at the west edge · M2", loc="left", fontsize=12)
    for net in ("COMP_N", "COMP_P"):
        _, (x0, y0, x1, y1) = ports[net]
        comp.annotate(
            net,
            xy=((x0 + x1) / 2, (y0 + y1) / 2),
            xytext=(4, 5),
            textcoords="offset points",
            fontsize=8,
            color="#663121",
        )
    detail(
        source,
        layout,
        top,
        (17.95, 48.60, 20.98, 52.46),
        [
            (3, "#e5eade"),
            (6, "#79a891"),
            (17, "#c18755"),
            (31, "#80a6bb"),
            (32, "#cc6754"),
            (33, "#967dae"),
            (34, "#cbb66c"),
            (30, "#334955"),
            (51, "#334955"),
        ],
    )
    source.set_title("VALID / WRITE clear devices · shared sources", loc="left", fontsize=12)
    for x, y, tag in ((18.82, 50.55, "VSS"), (20.08, 51.15, "VDD")):
        source.annotate(
            tag,
            xy=(x, y),
            xytext=(0, 22),
            textcoords="offset points",
            ha="center",
            fontsize=9,
            arrowprops={"arrowstyle": "-", "color": "#253947", "lw": 0.8},
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8, "pad": 1},
        )
    for ax in (comp, source):
        ax.set_xlabel("Local x (µm)")
        ax.set_ylabel("Local y (µm)")
        ax.tick_params(labelsize=8)
    fig.suptitle(
        "SAR and asynchronous timing   |   Initial placement and local routing",
        fontsize=16,
        fontweight="normal",
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(dest, dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    for k in ("intent", "checkpoint", "output"):
        ap.add_argument(k, type=Path)
    args = ap.parse_args()
    render(args.intent, args.checkpoint, args.output)
