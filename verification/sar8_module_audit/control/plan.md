# Control timing evidence extraction

Status: local artifacts implemented; synthetic/existing-evidence checks complete;
awaiting parent review. No remote work or circuit changes.

## Goal and authorization

The parent module-audit task authorizes a reproducible read-only event table for
the existing rx2 TT and SS-cold/210 ns evidence. Preserve historical conversion
definitions and distinguish native crossings, compact-wave estimates, source
parameters, unavailable data and unallocated timing budgets.

## Ownership and dirty state

Own only `verification/sar8_module_audit/control/`. The user Obsidian changes,
independent 10-bit work, existing 210 ns outputs, shared module-audit plan/log and
all other modules are read-only. Shared branch is ahead 30 at start; no commit,
push, remote operation, OA change, circuit edit or data deletion is authorized.

## Read-only dependencies

- Parent: `plan/2026-10-25-sar8-module-audit/plan.md`.
- Existing `verification/sar8_physical_repair/*rx2*` manifests/analysis JSON.
- Exact managed-run collection receipts and small event/meta/state files.
- Frozen `test.scs`, `dut.scs`, `r4_perf_monitor.va` for hashes and definitions.
- Existing `scripts/sar8_physical_repair/loaded_analyze.py` is context only.

Do not load/reduce original raw waves or call existing analysis entry points.

## Implementation and outputs

1. Add a standard-library-only event extraction script and synthetic tests.
2. Verify hashes of consumed receipt files and frozen inputs against manifests.
3. Preserve `conversion_ns`; add explicitly named relative-SEQ_SAMPLE events.
4. Represent missing/duplicate/invalid/unavailable evidence with null values and
   typed statuses; never infer DOUT validity from the final write crossing.
5. Emit `events.json` and concise README only inside this directory.

## Validation

Synthetic tests cover seconds-to-nanoseconds units, cross-frame reset lookup,
missing/duplicate/out-of-order inputs, invalid evidence, source pulse timings,
unknown budgets and a diagnostic timing gate refusing unusable event values.
Run the extractor on the two immutable cases; compare selected events and the
historical latency to prior analysis. Perform scoped whitespace/status checks.
Every generated record identifies input hashes and its evidence class. Missing
data or unknown budget yields an undecided gate, never an implicit pass.

## Local checkpoint

- Added standard-library extractor, synthetic tests, README and generated JSON.
- 22 synthetic cases passed, covering missing/duplicate/out-of-order events,
  cross-frame reset and unit conversion, unavailable-data and unknown-budget gates.
- Two existing runs/four frames extracted. TT second-frame next sampling remains
  unobserved/null; SS-cold margins are 1.500349/3.161161 ns compact estimates.
- All required acceptance budgets remain unallocated; all acceptance gates are
  undecided. DOUT-valid time remains null, independent of the final write event.
- Receipt small-file hashes and frozen source hashes verified; original raw and
  compact binary waveforms were not read/reduced. No old result was overwritten.

## Commit policy

No commit or push. Parent owns shared plan/log and final review. Stop after local
artifacts/tests and report the exact changed files and remaining limitations.

## Follow-up: sampled DOUT diagnostic

Parent authorizes a separate diagnostic from the existing compact `wave.bin`
exports only, bounded to 32 MiB combined binary input for TT and SS-cold. The
eight DOUT columns are present. Preserve old `events.json` definitions, especially
unavailable qualified DOUT-valid time; emit a separate `dout_sampled.json` with
per-bit sampled-ready estimates, legacy 90/98 ns window diagnostics, actual grid
gaps and explicit unknown receiver/setup/hold requirements. No raw PSF reads.

Use the frozen observer's +/-0.1 VDD rail band as a clearly named diagnostic,
not an assumed receiver specification. Do not infer absence of intersample
glitches. If endpoint coverage or justified grid resolution is missing, emit
null rather than a fabricated readiness. Add synthetic edge/boundary tests.

Also bound fallback RST0 lookup by the next observed SAMPLE_INT initialization,
or nominal frame boundary if neither sampling edge is available, so a missing
SEQ_SAMPLE event cannot accidentally select a reset from a later frame. Test
that failure mode and retain all historical timing definitions. This phase owns
only the same control subtree and requires no remote operation or commit.

Follow-up checkpoint: 24 event tests and 13 sampled-DOUT tests passed. Both compact
exports contain all eight output columns; combined binary input is 29,841,584 B
(28.459 MiB), with additional metadata included under the same 32 MiB batch cap.
Legacy-window samples match their expected rail bands in four frames. The
maximum measured grid gap is about 30 ps. First-frame sampled bus matching occurs
after the last write; second-frame matching occurs earlier because later zero
writes do not change the bus. No completion/setup/hold signoff is inferred.
All qualified DOUT-valid fields and silicon acceptance remain null/undecided.

## Follow-up: QUIET local reproduction specification only

Parent authorizes only `local_repro_spec.json`: freeze the existing combined
FF-cold DUT/test/mapping hashes and native QUIET-internal peak witness; list the
exact retained primitive network, upstream and downstream cuts, required replay
data, current saves and node KCL signs. Do not build a netlist, acquire remote
data, run/reduce waves or optimize sizes. Mark currently absent replay traces
as blockers. Retain real delay_quiet/CLOCK_SET input loading where possible;
make every controlled boundary and removed feedback explicit.

Validation is local JSON parsing, source-hash/instance/port cross-checks and scoped
whitespace checks. Stop at this specification checkpoint for parent review.

## Follow-up: converge physical loading and replay boundaries

Parent requests a short boundary supplement only: replace the proposed unknown
CLOCK_Q load-current replay with real X025 and real direct CMP_CLK loading;
evaluate retaining the Q1/LIVE/CLOCK_RESET forward cone without full registers.
Record added component counts and omitted feedback, not another full primitive
or KCL inventory. Check exact frozen native voltage-save statements against
compact export availability and identify the existing remote raw run location.
No new netlist, general tests, remote access, circuit edit or sizing is authorized.
Own only this control subtree; produce `boundary_convergence.json` and mark the
old current-replay proposal superseded. Stop for parent review after local checks.

Convergence checkpoint: replacing the current replay adds 23 MOS/4 passives;
retaining the Q1/LIVE/reset forward cone adds 32 MOS/4 passives. The proposed
89-MOS/18-passive fixture excludes full bitseq/registers. Ten voltage histories
are explicitly saved in the frozen successful native deck; only DEC/WD among
the ten are absent from the local compact export. Missing compact data is not
missing native data. Original gate-current histories are no longer prerequisites.
Checked exact block counts, source hashes and all ten native save spellings.
Corrected PHI_W to its flattened alias XDUT.XCTRL.PHI_W. No remote work, netlist
or circuit edits were performed; no new general tests were added.

## Follow-up: native boundary export preparation

The user removed the two-hour limit. Parent authorizes a control-local manifest,
stream parser, Python-2-compatible analysis-only wrapper and focused synthetic
tests. Interface: --run-dir NEW --output-dir NEW/derived --source-run-dir SOURCE.
The source is the completed sar8fix-loaded-both-ffcold run and is read-only.
Extract original native points from zero through the 40.8--41.6 ns peak window:
ten named boundary-voltage series, initial-state witnesses and diagnostic nodes.
No interpolation, large array load, decimation or remote execution in this task.
Required TRACE names must resolve; missing/invalid data fails explicitly.

Keep binary/metadata output below 32 MiB and runtime RSS below 256 MiB; the
managed parent retains resource admission and remote dispatch ownership. Frozen
source hashes, source metadata before/after and consumed ASCII-prefix SHA must
be recorded. New tool files and local synthetic outputs stay in this subtree.

Replace the previous forced comparator-output boundary with a single-driver
definition. Keep native N4 output generation; treat COMP_P/N and WD export as
comparison witnesses, not voltage sources on active outputs. Document any extra
receiver load and remaining omitted fanout without expanding into full SAR.
No circuit/netlist generation, shared changes, remote simulation or commit.

Native-export checkpoint: 20 focused synthetic tests passed (including compiled
stream parser, sparse native updates/GROUP aliases, missing initial values,
output cap, managed result.json gate and unchanged synthetic source hashes).
The tested parser peak RSS was about 9 MiB on Windows synthetic input; this is
not a measurement of the actual remote export. Runtime caps remain 256 MiB and
the complete derived directory below 32 MiB. Missing later sparse values retain
their previously initialized native values; no interpolated sample is created.

Parent registered sar8audit-ctrl-native-v1. The three analyzer inputs now match
their immutable registered hashes exactly. A concurrent Unicode CLI-byte-path
enhancement was separated as unicode_path_followup.patch rather than changing
registered v1. The frozen production managed paths are ASCII; no new registration
or dispatch occurred in this session.

Single-driver boundary now retains both original core receiving buffers: 97 MOS
and 18 passives. COMP_P/N and WD are native outputs and exported witnesses only;
seven upstream/input voltage replays remain. PR/NR and WD downstream fanout
omissions are explicit and require baseline-equivalence review. Await parent
native export recovery and a separately assigned fixture task.

## Recovered export review and first-event fixture preparation

Parent reports native export complete and authorizes local review/build only.
Verify all collection receipt hashes, nested result hashes, peak/time and every
initial-state witness against recovered native tables. Plot the actual first
sampling-close event, then prepare a new immutable `first_event_v1/` bundle.
Keep frozen exporter files and all source runs read-only.

The builder must reproduce the approved 97-MOS/18-passive extraction with
unchanged model/instance parameters and original clock/comparator/MOM loads.
Seven replay inputs use all recovered native knots; COMP_P/N, WD and every
retained active output remain single-driven. Preserve initial source history;
do not force internal nodes to their measured initial states. Report omitted
qualification/WD fanout and cut token/register/reference feedback explicitly.

Prepare the builder, deck, PWL files, device/measurement manifest, dedicated
bounded native current/KCL analyzer and a recipe suggestion under this subtree.
Propose baseline-reproduction tolerances for parent review without adopting
them as ADC specifications or declaring a physical reproduction before running.
No remote run, shared file change, sizing optimization, commit or push.

Checkpoint: all 13 receipt members (2,863,230 bytes), nested hashes and initial
witnesses match recovered native data. The 8,746-row history preserves the
X020.N maximum 1.078642014935018 V at 41.089515433655805 ns. Plot annotation
placement was repaired and the final image visually inspected.

Prepared unchanged 97-MOS/18-passive first_event_v1 extraction and seven complete
PWL histories (2,708,173 bytes). Parent caught the managed cwd distinction;
unregistered draft paths were corrected from inputs/pwl to pwl and now undergo
package-relative path checks. The three frozen native-exporter inputs stay
unchanged. A recipe suggestion and bounded Python-2/3 current/KCL reducer remain
local to this subtree. Proposed 1mV/5ps/1nA reproduction tolerances remain
unapproved and acceptance null. No simulation or current attribution has run.

Validation complete: 15 focused synthetic/package tests passed; receipt/native/
source hash checks passed; current catalog completeness and KCL signs checked;
missing native data, sparse/GROUP alias, cap and native completion failure checks
passed; recipe hashes and working-directory checks passed. Builder rerun accepted
all existing generated bytes unchanged. Scoped diff whitespace review passed.
Frozen exporter hashes remain 293b8aa64012577e527691007c623f017b7a3dd3ed53eb2f18e36314ed646064
(wrapper), c379d993c02438621d6609c67616b6b10dd7dbf5947713a0ea5156ebf7510e52
(parser), 400398ea38db4a01154faa9849ffc33e249bd2dd0f2b791be3b2103a37dfb284
(manifest). Await parent review and remote dispatch. No shared log edits or commit/push.

## First-event v1 collected result review

Parent registered and ran `sar8audit-ctrl-first-event-v1`, recipe SHA
587e794d928d6f25fa64ce7749d1d613fd0dd6fe3e1e46b7554b1dd1efb74ae7.
Every registered input, first_event_v1 generated file, native exporter and analyzer
is now frozen. New owned artifacts are a separate local review script and
`first_event_results_v1/` report/data/figures. Collected output, source data,
PDK/OA, shared plans/logs, other module directories, user Obsidian and independent
10-bit work remain read-only. Existing dirty state does not overlap this new review.

Verify receipt hashes and raw completion, then plot source versus fixture on
their original time axes with no alignment or fitting. Apply the approved 1mV
amplitude, 5ps peak/edge, 1mV initial and 1nA KCL screens plus edge count/order;
do not alter the frozen analyzer's null acceptance. Measure five X020.N total
terminal currents and signed native-grid integrals, explicitly distinguishing
local fixture evidence from original whole-ADC attribution.

Check SPECTRE-16780 at 41.0608ns against exact SAMPLE_INT PWL knots, native gaps
and segment slopes. Keep CMI-2751..2755, SFE-1131 and VACOMP-2435. Assess numerical
replay and missing-fanout hypotheses separately; propose only minimal single-
variable experiments. No input smoothing, sampling-edge change, relaxed screen,
new remote operation, sizing change, shared edit, commit or push.

Validation: independent receipt/recipe/input hashes, native table shape/finite/
strict-time checks, source-vs-fixture peak/edge calculations, independent KCL sum
and bounded integration arithmetic, original-axis figure inspection, scoped
whitespace review. Parent retains all remote scheduling and adoption decisions.

Review checkpoint: nine collected members,1,236,711B, all hashes and all12 frozen
inputs match recipe587e794d928d6f25fa64ce7749d1d613fd0dd6fe3e1e46b7554b1dd1efb74ae7.
Independent local1836-row peak matches reducer:1.079890183994581V,
41.08574058979127ns; difference+1.248169mV/-3.774844ps. Amplitude reproduction
fails without relaxing1mV; selected four edge counts/order and5ps screen pass;
initial9.367925nV and criticalKCL3.648512pA pass. Frozen acceptance remains null.

Source/fixture overlays stay on original native axes. Five-term signed KCL was
recomputed exactly at every local diagnostic row. Native-grid integration finds
MP1 drain (gate LIVE) is the sole net injecting branch in the prepeak interval:
+0.166363fC, balanced by the other four branches. This is local total-terminal
current evidence, not component decomposition or original whole-ADC attribution.

New topology audit adds previously unlisted SN fanout cuts: X010/X014 NAND
MP1/MN1 gate terminals. LIVE/QUIET advance about3.735ps, with nearly unchanged
LIVE-to-QUIET delay and faster LIVE rise; the load hypothesis is plausible but
not proven. SPECTRE16780 at rounded41.0608ns coincides with continuous native-
knot PWL slope changes. Input file/time data match exactly; measured SAMPLE_INT
matches declared linear PWL to3.884e-13V at available v1 points. This does not
rule out numerical replay/integration effects. All requested warning codes stay.

