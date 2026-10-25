# Baseline reference-current instrumentation and cause localization

Status: complete. Both original 200 ns baseline runs and sequential reductions
finished; current KCL, unchanged-circuit hashes, voltage/timing/code reproduction,
six plots and scoped validation passed. Diagnosis only; no circuit repair.

## Scope and ownership

User authorizes measurement-only reruns of the original Rgate baseline to locate
reference gate overshoot and CDAC bottom undershoot, with waveforms and cause
analysis. Do NOT change DUT topology, W/L, multiplicity, timing, supplies, PDK,
initial conditions or promote a candidate. Start from immutable
rg1_strict200_ff_m40 / rg1_strict200_ff_125, commit1101428 evidence.

Own this plan, plan/log.md, scripts/sar8_ref_current_probe/,
verification/sar8_ref_current_probe/, output/sar8_ref_current_probe/,
docs/sar8_ref_current_probe.md, docs/figures/sar8_ref_current_probe/.
May append a factual save-mode correction to docs/sar8_stress_closure.md if the
old allpub explanation proves inaccurate; preserve its numerical findings.
Remote owned result root:
/home/chenzc_intern25/TSMC28/llm_IO/sar8_ref_current_probe_20261025.
Remote OA owned objects: none. All existing OA/results/model files read-only.
Own the additive run record management/runs/2026-10-25-reference-current-probes.json;
do not rewrite the independently edited management inventory/index.

Dirty-state audit: HEAD1101428, branch exp/cdac-flat8-device ahead18. User
Obsidian changes, independent10-bit and management-registry untracked work are
unrelated and protected. No push; task-only local commit after verification.
During execution independent management commit657f5b6 landed, followed by more
management-execution work. Preserve those commits/dirty changes; only add the
task-specific run record. Append/stage only this task's maintenance-log entry.
At the first review of commit b6da655's mandatory managed-execution policy,
this batch's native runs and reductions were already finished. Keep historical paths intact;
disable this task's old launch/reduce functions for future jobs. Remaining
collection is bounded read-only recovery, followed by local analysis only.

## Steps and validation gates

1. Check current SSH/resource/process state, exact native simulator and model
   dependency hashes. No CIW shell/help calls. Obtain bounded native help on
   save/current syntax in an independent command, preserve logs privately.
2. Use case-correct observed/declared names, first run a short baseline probe
   to require actual TRACE presence for wrapper D/G/S/B currents, reference
   rails and gate-drive resistor currents. Verify sign/KCL and current scaling;
   terminal current includes displacement, not automatically pure channel current.
3. Only after that gate, run cold then hot baseline with the original200ns
   stimulus/history and solver accuracy. Save a focused list, not all-signal
   current expansion. One native job at a time,4threads; check resources and
   native memory, no duplicate submission. Preserve old raw and unique new runs.
4. Stream/memory-map new data; compare voltages/code/timing with immutable old
   baseline so measurement changes cannot silently alter circuit conclusions.
   Locate cold/hot BP7 conversion handoff and GNN4 reset overshoot; inspect
   other bottom nodes/reference rails and drivers. Use KCL/current direction
   and bounded charge integration, distinguishing correlation and mechanism
   inference from any unmeasured channel/displacement decomposition.
5. Separate related signals across plots (<=4 per panel), mark native timing,
   current signs, test conditions and analysis windows. Visually review plots.
   Report measurement limits, unresolved sources and no circuit changes.
6. Compile scripts, validate targeted fixtures/JSON/hashes/scoped diff; update
   plan/log. Commit only owned files; do not push or change any baseline/OA.

## Completion and constraints

Artifacts: current probe validation, immutable source hashes, native log/exit
evidence, case metrics, plots and concise Chinese cause report. If connection or
model hierarchy prevents reliable current extraction, stop at the exact failed
gate; do not fabricate currents or use behavioral substitutes. A positive result
means diagnosis, not overvoltage repair, PVT qualification or foundry SOA signoff.

## Results and validation

- One 0.2 ns smoke confirmed228 current saves; the full cases add4 dummy-cap
  terminals, giving232 currents/130 voltages. Fixed case-sensitive save names.
  Extended a task-owned copy of the streaming parser for current TRACE PROP
  metadata; fixture passed. Initial reduction failures did not rerun Spectre.
- Cold/hot319432/282775 samples, native exit0/PASS, same1609 nodes/1833 MOS.
  Original input/monitor/DUT hashes and measurement-only deck transforms pass.
  Core current KCL residuals<45pA; including reference rails<90pA.
- GNN4 peaks1.050940/1.055035V, gate current9.717/9.850uA returning to driver;
  no bit4 reset or logical driver-input toggle at the event.
- BP7 minimum-56.939/-45.028mV: low-side turnoff precedes high-side GP fall.
  During the second stage PMOS removes5.142/3.556fC while NMOS returns
  0.500/0.159fC. Do not attribute the entire undershoot to low-side turnoff.
- RST7 also couples TOPP through CDAC into inactive BP3; minima-27.090/-35.803mV,
  low NMOS replenishes rather than causes the main charge withdrawal.
- Codes243/12,8/8/8/16 events per frame,14/14 settling windows pass. Max settling
  2.217/2.379ns, deadline residual0.499/0.606mV. Common-voltage interpolation
  max differences79.13uV/0.000832uV; critical peaks reproduced within1uV,
  sample-close differences<0.001ps. No PVT/SOA signoff claimed.
- Native peak321/318MiB, streaming parser~6.5MiB, single job at a time. New
  raw9.67GB retained; old cases untouched. Native logs remain in ignored output.
- Final six plots visually checked; validation.json passed, scripts compile.
  Report, receipts, probe/measurement manifests and additive run record retained.
  Shared management commits and user Obsidian/10-bit changes preserved.
  Task-only local commit, no push.
