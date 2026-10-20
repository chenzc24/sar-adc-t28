"""Inspect actual finite Spectre waveforms without concealing excursions."""
from __future__ import annotations

import argparse
import hashlib
import json
import re

import numpy as np

from oa import OUT, dump


def load(name):
    record = json.loads((OUT / "results" / (name + ".json")).read_text(encoding="utf-8"))
    assert record["ok"], record["errors"]
    context = json.loads((OUT / "contexts" / (name + ".json")).read_text(encoding="utf-8"))
    wavepath = OUT / "waves" / (name + ".json")
    data = json.loads(wavepath.read_text(encoding="utf-8"))
    data = {k.lower(): np.asarray(v, dtype=float) for k, v in data.items()}
    for key, vector in data.items():
        assert len(vector) == len(data["time"]) and np.isfinite(vector).all(), key
    return record, context, data, hashlib.sha256(wavepath.read_bytes()).hexdigest()


def edges(t, vector, level, rising=True):
    mask = (vector[:-1] < level) & (vector[1:] >= level) if rising else (vector[:-1] >= level) & (vector[1:] < level)
    index = np.flatnonzero(mask)
    return t[index] + (level - vector[index]) * (t[index+1] - t[index]) / (vector[index+1] - vector[index])


def analyze(name):
    record, context, data, digest = load(name)
    t = data["time"] * 1e9; supply = context["supply_v"]; level = supply / 2
    at = lambda key, ts: np.interp(ts, t, data[key.lower()])
    word = lambda prefix, ts: sum((1 << bit) * int(at(prefix + str(bit), ts) > level) for bit in range(8))
    ev = {key: edges(t, data[key], level) for key in ("cmp_clk", "xctrl.phi_w", "xctrl.phi_u")}
    sample_falls = edges(t, data["sample"], level, rising=False)
    sample_rises = edges(t, data["sample"], level)
    sampling_illegal_edges = []
    sampling_initialized = True
    for acquired in sample_rises:
        following_falls = sample_falls[sample_falls > acquired]
        if not len(following_falls):
            continue
        finished = following_falls[0]
        for key, transitions in ev.items():
            sampling_illegal_edges.extend((key, float(when)) for when in transitions
                if acquired + .5 < when < finished - .1)
        mask = (t > acquired + .5) & (t < finished - .1)
        if np.any(mask):
            for bit in range(8):
                sampling_initialized &= not bool(np.any(data[f"d{bit}"][mask] > level))
                sampling_initialized &= bool(np.all((data[f"xctrl.t{bit}"][mask] > level) == (bit == 7)))
    frames = []
    for start in sample_falls:
        following = sample_rises[sample_rises > start]
        end = float(following[0]) if len(following) else float(t[-1])
        if end - start < 1:
            continue
        rising = {key: value[(value > start) & (value < end)] for key, value in ev.items()}
        cmp = rising["cmp_clk"]; writes = rising["xctrl.phi_w"]; updates = rising["xctrl.phi_u"]
        resets_all = edges(t, data["cmp_clk"], level, rising=False)
        resets = resets_all[(resets_all > start) & (resets_all < end)]
        read_time = min(start - 41.03 + 95, end - 1.0)
        row = dict(sample_end_ns=float(start), next_sample_ns=end, read_time_ns=read_time,
                   comparisons=len(cmp), writes=len(writes), updates=len(updates),
                   compare_ns=cmp.tolist(), write_ns=writes.tolist(), update_ns=updates.tolist(), reset_ns=resets.tolist(),
                   word_at_read=word("d", read_time), token_at_read=word("xctrl.t", read_time))
        selections = []
        for when in writes:
            # Read before the edge, while the pointer is explicitly held.
            selections.append(word("xctrl.t", when - .02))
        row["write_tokens"] = selections
        if len(writes) == len(updates) and len(writes):
            row["write_to_update_ns"] = (updates - writes).tolist()
        if len(writes) == len(resets) and len(writes):
            row["write_to_comparator_reset_ns"] = (resets - writes).tolist()
        if len(cmp) > 1 and len(resets) >= len(cmp)-1:
            row["comparator_low_ns"] = (cmp[1:] - resets[:len(cmp)-1]).tolist()
        # During every comparison until capture, both differential arrays
        # must agree with the SAME held trial code, not merely final DOUT.
        compare_controls = []
        for when in writes:
            point = when - .02
            code = word("xctrl.code", point)
            banks = {f"{b}_{r}": word(f"b{b}_{r}", point) for b in ("p", "n") for r in ("h", "l")}
            compare_controls.append(dict(t_ns=float(point), code=code, **banks))
        row["compare_bottom_words"] = compare_controls
        row["bottom_codes_correct_at_write"] = all(x["p_h"] == x["n_l"] == x["code"] and
                                                   x["p_l"] == x["n_h"] == (255 ^ x["code"]) for x in compare_controls)
        rail_keys = [f"b{b}_{r}{bit}" for b in ("p", "n") for r in ("h", "l") for bit in range(8)]
        changes_during_compare = []
        for launched, written in zip(cmp, writes):
            mask = (t >= launched) & (t <= written + .10)
            changes_during_compare.append(any(np.any(np.diff(data[key][mask] > level)) for key in rail_keys))
        row["bottom_changed_during_compare_or_100ps_write_hold"] = any(changes_during_compare)
        valid_edges = edges(t, data["xctrl.xtim.raw"], level)
        row["raw_completion_to_write_ns"] = [float(written - ready[-1]) for launched, written in zip(cmp, writes)
            if len(ready := valid_edges[(valid_edges >= launched) & (valid_edges <= written)] )]
        token_count = sum((data[f"xctrl.t{bit}"] > level).astype(int) for bit in range(8))
        multi = (token_count > 1) & (t > start) & (t < end)
        segments = np.diff(np.r_[False, multi, False].astype(int))
        begins = np.flatnonzero(segments == 1); ends = np.flatnonzero(segments == -1)
        row["token_transition_multihot_max_ns"] = max((float(t[min(b, len(t)-1)] - t[a]) for a, b in zip(begins, ends)), default=0.)
        row["token_single_hot_at_every_write"] = all(value in (1, 2, 4, 8, 16, 32, 64, 128) for value in selections)
        stable_start = min(start - 41.03 + 95, end - 4.5)
        stable_end = min(start - 41.03 + 99, end - 1)
        mask = (t >= stable_start) & (t <= stable_end)
        row["read_window_ns"] = [stable_start, stable_end]
        row["word_stable_in_read_window"] = all(not np.any(np.diff(data[f"d{i}"][mask] > level)) for i in range(8))
        frames.append(row)
    # Never clip/fill spikes: retain global extrema on every requested trace.
    extrema = {key: dict(min_v=float(value.min()), max_v=float(value.max()),
                        min_at_ns=float(t[value.argmin()]), max_at_ns=float(t[value.argmax()]))
               for key, value in data.items() if key != "time"}
    overlap = {}
    for bank in ("p", "n"):
        for bit in range(8):
            high, low = data[f"b{bank}_h{bit}"], data[f"b{bank}_l{bit}"]
            both = np.minimum(high, low)
            overlap[f"{bank}{bit}"] = dict(any_both_above_logic_threshold=bool(np.any(both > level)),
                                           max_min_rail_v=float(both.max()))
    log_candidates = list((OUT / "spectre" / name).rglob("spectre.out"))
    logtext = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in log_candidates)
    cmi = re.findall(r".*(?:CMI-\d+|Further occurrences|suppressed|relaxation).*", logtext)
    summary = dict(name=name, context=context, execution_ok=record["ok"], waves_sha256=digest,
                   frames=frames, extrema=extrema, bottom_overlap=overlap, device_warning_lines=cmi,
                   sampling_illegal_rising_edges=sampling_illegal_edges,
                   sampling_initialization_observed=bool(sampling_initialized),
                   any_bottom_overlap=any(x["any_both_above_logic_threshold"] for x in overlap.values()),
                   scope="native_controller_not_full_physical_ADC")
    dump("analysis/" + name + ".json", summary)
    print(json.dumps(dict(name=name, frames=[{k: row[k] for k in
          ("comparisons", "writes", "updates", "word_at_read", "token_at_read", "word_stable_in_read_window")}
          for row in frames], overlap=summary["any_bottom_overlap"],
          cmi_lines=sum("CMI-" in line for line in cmi),
          write_min_v=extrema["xctrl.phi_w"]["min_v"]), indent=2))
    return summary


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("name"); args = ap.parse_args()
    analyze(args.name)


if __name__ == "__main__":
    main()