Three figures and review.json/markdown/warning records plus a local-only next-
experiment proposal are under first_event_results_v1/. Proposal separates
analysis-only native SN/UD supplementation, reltol numerical sensitivity and
one-at-a-time physical fanout restoration with reviewed output boundaries.
Three focused integral/sign/nonuniform-grid tests passed. Frozen v1 inputs,
exporters and analyzers remain unchanged; no new remote operations or shared
edits/commit/push. Scoped whitespace checks and image inspection passed. Parent
also reviewed the three figures and review.json; local current-evidence limits
are accepted. The failed amplitude reproduction screen remains unchanged.

## Local supplementary native export packages

Parent's09:29 shared-plan authorization permits preparing two LOCAL analysis-
only export packages in this subtree: nine signals from original FF-cold source,
three from the completed first-event v1. No remote dispatch in this session.
Use a new stdlib wrapper around existing reviewed helpers/parser without editing
any frozen file. Each configuration binds its own source recipe/input SHA and
exact saved TRACE selection. Full zero-to-target native histories and initial
witnesses are required; no interpolation, fabricated endpoint or fitted timing.

Target stop41.59078565059045ns. Preserve actual last included native row; prove
coverage by a later source time marker or an observed END at the target. Explicitly
distinguish completed-source/logStatus evidence from an END actually scanned by
the prefix parser. Record consumed-prefix SHA and source stat/metadata equality.

Own new supplement_native_export.py, prepare_supplement_export.py, focused local
synthetic tests and supplement_export_v1/{source,fixture}/ generated configs,
package manifests/recipe suggestions. Read-only dependencies: frozen wrapper/
C++ parser, original source, collected v1, all registered inputs and shared plans.
Resource ceilings remain one declared thread,256MiB analysis,32MiB collection.
Focused tests must exercise both source identities, exact-END and non-endpoint
coverage, missing TRACE/value/save, wrong source/recipe/input SHA, path/output
isolation, sparse/GROUP native points and result.json managed interface. Parent
reviews and registers only after this local preparation is delivered. No circuit,
PDK/OA, timing/sizing, shared log, commit/push or remote change.

Supplementary preparation checkpoint: both source-specific manifests, four-input
package manifests and analysis-only recipe suggestions generated under
supplement_export_v1/{source,fixture}/. Source9-channel package35,569B; fixture
3-channel package34,473B, or38,541/37,445B including the manager's current2,972B
default summary. Each binds its own immutable source recipe, all source input
files were locally SHA-checked, and requested saves match exactly. Run IDs are
suggestions only, not registered here.

New wrapper reuses unchanged frozen Python helper/C++ parser and additionally
checks all registered source inputs including nested PWL files, exact analysis
PASS, full managed completion, prefix hash and source immutability. END at stop
versus a first marker beyond stop is explicit in coverage.json. A last native
row below stop remains unmodified; a premature END fails. No guessed endpoint.

Eleven focused synthetic tests passed with one compiled parser build, covering
both sources/full wrapper interfaces, exact-END/non-endpoint coverage, initial
rows, sparse/GROUP behavior, missing TRACE/value/save, source/recipe/nested-input
SHA failures, output isolation, caps and native completion. Builder rerun is byte-
identical; scoped whitespace and frozen helper/parser/export-manifest/analyzer
SHA checks passed. All three review figures inspected; final legend placements
avoid hiding current peaks. No actual supplementary raw data was exported in
this session. Await parent review and managed dispatch; no further design work.

## Direct SN load-mechanism continuation

User now requests flatter execution with fewer stop/review cycles. Keep the
1.248mV-versus1mV failure recorded, but it no longer blocks mechanism analysis
or targeted single-variable diagnostics. Parent dispatches both frozen SN exports.
Prepare new local sn_load_variants_v1/ builder/tests while data arrive; do not
modify any registered package. Use original MP1/MN1 gate-load devices with all
original geometry and source-native N/MID diffusion-bias histories, leaving SN
and every retained active output naturally driven. This is a conditional input-
load replica experiment, not full X010/X014 logic restoration. Do not fit C or
invent bias. Generate X010-only, X014-only and both-load variants directly when
both checked collected exports are available; parent alone dispatches remotely.
Owned new files: prepare_sn_load_variants.py, focused tests and sn_load_variants_v1/.
No fresh long approval plan, remote commands, shared edits, commit or push.

SN data recovered: both14-file receipts/nested hashes checked, correct export
recipe hashes3d1cc7bc36e51363159025e12f5b282335e1d6886190126a517f62bb3ce202d0
and512786dc52e02927814401dc2e46771a0d267b833c1923897971141f69932680.
Original8746x9 and v15917x3 native histories preserve initial/time/coverage.
SN advances3.012583ps, X001.N falling edge3.652493ps, LIVE3.734733ps.
Original/v1 SN minima-8.977648/-10.780405mV, X001.N peaks1.006291268/
1.013985215V. Actual N/MID biases, including about84.52mV initial MID, are
used in full; no guessed rail bias. Two new original-axis figures inspected.

Prepared three conditional native-MOS load variants (99/99/101MOS,18passives),
retaining all v1 native instances and upstream PWL bytes. Five focused tests
passed, including exact original geometry, non-forcing of retained outputs,
native PWL knots and frozen analyzer extended-measurement interface. Parent
reran the same tests and registered/submitted priority both as
sar8audit-ctrl-snload-both-v1, recipe66cda5e5a9c65de39abee30125b33fe39f8926729145adbe5d25999b0bcc802c.
All both inputs now frozen; no further edits.15 declared files4,408,071B,
4,411,043B with manager summary;436currents,61voltages,12criticalKCLnodes.
Parent owns the sole heavy slot/collection. Singles remain prepared/unrun.
This session made no remote call, shared edit, circuit optimization or commit.

## Both result and first local suppression experiment

Parent recovered completed both; continue directly, no extra reproduction rounds
or single-branch runs. Own new review_both_result.py, mp1_shape_v1/ and local
builder. Verify9-member receipt, three-way original-axis peak/timing, critical
KCL and total MP1 drain-current charge. Preserve actual CMI and the remaining
about88.64mV overshoot. Frozen both/v1/SN exports remain untouched.

Prepare one suppression experiment: separate only X020 NAND MP1's gate from
direct LIVE by one existing-PDK rupolym resistor, copying the original quiet-delay
R0 model/geometry. MN1 still sees LIVE directly; all MOS sizes, supplies, original
sampling PWL/closing edge and conditional SN loads stay. No added capacitor or
clock source. The resistance is not fitted; transient gate loading is solved by
the original PDK MOS. Measure N/LIVE/new gate, currents/KCL, output edge count/
delay and local supply current. This is a local mechanism test, not whole-ADC
qualification. Parent alone owns managed dispatch; no shared edits/commit/push.

Both review complete:9 receipt files/1,725,886B and436 currents verified;
6041 native points,1960 local diagnostic rows,END. Peak1.07864156613968V,
source difference-0.448795uV/-0.0174088ps; SN/LIVE source edges now agree
within0.000051ps. CriticalKCL max3.653741pA,initial9.37nV. Supports missing
SN gate-load explanation; original88.64mV positive overshoot andCMI remain.
MP1 prepeak net injection0.164111fC versus oldv10.166363fC, native-grid total
terminal currents only. Three-way timing and MP1 current/charge figures inspected.

Prepared mp1_shape_v1 with new prepare_mp1_shape.py. Exactly one existing MP1
gate connection changes and one rupolym is added, copied from R0 geometry;
all other original leaves, MOS model/geometry and11 PWL files remain byte-
identical.101MOS/19passives,62voltages,438currents,14criticalKCLnodes. Native
R0 V/I is about9.79kOhm at this condition; no ideal fitted R/C. Builder topology/
input assertions and one synthetic frozen-analyzer interface execution passed;
no actual new Spectre simulation in this session. Intentionally changed-circuit
response is evaluated by suppression/delay/current, not original-peak fidelity.
Scope/limits and suggested recipe delivered for parent serial execution.

## MP1 shape result and positive-floor continuation

Read completed mp1shape recipe8dc67ee9a10e3eeb56b27df222a593b475c600bb74ede6cd5496cfc055287d7a;
own new result review and mp1_floor_v1/ builder. Do not alter any frozen shape/
both/input/analyzer. Review original-axis voltage/current/charge and source
current tradeoffs. Shape reduces N overshoot88.642->15.488mV but is not safe:
global B_PM min-7.021713mV implies exact globalVSGmax0.997021713V for constant
0.99V supply; simultaneous diagnosticVGD reaches-0.996791886V. Full joint
0..END VGD and energy are not available from compact extrema alone; prepare a
small source-bound analysis-only reprocessing package instead of inventing them.

Next single circuit adjustment: add a VDD-to-B_PM pullup branch of three copies
of existing legal R0 in series. Together with existing gate-series R this gives
approximately VDD/4 low-state gate bias, without new bias supply, clock, fitted
C or MOS resizing. It targets gate under-voltage and early gate injection, not
only a smaller N maximum. Explicit static-current and delay cost is measured.
New local full-history stress/energy analyzer is separate from frozen one;
record VSG/VGD and all5 ideal source energies over original native timestamps.
Local tests focus on exact added branch and full-history observation outside
the diagnostic window. No shared edits, remote actions, commit or push.

MP1shape review complete:9files/1,927,723B/438currents,6054native points,
1973diagnostic rows,END and hashes verified. Nmax1.005487759V leaves15.488mV
overshoot (82.53% reduction). Exact globalVSGmax0.997021713V; simultaneous
diagnosticVGDmin-0.996791886V, so both terminal issues persist. CriticalKCL
max3.451631pA. QUIET advances0.568944ps, one rising/no diagnostic falling edge.
VDD peak1.008205->1.060869mA (+5.2235%). MP1 prepeak charge0.164111->
0.032637fC, full-event0.676401->0.692251fC. Figures inspected on original axes.

Prepared/froze mp1_floor_v1: only3 added exact R0 copies in a VDD-to-B_PM
branch; every existing leaf and11PWL bytes unchanged, external stop/supply/
sample edges unchanged.101MOS/22passives,64V/444I/16KCL,15 declared inputs,
4,421,568B, proposed recipe fileSHAb2fb6f4fcd947397d33e7cc15ebe6b1e5eeedf3375945a29a96f90fa74c4f36c.
New independent full_gate_analyze.py computes all-native simultaneous stress
and five-source signed energy. One focused synthetic test passed with maxima
before the diagnostic window and exact constant-power energy; builder asserts
the unique added branch and all original device/input identity. Parent independently
confirmed and will register/submit; no further modifications to frozen inputs.

Source-bound analysis-only reprocessing suggestions for oldshape/both are ready
under gate_reanalysis_v1/. They fill the full-time jointVGD/energy gap without
Spectre reruns and need not precede the candidate. No new circuit variants,
remote operations, shared files or commits. Existing original/shape/both frozen
inputs preserved. Candidate outcome remains unmeasured until parent collects.

## Floor result: injection versus MID discharge

Parent recovered floor. Review shape/floor native branch currents and all-history
stress/energy; frozen packages/observer stay untouched. Correctly distinguish
critical KCL from all-node maximum. Explain safe MP1 gate but worse N via net
injection and still-charged MID; no blind resistor sweep or full-module pass.

Prepare only one suggested next variation in cmid_half_v1/: X020 private CMID
multi2->1, otherwise exact floor leaves, all PWL/supply/sample edges/numerics and
observer unchanged. Identical unit geometry with multi1 already exists in CQB,
so no new PDK dimension or fitted capacitance. This targets earlier NM0 absorption
as MID discharges. No remote dispatch; parent chooses/serially executes. New
owned files: review_floor_result.py, prepare_cmid_half.py and reports/package.

Floor review and single-variable package checkpoint: both9-file run receipts and
shape-stress7-file analysis-only receipt/input/source identities verified. Added
comparison.json and two visually inspected native-axis figures; no interpolation
or channel/displacement separation. MP1 peak-before charge0.032637->0.075005fC,
Nmax1.005488->1.025472V, while upper MN0 absorption7.738->19.677uA increases.
At floor peak, MN1 drain845.697uA versus explicit CMID release784.723uA shows
why MID stored charge is the next targeted variable. All-node KCL3.954pA is
distinct from critical3.501pA. Full-history shape/floor energies now share
0..41.590786ns:0.0707719/1.0849297pJ; the new static-current cost stays explicit.

Parent accepted the next variation; prepared cmid_half_v1: exactly one flattened leaf and one DUT
byte change (private X020 CMID multi2->1),133 leaves unchanged, no added/removed
leaf,101MOS/22passives. Same unit MOM parameters already appear at multi1 in
CQB. Test deck,11PWL inputs, frozen observer and all other measurement bindings
unchanged.15 inputs/4,422,728B; recipe fileSHA
8fcc66eee7c99f49ed7f539f6f9de3af929ae60b3c6354ad21fe140e8c95cb43.
Prepared structural assertions, exact diff, input freeze and concise README;
no new remote operation, registration, simulation or pass assertion here.
Parent alone dispatches through managed serial execution. No shared edits,
commit or push. Existing source packages and failed results remain immutable.
Validation complete:15 declared input SHA values and freeze/recipe identities,
two Python AST checks, exact electrical diff and scoped whitespace inspection.
Both figures inspected at original axes; no labels hide the relevant peaks.

## CMID-half result review only

Parent has collected sar8audit-ctrl-cmidhalf-v1 (recipe
4a7e6299c079bec1b798b68ea076c72482005a04c273b39a7824fd039c972069).
Own new review_cmid_half_result.py and cmid_half_v1/results/ only for four-case
native voltage/current/charge comparison, source energy and a single justified
next circuit suggestion. Keep all registered inputs and observers frozen.
Quantify MID/N absorption improvement, identify residual terminal charge and
static power cost; do not mechanically sweep capacitance. One local design note
is allowed, no next experiment package or remote/OA/registry/shared-file change.
Validate receipts/input hashes, full-history source binding and same intervals;
inspect all final figures and scoped diff. Parent alone owns dispatch/log/commit.

CMID-half review complete:9files/2,081,537B and all four source inputs checked;
both/shape all-history reanalysis receipts7files each, recipe/source/raw identities
verified. Added comparison.json, three inspected figures, concise README and
next_step.md. Half Nmax1.013105156V, overrail23.105mV,34.864% lower thanfloor;
MN0 20/50uA threshold crossings advance1.483/1.820ps, QUIET advances3.332ps.
At half-peak absolute time MN0 absorption4.404->20.781uA (native rows differ2fs).
Peak-before MP1netinjection0.050314fC remains; all other N terminals netabsorb.
Same requested later window MP1injection increases while MN0absorption rises
more strongly. Charge sums obey KCL and are not extra net node charge/Cgd.

