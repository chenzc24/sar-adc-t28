# Maintenance Log

This file records factual project maintenance. Circuit and architecture
decisions remain in `docs/design_log.md`; reusable lessons require a separate
human-triggered note in `docs/experience/`.

## 2026-09-30 - Audit full-control bootstrap turn-off currents

- Target: distinguish turn-off output charge error from unintended hold input
  loading in the existing full-control mixed-voltage bootstrap fixture.
- Local changed areas: target plan, one exact-export transient-current probe
  script, audit report, bounded design-log entry, and this maintenance entry.
  New Spectre deck, log, PSF, and JSON remain ignored under
  `output/bootstrap_current_path_audit/`.
- Remote OA changes: none. The bridge tunnel was down at start, so the
  existing hashed OA export was simulated via direct SSH Spectre; no OA cell
  or PDK model file was edited.
- Validation: exact source SHA-256, Spectre 21.1 zero errors, 62 aligned
  finite saved signals (including terminal currents), source-resistor/device
  current balance, load-charge/KCL balance, JSON parse, Python compile, and
  owned diff review. The input-loading path is confirmed; unique parasitic
  attribution for turn-off charge still requires a distinct OA topology test.
- Commit status: commit only this audit locally as
  `test: audit bootstrap turn-off current paths`; do not push without request.

## 2026-09-29 - Screen independent mixed-voltage bootstrap candidates

- Target: build separately named OA experiments to address known bootstrap
  terminal-stress paths and measure stress and raw sample/hold error together.
- Local changed areas: target plan, two candidate YAMLs, OA creator,
  exact-export Spectre runner, result report, manifest, design log, and this
  entry. Generated readback, OA exports, decks, PSF, and logs remain ignored.
- Remote OA changes: created only the two experimental bootstrap
  schematic/symbol cells and their two differential schematic testbenches.
  All four schematics read back with zero check markers; existing bootstrap,
  CDAC, comparator, and PDK cells were not modified.
- Validation: two TT/0.9-V/27-C Spectre 21.1 differential transients completed
  with zero errors. The first retained 20 SOA warning examples and failed
  raw hold at -8.972 mV. The second had zero `CMI-275x` warnings and 144
  terminal metrics below diagnostic comparison levels, but failed raw hold
  at -8.755 mV versus 0.439 mV. Exact OA netlist hashes, model mappings,
  and source/readback correspondence were checked. No reliability signoff,
  PVT, noise, layout, or full-CDAC acceptance is claimed.
- Commit status: commit this target locally on
  `exp/bootstrap-protected-eval`; do not push without request.

## 2026-09-29 - Integrate T28 StrongARM with full split CDAC

- Target: diagnose the direct comparator/CDAC electrical interface, including
  on/off-clock controls at positive, negative and zero small differential input.
- Local changed areas: target plan, YAML conditions, OA creator, exact-export
  Spectre runner, result report, cell manifest, and this log. OA export, PSF,
  decks, readback, and six run logs remain ignored under
  `output/strongarm_cdac_integration/`.
- Remote OA change: new `SAR_ADC_T28/tb_sar_cdac_strongarm_diag/schematic`
  only. Existing W185 CDAC, StrongARM, bootstrap cells, and PDK were read-only.
  The new schematic has 25 instances and zero markers; exact netlist export
  connects StrongARM input gates to the full CDAC comparator-side top plates.
- Validation: six TT/0.9-V/27-C Spectre 21.1 runs completed with zero errors;
  matched ±0.439453-mV cases resolved in 224.116 ps with correct polarity.
  A/B clock-induced peak was 0.374181 mV, still 0.365124 mV at decision.
  Zero-input control showed a 0.375136-mV latch-dependent kickback but has
  no correctness verdict. Exact OA/source hashes, PSF coverage, Python/YAML
  and owned diff were checked. Existing bootstrap SOA warnings remain a
  physical-design blocker; no noise, mismatch, PVT, or full-conversion
  acceptance is claimed.
- Commit status: commit only this target as
  `test: integrate T28 StrongARM with split CDAC`; no push requested.

## 2026-09-29 - Map bootstrap terminal stress

- Target: locate complete-driver transistor terminal overstress before
  selecting an independently named protected bootstrap topology.
- Local changed areas: target plan, read-only OA-export/waveform audit script,
  result report, design log, and this maintenance entry. Ranked JSON and CSV
  remain ignored under `output/bootstrap_soa_map/`.
