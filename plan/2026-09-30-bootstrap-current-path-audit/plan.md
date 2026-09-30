# Bootstrap turn-off current-path audit

## Goal and initial state

Quantify how the full-control mixed-voltage bootstrap's -8.755-mV nominal
raw held error forms across the `PHI` falling edge, non-overlap gap, and
`PHIB` rising edge. Test the specific hypothesis that MN9's B=VIN, D=BBOT
connection forward-biases its body/drain junction in hold and loads the input.
This is a diagnostic of the existing OA circuit, not a new switch design or
reliability signoff.

At target start branch `exp/bootstrap-protected-eval` was clean. Its exact
existing `SAR_ADC_T28/tb_sar_bootstrap_protected_full18_eval/schematic`
Spectre export has SHA-256
`f466793e8655f2d81bdb7ce98d1041f00cdd90a374be3341750d2cb22a9bdd4d`.
The `t28_io` bridge tunnel was not running, but read-only direct SSH to the
Spectre host worked. No OA state will be modified or exported afresh.

## Ownership

- Local owned: this plan,
  `scripts/characterization/audit_bootstrap_current_paths.py`,
  `docs/bootstrap_current_path_audit.md`, and bounded entries in
  `docs/design_log.md` and `plan/log.md`.
- Generated output: ignored `output/bootstrap_current_path_audit/` only.
- Remote OA owned: none. All `SAR_ADC_T28` cellviews, PDK and foundry
  libraries, existing exports and prior result directories are read-only.
- Shared dependencies: existing full-control OA export, T28 model include
  sections, bridge SSH Spectre runner, Python PSF reader. Do not copy or edit
  PDK model files.

## Method and validation

1. Require the exact source hash, verify the TB source, resistor, two DUT
   instances, and MN9/MN11 D/G/S/B statements. Append only a transient
   analysis and explicit voltage/current saves to a new analysis deck.
2. Run one TT/0.9-V/27-C Spectre transient with the same source and timing.
   Save VSP/VSN and RINP/RINN currents; attempt terminal currents for MN9,
   MN11 and relevant boost/gate-discharge devices. Confirm signal names and
   current sign against the documented Spectre terminal convention.
3. Calculate phase checkpoints, input-source voltage drop/current, MN9
   `Vbd`, output-minus-input error, and charge integrals over the turn-off
   interval. Compare independent source/resistor and device currents where
   available. State attribution as confirmed only when currents and KCL
   agree; otherwise retain it as a topology hypothesis.
4. Do not alter any device netlist statement or existing OA cell. If a
   controlled topology ablation is needed, propose a separate OA target.

Pass criteria are Spectre `result.ok`, saved current/voltage waveform
coverage, aligned finite time series, source-hash preservation, explicitly
stated current orientation, Python compile, JSON parse, `git diff --check`,
and owned-diff review. Store the unique deck, raw log/PSF and concise summary
under ignored output. Commit locally as
`test: audit bootstrap turn-off current paths`; no push without request.

## Outcome

The exact-export transient completed with zero Spectre errors. Terminal
currents confirmed about 25.86 uA high-side input loading in hold through
the MN9 connection, while output/load charge placed -2.939 mV of error in
the non-overlap gap and -5.837 mV in the gate-discharge interval. Subsequent
output drift was only +0.022 mV. Full evidence and limits are in
`docs/bootstrap_current_path_audit.md`. A topology ablation and OA edit
were intentionally not part of this audit; the next named variant must be
designed separately.
