# Sampling fixture preparation

Status: parent rejected the large load-shell draft for remote use. Large files
are preserved unchanged. Parent then authorized the compact direct-clock-path
construction; compact_v2 is locally generated and tested, not Spectre compiled.
Remote operation remains unauthorized.

## Goal

Freeze a reviewable specification and construct two local SS-hot startup
diagnostic fixtures from immutable existing devices. Separate observed behavior
from causal hypotheses and unassigned limits. No new simulation is authorized.

## Ownership and dependencies

This session owns only `verification/sar8_module_audit/sampling/`, including
the plan/spec/review, local builder/tests, two decks, shared extracted fixture,
SHA manifest and load/boundary inventory. Parent coordination is
`plan/2026-10-25-sar8-module-audit/plan.md`; shared logs belong to the parent.
All other files, including current candidates, generators, PDK, OA, Obsidian,
independent ten-bit experiments, historical results and raw waves, are read-only.
Other sessions share this checkout. Existing dirty files remain untouched.

## Work

1. Bind existing seed and rx2 TT candidate files, extraction boundaries and
   evidence by SHA256. Freeze all retained device parameters.
2. Specify startup prehistory independently from the absolute steady-state
   waveform schedule. Preserve the acquisition window and closing edge.
3. Define measurements and null budgets, including first-frame handling when
   no physical sample-opening event occurred.
4. Build two local SS-hot diagnostic decks with common formal sample opening
   at101ns and closing at141ns, using physical precharge and no forced charge.
5. Inventory all loads at cuts. Preserve native controller/reference devices
   as a load shell if a smaller extraction cannot preserve nonlinear fanout.
   Cut comparator clock output drivers before attaching an ideal reset source.
6. Explicitly label high-DC plus short-low preparation as a modified control:
   a pure high-DC case has no101ns opening edge. Do not claim original-failure
   reproduction or strict Bootstrap-only causality for a common-edge fixture.

## Verification and policy

Parse the JSON, verify every source file SHA256, verify named subcircuit ports
and normalized source-block SHA256, and check existing manifest DUT identities.
Check that required unknown budgets remain null and startup is never silently
accepted as a normal sample. Test device identity, native cut drivers and
preserved fanout, single-source deck delta, matching formal edge schedules,
source impedances/models, and rejection of deliberate malformed fixtures.
Run scoped `git diff --check`. Mark all decks not Spectre compiled.
Validation is bounded, local and read-only outside this subtree. No remote
operation, new simulation, source-circuit/OA/PDK edit, cleanup, commit or push. Parent
reviews these artifacts before any future managed simulation is prepared.

## Local construction checkpoint

Retained2506 primitives/1831MOS with original parameters and source connections.
Only two native CMP_CLK output drivers were removed before exposing reset port.
Actual SAMPLE_INT/SEQ_SAMPLE/PRESET/COMP_P/COMP_N fanout is preserved via the
physical control/reference load shell. Removed final-driver gate loading on its
upstream internal node is explicitly inventoried, so controller equivalence is
not claimed. Both decks differ only in VSAMPLE prehistory; high-DC control has
a100ps low plateau before the common101ns opening and is not a zero-precharge
or original first-frame reproduction. No Cboot initial condition is applied.

Fourteen local structural/negative tests pass. Source SHA, generated artifacts,
load inventory and deterministic builder replay checked; no simulator invoked.

## Parent correction: compact proposal only

Stop extending or dispatching the2506-device shell. Preserve its files and SHA.
Own new `compact_proposal.json` and `compact_proposal.md` only for this checkpoint.
Select Bootstrap P/N, XSEQ.XB final physical buffer, full CDAC, reference final
MOS stages plus native gate-resistor segments, N4 reset comparator, receiver
buffers and their immediate combinational fanout. Exclude token/register/async
loop. Count source primitives and hash mappings/parameters without exporting
another geometry inventory. No new netlist, recipe, simulation or remote read.
Clock input replay and dropped DATA/RAW fanout remain explicit limitations.

## Parent authorization: compact clock-path construction

Retain actual XSAMPLE, XIDLE.XA/XB and full XSEQ, because SAMPLE_MATCH is a
direct SAMPLE_INT path independent of ACTIVE. Close direct SAMPLE_INT gate
fanout with only the original immediate gate units; enumerate their removed
output loading rather than expanding the bit/token/register loop. No QUAL
replay is needed in this variant. Parent permits local `compact_builder.py`,
`test_compact_builder.py` and artifacts only under `compact_v2/`. Preserve the
old builder/decks/manifest/inventory bytes and previous proposal as history.
Use Q128 from the independent reference oracle to validate static driver preset.
Keep short-low/long-low names, original external source waveform after101ns,
and actual-edge measurements pending. No remote/recipe/commit authorization.

