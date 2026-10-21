# SAR8 transistor-level closure candidate

## Goal and boundary

User authorizes completing the current eight-bit ADC at transistor/device
level. Implement the missing reference-control and gate-drive logic, eliminate
internal behavioral logic, and map intentional internal passives to implementable
PDK devices. External supplies, references, analog input and SAMPLE remain
testbench/interface sources. Nominal functional integration is the target;
layout, full PVT/mismatch optimization and production qualification are separate.

Keep R3+B and its active 512-point experiment immutable. Do not stop/restart or
alter that task. Original Bootstrap, MOM, comparator and SAR topology/size
snapshots are read-only references. Existing comparator mismatch/FF limitations
must remain explicit. At most one newly owned APS4 process while existing jobs
continue; no wholesale large regression before small-cell validation.

## Dirty state and ownership

Start: exp/cdac-flat8-device, ahead20. User note edits/deletions, pasted images,
Rvision notes and untracked cdac10 sources remain read-only and unstaged.

Owned local paths:
- scripts/sar8_physical/
- config/sar8_physical.yaml
- netlist/sar8_physical/
- verification/sar8_physical/
- docs/sar8_physical.md and docs/figures/sar8_physical/
- This plan, one plan/log.md append, a narrow project_status entry after results
- Ignored output/sar8_physical/ for snapshots, decks, receipts and results

Remote owned library: SAR_ADC_T28 only. New schematic/symbol cells named
sar8p_*; sar_logic_8b_physical; sar_bootstrap_flat_8b_p;
sar_adc8_join_r4; tb_sar_adc8_join_r4; tb_sar8p_unit; tb_sar8p_passives.
Final concrete cell list must be recorded before creation; existing unowned
names or unsaved/locked targets are blockers for their mutation. PDK and all
existing R0..R3/B, sar8s_* and unrelated OA cells remain read-only.

## Method

Use Virtuoso and Spectre skill references, supported schematic readers/builders,
existing project CMOS primitive topology, native OA export and APS. Do not
invent SKILL APIs. Inspect actual CDFs for resistor/MOM devices and validate
dimensions through callbacks/readback rather than assuming parameter names.

Proposed minimal hardware: eight real word-storage bits, capture driven by a
delayed sample-rise/UPDATE-derived phase, fixed initial reference word selected
while sampling, per-bit break-before-make and matched buffered outputs driving
the retained 3x reference pass MOS. Read actual SAR trial bits; no input-voltage
oracle or behaviorally generated decisions. Use actual CMOS pulse/delay paths,
not timer/cross/transition for internal control. Preserve unchanged references
where practical and verify physical skew/settling under weighted gate loads.
Reuse the working register/token loop; no new fault FSM, EOC or output bank.

Map ideal delay/storage caps and Cboot to PDK MOM; choose PDK resistors or a
measured transistor delay implementation. Observation-only artificial loads
must be distinguished from intentional physical circuit capacitors. Do not
silently treat inherited ideal passives as completed PDK implementation.

## Steps and checks

1. Verify bridge t28_io health/CIW/technology and audit selected baseline by
   supported readers. Restore a disconnected local tunnel once if necessary.
2. Freeze actual interfaces and PDK mappings; write candidate cell inventory.
3. Implement and simulate passive/timing/loaded-bank units first. Check truth
   table, initialization, changing and unchanged words, non-overlap, output
   edges and terminal stress. Keep failed variants/results as diagnostics.
4. Build new native OA candidate with readback and Check&Save; export raw
   netlist; audit that internal control contains no behavioral electrical
   sources, and establish exact schematic/netlist correspondence.
5. Run bounded nominal integrated smoke, signed/endpoint transitions and
   original full 12-frame anomaly history as warranted. Each frame must have
   eight comparisons/writes/updates, correct mapping and stable final code;
   conversion <=60ns; CDAC precompare error <=0.25LSB relative to held input;
   no gross held error for constant input; no unexplained CMI/LTE relaxation.
   Check relevant analog and new driver MOS terminal voltages and power.
6. Document results, unresolved limits and figures with provenance; do not
   adopt R4 as qualified until implemented surfaces pass. Update plan/log,
   review scoped diffs and commit locally; no push without a new request.

