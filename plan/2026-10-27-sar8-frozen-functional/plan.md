# SAR8 historical functional freeze and static characterization

## Goal and decision
User authorizes freezing the pre-stress-repair version with SS acquisition and
FF reference-leakage fixes, then TT full-code characterization after inspecting
the first few codes. Overvoltage is deferred, not waived or declared qualified.
Freeze e94e8028e6dcc9aa843116a7d0c46c865df5f7b7 DUT: Mmain two explicit 1um
units per side, reference-switch L90nm, inherited idle reset. No new circuit edit.
The existing sar8 automation stays paused. No commit/push or baseline adoption.

## Ownership and dependencies
Dirty shared management execution/policy, AGENTS.md, Obsidian, comparator and
manual ADC/10bit experiments are unrelated and preserved. Existing plan/log.md
is shared append-only. Current managed two-slot policy applies; this work submits
serially and never bypasses admission. Managed tools are a read-only dependency.

Owned: this plan; netlist/sar8_l90_mmain2_frozen/;
scripts/sar8_frozen_static/; verification/sar8_frozen_static/;
docs/sar8_frozen_functional.md; management/designs.yaml (one new entry only);
management/recipes/sar8frozen-*.yaml; management/runs/sar8frozen-*.yaml;
output/sar8_frozen_static/ and managed output/remote run directories for those IDs;
plan/log.md (append only).
Remote OA objects: none. PDK, libraries, OA, all historical data and original
netlists are read-only. Server Spectre via managed register/submit/analyze/collect.

## Steps and criteria
1. Freeze original DUT bytes and SHA256, source provenance and historical evidence.
2. Reuse existing input-search VA and nonloading event monitor unchanged. The ADC
   itself is entirely transistor-level. Fixed TT 0.9V/27C, 10MS/s, reference
   0..0.9V, differential range -0.9..0.9V, original source/load/clock timing.
3. Run boundary1..3 (codes0..3), four warmup frames separately reported, seven
   bisections. Inspect exact native codes, phase counts8/8/8/16, stable90..98ns,
   actual sampled input versus requested trial, bracket validity and completeness.
   Failure remains evidence; no automatic circuit modification or large launch.
4. If clean, extend boundaries4..255 in bounded serial segments, combining the
   smoke's1..3 measurements without repeating them. Verify255 unique boundaries,
   all256 code centers and monotonicity, raw/endpoint INL, DNL, offset/gain and
   measurement bounds. Saturated end-bin widths are not finite-width DNL.
5. Provide staged five-point PVT and Monte Carlo plan for milestone report;
   neither large PVT nor MC is launched by this initial characterization request.
6. Retain native warnings/effective solver settings. Do not transfer027b951 FFT
   metrics to this version. Noise/mismatch/PEX and stress qualification remain open.

## Validation and artifacts
Byte hash equal to all five historical L90 DUTs; compare to Mmain2/L30 predecessor
with only16 reference L parameters changed. Source files unchanged. Compile/check
Python; managed native zero-error completion; streaming PSF/log cross-check;
targeted diff/check. Sim<=1GiB,4threads; analysis<=256MiB; collection<=32MiB.
Frozen manifest, per-case inputs/results and concise milestone report at owned
paths. Full-code completion depends on first-code result, not mere simulator exit.

## Checkpoint
Snapshot frozen and inverse/5-case hash checks pass. First TT case registered
36689b1340b15945152fcc051cf1c2a5cefee5e7e8fccd9df541cc60f5adb1f3,
managed simulation running. Finite serial flow PID33560 follows this run,
analyzes/collects/reviews low codes, and only if functional_pass proceeds through
the eight prepared remaining segments in verification/sar8_frozen_static/batch.json.
This is a one-shot authorized batch, not a resumed automation. All failures and
uncertain transport states stop the flow without duplicate submission.
Read flow_status.json before resuming; do not start a second flow (flow.lock).

Initial native observation: frame0 input -0.896484375V (code0 center), output2,
counts8/8/8/16, held_diff -0.878146048634V. Startup error remains; this preliminary
record is not a steady-state verdict. Frames0..3 are preserved separately.
Python compile and focused native decoder/timestamp/truncation rejection checks
pass. Source hashes, exact boundary partition and unchanged testbench VA checked.
Full-code metrics and final plots remain pending; no dynamic/PVT/MC claim.
