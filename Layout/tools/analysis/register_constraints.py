"""Compare transient D/CP intervals to the DFCNQD1 conditional Liberty tables."""

from bisect import bisect_right
from collections import Counter


def _axis(axis, value):
    if len(axis) < 2 or any(a >= b for a, b in zip(axis, axis[1:])):
        raise ValueError("Invalid Liberty interpolation axis")
    i = max(0, min(len(axis) - 2, bisect_right(axis, value) - 1))
    point = max(axis[0], min(axis[-1], value))
    return i, (point - axis[i]) / (axis[i + 1] - axis[i]), point != value


def _table_ps(table, x, y):
    i, a, cx = _axis(table["axes"][0], x)
    j, b, cy = _axis(table["axes"][1], y)
    v = table["table"]
    val = (1 - a) * ((1 - b) * v[i][j] + b * v[i][j + 1]) + a * ((1 - b) * v[i + 1][j] + b * v[i + 1][j + 1])
    return 1000 * val, cx or cy


def evaluate(result, library):
    corner = result["context"]["corner"]
    cell = library["corners"][corner]
    attr = cell["attributes"]
    if attr["time_unit"] != "1ns" or set(cell["axis_order"]) != {"related_pin_transition", "constrained_pin_transition"}:
        raise ValueError("Unsupported timing-table axes or time unit")
    for edge in ("rise", "fall"):
        if [float(attr[k + "_pct_" + edge]) for k in ("slew_lower_threshold", "input_threshold", "slew_upper_threshold")] != [30, 50, 70]:
            raise ValueError("Liberty thresholds differ from the saved waveforms")
    derate = float(attr["slew_derate_from_library"])
    if derate <= 0:
        raise ValueError("Invalid Liberty slew derate")
    counts = Counter()
    worst = {}
    for frame in result["frames"]:
        for row in frame["register_pin_windows"]:
            counts["writes"] += 1
            if row["cdn_high"] is not True:
                counts["inactive_or_unknown_cdn"] += 1
                continue
            for check, polarity in (("setup", "previous_data_rise"), ("hold", "following_data_rise")):
                direction = row[polarity]
                arcs = cell["arcs"][check + "_rising"]
                applicable = list(arcs.values()) if direction is None else [arcs["rise_constraint" if direction else "fall_constraint"]]
                clock = row["clock_slew_ps"]
                data = row[check + "_slew_ps"]
                if direction is None or clock is None or data is None:
                    requirement = 1000 * max(v for table in applicable for line in table["table"] for v in line)
                    method = "trace_boundary" if direction is None else "unresolved_slew"
                else:
                    points = {"related_pin_transition": clock / (1000 * derate), "constrained_pin_transition": data / (1000 * derate)}
                    requirement, outside = _table_ps(applicable[0], *(points[k] for k in cell["axis_order"]))
                    method = "outside_table" if outside else "in_table"
                counts[check + "_" + method] += 1
                gap = row[check + "_ps"]
                observation = dict(frame=frame["frame"], bit=row["bit"], write=row["write"], clock_ns=row["clock_ns"],
                                   interval_ps=gap, requirement_ps=requirement, slack_ps=gap - requirement,
                                   method=method, clock_slew_30_70_ps=clock, data_slew_30_70_ps=data,
                                   data_rising=direction)
                for name in (check, check + "_" + method):
                    if name not in worst or observation["slack_ps"] < worst[name]["slack_ps"]:
                        worst[name] = observation
    return dict(cell=library["target_cell"], library_member=cell["member"], waveform_pvt=corner,
                slew_derate=derate, observation_counts=dict(counts), minimum_slack=worst)
