"""Score the short ADC regression with probes on the extracted CDAC."""

from __future__ import print_function

import argparse
import json
import os

import reference_short as reference
from measure_reference_driver import case_probe_names
from native_stream import samples


def measure(run, out):
    with open(os.path.join(run, "inputs/context.json")) as stream:
        context = json.load(stream)
    probes = case_probe_names(context["probe_paths"])
    peak_supply = [0.]

    def sampled(path):
        for time, volts in samples(path):
            for name, contacts in probes["gates"].items():
                volts["xdut." + name] = volts[contacts[0]]
            peak_supply[0] = max(peak_supply[0], abs(volts["vvdd:p"]))
            yield time, volts

    def bottom(volts, lsb):
        total, worst = 0., 0.
        words = []
        for side in ("n", "p"):
            word = 0
            for bit in range(8):
                nodes = (probes["gates"]["g%sn%d" % (side, bit)] +
                         probes["gates"]["g%sp%d" % (side, bit)])
                gates = [volts[node] > .5 * volts["vdd!"] for node in nodes]
                if not all(gates) and any(gates):
                    return None
                word |= (1 << bit) if gates[0] else 0
                ref = volts["vrefn" if gates[0] else "vrefp"]
                error = max(abs(volts[n] - ref) for n in probes["plates"]["b%s%d" % (side, bit)])
                total += (1 << bit) * error / 256.
                worst = max(worst, error)
            words.append(word)
        if words[0] + words[1] != 255:
            return None
        return dict(weighted_bound_lsb=total / lsb, max_bottom_error_v=worst, gate_words=words)

    reference.samples = sampled
    reference.bottom = bottom
    result = reference.analyze(run, out)
    for frame in result["frames"]:
        frame["switch_port_overlap_peak_a"] = None
        frame["switch_port_overlap_integral_c"] = None
    result.update(
        adc_supply_peak_a=peak_supply[0], settling_scope=(
            "Worst sampled MOM terminal per bit relative to its active reference rail, weighted by nominal binary weight."
        ),
        current_scope="Peak current in the external ADC supply source and reference feed resistors.",
        limitations=["Selected physically located gate and plate contacts; other blocks use their schematics.",
                     "Short deterministic test. Native terminal reliability, process mismatch, and top-level fill are separate."],
    )
    with open(os.path.join(out, "result.json"), "w") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--source-run-dir")
    args = parser.parse_args()
    measure(args.source_run_dir or args.run_dir, args.output_dir)