Local compact_v2 checkpoint:591 source primitives/237MOS, including38 direct
clock-path devices and40MOS in20 original immediate SAMPLE_INT inverter loads.
Twelve critical direct-node terminal sets are identical to source. Omitted
inverter-output and RAW/DATA loading is declared, not called transient-equivalent.
Independent reference oracle reset events yieldQ128 and correct P/N presets.
Thirteen local tests and deterministic artifact checks pass. Five generated
files total364146 bytes; no simulator, recipe, remote operation or commit.

## Parent approval: local stream packaging

compact_v2 is accepted as a short-low/long-low diagnostic, not proof of original
integrated sample-edge equivalence. Own new package_stream.py, review_stream.py,
test_stream_package.py and stream_package/ only within this subtree. Reuse the
existing loaded_remote.py and loaded-candidate stream.cpp byte-for-byte; shared
sources remain read-only. Generate flat-node mapping/pairs/selected/events/
products, measurement-only save additions, and suggested recipe parameters.
No shared recipe, remote submission, simulator, commit or new framework.
All237MOS six terminal pairs and actual clock crossings must be covered.
Keep preclose separate from141.8ns; missing opening/closing events stay unknown.
Analysis budget<=256MiB, collection<=32MiB. Parent reviews before dispatch.

Packaging complete:1422 MOS-terminal records/581 unique node pairs,293 compact
signals,7 native event channels and6 native V*I products. Reused stream.cpp and
loaded_remote.py SHA checked without edits. Two suggestions list all inputs for
sar8audit-sample-v2-short/long but no shared recipe is created. Nine package/
measurement tests and deterministic replay pass. Binary bound18823056bytes plus
4MiB reserve fits32MiB. Native new-run RSS/compile/runtime remain unmeasured.

## Parent-directed collected-result diagnosis

Parent registered and completed sar8audit-sample-v2-short/long. Their managed
collected directories are read-only; both receipts and all collected file SHA
were locally verified in bounded reads (13,854,191 and13,831,448bytes). Frozen
compact_v2/stream_package inputs must not change. Own a new result_review/
subdirectory and review_results.py for bounded local metrics and scientific
plots. Inspect both histories before attributing a defect to original circuit
or extraction. No remote query, rerun, recipe, circuit fix, commit or deletion.

Collected review complete: both0/1422 stress failures. Short history has an
actual2.155711ns low interval but P Cboot recovers only~0.179V before reopening,
G−VIN remains~−0.013V and P acquisition fails. Long low DC starts naturally
precharged~0.810V; preclose0.000895mV/held0.279027mV. No common supply/port/
preset defect demonstrated. This does not establish a minimum finite low time.
results.json and one inspected8-panel scientific figure saved in result_review/.
Frozen managed fixture/test/mapping/stream SHA and port order were rechecked;
no input changes, remote operations or reruns. Parent reviews the next proposal.

## Parent authorization: finite external low history

Own new finite_history.py, test_finite_history.py and finite_history/ artifacts.
Prepare2/10/40ns external low plateaus from the same high-DC short-case source,
moving only its first falling edge. Plateau means fall-end to101ns rise-start;
retain100ps edges,100.2-100.3ns input reversal,101/141ns formal edges and all
frozen DUT/measurement files. Reference existing frozen files by SHA, no edits.
Write exact diffs and recipe suggestions locally only. Actual SEQ low interval
remains null until measured; low-DC equilibrium is not a finite-duration point.
No remote, shared recipe, registration, simulation, commit or push.

Finite-history local preparation complete: initial falling edges98.9–99.0,
90.9–91.0 and60.9–61.0ns give external2/10/40ns plateaus before101ns. All
variants differ by one VSAMPLE line only; formal tail and input reversal are
identical. Six local tests and deterministic checks pass. SHA manifest, exact
diffs and sar8audit-sample-v2-low2/low10/low40 suggestions saved for parent review.

## Parent-directed finite-result review

Parent completed and collected all three finite-history runs. Inputs stay frozen.
Own review_finite_results.py and new finite_results/ report/JSON/figure only.
Process one case at a time with memory-mapped compact waves; each collected
set is<32MiB. Check native low duration, same initial DC and input hashes, all
Bootstrap acquisition-phase nodes and both main branch currents. Distinguish
the0.1ns finite control and low-DC equilibrium reference. Do not infer minimum
precharge time or whole-ADC repair; no remote operation or new run.