- Remote OA changes: none. All `SAR_ADC_T28` cells and PDK files were
  read-only; the healthy `t28_io` bridge and Spectre 21.1 were checked.
- Validation: exact OA-export SHA-256 and successful baseline-run identity;
  12 source-parsed MOS devices per differential side, six terminal pairs each
  (144 metrics), finite and aligned saved waveforms, and 19 Spectre SOA
  warning witnesses consistent within 20 mV. The driven cycle showed up to
  1.787 V on pump devices, 1.674 V in control/discharge, and 1.148 V `Vgd`
  on the main switch. Python compiled, generated JSON parsed, and the owned
  diff was checked. This is a model-warning screen, not foundry sign-off.
- Commit status: commit only this target as
  `test: map bootstrap terminal stress`; push was not requested.

## 2026-09-29 - Verify first-pass T28 StrongARM noise and interfaces

- Target: screen transistor-level comparator noise, local mismatch, selected
  PVT/output loads, and finite-input kickback against initial SAR budgets.
- Local changed areas: dedicated plan, YAML configuration, read-only OA-export
  and Spectre verification script, and result report. Raw exports, decks,
  Monte Carlo samples, PSF, and logs remain under ignored
  `output/strongarm_t28_verification/`.
- Remote OA changes: none. The exact 11-T28-MOS DUT netlist hash matched the
  first-pass baseline; only temporary Spectre analysis decks were derived.
- Validation: Spectre 21.1 noise, mismatch, PVT, and kickback runs; source
  hash/section checks and PSF parsing. Noise was 51 wrong decisions in 192
  near-threshold cycles. Corrected local-MC mismatch had 27 of 32 paired
  draws outside ±0.439 mV. Four deterministic PVT/load points met 1.5 ns,
  with FF/0.99-V device-voltage warnings. The 219.535-fF kickback fixture
  stayed below 0.439 mV; 50 fF exceeded it. An earlier MC model-section
  choice was found inert and its 48 apparent passes were invalidated.
- Commit status: commit only this target's files as
  `test: screen T28 StrongARM noise mismatch and loading`; no push requested.

## 2026-09-29 - Screen bottom-plate top-clamp widths

- Target: hold the full-CDAC bottom-plate fixture and 22 bootstrap pumps
  fixed while testing narrow T28 top/split clamp widths against the raw
  0.439-mV held-error gate; a bounded W185 probe was added after W200
  narrowly missed. No shared-boost construction or PVT was authorized.
- Local changed areas: plan, width configuration, independent OA creator,
  backward-compatible Spectre runner/analyzer options, cell manifest,
  result report, design log, and this maintenance entry. OA exports, source
  hashes, readback, decks, PSF, warnings, metrics, and plots remain under
  ignored `output/bootstrap_bottom_plate_clamp_width_screen/`.
- Remote OA changes: created only five independently named experimental CDAC
  schematic/symbol pairs and five testbench schematics, W500/W250/W200/W185/
  W100. Readback found 93 CDAC and 21 testbench instances and zero markers
  per variant; the technology remained `tsmcN28`. Existing bootstrap,
  prior CDACs, macro, PDK, and StrongARM cellviews remained read-only.
- Validation: exact OA Spectre exports had separate SHA-256 hashes and
  verified four T28 clamp sizing/connectivity statements plus the 22+2
  bootstrap hierarchy. Three TT/0.9-V/27-C static-input transients completed
  for each W500/W250/W200/W100 variant; all five completed for W185, with
  zero simulator errors. The W185 maximum raw error was 0.43378 mV, a
  5.22-uV nominal margin; all cases retain device SOA warnings, so physical
  acceptance is blocked. An OA-export formatting difference (`185.00n`)
  initially tripped the runner's strict width regex before simulation; the
  regex was corrected and the identical hashed export was used. Python
  syntax, YAML parsing, readback, metrics, and owned diff were checked.
- Commit status: commit only this target's files as
  `test: screen bottom-plate clamp width`; push was not requested.

## 2026-09-29 - Start T28 StrongARM transistor-level design

- Target: create an isolated first-pass 11-MOS `tsmcN28` StrongARM comparator,
  symbol, and transient testbench; measure nominal polarity, reset, and
  near-threshold resolution without claiming statistical closure.
