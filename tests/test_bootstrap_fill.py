import unittest

from Layout.design import bootstrap_fill as bf
from Layout.design.bootstrap import candidate_of


class BootstrapFillPlan(unittest.TestCase):
    def setUp(self):
        self.plan = bf.fill_plan()

    def shapes(self, layer):
        return [s for s in self.plan if s[:2] == (layer, 'dummy')]

    def test_density_targets(self):
        s = bf.summary(self.plan)
        self.assertGreaterEqual(s['array_window_od'], .21)   # OD.DN.3 20 %, with margin
        self.assertGreaterEqual(s['array_window_po'], .11)   # PO.DN.3 10 %, with margin

    def test_dummy_widths(self):
        for _, _, x0, y0, x1, y1 in self.shapes('PO'):
            self.assertGreaterEqual(round(x1 - x0, 4), .12)   # DPO.W.1
        for _, _, x0, y0, x1, y1 in self.shapes('OD'):
            self.assertGreaterEqual(round(x1 - x0, 4), .25)   # DOD.W.1

    def test_poly_stays_between_unit_fingers(self):
        # Unit M1 spans 0.005-0.755 um from each unit origin; the next unit starts 0.88 um later.
        for _, _, x0, y0, x1, y1 in self.shapes('PO'):
            offset = round((x0 - bf.origin(0)) % bf.UNIT_PITCH_X, 4)
            self.assertGreaterEqual(offset, .755)
            self.assertLessEqual(round(offset + (x1 - x0), 4), .885)

    def test_od_under_its_poly_stripe(self):
        # DPO.EX.2: OD 0.075 um past the poly sides; DPO.EX.1: poly 0.08 um past the OD ends.
        poly = self.shapes('PO')
        for _, _, x0, y0, x1, y1 in self.shapes('OD'):
            self.assertTrue(any(p[2] - x0 >= .075 - 1e-9 and x1 - p[4] >= .075 - 1e-9 and p[3] <= y0 - .08 + 1e-9
                                and p[5] >= y1 + .08 - 1e-9 for p in poly), 'dummy OD without its poly stripe')

    def test_clear_of_switch_bank(self):
        # Rows 0-1: OD_18 spans x -3.76 to 3.72 (DOD.S.8 0.08 um) inside the substrate ring OD x -3.57 to 3.37
        # (DOD.S.2 0.34 um).
        for _, _, x0, y0, x1, y1 in self.shapes('OD'):
            if y0 < 6.2:
                self.assertTrue(x1 <= -3.91 or x0 >= 3.80, (x0, x1))

    def test_blockages_cover_the_outline(self):
        blocks = [s for s in self.plan if s[0] in ('ODBLK', 'POBLK', 'DMEXCL')]
        self.assertEqual(len(blocks), 11)
        self.assertTrue(all(tuple(s[2:]) == bf.OUTLINE for s in blocks))


class RevisionViews(unittest.TestCase):
    def test_revision_view_uses_the_selected_netlist(self):
        self.assertIsNone(candidate_of('layout_r2'))
        self.assertIsNone(candidate_of('layout'))
        self.assertEqual(candidate_of('layout_mmain4'), 'mmain4')


if __name__ == '__main__':
    unittest.main()
