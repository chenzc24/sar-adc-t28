# Comparator module audit: local fixture preparation

Status: D2, kickback v2, hold2 and actual-pulse TT reviewed. Feedback v1 output-
limit failure and v2 export-cap failure remain preserved. Parent completed the
separate v2 analysis-only recovery; local source/receipt verification and three
timing figures/report are delivered. No new baseline adopted. Parent:
`plan/2026-10-25-sar8-module-audit/plan.md`.

Next paired opposite-history TT fixtures are locally prepared/frozen and tested;
not Spectre compiled or remotely submitted by this session.

Parent subsequently ran both opposite-history cases. Their individual and
paired local result reviews/figures are delivered; no new simulation here.

## Goal

Freeze the existing N4/rx2 circuit and its actual loads by path and SHA256;
specify separate deterministic receiver, charge/kickback, and historical
mismatch-boundary fixtures. Preserve statistical accuracy as a future acceptance
gate. Parent subsequently authorized a local builder, two short TT/SS-cold
decks, provenance manifests, a boundary review and synthetic structural tests.
No remote dispatch, simulator execution or candidate adoption is authorized.

## Ownership and dirty-state boundary

This session owns only `verification/sar8_module_audit/comparator/`, including:

- `verification/sar8_module_audit/comparator/plan.md`
- `verification/sar8_module_audit/comparator/fixture_spec.json`
- `verification/sar8_module_audit/comparator/review.md`
- Local builder/test sources, generated D-family decks and their manifests,
  and the extraction boundary review, all inside this same exclusive subtree.

The shared checkout is `exp/cdac-flat8-device`, ahead 30 at start. Existing
Obsidian changes, independent ten-bit work, rx1/rx2 210ns artifacts, the parent
plan/log and other module subtrees are read-only. Remote OA ownership: none.
No shared source, generator, analyzer, circuit, PDK or historical result edits.

## Read-only dependencies

- Project `AGENTS.md`, README, management status/design registry and parent plan.
- Frozen `sar8fix-loaded-both-rx2-end210-sscold` input deck, DUT, mapping and
  original manifest; TT/rx1 evidence is comparison-only.
- Existing comparator, receiver, timing, output MOM and full-CDAC hierarchy.
- Existing loaded analysis and its documented native/compact provenance.
- Historical core-comparator mismatch deck, search stimulus, case/summary and
  raw small metadata/parameter records; no copied foundry model contents.
- Current eight-bit specification and StrongARM initial budgets.

## Work sequence

1. Read the parent coordination plan and inspect exact source ports/dependencies.
2. Record byte-level file hashes plus explicit subcircuit hash convention.
3. Write fixture inputs, controlled differences, measurements, failure conditions
   and unresolved budgets; keep the three evidence classes separate.
4. Validate JSON parsing, source hashes and referenced subcircuit/load identities.
5. Review the scoped diff and report artifacts to the parent for review.

## Validation and restrictions

Only bounded local Python generation and read-only checks are permitted. Hashing and
JSON validation do not simulate or reanalyze raw waveforms. Unknown setup/hold,
receiver voltage envelope, input-CM range and accuracy/yield allocations remain
explicitly unallocated. Existing 0.25-LSB screens are not additive module budgets.
Two local fixture decks may now be generated from the frozen rx2 leaf cells.
No simulation, remote command, OA/PDK operation, deletion, cross-thread message,
shared log update, management recipe, commit or push. Parent owns run admission.
All generated cases must say `not Spectre compiled`; local tests prove source
and connection structure only, not electrical reset or decision performance.

## Superseded D-family prototype boundary

Retain the N4 comparator, rx2 receiver, complete original timing/validity logic,
eight native data-register/bit cells, and their original controller fanout.
Use the original three output/clock MOMs. Introduce a declared external start
cut at the timing CLOCK_SET boundary, preserving its physical SR input load;
the original producer is routed to an observation net, never tied to the source.
The physical clock buffer and comparator/update-driven reset feedback remain.
Remove the analog ADC chain and reference-word circuit; list all lost loads at
the corresponding interface boundaries and block any whole-ADC timing claim.
Check PR/NR/DATA/PHI_W native-terminal fanout against the original full DUT.
Use ideal differential inputs only for this deterministic module experiment.
The long reset spacing is diagnostic stimulus, not a new allocated bit budget.

Before emitting immutable case files, test the builder in memory: hashes, source
cell equality, single changed control boundary, fanout, ports, source contention,
sign history and corner-only differences. Re-running may verify identical
generated artifacts, but must refuse to overwrite different existing files.

Deadline: stop extending this task by 2026-10-26 01:09 Asia/Shanghai, preserve
the local checkpoint and do not dispatch a new run at or after that time.

## Superseded tightened-boundary checkpoint

Parent subsequently required the smaller N4/rx2 + RAW/DEC/DATA cone, with at
most the original eight-bit register attachment and no full async conversion
chain. The first in-memory prototype retains 783 MOS versus 1833 in the ADC,
including complete timing and token/bit sequencing. It therefore exceeds the
tightened boundary. No generated deck or manifest directory has been emitted.
At that checkpoint its write path was disabled. Parent then approved replacing
the prototype with the smaller externally clocked diagnostic described below.

## Parent-approved smaller boundary

Parent approved replacing the 783-MOS in-memory prototype. Retain N4/rx2,
RAW/RAW_D/DEC/DATA, necessary write-forward logic, native input-load attachments
and the eight unchanged sar8p_bit/register cells. Remove token advancement,
ACTIVE aggregation, quiet/SR/clock feedback and the X025 clock driver. Drive
CMP_CLK, token states, write guard and register reset with explicit independent
diagnostic sources. Enumerate removed native instances and clock-node terminals.
Keep the three original MOMs and verify the native fanout of COMP_P/N, PR/NR,
DATA and PHI_W. This is an ideal-clock diagnostic, not equivalent whole-ADC
asynchronous timing. Generate only local deterministic_v2 artifacts; no remote
operations, managed recipe, statistical batch or commit are authorized.

