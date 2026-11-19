"""Render the actual streamed comparator geometry (requires matplotlib; reads GDS itself)."""
import argparse
import math
from pathlib import Path
import struct

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Patch


def real8(data):
    """GDSII excess-64 base-16 real."""
    sign = -1 if data[0] & 0x80 else 1
    return sign * int.from_bytes(data[1:8], 'big') / 2 ** 56 * 16 ** ((data[0] & 0x7f) - 64)


def read_gds(path):
    """Structures of boundaries, references and texts, in um. PATH/BOX/NODE are rejected."""
    data = Path(path).read_bytes()
    cells, cell, element, scale, offset = {}, None, None, None, 0
    while offset < len(data):
        size, record = struct.unpack_from('>HB', data, offset)
        if size < 4:
            break
        body = data[offset + 4:offset + size]
        offset += size
        if record == 0x03:
            scale = real8(body[8:16]) / 1e-6
        elif record == 0x06:
            cell = cells.setdefault(body.rstrip(b'\0').decode('ascii'), {'polygons': [], 'refs': [], 'labels': []})
        elif record in (0x09, 0x15, 0x2D):
            raise ValueError('Unsupported GDS element; extend the reader before rendering')
        elif record in (0x08, 0x0A, 0x0B, 0x0C):
            element = {'kind': record, 'mirror': False, 'angle': 0.0, 'mag': 1.0}
        elif element is None:
            continue
        elif record == 0x0D:
            element['layer'] = struct.unpack('>h', body)[0]
        elif record == 0x12:
            element['name'] = body.rstrip(b'\0').decode('ascii')
        elif record == 0x13:
            element['colrow'] = struct.unpack('>hh', body)
        elif record == 0x1A:
            element['mirror'] = bool(struct.unpack('>H', body)[0] & 0x8000)
        elif record == 0x1B:
            element['mag'] = real8(body)
        elif record == 0x1C:
            element['angle'] = real8(body)
        elif record == 0x19:
            element['text'] = body.rstrip(b'\0').decode('ascii')
        elif record == 0x10:
            values = struct.unpack('>%di' % (len(body) // 4), body)
            element['xy'] = [(values[i] * scale, values[i + 1] * scale) for i in range(0, len(values), 2)]
        elif record == 0x11:
            if element['kind'] == 0x08:
                cell['polygons'].append((element['layer'], element['xy'][:-1]))
            elif element['kind'] == 0x0C:
                cell['labels'].append((element['text'], element['xy'][0]))
            else:
                cell['refs'].append(element)
            element = None
    return cells


def placements(ref):
    if ref['kind'] == 0x0A:
        yield ref['xy'][0]
        return
    (ox, oy), (cx, cy), (rx, ry) = ref['xy']
    cols, rows = ref['colrow']
    for j in range(rows):
        for i in range(cols):
            yield (ox + i * (cx - ox) / cols + j * (rx - ox) / rows,
                   oy + i * (cy - oy) / cols + j * (ry - oy) / rows)


def flatten(cells, name):
    """All polygons of a structure with references expanded (reflect, magnify, rotate, translate)."""
    out = list(cells[name]['polygons'])
    for ref in cells[name]['refs']:
        c, s = math.cos(math.radians(ref['angle'])), math.sin(math.radians(ref['angle']))
        for dx, dy in placements(ref):
            for layer, points in flatten(cells, ref['name']):
                moved = []
                for x, y in points:
                    x, y = x * ref['mag'], (-y if ref['mirror'] else y) * ref['mag']
                    moved.append((x * c - y * s + dx, x * s + y * c + dy))
                out.append((layer, moved))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('gds')
    parser.add_argument('output')
    parser.add_argument('--cell', default='sar_strongarm_t28')
    args = parser.parse_args()
    cells = read_gds(args.gds)
    polygons = flatten(cells, args.cell)
    layers = {3: ('NW', '#9cac78'), 6: ('OD', '#62a565'), 17: ('PO', '#d79748'),
              30: ('CO', '#444444'), 31: ('M1', '#4192cc'), 32: ('M2', '#e06c72'),
              33: ('M3', '#a980cd'), 34: ('M4', '#c2a638'), 35: ('M5', '#3ba8a3')}
    xs = [x for _, points in polygons for x, _ in points]
    ys = [y for _, points in polygons for _, y in points]
    width, height = max(xs) - min(xs), max(ys) - min(ys)
    figure, axis = plt.subplots(figsize=(8, max(6.0, min(12.0, 8 * (height + 1) / (width + 1.3)))))
    for layer, (name, color) in layers.items():
        points = [points for number, points in polygons if number == layer]
        if points:
            axis.add_collection(PolyCollection(points, facecolors=color, edgecolors=color,
                                               linewidths=0.25, alpha=0.18 if layer == 3 else 0.65))
    for text, (x, y) in cells[args.cell]['labels']:
        axis.annotate(text, (x, y), ha='center', va='center', fontsize=7, weight='bold',
                      bbox=dict(facecolor='white', alpha=0.85, edgecolor='none', pad=0.6))
    axis.set_xlim(min(xs) - 0.5, max(xs) + 0.8)
    axis.set_ylim(min(ys) - 0.5, max(ys) + 0.5)
    axis.set_aspect('equal')
    axis.set_xlabel('x (µm)')
    axis.set_ylabel('y (µm)')
    axis.set_title('StrongARM comparator · native GDS geometry\n%.2f × %.2f µm' % (width, height))
    axis.legend(handles=[Patch(facecolor=color, label=name) for name, color in layers.values()],
                loc='upper left', bbox_to_anchor=(1.01, 1), frameon=False)
    figure.tight_layout()
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=180)
    print(destination.resolve())


if __name__ == '__main__':
    main()
