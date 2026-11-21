"""Measure the gate-driver transition at actual switch and MOM terminals."""

from __future__ import print_function

import argparse
import glob
import json
import os

from native_stream import samples


def crossing(t0, t1, before, after, threshold, direction):
    if direction * (before - threshold) < 0 <= direction * (after - threshold):
        return t0 + (t1 - t0) * (threshold - before) / (after - before)
    return None


def case_probe_names(mapping):
    return {kind: {key: [name.replace("\\", "").lower() for name in names]
                   for key, names in probes.items()} for kind, probes in mapping.items()}


def measure(path, context):
    vdd = context["condition"]["vdd_v"]
    lsb = context["lsb_v"]
    bits = context["bits"]
    threshold = .25 * lsb
    cases = {case: case_probe_names(mapping) for case, mapping in context["probe_paths"].items()}
    edges = context["command_times_s"]
    windows = {}
    preset = dict.fromkeys(cases, None)
    flat = {}
    for case, mapping in cases.items():
        flat[case] = {n: group[1] for group, nodes in mapping["gates"].items() for n in nodes}
        windows[case] = [dict(command_s=t, code_high=i == 0, gates={}, last_outside=t,
                              residual_weighted_at_2ns_lsb=None, finish_s=None, diff_initial=None,
                              diff_end=None, diff_min=None, diff_max=None, reference_peak_a=0.,
                              supply_peak_a=0.) for i, t in enumerate(edges)]

    prev_t = prev = None
    for t, volts in samples(path):
        for case, mapping in cases.items():
            gate_side = flat[case]
            if preset[case] is None and t >= 4e-9:
                preset[case] = all((volts[n] > .5 * vdd) == ((name[1] == "p") == (int(name[3:]) == 7))
                                   for name, nodes in mapping["gates"].items() for n in nodes)
            differential = volts[case + "_topp"] - volts[case + "_topn"]
            for index, event in enumerate(windows[case]):
                cmd = event["command_s"]
                if t < cmd - .15e-9 or t > cmd + 10e-9:
                    continue
                if event["diff_initial"] is None:
                    event["diff_initial"] = differential
                direction_p = 1 if event["code_high"] else -1
                if prev is not None:
                    for node, side in gate_side.items():
                        sign = direction_p if side == "p" else -direction_p
                        times = event["gates"].setdefault(node, {})
                        for percent in (10, 50, 90):
                            label = str(percent)
                            if label not in times:
                                x = crossing(prev_t, t, prev[node], volts[node], vdd * percent / 100., sign)
                                if x is not None:
                                    times[label] = x
                if t < cmd:
                    continue
                check = 0.
                for group, nodes in mapping["plates"].items():
                    side, bit = group[1], int(group[2:])
                    ref = "refp" if (side == "n") == event["code_high"] else "refn"
                    worst = max(abs(volts[n] - volts[case + "_" + ref]) for n in nodes)
                    check += (1 << bit) / 256. * worst
                if check > threshold:
                    event["last_outside"] = t
                if t >= cmd + 2e-9 and event["residual_weighted_at_2ns_lsb"] is None:
                    event["residual_weighted_at_2ns_lsb"] = check / lsb
                event["finish_s"] = t
                event["diff_end"] = differential
                event["residual_weighted_end_lsb"] = check / lsb
                event["diff_min"] = min(differential, event["diff_min"]) if event["diff_min"] is not None else differential
                event["diff_max"] = max(differential, event["diff_max"]) if event["diff_max"] is not None else differential
                ref_current = max(abs(volts["vs_" + case + "_" + ref + ":p"]) for ref in ("refn", "refp"))
                event["reference_peak_a"] = max(event["reference_peak_a"], ref_current)
                event["supply_peak_a"] = max(event["supply_peak_a"], abs(volts["vv_" + case + ":p"]))
        prev_t, prev = t, volts
    if prev_t is None or abs(prev_t - context["expected_stop_s"]) > 1e-15:
        raise ValueError("Incomplete driver transition simulation")

    verdict = {}
    for case, events in windows.items():
        for event in events:
            cmd = event["command_s"]
            expected = len(flat[case])
            observed = [n for n, values in event["gates"].items() if len(values) == 3]
            event["gate_crossings_complete"] = len(observed) == expected and expected > 0
            event["gate_delay_ps"] = {n: (event["gates"][n]["50"] - cmd) * 1e12 for n in observed}
            event["gate_slew_ps"] = {n: abs(event["gates"][n]["90"] - event["gates"][n]["10"]) * 1e12
                                     for n in observed}
            times = list(event["gate_delay_ps"].values())
            event["gate_50pct_spread_ps"] = max(times) - min(times) if times else None
            event["settle_weighted_0p25_lsb_ns"] = ((event["last_outside"] - cmd) * 1e9
                                                    if event["residual_weighted_end_lsb"] <= .25 else None)
            event["differential_step_v"] = event["diff_end"] - event["diff_initial"]
            event["pass"] = (event["gate_crossings_complete"]
                             and event["settle_weighted_0p25_lsb_ns"] is not None
                             and (event["differential_step_v"] < 0) == event["code_high"])
            del event["gates"]
        verdict[case] = bool(preset[case]) and all(e["pass"] for e in events)
    return dict(context=context, analysis_complete=True, transient_stop_s=prev_t,
                preset_pass=preset, cases=windows, pass_by_case=verdict,
                all_screens_pass=all(verdict.values()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--source-run-dir")
    args = parser.parse_args()
    base = args.source_run_dir or args.run_dir
    with open(os.path.join(base, "inputs/context.json")) as stream:
        context = json.load(stream)
    trace, = glob.glob(os.path.join(base, "raw/*.tran"))
    result = measure(trace, context)
    with open(os.path.join(args.output_dir, "result.json"), "w") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
