"""Exclusions and placements of the Stage 5 core fill (Layout/design/toplevel_fill.py, Layout/specs/fill-policy.md)."""
import unittest

from Layout.design import toplevel_fill as tf


class CoreFillRules(unittest.TestCase):
    def setUp(self):
        self.boxes = tf.plan()

    def test_regions_follow_the_owner_table(self):
        rules = {tuple(round(v, 4) for v in box): layers for box, layers in tf.region_exclusions()}
        self.assertEqual(tf.pair_box(), (10.0, 10.0, 82.23, 68.325))
        self.assertEqual(rules[tf.pair_box()], tf.ALL)                        # the pair owns its whole outline
        for name in ("bootstrap_n", "bootstrap_p") + tf.REGIONS_ALL:
            self.assertEqual(rules[tuple(round(v, 4) for v in self.boxes[name])], tf.ALL, name)
        sar = rules[tuple(round(v, 4) for v in self.boxes["sar"])]
        self.assertEqual(set(sar), set(range(1, 7)) | {"OD", "PO"})          # the macro owns OD/PO and M1-M6
        self.assertFalse({7, 8, 9} & set(sar))                                # the top level fills M7-M9 over it

    def test_route_exclusions_cover_signal_layer_and_neighbours(self):
        rules = tf.route_exclusions()
        self.assertTrue(rules)
        for box, layers in rules:
            self.assertTrue(box[0] < box[2] and box[1] < box[3])
            self.assertTrue(set(layers) <= set(range(1, 10)))
            self.assertEqual(max(layers) - min(layers), len(layers) - 1)     # contiguous, at most layer +-1
        vin = [box for box, layers in rules if layers == (4, 5, 6) and box[3] > 110]
        self.assertEqual(len(vin), 2)
        left, right = sorted(vin)
        self.assertAlmostEqual(left[0] + right[2], 2 * tf.AXIS, places=6)    # VINN/VINP mirror images

    def test_bootstrap_cell_fits_both_instances(self):
        n, p = self.boxes["bootstrap_n"], self.boxes["bootstrap_p"]
        self.assertAlmostEqual(n[0] + p[2], 2 * tf.AXIS, places=6)
        self.assertEqual((n[1], n[3]), (p[1], p[3]))
        # MY about x = 2 * AXIS maps the XBOOTP outline onto the XBOOTN outline.
        self.assertAlmostEqual(2 * tf.AXIS - p[2], n[0], places=6)
        self.assertAlmostEqual(2 * tf.AXIS - p[0], n[2], places=6)

    def test_exclusion_layers(self):
        g = tf.gds()
        rects = tf.exclusion_rects([((0, 0, 1, 1), tf.ALL)])
        self.assertEqual(sorted((r.layer, r.datatype) for r in rects),
                         sorted([(150, n) for n in range(1, 10)] + [tf.ODBLK, tf.POBLK]))
        self.assertTrue(all(isinstance(r, g.Polygon) for r in rects))


if __name__ == "__main__":
    unittest.main()
