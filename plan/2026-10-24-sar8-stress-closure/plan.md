# Native SAR8 stress repair and verification

Status: four-case streaming recovery/comparison complete; physical stress repair unresolved.

## Scope

Start from immutable L90/Mmain2 native case and 6827fd5 diagnosis. Address
reference-bottom undershoot, stable-gate disturbances in reset/conversion and
known controller/driver/comparator stress. Do not declare closure from codes
alone or substitute ideal keeper models for physical transistor repair.
Preserve sample window and closing edge; any required architectural/timing
contract change must be explained before adoption. No PDK/model/limit edits.

Own this plan, plan/log.md, scripts/sar8_stress_closure/,
verification/sar8_stress_closure/, output/sar8_stress_closure/,
docs/sar8_stress_closure.md and docs/figures/sar8_stress_closure/.
Remote run root: /home/chenzc_intern25/TSMC28/llm_IO/sar8_stress_closure_20261024.
Remote OA ownership: none initially. Extend plan with exact candidate cells
and readback requirements after verified physical candidate and healthy bridge.
Read-only: all earlier experiments, original OA, PDK, standard libraries.
Dirty user Obsidian files and independent10-bit experiment unchanged; branch
exp/cdac-flat8-device initially6827fd5, ahead13. No push.

## Steps and gates

1. Verify profile t28_io, native model hashes, simulator availability and exact
   source hashes. Inspect full stress inventory, native CMI warnings and custom
   digital hierarchy. Check disk and existing processes, never duplicate runs.
2. Isolate local reference handoff with current/voltage probes and numerical
   convergence; bounded single-variable edge/handoff/driver experiments.
3. Implement chosen solution with native devices, remove diagnostic holds from
   final candidate. Inspect/repair remaining block stress without raising limits.
4. Expand terminal inventory to all MOS; check device-specific limits, native
   logs, negative pulse duration, overlap current/charge, settling and codes.
   Confirm sampling contracts against frozen baseline at FF cold/hot then five
   PVT points; static/full-code and1024sine regression on surviving candidate.
5. Only after verified netlist and healthy bridge, plan/synchronize independent
   OA candidate via supported APIs and verify exported netlist equivalence.
6. Report exact passes, failures and unverified conditions. If external access
   blocks simulations, preserve work and request necessary user action rather
   than claim repair. No layout/PEX/mismatch signoff inferred.

## Validation and deliverables

Use immutable unique cases, source hashes, native Spectre pass/exit and CMI
logs. Reuse source monitor but verify new current extraction and actual solver
settings. Compile changed scripts; scoped diff-check; inspect final figures.
Local owned-file commits per bounded phase; no baseline promotion until gates
pass and OA readback agrees. Intended commit: fix: close native SAR8 stress.

## Initial experimental batch

SSH/native Spectre21.1 license and model/config hashes verified. No existing
Spectre jobs on preflight. Bridge tunnel down, so no OA mutation permitted.
200ns/two-frame FF cold/hot baseline vs fourfold parallel gate resistors
(Rgate/4), native1833 MOS unchanged, no ideal keeper. PDK resistor geometry,
external supply/reference/sample sources unchanged. This tests reduced gate
source impedance before designing more elaborate native hold/edge shaping;
it does not assume reduced resistance will cure bottom undershoot.
All1833 MOS/10998terminal pairs,1073 saved signals including all32 reference
switch D/G/S/B wrapper currents. Strict CX -preset_override honors requested
reltol1e-6/maxstep10ps, subject to actual-log readback. Four cases,2 concurrent,
4threads each. Baseline same settings for fair comparisons.600ns and full
regressions still required. Current probe existence/interpretation must be
verified from native output before claiming channel-current attribution.

## Access interruption and resume checkpoint

