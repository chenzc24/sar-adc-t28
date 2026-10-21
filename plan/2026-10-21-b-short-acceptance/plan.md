# B one-times short integration acceptance

## Goal and authorization

Execute only steps0/1 approved by the user: read-only current B/1um baseline
audit and bounded native short transients for code jumps, timing, terminal
stress and power. Preserve the original anomaly's complete12-frame input
history from t0, not just frames9-12. No long FFT/static sweep, PVT, mismatch,
noise, width/timing/topology changes, OA writes, push or new automation.

Starting HEAD ca4c733, branch exp/cdac-flat8-device; index empty. Existing
Obsidian note moves/report edits and cdac10_dualrail files are unrelated user
work and remain untouched. Old sources/results/figures are read-only.

## Ownership

Own this plan, config/b_short_acceptance.yaml,
scripts/integration/b_short_acceptance.py,
scripts/integration/b_short_acceptance_analyze.py,
verification/integration/b_short_acceptance_results.json,
docs/b_short_acceptance.md, docs/figures/b_short_acceptance/,
narrow docs/project_status.md and plan/log.md entries. Generated
output/b_short_acceptance/ only. Remote OA owned:none. Remote writes only
unique bridge Spectre scratch with exact run/PID receipts. PDK read-only.

## Frozen bench and cases

R3+B gate model, Mmain1um/L150nm on both sides, same CDAC/3x reference
switches/StrongARM/native SAR, ideal SAMPLE/reference gate drive and50ohm
input/reference resistances plus4pF reference capacitors. TT/.9V/27C,
APS4/conservative/maxstep10ps/gear2only/requestedreltol1e-5/effective1e-6,
vabstol10nV/iabstol100fA. Declaredstop51.6us and passive early-finish method
retained to preserve dependent solver defaults. Continuous saved output,
never strobeonly. Only stimulus/measurement/save/finish-window differences.

Three bounded cases,44 total native frames, at most2 native workers and1
local parser: history12 (original frozen source byte-identical); directedA16
and directedB16 (4warmup+12observed each). Directed A covers signed large
cross-frame steps, code0/255 centers and midscale alternation. Directed B
uses both sides of k=1/32/64/128/192/255 transitions at±.25LSB. New directed
sources update100.8-100.9ns after prior frame (100ps PWL transition), leaving
existing SAMPLE timing and acquisition duration unchanged. They are not
relabelled as the historical analog source waveform.

## Method and checks

1. Read Spectre/virtuoso/EVAS/document skill instructions. EVAS cannot solve
   this PDK hierarchy; use native APS unchanged. Check bridge status/windows,
   exact profile/host/CIW/library/technology. Tunnel initially down; allow one
   scoped start. Stop for unrelated modal, ownership mismatch or changed DUT.
2. Supported read-only OA API verifies top/TB and36 dependencies against B
   snapshots; verify current VA source and all local immutable include hashes.
   Native blocks and device dimensions must match B; no handwritten OA edits.
3. Freeze all inputs and cases before launch. Save source/rail currents and
   relevant reference/comparator/bootstrap internal nodes without adding any
   DUT load or perturbing existing observers. Include all original12 inputs
   and source events from t0. No automatic rerun or circuit repair.
4. Each frame:8compare/write/update, 90/98ns code stability, valid logic rails,
   conversion complete within60ns. Compare against ideal source/actual held
   input; threshold-adjacent ambiguity is reported separately from gross jump.
   Verify B bank restore/hold states and original frame9 behavior.
5. Inspect complete-time selected analog terminal pairs and native CMI/LTE/
   convergence warnings. Core.99V is an engineering screen; 1.8V IO devices
   use separate reporting, not that core limit. Explicitly limit any incomplete
   all-device reliability coverage.
6. Integrate signed power delivered by VVDD, VREFHIGH/VREFLOW, VSAMPLE and input
   sources, separating startup, acquisition, conversion and warmed frames.
   Include P/N reference-gate ideal VA output currents if accessible through
   verified Spectre saves, with their injected/recovered energy shown apart.
   Do not call ideal drivers zero-power or claim real totalADC<=1mW from VDD
   alone. If currents are unavailable, report exactly what cannot be measured;
   no topology change for a meter and no unapproved extra experiment.
7. Validate result.ok, allframes, source identity/history, reported precision,
   actual current polarity/energy units, timing and saved signal coverage.
   Reconcile with prior B12 result and retain raw failed screens. Plot real
   ideal baselines/sample/read times, visually inspect, curate small results,
   update factual log/status and local scoped commit only.

