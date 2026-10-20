# Remove CDAC reference drivers: independent native Spectre diagnostic

## Goal and electrical boundary

User requests removal of the six driver MOS, retaining only PMOS-high and
NMOS-low reference selectors, to test the roughly 1.4-V restore spike. Use
independent netlist-level diagnostics, not an OA/baseline replacement. Retain
the existing Bootstrap, MOM array, rails, input, controller timing, ideal sign
comparator, 100-ps logical break-before-make and 20-ps command edges.

Five TT/.9-V/27-C, 300-ns cases: fresh native-driver -0.5-LSB replay; ideal
direct gates at -0.5 LSB with pass MULT_R=.5/1/2; direct-gate nominal-size
+453.515625-mV control. Native pass models/W/L remain identical at MULT_R=1.
Direct PMOS gate = VDD-EH, NMOS gate = EL via ideal dependent voltage sources;
these are diagnostic, not realizable zero-impedance drivers. Removing drivers
does not mean weaker drive. Size scan changes both channel strength AND gate/
junction charge/capacitance, so do not present it as a pure Ron experiment.
Allow one tighter-time-step repeat if a conclusion depends on a small margin.

## Ownership / dirty state

Branch exp/cdac-flat8-device. Dirty docs/sar8_async_implementation.md and
untracked sar8_async two-cycle results/plan/script/verification are concurrent,
read-only. Untracked cdac10_dualrail paths are preserved historical work.
Own this plan; scripts/cdac8_dualrail/no_driver_experiment.py and
no_driver_results.py; docs/cdac8_no_driver.md;
docs/figures/cdac8_no_driver/; bounded plan/log.md append. Generated evidence
output/cdac8_no_driver/. No remote OA owned objects or writes. All other
tracked files, original decks/results, installed VA views and PDK are read-only.
Scoped local commit; no push.

## Implementation / validation

1. Bridge/Spectre status and official primitive help; verify retained source
   deck/hash/VA provenance. Snapshot and stage exact local VA sources per run,
   changing only ahdl_include path, not their bodies or installed OA views.
2. Derive decks from completed OA-based cases without modifying originals.
   Delete exactly six driver instances per leaf definition; keep pass instance
   statements byte-identical. Add ideal gate sources, remove deleted EL_B saves.
   Assert all other native subckt blocks unchanged. Preserve baseline waveform
   reconstruction nodes. Native counts 128 vs bypass 32 reference/driver MOS.
3. Native APS, max two owned concurrent runs. Require result.ok, finite/full
   waveforms; preserve failures. Keep supply/corner/temperature/noise scope,
   deck/VA/source hashes and exact native logs/result locations.
4. Compare all five MOS port differences over every remaining reference/driver
   device, all 16 bottom min/max, TOP common-mode, NH/DOUT words and pre-compare
   residuals. Distinguish all-time/post-startup/restore-window maxima and printed
   CMI/suppressed/LTE warnings. Compare fresh replay with retained 1.399620-V
   result. Check .99-V screen, .25 LSB=1.7578125-mV residual gate and code; a
   numeric completion or one passing case is not ADC/reliability qualification.
5. Concise report, same-window plots with rails/port limits and waveform labels;
   visually inspect; focused source/metric assertions, Python compile and diff
   checks; update log, commit only owned paths. Do not change OA/Canvas or PDK.

## Outcome

Six native APS runs complete: five planned cases plus the allowed maxstep10ps
repeat of direct-gate MULT_R=2, which has only about 6.09mV screen margin.
Fresh native-driver replay exactly reproduces 1.399620349965V. At unchanged
pass sizes, direct gates reduce BN5 restore peak to .918697951337V and all
restore ports to .925287159604V, but SAR MP_HIGH Vgd still reaches 1.040450604V
because BN5 dips to -.140450604V with its PMOS gate at .9V. Half multiplicity
worsens all-time peak to 1.079516956V; double reduces it to .983908285V.
Tighter repeat gives .983907774V (delta -.511uV), comparator-error delta
+.129uV. All codes correct; no LTE relaxations. Native/half/direct1 retain
real CMI warnings; direct2/fine/control have zero CMI/suppressed warnings.
127->128 and the original control timings are unchanged in the direct cases.
The result implicates driver implementation but is not a pure delay/Ron proof;
0.5x fractional multiplicity is sensitivity-only. No native-driver replacement,
full ADC/cross-input/PVT/noise/MC/layout or reliability qualification.

Preparation guards verified exactly six driver removals per leaf and unchanged
pass statements/other subckts; ideal-gate equations hold to 1.11e-16V. All source,
staged VA and deck hashes remain pinned; finite complete waveforms and native
counts128/32 verified. A preparation-only AHDL filename mapping assertion was
fixed before simulation (OA modules share veriloga.va filenames); no failed
simulator result was accepted. Two plots visually inspected, source compile,
focused executable assertions and diff checks pass. Report docs/cdac8_no_driver.md;
raw output/cdac8_no_driver/; curated metrics and figures under docs/figures/.
Concurrent async work committed independently during the run; no overlaps or
edits by this target. Scoped local commit only, no push.
