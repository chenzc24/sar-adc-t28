# CDAC And Reference Settling Envelope

## Goal

Establish the first module-level settling and sampling-capacitance feasibility
envelope for the fully differential 5+5 split CDAC. Relate unit capacitance,
equivalent per-side CDAC capacitance, reference/switch resistance, and the
available bit-settling window to the existing 0.25 LSB deterministic settling
guardrail and 0.18 LSB RMS sampling-noise allocation.

## Dirty-State Note

The worktree starts clean. `main` is one local commit ahead of `origin/main`
at `eb68f98`; that unpublished characterization commit is an intentional
dependency and is not rewritten or pushed by this target.

## Local Owned Files

- `config/cdac_reference_settling.yaml`
- `docs/cdac_reference_settling.md`
- `docs/architecture.md`
- `docs/design_log.md`
- `netlist/tb/tb_cdac_reference_settling.scs`
- `scripts/analysis/run_cdac_reference_settling.py`
- `scripts/virtuoso/create_cdac_ref_settling.py`
- `verification/system/test_cdac_reference_settling.py`
- `virtuoso/cell_manifest.yaml`
- `plan/2026-08-30-cdac-reference-settling-envelope/plan.md`
- `plan/log.md`

## Remote OA Owned Objects

- `SAR_ADC_T28/tb_cdac_ref_settling/schematic`

No symbol, layout, Maestro, production CDAC, reference-buffer, switch, or
integrated-ADC cellview is owned by this target.

## Read-Only State

- all `tsmcN28` PDK content and model files
- every remote library other than `SAR_ADC_T28`
- all existing `SAR_ADC_T28` cellviews except the one explicitly named above
- the unrelated unsaved `PLAYGROUND_AMP/canvas_test/schematic` window
- stage-1 through stage-4A models, results, and characterization schematics
- Git history and the unpublished `eb68f98` commit

## Assumptions And Dependencies

- Architecture: fully differential 10-bit 5+5 split CDAC.
- Ideal subarray total per side is `32*Cu`; the ideal attenuation capacitor is
  `32/31*Cu`, whose series combination with the LSB subarray contributes
  `1*Cu` at the comparator-side top plate. The first-order per-side load is
  therefore `Cside = 33*Cu` before parasitics.
- Differential sampling-noise estimate is conservatively
  `sqrt(2*k*T/Cside)` because the two sampled sides contribute independently.
- The 5 ns bit period is fixed by the 200 MHz timing contract. Available CDAC
  settling time is not yet fixed; scan 2, 2.5, 3, and 4 ns.
- Use a 1.8 V differential worst-case step for the deterministic envelope.
  The remote schematic represents this as a 0.9 V single-ended step and the
  analysis doubles its residual error.
- `Rref + Rswitch` is a first-order Thevenin resistance. Reference memory,
  decoupling, code-dependent switching current, switch nonlinearity, charge
  injection, bridge/parasitic ratio error, and comparator kickback are outside
  this target and remain explicit follow-on work.
- Unit-capacitance candidates are scanned parametrically. The characterized
  6.86047 fF default `cfmom_2t` and 35.6304 fF specimen are comparison points,
  not automatically selected CDAC units.

## Implementation Steps

1. Preflight bridge, CIW, active windows, target library, and target-cell
   absence; audit analogLib source/resistor/capacitor terminals and CDF names.
2. Derive the split-array capacitance, differential `kT/C` floor, exponential
   settling constraint, and allowed resistance envelope from tracked specs.
3. Add a parameterized ideal Spectre deck and analysis runner that writes
   concise CSV/JSON/plots under `output/cdac_reference_settling/`.
4. Create `SAR_ADC_T28/tb_cdac_ref_settling/schematic` as a visual and
   netlistable single-ended half-circuit equivalent using only analogLib
   source, resistor, and capacitor elements.
5. Read back and netlist the remote schematic. Compare representative Spectre
   transient points against the closed-form exponential result.
6. Record the feasible region, limitations, and next transistor-level
   questions without selecting a production capacitor or switch topology.

## Validation And Pass Criteria

- Bridge 0.8.0+, CIW, and Spectre are healthy; the target library remains
  bound to `tsmcN28`.
- The unrelated unsaved window remains untouched.
- The remote schematic contains only the intended analogLib instances and
  named nets, passes schematic readback, and exports a Spectre netlist.
- Closed-form results reproduce the tracked LSB/noise/settling budgets.
- At least three representative Spectre transient points complete with zero
  errors and agree with the analytical residual within 1% or 1 uV, whichever
  is larger.
- The focused regression checks one expected noise failure, one settling
  failure, and one feasible candidate.
- YAML parsing, Python compilation, focused execution, visual plot review,
  `git diff --check`, status review, and owned-path review pass.

## Expected Artifacts

- tracked design inputs and conclusions in `config/` and `docs/`
- ignored generated CSV, JSON, plots, Spectre decks, PSF, and logs under
  `output/cdac_reference_settling/`
- ignored remote schematic readback and exported netlist packages under
  `output/cdac_reference_settling/virtuoso/`

## Commit And Push Intent

Commit completed work locally as:

```text
feat: establish CDAC reference settling envelope
```

Push policy: not requested.

## Completion Record

- Completed the analytical 1,440-point feasibility grid and both envelope
  plots from the tracked YAML inputs.
- Created, read back, and netlisted only the owned remote
  `SAR_ADC_T28/tb_cdac_ref_settling/schematic` cellview.
- Completed four Spectre 21.1 transients with zero warnings/errors; every
  residual matched the closed-form result within the declared tolerance.
- Confirmed explicit noise-fail, settling-fail, and feasible regression points.
- No capacitor, switch, or reference-buffer production topology was frozen.
