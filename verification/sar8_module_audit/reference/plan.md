# Independent reference-word oracle

Status: local implementation revised after parent review; 34 synthetic tests pass;
logic/analog contract separation reviewed locally; parent review pending.

## Goal and ownership

Implement a pure-Python reference-state oracle with independent commands, bit
order and reset priority. Demonstrate incorrect settled rail selection being
rejected without changing the historical analyzer or claiming ADC qualification.
Own only `verification/sar8_module_audit/reference/`, including this plan, helper,
tests and schema/truth-table notes. All other files and remote state are read-only.
Parent session owns the shared plan/log and coordinates other module sessions.

## Read-only dependencies and provenance

- `AGENTS.md` and `plan/2026-10-25-sar8-module-audit/plan.md`.
- `netlist/experiments/sar8_physical_repair/loaded_seed/dut.scs`:
  sar8p_bit, sar8p_bitseq8, sar8p_mux2, sar8i_refword, nonoverlap and drivers.
- `scripts/sar8_physical_repair/loaded_analyze.py`: conversion target dependence
  on gates versus already-independent fixed reset targets.
- User Obsidian, independent 10-bit work, existing repair results and all raw
  waveforms remain untouched. Shared branch dirty state is unrelated to this work.

## Implementation and validation

1. Define strict JSON event input, state transitions, reset priority and bounded
   observation windows; reject unknown state/time rather than granting a pass.
2. Implement command-derived D/CODE/Q, expected P/N/dummy rails and explicit
   observed-state comparison. No actual gate voltage feeds expected targets.
3. Add local unittest positive/negative cases for mapping, captures, ordering,
   missing/duplicate events, reset and MSB/dummy behavior.
4. Run the targeted unittest suite with Python -B and scoped diff checks.
   All fixtures are synthetic and in memory; no original data is rewritten.

## Restrictions and commit policy

No remote commands/simulation, OA/PDK/circuit edits, large-wave analysis,
cross-session messages, baseline adoption, commit or push. Parent reviews outputs.

## Delivered checkpoint

- `oracle.py`: strict event schema, independent D/CODE/Q state, per-bit reset
  priority and fixed dummy targets. Full-trace success requires eight descending
  decisions, sixteen correctly phased captures, reset initialization and digital
  Q observations at reset plus all sixteen capture stages. Analog rail tolerance
  is checked ONLY for separately declared analog windows from an independent
  required contract; early capture has no automatic analog settling requirement.
- `test_oracle.py`: 34 unittest methods, including six complete known-word
  positive cases and negative rail/mapping/capture/reset/unknown/window controls.
- `README.md`: source hashes, truth table, event input schema, synthetic tolerance
  scope, separate required analog-contract schema and explicit statement that the historical fixed-reset-target readiness
  check is independent of the conversion-target circularity identified here.
- Validation: project Python with `-B -m unittest discover -s
  verification/sar8_module_audit/reference -p test_oracle.py -v`; 34 tests PASS,
  reported duration 0.027 s before final documentation edits. Scoped `git diff --check` and whitespace inspection
  of all four new files pass. No bytecode/output artifacts created.
- Only this exclusive subtree was authored. No existing results, shared logs,
  original analyzer/circuit files or remote state were modified; no commit/push.
- No extraction from real ADC waveforms yet. Decisions/reset commands and analog
  check windows need independently reviewed provenance before applying to runs.
  These local tests establish helper behavior, not electrical ADC qualification.

## Parent-review correction

The first version required analog rail precision at every early and late capture.
That would incorrectly reject a legitimate unsettled intermediate D state before
late CODE. Corrected by requiring digital Q/protocol evidence at both phases,
while analog requirements and exact windows/tolerances come from a separate
explicit contract. Unknown budgets reject; deleting or shrinking observed analog
windows cannot remove independent contract obligations. Added early-unsettled /
late-settled positive case, early-wrong-word and late-unsettled negatives, plus
contract-coverage and unknown-budget controls. Historical analyzer/reset unchanged.

## Next local specification task

Parent authorizes `reference_fixture_spec.json` and a short fixture review in this
same owned subtree. Define minimal capture/BBM/driver/reference-switch/full-CDAC
extraction, independently replayed commands and frozen analog boundary loads.
Prioritize XDRV0 internal edge overshoot separately from GNN4 neighbor-reset
backflow. Hash source versions, declare ports, currents, MOS terminal screens and
unresolved replay/load/acceptance fields. Generate no netlist or remote work.
Validate JSON, source hashes and command-word arithmetic locally; do not expand
the oracle or edit shared files. No commit/push.

Specification checkpoint complete: `reference_fixture_spec.json` and
`fixture_review.md` delivered. JSON parses, all four source hashes match, five
key master port lists match, sixteen two-phase word rows and eight reset-word
updates pass independent arithmetic checks. Scoped diff/whitespace checks pass.
Unknown replay slew/times, downstream receiver loading and numerical acceptance
windows/tolerances remain explicit null; runnable=false. No netlist generated.
Primary case is the IO-reference/core-driver XDRV0 internal peak; original L90
GNN4 neighbor-reset case is separate. Parent review pending; no further dispatch.

## Priority-1 replay evidence audit

Parent authorizes a bounded local read (total <=32 MiB) of the already-collected
IO-reference/core-comparator FF-cold case to audit PHI_U, CAP_REQ, RST0..7,
SEQ_SAMPLE/CMP_CLK and other extraction-boundary availability, with paths/hashes.
Only priority-1 XDRV0 advances. Independent word commands stay243/12. If any
needed input is missing, deliver exact missing traces and minimal logical closure;
generate no deck from guessed edges. No remote/recipe/commit/framework expansion.

Replay audit checkpoint: delivered `replay_evidence_audit.json` and
`replay_review.md`. Five compact/native-summary files match receipt bytes/hashes;
receipt hash computed locally. Binary read once, 13,563,878-byte core payload;
conservative complete-task reads <16MiB, below32MiB. PHI_U/CAP_CLK/RST/SEQ_SAMPLE/
CMP_CLK schedules are available; CAP_REQ/CODE and driver0 internal waveforms are
absent from compact export, only extrema. Native voltage saves permit historical
recovery for those saved nodes. Rgate resistor-only junctions and driver0/LSB
currents were not saved and need future explicit measurement. Exact replay slew
is unresolved. Recommend eight-instance local capture-request closure or saved
voltage recovery; no guessed pulses, no deck/recipe/remote run or L90 expansion.
Audit JSON and scoped diff checks pass. Parent review pending.

## Native boundary exporter preparation

Parent authorizes local scripts and synthetic tests for an analysis-only child
run. Read source-run raw/tran_perf.tran.tran and frozen provenance only; write
exclusively under a different new run's output directory. Interface is --run-dir,
--output-dir and --source-run-dir. No remote invocation, simulation or recipe.
Export all native points from0 through the first driver0 fault plus margin for
required PWL boundaries; retain diagnostics only in a named local fault window.
Use lossless streaming compression if needed, never interpolation/decimation.
Missing required signals, incomplete history or budget overrun fail explicitly.
Target collected output <32MiB and managed RSS <256MiB. Preserve old parser.
Deliver manifest, new streaming parser/wrapper, synthetic tests and a short note;
no general framework, circuit changes, commit or push.

Native-export local checkpoint complete. Delivered native_boundary_export.json,
native_boundary_stream.cpp, native_boundary_export.py, dedicated synthetic tests
and native_export_review.md. Native raw path confirmed by source log line246.
31 required boundary traces retain every native point0..66ns; local diagnostics
retain64..66ns only. Lossless gzip, hard25MiB boundary/4MiB diagnostic/31MiB total
budgets, required-signal failures and source/run output isolation are implemented.
Python2 JSON-unicode path pre-review fixed via basestring-compatible STRING_TYPES.
Local JSON readback Unicode test passes. Python2 runtime is unavailable locally;
syntax/API compatibility reviewed, not reported as a Python2 execution test.

Full owned-subtree unittest run:53 tests,52 passed,1 Windows symlink-permission
skip, elapsed5.386s. Includes end-to-end lossless extraction and source unchanged,
group/property/sparse parsing, native narrow spike retention, budgets and errors.
Linux parser address-space cap192MiB plus future managed256MiB RSS policy are
declared; no real source extraction/output size/RSS result exists yet.
Generated synthetic temporary fixtures/executables were automatically cleaned.
No remote invocation, analysis recipe, simulation, old data/analyzer changes,
reference deck, commit or push. Parent review pending.

## Recovered native review and first local fixture

Parent supplies completed sar8audit-ref-native-v1 collection and authorizes local
SHA review, native driver-stage/capture/load figures, independent command-input
checks, and first isolated reproduction fixture preparation in this subtree.
Frozen exporters and all shared/source files remain read-only. Preserve source
devices, physical capture/BBM/Rgate/full CDAC and relevant real boundary loads;
add missing KCL currents, connection/current-direction/initial/load audits and
proposed reproduction/recipe gates. No sizing optimization or remote dispatch.
Measure actual full-native PWL text/package size before packaging decisions;
do not silently decimate. Proposed simplification must have explicit all-native
error/edge/extremum tests and parent approval before use. All new files stay here.

## Explicit approximate replay preparation authorization

Parent confirms the managed input package has a hard32MiB cap. Prepare only a
separately named approximate PWL candidate locally, leaving the native archive
and frozen exporter unchanged. Delete original knots only; retain first/last,
global min/max witnesses, both native brackets of every10/50/90%-VDD crossing,
and every native point64..66ns. Independently verify <=1uV absolute deviation at
every native point, exact retained knot values/times, crossing agreement and
per-trace counts/bytes. This is a diagnostic replay tolerance, not an ADC spec.
Do not relax limits if the package fails32MiB. No registration or submission
before parent review. Generated sources go only into the owned generated tree.

## Local review and candidate delivery checkpoint

Delivered review_recovered_native.py, build_first_fixture.py,
prepare_approximate_replay.py, ten focused additional tests, native_review.md,
first_fixture_review.md and generated local audits/figures/candidate decks.
All14 collected receipt hashes/bytes and lossless boundary SHA verified. Two
native figures visually inspected. Four native extrema reproduced exactly;
all14 recovered selected D/CODE input words and half-rail PHI_U phases match
independent243 commands. Arbitrary90%-guard failure is diagnostic, not declared
capture failure; complete Q/bit0/full-cycle proof remains outside this prefix.

Full-native PWL183,356,435 bytes/gzip65,275,785 bytes exceeds32MiB. Explicitly
authorized approximate29-input candidate deletes native knots only, retains
466,801/3,751,991 total knots, all fault-window and required crossing/extremum
witnesses. Independent all-native and actual-written-pair readback verification
gives max0.9999874320820723uV. PWL22,534,325 bytes; combined3-file local candidate
22,749,015 bytes. Parent independently verified PWL numerical constraints;
physical fixture and remote package/recipe remain unapproved.

