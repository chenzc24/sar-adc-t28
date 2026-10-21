"""Offline short-run code/timing/stress/energy checks, no simulator launch."""
from __future__ import annotations
import argparse
import itertools
from pathlib import Path
import pickle
import re
import shutil

import numpy as np

import b_short_acceptance as run
from r3_anomaly_analyze import edges, monitor, reported_parameters
from r3_refgate_analyze import state_rows

ROOT, OUT, Q = run.ROOT, run.OUT, run.Q


def integral(t_ns, values, start_ns, end_ns):
    assert t_ns[0] <= start_ns < end_ns <= t_ns[-1] + 1e-6
    mask = (t_ns > start_ns) & (t_ns < end_ns)
    x = np.r_[start_ns, t_ns[mask], end_ns]
    y = np.r_[np.interp(start_ns, t_ns, values), values[mask], np.interp(end_ns, t_ns, values)]
    return float(np.trapezoid(y, x))


def energy(t, power_w, start, end):
    net = integral(t, power_w, start, end) * 1000
    positive = integral(t, np.maximum(power_w, 0), start, end) * 1000
    negative = integral(t, np.maximum(-power_w, 0), start, end) * 1000
    assert abs(net - positive + negative) < 1e-8
    return dict(net_delivered_pj=net, positive_delivered_pj=positive,
                recovered_pj=negative, average_net_mw=net / (end - start))


def self_check():
    t = np.array([0., 20., 50., 70., 100.])
    e = energy(t, np.full_like(t, .001), 0, 100)
    assert abs(e["net_delivered_pj"] - 100) < 1e-12
    assert abs(e["average_net_mw"] - 1) < 1e-12
    assert abs(sum(integral(t, np.full_like(t, .001), a, b) for a, b in ((0, 40), (40, 98), (98, 100))) - .1) < 1e-12
    e = energy(t, np.array([-.001, -.001, 0, .001, .001]), 0, 100)
    assert e["positive_delivered_pj"] > 0 and e["recovered_pj"] > 0
    assert abs(energy(t, -np.full_like(t, .9) * -.001, 0, 100)["average_net_mw"] - .9) < 1e-12
    print("POWER_POLARITY_PJ_MW_WINDOW_PARTITION_SELF_CHECK_PASS")