## Commit policy

Do not stage, commit or push. Deliver scoped local files and check results;
wait for the parent to review before any next phase.

## Initial specification validation result

Completed JSON parsing; all 17 source byte hashes, five subcircuit hashes/port
lists, 19 controller dependency names, four top instance/load lines and 19
measurement-node identities match the frozen files. The historical deck's
LF-normalized hash also matches its case record. No new netlist, simulation,
remote command, circuit change or statistical batch was produced. Output is
limited to the three owned files. Parent retains shared-log/commit decisions.

## Smaller D-family validation result

Generated deterministic_v2/cells.scs, tt.scs, sscold.scs, boundary_audit.json and
manifest.json locally. The fixture contains 467 MOS: N4 11, receiver/forward
logic 88, eight unchanged bit/register attachments 368. Six protected native
fanouts match exactly; two removed CMP_CLK driver drain terminals are explicit.
No full token/ACTIVE/quiet/SR chain, CDAC, Bootstrap or reference-word circuit.
Twelve local structural tests pass. Generated files and builder/spec identity
are SHA-bound; no Spectre compile, simulation, managed recipe or remote action.
The parent owns further run admission and shared-log updates.

## Managed-input packaging authorization

Parent accepted the frozen v2 TT/SS decks and 12 structural tests. Add a separate
local package using those immutable decks/cells unchanged, all-MOS six-pair
mapping, selected/native event/product configuration and a small streaming
adapter. Reuse read-only loaded_remote.py and the frozen loaded stream.cpp;
correct its historical two100ns energy bins to the full260ns fixture interval.
Native crossings/checkpoints must sample DATA at actual PHI_W and D0 after
write, with explicit input polarity and precharge observations. Keep compact
collection below32MiB. Parent alone creates shared recipes and submits runs.
No frozen output replacement, remote operation, new simulation or commit.

Packaging checkpoint: generated mapping/pairs/selected/events/products/checkpoint
inputs and an adapted frozen stream under managed_inputs/d2. It covers2802
MOS-pair records and integrates module VDD over the full260ns. The Python2-style
adapter delegates native reduction to unchanged loaded_remote.py, then reads
bounded native checkpoints/crossings. Five new local tests plus12 structure tests
pass; two recipe-input proposals are provided for parent-only registration.
No C++ compilation, Python2 runtime execution or Spectre/remote test has occurred.

## Parent-run result review authorization

The parent registered, simulated, analyzed and collected sar8audit-comp-d2-tt
and sar8audit-comp-d2-sscold. This session may now read their complete local
receipts/compact derived outputs/native logs and write review script, JSON,
concise report and one separated-row timing figure inside this subtree only.
Verify all six actual PHI_W writes, source register clock binding, polarity,
native reset90 crossings, DATA-before-write observations, all2802 terminal
screens and the full260ns VDD integral. Keep frozen v2/managed inputs and
remote_reduce.py unchanged. No remote queries, resubmissions or commit.
Do not infer a characterized storage aperture/setuphold guarantee from a half-
VDD clock crossing. Actual CX reltol is1e-7; logs disable multithreading.
Local processing budget <=256MiB; raw multi-GB files stay remote.

## Completed native result review

Both collected receipts and frozen managed inputs verified. TT100514 and
SS-cold97630 native points match accepted steps+1 and full260ns stop. Independent
stress remapping confirms0/2802 failed records per case. Each has six actual
write rises and falls, DATA/D0 sequence1,1,0,1,0,0; the original storage CK pins
are directly PHI_W. Internal CKB sampling aperture remains unmeasured.
Reported full-window module VDD energy: TT2.189794657pJ, SS1.276131829pJ.
The separated-row figure was viewed and its legend layout corrected locally.

Parent-requested transient check: TT first PR/NR=00 interval0.570–1.383ns after
clock; SS has no half-VDD PR/NR=00 interval. RAW/RAW_D/DEC/PHI_W each rise six
times per case, with no duplicate/reset accepted write. The207psTT/295psSS
positive-input DATA lead is the observed forward-path delay difference; it is
not a qualified setup margin. Report and JSON preserve these distinctions.
Three targeted reset-ready tests pass in addition to17 existing local tests.
Input bundles, reducer, recipes and all parent files remain untouched.

## Independent reference-current package review

Parent authorizes a read-only review of reference_current_analyze.py,
prepare_current_analysis.py, build_first_fixture.py current/KCL mapping and the
generated measurement manifests. Record exact SHA/time and any concurrent
changes; inspect 275 terminal currents, five node incidence/sign conventions,
native sparse/GROUP/final-point handling, charge integration, bounded outputs
and replay-to-save naming. Run only bounded local synthetic probes, with all
temporary files confined to this comparator subtree. Save the independent
review under comparator/reviews/reference_current_20261026.md.

Reference/control source files, generated packages, shared plans/logs and all
existing comparator circuit/results stay read-only. No remote operation, new
simulation, delegation, commit or push. Unfinished source-package or physical
validation remains explicitly pending; this is diagnostic credibility review,
not comparator optimization or circuit qualification.

## Physical CDAC input-load diagnostic

Parent redirects this session to comparator design and authorizes one minimal
TT package under generated/kickback_v1, plus its local builder, bounded analyzer
and focused tests. Reuse frozen D2 N4/rx2 and its actual receiver/register fanout;
add the eighteen original flat-CDAC MOM instances with unchanged parameters and
256 units per side. Hold their bottom plates at declared ideal fixed rails,
excluding unsettled reference drivers and reference switching from this target.