Fixture1551 MOS wrappers vs original1833;1177 protected source-device records
and11 immediate fanouts match. Real downstream forward/load island retained;
clock and register-output feedback cuts remain explicit, so no whole-ADC load
equivalence asserted.275 current saves,1100 voltages and complete KCL incidence
at five priority nodes added. Retained original numerical settings; stop exactly
last native time6.5996504234270155e-08s; no invented66ns endpoint. Numerical
reproduction/KCL tolerances remain proposals pending parent review. No Spectre
compile/electrical pass, new remote invocation, OA edit, commit or push.

Validation:63 owned tests,62 PASS/1 Windows symlink privilege SKIP,6.251s;
scoped git diff --check passes. No frozen exporter/shared/source file edited.
Shared plan/log maintenance belongs to parent. Source current attribution,
physical reproduction, streaming-current reducer and recipe approval remain.

## Streamed-current analyzer preparation

Parent authorizes an independent Python2.7-compatible managed analyzer and focused
synthetic tests here. Interface --run-dir/--output-dir; result.json written last.
Read control/first_event_analyze.py only as parser/resource reference. Preserve
all selected-current requirements, full-history five-node KCL/incident currents,
native driver/gate extrema and half-VDD witnesses, startup evidence and original
CMI log. Reproduction comparisons are diagnostic with acceptance_pass=null.
Distinguish approximate input boundary from native simulator measurements.
Hard derived output <=32MiB, analysis <=256MiB; missing currents fail, never zero.
Prepare a complete local recipe proposal with analyzer/measurement and hashes;
no registration/remote operation or modification of original package/exporters.

## Streamed-current analyzer local checkpoint

Delivered reference_current_analyze.py (standalone Python2.7/3-compatible stdlib
source), prepare_current_analysis.py,25 focused synthetic tests and
current_analyzer_review.md. Complete local recipe proposal and measurement live
under generated/managed_reproduction. Initial package6 inputs total25,337,049 bytes,
including original unchanged3-file approximate fixture, analyzer,183402-byte
measurement catalog and frozen2,376,192-byte same-source native diagnostic.
Exact receipt/hash inventory is package_review.json; no registration occurred.

Five physical KCL nodes have complete15-terminal incidence checked against the
275-entry native-port catalog. Full27-column KCL/current/node trace retains all
native history;324-column fault trace retains43 voltages/all275 selected currents
without decimation.1100 voltage/275 current extrema, startup witnesses, native
peak current snapshots, half-VDD brackets and charge/KCL integrals are recorded.
Same-source21-voltage and edge comparisons are diagnostic; acceptance_pass=null.
Full original future spectre.out/CMI text is preserved. Only228 priority MOS pair
screens reduced; remaining9078 saved-voltage pairs are explicitly outside scope.

Hard30MiB derived/32MiB managed-collection budgets,2MiB original-log cap,
Linux240MiB AS/256MiB RSS guards and fresh-output/source-read-only protections
are implemented. Missing TRACE/initial current, incomplete native history,
omitted KCL branch or budget failure cannot publish result.json. Metadata uses
atomic rename; result.json is last. Actual real-run compression size, wall time,
Linux RSS, Python2 execution and model-port realization are still unmeasured.

Validation:88 owned tests,87 PASS/1 Windows symlink privilege SKIP,6.146s.
25 new tests include grouped/sparse/property parsing, exact terminal incidence,
current signs/charges, raw CMI preservation, input hashes, native/source extrema
diagnostics, CLI/source preservation, resource/output failures and atomic result
publication failure. Source reviewed for Python2.7 syntax/APIs; no local Python2
runtime claimed. Native/approximate original packages and frozen exporters stay
unchanged; only this owned subtree authored. No commit/push or remote operation.

## Parent-blocked unit-interface correction before registration

Parent caught a real interface bug: generator spread source peak dictionaries
with time_ns, while reducer expected time_s. Corrected generation to explicit
value_v/time_ns*1e-9->time_s fields. Analyzer validation now rejects ambiguous
ns fields/missing seconds, and generator calls that exact validator before write.
Added negative unit-field control and a minimal native-PSF end-to-end peak test
using the actual generated1375-signal/275-current configuration, not another
handwritten schema. All four synthetic peak values/times reproduce their source
constants with zero calculated diagnostic error. This is not circuit evidence.

Regenerated unfrozen measurement/recipe/input hashes. Final6-input proposal is
25,337,764 bytes; measurement183,415 bytes. Original3-file approximate package,
lossless export/source data and frozen exporter hashes remain unchanged.
27 analyzer tests pass; full owned suite90 tests,89 PASS/1 Windows symlink
privilege SKIP,6.716s. Complete package hashes/schema and scoped whitespace/diff
checks pass. No remote/registration/commit/push. Parent review still pending.

## v1 output-limit failure and v2 save-only reduction

Parent completed managed registration/dispatch of frozen v1; its hash and failed
history remain intact. Run stopped after364.853s with output_size_limit,
8,615,637,167 bytes and peakRSS390,717,440 bytes. Collected native log confirms
1100 voltage/275 current saves and SPECTRE-27 at61.9763ns, before64ns fault data;
this incomplete run is not accepted as reproduction evidence. Original CMI and
LTE-relaxation warnings remain in the collected log, untouched.

Parent authorizes a separate owned local v2 package that changes save selection
and measurement metadata only. Keep exact DUT, PWL, solver/timing/supply/closing
edge,275 currents, five-node KCL,228 priority MOS terminal screens,43 diagnostic
voltages,31 source-initial witnesses and21 source-wave comparisons. Retain all
existing selected-current port-node voltage context (excluding two fixed ideal
reference-source nodes not saved in v1). Remove unrelated voltage saves only.
No resource-cap increase, history deletion, remote command or new submission.
Parent owns execution and has assigned the slot to the control experiment.

Analyze actual v1 logged progress and original native point counts to estimate
whether the new selection fits the unchanged8GiB output cap. Distinguish estimate
from observed v2 output/step counts. Prepare an explicit conditional output-window
fallback if necessary, with startup separate and no claim of unsaved early current.
Only new v2 files and this plan are mutable; frozen v1 inputs/analyzer remain unchanged.

v2 local checkpoint: prepare_current_v2.py emits only generated/current_v2/.
1100->138 voltage saves (89 required +49 extra existing current-port context),
275 currents unchanged,1375->413 total signals. Full27-column KCL and324-column
fault exports,228 terminal-pair screens,31 source startup witnesses and21 source
comparisons remain intact. Only962 save lines removed; all other testbench bytes
and DUT/PWL/analyzer/source-diagnostic hashes unchanged. Actual parent-frozen
v1 resource dictionary copied unchanged, including8GiB output and600s queue wait.
No window split or fabricated early data introduced. Six-input v2 package
25,274,935 bytes. Current_v2_note.md provides a short operational handoff.

Original-reference native count111083 through61.9763ns vs129379 to target is
explicitly only a point-density proxy; actual v1 completed points are unknown.
Combined with path-width proxy, expected complete v2 output~2.69GiB, nearly3x
headroom to8GiB; actual v2 output/steps remain unmeasured. Existing CMI and LTE
warnings are not explained away by output failure or save reduction.
Six focused tests pass,0.104s, including actual v2 config->native peak/KCL
synthetic reduction, mandatory-field identity, save-only bytes and budget identity.
Package hashes and frozen-v1 preservation checked locally. No remote/registration,
budget increase, history deletion, circuit/sampling change, commit or push.

## Reuse completed v2 source; reduce fault-export columns only

Parent reports v2 Spectre complete/PASS/zero errors,411.44s,2,911,251,176 bytes,
peakRSS~391MB. Analysis then failed after459.73s/RSS14.68MB at fault.row budget
reserve: derived30MiB cap, not simulation failure. Preserve completed raw and
failed analysis artifacts. No Spectre rerun or budget increase is authorized.

Prepare a new analysis-only package bound to completed sar8audit-ref-current-v2
through the existing managed source_run_id/provenance pattern. New analyzer file
only; frozen v1/v2 analyzer and inputs stay unchanged. Reuse its tested reducer
with an explicit lossless export-column adapter: full27-column KCL stream stays;
fault stream324->64 columns (time+43V+all15 incident currents+5KCL). All275 currents
still required, summarized/integrated and retained at four native-peak snapshots;
21 source comparisons and228 screens unchanged. Only260 noncritical fault-wave
columns omitted; raw source remains available for later targeted export.
Hard30MiB derived/32MiB collection and256MiB RSS unchanged. No remote/registration.

Analysis-only local ready checkpoint: reference_source_reduce.py reuses the
unchanged SHA96689ee7... frozen reducer as an imported module with a scoped,
strict-column binary-writer adapter. No native measurement row/time is discarded.
Full KCL stream27 columns unchanged; fault stream324->64 columns. All275
statistics, signed/absolute charge integrals, native extrema and four275-current
peak snapshots remain unchanged. source_binding.json pins completed managed
sar8audit-ref-current-v2 recipe4fd9a1d867afc325c1071a698186e16ef8845691fc1cccf6e394d28cfadb88cc
and every registered source input. Actual source native PASS/exit0/zero-error,
registration and managed source_provenance are required; old failed analysis is
not treated as failed simulation. New result.json is still published last.

Seven focused tests pass1.946s, including actual275-config bit-identical full-KCL,
statistics/integral/peak comparison, exact fault-column subset/native row equality,
missing omitted-waveform current rejection, source-binding failure controls and
CLI read-only reuse despite a previous analysis failure. Source file hashes before
and after synthetic reuse match. No broad repeated suite or real-source run here.
Generated/source_reduce_v1 contains the small analysis-only recipe/binding/package
receipt; original DUT/PWL/measurement/analyzer and old failed outputs unchanged.
Freeze new package for parent registration/execution; no additional review layer.

## Completed recovery: direct branch attribution

Parent confirms reduce1 exit0/source binding and complete receipt8 files,
29,400,176 bytes/no skips; analysis522.63s,managed peakRSS~17.55MB. Collected
result147657 native rows and fault14293 rows are now read-only. Analyze native
five-node KCL, leading-lobe signed terminal charge, four all-current peak
snapshots and source reproduction deviations. Preserve CMI/LTE warnings and
distinguish PDK total D-port current from unseparated intrinsic channel/capacity.
Author concise numeric attribution, two native-wave figures and one minimal
single-variable proposal here only. Freeze all existing input/result packages;
no remote, new submission or source-result edits. Any local candidate is marked
unexecuted diagnostic and must not be presented as a successful circuit repair.

Native attribution complete: branch_metrics.json and two figures show leading
GNNA/GNNB/GNNDRV excursions44.989/-42.542/+67.986mV. Source peak error<=1.974uV,
time error<=0.0251ps. Rgate leading signed charge+0.0008766fC and peak+0.685855uA
leave GNNDRV, while local N/P drain ports balance it. A/B loading gate ports
oppose their respective leading excursions. Peak gate/source/drain directions
support local dynamic feedthrough; no intrinsic Cgd/channel split claimed.
Full five-node maxKCL3.78pA, fault1.30pA. Figures visually inspected. Warning and
later-bottom-negative-wave limitations recorded in current_branch_findings.md.

