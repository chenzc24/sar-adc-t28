# Bootstrap turn-off charge screen

## Goal and starting state

Quantify how the approximately -2.53 mV pre-reset differential error in the
independent `OFF_MAIN` experiment depends on control-clock transition,
actual GMAIN slew, and held capacitance. Integrate the saved T28 MN11 drain current and verify its
consistency with the held-capacitor voltage change. This is a netlist-only
mechanism screen, not a physical implementation or a complete separation of
channel charge injection from displacement current.

At start, branch `exp/bootstrap-protected-eval` is clean. The read-only OA
export has SHA-256
`f466793e8655f2d81bdb7ce98d1041f00cdd90a374be3341750d2cb22a9bdd4d`.
The exact `reset_gap_1ns` copied-netlist topology is the control. EVAS does
not support this PDK transistor circuit; use Spectre 21.1 via `t28_io`.

## Ownership

- Local owned: this plan, `scripts/characterization/screen_bootstrap_turnoff_charge.py`,
  `docs/bootstrap_turnoff_charge_screen.md`, and bounded entries in
  `plan/log.md` and `docs/design_log.md`.
- Generated: ignored `output/bootstrap_turnoff_charge_screen/` containing
  exact copied decks, logs, PSF, and JSON summary.
- Remote OA owned: none. All OA, original export, PDK, and previous experiment
  artifacts are read-only.
- Shared read-only dependencies: `screen_bootstrap_netlist_ab.py`,
  `test_bootstrap_isolate_before_reset.py`, the PSF parser, and the direct-SSH
  Spectre runner.

## Experiment and gates

1. Regenerate and hash-check the exact prior source. Use PHIB reset at
   251.3 ns, independent main-switch turn-off starting at 250.2 ns.
2. Hold 219.5 fF per side and sweep the `OFF_MAIN` return-edge duration at
   50, 100, 300, and 600 ps. Independently hold the 100-ps edge and sweep
   load at 109.75, 219.5, and 439 fF per side. These are clock and load
   screens, not necessarily actual GMAIN slew screens.
3. If the ideal relay makes GMAIN's true edge much sharper than `OFF_MAIN`,
   hold the clock and load at baseline, and sweep only the hold-side relay's
   closed resistance at 1, 1k, 5k, and 20k ohm. This additional bounded
   mechanism test changes the ideal driver impedance, not any PDK MOS size.
4. Measure acquisition/pre-off, pre-reset, post-reset, and 270-ns errors;
   integrate MN11 drain and load currents over the turn-off window; check
   `Qload=Cload*deltaV` and output-node KCL. Record actual GMAIN transition,
   leakage, Spectre errors/CMI warnings, and diagnostic terminal stress.
5. Infer only supported mechanism trends. Do not identify individual MOS
   charge components from terminal current alone or declare a physical cell.

Pass criteria for the *experiment*: source hash and bounded deck diff,
Spectre `result.ok`, finite aligned PSF, charge/KCL consistency, Python
compile, JSON parse, `git diff --check`, and owned-diff review. The 0.439-mV
raw hold-error allocation is reported as a design screen, not a prerequisite
for completing this diagnostic.

Commit locally as `test: screen bootstrap turn-off charge`; no push without
user request.

## Outcome

Nine one-factor copied-deck Spectre runs completed. The 50-600-ps control
clock sweep did **not** generate a comparable GMAIN slew: the ideal relay
made 1.1-5.0-ps gate transitions. A separate 1/1k/5k/20k-ohm SHOLD
resistance sweep genuinely extended the gate transition to 1.6/20.6/74.4/
293 ps and worsened held error from -2.452 to -2.647 mV. Halving/doubling
the ideal load changed both voltage error and transferred charge, so a fixed
charge-injection source is not a sufficient model. All cases miss the
0.439-mV raw allocation. Full evidence and limitations are in
`docs/bootstrap_turnoff_charge_screen.md`.

During execution, unrelated untracked `plan/2026-09-30-canvas-topology-sample/`
and `review/topology/`, plus a modification to `scripts/review/build.py`,
appeared. They are disjoint from this target, were not modified or staged by
this work, and remain user-owned.