VDDenergy0..41.590786ns remains1.085184pJ versusfloor1.084930pJ. Initial supply
current24.9778uA/power24.728uW unchanged; four resistors dissipate24.352uW, so
power cause is the persistent VDD-to-LIVE divider, not CMID. OriginalCMI codes
remain; MP1selectedstresspasses but restoringINV NMOSVGS1.013105V stillfails.
CriticalKCL2.475pA/allnodes3.956pA. Next proposal is ONLY NMOSgate-order swap
(upperLIVE/lowerQ1) to groundMID before the current event; keepfloor initially
for single-variable attribution and record its unresolved staticpower. Any later
floor retirement is separate, not a new prepared candidate or assumed pass.
No remote/circuit/package/registry/shared edits. AST, frozeninputSHA, native
charge-sum/QUIET-edge checks and scoped whitespace passed; no commit/push.

## Accepted next preparation: private NMOS gate-order swap

Parent accepted only the two private X020 NAND NMOS gate assignments changing:
upperMN0->LIVE, lowerMN1->Q1, based on frozen cmidhalf. Own new
prepare_stack_order.py, test_stack_order.py and stack_order_v1/; no remote work.
All MOS/model/size, halfCMID, floorbranch, original sourcePWL, external sampling,
numerics and supplies remain. Update native current-catalog gate incidence and
rebuild KCL, explicitly include Q1/LIVE and all four MN0/MN1/MP1 currents in
the compact diagnostic data. Add simultaneous all-history MN0/MN1 VGS,VGD,VDS,
VGB,VDB,VSB. Junction signed extrema are reported;0.99V abs is a diagnostic
screen, not an invented forward-junction qualification limit; retain nativeCMI.

Frozen full_gate_analyze.py already supports data-defined simultaneous pairs;
prefer extending only the new measurement configuration. No shared analyzer
change/wrapper unless technically needed. Preserve historical initial/peak
references as labeled comparison data, use only imposed boundary-source initial
witnesses for the new active comparison, and explicitly remove old original-
state/peak reproduction gates. MID initial change is expected, not a failure.
Validate unique two-leaf/two-byte electrical diff, all frozen inputs/PWL, actual
gate catalog/KCL incidence, targeted anti-correlated synthetic joint-stress values
outside diagnostic window and expected initial-state policy. Parent alone owns
register/submit/log/commit. No broad scans or further circuit schemes.

Stack-order preparation complete: unique two-leaf/two-byte gate swap,132 other
leaves unchanged;101MOS/22passives, halfCMID/floor/resistor geometry retained.
Gate-current terms MN0:2 andMN1:2 rebound toLIVE/Q1 and all KCL rebuilt. Same
64V/444I saves,17criticalKCL nodes and75 diagnostic currents. Generic frozen
observer supports all15 configured simultaneous pairs unchanged; no wrapper.
Historical internal initial/peak tolerances are inactive; only8 imposed voltage
witnesses remain in active initial comparison. MID is not forced or required
to match old initial state.5source energies/CMI and original external deck/
11PWL retained. Suggested sar8audit-ctrl-stackorder-v1 has15 inputs/4,428,042B,
recipe fileSHA11dce5c2bed8b007bc64d55ac086cb85945918b97b0b71264238764439f73f33.

One focused synthetic full-analyzer test passed: actual new gate incidence,
all12 new signed terminal voltage extrema, global peak before diagnosticwindow,
noncoincident extrema subtraction would falsely report1.0V instead ofactual
0.5V MN0VGS, signed negative junction excursion retained, changed MID initial
accepted and constant-source energy exact. Builder rerun byte-identical;15input
hashes, AST and scoped whitespace checked. Exact diff lists only two gate lines.
No actual Spectre result, remote registration/submission, shared edits or commit.

## Stack-order result: current paths and comparable voltage stress

Parent collected stackorder recipe
f7fdea18a1eb32890b5dd3688952ac6e14e91d8d05106bc8dfcd3d85305a82e3.
Own new review_stack_order_result.py and stack_order_v1/results/ only. Compare
half/stackorder native N charge exchange, Q1/LIVE/MID terminal waveforms and
simultaneous stresses using each actual netlist's gate assignment. Half's newly
computed pairs are diagnostic-window observations only; do not claim full-
history or newly generated faults without matching prior observations. Stack
full-history12added pairs remain available and checked against native rows when
their extrema lie in the diagnostic data. Keep all registered inputs/observers
frozen. Deliver concise figures/report and one grounded local repair proposal
addressing the unchanged DCdivider and zeroheadroom core devices. No new package,
remote/OA/registry change, parameter scan, shared log or commit/push.

Stack result review complete:9files/2,109,393B/5939allnative/1858diagnostic;
both source recipes/inputs/receipts verified. Nmax1.005230071V,15.230mV over,
34.084% reduction fromhalf; MIDinitial0.325uV. Stack peak-before netN charge
MN0 +0.043200fC versusMP1 -0.022544fC; dominant native injection path changed.
At Q1peak MN1gate injects13.569uA; Q1 was already0.990624V inhalf, now0.991334V.
Stack MN1gate peak-before injection0.007538fC. Oldhalf lacks allfour Q1compact
current columns, explicitly recorded; no fabricated old-current comparison.

Computed twelve terminal pairs from each actual old/new gate binding over common
40.810..41.590786ns diagnostic window. Stack extreme values match fullhistory;
half additions remain window-only. ExistingLIVEdip-11.623->-11.629mV now applies
to uppergate withN0.989240V, yieldingVGD-1.000869V. MN0VDS0.576897->0.997816V;
Q1's earlier VGB issue is exposed at new lowerMN1 VGS/VGB0.991334V. Junction
signs retained, MIDmin-0.301mV not given an invented new forward limit. Original
MP1screen remains clear but N/restoringINV and measuredotherpairs fail. CMIcodes
preserved. AllnodeKCL3.954pA/critical2.739pA. VDDenergy1.085590pJ and initial
24.7287uW show unchanged DCfloor cost.

Three native-axis figures visually checked; current-panel autoscale restricted
to visible event interval and crowded xoffset ticks corrected. Added concise
README/next_step: one proposed rated-CMOS local drive/gate/receiver boundary,
ordinary18mac family already audited, retain provenstack/pre-discharge and
remove three-resistor DCdivider. No assumed newdevice size/pass; preserve0.81..
0.99V/sample contract and recheck SS speed/reset per existingFO4cost evidence.
No new package/remote/shared changes. AST, frozeninputSHA, local links/whitespace,
charge/KCL sums and unique edges checked; no commit/push.

## Accepted local rated-CMOS candidate preparation

Parent accepts one scheme-level candidate from frozen stackorder: only15 core
MOS change to existing regular18mac CDF primitives (X020 six, LIVE/Q1 output
inverters four, directQUIET gate loads five); delete RPU0/1/2. Preserve stack
order, logical connectivity, originalCMID/RSLEW, remaining devices and external
PWL/supply/sample/solver/stop contracts. OrdinaryIO dimensions150nm/320nm use
existing CDF record; choose integer multiplicity by original effective width,
consistent with earlier tested IOinv P4/N2. This is not a single-sizing trial.

Own prepare_io_local.py, test_io_local.py and io_local_v1/ only. Specialize
hierarchy along changed paths so shared primitive instances elsewhere stay.
Observe all changed15 and exposed17 neighboring/core MOS (32total), including
QUIET RC loads and complete adjacent primitive cells, with all six simultaneous
terminal differences. Reuse prior core0.99V and IO1.98V provisional diagnostic
screens, explicitly retain nativeCMI and signed junction excursions, no lifetime
qualification. Preserve a separately labeled N-versus-core-rail diagnostic.
All32 gate/source/drain/body waveforms and currents/KCL should be recoverable in
compact outputs within existing32MiB/256MiB analysis caps. Show boundary in a
local diagram and exact leaf-change table. ExistingCDF/FO4 evidence read-only,
do not rerun basic audit or claim FF conditioned PWL as SS response. Next SS
case requires independently valid low-voltage boundary histories. No remote,
shared source/registry/log change, commit/push; parent submits this FF case.

IO-local preparation complete:exact15MOS changed using CDF150nm/320nm/nf1
unit with integer width mapping(multi4/2/10),3RPU removed,116otherleaves unchanged.
Private hierarchy specialization/pruning preserves all surviving instance paths,
terminals/logicalconnectivity and modelsizes outside targets.101MOSinstances/
19passives; all11PWL and non-save/noncomment simulation deck remain identical.
CDF parasitics reused, uppercasePeta written explicitly as prior native screens.
No reference/comparator/shared source edit or new primitive audit.

New io_local_v1:62V/438I,27criticalKCL,169diagnosticI and all62diagnosticV.
32MOS(15IOchanges+17coreadjacent) sixpairs plus original3aliases and separate
old-core-rail diagnostic=196 all-time simultaneous observations. Core0.99V
retained; IO1.98V is explicitly provisional prior-screen policy, not lifetime
qualification. Signed junctions/nativeCMI/five-sourceenergy retained. Diagram
maps X020/Nreceiver, LIVE/Q1 outputdrivers, all5directQUIETMOS and RCloads;
core neighbors still subject to failures, no wider pass assertion.

One focused test passed:exact nodes/unit geometry/counts,32x6coverage, core
1.04V remains over0.99 while IO1.04V uses1.98 screen, prewindowglobal extrema,
nativeCMI retention and sourceenergy. AST/15inputSHA/freeze/whitespace checks
passed. ExistingFO4FF0.99fall52.409ps vsSS0.81fall202.620ps(3.87x) recorded,
not substituted for actualload or SSstimulus. Recipe fileSHA
185777388be0fe0d906940d437fdff9ddd457b2f831dd4dde466721d661e1987,
15inputs/4,481,087B. Ready for parent managedFF submission only. No local actual
Spectre/remote registration or further package, no commit/push/shared-log edit.

## IO-local result and evidence-led boundary correction

Parent recovered sar8audit-ctrl-iolocal-v1, recipe
aa418b9919dce4576fe5013f09e6d1721c63df76b856e20e205a682d570682a7.
Own new review_io_local_result.py and io_local_v1/results/ for native receipt/
KCL/current/stress/edge/five-source energy comparison against stackorder. Only
matching old voltage columns or exact constant-reference identities support
old terminal comparisons; label new observations without adequate old data.
Do not claim suppressed overshoot or all remaining faults newly introduced.

Based on concrete retained-core exposure, may prepare ONE minimum necessary
boundary-correction candidate under io_boundary_v2/, with new local builder/test
only if justified. Preserve original logical function/stack/external sampling/
FF source histories and original frozen inputs/analyzer. No whole-controller IO
replacement, remote dispatch, PVT retagging or shared edits. Parent submits.

Native IO-local results justify exactly15 additional current-failing core MOS,
not the2 remaining observed non-failing core devices. Own new
prepare_io_boundary_v2.py, test_io_boundary_v2.py and io_boundary_v2/. Candidate
retains first15IO/floor removal and swaps only these15 measured failures to
same regularCDF units, including MN_CLEAR2um->7units. Circuit change stays local;
expand observation to all101 fixture MOS sixpairs and all saved voltages/current
in diagnostic output, protecting against another missed adjacent endpoint.
Existing30MiB binary/32MiB collection/256MiB analysis caps stay unchanged;
estimated9MiB native diagnostic output at2kpoints. All source waveforms remainFF.

IO-local result checkpoint:9files/4,436,865B SHA/size/nativeEND/source inputs
verified,6065native/1984diagnostic. N1.034017V is44.017mV above0.99, LIVEmin
-175.076mV; overshoot not eliminated. New15IO/90absolute1.98screens clear,
worst1.165076V but forward-polarity LIVE drain/body and totalbody currents remain
unqualified. Retained17core/102pairs include15instances/46failpairs. AB1.031652V
feedsMN_CLEAR; oldAB1.009554V already unsafe. OldX001.N1.006276->1.005442V
slightly improves; oldRC1/RC0 faults persist. Constant-reference comparisons are
exact one-scalar transformations, missing oldAB/X001 waveform columns staypoints.
Three figures inspected; JSON includes allKCLbranchsnapshots and five-sourcework.

QUIET halfrail120.517ps fromclose vs22.803ps prior, delay+97.714ps; actualend
QUIET0.829476V feeds66.47uA intoR0, so edge is not fullsettling. Neither source
history contains subsequentQUIET_D/CLOCK_SET/CLOCK_Q/CMP_CLK halfrail edge.
VDDnetwork1.085590->0.0610168pJ(-94.379%), initialpower24.7287->0.03575uW;
five-source signed work remains separate from whole-cycle dissipative power.
MaxKCL7.901pA; allnativeCMI codes preserved, no integratedqualification.

Prepared exact15failed-core-only io_boundary_v2 before the parent steering;
116otherleaves, allnodes/passives/prior15IO/11PWL unchanged. Observe101MOS610
simultaneouspairs,62V/438I/all61KCL under existingcaps. One focused synthetic
test passed including multi7MN_CLEAR and retainedcore1.04V stillflagged0.99.
15inputs/4,636,412B; recipe fileSHA
d444e366e3a5ce1079d7c933ab5396a125747b4420109d2abfe9cab456d7db0d.
Not registered/submitted remotely; no shared edits/commit/push.

Latest parent/user direction:mainchat is evaluating actualtcb standard-cell
libraries read-only. Preserve both evidence and preparedV2 as an unsubmitted
checkpoint; do not further expand manualIO repair or dispatch more experiments.
Await parent route decision. Registered sources/observers stay frozen.

## Minimal standard-cell mapping note only

Parent completed read-only tcb inventory and requests a short actionable mapping
under control only. Own standard_cell_minimal_mapping.md; all standard_cells/
metadata, foundry packages and frozen experiments stay read-only. No new source
package, library/OA mutation, remote work, shared-plan/log edit or baseline use.
Choose X020's stateless AND boundary only: verified-existing ND2D1 plus INVD1
in main12t30p140 library. Map actual subckt pins/power, preserve external Q1/LIVE/
QUIET and native driver/RC/clear/SR loads/feedback. Use completed snload-both as
the original-device A/B source with matching conditionedFF history; IOv2 stays
an unsubmitted checkpoint. Document old explicit MID capacitor removal as part
of the unit implementation change, not hidden foundry wiring edits. Metadata
does not contain Boolean tables/physical input-stack mapping: mark those pending
read-only source/manual confirmation; do not infer sequential-cell equivalence.
Validate pin table against suppliedJSON, currentSR reset-priority derivation and
local links/whitespace. No simulations or new approval/review hierarchy.

Delivered standard_cell_minimal_mapping.md: X020only two-cell ND2D1/INVD1
mapping with actual ports/power indices, original both-source comparison, explicit
MID-implementation change and preserved native drivers/loads/SR feedback. Marks
Boolean tables/physicalinputstack/drivechar as pending where metadata has no
evidence; no inferred DFF/latch/delay equivalence. Targeted metadata pin checks,
sourceSR stable-state reset priority, local links/whitespace and hashes of both/
IOlocal/IOv2 packages passed. No new runnable package or remote/OA/shared edits,
no baseline adoption/commit/push. IOv2 remains unsubmitted and unchanged.