## Accepted next local experiment: common final-stage gate series1kOhm

Parent accepts the precise single-variable mechanism experiment. Prepare a new
immutable local simulation/analysis package only, driver0 GNNCN/GNNCP gates
reconnected from GNNB to a new common gate through one ideal1kOhm resistor.
All MOS geometry/models, other drivers, PWL, supply/sampling/closing timing stay.
Preserve all275 currents, add both resistor ports, update B-node incidence and
add new gate-node KCL. Preserve228 stress pairs with updated gate connections,
all A/B/C peaks/delay/load-settling observations; no code/whole-ADC pass claim.
Parent alone registers/submits; no extra review gate or remote task here.

To retain30MiB derived cap with six full-history KCL equations, export full-time
17 incident currents+6KCL+time (24 columns). Full139-voltage statistics/startup
remain; fault44-voltage window includes the new gate. Full-time voltage waveform
columns are explicitly omitted from this stream, not fabricated or called saved
measurements; original simulator raw retains them. Fault stream68 columns.
Frozen reducer remains unchanged; a new bounded wrapper handles six-node schema
and export-only selection with277 current summaries/integrals/peak snapshots.

Local candidate ready: generated/cinput_r1k_v1/ contains one-resistor DUT,
unchanged non-save testbench prefix, exact native baseline table/measurement,
managed recipe proposal and hash receipt. New reference_cinput_analyze.py imports
the frozen reducer; six-node validation retains its original five-node checks,
adds the new gate's three-terminal incidence and narrows only native exports.
Baseline21-voltage table is an exact column subset of completed-v2 fault data,
all14293 native times retained. Original275 currents+2 resistor currents,
139 voltages,6KCL/17 incident currents and228 updated terminal screens are saved.
Full24/fault68 streams preserve current evidence within unchanged30MiB cap;
all-time node-voltage waveforms are explicitly not in full stream, but full
statistics/initials and fault voltages remain. Raw simulator saves include them.

Additional metrics report fixed independent CODE243/Q0=1 BN0->VREFP/BP0->VREFN
settling with1mV diagnostic-only threshold, and same partial-window ideal-VDD
energy against actual v2. No full-ADC power/code/terminal-safety pass asserted.
Three focused tests pass1.384s: exactly two gate pins/one idealR and all other
primitive/testbench bytes unchanged; actual277-current/six-node schema and
stress mapping; actual staged package synthetic CLI including native export,
settling and energy fields. No Spectre execution has occurred here. Parent alone
registers/submits. Existing frozen source/analyzers/results remain unchanged.

## Completed R1k comparison (read-only source runs)

Parent confirms native/analysis completion and verified11-file27,863,346-byte
collection for sar8audit-ref-cinput-r1k-v1. Compare against completed current-v2
using the same64..65.9965ns native fault window, while reporting whole-history
extrema separately (GNN0 global45.37973ns peak is present in both versions).
Write only new module comparison metrics, all228 signed terminal-screen rows,
native-wave/current/KCL and settling figures. Quantify R-port charge/Ohm law,
independent BN0/BP0 target settling, same partial-window supply energy, and all
warnings. No frozen input/result mutation or new candidate/remote operation.
Recommend exactly one evidence-based next direction without generating it.

Comparison complete: compare_cinput_r1k.py produced three visually inspected
native-wave figures, comparison.json and all228_terminal_pairs.csv; concise
r1k_findings.md records the outcome. Same-window C excess67.986->57.580mV
(15.3% reduction), B negative42.542->44.300mV worsens, A remains44.878mV.
NewCG negative30.582mV still exposes its core PMOS Vgs1.020582V. The global
GNN0~1.006635639V/45.37973ns maximum is essentially identical in both versions
and is reported separately from65ns local peaks. C/GNN0 half-level falling
edges are delayed0.838/0.853ps. No waveform time shifts applied.

Full-history228 screen pairs:111 strict exceedances in both,87 exceed limit by
>1mV in both (record counts, not transistor counts or a relaxed limit). Candidate
worst shifts to untouched GNPCN,65.370mV excess.110 pairs can additionally be
computed from saved local voltages;118 local columns remain empty, not fabricated.
BN0/BP0 end residuals~-0.103455/+0.015432mV unchanged;1mV diagnostic entry native
brackets5.80/1.43ps exceed tiny entry-point shifts, so no resolved load-settling
regression claimed. Source CMI/LTE warnings retained.

R fault charges+/-1.23190145fC; full charges+/-1.23085773fC, instantaneous port
sum0, Ohm-law fault residual1.39e-16V. Six-node KCL max1.66pA. Gate-current
sum peak315.485->263.362uA while net gate charge~1.2319fC unchanged. R full
dissipation0.227386fJ. Partial ideal-VDD energy7.613665/7.613643pJ essentially
unchanged; no whole-ADC power claim. Report recommends a single1.8V-rated
driver-cell feasibility/real-load speed/stress characterization at retained
0.81..0.99V supply, including SS low/cold risk, before chain replacement; no
new candidate generated. Existing frozen candidate input hashes still match.
Focused data invariants/228-row uniqueness/current-charge closure and scoped
diff/UTF8 whitespace checks pass. No remote, source edits, commit or push.

## Rated driver-cell feasibility pair, independently commanded

Parent accepts moving to a real-load1.8V-rated cell screen. Prepare exactly one
IO geometry choice and matching core baseline at FF0.99V/-40C and SS0.81V/-40C.
Search prior native-accepted primitives first: io_cdf_audit and ioscreen cold
results supply nominalIO unit W320nm/L150nm/nf1, logic N multi2/P multi4.
The prior SS-cold FO4 delay~202.6ps is feasibility evidence, not full-load timing.
Do not repeat IO reference-switch substitution (those switches are already IO).

Boundary: representative bit0 NN driver A/B/C chain, same original three
inversions; core A/B are physical upstream cells in both cases. Only final C
changes to the previously native-accepted ordinaryIO N0.64um/P1.28um,L150nm.
Retain original all four bit0 Rgate paths, all physical reference switches/full
differential CDAC, both original bootstraps and reset-held comparator loading.
Other-bit gates and companion bit0 gates are explicit independent ideal logic
boundaries; comparator has no active decisions. Core B->IO C node is physical,
not voltage-forced; save its terminal stress and input/output back-action.

Generate corner-normalized independent logical PRE/companion commands; no FF
analog replay. Three-stage PRE rises43ns/falls48ns, declared10ps input edge;
companion gates have1ns BBM guard as a unit-bench fixture, not a new SAR contract.
Sample half-level on1/off41ns retains40ns external window; full Vin/ref/50ohm/
4pF conditions preserved.52ns stop covers both polarities and static plateaus.
Explicitly do not claim this PRE slew is actual SS or full async timing.

Own only new generated/io_cell_v1, generator/analyzer/focused tests and short
handoff here. Parent owns managed registration/serial execution, no remote/OA.
Freeze four small runs (core/io x FF/SS), one geometry candidate; no size/R sweep
or baseline adoption. All affected MOS terminal pairs/currents, upstream/core->IO
stress, load kickback, delay, settling and static behavior remain measurable.

Sampling-source readback resolves the exact contract: original VSAMPLE is
val0=SUP,val1=0,delay41ns,rise/fall100ps,width59.9ns,period100ns. Reuse that
line verbatim (first-frame high starts at DC, closing starts41ns); do not replace
it with the initially considered generic1ns-on waveform. Direct bootstrap clock
drive is an explicit ideal load-fixture boundary, not actual SS internal timing.

Local IO-cell package checkpoint: generated/io_cell_v1 now contains exactly four
unexecuted cases, core/io at FF0.99V/-40C and SS0.81V/-40C. Paired same-corner
testbenches are byte-identical; only flattened GNNCN/GNNCP differ. Complete
parameters copied from native-accepted F18IN/F18IP; original40 Rgate segments,
32 IO reference MOS, full CDAC, two bootstraps and reset comparator remain.
138 primitive records have no single-incidence internal nodes. Each case pins
five staged inputs and exact bytes/SHA in package_review.json (core268671B,
IO268633B); recipe hashes are included. No registered/remote run is asserted.

Analyzer reuses unchanged frozen reducer, validates447 mandatory currents,
93 voltages,7 exact-incidence KCL equations and450 terminal screens. Complete
0..52ns primary waveform94 columns retains critical voltages/currents/allKCL;
time-only auxiliary avoids duplication. Static rail deviations, both local
edge polarities, load settling and partial/direct-rail energy are diagnostic,
acceptance_pass remains null. No FF analog replay, fabricated source peak or
wholeADC qualification. io_cell_note.md documents unit-fixture ideal boundaries,
native geometry evidence, initial-high sampling contract and resource limits.

Validation: all3 focused tests pass0.408s, including staged analyzer CLI on
synthetic data and all-case receipt hashes. Frozen reference_current_analyze.py
SHA96689ee7afd0193a6037f66167a5daedf2f638aa43f52f25a16d7d52dc9ebe7e
and reference_source_reduce.py SHA7e4b30a9111c26b39ff85678ea6bf9cc4464b7843b78e404c37a1b793df1b649
remain unchanged. Scoped diff/UTF8/whitespace review completed. Parent may now
register and execute the four frozen proposals serially; no extra review gate,
remote operation, OA edit, commit or push performed by this module.

## Collected FF cell pair: read-only comparison

Parent confirms complete/verified11-file collections for refcell-core-ffcold
and refcell-io-ffcold; SS pair remains parent-managed. Own only new local
compare_io_cell.py, io_cell_ff_findings.md and generated/io_cell_ff_comparison.
Read collected sources without modification. Compare full-time terminal screens,
separate A/B upstream and C/GNN0 excursions, both local delay directions,
BN0/BP0 independently selected load settling and same-window energy. Preserve
CMI2751..2756 and core high-reference final BN0~+1.1376mV outside1mV diagnostic.
Use shared native absolute time windows with clear rail/target references; no
waveform alignment, new experiment, baseline adoption or fullADC conclusion.
Validate source waveform SHA, all450 paired records, input freeze hashes and
plotted dimensions; visually inspect final figures. No shared log/remote edits.

FF comparison checkpoint: compare_io_cell.py verifies11-file receipts, both
native waveform SHA, unchanged frozen-input hashes and all450 stress records;
outputs comparison.json/CSV/3 visually inspected figures and concise findings.
IO C12 pair screens all below1.98V, but C-node peak increases1.056699->1.371385V
and negative dip56.197->305.699mV. Core A/B still exceed0.99V by20.753/36.131mV.
GNN0 low-path disable/enable delays increase8.626/11.717ps; local changes are
not a complete async timing qualification. All450 strict screen counts36->26,
>1mV counts24->14; terminal-pair counts not device counts. CMI codes preserved.