- Local changed areas: this target's plan, OA creation/readback automation,
  exact-export Spectre runner, and focused result report. Generated OA
  export, PSF, JSON, and run decks remain under ignored
  `output/strongarm_t28_first_pass/`.
- Remote OA changes: created only `SAR_ADC_T28/sar_strongarm_t28` schematic
  and symbol and `SAR_ADC_T28/tb_sar_strongarm_t28` schematic. Readback
  verified 11 T28 MOS, pin/terminal/size connections, and zero markers in
  both schematics. Existing macro, active bottom-plate cells, PDK, and
  Analog Canvas remained read-only.
- Validation: exact OA netlist SHA-256
  `628f493c46c7c4df1e5e6262ab563c466958fd7ce182489515c507f3689be581`;
  six TT/0.9-V/27-C Spectre 21.1 transients completed with zero errors.
  ±0.439453-mV input gave correct polarity, complete reset, and 223.35-ps
  signed 0.45-V output resolution against the nominal 1.5-ns window.
  Initial local SSH export and input-parameter declaration errors were
  diagnosed and repaired; one testbench instance/signal name collision was
  removed before the final full rerun. Four PDK scoped-`scalefactor`
  warnings remained. Noise, mismatch, PVT, kickback, and layout are open.
- Commit status: commit only owned files as
  `feat: add T28 StrongARM first-pass schematic and testbench`; push was
  not requested.

## 2026-09-29 - Evaluate bootstrap bottom-plate sampling

- Target: compare same-bootstrap top-plate and true bottom-plate sampling in
  matched full differential 5+5 CDAC fixtures, then test a T28 top clamp.
- Local changed areas: target plan, parameterized OA creator, exact-export
  Spectre runner, analytical/phase analyzer, configuration, result report,
  cell manifest, design log, and this maintenance entry. Generated netlists,
  PSF, warnings, CSV/JSON, and SVG remain ignored under
  `output/bootstrap_bottom_plate_eval/`.
- Remote OA change: created only the two experimental CDAC schematic/symbol
  cells and their two testbench schematics named in the target plan. Readback
  found 93/21 electrical instances and zero markers per variant; exact OA
  exports contain 22 bottom plus two top copies of the existing bootstrap.
  Existing bootstrap and macro-model OA objects remained read-only.
- Validation: 9/9 ideal-clamp and 5/5 T28-clamp TT/0.9-V/27-C Spectre cases
  completed with zero simulator errors from separately hashed OA exports.
  An initial 1-ns result download failed at the Windows transport/rename
  stage; the exact case reran successfully. The analytical matrix gives
  ideal binary bit weights and monotonic 1024-level transfer, explicitly not
  a transistor-level physical DNL/INL claim. Python compiled; YAML parsed;
  both phase SVGs parsed; OA markers, hashes, selected netlist statements,
  and raw error metrics were checked. Every transient retains SOA warnings.
- Decision: the ideal clamp reduced the matched raw held error from 1.5320
  to 0.00790 mV, but the T28 NMOS clamp yielded 2.0960 mV versus the
  0.439-mV guardrail and itself triggered a `Vgd` SOA warning. Do not
  promote this physical candidate, start PVT/mismatch, or claim a verified
  physical code ramp. Next isolate clamp parasitics and reduce the 22-pump
  implementation while independently resolving bootstrap/clamp SOA.
- Commit status: ready to commit as
  `test: evaluate bootstrap bottom-plate sampling`; push was not requested.

## 2026-09-29 - Plan bootstrap sampling topology comparison

- Target: define the next bounded switch experiment after the held-error
  ablation and ineffective discharge-device resizing.
- Local change: added `plan/2026-09-29-bootstrap-bottom-plate-evaluation/plan.md`
  with a full-CDAC top-plate baseline, true bottom-plate sampling comparison,
  aperture and raw-error measurements, and an independent SOA gate.
- Remote OA change: none. No new simulation was run for this planning target.
- Validation: reviewed the existing macro connectivity and bootstrap reports;
  checked the plan's owned paths, numerical gates, and `git diff --check`.
- Status: plan ready for execution; no sampling-topology decision has been
  made. The planning change is committed locally and not pushed.

## 2026-08-31 - Screen bootstrap-driver error reduction

- Target: determine whether MN7/MN10 discharge strength, MP8 sizing, or
  external non-overlap can repair the complete bootstrap driver's held error
  before any OA edit.
