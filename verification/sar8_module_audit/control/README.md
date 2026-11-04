# Control timing audit

`extract_events.py` reads the existing rx2 TT/200 ns and SS-cold/210 ns runs.
It hashes all consumed files, verifies receipt hashes for small collected files,
and checks frozen DUT/deck/observer hashes against each run manifest. The script
does not launch simulation, import a remote runner, or read/reduce raw waves.

From the project root:

```powershell
.venv/Scripts/python.exe -B verification/sar8_module_audit/control/test_extract_events.py
.venv/Scripts/python.exe -B verification/sar8_module_audit/control/extract_events.py
```

The only generated result is `events.json` in this directory. Regeneration does
not modify any old result. Inputs must remain under their original local run
directories. Collection logs may have checksum-suffixed versions; the receipt
selects the correct one. Each input is limited to 4 MiB, output to 1 MiB.

## Definitions

- `conversion_ns` is preserved unchanged: last PHI_U rising minus SAMPLE_INT
  falling. A separate native-event calculation cross-checks this historical
  number; the 0.00001 ns comparison tolerance is numerical, not a circuit budget.
- Every event has `time_ns`, a typed status, an evidence class and explicitly
  named `time_from_SEQ_SAMPLE_close_ns`. SEQ_SAMPLE's native falling 0.5VDD
  crossing is a control-edge reference, not a calibrated physical aperture.
- Native crossings use all original solver points with crossing interpolation.
  Seconds in the event TSV are explicitly converted to ns. First/last bit events
  require eight unique chronological crossings, rather than silently selecting
  one from missing/duplicate events.
- Bottom-ready times are existing 20 ps compact-wave summary estimates, copied
  from hashed local analysis JSON. The summary's next-sample identity is checked
  against native events. Raw/compact waves are not reprocessed or rehashed.
  The summary itself is local derived evidence; its recorded hash is not a new
  independent certification of the prior reduction.
- External SAMPLE times are predictions from the frozen ideal symmetric pulse.
  The 90/98 ns observer schedule is classified separately. It is not an adopted
  silicon output-interface requirement.
- Reset search crosses the 100/200 ns boundary until the next observed actual
  sampling event. If that sampling event is outside the observation, readiness
  remains null; a separately observed RST0 assertion can still be listed.
- `DOUT_valid` is always unavailable in this extractor: neither last PHI_W nor
  the observer's `valid` measures the output-valid timestamp and receiver margin.

## Gates and limits

`bottom_before_next_sample` reports the measured margin, but stays `undecided`
with `pass_: null` because the required protection margin is unallocated. The
data/read gate also remains undecided. No 90 ns, 1.5 ns or zero-margin silicon
criterion is adopted. Missing, ambiguous, wrong-class and nonfinite evidence
cannot become a passing timing gate.

Fixed reset targets and the legacy +/-0.25 LSB observation band remain diagnostic
measurement definitions. Per-bit budgets, RC process extremes, output receiver
requirements and full clock/handshake coverage remain open. The frozen decks
still select TT resistor/MOM process sections. No full-ADC qualification follows
from this table.

Synthetic tests exercise cross-frame resets, observation truncation, duplicate
and missing edges, units, source schedules, provenance identity checks and
unavailable-data gates. They do not simulate transistor behavior.

## Separate sampled DOUT diagnostic

```powershell
.venv/Scripts/python.exe -B verification/sar8_module_audit/control/test_dout_sampled.py
.venv/Scripts/python.exe -B verification/sar8_module_audit/control/dout_sampled.py
```

Run the event extractor first. `dout_sampled.json` is separate from `events.json`;
the latter's qualified `DOUT_valid` remains unavailable. Only the two existing
compact binary exports are consumed, with a combined 32 MiB binary batch limit,
receipt SHA verification, and all eight DOUT columns checked. No original PSF
is read. The compact input grid is approximately 20 ps, not uniformly 20 ps:
each diagnostic reports its actual maximum gap. A resolution integrity bound is
derived from the recorded export spacing plus logged native maxstep; absent
metadata, endpoint coverage or adequate samples produces a null estimate.

Per bit, the estimate is the first in-band sample after the final out-of-band
sample, from SEQ_SAMPLE closing through the samples bracketing the legacy 98 ns
read. The diagnostic band is taken from the frozen observer: strictly within
+/-0.1 VDD of the expected zero/high rail. This is not a receiver VIL/VIH spec.
The expected word comes from the prior two-frame case; no new ADC accuracy
claim is made. An unchanged output bit can match its final value well before
the final write, so sampled word matching is not conversion completion.

The 90--98 ns sample-window check is also only a historical-test diagnostic.
Finite samples do not prove absence of intersample glitches; setup/hold,
qualified DOUT-valid time and silicon acceptance all remain unallocated/null.
The reset extractor fallback now stops at the next observed SAMPLE_INT rise,
or the nominal frame boundary when both next sampling events are unavailable,
instead of searching into unrelated later frames.

## Native replay export package (prepared; parent dispatch only)

`native_export_manifest.json`, `stream_native_boundary.cpp` and
`native_boundary_export.py` form an analysis-only package for the already
completed `sar8fix-loaded-both-ffcold` source. The wrapper interface is:

```text
native_boundary_export.py --run-dir NEW_RUN --output-dir NEW_RUN/derived --source-run-dir COMPLETED_SOURCE_RUN
```

The parent will register a dedicated `kind: analysis_only` managed recipe with
those three files, source_run_id set to that completed source, and the wrapper
as analyzer. Only `analyze` is applicable; no simulation submission is needed.
The frozen wrapper is written for remote Python 2.7 and Python 3 using this
project's ASCII managed paths. A concurrent non-ASCII CLI-byte-path improvement
is preserved separately in `unicode_path_followup.patch` and is not applied to
registered v1 inputs. JSON's unicode ASCII basenames are supported by the frozen
filesystem operations. The parent retains resource admission and remote execution.

The parser holds one native snapshot and reads only a prefix of ASCII PSF. It
exports ten boundary series, six initial-state witnesses and nine diagnostics
(25 voltage columns plus time), from zero through 41.6 ns, with a separate
40.8--41.6 ns native-point table. Required native names are explicit in the
manifest. Missing TRACE/initial values fail; legitimate sparse native updates
hold the previous initialized value, matching ASCII PSF semantics rather than
interpolating. Duplicate values at one native point still fail.

`boundary.native.bin` and `peak.native.bin` are little-endian float64 row tables.
`boundary.columns.json` supplies names, units, roles and primary-series flags;
each of the ten primary columns retains its original native timestamps for
later PWL construction. No resampling or peak clipping is performed. `COMP_P`,
`COMP_N` and `WD` are exported witnesses; they must not drive native outputs.

The wrapper verifies source recipe/registration/native completion and frozen
DUT/test hashes, records raw stat identity before/after, and hashes the exact
consumed ASCII prefix in chunks. It does not claim a hash of unread raw data or
that the parser scanned the original END when it stops at a later time marker.
Output data has a 30 MiB cap; the complete new derived directory (including the
compiler executable and metadata) must remain below 32 MiB. The parser checks
its measured RSS against 256 MiB. `result.json` is written last, matching the
managed worker's exit-zero plus result-file completion contract. A numeric peak
difference is reported, while reproduction acceptance remains unallocated.

Local synthetic validation only:

```powershell
.venv/Scripts/python.exe -B verification/sar8_module_audit/control/test_native_export.py
```

Tests compile the new parser in an owned temporary directory and use synthetic
ASCII data. They exercise exact native points, sparse/GROUP updates, properties,
missing data, duplicate/time/unit failures, caps, the analysis-only interface,
source immutability and path isolation. They do not execute a transistor run.

The revised `boundary_convergence.json` defines 97 MOS: add the original two
receiving buffers and let N4 outputs develop naturally under their MOM/native
loads. WD is also naturally driven. Only seven upstream/input voltages may be
replayed. PR/NR downstream qualification fanout and WD-to-X010 fanout remain
explicit loading differences to assess during baseline reproduction; the
fixture is not an end-to-end asynchronous correctness test.

## Recovered first-event source and prepared isolated fixture

See [first_event_review.md](first_event_review.md) for the native waveform,
timing evidence, unchanged 97-MOS/18-passive boundary, load omissions and proposed
reproduction gates. The source peak is 1.078642 V at 41.089515 ns, before the
first comparison. The 13-file receipt and every initial witness were verified.

`prepare_first_event.py` builds `first_event_v1/` locally and refuses to overwrite
different generated bytes. Seven replay sources retain all native knots; package
paths are checked from managed Spectre's `RUN/inputs` cwd. COMP_P/N and WD remain
native outputs. `first_event_analyze.py` saves bounded native currents and signed
KCL sums, preserves warnings and keeps acceptance null pending parent review.

```powershell
.venv/Scripts/python.exe -B verification/sar8_module_audit/control/prepare_first_event.py
.venv/Scripts/python.exe -B verification/sar8_module_audit/control/test_first_event.py
```

The suggested managed recipe remains inside the control subtree. This session
has not registered or submitted it, modified OA, changed any device, or committed.

## Collected v1 result review

The parent subsequently registered and ran the frozen package. See
[first_event_results_v1/review.md](first_event_results_v1/review.md) for the
collected-source overlay, five-terminal-current integrals and SAMPLE_INT/LTE
warning review. Peak amplitude differs by +1.248169 mV, exceeding the approved
1 mV reproduction screen; time, edges/order, initial witnesses and KCL pass.
The frozen analyzer acceptance remains null and no repair is claimed.

This local review also identifies four omitted SN gate terminals in the X010
and X014 fanouts. Numerical replay sensitivity and these load cuts remain
separate hypotheses. Follow-up suggestions preserve original sampling edges
and request source-native supplementary data plus single-variable comparisons.
They have not been dispatched by this session.

Two source-bound supplementary analysis-only packages are now prepared at
[supplement_export_v1/README.md](supplement_export_v1/README.md). They export nine
source voltages and three v1 voltages without changing any frozen file. Eleven
focused synthetic interface tests passed. Parent review/registration and actual
native export remain outstanding; no SN or load-bias finding is claimed yet.