Use matched evaluating and always-reset arms in one native time grid. Keep the
D2 0.9-V/27-C environment, six 20/60/100/140/180/220-ns clock starts, 0.1-ns edges,
12-ns high phases, 260-ns stop, input common mode0.45V and +/-1.7578125mV residual
sign history. Initialize through finite10-ohm controlled conductances, completely
disconnect at18.1/58.1/.../218.1ns, before each compare edge. This is ideal charge
initialization, not a sampler/Bootstrap implementation or an ADC clock change.

Measure actual initialized/pre-compare residuals, top differential/common-mode
excursions, evaluating-minus-reset changes, raw resolution, receiver/write
polarity/timing, input-gate and capacitor charge, top-node KCL, native MOS-pair
screens and original logs. Preserve explicit unknown kickback/accuracy budgets;
do not turn the0.25-LSB diagnostic input into a module acceptance allocation.

Only local generation and synthetic validation are authorized. Parent performs
one package check and alone registers/submits managed work. No remote, new PVT,
noise/MC, sizing, source D2 changes, shared edits, commit or push. No extra review
layer: deliver executable inputs, measurement configuration and concise README.

Local delivery: build_kickback_fixture.py, kickback_analyze.py, test_kickback.py
and generated/kickback_v1. Exact D2 cells reused; two matched467-MOS arms plus
36 original MOM wrappers.45 currents, four11-term top-node KCL equations and
228 selected N4/rx2 terminal-pair screens. Native output has all timestamps;
no simulated result or new accuracy allocation is claimed. Nine structural and
synthetic tests pass, including the actual generated configuration and managed
result-last/CMI-preservation path. Re-running the builder is byte-identical.
Package inputs total100,768 bytes; parent recipe proposal remains local-only.

## Kickback v1 native failure and minimal save-case correction

Parent registered/submitted v1 with recipe hash
5c3eee55600347ee6100a5dd2115f747cc4aa43a5ec490f51032f03bce65b769 and600s queue
timeout. Managed execution stopped at150.268s/2,148,028,470B, peak RSS340,070,400B;
native FAIL and no zero-error footer. Preserve this run and its immutable inputs.

The collected original log identifies case-invalid save names (lines149--171),
an allpub fallback (248),463 voltage/9 current outputs (281--282), and file-size
errors at221.657ns (294--300). AHDL compiled successfully; the initial matrix/
DC/Verilog-A warning (232--243) is separate and remains unresolved. Accepted-step
count is unavailable after abort; do not claim that timestep refinement is absent.

Parent authorizes a local v2 proposal under generated/kickback_v2 and a small
save-fix builder/test. Restore exact netlist case for the same36 voltage and45
current requests, changing no device, initialization, clock, endpoint, tolerance,
analyzer, output or memory budget. Keep metadata normalization after reading PSF.
Verify every corrected name against the flattened fixture and top-level deck,
and require every requested native TRACE in analysis. Parent alone submits.

V2 delivered locally: prepare_kickback_savefix.py resolves all81 actual-case
symbols; four focused tests pass, including rejection of v1's names and an
uppercase native/GROUP/sparse end-to-end measurement probe. Only test.scs saves
and the matching measurement.json hash differ; the other four packaged inputs
are byte-identical. The four-file original collection22831B verifies by SHA256.
V2 input size remains100,768B and output budget remains2048MiB; queue timeout600s
matches parent registration. No remote or new simulation was performed here.

## Kickback v2 parent-run result analysis

Parent completed native simulation/analysis and collected ten files11,855,029B.
This session may verify the local receipt, nested gzip/native-row hashes,
native36V/45I acceptance,260-ns PASS, warnings and228-pair scope; write a concise
report, numeric phase summary and separated phase timing figure only under
results/kickback_v2. Distinguish pre-write, high-clock, fall and post-reset phases
using original native samples, not only the analyzer's20--32.1ns aggregate window.
Recommend one necessary single-variable follow-up without preparing or submitting
it. Frozen v2 input package, all other modules, shared files and remote remain
read-only; no new tests, PVT/MC, simulations, commits or pushes are authorized.

## Approved single-variable retained-charge follow-up

Parent accepted the phase report and authorizes a new local package only:
generated/kickback_hold2_v1, with prepare_kickback_hold2.py and focused
single-variable checks. Omit only the44--58.1ns CINIT acquisition pulse in both
arms, keeping v2 hardware, all other sources, clock windows/endpoints, reference
rails, numerical settings, analyzer and resource budgets unchanged. The first
two targets are both+0.25LSB. Second-cycle measurement metadata must refer to the
actual first18.1ns disconnection, not invent another release at58.1ns; the next
actual acquisition is84ns. These are measurement descriptions, not extra circuit
variables. No new baseline or remote submission is authorized.

The phase figure has been corrected to include complete native input-gate and
COMP_P/N peaks. Keep v2 frozen and preserve its seven native warnings. Deliver
only the updated figure/report and exact new proposal paths to the parent.

Completed local checkpoint: results/kickback_v2 report/summary/timing figure verify
the full10-file receipt,100668 native points and36V/45I accepted saves. Corrected
figure shows the complete62.9uA gate-current and1.017V output peaks. Six expected
DATA/D0 writes are correct at1.608--1.616ns; pre-write differential disturbance
peaks0.285mV, reset recovery0.348mV. Common-mode motion already reaches about
-8.24mV at first write, before the clock falls. All228 selected pair screens are
below their limits; seven native warnings remain visible and no whole-ADC pass
is inferred.

Delivered prepare_kickback_hold2.py, test_kickback_hold2.py and
generated/kickback_hold2_v1/recipe_proposal.json. Three focused checks pass. Only
the CINIT pulse and corresponding input/hash/actual-history measurement metadata
change; the four hardware/analyzer payload files remain byte-identical to v2.
New package input size101348B. V2 remains frozen; no remote command, new run,
commit, push or other module/shared-file edit was made by this session.

## Hold2 parent-run comparison