- Local changed areas: audited diagnostic configuration, exact-export Spectre
  runner, analyzer/plots, result report, target plan, design log, and this log.
- Remote OA change: none. All generated decks assert the existing OA-export
  hash and restrict subcircuit edits to declared instance multipliers.
- Validation: 13/13 one-factor, 8/8 final combination, and 24/24 confirmation
  Spectre cases succeeded. One intermediate SSH upload reset was explicitly
  retained and its exact case reran successfully. Baseline 12.026 mV was
  reproduced; the reasonable and extreme candidates reached only 10.298 and
  9.097 mV. Python/YAML, provenance, result assertions, and both plots passed.
- Decision: do not update OA. Stronger discharge removes the later gate event
  but not the dominant immediate turn-off step, while reducing sample VGS and
  leaving 1.787-V/SOA concerns intact. Next evaluate independent isolation and
  charge-cancellation topology.
- Commit status: ready to commit as
  `test: screen bootstrap driver error reduction`; push was not requested.

## 2026-08-31 - Isolate bootstrap held-sample error

- Target: separate the selected main DNW switch's deterministic turn-off error
  from the complete bootstrap driver's contribution before changing OA or
  expanding PVT.
- Local changed areas: one diagnostic matrix, reproducible Spectre runner,
  analyzer/plots, focused result report, target plan, design log, and this log.
- Remote OA change: none. The analysis preserves the exact automatic OA export
  hash and exact main-device statement; all `SAR_ADC_T28` cellviews remained
  read-only.
- Validation: 40/40 Spectre 21.1 cases completed at TT/0.9 V/27 C. The complete
  differential pair reaches 12.026-mV raw error and -1.510% gain error; the
  absolute-off isolated main reaches 1.390 mV and -0.173%. The driver-added
  fitted term is -1.337%. Both generated plots were visually inspected and
  deterministic case/provenance/result assertions passed.
- Decision: correct the driver discharge/isolation/non-overlap path before
  another main-width sweep or global PVT. Raw 0.439-mV compliance and the
  separate approximately 1.79-V SOA issue remain open.
- Commit status: ready to commit as `test: isolate bootstrap held-sample error`;
  push was not requested.

## 2026-08-31 - Prototype transistor bootstrap driver

- Target: create and correlate the first finite-capacitor transistor-level
  bootstrap sampling switch before global PVT or production-cell design.
- Local changed areas: bootstrap OA create/readback/export automation,
  nominal and width-screen configurations, Spectre runner/analyzer, design
  documentation, manifest, target plan, and this log.
- Remote OA change: created only `SAR_ADC_T28/sar_bootstrap/schematic+symbol`
  and `tb_sar_bootstrap_transient/schematic`. Exact readback confirms the Abo
  NMOS multiplier, all B/D/G/S connections, dynamic input step, symbol ports,
  and zero check markers in both schematics.
- Validation: 9/9 nominal Cboot/input jobs and 12/12 main-width jobs completed
  in Spectre 21.1 from one unedited OA export hash. Acquisition, gate
  overdrive, and Cboot droop pass, but nominal held error reaches 6.463 mV
  versus 0.439 mV. The 2-um main switch remains the best screened seed.
- Blockers: core-device SOA warnings reach about 1.79-V terminal differences,
  and the signal-dependent held error is not fixed by main-switch width.
  Global PVT and production freeze are deliberately deferred.
- Commit status: ready to commit as
  `feat: prototype transistor bootstrap driver`; push was not requested.

## 2026-08-31 - Screen bootstrapped main switch

- Target: test the new bootstrapped-NMOS architecture at the main-switch level
  before building its transistor-level clock/charge driver.
- Local changed areas: PVT/device matrix, three OA create/export tools, batched
  Spectre runner, analysis/Pareto reporting, PDK mapping, manifest, target plan,
  and design documentation.
- Remote OA change: created only `tb_bootstrap_core_main_char`,
  `tb_bootstrap_dnw_main_char`, and `tb_bootstrap_18_main_char` schematics in
  `SAR_ADC_T28`. Each has one real PDK MOS and three sources with explicit body
  connection; existing SAR cellviews were not modified.