All four cases submitted once, batch PID133523; first two cold cases run
concurrently, hot pair queued behind them. Native cold baseline log reached
41.0583ns with retained CMI warnings. Subsequent independent status query timed
out over SSH, so latest completion state is UNKNOWN, not a simulation failure.
Do not resubmit any existing launch.json case. No native jobs terminated.
Bridge start attempted after initial tunnel-down finding, but remained in
deployment while SSH became unresponsive. No CIW/OA connection success claimed.
Stopped only this turn's verified local bridge-start client PIDs44248/46276
after the timeout; no Virtuoso, remote simulator or prior tunnel process killed.

Local validation: all hashes,1833MOS coverage,10998pair coverage,1073save-list
coverage and native-only DUT invariants pass; all scripts compile/import.
Analysis/reducer not yet validated against these new native current traces.
Digital provenance: custom sar8p_* CMOS hierarchy, PDK nch/pch_mac, rupolym,
cfmom_2t; no imported standard digital cell library. Physical RC, not old idealRC.
Commit this bounded infrastructure/candidate checkpoint without marking overall
plan complete: experiment: prepare native SAR8 full-stress repair screen.
Resume with control.py status, then reduce/collect/analyze completed cases;
verify currents/settings before choosing physical repairs. PVT/full-code/FFT/OA
closure remain outstanding. No baseline changes or push.

## Network-restored recovery

User requested recovery and continuation. Starting commit4c03943, unrelated
Obsidian/10-bit dirty state unchanged. Jump host responds and target public-key
authentication succeeds. Direct target hostname eventually succeeded after
23.3s session time; old30s command deadline can expire during slow startup.
Use bounded90s command deadlines in this isolated task process, not global SSH
settings. Inspect existing cases only, preserve raw data and avoid resubmission.

Recovery outcome: inherited status timed out at30s and90s. Direct target SSH
Python status bypassing login shell timed out at90s; a separate /bin/cat of
the first native exit_code also timed out at90s. Target authenticated and its
hostname returned, so network reachability is not equivalent to working result
access. SCP/SFTP exit-code probe did not return data; stopped only verified
local probe wrappers30168/38684. No remote process or file was changed.
Jump-host same-path alternative returned ENOENT immediately, so it cannot be
assumed a shared results mount. Exact root cause (session startup, resource
pressure or filesystem) is not established. Need existing target terminal or
administrator check before reliable recovery. All four native case completion
states remain UNKNOWN. No new simulations or circuit edits this turn.
Diagnostics retained in output/sar8_stress_closure/direct_status_*.json/.stderr;
updated access_state.json distinguishes connectivity from data access.
Compile and scoped diff checks passed; task-only diagnostic checkpoint commit,
not repair completion, no push. Existing Obsidian/10-bit changes preserved.

## Cold-result recovery request

User requests collection and cold baseline/Rgate-quarter comparison of stress,
settling and codes, plus exact hot-case status. Direct read at20261024T134424Z
confirmed rg4 cold exit0; rg1 cold reached post-transient summary without an
exit marker; hot logs absent at that snapshot. No simulation failure inferred.
Preserve raw cases and timing. Use bounded connection attempts and improve only
task-owned recovery/analysis scripts as necessary. If extraction is too large,
retain all native samples for stress and required comparison signals while
preserving original PSF. No repeated launches, no OA changes or baseline promotion.
Starting HEAD cef1ce8; unrelated Obsidian/10-bit dirty state remains protected.

Recovery outcome: later direct90s and detailed180s queries timed out, as did
the existing reducer's90s prerequisite exit read and independent90s SFTP log
read. No reducer uploaded/launched; no native job restarted or terminated.
New interactive SSH returned login banner, but neither hostname nor echo
returned; disconnected only that probe session. Asked user to compare from an
already-open thu-wei terminal. Cause unresolved, not diagnosed as server failure.
Preserved the successful snapshot and extracted log-only baseline codes243/12,
held errors-1.695/+0.577mV and conversion26.683/26.644ns. Enhanced case native
exit0/58warnings confirmed, but its codes/stress/settling unavailable. Both logs
show actual reltol1e-7/maxstep10ps, not requested1e-6. No waveform comparison,
hot-state confirmation or repair closure claimed. Partial metrics distinguish
conversion duration from analog settling time. Task-only checkpoint, no push.

