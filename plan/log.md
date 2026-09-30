# Maintenance Log

## 2026-09-30 - Screen T28 GMAIN hold pull-down in full CDAC

- Replaced only the copied-netlist ideal `SHOLD` relay with a real T28
  `nch_18_mac` NMOS, sweeping multiplicity 4/16/64 while retaining ideal
  `STRACK`, clamp and clock driver. No OA or PDK changes.
- Seven zero-error Spectre 21.1 transients: five inputs at `multi=4`,
  +0.8 V at `multi=16/64`. Five-point bottom maximum raw error was
  0.004223 mV and representative gate-off margin before reset at least
  0.846 ns. Top-control error still reached 6.822 mV. Printed MP8 SOA
  warnings and 550-11,010 suppressed warnings prevent signoff.
- Validated hashed OA-source and ideal-control deck identity, a bounded
  deck diff, phase order, saved terminal currents, source-current reduction,
  warning inventory, Python compile and per-case JSON reanalysis. Results
  and raw logs are ignored under `output/bootstrap_t28_hold_pulldown/`;
  curated evidence is in `docs/bootstrap_t28_hold_pulldown.md`.
- Commit policy: `test: screen T28 bootstrap hold pull-down`; local only,
  no push requested.

## 2026-09-30 - Review maintainability boundaries

- Moved graph composition from browser code into one declarative graph source;
  build resolves analysis, figure, experiment and topology references. Retired
  obsolete flow and combined topology files (recoverable through Git).
- Split presentation formatting and static-diagram adapter; separated topology
  reasoning from image coordinates. Added reviewed evidence/connectivity baselines
  and read-only --impact reporting, with affected-node review status.
- Validation: 22 focused tests, formula regression, JS/build/diff checks, 31-node
  migration comparison and browser navigation/device-selection smoke pass.
- No OA, Canvas connection, simulator or experimental result changes. Screenshot:
  output/review/refactor-preview.png. Concurrent circuit plan preserved.
- Commit policy: refactor: separate review data rendering and impact checks;
  local only, no push requested.

## 2026-09-30 - Screen protected bootstrap in full CDAC

- Target: integrate the independent OFF_MAIN-before-reset protected-bootstrap
  copied netlist into the exact full 5+5 CDAC exports and compare top/bottom
  paths, ideal/T28 top clamps, and VIN/VSS ideal main-gate hold biases.
- Local changed areas: bounded plan, exact-hash copied-deck generator and
  analyzer, result report, design-log entry, and this log. Fifteen decks,
  logs, PSF, and per-case/aggregate JSON remain ignored under
  `output/bootstrap_full_cdac_isolation/`.
- Remote OA changes: none. Original OA exports and PDK files remained
  read-only. Spectre 21.1 ran only generated copied decks via `t28_io`.
- Validation: fifteen zero-error TT/0.9-V/27-C transients, hashed source
  checks, 24-call/full-CDAC deck-contract checks, finite waveform reads,
  phase-order checks, targeted MN11/reference/source-current probe,
  warning inventory, Python compile, JSON reanalysis, and owned diff review.
  With ideal clamp, VIN-relative hold failed at ±0.8 V by 6.261925 mV;
  ideal VSS-off hold reduced five-point bottom raw error to 0.004218 mV
  maximum, but printed MP8 SOA warnings. T28 clamp + VSS-off still had
  -7.538001 mV raw error and printed clamp SOA warnings. No OA promotion.
- Commit policy: `test: screen protected bootstrap in full CDAC`; local
  commit only, no push requested.

## 2026-09-30 - Simplify topology review copy

- Removed repeated disclaimers and duplicate headings; moved assumptions/version
  metadata into a disclosure. Retained phase conditions and connection/inference/
  verification content. No netlist, image, simulation or remote changes.
- Build, JS syntax, diff check and browser visual inspection passed.
- Screenshot: output/review/topology-compact-preview.png. Local commit only;
  style: simplify topology review copy. No push.

## 2026-09-30 - Static Bootstrap topology linkage sample

- Preserved user-supplied netlist/image separately from the T28 DUT; added 15
  instance anchors, five groups, four phases and three typed analysis topics.
  Device selection displays body-inclusive terminals and reverse topic links.
- Sampling review entries open a scoped static-image dialog; no actual Canvas
  connection or remote OA mutation, and no simulation/model-validity claim.
- Validation: 18 focused tests, build/JS/diff checks; browser keyboard phase/group/
  device/topic navigation, image highlights, Escape and narrow layout verified.
  Pointer automation remains outside acceptance. Preview: output/review/topology-preview.png.
- Commit locally as feat: add bootstrap topology review sample; no push requested.

## 2026-09-30 - Screen bootstrap turn-off charge

- Target: distinguish ideal-relay control-clock timing from actual MN11 gate
  slew, and measure held-load sensitivity and charge balance for the
  independent OFF_MAIN-before-reset candidate.