- Validation: 27/27 Spectre jobs completed with zero failures, producing 486
  Ron curves and 486 leakage measurements. Fourteen of 18 candidates met the
  global 1-kOhm Ron target. DNW L60/W2 is the preferred electrical seed at
  321.2-Ohm worst Ron and 143.8-nA maximum leakage.
- Scope boundary: the drive was ideal `Vgate=Vin+VDD`; no finite bootstrap
  capacitor, transient driver loss, foundry reliability sign-off, or production
  switch is claimed.
- Commit status: ready to commit as `feat: screen bootstrapped main switch`;
  push was not requested.

## 2026-08-31 - Screen transmission gate across PVT

- Target: compare standard- and high-VT plain transmission gates across the
  verified SS/TT/FF, supply, and temperature grid before creating a production
  sampling switch.
- Local changed areas: PVT configuration, audited corner/device mappings,
  high-VT OA create/export automation, batched Spectre runner, analysis and
  design documentation, manifest, target plan, and this log.
- Remote OA change: created only
  `SAR_ADC_T28/tb_tg_switch_hvt_char/schematic`. Readback confirmed the two
  intended HVT MOS devices, five sources, six nets, body ties, and no floating
  terminals; existing SAR cellviews were not modified.
- Validation: 27/27 batched Spectre jobs completed with zero errors, covering
  216 Ron curves and 216 off-leakage measurements. The batching exactly
  reproduced the independent TT nominal Ron and leakage. No candidate passed
  all PVT points; the target reports the bounded no-solution rather than
  relaxing 1 kOhm.
- Decision: do not create a production plain-TG sampling switch. The next
  target is a reliability-aware bootstrapped NMOS sampling switch; CDAC
  bottom-plate switches remain separate.
- Commit status: ready to commit as `feat: screen T28 switch across PVT`;
  push was not requested.

## 2026-08-31 - Characterize T28 transmission-gate switch

- Target: begin transistor-level CDAC/sampling design with a bounded PDK
  transmission-gate Ron and leakage fixture.
- Local changed areas: switch-characterization configuration, OA
  create/export automation, Spectre runner, analysis/reporting script, design
  documentation, manifest, target plan, and this log.
- Remote OA change: created only
  `SAR_ADC_T28/tb_tg_switch_char/schematic` with verified
  `tsmcN28/nch_mac` and `pch_mac` devices. Readback confirmed the two parallel
  channels, complementary gate sources, and explicit body connections. The
  unrelated unsaved ISCAS IO-ring session and dialog were not touched.
- Validation: the automatic OA export preserved the topology; all 12 TT/27-C
  Spectre Ron cases completed with zero errors. Four met the 1-kOhm limit. The
  minimum-width passing seed is `Wn=Wp=2 um, L=30 nm`, with 911.4-Ohm maximum
  Ron and 36.0-nA full-stress off leakage. It remains intentionally unfrozen
  pending PVT, leakage/hold, and transient error checks.
- Commit status: ready to commit as
  `feat: characterize T28 transmission-gate switch`; push was not requested.

## 2026-08-30 - Repair OA electrical macro-model loop

- Target: replace the floating structural OA top with an executable nominal
  closed-loop SAR electrical macro testbench.
- Local changed areas: controller scalar port contract, OA builder, focused
  contract test, electrical-macro documentation, manifest, target plan, and
  this log.
- Remote OA changes: created `sar_macro_controller_10b/symbol+veriloga` and
  rebuilt the owned CDAC, sampling, comparator, and top schematics. No
  placeholder controller schematic remains. Unrelated libraries, PDK data,
  and the unsaved `PLAYGROUND_AMP/canvas_test` window were untouched.
- Validation: all four schematic check-marker counts are zero; OA readback
  and automatic Spectre export contain the complete controller/CDAC path;
  Spectre 21.1 completed the unmodified exported circuit with zero errors.
  The code-768 case returned 768, asserted `VALID` after 49.5201 ns, stayed at
  0.08735 LSB maximum pre-compare residual, and resolved all ten decisions
  with the correct sign. The remaining five Spectre warnings are external
  AHDL/PDK environment notices.
- The full 11-case correlated Spectre regression also passed execution after
  the shared controller update. All six nominal code centers remained exact
  and below 0.25 LSB; the deliberate slow-RC, parasitic, and 1-fF-kickback
  cases continued to expose their expected resolution, code, and sign
  failures.
- Commit status: ready to commit as `fix: close OA SAR macro-model loop`; push
  was not requested.

