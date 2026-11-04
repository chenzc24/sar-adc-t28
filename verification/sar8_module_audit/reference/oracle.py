"""Command-derived SAR8 reference oracle; no simulator or waveform dependencies.

Observed gates, Q, D and CODE are comparison inputs only. They never set expected
state. CLI input is described in README.md; output is a local contract check,
not a circuit qualification. All times and analog tolerances must be supplied.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path


class ContractError(ValueError):
    """Malformed, unknown, out-of-order or mismatched evidence."""


def number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ContractError(f"{label}: finite number required")
    return float(value)


def integer(value, label, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ContractError(f"{label}: integer in [{low}, {high}] required")
    return value


@dataclass(frozen=True)
class Window:
    name: str
    start_ns: float
    end_ns: float
    stage: str
    bit: int | None
    checks: frozenset
    analog_requirement: str | None


class ReferenceOracle:
    def __init__(self, config, windows, contract=None):
        if not isinstance(config, dict) or set(config) != {"vrefp_v", "vrefn_v", "vdd_v",
                           "logic_low_max_v", "logic_high_min_v"}:
            raise ContractError("config: explicit rails and logic limits required")
        self.config = {key: number(value, key) for key, value in config.items()}
        c = self.config
        if not (c["vrefp_v"] > c["vrefn_v"] and c["vdd_v"] > 0
                and 0 <= c["logic_low_max_v"] < c["logic_high_min_v"] <= c["vdd_v"]):
            raise ContractError("config: invalid rail/tolerance/logic limits")
        self.analog_requirements = self._contract(contract)
        self.contract_id = contract["contract_id"]
        self.windows = {}
        if not isinstance(windows, list):
            raise ContractError("windows: list required")
        for item in windows:
            if not isinstance(item, dict) or set(item) != {"name", "start_ns", "end_ns", "stage", "bit",
                                                          "checks", "analog_requirement"}:
                raise ContractError("window: all schema fields required")
            start = number(item["start_ns"], "start_ns")
            end = number(item["end_ns"], "end_ns")
            stage = item["stage"]
            bit = item["bit"]
            if not isinstance(stage, str) or stage not in {"reset", "early", "late"} or start < 0 or end < start:
                raise ContractError("window: invalid stage or interval")
            if stage == "reset":
                if bit is not None:
                    raise ContractError("reset window: bit must be null")
            else:
                integer(bit, "window bit", 0, 7)
            name = item["name"]
            if not isinstance(name, str) or not name or name in self.windows:
                raise ContractError("window: unique nonempty name required")
            checks = item["checks"]
            if (not isinstance(checks, list) or not checks or any(not isinstance(x, str) for x in checks)
                    or len(checks) != len(set(checks)) or not set(checks) <= {"logic", "analog"}):
                raise ContractError("window: explicit logic/analog checks required")
            requirement = item["analog_requirement"]
            if "analog" in checks:
                if not isinstance(requirement, str) or requirement not in self.analog_requirements:
                    raise ContractError("window: undefined analog contract requirement")
                req = self.analog_requirements[requirement]
                if (stage, bit, start, end) != (req["stage"], req["bit"], req["start_ns"], req["end_ns"]):
                    raise ContractError("window: analog stage/bit/interval differs from independent contract")
            elif requirement is not None:
                raise ContractError("logic-only window: analog_requirement must be null")
            self.windows[name] = Window(name, start, end, stage, bit, frozenset(checks), requirement)
        self.q = [None] * 8
        self.reset = [False] * 8
        self.d = None
        self.token = None
        self.bit = None
        self.phase = "initial"
        self.stage = None
        self.captured_bit = None
        self.last_transition_ns = -math.inf
        self.last_time_ns = -math.inf
        self.decisions = 0
        self.captures = 0
        self.observations = []

    @staticmethod
    def _contract(contract):
        if (not isinstance(contract, dict) or set(contract) != {"schema_version", "contract_id", "analog_requirements"}
                or type(contract["schema_version"]) is not int or contract["schema_version"] != 1
                or not isinstance(contract["contract_id"], str) or not contract["contract_id"]
                or not isinstance(contract["analog_requirements"], list) or not contract["analog_requirements"]):
            raise ContractError("independent contract: id and nonempty analog requirements required")
        result = {}
        for req in contract["analog_requirements"]:
            if (not isinstance(req, dict) or set(req) != {"id", "stage", "bit", "start_ns", "end_ns",
                                                        "tolerance_v", "purpose"}):
                raise ContractError("analog requirement: all schema fields required")
            name = req["id"]
            if not isinstance(name, str) or not name or name in result:
                raise ContractError("analog requirement: unique id required")
            if req["stage"] not in ["reset", "early", "late"]:
                raise ContractError("analog requirement: invalid stage")
            if req["stage"] == "reset":
                if req["bit"] is not None:
                    raise ContractError("analog requirement: reset bit must be null")
            else:
                integer(req["bit"], "analog requirement bit", 0, 7)
            start = number(req["start_ns"], "contract start_ns")
            end = number(req["end_ns"], "contract end_ns")
            tolerance = number(req["tolerance_v"], "contract tolerance_v")
            if (start < 0 or end < start or tolerance < 0
                    or not isinstance(req["purpose"], str) or not req["purpose"]):
                raise ContractError("analog requirement: explicit interval, tolerance and purpose required")
            result[name] = dict(req, start_ns=start, end_ns=end, tolerance_v=tolerance)
        return result

    def qword(self):
        if any(value is None for value in self.q):
            raise ContractError("Q: unknown state; explicit initialization required")
        return sum(value << bit for bit, value in enumerate(self.q))

    def codeword(self):
        if self.d is None or self.token is None:
            raise ContractError("D/CODE: unknown before begin_conversion")
        return self.d | (0 if self.token < 0 else 1 << self.token)

    def targets(self):
        self.qword()  # Unknown bits may not become implicit zeroes.
        hi, lo = self.config["vrefp_v"], self.config["vrefn_v"]
        return {"bp_v": [lo if q else hi for q in self.q],
                "bn_v": [hi if q else lo for q in self.q],
                "dummy_p_v": hi, "dummy_n_v": lo}

    def apply(self, event):
        if not isinstance(event, dict) or "time_ns" not in event or "kind" not in event:
            raise ContractError("event: explicit time_ns and kind required")
        time = number(event["time_ns"], "time_ns")
        if time < 0 or time <= self.last_time_ns:
            raise ContractError("events: strictly increasing nonnegative times required")
        self.last_time_ns = time
        kind = event["kind"]
        if not isinstance(kind, str):
            raise ContractError("kind: string required")
        fields = {"reset_assert": {"bit"}, "reset_release": {"bit"},
                  "begin_conversion": set(), "decision": {"bit", "value"},
                  "update_rise": {"bit"}, "update_fall": set(), "capture": set(),
                  "observe": {"window", "values"}, "end_conversion": set()}
        if kind not in fields or set(event) != {"time_ns", "kind"} | fields[kind]:
            raise ContractError("event: unknown kind or unexpected/missing fields")
        if kind in {"reset_assert", "reset_release"}:
            bit = integer(event["bit"], "reset bit", 0, 7)
            asserted = kind == "reset_assert"
            if self.reset[bit] == asserted:
                raise ContractError("reset: repeated assertion or release without assertion")
            self.reset[bit] = asserted
            if asserted:
                self.q[bit] = int(bit == 7)
                self.stage, self.captured_bit = "reset", None
                self.last_transition_ns = time
        elif kind == "begin_conversion":
            if self.phase != "initial" or any(self.reset) or self.qword() != 128:
                raise ContractError("begin_conversion: released initialized preset 128 required")
            self.d, self.token, self.bit, self.phase = 0, 7, 7, "ready"
            self.stage = None
        elif kind == "decision":
            bit = integer(event["bit"], "decision bit", 0, 7)
            value = integer(event["value"], "decision value", 0, 1)
            if self.phase != "ready" or bit != self.bit:
                raise ContractError("decision: descending bit order / preceding two captures required")
            self.d = (self.d & ~(1 << bit)) | (value << bit)
            self.decisions += 1
            self.phase, self.stage = "decided", None
        elif kind == "update_rise":
            bit = integer(event["bit"], "update bit", 0, 7)
            if self.phase != "decided" or bit != self.bit:
                raise ContractError("update_rise: corresponding decision required")
            self.token = bit - 1
            self.phase, self.stage = "early_wait", None
        elif kind == "capture":
            if self.phase not in {"early_wait", "late_wait"}:
                raise ContractError("capture: duplicate, unordered or outside update phases")
            early = self.phase == "early_wait"
            word = self.d if early else self.codeword()
            for bit in range(8):
                self.q[bit] = int(bit == 7) if self.reset[bit] else (word >> bit) & 1
            self.stage = "early" if early else "late"
            self.captured_bit = self.bit
            self.last_transition_ns = time
            self.captures += 1
            if early:
                self.phase = "early_captured"
            else:
                self.bit -= 1
                self.phase = "ready" if self.bit >= 0 else "all_captured"
        elif kind == "update_fall":
            if self.phase != "early_captured":
                raise ContractError("update_fall: missing early capture")
            self.phase = "late_wait"
        elif kind == "observe":
            self._observe(event, time)
        elif kind == "end_conversion":
            if (self.phase != "all_captured" or self.decisions != 8 or self.captures != 16
                    or any(self.reset)):
                raise ContractError("end_conversion: eight decisions / sixteen captures / released resets required")
            self.phase = "complete"

    def _observe(self, event, time):
        if not isinstance(event["window"], str):
            raise ContractError("observation: window name required")
        window = self.windows.get(event["window"])
        if window is None or not window.start_ns <= time <= window.end_ns:
            raise ContractError("observation: undefined window or time outside window")
        if (window.stage != self.stage or window.bit != self.captured_bit
                or window.start_ns <= self.last_transition_ns):
            raise ContractError("observation: wrong stage/bit or window includes a target transition")
        expected = self.targets()
        values = event["values"]
        analog_keys = set(expected)
        allowed = analog_keys | {"q_word", "d_word", "code_word", "gates"}
        if not isinstance(values, dict) or not set(values) <= allowed:
            raise ContractError("observation: unknown measured field")
        analog = "analog" in window.checks
        logic = "logic" in window.checks
        if analog and not analog_keys <= set(values):
            raise ContractError("analog observation: all bottom and dummy measurements required")
        if logic and "q_word" not in values:
            raise ContractError("logic observation: independent Q-word comparison required")
        tolerance = self.analog_requirements[window.analog_requirement]["tolerance_v"] if analog else None
        for side in ["bp_v", "bn_v"]:
            if side not in values:
                continue
            if not isinstance(values[side], list) or len(values[side]) != 8:
                raise ContractError(f"{side}: bit0-first eight-value list required")
            for bit, (actual, target) in enumerate(zip(values[side], expected[side])):
                actual = number(actual, side)
                if analog and abs(actual - target) > tolerance:
                    raise ContractError(f"{side}[{bit}]: incorrect rail / settling error")
        for key in ["dummy_p_v", "dummy_n_v"]:
            if key not in values:
                continue
            actual = number(values[key], key)
            if analog and abs(actual - expected[key]) > tolerance:
                raise ContractError(f"{key}: incorrect dummy/reference voltage")
        for key, expected_value in [("q_word", self.qword), ("d_word", lambda: self.d),
                                    ("code_word", self.codeword)]:
            if key in values:
                target = expected_value()
                if target is None:
                    raise ContractError(f"{key}: unknown expected state")
                if integer(values[key], key, 0, 255) != target:
                    raise ContractError(f"{key}: incorrect independent command state")
        if "gates" in values:
            gates = values["gates"]
            if not isinstance(gates, dict) or set(gates) != {"gpn", "gpp", "gnn", "gnp"}:
                raise ContractError("gates: gpn/gpp/gnn/gnp required")
            for name, samples in gates.items():
                if not isinstance(samples, list) or len(samples) != 8:
                    raise ContractError("gates: bit0-first eight-value lists required")
                for bit, voltage in enumerate(samples):
                    voltage = number(voltage, name)
                    level = 0 if voltage <= self.config["logic_low_max_v"] else (
                        1 if voltage >= self.config["logic_high_min_v"] else None)
                    if level is None:
                        raise ContractError("gates: intermediate/unknown logic level")
                    target = self.q[bit] if name in {"gpn", "gpp"} else 1 - self.q[bit]
                    if level != target:
                        raise ContractError(f"gates {name}[{bit}]: incorrect mapping")
        self.observations.append(dict(window=window.name, logic_checked=logic, analog_checked=analog,
                                      analog_requirement=window.analog_requirement))

    def finish(self):
        if self.phase != "complete":
            raise ContractError("trace: incomplete conversion / missing capture or end_conversion")
        observed_names = {row["window"] for row in self.observations}
        missing = set(self.windows) - observed_names
        if not self.windows or missing or not self.observations:
            raise ContractError(f"trace: unobserved required windows: {sorted(missing)}")
        coverage = {(self.windows[row["window"]].stage, self.windows[row["window"]].bit)
                    for row in self.observations if row["logic_checked"]}
        required = {("reset", None)} | {(stage, bit) for stage in ["early", "late"] for bit in range(8)}
        if not required <= coverage:
            raise ContractError("trace: reset and both capture stages for all eight bits require logic observations")
        observed_analog = {row["analog_requirement"] for row in self.observations if row["analog_checked"]}
        missing_analog = set(self.analog_requirements) - observed_analog
        if missing_analog:
            raise ContractError(f"trace: independent analog contract requirements missing: {sorted(missing_analog)}")
        return {"contract_checks_passed": True, "decisions": self.decisions,
                "contract_id": self.contract_id,
                "captures": self.captures, "observations": len(self.observations),
                "observed_capture_stages": 16, "observed_reset_stage": True,
                "analog_requirements_checked": sorted(observed_analog),
                "check_details": self.observations,
                "scope": "supplied local contract samples only; no ADC qualification"}


def validate_document(document, contract=None):
    if (not isinstance(document, dict) or set(document) != {"schema_version", "config", "windows", "events"}
            or type(document["schema_version"]) is not int or document["schema_version"] != 1
            or not isinstance(document["events"], list) or not isinstance(document["windows"], list)):
        raise ContractError("document: schema_version=1, config, windows and events required")
    oracle = ReferenceOracle(document["config"], document["windows"], contract)
    for index, event in enumerate(document["events"]):
        try:
            oracle.apply(event)
        except ContractError as exc:
            raise ContractError(f"event {index}: {exc}") from exc
    return oracle.finish()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_json", type=Path)
    parser.add_argument("--contract", type=Path, required=True,
                        help="independently reviewed required analog checks; separate from observed trace")
    args = parser.parse_args()
    try:
        if args.input_json.stat().st_size > 1024 * 1024 or args.contract.stat().st_size > 1024 * 1024:
            raise ContractError("input: 1 MiB bounded local fixture limit")
        print(json.dumps(validate_document(json.loads(args.input_json.read_text(encoding="utf-8")),
                                           json.loads(args.contract.read_text(encoding="utf-8"))), indent=2))
    except (ContractError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"contract_checks_passed": False, "reason": str(exc)}, indent=2))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
