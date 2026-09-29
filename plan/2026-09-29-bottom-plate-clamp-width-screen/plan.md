# Bottom-plate top-clamp narrow-width screen

## Goal and starting state

Screen whether reducing the four T28 core-NMOS top/split-node clamps from
the existing W=1.0 um total to W=0.5, 0.25, 0.20, 0.185, and 0.10 um can bring the full-CDAC
bottom-plate sampling path below the **raw** 0.439-mV held-error gate.
Hold the 22 existing bootstrap instances, CDAC capacitors, sources, phases,
reference handoff, and measurement instants fixed. This is a one-factor
diagnostic; shared boost generation and a production clamp are separate
targets. If a narrower variant passes nominal raw error, that permits
only a further physical-clamp study, not promotion while SOA is unresolved.

At target start, `git status --short --branch` was clean at `42c0189` on
`main`, eight commits ahead of `origin/main`. The immediately previous
bottom-plate experiment is committed at `ed8965a`; a separate StrongARM
target was committed later and has no overlapping paths here. Bridge 0.8.0
profile `t28_io` currently reports its tunnel **not running**. Restore and
recheck the tunnel/daemon/CIW, Spectre, windows, locks, exact proposed OA
names, and `SAR_ADC_T28` technology binding before any OA mutation. Stop if
the user has an unsaved target window, a modal dialog, or unexpected mapping.

## Owned local paths

- this plan
- `config/bootstrap_bottom_plate_clamp_width_screen.yaml`
- `scripts/characterization/create_bottom_plate_clamp_width_screen.py`
- backward-compatible CLI extension of
  `scripts/characterization/run_bootstrap_bottom_plate_eval.py`
- backward-compatible CLI extension of
  `scripts/characterization/analyze_bootstrap_bottom_plate_eval.py`
- `docs/bootstrap_bottom_plate_clamp_width_screen.md`
- bounded entries in `docs/design_log.md`, `plan/log.md`, and
  `virtuoso/cell_manifest.yaml`

Generated readback, OA exports, decks, PSF, warnings, metrics, and plots go
only under ignored `output/bootstrap_bottom_plate_clamp_width_screen/`.
The existing bootstrap scripts' default behavior and previous outputs must
remain unchanged.

## Owned remote OA objects

- `SAR_ADC_T28/sar_cdac_bottom_plate_clamp_w500_eval_10b/schematic` and
  `/symbol`; `SAR_ADC_T28/tb_sar_bottom_plate_clamp_w500_eval/schematic`
- `SAR_ADC_T28/sar_cdac_bottom_plate_clamp_w250_eval_10b/schematic` and
  `/symbol`; `SAR_ADC_T28/tb_sar_bottom_plate_clamp_w250_eval/schematic`
- `SAR_ADC_T28/sar_cdac_bottom_plate_clamp_w100_eval_10b/schematic` and
  `/symbol`; `SAR_ADC_T28/tb_sar_bottom_plate_clamp_w100_eval/schematic`
- `SAR_ADC_T28/sar_cdac_bottom_plate_clamp_w200_eval_10b/schematic` and
  `/symbol`; `SAR_ADC_T28/tb_sar_bottom_plate_clamp_w200_eval/schematic`
- `SAR_ADC_T28/sar_cdac_bottom_plate_clamp_w185_eval_10b/schematic` and
  `/symbol`; `SAR_ADC_T28/tb_sar_bottom_plate_clamp_w185_eval/schematic`

These are new experimental cells. The prior ideal-clamp, W1-um clamp,
`sar_bootstrap`, macro-model, StrongARM, PDK, technology, and every other
library/cell/view are read-only. Never edit OA databases as ordinary files.

## Contracts and procedure

- Reference: the earlier W1-um T28 clamp produced 2.0960-mV maximum raw
  bottom-plate held error over five inputs, −0.2602% fitted gain-error
  slope, and PDK clamp/boost SOA warnings. The ideal clamp yielded
  0.00790 mV, but is not a physical baseline.
- For W500/W250, use four `tsmcN28/nch_mac` L30 devices with one 250-nm
  finger and `simM=2` or `1`; W100/W200/W185 use one finger of the named
  width with `simM=1`.
  Body remains VSS; D/G/S connections
  remain the same as the W1-um OA fixture. No compensating device or
  netlist transistor-line rewrite is allowed.
- Clone the previous owned OA fixture through supported bridge schematic
  APIs into independent names; read back each variant, require zero check
  markers, export its exact OA Spectre netlist, and verify width/connectivity
  statements before simulation. Preserve source hashes and untouched
  circuit lines in the parameterized analysis deck.
- First run TT/0.9 V/27 C at `Vdiff=-0.8, 0, +0.8 V` with 0.5-ns clamp
  lead and existing 50-ohm sources. If a candidate reaches the raw
  0.439-mV gate, add `±0.4 V` for a five-point confirmation. Do not infer
  pass from fitted residual or common-mode cancellation.
- Record acquisition error, clamp step/common mode, final raw held error,
  fitted gain/residual (diagnostic only), hold drift, and raw Spectre SOA
  warnings. Compare against the prior W1-um and ideal-clamp results using
  the same definition. Calculate whether the width-error trend is compatible
  with a top-node parasitic interpretation, but do not claim unique cause
  without a separated device/parasitic test.
- If all five narrow-width candidates fail raw error, stop before shared-boost
  OA construction; if one passes, propose shared-boost as the next bounded
  target only after reviewing clock load and SOA. This screen does not
  authorize PVT, full-code physical DNL/INL, or ADC integration.

## Validation and handoff

Require Python syntax/YAML checks, bridge preflight, exact OA readback and
zero markers, OA export hash consistency, focused Spectre completion with
no simulator errors, case-count/result assertions, warning retention,
`git diff --check`, and an owned-diff review. A transient that converges
but violates PDK SOA is not an accepted transistor solution. Report any
bridge or licensing blocker without fabricating simulation results.

Expected artifact: `docs/bootstrap_bottom_plate_clamp_width_screen.md`
with the width comparison, numerical pass/fail decision, source provenance,
and a precise next experiment. Commit the bounded target locally as
`test: screen bottom-plate clamp width`; push only on user request.

### Scope correction during execution

After the W250 first point missed the raw gate, read-only CDF inspection
showed `tsmcN28/nch_mac` `Wfg` defaults to 100 nm and exposes no `minVal`.
Therefore W250 must not be called the foundry minimum. The distinct W100
cellviews and single-width simulation above were added before OA mutation;
W100 is a CDF-default *experimental* width, not a claim of foundry-approved
minimum geometry or reliability.

The W100 first extreme point then showed poor top/split-node clamp settling,
whereas W250 missed the raw gate by only 0.093 mV. W200 is added as one
intermediate, separately named OA sample to test whether a feasible width
window exists; no existing variant is changed.

W200's first extreme point missed the raw gate by only 9.7 uV. A final W185
single-point probe at −0.8 V is added before concluding whether a nominal
width window exists. If it passes, extend only that same OA variant to the
remaining four input points; no further width variants in this target.

### Outcome

All five separately named OA variants were read back with zero markers and
tested from their exact exported netlists. W185 passed the nominal five-point
raw gate by only 5.22 uV (0.43378 versus 0.439 mV), while W200 missed by
9.65 uV and W100 became reset-limited. Every run retains T28 core-device SOA
warnings. The scope ends at this width screen; a reliable clamp/boost
redesign and shared-boost architecture test require new bounded targets.
