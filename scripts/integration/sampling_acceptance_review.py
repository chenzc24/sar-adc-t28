"""Review committed sine samples only; never imports or launches a simulator."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/sampling_acceptance.yaml"
RESULT = ROOT / "verification/integration/sampling_acceptance_review.json"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fit(ns, values, frequency):
    omega = 2 * np.pi * frequency * 1e-9
    theta = (ns - 400) * omega
    basis = np.column_stack((np.ones_like(ns), np.sin(theta), np.cos(theta)))
    coefficients, _, rank, _ = np.linalg.lstsq(basis, values, rcond=None)
    assert rank == 3
    remainder = values - basis @ coefficients
    assert max(abs(basis.T @ remainder)) < 1e-10
    return coefficients, remainder


def stats(values, q):
    return dict(peak_lsb=float(max(abs(values)) / q),
                rms_lsb=float(np.sqrt(np.mean(values**2)) / q))


def measure(ns, source, held, frequency, common_lag_ns, q):
    sc, source_remainder = fit(ns, source, frequency)
    hc, remainder = fit(ns, held, frequency)
    gain = np.hypot(*hc[1:]) / np.hypot(*sc[1:])
    omega = 2 * np.pi * frequency * 1e-9
    phase = np.angle(np.exp(1j * (np.arctan2(hc[2], hc[1]) - np.arctan2(sc[2], sc[1]))))
    lag_ns = -phase / omega
    dc = hc[0] - gain * sc[0]

    def delayed(delay):
        theta = (ns - 400 - delay) * omega
        return sc[0] + sc[1] * np.sin(theta) + sc[2] * np.cos(theta)

    fitted_source = delayed(0)
    phase_term = delayed(lag_ns) - fitted_source
    gain_term = (gain - 1) * delayed(lag_ns)
    assert max(abs(phase_term + gain_term + dc + remainder - source_remainder - (held - source))) < 1e-12
    joint = held - delayed(common_lag_ns)
    return dict(equivalent_lag_ns=float(lag_ns), gain=float(gain),
                gain_error_percent=float((gain - 1) * 100), offset_uv=float(dc * 1e6),
                gain_endpoint_error_lsb=float(abs(gain - 1) * .9 / q),
                nonfundamental=stats(remainder, q), raw=stats(held - source, q),
                per_frequency_phase_only=stats(held - delayed(lag_ns), q),
                common_delay_phase_only=stats(joint, q))


def self_check():
    q = 1.8 / 256
    ns = 441.05 + 100 * np.arange(20)
    for frequency in (500000, 4500000):
        theta = (ns - 400) * 2 * np.pi * frequency * 1e-9
        source = .8 * np.sin(theta)
        distortion = 13e-6 * np.sin(3 * theta) + 9e-6 * np.cos(2 * theta)
        held = 123e-6 + .9997 * .8 * np.sin(theta - 1.73 * 2 * np.pi * frequency * 1e-9) + distortion
        m = measure(ns, source, held, frequency, 1.73, q)
        assert abs(m["gain"] - .9997) < 1e-12
        assert abs(m["equivalent_lag_ns"] - 1.73) < 1e-9
        assert abs(m["offset_uv"] - 123) < 1e-6
        assert abs(m["nonfundamental"]["rms_lsb"] - np.sqrt(np.mean(distortion**2)) / q) < 1e-12
        pure = measure(ns, source, .8 * np.sin(theta - 1.73 * 2 * np.pi * frequency * 1e-9), frequency, 1.73, q)
        assert pure["common_delay_phase_only"]["peak_lsb"] < 1e-10
        bad_gain = measure(ns, source, .997 * source, frequency, 0, q)
        bad_offset = measure(ns, source, source + .003, frequency, 0, q)
        assert bad_gain["gain_endpoint_error_lsb"] > .25
        assert bad_offset["common_delay_phase_only"]["peak_lsb"] > .25
        assert bad_offset["nonfundamental"]["peak_lsb"] < 1e-10
    print("SAMPLING_ACCEPTANCE_SYNTHETIC_RECOVERY_AND_RETAINED_GAIN_DC_PASS")


def review():
    policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
    spec_path = ROOT / policy["system_spec"]
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    assert spec["converter"]["resolution_bits"] == policy["resolution_bits"] == 8
    assert spec["converter"]["sample_rate_hz"] == policy["sample_rate_hz"] == 10000000
    assert spec["input"]["differential_range_v"] == [-.9, .9]
    q = policy["differential_span_v"] / 2**policy["resolution_bits"]
    reserve = policy["nonfundamental"]["shared_system_distortion_rms_budget_lsb"]
    assert reserve == spec["error_budget"]["distortion_unmodeled_rms_lsb"] == .15
    assert policy["equivalent_delay"]["jitter_budget_rms_ps"] == spec["error_budget"]["clock_jitter_rms_ps"]
    inputs = [(s, read(ROOT / s["path"])) for s in policy["sources"]]
    assert [s["input_frequency_hz"] for s, _ in inputs] == [500000, 4500000]
    reference_cases = {c["width_multiplier"]: c for c in inputs[0][1]["cases"]}
    records = []
    source_hashes = {s["path"]: digest(ROOT / s["path"]) for s, _ in inputs}
    for source_info, result in inputs:
        frequency = source_info["input_frequency_hz"]
        assert result["no_OA_adoption"] and not result["qualified_full_ADC"]
        assert [c["width_multiplier"] for c in result["cases"]] == policy["width_multipliers"]
        reference_history = None
        for case in result["cases"]:
            width = case["width_multiplier"]
            assert case["native_result_ok"] and case["complete_frames"] == 24
            assert case["all24_8compare_write_update"] and case["all24_final_codes_stable"]
            assert all(count == [8] * 24 for count in case["event_counts"].values())
            assert not case["solver_parameter_differences"] and not case["has_CMI"]
            frames = case["frames"]
            assert len(frames) == 20 and [f["frame"] for f in frames] == list(range(4, 24))
            ns = np.array([f["sample_ns"] for f in frames])
            source = np.array([f["source_v"] for f in frames])
            held = np.array([f["held_v"] for f in frames])
            history = np.column_stack((ns, source))
            if reference_history is None:
                reference_history = history
            else:
                np.testing.assert_allclose(history, reference_history, rtol=0, atol=1e-7)
            expected = source_info["input_differential_peak_v"] * np.sin(2 * np.pi * frequency * ns * 1e-9 + np.deg2rad(-72))
            np.testing.assert_allclose(source, expected, rtol=0, atol=1e-7)
            common = reference_cases[width]["held_transfer"]["equivalent_lag_ns"]
            m = measure(ns, source, held, frequency, common, q)
            old = case["held_transfer"]
            assert abs(m["equivalent_lag_ns"] - old["equivalent_lag_ns"]) < 1e-9
            assert abs(m["gain"] - old["gain"]) < 1e-12
            assert abs(m["offset_uv"] - old["offset_uv"]) < 1e-6
            for field, old_field in (("nonfundamental", "held_remainder"), ("raw", "raw_held_error")):
                for key, old_key in (("peak_lsb", "peak_abs_uv"), ("rms_lsb", "rms_uv")):
                    assert abs(m[field][key] * q * 1e6 - case[old_field][old_key]) < 1e-6
            m.update(input_frequency_hz=frequency, input_differential_peak_v=source_info["input_differential_peak_v"],
                     width_multiplier=width, common_lag_ns=common,
                     common_vs_fitted_lag_difference_ps=(m["equivalent_lag_ns"] - common) * 1000,
                     gain_screen_pass=bool(m["gain_endpoint_error_lsb"] <= policy["gain"]["endpoint_error_abs_max_lsb"]),
                     joint_voltage_screen_pass=bool(m["common_delay_phase_only"]["peak_lsb"] <= policy["joint_voltage_screen"]["peak_abs_max_lsb"]),
                     nonfundamental_rms_fraction_of_shared_budget=m["nonfundamental"]["rms_lsb"] / reserve,
                     independent_sampling_nonlinearity_allocation_pass=None,
                     historical_raw_gate_pass=case["measured_held_within_original_budget"],
                     historical_raw_gate_exceedance_count=case["original_budget_exceedance_count"],
                     turnoff_nonfundamental_peak_uv=case["turnoff_remainder"]["peak_abs_uv"],
                     turnoff_total_peak_uv=case["turnoff_increment"]["peak_abs_uv"],
                     native_event_timing_pass=True, has_LTE_relaxation=case["has_LTE_relaxation"],
                     numerical_warning_events=case["numerical_warning_events"])
            records.append(m)
    eligible = [w for w in policy["width_multipliers"] if all(
        c["gain_screen_pass"] and c["joint_voltage_screen_pass"] and c["nonfundamental_rms_fraction_of_shared_budget"] < 1
        for c in records if c["width_multiplier"] == w)]
    assert all(digest(ROOT / p) == h for p, h in source_hashes.items())
    return dict(policy_path=str(POLICY.relative_to(ROOT)).replace("\\", "/"), policy_sha256=digest(POLICY),
                system_spec_sha256=digest(spec_path), system_spec=spec, source_sha256=source_hashes,
                analysis_source_LF_sha256=hashlib.sha256(Path(__file__).read_text(encoding="utf-8").encode()).hexdigest(),
                LSB_v=q, cases=records, nominal_screen_eligible_widths=eligible,
                recommended_nominal_width_multiplier=min(eligible) if eligible else None,
                two_x_required_by_existing_nominal_evidence=False if 1 in eligible else None,
                no_new_simulation=True, no_OA_change=True, no_gain_or_DC_calibration=True,
                broadband_constant_delay_proven=False, qualified_full_ADC=False,
                qualification_scope="Two nominal sine points only; shared distortion reserve is not a sampling-only budget.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    self_check()
    result = review()
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.write:
        RESULT.write_text(encoded, encoding="utf-8")
    if args.check:
        assert read(RESULT) == result
    for case in result["cases"]:
        print("SAVED_CASE", case["input_frequency_hz"], case["width_multiplier"],
              "gain_endpoint_LSB", case["gain_endpoint_error_lsb"],
              "common_delay_peak_LSB", case["common_delay_phase_only"]["peak_lsb"],
              "nonfund_RMS_LSB", case["nonfundamental"]["rms_lsb"])
    print("RECOMMENDED_NOMINAL_WIDTH", result["recommended_nominal_width_multiplier"],
          "FULL_ADC_QUALIFIED", result["qualified_full_ADC"])
