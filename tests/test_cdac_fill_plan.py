"""Rule and placement invariants of the planned CDAC array fill (Layout/specs/fill-policy.md)."""
import json
from pathlib import Path
import tempfile
import unittest

from Layout.design import cdac_paired as cp


def rects(layer, purpose):
    return [s[2:] for s in cp.fill_plan() if s[:2] == (layer, purpose)]


def gap(a, b):
    """Edge-to-edge distance of two boxes (0 if they touch or overlap)."""
    dx = max(a[0] - b[2], b[0] - a[2], 0)
    dy = max(a[1] - b[3], b[1] - a[3], 0)
    return (dx * dx + dy * dy) ** .5


class FillPlanTests(unittest.TestCase):
    def setUp(self):
        self.od = rects('OD', 'dummy')
        self.po = rects('PO', 'dummy')

    def test_dummy_od_po_rules(self):
        for x0, y0, x1, y1 in self.od:
            self.assertGreaterEqual(round(min(x1 - x0, y1 - y0), 4), .25)          # DOD.W.1
            if min(x1 - x0, y1 - y0) < .39:
                self.assertGreaterEqual(round(max(x1 - x0, y1 - y0), 4), 1)        # DOD.L.1
        for i, a in enumerate(self.od):
            for b in self.od[i + 1:]:
                self.assertGreaterEqual(round(gap(a, b), 4), .13)                  # DOD.S.1
        for x0, y0, x1, y1 in self.po:
            self.assertTrue(.12 <= round(x1 - x0, 4) <= 2)                         # DPO.W.1/W.2
        for i, a in enumerate(self.po):
            for b in self.po[i + 1:]:
                self.assertGreaterEqual(round(gap(a, b), 4), .11)                  # DPO.S.1
        for p in self.po:
            for d in self.od:
                if gap(p, d) == 0:
                    # Vertical dummy gate: DOD extends 75 nm on both sides, DPO end caps 80 nm.
                    self.assertGreaterEqual(round(p[0] - d[0], 4), .075)            # DPO.EX.2
                    self.assertGreaterEqual(round(d[2] - p[2], 4), .075)
                    self.assertGreaterEqual(round(d[1] - p[1], 4), .08)             # DPO.EX.1
                    self.assertGreaterEqual(round(p[3] - d[3], 4), .08)

    def test_clear_of_top_fingers_and_straps(self):
        # Native unit: TOP edge finger x 0.705..0.755, TOP strap y 2.31..2.42 (unflipped).
        top = []
        for c in range(-1, 33):
            for r in range(-1, 9):
                base = r * cp.PY
                flip = r % 2 == 1
                strap = (base, base + .11) if flip else (base + 2.31, base + cp.MOM_H)
                finger = (base + .21, base + 2.31) if not flip else (base + .11, base + 2.21)
                for x0, x1, y0, y1 in [(cp.col(c) + .005, cp.col(c) + .755, *strap),
                                       (cp.col(c) + .705, cp.col(c) + .755, *finger),
                                       (cp.col(c) + .105, cp.col(c) + .155, *finger)]:
                    top.append((x0, y0, x1, y1))
                    top.append((cp.MIRROR - x1, y0, cp.MIRROR - x0, y1))
        for d in self.od:
            if d[1] > -3:
                self.assertGreaterEqual(min(round(gap(d, t), 4) for t in top if gap(d, t) < 1), .01)
        spine = [(cp.TOP_X - .06, cp.MOM_H + .25, cp.TOP_X + .06, cp.TOP_Y)]
        spine.append((cp.MIRROR - cp.TOP_X - .06, spine[0][1], cp.MIRROR - cp.TOP_X + .06, cp.TOP_Y))
        for s in self.od + self.po:
            for t in spine:
                self.assertGreater(gap(s, t), .05)

    def test_mirror_symmetry_and_blocks(self):
        array = [s for s in self.od + self.po if s[1] > -3.1]
        mirrored = {(round(cp.MIRROR - x1, 4), round(y0, 4), round(cp.MIRROR - x0, 4), round(y1, 4))
                    for x0, y0, x1, y1 in array}
        self.assertEqual(mirrored, {tuple(round(v, 4) for v in s) for s in array})
        blocks = [s for s in cp.fill_plan() if s[0] in ('ODBLK', 'POBLK', 'DMEXCL')]
        self.assertEqual(len(blocks), 11)
        box = blocks[0][2:]
        self.assertTrue(all(b[2:] == box for b in blocks))
        for s in array:
            self.assertTrue(box[0] <= s[0] and s[2] <= box[2] and box[1] <= s[1] and s[3] <= box[3])

    def test_m7_lines_cover_mx_dn_7_windows_over_dummy_rows(self):
        lines = rects('M7', 'dummy')
        self.assertEqual(len(lines), 4)
        for x0, y0, x1, y1 in lines:
            # Inside a VSS dummy row (row -1 or row 8), never above active rows.
            row = int((y0 + .01) // cp.PY)
            self.assertIn(row, (-1, 8))
            self.assertLessEqual(y1, row * cp.PY + cp.MOM_H)
            self.assertTrue(.05 <= y1 - y0 <= 4.5)                                # M7.W.1/W.3
        # Mx.DN.7: every 30 um window over the array keeps M7 above 5%.
        x0, x1 = -1.715, 70.515
        for wx in [x0 + 15 * i for i in range(4)] + [x1 - 30]:
            covered = sum(max(0, min(b[2], wx + 30) - max(b[0], wx)) * (b[3] - b[1]) for b in lines)
            self.assertGreater(covered / 900, .055)

    def test_stacked_center_trunks_follow_weight(self):
        grid = cp.assignment('stacked')
        rows = {}
        for (c, r), net in grid.items():
            if c in (15, 16):
                rows[net] = max(rows.get(net, -1), r)
        # Highest row reached by each small-bit trunk grows with its unit count.
        self.assertEqual([rows[b] for b in ('B0', 'B1', 'B2', 'B3')], [0, 1, 3, 7])
        gaps = cp.CENTER['stacked']['gaps']
        self.assertEqual(len(set(gaps.values())), len(gaps))
        # The major bits keep central inversion; the published center stays unchanged.
        self.assertEqual({k: v for k, v in grid.items() if k[0] not in (15, 16)},
                         {k: v for k, v in cp.assignment().items() if k[0] not in (15, 16)})

    def test_fill_cell_only_when_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            for planned in (False, True):
                dest = cp.generate(Path(tmp) / str(planned), planned_fill=planned)
                skill = (dest / 'paired.il').read_text(encoding='ascii')
                self.assertEqual(f'rdOpen("{cp.FILL}")' in skill, planned)
                self.assertEqual('procedure(rdLpp(' in skill, planned)
                placement = json.loads((dest / 'placement.json').read_text())
                self.assertEqual(placement['planned_fill_cell'], cp.FILL if planned else None)


if __name__ == '__main__':
    unittest.main()