- Local changed areas: one bounded plan, copied-netlist generator/analyzer,
  result report, design-log entry, and this log. Nine exact decks, logs, PSF,
  and JSON are ignored under `output/bootstrap_turnoff_charge_screen/`.
- Remote OA changes: none; the original hashed OA export and PDK stayed
  read-only. Spectre 21.1 ran only copied decks via `t28_io`.
- Validation: nine zero-error TT/0.9-V/27-C transients, finite PSF, output
  KCL and load-charge checks, deck-diff review, zero printed CMI warnings,
  and no diagnostic terminal-level crossings. The 1-ohm relay makes a
  1.6-ps actual gate edge despite a 100-ps clock. Raising SHOLD resistance
  to 20 kohm stretches gate fall to 293 ps but worsens held error to
  -2.647 mV. No case meets the 0.439-mV raw-error gate.
- Commit policy: `test: screen bootstrap turn-off charge`; no push requested.
- Unrelated untracked Canvas-review paths and a modification to
  `scripts/review/build.py` appeared during execution and were left untouched.

## 2026-09-30 - Node analysis and result-figure entries

- Added 24 module-node analysis lists, six scoped/hash-pinned figure bindings,
  embedded image dialog and tighter module layout. Local review sources/build/
  focused tests only; remote OA and ongoing circuit experiments untouched.
- Validation: 17 Python tests, formula regression and syntax checks pass. Browser
  verified all figure loads and keyboard navigation/dialog behavior, node coverage,
  and narrow layout. Automated pointer input did not actuate controls this session;
  pointer acceptance remains unconfirmed. No simulation rerun.
- Artifacts: output/review/index.html, node-analysis-preview.png, figure-preview.png.
- Commit policy: feat: add node analysis and result figures; local only, no push.

## 2026-09-30 - Consolidate review into module branch maps

- One global map now opens five module branches combining constraints, progress,
  results and next actions. Details expand inside nodes; Canvas slots stay with
  their module. Removed separate tabs, block-map panel and bottom detail panel.
- Owned changes: review/app, review README and bounded target plan. No remote
  OA changes, simulation, evidence refresh or source-lock acknowledgment.
- Validation: 13 data tests, formula regression, JS syntax, branch navigation,
  inline expansion, narrow local scrolling and browser error check passed.
- Generated preview: output/review/index.html; loopback port 8765. Local commit
  policy: feat: consolidate review into module branch maps; no push requested.

This file records factual project maintenance. Circuit and architecture
decisions remain in `docs/design_log.md`; reusable lessons require a separate
human-triggered note in `docs/experience/`.

## 2026-09-30 - Isolate bootstrap output before reset

- Target: test the independent OFF_MAIN-before-PHIB-reset sequence on the
  existing full-control bootstrap export, including a no-reset control and
  a short VIN-step isolation challenge.
- Local changed areas: one bounded plan, exact-export copied-netlist
  generator/analyzer, result report, design-log entry, and this maintenance
  entry. Six decks, PSF/logs and JSON are ignored under
  `output/bootstrap_isolate_before_reset/`.
- Remote OA changes: none; direct-SSH Spectre 21.1 ran copied decks only.
  Original OA, original hashed netlist and PDK files stayed read-only.
- Validation: six zero-error TT/0.9-V/27-C transients, hash check, finite
  aligned waveforms, source-resistor and MN11/load KCL, full-transient
  PDK-terminal diagnostic comparison, zero printed CMI warnings, Python
  compile, JSON parse and owned diff check. Delayed PHIB reset sequence contributes
  about +0.080 mV after a -2.53-mV turn-off error; best held error remains
  -2.452 mV, failing the 0.439-mV gate. Ideal relays are not physical T28.
- Commit status: commit locally as
  `test: isolate bootstrap output before reset`; no push requested.

## 2026-09-30 - Simplify review into block-linked flow diagrams

- Target: respond to user review by replacing the flat, document-centric UI
  with explicit circuit correspondence and connected derivation/progress graphs.
- Local changes: review frontend, extracted flow content and latest A/B summary,
  public-payload filtering, focused tests, maintenance guide and target plan.
  Repository document links, raw source viewer, sidebar, hashes and scenario
  controls were removed from the frontend. Internal provenance stays in source
  data/build checks; generated HTML/data contains no report documents or paths.
- The separate committed `e0c12e7` A/B report was read and summarized without
  modifying any circuit-target file. Ideal split-gate -2.482-mV results are
  explicitly mechanism bounds, not implemented T28 acceptance.
- Validation: 13 Python contract tests; existing formula/observation gates;
  Python compile and JS syntax. Browser checked global and Bootstrap flow views,
  node/block highlighting and explanations, no document links/viewer, no edge
  crossing unrelated Bootstrap nodes, and 390px graph-local scrolling without
  page overflow. No browser errors/warnings in the inspected log.