The expanded136-signal save list would exceed available local RAM with the
bridge's whole-file/tuple-list ASCII parser. Use a plan-local streaming parser
with identical delta carry-forward semantics and float64 arrays; cross-check
against the bundled parser and saved baseline samples before launch. Keep the
native runner/result error classifier unchanged; no format, sample, solver or
raw-data change. This is a local parsing memory bound, not relaxed simulation.

## Status

Completed. Spectre and Virtuoso skills select supported native simulation and
read-only OA readers; document skill separates measured results and ideal
power/model limits.

One tunnel start restored healthy0.8.0/t28_io, exactthu-wei/chenzc_intern25/
llm_IO CIW and Spectre21.1. Only CIW window present. Supported APIs verified
top/TB,36dependencies and the downloaded current B VA byte hash. Three frozen
decks total44frames,136saved signals each, cover67analog MOS:24bootstrapIO,
32referencecore and11comparatorcore. All native blocks,1um/L150nm, clock
statement and solver precision match immutableB. History stimulus is exactly
the prior frozen12-frame source. Streaming parser matches bundled parser on
delta/current synthetic data and2048real baseline points. Local~15GBfreeRAM
requires bounded float64 storage; no solver/saves/raw weakening for speed.

Launch2026-10-21 16:10:26 local, committed inputs1fe7174, coordinator57916.
Native history12 Spectre94720 binds scratch6d2a1520; directedA94834 binds
a26c416f. DirectedB queued automatically after history12 native/download,
Spectre215458 binds ee5f6303. No duplicate, restart or OA write.

History12 finished normally (871s native elapsed; downloaded full0..1200ns),
663230 points/136signals, result.ok true. Local streaming parser was adjusted
before parsing to skip native current TRACE PROP metadata, validated on a
synthetic attribute case and the actual schema; no input/raw/solver change.
Its actual LF SHA is recorded with waveform SHA. All12 history codes equal
prior B, including human-frame9 code65 rather than old R3 code1. Initial
offline checks pass: 8/8/8 counts, MSB-first, midpoint restore, held/error,
selected67-device terminal screens; native0errors/7knownwarnings, noCMI/LTE.
Power currents all38 present. Analysis also explicitly checks per-bit
compare<write<update<nextcompare and both90/98ns output rail levels.
DirectedA16 also finished, all16codes equal ideal nominal and all screens
pass; raw held peak.234215mV, precompare peak.118364LSB, maxcore.952012V,
IO1.790505V. Its streaming parse took~210s with~1GB bounded storage; all raw
data retained. DirectedB16 completed native/download/parse by16:51:50 local,
all16codes ideal and all declared screens pass. Three cases total44frames,
2434483points with136signals each; all result.ok true,352compare/write/update
events each,1408phase/704restore events, noCMI/LTE/convergence failure.
Each case retains7knownwarnings (1VACOMP2435,2SFE2453,4SFE1131).
Native notice counts5/6/6 retain initialDC gmin effects and two directedDC
bad-pivot notices, also seen in priorB baseline; no solver change/rerun.
Initial ad-hoc footer check over-specified5notices for allcases; corrected
offline validation to exact case counts, not a native/circuit failure.

Observed rawheld peak.234215mV, precompare settling peak.118632LSB;
allframe conversion29.460006..29.928026ns vs60ns budget. Global selected
analog terminal peaks reference.947124V, comparator.952012V, bootstrapIO
1.790505V, within separately declared engineering lines. Not all logic
terminal or foundry reliability qualification. Original history frame7 is
exactly an ideal boundary and differs by1adjacentcode; no gross jump.

All38currents saved in eachcase. Warm net VDD.079727/.080071/.080004mW,
reference.020743/.014247/.016287mW. Ideal clock/ref-output positive/recovered
energy and external source energy kept apart. No physical driver/buffer
overhead or complete realADC<=1mW claim. Figures show ideal baselines, actual
sampling/read times, held-to-firstcompare shade and signedpower. Visual
review covers all5figures; regenerated hashes match the exact reviewed PNGs.
Source/native/precision checks, power sign/unit/window identities, all44frames,
2434483points, all38currents,5figure hashes, UTF8/YAML/JSON/links and compile
pass. Exact remote-root process check confirms all3native runs exited; local
coordinator/parsers also exited. Index was empty before scoped staging.
Report/JSON/status/log and scoped local results commit only, no push. User
note moves/images and unrelated cdac10 files remain untouched/uncommitted.
