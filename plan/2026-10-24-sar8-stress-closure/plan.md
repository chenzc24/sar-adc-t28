# Native SAR8 stress repair and verification

Status: recovery blocked by target command/file-read nonresponse. Repair incomplete.

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
