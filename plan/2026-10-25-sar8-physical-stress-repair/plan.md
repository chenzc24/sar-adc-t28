# Physical stress repair and regression

Status: repair incomplete; first managed candidate reviewed and not adopted.
User confirmed: preserve 0.81–0.99 V supply and repair using physical circuits
or voltage-tolerant devices. Device-class/topology screening is now authorized.

## Goal and boundaries

User authorizes fixing the known transistor-level faults, not just measuring them.
Close reference-switch gate overshoot, conversion/idle bottom undershoot, then
remaining driver/comparator/control stress and acquisition faults. Preserve the
external sample window and closing edge, finite 50-ohm reference/input networks,
physical internal timing, 8-bit flat architecture and original evidence.
No ideal clamps/keepers, warning suppression, relaxed model limits or PVT relabeling
may be used to claim a physical fix. Separate a useful improvement from closure.

Dirty state: user Obsidian reorganizations and independent cdac10_dualrail files
are unrelated and protected. Start HEAD de70f82, branch exp/cdac-flat8-device;
management commits b6da655/657f5b6 remain intact.

## Ownership

- Local: this plan; scripts/sar8_physical_repair/; netlist/experiments/sar8_physical_repair/;
  verification/sar8_physical_repair/; docs/sar8_physical_repair.md and matching figures;
  output/sar8_physical_repair/; management/recipes/sar8fix-*;
  management/runs/sar8fix-*; task-only appended plan/log.md.
- Managed execution may create its standard ignored output/managed_execution receipts.
- Remote OA: none. Netlist candidates are NOT synchronized schematics.
- Remote new runs: only managed SSD runs/sar8fix-*; historical runs read-only.
- Read-only: PDK, existing design sources, R3/R4, current L90/Mmain2 baseline,
  previous diagnostic and stress runs, unrelated user files, management execution code.

## Sequence

1. Audit exact original deck, PDK device parameters and native CMI limits. The
   existing 0.99/1.98 V limits remain screening criteria, not lifetime certification.
2. Build native PDK-only single-variable candidates. First evaluate passive gate
   charge buffering (MOM gate capacitance with reduced gate resistance), retaining
   slew rather than blindly accelerating all gates. Reuse verified geometry.
   Reject if new bottom/driver stress or settling failures outweigh improvements.
3. Use measured results to select subsequent bounded topology/sizing corrections;
   record each delta before running. Preserve original candidate inputs forever.
4. Full MOS-pair monitoring, independent code/timing checks and all-bottom settling
   on the 200 ns FF cold screen; then FF hot, five PVT risk points, steady-state
   acquisition, static and 1024-point dynamic regression on a viable candidate.
5. Preserve the user-confirmed 0.81–0.99 V supply contract. Screen legal 1.8 V
   devices at the EXISTING gate supply, first on small native reference-switch,
   logic and comparator fixtures. Measure low-supply speed/Ron before integration.
   Do not add ideal internal rails or silently change input/reference ranges.
   Circuit protection and device-class changes are permitted; failures remain
   failures even when output codes are correct.

## Validation and resource policy

- Every new simulation and heavy remote analysis uses managed register/submit/
  run-status/analyze/collect, single job, four threads, frozen SHA256 inputs.
- Initial budget: simulation RSS 1024 MiB, virtual 8192 MiB, 3600 s; analysis
  RSS 256 MiB, virtual 1024 MiB, 1800 s; output 32 GiB for full MOS voltage
  coverage; collection <=32 MiB. SSD admission reported 557 GiB free.
- Stream every native point for device peaks; export compact min/max-preserving
  plotting data, not full raw. Never load multi-GB ASCII PSF in memory.
- Exact case-sensitive voltage/current saves; validate TRACE, END, stop time,
  native PASS/exit, effective CX conservative tolerances and all device mappings.
- Guardrails: same external sources and SEQ_SAMPLE edges (report actual deltas),
  codes 243/12, 8/8/8/16 events each frame, all 14 settling windows within
  +/-1.7578125 mV by next comparison, reset completed before acquisition.
- Final closure additionally requires no MOS terminal pair above its unchanged
  screening limit, PVT/performance regressions, and no hidden warning suppression.
  Two static frames alone cannot qualify the ADC.
- Inspect generated figures; targeted tests, git diff --check, scoped review.

## Commit policy and artifacts

Commit only task-owned reproducible inputs, scripts, reviewed metrics and reports;
no raw/PDK/OA data, no push. Keep plan active while any required closure remains.
Use factual checkpoint commits if experiments demonstrate improvement but not closure.

## Execution checkpoint

- Registered and submitted sar8fix-c1r4-ffcold via managed entry, original 1833 MOS
  unchanged, 320 gate resistors paralleled x4, 1020 existing-geometry MOM units
  added to 32 gate outputs (nominal total 4.08408 pF). Compare also to historical
  Rgate/4 run to isolate the added capacitance effect.
- Native save summary: 939 voltage +24 current traces, no invalid-save warnings.
  10998 MOS terminal-pair peaks will be measured at every native sample. Compact
  plot export has minimum 10 ps spacing, explicitly not exact timing signoff.