Parent completed native/analysis for sar8audit-comp-hold2-tt-v1, registered recipe
0ed949bb4dbf5cf206e928d2d27642530e91806146ef6647882d727e992d9737. This session
may compare its collected second pre_compare differential/common-mode residuals,
accepted DATA/D0 and write delay with kickback_v2, then add a report/summary and
native timing comparison figure under results/kickback_hold2_v1. Keep32.1--60ns
first reset/hold distinct from60--72.1ns second comparison and72.1--84ns second
reset/hold. Read the partial numerical result now; only consume waveforms after
complete native hash/receipt checks. No input edits, experiments, new tests,
scan, remote command, shared-file change, commit or push are authorized.

Hold2 result checkpoint: full10-file11,907,280B receipt, native gzip/uncompressed
hashes,100644 points/100643 steps and260ns endpoint verified. The second held
input is+1.757606762mV with-0.205738uV target residue and449.700415mV CM;
v2 reinitializes to+1.757817581mV/450.003183mV. Second DATA/D0 remains1; delay
1.608462730ns versus1.608375326ns, an interpolated0.0874ps difference without a
numerical-convergence speed claim. Both runs have six expected writes and no
reset-arm accepted writes;228 selected screens show zero exceedances, while all
seven native warnings remain retained.

Delivered review_kickback_hold2.py and results/kickback_hold2_v1 report.md,
summary.json and hold2_comparison.png. Figure viewed; it uses each run's native
timestamps without cross-run interpolation and shows the omitted initialization
separately from comparison2. Explicit40ns compare spacing/27.9ns reset-low interval
prevents a true-SAR short-bit conclusion. Only next suggestion is the actual-bit-
cadence retained-input comparison, not prepared or submitted. Frozen v2/hold2
packages and other modules/shared files remain unchanged.

## Existing actual-bit timing replay preparation

Parent authorizes one local TT actual-interval package in
generated/kickback_actual_tt_v1, with builder and focused source/measurement
checks. Use the frozen N4/rx2 TT managed native event table, not a future timing
budget. Enumerate adjacent bits within each recorded frame; select the shortest
rise-to-rise pair intact, retaining its corresponding two high widths and low
interval. Report the distinct minimum-low pair without mixing their extrema.

Keep the existing hold2 hardware, physical MOMs, initialization, six original
input targets, external sources and260ns endpoint. Replace only the first two
clock pulses with that measured interval sequence (translated to the first
diagnostic clock edge); later +/-0.25LSB cases remain long-interval controls.
The0.1ns ideal PWL ramps remain the existing block-clock boundary: native0.5VDD
interval replay is not a full native-voltage/slew replay. No parent ADC sample
window or closing edge is changed. Fixed bottom plates exclude real CDAC update
coupling, and the clock feedback loop stays cut.

Source shortest pair is TT frame1 bit6->5, at about147.671/151.627ns. Its large
source residues differ from the +/-0.25LSB diagnostic; forced early reset/no
write is a possible conditional result, not automatically an async-ADC defect.
Adapt only the new packaged analyzer to explicit fall-start metadata, removing
its old12ns late-D0 assumption. Record resolution before reset, accepted-write
phase and absent/late writes without a vacuous empty-list success. Keep all
native currents/KCL/selected screens and resource budgets. Do not alter frozen
v2/hold2 packages, other modules, shared files, MOS/PDK parameters or clocks in
the actual ADC. No remote command, simulation, parameter sweep, commit or push.

Actual-interval delivery: prepare_kickback_actual_timing.py,
test_kickback_actual_timing.py and generated/kickback_actual_tt_v1. Native source
recipe ba8432cd1e6678c1c00f7888982b8511e29424b34c7981159be511fa3a8d3557
and event SHA verified. Minimum observed TT rise interval3.955842938ns uses the
intact second-frame bit6->5 pair: highs1.179356732/1.212701389ns and low2.776486207ns.
The different minimum-low pair is explicit, never mixed. Only first two clock
pulses change; original0.1ns ideal ramps remain a stated boundary. Source inputs
were about-362/-138mV; forced replay at+0.25LSB can legitimately yield no write,
not automatic evidence of an async-ADC failure. The analyzer now explicitly
classifies missing/late/unassigned writes and samples D0 before the true fall.
Three targeted checks pass. The104736B package, frozen hardware, unchanged
budgets and source/interpretation limits are documented; parent alone dispatches.

Parent clarification retained in the package README: core scope is fixed-measured-
pulse short-reset/receiver diagnosis. If the first small-input decision/write is
interrupted by the borrowed short high phase, the second pre-compare residue is
an interrupted-evaluation recovery trajectory, not a valid prior SAR decision.
Check first-cycle completion fields before describing any two-decision result;
no claim of two completed real conversions follows from this clock replay.

## Actual TT outcome and native completion-feedback proposal

Parent completed/collected actual TT:10 files10,970,767B,93208 native points.
Authorize local receipt/native-log/gzip verification, hold2 comparison plot and
concise result report under results/kickback_actual_tt_v1, plus one proposed
minimal native-completion/reset fixture description in that directory. Inspect
the frozen sar8p_timing/sar8i_ctrl/clock, receiver and PHI_U loads read-only.
No new package, simulation, sweep, sizing change, remote command, shared edit,
commit or push. First two fixed pulses have no resolution/write before reset;
second pre-compare state follows interrupted evaluation, not a valid SAR decision.
The proposed fixture must restore actual DATA/DEC/write/update/clock feedback,
name the real output-load/PHI_U receiver boundary and avoid an invented DONE/timer.

Actual TT result checkpoint: complete10-file10,970,767B receipt and nested native
waveform hashes verified;93208 rows/93207 accepted steps,260ns endpoint and36V/45I
accepted saves match. First two forced pulses have no pre-reset resolution or
write; pre-reset output differences peak0.343036/0.390758V. Remaining four long
controls write correctly; no unassigned writes. Second pre-compare differential
is1.756938433mV (-0.874067uV target residue), common mode449.582184mV, explicitly
after an interrupted first evaluation. Seven native warnings and selected228
pair checks with zero exceedances remain scoped; no full-circuit pass claimed.

