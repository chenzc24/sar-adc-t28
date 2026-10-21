"""Compact one-period SAR plots from existing native Spectre waveforms."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.text import Text
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "Obsidian_docs/assets/sar_logic_compare"
SUPPLY = .9
COLORS = ("#64748b", "#2563a0", "#bd6b27", "#278071", "#65529b", "#ae5151", "#334b62")
SOURCES = {}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def source(relative):
    path = ROOT / relative
    SOURCES[relative] = digest(path)
    return path


def crossing(t, value, level=.45, rising=True):
    valid = ((value[:-1] < level) & (value[1:] >= level)) if rising else (
        (value[:-1] >= level) & (value[1:] < level))
    i = np.flatnonzero(valid)
    return t[i] + (level-value[i]) * (t[i+1]-t[i]) / (value[i+1]-value[i])


def load(base, case, names):
    record = json.loads(source(f"{base}/results/{case}.json").read_text(encoding="utf-8"))
    assert record["ok"], record.get("errors")
    deck = source(f"{base}/decks/{case}.scs")
    deck_text = deck.read_text(encoding="utf-8")
    # Runner hashes source text with LF; downloaded local copies use CRLF.
    assert hashlib.sha256(deck_text.encode("utf-8")).hexdigest() == record["deck_sha256"]
    expected_step = "200p" if "async_impl" in base else "50p"
    assert re.search(r"tran_async tran .*maxstep=" + expected_step + r"\b", deck_text)
    raw = json.loads(source(f"{base}/waves/{case}.json").read_text(encoding="utf-8"))
    names = {"time", "vin", *names}
    data = {key.lower(): np.asarray(value, dtype=float) for key, value in raw.items()
            if key.lower() in names}
    del raw
    assert names == set(data), names - set(data)
    n = len(data["time"])
    assert all(len(v) == n and np.isfinite(v).all() for v in data.values())
    assert np.all(np.diff(data["time"]) > 0)
    data["time"] *= 1e9
    return data, record


def decode(w, prefix):
    # A displayed word is the physical register pins, not an ideal ADC result.
    return sum((1 << bit) * (w[f"{prefix}{bit}"] > SUPPLY/2).astype(np.int16)
               for bit in range(8))


def envelope(t, v, lo, hi, bins=1800):
    """Retain first/minimum/maximum/last actual samples in every display bin."""
    ix = np.flatnonzero((t >= lo) & (t <= hi))
    if len(ix) < bins*4:
        kept = ix
    else:
        bucket = np.minimum(bins-1, ((t[ix]-lo)*bins/(hi-lo)).astype(int))
        begin = np.r_[0, np.flatnonzero(np.diff(bucket))+1]
        end = np.r_[begin[1:], len(ix)]
        kept = []
        for a, b in zip(begin, end):
            seg = ix[a:b]
            kept.extend((seg[0], seg[v[seg].argmin()], seg[v[seg].argmax()], seg[-1]))
        kept = np.unique(kept)
    # Endpoints are interpolated on the original waveform; no timing is moved.
    return (np.r_[lo, t[kept], hi],
            np.r_[np.interp(lo, t, v), v[kept], np.interp(hi, t, v)])


def bus(ax, t, values, origin, y, color):
    start = np.searchsorted(t, origin, side="right") - 1
    stop = np.searchsorted(t, origin+100, side="right")
    indices = np.r_[start, np.flatnonzero(np.diff(values[start:stop])) + start + 1, stop]
    intervals = []
    for a, b in zip(indices[:-1], indices[1:]):
        left, right = max(0., float(t[a]-origin)), min(100., float(t[b]-origin))
        value = int(values[a])
        assert right >= left
        ax.fill_between([left, right], y-.21, y+.21, facecolor=color, alpha=.045)
        ax.plot([left, right], [y-.21]*2, color=color, lw=.7)
        ax.plot([left, right], [y+.21]*2, color=color, lw=.7)
        ax.vlines(left, y-.21, y+.21, color=color, lw=.55)
        if right-left >= 2.4:
            ax.text((left+right)/2, y, str(value), ha="center", va="center", fontsize=9)
        intervals.append(dict(start_ns=left, end_ns=right, value=value))
    ax.vlines(100, y-.21, y+.21, color=color, lw=.55)
    return intervals


def plot(kind, title, w, record, lanes, pins):
    t = w["time"]
    rises = crossing(t, w["sample"])
    assert len(rises) >= 2 and abs(rises[1]-rises[0]-100) < 1e-6
    origin, end = float(rises[0]), float(rises[1])
    mask = (t >= origin) & (t < end)
    sample_end = float(crossing(t, w["sample"], rising=False)[0])
    acquired = (t > origin+.5) & (t < sample_end)
    assert np.max(np.abs(w["vin"][acquired]-.123)) < 1e-8
    events = {}
    for role, net in pins.items():
        all_edges = crossing(t, w[net])
        event = all_edges[(all_edges > origin+.5) & (all_edges < end)]
        assert len(event) == (1 if role == "commit" else 8), (role, event)
        events[role] = (event-origin).tolist()
    assert np.all(np.asarray(events["write"]) > np.asarray(events["compare"]))
    assert np.all(np.asarray(events["update"]) > np.asarray(events["write"]))
    output = decode(w, "d")
    read_code = sum((1 << bit)*int(np.interp(origin+95, t, w[f"d{bit}"]) > .45)
                    for bit in range(8))
    assert read_code == 145
    prefix = "xctrl.w" if kind == "old" else "d"
    captured = [sum((1 << bit)*int(np.interp(origin+when+.20, t, w[f"{prefix}{bit}"]) > .45)
                    for bit in range(8)) for when in events["write"]]
    assert captured == [128, 128, 128, 144, 144, 144, 144, 145], captured
    if kind == "old":
        assert events["commit"][0] > events["update"][-1]
        assert output[np.searchsorted(t, origin+events["commit"][0]-.02)] == 0
    count = len(lanes)
    fig, ax = plt.subplots(figsize=(8.4, .43*count+.85))
    fig.subplots_adjust(left=.17, right=.985, bottom=.56/(.43*count+.85), top=.88)
    yrows = np.arange(count)[::-1]
    sam_end = sample_end - origin
    ax.axvspan(0, sam_end, color="#e7edf3", alpha=.70, lw=0)
    decoded_intervals = {}
    display_extrema = {}
    for index, (y, (label, net, mode)) in enumerate(zip(yrows, lanes)):
        color = COLORS[index]
        if mode == "voltage":
            x, v = envelope(t, w[net], origin, end)
            ax.plot(x-origin, y-.25 + .50*v/SUPPLY, color=color, lw=1.05)
            ax.hlines(y-.25, 0, 100, color="#cbd2d8", lw=.45, zorder=-1)
            display_extrema[net] = [float(w[net][mask].min()), float(w[net][mask].max())]
        else:
            decoded_intervals[net] = bus(ax, t, decode(w, net), origin, y, color)
    ax.set_yticks(yrows, [label for label, _, _ in lanes], fontsize=9)
    ax.tick_params(axis="y", length=0, pad=10)
    ax.set(xlim=(0, 100), ylim=(-.55, count-.4), xlabel="时间 / ns")
    ax.set_xticks(np.arange(0, 101, 20))
    ax.tick_params(axis="x", labelsize=9)
    ax.grid(axis="x", color="#dbe1e6", lw=.55)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.set_title(title, loc="left", fontsize=11, pad=12)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for item in fig.findobj(Text):
        if item.get_visible() and item.get_text().strip():
            bbox = item.get_window_extent(renderer)
            assert bbox.x0 >= -1 and bbox.y0 >= -1, (item.get_text(), bbox)
            assert bbox.x1 <= fig.bbox.width+1 and bbox.y1 <= fig.bbox.height+1, item.get_text()
    files = []
    for ext in ("png", "svg"):
        target = DEST / f"{kind}_one_cycle.{ext}"
        fig.savefig(target, dpi=200, facecolor="white", metadata={"Date": None} if ext == "svg" else None)
        if ext == "svg":
            target.write_text("\n".join(line.rstrip() for line in target.read_text(encoding="utf-8").splitlines())+"\n",
                              encoding="utf-8")
            ET.parse(target)
        files.append(dict(file=target.name, sha256=digest(target)))
    dimensions = [int(round(size*200)) for size in fig.get_size_inches()]
    plt.close(fig)
    return dict(kind=kind, source_origin_ns=origin, source_end_ns=end, duration_ns=100,
                input_differential_v=.123, final_read_code=read_code,
                plotted_nodes=[dict(label=label, prefix_or_node=net, representation=mode)
                               for label, net, mode in lanes],
                events_ns=events, captured_working_codes=captured, register_intervals=decoded_intervals,
                actual_voltage_extrema=display_extrema, png_dimensions=dimensions,
                files=files, source_scope=record["scope"],
                validated_deck_lf_sha256=record["deck_sha256"])


def main():
    font = Path("C:/Windows/Fonts/msyh.ttc")
    font_manager.fontManager.addfont(font)
    plt.rcParams.update({"font.family": font_manager.FontProperties(fname=font).get_name(),
                         "axes.unicode_minus": False, "path.simplify": False,
                         "svg.fonttype": "none", "svg.hashsalt": "sar_logic_compare"})
    DEST.mkdir(parents=True, exist_ok=True)
    old_lanes = [("SAMPLE", "sample", "voltage"), ("CMP_CLK", "cmp_clk", "voltage"),
                 ("CAPTURE", "capture", "voltage"), ("ADVANCE", "advance", "voltage"),
                 ("W[7:0]", "xctrl.w", "bus"), ("COMMIT", "xctrl.commit", "voltage"),
                 ("D[7:0]", "d", "bus")]
    new_lanes = [("SAMPLE", "sample", "voltage"), ("CMP_CLK", "cmp_clk", "voltage"),
                 ("PHI_W", "xctrl.phi_w", "voltage"), ("PHI_U", "xctrl.phi_u", "voltage"),
                 ("D[7:0]", "d", "bus")]
    plots = []
    for kind, base, case, title, lanes, pins in (
        ("old", "output/sar8_async_impl", "two_cycles_keynodes_aps_01", "旧版：工作码 → 提交 → 输出锁存",
         old_lanes, dict(compare="cmp_clk", write="capture", update="advance", commit="xctrl.commit")),
        ("new", "output/sar8_simple", "two_cycles_simple_v2_aps", "新版：写入的工作码直接作为输出",
         new_lanes, dict(compare="cmp_clk", write="xctrl.phi_w", update="xctrl.phi_u"))):
        nets = {net for _, net, mode in lanes if mode == "voltage"}
        nets.update(f"{net}{bit}" for _, net, mode in lanes if mode == "bus" for bit in range(8))
        w, record = load(base, case, nets)
        plots.append(plot(kind, title, w, record, lanes, pins))
        del w
    for relative in ("scripts/sar8_async/circuit.py", "scripts/sar8_simple/circuit.py",
                     "verification/sar8_async/two_cycle_summary.json", "verification/sar8_simple/summary.json",
                     "scripts/reporting/sar_logic_compare.py"):
        source(relative)
    manifest = dict(scope="Existing native T28 control with ideal analog plant; one period each",
                    supply_v=.9, temperature_c=27, corner="tt", input_v=.123,
                    voltage_display="Raw actual samples, each lane 0 to0.9V; no ideal square-wave reconstruction",
                    bus_display="Decimal from actual register pins at0.45V; short transient intervals remain unlabeled",
                    origin="Each first observed SAMPLE rising midpoint; no warp or per-bit alignment",
                    source_solver_maxstep_s=dict(old=200e-12, new=50e-12),
                    comparison_limit="Different original solver settings; descriptive transfer-flow comparison, no new timing/PVT/SOA qualification",
                    sources=SOURCES, plots=plots)
    (DEST/"provenance.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(json.dumps({"figures": [p["files"][0]["file"] for p in plots],
                      "counts": [{k: len(v) for k, v in p["events_ns"].items()} for p in plots]}, indent=2))


if __name__ == "__main__":
    main()