Finite-result review complete: all three initial DCs exactly match the checked
short reference. Actual SEQ low4.059936/12.060844/42.061762ns; held errors
800.336675/701.130927/.302817mV. All0/1422stress failures.40ns passes the existing
static diagnostic, not a minimum-time requirement.2/10/40 sampled errors improve
but adding0.1ns makes strict monotonicity false. One inspected8-row figure and
source-backed JSON/report are in finite_results/. No frozen input changes/reruns.

## Parent authorization: cold local controls

Own new prepare_cold_controls.py, test_cold_controls.py and cold_controls/.
Copy frozen low40 and frozen long low-DC decks into new local variants, changing
only simulatorOptions temp125 to-40. Preserve all source/model/supply/device/
load/timing lines and reused measurement SHA. Supply SS/.81V/TT passives is
unchanged. Parent suggestions use sar8audit-sample-v2-low40cold/longcold. No
remote action, shared recipe, registration, run, sizing change or commit.

Cold preparation complete: low40cold/longcold each differ from their respective
frozen hot source only by temp125->-40. Five local tests, source/common hashes,
exact diffs and deterministic checks pass. No remote/native action by this task.

## Resumed cold result review

User canceled the former two-hour limit through the parent. Parent explicitly
authorized local review of collected low40cold/longcold and the corresponding
hot controls. Own review_cold_results.py and cold_results/ only; every prepared
input remains frozen. Verify receipts, native temperatures, actual clock edges,
precharge and acquisition-phase signals/currents. Keep preclose and net turnoff
separate. Save a brief report/JSON/inspected figure. No new run, circuit/shared
file edit, commit or experiment preparation.

Cold review complete: native -40 C logs and all frozen/collected SHA checked.
Finite40 preclose/held13.693390/12.210887mV; low-DC equilibrium .054976/.306053mV.
Actual windows37.841021/37.837578ns. Acquisition-phase CTRL is low and G-VIN
positive in both; finite recovery leaves about40mV less pump drive. All four
hot/cold controls have0/1422 stress failures. Figure inspected; brief review,
JSON and plot saved under cold_results/. No new run or frozen-input edit.

## Parent authorization: normal-period finite cold control

Parent reviewed the cold plot and authorized local preparation only after the
report. Own prepare_normal_period.py, test_normal_period.py and normal_period/.
Check the existing loaded candidate's actual VSAMPLE contract before choosing
the first falling edge.10MS/s gives100ns period; nominal40ns high/60ns low
includes100ps transitions. Preserve formal101/141ns edges, all devices/loads,
input PWL, SS/.81V/-40C/TT-passives and reused measurement files. Freeze a new
low60cold deck with exact diff/SHA against low40cold and a suggested managed
recipe, not a shared recipe or remote submission. Actual SEQ low remains null
until measured. DC equilibrium must not be called normal-cycle recovery.
Use minimal structural/negative tests and deterministic replay; no commit.

Normal-period preparation complete: original frozen loaded rx2 pulse has41ns
first fall,100ps edges,59.9ns low plateau and100ns period. Half-level intervals
are60ns low/40ns high. New low60cold changes only the first fall of low40cold
from60.9-61ns to41-41.1ns, retaining the101/141ns formal edges and all other
inputs. This is59.9ns flat low, not60ns flat low. Five focused structural and
negative tests pass; source/common SHA, exact diff and recipe reuse checked.
Files are in normal_period/ with status local_prepared_not_registered_or_run.
Actual SEQ timing and pass/fail remain unknown; no remote action or commit.

## Parent-directed normal-period result review

Parent completed and collected sar8audit-sample-v2-low60cold. Own a new
review_normal_period_results.py and normal_period_results/ report/JSON/figure.
Freeze normal_period/, cold_results/ and all prior inputs/outputs. Inspect only
already collected compact evidence; verify every receipt/file SHA and frozen
input, native temperature/settings/completion,1422 terminal-pair screening and
actual SEQ events. Compare40cold/60cold/DCcold with sequential memmap reads,
Cboot recovery and branch currents. Do not infer Ron from dynamic currents or
normal closed-loop/POR qualification from fixed-reference/reset evidence.
Preserve existing dirty ownership, including parent runner/shared plans and
user Obsidian/10bit files. No remote action, new fixture/run or circuit edit,
commit or push. Parent owns the shared log and reviews the next experiment.