Measurement interpretation corrected without changing frozen analyzer/results:
original44..47ns high-reference window includes turnoff starting46.995ns.
Its+1.137641/+1.139886mV final values are retained. Stable45..46ns BN0 errors
<=11.64/11.24uV; last preedge native points46.990430/46.987059ns~-.0111uV.
After turnoff to before next command47.995ns, BN0 rises+44.3668mV/BP0 falls
-35.3744mV nearly identically. Both versions settle before turnoff; this is
a separate real off/floating disturbance, not proof of on-state settling failure.
Low-reference BN0±1mV entry delayed12.87ps; high-entry3.06ps difference is below
native4.6ps brackets. Partial VDD energy918.899->920.849fJ; no fullADC claim.
No remote/new experiment/frozen input mutation. SS still parent-managed.

Final FF checks: independent CSV uniqueness/counts, both preedge/settling
windows and all CMI code preservation assertions pass; frozen reducer hashes
unchanged. Python syntax, UTF8/whitespace and scoped diff checks pass. All3 final
figures visually inspected, including wider GNN0 windows and47ns residual inset.
New comparison artifacts total898464B. Own findings explicitly marks~11nV
preedge residual as near10nV vabstol rather than a physical precision claim.
No commit/push, no shared files or immutable source-result edits.

## SS core recovery checkpoint; IO pair pending

Parent confirms sar8audit-refcell-core-sscold collected11files/4150189B,
zero skips. Read-only review now owns new review_io_cell_ss.py and
generated/io_cell_ss_comparison/ss_core_checkpoint.json. Generalize only the
new local FF comparison loader to accept an explicit corner/run identity;
do not change its delivered FF outputs, frozen measurement/analyzer/input or
any shared file. Preserve platform/on-settling vs turnoff distinction. No IO
comparison until parent supplies its actual completed collection.
Original io-sscold was confirmed queue_timeout without child/started_epoch,
not a simulated failure; parent alone handles explicit same-input -q2 enqueue.
No new experiment, registration, remote operation or adoption here.

SS core checkpoint ready:11-file4150189B receipt and all staged-input/native
waveform SHA match;8142 native points0..52ns. All450 terminal screens below
their model-specific limits (A/B/C worst0.875342/0.901466/0.935208V versus
core0.99V); no CMI codes in this fixture. This0.81V result does not qualify
the whole ADC or prove no overshoot relative to supply. B->C4.328/3.749ps,
B->GNN040.939/27.972ps for low-path disable/enable. High-on±1mV entry BN/BP
44.660954/44.745501ns; low-on48.753096/48.649314ns. Stable-on end errors
near numerical floor; off-gap BN+33.7752/BP-32.3876mV retained separately.
Partial VDD energy264.661fJ, C1.039fJ, A/B2.753fJ. IO comparison remains
explicitly pending; no invented pairing or inferred IO corner performance.

## Collected SS pair and FF+SS route assessment

Parent confirms SS IO completed run sar8audit-refcell-io-sscold-q2,
11files/3710891B, recipe70189d38065071c2a25266856ec1eb94274817c9263b44138707956787c84e3b;
PASS/zero-errors, no CMI. Old queue-timeout identity is preserved, not counted
as circuit failure. Own new compare_io_cell_ss.py, io_cell_ss_findings.md and
new files in generated/io_cell_ss_comparison. Keep existing checkpoint and FF
outputs immutable. Read-only pair analysis must verify q2 provenance/receipt,
same frozen IO inputs and baseline conditions. Compare450 screens, local timing,
stable-on settling, separate turnoff-gap disturbance and partial/direct energies.
Prepare same-native-time figures and qualify FF+SS support for rated C-cell
route without adoption/new simulations or changes to any shared/frozen file.

SS pair checkpoint: all450 screens below respective limits in both runs,
IO C worst1.113774V versus1.98V; A/B0.875399/0.883946V versus0.99V. IO C still
has larger output excursions (C min-.274963V, GNN0 min-.077163V). B->C
disable/enable4.328/3.749->57.494/48.252ps; B->GNN040.939/27.972->104.093/
80.201ps. Low-on BN0±1mV entry48.753096->48.826950ns(+73.85ps); other
settling shifts0.72..2.97ps are below native3..6ps brackets. Both stable-on
windows settle; off-gap BN+33.7752/BP-32.3875mV remains essentially identical.
Original47ns-window BN endpoint+.979624/+.796250mV retained; last native
times46.999881/46.999387ns differ on turnoff edge, so no injection improvement
inferred from endpoint subtraction. Partial VDD264.661->265.546fJ(+.334%).

New SS three figures/450-row CSV/comparison.json and io_cell_ss_findings.md
complete; FF comparison and SS-core checkpoint remain unchanged. FF+SS matrix
supports continued IO C feasibility work at these two points, not final size
adoption or chain closure. FF A/B still exceed; actual upstream interface and
SS delay budget plus off-floating disturbance remain separate constraints.
No CMI in SS fixture, original SFE/VACOMP preserved. q2 recipe hash verified.

## Single B-stage IO replacement: local preparation only

Parent authorizes prepare_io_bstage.py, io_bstage_analyze.py,
test_io_bstage.py, io_bstage_note.md and generated/io_bstage_v1 here. Start
from frozen completed IO-C fixture, replace only GNNBN/GNNBP with exact full
parameters/models of existing IO C (unit320nm/150nm,Nmulti2/Pmulti4).
Core A, IO C, all passives/load devices and independent stimuli are immutable.
Prepare FF0.99V/-40C and SS0.81V/-40C only; no remote/new submission/adoption.
Keep all450 screens/447 currents/sevenKCL/native94 columns. B screens reflect
its actual IO class1.98V while A remains0.99V. Preserve historical inputs,
analyzers and results. New wrapper may extend measurements with A->B loading
and separate A/B/C direct-rail energies; do not call the new mixed A/B chain
entirely core. One targeted local test checks exactly two changes and the
complete native IO parameters/screen mapping; focused synthetic analyzer
execution validates any new wrapper behavior, never a circuit success claim.
Main chat alone registers/queues both frozen proposals after handoff.

B-only local package ready: generated/io_bstage_v1/dut.scs SHA
2381b1d49e7df33d5b5af6755c75cc08aa05b8df40a9b7126c46163fc4fc7906.
Only flattened GNNBN/GNNBP differ from completed IO-C; exact existing C IO
model/geometry/parasitic parameters copied.138 primitive records, no
single-incidence internal nodes. FF/SS six-input totals274943/274946B;
same-corner testbench bytes identical to old IO-C. Baselines bound to completed
io-ffcold and io-sscold-q2 result hashes. Recipe proposals are not registered.

New stdlib/Python2.7-compatible analyzer wrapper reuses unchanged frozen cell
and current reducers;450 screen/447 current/7KCL/94 native-column surface stays.
B12 screens map to actual IO1.98V, core A stays0.99V. A/B total energy relabeled
as mixed stages, separate A/B/C energies and PRE->A/A->B delays added. B gate
sum current/full charge and native event42.98..45/47.98..51ns integrals quantify
loading on A without omitting precommand feedthrough. Original on/off window
caveat retained and acceptance null. One focused test passes0.494s, including
actual six-input staged analyzer CLI on synthetic data. Initial synthetic edge
fell outside its event window; fixture corrected to causal staged transitions,
without touching real stimuli. No remote/registration/old input edit/adoption.

## Collected B-only FF: causal comparison against IO-C

Parent confirms sar8audit-refcell-iob-ffcold collected11files/3988387B,
managed recipea89eda94b9e3b68db0598a21cbde394af33dd297f9c18f82d0ea9366df36aae6,
nativePASS with remaining CMI2751/2754/2755/2756. Own new
compare_io_bstage.py, io_bstage_ff_findings.md and generated/io_bstage_ff_comparison.
Read only small collected IO-C/B-IO FF traces; recover baseline gate-load and
upstream delays from existing94 columns. Compare A/B/C stress and signed gate
current/charge/rail energy, complete PRE->load timing, real load stable-on
settling vs off-gap disturbance. Preserve frozen analyzer's missing PRE event
or other diagnostics; any local remeasurement must state widened edge window
and native witnesses rather than overwrite results. No new run/circuit expansion.
SS remains parent-managed and is not inferred from FF.

Parent subsequently supplies completed SS iob-sscold collection11files/
3948132B, managed recipead9bc0c2c590427fac6d81ca47b273f278f6a3aec353b01309f11de733fab36e,
nativePASS/noCMI. Extend same new local comparator for explicit SS input and
new generated/io_bstage_ss_comparison only; single combined short
io_bstage_findings.md replaces planned FF-only report. No separate large report,
next candidate or repeated simulation. Keep prepared/frozen sources unchanged.
Also own small generated/io_bstage_comparison_index.json and
generated/io_bstage_timing.png for a single linked summary of both completed
comparisons and the complete PRE->load delay decomposition; no raw duplication.

B-only paired checkpoint complete: compare_io_bstage.py consumes only small
collected data; 450 CSV rows/corner, full native gates/current event charges,
stage energies and time-window-separated settling/off-gap saved. Independent
local B-gate metrics reproduce remote new-wrapper metrics at tolerance1e-24.
No waveform shift. Old PRE-rising null preserved; widened native edge-witness
observation recovers timing lost at strict43ns rounding boundary.

FF core A worst1.010753->1.009099V remains over0.99V. New B/C both below1.98V,
but B actual peak rises to1.199118V and C worst terminal is then input-gate
stress1.199118V (C output peak1.147291V). FF strict pair counts26->18,>1mV14->4;
SS all450 remain zero. Gate charge per A-rising event1.232->2.429fC FF and
.870->1.365fC SS; A direct-rail energy2.197->3.397/1.359->1.782fJ. SS GNN0
min-.077163->-.121881V even while C output kick falls. Measured changes support
loading/edge reshaping, not a claim IO eliminates overshoot or intrinsic Cgd split.

Complete PRE->GNN0 delay FF82.84/50.59->105.88/64.36ps, SS115.94/91.53->
252.67/234.00ps. Low-on BN0 entry later14.75ps FF/148.32ps SS; all proper
on-windows settle and static states recover. Off-gap disturbance unchanged.
One combined report gives next recommendation: address remaining core A and
real PRE interface voltage safety, allocate actual SS total delay before A
implementation; no next candidate or adoption. Six native-wave figures plus
one timing summary created locally and visually inspected (summary legend
overlap corrected). No remote/frozen/shared writes, commit or push.

Final bounded checks pass:450 unique paired rows per corner, screen counts,
proper on-window entries, end-to-end delay sum, combined-index SHA and all
original IO-C/B-only frozen input hashes. Syntax/UTF8/whitespace/scoped diff
checks pass; static recovery checked directly in both candidate source results.
Only new local module comparison artifacts and this owned plan were written.

## A-only IO replacement and exact original PRE boundary