## Standard-cell FF package preparation: compatibility metadata needed

Parent confirmed two_cell_logic_check.json: ND2fourMOS NAND and INVtwoMOS,
LIVE->A1 is adjacent-output NMOS, no global SPICE directives. Own new
standard_cell_v1/ and local prepare/analyzer/test files for the accepted FF-only
X020 replacement; baseline snload-both. Preserve foundry source as external
read-onlyinclude, never copy/modify its body. Existing metadata omits actual
six device identifiers/DGSB measurement bindings, literal geometry-unit forms
and file digest, plus whether installed nch_mac/pch_mac masters are models or
subckts for the SPICE M reader. These determine correct elaboration/probes.
Record exact missing metadata instead of guessing an executable package or
reporting success from model-name equality. Parent performs remote lookup.
No remote work or frozen/shared-file change in this session.

Local metadata links/whitespace and scoped diff check passed. Original
snload-both and IO V2 declared input hashes remain unchanged. Exact missing
metadata is listed in standard_cell_v1/compatibility_request.md; no executable
recipe or simulation result is claimed. Parent performs the bounded lookup.

## Standard-cell FF package: supplied metadata resolves preparation hold

Parent supplied two_cell_probe_metadata.json and model_master_metadata.json.
Six MOS names/DGSB and explicit-n geometry form, original SPI SHA/size and
inline subckt four-port definitions are now known. Continue only the accepted
X020 NAND+INV replacement from snload-both; no further metadata review gate.
Own prepare_standard_cell.py, standard_cell_analyze.py, test_standard_cell.py
and standard_cell_v1/ local artifacts. Read-only foundry include is enclosed
in SPICE mode and language restored to Spectre before local wrapper include.
Do not copy body, alter M prefix, geometry, scale or model sections. Keep
original upstream drivers, four conditional SN loads, RC/SR and eleven PWL.
Native numeric four-port current saves follow existing mac convention; actual
SPICE-M inline elaboration/probe support is deliberately a managed run check.
Missing required traces fail, never zero-fill or guessed internal binding.
Use frozen full_gate_analyze as streaming reduction plus a local wrapper for
external-library identity/probe provenance. All101 MOS six-pair observations
and actual retained-node KCL, five source work, native edges; core0.99 screen.
One focused synthetic test checks exact replacement/inputs/probes, native
global screening/energy, hard missing-trace failure and library SHA mismatch.
No remote operations/registration, shared files, adoption, commit or push.

Prepared standard_cell_v1 with unchanged original source history and123 retained
leaves;6 custom MOS+one internal CMID replaced by6 native-library MOS, total101
MOS/17passives.61V/435I/60KCL,606 simultaneous physical pairs+3 legacy aliases,
12 imposed initial witnesses only,5 source energies. Source deck differs only
external SPICE include and saves;11 PWL byte-identical. Numeric-port binding
unknowns remain explicit; external SHA/size is checked by analysis/optional
identity-only preflight, not a claimed time-of-use proof.19 declared inputs,
4,589,068B; recipe fileSHA1ca7c5ffb2b246ce8254f608453836b54c1286b2fd4d6bbefcf087daa3f3e681.
One focused synthetic test passed: exact source preservation/metadata truth,
library probe paths, global pre-window stress/energy, missing library gate-current
trace hard failure, and original-SPICE identity mismatch hard failure. Synthetic
data is never a circuit result. No registration/simulation or baseline adoption.

Parent subsequently confirmed exact19 inputs/freeze and foundry SHA/size,
registered and submitted sar8audit-ctrl-stdcell-ff-v1 with managed recipe hash
593b9ea2d3d261345eb16a21037346df3717a6c7b0781342ea09de606a611d20.
All declared inputs/observers/shared metadata now frozen. This session changed
ancillary status prose only; parent owns native compatibility/collection. No
additional submission or simulation pass is claimed; await actual results.

## Standard-cell result review: local collected data only

Parent completed/collected sar8audit-ctrl-stdcell-ff-v1, managed hash
593b9ea2d3d261345eb16a21037346df3717a6c7b0781342ea09de606a611d20.
Own review_standard_cell_result.py and standard_cell_v1/results/ only for this
comparison; ancillary status prose may update. All19 inputs, analyzer, source
packages, metadata and managed/shared records remain frozen. No remote work.
Verify receipt/input identities and native completion, then compare actual
snload-both source and completed both-stress energy. Separate6 library MOS
from95 retained MOS, simultaneous terminal extrema and exact0.99 screening.
Report tiny excursion magnitude bands separately without changing limits or
claiming solver error estimates prove safe. Duration uses native in-window
samples with bracket/linear-crossing method explicit; no fabricated full-history
duration from scalar extrema. Only genuinely present old waveforms are curves.
Use current/KCL snapshots and native charge to establish net exchange, not
pure-Cgd/channel inference. Compare native delays and identical-time signed
five-source energies; retain actual CMI and first-event scope. Generate/inspect
clear figures, recommend one next variable without submitting or expanding
replacement. No integrated, lifetime or full-cycle qualification claim.

Completed local receipt-bound comparison. Original9files/1,725,886B, standard
9files/8,997,843B and source energy reanalysis7files/1,707,968B all SHA/size,
registered inputs/native END/source raw identity verified. Direct M/inline and
all24 library numeric-port currents bind. Native settings equal: actual tran
reltol1e-7,abstol10nV/100fA,gear2only; PDKscalefactor0.9 in both native logs.
Standard6MOS36pairs23fail:9 between1uV..1mV,2 between1..10mV,12 above10mV.
Retained95MOS570pairs230fail:2<=0.11uV,3<=1uV,104<=1mV,63<=10mV,58>10mV.
Exact0.99 screen unchanged; numerical size bands are not acceptance margins.

N1.078641566->1.032371960V: overshoot -52.1985%, main peak episode10.1977->
3.7603ps; strict cumulative20.1169->12.9509ps includes early12/13uV hump.
Actual sample-to-QUIET31.2948->25.0998ps, VDDnet0.0707303->0.0683399pJ
(-3.3795%). LIVEdip -25.6123->-28.5116mV, Q1peak+2.2057->+3.0570mV,
QUIETdip -16.2905->-13.2673mV. RemainingRESET/RB/RC1 faults largely preexist.
Library N peak driven by A1 PM total drain injection, LIVE negative by original
driver PM total drain extraction; loads oppose LIVE dip. New KCLmax3.954pA.
Signed native charge/snapshots retained without claiming channel/Cgd separation.
Library36 pair and worst retained-device duration windows checked against full
over-limit witness counts when covered. Original source full606-pair comparison
is unavailable, so failure counts never used as old/new quality metric.

Reports in standard_cell_v1/results/: comparison.json, nativeCMIexcerpt, README
and three inspected figures. Two duration crossing self-checks, receipt/identity,
native over-count coverage, exact scalar settings and scoped checks performed.
All frozen19 inputs/observer/metadata and IO V2 stay unchanged. Propose only one
external R0 between actual LIVE and complete library A1 as next mechanism test;
no package, registration or remote work. First-event scope still not full reset,
clock feedback/PVT/lifetime or whole ADC qualification. No commit/push.

## Standard-cell external A1 R0: local package only

Parent accepted exactly one native R0 between actual LIVE and entire standard
NAND A1. Own standard_cell_r0_v1/ plus prepare_standard_cell_r0.py,
standard_cell_r0_analyze.py and test_standard_cell_r0.py; original standard_cell_v1,
its19 registered inputs/analyzers/shared metadata remain read-only. Source is
completed sar8audit-ctrl-stdcell-ff-v1/hash593b9ea2d3d261345eb16a21037346df3717a6c7b0781342ea09de606a611d20.
Use actual existing XD_QUIET_D.R0: rupolym,l=17.13u,w=1u,m=1,multi=(1).
Do not replace it with ideal resistance or alter foundry geometry. Existing FF
loaded R0 late native V/I is9.791809..9.792118kohm at41.4ns..END; record exact
native times/bias/current and both-port agreement, not a universal resistance.
Add one node inside unchanged X020 wrapper, move only both A1 gates through R0;
no other gate/passive/source/PWL or solver/sample contract changes. Retain all
606physical screens+3 actual-gate voltage aliases, update actual gate bindings;
observe both sides/two R ports, all KCL/slew/delay/five-source work and resistor
absorbed port work separately. Frozen streaming reducer remains unchanged.
Dedicated wrapper must fail missing native R currents, preserve CMI and no-pass
status. Native synthetic focused test covers topology/source equality, both
A1 inputs, complete screens, KCL/catalog, two-sided resistance/energy and missing
trace failure. Generate/hash/freeze one suggested managed recipe, no remote
registration/submission, broad scan, replacement expansion, commit or push.

Prepared one-R package: native RINPUT plus A1_FILTER, only MM4/MM1 gate bindings
change;127 existing leaves unchanged, no removals,11 PWL and non-save deck bytes
identical.101MOS18passives;62V437I61KCL;606physical+3 actual-gate aliases. Source
R0 late V/I9.791809..9.792118kohm recorded with exact native bias/timestamps and
both-terminal currents, not assumed new transient resistance. Dedicated analyzer
separates full-history passive port absorption from the original five sources;
both-side diagnostic native slew/halfrail/ratio/end values, all CMI/no-pass kept.
20 declared inputs/4,600,831B; recipe fileSHA
7112adc127e913320ba1bcb284e0ac03a0b8e9f31ac241ec2d7576bce3dbfad1.
One focused synthetic test passed covering exact topology/source freeze/PWL,
all screens and KCL bindings, finite two-side ratio, relative edge/slew, passive
energy/no source double-counting, and missing new-terminal hard failure. No
native simulation/new registration or source-helper edit; parent owns dispatch.

## R0 completed result review: local only

Parent registered/submitted/completed R0 case with managed hash
f182531c14a57e1a6aabb8a38fb532c17b7ae56b8889ec504e8fadc8244f990a;
9 collected files/9,440,208B. Own review_standard_cell_r0_result.py and new
standard_cell_r0_v1/results/ comparison prose/JSON/figures only. Entire frozen
source/new packages, helpers, shared metadata/registries and old results readonly.
No polling, remote commands, new variants/submission, adoption, commit or push.
Compare source stdcell-v1 and one-R case on original native times: voltage,
current and KCL at input dip/N peak/QUIET dip, peak/current-phase and native
exchange over common and event windows. Separate slower coupling from changed
pulldown competition without calling total drain current pure Cgd/channel.
Report both sides, all606 physical screens/legacy aliases, duration scope,
actual delay/slew and signed five-source versus passive energy. Check source
identity/settings/11 PWL and quantitative screen-amplitude groups. Keep tiny
failures recorded and conspicuous upstream stress separate. Inspect clear
waveform/current figures and recommend just one next variable, no generation.

Completed local R0 review. Both receipts/input identities/native END verified;
standard9files/8,997,843B versus R0 9files/9,440,208B. All606physical+3alias
screens retain0.99 limit. Nover42.37196->18.68331mV(-55.9064%), but main peak
episode3.76026->5.58397ps; +1mV duration3.52643->5.04080ps; strict cumulative
12.95086->14.38567ps. FilteredA1dip -9.85656mV while LIVE -28.51160->-30.13273mV.
Q1over3.05696->0.41927mV,QUIETdip -13.26728->-9.21098mV. A1input current peak
185.69555->70.91484uA, but total gate exchange0.7553465->0.7555336fC is almost
unchanged: rate shaping, not elimination of total transferred charge. Nfall
5.79623->9.09853ps, receiverA1rise2.94358->20.08631ps; one-R sides2.5394/20.0863ps.
QUIETafterclose25.09981->31.66481ps(+6.56501ps). Same-window VDDnetenergy
0.06833995->0.06785226pJ(-0.71362%); resistor absorbed0.282000fJ kept separate.

Common-stop A1 PM into-N exchange0.0347594->0.0043282fC. To own peak remaining
MM4 net injection0.0124977fC versus PM0.0033756fC; not a pure channel/Cgd split.
Upstream PM removed charge is nearly unchanged in common early interval while
load-network restoration drops0.0170540->0.0049016fC; NM restores more. Thus
filter improves receiver but original-driver |VDS|max1.0201327V remains worst.
KCLmax3.954pA; allCMI2751..2755 retained. Library failed pairs23->15, retained
230->222 with explicit magnitude groups/tiny cases, not a repair verdict.
Three figures inspected under standard_cell_r0_v1/results/, JSON and report.
Next proposal only: original LIVE NMOS multi1->2 at same500n/30n unit, keep R0
and everything else; measure extra input loading/parasitics and all screens.
No new candidate/generated inputs/remote job or frozen source edit/commit/push.

## Original LIVE NMOS multi1->2 with existing R0: local preparation

Parent accepts exactly XDUT.XCTRL.XTIM.X001.X001.MN multi1->2. Own new
standard_cell_r0_mn2_v1/ and prepare_standard_cell_r0_mn2.py,
standard_cell_r0_mn2_analyze.py, test_standard_cell_r0_mn2.py. Source completed
R0 case managed hashf182531c14a57e1a6aabb8a38fb532c17b7ae56b8889ec504e8fadc8244f990a.
All frozen source packages/helpers/metadata and results, shared registry/planlog,
PDK/OA/Obsidian/10bit remain readonly. Scoped dirty state is own untracked
control subtree; source registered input identities checked before preparation.
No remote operations, variant scan, other gate replacement, commit or push.

Target uses nch_mac W500n/L30n/nf1 and original diffusion/DFM parameters; keep
each unit unchanged and only multi1->2. Shared sar8p_inv must not be edited
globally: clone only ancestor path to this instance, preserve absolute node/
instance paths and verify flattened leaves differ at exactly target multi.
Keep PM, native input R0, library include, Q1, sources/11PWL and sampling/solver
contract unchanged. Existing62V/437I/61KCL/606physical+3aliases suffice: retain
all screens and currents. Dedicated analyzer reuses frozen streaming/library/
R0 helpers, quantifies X001.N voltage/timing/KCL and separate changed-NM/
unchanged-PM gate current extrema, signed event charge and terminal work.
Native currents are used as returned, never multiplied by2 in analysis.
Keep five-source net work and passive R0 absorption separate; no gate-terminal
work reclassified as dissipation. Source binding now points to R0 case.
One focused synthetic test checks exact one-instance multi change/no cross-cell
edit, unchanged nodes/saves/PWL/screens, native gate loading and energy/KCL,
missing loading trace hard failure, no-pass scope. Freeze one low-resource
recipe proposal only, no native run or claim that stronger NM fixes overshoot.