Normal-period review complete: new run16files/13,883,806bytes, all SHA/no-skips,
native-40C/X-CX/4threads/zero-error footer and effective tolerances verified.
Independent native stress reconstruction237MOS/1422records/581pairs gives0
failures for all three cold histories. Finite40/60 checked DC states exactly
match. New actual SEQ low62.159006ns, acquisition37.841017ns, preclose+.119668mV,
held+.361995mV, net+.242327mV. At100ns P Cboot.799508V versus.757103V; M2/M8
recovery currents .865374/.865273uA versus4.098379/4.097854uA.110ns PG-VIN
.796323V and main sum43.205886uA; not a DC Ron comparison. JSON, brief report
and inspected8-panel comparison are in normal_period_results/. Prior frozen
cold_results/normal_period/ hashes unchanged. Next suggestion is real reference
history interface replay with N4 held reset, subject to parent review. No run,
shared edit, circuit modification or commit by this session.

Parent accepted the normal-period review. Report wording now explicitly credits
low60cold as the parent's newly submitted/run case; only this local review
started no further simulation. Existing FF boundary exports are not accepted
as SS replay history; suitable corner/source evidence awaits parent selection.
Numbers, JSON, plot, inputs and scripts remain frozen. No expanded sampling
test or new preparation is authorized at this checkpoint.

## Parent authorization: independent local power-on diagnostic draft

Parent now authorizes one separate local preparation item: reuse the SS-cold
compact DUT, fixed reference and N4-reset load, without waiting for FF replay.
Own prepare_power_on.py, review_power_on.py, test_power_on.py and power_on/ only.
Existing source decks/results remain frozen; no MOS, architecture, shared file,
remote operation, registration, simulation, commit or push. Dirty user/parent
and independent10bit paths remain read-only.

Draft pair: use the existing low SAMPLE prelude until101ns; both cases share
an explicitly hypothetical ramp of analog inputs/reference and high Q128
boundary commands,31.1-41.1ns. Compare only VDD DC-final versus a0-to-final
ramp over that same10ns interval. This separates natural power-on storage
from DC precharge without powered analog inputs at t=0. Keep all source
waveforms from101ns onward,100ps formal edges and101/141,201/241ns windows.
These ramp times/order and the external low-clock wait are diagnostic bench
assumptions, not existing POR or approved startup specifications. Final SS
supply is.81V; operating contract remains.81-.99V, not a reduced supply range.

Extend observation to260ns for two formal frames; reuse native parser without
changes, freeze a new mapping with260ns stop and correct fixed0-100/100-200ns
energy bins. It has no native energy coverage after200ns. Bound collection
to40MiB and analysis to256MiB; no managed recipe before parent reviews ramp,
sequencing, clock-prelude assumption and budgets. Validate exact single VDD
delta, all reused SHA, unchanged DUT/formal timing, no forced initial state,
and synthetic measurement cases for absent/multiple/late events and source
motion. Provide executable draft decks and two-frame local review helper,
with numerical simulation outcomes left unknown.

Power-on draft complete: two Spectre decks differ only at VVDD. Shared analog/
Q128-boundary ramps and external clock-low prelude are explicitly hypothetical;
normal101/141 and201/241ns edges, final voltage contract and MOS stay unchanged.
New260ns mapping reuses native stress/events/stream bytes; energy only covers
0-100/100-200ns. Seven focused structural/negative measurement tests pass.
Draft files, exact diffs, SHA and pending dependencies are under power_on/;
two-frame local review helper preserves missing edges and fixed held times.
No recipe or remote/native execution was created. Real startup/POR results,
budget and valid-frame requirements remain unknown; parent reviews first.

## Parent acceptance:32MiB managed startup packaging

Parent accepted the diagnostic ramp/clock assumptions and260ns observation,
without freezing POR or first-valid-frame requirements. Own new
prepare_power_on_managed.py, power_on_analyze.py, unpack_power_on.py,
test_power_on_managed.py and power_on_managed_v1/ only, plus this local plan.
Keep power_on/ deck/mapping/manifest and all old stream/analyzer files frozen;
the former40MiB draft is superseded by a32MiB hard collection requirement.

Prepare two local managed YAML recipes for parent dispatch only. Reuse frozen
native reducer in a private work directory of each new run, stream-losslessly
gzip its existing20ps selected binary, verify compressed/raw SHA and gzip
roundtrip, preserve native point count and all-native stress/events. Keep
uncompressed generated wave and raw PSF remotely; publish only verified gzip
and complete small derived evidence. Do not add waveform decimation or change
the native reducer. Native energy still stops at200ns. Fail without a completed
delivery if full derived evidence plus root-file reserve exceeds32MiB.

