# Bootstrap terminal-stress map

## Goal and starting state

Continue the transistor-level `sar_bootstrap` mainline by locating which
devices and terminal pairs exceed the nominal 0.99-V PDK warning level in the
already completed full-driver differential transient. This is a read-only
forensic gate before any protected-driver topology edit. It must not declare
foundry reliability approval or treat a voltage-level screen as a transient
duration rule.

At target start `main` was ten commits ahead of `origin/main`. Three unrelated
untracked StrongARM/CDAC integration files were present: its config, plan, and
creator script. They do not overlap this target or its dependencies and remain
untouched. Bridge profile `t28_io` reported a healthy CIW and Spectre 21.1.

## Ownership

- Local owned: this plan, `scripts/characterization/audit_bootstrap_soa.py`,
  `docs/bootstrap_soa_map.md`, and bounded entries in `docs/design_log.md` and
  `plan/log.md`.
- Generated output: ignored `output/bootstrap_soa_map/` only.
- Remote OA owned: none. All `SAR_ADC_T28` cellviews, PDK models, libraries,
  and ongoing StrongARM work remain read-only.

The source of truth is the existing exact OA export at
`output/bootstrap_driver_design/netlist/tb_sar_bootstrap_transient/input.scs`
(SHA-256 `f3818ef606de602671beac8b6728a1f5460958d03ca0299de0fc79e28132242c`)
and the successful, one-case `screen_baseline_vdp800` Spectre result at
`output/bootstrap_driver_error_reduction/smoke_baseline/run_summary.json`.
No rerun or circuit/netlist mutation is needed.

## Method and limits

1. Parse every `sar_bootstrap` MOS D/G/S/B connection from the exact OA
   export, not a hand-written device map. Require all referenced nodes to be
   present in the saved waveform or a known supply/ground net.
2. For both differential sides, reconstruct `|Vgs|`, `|Vgd|`, `|Vgb|`,
   `|Vds|`, `|Vbs|`, and `|Vbd|` across the complete trace and separately
   the 200–285-ns driven cycle. Record
   device, side, terminal pair, maximum value, time, and time above the
   nominal 0.99-V PDK warning level. Retain signed terminal differences.
3. Compare reconstructed magnitudes with retained Spectre `CMI-275x` SOA
   warnings. Rank violating devices by excess voltage and distinguish pump,
   control/isolation, discharge, and main-switch paths.
4. Record the prior phase-resolved held-error result (about −11.692 mV at
   immediate PHI turn-off, −0.335 mV during discharge, +0.008 mV drift) as
   an independent performance axis; stress ranking alone is not a fix.

This one TT/0.9-V/27-C static-input case is only a diagnostic. The 0.99-V
threshold comes from logged model warnings, not a complete foundry transient
SOA rule. No claim is made for PVT, dynamic aperture, mismatch, lifetime, or
layout. If a protected device class or allowed overvoltage duration cannot be
verified, stop at a topology requirement rather than guessing a substitution.

## Validation and handoff

Require source hash and baseline case identity, complete 12-device terminal
coverage on both sides, finite waveforms and time
base, consistency with printed Spectre warning device/metric examples,
Python compile, JSON parse, `git diff --check`, and owned-diff review. The
report must give a concrete next circuit target without changing the OA
prototype. Commit locally as `test: map bootstrap terminal stress`; do not
push without user authorization.

## Outcome

The existing one-case differential run and exact OA export passed all source,
waveform, 12-device-per-side, 144-metric, and 19 logged-warning witness
checks. Pump MN1/MN2/MN3 reach about 1.78 V, control/discharge MN7/MN13
reach about 1.67 V, and main MN11 reaches 1.148 V across its gate and drain.
No OA cell or simulation deck was changed. The next target is a protected,
separately named experimental driver after device-class rule verification;
the 0.99-V screen is not a foundry reliability acceptance.
