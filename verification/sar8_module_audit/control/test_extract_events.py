"""Small synthetic cases; no simulation data mutation or waveform processing."""
import unittest

from extract_events import (
    CLASS_COMPACT, CLASS_NATIVE, collect_frame, margin_gate, observer_times,
    parse_events, pick, pulse_contract, record, require_time, spice_time_ns,
)


DECK = "VSAMPLE (SAMPLE 0) vsource type=pulse val0=SUP val1=0 delay=41n rise=100p fall=100p width=59.9n period=100n\n"
OBSERVER = "@(timer(41.8n,100n)) x=0; @(timer(90n,100n)) x=1; @(timer(98n,100n)) x=2;"


def fixture():
    events = {
        ("xdut.sample_int", 0): [41.0],
        ("xdut.seq_sample", 0): [41.1],
        ("xdut.cmp_clk", 1): [43.0 + 6 * i for i in range(8)],
        ("xdut.xctrl.phi_w", 1): [44.0 + 6 * i for i in range(8)],
        ("xdut.phi_u", 1): [44.5 + 6 * i for i in range(8)],
        ("xdut.xref.rst0", 1): [101.0],
        ("xdut.sample_int", 1): [101.1],
        ("xdut.seq_sample", 1): [103.0],
    }
    summary = dict(conversion_ns=45.5, monitor_valid=True,
        reset_before_actual_next_sample=dict(observed=True, settled_ns=102.0, next_actual_sample_ns=103.0))
    return events, summary


def frame(events, summary, stop=110.0):
    return collect_frame(events, summary, 0, stop, pulse_contract(DECK), observer_times(OBSERVER))


