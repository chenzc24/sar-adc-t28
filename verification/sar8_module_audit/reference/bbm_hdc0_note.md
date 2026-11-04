# HD C0 ×4: frozen single-variable packages

Prepared locally only; not registered, submitted or simulated. Parent owns
managed execution. This tests reference-interface delay, not RC1 overvoltage
repair or ADC qualification.

## One change

Conditional baseline: completed `sar8audit-real-bbm-ffcold/sscold` and frozen
`generated/real_bbm_v1`. Only `XDUT.XBBM0.XD_HD.C0`, model `cfmom_2t`, changes
`multi=1` to `multi=4`. Unit geometry remains nr=8, lr=2.5 µm, w/s=50 nm,
stm=1, spm=3, mismatchflag=1. The HD delay master is cloned locally so the LD
leg is untouched. Flattened comparison confirms the other 195 device records
are identical; no transistor, load, node, CODE edge or sampling edge changes.
The entire test.scs is byte-identical to the corresponding baseline.

The completed baseline uses the same 2.5 µm unit geometry at multi=2
(`XBBM0.X002.X000.CMID`) and multi=200 (`XBOOTP.Cboot`); the same model already
uses multi=4 at lr=2 µm (`XCDAC.CMOMN2`). This supports reuse of the model's
multiplier without changing legal unit geometry. The new native candidate
still requires Spectre validation; there is no layout or foundry sign-off.
Exact records are included in measurement.json/package_review.json.

## Fixed environment and intended comparison

Full original bit0 BBM plus real H driver, tested GNN ABC IO/single IO GPP,
X025, Rgate and physical CDAC/reference/Bootstrap/reset-comparator load remain.
Other bits stay static. CODE is ideal, with 43 ns rise/48 ns fall and 10 ps
edges. Ideal external rails, SAMPLE window/closing edge, input/reference
networks, comparator reset, model sections and solver settings are unchanged.
No internal edge is realigned. FF=0.99 V/-40 C; SS=0.81 V/-40 C; stop=52 ns;
no noise, mismatch or PEX.

The baseline SS N-side half-VDD gate ordering is -191.747 ps despite positive
H/L separation. Compare whether added HD delay changes actual GNP/GNN ordering,
opposed reference total-port currents, reference establishment, reset and input
burden. Do not interpret half-VDD timing or total drain currents as pure-channel
conduction proof. Do not assume a fourfold C0 gives a specified delay.

## Measurements preserved and added

All 738 terminal-pair screens across 123 MOS, 656 mandatory currents, 36 KCL
nodes, 246 junction/body observations and 376 complete native columns remain.
Core/IO screening limits stay 0.99/1.98 V; raw CMI remains reportable.
CODE input/source work, BBM and driver VDD energy, internal source/load work,
both-direction H/L and actual gate timing, opposed reference terminal currents
and original reference-establishment fields are reused unchanged from the
frozen BBM analyzer. Its file is staged without edits.

The additive wrapper provides:

- `legacy_halfVDD_window_switching_diagnostic`: preserves the original window
  crossing into the next turnoff. Its high-end false flag is not treated as a
  steady-high establishment failure.
- `physical_command_phase_reference_settling`: high-state error versus actual
  selected references over [43.005,47.995) ns, before the next CODE edge begins;
  low-state error over [48.005,52] ns. Each side must remain within the existing
  1 mV diagnostic through its phase end. No acceptance threshold is relaxed.
- `delay_leg_reset_diagnostics`: HD after CODE falls and LD after CODE rises.
  Record RC0→0, RC1→VDD and delayed output→0 persistence within 1% of VDD,
  absolute entry time, delay from CODE midpoint and from the actual falling
  leg-input half-VDD event. Reset is an observed level diagnostic; activation
  and missing/ambiguous control events remain separately checked. Missing
  events stay unknown and failure to reset/establish by phase end stays false.

Known baseline FF stress is broader than X005: HD X005 |Vgs|=1.059705 V and
|Vgd|=1.062566 V; MP_CLEAR |Vds|/|Vbd| also reaches 1.008802 V in RC1's negative
phase. All remain covered. This C0 comparison does not claim to fix them or
authorize another device replacement.

## Frozen handoff

| Run ID | Recipe relative to this directory | SHA256 | Eight input bytes |
| --- | --- | --- | ---: |
| sar8audit-bbm-hdc0x4-ffcold | `generated/bbm_hdc0_v1/ffcold/recipe_proposal.json` | `0ab4664d440537a1120e13626c576cc5e23fefdf981d4153ef638c89ddd4c892` | 442695 |
| sar8audit-bbm-hdc0x4-sscold | `generated/bbm_hdc0_v1/sscold/recipe_proposal.json` | `86caf38f2d3f07a8002b26f9d78ecee40ed6c771f10f01f8d9d5ded291102523` | 442695 |

DUT SHA256: `b3aa7345ddc41502a606b8b0988b1eb311c652c8fa5303ecee0d8b3e53705b8c`.
Package receipt SHA256: `1eaa655b77ded7e608e33b77178037bb03023798b1aaf737845bf2ad44433fd2`.
Same resource requests: four threads/512 MiB simulation, 256 MiB analysis,
2 GiB raw output, 30 MiB derived output. Parent serializes remote work.

One focused test passed: exact one-record multiplier change, all other records
and clock/testbench bytes preserved, both case input hashes, unchanged model
limits and executable staged analysis on synthetic scalar data. It verifies
true pre-CODE high establishment alongside false legacy turnoff residual,
explicit 52 ns low nonsettling, both reset legs, missing-control handling,
source/internal work closure, opposed currents and all native columns.
Synthetic rows are measurement plumbing checks, not Spectre performance results.

Syntax/UTF8/whitespace and exact staged hashes/sizes passed. Previous full-BBM
frozen inputs/results are unchanged. No remote operation, OA/PDK mutation,
baseline adoption, commit or push. The report's figure count now says three.