## 2026-08-30 - Complete topology-aware electrical macro-model

- Target: replace isolated phase fixtures with one closed-loop pre-transistor
  electrical model for sampling, differential 5+5 CDAC switching, reference
  memory, comparator regeneration/reset/kickback, and SAR sequencing.
- Local changed areas: one parameter contract, electrical DUT and testbench,
  unrolled Verilog-A controller, analytical/Spectre runner, focused regression,
  architecture/result documentation, OA generator, manifest, and target plan.
- Remote OA changes: created only `sar_cdac_macro_10b`,
  `sar_sampling_macro`, `sar_comparator_macro`, their symbols, and
  `tb_sar_macro_transient` in `SAR_ADC_T28`. Existing OA cells, PDK content,
  and the unsaved `PLAYGROUND_AMP` schematic remained untouched.
- OA correction: enlarged CDAC switch spacing and replaced the compact
  generated CDAC symbol with a wide-pitch review symbol after readback exposed
  adjacent terminal-stub shorts. Final connectivity readback is clean and the
  hierarchical Spectre netlist exports successfully.
- Validation: exact capacitance-matrix/static regressions, eleven Spectre 21.1
  transients, waveform/metric extraction, focused tests, OA parameter/net
  readback, symbol-port audit, Check and Save, hierarchical netlist export,
  and visual review.
- Results: the canonical split load is `32Cu=219.53504 fF`. Six nominal code
  centers were exact with <=0.102 LSB settling residual and 49.52 ns latency.
  Deliberate slow-RC, assumed-parasitic, and 1-fF-kickback cases exposed
  expected failures.
- Scope limit: no PDK block or dimensions are frozen; random noise, nonlinear
  device effects, PVT, mismatch, reliability, and extraction remain open.
- Commit status: ready to commit as
  `feat: add topology-aware SAR macro-model`; push was not requested.

## 2026-08-30 - Complete module first-order models

- Target: close the abstraction layer between the behavioral ADC and
  transistor blocks with sampling acquisition, comparator regeneration, and
  clock-jitter sensitivity models.
- Local changed areas: tracked model inputs, two ideal Spectre decks, unified
  analysis/simulation runner, focused regression, architecture and result
  documentation, cell manifest, target plan, and this log.
- Remote OA changes: created only
  `SAR_ADC_T28/tb_sampling_acquisition/schematic` and
  `tb_comparator_regeneration/schematic`. Existing OA cells, PDK content, and
  the unrelated unsaved `PLAYGROUND_AMP` schematic remained read-only.
- Validation: both schematic readbacks and Virtuoso netlist exports, six
  Spectre 21.1 transients, analytical correlation, parametric grid/plot
  generation, and focused pass/fail/jitter tests.
- Results: at Cu=6.86047 fF, 40 ns acquisition permits 21.242 kΩ total source
  plus switch resistance. A 20 fF comparator regeneration node requires
  92.42 uS effective gm for a 1.5 ns decision from 0.25 LSB. The tracked clock
  point produces 0.182464 LSB RMS jitter error.
- Scope limit: comparator noise/offset, nonlinear switch behavior, charge
  injection, reference memory, PVT, mismatch, and extracted parasitics remain
  transistor-level work; no production device dimensions were frozen.
- Commit status: ready to commit as
  `feat: complete module first-order models`; push was not requested.

## 2026-08-30 - Establish CDAC/reference settling envelope

- Target: translate the sampling-noise and deterministic-settling allocations
  into a parameterized first-order feasibility envelope for the 5+5 split
  CDAC, reference path, and switch.
- Local changed areas: tracked YAML inputs, ideal Spectre deck, analytical and
  simulation runner, focused regression, architecture/design report, cell
  manifest, target plan, and this log.
- Remote OA changes: created only
  `SAR_ADC_T28/tb_cdac_ref_settling/schematic` from analogLib pulse,
  resistor, capacitor, and ground instances. PDK content and the unrelated
  unsaved `PLAYGROUND_AMP` schematic remained read-only.
- Validation: schematic connectivity/parameter readback, Virtuoso Spectre
  netlist export, four Spectre 21.1 transient runs, analytical correlation,
  1,440-point local grid generation, two focused tests, and plot inspection.