- Remote OA/Canvas changes: none; no simulation. Existing loopback preview
  remains available at port 8765. Local commit only; no push requested.

## 2026-09-30 - Screen bootstrap netlist A/B variants

- Target: rapidly test hold-leakage removal, PHIB timing, and ideal
  source-relative main-gate steering on an exact OA-exported full-control
  bootstrap netlist.
- Local changed areas: target plan, one controlled variant generator/runner,
  result report, bounded design-log entry, and this maintenance entry.
  Eight copied decks, Spectre logs/PSF, and JSON remain ignored under
  `output/bootstrap_netlist_fast_ab/`. The unrelated design-review
  workbench was left untouched.
- Remote OA changes: none; all simulations used direct SSH Spectre 21.1 and
  left OA, original export, and PDK models read-only.
- Validation: original SHA-256 checked; eight TT/0.9-V/27-C transients
  completed with zero Spectre errors; finite/aligned waveforms, input
  source-resistor balance, output-node KCL, full-transient MOS terminal
  diagnostic limits and printed CMI warnings reviewed. All variants fail
  0.439-mV raw held-error target. The body-only core variant also has
  five printed CMI warnings; ideal-relay bounds are not T28 implementations.
- Commit status: commit only this target locally as
  `test: screen bootstrap netlist A/B`; no push requested.

## 2026-09-30 - Add local design review workbench v1

- Target: link formal benchmark constraints, module workflow and a future
  Analog Canvas slot in a maintainable local review interface.
- Local changed areas: `review/` source/data/fingerprints/maintenance guide,
  `scripts/review/build.py`, focused `verification/review/` checks, README,
  target plan and this entry. Generated self-contained HTML/data remain ignored
  under `output/review/`. Existing specs and circuit reports remain read-only.
- Content: 13 metric nodes, 12 steps and eight evidence records; sampling and
  Bootstrap form the vertical slice. Other modules explicitly retain partial
  coverage. September 30 current-path diagnosis is not presented as a repair.
- Validation: ten Python contract tests, Node benchmark/formula/gate/scenario
  checks, Python compile, JS syntax and diff checks. Browser-tested all three
  views, module/evidence links, embedded source reading, candidate/reset and
  320/390-pixel no-overflow layouts. No captured browser errors/warnings.
  The in-app browser disallows file URLs; no bypass was attempted. The verified
  preview is loopback-only at port 8765. No external frontend assets are needed.
- Remote OA/Canvas changes: none; historical netlist hashes are explicitly
  not a fresh readback. Concurrent bootstrap fast-A/B files are unrelated and
  excluded from this commit. No simulator was run for this frontend target.
- Commit policy: local `feat: add local ADC design review workbench`; no push.

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

## 2026-09-30 - Review sampling causal history

- Reorganized the sampling panel into eight key nodes, two current design
  branches and joint acceptance; refreshed global/CDAC summaries.
- Curated reset-isolation, edge/load and full-CDAC evidence. Node details now
  show methods, conditions and result tables without repository document links.
- Kept lumped-load and full-CDAC fixtures distinct; retained ideal-control and
  stress qualifications, and the separate static Canvas sample.
- Validation: 22 focused tests, formula regression, build/check, JS syntax and
  diff check passed. Browser verified result table, figure/topology entries and
  branch layout with no console errors. Preview: output/review/sampling-flow-preview.png.
- Remote OA changes: none. Local scoped commit; no push. Concurrent circuit
  files and its separate maintenance-log entry are excluded.

## 2026-09-30 - Compact review presentation

- Reduced card padding, duplicate heading chrome and action rows; preserved all
  visible reasons and all 31 nodes' detailed content and evidence bindings.
- Moved method/experiment tables to a shared dialog, keeping flow geometry
  stable. Promoted sampling numerical comparisons into the main diagram.
- Validation: 22 tests, formulas, build, JS syntax, diff check; browser verified
  desktop/narrow layout, dialogs, figures, topology, Escape and no console errors.
- Artifact: output/review/compact-preview.png. No circuit/OA changes or push;
  local commit: style(review): compact flow layout and experiment details.

## 2026-09-30 - Stage-specific isolation diagram

- Added supplied isolated-GMAIN drawing and exact draft netlist as a separate
  static topology snapshot; retained original pre-isolation diagram.
- Bound isolation and later relevant sampling nodes to the new version, with
  MN11/net1 and Cu/VOUT/VCM readback. TRACK/OFF remain drawing-only, not invented
  netlist devices; Cu is not represented as a complete CDAC.
- Validation: 23 tests, build, JS syntax and diff check; browser verified old/new
  diagrams, MN11/Cu selection and no console errors. Preview:
  output/review/isolated-diagram-preview.png.
- No remote OA edits or simulation. Scoped local commit; no push. Unrelated
  top-plate GMAIN device experiment files preserved.
