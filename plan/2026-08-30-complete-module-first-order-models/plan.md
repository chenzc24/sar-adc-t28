# Complete Module-Level First-Order Models

## Goal

Complete the remaining module-level first-order models between the behavioral
ADC and transistor implementation: sampling acquisition, comparator
regeneration, and clock-jitter sensitivity. Reuse the completed CDAC/reference
settling envelope and finish this abstraction layer without claiming that a
linear whole-ADC model or production transistor sizing has been completed.

## Dirty-State Note

The worktree starts clean. `main` is two local commits ahead of `origin/main`:
the T28 primitive characterization and CDAC/reference settling envelope are
intentional dependencies. They are not rewritten or pushed in this target.

## Local Owned Files

- `config/module_first_order.yaml`
- `docs/module_first_order_models.md`
- `docs/architecture.md`
- `docs/design_log.md`
- `netlist/tb/tb_sampling_acquisition.scs`
- `netlist/tb/tb_comparator_regeneration.scs`
- `scripts/analysis/run_module_first_order.py`
- `scripts/virtuoso/create_module_first_order.py`
- `verification/system/test_module_first_order.py`
- `virtuoso/cell_manifest.yaml`
- `plan/2026-08-30-complete-module-first-order-models/plan.md`
- `plan/log.md`

Generated artifacts remain ignored under `output/module_first_order/`.

## Remote OA Owned Objects

- `SAR_ADC_T28/tb_sampling_acquisition/schematic`
- `SAR_ADC_T28/tb_comparator_regeneration/schematic`

No production sampling switch, comparator, clock generator, symbol, layout,
Maestro view, or existing schematic is owned by this target.

## Read-Only State

- all `tsmcN28` PDK content and model files
- every remote library other than `SAR_ADC_T28`
- every existing `SAR_ADC_T28` cellview, including
  `tb_cdac_ref_settling/schematic`
- the unrelated unsaved `PLAYGROUND_AMP/canvas_test/schematic` window
- prior behavioral, Verilog-A, PDK characterization, and CDAC/reference results
- Git history and both unpublished local commits

## Assumptions And Dependencies

- Continue the ideal split-array load `Cside = 33*Cu` before parasitics.
- Sampling acquisition is a first-order `Rsource + Ron` path driving Cside.
  Use the fixed 40 ns acquisition phase and the existing 0.25 LSB residual
  guardrail; kT/C remains the same sampled-capacitance constraint already
  derived for the CDAC.
- Comparator regeneration is not modeled with AC gain. Use the linearized
  positive-feedback equation `tau_reg = Cnode/gm_eff` and
  `tdecision = tau_reg*ln(Vdecision/Vinitial)`. The direct mapping from
  input-referred initial differential to internal latch differential is a
  unit-gain sensitivity assumption, not a StrongARM topology claim.
- Use 0.25 LSB as the smallest deterministic comparator input in the first
  decision-time sweep and 0.45 V as the resolved differential threshold.
- Map representative `gm_eff` values to the characterized nominal minimum-L
  NMOS `gm/Id ~= 15 1/V` point only as a width/current scale reference. The
  effective latch gm and node capacitance remain topology-dependent.
- Clock jitter is a sampled-sine timing sensitivity, not an AC circuit. Use
  the tracked 20 ps RMS target at 4.5 MHz and -1 dBFS.
- EVAS is not applicable because the two circuit models require KCL/KVL and
  analog transient solving; remote Spectre is the simulation authority.

## Implementation Steps

1. Re-run bridge/CIW/Spectre preflight, verify the two target cells are absent,
   and audit only the analogLib primitives required by the equivalent models.
2. Derive sampling acquisition resistance/bandwidth envelopes across Cu and
   verify representative RC cases with Spectre.
3. Derive comparator regeneration time across `gm_eff`, Cnode, and initial
   input; verify representative exponential cases with Spectre.
4. Derive input-referred RMS jitter error versus input frequency and amplitude;
   report the tracked near-Nyquist point without creating a false AC model.
5. Create, read back, and netlist the two owned remote equivalent schematics.
6. Record the feasible regions, PDK sizing implications, and explicit limits.

## Validation And Pass Criteria

- Bridge 0.8.0+, CIW, and Spectre are healthy; the target library remains
  bound to `tsmcN28` and the two target cells are initially absent.
- Sampling and comparator remote schematics contain only the audited analogLib
  instances and intended nets, pass readback, and export Spectre netlists.
- At least three sampling and three comparator Spectre transients complete
  without errors and match their analytical exponential result within 1% or
  1 uV / 1 ps, whichever applies.
- Focused tests cover sampling pass/fail, comparator pass/fail, and the tracked
  jitter point.
- YAML parsing, Python compilation, focused system tests, plot inspection,
  complete owned-path review, `git diff --check`, and final status review pass.

## Expected Artifacts

- tracked inputs, runner, ideal decks, conclusions, and regression tests
- ignored analytical tables, plots, generated decks, waveforms, and logs under
  `output/module_first_order/`
- ignored remote readback and netlist exports under
  `output/module_first_order/virtuoso/`

## Commit And Push Intent

Commit completed work locally as:

```text
feat: complete module first-order models
```

Push policy: not requested.

## Completion Record

- Generated sampling, comparator, and clock-jitter grids and inspected all
  three result plots.
- Completed three sampling and three comparator Spectre 21.1 transient cases;
  all six matched their analytical exponential model within the stated
  tolerance and included explicit pass and fail cases.
- Created, read back, and netlisted only the two owned remote equivalent
  schematics. The comparator VCCS netlist polarity was explicitly verified.
- Reproduced the stage-1 20 ps / 4.5 MHz jitter result exactly.
- Kept all production circuit dimensions and unresolved physical effects open
  for the transistor-level design loop.
