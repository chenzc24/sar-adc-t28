"""Measure clamped charge, top step and 0.1% settling for the fixed fixture."""

from __future__ import print_function

import argparse
import glob
import json
import math
import os

from native_stream import samples


BIAS = 0.45
BIAS_TOL = 1e-5


def linear(p, q, t, signal):
    ta, a = p
    tb, b = q
    return a[signal] + (b[signal] - a[signal]) * (t - ta) / (tb - ta)


def values_between(trace, signal, start, stop):
    result = []
    for p, q in zip(trace[:-1], trace[1:]):
        if p[0] > stop:
            break
        if q[0] < start:
            continue
        lo, hi = max(start, p[0]), min(stop, q[0])
        if not result:
            result.append((lo, linear(p, q, lo, signal)))
        if hi > lo:
            result.append((hi, linear(p, q, hi, signal)))
    if not result or result[0][0] != start or result[-1][0] != stop:
        raise ValueError("Incomplete interval for " + signal)
    return result


def measure(trace, branch, edge):
    clamp, top = branch
    # The shunt is 1 ohm. The other bottom plate is held at DC throughout.
    c = values_between(trace, clamp, edge - 0.05e-9, edge + 1.5e-9)
    capacitance = sum((t1 - t0) * (v0 + v1) / 2 for (t0, v0), (t1, v1) in zip(c[:-1], c[1:])) / 0.10
    wave = values_between(trace, top, edge - 0.05e-9, edge + 1.5e-9)
    initial, final = wave[0][1], wave[-1][1]
    if abs(initial - BIAS) > BIAS_TOL:
        raise ValueError("TOP drifted before the test step")
    step = final - initial
    if not (capacitance > 0 and step > 0):
        raise ValueError("Unexpected direction of charge or top step")
    tol = 0.001 * step
    times = [(t, abs(v - final)) for t, v in wave]
    last = max(i for i, (_, e) in enumerate(times) if e > tol)
    t0, e0 = times[last]
    t1, e1 = times[last + 1]
    settled = t0 + (t1 - t0) * (e0 - tol) / (e0 - e1)
    return {"capacitance_f": capacitance, "pre_edge_top_v": initial,
            "top_step_v": step, "settle_s": settled - edge}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    waveforms = glob.glob(os.path.join(args.run_dir, "raw", "*.tran.tran"))
    if len(waveforms) != 1:
        raise ValueError("Missing unique native transient")
    trace = []
    bias = None
    for t, v in samples(waveforms[0]):
        if bias is None:
            bias = {signal: v[signal] for signal in ("cm", "qpre", "qpost", "fpre", "fpost")}
            if t != 0 or not all(abs(volts - BIAS) <= BIAS_TOL for volts in bias.values()):
                raise ValueError("Initial bias mismatch: " + repr(bias))
        row = {"qpre": v["qpre"] - v["cm"], "qpost": v["qpost"] - v["cm"],
               "fpre": v["fpre"], "fpost": v["fpost"]}
        if not all(not (math.isnan(x) or math.isinf(x)) for x in row.values()):
            raise ValueError("Non-finite fixture waveform")
        trace.append((t, row))
        if len(trace) > 200000:
            raise ValueError("Fixture exceeds the approved measurement size")
    if not trace or abs(trace[-1][0] - 9e-9) > 1e-15:
        raise ValueError("Incomplete transient")
    result = {"analysis_complete": True, "stop_s": trace[-1][0], "points": len(trace),
              "initial_bias_v": bias, "initial_bias_tolerance_v": BIAS_TOL}
    for name in ("pre", "post"):
        data = {bit: measure(trace, ("q" + name, "f" + name), edge)
                for bit, edge in (("b0", 1e-9), ("b1", 5e-9))}
        data["b1_to_b0"] = data["b1"]["capacitance_f"] / data["b0"]["capacitance_f"]
        result[name] = data
    with open(os.path.join(args.output_dir, "result.json"), "w") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")


if __name__ == "__main__":
    main()
