# Maintenance Log

This file records factual project maintenance. Circuit and architecture
decisions remain in `docs/design_log.md`; reusable lessons require a separate
human-triggered note in `docs/experience/`.

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
