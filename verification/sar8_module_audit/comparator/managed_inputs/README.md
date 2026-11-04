# Comparator D2 managed-input handoff

Local package only. No shared recipe, remote submission, Spectre compilation or
simulation PASS has occurred. Frozen `generated/deterministic_v2` files remain
byte-identical. Parent creates and admits recipes from `d2/parent_recipe_inputs.json`.
That JSON is a proposal/input ledger, not an already registered managed recipe;
its SHA and collection-limit fields are review metadata for the parent.

Proposed IDs: `sar8audit-comp-d2-tt`, `sar8audit-comp-d2-sscold`. Entry is packaged
as `test.scs`; its content is the accepted corresponding v2 deck. Native models
are referenced by the existing includes, never copied. Run serially using the
managed gate; no action in this directory dispatches a job.

## Stream interface and changes

- Reuse read-only `scripts/sar8_physical_repair/loaded_remote.py`. The adapter
  `remote_reduce.py --run-dir ... --output-dir ...` calls it with the same CLI.
  It compiles the packaged `stream.cpp` using g++/C++11 and expects one native
  `raw/*.tran.tran` file. Compilation is deferred to an authorized Linux run.
- The source is the hash-locked loaded rx2 stream, with its native all-point
  voltage extrema/pairs, event crossings and time-weighted VDD integration intact.
  Its original two100ns product bins are replaced by one0–260ns interval, so the
  final60ns is included. `products.txt` defines VDD voltage times source current;
  supplied energy is the negative integral. This is module VDD energy only.
- `mapping.json` covers467MOS x six terminal pairs =2802 records; node pairs are
  deduplicated only for computing peaks, not for assigning per-device limits.
  Original0.99V core and provisional1.98V ordinary/native18 screens remain.
- `selected.txt` controls compact20ps display output. Native half-VDD events use
  `events.txt`; fixed check times and snapshot node names have their own files.
  `wave.samples.tsv` contains native-interpolated values at actual PHI_W/clock
  crossings and pre-input/pre-compare/pre-fall checks. `wave.reset90.tsv` records
  four precharge-node90%-VDD crossings; that level is a measurement definition,
  not a new allowed reset time. No full raw waveform is loaded into Python.

## Expected observations

Input history is `+,+,-,+,-,-`: expected DATA and selected D0 are `1,1,0,1,0,0`.
Sample DATA at actual PHI_W rising half-VDD crossing. D0 at that instant can
still be the previous value; report it and then separately observe D0 before
the diagnostic clock fall. Last DATA half-VDD transition is recorded when present.
These crossings do not characterize setup/hold or noise margins. The12ns
observation high interval is not an allocated comparator latency gate.

`diagnostic.json` exposes wrong DATA, write count, D0 observations, raw/received
levels and reset history; its overall performance PASS remains null. A simulator
or stress-only PASS must not turn into module qualification. A complete native
log/TRACE/stop-time/accepted-step check remains the parent's collection review.

## Size and local checks

Compact binary maximum is conservatively computed from260ns/20ps and selected
column count; it is below8MiB. The adapter asserts all derived output is at most
32MiB. Parent must apply the same32MiB cap to total collection including logs.
Large original raw files stay on the managed SSD. Resources proposed in the
ledger are limits, not permission to launch concurrently.

Local checks: five packaging/synthetic-observation tests plus the12 existing
structure tests. Python source is written in Python2-compatible syntax for the
remote adapter; it has not been executed under Python2 or compiled remotely here.
The C++ extensions have passed local source/interface checks, not compiler tests.

Reproduce local checks with:

```powershell
.venv/Scripts/python.exe -B -m unittest discover -s verification/sar8_module_audit/comparator -p test_*.py -v
.venv/Scripts/python.exe -B verification/sar8_module_audit/comparator/prepare_managed_inputs.py
```

The packager refuses to overwrite different existing package files.
