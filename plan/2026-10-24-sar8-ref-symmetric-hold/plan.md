# Complementary reference-gate holding across the complete idle reset

Status: complete. Diagnostic validation passes; reference SOA still fails.

## Scope / ownership

Continue the previous diagnostic experiment (89e33e6), not a transistor keeper
implementation. Frozen native ADC: Mmain2um, reference L90nm, W/multiplicity,
input, supplies, reference50ohm/4pF, sampling source and controller unchanged.
FF0.99V at -40C and125C, six100ns static frames per case. No PVT expansion,
noise/mismatch/PEX/full-code/FFT or OA promotion.

Own this plan, plan/log.md, scripts/sar8_ref_symmetric_hold/,
verification/sar8_ref_symmetric_hold/, output/sar8_ref_symmetric_hold/,
docs/sar8_ref_symmetric_hold.md, docs/figures/sar8_ref_symmetric_hold/.
Remote OA ownership: none. New immutable netlist run root:
/home/chenzc_intern25/TSMC28/llm_IO/sar8_ref_symmetric_hold_20261024,
SSH profile t28_io. PDK/OA/all prior runs and scripts read-only.
Preserve unrelated Obsidian edits/deletions/images and 10-bit experiment files.
Branch exp/cdac-flat8-device, starting HEAD89e33e6; no push.

## Implementation

1. Read prior native driver topology and helper equations; preflight license,
   source/model hashes, resource availability. Native Spectre (not EVAS).
2. For all four gates of bits0..7 add complementary finite conductances to VDD
   and VSS, strength400/2^bit ohms (25ohms at bit4). Qualification uses the
   existing final inverter INPUT (B node), not gate feedback as the command.
   Target is inverted B. Release when B leaves its settled logic band; enable
   only after B reaches its new rail and actual gate reaches within5% of that
   target. Latch the qualified hold until command changes or idle ends.
   Separate high/low enables, smoothed5ps. No hard ideal voltage clamp.
3. Enable only PRESET high and SAMPLE low. No RST qualification: a reset bit
   stays held while later bits reset. Transition waveform is still driven by
   native MOS/resistors; qualify/release is explicitly ideal diagnostic logic.
4. Two null and two symmetric-hold cases, same helper structure with zero
   conductance for null. Max2 simultaneous native simulations,4threads each.
   Preserve raw and collected data. Compare previous high-only hold read-only.

## Validation / outputs

- Exact native MOS mapping and deck inverse checks; original monitor preserved.
- Spectre compile/native completion, six frames/codes/timing, source/log/reduced
  receipts, actual CX settings. Do not describe deck10ps as effective maxstep.
- All saved reference terminal pairs over600ns plus early and later idle peaks;
  signed high overshoot/low undershoot, displaced worst instance and phase.
  Other control/comparator stress remains separately reported.
- All16 bottoms final settling within0.25LSB=1.7578125mV of assigned actual
  reference, margin to next sample, held errors, actual sample open/close and
  duration against null. No changes to external sampling source allowed.
- Saved high/low enable probes: no simultaneous rails, no holding during
  established acquisition/conversion, command consistency, continued late-idle
  holding. Record derived helper current; not total real-keeper supply power.
- Inspect scientific waveform plots; compile/focused assertions/scoped diff.
  Report evidence completeness separately from circuit SOA acceptance.
- Finish plan/log and task-only local commit; no baseline replacement or push.

Intended commit: verify: test symmetric reference holding through idle reset.

## Completed results and review

Four native Spectre21.1 CX cases completed once, exit0/tran PASS. All24 static
frames give [243,12,127,128,127,145], timing/idle checks pass. All1833 native
MOS mappings identical. Source/helper/reducer/log/data remote hashes match.
No OA/PDK/prior-run edits. Raw native and reduced waves retained.

- Cold: idle gate rail excursions +61.031/-57.103mV -> +1.010/-0.849mV.
  Hot: +65.136/-62.943mV -> +0.963/-0.913mV. Metrics include all idle phases
  in600ns, not just the plotted frame1 reset. Old high-only evidence retained
  read-only in figures to show negative and post-release residuals.
- Global reference peak cold1.051031->1.046743V, hot1.055136->1.035509V.
  Cold worst XSP7.MP_HIGH body-drain at144.411ns, BP7=-56.743mV. Hot worst
  XSN3.MN_LOW gate-bulk at246.040ns, GNN3=1.035509V. Both during conversion.
  Idle worst now XSN7.MP_HIGH body-drain: cold1.046679V/472.660ns and
  hot1.031700V/275.206ns. Gate holding does not bound bottom/drain voltages.
- All-bottom final settling after frame1RST7 cold3.197879->3.336571ns,
  hot3.539235->3.674063ns. New margin to actual Bootstrap sample26.930240/
  24.401231ns. Post-startup held errors0.576399/0.517121mV unchanged.
- Source sampling waveform identical. New/null actual open/close differences
  <0.001ps; this is numerical equivalence, not physical timing accuracy.
- Both hold enables saved for all32gates. No overlapping high/low enables,
  no settled-command mismatch, zero helper during sampling/conversion;
  all32 active in every post-reset idle interval until SAMPLE_INT request.
  Bit4 explicitly remains held through RST3..0, unlike old release-at-RST4.
- SAMPLE_INT request arrives~201.07ns, earlier than actual SEQ_SAMPLE opening
  ~202.69ns(cold)/202.84ns(hot). Initial analysis mistakenly extended the
  hold-continuity check through this intentional release gap; corrected the
  measurement window to request-minus20ps, not the circuit. Actual Bootstrap
  sample window and settling margin remain measured against SEQ_SAMPLE.
- Largest derived helper branch current2.346mA; finite diagnostic conductance
  accelerates the final gate tail and changes reset settling. No real keeper
  power/area/transition detection or analog shoot-through qualification.
- Zero-strength helper introduces more cross-event breakpoints. Null vs old
  maximum peak delta11.292uV, held-error delta5.794uV, sample-edge delta0.095874ps.
  Audited bounds20uV/10uV/0.1ps distinguish instrumentation effects from the
  ~60mV mechanism; no raw data altered. Independent audit was initially invoked
  before cold metrics existed, then rerun successfully after collection.
- Effective CX settings match frozen source: reltol1e-4,maxstep6ns,gear2only,
  abstolV1uV/I1pA; not requested deck10ps. Residual~1mV needs tighter convergence
  before silicon sizing. CMI and driver/control/comparator stresses persist.
  Coverage445selectedMOS/2670pairs, not full1833; no FFT/fullcode/noise/MC/PEX.

Three final figures visually inspected; corrected plot scaling around rails.
Python compile, source/hash/phase/continuity/code checks and scoped diff pass.
Results: docs/sar8_ref_symmetric_hold.md and verification/sar8_ref_symmetric_hold/.
Task-only local commit; no push and no baseline promotion.
