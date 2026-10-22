# R4 full-code and coherent-sine characterization

## Goal and ownership

Characterize the unchanged, OA-verified R4 transistor ADC at TT/0.9 V/27 C:
all 255 transition boundaries and a 1024-point coherent near-Nyquist sine.
Check Spectre X availability and compare its accurate preset with APS before
choosing the production solver. Report measured performance even if it fails.

Dirty state at start: user Obsidian reorganization/edits and a separate untracked
cdac10_dualrail experiment. These do not overlap this target and remain untouched.
Branch exp/cdac-flat8-device, parent e276458. No push requested.

Owned local paths: this plan, scripts/sar8_r4_performance/,
models/veriloga/sar8_r4_performance/, config/sar8_r4_performance.yaml,
verification/sar8_r4_performance/, docs/sar8_r4_performance.md,
docs/figures/sar8_r4_performance/, and a factual append to plan/log.md.
Generated output: output/sar8_r4_performance/ (ignored).
Remote OA mutations: none. Read-only library SAR_ADC_T28, technology tsmcN28,
R4 hierarchy and tb_sar_adc8_join_r4; all PDK files read-only.
Read-only circuit source: netlist/sar8_physical/ and its provenance, plus the
original two_phase export and nominal06 results. Keep all device parameters.

## Method

1. Verify hashes, bridge/profile/simulator, and exact saved OA export where
   the live CIW is available. If unavailable, use the frozen audited DUT and
   report the live OA verification boundary explicitly.
2. Use external testbench-only source and observer models. Count actual
   comparator/write/update/capture edges; verify stable output and rails at
   90 and 98 ns. Observer contributes no current or voltage to DUT nodes.
3. Short matched APS and X accurate-preset runs: compare output words and
   analog held/residual values, log effective settings and elapsed time.
4. Scan all code centers and bisect all 255 ADC transition boundaries using
   actual output feedback. Validate brackets before accepting DNL/INL;
   widen/retry explicit failed brackets if needed. Preserve failed runs.
5. Continuous -1 dBFS differential sine, fs=10 MHz, N=1024, k=461,
   fin=4.501953125 MHz, at least four startup frames. Rectangular coherent
   FFT, DC removed, harmonics retained in SNDR, no code calibration.
6. Independently decode saved outputs and cross-check FFT with ADCToolbox.
   Save only lean strobed waveforms for long runs; edge counting is continuous
   via a passive observer. Separate short full-waveform checks from strobed
   performance runs; do not claim peak-stress coverage from strobed data.
7. Plot transfer/DNL/INL, sine/code staircase, spectrum with explicit test
   conditions; record solver warnings, convergence and provenance.

## Validation and completion

Require result.ok, full requested duration, all measurement rows present,
8 comparisons/writes/updates and 16 reference captures per measured frame,
stable valid output, complete code coverage and valid ordered transition
brackets. Targets: no missing codes, |DNL|/|INL| <=1 LSB, ENOB>=7 bits.
Targets are not assumed to pass. Report nominal noiseless results separately
from PVT/mismatch/transient-noise qualification, which is out of scope.
Require focused parser/metric tests and source compilation, source hashes,
scoped diff checks and review. Commit only owned artifacts after recording
actual completed results; intended commit: test(adc): characterize R4 static
linearity and coherent-sine performance. No automatic baseline adoption.

## Initial solver and smoke observations

Live OA export matches frozen R4 subcircuits. Spectre21.1 X AX/CX are callable.
Preset defaults ignore some requested netlist options; log actual effective
settings. APS reference uses reltol1e-7/gear2only/maxstep10ps. Default CX uses
reltol1e-4/gear2only/adaptive steps, and AX uses reltol1e-3/trap. A separate
AX preset_override and CX tolerance-only override test retain tighter controls.
Do not describe default-preset acceleration as equal-tolerance acceleration.

The continuous-sine smoke reports native CMI-2755 near401.36ns, around the
next acquisition initialization, on XCDAC.XSP6.MP_HIGH and XSN6.MN_LOW.
Reported body-drain excursions reach about1.003V versus0.99V. This is a
physical diagnostic to retain. Continue valid functional/static/FFT
characterization and mark device-stress qualification failed; do not alter
the ADC or silently discard the warning. Numerical/functional failures still
require investigation before accepting spectrum/linearity metrics.

## Production launched, 2026-10-21 23:21 CST

APS pilot4 completed in1407.687s wall; default CX4 in101.186s, AX4 in75.910s,
AX with preset_override in440.999s, CX1 in205.448s. Every case gives145/14/241/14
with all frame checks passing. CX4 versus APS max held/residual differences
2.16251/2.00250 microvolts, under0.01LSB comparison gate. These speeds use
different effective tolerances. The extra tolerance-only CX pilot remains
independent; the completed tighter AX pilot satisfies the production preflight.

Static smoke12frames covers boundaries128/129 and centers127..129, all valid.
Sine smoke36frames (4warmup+32measured,15/32fs) passed frame/FFT cross-checks;
its short-record performance is not the final1024-point claim. CMI remains
explicit. Initial DC relaxation in some auxiliary solver pilots is recorded
separately from transient LTE/convergence issues.

One-shot flow.py is running four independent native jobs at a time, each4threads.
Exact cases: sine_cx_1024_k461 and static_cx_001_032,033_064,065_096,097_128,
129_160,161_192,193_224,225_255. All decks and VA snapshots are immutable and
all DUT subcircuits remain identical to the live OA/frozen export. Local
orchestrator was reloaded only while waiting for preflight to retain physical
CMI failures as reportable results and avoid waiting on an optional pilot;
no native simulation was stopped. State is output/sar8_r4_performance/flow_status.json.

