# Isolate VOUT before BOOT reset: netlist timing test

## Goal and starting state

Test the user's specific hypothesis that separating the main sampling
switch's turn-off from BOOT reset removes the dominant reset-edge output
error. Existing PHIB advances both together; this target introduces
independent `OFF_MAIN` and `PHIB` waveforms in copied Spectre decks.

At start, `exp/bootstrap-protected-eval` is clean. The exact read-only OA
export is SHA-256
`f466793e8655f2d81bdb7ce98d1041f00cdd90a374be3341750d2cb22a9bdd4d`.
Use the prior validated `split_main_gate_bound_early` topology as the
control basis: T28 MN9 uses the known 1.8-V class/body-to-VSS screen, and
only the two main-gate links are ideal relays. No claim of a realizable
T28 topology is implied.

## Ownership

- Local owned: this plan,
  `scripts/characterization/test_bootstrap_isolate_before_reset.py`,
  `docs/bootstrap_isolate_before_reset.md`, and bounded entries in
  `docs/design_log.md` and `plan/log.md`.
- Generated: ignored `output/bootstrap_isolate_before_reset/`, containing
  exact decks, Spectre log/PSF, and machine-readable summary.
- Remote OA owned: none; all OA, original export, and PDK files read-only.
- Shared dependencies: previous controlled variant generator,
  direct-SSH Spectre runner, PSF reader, and the exact T28 model includes.

## Matrix and measurements

1. Keep `OFF_MAIN` rise at 250.2-250.3 ns after PHI falls at
   250.0-250.1 ns. Only the ideal MN11 `GMAIN` hold relay sees OFF_MAIN.
   PHIB still controls G discharge and all BOOT reset devices/clock pumps.
2. Sweep PHIB rise at 250.2, 250.4, 250.6, and 251.3 ns. The first is
   simultaneous; the latter provide about 0.1, 0.3, and 1.0 ns from
   *completed* OFF_MAIN edge to reset start. No other topology changes.
3. At each run, measure differential VOUT immediately before/after
   reset, the 270-ns held raw error, MN11 drain current before reset,
   source current, and full device-terminal stress. Validate output KCL.
   A held error below 0.439 mV is a screen, not acceptance.
4. If a delayed case looks effective, add a separate small VIN-step
   challenge during the off-before-reset interval to test whether VOUT
   is truly isolated, rather than merely holding for a static VIN.
5. Add a no-reset diagnostic control in the same 250-ns cycle and compare
   the 251.28-251.8-ns natural output drift against the 1-ns-delay reset
   case. This control is not a functional next-cycle clock sequence.

Pass criteria for the *test*: original hash unchanged; bounded deck diff;
Spectre `result.ok`; finite/aligned PSF; source current and output KCL
consistency; phase and waveform checkpoints; Python compile, JSON parse,
`git diff --check`, and owned-diff review. Interpret any favorable result
as an ideal-gate timing upper bound until real T28 switches, next-cycle
acquisition, multiple input levels, full CDAC, and foundry SOA are checked.

Commit locally as `test: isolate bootstrap output before reset`; do not
push without user request.

## Outcome

Six copied-netlist Spectre transients completed with zero errors. The
independent OFF_MAIN transition leaves approximately -2.53 mV output
error before PHIB reset. Delaying reset 0.1-1.0 ns makes the later
PHIB-driven sequence contribute only about +0.080 mV; a no-reset
control's matched natural drift is +0.0000026 mV. The best held raw
error (-2.452 mV) still fails the 0.439-mV gate. A deliberately sharp
19.922-mV differential VIN challenge after turn-off couples 0.559 mV
to VOUT, so low static MN11 current is not complete dynamic isolation.
Evidence and scope limits are in `docs/bootstrap_isolate_before_reset.md`;
exact generated decks, logs, PSF and JSON are in the ignored output
directory. No OA or PDK changes were made.
