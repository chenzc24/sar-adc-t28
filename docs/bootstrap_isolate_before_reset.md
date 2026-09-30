# Turn off the sampling path before resetting BOOT

Date: 2026-09-30. This is a netlist-only timing experiment on the
`SAR_ADC_T28/tb_sar_bootstrap_protected_full18_eval/schematic` export,
not a changed OA schematic. The original OA export SHA-256 is
`f466793e8655f2d81bdb7ce98d1041f00cdd90a374be3341750d2cb22a9bdd4d`.
Every copied deck uses the previous `split_main_gate_bound_early` circuit:
T28 MN9 has B=VSS and a known 1.8-V device class/geometry; MN11 has its
own `GMAIN`, connected by **ideal relay** to boosted G in sample and to VIN
in hold. This study changes only the hold-relay clock from shared PHIB to
independent `OFF_MAIN`, and varies the separate PHIB BOOT-reset edge.
The ideal relays are not a realizable T28 implementation.

## Exact clocks and conditions

`PHI` falls over 250.0-250.1 ns. `OFF_MAIN` rises over
250.2-250.3 ns, starting the independent MN11 gate transition. PHIB
still controls the original G discharge, MN12 BBOT-to-VSS reset, and
pump timing. It rises at 250.2, 250.4, 250.6, or 251.3 ns (100-ps
edges). The corresponding non-simultaneous reset starts about 0.1,
0.3, or 1.0 ns after OFF_MAIN has reached its high level. A separate
diagnostic keeps PHIB low through 285 ns; it is **not** a functional
repetitive reset sequence. The challenge case applies a 10-mV step on
each input side in opposite directions at 250.50-250.51 ns, returning
at 250.70-250.71 ns before the 251.3-ns reset.

All six runs use Spectre 21.1, T28 PDK sections `pre_simu`,
`noise_worst`, `ttmacro_mos_moscap`, `tt_res_bip_dio_disres`,
`tt_mom`, `tt_ind_jvar`, and `tt_r_metal`, TT/0.9 V/27 C, 50-ohm
input source resistance, 219.5-fF output load per side, and the
original 0.85/0.05-V differential stimulus. No transient noise,
PVT, layout parasitics, or full CDAC is included. Spectre completed
with zero errors in each case; only four duplicate-model-include
`SFE-1131` warnings were printed per run, with zero `CMI-275x`
warnings. The full-transient saved D/G/S/B diagnostic-voltage screen
found no listed 0.99/1.98-V comparison-level crossing on real PDK
MOS devices; it cannot screen the ideal relays or prove foundry SOA.

## Results

The reset-window delta is the **differential** VOUT change from 20 ps
before PHIB begins rising to 500 ps after it begins. For simultaneous
clocks, that window also includes main-gate turn-off and therefore is
not a separable BOOT-reset effect. For delayed cases, the MN11 gate has
already moved to about VIN and its drain current at the pre-reset
checkpoint has decayed.

| Case | BOOT reset start (ns) | Pre-reset raw error (mV) | Window delta (mV) | Held raw error at 270 ns (mV) | MN11-P drain current pre-reset |
| --- | ---: | ---: | ---: | ---: | ---: |
| simultaneous | 250.2 | +0.106 | -2.588 combined | -2.482 | -0.373 uA; still switching |
| gap 0.1 ns | 250.4 | -2.536 | +0.0803 | -2.456 | +0.717 nA |
| gap 0.3 ns | 250.6 | -2.536 | +0.0801 | -2.456 | -4.13 pA |
| gap 1.0 ns | 251.3 | -2.532 | +0.0801 | -2.452 | -4.13 pA |
| no BOOT reset | none before 285 | -2.537 | +0.0000026 natural drift in 251.28-251.8 ns | -2.537 | -4.13 pA |

The no-reset control makes the attribution clearer: when reset is delayed
to 251.3 ns, the 251.28-251.8-ns differential VOUT change is about
`+0.080110 mV`, whereas without reset the same time window changes
only `+0.0000026 mV`. Thus the PHIB-driven BOOT/G reset sequence still couples about
`+0.080 mV` into the held output, but the dominant approximately
`-2.53 mV` has already formed at the independent main-gate turn-off.
The earlier shared-PHIB experiment's approximately -5.84-mV edge
change conflated gate turn-off and BOOT reset; it was not evidence that
the PHIB-driven reset sequence alone caused all of it. This test does not
separate MN12 BBOT clamping from G discharge and pump clocking within that
sequence. Delaying reset from 0.1 to 1.0 ns
changes final raw error by only about 0.004 mV once the gate has settled.

The off-before-reset input-step challenge is also instructive. An
approximately `+19.922 mV` differential VIN step produces a
`+0.558599 mV` differential VOUT response during the step; the
otherwise matched static-input control changes only about
`+0.000011 mV` over that interval. VOUT recovers to within
`0.000274 mV` of its pre-step differential level once VIN returns.
This deliberately sharp 10-ps step is a stress diagnostic, **not** the
specified 4.5-MHz input waveform. It shows that a low static MN11
drain current does not mean complete *dynamic* electrical isolation;
parasitic/displacement coupling and possible brief conduction must be
separated in a physical implementation. Do not directly apply the
0.439-mV static raw-error gate to this artificial transient challenge.

After an actual reset, high-side hold input current is about
`0.0000386 uA` (0.0386 nA), versus 25.86 uA in the original full-control
bootstrap. The no-reset control draws -5.61 uA at 270 ns because BOOT
was intentionally left in its nonfunctional active state; it is only a
local edge-drift reference. Source-resistor current balance and
MN11/output-load KCL passed in all six runs. Exact copied decks, PSF,
Spectre logs, individual JSON and `summary.json` are under ignored
`output/bootstrap_isolate_before_reset/`; the generator/analyzer is
`scripts/characterization/test_bootstrap_isolate_before_reset.py`.

## Design decision

**Yes, isolate the sampling path before BOOT reset.** The delayed sequence
reduces the independently measured reset contribution to about
0.080 mV, below the 0.439-mV *total* raw-error allocation. However,
it does **not** make this candidate pass: the best final error is
-2.452 mV, about 5.59 times the allocation, and the turn-off event
dominates. The next design work should target MN11 turn-off charge and
the sampled-node coupling (including true CDAC bottom-plate ordering),
not simply increase the reset gap. A physical T28 implementation must
replace both ideal GMAIN relays, ensure a safe final off bias throughout
CDAC conversion, check next-cycle acquisition and all PDK terminals,
then repeat multi-input/PVT/full-CDAC tests before OA promotion.
