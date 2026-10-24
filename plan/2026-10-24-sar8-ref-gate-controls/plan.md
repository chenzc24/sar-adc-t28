# Reference gate hold versus bit7 reset-slew single-variable controls

Status: complete. Diagnostic controls verified; no variant passes reference SOA.
No OA promotion or baseline replacement.

## Scope and ownership

- Frozen baseline: e94e802 L90 / 2um Mmain FF0.99V cold(-40C) and hot(125C),
  six100ns static frames. Reuse exact input, supply, reference50ohm/4pF,
  sampling/closing wave, controller, PDK, reference W/L/multi and CX settings.
- Preserve dirty Obsidian deletions/edits/untracked images and10-bit experiment.
- Own this plan, plan/log.md, scripts/sar8_ref_gate_controls/,
  verification/sar8_ref_gate_controls/, output/sar8_ref_gate_controls/,
  docs/figures/sar8_ref_gate_controls/. Remote OA ownership: none.
- New remote netlist-only directory:
  /home/chenzc_intern25/TSMC28/llm_IO/sar8_ref_gate_controls_20261024,
  profile t28_io. All previous runs, PDK and OA read-only. No push.

## Experiments

Use explicit Verilog-A diagnostic conductances (not a completed transistor
keeper implementation). Native MOS/CDAC and their parasitics remain present.

1. Instrumented null: hold conductance0, extra bit7 series resistance0.
   Compare with frozen native baseline to bound instrumentation/numeric effects.
2. Hold-only: add conductance from an already high GNN/GPN gate to VDD for
   bits0..6 during idle PRESET, before that bit's own RST. Disable during
   sampling/conversion and before commanded gate changes. Two strengths:
   Rhold=1600/2^bit and400/2^bit ohms (100/25ohms at bit4). Only holding
   conductance changes; bit7 remains untouched. Smooth enable/disable5ps.
3. Slew-only: hold conductance0. Add100/300ohms to each of the four bit7
   gate-drive paths only during idle PRESET (not acquisition/conversion).
   Retain existing physical gate resistors and drivers. Smooth switching5ps;
   zero series voltage outside idle. Measure actual gate/BN7 slew, not assume
   a2x/4x time factor. This alters bit7 electrical reset edges, not RST7 command.
4. Each family tested independently at FF hot and cold. No combined variant.
   Ten new six-frame cases total, max2parallel x4threads. No repeated dispatch.

## Checks and measurements

- Preflight native Spectre license/profile, model hashes and remote resources.
  No CIW/OA operation needed for immutable netlist runs.
- Exact inverse DUT/deck changes, unchanged sample source and fixed device
  parameters. Native end/PASS/logs plus source/reduced receipts.
- Hold activation and bit7-added-resistance controls verified from saved probes;
  high-gate clamping is diagnostic ideal behavior, not silicon-qualified logic.
- All six codes and compare/write/update counts; startup separate. Actual
  sampling open/close and duration deltas against null and old baseline.
- Reference gate and all existing2670 terminal-pair stress, no relaxed limits.
  Report cold/hot worst reference peak AND same bit4 idle event, not substitute
  a displaced peak. Other control/comparator failures remain separately visible.
- At frame1 idle reset: RST7->BN7 10-90%, settling to actual reference rail
  within0.25LSB=1.7578125mV and stays until next sample; all-bottom reset
  completion and margin to next sampling. Conversion precompare residual and
  preclose/held sampling errors, source-current excursions, actual gate overlap.
- Plot matched native windows; inspect final images. Compile, focused checks,
  scoped diff, factual log and task-only local commit. Preserve all raw runs.

Intended commit: verify: compare reference gate holding and idle MSB slew controls.

## Completed evidence