- Results: kT/C imposes `Cu >= 2.509 fF` in the parasitic-free 33-Cu
  equivalent. For Cu=6.86047 fF and a 3 ns window, total `Rref + Ron` must be
  at most 1.593 kΩ. Four Spectre residuals matched the analytical model within
  the specified 1% or 1 uV tolerance.
- Scope limit: no production capacitor or switch was selected; nonlinear Ron,
  reference memory/noise, switching trajectory, mismatch, charge injection,
  kickback, PVT, and parasitics remain open.
- Commit status: ready to commit as
  `feat: establish CDAC reference settling envelope`; push was not requested.

## 2026-08-30 - Establish T28 primitive characterization

- Target: create verified NMOS, PMOS, and MOM characterization schematics and
  obtain the first nominal PDK sizing data.
- Local changed areas: PDK/characterization mappings, reproducible audit,
  schematic creation, netlist export, Spectre run and extraction scripts,
  characterization report, cell manifest, target plan, and this log.
- Remote OA changes: created only `SAR_ADC_T28/tb_nmos_char/schematic`,
  `tb_pmos_char/schematic`, and `tb_cap_char/schematic`. The PDK and unrelated
  unsaved `PLAYGROUND_AMP` schematic remained read-only.
- Validation: bridge/CIW/Spectre health, PDK terminal/CDF audit, schematic
  connectivity and parameter readback, Virtuoso netlisting, three Spectre
  runs, PSF extraction, CSV/JSON generation, visual plot inspection, and six
  existing system regression tests.
- Results: 181-point nominal DC sweeps for each core MOS and a 141-point MOM
  AC sweep all completed with zero errors. At full 0.9 V bias, NMOS/PMOS
  currents are 728/615 uA per um. The 35.6304 fF MOM CDF value correlates to
  35.6355 fF in Spectre, a 0.0143% difference.
- Scope limit: one TT geometry/bias only; no PVT, output/length sweep, noise,
  Monte Carlo, mismatch, or extracted parasitics. The MOM fixture is not a
  final CDAC unit selection.
- Commit status: ready to commit as
  `feat: establish T28 primitive characterization`; push was not requested.

## 2026-08-30 - Record Verilog-A noise-injection learning

- Target: record the reviewed distinction between RMS parameters, event-level
  random realizations, and physical continuous-time noise modeling.
- Local changed areas: one learning note, its bounded plan, and this log.
- Remote OA changes: none; all remote state remained read-only.
- Validation: numerical cross-check against the design spec and fixed-seed
  Spectre summary, targeted Markdown inspection, owned-path review, and
  `git diff --check`.
- Commit status: ready to commit as
  `docs: record Verilog-A noise injection learning`; push was not requested.

## 2026-08-30 - Validate allocated Verilog-A random noise

- Target: enable the stage-1 sampling, comparator, and reference/switching
  random-noise allocations in a separate fixed-seed Verilog-A dynamic deck.
- Local changed areas: allocated-noise testbench, analysis and focused test
  support, verification/design records, target plan, and this log.
- Remote OA changes: none; all libraries, PDK content, and the unrelated
  unsaved `PLAYGROUND_AMP` schematic remained read-only.
- Validation: Spectre 21.1 completed 16,384 conversions with zero errors;
  Python compilation, four focused tests, YAML parsing, and diff checks
  passed.
- Results: 58.059 dB SNDR, 87.453 dB SFDR, and 9.352 bit ENOB versus a
  58.066 dB partial RSS prediction. Of 16,384 codes, 3,641 differed from the
  ideal sequence, all by one LSB, with -0.001 LSB mean error.
- Scope limit: clock jitter, unmodeled distortion, comparator offset, and
  CDAC settling were not included because they are not equivalent to the
  three enabled independent random sources.
- Commit status: ready to commit as
  `feat: validate allocated Verilog-A noise budget`; push was not requested.

## 2026-08-30 - Implement clocked Verilog-A SAR baseline

- Target: add the stage-3 cycle-accurate 10-bit fully differential Verilog-A
  model, curated timing/static/dynamic decks, and Python correlation flow.
- Local changed areas: Verilog-A model, three Spectre-format testbenches,
  EVAS dependency pin, run/analysis automation, focused tests, architecture
  and verification documentation, manifest, and target plan.
- Remote OA changes: none. The `SAR_ADC_T28` library, PDK, active CIW, and an
  unrelated unsaved `PLAYGROUND_AMP` schematic remained read-only.
