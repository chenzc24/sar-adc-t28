# Top-plate PGATE local transistor driver

## Scope and ownership

Implement and test a copied-netlist T28 PGATE driver, not a clock generator.
Start: clean exp/top-plate-gmain-t28. Own this plan,
scripts/characterization/screen_top_plate_pgate_driver.py,
docs/top_plate_pgate_driver.md, docs/sampling_architecture_status.md,
bounded docs/design_log.md and plan/log.md entries. Generated output belongs
under ignored output/top_plate_pgate_driver/. Remote OA owned: none.
Prior generators, exported decks, PDK, and OA are read-only. Use existing
t28_io SSH Spectre runner and exact-hash source validation.

## Implementation and validation

Keep tg_hold_m4 geometry and all external timing unchanged as matched control.
Replace only SPTRACK/SPHOLD with cross-coupled thick-oxide PMOS pullups
powered by existing boosted G, NMOS pulldowns, and a real 0.9-V CMOS inverter
for complementary OFF_MAIN. No ideal boosted supply or new external rail.
This dynamic-rail level shifter is a hypothesis; pump loading, startup,
switching delay, contention and terminal stress must be measured.
STRACK, external clocks and CDAC switches remain ideal; MP14 dynamic-well
feasibility remains unresolved.

Run +0.8/+0.4 first and all five static input points for the first candidate.
If switching fails, permit a bounded NMOS/PMOS ratio screen (1/1, 4/1, 8/1).
Save driver nodes/currents, pump G and supply; verify finite aligned PSF,
Spectre success, CMI/suppressed warnings, PGATE track/hold residuals,
all six pairwise terminal voltages, GMAIN discharge and 270-ns raw error.
Compare matched ideal-PGATE control, including any pump droop. Functional
target remains 0.439 mV, not a fabricated acceptance threshold for signoff.
Record failures honestly; do not infer foundry SOA from absent warnings.
Compile Python, inspect generated deck delta, diff-check and review owned
changes. Local commit: test: implement T28 top-plate PGATE driver. No push.

## Outcome

Completed five ratio-4 nominal transients at -0.8/-0.4/0/+0.4/+0.8 V.
Signed errors: -0.080368/+0.605518/~0/-0.605518/+0.080368 mV.
All five: zero simulator errors, four SFE-1131 warnings, no CMI or
suppressed warnings. A -0.4-V upload failure and subsequent download
failure were retried in a bounded final attempt; failed transfers are
not accepted as simulation evidence. Original exports and OA unchanged.

Switching works, but raw error fails 0.439 mV. MP16 drain/body positive
bias reaches 0.497386 V when G resets while PGATEB retains charge.
No driver ratio sweep: the switching-failure gate was not activated.
First netlist implementation/characterization is complete; circuit
acceptance remains open. Next target is reset-aware PGATEB discharge
and junction/well review, followed by charge/edge analysis and STRACK.

Validation: Python compile, five-input deck generation and bounded diff
inspection, zero-error Spectre logs, complete finite/aligned PSF, per-run
deck hashes, re-analysis of the first four saved runs, final fifth-run
analysis, owned diff review and git diff --check. Detailed result report:
docs/top_plate_pgate_driver.md. Generated output stays ignored.