Remaining: wait for complete native records, investigate any invalid search
brackets/frames, inspect generated plots, review results and scoped diff,
update factual log, commit owned files. No full-code/1024-point result yet.

The current-thread heartbeat `r4` (R4 全码扫描与频谱收尾) checks this running
task every30minutes and must be paused after final delivery. It is separate
from the pre-existing paused B/512-point automation. The local flow handles
native execution and report generation; the heartbeat handles evidence/plot
review, bounded recovery if needed, final log/commit and delivery. Keep this
PC/Codex running for local queue dispatch and result collection.

Concurrent unrelated commit3577987 (approved historical waveform cleanup)
appeared after work began; preserve it. It did not change this target's frozen
DUT or owned sources. No push or baseline replacement is authorized.

## SSH interruption recovery, 2026-10-22 06:10 CST

The first flow stopped after SSH reset/download failures; later four ranges
failed upload. Remote read-only audit confirms no remaining Spectre process.
Native sine logStatus reports tran_perf PASS with all1028frames and PSF END;
001_032 has a zero-error native completion. Recover these into separate local
recovery directories/receipts, preserving the original failed bridge result.
Never infer whole-process exit code from a native analysis PASS.
033_064 and097_128 have incomplete native records and no running process.
Retry those two and the four upload failures under fresh case identities;
retain every original case. No circuit/source/solver change is permitted.

Owned scripts may add a bounded recovery coordinator, detached remote wrappers
with explicit exit-code files, and final case mapping. Use bridge SSH transfer
APIs, max4 native jobs/4threads, redirect stdout remotely to survive client
disconnect. Only task-owned scratch is written; no OA/PDK mutation. Analysis
must distinguish recovered native PASS from the failed transport result and
preserve all CMI warnings. Final metrics are still pending.

Recovery entry point: workspace `.venv/Scripts/python.exe`
`scripts/sar8_r4_performance/recover.py status` (read-only) or `collect`
(collect finished cases, then generate final report only when all are complete).
Do not rerun `initialize`, original `flow.py`, or any original failed case.
The six active fresh cases append `_r2`; exact remote paths and case mapping live in
`output/sar8_r4_performance/recovery_20261022_r2.json`. `status.py` also supports
these new identities using the bridge-only Python. The remote detached batch
executes first4 then remaining2; at most4Spectre processes/4threads each.
The heartbeat must call `recover.py collect` for completion, since the old
local one-shot flow has exited. Transport-failed originals are never rewritten.

The first `_r1` detached wrappers failed input-file lookup (CMI2011, exit2):
the sourced Cadence csh startup changed cwd to the home directory. No ADC
transient ran. Preserve r1 console/exit files and manifest; r2 restores cwd
after sourcing and uses absolute input/log/raw paths. No other task's files
are cleaned up or modified. This is a runner-path fix, not a circuit change.

## Final report review, 2026-10-22

All recovery native jobs have exited0; collect remaining193_224/225_255.
Observer aperture_time_s is the internal SAMPLE falling50% crossing, not a
calibrated physical aperture. Label it explicitly; the ideal-code comparison
is a clock-time reference, not an error ground truth. Use transition brackets
for the static transfer plot instead of code-center midpoint boundaries.
Keep raw data unchanged. Independently validate frame/edge counts, center
coverage, source identity and FFT; inspect all three figures. Reference stress
diagnosis commit4ff06f4 remains separate and may be linked, not modified.

## Complete — 2026-10-22

- All8static cases and full1024-point sine analyzed:255 valid ordered disjoint
  transition brackets,256/256 observed codes and matching center probes.
  Total3618frames including startup (2590static+1028sine); measured-frame
  8/8/8/16 edge counts, stable output and independent PSF decoding pass.
- DNL -0.0234375..+0.0234375LSB; raw transition error max0.12109375LSB;
  endpoint INL max0.02102768LSB; bracket width0.0078125LSB. Endpoint gain
  error-0.0953494%; sub-bracket ripples are not resolved physical features.
- SNDR48.728620dB, ENOB7.802096bit, SFDR65.592698dB. Direct FFT agrees with
  ADCToolbox to7.11e-15dB. Performance targets pass, electrical qualification
  FAIL: CMI in static033_064,065_096,097_128 and continuous sine.
- All8static native logs end0errors, all6recovery wrappers exit0. Original
  sine native tran PASS/full PSF/1028frames accepted under explicit recovery
  boundary: missing final process exit/zero-error summary remains reported.
  No transient numeric diagnostics; initial DC relaxation in161_192 retained.
- Actual defaultCX reltol1e-4/gear2only, effective maxstep325ns(32boundary
  segments),315ns(last segment),1.028us(sine). Requested10ps is not effective.
  Short pilot speed comparison does not establish equal-tolerance acceleration.
- Three final figures visually inspected; sine legends moved outside data;
  clock50% marker no longer mislabeled physical aperture. Report, result and
  updated setup checkpoint saved. Three focused tests, compile, all-case DUT
  hash/connectivity audit and scoped diff review pass. Unrelated Obsidian
  whitespace/edits and10bit work preserved. No OA/PDK/circuit or R3 changes.
- Scoped local commit; no push. This monitoring purpose is finished; remove
  only automation r4 after committing and deliver final results/limitations.