Delivered review_kickback_actual.py, results/kickback_actual_tt_v1/report.md,
summary.json, actual_vs_hold2.png and feedback_fixture_plan.md. Figure inspected
for complete native peaks. Next proposal restores the original783-MOS N4/full-
controller core, actual clock driver, output MOM and8x5fF loads, plus a same-source
PHI_U reference-receiver/capture load island. Its130-MOS first-cell group is only
a lower bound; downstream fanout closure is mandatory before packaging, not an
invented913-MOS complete fixture. No new package, run, sizing/sweep, remote
operation, shared edit, commit or push is performed by this session.

Local validation: review script executed successfully and AST parsed as UTF-8;
all24 payload hashes across frozen kickback v1/v2/hold2/actual proposals match.
Scoped diff whitespace check is clean. No additional electrical test is claimed.

## Authorized native-feedback TT package

Parent now authorizes local construction of generated/feedback_tt_v1 plus its
builder, streaming analyzer and focused synthetic checks, all within this
comparator subtree. Restore the unmodified783-MOS N4/full-controller core,
three original output/clock MOMs, eight5fF output loads, original physical CDAC
hold load and real PHI_U/D reference receive/capture fanout. Keep native request,
capture-clock/ACK and token feedback rather than inventing DONE or fixed pulses.

Use a finite physical cut after complete BBM cells and the complete first
receiving inverter stages in each reference driver. Their drains evolve through
their native devices; downstream output fanout is explicitly zero at this
conditional boundary, never substituted by arbitrary capacitors or clamped
ideal logic. Inventory every retained and removed terminal and disclose that
post-cut Miller loading/reference settling is not represented. Reference capture
reset pins use the declared SAMPLE_INT startup guard instead of retaining the
whole reference-preset sequencer. No claim of whole-ADC startup handshaking.

First case only TT0.9V27C, held+0.25LSB, one native8-token sequence. Preserve
original cells, dimensions, delays and numerical settings. Analyze eight token-
indexed writes/updates/resets, real recovery time and every retained MOS terminal
pair using bounded streaming; save selected native timing/current columns and
enforce29MiB derived output inside the32MiB collection allowance. Parent owns
managed registration/serial submission; no remote/OA/PDK, shared file changes,
new approval round, commit or push. Old packages/results remain immutable.

Local feedback delivery checkpoint: build_feedback_fixture.py, feedback_analyze.py,
test_feedback.py and generated/feedback_tt_v1. The783-MOS core and all named
PHI_U/D/CODE/capture/BBM/H/L terminal fanouts match the frozen native source.
674 receive/capture/BBM/front MOS close the load island for1457 total.32 physical
cut nodes retain their two native inverter output drains and explicitly remove
two downstream gates each, with no post-cut capacitance or clamp. Source-sized
first receivers and their D/S dynamics remain; zero external output fanout and
SAMPLE_INT-conditioned capture resets are declared limits, not full ADC parity.

Input payloads total1,734,134B. Native saves are711 voltages/23 currents;8742 MOS
pair records reduce to2699 unique streamed node pairs, while57 native timing/
current/KCL columns are compressed for return. Derived29MiB plus2MiB native
log,512KiB state/logStatus metadata and512KiB receipt reserve bound32MiB return.
Raw simulator2048MiB and single-thread/RSS/wall budgets are separate.100ns is
only the observation endpoint; all eight clocks arise from native feedback.

Four focused tests pass: complete source/core/load/cut identity and save names;
synthetic managed analysis with eight token-indexed writes/updates/resets and
terminal stress; missing token3 write is an explicit failure; truncated native
END is rejected. The synthetic success does not prove electrical operation.
AST checks and original24 payload hashes pass. No remote, shared edit, OA,
simulation, candidate adoption, commit or push. Parent alone performs managed
serial registration/submission. Proposal SHA256:
1c5039cf926b5a8f23712695c33406a8aaa0ed534c818506274aa9e3bed5a8eb.

Parent accepted the finite cut/scope and requires simulation_rss_mib=1024,
not1536. Correct only the new draft generator/recipe resource declaration and
add a local1GiB ceiling guard; regenerate the draft metadata and verify resource
consistency/new hashes. Do not repeat the passed structure suite, expand memory,
or submit remotely. Preserve a real memory failure if the managed run reaches
the1GiB limit. The preceding proposal hash is superseded by this correction.

Resource-only correction verified: recipe simulation_rss_mib1024/threads1;
analysis256MiB and raw-output2048MiB budgets stay unchanged. All seven packaged
simulation/analysis payload hashes are byte-identical to the four-test-verified
delivery. Only generator, recipe and manifest builder-provenance change; no
structure/test suite rerun. Package now confirmed frozen for parent submission.
Current proposal SHA256:
f91d2132d664eacb0f50e1bb0b14f970f7c61b659a49d94ce34db00aeb86e6b8.
Current manifest SHA256:
16d41b0ffd2ebae80e7d8dce566ed5fbb1157050c2fb0343b9ca7b7355f10dc6.

## Feedback v1 output-limit failure; measurement-only v2

Parent collected four small files20,761B from the immutable v1 failure. Receipt
hashes verified locally. Native accepted711V/23I with no allpub fallback; at
38.0381ns SPECTRE-27 file-size limit precedes7082/USIMUWI-20006. Managed status
limit_exceeded/output_size_limit,264.55s, peakRSS319,078,400B; native PASS and
zero-error footer false despite native exit0. This is not memory exhaustion
evidence. Preserve v1 and do not resubmit it.

