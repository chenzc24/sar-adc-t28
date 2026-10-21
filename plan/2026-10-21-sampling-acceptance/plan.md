# Sampling acceptance and main width review

## Scope

Reorganize sampling acceptance into equivalent delay, gain/DC, and
nonfundamental remainder. Use only the committed 500 kHz and 4.5 MHz B
width results to decide whether 1x is adequate at the measured nominal points
and whether 2x is necessary. No simulation, bridge/GUI operation, OA change,
new circuit experiment, automation, push, or claim of full ADC qualification.

Starting branch exp/cdac-flat8-device, HEAD b00c0f4. Existing Obsidian note
moves/deletions/report edits and cdac10_dualrail sources are unrelated user
work; leave them untouched. The untracked SAR-logic compact-figures plan is
also outside this target. Initial index is empty.

## Ownership

Own this plan, config/sampling_acceptance.yaml, a comment-only pointer in
config/design_spec.yaml, scripts/integration/sampling_acceptance_review.py,
verification/integration/sampling_acceptance_review.json,
docs/sampling_acceptance.md, the active eight-bit clarification in
docs/error_budget.md, a supersession notice in docs/b_hf_main_w.md, narrow
docs/project_status.md entries, and the append to plan/log.md. Generated
output/sampling_acceptance/ is allowed if needed. Remote OA owned: none.

Read-only: all prior results/figures/configurations/netlists/waveforms,
simulation runners and fit code, PDK, all remote state, and user notes.
Preserve the old raw-gate failures and historical 2x recommendation; record
the changed acceptance interpretation separately rather than rewriting data.

## Method and acceptance

Keep the eight-bit system targets and noise/jitter/CDAC/comparator budgets
numerically unchanged. Equivalent delay is report-only until an application
requires absolute time alignment; distinguish phase delay from jitter and
conversion latency. A separate per-frequency fit is diagnostic, not proof of
one broadband constant delay or a calibration implemented in hardware.

For the nominal sampling stage, reuse the 0.25-LSB voltage guard as a
phase-aligned peak screen with gain and DC retained. Also report gain at the
full-scale endpoint against a provisional 0.25-LSB gain-only allocation,
explicitly an engineering allocation rather than an industry theorem.
Nonfundamental RMS is compared with the existing shared 0.15-LSB system
distortion reserve; do not silently allocate that entire reserve to sampling
or invent an independent sampling-only hard gate. Keep jitter at 20 ps RMS
and retain settling/reference and static/dynamic full-ADC gates separately.

Refit the saved 20-point records at their actual frequencies with DC+sin/cos.
Use each width's 500 kHz lag unchanged at both measured frequencies for the
joint voltage screen, avoiding independent high-frequency phase optimization.
Keep the per-frequency delay/gain/remainder fits as separate diagnostics.
Recover delay/gain/DC/remainder and exact phase-only error, cross-check old
metrics, preserve low-frequency LTE warnings, and compute both fit-endpoint
gain and sampled phase-aligned peak. No per-point time warping or removal of
gain/DC from the joint voltage screen. Decisions must distinguish measured
nominal sufficiency, optional margin improvement, and untested qualification.

## Validation and delivery

Record source SHA256s and protect old files. Compile the one new analysis
script, run synthetic gain/delay/DC/harmonic recovery including a failing
gain/DC screen case, then recompute all six saved cases without loading the
native solver. Check same history within each frequency, 24 completed frames,
8 compare/write/update and stable codes, old metric equality, exact fit
reconstruction, config/system-target identity, and reproducible JSON output.
Review numerical units, new engineering-allocation labels, shared-budget
language, and links. Run focused diff-check and inspect the complete owned
diff. Append factual log and create a local scoped commit only, preserving
unrelated concurrent work and any staged paths belonging to other targets.

Intended commit: docs: separate sampling timing and accuracy acceptance.

## Status

Complete. Skill write-page is used for concise evidence-versus-allocation
wording, honoring the repository-local document format and not creating a
cloud Page. No simulation skill or simulator is needed for curated-data fits.

Added executable acceptance policy and a standalone read-only fit/review
script; generated one separate curated six-case result. Every old result
hash stays unchanged, with committed text checked after normalizing Windows
checkout newlines. The parsed design_spec is identical to HEAD; only a policy
comment pointer was added. No old runner/test is silently reclassified.

1/2/3x at4.5MHz: fitted gain-endpoint error .196630/.105786/.110051LSB;
one500kHz-delay joint peak .194082/.100311/.102902LSB; nonfundamental RMS
.015750/.005433/.004160LSB. All pass the provisional gain/joint nominal
screens. 1x uses10.50% of the shared .15LSB RMS reserve, not an independently
allocated sampling budget. At500kHz joint peaks .030324/.055089/.080485LSB.
Retain1x nominal baseline;2x improves margin but is not required by existing
nominal evidence. This supersedes the historical2x candidate, not its data.

Synthetic phase/gain/DC/H2/H3 recovery and fail cases prove DC/gain are not
hidden by the phase-only screen. Recomputed all6 old fits, raw failures
14/10/0 and20/20/20, and low-frequency2x LTE warning. Actual frame timing and
8/8/8 event records remain valid. Compile, repeatable JSON --check,
UTF8/YAML/local links, source SHA, unchanged system values and focused diff
checks pass. No broadband/PVT/noise/mismatch/fullcode/FFT/power qualification.
Report/status/budget policy links and historical notice updated; local scoped
commit only. Unrelated concurrent user/report/code changes are preserved.