Validation uses APS4/conservative/maxstep10ps (or stricter for focused units),
baseline effective tolerances and full saved points for inspected signals.
No speed-mode downgrade, solver-tolerance relaxation or PDK edits for a pass.
External observers may log behavior without driving DUT nodes.

## Completion criteria

Reviewable native OA and matching exported netlist for the implemented candidate,
measured module and integrated evidence, no internal ideal control placeholders,
and a clear inventory of remaining qualification work. If connection/resources
prevent integration, preserve completed in-scope work and report the precise
failed stage without claiming transistor closure.

## Preflight and concrete cell inventory

Bridge0.8.0 t28_io tunnel restored once; CIW and Spectre21.1 healthy, only CIW
window. Library path/tsmcN28 match. Read current R3, Bootstrap, CDAC, StrongARM
and SAR through supported readers; candidate names absent. Audit metadata is
under output/sar8_physical/. PDK resistor rupolym has PLUS/MINUS and ResCalc,
w/res sizing interface. MOM cfmom_2t uses existing legal geometry controls.

Before creation, owned cells are fixed to:
sar8p_inv, sar8p_nand2, sar8p_and2, sar8p_buf, sar8p_or2, sar8p_xor2,
sar8p_mux2, sar8p_sr, sar8p_dffr, sar8p_clkbuf,
sar8p_delay_quiet, sar8p_delay_valid, sar8p_delay_write, sar8p_delay_bbm,
sar8p_delay_restore, sar8p_delay_capture, sar8p_timing, sar8p_bitseq8,
sar8p_bit, sar_logic_8b_physical, sar8p_nonoverlap,
sar8p_refdrv_b0..b7, sar8p_refword, sar_bootstrap_flat_8b_p,
sar_adc8_join_r4, tb_sar8p_passives. Additional unit/integration benches listed
in the boundary will be concretely declared before their creation.

Candidate source keeps native CMOS controller primitives and token/register
loop, removes its unused BP request driver banks, and exposes actual CODE and
PHI_U to the new physical reference word capture. All intentional caps map to
integer MOM unit counts; 10kohm delay resistors map to sized PDK rupolym.
The unit is nominally5fF at Lfinger2.5um/Nfinger8/M1-M3 and must be measured.
Cboot uses200 units. No claim of identical original delay/capacitance is made.

Additional benches fixed before creation: tb_sar8p_unit (physical word driver
loaded by the existing real CDAC with externally fixed top-plate voltages) and
tb_sar_adc8_join_r4 (actual integrated native ADC). Passive CDF readback measured
the small MOM unit4.97494fF. The first resistor size-mode attempt recomputed to
5.83745kohm; explicitly repaired only the owned passive bench via CDF to legal
geometry w1um/l17.13um. Delay-resistor candidates now use that geometry; actual
resistance is checked instead of assuming an editable resistance value survived.

Owned candidate connectivity repair: first R4 Check&Save found unused exported
debug-only Q/CAP_CLK/PHI_W and Bootstrap CLKSB pins. Remove those unnecessary
ports, retain their internal nodes for hierarchical waveform saves. Explicitly
rebuild only the newly owned Bootstrap/controller/refword/R4 schematics and
symbols after comparing live connectivity to their own source receipts; preserve
before snapshots and completion receipts. No old R3 or shared cells are edited.
The passive AC run executed successfully; one misplaced lteratio option was
reported ignored and is moved to the tran statement before any fidelity test.

Regenerated owned child symbols moved pin coordinates; old R4 label stubs no
longer touch several child pins. Repair checks the same owned instance/master
set and permits only missing connections on those explicitly changed child
interfaces, with every surviving connection required to match its receipt.
Rebuilding the owned parent regenerates terminal-aware stubs and complete
readback, rather than hiding floating markers. The unit bench's VREFP/VREFN
source instance names also collide with their net names; rename only those
testbench sources before the final unit export.

R4 external interface is reduced to actual input/supply/reference/SAMPLE pins
and D7..D0. TOPP/TOPN, comparator outputs and clock remain internal observable
nodes, avoiding five debug-only unconnected output pins in the integration
bench. Rebuild only the owned R4 symbol/schematic and its owned TB afterward;
record each repair under a source-identity-specific snapshot directory.