Parent authorizes only generated/io_astage_v1/, prepare_io_astage.py,
io_astage_analyze.py, test_io_astage.py, io_astage_note.md and
pre_driver_boundary.json in this owned subtree. Start from completed IO-BC,
change only GNNAN/GNNAP to the same full verified320nm/150nm,nf1,Nmulti2/Pmulti4
ordinaryIO parameters. B/C, all physical loads, PRE and sampling commands stay.
Prepare FF/SS cold locally; main chat alone registers/submits. No next design,
remote/OA/shared edits or adoption. Preserve original body currents and signed
junction polarity,450 actual-model screens, negative GNN0 excursions and SS
~.25ns timing context even if IO1.98V screening succeeds.

New metrics must measure PRE N/P input-gate charge, independent ideal PRE
source delivered/returned work and source KCL, separately from VDD energy;
complete PRE->GNN0 delay and independent correct ON-state settling windows.
No ideal-source power summed into VDD or fullADC power claim. Extend via new
wrapper only; frozen old analyzers/data remain unchanged. One minimal mapping
test with synthetic staged analysis validates changed measurement behavior.

Read-only original whole-ADC export a42e44613b4b1a8a74876a4c996f5bd2bf2e74bf13da6729818ab85bde5a21de
identifies PRE source XREF.XDRV0.X025(sar8p_inv), its actual MN/MP drain pins,
original two A-gate loads and upstream L0 shared GPP/input fanout. Record exact
flattened instance/pin/geometry identities and provenance for later physical
driver fixture; this experiment retains ideal PRE and cannot qualify that driver.

A-only local pair ready: newDUT SHA
adfb47cac3e923acb59cbb0a171e38e20cb0b5be87346fc4bedc1a1b5a6896c3.
Only GNNAN/GNNAP flattened records differ from IO-BC; both reuse exact existing
C IO parameters. Eight inputs292468B per corner,450 screens/447 currents/7KCL/
94 native columns unchanged. New stdlib wrapper calls unchanged reducers and
adds PRE delivered/returned/gate work separately from VDD, PRE KCL/input charge,
complete edge witnesses, correctly cut ON settling, explicit supply excursions,
150 signed junction-polarity records plus native body current extrema/charges.
Coincident body current is available only where its native waveform column
exists; other records stay null. No assumed diode threshold or body-current
decomposition. Stage A energy correctly relabeled IO, not core.

Read-only source trace found PRE driven by core XREF.XDRV0.X025 MN/MP drain1;
exact original PRE has only A N/P gate2 loads. X025 input L0 is shared with
GPP N/P gates and driven by XBBM0.X004.X001. pre_driver_boundary.json records
both incident sets4/6, full original driver parameters and source provenance.
Current ideal source omits this core driver, explicitly no interface acceptance.
SS baseline252.67/234.00ps and GNN0 negative121.88mV retained in handoff.

One minimal mapping/synthetic CLI test passes0.620s: actual new staged package,
exact2 changes, unchanged commands/other screens, PRE source sign/work closure,
150 junctions/N-P polarity/body-current witnesses, negative GNN0, full delay and
proper ON windows. No real circuit result asserted. Main chat alone registers.

Final A-pair local checks pass: all eight new input bytes/hashes and both
recipe hashes, all old IO-C/IO-BC frozen input hashes, no single-incidence
internal nodes, Python syntax/UTF8/whitespace and scoped diff. New proposals
remain unregistered/unexecuted. No commit/push or shared-path changes.

## Collected A-only pair: concise BC->ABC assessment

Parent supplies FF ioa-ffcold11files/4121724B, managed recipe
f1e6dd17f97789e692fb6f9a988804048275ba32cefcbe414c9265952544f4f1.
NativePASS8410points; remaining12 strict screens are reset comparator microvolt
records, not reference chain. SS analysis still parent-managed; no remote poll.
Own new compare_io_astage.py, io_astage_findings.md and
generated/io_astage_comparison/. First summarize FF, then append SS only after
parent supplies verified collection; final one figure has corners side by side.
Compare PRE work/load, full timing, body forward polarity and actual-model
stress separately, correct ON establishment and off-floating residual. Existing
BC94-column waves may supply new baseline metrics locally without simulation.
Keep baseline core-A model label when remeasuring formulas. No source/frozen
analyzer writes, generic report expansion, repeated test suite or new package.
Suggest minimal real X025/L0 shared-load fixture only; current PRE ideal remains
explicitly unqualified and body-current totals do not prove diode fraction.

Parent now supplies completed SS ioa-sscold11files/4037948B, managed recipe
327a9455d983dfa17c1d72eb7ba456af43b7539f007e80ee7633c4133413e283,
7915points/no screen exceed. Complete both corners in the same short report
and one paired timing figure. No queue/status request or extra experiment.

A-pair comparison checkpoint: compare_io_astage.py verifies both new receipts,
SHA/inputs/native waves and reuses same PRE-work formulas read-only on completed
BC traces (only actual PRE/junction/timing fields extracted; baseline A stays
core in saved model labels). Four cases1800 terminal rows and one8-panel
FF/SS native-time figure stored; no generic figure batch/test sweep.

Reference A/B/C zero strict screens in ABC at both points. FF all12 remaining
strict records are XCOMP, max2.933uV, original CMI preserved. ABC A/B/C worst
FF1.162828/1.162828/1.140901V, SS.960077/.960077/.960807V; larger A excursions
remain within IO rating. A drain junction forward-polarity FF119.6/172.8mV,
SS115.7/150.1mV with coincident total body currents+7.92/-14.03 and
+12.43/-24.30uA. No diode-current fraction/threshold claim.

PRE charge per rise1.232->2.429fC FF/.870->1.365fC SS. PRE source net work
.236->.630fJ/.175->.299fJ separately from VDD, not added. Full PRE->GNN0
119.562/88.048ps FF,402.956/375.908ps SS. GNN0 minimum-.030565/-.120084V.
Low BN0±1mV entry48.291495/49.117648ns; all proper ON windows establish,
off-gap disturbance unchanged. Report suggests real X025 with original core
geometry and L0 shared GPP physical branch/load, remove conflicting ideal
output sources, clearly retain any ideal L0 boundary and unverified BBM driver.
No new fixture generated or remote job launched; no frozen/source edits.

Final A comparison checks pass:1800 unique records/450 per case, stage class
and strict-count identity, all proper ON entries, complete delay sum, PRE
delivered-minus-returned/source-vs-gate work closure<1e-24J, FF remaining strict
records exclusively XCOMP and SS none. All original IO-C/BC/ABC input hashes
unchanged. Syntax/UTF8/whitespace/scoped diff pass. Final paired figure visually
inspected after short-axis-label layout change; comparison folder640586B.
No new broad tests, simulations, candidate package, commit or push.

## Real PRE / shared L0 load: local freeze only

Parent authorizes prepare_real_pre.py, real_pre_analyze.py, test_real_pre.py,
real_pre_note.md and generated/real_pre_v1 here. From frozen ABC restore original
core X025 and six original core GPP stage devices, driving existing Rgate and
physical P-side reference load. Remove VPRE/VGPP output forcing; boundary moves
to independent inverted L0 command with original external sampling unchanged.
No alignment of physical PRE; no retiming/sizing/PDK change. FF/SS cold only.
Main chat alone submits. L0 remains ideal and BBM source is still unverified.

Own new variable-size current/KCL validation and measurements for actual PRE,
L0 shared gates/source work, original/new core voltage screens/body polarity,
actual GNN/GPP control skew and same-side opposed branch-current coincidence,
proper ON settling and static recovery. HalfVDD control state is not a MOS
conduction test; total drain/body currents do not prove shoot-through fraction.
Retain all added MOS port currents/stress and exact source provenance. One
minimal mapping/shared-load/no-source-conflict/synthetic measurement test,
then freeze executable packages and brief note. No old-case rerun or large
report, remote/OA/shared-file writes, adoption or push.

Real PRE local checkpoint: generated/real_pre_v1 keeps all138 ABC primitive
records under explicit PRE/GPPDRV internal-node mapping, restores exact original
X025 two core MOS plus GPP6 core MOS.146 primitives/83MOS,96V/478mandatoryI,
498 actual-model screens,14 exact-incidence KCL nodes,152-column full native
stream. VPRE/VGPP removed; L0 shared4-gate source initialSUP/fall43/rise48ns,
10ps. Actual PRE edge is not forced/aligned. Old sampling/model/supply and
other companion commands unchanged. Both seven-input packages312423B.

New stdlib reducer wrapper accepts explicit14-node schema, reuses unchanged
stream parser/writer and adds source/internal work closure, actual stage delay
and same-side halfVDD control gaps, opposed total reference-port current
coincidence, correct ON targets,166 signed junction/body-current records and
negative rail excursions. Core X025/GPP remain0.99V screens, ABC1.98V. L0
source work/internal PRE work/VDD energy remain separate; no conduction claim
from logic threshold or total transient currents. BBM source remains ideal-cut.

One focused restoration/shared-load/source-conflict/staged-analysis test passes
0.585s. It checks all retained records/new core params, original model/clock
lines,7-input hashes and synthetic CLI with498pairs/478I/152columns, source
and internal work, body/negative excursions and20ps synthetic GNN/GPP skew.
No real simulation or circuit success asserted. real_pre_note.md is short
handoff; main chat alone registers/executes. Old files and results untouched.

## Collected real PRE pair: short priority/current-cause analysis

Parent supplies verified FF realpre-ffcold11files/7253880B,9237points,
recipec9909243ed203316d852a034eb18d5552a4a631aa925158124f1377f5e4c969f;
SS realpre-sscold11files/7162427B,8848points,
recipe0809de01ca6223f739f43ecc47f84111b0eb74ad6777968445763ffe109f7a42.
Own new analyze_real_pre.py, real_pre_findings.md and
generated/real_pre_comparison/. Read only completed small152-column traces and
previous ideal-boundary ABC traces. Separate X025/GPP/GNN/load screen groups,
leading-lobe signed incident port charge/current, control gaps vs actual
opposed terminal currents, source/internal work and correct ON settling.
One concise dual-corner comparison/causal plot set, no report hierarchy.
Frame new faults as restored ideal-interface omissions, not ABC regression.
Suggest exactly one supported module-level variable, not blind serial IO swaps;
do not generate new candidate, remote work, generic review or repeated tests.

Parent adds interpretation lens from user recovery discussion: distinguish
edge-local coupling from post-edge sustained currents/slow voltage restoration
using existing native data only. No new experiment/topic. Total D/G/S/B port
currents and KCL cannot establish channel-current imbalance, triode region or
junction conduction; record late-window voltages/currents and diagnostic
settling after input edge, qualify mechanism limits explicitly in same report.

Real PRE paired checkpoint: X0256/12 FF strict records (worst19.124mV excess),
GPP24/36(worst66.699mV), ABC0/36, load12 microvolt comparator records; SS all
498 zero. Leading FF PRE lobe local N/P drain charges-.01431/-.01722fC,
A gates+.03153fC; GPP C N drain+.001813/P drain-.002675/Rgate+.000862fC.
Local total-port flow supports edge-coupled redistribution, no Cgd/channel split.