def analyze_case(name, make_figures=True):
    run.check()
    ctx = run.read(OUT / "context.json")
    cfg = ctx["cases"][name]
    folder = OUT / name
    result = run.read(folder / "result.json")
    receipt = run.read(folder / "waveform_receipt.json")
    assert result["ok"] and receipt["sha256"] == run.sha(folder / "waveform.pickle")
    with (folder / "waveform.pickle").open("rb") as stream:
        w = {k: np.asarray(v) for k, v in pickle.load(stream).items()}
    t = w["time"] * 1e9
    assert t[0] == 0 and abs(t[-1] - cfg["actual_stop_ns"]) < 1e-6
    assert np.all(np.diff(t) > 0) and all(np.isfinite(v).all() for v in w.values())
    log_path = folder / "spectre/spectre.out"
    log = log_path.read_text(errors="replace")
    rows = monitor(log)
    assert len(rows) == cfg["frames"] and [r["frame"] for r in rows] == list(range(cfg["frames"]))
    baseline_params = run.read(ROOT / "verification/integration/b_sine_period_results.json")["reported_solver_parameters"]
    params = reported_parameters(log)
    differences = {k: dict(baseline=v, actual=params.get(k)) for k, v in baseline_params.items() if params.get(k) != v}
    assert not differences, differences
    node = lambda n: np.zeros_like(t) if n == "0" else w[n.lower()]
    at = lambda n, ns: np.interp(ns, t, node(n))
    word = lambda ns: sum((at(f"D{b}", ns) > .45).astype(int) * (1 << b) for b in range(8))
    token = lambda ns: sum((at(f"XDUT.XCTRL.T{b}", ns) > .45).astype(int) * (1 << b) for b in range(8))
    sample_falls = edges(t, w["sample"], rising=False)
    assert len(sample_falls) == cfg["frames"]
    np.testing.assert_allclose(sample_falls, 41.05 + 100 * np.arange(cfg["frames"]), rtol=0, atol=1e-5)
    event_times = {n: edges(t, w[n]) for n in ("cmp_clk", "xdut.xctrl.phi_w", "xdut.xctrl.phi_u")}
    frame_rows = []
    for f, measurement in enumerate(rows):
        h = sample_falls[f]
        source = float(at("VINP_SRC", h) - at("VINN_SRC", h))
        assert abs(source - cfg["input_values_v"][f]) < 1e-9
        assert abs(float(at("VINP_SRC", h) + at("VINN_SRC", h)) - .9) < 1e-9
        held = float(at("TOPP", h + .6) - at("TOPN", h + .6))
        groups = {k: v[(v >= f * 100) & (v < (f + 1) * 100)] for k, v in event_times.items()}
        comparisons = []
        for i, c in enumerate(groups["cmp_clk"]):
            before = float(c - .02)
            active_token = int(token(before))
            trial = int(word(before)) | active_token
            expected = source + .9 - trial * Q
            actual = float(at("TOPP", before) - at("TOPN", before))
            comparisons.append(dict(index=i, compare_ns=float(c), token=active_token,
                expected_token=128 >> i if i < 8 else None, trial_word=trial,
                ideal_residual_v=expected, actual_residual_v=actual, settling_error_lsb=(actual - expected) / Q))
        bad_midpoint, bottom_errors = {}, []
        check_ns = h - .1
        for s in "PN":
            for b in range(8):
                high = (s == "P" and b < 7) or (s == "N" and b == 7)
                expected_gate = .9 * (1 - high)
                for polarity in "PN":
                    key = f"XDUT.G{s}{polarity}{b}"
                    value = float(at(key, check_ns))
                    if abs(value - expected_gate) > .09:
                        bad_midpoint[key] = value
                rail = "VREFP" if high else "VREFN"
                bottom_errors.append(float(at(f"XDUT.XCDAC.B{s}{b}", check_ns) - at(rail, check_ns)))
        ideal_code = lambda value: int(np.clip(np.floor((value + .9) / Q), 0, 255))
        code = measurement["code"]
        count_ok = all(len(v) == 8 for v in groups.values())
        cs, ws, us = (groups[k] for k in ("cmp_clk", "xdut.xctrl.phi_w", "xdut.xctrl.phi_u"))
        event_order = bool(count_ok and np.all(cs < ws) and np.all(ws < us)
                           and np.all(us[:-1] < cs[1:]) and cs[0] > h)
        rail_error = max(min(abs(float(at(f"D{b}", ns))), abs(float(at(f"D{b}", ns)) - .9))
                         for ns in (f * 100 + 90, f * 100 + 98) for b in range(8))
        completion = float(groups["xdut.xctrl.phi_u"][-1] - h) if len(groups["xdut.xctrl.phi_u"]) else None
        frame_rows.append(dict(frame=f, observed=f >= cfg["warmup_frames"], sample_ns=float(h),
            source_v=source, held_v=held, held_error_lsb=(held - source) / Q,
            held_error_mv=(held - source) * 1000, code=code, ideal_source_code=ideal_code(source),
            ideal_held_code=ideal_code(held), code_error_vs_source=code - ideal_code(source),
            code_error_vs_held=code - ideal_code(held), monitor_valid=measurement["valid"],
            output_90_98_stable=measurement["early"] == code == int(word(f * 100 + 98)),
            output_90_98_max_rail_error_v=rail_error, output_rail_pass=rail_error < .09,
            compare_write_update_counts={k: len(v) for k, v in groups.items()}, event_counts_pass=count_ok,
            event_order_pass=event_order,
            events_ns={k: list(map(float, v)) for k, v in groups.items()},
            bit_order_pass=len(comparisons) == 8 and all(r["token"] == r["expected_token"] for r in comparisons),
            completion_after_hold_ns=completion, conversion_budget_pass=completion is not None and completion < 60,
            held_read_precedes_first_compare=bool(len(groups["cmp_clk"]) and h + .6 < groups["cmp_clk"][0]),
            midpoint_gate_failures=bad_midpoint, midpoint_bottom_max_error_lsb=max(map(abs, bottom_errors)) / Q,
            midpoint_pass=not bad_midpoint and max(map(abs, bottom_errors)) < .25 * Q,
            comparisons=comparisons,
            pre_compare_settling_max_error_lsb=max([abs(r["settling_error_lsb"]) for r in comparisons], default=0)))
    stress = []
    for device in ctx["analog_devices"]:
        terminals = dict(zip("DGSB", device["nodes"]))
        limit = ctx["config"]["io_terminal_engineering_screen_v" if device["category"] == "bootstrap_io" else "core_terminal_screen_v"]
        pairs = []
        for a, b in itertools.combinations("DGSB", 2):
            values = node(terminals[a]) - node(terminals[b])
            j = int(np.argmax(abs(values)))
            pairs.append(dict(terminal_pair=f"V{a}{b}", max_abs_v=float(abs(values[j])),
                signed_v=float(values[j]), time_ns=float(t[j])))
        worst = max(pairs, key=lambda r: r["max_abs_v"])
        stress.append(dict(**device, screen_v=limit, worst=worst, all_terminal_pairs=pairs,
            screen_pass=worst["max_abs_v"] <= limit))

    current_map, missing = {}, []
    def current(instance, pin, index):
        for key in (f"{instance}:{pin}", f"{instance}:{index}"):
            key = key.lower()
            if key in w:
                current_map[f"{instance}:{pin}"] = key
                return w[key]
        missing.append(f"{instance}:{pin}")
        return None
    powers, current_stats = {}, {}
    def add_power(group, instance, pin, index, voltage_node):
        values = current(instance, pin, index)
        if values is None:
            return
        delivered = -node(voltage_node) * values
        powers[group] = powers.get(group, np.zeros_like(t)) + delivered
        current_stats[f"{instance}:{pin}"] = dict(peak_abs_a=float(np.max(abs(values))),
            warm_mean_a=integral(t, values, cfg["warmup_frames"] * 100, cfg["actual_stop_ns"]) /
            (cfg["actual_stop_ns"] - cfg["warmup_frames"] * 100))
    for group, instance, voltage in (("VDD", "VVDD", "VDD!"), ("reference", "VREFHIGH", "VREFP_SRC"),
        ("reference", "VREFLOW", "VREFN_SRC"), ("SAMPLE_ideal_clock", "VSAMPLE", "SAMPLE")):
        add_power(group, instance, "p", 1, voltage)
    for side in "PN":
        add_power("input_sources", "XSTIM" if name == "history12" else "VVIN" + side,
                  "V" + side if name == "history12" else "p", (1 if side == "P" else 2) if name == "history12" else 1,
                  "VIN" + side + "_SRC")
        for bit in range(8):
            for pin, index, net in (("GP", 6, f"XDUT.G{side}P{bit}"), ("GN", 7, f"XDUT.G{side}N{bit}")):
                add_power("reference_gate_ideal_outputs", f"XDUT.XG{side}{bit}", pin, index, net)
    power_rows = {}
    for group, values in powers.items():
        frames = []
        for f in range(cfg["frames"]):
            start, end = f * 100, (f + 1) * 100
            rise, fall = start + 1.05, float(sample_falls[f])
            full = energy(t, values, start, end)
            acquisition = energy(t, values, rise, fall)
            conversion = energy(t, values, fall, start + 98)
            other = full["net_delivered_pj"] - acquisition["net_delivered_pj"] - conversion["net_delivered_pj"]
            frames.append(dict(frame=f, **full, acquisition_net_pj=acquisition["net_delivered_pj"],
                conversion_net_pj=conversion["net_delivered_pj"], other_net_pj=other))
        power_rows[group] = dict(startup_first_frame=energy(t, values, 0, 100),
            warmup=energy(t, values, 0, cfg["warmup_frames"] * 100),
            observed=energy(t, values, cfg["warmup_frames"] * 100, cfg["actual_stop_ns"]), frames=frames)
    phase_events, restore_events = state_rows(log, "R3PHASE"), state_rows(log, "R3RESTORE")
    overlap_banks = []
    for s in "PN":
        for b in range(8):
            gp, gn = node(f"XDUT.G{s}P{b}"), node(f"XDUT.G{s}N{b}")
            overlap = np.flatnonzero((gp < .45) & (gn > .45))
            if len(overlap):
                overlap_banks.append(dict(bank=f"{s}{b}", first_ns=float(t[overlap[0]]),
                    last_ns=float(t[overlap[-1]]), samples=len(overlap)))
    expected_B = run.read(ROOT / "output/r3_refgate_events/b3/analysis.json")
    observed_rows = [r for r in frame_rows if r["observed"]]
    failures = dict(
        invalid_frames=[r["frame"] for r in frame_rows if not r["monitor_valid"] or not r["output_90_98_stable"] or not r["output_rail_pass"]],
        event_count_frames=[r["frame"] for r in frame_rows if not r["event_counts_pass"] or not r["bit_order_pass"] or not r["event_order_pass"]],
        held_measurement_after_compare=[r["frame"] for r in frame_rows if not r["held_read_precedes_first_compare"]],
        late_frames=[r["frame"] for r in frame_rows if not r["conversion_budget_pass"]],
        midpoint_frames=[r["frame"] for r in frame_rows if not r["midpoint_pass"]],
        gross_code_frames=[r["frame"] for r in observed_rows if abs(r["code_error_vs_held"]) > 1],
        source_code_outliers=[r["frame"] for r in observed_rows if abs(r["code_error_vs_source"]) > 1],
        held_voltage_frames=[r["frame"] for r in observed_rows if abs(r["held_error_lsb"]) > .25],
        precompare_settling_frames=[r["frame"] for r in observed_rows if r["pre_compare_settling_max_error_lsb"] > .25],
        analog_terminal_devices=[r["path"] for r in stress if not r["screen_pass"]],
        reference_command_overlap_banks=overlap_banks,
        restore_event_accounting=not (len(phase_events) == len(rows) * 32 and len(restore_events) == len(rows) * 16),
        CMI="CMI-2754" in log, LTE="SPECTRE-16780" in log)
    gmin_notice = re.search(r'(GminDC = [^\n]+)\n\s+dV\(([^)]+)\) = ([^\n]+)', log)
    summary = dict(case=name, native_result_ok=result["ok"], complete_frames=len(rows),
        all_codes=[r["code"] for r in frame_rows], same_history_B_codes=(
            [r["code"] for r in frame_rows] == expected_B["codes"]) if name == "history12" else None,
        frame9_code=frame_rows[8]["code"] if name == "history12" else None,
        frames=frame_rows, failures=failures, functional_voltage_stress_screen_pass=not any(failures.values()),
        max_observed_held_error_lsb=max(abs(r["held_error_lsb"]) for r in observed_rows),
        max_precompare_settling_error_lsb=max(r["pre_compare_settling_max_error_lsb"] for r in observed_rows),
        stress=stress, analog_MOS_covered=len(stress), logic_all_terminal_coverage=False,
        power=power_rows, current_trace_map=current_map, missing_current_traces=missing, current_stats=current_stats,
        full_real_driver_power_qualified=False, power_is_signed_energy_supply_not_all_internal_dissipation=True,
        state_event_counts=dict(phase=len(phase_events), restore=len(restore_events)),
        all_restore_events_handled=len(phase_events) == len(rows) * 32 and len(restore_events) == len(rows) * 16,
        reported_solver_parameters=params, solver_parameter_differences=differences,
        native_warnings=[s.strip() for s in log.splitlines() if "WARNING (" in s],
        initial_DC_gmin_notice=dict(message=gmin_notice[1], node=gmin_notice[2],
                                   delta_voltage=gmin_notice[3]) if gmin_notice else None,
        initial_DC_bad_pivot_notice=next((s.strip() for s in log.splitlines() if "Bad pivoting is found during DC analysis" in s), None),
        native_footer=next((s for s in log.splitlines() if s.startswith("spectre completes with")), None),
        native_timings_s=result["metadata"].get("timings"), parse_seconds=result["parse_seconds"],
        native_log_sha256=run.sha(log_path), waveform_sha256=receipt["sha256"],
        waveform_points=receipt["points"], waveform_parser_LF_sha256=receipt["parser_LF_sha256"],
        terminal_current_PROP_metadata_excluded=receipt["terminal_current_PROP_metadata_excluded"],
        input_deck_sha256=cfg["deck_sha256"], current_data_complete=not missing,
        qualified_full_ADC=False, no_OA_changes=True)
    run.dump(folder / "analysis.json", summary)
    if make_figures:
        plot(name, t, w, frame_rows, powers)
    print("B_SHORT_CASE", name, "frames", len(rows), "codes", summary["all_codes"],
          "failures", failures, "missing_currents", missing,
          "VDD_mW", power_rows.get("VDD", {}).get("observed", {}).get("average_net_mw"), flush=True)
    return summary


