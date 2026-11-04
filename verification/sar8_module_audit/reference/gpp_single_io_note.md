# GPP single IO: frozen local comparison

Prepared only; not registered, submitted or simulated. Parent owns managed execution.

Replace bit0 GPP's three identical core inverter stages (six MOS) with one
ordinary IO inverter pair: unit W=320 nm, L=150 nm, nf=1,
N multi=2 / P multi=4. Full parameters match existing GNNCN/GNNCP.
This is one driver-block implementation contrast; device count and parasitics
change together. It does not isolate one transistor effect or change ADC
architecture. L0-to-GPP inversion is preserved without internal edge alignment.

All other 140 flattened device records remain identical: core X025, GNN ABC,
original Rgate, CDAC/reference/bootstrap/reset-comparator load. Testbench commands,
sampling edges, model includes and solver settings are unchanged; only saves
follow the changed device inventory. L0 remains ideal, so full BBM is unqualified.

## Frozen packages

| Run ID | Recipe relative to this directory | SHA256 | Seven input bytes |
| --- | --- | --- | ---: |
| sar8audit-gpp-singleio-ffcold | `generated/gpp_single_io_v1/ffcold/recipe_proposal.json` | `426b80e4438a8198093f7a94b30fd47d50ae8f8d711f9c4ade7756273f50fdc8` | 302486 |
| sar8audit-gpp-singleio-sscold | `generated/gpp_single_io_v1/sscold/recipe_proposal.json` | `9d65f0c0a43a13ab9d34b9aba9df588e03a00b969186720d93acc78307b59674` | 302487 |

FF: 0.99 V / -40 C; SS: 0.81 V / -40 C. Both stop at 52 ns.
Input hashes and sizes are in `generated/gpp_single_io_v1/package_review.json`.
DUT SHA256: `d352e371631d4c4c382dc3666a857e52e4137162b32757efbf66d71d75c6198a`.
Package receipt SHA256: `ae96975f7e89dd2c23e1ed1f837c2ede5d3224ea99f09df57dc2def3ed335792`.

Each case retains 94 voltages, 462 mandatory terminal currents, 474 terminal-pair
screens across 79 actual MOS, 12 KCL nodes and 132 full native columns. Removed
GPP A/B/C stages are absent from inventory and stage energy, not represented as
zero-valued measurements. Keep actual branch timing/control gaps, negative
excursions, 158 junction-polarity observations, proper ON settling, stage source
work, L0 source/load work and X025-to-A internal work closure. Half-supply control
gaps alone do not establish absence of simultaneous transistor conduction.

X025 is unchanged and remains screened at 0.99 V; its previous FF maximum
1.009124 V (19.124 mV excess) is unresolved. IO devices retain provisional
1.98 V screens. Any GPP improvement cannot qualify X025 or the whole chain;
native CMI, body polarity/current and below-ground excursions remain reportable.
No noise, mismatch, PEX or lifetime sign-off is included.

## Local checks

One focused test passed: exact six-removed/two-added mapping; all 140 retained
records equal; IO parameters and four L0 gate loads; unchanged commands; both
input hash sets; actual-model screen limits; staged analyzer execution on
synthetic scalar data covering source work, KCL, body polarity, timing, negative
PRE excursion and ON settling. Synthetic input is a measurement check, not a
Spectre result or candidate performance evidence.

Syntax/UTF8/whitespace, no stale deleted-stage assumptions, and no single-incidence
internal nodes passed. All 62 previous IO-C/BC/ABC/real-PRE frozen input hash
records remain unchanged. No remote action, OA edit, adoption, commit or push.
