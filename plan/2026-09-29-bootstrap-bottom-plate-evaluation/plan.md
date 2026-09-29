# Bootstrap sampling topology and turn-off evaluation

## Status and goal

Ready for execution. This record defines the next bounded switch-design
target; writing the plan does not start an OA or Spectre experiment.

Determine whether true bottom-plate sampling in the differential 5+5 split
CDAC reduces the T28 bootstrap sampling path's signal-dependent held error.
Compare it with the existing top-plate sampling arrangement under identical
device, input, timing, and PDK conditions. Resolve which turn-off event defines
the aperture and which event creates the residual error. The output is a
measured topology decision, not a production sampling cell.

The current simple capacitor-to-ground fixture reports 12.026 mV maximum raw
differential held error versus the 0.439 mV (0.25 LSB) allocation. That value
is motivation, not a directly comparable baseline for a full CDAC fixture.
The latter must establish its own top-plate baseline before comparing a
bottom-plate candidate.

## Dirty-state and remote preflight note

At planning time `git status --short --branch` shows a clean `main`, five
commits ahead of `origin/main`, at `36ee004`. On 2026-09-29, Bridge 0.8.0
profile `t28_io`, the CIW on `thu-wei`, Spectre 21.1, and the
`SAR_ADC_T28` -> `tsmcN28` binding were verified. Recheck all of them,
windows, locks, and the exact OA export before executing the experiment.

The existing `sar_bootstrap` and macro-model cellviews are read-only. If a
proposed new cell name already exists, inspect ownership and revise this
plan before creating or editing it. Stop on an unsaved user-owned window,
unexpected technology binding, modal dialog, or lock.

## Local owned files for execution

- `plan/2026-09-29-bootstrap-bottom-plate-evaluation/plan.md`
- `config/bootstrap_bottom_plate_eval.yaml`
- `scripts/characterization/create_bootstrap_bottom_plate_eval.py`
- `scripts/characterization/run_bootstrap_bottom_plate_eval.py`
- `scripts/characterization/analyze_bootstrap_bottom_plate_eval.py`
- `docs/bootstrap_bottom_plate_eval.md`
- bounded entries in `docs/design_log.md`, `plan/log.md`, and the Virtuoso
  cell manifest if the new OA cellviews are created

Generated netlists, PSF data, waveforms, case metrics, and plots belong under
ignored `output/bootstrap_bottom_plate_eval/`. Execution may narrow this file
set; any expansion requires a plan update first.

## Remote OA owned objects for execution

- `SAR_ADC_T28/sar_cdac_bottom_plate_eval_10b/schematic` and `/symbol`
- `SAR_ADC_T28/tb_sar_bottom_plate_eval/schematic`

These are proposed new experimental cellviews only. The existing
`SAR_ADC_T28/sar_bootstrap`, `sar_cdac_macro_10b`, their symbols and
testbenches remain read-only. A successful analysis does not authorize
overwriting them; promotion is a separate target.

## Read-only dependencies and shared contracts

- T28 PDK models, `tsmcN28`, foundry reliability rules, and shared libraries
- the automatic OA export of the existing bootstrap prototype and its source
  hash; the selected DNW main device is L=60 nm, W=2 um, CBOOT=200 fF
- the existing differential split-CDAC topology: 31-Cu MSB active array,
  32-Cu LSB array including dummy, `(32/31)Cu` bridge, and nominal
  `32Cu=219.53504 fF` comparator-side load at `Cu=6.86047 fF`
- 10-bit, 10-MS/s timing contract: 40 ns acquisition, 3 ns CDAC settling,
  1.5 ns comparison, and 60 ns conversion allocation
- current 0.439-mV raw deterministic sampling/settling guardrail, 20-ps RMS
  sample-jitter allocation, and previously recorded SOA warning evidence

## Experimental method

1. **Establish a comparable baseline.** Read back and export the exact
   existing OA bootstrap. Build a full differential 5+5 CDAC sample/hold
   fixture using the existing top-plate sampling connection: input through
   `sar_bootstrap` to the comparator-side top nodes, bottom plates at VCM.
   Preserve the same source resistance, input range, clock edges, unit
   capacitance, and measurement instants for every variant. Confirm the
   charge-conservation prediction and record its raw error at the new
   fixture's aperture and hold instants.