Prepared exact one-MN-multi package with four private ancestor clones; original
shared sar8p_inv unchanged, all absolute paths retained.130leaves/129unchanged,
no add/remove. Only multi1->2 at nch_mac500n/30n/nf1; test.scs and11PWL byte
identical. Existing62V437I61KCL609screens/source-power catalog unchanged. Generic
full observer and three source helpers remain hash-identical; target is its own
1MOS/6pair group, library6MOS/36, other94MOS/564. New loading reducer reports
native signed total currents without factor2, real event endpoints/charge/work,
input timing/KCL and all existing source/passive accounting, no-pass state.

21 declared inputs/4,615,577B; recipe fileSHA
dc8aa9568234f6fda7d21f86333552ae8ad2257a541a038666f098a3b10dbcf9.
Focused synthetic test passed: one-instance/per-unit identity, shared INV and
all catalogs, native gate current/no double scaling, signed charge/work/input
KCL, passive/five-source split and missing gate trace hard failure. Initial
synthetic KCL exact-zero assertion encountered1.694e-21A float roundoff; changed
only its arithmetic check to<1e-18A, not any native circuit limit or observer.

Ancillary source_input_loading_reference.json uses same new reducer on receipt-
verified old R0 native rows, actual source multi1 explicitly marked, no new
simulation/source writes. X001.Nmax1.006273V,fall7.68084ps; NM/PM gate minima
-73.8924/-156.9139uA, signed event exchange-0.397575/-0.844152fC. Reference
helps measure extra load rather than assume2x. Metadata/proposed-source linkage
and no remote/adoption/commit policy retained. No candidate native results.

## MN2 completed q2 review, preserve rejected first admission

Parent requests local comparison only. Own review_standard_cell_r0_mn2_result.py,
standard_cell_r0_mn2_v1/results/ and ancillary README status prose. All21 frozen
inputs/helpers and old source/results, shared metadata/registry/planlog readonly.
Original mn2-ff-v1 hash a262cf7214baa45720243b0252a0988d6c2ddcfcd391b9f1aebf571853927629
is rejected queue_timeout/host_memory_headroom, with no child/start/native and
only2 status/admission receipt files. Preserve it. Actual result mn2-ff-q2 hash
3b0e98474b6d0dc6e6a11484382c79e06d762e3a4d070c8134536097cedff31c has9files/
9,399,303B. Verify canonical recipes and same21 file inputs rather than call
the refused admission a simulated failure or silently reuse its ID.

Compare exact source R0 using common native times, same loading reducer for
X001.N current/charge/work and saved MN2 result. Reconcile group membership:
source old95 retained includes target, so separate target/6 library/94others
identically in both cases, not falsely222->219 as an improvement. Keep exact
0.99 screens and magnitude/duration details. Report restoration/feedthrough
and input loading/time tradeoff without decomposing total current. Show input,
LIVE/A1/N/QUIET waveforms/currents and signed source/passive energy. Recommend
one discriminating next test only; no new circuit/package/run or baseline use.

Completed q2 review and three figures. Initial identity check expected21 managed
files; actual managed recipes contain21 declared plus unchanged native_summary.py.
Verified all22 files are identical across rejected and actual admission; only
run_id differs. Original refusal receipt2files/1,940B remains no-child/start/native.
Actual receipt9files/9,399,303B and source9files/9,440,208B hashes/inputs/PASS/END
verified. Source loading reducer matches prior local reference; MN2 local same-
function metrics exactly match saved managed result. Frozen21 payloads unchanged.

LIVE -30.13273->-24.54881mV(-18.531%), A1dip -9.85656->-8.68568mV; X001.Nover
16.27324->15.87489mV, fall7.68084->8.48449ps. NM input exchange ratio1.999377,
whole INV gate exchange ratio1.319878; gate peak currents are not simply2x.
LIVE below-1mV duration5.19355->5.59944ps, Nmainover5.58397->5.90079ps. QUIET
delay31.66481->32.51260ps(+0.84779ps), VDDnetenergy0.06785226->0.06810904pJ
(+0.37845%), R0 absorption0.282000->0.275711fJ. Signed input gate work remains
separate from dissipative/whole-ADC power. Stronger-unit and changed-input
effects are not uniquely separated by native total currents, so no pure Ron/
channel/Cgd claim. Two own-minimum snapshots are not same-bias comparisons.

Harmonized target1/6,library6/36,other94/564 screens have3,15,219failures in
both cases (237total). Avoid misleading source95includes-target count222 vs219.
Existing SR RB -25.523mV remains, now worst other-core excursion; not newly
introduced by MN2. All CMI retained, KCL3.954/3.956pA. Ancillary README updates
distinguish refused original from actual q2; no frozen inputs or old results edit.
Next proposal only: controlled common-input isolated LIVE driver, same complete
recorded input and real load for multi1/2, to distinguish output-unit benefit
from upstream slowdown; require complete native prehistory, not invented
constant prefix. No bench generated, no remote commands/submission, commit/push.

## User-directed next standard-cell logic stage: X001 LIVE

Parent chooses standard-cell route instead of larger NM/fixed-input attribution.
Own standard_cell_live_v1/, prepare_standard_cell_live.py,
standard_cell_live_analyze.py and test_standard_cell_live.py only. Source is
completed standard_cell_r0_v1 MN1/hashf182531c14a57e1a6aabb8a38fb532c17b7ae56b8889ec504e8fadc8244f990a.
All previous frozen inputs/helpers/results and shared metadata/PDK/OA remain
readonly; no remote submission, global INV replacement, commit or push.
Replace entire X001 AND stage only with original foundry ND2D1+INVD1; external
A=SN,B=ACTIVE,Y=LIVE mapping and five wrapper ports stay. SN->NAND A1 preserves
original output-adjacent switched-input assignment; ACTIVE->A2. Disclose old
six MOS and internal X001.X000.CMID removal as whole-stage implementation
change, not single-transistor causality. X020 native standard cells, RINPUT,
other actual loads,11PWL and sample/solver contract unchanged.

Rebuild actual twelve library MOS native four-port catalog, new NAND net10 vs
removed MID, all101MOS606physical+3actual-gate aliases and all nonrail KCL.
Measure external SN/ACTIVE input loading and event charge/work, internal N,
LIVE/X020.N/Q1/QUIET timing. Preserve five-source work and passive R0 accounting;
separately observe existing ideal PWL boundary work using already-saved ports,
without adding power sources or claiming whole-ADC power. One focused local
mapping/current-coverage/loading check, syntax/identity/scoped validation;
freeze one recipe proposal and concise checklist handoff. No new native result.

Prepared X001 whole-stage package from completed MN1+R0, SN/A1 and ACTIVE/A2
verified against actual old gate roles. Removed exactly six old MOS+one cfMOM
CMID (original multi2 parameter record retained), added six native library MOS;
123 other leaves unchanged. Retired X001.X000.MID replaced by native net10;
shared INV unmodified, X020/RINPUT and11 PWL/non-save deck unchanged.
101MOS17passives;12libraryMOS/48numeric terminal requests,62V436I61KCL609screens.
Loading reducer reused read-only for SN/ACTIVE/internalN with correct old/new
gate port mapping and event41ns..END native charges/work. Source-only reference
is ancillary and not a candidate result. Existing five source powers, seven
already-present ideal input/command powers and two R0 passive ports observed
separately; no added electrical source. Complete old seven-boundary fullhistory
work not inferred from partial local export. Native pass/acceptance not claimed.

One minimal mapping/current-coverage/loading test passed, including exact old
cap removal, actual48MOS ports, all screens/KCL, synthetic signed gate exchange,
missing trace hard failure and energy classification.22 declared inputs,
4,626,037B, recipe fileSHA
fba7d02e16245a7cf52ff058f6cd716dd4df77f2425e265b199615619cf28870.
Four frozen source analyzer/helpers reused without edits. No remote registration/
submission, previous source/result edit, global INV replacement, commit or push.

## Completed LIVE library stage: compact local comparison

Parent completed sar8audit-ctrl-stdcell-live-ff-v1 managed hash
a99eeaad32f6fb75ac2c548ebf617690091e2175fb022aa43437e522684a9226.
Own review_standard_cell_live_result.py and standard_cell_live_v1/results/
plus ancillary status prose only. All22 input files, helpers, source R0/MN1,
metadata and prior results remain readonly. Reuse receipt/native/current/duration
helpers, one comparison table and one parallel-wave figure, concise native
terminal-current explanation and one repair recommendation. No report expansion,
new circuit, remote job/collection/registration, commit or push. Primary control
is completed R0 MN1; six-MOS/internal-CMID whole-stage replacement must stay
explicit. Group source original LIVE6 and X0206 and other89 identically, retain
exact0.99 physical screens/CMI and first-event qualification limits.

Compact review completed: source9files/9,440,208B versus candidate9files/
9,416,094B, all receipt/input/PASS/END identities verified; all48 native library
ports bind. LIVE -30.13273->-21.36999mV(-29.0804%), below-1mV duration
5.19355->5.55524ps. SNdip -8.98182->-9.41122mV, X001.Nover16.27324->12.51187mV,
X020.Nover18.68331->17.96565mV. QUIETafterclose31.66481->31.98649ps(+0.32167),
VDDnet0.06785226->0.06652662pJ(-1.9537%). Physical fail count237/606 in both,
groups15LIVE+15X020+207other. No fullADC or cap/device-only causality claim.
Native LIVE minimum PM total drain extraction3.64498uA balanced by NM2.08975
and R01.55523uA, allnodeKCL3.937pA. SNstage gate peak131.438->59.979uA and event
exchange1.61525->0.75570fC reflect whole-stage loading change. Four frozen
source reducers reused; one table/one inspected parallel figure plus compact
JSON only. Suggest next one logical reset-inverter stage XCLOCK.X000->INVD1
because unchanged RBdip25.523mV is larger remaining event; incoming RESET+24mV
must stay separate. No expansion/generated circuit or remote job, commit/push.

## Next single stage: native RB reset inverter, local preparation

Parent explicitly accepts XCLOCK.X000 only, from completed LIVE library case
sar8audit-ctrl-stdcell-live-ff-v1/a99eeaad32f6fb75ac2c548ebf617690091e2175fb022aa43437e522684a9226.
Own standard_cell_rb_v1/, prepare_standard_cell_rb.py, standard_cell_rb_analyze.py,
test_standard_cell_rb.py here. Shared dirty Obsidian, management, independent10bit,
sibling module work and shared plans/log remain untouched; own untracked control
subtree is the only write area. No OA objects owned, no remote commands/jobs,
registration, adoption, commit or push. Original recipes/helpers/PDK/OA read-only.

Clone only target SR master path and replace its original two-MOS reset INV
with unchanged native INVD1; preserve global SR/INV, real CLOCK_RESET driver,
all SR fanout, polarity/priority, eleven PWL, solver, sample window/closing edge.
Record old devices and absence/presence of any explicit capacitor change; native
cell dimensions/parasitics change together, not a single-device attribution.
Retain101MOS/606physical pairs plus3 aliases, actual new four-port currents,
all nonrail KCL, input gate loading/charge/work, CLOCK_RESET/RB over/undershoot
widths, SR reception/release timing and separately classified source/R0 work.
Missing events remain unobserved; same first-event stop cannot prove full reset.
One focused mapping/coverage and synthetic measurement test, source identities,
syntax/scoped diff checks; freeze suggested recipe for parent-managed dispatch.

Prepared exact two-MOS RB INV replacement, using one private SR clone.127 other
leaves unchanged; shared SR/INV and all eleven PWL/non-save deck byte-identical.
No explicit capacitor added/removed.101MOS17passives,14libraryMOS56native ports,
62V436I61KCL606physical+3aliases. Dedicated reducer retains original streaming
full-history screens/CMI/source work and diagnostic CLOCK_RESET/RB widths, input
loading, SR state/release. Unmeasured SR gate work is unavailable, not zero.
Focused synthetic check exposed causal-only halfrail pairing: unequal slopes
can yield negative50% delay; observer now keeps signed ordered pairs and leaves
unequal counts unpaired, without changing any electrical edge/limit. One focused
test passes exact mapping/coverage, signed delay, native charge/KCL, missing-port
failure, width estimates and source/passive classification. Source reference is
read-only recovered LIVE data, Rfall-to-RBrise3.70648ps; no reset assertion seen.
23declared inputs/4,640,740B, suggested recipe fileSHA
d4f3a5fea3e3d2043e58643da2a923bd74d172b092bd10116ff10c30be2b6e42.
Native elaboration/result remain pending parent-managed dispatch; no remote job,
new stress result, adoption, commit/push or edits outside control ownership.

Final AST/frozen23-input identities/owned-file whitespace checks passed. Global
git diff --check still flags existing protected Obsidian Wrap-up line13 trailing
space; left untouched. No further code/freeze changes after parent review.

## Completed native RB case: compact local review

Parent completed sar8audit-ctrl-stdcell-rb-ff-v1 with managed hash
745d10a01ded0cc487e7d2e5ff4ba57d130f7de2ec4e2959979f937375524bc4.
Own review_standard_cell_rb_result.py and standard_cell_rb_v1/results/ plus
ancillary README status prose. All23 frozen inputs/helpers, source LIVE,
PDK/OA, sibling modules and shared management/plans/log remain read-only.
Reuse verified receipts/native timing/current helpers; one compact comparison
table and one parallel waveform only. Reconcile source original reset2MOS
with new library2MOS, retaining all606 pairs/CMI and both source-work groups.
Compare RB minimum/maximum and widths, real upstream CLOCK_RESET loading,
SR reception/release timing and current KCL at extrema. Rank major remaining
faults by amplitude and native phase, not only failure counts. Recommend one
effective next local experiment with reason; no next package, remote call,
new simulation, adoption, commit or push. Validate plot visually and scope.

Completed compact RB review: both9-file receipts/input/PASS/END and equal native
effective settings verified; candidate9,487,824B/6065points,56 library ports bind.
Original/candidate RB minima-25.52335/-20.57122mV(-19.4023% amplitude), negative
1mV widths3.89047/3.73509ps; positive peaks+2.87327/+4.65025mV and +1mV widths
12.9305/17.3054ps. CLOCK_RESET peaks+24.00552/+24.62249mV; release3.70648/
4.71241ps. VDDnet0.06652662/0.06603150pJ(-0.7442%), source/R0 work separate.
Harmonized groups both RB8/12,existing-library30/72,other199/522;237/606total.
RB minimum native NM total drain extracts19.006uA, PM restores18.311uA and
SR gates restore0.695uA. Rebound occurs as QB recovers; X003 gate pair injects
10.470uA while INV removes9.812uA and other SR pair0.658uA. No channel/Cgd split.
Ranked rail issues include CLOCK_RESET24.622,LIVE21.368,RB20.571,X020.N17.966,
delayAB14.032,X001.N12.512,SRQB12.319mV with exact native phases retained.
QB high-state droop112.002mV remains a separate functional disturbance, no
half-rail Q edge/reset assertion observed, no full-reset/ADC acceptance claim.
One table/one inspected parallel figure and JSON under standard_cell_rb_v1/results/.
45 source/candidate frozen input identities unchanged; scoped AST/whitespace/
links/current/KCL/group checks pass. Eleven PWL byte-identical; native closing
crossing extraction differs-9.619e-18s, recorded without alignment or new timing.
Suggest only X023.X002 output NAND->verified ND2D1 with original AB/BB drivers
and RB/SR loads: largest upstream stress and excitation source. No next package,
remote job, frozen-helper edit, source/result overwrite, commit/push or adoption.