def plot(name, t, wave, frames, powers):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    target = OUT / "figures"
    target.mkdir(exist_ok=True)
    fig, ax = plt.subplots(3, 1, figsize=(11.5, 8), sharex=True)
    x = np.array([f["sample_ns"] for f in frames])
    read = np.array([f["frame"] * 100 + 98 for f in frames])
    ax[0].plot(x, [f["source_v"] for f in frames], "kx", label="Ideal source at SAMPLE fall")
    ax[0].plot(x + .6, [f["held_v"] for f in frames], "o", ms=4, label="Held read +0.6 ns")
    ax[0].set_ylabel("Differential (V)")
    ax[1].step(read, [f["code"] for f in frames], where="post", label="Native code; frame +98 ns")
    ax[1].plot(read, [f["ideal_source_code"] for f in frames], "kx", label="Ideal nominal code")
    ax[1].set_ylabel("Output code")
    ax[2].plot(x + .6, [f["held_error_lsb"] for f in frames], "o-", label="Raw held error; static during acquisition")
    ax[2].axhspan(-.25, .25, color="#e1eee3", label="0.25 LSB voltage guard")
    ax[2].axhline(0, color="#666666", ls="--", lw=.8)
    ax[2].set_ylabel("Held error (LSB)")
    ax[-1].set_xlabel("Time (ns)")
    for a in ax:
        a.grid(alpha=.25); a.legend(fontsize=8)
    fig.suptitle(f"B / 1 um / {name}; TT 0.9 V 27 C, 10 MS/s; no noise/mismatch")
    fig.tight_layout(); fig.savefig(target / f"{name}_overview.png", dpi=160); plt.close(fig)
    if name == "history12":
        first_compare = frames[8]["comparisons"][0]["compare_ns"]
        end = first_compare - .02
        ns = np.arange(840.8, end, .002)
        at = lambda key: np.interp(ns, t, wave[key])
        fig, ax = plt.subplots(4, 1, figsize=(11.5, 9), sharex=True)
        ax[0].plot(ns, at("sample"), label="SAMPLE")
        ax[0].set_ylabel("Clock (V)")
        ax[1].plot(ns, at("topp") - at("topn"), label="Actual top differential")
        ax[1].axhline(frames[8]["source_v"], color="#555555", ls="--", label="Ideal sampled source")
        ax[1].set_ylabel("Differential (V)")
        ax[2].plot(ns, (at("topp") - at("topn") - frames[8]["source_v"]) * 1000, label="Held error before first comparison")
        ax[2].axhline(0, color="#555555", ls="--", label="Zero error")
        ax[2].axhspan(-.25 * Q * 1000, .25 * Q * 1000, color="#e1eee3", label="0.25 LSB guard")
        ax[2].set_ylabel("Error (mV)")
        ax[3].plot(ns, at("topp") - at("xdut.xcomp.y"), label="MNINP VGD")
        ax[3].axhline(.99, color="#b34a46", ls="--", label="Core engineering screen")
        ax[3].axhline(-.99, color="#b34a46", ls="--")
        ax[3].set_ylabel("Terminal (V)")
        for a in ax:
            a.axvspan(841.65, end, color="#e3edf3", alpha=.4, label="Held read to first compare" if a is ax[0] else None)
            a.axvline(841.05, color="#777777", ls=":", label="SAMPLE fall" if a is ax[0] else None)
            a.axvline(841.65, color="#777777", ls="--", label="Held read" if a is ax[0] else None)
            a.grid(alpha=.2); a.legend(fontsize=8)
        ax[-1].set_xlabel("Time (ns)")
        fig.tight_layout(); fig.savefig(target / "history_frame9.png", dpi=160); plt.close(fig)


