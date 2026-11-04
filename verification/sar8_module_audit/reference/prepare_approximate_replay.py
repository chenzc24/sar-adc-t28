"""Local knot-deletion candidate, with independent all-native verification.

No remote API, simulation, source edits, shifting, clipping or generated knots.
The 1uV bound is a diagnostic replay tolerance, not an ADC requirement.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
from review_recovered_native import load, REPLAY
from build_first_fixture import replay_node

HERE = Path(__file__).resolve().parent
DEST = HERE / "generated/approximate_replay"
TOLERANCE_V = 1e-6
LIMIT = 32 * 1024**2


def crossing_brackets(y, threshold):
    """Both sides of each rising/falling crossing, including exact equality."""
    a, b = y[:-1] - threshold, y[1:] - threshold
    return np.flatnonzero(((a < 0) & (b >= 0)) | ((a > 0) & (b <= 0)) |
                          ((a == 0) & (b != 0)))


def mandatory_knots(t, y, vdd):
    keep = np.zeros(len(t), dtype=bool)
    keep[[0, len(t)-1, int(np.argmin(y)), int(np.argmax(y))]] = True
    keep[(t >= 64e-9) & (t <= 66e-9)] = True
    for fraction in [.1, .5, .9]:
        brackets = crossing_brackets(y, fraction*vdd)
        keep[brackets] = True
        keep[brackets+1] = True
    return keep


def delete_knots(t, y, mandatory, tolerance):
    if len(t) != len(y) or len(t) != len(mandatory) or len(t) < 2:
        raise ValueError("array length mismatch")
    if not np.all(np.isfinite(t)) or not np.all(np.isfinite(y)) or not np.all(np.diff(t) > 0):
        raise ValueError("nonfinite or unordered native knots")
    if tolerance <= 0 or not mandatory[0] or not mandatory[-1]:
        raise ValueError("invalid tolerance or missing endpoints")
    keep = mandatory.copy()
    fixed = np.flatnonzero(keep)
    pending = list(zip(fixed[:-1], fixed[1:]))
    while pending:
        left, right = pending.pop()
        if right-left < 2:
            continue
        idx = np.arange(left+1, right)
        estimate = y[left]+(y[right]-y[left])*((t[idx]-t[left])/(t[right]-t[left]))
        error = np.abs(y[idx]-estimate)
        worst = int(error.argmax())
        # Keep a small numerical margin; verification applies the exact bound.
        if error[worst] > tolerance*(1-1e-9):
            split = int(idx[worst])
            keep[split] = True
            pending.extend([(left, split), (split, right)])
    return np.flatnonzero(keep)


def verify_native(t, y, ids, required, vdd, tolerance):
    """Independent reconstruction via np.interp, separate from deletion loop."""
    if not np.all(np.diff(ids) > 0) or ids[0] != 0 or ids[-1] != len(t)-1:
        raise ValueError("bad retained indices")
    if not np.all(np.isin(np.flatnonzero(required), ids)):
        raise ValueError("required native witness deleted")
    retained_t, retained_y = t[ids], y[ids]
    reconstruction = np.interp(t, retained_t, retained_y)
    absolute = np.abs(reconstruction-y)
    worst = int(absolute.argmax())
    if absolute[worst] > tolerance:
        raise ValueError("all-native error exceeds fixed tolerance")
    crossing = []
    for fraction in [.1, .5, .9]:
        threshold = fraction*vdd
        source = crossing_brackets(y, threshold)
        candidate = crossing_brackets(retained_y, threshold)
        # Exact original bracket IDs, not approximate edge-time coincidence.
        mapped = ids[candidate]
        matched = (np.array_equal(source, mapped) and
                   np.array_equal(source+1, ids[candidate+1]))
        if not matched:
            raise ValueError("crossing brackets changed")
        crossing.append(dict(fraction_vdd=fraction, native_brackets=len(source),
                             exact_native_brackets_preserved=True, edge_time_delta_s=0.0))
    return dict(native_knots=len(t), retained_knots=len(ids),
                mandatory_knots=int(required.sum()), max_abs_error_v=float(absolute[worst]),
                max_abs_error_time_s=float(t[worst]), rms_error_v=float(np.sqrt(np.mean(absolute**2))),
                crossings=crossing, retained_knots_are_exact_original=True,
                fault_window_all_native_preserved=bool(np.all(np.isin(np.flatnonzero((t>=64e-9)&(t<=66e-9)),ids))),
                global_minimum=dict(value_v=float(y.min()), witness_index=int(np.argmin(y))),
                global_maximum=dict(value_v=float(y.max()), witness_index=int(np.argmax(y))))


def write_candidate():
    w, columns, _, _, result, _, _ = load()
    t = np.asarray(w[:,0])
    vdd_values = w[:,columns.index("vdd!")]
    if not np.all(vdd_values == .99):
        raise ValueError("constant .99V rail assumption invalid")
    DEST.mkdir(parents=True, exist_ok=True)
    path = DEST/"boundary_sources_approximate.scs"
    records = []
    retained_indices = []
    package_hash = hashlib.sha256()
    with path.open("wb") as out:
        def emit(value):
            value=value.encode("ascii")
            package_hash.update(value)
            out.write(value)
        emit("// APPROXIMATE: original knots deleted only; independently bounded at 1uV.\n")
        emit("// All native knots64..66ns and required edge/extremum witnesses retained.\n")
        for number, signal in enumerate(REPLAY):
            y = np.asarray(w[:,columns.index(signal)])
            required = mandatory_knots(t,y,.99)
            ids = delete_knots(t,y,required,TOLERANCE_V)
            retained_indices.append(ids)
            report = verify_native(t,y,ids,required,.99,TOLERANCE_V)
            before = out.tell()
            emit("VREPLAY%d (%s 0) vsource type=pwl wave=[ \\\n" % (number,replay_node(signal)))
            for i in ids:
                emit("  %.17g %.17g \\\n" % (t[i],y[i]))
            emit("]\n")
            records.append(dict(signal=signal, source_bytes=out.tell()-before, **report))
    # Verify the actual written .17g PWL pairs, not just in-memory candidates.
    with path.open("rt",encoding="ascii") as replay:
        assert replay.readline().startswith("// APPROXIMATE")
        assert replay.readline().startswith("// All native")
        for number, (signal, ids) in enumerate(zip(REPLAY,retained_indices)):
            header=replay.readline()
            if not header.startswith("VREPLAY%d (%s 0) "%(number,replay_node(signal))):
                raise ValueError("written source header mismatch")
            actual=[]
            for line in replay:
                if line.strip()=="]":break
                pair=line.rstrip().rstrip("\\").split()
                if len(pair)!=2:raise ValueError("written source pair malformed")
                actual.append([float(pair[0]),float(pair[1])])
            actual=np.asarray(actual)
            y=np.asarray(w[:,columns.index(signal)])
            if actual.shape!=(len(ids),2) or not np.array_equal(actual[:,0],t[ids]) or not np.array_equal(actual[:,1],y[ids]):
                raise ValueError("written source contains altered or new native knots")
            verify_native(t,y,ids,mandatory_knots(t,y,.99),.99,TOLERANCE_V)
        if replay.read().strip():raise ValueError("unexpected written source tail")
    size = path.stat().st_size
    # A separately identified local package candidate; the native-template deck
    # remains untouched and visibly incomplete. No run is registered here.
    base = HERE/"generated/first_reproduction"
    (DEST/"dut.scs").write_bytes((base/"dut.scs").read_bytes())
    test = (base/"test.scs").read_text()
    test = test.replace("// NOT READY FOR DISPATCH: full-native PWL packaging requires parent decision.",
                        "// APPROXIMATE REPLAY CANDIDATE: local only, parent review required before dispatch.")
    test = test.replace('include "boundary_sources_full_native.scs"',
                        'include "boundary_sources_approximate.scs"')
    (DEST/"test.scs").write_text(test)
    package = []
    for name in ["dut.scs","test.scs",path.name]:
        data=(DEST/name).read_bytes()
        package.append(dict(name=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
    package_bytes=sum(item["bytes"] for item in package)
    report = dict(status="candidate_local_only_parent_review_required",
        approximation=True,tolerance_v=TOLERANCE_V,tolerance_scope="diagnostic replay only; not ADC specification",
        source_boundary_uncompressed_sha256=result["boundary_uncompressed_sha256"],
        source_native_rows=len(w),channels=len(REPLAY),fault_window_s=[64e-9,66e-9],
        extremum_tie_policy="Earliest exact native witness of each global min/max; equal-valued plateau knots may be deleted except required edges/window",
        verification="Every native time tested independently with np.interp; two curves are piecewise linear on original knots, so absolute error is bounded between native knots too",
        actual_written_source_pairs_readback_verified=True,
        source_file=path.name,source_bytes=size,source_sha256=package_hash.hexdigest(),
        managed_input_cap_bytes=LIMIT,source_alone_within_cap=size<=LIMIT,
        package_files=package,package_bytes=package_bytes,package_within_32MiB=package_bytes<=LIMIT,
        package_acceptance="local byte count only; managed registration/remote acceptance not attempted",
        native_knots_total=len(w)*len(REPLAY),retained_knots_total=sum(r["retained_knots"] for r in records),
        max_abs_error_v=max(r["max_abs_error_v"] for r in records),traces=records,
        remote_started=False)
    (DEST/"verification.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:report[k] for k in ["source_bytes","source_alone_within_cap","native_knots_total","retained_knots_total","max_abs_error_v"]}))


if __name__ == "__main__":
    write_candidate()