2. **Evaluate true bottom-plate sampling.** During acquisition, hold the
   comparator-side top and split-array internal nodes at the defined VCM
   state while the input drives the selected bottom plates. First open the
   VCM/top-node clamp; after a controlled delay, open the input/bottom-plate
   switches; only then apply conversion references. Derive the new
   charge-conservation transfer, comparator polarity, common-mode movement,
   bridge-node behavior, and SAR bit weights before judging output codes.
   Test the clamp initially as an ideal timing element to isolate the
   sampling-order effect, then include a T28 device clamp to measure its
   injection and leakage. Keep the same per-switch bootstrap topology and
   dimensions, and report the changed input/clock loading from distributing
   switches across the array. Never claim the ideal-clamp result as a
   physical cell result.
3. **Sweep only the necessary timing.** Parameterize clamp-to-input turn-off
   delay and edge placement around the established acquisition boundary.
   Measure the actual aperture from the top-clamp opening, as well as
   acquisition, immediate top-clamp step, bottom-switch step, reference
   transfer, and hold drift. Include both clock polarities and verify that
   no source/reference path shorts during handoff.
4. **Confirm across input.** Screen `Vdiff=-0.8,-0.4,0,+0.4,+0.8 V` at
   0.45-V input common mode plus low/mid/high single-ended points. For the
   best candidate, check code centers and a static transfer/ramp in the
   full CDAC fixture. Keep raw differential error, fitted gain, and
   post-fit residual separate; no calibration is assumed.
5. **Attribute the remainder.** If bottom-plate order materially reduces
   the error but misses 0.439 mV, identify whether the remaining step comes
   from boosted-path isolation, the top clamp, or the bottom input switch.
   Specify a later bounded target for independently timed isolation and/or
   complementary dummy compensation; do not combine those interventions
   with this topology comparison.
6. **Check reliability independently.** For every T28-device candidate,
   retain Spectre SOA warnings and maximum per-device terminal voltages.
   Record the foundry rule/allowed transient condition before proposing a
   protected pump or a different device class. A better held voltage does
   not clear the existing approximately 1.787-V stress.

The OA schematics are the electrical source of truth. Export them automatically
and keep the exported circuit section unedited; parameterized analysis
wrappers may set stimuli, model section, saves, and analysis statements.

## Validation and decision gates

- All fixtures use the same T28 bootstrap main device and driver, nominal
  TT/0.9 V/27 C first, with exact OA revision/export provenance.
- An analytical charge-conservation oracle reproduces the proposed sampling
  polarity and binary weights before Spectre results are interpreted.
- The new top-plate baseline is reproduced in the same full-CDAC fixture;
  the older 12.026-mV capacitor-to-ground result remains separately labeled.
- For each case report raw differential held error at the actual sampling
  aperture and at the pre-compare point, common-mode shift, acquisition
  error/time, turn-off steps, hold drift, clock delay, and terminal stress.
- A nominal performance candidate needs maximum absolute raw differential
  error below 0.439 mV over the confirmed input set, acquisition error below
  0.439 mV within 40 ns, no missing codes, and absolute DNL/INL below 1 LSB
  in the stated ideal-capacitor static transfer. The 3-ns CDAC settling and
  1.5-ns comparison windows must still fit the 60-ns conversion phase.
- An accepted transistor topology additionally needs no unresolved PDK SOA
  warning and a documented foundry terminal-voltage interpretation. Nominal
  compliance only permits later PVT, noise, mismatch, and extraction work;
  it does not constitute those results.
- Python syntax, configuration parsing, OA readback/check, generated-netlist
  provenance, focused Spectre runs, case-count assertions, waveform review,
  `git diff --check`, and owned-diff review pass. Retain failed cases.

If bottom-plate sampling does not improve the full-CDAC raw error or changes
the transfer/timing unfavorably, record that result and retain the current
topology. If it improves the error but fails either the raw or SOA gate,
schedule isolation/dummy compensation and reliability in separate bounded
targets; do not freeze the switch or start global PVT.

## Expected artifacts and handoff

- `output/bootstrap_bottom_plate_eval/` with exact OA exports, case decks,
  PSF waveforms, metrics JSON/CSV, and phase-resolved plots
- `docs/bootstrap_bottom_plate_eval.md` with the comparison, transfer
  derivation, warnings, conclusion, and next topology recommendation
- a decision on whether to promote bottom-plate sampling for the SAR front
  end, with any remaining isolation, dummy, or SOA target stated explicitly

## Commit and push intent

Commit the completed experimental target locally as
`test: evaluate bootstrap bottom-plate sampling`. Push only on user request.
This planning-only record may be committed separately as
`docs: plan bootstrap bottom-plate evaluation`.