Limits:4threads, simulation RSS<=1024MiB, analysis<=256MiB,260ns. Use31MiB
derived cap plus1MiB reserved for managed root logs/states, check actual root
size with completion headroom and require no skipped collection afterward.
No manager/policy edit or new simulation/registration by this session. Validate
bounded gzip roundtrip, corruption/hash/size rejection, source preservation,
recipe input hashes/path resolution and deterministic regeneration. Provide a
bounded local unpacker compatible with the frozen two-frame review helper.

Managed preparation complete: two local YAML recipes under
power_on_managed_v1/recipes/, frozen input hashes and new compression config
generated without registration. Wrapper reuses original native reducer in
private run work, retains raw generated data, gzip/SHA/CRC roundtrips the
unchanged20ps selected binary and preserves all-native stress/events/counts.
31MiB derived cap +1MiB root reserve enforces32MiB delivery budget; overflows
fail without dropping evidence. Native energy still ends at200ns. New local
unpacker verifies the collection/no-skips and both compressed/raw SHA before
producing a separate decode directory.10 focused packaging/corruption/budget/
workflow tests pass. Resource declarations remain4threads/1024MiB simulation/
256MiB analysis. Server runtime/peak RSS remain unmeasured. Original power_on
files, stream package/analyzer and completed sampling results unchanged;
no shared manager/policy edit, remote operation, commit or push.

## Parent-directed startup DC result review

Parent completed and collected sar8audit-sample-start-dc-sscold-v1. Own a new
power_on_results/dc_core/ subtree and review_startup_dc_results.py only for this
checkpoint. Use frozen unpack_power_on.py into a fresh decoded/ directory,
then frozen review_power_on.py for both frames. Verify receipt/no-skips, frozen
inputs, raw/compressed SHA, native settings/log and independent1422 terminal
records. Analyze with sequential memmap/1MiB reads and keep local RSS<=256MiB;
no full PSF read or remote operation. Preserve frozen power_on/packages/wrapper.
Report DC Cboot and actual events/preclose/held/net change without equating
no CMI or stress-screen pass with startup qualification. Ramp case is running
under parent ownership; no new case/preparation/commit/push. Parent owns log.

DC preliminary review complete:18files/16,540,954B, all receipt/input/compressed/
decoded SHA checked. Native35509points/9523compactpoints; independent0/1422
terminal failures. Cboot starts naturally .809999987V in both sides. First
preclose/held+.048685/+.303479mV; second-.187385/-.163703mV. Windows37.837578/
37.840904ns. Local measured peak working set55.004MiB. No pre101ns SEQ events.

## Parent-directed complete DC/ramp comparison

Parent has now collected the ramp counterpart (18files/17,932,208B,no skipped)
and requests complete existing-pair quantification, no new experiment package.
Extend ownership to power_on_results/ramp_core/, power_on_results/comparison/
and review_startup_pair_results.py. The newly authored result-review script
may be reused with explicit run/output arguments; frozen original unpack,
two-frame helper, wrapper/decks/packages remain unchanged. Compare each frame
across the two histories; first input-.81V and second0V are different, so do
not assign their within-run differences entirely to startup. Sequential reads,
local peak<=256MiB, complete SHA/native log/stress checks and inspected result
plot required. No remote command, new run, circuit/shared edit, commit or push.

Complete pair review: ramp18files/17,932,208B SHA/no-skips and22,461,600B decoded
SHA verified. Native37152points/9550compact, independent0/1422 stress failures.
Ramp first preclose/held+.287818/+.523542mV versus DC+.048685/+.303479mV;
same-frame differences+.239133/+.220062mV. Second ramp-.190135/-.166134mV
versus DC-.187385/-.163703mV, at a different0V input. Ramp t0 Cboot~0,
41.11ns.017099V,100.99ns.786028V and200.99ns.809824V (P). Early native SEQ
crossings36.1491/36.6171/36.7256ns occur atVDD.409-.456V below operating range,
not qualified clocks or proven valid-supply functional failures. All formal
windows observed. N top dominates the first-frame extra preclose error.
Three result figures inspected, report/JSON saved under power_on_results/
comparison/. Local plotting measured peak112.973MiB; scalar DC/ramp55.004/
54.551MiB. Frozen original packages/helpers unchanged, decoded copies ignored
from Git. No source PSF/remote operation, new case, circuit/shared edit or commit.

## Accepted module checkpoint

Parent reviewed and accepted the fixed-Q128/N4-reset SS-cold DC/ramp diagnostic
as complete, without POR, baseline or integrated-ADC qualification. Inputs,
wrappers and results are frozen. Own only a short checkpoint.md plus this plan
entry for closeout. No additional startup/PVT sweep, POR logic or new experiment.
Actual reference switching/load integration depends on reference/control work
and source selection by the parent; no direct FF-to-SS history replay.
