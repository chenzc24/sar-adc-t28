# Ten-bit dual-rail monotonic CDAC candidate

STATUS: superseded by explicit user correction to EIGHT bits. These were
independent experiments, never a promoted ADC baseline. Stop pending 10-bit
static/dynamic jobs, preserving their partial evidence as interrupted. Existing
new OA objects remain recoverable history. The in-progress owned Canvas draft
is adapted into the requested 8-bit review, preserving original user artwork.
The next target has separate cdac8_dualrail sources and cdac8_dr OA names.

## Goal, reference and ownership

Implement the user's Canvas two-reference/top-sampling topology as an independent
10-bit T28 candidate; simulate saved OA exports and draw the actual candidate
back into a new Canvas Cell for review. Do not promote it to the active baseline.
Canvas source: project CDAC, document-e7893585-daed-4fed-9e1b-85f215459cd1,
revision 266. Its 20 equal/default 1-pF capacitors and unconnected comparator
outputs are a structural sketch, not an executable 11-bit ADC specification.
Preserve that original Cell unchanged.

Starting branch exp/cdac-flat8-device; git status is clean. The completed
StrongARM and SAR8-logic work, existing eight/ten-bit circuits and PDK remain
read-only. Own config/cdac10_dualrail.yaml; models/veriloga/cdac10_dualrail_*.va;
scripts/cdac10_dualrail/; verification/cdac10_dualrail/;
docs/cdac10_dualrail.md; docs/figures/cdac10_dualrail/; this plan and a bounded
maintenance-log append. Generated evidence: output/cdac10_dualrail/ only.
Commit only owned files, no push. Do not change active design_spec.yaml or
existing manifest entries; a separate candidate manifest is allowed here.

Remote owned SAR_ADC_T28 cells: cdac10_dr_sw_b0..b8 (schematic/symbol),
cdac10_dr_bank256 (schematic/symbol), cdac10_dr_nominal and cdac10_dr_literal
(schematic/symbol), cdac10_dualrail_controller, cdac10_dualrail_input,
cdac10_dualrail_comparator (symbol/veriloga only), and tb_cdac10_dr_nominal,
tb_cdac10_dr_literal, tb_cdac10_dr_strongarm, tb_cdac10_dr_ideal_sample
(schematic). Refuse existing cells/locks or unsaved user-owned targets.
Read-only dependencies: sar_bootstrap_canvas_flat_8b, sar_strongarm_t28,
cdac8_unit, cdac8_bank_{1,2,4,8,16,32,64,128}, and PDK native MOS/MOM.

## Architecture and explicit assumptions

10 bit, 10 MS/s, VDD/VREFP=0.9 V, VREFN=0, differential range +/-0.9 V.
Retain top-plate Bootstrap sampling. Each side: 256:128:64:32:16:8:4:2:1 Cu
plus a fixed VREFP dummy Cu, total 512 Cu = about 2.05008 pF using existing
4.00407-fF T28 cfmom_2t unit. No split bridge and no bottom VCM switch.
All bottoms initially VREFP. First decision needs no DAC trial. After each of
the first nine real comparator decisions, only the selected side's next
weighted bottom moves high-to-low; ten decisions produce offset-binary code.
Restore all switched bottoms to VREFP after conversion, before next sample.
No predicted code from Vin in the controller. Driver and reference MOS are
native T28, not ideal relays. SAR/clock/control and the baseline comparator
remain labeled behavioral abstractions. Literal array has 1024 independent
MOM units; nominal m-equivalent array is deterministic-only evidence.

Standard downward monotonic switching lowers comparator common-mode toward
ground. Existing NMOS-input StrongARM is an interface diagnostic, not assumed
compatible. Input common-mode bias still exists although CDAC has two rails.
Bootstrap is unchanged; doubling load is not assumed safe across corners.
Reference is finite source resistance plus decoupling, not a designed buffer.
No noise/mismatch/PVT/layout signoff implied by deterministic transient.

## Steps and validation

1. Check bridge t28_io, live CIW, windows, exact library path and tsmcN28
   technology; record dependency readbacks and reference Canvas snapshot.
2. Implement/test a ten-decision charge-conservation oracle, two-rail truth
   table, continuous finite-edge control, non-overlap and 100-ns schedule.
3. Build native reference switches/CMOS drives and MOM arrays, VA interfaces,
   and saved OA benches. Read back pin connectivity, count unit capacitances,
   require zero schematic markers, export exact fresh native netlists.
4. Run Spectre APS initial smoke and +/-input, near-zero, reset stress tests.
   Compare ideal sampling to unchanged Bootstrap; compare nominal/literal
   transient; test actual StrongARM separately. Evaluate every relevant MOS
   Vds/Vgs/Vgd/Vbs/Vbd with declared model-screen boundary 0.99 V, not foundry
   reliability signoff. Preserve CMI warnings/suppressed warnings.
5. If the initial circuit is executable, run bounded nominal static-code and
   coherent-sine tests plus representative corner diagnostics as justified;
   report failing gates without silently replacing devices/models. No broad
   noise/MC/PVT sweep is required before fixing a demonstrated hard failure.
6. Draw actual bank connections and a native reference-switch expansion in
   fresh Canvas Cells. Verify logical connectivity against an expected netlist,
   render/inspect for wires and labels; do not claim Canvas drawing is T28
   simulation acceptance or upload proprietary PDK model source.
7. Report LSB=1.7578125 mV and deterministic 0.25-LSB=0.439453125 mV separately
   from quantization. Figures include ideal baselines and sample/conversion/
   reset windows. Record scope limits, targeted tests, dependency audit,
   git diff --check, log and scoped commit. Do not edit Bootstrap/StrongARM to
   hide their independent limitations.

## Expected artifacts

OA readbacks/markers/exports, source hashes, result.ok metadata, waveforms,
stress and code metrics under output/cdac10_dualrail/; concise report/config,
curated timing and transfer figures, separate candidate Canvas Cells. Intended
commit: feat: evaluate independent 10-bit dual-rail monotonic CDAC.

## First native result and bounded reset adaptation

Initial exact OA run: correct code 770 at +453.516 mV, comparison raw error
0.279 mV, but reference/driver reset stress 1.327 V. Two-rail removal alone
does not fix floating-top reset. Preserve initial OA exports and waveforms.
Within the owned benches only, compare a sampling-overlapped reset: Bootstrap
on from about 94.05 ns through 141.05 ns, unchanged falling sample edge;
restore references at next-cycle 3.01 ns (103.01 ns), after the new stimulus
step at 100 ns. Native Bootstrap devices remain unchanged. Save fresh exports
under sample_reset and declare acquisition/reset overlap in plots and metrics.
Do not overwrite accepted initial exports or silently call this the old timing.
