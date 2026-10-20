# Compare native CDAC restore timing at normal and -0.5-LSB input

## Goal / scope

User requests a timing comparison against the existing +453.516-mV figure,
showing where the 1.4-V spike occurs during 127->128 restoration. Replot exact
completed final_nominal and clean_va_input_-3516 waveforms, extend the original
100..195-ns view through next-sample restore at 203.01 ns, and add a shared-scale
zoom. Identify BN5 and XCDAC.XSN5.MN_LOW Vbd, not a 1.4-V differential error.
Use original samples without smoothing/downsampling away peaks. No new simulation,
OA/Canvas changes, device/control edits or qualification claims.

## Ownership and dirty state

Branch exp/cdac-flat8-device. Only untracked cdac10_dualrail paths exist at start;
preserve/exclude. Existing async design, baseline, models, config and raw evidence
are read-only. Own this plan; scripts/cdac8_dualrail/compare_restore.py;
docs/figures/cdac8_dualrail/restore_compare_{overview,zoom}.png and
restore_compare_metrics.json; bounded docs/cdac8_dualrail.md and plan/log.md
append. Intermediate output/cdac8_dualrail/restore_compare_check.log is generated evidence.
Remote owned objects: none. Scoped local commit; no push.

During work, concurrent untracked docs/inventory/, plan/2026-10-20-project-inventory/,
plan/2026-10-20-sar8-two-cycle-timing/, scripts/maintenance/ and
scripts/sar8_async/two_cycles.py appeared. Preserve/exclude all of them.

## Validation / artifacts

Require both result.ok, same OA-source and VA hashes, native subckt equality,
same supply/corner/temperature/parameters except VDIFF. Decode saved NH controls
and DOUT to verify 192->128 and 127->128; assert all-eight-bit vs one-bit changes.
Check raw BN5 peak/time against retained stress metric (1.399620349965 V at
203.128786193 ns), PHI high and BUSY/VALID cleared at peak, and its physical
MN_LOW D/G/S/B mapping in the native netlist. Show common scales, phase windows,
ideal CM/residual baselines, rail and .99-V core screen, original sample peak,
command/new-enable/peak timing. Visually inspect both final figures, Python
compile, diff checks, factual log and scoped commit. The two runs use native T28
Bootstrap/reference MOS/MOM plus ideal comparator and behavioral fixed-period
control; do not relabel as the separate async/StrongARM experiment.

## Result

Both completed original runs pass provenance/context/native-hierarchy equality
checks; only VDIFF differs. Saved words confirm normal 192->128 (one bit),
failure 127->128 (eight bits). Raw BN5 peak/time exactly match retained metric:
1.399620349965 V at 203.128786193 ns. Native terminal mapping confirms MN_LOW
D=BN5, G=EL_D, S=VREFN, B=0; |Vds| is 1.396208624418 V at that sample.
PHI=.9 V, BUSY=VALID=0, so phase is next-sample restore. Normal same-device
max |Vbd| in the zoom is .077786497454 V, not the normal run's global MOS
worst .977787 V. All existing raw/source/model files remain unchanged.
Two new shared-scale figures have Chinese labels, ideal baselines, phase
windows and unclipped original peak samples; visually inspected and fixed
annotation/legend overlap. Focused executable assertions and Python compile
pass; report updated, diff checks complete. No simulator or remote writes.
