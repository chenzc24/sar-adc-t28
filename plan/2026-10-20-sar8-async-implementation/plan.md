# Runnable asynchronous SAR model and native gate implementation

## Goal / authority

User requests executable asynchronous SAR modelling, modular gate design in
Virtuoso and simulation. Eight-bit flat-CDAC / 10 MS/s remains selected.
Implement a new isolated controller, not a replacement of historical cells.
Native logic must contain actual T28 static CMOS gates/registers; behavioral
models may serve only as reference and explicit testbench plant/stimulus.

## Starting state and boundaries

Start 0820464, exp/cdac-flat8-device. Untracked cdac10_dualrail config/VA,
scripts/cdac10_dualrail/, verification/cdac10_dualrail/ and its plan are
unrelated and read-only. Existing GUI windows tb_cdac10_dr_* are user/other
target owned and must remain open and unchanged. Do not change branch while
this shared workspace has concurrent unrelated work. No push authorized.

Local owned: this plan; models/behavioral/sar_async.py;
models/veriloga/sar8a_*.va; scripts/sar8_async/; verification/sar8_async/;
config/sar8_async_impl.yaml; docs/sar8_async_implementation.md;
docs/figures/sar8_async_impl/; bounded implementation-status additions to
config/design_spec.yaml, docs/sar8_async_logic.md, README.md,
virtuoso/cell_manifest.yaml, plan/log.md, docs/design_log.md.
Ignored evidence: output/sar8_async_impl/. Original proposal config retained.

Remote owned library: SAR_ADC_T28, expected path
/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28, technology tsmcN28,
profile t28_io. New schematic/symbol cells only, checked absent first:
sar8a_inv, sar8a_nand2, sar8a_nor2, sar8a_and2, sar8a_or2, sar8a_xor2,
sar8a_buf, sar8a_mux2, sar8a_sr, sar8a_dffr,
sar8a_delay_dac, sar8a_delay_valid, sar8a_delay_capture,
sar8a_delay_reset, sar8a_delay_advance, sar8a_delay_publish,
sar8a_delay_bbm, sar8a_bbm, sar8a_frame, sar8a_cmp_if, sar8a_seq,
sar8a_token8, sar8a_bit, sar8a_out8, sar8a_status,
sar_logic_8b_async, tb_sar8a_gates, tb_sar8a_logic,
tb_sar8a_strongarm. New behavioral cellviews if needed: sar8a_controller,
sar8a_plant; symbol/veriloga, no dummy schematic left connected.
Do not overwrite an existing name without confirming ownership and exact
readback against this target's recorded state. No OA filesystem editing.

Read-only: PDK/shared libraries, all historical comparator/CDAC/bootstrap/
controller cells and old netlists, old plans, unrelated windows. OA dependency
reads and fresh exports allowed; no repair of comparator offset or analog
stress/acquisition issues under this target.

## Implementation

1. Preflight bridge/version/profile/CIW/windows/library/technology/locks;
   preserve snapshots of any read-only dependency used. 2026-10-20 initial
   bridge status: v0.8.0 tunnel/daemon/Spectre healthy, expected t28_io CIW.
2. Implement event-driven Python reference, comparator input-dependent delay,
   DAC/reset/capture guards and independent deadline; no free bit clock.
   Cover static all codes, coherent sine, variable completion, faults/abort,
   stale events, result retention. Disable analog nonidealities for golden
   cases, parameterize them for sensitivity, not PDK evidence.
3. Author separate reusable VA controller/plant modules and Spectre smoke
   decks as needed. The independently executable controller reference is
   Python; the implemented electrical controller is the native gate hierarchy,
   not a VA shortcut. Only the testbench plant/measurement observer use VA.
   Controller reads only comparator rails, never Vin. Timed transitions are
   state-qualified and cancelled/invalidated on abort/new frame.
4. Create static CMOS gates, reset-priority SR, resettable edge-triggered
   storage and native RC/buffer delay cells. Read back, export and characterize
   actual loaded delay/pulse/reset behavior. Delay cells are not ideal timers.
5. Construct handshake sequencer with distinct trial/eval/capture/reset phases,
   comparator clock held through capture, advance only after reset; eight
   working bits and separate output bank. Build explicit abort/deadline path,
   BBM and loaded testbenches. Validate small circuit before full integration.
