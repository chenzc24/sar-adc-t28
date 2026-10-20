# R3 reference gate event repair B

## Goal and boundaries

Verify and repair the reference gate SAMPLE event handling. Preserve native SAR,
Bootstrap, comparator, CDAC, all connectivity and device sizes, reference/input
impedances, clocks and R3 100ps restore guard / 100ps BBM / 50ps gate edges.
Replay the original first12 input frames at TT/.9V/27C, no noise/mismatch, using
the original APS4 conservative/10ps solver settings and original51600ns declared
stop with the previously verified passive1200ns early finish. Compare R3 and B
for midpoint restoration, overvoltage, held charge error and output codes.

Branch exp/cdac-flat8-device, parent0eb69c5. Unrelated untracked cdac10_dualrail
config/models/scripts/verification/plan belong to the user and remain untouched.
Existing R3 OA, shared gate/commit sources, all previous raw runs, and ongoing
full static/dynamic jobs are read-only. No cancellation, OA mutation or push.

Owned local paths: this plan; models/veriloga/r3_refgate_events/;
scripts/integration/r3_refgate_events.py; scripts/integration/r3_refgate_analyze.py;
verification/integration/test_r3_refgate_events.py;
verification/integration/r3_refgate_events_results.json;
docs/r3_refgate_events.md; docs/figures/r3_refgate_events/; plan/log.md.
Generated ignored artifacts: output/r3_refgate_events/. Remote OA owned: none.
Remote activity is isolated Spectre scratch runs and read-only status/log checks.

## Method and validation

1. Verify t28_io bridge/session/Spectre and original deck/include hashes. Read
   event/state guidance and native simulator API. No CIW help invocation.
2. Snapshot original reference gate and add passive event/state logging only;
   add an independent B gate with direction-specific SAMPLE rise/fall handling.
   Preserve output equations, interface, parameter values and reference commit.
   Use a small native Spectre gate unit test before expensive ADC runs.
3. Freeze the original12-frame differential source history, including adaptive
   bisection-derived values, in a testbench-only VA snapshot. Keep original input
   event times and100ps transition shape. Never replace actual comparator or
   native SAR decisions with ideal decisions. Replay A and B with the identical
   frozen input source; A must reproduce the original anomaly or sensitivity
   must be reported explicitly. Native subcircuits and non-observer wrapper
   statements must compare equal, including all MOS W/L.
4. Instrument original SAMPLE events without new threshold/timer events; check
   sampling/restored/deadline records to establish the failed branch. Measure
   all16 banks at end acquisition and save actual analog/stress waveforms.
5. Require result.ok,12 complete frames, identical input history and solver
   precision. Report codes, actual comparator count, acquisition/held error,
   midpoint correctness and MNINP/N overvoltage; retain all CMI/LTE warnings.
   Success for repair means missing-midpoint/late-restore failure removed, not
   automatic full ADC/PVT/reliability qualification. Adjacent-code ambiguity
   near the searched transition is distinct from a gross outlier.
6. Save concise provenance/metrics and inspected timing comparison figures,
   report in existing docs style (write-page guidance; no cloud Page). Run
   focused source/deck identity and history tests, syntax and diff-check,
   record factual log, scoped local commit only:
   `fix: handle R3 reference timers without deadline rejection`.

## State

Preflight: bridge0.8.0 t28_io healthy, correct user/thu-wei/llm_IO CIW and native
Spectre21.1 at00:03local Oct21. No OA or shared original source changes.

Unit A/B Spectre runs complete, result.ok each, no errors, one deprecated AHDL
environment warning each. Four SAMPLE timing offsets and two initial-high
polarities:96 midpoint samples each, no H/L overlap. B logs96 rises/96falls,
all phases correct. Unit does NOT reproduce the original numerical corner.
The log reader was corrected to accept native progress prefixes before strobe
records; a floating-point literal equality test was changed to15decimal digits.
Three focused contracts pass (native/source identity, frozen history/directional
phase, progress-prefixed event parsing); syntax and diff-check pass.

Full A/B first12 runs active, four APS threads each, local runner session90408.
Remote isolated scratch IDs4c9327b8(A),54a6224e(B). Original4long jobs untouched.
Native DUT/wrapper statements are byte-identical to previous original-stop
replay. Only includes resolve to owned passive-instrumented A / explicit-phase
B gate and same frozen testbench search-history source; existing monitor,
reference commit and passive stop observer are unchanged. Save85 signals in
800-1200ns; all12frames still solved, logged and monitored from initial startup.