Recovery lens added in same analysis: after48.005ns L0 edge, load current
returns to PRE/GPP C and is absorbed at driver N drain. FF near48.04ns,
A gates-9.70uA/Ndrain+9.97uA withPRE5.47mV; Rgate-4.14uA/Ndrain+4.17uA
withGPP C2.24mV. Sustained1mV output entry PRE66/154ps, GPP C101/105ps
after48ns. Late49.5..50.5ns totalD currents<=~1.8nA FF/~.05nA SS and
rail restoration observed. This establishes a load-feedback tail, not triode,
diode conduction or fixed Iss>Ip; KCL cancellation cannot identify channel bias.

One short report/3 figures now combines corners. L0->GNN0 off/on122.68/93.03ps
FF,409.93/386.75ps SS; branch skew62.46/60.71 and353.56/348.26ps. Correct
ON establishment persists; minimum halfVDD same-side gap901ps FF/612ps SS
is diagnostic only. Suggested one next module-level variable: replace bit0
GPP's3 identical core inverter stages with one already-validated IO inverter,
retain odd polarity/L0/Rgate/load/command and leave X025/ABC unchanged. Not a
proven optimum or generated package; original X025 residual still unresolved.
No mechanical whole-chain IO swap, remote job, new candidate or source edits.

Final real-PRE checks pass:996 unique paired terminal records, group counts
42 FF/0SS, leading/tail signed charge/KCL closure, positive diagnostic control
gaps, correct ON entries and late low-level recovery. All frozen input hashes
across IO-C/BC/ABC/real-PRE unchanged. Syntax/UTF8/whitespace/scoped diff pass;
three final figures visually inspected. Output folder1065419B. No broad tests,
new simulation/candidate, shared changes, commit or push.

## One GPP IO inverter implementation: local controlled package

Parent authorizes prepare_gpp_single_io.py, gpp_single_io_analyze.py,
test_gpp_single_io.py, gpp_single_io_note.md and generated/gpp_single_io_v1/.
From completed real-PRE fixture replace only bit0 GPP3 identical core stages
(six MOS) with one verified ordinaryIO INV pair320nm/150nm,Nmulti2/Pmulti4.
Preserve L0 inversion, original Rgate/load, core X025, ABC, all commands and
sampling; no internal-edge compensation. This is one driver-implementation
variable changing device count/parasitics together, not one-transistor causality
or ADC architecture change. X025 core0.99V screen/known residual remain.

Own only new local preparation/analyzer adaptation/focused mapping measurement
test and short handoff. Reuse frozen native parser/writer; do not edit prior
analyzers or results. Preserve source work/L0 burden, both branch timing/gaps,
all actual-model screens/body polarity/negative excursions/ON settling. L0
still ideal; no complete chain claim. Two FF/SS cold proposals only, no remote
registration/submission, parent owns managed execution. No new report layer.

Frozen GPP single IO checkpoint: focused test passed (1 test, staged analyzer
on synthetic scalar data; no Spectre performance claim). Exact6removed/2added,
140retained equal, commands unchanged, 79MOS474screens462currents12KCL132native
columns, coreX0250.99V retained. No single-incidence internal nodes or stale
GPP A/B stage assumptions. Syntax/UTF8/whitespace pass;62 preceding frozen
input hash records unchanged. Package review hash
ae96975f7e89dd2c23e1ed1f837c2ede5d3224ea99f09df57dc2def3ed335792.
FF recipe hash426b80e4438a8198093f7a94b30fd47d50ae8f8d711f9c4ade7756273f50fdc8;
SS recipe hash9d65f0c0a43a13ab9d34b9aba9df588e03a00b969186720d93acc78307b59674.
Short gpp_single_io_note.md records scope/limits and exact handoff. Not registered
or simulated; parent owns later managed queue. No shared edits/commit/push.

## Completed GPP IO results: paired local interpretation

Parent supplies FF completed collected run sar8audit-gpp-singleio-ffcold,
managed recipe f75375b04ba9631de7d93636fb5323717ec57046cc6da0068688e56b22bfb3b0,
11files6013768B8844points. SS simulation completed under managed recipe
1933f7950fcca2fa5e96c9b9cf03205a5bad25d117a042d7be37ce95b9c72317;
local receipt not yet present at start; do not infer its data. Parent collects.
Own analyze_gpp_single_io.py, gpp_single_io_findings.md and
generated/gpp_single_io_comparison/ only in addition to own plan/checkpoint.
Read small completed native traces and results, verify receipts/hash/size/native
pass and prior real-PRE binding before use. First FF interpretation, then merge
SS only after complete receipt verification. Compare actual-model screen
groups, X025 remainder, signed phase gaps, negative voltages, correct ON load
settling, L0 load/source work and direct stage energy. Separate absolute rail
excursions from IO rating screens; no complete-chain qualification.
Minimal figures/report, no new candidate/testbench, remote actions, adoption,
shared edits, commit or push. Current unrelated dirty ownership remains intact.

GPP paired result checkpoint: FF8844points6013768B and SS8346points5992515B,
11files each SHA/size verified;1944 terminal records, two figures inspected.
FF GPP24/36->0/12 at IO1.98V, but GPPDRV -240.667mV/1.270576V;
SS GPPDRV -290.528mV/1.115649V. X025 FF19.120mV excess persists;
GNN0 SS minimum-120.031mV unchanged. GPP branch is slower (SS+40/48ps),
latest low ON entry only~4ps later. L0 abs edge charges2.464/2.465->3.666/3.661fC
FF,1.740/1.740->2.238/2.235fC SS. GPP direct supply energy decreases while
idealL0 net work increases; no whole-chain acceptance. Parent reviewed report
and both figures; stop repeated checks. No next candidate or remote work here.

## Restore original physical L0 driver boundary

Parent authorizes real_l0_note.md,prepare_real_l0.py,real_l0_analyze.py,
test_real_l0.py,generated/real_l0_v1/ under reference/ only. Conditional source
is frozen GPP singleIO fixture. Trace original XREF.XBBM0.X004.X001 L0 driver
and all actual fanout; restore that original stage and actual load, moving ideal
input boundary exactly one driver stage upstream. Keep X025, GPP IO geometry,
all other loads and sampling commands/edges unchanged, no internal alignment.
Identify true original instance/port slice before implementation; do not silently
truncate sibling fanout. Retain source-side new stress/body/load/work and native
branch timing, correct ON windows. L0 delay must emerge from real stage; next
upstream remains explicitly ideal/unqualified. Prepare only FF/SS cold packages
and one focused mapping/measurement test, parent owns remote queue. All prior
frozen sources/history/OA/PDK read-only; no shared edits/adoption/commit/push.

Real L0 local checkpoint: original L0 has only6 incident ports (source2D,
X0252G and originalGPP2G); no sibling fanout omitted. Restore original
XBBM0.X004.X001 core pair as L0SRC;142 old records equal with explicit
L0->XDUT.L0 alias. Upstream idealL0N is original X004.N/NAND output, not full
BBM. Complementary input command midpoints43/48ns retained without delay
compensation; other sources/models/settings unchanged.81MOS486screens470I,
95V13KCL142native, new source0.99V screen/body/source-work observed. One focused
mapping+staged synthetic analyzer test passed; syntax/UTF8/whitespace/no single
internal incidence checks pass.76 previous frozen input hash records unchanged.
FF recipe9ca350694455bfbe7d05f0daef82399daf42dbc0d967558f738354a1396258c7;
SS recipe84057714e091d28f1d08ccf0c6eab515cb93f264a751367bfd310dbc24475202.
Each7inputs303812B; full local handoff in real_l0_note.md. Parent handles
managed execution; not registered/submitted/simulated. No shared edits/commit.

## Real L0 completed-source interpretation

Parent supplies real-l0-ffcold recipe
05a160866e5f9d0a2c8a870c1fdda9150735713fab975613e192848cb8cd4ac1,
11files6600138B8966points470currents. SS same original run queued externally;
no receipt at start, do not resubmit or infer SS. Own analyze_real_l0.py,
real_l0_findings.md and generated/real_l0_comparison/ for local bounded
interpretation. Compare with frozen completed singleIO input-boundary run,
retain exact source-stage added screens and source/load signed terminal flows,
correct ON settling, actual timing and separate external/internal work. Draw
concise source and load plots from native complete small traces, no alignment.
First FF partial result; merge SS only when parent supplies complete collected
receipt verified against managed run identity. No new circuit or candidate,
remote operation, shared edit, adoption, commit or push. Keep ideal N boundary
and new core source failure explicit; no whole-BBM/ADC acceptance.

Real L0 dual-corner checkpoint complete: FF11files6600138B8966points,
SS11files6490553B8527points/470currents, native receipts/hash/size/input PASS
and lossless monotonic table bindings checked. SS managed recipe
5a871ba335820094f7e7d7aa87e61b15aeae21dccdd1a057fdb333b0ba6f95a2.
1920 unique old/new terminal records; two figures visually inspected.
FF new L0SRC6/12 fails(max1.007959V), X0256->10/12(max1.016824V),
GPP0/12(IOmax1.327264V), load12microvolt; total28/486,14over1mV.
SS486strict clear/noCMI, onlySFE1131/VACOMP2435; realL0 min-30.099mV,
PREmax.872312V, GPPmin-.254910V/max1.105327V remain non-rail excursions.
L0 positive leading D charges-.013932/-.030179fC FF,
-.009286/-.084795SS; X025/GPP gates absorb +.014618/+.029493 FF,
+.034146/+.059936SS. Charge/KCL closure supports source-side edge disturbance,
no intrinsic capacitance/channel/diode attribution. Correct high/low ON entries
remain; latest low entry48.435827FF/49.133605SS. New source directVDD4.639fJ
FF/2.501SS; idealN work and internalL0/PRE transfers separately retained.
One priority suggestion only: establish actual upstream NAND X004.X000 N
edge/backfeed boundary before choosing L0SRC/X025 repair; not another candidate.
Counts, charge closure, ON windows, syntax/UTF8/whitespace pass. No remote
actions/new package/adoption/shared edits/commit/push. Stop repeated analysis.

## Complete original bit0 BBM boundary at CODE

Parent reviewed real-L0 report/figures and authorizes prepare_real_bbm.py,
real_bbm_analyze.py,test_real_bbm.py,real_bbm_note.md,generated/real_bbm_v1/
under reference/ only. Restore whole original sar8p_nonoverlap CODE->H/L,
both delay legs and ANDs and all actual fanout. Conditional source is frozen
real-L0 slice; preserve tested GNN ABC IO/singleIO GPP/X025, all sampling/supply
and physical loads. Restore original H-side GNP/GPN driver chain as needed
to preserve complete H load and remove ideal GNP/GPN forces. Replace separate
local L0SRC with original BBM copy of same devices under explicit mapping.
First trace exact full fanout/primitive list from frozen original, then build.
Only ideal CODE input remains for bit0 reference control; logical events43/48ns
but no H/L delay compensation or presumed old1ns guard. Full original analog
load remains, other bits unchanged/static, no whole ADC or other bit restore.
Observe all actual-model screens/body currents/KCL, input load/source work,
both-branch mutual exclusion and actual-reference settling. Missing edges or
52ns nonsettling must remain failures/unknowns; no forced success. Two local
FF/SS cold packages with existing resource caps and one minimum mapping/native
measurement test. No remote operation, new repair candidate, architecture,
source history/OA/PDK/shared file edit, adoption, commit or push. Existing
unrelated dirty ownership (Obsidian/10bit/parent registries) stays protected.