6. Native gate loop with behavioral comparator/DAC testbench, then unchanged
   real StrongARM interface. Test all 256 logic patterns, variable comparison
   delay, timeout, repeated frames, reset, output retention, final LSB and
   measured capture/advance separation. Characterize selected PVT endpoints
   and report misses rather than hiding/reclassifying them.
7. Re-export saved OA, assert readback/connectivity/parameters and exact circuit
   equivalence to simulated native hierarchy. Save run metadata/model section,
   VDD/temp/load/mode, result.ok and warnings; visually inspect waveforms.
8. Record report/log/manifest, focused syntax/tests/diff checks and scoped
   commit(s): `feat: model and implement asynchronous eight-bit SAR logic`.

## Pass / evidence limits

All accepted Spectre runs require result.ok and complete finite waveforms.
Native gates must not secretly use VA/DFF ideal primitives. All owned OA
schematics need checked connectivity/readback; open markers are failures or
explicit unresolved findings. Static behavioral codes and coherent-sine
metrics must be recorded with config; all native 256 patterns need eight
ordered captures, correct published code and no reference overlap. Timing
is measured, not the old 86.9-ns budget. PVT failures remain failures.
No layout/PEX, noise/mismatch yield or complete-transistor ADC sign-off.
If a newly required cell or contract change is needed, update this plan first.

## Implementation refinements

After constructing initial leaves, identified a delayed-edge reuse hazard:
an ordinary RC chain may retain charge across the short compare/reset gap.
Delay leaves therefore gain real MOS fast-reset clamps (A=0 clears RC0 and
precharges RC1). Explicit owned-only rebuild is allowed for these seven
sar8a_delay_* leaves after matching their recorded previous OA topology and
checking they are not open in a GUI window. Preserve before-rebuild receipts.
Symbol spacing was also expanded to contain all port rows. Replacing a child
symbol moves parent instance terminals before its named stubs are rebuilt;
the first parent readback detected this correctly, and that attempt stopped.
Allow a topological rebuild of all **this target's** recorded new leaves and
controller cells, verifying live instance identity/master ownership and saving
before-rebuild readbacks. Recreate all wires from the declarative contracts
and require final complete connectivity/zero markers. No unrelated cell or
PDK change. Require repeated short-low-pulse delay tests,
not only one isolated step.

First full native run produced code 145, eight decisions, but is **rejected**
as timing acceptance: VALID about 88.008 ns overlaps the deadline edge;
CMP_CLK falls 28.9 ps before the externally loaded CAPTURE fall. About
492k suppressed SOA messages originate at a floating stacked-PMOS NOR middle
node on redundant SAMPLE/SYS_RST transitions. Fix the native NOR/OR cells
with inverter/NAND De Morgan static CMOS (no stacked PMOS), add RESET AND
NOT CAPTURE to the comparator reset interlock, and reduce DAC delay seed
220 fF to 200 fF, with minimum guard to be remeasured at FF and slow timing.
CDF clamped the initial 4-um reset-PMOS request to 3 um; record the actual
3-um implementation and reconcile source to that legal width. Rebuild owned
new cells topologically and preserve the rejected export/results.

Small-case baseline used 5-ps maxstep. Subsequent screening may use 200 ps
only after a representative tighter-step comparison confirms codes/edges;
Spectre's conservative LTE still resolves native gate transitions. Save
independent per-case runner output directories to avoid auxiliary log races.

Add models/veriloga/sar8a_monitor.va as a measurement-only deck observer (no OA
master required). It reports capture/eval/advance counts and output at 95 ns
each frame, allowing exhaustive native code-pattern testing with sparse saved
waveforms without hiding internal clocks. Add fault_frame to the test plant
for success -> fault -> recovery in one physical transient, and pattern mode
2 enumerating 0..255 as a logic fixture, not a physical DAC/ADC transfer claim.

