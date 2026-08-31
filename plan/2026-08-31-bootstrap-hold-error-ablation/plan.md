# Bootstrap held-error ablation and differential check

## Goal

Identify the dominant source of the transistor bootstrap prototype's
signal-dependent held-sample error before changing the production candidate or
expanding PVT. Compare the complete OA-exported driver against an isolated DNW
main switch with an ideal relative gate drive, then test the complete driver as
a matched fully differential pair. Quantify turn-off-edge and hold-capacitance
sensitivity so the next topology edit is based on evidence.

This target is diagnostic and simulation-only. It does not redesign the
charge pump, claim reliability closure, or create a production sampling cell.

## Dirty-state and preflight note

`main` starts clean at `1c31127`, three commits ahead of `origin/main`. The
source OA export hash is
`f3818ef606de602671beac8b6728a1f5460958d03ca0299de0fc79e28132242c`.
The existing `sar_bootstrap` and transient testbench were read back with zero
check markers in the preceding target. No unrelated local dirty files exist.

Before simulation, recheck bridge profile `t28_io`, CIW connectivity, Spectre
21.1 availability, and the exact source-export hash. No OA mutation is owned.

## Local owned paths

- `plan/2026-08-31-bootstrap-hold-error-ablation/plan.md`
- `config/bootstrap_hold_ablation.yaml`
- `scripts/characterization/run_bootstrap_hold_ablation.py`
- `scripts/characterization/analyze_bootstrap_hold_ablation.py`
- `docs/bootstrap_hold_error_analysis.md`
- bounded updates to `docs/design_log.md` and `plan/log.md`

Generated decks, PSF, JSON, CSV, and plots under
`output/bootstrap_hold_ablation/` are owned but ignored.

## Remote OA owned objects

None. `SAR_ADC_T28/sar_bootstrap` and all other remote cellviews are read-only
in this target.

## Read-only dependencies

- automatic OA export at
  `output/bootstrap_driver_design/netlist/tb_sar_bootstrap_transient/input.scs`
- all PDK/model content and the `tsmcN28` library
- all `SAR_ADC_T28` OA cellviews
- existing simulation results and reference literature
- all user windows and unrelated libraries

## Diagnostic matrix and assumptions

1. **Full single-ended baseline**: instantiate the unmodified exported
   `sar_bootstrap` hierarchy with the 2-um DNW main switch and 200-fF Cboot.
2. **Isolated relative-off main switch**: instantiate only the same exported
   `nch_dnw_mac L=60 nm, W=2 um` sampling device. Drive its gate relative to
   its source with an ideal 0-to-0.9-V sample pulse. This retains the main
   device's intrinsic channel/parasitic behavior while removing the pump,
   follower, and protection network. It is a cancellation control, not a
   realizable fixed-ground off drive.
3. **Isolated absolute-off main switch**: drive the same device to
   `VG=VIN_target+VDD` during sampling and to absolute 0 V in hold. Because the
   input step is complete before sampling, this is the practical ideal-
   bootstrap reference for separating the main device from driver-network
   imperfections.
4. **Full differential pair**: instantiate two identical full bootstrap
   blocks with complementary inputs around 0.45-V common mode and matched
   clocks/loads. Report differential and common-mode held errors separately.
5. **Isolated differential pairs**: repeat the complementary-input test for
   both relative-off and absolute-off ideal-gate controls.

Use off-phase input steps so acquisition is dynamic. Sweep representative
differential input values, load capacitance, and ideal-gate fall time for both
isolated gate controls. The full-driver edge remains the OA clock edge and is
not silently retimed.

The deterministic held-error gate remains `0.25 LSB = 0.439 mV`, evaluated at
the representative 270-ns comparison instant. Passing an isolated fixture
does not waive the existing full-driver SOA blocker.

## Implementation steps

1. Verify bridge/Spectre health and source-export provenance.
2. Parse and preserve the exact exported `sar_bootstrap` subcircuit and model
   include; generate analysis-only Spectre decks for the six diagnostic modes.
3. Run a small smoke case for each mode, inspect phase and saved-node
   contracts, then execute the bounded matrix.
4. Measure acquisition error/time, immediate turn-off step, held error at
   270 ns, differential error, common-mode shift, and load/edge sensitivities.
5. Classify the dominant contributor and recommend the smallest next circuit
   change. Do not mutate OA or expand to PVT in this target.

## Validation and pass criteria

- source OA export hash matches the recorded value; generated decks preserve
  the exported subcircuit text and model section
- every scheduled Spectre job completes or remains an explicit failure
- low/mid/high single-ended and complementary differential stimulus points are
  represented; no failed point is dropped from analysis
- isolated-device and full-driver modes use the same main device dimensions,
  source resistance, load, supply, temperature, and sample/hold measurement
  times unless the swept parameter states otherwise
- analyzer checks deterministic mode/case counts and reports rather than hides
  the 0.439-mV held-error criterion
- waveform plot is visually inspected; Python compiles; YAML parses; focused
  result assertions, `git diff --check`, owned-diff review, and clean final
  status complete

## Expected artifacts

- `output/bootstrap_hold_ablation/spectre/run_summary.json`
- `output/bootstrap_hold_ablation/analysis/summary.json`
- `output/bootstrap_hold_ablation/analysis/case_summary.csv`
- `output/bootstrap_hold_ablation/analysis/waveforms.png`
- `output/bootstrap_hold_ablation/analysis/sensitivity.png`

## Commit policy

Commit locally after validation as
`test: isolate bootstrap held-sample error`. Do not push without a separate
user request.

## Completion record

Completed without OA mutation. All 40 scheduled Spectre cases succeeded. The
complete differential pair showed 12.026 mV maximum raw held error and
-1.510% fitted gain error; the practical absolute-off isolated main showed
1.390 mV and -0.173%, while the relative-off cancellation control remained
below 1 nV. The driver-added fitted gain term is therefore -1.337% and is the
dominant next design target. Generated waveforms and load/edge sensitivity
plots were visually reviewed. Raw 0.439-mV compliance and the independent SOA
blocker remain unresolved; no PVT expansion or production freeze is claimed.