## Next single stage: CLOCK_RESET output NAND, local preparation

Parent accepts only X023.X002 replacement from completed RB case
sar8audit-ctrl-stdcell-rb-ff-v1/745d10a01ded0cc487e7d2e5ff4ba57d130f7de2ec4e2959979f937375524bc4.
Own standard_cell_resetnand_v1/, prepare_standard_cell_resetnand.py,
standard_cell_resetnand_analyze.py, test_standard_cell_resetnand.py under control.
Unrelated dirty Obsidian, management,10bit and sibling module work remains
protected, no owned remote OA objects, no remote calls/registration/commit/push.
All existing frozen inputs/helpers/results and PDK/OA remain read-only.

Clone only X023 OR master path, replace its terminal NAND with unchanged native
ND2D1, AB->A1/BB->A2; shared OR/NAND/INV, actual upstream two INV, current RB/SR
loads, polarity/priority, all eleven PWL and sample/solver contracts unchanged.
Record entire original4MOS+MID capacitor removal and new intrinsic parasitics.
Rebuild actual D/G/S/B currents, all606 physical pairs/legacy aliases/nonrail KCL;
measure both input gate burdens/charge/work, CLOCK_RESET/RB widths, SR state/
reset release, independent five+seven source works and passive R0 absorption.
First-event missing assertion remains unobserved. One focused mapping/coverage
and synthetic measurement test, identity/syntax/scoped checks, then freeze one
suggested low-resource recipe for parent-managed dispatch. No next gate/full chain.

Prepared exact X023.X002 whole-NAND replacement with private OR clone. Original
four MOS plus explicit cfmom MID removed, four native ND2D1 MOS added;124 other
leaves unchanged, shared OR/NAND/INV and current RB/SR masters unchanged. Eleven
PWL and non-save deck bytes identical.101MOS16passives,18libraryMOS72native ports,
62V435I61KCL606physical+3aliases; one fewer current is retired CMID port, oldMID
voltage replaced by actual native net10. Reuse five frozen source reducers plus
RB observer unchanged; dedicated wrapper adds native AB/BB gate burden/charge/
work while keeping CLOCK_RESET/RB widths, SR state/release, source/R0 split/CMI.
One focused mapping/coverage/synthetic test passed exact source identity, real
upstream/downstream leaf equality, input pin roles/all screens/current KCL,
signed native charge/no rescaling, missing-port failure and energy categories.
24declared inputs/4,652,919B; recipe fileSHA
358c53c6d6d5893974739a746534bb63328ce68ebd46a3110aae1cc5d6e0736a.
Ancillary old-input reference from receipt-verified completed RB source is not
a candidate result. Native new binding/elaboration and circuit outcomes remain
pending parent-managed dispatch; no remote operation, next gate, adoption or push.

## Completed RESET NAND case: local waveform/current review

Parent completed sar8audit-ctrl-stdcell-resetnand-ff-v1 with managed hash
7f60d766e2c8f6f4b964d5744cdd1442292e7f86485596b8374694a5ec616c9d.
Own review_standard_cell_resetnand_result.py, standard_cell_resetnand_v1/results/
and ancillary README status only. Source RB and candidate frozen inputs/helpers,
all prior results, PDK/OA/shared plans/registries/sibling modules remain readonly.
Verify receipts/native settings,72 port bindings and harmonized606pair roles.
Identify entered/cleared pairs behind net237->245 rather than equate net8 to
eight newly failing physical pairs. One compact table/parallel figure; quantify
CLOCK_RESET/RB/SR changes and native current KCL. From existing native V/I only,
inspect QB before/minimum/recovery plus actual upper/lower NAND VGS/VDS and MID
capacitor exchange, compare persistence after RB edge against pure edge coupling.
No model-region/channel/Cgd split asserted without supplied evidence. Rank local
mechanisms and recommend one discriminating next experiment, no next package,
mechanical all-cell replacement, remote commands/job, adoption, commit or push.

Completed local RESET NAND review. Source9files/9,487,824B,candidate9files/
9,448,118B/6058native points,72 actual library terminal bindings; receipts,
input identities/PASS/END and equal effective settings verified. Upper reset
peak24.622->20.340mV(-17.392%), RBdip20.571->18.144mV(-11.797%) but negative
1mV width3.735->4.104ps; RB rebound4.650->4.724mV,release4.712->5.008ps.
Role-matched606 pairs identify8entered/0cleared: six max83.280uV from reset
low undershoot, one44.030uV,one13.837uV. Native counts245 vs237 retained; no
small-amplitude waiver. At reset low minimum RB INV gate ports extract77.090nA
and NAND output ports restore77.090nA, explaining finite small rail excursion.

QB drop/recovery essentially unchanged. Before/low/+30ps actual upper NM
VGS/VDS=-0.067/0.907,0.654/0.546,0.422/0.413V; low lower gate VGS-2.444mV.
QBmin0.877733V at41.091571ns with upper NM drain320.657uA/source-300.310uA,
CMID286.536uA and PM1 replenish319.969uA. +30ps cap still20.415uA; recovery
within1mV until stop takes131.898ps vs131.674ps source. After RB90% cap absorbs
4.364577fC,upper source provides4.571836fC,lower drain0.207259fC balances;
upper gate absolute exchange0.159139fC. Supports persistent MID charging/QB
sharing and pull-up recovery, not edge-only feedthrough. No saved region/Vth/
channel decomposition; no triode/amplifier-overdrive or leakage claim. QB stays
above halfrail, no wrong flip proven. AllnodeKCLmax3.937pA, CMI retained.
One inspected parallel figure includes voltages/MID/currents/actual VGS/VDS,
one short comparison table and JSON under standard_cell_resetnand_v1/results/.
Next proposal only XCLOCK.X003.CMID native MOM multi2->1 at unchanged MOS,
driver/load/history/edge, to test observed charge reservoir and overshoot tradeoff.
No next gate/package, remote operation, model edit, adoption, commit or push.

## Next unique capacitor experiment: QB NAND MID multi2->1

Parent accepts only XCLOCK.X003.CMID native MOM multi2->1 from completed
sar8audit-ctrl-stdcell-resetnand-ff-v1/hash
7f60d766e2c8f6f4b964d5744cdd1442292e7f86485596b8374694a5ec616c9d.
Own standard_cell_qbcap_v1/, prepare_standard_cell_qbcap.py,
standard_cell_qbcap_analyze.py, test_standard_cell_qbcap.py here. Current shared
dirty Obsidian/management/10bit/sibling work and all frozen source/helper/result/
PDK/OA content remain read-only. No owned OA objects, no remote calls/registration,
source adoption, shared log edit, commit or push. Only own control subtree writes.

Clone only target SR/NAND master paths, retain absolute nodes/instances and all
MOS geometry/diffusion/logic/PWL/real upstream and downstream load/solver/sample
contracts. Only flattened leaf parameter difference must be cap multi2->1.
Existing62V435I61KCL606physical+3alias observations stay; no second scale factor
on returned capacitor currents. Reuse frozen reducers for full-history terminal
stress/CMI/five+seven source work/passive R0 and upstream loading/reset widths.
Add bounded native-window MID charge/work, QB minimum/persistent recovery,
before/minimum/recovery bias and terminal-current snapshots, post-RB90 charge
balance. Missing recovery/edge stays unavailable. Faster settling may increase
overshoot; no predeclared circuit pass or region/channel/Cgd/long-channel inference.
One focused source/map/coverage and synthetic measurement check, syntax/identity/
scoped checks, local freeze for parent-managed dispatch. No second circuit change.

Prepared exact one-cap multi2->1 package with private SR/NAND ancestor clones.
Same128leaves,127identical; actual target nodes/model/unit geometry preserved,
all101MOS/18library MOS mapping and all source/passive/clock/load leaves unchanged.
Whole test.scs and11PWL byte-identical;62V435I61KCL606physical+3aliases and source
power catalog unchanged. Additional stdlib streaming observer retains signed
native charge/absolute exchange/port work, before/minimum/recovery DGSB and
actual VGS/VDS, phase-specific five-source/seven-boundary/passive-R0 powers.
Returns unavailable recovery/phases rather than zero; no multiplicity rescaling,
new OP/region/long-channel assumptions or circuit qualification. Frozen prior
reducers reused without edits. One focused test passed exact single-leaf and
all observation identities, charge/work/current balance/bias/power categories,
unrecovered window handling and missing-port hard failure. Local unsubmitted
metadata refrozen only after phase-power observation addition; no circuit change.
25declared inputs/4,668,313B, final recipe fileSHA
bc207d890e6890435142443cf8b62b6b7a6504f921501b402cd7453f7f6e1c7c.
Read-only source reference explicitly multi2; source receipt/canonical native
bytes verified, no candidate result. Pending parent-managed native dispatch,
no remote command/job, registry edit, second variable, adoption, commit or push.

Parent submitted sar8audit-ctrl-stdcell-qbcap-ff-v1, managed hash
e51627eebe5435844411e185bfd80f38eb3a2ded3796abf95bdfd4c955c5a7ee.
It exited2 after31.3019s/RSS42,795,008B at license checkout, SPECTRE-209, before
circuit parsing/analysis; electrical verdict not inferred. Verified local3-file/
6,023B receipt and canonical managed identity, no native waveform/analysis pass.
All25 declared frozen inputs and recipe fileSHA bc207d890e6890435142443cf8b62b6b7a6504f921501b402cd7453f7f6e1c7c
unchanged. Only ancillary README status recorded; no circuit/helper/recipe edit,
retry/new run/experiment/remote operation. Parent chat owns further handling.

## Completed QB-cap q2: compact local comparison, preserve license failure

Parent completed sar8audit-ctrl-stdcell-qbcap-ff-q2 with managed hash
ae800c95066a921a5df6e9101c29adecdf7a6e761cac71b1490ed0f1b30920b0.
Own review_standard_cell_qbcap_result.py, standard_cell_qbcap_v1/results/ and
ancillary README status only. All25 candidate inputs/helpers/source artifacts,
earlier license failure and reset-NAND baseline results, PDK/OA/shared registry/
planlog/sibling modules remain read-only. No remote operations or next experiment.

Verify failed v1 and q2 identities, same25 electrical input hashes/settings,
actual q2 receipt/PASS/END/72 ports. Compare exact reset-NAND baseline and frozen
multi2 storage reference with multi1 q2: charge/biased currents/work/recovery,
RB/RESET widths/peaks, release, all606 physical screens and independent source
work. One compact table/same-axis figure; distinguish QB charge improvement
from transient voltage failures and natural input-loading feedback. Recommend
only one evidence-supported priority if warranted, no package/circuit edit,
registration, model-region inference, adoption, commit or push.

Completed concise q2 report and inspected same-axis five-row native waveform.
Failed v1 remains3files/6,023B/SPECTRE-209/exit2, no electrical result. Normalized
execution recipe differs only run_id; submitted recipe also has retry_provenance,
same25 electrical inputs/settings. Earlier report omitted this submitted metadata.
q2 receipt9files/9,473,260B/6059points and source9files/9,448,118B/6058points,
input identities/PASS/END/72library ports verified, effective settings equal.
Source multi2 storage reference binds exact baseline proof; q2 actualmulti1.
QBmin0.877733->0.917302V, droop112.267->72.698mV(-35.245%), recovery131.898->
70.734ps(-46.372%). Own-RB90-to-recovery cap charge4.364577->1.906870fC;
different native integration endpoints explicitly retained, not fixed-bias C fit.
New minimum upper NM VGS/VDS0.597/0.535V, lowerVGS-0.683mV, upper D223.538uA,
source-201.042uA,cap183.568uA,PM1replenish221.481uA; +30ps cap7.790uA vs20.415.
Bias/total current/phase source-power evidence preserved without region/channel
decomposition. RB initialdip18.144->18.149mV and RESET+20.340->20.339mV essentially
unchanged; RB rebound4.724->3.573mV and +1mV width17.400->11.680ps improve,
QB/SN positive peaks increase0.125/0.108mV. Release5.008->5.002ps. VDDsame-window
net0.0651130->0.0622725pJ(-4.3624%), other sources/passive separate.245/606physical
failed pairs remain same members (entered0/cleared0), CMI2751..2755 remain.
Recommend only future X003 series-NM gate-control swap, held-low Q adjacent QB
and RB lower, PM/MIDmulti1/geometry/history unchanged: directly test isolation
of observed QB->MID path, not continued capacitor shrink/library sweep. Need
future SR set/reset/input loading/stress validation; no package/new experiment,
remote call, source/helper edit, adoption, commit or push in this review.

## Next unique QB NAND gate-order experiment: Q upper, RB lower

Parent accepts local-only XCLOCK.X003 MN0/MN1 gate swap from completed QBcap
q2/ae800c95066a921a5df6e9101c29adecdf7a6e761cac71b1490ed0f1b30920b0.
Own prepare_standard_cell_qborder.py, standard_cell_qborder_analyze.py,
test_standard_cell_qborder.py, standard_cell_qborder_v1/ here; ancillary q2
provenance wording correction also owned. Existing frozen25 inputs/helpers,
prior results/native failure, PDK/OA/shared management/log/sibling work readonly.
No remote owned OA objects, registration/submission, commit/push or adoption.

Only two series-NM gate connections change: MN0 remains output-adjacent but
gateQ, MN1 remains lower but gateRB. PM network, native MID multi1, all MOS
geometry/D/S/B, sources, actual fanout and11PWL/sample/solver remain. Clone
only required SR/NAND ancestors; no overwrite of earlier X020 swap experiments.
Update actual gate-port node catalog, RB/Q KCL, physical VGS/VGD/VGB pairs,
RB affected gate observer and complete Q gate fanout. Retain606physical screens,
all bias/native-current/storage/recovery/independent source-work observations.
Natural initial state is not imposed/recentered; only original external source
initial witnesses remain gates. This first sample-close/release window does
not exercise full CLOCK_SET/set or reset assertion from Qhigh; both qualification
gaps explicit, no inferred pass or OP/region/channel decomposition.
One focused mapping/source/native coverage test and local freeze for parent;
no second circuit change or further experiment generation. Correct raw q2
recipe provenance wording: run_id/retry_provenance differ, electrical25/solver
same; normalized execution recipe comparison alone omitted submitted metadata.