Parent authorizes only generated/feedback_tt_v2 and prepare_feedback_save_v2.py
plus one focused measurement/synthetic test. Copy1457-MOS hardware, input
initialization/SAMPLE/clock-feedback sources,100ns, options, tolerances and all
resource limits unchanged. Select124 voltages/23 original currents: preserve
the57 returned timing/current/KCL columns and full comparator/receiver/direct
timing chain165MOS/990 pair screens. Native CMI/model checks stay enabled on
all unchanged devices. Explicitly defer1292MOS/7752 pair screens; no global
zero/full8742-completion claim in v2 output. No allpub, solver relaxation,
budget/RSS expansion, circuit change, remote operation, commit or push.

First-order ASCII-name/field cost scaled from the2GiB-at38.0381ns failure gives
about1008MiB at100ns,1511MiB with1.5x native-point-density allowance. Failure log
lacks accepted-step footer; the density assumption is not guaranteed. Retain
the actual2048MiB hard output gate and29MiB derived/32MiB collection budget.
One focused local test must verify measurement-only diffs, exact required saves,
unchanged57 columns and protocol, scope-aware stress output and native log counts.
Parent alone registers/submits the new immutable v2.

V2 local delivery: prepare_feedback_save_v2.py, generated/feedback_tt_v2 and
test_feedback_save_v2.py. Exactly one focused test passed, covering byte-identical
hardware/support and non-save deck content, original solver/resources,124V/23I
exact-case required saves, unchanged57 columns/protocol, eight synthetic token
writes/updates/resets,990 selected stress results with full-scope=null/false and
native save-count/footer guards. This is synthetic analysis validation, not
electrical completion. No old structure suite or remote test was repeated.

V2 seven inputs total285,712B. Global stress coverage remains incomplete:
165MOS/990 local waveform screens,1292MOS/7752 deferred; original full-device
CMI logging is untouched. AST/whitespace and all frozen v1/new v2 hashes match.
Current v2 proposal SHA256:
fb9dd7872f730634cfc467af7ddb95c56d78b46d4ced855a989f12b1ba3b2b0d.
V2 manifest SHA256:
0b34a72f40a328cb78df50b8ed3f8242d17286ab0384b1cb0cb67aaa32a15552.
Package confirmed frozen for parent managed serial submission. No circuit/PDK,
time/solver/budget change, OA/remote operation, shared edit, commit or push.

## Analysis-only recovery of completed feedback v2

Parent reports v2 simulation complete100ns/PASS/zero errors,561.37s with
316,985,344B peakRSS. Native log accepted156160 steps. Analysis failed at100.12s,
11272192B RSS because full57-column gzip exceeded29MiB; the collected partial
gzip is not a complete result. Preserve all frozen inputs and previous derived
files. No resimulation, raw recovery to this PC, circuit or solver changes.

Authorize only comparator/generated/feedback_v2_reduce_v1, its prepare/reducer
sources and one focused export-limit test. Bind exact completed managed v2
recipe d56adca4380107296e7bd8aebe5fadd39f419aa579e8a0235bc53284b2b5cb90,
all registered inputs, native simulation/log hashes and managed source provenance.
Reuse frozen reducer/config/support byte-identically. First pass computes all
native statistics/protocol/integrals/KCL/990 selected stress extrema while
discarding only waveform serialization. Second streaming pass exports57 columns
at a deterministic native-index stride plus original event brackets, extrema
and recovery witnesses. Verify both complete raw hashes/point counts match.

Export baseline at most20000 rows plus at most10000 witness times, binary cap
14MiB and total derived cap29MiB;32MiB managed analysis/collection allowance.
Publish full100ns export range, exact stride, included witness policy and native
vs export point counts so plots cannot imply every point is displayed. Full
8742-pair stress coverage remains incomplete. Test dense skipped-point spikes
against unchanged full-native reducer results and source-file hashes. Parent
alone runs managed analysis-only; no shared/remote edit, commit or push here.

Analysis-only delivery checkpoint: feedback_source_reduce.py,
prepare_feedback_source_analysis.py, test_feedback_source_reduce.py and
generated/feedback_v2_reduce_v1. Five inputs245,720B. Frozen v2 reducer, support
and measurement are byte-identical. Source binding verifies actual normalized
managed recipe (not the pre-registration proposal), all eight registered source
inputs, native log/state hashes and source_provenance.json. The failed partial
gzip is never consumed; only its collection checksum was verified.

One focused dense synthetic test passes: all protocol/events/current integrals/
KCL/990 stress metrics and full-native serialized SHA match the unchanged
reducer; a spike omitted by the baseline stride is retained as a witness; full
source directory hashes are unchanged. Initial exact-decimal endpoint assertion
was corrected for native floating representation, without algorithm changes.
Actual source baseline stride8; maximum30000 rows/57 columns=13,680,000 raw bytes.
Export metadata includes0--100ns range, stride, native/export counts and mandatory
figure label. Two complete raw SHA/END/point-count checks guard consistency.

AST/owned whitespace and frozen/new input hashes verified. Recovery proposal SHA:
dfdc0b0295d2a1456010d41894e3741bfa0a39957ed408051f38168defa26efd.
Manifest SHA:
fdbc942dfc0854ef8f8d9684c738341cc889a27851581259a4aab5157a76a7d8.
Source-binding SHA:
70661312fd5268fa87f84ddc4cf5a0b6fad80df7361d430d559000b880587a32.
Confirmed frozen for parent managed analyze-only submission. No source-result,
input/circuit/solver, shared file, remote operation, simulation, commit or push.

## Completed feedback-source result review

Parent collected7files7,290,320B for completed analysis-only recovery. This
session may verify hashes/size, source binding, full156161-point measurement
record and19924-row sampled native export, then write a concise report/summary
and2--3 side-by-side figures under results/feedback_v2_reduce1 with a local
review_feedback_source.py. Compare against frozen forced-short diagnostic only
with explicit differences in control/load boundaries; this is not a strict
single-variable speed comparison. No new simulation, source/package edits,
heavy raw reanalysis, other-module/shared edit, commit or push.