Publication refinement: distinguish final-result request, qualified COMMIT,
and delayed external VALID. Only COMMIT clocks the output bank; it is
inhibited by deadline/fault. BUSY is an independent transaction latch cleared
by COMMIT or FAULT, not a combinational HOLD/VALID decode that can glitch on
sampling reset. After a successful COMMIT, deadline no longer aborts the
output-settling guard; reference HOLD remains to PREPARE. Deadline versus
COMMIT ties are deadline-priority in the event model; native zero-margin
analog arbitration is not claimed and must retain characterized guard.
The Python model and native status contract are updated together.

Final gate fixture still found a stacked-NMOS middle-node undershoot in the
ordinary NAND at startup. Add an explicit 10-fF analogLib capacitor MID-to-VSS
inside sar8a_nand2 to bound capacitive feedthrough; this is an intentional
schematic component, not hidden simulator cmin or a PDK/model edit. Recheck
truth/timing/SOA, record its physical area/power/layout cost as unoptimized.
Only rebuild this owned NAND leaf (same external symbol geometry) and then
the owned controller hierarchy/benches. Remove now-unused HOLD from the
status interface; recheck schematics after regenerating changed symbols so
cross-view interface markers are not mistaken for final check results.

The loaded NAND unit fixture is SOA-clean at TT (four inherited model warnings
only). First complete loaded-controller run passes code 145/eight events but
has a brief BUSY-node overvoltage with effectively open external flag ports.
Give BUSY/VALID/FAULT explicit 5-fF interface loads, consistent with output
data load assumptions; preserve the open-flag result. This changes only the
two owned testbenches, not the controller DUT. This is a stated loaded-port
baseline, not qualification for arbitrary unloaded/PVT conditions.

Measured 100-ns transistor runs take minutes; full 256-frame PDK regression
is hours-scale. Asked the user whether to start that extended compute run.
Default current-turn acceptance is independent all-256 functional simulation
of the actual exported netlist (native INV/NAND DC truth audited as MOS
connectivity, SR/DFF/delay abstractions explicitly labelled), plus native
representative/timing/control/fault/real-comparator runs. Never describe that
functional abstraction as all-256 native Spectre qualification. Full PDK code
sweep remains separate unless the user authorizes the longer run.

The Spectre skill recommends AX for daily transient work. AX is permitted for
additional bounded fault/PVT screens only after comparison with the APS tight
nominal baseline; record exact mode and edge/code differences. APS remains
the primary timing reference. No LX/VX approximations or hidden model/limit
disabling. A mode mismatch must never be treated as equivalent qualification.

Additional untracked cdac8_dualrail config/models/docs/figures/scripts/tests
and plan appeared during work in this shared checkout. They are read-only
and excluded along with the original ten-bit dual-rail files; no integration
of that unreviewed switching interface is inferred for this controller task.

Further SOA readback localizes the remaining nominal overvoltage to the
internal complement QB of the ACTIVE SR latch, not just its external BUSY
port. Add an explicit 5-fF QB-to-VSS capacitance to the owned sar8a_sr cell;
record it as intentional unoptimized schematic loading. Do not disable SOA
checks or alter foundry limits. Recheck/re-export the entire owned hierarchy.
Native measured guards exceed the initial timer budget. Rebalance the native
COMMIT deadline to 89 ns, retaining a 1-ns planned abort margin before 90-ns
PREPARE; sampling remains exactly 10 MS/s. Update Python reference, testbench,
functional netlist stimuli and implementation config together. Preserve the
88-ns original proposal and all intermediate runs as history, not pass data
for this final revision. Measure abort/reference-release latency against this
new guard; PVT failures remain explicit, not hidden by the retiming.

Area/runtime refinement before final acceptance: the generic gate-built DFF
uses 94 MOS and two SRs, resulting in 3492 controller MOS. Replace only the
owned sar8a_dffr internals with a 24-MOS static TG master/slave resettable DFF:
clock/reset inverters, four complementary TGs, two NAND+inverter latch cores,
and two explicit 5-fF storage-node caps. Same D/CK/RST/Q/VDD/VSS interface.
Reset forces both latch outputs low for either clock level; feedback is static,
not dynamic TSPC. Require new native DFF/clock/reset tests and full integration
reruns from a fresh `tgdff` export. All earlier native runs are intermediate,
not acceptance evidence for this new cell. Refresh all ancestor check status.