- Local validation: EVAS 0.7.0 Python backend compiled the model with zero
  lint diagnostics and produced codes 768 and 256 for the held-input timing
  vectors; both conversions completed in 47.5 ns. Source-contract tests and
  1024-code/16,384-sample analysis regressions passed.
- Remote validation: configured the bridge's generic Cadence startup file to
  `/home/cshrc/.cshrc.cadence.IC618SP201`, matching the working `t28_io`
  profile. Spectre 21.1 then compiled the AHDL model and completed timing,
  8,192-sample static, and 16,384-sample coherent-sine runs with zero errors.
  Timing produced codes 768 and 256 with 47.5 ns conversion latency. Static
  analysis produced zero missing codes and zero ideal DNL/INL. Dynamic
  analysis produced 60.954 dB SNDR, 82.213 dB SFDR, and 9.833 bit ENOB, with
  0.001 dB SNDR delta from the Python golden result.
- Correlation correction: aligned the Python dynamic stimulus time with the
  actual 0.45 V crossing at the midpoint of the testbench's 20 ps sampling
  edge. The resulting 10 ps correction reduced code mismatches from 1,362 to
  zero; every mismatch before correction was only one LSB.
- Commit status: committed locally as
  `feat: add clocked Verilog-A SAR baseline`; push was not requested.

## 2026-08-30 - Record error-budget learning

- Target: record the human-requested learning process behind the first
  top-down module error allocation.
- Local changed areas: one note under `docs/learning/`, its target plan, and
  this maintenance entry.
- Remote OA changes: none; all Virtuoso and PDK state remained read-only.
- Validation: numerical cross-check against the tracked design spec and
  behavioral summary, targeted Markdown inspection, owned-path review, and
  `git diff --check`.
- Commit status: ready to commit as
  `docs: record top-down error budget learning`; push was not requested.

## 2026-08-30 - Complete behavioral baseline

- Target: complete the system error budget and bit-accurate ideal model for
  the default 10-bit, 10 MS/s fully differential SAR ADC.
- Local changed areas: design spec, dependency pin, behavioral model, unified
  analysis runner, focused system regression, architecture/verification/error
  budget documentation, and target plan.
- Remote OA changes: none; `SAR_ADC_T28` and all Virtuoso state remained
  read-only.
- Validation: YAML parse, Python compile, two focused regression tests, full
  1024-code ramp, 16,384-sample near-Nyquist coherent sine, JSON/plot artifact
  generation, and visual plot inspection.
- Results: zero missing codes and zero ideal DNL/INL; 60.953 dB SNDR,
  82.033 dB SFDR, and 9.833 bit ENOB at -1 dBFS; allocated error budget
  projects 9.140 bit ENOB with 0.844 dB SNDR margin.
- Commit status: ready to commit as `feat: add SAR ADC behavioral baseline`;
  push was not requested.

## 2026-08-30 - Adopt SAR ADC Agent workflow

- Target: adapt the portable plan-log-experience kernel for a split local Git
  and remote Virtuoso OA project, then publish the repository.
- Local changed areas: root Agent rules, project README, target planning,
  maintenance-log, and experience-note templates.
- Remote OA changes: none; `SAR_ADC_T28` remained read-only for this target.
- Validation: documentation diff checks, targeted rule-presence checks, owned
  path review, Git state review, and GitHub remote verification.
- Commit status: ready to commit as `chore: adopt SAR ADC agent workflow` and
  push to the user-authorized `chenzc24/sar-adc-t28` repository.

## 2026-08-30 - Create remote Virtuoso library

- Target: create an empty remote `SAR_ADC_T28` OA library.
- Local changed areas: idempotent library creation script, cell manifest, and
  design log.
- Remote OA changes: created `/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28`
  and bound it to `tsmcN28`; no cells were created.
- Validation: bridge/API readback verified library name, path, and technology;
  filesystem inspection showed only OA library metadata.
- Commit status: committed in `f60725f`.

## 2026-08-30 - Scaffold SAR ADC project

- Target: establish the local SAR-ADC repository and default design skeleton.
- Local changed areas: configuration, architecture and verification docs,
  model/netlist/script/verification directories, artifact boundaries, and Git
  ignore policy.
- Remote OA changes: none in this target.
- Validation: Python automation compiled and the initial repository state was
  reviewed.
- Commit status: committed in `069bd7f`.
