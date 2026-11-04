# Reference current/KCL analyzer: local proposal

Status: local preparation and synthetic validation only. No registration, remote
submission, simulator compilation or electrical reproduction result. Original
approximate/native packages and all frozen exporters remain unchanged.

## Entry and outputs

`reference_current_analyze.py` is independent, stdlib-only Python2.7/3 source:

```
python reference_current_analyze.py --run-dir RUN --output-dir RUN/derived
```

The directory must be fresh. Historical source run is explicitly read-only.
Require managed simulation complete/exit0/native PASS/zero-error footer, the
exact `tran_repro PASS`, all frozen input hashes and exactly one native ASCII
transient. `result.json` is published last by atomic rename after other outputs,
byte-cap and Linux RSS checks. Prior failures leave no completion result.
Existing output is never overwritten.

| Artifact | Contents |
| --- | --- |
| kcl.full.native.f64le.gz | Every native time0..last, VDD, five physical node voltages, all15 incident component-port currents, five signed KCL sums;27 columns |
| fault.native.f64le.gz | Every native point in64..last ns,43 diagnostic voltages, all275 selected currents and five KCL sums;324 columns |
| native.columns.json | Exact column order, rows, compressed/uncompressed bytes and SHA256, native/derived field interpretation |
| spectre.original.log | Complete, unchanged future simulation spectre.out, including original CMI text/context; SHA256 |
| result.json | Native extrema/times, startup values, edges/brackets, charge/KCL statistics, peak current snapshots and diagnostic-only source comparisons |

Both binary streams use lossless gzip, no decimation/resampling. All1100 selected
voltages and275 currents must exist in TRACE and initialize at the first t=0
point. Sparse unchanged values are held from their actual prior native update;
this never substitutes zero for an absent terminal. GROUP1 alias and multiline
PROP metadata are handled; unknown VALUE keys, duplicate selected updates,
nonfinite scalars, non-increasing times, missing END or wrong stop reject.

Five KCL incidence lists must agree exactly with the complete275-entry terminal
catalog from flattened physical connections. Omitting a selected incident branch
therefore fails before reduction. Positive current enters the component from its
node; PDK wrapper ports1/2/3/4 are D/G/S/B. Native model multiplicity is already
included. No intrinsic channel/displacement/junction decomposition is claimed.

## Measurements and limitations

- Every selected voltage/current: full-history native min/max and time.
- Five critical nodes: full-history raw incident currents and signed residual at
  every point; maximum absolute residual and current snapshot, residual/L1 ratio,
  signed/absolute residual integrals and fault-window maximum.
- Every selected current: signed and absolute-current trapezoidal charge over
  consecutive native points, plus fault-window charge. Window integration uses
  the actual first/last included native points; it does not invent64ns samples.
- All43 diagnostic voltages: rising/falling0.5VDD estimates with both native
  witnesses and their VDD values. Estimates are derived events, not new waveform
  samples. Event-count cap is10000; overflow fails rather than truncates.
- Four fault-window driver A/B/C/GNN0 extrema: native voltage/time and all275
  signed currents plus KCL at that exact native point. Full-history extrema are
  separately reported, so a different startup maximum remains visible.
- All1375 initial selected values are saved. Only31 incoming/CAP_CLK boundary
  voltages have same-source t=0 witnesses. Internal driver/Q/TOP startup states
  are observed; reproduction of unseen original initial states is not claimed.
- 228 MOS terminal-pair extrema cover driver0, four LSB reference MOS, comparator
  input pair and four bootstrap-main instances. The full saved catalog has9306
  pairs; remaining9078 are explicitly outside this reducer's screening scope.
  Their raw voltages remain saved. No whole-circuit stress or lifetime verdict.

## Native evidence versus approximate boundary

The input boundary remains explicitly marked approximate (knot deletion,
<=1uV diagnostic bound, original/approximate hashes and counts). Measured output
voltages/currents are new native simulator samples, including genuine narrow
spikes. KCL sums, trapezoids and half-level estimates are labeled derived.

A frozen2,376,192-byte original native diagnostic table is included in the
proposal with its hash. For21 corresponding voltages, the source piecewise
linear curve is evaluated at the **new** native times only for diagnostic error
statistics. The reported RMS weights native samples equally; it is neither
uniform-time RMS nor ADC SNDR. Common-window half-VDD events are paired by
ordinal/direction, with counts and time differences exposed. Unmatched events
remain visible. Peak differences use original native extrema and new native
extrema, separately from interpolated curve comparisons.

All comparison/contract results retain `acceptance_pass:null`, including clear
disagreement. This tool neither approves the proposed1mV/2ps/KCL tolerances nor
declares a repaired circuit. Actual settings/version/warning codes come from
managed native simulation state; the complete original simulator log is kept.
CMI counts mean logged occurrences only: simulator warning caps can suppress
repeated messages, and absence of CMI text does not establish safe voltages.

## Budgets and complete recipe proposal

`prepare_current_analysis.py` generates only owned local artifacts:

- `generated/managed_reproduction/measurement.json`
- `generated/managed_reproduction/recipe_proposal.json`
- `generated/managed_reproduction/package_review.json`

The recipe references unchanged original dut.scs/test.scs/approximate PWL plus
this analyzer, measurement and the small frozen original diagnostic table.
Exact combined bytes and every input hash are recorded in package_review.json;
the complete local proposal fits the32MiB input cap. No duplicate PWL is created.

Derived output hard cap30MiB leaves2MiB for managed collection status/log
overhead under32MiB. Complete simulator log has an explicit2MiB individual cap.
All compressed streams and metadata share one exact byte counter. Oversize
data fail explicitly; no budget relaxation or silent deletion is implemented.
Original native raw remains under the managed run lifecycle.

Linux main sets a240MiB address-space limit and checks measured peak RSS against
256MiB; the managed recipe separately declares256MiB analysis RSS/512MiB virtual
ceiling and1800s analysis wall time. Streaming state is bounded by declared
signals/events and a <=4MiB baseline. Real-run compression size, execution time,
Linux RSS and model-port probe realization remain unmeasured until managed
execution. Local Windows synthetic tests are not reported as Linux/Python2 runs.

Parent review found and blocked a source/analyzer field mismatch before dispatch:
the source review stores peak `time_ns`, while the analyzer requires `time_s`.
Generation now explicitly converts `time_ns*1e-9`, validates the actual analyzer
schema before writing, and rejects an ambiguous ns field at that interface.
A focused test reads the actual generated measurement (all1375 signals), feeds
minimal clearly synthetic native rows through reduction and checks all four
peak values/times/errors against the original review. This is interface testing,
not physical reproduction evidence. Measurement/recipe hashes were regenerated.

Before dispatch: parent reviews physical feedback/load cuts, analyzer/terminal
catalog and complete recipe; register/submit serially through the managed queue.
The parent is currently prioritizing the separate97-MOS control reproduction.
