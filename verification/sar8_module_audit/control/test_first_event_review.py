"""Focused dimensional/sign checks for the new local integration measurement."""
import unittest

import numpy as np

from review_first_event_v1 import integrate_native


class IntegrationTests(unittest.TestCase):
    def test_constant_opposite_currents_on_irregular_native_grid(self):
        t = np.array([0., .13, .41, 1.]) * 1e-9
        currents = np.column_stack([np.full(len(t), 2e-6), np.full(len(t), -2e-6)])
        native, q = integrate_native(t, currents, 0, 1e-9)
        np.testing.assert_array_equal(native, t)
        np.testing.assert_allclose(q[:, 0], -2e-6 * t, rtol=1e-14, atol=1e-29)
        np.testing.assert_allclose(q[:, 1], 2e-6 * t, rtol=1e-14, atol=1e-29)
        np.testing.assert_array_equal(q.sum(axis=1), np.zeros(len(t)))

    def test_linear_current_matches_closed_form_antiderivative(self):
        t = np.array([0., .17, .22, .85, 1.]) * 1e-9
        currents = (1e-6 + 2000 * t)[:, None]
        native, q = integrate_native(t, currents, 0, 1e-9)
        expected = -1e-6 * t - 1000 * t**2
        np.testing.assert_array_equal(native, t)
        np.testing.assert_allclose(q[:, 0], expected, rtol=1e-14, atol=1e-29)

    def test_window_uses_existing_rows_without_fabricated_endpoints(self):
        t = np.array([0., .2, .4, .8, 1.]) * 1e-9
        currents = np.full((len(t), 1), 1e-6)
        native, q = integrate_native(t, currents, .1e-9, .9e-9)
        np.testing.assert_array_equal(native, t[1:4])
        self.assertAlmostEqual(q[-1, 0] / 1e-15, -.6)
        with self.assertRaisesRegex(ValueError, 'too short'):
            integrate_native(t, currents, .3e-9, .5e-9)


if __name__ == '__main__':
    unittest.main(verbosity=2)