## Sequential streaming recovery

User requests cold pair first, then hot pair, with controlled memory. Starting
HEAD f2862f8; all protected/user dirty paths unchanged. Cleanup independently
confirmed four native exit0 and94.87GB total raw data, which remains immutable.
Do not invoke the old all-series Python/JSON reducer. Add task-owned streaming
C++ parser (compiler already present) and orchestration/analysis scripts. Single
worker only, nice/ionice, <=512MiB virtual-memory resource limit; no simulation
launch. Parse one sample at a time, evaluate all10998 terminal pairs at every
native sample, retain peaks/times and selected full-resolution binary columns.
No analog decimation in stress or settling analysis; compact outputs only are
transferred, local arrays memory-mapped. Native raw files never deleted/rewritten.
Own new derived remote stream_v1 directory under each of the four existing case
paths plus shared task-specific stream_v1_tools directory. Preserve native context,
deck, log and PSF; verify hashes/settings, END and duration/native sample count.

Validate sparse-update/group-name parsing on a synthetic exact fixture and
cross-check reference stress against saved columns. Required comparisons:
per-group peak and affected devices, reference/bottom excursions, settling to
explicit0.25LSB bands and next comparison deadline, code/timing correctness,
unchanged sampling control edges. Two-frame200ns comparison is not full repair
qualification or PVT/static/FFT signoff. Inspect cold then hot scientific plots.
Record measured reducer peakRSS, input/output sizes and immutable-source checks.

## Streaming recovery outcome — 2026-10-25

All four exit0/PASS native cases recovered sequentially, cold pair analyzed before
hot pair. One512MiB-capped worker, measured C++ peakRSS7540KiB for each case;
94,869,661,741bytes original PSF retained unchanged. Selected112 voltage columns
plus time keep1,200,097 native points; compressed transfer754,657,809bytes.
Sparse/GROUP1 fixture, END/200ns/accepted-step count, deck and transfer hashes,
192 reference-pair crosschecks per case, independent output-code and timing/idle
checks pass. Exactly320 resistor multiplier lines differ in each cold/hot pair;
both sampling-control edge differences <0.001ps. No simulator/OA/PDK mutation.

Rgate/4 is NOT a successful overvoltage repair: cold reference peak1.05094→1.06561V,
minimum bottom-56.94→-75.61mV; hot1.05503→1.07207V,-45.03→-82.07mV. New hot worst
is BP3 after RST7, not conversion BP7. Maximum nominal-bottom settling improves
2.217→2.166ns cold and2.379→2.329ns hot;14/14 update windows meet the explicit
1.7578mV band in each case; codes243/12 and timing/idle checks pass. Cold startup
pre-close tracking error~1.978mV remains distinct from held error~1.695mV.
Comparator/reference-driver/digital stress remains above project screen; no SOA
qualification or baseline promotion. MOS terminal currents are absent: original
lowercased save requests were invalid in native Spectre. Allpub preserves needed
voltages; no branch-current attribution or pure-channel charge claim allowed.

Four final plots visually reviewed; concise report docs/sar8_stress_closure.md,
per-case stream_analysis/receipt and stream_summary JSON record evidence. Recovery
and analysis scripts compile; parser and pulse/settling fixtures and scoped diff
checks pass. User Obsidian/10-bit and newly appeared management registry work
remain outside scope and untouched. Full-tree diff check finds pre-existing
whitespace in user Obsidian; do not edit it.
This completes the user's bounded recovery/comparison, not the larger repair plan.
Next physical experiment requires valid probes and separate holding/edge shaping;
do not launch new runs as part of this recovery. Local task-only commit, no push.
