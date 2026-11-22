"""Replace one master in a chip stream with the same cell from another stream, at the GDS level (no OA write).

Used to check a revised block in its chip context before the chip is re-mastered, for example the flat chip
latch-up rules on a new Bootstrap view. The master keeps its name, so every instance in the chip now places the
new geometry; the new master's sub-cells get a prefix so they cannot collide with the chip's own. The old
sub-cells stay in the stream; any that no other cell references become unused top cells, which a run with a
fixed LAYOUT PRIMARY ignores. The pins of the two masters must match (layer, datatype and text) unless --force.
  python -m Layout.tools.physical.substitute_master CHIP.gds BLOCK.gds CELL OUT.gds [--top TOP] [--prefix R2_]
"""
import argparse
import hashlib
import json

import gdstk


def labels(cell):
    return sorted((lbl.text, lbl.layer, lbl.texttype, round(lbl.origin[0], 4), round(lbl.origin[1], 4))
                  for lbl in cell.labels)


def substitute(chip_path, block_path, cell_name, out_path, top=None, prefix='R2_', force=False):
    chip = gdstk.read_gds(chip_path)
    block = gdstk.read_gds(block_path)
    old = next(c for c in chip.cells if c.name == cell_name)
    new = next(c for c in block.cells if c.name == cell_name)
    if labels(old) != labels(new) and not force:
        raise ValueError('Pin labels of %s differ:\n%s\n%s' % (cell_name, labels(old), labels(new)))
    children = new.dependencies(True)
    names = set(c.name for c in chip.cells)
    for child in children:
        child.name = prefix + child.name
        if child.name in names:
            raise ValueError('Prefixed name already in the chip stream: ' + child.name)
    users = [c for c in chip.cells if any(r.cell is old for r in c.references)]
    for user in users:
        for ref in user.references:
            if ref.cell is old:
                ref.cell = new
    chip.remove(old)
    chip.add(new, *children)
    if top:
        tops = [c.name for c in chip.top_level()]
        if top not in tops:
            raise ValueError('Top cell %s is not a top-level cell after substitution: %s' % (top, tops))
    chip.write_gds(out_path)
    digest = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()  # noqa: E731
    return dict(chip=chip_path, chip_sha256=digest(chip_path), block=block_path, block_sha256=digest(block_path),
                cell=cell_name, out=out_path, out_sha256=digest(out_path), prefix=prefix,
                instances_rebound=sum(1 for u in users for r in u.references if r.cell is new),
                users=sorted(u.name for u in users), new_subcells=len(children), pins_equal=labels(old) == labels(new),
                old_bbox=[list(map(float, p)) for p in old.bounding_box()],
                new_bbox=[list(map(float, p)) for p in new.bounding_box()])


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('chip')
    ap.add_argument('block')
    ap.add_argument('cell')
    ap.add_argument('out')
    ap.add_argument('--top')
    ap.add_argument('--prefix', default='R2_')
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    print(json.dumps(substitute(a.chip, a.block, a.cell, a.out, a.top, a.prefix, a.force), indent=1))