class EventExtractionTests(unittest.TestCase):
    def test_seconds_converted_to_ns(self):
        self.assertAlmostEqual(parse_events("CLK 1 1.01e-7\n")[("clk", 1)][0], 101.0)

    def test_explicit_ns_unit(self):
        self.assertEqual(parse_events("CLK 0 101\n", "ns")[("clk", 0)], [101.0])

    def test_unsupported_units_rejected(self):
        with self.assertRaises(ValueError):
            parse_events("CLK 0 101", "ps")

    def test_malformed_or_nonfinite_events_rejected(self):
        for text in ("clk 1", "clk 2 1", "clk 1 nan", "clk 1 -1e-9", "clk 1 inf"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_events(text)

    def test_missing_event_has_null(self):
        event = pick({}, "clk", 1, 0, 100)
        self.assertIsNone(event["time_ns"])
        self.assertEqual(event["status"], "not_observed")

    def test_duplicate_event_not_collapsed(self):
        events = parse_events("clk 1 1e-9\nclk 1 1e-9\n")
        event = pick(events, "clk", 1, 0, 100)
        self.assertEqual(event["status"], "ambiguous")
        self.assertIsNone(event["time_ns"])

    def test_duplicate_with_matching_count_still_ambiguous(self):
        event = pick({("clk", 1): [1.0, 1.0]}, "clk", 1, 0, 10, expected_count=2)
        self.assertEqual(event["status"], "ambiguous")

    def test_out_of_order_signal_events_rejected(self):
        event = pick({("clk", 1): [2.0, 1.0]}, "clk", 1, 0, 10, expected_count=2)
        self.assertEqual(event["status"], "ambiguous")

    def test_frame_boundary_belongs_to_next_interval(self):
        events = {("clk", 1): [99.0, 100.0]}
        self.assertEqual(pick(events, "clk", 1, 0, 100)["time_ns"], 99.0)
        self.assertEqual(pick(events, "clk", 1, 100, 110)["time_ns"], 100.0)

    def test_cross_frame_reset_is_found(self):
        events, summary = fixture()
        output = frame(events, summary)
        self.assertEqual(output["events"]["last_reference_RST0_assertion"]["time_ns"], 101.0)
        self.assertEqual(output["events"]["next_SEQ_SAMPLE_open"]["time_ns"], 103.0)
        self.assertEqual(output["bottom_before_next_sample"]["measured_margin_ns"], 1.0)
        self.assertIsNone(output["bottom_before_next_sample"]["pass_"])

    def test_missing_next_sample_leaves_readiness_undecided(self):
        events, summary = fixture()
        events.pop(("xdut.seq_sample", 1))
        output = frame(events, summary, stop=102.0)
        self.assertIsNone(output["events"]["bottom_ready"]["time_ns"])
        self.assertIsNone(output["bottom_before_next_sample"]["measured_margin_ns"])
        self.assertIsNone(output["bottom_before_next_sample"]["pass_"])
        self.assertEqual(output["events"]["last_reference_RST0_assertion"]["time_ns"], 101.0)

    def test_duplicate_next_sample_is_not_pass(self):
        events, summary = fixture()
        events[("xdut.seq_sample", 1)].append(103.0)
        output = frame(events, summary)
        self.assertEqual(output["events"]["next_SEQ_SAMPLE_open"]["status"], "ambiguous")
        self.assertIsNone(output["bottom_before_next_sample"]["pass_"])

    def test_missing_next_sample_cannot_select_later_frame_reset(self):
        events, summary = fixture()
        events.pop(("xdut.seq_sample", 1))
        events[("xdut.xref.rst0", 1)] = [201.0]
        output = frame(events, summary, stop=210.0)
        self.assertIsNone(output["events"]["last_reference_RST0_assertion"]["time_ns"])
        self.assertEqual(output["events"]["last_reference_RST0_assertion"]["search_interval_ns"][1], 101.1)

    def test_missing_both_sample_edges_bounds_reset_at_frame_end(self):
        events, summary = fixture()
        events.pop(("xdut.seq_sample", 1))
        events.pop(("xdut.sample_int", 1))
        events[("xdut.xref.rst0", 1)] = [201.0]
        output = frame(events, summary, stop=210.0)
        self.assertIsNone(output["events"]["last_reference_RST0_assertion"]["time_ns"])
        self.assertEqual(output["events"]["last_reference_RST0_assertion"]["search_interval_ns"][1], 100.0)

    def test_historical_latency_and_new_relative_origin(self):
        events, summary = fixture()
        output = frame(events, summary)
        self.assertEqual(output["conversion_ns"], 45.5)
        self.assertAlmostEqual(output["events"]["last_update"]["time_from_SEQ_SAMPLE_close_ns"], 45.4)

    def test_historical_latency_mismatch_rejected(self):
        events, summary = fixture()
        summary["conversion_ns"] = 999.0
        with self.assertRaises(ValueError):
            frame(events, summary)

    def test_compact_next_sample_identity_mismatch_rejected(self):
        events, summary = fixture()
        summary["reset_before_actual_next_sample"]["next_actual_sample_ns"] = 104.0
        with self.assertRaises(ValueError):
            frame(events, summary)

    def test_unusable_event_refused_even_if_it_contains_a_number(self):
        event = record(100.0, "not_observed", CLASS_NATIVE)
        with self.assertRaises(ValueError):
            require_time(event)
        gate = margin_gate(record(99.0, "estimated", CLASS_COMPACT), event, 0.0)
        self.assertEqual(gate["status"], "undecided")
        self.assertIsNone(gate["pass_"])

    def test_wrong_evidence_class_refused_by_gate(self):
        ready = record(99.0, "scheduled", "observer_schedule")
        gate = margin_gate(ready, record(100.0, "observed", CLASS_NATIVE), 0.0)
        self.assertIsNone(gate["pass_"])

    def test_unknown_budget_has_no_implicit_pass(self):
        gate = margin_gate(record(90.0, "estimated", CLASS_COMPACT), record(100.0, "observed", CLASS_NATIVE))
        self.assertEqual(gate["measured_margin_ns"], 10.0)
        self.assertEqual(gate["status"], "undecided")
        self.assertIsNone(gate["pass_"])

    def test_explicit_synthetic_budget_gate_detects_failure(self):
        ready = record(99.0, "estimated", CLASS_COMPACT)
        deadline = record(100.0, "observed", CLASS_NATIVE)
        self.assertTrue(margin_gate(ready, deadline, 0.5)["pass_"])
        self.assertFalse(margin_gate(ready, deadline, 2.0)["pass_"])
        with self.assertRaises(ValueError):
            margin_gate(ready, deadline, -1.0)

    def test_final_write_and_observer_valid_do_not_qualify_dout(self):
        events, summary = fixture()
        output = frame(events, summary)
        self.assertIsNotNone(output["events"]["last_write"]["time_ns"])
        self.assertTrue(summary["monitor_valid"])
        self.assertIsNone(output["events"]["DOUT_valid"]["time_ns"])
        self.assertIsNone(output["data_before_read_window"]["pass_"])

    def test_source_units_and_pulse_offsets(self):
        self.assertEqual(spice_time_ns("100p"), 0.1)
        self.assertEqual(spice_time_ns("1e-7"), 100.0)
        contract = pulse_contract(DECK)
        self.assertAlmostEqual(contract["close_offset_ns"], 41.05)
        self.assertAlmostEqual(contract["next_open_offset_ns"], 101.05)
        self.assertEqual(contract["period"], 100.0)

    def test_unsupported_source_or_observer_contract_rejected(self):
        for text in (DECK.replace("val0=SUP", "val0=0"), DECK.replace("rise=100p", "rise=200p")):
            with self.assertRaises(ValueError):
                pulse_contract(text)
        with self.assertRaises(ValueError):
            observer_times(OBSERVER.replace("90n", "91n"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
