# Physical stress repair and regression

Status: repair incomplete; loaded five-PVT and receiver controls reviewed;
210ns receiver/reset controls running or queued. No ADC baseline adoption.
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
- Stream every native point for device peaks; export compact plotting data and
  separate exact native extrema, not full raw. Never load multi-GB ASCII PSF in memory.
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

## Real-load integration phase (user authorized continuation)

Start HEAD 14b9446; unrelated cleanup commit and user dirty files are protected.
Bridge t28_io / thu-wei / expected CIW / Spectre verified healthy. OA remains none.
Use unchanged full ADC hierarchy as the real-load fixture: first replace only
reference switches (ordinary IO scale2) at FF cold, and only comparator (N4)
at SS cold. Both retain actual CDAC, physical BBM drivers, downstream logic and
original comparator output MOMs. These are diagnostic integration tests, not
adopted versions. Follow with combined candidate and five PVT points after
understanding loaded behavior; fix failed circuits rather than suppress warnings.

Add exact native-point supply-energy integration and event timestamps to bounded
stream reduction; selected plotted waveforms may be compact. Save comparator
input gate currents, all four reference-switch terminal currents on diagnostic
branches, actual reset/compare/write/update/sample signals. Measure load-induced
top-plate motion, input charge, reset recovery and energy separately from code
correctness. Do not label motion during CDAC switching as comparator-only kickback.
Verify unchanged unselected devices, loads, external stimulus and monitor hashes.
Same corner baseline is required for aperture and energy comparisons. Test the
new integration reducer on a synthetic sparse PSF before remote use.

Numerical screening study: before spending another full strict batch on a
known-incomplete integrated circuit, compare the identical loaded reference
candidate with requested reltol 1e-4 (versus 1e-6 strict; actual CX settings must
be read from logs). Keep maxstep10ps and absolute tolerances unchanged. This is
a different-precision diagnostic screen, NOT an equal-accuracy speed claim.
Check code/events, sample edges, native stress maxima and energy against the
already completed strict run. Only use it for candidate triage if stress differs
by <0.1mV, timing by <5ps and energy by <0.5%; final closure still requires strict
PVT/performance verification. Preserve both inputs and results independently.

Loaded checkpoint: reference-only FF cold and comparator-only SS cold complete;
both give243/12, reset and external aperture checks pass. IO reference worsens
BP7 undershoot to -82.31mV but settles; N4 increases compare-phase top motion
and does not reach the optional 0.8VDD differential-output diagnostic threshold
before write. This threshold is not substituted for the actual receiver trip point.
Original core driver/control stress remains unresolved. The combined five-corner
batch is therefore a diagnostic interaction regression, not final qualification.
Run it at the original strict tolerance; no digital/timing changes in this batch.
Preserve new unrelated cleanup commits98bc95c/19ae72f. No historical deletion here.

Next bounded comparator check: N4 raw output high is only0.403V at the final
SS-cold write (VDD0.81V), despite a correct code. Diagnose by increasing ONLY
the two cross-coupled PMOS latch multiplicities2->4; keep native input/latch,
tail, reset, MOM and logic unchanged. Actual downstream receiver timing, not an
invented rail-to-rail condition, determines functional validity. Test SS cold
under the same full load and strict settings; do not substitute it into the
already-frozen five-point batch. No new supply or external timing changes.

## Loaded PVT continuation

Start HEAD85378b3; completed six prior jobs and collected outputs are owned by
this task. User Obsidian/10-bit work and independent home archive remain protected.
All six native/analysis statuses verified complete/exit0, no reruns required.
Combined five-point two-frame regression: references/comparator pass their
device-class stress screens at all corners; SS hot startup242 instead of243
with -9.978mV held error; TT has8 failed pairs in the comparator receiver;
FF retains driver/control stress. PMOS latch doubling did not improve output
high at last SS-cold write(.403->.402V); do not adopt that sizing change.

Next single-variable interface fix: clone ONLY the two COMP_P/N receiving buffers
in sar8p_timing. Replace their first inverter's4 MOS with legal ordinary IO
CDF units, NMOS2/PMOS4 (W0.64/1.28um,L150nm); keep second inverter core, all
other control/BBM/delay/sample circuitry and N4 latch sizes unchanged. Check
TT and SS cold first, full native stress+receiver/PR/NR/RAW/DEC waveforms. This
addresses direct comparator-output stress; it is not a proposed cure for all
remaining FF core gates. Reject if valid timing, reset or external aperture fails.
Separate evidence for SS hot startup from normal cycles; no power-ramp or
restart correctness inferred from DC-start two-frame tests.

SS-hot acquisition discrimination: reverse only VINP/VINN external PWL values
so first/second differential inputs become-.81/+.81V (expected12/243), with
identical source impedances, reference, supply, clock and all DUT devices.
Use combined original-N4 candidate, not receiver variant. This separates initial
DC-state sensitivity from input-polarity acquisition; it is not a POR repair.

## Remaining core logic feasibility

Read-only PDK cell-name inventory confirms ordinary18, under-drive18ud12/15,
native18 NMOS and core threshold variants; no fast 1.2V core class inferred.
Before considering under-drive logic, measure its actual native CMI limits in a
tiny isolated four-device diagnostic fixture. Intentionally excessive terminal
biases are simulation-only metadata probes, NOT operating recommendations or
qualified ADC test points. Retain printed limits for both polarities/all six
pairs; unknown or suppressed limits remain unknown. No model edits/copies.
Use managed queue and minimal raw/analysis budget; existing loaded jobs continue.
Ordinary IO/UD FO4 at SS cold is already much slower than core: do not adopt a
whole-logic replacement without latency, sampling-edge and power verification.

Receiver SS-cold native first frame converts in47.492ns vs44.254ns, still243.
This puts last reference reset potentially beyond the old200ns stop, but not
necessarily beyond next actual acquisition(~203ns). Extend an identical rx2
SS-cold diagnostic to210ns under a NEW immutable ID; preserve old200ns raw.
Also screen rx1 (half the four receiver MOS multiplicities, nothing else) with
the same210ns observation. Assess reset/bottom readiness before actual sampling,
not merely whether a reset timestamp falls within an arbitrary100ns bin.
This is observation extension, NOT external timing or frequency modification.

Checkpoint reviewed: receiver rx2 TT eliminates all8 failed pairs (now0), codes
243/12,14 settling windows pass; second conversion34.09475ns,power144.880uW.
SS cold rx2 also0 failed pairs,243/12,14 windows pass; conversion47.38843ns,
power103.960uW. Actual sample closing deltas<.001ps; window deltas<.005ps.
First SS-cold cross-frame reset starts100.75664ns, bottoms settle101.82129ns,
next actual sample103.32164ns: compact-estimate margin1.50035ns. Second reset
unobserved at200ns, so both new210ns cases registered/submitted under single-job
gate, not baseline changes. One-shot flow only analyzes/collects named jobs.

Reverse-input SS hot gives13/243 (expected12/243), held+9.96584/-.282829mV,
both event counts and full stress screen pass. First high-side gate.763109V,
normal precharged high-side1.656871V: initial-state issue follows first frame,
not a unique P/N branch. Initial DC relaxation warning retained; POR not fixed.
Native under-drive limit probe completed and hashes verified: both polarities,
all6 pairs1.32V CMI threshold, not a lifetime rating or ADC operating test.
Unrelated files and all historical raw retained; overall FF/control/startup and
performance closure remain open. This checkpoint must not be marked complete.
