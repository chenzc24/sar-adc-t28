# Full-control bootstrap: netlist-only fast A/B screen

Date: 2026-09-30. This is a rapid **netlist-level** diagnostic, not an OA
schematic change or a production switch. Every variant is generated from the
same OA-exported
`SAR_ADC_T28/tb_sar_bootstrap_protected_full18_eval/schematic` source,
SHA-256 `f466793e8655f2d81bdb7ce98d1041f00cdd90a374be3341750d2cb22a9bdd4d`.
The generator makes only the stated device-pin/class/geometry, clock-width,
or ideal-relay edits in separate copied decks. Original OA, original export,
and PDK models were not modified. Code and exact variant rules are in
`scripts/characterization/screen_bootstrap_netlist_ab.py`.

## Conditions and screening gates

- Spectre 21.1, T28 PDK include sections `pre_simu`, `noise_worst`,
  `ttmacro_mos_moscap`, `tt_res_bip_dio_disres`, `tt_mom`, `tt_ind_jvar`,
  and `tt_r_metal`; nominal 0.9 V, 27 C. No transient noise source was
  enabled.
- Differential input: high-side 0.85 V, low-side 0.05 V from 205 ns;
  50-ohm input source resistance per side, 219.5-fF output capacitance per
  side. Read acquisition at 249.8 ns and raw hold at 270 ns. Nominal
  differential raw-error gate is 0.439 mV. Only one static input magnitude
  and one corner were simulated.
- Original `PHI` falls over 250.0-250.1 ns and `PHIB` rises over
  251.0-251.1 ns. The early-PHIB variants move its rising edge to
  250.2-250.3 ns without changing the first PHIB edge.
- MOS D/G/S/B peak voltage comparisons use the existing diagnostic
  0.99-V core and 1.98-V 1.8-V model-warning levels over the *entire*
  transient. These are not foundry SOA/lifetime rules. `CMI-275x` counts
  below are printed warnings; five can mean more were suppressed by
  `maxwarns=5`. All runs have four unrelated model-include duplicate
  `scalefactor` warnings.

## Eight matched results

| Variant | Change from control | Held raw error (mV) | High-side hold input current (uA) | Printed CMI | Verdict |
| --- | --- | ---: | ---: | ---: | --- |
| `baseline` | exact OA DUT | -8.755 | 25.858 | 0 | fails accuracy and leakage |
| `body_vss_core` | MN9 B: VIN -> VSS only | -8.806 | 0.00326 | 5 | junction path removed; core `Vgb` unsafe |
| `body_vss_18` | MN9 B=VSS, known `nch_18_mac` L/W/geometry | -6.842 | 0.0000343 | 0 | leakage removed; accuracy fails |
| `early_phib` | PHIB rising 0.8 ns earlier | -8.656 | 25.858 | 0 | clock shift alone ineffective |
| `body_vss_18_early` | thick MN9 plus early PHIB | -6.962 | 0.0000343 | 0 | accuracy slightly worse than thick alone |
| `body_vss_18_source_off_bound` | replace shared G-ground clamp with ideal G-to-VIN relay | -1.102 | 76.974 | 0 | reject: reverse MN9 channel current; ideal relay |
| `split_main_gate_bound` | separate MN11 `GMAIN`, ideal sample/hold gate relays | -3.014 | 0.0000386 | 0 | useful mechanism bound, fails raw gate |
| `split_main_gate_bound_early` | separate gate plus early PHIB | -2.482 | 0.0000386 | 0 | best valid-leakage bound, still 5.65x raw gate |

The `body_vss_18` variant copies a known, already-netlisted 1.8-V NMOS
geometry (L=150 nm, W=320 nm, multi=4) from this DUT; it is **not** a
width-matched one-factor comparison with the original MN9 (L=60 nm,
W=250 nm, multi=4). Its 1.96-mV improvement cannot be attributed solely
to the body-connection change. The pure body-only experiment shows almost
no accuracy improvement and creates core `Vgb` warnings (two device-side
diagnostic limit crossings, five printed CMI examples).

The shared source-relative-off bound demonstrates a subtle reverse-channel
problem: in hold, `G≈VIN≈0.85 V` turns the **main** switch off, but MN9's
other terminal is `BBOT≈0.06 V`; its `Vgd≈0.79 V` is sufficient to conduct
from VIN toward BBOT in the reverse D/S direction. The saved MN9 drain
pin then carries about -95 uA and input source current is about 77 uA.
This is not solved by eliminating its forward body junction. The main
and bootstrap-input switch gates need independent off-state control.

In the split-gate bound, `STRACK` ideally links `GMAIN` to the boosted G
during sample and `SHOLD` ideally links it to VIN in hold; the real MN9
continues to see G discharged low. With the original timing, the output
error reaches about -2.86 mV by 251.0 ns while GMAIN remains high during
the non-overlap gap. With early PHIB it reaches about -2.48 mV by 250.5 ns
and then holds. Ideal switches omit their own clock feedthrough, charge
injection, area, device voltage stress, clock-driver cost, and turn-on/off
limitations. Thus -2.482 mV is only an optimistic topology indication, not
a T28 implementation result.

The acquisition checkpoint remains within about 0.0004 mV of the ideal
0.8-V differential input for all eight runs, but this single post-settling
point is **not** an input-bandwidth or Ron sweep. Output-node MN11/load
current KCL peaks below `3e-6 nA` residual, and the saved 50-ohm source
drop/current relation agrees below `1e-8 nA`. Each run completed with
zero Spectre errors. Machine-readable summary, exact generated decks,
logs, and PSF are in ignored `output/bootstrap_netlist_fast_ab/`.

## Decision

No variant passes the 0.439-mV raw target, so do not copy any of them to
OA or launch PVT/full-CDAC signoff. The high-confidence finding is that
the MN9 off-state forward-junction path must be removed to eliminate the
25.86-uA baseline input loading, yet doing so is insufficient for sampling
accuracy.
Advancing one shared PHIB edge is also insufficient. Separate main-gate
control is the next architectural direction, but the first independent
T28-transistor version must implement both sample/hold gate links and
stress-safe MN9 reset, then remeasure leakage, edge charge, acquisition,
and all D/G/S/B voltages. A true bottom-plate/CDAC charge-invariance test
is a separate fixture; the simple 219.5-fF hold capacitor cannot validate
that mechanism, and a one-point dummy-capacitor fit would be misleading.
