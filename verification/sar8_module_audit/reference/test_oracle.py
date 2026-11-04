"""Small in-memory counterexamples; no existing simulation evidence is changed."""
import copy
import unittest

from oracle import ContractError, ReferenceOracle, validate_document as check_document


CONFIG = dict(vrefp_v=.9, vrefn_v=0., vdd_v=.9,
              logic_low_max_v=.09, logic_high_min_v=.81)


def fixture_contract():
    requirements = [dict(id="preset_analog", start_ns=7.1, end_ns=7.9, stage="reset",
                         bit=None, tolerance_v=.001, purpose="Synthetic initialized-preset check")]
    for step, bit in enumerate(range(7, -1, -1)):
        at = 20 + 10 * step + 4.5
        requirements.append(dict(id=f"late_{bit}_analog", start_ns=at - .2, end_ns=at + .2,
                                 stage="late", bit=bit, tolerance_v=.001,
                                 purpose="Synthetic settled late-word check"))
    return dict(schema_version=1, contract_id="synthetic-only-not-an-approved-circuit-budget",
                analog_requirements=requirements)


def validate_document(document):
    return check_document(document, fixture_contract())


def measured(q, d=None, code=None):
    """Synthetic meter, using the documented truth table independently of class state."""
    bits = [(q >> bit) & 1 for bit in range(8)]
    value = dict(bp_v=[.9 * (1 - bit) for bit in bits],
                 bn_v=[.9 * bit for bit in bits], dummy_p_v=.9, dummy_n_v=0.,
                 q_word=q, gates={"gpn": [.9 * bit for bit in bits],
                                  "gpp": [.9 * bit for bit in bits],
                                  "gnn": [.9 * (1 - bit) for bit in bits],
                                  "gnp": [.9 * (1 - bit) for bit in bits]})
    if d is not None:
        value.update(d_word=d, code_word=code)
    return value


def fixture(word=0xA5):
    """Known independent decision word; 16 captures and 17 analog checkpoints."""
    events, windows = [], []
    for step, bit in enumerate(range(7, -1, -1)):
        events.append(dict(time_ns=step, kind="reset_assert", bit=bit))
    windows.append(dict(name="preset", start_ns=7.1, end_ns=7.9, stage="reset", bit=None,
                        checks=["logic", "analog"], analog_requirement="preset_analog"))
    events.append(dict(time_ns=7.5, kind="observe", window="preset", values=measured(128)))
    for step, bit in enumerate(range(7, -1, -1)):
        events.append(dict(time_ns=8 + step, kind="reset_release", bit=bit))
    events.append(dict(time_ns=16, kind="begin_conversion"))
    d = 0
    for step, bit in enumerate(range(7, -1, -1)):
        base = 20 + 10 * step
        value = (word >> bit) & 1
        d |= value << bit
        code = d | ((1 << (bit - 1)) if bit else 0)
        events.extend([dict(time_ns=base, kind="decision", bit=bit, value=value),
                       dict(time_ns=base + 1, kind="update_rise", bit=bit),
                       dict(time_ns=base + 2, kind="capture")])
        for stage, at, q in [("early", base + 2.5, d), ("late", base + 4.5, code)]:
            name = f"{stage}_{bit}"
            windows.append(dict(name=name, start_ns=at - .2, end_ns=at + .2,
                                stage=stage, bit=bit, checks=["logic"] if stage == "early" else ["logic", "analog"],
                                analog_requirement=None if stage == "early" else f"late_{bit}_analog"))
            events.append(dict(time_ns=at, kind="observe", window=name,
                               values=measured(q, d, code)))
        events.extend([dict(time_ns=base + 3, kind="update_fall"),
                       dict(time_ns=base + 4, kind="capture")])
    events.append(dict(time_ns=100, kind="end_conversion"))
    events.sort(key=lambda event: event["time_ns"])
    return dict(schema_version=1, config=copy.deepcopy(CONFIG), windows=windows, events=events)


def observation(doc, window="late_7"):
    return next(event for event in doc["events"] if event.get("window") == window)


