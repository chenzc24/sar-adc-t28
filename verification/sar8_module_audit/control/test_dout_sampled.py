"""Synthetic sampled-data diagnostics; explicit grids are not silicon budgets."""
import unittest

import numpy as np

from dout_sampled import frame_diagnostic, grid_bound, sampled_ready


def ready(values, **changes):
    options = dict(band_fraction=.1, justified_max_grid_gap_ns=1.0)
    options.update(changes)
    t = np.arange(len(values), dtype=float)
    return sampled_ready(t, values, np.ones(len(t)), 1, 0.0, float(t[-1]), **options)


def frame():
    def event(t, status="observed"):
        return dict(time_ns=t, status=status)
    return dict(frame=0, events=dict(SEQ_SAMPLE_close=event(41.1),
        test_read_window_start=event(90.0, "scheduled"), test_read_time=event(98.0, "scheduled"),
        last_write=event(86.0)))


class SampledDoutTests(unittest.TestCase):
    def test_ready_follows_last_bad_sample(self):
        result = ready([0, 0, 0, 1, 1, 1])
        self.assertEqual(result["sampled_ready_ns"], 3.0)
        self.assertEqual(result["sampled_ready_bracket_ns"], [2.0, 3.0])

    def test_later_sampled_excursion_moves_estimate(self):
        result = ready([1, 1, 1, 0, 1, 1, 1])
        self.assertEqual(result["sampled_ready_ns"], 4.0)

    def test_bad_read_endpoint_has_no_ready_estimate(self):
        self.assertIsNone(ready([1, 1, 0])["sampled_ready_ns"])

    def test_single_good_suffix_sample_is_insufficient(self):
        self.assertIsNone(ready([0, 0, 1])["sampled_ready_ns"])

    def test_missing_read_bracket_is_unavailable(self):
        result = sampled_ready([0., 1., 2.], [1., 1., 1.], [1., 1., 1.], 1, 0., 2.1,
                               band_fraction=.1, justified_max_grid_gap_ns=1.)
        self.assertIsNone(result["sampled_ready_ns"])

    def test_large_grid_gap_is_not_accepted_as_resolution(self):
        result = ready([1, 1, 1], justified_max_grid_gap_ns=.03)
        self.assertIsNone(result["sampled_ready_ns"])
        self.assertEqual(result["observed_max_gap_ns"], 1.0)

    def test_unknown_resolution_or_band_is_unavailable(self):
        self.assertIsNone(ready([1, 1, 1], justified_max_grid_gap_ns=None)["sampled_ready_ns"])
        self.assertIsNone(ready([1, 1, 1], band_fraction=None)["sampled_ready_ns"])

    def test_strict_rail_band_rejects_boundary_and_overshoot(self):
        result = ready([1.0, 1.2, 1.0, 1.0])
        self.assertEqual(result["sampled_ready_ns"], 2.0)
        result = sampled_ready([0., 1., 2., 3.], [0., .1, 0., 0.], [1.] * 4, 0, 0., 3.,
                               band_fraction=.1, justified_max_grid_gap_ns=1.)
        self.assertEqual(result["sampled_ready_ns"], 2.0)

    def test_nonfinite_or_duplicate_samples_are_unavailable(self):
        result = sampled_ready([0., 1., 1.], [1.] * 3, [1.] * 3, 1, 0., 1.,
                               band_fraction=.1, justified_max_grid_gap_ns=1.)
        self.assertIsNone(result["sampled_ready_ns"])
        self.assertIsNone(ready([1., float("nan"), 1.])["sampled_ready_ns"])

    def test_word_can_match_before_last_write_without_validity_claim(self):
        t = np.arange(111, dtype=float)
        dout = np.zeros((len(t), 8))
        dout[t >= 45., 0] = 1.
        result = frame_diagnostic(t, dout, np.ones(len(t)), frame(), 1,
                                  band_fraction=.1, max_gap=1.)
        self.assertEqual(result["sampled_bus_ready_ns"], 45.0)
        self.assertEqual(result["sampled_bus_ready_minus_last_write_ns"], -41.0)
        self.assertIsNone(result["qualified_DOUT_valid_time_ns"])
        self.assertIsNone(result["silicon_acceptance"]["pass_"])

    def test_legacy_window_violation_is_sample_diagnostic_only(self):
        t = np.arange(111, dtype=float)
        dout = np.zeros((len(t), 8))
        dout[t >= 96., 0] = 1.
        result = frame_diagnostic(t, dout, np.ones(len(t)), frame(), 1,
                                  band_fraction=.1, max_gap=1.)
        self.assertFalse(result["legacy_window_all_checked_samples_in_expected_band"])
        self.assertEqual(result["sampled_bus_ready_ns"], 96.0)
        self.assertIsNone(result["silicon_acceptance"]["pass_"])

    def test_missing_output_column_has_no_estimate(self):
        result = frame_diagnostic(np.arange(111.), np.zeros((111, 7)), np.ones(111), frame(), 0,
                                  band_fraction=.1, max_gap=1.)
        self.assertIsNone(result["sampled_ready_ns"])

    def test_native_grid_bound_is_derived_from_recorded_settings(self):
        self.assertAlmostEqual(grid_bound(dict(plot_estimate_spacing_ps=20,
            effective_settings={"maxstep": "10 ps, default 2 ns (conservative)"})), .03)
        self.assertIsNone(grid_bound({}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