Prepared exact MN0/MN1 gate-only swap: same128leaves/126identical, no adds/removals;
original PM/MIDmulti1, all D/S/B/geometry/18foundryMOS mappings unchanged. Old SR/
NAND and X020 history untouched, private ancestors only. Current names remain
435 but two gate catalog nodes swap; regenerated all KCL and actual six pairs,
RB NM load nowMN1, Q covers MN0+MP1+two buffer gates.62V61KCL606physical+3aliases.
Original12 imposed initial witnesses retained; no internal clamp/peak contract.
Full set/latch and reset from Qhigh/priority are explicit unqualified gaps.
One focused test passes exact leaves/catalog/pair and natural-initial invariants,
source test/PWL identity, real RB/Q current routing/KCL, actual new VGS, signed
negative MID exchange preservation, missing gate rejection and coverage flags.
26declared inputs/4,678,670B; recipe fileSHA
86cdada64927dd1c7ae68b3a6b99a1de99b6d570c3c20f1885b4a134c3ab0cda.
Source q2 observation reference uses verified old rows/old gate mapping, adding
complete original Q gate burden without new simulation. Submitted q2 raw recipe
run_id/retry_provenance correction applied to existing prose/JSON and generator;
native metrics/figure/frozen25 helpers unchanged. No remote/new candidate native
run/registry edit, second variable, adoption, commit or push; parent dispatch next.

## Completed QB gate-order case: local compact report only

Parent completed sar8audit-ctrl-stdcell-qborder-ff-v1,9files/9,440,613B verified.
Own review_standard_cell_qborder_result.py, standard_cell_qborder_v1/results/,
ancillary README status and this control plan only. Frozen source/candidate
inputs/helpers, PDK/OA, all shared plans/log/registries and sibling work readonly.
Compare completed qbcap-q2 and frozen complete-Q-load source reference with
actual candidate native QB/MID charge/recovery, real RB/Q gate fanout, bias/
source work, reset/RB stress and606-pair entered/cleared members. Natural initial
observations never substitute for SR set/reset qualification. Check whether
within1mV metric includes positive glitch after already-small negative minimum.
One compact table/same-axis waveform and one priority validation recommendation,
no remote call/new simulation/circuit/package/qualification, commit or push.

Completed compact QB-order report. Managed hash
c933758028b599adad5e3ab700a3e610424c2ab10133ccbaa33ead845fd87ce4;
candidate9files/9,440,613B/6051points,source9files/9,473,260B/6059points;
input/receipt/PASS/END/effective settings and72library native ports verified.
RB/Q all four real gate bindings match new nodes. QBnegative72.698->0.388mV
(-99.466%); minimum-to-stable70.734->16.442ps is explicitly different metric
composition: candidate minimum already inside1mV, subsequent+10.185mV peak
settles at41.094366ns, not16ps of negative-error recovery. MID no longer charges
to0.702V; max0.0963V then discharges. Own-RB90-to-stable cap+1.906870->-0.153834fC,
absolute candidate exchange0.153834fC (not cancellation). At RB90 upperVGS-0.034V,
drain-0.540uA, lowerVGS0.892V/drain74.478uA,cap-67.150uA supports rerouted path;
no region/channel decomposition. RB gatecharge2.224668->2.594256fC(+16.613%),
peak323.230->328.206uA; Q full gatecharge-0.098514->+0.014329fC recorded.
RBdip-18.149->-18.074mV persists, rebound3.573mV->2.006uV; RESET+20.339->20.340mV
persists. Release5.002->5.080ps; VDDnet0.0622725->0.0593486pJ(-4.695%) separate
from other ideal source works/passiveR0. Physical245->237 is12cleared/4entered,
new excesses0.324,2.006,2.006,33.901uV, all exact0.99 screens/CMI retained.
Cleared group includes3 merely0.0647uV and one3.573mV; changed gate endpoints
retained per-case. Natural DC MID84.519/84.419mV not forced; no Q rise/fall,
set assertion or reset-from-Qhigh observation. Recommend one loaded full SR
reset/hold-release-set/hold-reset-from-Qhigh validation incl priority to check
other direction before more repair. One table/one same-axis figure/JSON only;
no remote/new circuit/qualification/shared planlog edit, adoption, commit or push.

## Full SR bidirectional paired bench: local preparation

Parent owns future serial managed execution. Own prepare_sr_cycle.py,
sr_cycle_analyze.py,test_sr_cycle.py,sr_cycle_note.md,sr_cycle_v1/ here only.
All frozen qbcap-q2/qborder inputs/helpers/results, original netlists, PDK/OA,
shared management/planlog and sibling work readonly. No remote calls/OA objects,
new chat/extra review layer, source adoption, commit or push.

Trace original sar8p_sr and selected SR wiring before assigning expectations:
RB=!R,SN=!(S&RB),QB=!(RB&Q),Q=!(SN&QB). Enumerate stable solutions from actual
INV/NAND pin mappings, verify both two-NM orders remain static NAND. Rhigh
forces Qlow even with Shigh; hold has two solutions. Dynamic priority not assumed.

Paired independent SR cycle retains original actual101MOS load shell, native
X022 AND and X023 INV/NAND reset driver, Q/QB direct fanout and X025 loaded
comparator clock receiver. Only driver input boundaries exposed to four ideal
command sources; background sample/phase/DEC/analog and conditional diffusion
bias histories held DC at source initial values. Thus no ADC feedback cycle or
sample-contract change; this is an isolated SR excitation with retained native
load context, not full-ADC timing qualification. No ideal Q/QB/MID/RB clamping,
ic/nodeset, waveform alignment or forced internal initial state.

Ten1ns plateaus: reset/hold,release/hold0,set,hold1,reset-from-Qhigh,overlap R=S=1,
release R while S high,set then assert R while S high,drop S while R high,
release R/hold0.20ps external command edges; R_B=0,S_B=1 conditioning fixed.
Both variants differ only the two X003 NM gates. Actual R/S/Q/QB transitions,
signed both-direction driver/core delays, hold windows/input truth, storage
charge, all actual terminal voltages/currents/screens and independent sources
recorded; failures/missing/ambiguous events not filled with passing values.
Full native saves remain all actual ports. Full-history statistics for every
saved port/606physical pairs/KCL; exported native wave currents limited to SR,
driver/Qbuffer/direct-clock-load/input-power nodes to bound collection, declared
explicitly. Raw2GiB, derived binary64MiB/total80MiB,1thread,sim1GiB/900s,
analysis256MiB/1200s. Same models/solver/PWL for both, no speed claim.
One focused truth/source-pair/fanout/measurement test, syntax/hash/scoped checks,
freeze two local packages for parent. No native simulation or second circuit edit.

Prepared paired loaded SR benches,10ns/10plateaus/20ps commands; source actual
INV/NAND equations and stable solutions extracted from original and both selected
SRs. Verified R=S=1 intended staticQ0 from qualification wiring, not ordinary SR
assumption; dynamic behavior remains untested. Four new ideal command inputs at
unchanged X022/X023 input boundaries;11background histories held source DC.
Full original101MOS/native input drivers/Q/QB/CMPCLK direct fanout retained;
paired flattened leaves differ only two X003 NM gates, PM/MIDmulti1 unchanged.
No internal clamps/initial alignment or ADC-contract edit.66V439I65KCL606pairs,
72native library ports, all raw currents/global stats;172 core/driver/load/power
currents exported at all native timestamps with fullV/KCL.16ideal source works
and passive terminal works separate, no whole ADC power claim.
Minimal single focused test passed source/freeze/truth/fanout/pair identity,
both-direction5ps/7ps synthetic delays, hold memory failure detection, missing
hold windows unknown, mandatory current rejection and source work classification.
Each25declared inputs, rb384,754B / q387,140B, recipe fileSHAs
58cc18c3df107bf69907028bed88bf2789a9b4c3453fb4c635aea49aa7f0b7c5 and
c8a07326d3bf901b44724d0dc44e950bafdc376441454381f23c701bab0e2408.
One sr_cycle_note.md plus contract/manifests/two local packages, no native result,
remote launch, extra review/chat, shared log edit, adoption, commit or push.

## SR cycle collection correction: <=30MiB final set, <=32MiB user cap

Parent flags the prepared80MiB collection declaration as above user's32MiB cap.
Only edit SR derived export/collection budget and corresponding minimal budget
test/freeze metadata/note; circuit10ns sequence/all439 raw currents/606 full-history
stress and physical extrema unchanged. No remote execution. Full172-current
analysis may use bounded temporary table; after complete observations project
wave columns at every original timestamp, retaining all66voltage traces and
full-history/per-phase stress/logic/current/source metrics. Full PSF retained
remote. Final derived and actual collection members including state/log reserve
must fit30MiB, not silently drop extrema or interpolate points. Refreeze only
these unsubmitted SR packages after verifying electrical files stay identical.

## Standard-cell migration inventory: local review checkpoint

Parent's latest direction supersedes further custom-NAND optimization. Finish
only the resource correction above; do not dispatch the paired custom-SR jobs.
Own standard_cell_migration.md and standard_cell_mapping.json in this control
directory. Read frozen full-ADC DUT and existing standard_cells metadata only;
no new remote queries, simulation, library edits, architecture or external ADC
sampling-contract changes. Record exact original pure-digital instances and
connections, reset/feedback/load contracts, actual foundry masters/SPICE pins,
and observed PVT/model availability. Distinguish Boolean-equivalent mappings
from storage, RC qualification, handshake, analog receivers and drivers that
need separate timing/implementation review. Missing library evidence stays
explicitly unknown; never infer latch/reset polarity from a cell name.

Validate complete original hierarchy coverage, all existing metadata hashes,
pin counts, actual fanout and SR truth against the frozen source. Local JSON
parse, deterministic source cross-checks and scoped whitespace review suffice;
no electrical pass is claimed. Existing 10ns SR sequence/measurement can be
reused by a future all-standard-cell candidate after parent review. No remote
ownership, managed registration, shared plan/log, adoption, commit or push.

Resource correction complete: one focused near64MiB synthetic budget test passed.
All27,594 native timestamps/all66voltages remain byte-exact; final96columns
21,192,192B,8MiB synthetic result plus actual managed members29,588,159B,
with256KiB final-state reserve29,850,303B<30MiB<32MiB. Oversized-log case
rejected; rawPSF/global606extrema unchanged. Electrical DUT/test/15PWL hashes
unchanged in both packages; current recipe hashes b3829d138915221925afde93b153c1d953abb92295bbbd84928220eeea1d6601
and7800096f08b5da0a1b4853615cbf8eef864ddb4969b768439aa78a3084b14154.
No runtime/electrical qualification; both custom-SR cases now held locally per
latest standard-cell migration direction, not submitted.

Standard-cell mapping review checkpoint complete. Added standard_cell_migration.md
and standard_cell_mapping.json only. Frozen full source SHA b9bf9f46...133680
and six read-only library metadata files verified unchanged. All174 maximal
units/90 nested timing INV paths and bindings independently cross-checked;
all2508 original leaves partition exactly once (1833MOS).30 combinational truth
cases and four SR stable cases verified from actual source wiring and original
library INV/ND2 truth.24 source DFF master/slave TG and async-high reset
connections verified structurally; library DFCNQD1 CP/CDN contract remains
unknown, not inferred from name.118 combinational units include16 reference
driver INV interfaces;2SR/24DFF/30RC modules remain explicitly separated.
AST of three changed SR scripts, local JSON/MD links/whitespace and scoped
git diff --check passed. No new remote query/job/registration, candidate DUT,
foundry/OA/shared-planlog edit, migration pass, adoption, commit or push.

Server-stop checkpoint: parent relays the user's explicit instruction to stop
SSH/Bridge/status queries, submissions and collection retries until the user
confirms recovery. This control session already uses local evidence only.
Stop here with the completed mapping and budget checkpoint. DFCNQD1 CP/CDN
semantics, delivery compatibility and native timing/stress validation require
later verified server access; leave them unknown. Do not auto-probe, kill or
resubmit any in-flight job, prepare another circuit, or extend this checkpoint.

## 2026-10-27: approved full standard-cell netlist candidate

User restored SSH and authorized netlist-level work while Virtuoso remains
unavailable. Parent reviewed174-unit mapping and reference standard-cell
boundary once; proceed without another review pause. Own
standard_cell_full_v1/ and control-local prepare/analyze/test helper files.
Keep earlier frozen packages, raw results, shared registries/plan/log, sibling
work, PDK/foundry/OA/Obsidian/10bit read-only. Dirty branch remains ahead30 with
unrelated shared/user changes; no overlapping owned files observed.

Perform bounded read-only SSH metadata query on thu-wei (UID596): verify actual
DFCNQD1 and INV/NAND ports, original SPICE graph, library identity, model entry
and relevant section/declaration identity. Store only hashes/connectivity and
derived logic evidence, no foundry geometry/body. No Virtuoso/Bridge mutation,
remote simulation or managed register/submit/collect in this session.

Generate complete pure-digital candidate from immutable full audit DUT,
preserving external pin order, analog primitives, source stimuli, original
reset/feedback and sample-window/close-edge contract. Explicitly retain and
list RC/clear timing and analog interface boundaries rather than claiming
their unresolved physical behavior is solved. Use unmodified foundry SPICE
include, never emit library internal bodies or change device geometry.

Prepare minimal complete loaded SR bidirectional and DFF capture/reset
testbenches for FF0.99V/-40C and SS0.81V/-40C. Input drivers and native direct
fanout/load context must be explicit and measurements include all actual MOS
terminal pairs, current/KCL, waveform events, reset/hold and independent source
energy. Declare <=4threads/1GiB simulation, <=256MiB analysis, <=32MiB collected
files. No new execution of old custom-SR pair. Parent owns serial managed runs.

Validate source/library truth by deterministic graph/state checks, candidate
connectivity/analog-delta/source-hash coverage, required saves/current bindings,
focused synthetic observer failure paths and budgets. Freeze input recipes
only after helper checks pass, preserve all prior artifacts. Deliver ready
managed recipes and actual remaining limitations; no qualification/adoption,
shared log edit, commit, push or timer resume.

2026-10-27 local implementation frozen. Read-only SSH verified thu-wei/UID596,
original SPI b7b366bf...2fc0e (2452584B),28MOS DFCNQD1 graph and model entry/
child hashes. Enumerated actual switch states: CP positive edge under master-
memory continuity, CDN low asynchronous output clear; numeric timing untested.
A second bounded section-metadata query failed because its regex did not match
pre_simu; no absence inference, no further probing; original templates/native
elaboration remain the validation surface. No remote writes or simulation.