DFF unit control adds explicit testbench-only reset pulses during CK=1 and
CK=0 while D remains high. Demand asynchronous clear and held reset state
after release until the next positive CK; this is independent of startup-only
reset. Stimulus substitutions do not alter the exported DUT hierarchy.

Branch-current PSF parsing exposed a nonphysical `units` property column
filled with NaNs, while every requested voltage/current trace was finite.
The wrapper now selects and validates exactly the explicit save list, records
excluded metadata, and never fills/removes nonfinite physical samples. Raw
PSF is unchanged; existing executions can be re-read, not rerun or fabricated.

The tgdff multi-frame native tests exposed a real recovery race: FAULT was
cleared only by ACCEPT while the same old FAULT reset the reference HOLD SR.
Retain the failing results. Change the status FR input from SYS_RST to
WORK_RST (SYS_RST OR SAMPLE), so acquisition clears old FAULT well before
HOLD_START; keep ACCEPT clear too. Rebuild only this owned status cell, then
check/read/export all ancestors. New acceptance tag is `recovery`; rerun all
native scenarios and both numerical-mode controls for this exact revision.
Do not hide SS 0.81 V / 125 C deadline failures, FF 0.99 V SOA warnings or
large-negative-residue StrongARM stress warnings by changing model limits.

Visual review found semantic labels too small relative to the deliberately
large custom symbol bodies. Increase only custom symbol pin/name font sizes,
without moving terminals or changing circuits. Recreate these owned symbols,
recheck parent connectivity, preserve a new final export and require normalized
native definitions equal to the simulated recovery export. Leave the three
owned review schematics open; do not close unrelated windows.

User answered the asynchronous compute question: finish current validation,
do not launch the hours-scale native 256-code regression. Bounded representative
APS confirmations already in progress are within the current verification;
full-code native Spectre remains explicitly unperformed, not a pending job.

## Delivered result / open gates

Executable event reference and isolated 26-cell native controller implemented;
three schematic benches and one behavioral plant added (30 cells, 29 native
schematics checked/read back with zero markers). Controller: 1742 MOS plus
316 explicit ideal caps and 55 ideal resistors; not an optimized standard cell
or complete-transistor ADC. Saved human_final exports match recovery simulated
subcircuits; unchanged StrongARM readback and plant SHA verified. Three owned
review windows remain open; all unrelated windows retained.

Five model tests pass; ideal 2048-ramp/4096-sine has no missing codes and
48.7529-dB SNDR / 7.8061 ENOB; allocated-noise/jitter sensitivity gives
45.9121 dB / 7.3342 ENOB. Actual-export functional abstraction passes all
256 patterns plus 16 fault positions and recovery, explicitly not Spectre.

Current-revision evidence: 17 integrated native runs plus 4 unchanged-unit runs,
all result.ok and all requested physical traces finite. TT APS5p VALID87.349ns,
code145/eight ordered events, no reference overlap; AX edge deviation <=17.611ps.
Real StrongARM nominal code145 VALID86.419ns; representative codes14/241 correct.
Fault retention/recovery, reset and duplicate-start behavior work. BASE drops
0.192ns after the slow-case deadline edge, before PREPARE; TT opposite-select
minimum dead time0.150ns. Explicit CK-high/CK-low DFF asynchronous-reset tests pass.

NOT QUALIFIED: SS0.81V125C misses the 89ns cutoff with only seven decisions
(AX and APS confirmed); multiframe CAPTURE undershoot about -0.111V has CMI
SOA violations (APS confirmed), FF0.99V and negative-residue real StrongARM also
have CMI/suppressed warnings. Functional success does not waive these failures.
No PDK RC/layout/noise/MC/full-ADC/power acceptance. No native 256-code sweep,
as selected by user. All failed/intermediate executions are preserved in output.

Report, three inspected scientific figures and curated summary identify exact
decks/model sections/VDD/temp/modes/hashes. CLI check/batch now exit nonzero on
functional or SOA failure rather than treating a clean simulator exit as pass.
Final focused syntax/YAML/diff/scoped-commit checks; no push. Unrelated ten-bit
dual-rail files excluded; the concurrent eight-bit candidate committed separately.
