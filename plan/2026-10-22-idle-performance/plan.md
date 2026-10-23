# Idle-tail candidate: full nominal performance versus R4

Status: native batch previously confirmed complete; collection blocked by SSH jump-host connectivity (2026-10-23).

## Goal and boundaries

User requests the idle-tail reference-reset version from commit `027b951` be
tested with all 255 transitions / 256 codes and 1024 coherent sine samples,
then compared with original R4. TT, 0.9 V, 27 C, 10 MS/s only. No PVT,
mismatch, transient noise, PEX, circuit optimization, or baseline promotion.
The candidate DUT SHA256 must remain
`ef0fc74a3df306a366261bd5ce6bbe01f6b4386007c0b86c3150e09c28f976ea`.

Dirty-state audit: branch `exp/cdac-flat8-device`, ahead 6; user changes in
Obsidian_docs and untracked cdac10_dualrail config/model/plan/scripts/results
are unrelated, remain untouched. No overlap with this target.

Owned local paths:
- this plan; append-only entry in `plan/log.md`
- `scripts/sar8_idle_performance/`
- `verification/sar8_idle_performance/`
- `docs/sar8_idle_performance.md`, `docs/figures/sar8_idle_performance/`
- ignored generated `output/sar8_idle_performance/`

Remote OA ownership: none. No CIW/OA edits. Native netlist-only Spectre via
supported bridge SSH profile `t28_io`; task-specific immutable scratch under
`/tmp/virtuoso_bridge_chenzc_intern25/90590/sar8_idle_performance_20261022`.
Scratch is not project storage; collect logs/waves locally.
PDK, other libraries/jobs, frozen R4, prior idle/staged cases, all user files
and baseline reports are read-only.

## Method and dependencies

Reuse the original R4 external testbench, passive monitor, transition-search
stimulus and metrics implementation without altering those files. Swap only
the frozen DUT text for the byte/hash-verified idle candidate; check all
subcircuit definitions and testbench identity. Original R4 results and native
case mapping remain the comparator. Spectre X CX, 4 threads per job; at most
4 simultaneous jobs after resource preflight. No comparison of unlike solver
tolerances as equal-accuracy speedup.

Static: 8 ranges, 7 binary refinements, 4 warmup frames per range, bound width
1/128 LSB; include every center. Sine: 1024 samples after 4 warmup frames,
bin 461, 4.501953125 MHz, -1 dBFS, rectangular coherent FFT; direct FFT and
ADCToolbox SNDR cross-check. Save lean 1 ns strobes, continuous native event
monitor and CMI diagnostics. Do not claim strobe traces bound analog peaks.
Digital output is read at frame+98 ns and checked at 90/98 ns; idle-reset
TOPP-TOPN at 98 ns is NOT a conversion residue or a comparison metric.

## Steps and validation gates

- [x] Verify source hashes and read original setup/results; native license/resource preflight.
- [x] Implement isolated immutable preparation, detached native launch, exact status,
      collection and comparison; compile and focused dry-run invariants.
- [x] Run a short static-search smoke; require native exit 0, PASS, full frames,
      valid brackets, centers and continuous-event counts before full batch.
- [x] Launch one full sine and eight static segments exactly once, detached from SSH.
      Persist launch manifest before dispatch; resume status/collection only.
- [ ] Verify native exit/PASS/END, full time coverage, remote/local deck and wave
      hashes, independently decoded codes versus monitor, all frame event counts,
      255 disjoint transition brackets, 256 observed codes and 1024 FFT codes.
- [ ] Read effective solver settings and CMI/numerical diagnostics for every run;
      retain failures and initial-DC notes. Compare same-method metrics to R4.
- [ ] Generate and visually inspect static, spectrum and code-comparison figures;
      clearly state nominal-only scope and stress evidence limits.
- [ ] Update log/plan, scoped diff review, commit owned sources/results/report only.

Performance screening: all timing/center/bracket gates, |DNL|<=1 LSB,
endpoint |INL|<=1 LSB, ENOB>=7. Electrical warning status is separate;
no CMI alone is not all-node or reliability qualification. Completed runs are
retained even when a gate fails; do not modify the DUT to rescue measurements.

Outputs: `verification/sar8_idle_performance/{setup,results}.json`,
`docs/sar8_idle_performance.md`, final PNGs; immutable raw cases/status in
`output/sar8_idle_performance/`. Commit policy: bounded local commit(s),
`experiment: characterize idle-reset ADC against R4`; no push.

## Running checkpoint (2026-10-22, CST)

- Smoke `smoke_static_128_128`: native exit 0, PASS, 15/15 valid frames,
  centers 127/128 correct, boundary bracket [-54.931640625 uV, 0 V], status 0.
  Zero CMI and no transient numerical diagnostics. Initial DC Gmin/pivot notes
  preserved. Actual CX: reltol 1e-4, vabstol 1 uV, iabstol 1 pA, gear2only,
  maxstep 15 ns; elapsed 256 s. Native PSF/deck SHA256 verified after transfer.
- Exact text checks: substituting frozen R4 DUT back into each of the nine new
  decks reproduces its original R4 deck text. Context/model hashes match;
  candidate has 49 subcircuits and exact prior native DUT hash. All pass in
  `verification/sar8_idle_performance/preparation_checks.json`.
- Full batch dispatched 2026-10-22 23:32 CST, native batch PID 17423.
  Four lanes, four threads/job, planned 3618 total frames. First native logs
  confirm sine and static 001–032/033–064/065–096 running; five cases queued.
  Immutable dispatch receipt: `output/sar8_idle_performance/full_launch.json`.
- Hidden one-shot collector `finish.py`, native Python PID 44912 (launcher
  43056), started 23:33 CST, bounded to 24 h. It only reads/collects already
  submitted jobs and generates the comparison after all complete; no relaunch,
  Git mutation or automation changes. If PC sleeps the remote batch continues;
  inspect local collector/status files before any manual recovery.
- Remaining: all full-result validation, visual inspection, final log and
  result commit. This checkpoint is NOT completed characterization. Commit
  launch/test scaffolding and evidence separately, without push or adoption.

## Collection resumption (2026-10-23)

User explicitly requested collection. Nine remote jobs have exit 0 and complete
frame counts; all eight static completion markers exist. The original local
collector stopped without a completion receipt, and its cause is not established.
No full case had been downloaded or partly collected. Resume the existing
`collect` command, never launch or recreate cases. Original collector log and
launch receipt are retained. Dirty user files remain unchanged; branch ahead 7
at resumption. Complete analysis/figures and scoped local commit; no push.

Collection attempt outcome: two bounded `flow.py collect` attempts timed out
before any case download began. Independent TCP probe to the configured SSH
jump host port 22 also timed out after 5 seconds. No active original collector
was found. This establishes a current connectivity blocker, not a simulation
failure; the precise network/VPN/server cause is not established. No full raw
case was overwritten, deleted or restarted. Preparation/source checks still
pass. User must restore the usual SSH/network access before resuming `collect`;
do not run `setup`, `smoke`, or `full` again. Final metrics/reports remain pending.