Use actual native half-VDD event brackets, distinguish precompare CLK<=0.1VDD
snapshots and the90%-logic-reset-ready diagnostic from TOP charge recovery.
Never label within-comparison/turnoff motion as acquisition settling or final
ADC error. All numerical intervals come from full-native result records; plots
use stride8 native export plus475 witnesses, clearly labeled. No full8742 stress,
noise/accuracy or full ADC code claim. Recommend one most necessary next check.

Completed local review: review_feedback_source.py and results/feedback_v2_reduce1
report.md, summary.json, feedback_vs_forced.png, bit_write_reset.png and
top_kickback_recovery.png. Seven-file7,290,320B receipt, full gzip/row SHA, source
binding and19924-row stride8+475-witness export verified against156161 native
measurement points. Three figures viewed and layout checked; tiny sub-ps
interval differences are not enlarged into physical speed claims.

Eight native writes/updates/resets and token7->0 all pass. CLK-rise to write
1.586--1.598ns; write to RESET0.503--0.504ns; CLK-fall to internal reset90
0.590--0.591ns; reset90 to next half-rise2.186--2.187ns for first seven decisions.
These are event observations, not qualified setup/hold/reset margins. First
reset90 input residue is-79.0uV but next precompare-0.807uV/449.599mV CM, proving
internal precharge readiness and input charge recovery are distinct. PHI_U and
QUIET retain RC delays, not independent DFF/analog-input completion detectors.
The report calls turnoff motion kickback/recovery, not acquisition or ADC error.

990 selected stress checks show0 exceedances; full8742 remains incomplete.
Fixture VDD energy10.912755pJ/100ns is not whole-ADC power. Startup, fixed bottom
rails, temporary initialization,32 unloaded reference-front cut nodes and lack
of noise/MC/PVT/PEX stay explicit. Recommend only opposite strong-decision
history followed by small opposite residual with controlled charge/native
feedback. No new package or simulation prepared. All three frozen feedback
packages, AST and owned text whitespace verified; no shared edit, commit/push
or remote action by this session.

## Authorized paired opposite-history charge fixtures

Parent authorizes local scheme and two small TT packages only under
generated/history_charge_v1/{negative_to_positive,positive_to_negative}, plus
their builder, bounded analyzer and focused local check. All old packages are
read-only. No new baseline, OA/circuit-device/RC changes, simulation/remote,
shared edit, commit/push or dispatch; standard-cell FF work has queue priority.

Keep1457MOS/N4/full native feedback/receive chain, physical MOM parameters,
0.9V27C/100ns/settings/resources, original SAMPLE_INT20--20.1ns closing edge and
initializer18--18.1ns release. Change input history through initial residual
sign and one equal/opposite step at the existing255-unit bit bottom plates,
leaving the one-unit dummy rails unchanged. First residual +/-8LSB=56.25mV
(32x small residual; inputs421.875/478.125mV around450mV). Nominal second residual
is opposite0.25LSB=1.7578125mV. Cu cancels:alpha=255/256, required per-side step
+/-29.1176470588mV, nominal common-mode step0. No Cu value or gate-C correction
is invented; actual unnormalized second precompare Vdiff/VCM must be reported.

One TB Verilog-A source only observes first PHI_U and subsequent falling CLK
0.1VDD. It delays900ps, slews bottom rails200ps then holds them constant; no
TOP/clock/token contribution. This schedules charge movement after observed
reset, not a new ADC sampling window. Measured reset-ready/stimulus/next-compare
order must be checked, not assumed. Initializer is never re-enabled; TOP remains
connected only to native MOM/input gate and zero-conductance init branch.

Cases differ only HSIGN/input-history metadata. Retain990 selected stress screens
and full native CMI scope; add3 bottom/trigger probe voltages and3 export columns.
All-native metrics with bounded two-pass60-column export (max30000 rows,
14,400,000 raw bytes <14MiB gzip cap),29MiB derived/32MiB collection. Adapt only
history polarity/D-register expectations and stimulus phase/target measurements.
Reuse full-native protocol logic and source math with explicit conditional
load/stimulus boundaries. No direct physical/offset/noise qualification claimed.

Local interface clarification before freezing: keep original cells.scs bytes
unchanged and add history_interface.scs, a copied audit_feedback body whose only
interface change exposes CMP_CLK/PHI_U as passive observation ports. Bind these
to top-level CMP_CLK/PHI_U for the TB instead of relying on cross-hierarchy node
connection syntax. Update only the corresponding save/measurement node aliases;
verify flattened native devices/loads are identical under that two-node map.
No native device/RC/driver/body instance or electrical fanout is added/removed.

Paired-history delivery checkpoint: prepare_feedback_history.py,
history_charge.va, history_analyze.py, test_feedback_history.py and
generated/history_charge_v1/fixture_scheme.md with the two case packages.
Negative->positive11 inputs315050B; symmetric11 inputs315055B. Both127V/23I,
60 returned columns,990 selected screens, all other resource/settings unchanged.
Original cells/initializer/native support/protocol reducer bytes remain exact.
Copied test wrapper body only exports two passive observation ports; full
flattened native device/load equivalence under the alias map is verified.

One focused local test passes for both histories plus deliberately early charge
motion: nominal charge/CM algebra and device parameters match; only HSIGN differs
in the electrical decks; expected and actual precompare signs, D histories,
all-native phase measurements and two-pass bounded export are exercised. The
early-step case has correct stored bits but assessment_valid=false, proving
invalid stimulus timing is not silently accepted. A deliberately3uV actual input
offset remains unnormalized in reported TOP/DM/CM. These are synthetic tests,
not electrical verification or Verilog-A compiler success.

