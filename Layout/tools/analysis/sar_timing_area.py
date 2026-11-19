"""Measure native SAR footprints and compare two placements on the same axes."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from klayout import db
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Patch, Rectangle

from Layout.design.sar_timing import CORE, SUFFIX, WIDTH
from Layout.project import ROOT
from Layout.tools.analysis.check_sar_timing import readback


COLORS = {
    "Logic": "#425e81",
    "Delay cells": "#4d9790",
    "Taps / ends": "#aebbc4",
    "MOM": "#4b9399",
    "Resistors": "#c68c40",
    "Clear switches": "#9f626b",
    "Decaps": "#74629f",
}


def category(name):
    if name.endswith(SUFFIX):
        if name.startswith("DEL"):
            return "Delay cells"
        if name.startswith("DCAP"):
            return "Decaps"
        return "Taps / ends" if name.startswith(("BOUNDARY", "TAPCELL")) else "Logic"
    return {
        "cfmom_2t": "MOM",
        "rupolym": "Resistors",
        "nch_mac": "Clear switches",
        "pch_mac": "Clear switches",
    }.get(name)


def measure(folder, reservation):
    manifest = json.loads((folder / "sar-physical.json").read_text())
    gds = folder / "fixture.gds"
    if hashlib.sha256(gds.read_bytes()).hexdigest() != manifest["gds_sha256"]:
        raise ValueError("The stream differs from the DRC input")
    layout = db.Layout()
    layout.read(str(gds))
    top = layout.cell(CORE)
    (lib, _, outline), instances, _, _, _ = readback(folder / "sar-readback.txt")
    dbu = layout.dbu

    def box(xy):
        return db.Box(*(round(coord / dbu) for coord in xy))

    def site(master):
        return box((0, 0, WIDTH[master.removesuffix(SUFFIX)] * 0.14, 1.2))

    def key(master, x, y):
        return master, round(x / dbu), round(y / dbu)

    regions = defaultdict(db.Region)
    gds_instances = Counter()
    for inst in top.each_inst():
        master = inst.cell.name.split("_CDNS_")[0]
        group = category(master)
        if group:
            origin = inst.dtrans.disp
            gds_instances[key(master, origin.x, origin.y)] += 1
            regions[group].insert(inst.trans * site(master) if master.endswith(SUFFIX) else inst.bbox())
    oa = db.Region()
    oa_instances = Counter()
    for _, master, orient, (x, y), bounds in instances.values():
        if category(master) is None:
            continue
        oa_instances[key(master, x, y)] += 1
        if master.endswith(SUFFIX):
            movement = {"R0": db.Trans.R0, "MX": db.Trans.M0, "MY": db.Trans.M90, "R180": db.Trans.R180}[orient]
            oa.insert((movement * site(master)).moved(round(x / dbu), round(y / dbu)))
            continue
        oa.insert(box(bounds))
    combined = db.Region()
    for region in regions.values():
        combined += region
    combined.merge()
    if gds_instances != oa_instances or not (combined ^ oa.merged()).is_empty():
        raise ValueError("Device positions or occupied polygons differ between GDS and OA")
    area = box(outline).area() * dbu**2
    used = combined.area() * dbu**2
    result = dict(
        view="/".join([lib, CORE, manifest.get("view", "layout")]),
        id=manifest["identity"],
        bounds_um=outline,
        area_um2=round(area, 6),
        device_area_um2=round(used, 6),
        device_area_by_group_um2={
            name: round(region.merged().area() * dbu**2, 6) for name, region in sorted(regions.items())
        },
        device_share_pct=round(100 * used / area, 4),
        instance_count=sum(gds_instances.values()),
        reservation_um=list(reservation),
        device_share_of_reservation_pct=round(100 * used / (reservation[0] * reservation[1]), 4),
    )
    return result, regions, layout


def polygons(region, scale):
    return [[(p.x * scale, p.y * scale) for p in poly.each_point_hull()] for poly in region.each()]


def compare(first, current, image):
    blocks = json.loads((ROOT / "Layout/design/floorplan.json").read_text())["blocks"]
    reservation = next(block["size"] for block in blocks if block["id"] == "sar_timing")
    before, after = measure(first, [40, 70]), measure(current, reservation)
    fig, axes = plt.subplots(1, 3, figsize=(10, 6.1), layout="constrained", sharex=True, sharey=True)
    for ax, (metrics, groups, layout), title in zip(
        axes[:2], (before, after), ("Initial placement", "Routed compact core")
    ):
        for group, shapes in groups.items():
            ax.add_collection(
                PolyCollection(
                    polygons(shapes, layout.dbu),
                    facecolor=COLORS[group],
                    edgecolor="white",
                    linewidth=0.18,
                )
            )
        x0, y0, x1, y1 = metrics["bounds_um"]
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, lw=1, ec="#243746"))
        ax.set_title(
            f"{title}\n{metrics['area_um2']:,.1f} µm²  ·  {metrics['device_share_pct']:.1f}% occupied",
            fontsize=11,
            loc="left",
        )
    layout = after[2]
    top = layout.cell(CORE)
    palette = ["#9da8b2", "#3282a1", "#c17857", "#5c648f", "#70a385", "#3c4652"]
    for number, color in enumerate(palette, 31):
        layer = layout.find_layer(number, 0)
        if layer is not None:
            region = db.Region(top.shapes(layer)).merged()
            axes[2].add_collection(
                PolyCollection(polygons(region, layout.dbu), facecolor=color, edgecolor="none")
            )
    x0, y0, x1, y1 = after[0]["bounds_um"]
    axes[2].add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, lw=1, ec="#243746"))
    axes[2].set_title("Routed compact core\nTop-cell M1–M6 wires", fontsize=11, loc="left")
    for ax in axes:
        ax.set(xlim=(-1.5, 41.5), ylim=(0, 68), aspect="equal", xlabel="x (µm)")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(labelsize=8)
    axes[0].set_ylabel("y (µm)")
    fig.suptitle("SAR timing core  |  Native OA and GDS measurements", fontsize=15)
    fig.legend(
        handles=[Patch(color=c, label=n) for n, c in COLORS.items()],
        loc="outside lower center",
        ncol=5,
        frameon=False,
        fontsize=9,
    )
    image.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(image, dpi=175, bbox_inches="tight")
    plt.close(fig)
    return dict(
        initial=before[0],
        compact=after[0],
        area_reduction_pct=round(100 * (1 - after[0]["area_um2"] / before[0]["area_um2"]), 4),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("initial", "compact", "figure", "summary"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    result = compare(args.initial, args.compact, args.figure)
    args.summary.write_text(json.dumps(result, indent=2) + "\n")