Generated complete original-core-reference ADC candidate SHA0eb51413d69a8a3a7da7708dbbb6b9e8a4a82688cb30944bc7da7fb3d65c27cf;
96 direct ordinary reference N/P inverter pairs additionally standardized.
All1848 native library MOS included;1977total candidate MOS,60 original clear
MOS in30RC blocks,69 protected analog MOS. All protected analog/Rgate leaves
and nonchanged blocks verified exact;210private NAND/DFF MOMs retire with the
old implementations. Not the later IO/singleGPP repair source. D1 initial
strength unqualified; internal effective sampling edge must later be measured.

Two20ns FF0.99V/-40C and SS0.81V/-40C packages:26storage contexts(2SR/24DFF),
76 exact native immediate load blocks,1870MOS/11220physical pairs/980V/7555I.
Load output fanout cut explicitly; not complete Miller/analog/ADC qualification.
Load FF reset held; independent corner-scaled commands through real gates.
All native ports/KCL/stress/source work retained; lossless gzip return wave,
30MiB entire collection guard under32MiB user cap,1thread/1GiB/256MiB analysis.
Four focused tests passed2.347s, all source immediate gate counts crosschecked,
all15frozen inputs per corner hashed,3AST/scoped whitespace checked.
FF recipe6b79278918ed1435da37007c1a3054b5f10728880241cd8e3d3606327cdb657e;
SS recipe91e7d8abce4b80e924fe85e9f3ca6ddb57cc8330acf0da2ac1af54e21b9928c8;
each4133359B declared inputs. Parent owns managed registration/serial execution.
No old custom-SR restart, OA/PDK/shared planlog edits, adoption, commit/push.

## Frozen storage runs: prepare local result entry only

Parent has submitted FF and registered SS. All15 registered inputs per case,
including prepare-produced DUT/config/library evidence and frozen analyzer,
remain byte-identical. Own only a new review_standard_cell_full_result.py and
standard_cell_full_v1/results/ reading guide/review outputs; these are not run
inputs. Prepare receipt/managed-recipe/input identity checks and bounded gzip
wave verification, then concise independent hold, extra-Q/reset-overlap,
actual-pin-delay and per-device terminal-screen summaries. Missing/incomplete
results cannot become zero/pass. Keep first-hop-load scope explicit.

Use one focused synthetic validation of classification/integrity and local
syntax/scoped whitespace checks. Do not analyze either real case until parent
notifies collection completion; do not query remote state, modify registered
files, prepare a full-ADC closed-loop run, or start any simulation.

## Storage v1 output-limit failure: measurement-only v2

Parent reports FFv1 limit_exceeded at3.11464ns,2151981342B output,79.35s,
peakRSS379396096B. Native incomplete/no zero-error footer; SPECTRE27/7082
and later USIMUWI20006 are output-limit evidence, not insufficient RSS or
completed electrical verdict. SSv1 is registered only and must not be started.
Keep all v1 inputs and raw/failure evidence unchanged. No remote calls here.

Own new standard_cell_storage_v2/ plus prepare_standard_cell_storage_v2.py,
standard_cell_storage_v2_analyze.py and one focused test helper, all under this
control directory. Derive v2 from exact registered v1 bytes, changing only
save requests/current coverage/KCL configuration and a measurement wrapper.
Keep circuit,20ns commands,980V/11220physical pairs/26functional contexts,
source levels, complete native voltage stress, solver and resource limits.
Keep <=100 necessary source-power/key SR/RC current traces. Unsaved currents
and incomplete KCL explicitly unknown, never zero or full coverage. Retain
all external ideal-source work observations; no whole-ADC power claim.

Use separate proposed run IDs/directories; parent owns registration/execution.
Estimate raw-size reduction from the partial v1 output/record count, state
that activity/format/timestep make it an estimate, not completion proof. Do
not enlarge2GiB output/32MiB collection or split into a queue speculatively.
One focused measurement-delta/coverage/observer-compatibility test, freeze and
deliver recipes. Defer real v1 review until notified; local report entry may
be completed without reading either active run or modifying frozen inputs.

V2 measurement-only packages frozen.89currents(7sources/34SR/48RC),980voltages,
11220 simultaneous physical pairs and26functional contexts retained;7466
unsaved current histories explicitly unknown, no complete KCL equation/pass.
Frozen v1 electrical/20ns stimulus/nonsave solver lines/resources unchanged;
new V2 adapter reuses the exact frozen voltage/function reducer and only adds
truthful partial-current/KCL coverage metadata.16inputs each;15old inputs
verified unchanged. One focused test passed0.298s after correcting shared-list
alias in in-memory generator validation (serialized config/recipe unchanged).
ThreeAST and scoped whitespace checks; no real result read or remote action.
Trace-count scaling from parent-reported incomplete FFv1 gives1.611888GiB
for20ns, not a phase-activity/SS guarantee;2GiB guard unchanged.
FF recipe2b6aff3cf08ad0e052a5311da7acfe38da7f302615e2a8c9b3e23100c7a2c8e4;
SS recipe5b01396275e00b895bd7618ab3c4e537e52cb13af089e3bfba3d02172df924d0.
Parent owns V2 registration/submission. V1 failed raw retained, SSv1 not started.
Local v1 review-entry draft remains unregistered/not executed; real result
review waits for parent notification and must honor V2 unknown-current scope.
No further report/candidate expansion, circuit edit, OA/PDK/shared log mutation,
old-source/raw overwrite, extra queue, resource increase, commit or push.

V2 minimal README added at parent request only. Links/local whitespace checked;
no registered input, recipe, analyzer, test receipt or manifest changed.
No remote query/result analysis/new circuit preparation; wait for parent
collection notification. Parent owns FFv2 registration and serial dispatch.

## Optional exact-equivalent fast source analysis, local preparation only

Parent reports FFv2 native complete20ns/30059 accepted steps/239.49s/
356433920B peakRSS/about1.379GB output, current analysis still running. Do
not read/stop/restart it; SSv2 stays in parent queue. Own only new
standard_cell_storage_fastanalysis_v1/ for a Python2-compatible prebound
reducer, source-bound analysis-only wrapper/recipe, one equivalence test and
minimal provenance/README. All frozen v1/v2, shared management/log and raw
sources unchanged. No remote operations/registration/submission.

Prebind terminal node names and persistent statistics state, remove repeated
per-pair normalization/function/dictionary construction, preserve every native
point, floating operation/order, limit/window/functional/peak/energy result.
Compare old/new fields and emitted waves exactly on the same small synthetic
native fixture once; no benchmark claim on the real run. Retain256MiB analysis
and32MiB collection. Bind only completed FFv2 managed recipe351d0c4ca4e27bd33dccbe0057e92e1f2146e5f4ba2ca5619983749217407596.
The runtime adapter must refuse activation unless source analysis actually
ended limit_exceeded/wall_time_limit; no synthetic simulation state and no
native simulation. Otherwise leave package unused as a standby checkpoint.

Fast analysis-only FF standby frozen: sar8audit-ctrl-storage-ff-v2-fastanalysis-v1,
recipe fileSHA ae15453f4ad766aa33364ab21109513283dd71cc6c19701b5fe0e6452ead4bcc,
8inputs/2302047B; source351d0c4c...07596. Prebound reducer8d73ae91...c57f7;
all native point/threshold/window/arithmetic/tie policies unchanged. Same6point
full980V/89I/11220pair/26context synthetic input gave exactly equal all reducer
and functional fields, columns, binary and gzip bytes; canonical1889a191...58c70
(0.502s). Additional explicit-source-activation test0.199s passed: exact source
metadata binding, missing-state allowed only by explicit flag, no fake states,
running/success/wrong recipe rejected, nonzero parent-stop terminal accepted.
FourAST/inputSHA/local link/whitespace checks passed. No real raw read/speedup
claim, remote query, child kill, registration or submission. Source logs copied
whole, raw unchanged;256MiB/1200s/32MiB collection,128MiB newanalysis cap.
Latest parent reports identity-checked FF oldanalysis SIGTERM/failed-15; this
session did not perform it. FF runtime flag allow_analysis_not_started=false.
New SSv2q1 source is separate and requires exact future binding.

New parent direction: SSv2q1 is the actual queued/submitted native source,
managed3bd20be455b023474fcf80be74819b95c7fe8c7d0cb6a35db77e76486071a9f8.
Prepared separate8input SS analysis-only binding/config, fileSHA
421ecdfa05c33e1b905a7dc0c600c524f57fd4f4b1e75c7580652756b35285f4,
2301986B; allow_analysis_not_started=true, native PASS/footer required first.
This capability already has focused source-binding/no-fake-state test. No
SS source success claimed from local evidence. Old SSv2 queue_timeout is not
used. All FF8 frozen runtime inputs unchanged; new SS8 checked/AST/doclinks,
no new test broadening or remote actions. Parent owns both dispatch decisions.

## Documentation status headers only, after parent native update

Parent reports SSv2q1 native complete225.959s/354189312B peakRSS/1424264047B
output/zero-error footer/no CMI, and FFfast registered/running under managed
3a52e63451d7563e5938829b9df8efd6a6b27b4d66ca8064333ea72e2f536f40.
Only edit status headers/links in standard_cell_migration.md and READMEs of
standard_cell_full_v1, standard_cell_storage_v2 and fastanalysis_v1. Preserve
historical descriptions but clearly mark initial no-candidate/no-run statements
as history; v1=7555I output-limit failure, current v2=89I, native completed,
analysis results pending parent collection. No frozen runtime/config/recipe/
manifest or actual result read/change, no remote calls or qualification claim.

Four documentation headers/links updated only. Current generated candidate,
historical v1 output failure/SSv1 not started, current v2(89I), actual SSq1
source and pending fastanalysis results are explicit. All four MD files are
outside six frozen recipe input sets; local links/whitespace checked. No
registered input/result/remote state/qualification change.

## Collected FF storage result: local dual-corner report, SS pending

Parent authorizes local review of completed FFfast3a52e634...536f40,8files/
23313357B. Own review_standard_cell_storage_v2.py and storage_v2/results/
only, plus later small joint-voltage export preparation in a distinct owned
control directory. Preserve all registered inputs/receipts/raw, shared/sibling
work and PDK/OA; no remote queries, new simulation or full-ADC expansion.

First verify receipt/canonical managed source+analysis binding/frozen input
hashes/native source logs and lossless30060point gzip. Report502phase holds,
extra Q patterns/reset overlaps, actual signed input delays, all11220physical
pairs with literal>0 and diagnostic>1mV counts, source/target/replica/conditioner
instance provenance, and independent source work with fixture-only scope.
Plot original native functional waves, worst-event/reset-overlap zoom and
stress class comparison. All980raw voltages are NOT in the135-column returned
wave: MM64 same-time D/S/G remain unknown until targeted native export, never
subtract independent node extrema. MM45 first logged microvolt alarm occurs
about0.990003ns, not necessarilyt=0 or the full-history maximum. No blanket
library reliability/failure conclusion. SS stays pending until parent collection.

After report, prepare a separate small source-bound analysis-only stream export
for MM64 D/S/G/B, actualU19 CK/D/RST/RN/Q and internal clock nodes, original
native peak/repeated-event windows plus full-history joint stress/duration.
No recomputation of11220pairs, no fake simulation, <=256MiB/32MiB. Parent
reviews once/dispatches; this session only local preparation. No commits/push.

FF/SS local report complete at standard_cell_storage_v2/results/README.md.
Verified all collected bytes/canonical managed/source inputs/native logs/gzip
SHA and native time rows:FF30060,SS31020. Both26contexts/502holds/152expected
transitions all measured; no extra/missingQ pattern or reset-overlap glitch.
Actual delays FF7.738721..22.704087ps,SS16.494812..46.781751ps.
FF7596/11220strict pairs,7348>1mV diagnostic,99>100mV;SS0pairs.
FFworstMM64 VDS1.105788039958454V@5.031257327444921ns, actualCK
fall5.006050234860574ns, D/RST low/Qhigh. Target maps toXREF.XSTORE6;
D/G/S exact values unknown in135returnedV, explicitB0, never combined separate
node extrema. MM45first log0.990003ns rounded1uV, fullhistoryVGS1.038641961V
near1.007445556ns; not aDC alarm or sole whole-run severity. Native CMIF Ftrue,
SSfalse. VVDDnet20ns FF3.711878pJ/185.593882uW,SS2.212026pJ/110.601285uW
fixture-only, not ADCpower. All actual1870MOS origin classes mapped; test
conditioners distinguished from full candidate, repeated pairs not mechanisms.
All6figures visually inspected; numericcorner/supply/temp footers included;
SS zoom phase-contract/clock-direction handling corrected. No current/KCL
coverage inflation, blanket library conclusion or full-ADC qualification.

Minimal joint export ready: sar8audit-ctrl-mm64-joint-ff-v1, recipeSHA
96e4fa162cc806b70a9ef5d40078adbb4d7692476d0d0e1142ec7382e3e9b59b;
11inputs/2318315B, originalFFv2 source351d...07596. Reuses unchanged
fast parser/source binding;12voltage nodes+B0, six MM64 pairs, all20ns joint
statistics/duration and exact original peak; only requested original windows
exported toCSV +single managedresultJSON. No11220pair rerun/new simulation.
One3point synthetic/strict crossing check passed, source/input SHA/AST/docs
checked. Parent owns one managed analysis dispatch. This session no remote
commands, originaldata/registered-input edits, commits or push.

## Joint MM64 source recovered: one short section and one figure

Parent authorized local read of completed sar8audit-ctrl-mm64-joint-ff-v1,
5files/10789529B, source rawSHA/six-pair statistics matched. Own only the
existing results/FF joint snapshot/short Markdown/one4.98..6.05ns figure and
small report-generator hooks to preserve the appended result. No frozen
package, waveform/raw/receipt, circuit or remote changes. Verify source proof
and exact CSV D-S; show CK/clkb/G, D/S, signedVDS versus0.99, andQ on original
time axis. Use bracketed linear duration, not first-last native span. Explain
near1ns negative-state holding and simultaneous values, retaining current/
region/unique-mechanism uncertainty. No new frameworks, tests or simulations.

Joint supplement complete: existing dual-corner README now states exact
same-time nodes recovered and includes one short section/one figure; standalone
FF note uses local relative links. Parent visually reviewed the figure. Exact
peak D0.988246124V/S-0.117541916V/G0.000332838V gives VDS1.105788040V;
bracketed linear over-limit interval5.021254939..6.011584995ns (~0.990330056ns).
All six pair statistics/source raw SHA matched. Current/region/unique mechanism
remain unknown. No further scripts, simulation, circuit, OA or shared edits.