First physical word unit completed:18/18 restored/captured words and all gate
polarities correct, no high/low threshold overlap or LTE. Nevertheless native
CMI occurs on an LSB reference PMOS at44.732ns; gate edges are only3..9ps and
have finite-driver overshoot. Preserve unit_word01 as a failed electrical
candidate. Add two series10kohm PDK gate resistors per output, each implemented
with2^bit parallel units to scale inversely with the weighted reference-gate
load. Rebuild only owned driver leaves, export a new immutable unit identity,
and remeasure edge/stress before integrated testing. This is a physical slew
experiment, not a simulator/limit change or a behavioral gate replacement.

The R-limited reference unit passes, but first integrated run exposes startup:
uninitialized word252 ->128 kicks TOPN to-161mV and trips comparator Vgd.
Replace the clocked SAMPLE initialization with real DFF asynchronous SAMPLE
reset. Invert only the stored MSB to obtain initial128 without a new reset net;
UPDATE still captures actual trial bits through its native delayed phase.
Remove the eight input muxes and SAMPLE clock-OR path. Declare integration
clock initialization before running: SAMPLE starts high (reset/acquisition),
then falls at41ns and repeats with unchanged100ns frame/fall times. First frame
is explicit startup observation, not silently deleted. A full high/low SAMPLE
cycle is required before valid conversion; arbitrary power-up/clock state is
not qualified. Keep the prior low-start failure and all analog-stress points.

Complete old-clocked integration also exposes a functional miss: real UPDATE
is207.9..208.6ps while the original loaded unit used1ns. The20fF RC capture
chain suppresses real pulses; Q stays128 and the register saturates255.
Replace that delay with UPDATE-falling-edge capture (one native inversion and
buffer). Measured CODE settles about100ps after UPDATE rises, leaving roughly
100ps setup before its fall at this nominal point. Keep asynchronous SAMPLE
reset. Tighten the unit to208ps UPDATE pulses and CODE changes80ps after the
UPDATE rising threshold. Qualify nominal timing only, not PVT margin.
After that unit, use one bounded4-frame integrated test: first+.123V explicit
startup observation, then-.8,+.8,-.8V. Preserve all frames/stress. Original
history12/full-code/FFT remain unrun for this candidate; avoid a long broad
regression before proving the new physical path.

The208ps falling-capture unit passes all18 words and16 pre/post-fall checks,
with no conservative gate overlap/CMI/LTE. Floating-top integrated load then
exposes a different stress at48.645ns: N-side bit6 bottom exceeds0.99V during
multi-bit handoff (CMI-2755/2751). Preserve that full4-frame run. Increase only
the two owned driver gate-resistor lengths from17.13um to85.65um (target5x R,
unchanged legal1um width/2^bit parallel count). Verify actualCDF/readback and
loaded unit, then repeat the same4-frame stimulus. Do not alter CDAC3x MOS,
VDD, voltage limits, solver, or omit failing startup data to obtain a pass.

PDK CDF correctly rejects an85.65um single stripe, clamping it to24.64um;
readback stops the loop at b0. Use its native five-Series-segments interface
with legal17.13um segment length instead, preserving the failed callback
snapshot. Confirm sumL/res and actual exported effective geometry before
simulation; never disable HardCons or bypass CDF limits.

Five-Series-segment unit passes:18 words,16 falling-edge checks,118..124ps
gate falls, peak0.92363V and no CMI/LTE/overlap. The same floating-top4-frame
run still reports negative-endpoint stress, so slew alone is not sufficient.
Exact old4-frame evidence at the first negative conversion: Q7 falls144.760322ns,
Q6 rises144.754840ns; N bit6 PMOS gate crosses0.6V at144.948280ns, but N bit7
NMOS gate crosses0.3V only144.970705ns. The22.425ps skew lets the lower-bit
handoff kick the still-floating MSB bottom to1.26178V (TOPN1.24340V).
Bounded correction: retain the measured gate-R and add two native buf cells
per bit between descending reference-capture clocks (bit7 first, then6..0).
This deliberately sequences the larger changed weight before its next lower
trial; no added FSM, ideal delay, or CDAC/pass-MOS change. All new parts stay
inside the owned refword cell. Save all seven derived clocks. Unit deadline:
actual LSB capture clock within1ns of UPDATE fall, old word before that fall,
full new word by actual LSB clock+200ps; retain the original5ns stimulus cadence.
Verify real208ps pulse propagation and integrated precompare settling. Continue
recording the complete failed same-stimulus100k run; do not discard its alarms.