Ten immutable native Spectre21.1 CX cases completed with exit0, native PSF END,
tran_perf PASS and matching remote source/helper/reducer/log/reduced hashes.
Two parallel jobs,4threads each; no dispatch repeated. PDK/config dependency
hashes match the previous audit. No CIW/OA/PDK modifications. Native raw waves
remain remote; complete native-point timing/gate/bottom arrays and stress
summaries were collected locally. No noise, mismatch, PEX, FFT or full-code test.
Effective settings match baseline: CX reltol1e-4, voltage abstol1uV, current
abstol1pA, maxstep6ns, gear2only. These override requested deck defaults; do
not describe this as a10ps-maxstep run. Actual peak neighborhoods are adaptive.

Source verification confirms all1833 native MOS instances, pins and parameters
unchanged for every variant. Only diagnostic hold conductance or idle bit7
series resistance changes between variants; null contains the same helper
instances with zero strength. The monitor's original module is byte-preserved
and helper modules appended explicitly to its uploaded VA source.

### Null-control validation

Old vs instrumented null: identical six codes at both corners, maximum reference
peak difference0.000315mV and held-error difference0.000660mV. Sample opening
edge difference <=0.07442ps, closing <=0.01807ps. Same effective settings.
These tiny differences are numerical/instrumentation effects, not intentionally
changed clock timing. The original native runs remain unmodified.

### Measured results

GNN4-event peak is measured after frame1 RST7 and BEFORE frame1 RST4, with a
10ps exclusion at the latter boundary. It must not be confused with the maximum
over the entire idle interval. Complete600ns reference peaks below include all
saved terminal pairs of the reference switches, not only GNN4. Timing columns
are frame1 idle reset after input differential-0.81V.

| Corner | Control | GNN4 event peak V | Worst reference terminal V | GNP7 90-10% ps | BN7 10-90% ps | All-bottom final settling after RST7 ns |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| FF125C | null | 1.055147 | 1.055147 | 240.237 | 59.131 | 3.539394 |
| FF125C | hold100ohm at bit4 | 0.992886 | 1.053099 | 240.169 | 59.034 | 3.539330 |
| FF125C | hold25ohm at bit4 | 0.990733 | 1.053103 | 240.166 | 59.038 | 3.539376 |
| FF125C | bit7 extra100ohm | 1.052351 | 1.052351 | 269.018 | 63.000 | 3.539381 |
| FF125C | bit7 extra300ohm | 1.047886 | 1.047886 | 327.737 | 70.870 | 3.539404 |
| FF-40C | null | 1.051037 | 1.051037 | 214.654 | 56.385 | 3.198274 |
| FF-40C | hold100ohm at bit4 | 0.992989 | 1.047223 | 214.718 | 56.406 | 3.198095 |
| FF-40C | hold25ohm at bit4 | 0.990758 | 1.047227 | 214.720 | 56.410 | 3.198095 |
| FF-40C | bit7 extra100ohm | 1.048439 | 1.048439 | 242.367 | 60.589 | 3.198228 |
| FF-40C | bit7 extra300ohm | 1.044007 | 1.046710 | 298.584 | 68.725 | 3.198209 |

- All60/60 static codes pass, including startup. Each case outputs
  [243,12,127,128,127,145]; zero input permits127or128. All compare/write/update
  count, reset-order, held-code, logic H/L non-overlap and idle checks pass.
- Relative to null, largest sample-open difference0.00003694ps; close difference
  0.00000000830ps. The source waveform is byte-identical; no acquisition budget
  was shortened or shifted. Establishment of sampling-high disables both hold
  and added-resistance helper controls, verified from saved enable probes.
- Settling means all16 bottoms within1.7578125mV of their actual assigned
  VREFP/VREFN and remaining there until20ps before next sample, NOT RST_DONE.
  Cold final reset margin27.0683ns, hot24.5356ns, essentially invariant. Small
  changes to bit7 electrical edge do not control the final all-bit completion
  in this stimulus; later staged bits still govern it.
- Maximum post-startup held error remains0.576491mV(cold),0.517154mV(hot).
  This is deterministic six-point testing, not proof of unchanged full-code,
  spectral or noise performance.