VA event/contribution syntax audited using the loaded veriloga language skill;
only bottom rails/isolated marker receive contributions. AST, whitespace,
reproducible generation and all old/new input hashes checked. No broad scan,
actual simulation, shared/remote edit, baseline change, commit or push.
Frozen negative->positive proposal SHA256:
bbf073e58e5e788a3a46442c901a03ea7f14a7ee98a9daadab210a2259b8d136.
Frozen positive->negative proposal SHA256:
5190f68e71ae263547a8f1328c3c48b0f63dbbdd496a3dceb0be4d732c031d76.
Parent alone schedules after the standard-cell FF first run.

Parent metadata correction before admission: replace inherited Held+0.25LSB
test_conditions.input with each signed8LSB->opposite nominal0.25LSB charge
history, explicitly no actual-TOP normalization. Set summary_signals to the new
top-level observation ports. Only generator/recipe/manifest provenance and the
existing focused metadata assertions change; all11 executable/measurement input
hashes must remain byte-identical. Parent will run the focused test once; no
repeat of the full local test or remote submission here.

Metadata-only correction completed: signed histories now explicit in input,
actual TOP remains unnormalized, summary_signals=topp/topn/cmp_clk/phi_u/bot_p/
bot_n and all names match saved ports. Both11-input payload lists/hashes are
unchanged. Generator/test AST and resource/summary consistency checked; parent
owns the one focused-test rerun. Final corrected proposal SHA256 values:
negative->positive094e11d27af64a6f26d26e7486831dd25cd664a5304448ce6f25e677ffab9500;
positive->negative6b316d876b40ee2cc2508008d64b74789a13b1dadbbd6447f2172674d42290b1.
These supersede the earlier proposal hashes; packages confirmed frozen, no
remote submission performed here.

## Negative-to-positive recovered history review

Parent collected the negative->positive run:10files7,365,284B;154820 native points,
protocol/history-assessment valid,8 writes. Authorize local receipt/native/export
hash verification, review_history_charge.py and concise figures/report/summary
under results/history_charge_v1/negative_to_positive. Prepare the review schema
for the symmetric result, but do not query/poll it; parent owns its analysis and
will send the collected evidence. No fixture/input edits, tests or simulations.

Use actual unnormalized precompare TOP/DM/CM and measured first-motion/plateau
events. Distinguish the~199.792uV nominal-target realization difference from a
comparator offset measurement. No Cu/gate-C or history-memory attribution can be
extracted from these endpoints alone; phase current curves are sampled display
only, not new all-native window charge integration. Keep selected990 versus
incomplete8742 stress fields exact and raw-source/old packages read-only.

First-history review delivered: review_history_charge.py and
results/history_charge_v1/negative_to_positive/report.md, summary.json,
first_second_decisions.png and charge_and_recovery.png. Ten-file7,365,284B receipt,
native log/config/source hashes and complete60-column gzip/row SHA verified.
Metrics154820 native points; display19773 sampled rows/482 witness times. Both
figures viewed, including a corrected plateau-only zoom so the input-target gap
is visible. No repeated tests, raw reanalysis or remote operation performed.

First actual input-56.250246mV; second actual+1.558021mV/+0.221585LSB at449.591069mV
CM, write delay1.604954ns, phase/protocol valid with8 writes. Selected990 stress
exceedances0; full8742 incomplete/null. Nominal target realization difference is
-199.792uV, already-195.472uV at stimulus plateau, then-4.320uV additional drift
over1.637700ns. The difference exists on physical TOP before comparison, not a
measured offset. No gate-C ratio or history-only speed attribution is extracted.
Post-plateau display ends at the nativeCLK<=0.1VDD witness and explicitly allows
coupling from the next clock ramp. Frozen paired input hashes/AST/text checks
pass; the script can merge both cases only when parent supplies collected data.

## Authorized symmetric-pair result merge

Parent supplied positive->negative:10files7,359,206B;150636 native points and
phase/history/protocol true. Review both existing collected exports only, add a
concise paired report/summary and paired waveforms under results/history_charge_v1,
and update owned single-case report links. No new tests, simulations, remote
commands, frozen-input or raw mutations.

Separate a transparent voltage ledger: A=last EXPORTED original-native row with
both bit bottoms still450mV before first detected motion; B=full-native first
plateau witness; C=full-native second-precompare witness. Decompose total target
gap into A-initial-target, [(B-A)-nominal step], and C-B, retaining any drive-
realization remainder. A is not promised to be the last accepted native point;
publish its gap to first motion (~1.4ps), so endpoint-window bookkeeping is not
misrepresented as full-native phase integration or an extracted C/offset/memory.
Selected990 stress counts remain actual; full8742 coverage remains incomplete.

Paired merge complete: results/history_charge_v1/paired_report.md,
paired_summary.json, paired_second_decisions.png and paired_charge_components.png,
plus updated single-case reports/figures. Both10-file collections and complete
export row SHA verified. Negative->positive154820 native/19773 display points;
positive->negative150636/19238. Both history/protocol/phase valid,8 writes each,
selected990 stress exceedances0 and full8742 incomplete/null.

Actual second residuals+1.558020635/-1.558020336mV, CM449.591069/449.590950mV,
write delays1.604954/1.612582ns. No amplitude/sign normalization. Voltage ledger
negative->positive:+81.11 -276.58 -4.32=-199.792uV; reverse:-81.12 +276.59 +4.32
=+199.792uV. A is sampled native at24.878968/24.879531ns,1.433/1.493ps before
first detected motion. This endpoint selection is explicit, not a claimed last
raw point or a current-integral/C/offset/history-memory extraction. A-to-B actual
voltage transfers+57.731231/-57.731219mV include ongoing recovery; post-plateau
movement remains about+/-4.32uV, potentially including next-clock early coupling.

Paired waveforms and new symmetric-case figures viewed; plot labels moved out
of waveform regions and single-case save bounds expanded to retain labels.
Owned AST/whitespace and both frozen11-input bundles checked. No unit-test
rerun, simulation/remote command, raw/fixture mutation, shared edit, commit/push.
