# Bitwise token/SAR timing and observed approximation

## Goal

Show all eight token and eight stored SAR bits on one aligned figure, together
with the actual trial decisions/ideal-plant DAC voltage and residual. Use the
unchanged native two-frame run; no new circuit or simulation requested.

## Dirty-State Note

Branch `exp/cdac-flat8-device`, starting implementation commit `5ce35d2`.
Untracked CDAC10 config, three VA sources, plan, scripts and verification are
unrelated concurrent work and remain untouched. Target-owned paths start clean.

## Local Owned Files

- This plan and one factual entry in `plan/log.md`.
- `scripts/sar8_simple/bitwise.py`.
- New `docs/figures/sar8_simple/bitwise_approximation.{png,svg}` and
  `bitwise_two_cycles.{png,svg}`.
- `verification/sar8_simple/bitwise_approximation.json`.
- One added figure/reading-guide section in `docs/sar8_simple_async.md`.

## Remote OA Owned Objects

None. Do not change OA, simulation configuration, saved raw waves, exports,
old plots, current circuit sources, or the open Virtuoso/Canvas windows.

## Read-Only Dependencies

- Exact case `two_cycles_simple_v2_aps`, source/export/wave hashes and current
  `verification/sar8_simple/summary.json`.
- Existing `analyze.load`, `plot.envelope`, `plot.save`, and local plant source.
- Native comparator/write/update phases, token and stored-word raw voltages,
  actual P/N reference controls and saved TOPP/TOPN ideal-plant voltages.

## Implementation

1. Derive each decision record from the saved trace20ps before actual write:
   selected bit, actual trial CODE/P-high code, DATA, stored word after capture,
   held VIN, TOPP-TOPN residual, and DAC=held VIN-residual.
2. Check each observed record against switching arithmetic, bit position,
   comparator sign and existing output words. Do not replace measured traces
   with an independently generated ideal bit sequence.
3. Plot one combined two-column conversion-detail figure with four local
   clock lanes, T7..T0, D7..D0, actual DAC trial and residual per frame. Also
   provide a full two-period bitwise overview on one common time axis.
4. Mask the ideal DAC/residual only when reference choices are disconnected
   or inconsistent; show gaps rather than pretend BBM intervals have physical
   capacitor settling. Preserve all digital trace excursions; no averaging.
5. Save concise provenance/decision records, inspect both figures, add reading
   guide, syntax/JSON/link/diff checks and a scoped local commit.

## Validation / Pass Criteria

- Source wave hash equals pinned case summary; result.ok and all requested
  vectors finite. Eight write events, ordered one-hot write selections per frame.
- Trial choices match actual CODE and P/N reference controls. DAC arithmetic
  agrees with observed ideal-plant residual to1e-8V at decision points.
- Stored bits after capture agree with sampled DATA and final145/85.
- Display clearly distinguishes stored SAR bits, trial code, ideal-plant
  voltage, and physical CDAC (not simulated). No claim of new PVT/SOA closure.
- Python compile, focused execution, JSON/SVG parsing, visual inspection and
  `git diff --check`.

## Artifacts

Two PNG/SVG views,16 observed decision records with hashes and finite-trace
checks, doc reading guide. No remote mutations and no new Spectre run.

## Commit / Push

Commit: `docs: plot bitwise SAR timing and observed approximation`.
Push not requested.

## Result

- Completed offline extraction of16 observed decisions from the unchanged
  pinned native TT/.9V/27C two-frame waveform. Final words145/85, actual trial
  choices, comparator sign, all P/N choices, and post-write stored bits pass.
  DAC voltage inferred from saved TOPP/TOPN agrees within1e-8V with the actual
  trial-code arithmetic; no synthesized replacement sequence used.
- Detail and full-period PNG/SVG figures include every T7..T0 and D7..D0 lane,
  four phase lanes, observed DAC and residue. Raw digital extrema retained;
  invalid/disconnected analog plant intervals are visible gaps. Both images
  visually inspected: labels readable, no overlap/clipping, all bits present.
- Added doc reading guide distinguishing stored decisions from trial code and
  ideal-plant voltage from physical CDAC behavior. No remote operations or new
  simulations. Open circuit/Canvas state untouched; unrelated dirty work kept.
- Python compile/focused execution, JSON/SVG parse and scoped diff checks pass.
  Scoped local commit per policy; no push.