Whole-BBM local checkpoint complete: original40 primitives(30MOS6MOM4R),
both full delay legs/ANDs; H driver14original MOS restored. EachH/L exact6
incident ports includes all4real gate loads. Existing142 records retained under
explicit GNP/GPN internal mapping; oldL0 pair relocated unchanged withinBBM.
196primitives123MOS; onlyCODE ideal reference logic, oldVL0N/VGNP/VGPN gone.
CODE43rise/48fall10ps, old44/47 ideal H commands removed; actual guard not
compensated. SAMPLE/closing edge/supply/models/other sources unchanged.
116V656I738screens36KCL376native;246body observations, all new core0.99V.
Actual ON gating includes CODE/H/L/all4gates; missing/ambiguous edges unknown,
52ns nonsettling false; previous fixed windows only labelled diagnostics.
One focused mapping/staged synthetic-native test passed, including actual
unknown and not-established branches; synthetic CODE bracketing corrected to
represent its43/48ns midpoint, no physical stimulus changed. Exact full BBM/H
primitive comparison, source/load work, opposed ports and energy covered.
Syntax/UTF8/whitespace, no internal one-incidence nodes and90 prior frozen
input hash records pass. Same512MiB4thread simulation/256MiB analysis budget.
FF recipe435a572603391889baf830fd51477594e1f40c13b326ad64ea84d89fc7542bd5;
SS recipeebabae8782feee254f667ce04016b900e095d0bac6f9dc309156f5f90b969d33.
Each7inputs434235B; real_bbm_note.md and package_review.json hold handoff.
No registration/submission/simulation/OA/PDK/shared changes/adoption/commit/push.

## Full BBM collected-source diagnosis and physical window clarification

Parent completed/collected FF sar8audit-real-bbm-ffcold: managed recipe
7559d2fd8cb85edf5034c7711babe6f653611d0b52bba9b122f2b1616b87820a,
11files22435355B11326points656currents; CMI2751..2756 retained. SS native
completed, managed analysis pending; no local receipt at start, no assumptions.
Own analyze_real_bbm.py,real_bbm_findings.md,generated/real_bbm_comparison/
under reference/ only. Keep all frozen builder/analyzer/config/source/results
read-only; parent approved input freeze and owns remote queue/collection.
Verify receipt/input/native identities and inspect bounded native curves.
Frozen high-ON halfVDD end reaches48.06785ns after CODE48ns and includes
turnoff injection: do not call its false flag a stable-high settling failure.
Add independent command-stable high evaluation ending before CODE falling
starts47.995ns, separately report post-CODE/pre-halfVDD switching disturbance.
Preserve original measurements unchanged alongside clarified interpretation.
Analyze H/L/four gates/bottom/reference and signed source/driver/rail currents,
real steady plateaus, negative excursion stages and new model screens. Merge
SS only once exact complete receipt verified. Minimal paired report/figures;
no circuit/PDK/OA edits, new candidate, remote action, adoption, commit/push.

Full-BBM paired diagnosis complete: FF11326points22435355B,
SS10975points22627864B;11files each verified, streams projected101columns
while hashing every original376-column row.1476 unique terminal records;
three figures inspected and parent reviewed. High establishment FFBN43.583991/
BP43.391137ns, SS43.938057/43.990761ns; preCODE47.995ns endpoint errors
nanovolt-scale. Original frozen high false includes next turnoff up to
48.067849FF/48.071621SS, retained unchanged as switching residual.
Low establishmentFF48.451880/48.585845ns, SS49.363714/48.973808ns.
FF213/738strict (121BBM70H10X02512load); retained486 old28->32fail,
newlyrestored252 has181fail. SS738clear, but actualN-side high handoff gap
-191.747ps despite positiveBBM185.134ps; opposed native D min magnitude
10.863uA, not pure-channel proof. HD RC1 FF1.059705V, X005gd1.062566V;
MP_CLEAR D leading net-.436382fC absorbedC1+.345053/R1+.032955/gates+.058373.
Source charge/KCL and physical preCODE/next-turnoff phases verified; raw JSON,
old analyzers and input hashes unchanged. Parent accepted one next HD C0
delay-multiplier contrast; no additional interpretation review needed.

## HD delay C0 multiplier only

Parent authorizes prepare_bbm_hdc0.py,bbm_hdc0_analyze.py,test_bbm_hdc0.py,
bbm_hdc0_note.md,generated/bbm_hdc0_v1/ under reference/ only. From frozen
full-BBM package change only XDUT.XBBM0.XD_HD.C0 MOM multi1->4. Clone the
HD delay master locally as necessary so LD and every other flattened record
remain byte/parameter equivalent. Existing PDК sources/models read-only.
Keep CODE and external sampling/supply/timing exact, no internal compensation.
Observe all738screens656currents36KCL, source work/input burden, both control
directions and both delay-leg resets. Preserve old cross-halfVDD windows as
switching diagnostics plus independent pre-nextCODE high establishment;
missing edges and52ns nonsettling explicit. FF/SS local packages and one focused
mapping/measurement test only. This tests interface timing, does not claim RC1
overvoltage fixed. Parent owns remote; no OA/shared edits/adoption/commit/push.

HD C0x4 local checkpoint: only flatXDUT.XBBM0.XD_HD.C0 multi1->4 changed,
195other records identical, HD master cloned so LD unchanged. Full testbench
byte-identical for each corner; no edge compensation. Same unit geometry
exists atmulti2/200 andsame modelmulti4 atlr2u in completed fixture; candidate
native validation remains pending. Frozen BBM analyzer reused byte-identical;
new wrapper additive pre-nextCODE high establishment and HD/LD reset diagnostics,
preserves original cross-halfVDD fields as switching diagnostics.738screens656I
36KCL376native and all source/body/opposed-port fields kept. One focused
mapping/staged synthetic measurement test passed (preCODEtrue/turnofffalse,
52nsnonsettling, both resets, missingcontrol, work closure/native columns).
Syntax/UTF8/whitespace/hash/size pass; previous fullBBM frozen inputs unchanged.
FF recipe0ab4664d440537a1120e13626c576cc5e23fefdf981d4153ef638c89ddd4c892;
SS recipe86caf38f2d3f07a8002b26f9d78ecee40ed6c771f10f01f8d9d5ded291102523.
Each8inputs442695B; bbm_hdc0_note.md holds handoff. Parent notes MP_CLEAR
alsoFF1.008802V ds/bd duringnegativeRC1; all retained, no receiver-only fix claim.
Corrected full-BBM report figure count tothree without reanalysis. No remote
actions/new extra candidates/OA/PDK/shared edits/adoption/commit/push.

## HD C0x4 completed comparison

Parent supplies sar8audit-bbm-hdc0x4-ffcold complete collected11files22574580B,
11421points; managed recipe97c93bdf4a718ddce8129b348d98c442a71a689d8aa35e3bae909ce356153ef3.
SS original run started serially, no receipt at this start; do not resubmit.
Own analyze_bbm_hdc0.py,bbm_hdc0_findings.md,generated/bbm_hdc0_comparison/
under reference/ only. Compare paired completed full-BBM baseline and candidate
on native CODE-aligned time, full738 terminal records, RC1 positive/negative
and clear branch, reset of both legs and independent physical CODE-phase
establishment, source/load work and input burden. Delay increase alone is not
a fix. Read bounded native tables/verify exact receipt and source binding;
retain original metrics unchanged. FF first, merge SS only on complete receipt.
Necessary comparison plots/short report only, no extra experiment or candidate,
remote operation, frozen analyzer/config/raw edits, adoption, commit or push.

Parent forwards user steering: standardize digital gates. Finish in-flight C0
results as evidence; no further custom-gate tuning packages. Own added
standard_cell_boundary.md in reference/ only. Document exact original reference
Boolean/buffer mapping, RC+clear timing/reset contract and analog-facing drive
domains/real loads for control owner. No new thread/remote work/OA/PDK edits.
The standardization decision does not turn analog switches or Bootstrap into
ordinary logic or erase source-side overshoot. Shared coordination remains parent.

FF C0 comparison checkpoint: source11421points22574580B against full-BBM
11326points;1476 unique same-pair rows, models/limits/testbench/settings equal.
Two native same-axis figures inspected; caption wrapping corrected for one
corner. HighN gate gap39.346->153.710ps, highBN43.583991->43.698327ns;
low direction unchanged. Both738record sets213strictfail; X005gd
1.062566->1.062579V, HD gd>0.991V cumulative native-linear duration
70.601->141.989ps. HD whole-leg1%reset12.737->24.485ps; LD21.444->21.434ps.
BBM VDD76.976->82.299fJ, idealCODE8.796->23.337fJ; no repair/power pass.
Full positive/negative RC1 and both clear body/D records retained. Candidate
additive phase/reset fields agree with independent native reads; all frozen
inputs/source results remain unchanged. Syntax/UTF8/whitespace/local links pass.

standard_cell_boundary.md delivered: exact BBM INV/AND mapping and original
NAND MN0 Y/A proof, library pin orders from control owner's verified note;
actual CODE/H/L fanout, RC+clear charge-state/fast-release/reset contract,
post-driver4gate ordering, supply/input domain and true analog loads. Core/IO
and boosted/analog switches not conflated with ordinary logic; CODE storage
source remains ideal in diagnostic. No new standard-cell implementation here.
Parent reports SS state channel failed (banner/no-route then first-hop refused),
not worker failure; analysis87954 state unknown. No extra probe/retry/resubmit.
FF-only report marks SS pending; parent recovers later. New custom-gate
candidates stopped per user standard-cell direction. No remote/circuit/OA/PDK/
shared edits/adoption/commit/push.

## Resume local C0 closure after SS collection (2026-10-27)

Parent/user restored SSH/Spectre permission; Virtuoso remains unavailable.
This child still performs local analysis only, no remote queries or new runs.
SS collected sar8audit-bbm-hdc0x4-sscold:11files22387216B,10861points656I,
recipe0637635277e9c930917f811951e9de090ab01cdeee85810a60b573c4cf638973,
no skips, native/analysis exit0 and noCMI reported. Complete paired report and
two native same-axis figures in existing comparison ownership; verify precise
receipt/source hashes, full738 each, phase/reset metrics and energy tradeoffs.
Update own standard_cell_boundary.md with explicit migration timing relations
and remaining margin; no custom-gate tuning or extra candidate. Do not modify
shared plan/log, frozen inputs/results, OA/PDK or control-owner implementation.
Unrelated shared dirty ownership stays protected; no commit or push.