- An early live collect hit checksum mismatch because mutable logs changed
  during collection. Simulation is unaffected; wait for stable completion, then
  retry collection only. No resubmission.

## Reviewed result

Managed simulation and analysis both complete/exit0; no outstanding worker.
318574 native points, 10998 MOS pairs; collected 14 files /20110753 bytes with
all hashes verified. An early START log snapshot was preserved by the collector;
analysis now resolves receipt hashes to versioned logs instead of reading stale
basename snapshots. No native rerun was needed.

GNN4 peak 1.050940 ->0.999016 V; BP7 minimum -56.939 ->-40.632 mV;
reference worst pair 1.050940 ->1.030632 V, now XSP7.MP_HIGH |Vbd|.
Reference driver/comparator/digital remain 1.056952/1.043639/1.078642 V.
Codes243/12 and counts pass; compact-export settling estimates14/14, max2.293ns.
First-frame preclose acquisition error remains -1.978mV. Not repaired, not
promoted, no new supply rails or relaxed limits. Full PVT/static/FFT not started
on this known-failing candidate.

User answered: retain 0.81–0.99 V, solve with circuits or voltage-tolerant devices.
The next checkpoint begins at HEAD 01cf64b; unrelated dirty state is unchanged.
First characterize the low-voltage usefulness of existing legal IO devices,
with original core devices as controls. This is a device feasibility screen,
not an adopted ADC revision or evidence of completed repair.
Checkpoint preserves failed/improved evidence while overall target stays open.

## Fixed-supply device screen

- Read-only live CDF audit: ordinary 1.8 V (150 nm / 320 nm defaults),
  under-drive 1.2 V (105 nm / 320 nm defaults). Reuse complete CDF instance
  geometry, not core parasitics with a renamed model. Native input acceptance
  is not layout DRC. Under-drive SOA is deliberately unclassified until audited.
- Five small corners: TT/.9/27, SS/.81/-40, SS/.81/125, FF/.99/-40,
  FF/.99/125. Each includes core controls, FO4 inverters, MSB-equivalent MOM
  loads and two polarities of 1.758 mV StrongARM input at VCM=.45 V.
  Bench clocks and inputs are ideal; these are not integrated ADC results.
- Reference fixtures measure near-rail Ron at 10 mV VDS. Off currents at this
  bias MUST NOT be called full-swing off leakage. The switching fixture has
  common GN/GP excitation, not the actual integrated BBM driver.
- SS cold direct-IO StrongARM fails the 1.9 ns fixture window. A physical
  hybrid retains core input devices and inserts two IO cascodes; 2/4/8 units
  protect input stress but still fail both 1.9 ns and extended 5.9 ns windows.
  Extended bench windows do not change ADC sample/closing-edge contracts.
- Next bounded SS cold candidate uses CDF-default 1.8 V NATIVE NMOS
  (800 nm / 500 nm) for input/latch devices; ordinary IO tail and PMOS remain.
  Size factors 1/4/16 are screened, with core comparator as simultaneous control.
  No candidate promoted or OA edits made.
- Native-NMOS candidate also receives a 5.9 ns standalone decision window:
  SS cold N4 resolves at 2.820 ns, maximum pair 0.894 V. N1/N16 take
  3.426/5.683 ns. Continue the other four module PVT points before considering
  integration. This does not reallocate the ADC conversion/sample windows.
- Concurrent history-cleanup-review files and management/README.md appeared
  during this turn. They are unrelated, outside this target and remain untouched.
  No historical/raw deletion is performed by this repair task.

## Fixed-supply checkpoint reviewed

13 managed block runs and analyses complete; 322993 native points, 169 collected
files /97709108 bytes. Simulation group peak293.3MiB, analysis115.5MiB;
small models actually ran single-thread despite four-thread resource ceiling.
Core-control CMI warnings remain visible; inputs and all receipts verified.
Measurement-window variable-shadowing bug fixed and every local analysis rerun;
native simulations were not rerun. One premature analysis request was refused,
then the same ID was analyzed once after native completion.

Ordinary IO reference scale2 meets the five standalone settling windows, but
full-swing off leakage and actual CDAC/BBM loading remain untested for that class.
Full IO comparators and hybrid core-input/IO-cascode variants are not adopted.
Native-NMOS N4 comparator resolves both signs at VCM=.45V in all five extended
window screens: TT1.358ns, SS cold2.820ns, SS hot2.752ns, FF cold.797ns,
FF hot1.697ns; largest pair1.152V on actual 1.8V devices. This is NOT full ADC
qualification and does not establish full input-CM range, noise/offset or power.

Next: optimize N4 tail/reset stages and test input sign reversal, real downstream
load, CM range and kickback; then reference full-off leakage/real BBM/full-CDAC,
followed by tolerant digital timing integration. Preserve external supply/sample
contract. All existing ADC circuits/OA remain unchanged. No background worker
remains at this checkpoint; overall physical repair stays incomplete and active.