Pre-simulation electrical review rejects the short per-bit clock staircase:
lower old rails would already be off before the higher new rail settles,
moving the overvoltage to another floating bottom. Do not simulate that as a
claimed solution. Refine to explicit clear-before-next-trial phases instead:
phase1 captures actual native SAR D at UPDATE-rise after a native buffer guard;
phase2 captures CODE after a latched request has passed a50fF PDK RC delay.
The request SR holds the real208ps UPDATE long enough for that delay; a second
5fF delay clears the SR after the late clock, preserving a usable late pulse.
SAMPLE resets both request and eight reference DFFs. Use existing native sr,
buf, mux2, clkbuf, delay_capture (change its unused MOM count4->10) and
delay_valid, all inside owned refword. No counter/FSM/ideal timer is added.
For a binary SAR step, D differs from the old trial only in the current bit;
CODE then adds only the next lower trial. Other reference banks stay on.
Add D0..7 inputs to refword and eight external D sources to the owned unit
bench; actual top-level D outputs already exist and feed these inputs.
Rebuild owned refword, unit bench and R4 parent for the changed symbol, then
recheck the top TB. Declare unit Dcommit=previous&target stable before UPDATE,
CODE changes80ps after UPDATE rises. Require two actual capture clocks per
UPDATE, correct committed intermediate and final word, late capture<=1.5ns,
and no CMI/LTE/voltage overlap. Preserve the unsimulated staircase export.

## Completed bounded implementation —2026-10-21

Final source/export tag two_phase, unit_word06_two_phase and
nominal06_two_phase. Unit18/18 final words and16 committed/next-trial pairs
pass at208ps UPDATE; late capture<=1.048025ns, no conservative gate overlap,
CMI or LTE, reference peak0.923628V. Full4-frame+.123,-.8,+.8,-.8V output
145/14/241/14 exactly; every frame8 compare/write/update, output levels and
90..98ns stability pass. All32 two-phase operations/64 capture clocks match
actual native D then CODE, each phase changes<=1 bit, gap0.983808..0.985052ns.
Sample-close to final UPDATE-rise29.950653..29.994970ns; held difference
max0.202295mV, precompare residual error0.147335LSB vs0.25 limit.

All67 analog MOS six-pair/all-saved-point screens pass: reference0.962484V,
comparator0.950655V (core0.99V), Bootstrap1.751582V (IO1.98V). No foundry CMI
or LTE. Native completes0errors/7PDK-global-port warnings/5notices. Preserve
all startup frames and notices; no claim of arbitrary-clock/power-ramp safety.
100..400ns source averageVDD0.108595mW, REF_HIGH0.012785mW, input/clock delivered,
returned and net energy recorded separately; not a steady-state/system-power
signoff. Solver remainsAPS4/conservative/maxstep10ps/effective_reltol1e-7.

All35 owned OA cells read back with exact connectivity/parameters and zero
markers; full readback of five old dependencies identical. Final exported
DUT hash6e494dac6dc70792ae9c3941eda8107aec70067f4880fbc33209fd39679b1e6b.
The run and curated full-CDF DUT are canonically identical to that OA export;
only bench stimuli/parameters, saves and solver setup are overridden.
Native expanded leaves1677MOS statements,266MOM declarations,362PDK resistor
segments (multiplicity not unfolded; not a physical-area estimate).

Final evidence: verification/sar8_physical/results.json, netlist/sar8_physical/,
docs/sar8_physical.md and its two final-design figures. Failed spectra and
diagnostic-only figures retained in ignored output. New R4 window opened for
review. R3+B stays selected; R4 is an independent nominal candidate, not full
qualification. Full-code/FFT/PVT/noise/mismatch/area/logic-SOA/layout and real
reference-buffer/IO/power-network design are intentionally not started.

Five focused contract checks pass; owned Python compilation and YAML parsing
pass. Whole-tree diff checking identifies only the user's existing trailing
space in Obsidian wrap-up; leave it untouched and use scoped staged diff checks.
Finish with a scoped local commit; no push authorized.