## Reference standard-cell BBM v1 (2026-10-27)

Parent assigns reference/standard_cell_bbm_v1/ plus reference-local
prepare_standard_cell_bbm.py, standard_cell_bbm_analyze.py and
test_standard_cell_bbm.py. Prepare one equivalent original real_bbm_v1 bit0
candidate at C0 multi1: native INVD1/ND2D1 for ordinary BBM Boolean gates,
three threshold/reset INV in each delay leg and all ordinary paired core
reference inverters. Keep RC/clear, tested IO stages, Rgate and complete real
CDAC/Bootstrap/comparator-reset load identical. No further C0 sweep or custom
gate sizing. Read control/standard_cell_full_v1/library_probe.json metadata;
foundry source stays read-only external SPICE include, never copied geometry.

Own local package preparation, full native terminal/current/KCL mapping,
physical phase settling, both delay-leg reset, actual postdriver half-rail
ordering and source-energy measurement. FF0.99V/-40C and SS0.81V/-40C proposed
managed recipes: <=4 threads, <=1GiB simulation RSS, 256MiB analysis RSS,
<=32MiB collection/derived budget. Parent alone registers/submits/collects.
Focused structural/provenance and staged-measurement tests; native elaboration
and circuit qualification remain pending parent execution. Unrelated dirty
Obsidian, management, 10bit, control and shared plan/log are protected; no OA,
PDK edits, remote actions, new chats/delegation, adoption, commit or push.

Standard-cell BBM frozen handoff: candidate194 leaves/123MOS,42 native-library
MOS,152 retained records exact; only2 custom NAND CMID omitted with gate
replacement. Complete RC/clear/IO/Rgate/real load unchanged; C0multi1. Each
case8inputs443855B;116V652I738screens36KCL372native columns. FF recipe
f8748125aa8e3528ba6fc2767f6e6d6f20aeb0d467144d085b5a1cda415dba6c;
SS f36c9d35de24675e06ee1a5a077974aeaa104d4e55c049569a2db2bdfa6cb9d4.
One focused structural+staged parser/measurement unittest PASS0.726s; AST,
all frozen hashes/bytes and whitespace PASS. Do not modify inputs after this
handoff. Native library/model identity and numericMM port binding still require
parent managed execution; no physical pass/adoption inferred. README gives
scope/exceptions/resources and physical/reset measurement contracts. Parent
owns execution and shared log. No remote/OA/PDK/shared edits/commit/push.

## Standard-cell BBM paired analysis preparation

Parent reports FF native exit0 (26.70s,345MB) with CMI2751..2756;
managed analysis in flight, SS serially pending. Own added
analyze_standard_cell_bbm.py, test_standard_cell_bbm_comparison.py and
standard_cell_bbm_v1/comparison/ only. Frozen eight-input packages and recipes
remain read-only. Prepare exact original-to-native device/function mapping,
receipt/hash/current/PSF proof, all738-pair stress phases and excursions,
actual postdriver order, physical reference windows, both reset legs,
charge/energy and same-axis/no-time-shift plots. Distinguish standard gate
internal devices, RC clear, retained IO and actual analog load. No inference
from FF completion/CMI alone. No waiting loops, remote status/launch/queries,
or data analysis until parent confirms complete collection; run once then.
Validation now limited to syntax, mapping/functional coverage and bounded
synthetic measurement controls, not re-running frozen-package tests.

Paired-analysis preparation checkpoint: analyze_standard_cell_bbm.py and
comparison/report.md skeleton ready; default requires explicit complete-pair
execution flag and both collected receipts, no partial report/polling. Exact
123MOS physical mapping covers42 native gate MOS,4 retainedRCclear,8 IO and
69 analog load; original NAND output-adjacent A->nativeA1/MM4, source-adjacent
B->A2/MM9.2952 unique mapped pairs planned across two corners/two variants.
One focused mapping/signed-negative-extrema/phase-boundary test PASS0.016s;
AST/whitespace/all frozen input/proposal hashes pass. Parent authorized FF
local readback:11files21843637B11316points652initializedI, nativePASS/END;
all SHA/size verified. Against original11326points, both213strict/197>1mV;
std BBM worst actualMM4ds1.108483V. Physical phase/reset values independently
agree with remote metrics; external stimulus/solver deck body exact. Report
not executed; SS collection awaits parent notice. Four native-time figures
planned (high/low ordering+currents+settling, RC1/clear-context, NAND nodes/real
terminalstress); no time or amplitude normalization. Frozen inputs untouched,
no remote/new run/OA/shared edit/adoption/commit/push.

Standard-cell paired comparison complete after parent SS receipt: SS11files
22126021B10956points652initializedI, nativePASS/END; all11 SHA/bytes verified,
FF11files21843637B11316points.2952 unique mapped terminal rows cover123MOS
per variant/corner with exact models/screens. Four figures visually reviewed;
legends reduced and NAND H row corrected to its own48ns phase, no trace
translation. All8 physical reference windows establish and all12reset nodes
complete per variant/corner; independent values match candidate native metrics.
FF213/738 both197>1mV; SS0/738 both, but highN gap-191.747->-209.799ps and
opposedD-min peak10.863->12.333uA. StandardFF RC1HDmax1.061799V,
clearDSHD1.009947/LD1.010347V remain. Standard L NAND actual MM4DS1.108483V
at43.026695ns is simultaneous D=.989731423,S=-.118751848,G=.001828129,B=0,
not1.108V output overshoot. net10 min-.118856V occurs43.024816ns; L CBfall
43.006012 thenLDfall43.013271; H analogous CODEfall48 thenHDfall48.006245
leaves stack floating after both off. FF/SS actualsolver settings equal.
Report explains both assert/deassert input orders and floating/charging
paths; suggests only L native NAND A1/A2 swap as one causal interface test,
H unchanged, while preserving RC/clear and SS issues as unresolved. No new
candidate/sim prepared or launched. Scope bit0 idealCODE/rails/comparatorreset,
no wholeADC power or adoption. Mapping/signedphase test passed; final AST,
2952uniqueness,reset/window,links,all frozen input/proposal SHA and scoped
diffcheck pass. Shared plan/log and frozen sources/results untouched.

## Single L NAND native pin-swap preparation (2026-10-27)

Parent accepts one causal interface experiment. Own added
standard_cell_bbm_lswap_v1/, prepare_standard_cell_bbm_lswap.py,
standard_cell_bbm_lswap_analyze.py, test_standard_cell_bbm_lswap.py under
reference/. From frozen standard_cell_bbm_v1 FF only, swap native A1/A2
CB/LD->LD/CB at L NAND XBBM0.X004.X000.XLIB via dedicated local wrappers.
H NAND and every other leaf remain exact. Do not globally change sar8p_nand2
or foundry cell. Keep full52ns external timing/model/solver,738pair screens,
652currents, source charge, physical settling and both reset legs; rebuild
gate-terminal incidence/KCL and true screen-node mapping for four changed
MOS gates. Parent alone registers/submits serial managed run
sar8audit-ref-bbm-stdcell-lswap-ff-v1. Preserve frozen baseline packages,
reported evidence and raw results. Validation: exact flattened four-gate-only
delta, H/everyother record and external testbench body exact, full save/
catalog/KCL coverage and a focused staged-measurement test. No native pass
inferred locally, no remote/OA/PDK/shared edit/adoption/commit/push.

Single-L swap frozen checkpoint: dedicated sar8audit_and2_Lswap and
sar8audit_nand2_Lswap only on XBBM0.X004; global sar8p_nand2 and H exact.
194leafrecords,190exact; only four native MM1/MM2/MM4/MM9 G nodes swapped,
D/S/B/model/params/paths exact.652current names unchanged,4gatecatalog entries
rebound;12 g-containing screens rebound, onlyCB/LDKCL equations changed.
116V738screens36KCL372nativecols retained; FFtest.scs byte-identical including
model/solver and CODE/sample clocks. One focused exact-delta+stagednative
measurement test PASS0.864s (badbinding/badlimit,phase/reset/missingedges,
body/work closure retained).10inputs456727B; recipe
6ea8073bf06e3ffea5863a8bf4b33c7c342d255a6d927b98affff40d4528ae02,
run sar8audit-ref-bbm-stdcell-lswap-ff-v1. README/delta report state causal
prediction, actual mapping, resource scope and unresolved non-target issues.
No native run/registration, frozenbaseline/shared modification or adoption.

## Collected L-swap single-contrast analysis

Parent supplies complete sar8audit-ref-bbm-stdcell-lswap-ff-v1 collection:
managed2b62fa1e5f736c747ecc25f8573280df23276f5d6e69705b873865874b7bf99b,
11files21911695B/no skips; native22.726s338567168B,analysis81.489s22556672B.
Own analyze_standard_cell_bbm_lswap.py and standard_cell_bbm_lswap_v1/comparison/
only; compare frozen standardFF baseline on738actual pairs, simultaneous L
D/S/Vds, internal node/current/edge order/reference establishment, H andRC
control. Two necessary native-time figures and concise explanation/one next
experiment recommendation. Verify exact receipt/registered input/native history
hashes with bounded streams; no raw full load or internal time shifting.
No new remote submission, frozen inputs/shared plan/original results edits.

L-swap collected comparison closed per parent review. Native11278points652I,
receipt11files21911695B; managed hash matches exact supplied identity;
PASS/END,complete currents/all inputs/streams SHA verified.1476 actual same-name
pair rows with real per-model frozen screens:213strict/197over1mV in each
variant, not a missing-field counter.43ns phase LMM4maxDS1.108483->.731909V,
timeabove.99 estimated4979.096ps->0; stack min-.118856->-.016002V transient,
then precharged/held positive.48ns phase maxDS1.016771->.992307V at48.123404ns,
same native D=.993660038,S=.001352966,G=.198964846,B=0; residual2.307mV,
above.99 duration8.819->34.328ps. Full-window extrema not conflated across
stages. HMM4max1.105306V andRC/clear issues retained; HDunchanged practically,
LDpositiveRC1peak1.053508->1.052682V. Actualgate gaps/branchcurrents, both
reference establishments and resets retained; all physical windows true.
CB/LD netincident load charges separately measured, KCLpeak <=2.76e-11A.
Two same-native-time figures inspected; added0.99Vscreen label and48ns
2.307mV zoom, no time shifts. Report/JSON/CSV inlswap_v1/comparison/; AST,
1476unique rows/actual-limitcounts/phasewitness/links/all frozen baselineand
candidate hashes/scoped diffcheck pass. Parent accepts diagnostic evidence,
requests no further H/remote task this round; next experiment remains only
a proposal pending coordinator's storageSS/DFF evidence. Checkpoint saved;
no new candidates,runs,shared edits,adoption,commit or push.