Critical live-state evidence at801.15ns supersedes the initial SAMPLE-cross
hypothesis: A enters sampling correctly at801.050000250055ns, schedules restore
801.150000250056ns. The timer callback arrives801.150000090759ns,0.159297fs
before its floating-point deadline. The secondary >=deadline-1e-18 comparison
rejects the valid callback; restored remains0. B (phase-only fix) shows the SAME
miss. Preserve both failed variants and finish their12frame runs.
Expand the already owned model directory/flow to a corrected b2 implementation
with event-owned restore/turn-on callbacks, not a guessed relaxed solver
tolerance or changed nominal100ps/50ps timing. Read installed Cadence timer
event reference via read-only SSH, never CIW help. Add native unit and same
12frame corrected-B run; keep existing A/B results immutable and compare all variants.

Revised candidate b2's small unit exposed a sample-fall initial-word interlock
release omission (also present in the phase-only b): acquisition checks alone
had passed, but48/96 subsequent conversion request samples stayed at initial
rail. b2 was NOT run as a full ADC. Preserve this unit evidence; b3 restores
the sample-fall interlock release and is the selected corrected B candidate.
Its separate SAMPLE directions, COMMIT notifications and event-owned restore /
turnon handlers have no secondary floating-point timer deadline rejection.
Original port/default parameters, output equations, physical timing unchanged.

All4unit native simulations result.ok; A and final b3 pass both96acquisition
and96conversion samples, no overlap; b3 logs96rise/96fall. Their entire saved
unit waveforms have the SAME SHA256. The installed Cadence veriaref chap8 timer
event documentation was read through SSH (no CIW help). b3 full12frame job
started00:31local, runner session39080,4APSthreads, identical frozen input and
solver settings. Full A already reproduced frame8code1 and CMI; phase-only b
still fails with frame8code2. The physical timer miss is confirmed, not a
remaining SAMPLE-level hypothesis. All original/global sources remain intact.

## Completed result

A and phase-only b native12frame runs result.ok,0errors/12warnings/7notices,
CMI retained. A reproduces all12original codes and its217838point time grid /
49common saved waveforms EXACTLY (maximum difference0). A frame8 held error
-442.8504966mV, MNINP VGD-.99914984V at841.193394ns, finalcode1. Original16bank
state logs prove sampling entered and the801.15ns valid callback was rejected
by the1e-18s secondary deadline guard. Phase-only b stillfails: code2, held
-442.3207354mV, |VGD|.999025V. Neither failed variant is adopted.

Final B=b3 native12frame run result.ok,0errors/7warnings/6notices, NO CMI or LTE.
All reported solver parameters match A/original. Codes64,64,64,64,64,65,64,65,
65,65,65,65; all12frames8compares, visible4frames8writes/8updates. All16banks
correct before sampling opens;85signals218631points800-1200ns. Phase384,
restore192events complete;32early timer callbacks correctly processed without
time rechecking. Frame8 held+.101355347mV(.01441498LSB), handoff MNINP maximum
|VGD|.671721901V, read65. Visible4frame held errors+.101302..+.101355mV all
within.25LSB=1.7578125mV. Joint maximum saved input-pair |VGS/VGD/VDS|.886745V
below.99V screen. Remaining7warnings are1deprecatedAHDL,2global-terminal and
4originalPDKscalefactor messages, not ignored circuit/precision warnings.

Final B compute1153.9s/download27.5s/parse95.2s. Raw all runs remain ignored
under output/r3_refgate_events/. Full provenance/metrics294KB manifest,
Chinese report and3scientific timing figures with real baselines/phase shading
saved; final3images inspected at original resolution. Unit normal A/B3 complete
waveforms identical; b/b2 interlock regression preserved and disclosed.

Bounded repair passes, NOT full ADC performance/PVT/noise/mismatch/lifetime.
No native controller, physical topology/WL, clocks, source impedance or shared
R3/OA/full-campaign mutation. No pushes. Final syntax,3focused contracts,
source/figure hashes, diff-check and scoped review close this target with the
intended local commit; unrelated cdac10_dualrail work remains excluded.
