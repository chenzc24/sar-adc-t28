"""Bounded local native review; collected source files/exporters stay read-only."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import zlib
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
COLLECTED = ROOT / "output/managed_execution/runs/sar8audit-ref-native-v1/collected"
CACHE = HERE / "cache"
OUT = HERE / "generated/native_review"
REPLAY = (["xdut.phi_u", "xdut.xref.cap_req", "xdut.sample_int",
           "xdut.seq_sample", "xdut.cmp_clk"]
          + ["xdut.xref.rst%d" % b for b in range(8)]
          + ["d%d" % b for b in range(8)] + ["xdut.code%d" % b for b in range(8)])


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def load():
    receipt = json.loads((COLLECTED / "collection_receipt.json").read_text())
    assert not receipt["skipped"]
    for item in receipt["files"]:
        p = COLLECTED / item["name"]
        assert p.stat().st_size == item["bytes"] and sha(p) == item["sha256"], item["name"]
    derived = COLLECTED / "derived"
    result = json.loads((derived / "result.json").read_text())
    state = json.loads((COLLECTED / "analysis.state.json").read_text())
    assert state["status"] == "complete" and state["exit_code"] == 0
    CACHE.mkdir(exist_ok=True)
    dest = CACHE / "boundary.f64le"
    if not dest.exists() or dest.stat().st_size != result["boundary_uncompressed_bytes"] or sha(dest) != result["boundary_uncompressed_sha256"]:
        decoder = zlib.decompressobj(31)
        h = hashlib.sha256()
        with (derived / "boundary.f64le.gz").open("rb") as src, dest.open("wb") as target:
            for block in iter(lambda: src.read(65536), b""):
                decoded = decoder.decompress(block)
                h.update(decoded)
                target.write(decoded)
            decoded = decoder.flush()
            h.update(decoded)
            target.write(decoded)
        assert decoder.eof and h.hexdigest() == result["boundary_uncompressed_sha256"]
    assert dest.stat().st_size == result["boundary_uncompressed_bytes"]
    bc = (derived / "native.boundary.columns").read_text().splitlines()
    dc = (derived / "native.diagnostic.columns").read_text().splitlines()
    boundary = np.memmap(dest, dtype="<f8", mode="r").reshape((-1, len(bc)))
    diagnostic = np.memmap(derived / "native.diagnostic.f64le", dtype="<f8", mode="r").reshape((-1, len(dc)))
    bt, dt = boundary[:, 0] * 1e9, diagnostic[:, 0] * 1e9
    assert len(boundary) == result["native"]["native_points_exported"]
    assert np.all(np.diff(bt) > 0) and bt[0] == 0
    ids = np.searchsorted(boundary[:, 0], diagnostic[:, 0])
    assert np.array_equal(boundary[ids, 0], diagnostic[:, 0])
    return boundary, bc, diagnostic, dc, result, receipt, state


def edges(t, signal, rail, up=True):
    delta = signal - rail / 2
    ids = np.flatnonzero((delta[:-1] < 0) & (delta[1:] >= 0) if up
                         else (delta[:-1] > 0) & (delta[1:] <= 0))
    return [dict(before_index=int(i), after_index=int(i+1), before_ns=float(t[i]),
                 after_ns=float(t[i+1]),
                 half_vdd_estimate_ns=float(t[i] - delta[i] * (t[i+1]-t[i])/(delta[i+1]-delta[i])))
            for i in ids]


def word_at_sample(w, columns, prefix, index, vdd):
    values = [float(w[index, columns.index(prefix + str(bit))]) for bit in range(8)]
    bits = [0 if value <= .1 * vdd else 1 if value >= .9 * vdd else None for value in values]
    return None if None in bits else sum(bit << i for i, bit in enumerate(bits))


def capture_checks(boundary, columns):
    """Compare selected D/CODE input against independently fixed command243."""
    t = boundary[:, 0] * 1e9
    vdd = boundary[:, columns.index("vdd!")]
    captures = edges(t, boundary[:, columns.index("xdut.xref.cap_clk")], vdd)
    requests = edges(t, boundary[:, columns.index("xdut.xref.cap_req")], vdd)
    program = json.loads((HERE / "reference_fixture_spec.json").read_text())["independent_command_program"]["two_capture_program"]
    program = [row for row in program if row["command_word"] == 243]
    records = []
    for i, capture in enumerate(captures):
        ordinal, early = i // 2, i % 2 == 0
        assert ordinal < 8, "Extra native capture before first-frame completion"
        row = program[ordinal]
        at = capture["half_vdd_estimate_ns"]
        prefix = "d" if early else "xdut.code"
        expected = row["D_early"] if early else row["CODE_late"]
        sample_ids = np.flatnonzero((t >= at - .01) & (t <= at + .01))
        assert len(sample_ids), "No native input witness"
        observed = [word_at_sample(boundary, columns, prefix, int(k), float(vdd[k])) for k in sample_ids]
        phi = boundary[sample_ids, columns.index("xdut.phi_u")]
        phi_expected = bool(early)
        phi_known = np.all(phi >= .9 * vdd[sample_ids]) if early else np.all(phi <= .1 * vdd[sample_ids])
        half_phase = np.all(phi > .5 * vdd[sample_ids]) if early else np.all(phi < .5 * vdd[sample_ids])
        center = capture["after_index"]
        records.append(dict(capture=i, bit=row["bit"], phase="early_D" if early else "late_CODE",
            expected_word=expected, measured_words=sorted(set(x for x in observed if x is not None)),
            unknown_samples=sum(x is None for x in observed), samples=len(sample_ids),
            input_word_matches=all(x == expected for x in observed),
            PHI_U_expected_high=phi_expected, PHI_U_phase_matches=bool(phi_known),
            PHI_U_halfrail_phase_matches=bool(half_phase),
            PHI_U_min_v=float(phi.min()), PHI_U_max_v=float(phi.max()),
            PHI_U_at_native_sample_after_capture_v=float(boundary[center, columns.index("xdut.phi_u")]),
            PHI_U_90percent_rule_is_not_a_cell_requirement=True,
            observed_window_ns=[float(t[sample_ids[0]]), float(t[sample_ids[-1]])],
            requested_diagnostic_guard_ps=10, guard_is_not_a_foundry_setup_hold_spec=True,
            capture_edge=capture,
            CAP_REQ_to_CAP_CLK_half_level_delay_ps=None if i >= len(requests) else
                (at - requests[i]["half_vdd_estimate_ns"]) * 1000))
    return dict(independent_command_word=243, prefix_end_ns=float(t[-1]),
        observed_capture_count=len(records), checks=records,
        all_observed_selected_input_words_match=all(r["input_word_matches"] for r in records),
        all_halfrail_protocol_phases_match=all(r["PHI_U_halfrail_phase_matches"] for r in records),
        all_90percent_guard_rules_match=all(r["PHI_U_phase_matches"] for r in records),
        cell_setup_hold_voltage_margin_verdict="not_inferred; diagnostic guard/fractions are not characterized cell limits",
        scope="First-frame recovered prefix only; selected D for early, CODE for late. Full eight-bit Q/cycle oracle finish is not asserted.",
        source_of_expected_words="Approved independent243/12 program; no gate or measured Q creates targets",
        edge_method="Half-VDD estimates interpolate adjacent native witnesses; wave data/knots remain unchanged")


def source_chunks(w, columns, traces=REPLAY):
    """Prospective inline PWL text: every native knot, round-trip float precision."""
    for name in traces:
        column = columns.index(name)
        label = "VREPLAY_" + re_identifier(name)
        yield ("%s (REPLAY_%s 0) vsource type=pwl wave=[ \\\n" % (label, re_identifier(name))).encode()
        for start in range(0, len(w), 1024):
            stop = min(start + 1024, len(w))
            yield ("".join("  %.17g %.17g \\\n" % (w[i, 0], w[i, column]) for i in range(start, stop))).encode()
        yield b"]\n"


def re_identifier(name):
    return name.replace(".", "_").replace("!", "_").upper()


def pwl_size(w, columns):
    raw, packed = 0, 0
    encoder = zlib.compressobj(1, zlib.DEFLATED, 31)
    h, zhash = hashlib.sha256(), hashlib.sha256()
    for chunk in source_chunks(w, columns):
        raw += len(chunk)
        h.update(chunk)
        encoded = encoder.compress(chunk)
        packed += len(encoded)
        zhash.update(encoded)
    encoded = encoder.flush()
    packed += len(encoded)
    zhash.update(encoded)
    return dict(signals=len(REPLAY), knots_per_signal=len(w), total_knots=len(REPLAY)*len(w),
        full_native_pwl_bytes=raw, full_native_pwl_sha256=h.hexdigest(),
        gzip_level1_bytes=packed, gzip_level1_sha256=zhash.hexdigest(),
        exceeds_32MiB_as_plain=raw >= 32*1024**2,
        exceeds_32MiB_as_gzip=packed >= 32*1024**2,
        file_written=False, formatting="seconds/volts .17g, every native row, no extra endpoint",
        scope="Prospective native source text only; not an approved remote package or simplification")


def plot(diagnostic, columns, result):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    t = diagnostic[:, 0] * 1e9
    def y(n): return diagnostic[:, columns.index(n)]
    groups = [
        (["xdut.xref.cap_req", "xdut.xref.cap_clk"], "CAP input/output (V)"),
        (["xdut.xref.q0", "xdut.xref.h0", "xdut.xref.l0"], "Q0 / H0 / L0 (V)"),
        (["xdut.xref.xdrv0.gnnpre"], "GNNPRE (V)"),
        (["xdut.xref.xdrv0.gnna"], "Stage A: GNNA (V)"),
        (["xdut.xref.xdrv0.gnnb"], "Stage B: GNNB (V)"),
        (["xdut.xref.xdrv0.gnndrv"], "Stage C: GNNDRV (V)"),
        (["xdut.gnn0", "xdut.gnp0"], "Actual N-side gates (V)"),
        (["xdut.xcdac.bn0", "xdut.xcdac.bp0", "vrefp", "vrefn"], "Load / references (V)")]
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(8, 1, figsize=(12, 14), sharex=True, layout="constrained")
    for ax, (names, label) in zip(axes, groups):
        for name in names:
            ax.plot(t, y(name), lw=1.3, label=name.rsplit(".", 1)[-1].upper())
        ax.axhline(.99, color="#888", ls=":", lw=.8)
        ax.axhline(0, color="#bbb", ls=":", lw=.7)
        ax.set_ylabel(label)
        ax.grid(alpha=.2)
        ax.legend(fontsize=8, loc="upper right", ncol=len(names))
    axes[-1].set(xlim=(64.8, 65.6), xlabel="Time (ns)")
    fig.suptitle("Driver0 native timing | T28 FF, 0.99 V, -40 C; TT passives\n"
                 "IO reference switches / original core driver and comparator / physical full CDAC\n"
                 "Ideal external VDD, reference sources and sample clock; 50 ohm + 4 pF reference; no noise/mismatch/PEX", fontsize=11)
    fig.savefig(OUT / "driver0_native_timing.png", dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(4, 1, figsize=(11, 8), sharex=True, layout="constrained")
    details = [("xdut.xref.xdrv0.gnna", .99, "GNNA - VDD", False),
               ("xdut.xref.xdrv0.gnnb", 0, "GNNB - VSS", True),
               ("xdut.xref.xdrv0.gnndrv", .99, "GNNDRV - VDD", False),
               ("xdut.gnn0", .99, "GNN0 - VDD", False)]
    for ax, (name, baseline, label, minimum) in zip(axes, details):
        data = (y(name)-baseline)*1000
        mask = (t>=65.23) & (t<=65.26)
        k = np.flatnonzero(mask)[np.argmin(data[mask]) if minimum else np.argmax(data[mask])]
        ax.plot(t[mask], data[mask], ".-", ms=2, lw=1, label=label+" (native points)")
        ax.axhline(0, color="#777", ls="--", lw=.8)
        ax.plot(t[k], data[k], "o", color="#d8503d", ms=4)
        ax.annotate("%.3f mV @ %.9f ns" % (data[k], t[k]), (t[k], data[k]),
                    xytext=(8, 8 if not minimum else -16), textcoords="offset points", fontsize=9)
        ax.set_ylabel(label+"\n(mV)")
        ax.grid(alpha=.2)
        ax.legend(fontsize=8, loc="upper left")
    axes[-1].set(xlim=(65.23,65.26),xlabel="Time (ns)")
    fig.suptitle("Native driver-stage excursion sequence | same frozen FF cold reference-only case\n"
                 "Stage timing is observed; branch currents were not saved, so current causality remains unresolved", fontsize=11)
    fig.savefig(OUT / "driver0_native_peak_zoom.png", dpi=180)
    plt.close(fig)


def main():
    boundary, bc, diagnostic, dc, result, receipt, state = load()
    OUT.mkdir(parents=True, exist_ok=True)
    peaks = {}
    for name, minimum in [("xdut.xref.xdrv0.gnna", False), ("xdut.xref.xdrv0.gnnb", True),
                          ("xdut.xref.xdrv0.gnndrv", False), ("xdut.gnn0", False)]:
        k = int(np.argmin(diagnostic[:, dc.index(name)]) if minimum else np.argmax(diagnostic[:, dc.index(name)]))
        peaks[name] = dict(value_v=float(diagnostic[k, dc.index(name)]), time_ns=float(diagnostic[k, 0]*1e9))
    review = dict(source_run="sar8fix-loaded-ref-ffcold", recovered_run="sar8audit-ref-native-v1",
        all_receipt_files_sha_verified=True, receipt_files=len(receipt["files"]),
        collection_bytes=receipt["total_bytes"], uncompressed_sha_verified=True,
        source_input_hashes=result["source_input_hashes"], peaks=peaks,
        capture_input_oracle=capture_checks(boundary, bc),
        full_native_pwl_size=pwl_size(boundary, bc),
        remote_export_elapsed_s=state["elapsed_seconds"], remote_export_peak_rss_bytes=state["peak_rss_bytes"],
        causal_current_attribution="unresolved: driver0/reference-bit0 current branches were not saved")
    (OUT / "review.json").write_text(json.dumps(review, indent=2)+"\n")
    plot(diagnostic, dc, result)
    print(json.dumps({k:review[k] for k in ["peaks","full_native_pwl_size"]}, indent=2))
    print("CAPTURE_PREFIX",review["capture_input_oracle"]["observed_capture_count"],
          review["capture_input_oracle"]["all_observed_selected_input_words_match"])


if __name__ == "__main__":
    main()