- Hot reference-source current peak P/N (includes decap charging) changes from
  1.4898/1.5099mA to1.4262/1.4392mA at extra300ohm. Cold1.4782/1.4955mA to
  1.4013/1.4090mA. This is not a transistor-resolved shoot-through measurement.
- Largest diagnostic hold-branch current is about121.34uA across the two
  corners. This is ideal-rail holding current, not total real-keeper supply power.

### Interpretation and remaining problems

1. Hold controls strongly suppress the ORIGINAL bit7-induced GNN4 spike at both
   temperatures without changing bit7 edge or code. This counterfactual supports
   weak high-state gate holding as an important cause, beyond temporal correlation.
   The experiment does not isolate each individual Cgd/current contribution.
2. Only the NMOS high gates were held. Worst reference stress consequently
   shifts to XCDAC.XSP4.MP_HIGH(hot), XCDAC.XSP5.MP_HIGH(cold). Their low gates
   still undershoot below ground. Hot peak1.053103V is |Vgb| with bulk0.99V,
   corresponding to gate about-63.10mV, not a gate at+1.053V. Increasing high
   holding alone cannot cure this unmodified complementary path.
3. Holds are intentionally released at each bit's RST edge. A later GNN4
   peak persists after release (hot0.993631V at~177.574ns). RST4 need not change
   that bit's stored value in this input case: release of the diagnostic keeper
   is not evidence of an actual commanded GNN4 transition. Both earlier event
   and entire-idle peaks are preserved as separate metrics.
4. Bit7 extra resistance changes actual gate and bottom slew and moderately
   reduces both positive/negative coupling. At300ohm the hot global peak is
   lower than in the high-only hold group, but still1.047886V. Cold worst moves
   to XCDAC.XSP7.MP_HIGH at1.046710V. Reduction is not elimination.
5. All runs still report native CMI. Existing selected-pair failure counts are
   hot1740/cold2008; a binary count conceals amplitude improvement. Coverage is
   445selected MOS /2670 pairs, not all1833. Other driver/control/comparator
   stress classes were not addressed. Small residual excursions need stricter
   accuracy convergence before sizing or reliability conclusions.
6. Logic H/L non-overlap passes, but no new reference-switch branch-current
   probes were added. Slower analog gates can change transistor overlap despite
   logic non-overlap; do not claim zero shoot-through from these results.

## Recommended next target (not implemented)

Test complementary high/low stable-state holding, including the already reset
bits while later bits change, rather than continuing to strengthen high-only
holding. Keep one mechanism variable at a time and first verify the attribution
model. If effective, implement an asymmetric transistor driver: controlled
transition slew, low impedance at settled rail, and explicit release/re-enable
that does not contend with commanded transitions. Then evaluate modest bit7
slew shaping separately/combined and save P/N branch currents for analog
overlap checks. Preserve the sampling source/window and the0.99V acceptance
condition; no model-limit relaxation. Native5-point PVT, full-terminal stress
and static/sine regression are required before promoting a real circuit.

## Validation and artifacts

- scripts/sar8_ref_gate_controls/: VA helper, source preparation/verification,
  bounded native flow, extraction, event-window refinement, plotting and audits.
- verification/sar8_ref_gate_controls/comparison.json and per-case metrics:
  exact results; null_comparison.json, remote_receipts.json, validation.json.
- docs/figures/sar8_ref_gate_controls/{holding,slew}.png: final inspected plots;
  same frame/absolute baseline origin, model limits, complementary PMOS stress,
  reset edge and all-bottom settling. No smoothing or fabricated waveform data.
- Source inverse/mapping checks, native exits/logs/receipts, all60 frames,
  null-equivalence bounds, saved helper enables, event peaks, image hashes,
  Python compile and scoped diff checks pass. Analysis initially combined the
  early GNN4 event and later idle peak; corrected measurement windows and retained
  both. A local import-path collision in refinement was fixed with explicit
  module loading; no native case was rerun or overwritten.
- Task-only local commit, no push. User Obsidian and10-bit changes untouched.
