"""Draw the Bootstrap footprint and its switch routing from the checked GDS."""
import argparse
from pathlib import Path

import klayout.db as db
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Patch, Rectangle

from Layout.design.bootstrap import CORE


LAYERS = [
    (3, 0, 'NW', '#b2c893', 0.50), (6, 0, 'OD', '#548961', 0.80),
    (17, 7, 'Dummy PO', '#d5c2a6', 0.82), (17, 0, 'PO', '#bd7944', 0.82),
    (31, 0, 'M1', '#3b839f', 0.66), (32, 0, 'M2', '#d37466', 0.76),
    (33, 0, 'M3', '#745aa3', 0.74), (34, 0, 'M4', '#28584e', 0.90),
    (30, 0, 'CO', '#253138', 0.86)]


def draw_layer(axis, layout, cell, number, purpose, color, alpha, clip, recursive):
    index = layout.find_layer(number, purpose)
    if index is None:
        return
    region = db.Region(cell.begin_shapes_rec(index)) if recursive else db.Region(cell.shapes(index))
    region &= db.Region(clip.to_itype(layout.dbu))
    polygons = [[(p.x*layout.dbu, p.y*layout.dbu) for p in poly.each_point_hull()] for poly in region.each()]
    # Draw per shape. A merged ring has an interior hole, which the hull would cover.
    if any(poly.holes() for poly in region.each()):
        polygons = [[(p.x*layout.dbu, p.y*layout.dbu) for p in tri.each_point_hull()]
                    for tri in region.decompose_trapezoids_to_region().each()]
    if polygons:
        axis.add_collection(PolyCollection(polygons, facecolors=color, edgecolors='none', alpha=alpha))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('gds', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    layout = db.Layout()
    layout.read(str(args.gds))
    top = layout.cell(CORE)
    box = top.dbbox()
    zoom = db.DBox(-3.10, -0.14, 3.62, 5.62)
    plt.rcParams.update({'font.family': ['Microsoft YaHei', 'DejaVu Sans'],
                         'axes.unicode_minus': False, 'font.size': 10, 'axes.linewidth': 0.65})
    fig, (overall, detail) = plt.subplots(1, 2, figsize=(13, 6.35), gridspec_kw={'width_ratios': [1, 1.24]})
    fig.subplots_adjust(left=0.052, right=0.988, top=0.844, bottom=0.20, wspace=0.14)
    fig.suptitle('Bootstrap 采样核心', x=0.052, y=0.97, ha='left', fontsize=22, weight='bold', color='#21352e')
    count = 0
    for inst in top.each_inst():
        if inst.cell.name.startswith('cfmom_2t'):
            b = inst.dbbox()
            overall.add_patch(Rectangle((b.left, b.bottom), b.width(), b.height(),
                               facecolor='#dfede4', edgecolor='#89ad96', lw=0.42))
            count += 1
    if count != 200:
        raise ValueError('Expected 200 native unit capacitors')
    for layer, purpose, _, color, alpha in LAYERS:
        draw_layer(detail, layout, top, layer, purpose, color, alpha, zoom, True)
        draw_layer(overall, layout, top, layer, purpose, color, alpha, box, False)
    outline = Rectangle((zoom.left, zoom.bottom), zoom.width(), zoom.height(), fill=False,
                        edgecolor='#a23d27', lw=1.4, linestyle=(0, (3, 2)))
    overall.add_patch(outline)
    overall.set_title(f'单侧核心  {box.width():.2f} × {box.height():.2f} µm', loc='left', fontsize=13, pad=8)
    detail.set_title('开关区与两个独立 N 阱', loc='left', fontsize=13, pad=8)
    overall.set_xlim(box.left-0.45, box.right+0.45)
    overall.set_ylim(box.bottom-0.60, box.top+0.35)
    detail.set_xlim(zoom.left, zoom.right)
    detail.set_ylim(-0.64, zoom.top)
    for a in (overall, detail):
        a.set_aspect('equal')
        a.spines[['top', 'right']].set_visible(False)
        a.tick_params(labelsize=8, colors='#53665c', length=3)
        a.set_xlabel('x  (µm)', fontsize=9)
        a.set_ylabel('y  (µm)', fontsize=9)
    for x, label in ((-1.45, 'BTOP 井'), (2.30, 'VDD 井')):
        detail.text(x, 5.54, label, ha='center', va='center', fontsize=9, weight='bold')
    detail.text(-1.90, 2.75, '采样与 BBOT 切换', ha='center', va='center', fontsize=9, color='#283e34')
    detail.annotate('复位与时钟', xy=(2.09, 2.39), xytext=(0.95, 2.72), ha='center', fontsize=9,
                    color='#283e34', arrowprops=dict(arrowstyle='-', color='#697c70', lw=0.6))
    # Port labels and anchor points come directly from the stream's pin text.
    for idx in layout.layer_indices():
        for s in top.shapes(idx).each():
            if s.is_text() and s.text.string in {'VIN', 'VOUT', 'CLKS', 'VDD', 'VSS'}:
                p = s.text.trans.disp
                x, y = p.x*layout.dbu, p.y*layout.dbu
                target_x = {'VIN': x-0.32, 'VOUT': x+0.25, 'VDD': x-0.14, 'CLKS': x+0.02, 'VSS': x+0.12}[s.text.string]
                detail.annotate(s.text.string, (x, y), xytext=(target_x, -0.38), ha='center', va='top',
                                fontsize=8.5, weight='bold', arrowprops=dict(arrowstyle='-', color='#4e5f58', lw=0.6))
    legend = [Patch(facecolor='#dfede4', edgecolor='#89ad96', label='MOM 单元边界')]
    legend += [Patch(facecolor=color, alpha=alpha, label=name) for _, _, name, color, alpha in LAYERS]
    fig.legend(handles=legend, loc='lower center', ncol=10, frameon=False, fontsize=8.7,
               bbox_to_anchor=(0.5, 0.055), columnspacing=1.3, handlelength=1.2)
    fig.text(0.052, 0.023, '左图显示 200 个原生 MOM 的外框和核心布线，红框对应右图。右图展开器件、接触与金属。', fontsize=8.8, color='#53665c')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=175)
    plt.close(fig)


if __name__ == '__main__':
    main()