def plot_power(cases):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    groups = ["VDD", "reference", "SAMPLE_ideal_clock", "reference_gate_ideal_outputs", "input_sources"]
    if any(any(g not in c["power"] for g in groups) for c in cases):
        return
    fig, ax = plt.subplots(2, 1, figsize=(11.5, 7))
    x = np.arange(len(groups))
    for i, case in enumerate(cases):
        shift = (i - 1) * .25
        ax[0].bar(x + shift, [case["power"][g]["observed"]["average_net_mw"] for g in groups],
                  width=.24, label=case["case"])
        observed = case["power"]["reference_gate_ideal_outputs"]["observed"]
        count = sum(f["observed"] for f in case["frames"])
        ax[1].bar(i - .14, observed["positive_delivered_pj"] / count, width=.28,
                  color="#ca8244", label="Positive delivered" if i == 0 else None)
        ax[1].bar(i + .14, observed["recovered_pj"] / count, width=.28,
                  color="#447e8d", label="Recovered by ideal outputs" if i == 0 else None)
    ax[0].set_xticks(x, ["VDD", "Reference rails", "Ideal SAMPLE", "Ideal ref gates", "External inputs"])
    ax[0].set_ylabel("Warm net source power (mW)")
    ax[0].axhline(0, color="#666666", lw=.8)
    ax[0].legend(fontsize=8)
    ax[1].set_xticks(range(len(cases)), [c["case"] for c in cases])
    ax[1].set_ylabel("Ideal ref gate energy (pJ/frame)")
    ax[1].legend(fontsize=8)
    for a in ax:
        a.grid(axis="y", alpha=.2)
    fig.suptitle("Measured source delivery after 4 warmup frames; physical driver overhead not included")
    fig.tight_layout(); fig.savefig(OUT / "figures/power_ledger.png", dpi=160); plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=["history12", "directed_a16", "directed_b16"])
    parser.add_argument("--curate", action="store_true")
    args = parser.parse_args()
    self_check()
    if args.case:
        analyze_case(args.case)
        return
    cases = [analyze_case(n) for n in run.read(OUT / "context.json")["cases"]]
    plot_power(cases)
    context = run.read(OUT / "context.json")
    deck = Path(context["cases"]["history12"]["deck"]).read_text(encoding="utf-8")
    result = dict(purpose="B_1x_steps0_1_short_integration_not_full_ADC_qualification",
        config=context["config"], launch=run.read(OUT / "launch.json"),
        preflight=run.read(OUT / "preflight.json"),
        model_includes=[dict(file=path.rsplit("/", 1)[-1], section=section)
                        for path, section in re.findall(r'^include "([^"]+)" section=(\S+)', deck, re.M)],
        include_sha256={Path(p).name: h for p, h in context["include_sha256"].items()},
        full_original_history=context["full_original_history"],
        baseline_deck_sha256=context["baseline_deck_sha256"],
        cases=cases, total_native_frames=sum(c["complete_frames"] for c in cases),
        all_functional_voltage_stress_screens_pass=all(c["functional_voltage_stress_screen_pass"] for c in cases),
        full_ADC_qualified=False, full_real_driver_power_qualified=False, no_OA_change=True,
        no_PVT_mismatch_noise_fullcode_FFT=True, context_sha256=run.sha(OUT / "context.json"),
        config_sha256=run.sha(run.CFG), figures_visually_reviewed=False,
        figure_sha256={p.name: run.sha(p) for p in sorted((OUT / "figures").glob("*.png"))},
        analysis_source_LF_sha256=__import__("hashlib").sha256(Path(__file__).read_text(encoding="utf-8").encode()).hexdigest())
    run.dump(OUT / "summary.json", result)
    if args.curate:
        result["figures_visually_reviewed"] = True
        run.dump(ROOT / "verification/integration/b_short_acceptance_results.json", result)
        target = ROOT / "docs/figures/b_short_acceptance"
        target.mkdir(parents=True, exist_ok=True)
        for p in (OUT / "figures").glob("*.png"):
            shutil.copyfile(p, target / p.name)


if __name__ == "__main__":
    main()