class ReferenceTests(unittest.TestCase):
    def reject(self, doc, reason):
        with self.assertRaisesRegex(ContractError, reason):
            validate_document(doc)

    def test_known_complete_words(self):
        for word in [0, 255, 0xA5, 0x5A, 128, 1]:
            with self.subTest(word=word):
                result = validate_document(fixture(word))
                self.assertTrue(result["contract_checks_passed"])
                self.assertEqual((result["decisions"], result["captures"]), (8, 16))

    def test_wrong_rail_is_settled_but_rejected(self):
        doc = fixture()
        sample = observation(doc)["values"]
        # Bit0 ought to select high on P. Flip both gate commands coherently,
        # and let its bottom fully settle to low: the old local metric is zero.
        sample["bp_v"][0] = 0.
        sample["gates"]["gpn"][0] = sample["gates"]["gpp"][0] = .9
        non, pon = .9 > .45, .9 < .45
        self.assertNotEqual(non, pon)
        old_target = .9 if pon else 0.
        self.assertEqual(abs(sample["bp_v"][0] - old_target), 0.)
        self.reject(doc, "incorrect rail")

    def test_p_n_exchange(self):
        doc = fixture()
        sample = observation(doc)["values"]
        sample["bp_v"], sample["bn_v"] = sample["bn_v"], sample["bp_v"]
        self.reject(doc, "incorrect rail")

    def test_bit_weight_pin_exchange(self):
        doc = fixture()
        sample = observation(doc)["values"]
        for side in ["bp_v", "bn_v"]:
            sample[side][5], sample[side][7] = sample[side][7], sample[side][5]
        self.reject(doc, "incorrect rail")

    def test_late_word_captured_in_early_phase(self):
        doc = fixture()
        observation(doc, "early_7")["values"] = measured(192, 128, 192)
        self.reject(doc, "incorrect independent command state")

    def test_capture_before_update(self):
        doc = fixture()
        doc["events"].insert(18, dict(time_ns=19, kind="capture"))
        doc["events"].sort(key=lambda e: e["time_ns"])
        self.reject(doc, "capture: duplicate, unordered")

    def test_missing_early_capture(self):
        doc = fixture()
        doc["events"] = [event for event in doc["events"] if event["time_ns"] != 22]
        # Drop the early observation too, exposing the actual update_fall check.
        doc["events"] = [event for event in doc["events"] if event.get("window") != "early_7"]
        self.reject(doc, "missing early capture")

    def test_missing_late_capture(self):
        doc = fixture()
        doc["events"] = [event for event in doc["events"]
                         if event["time_ns"] != 24 and event.get("window") != "late_7"]
        self.reject(doc, "preceding two captures required")

    def test_duplicate_capture(self):
        doc = fixture()
        doc["events"].append(dict(time_ns=24.2, kind="capture"))
        doc["events"].sort(key=lambda e: e["time_ns"])
        self.reject(doc, "capture: duplicate")

    def test_descending_bit_order(self):
        doc = fixture()
        next(e for e in doc["events"] if e["kind"] == "decision")["bit"] = 6
        self.reject(doc, "descending bit order")

    def test_per_bit_reset_has_capture_priority(self):
        oracle = ReferenceOracle(CONFIG, [], fixture_contract())
        for event in fixture(0)["events"]:
            if event["time_ns"] >= 22:
                break
            if event["kind"] != "observe":
                oracle.apply(event)
        oracle.apply(dict(time_ns=21.5, kind="reset_assert", bit=7))
        oracle.apply(dict(time_ns=22, kind="capture"))
        self.assertEqual(oracle.d, 0)
        self.assertEqual(oracle.qword(), 128)  # Reset, not D=0, controls MSB.
        oracle.apply(dict(time_ns=23, kind="update_fall"))
        oracle.apply(dict(time_ns=24, kind="capture"))
        self.assertEqual(oracle.qword(), 192)  # Only bit7 is reset; bit6 trials.
        oracle.apply(dict(time_ns=25, kind="reset_release", bit=7))
        self.assertEqual(oracle.qword(), 192)  # Release does not invent capture.

    def test_msb_preset_and_fixed_dummies(self):
        oracle = ReferenceOracle(CONFIG, [], fixture_contract())
        for event in fixture()["events"]:
            if event["time_ns"] >= 7.5:
                break
            oracle.apply(event)
        target = oracle.targets()
        self.assertEqual(target["bp_v"], [.9] * 7 + [0.])
        self.assertEqual(target["bn_v"], [0.] * 7 + [.9])
        self.assertEqual((target["dummy_p_v"], target["dummy_n_v"]), (.9, 0.))

    def test_dummy_wrong_rail(self):
        doc = fixture()
        observation(doc)["values"]["dummy_p_v"] = 0.
        self.reject(doc, "incorrect dummy")

    def test_observed_words_do_not_drive_expectation(self):
        for key in ["q_word", "d_word", "code_word"]:
            with self.subTest(key=key):
                doc = fixture()
                observation(doc)["values"][key] ^= 1
                self.reject(doc, "incorrect independent command state")

    def test_unknown_initial_state(self):
        oracle = ReferenceOracle(CONFIG, [], fixture_contract())
        with self.assertRaisesRegex(ContractError, "unknown state"):
            oracle.targets()
        with self.assertRaisesRegex(ContractError, "unknown state"):
            oracle.apply(dict(time_ns=1, kind="begin_conversion"))

    def test_undefined_window(self):
        doc = fixture()
        observation(doc)["window"] = "not_defined"
        self.reject(doc, "undefined window")

    def test_outside_declared_window(self):
        doc = fixture()
        observation(doc, "early_7")["time_ns"] = 22.8
        self.reject(doc, "time outside window")

    def test_window_includes_transition(self):
        doc = fixture()
        next(w for w in doc["windows"] if w["name"] == "early_7")["start_ns"] = 22
        self.reject(doc, "window includes a target transition")

    def test_nonfinite_analog_and_time(self):
        for mode in ["analog", "time"]:
            with self.subTest(mode=mode):
                doc = fixture()
                event = observation(doc)
                if mode == "analog":
                    event["values"]["bp_v"][0] = float("nan")
                else:
                    event["time_ns"] = float("nan")
                self.reject(doc, "finite number required")

    def test_intermediate_gate_level_unknown(self):
        doc = fixture()
        observation(doc)["values"]["gates"]["gpn"][0] = .45
        self.reject(doc, "intermediate/unknown")

    def test_unknown_word_rejected(self):
        doc = fixture()
        observation(doc)["values"]["q_word"] = None
        self.reject(doc, "integer in")

    def test_missing_required_observation(self):
        doc = fixture()
        doc["events"] = [e for e in doc["events"] if e.get("window") != "late_0"]
        self.reject(doc, "unobserved required windows")

    def test_omitting_a_window_definition_cannot_hide_missing_coverage(self):
        doc = fixture()
        doc["windows"] = [w for w in doc["windows"] if w["name"] != "late_0"]
        doc["events"] = [e for e in doc["events"] if e.get("window") != "late_0"]
        self.reject(doc, "both capture stages for all eight bits")

    def test_incomplete_trace(self):
        doc = fixture()
        doc["events"].pop()
        self.reject(doc, "incomplete conversion")

    def test_all_sixteen_captures_but_wrong_phase_is_not_count_pass(self):
        doc = fixture()
        next(e for e in doc["events"] if e["time_ns"] == 24)["time_ns"] = 22.8
        doc["events"].sort(key=lambda e: e["time_ns"])
        self.assertEqual(sum(e["kind"] == "capture" for e in doc["events"]), 16)
        self.reject(doc, "capture: duplicate")

    def test_analog_mapping_checked_without_optional_d_code_gates(self):
        doc = fixture()
        for event in doc["events"]:
            if event["kind"] == "observe":
                for key in ["d_word", "code_word", "gates"]:
                    event["values"].pop(key, None)
        self.assertTrue(validate_document(doc)["contract_checks_passed"])
        observation(doc)["values"]["bn_v"][7] = 0.
        self.reject(doc, "incorrect rail")

    def test_early_analog_unsettled_logic_correct_late_settled(self):
        doc = fixture()
        # Intermediate D is correctly stored while capacitors are still moving.
        # Late CODE has reached its target in the separately required window.
        for event in doc["events"]:
            if event.get("window", "").startswith("early_"):
                event["values"]["bp_v"] = [.3] * 8
                event["values"]["bn_v"] = [.6] * 8
        result = validate_document(doc)
        self.assertTrue(result["contract_checks_passed"])
        early = [row for row in result["check_details"] if row["window"].startswith("early_")]
        self.assertTrue(all(row["logic_checked"] and not row["analog_checked"] for row in early))

    def test_late_unsettled_is_rejected(self):
        doc = fixture()
        observation(doc, "late_7")["values"]["bp_v"][0] = .3
        self.reject(doc, "incorrect rail / settling error")

    def test_early_wrong_word_rejected_with_no_analog_fields(self):
        doc = fixture()
        observation(doc, "early_7")["values"] = dict(q_word=192)
        self.reject(doc, "incorrect independent command state")

    def test_early_logic_only_can_omit_analog_measurements(self):
        doc = fixture()
        for event in doc["events"]:
            if event.get("window", "").startswith("early_"):
                event["values"] = dict(q_word=event["values"]["q_word"])
        self.assertTrue(validate_document(doc)["contract_checks_passed"])

    def test_deleting_analog_check_does_not_change_independent_contract(self):
        doc = fixture()
        window = next(w for w in doc["windows"] if w["name"] == "late_7")
        window.update(checks=["logic"], analog_requirement=None)
        self.reject(doc, "independent analog contract requirements missing")

    def test_window_cannot_shrink_required_analog_interval(self):
        doc = fixture()
        next(w for w in doc["windows"] if w["name"] == "late_7")["start_ns"] += .1
        self.reject(doc, "interval differs from independent contract")

    def test_undefined_budget_or_contract_is_rejected(self):
        for value in [None, float("nan")]:
            with self.subTest(value=value):
                contract = fixture_contract()
                contract["analog_requirements"][0]["tolerance_v"] = value
                with self.assertRaisesRegex(ContractError, "finite number required"):
                    check_document(fixture(), contract)
        with self.assertRaisesRegex(ContractError, "independent contract"):
            check_document(fixture())

    def test_logic_window_requires_observed_q(self):
        doc = fixture()
        observation(doc, "early_7")["values"].pop("q_word")
        self.reject(doc, "independent Q-word comparison required")


if __name__ == "__main__":
    unittest.main()
