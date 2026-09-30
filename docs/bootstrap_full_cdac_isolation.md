# Protected bootstrap in a full differential CDAC

Date: 2026-09-30. This is a **copied-netlist architectural and current-path
screen**, not a changed Virtuoso schematic or a physical T28 gate driver.
The full 5+5 split CDAC and matched top-plate comparison come from the exact
OA exports of `tb_sar_bottom_plate_eval` (ideal top/split clamp, SHA-256
`965cbc2f99712c0f5d72af0eefcf28abdf398340f31cff32d96a0e1fd36e50ac`)
and `tb_sar_bottom_plate_t28clamp_eval` (T28 NMOS clamp, SHA-256
`02c8ffc923915c279c1a316a1984e8cb677e6c3be06147a822f9d42aa36944ef`).
The protected bootstrap source is the exact SHA-256
`f466793e8655f2d81bdb7ce98d1041f00cdd90a374be3341750d2cb22a9bdd4d`
OA export plus the prior `reset_gap_1ns` copied-netlist transform.

The generator replaces the original `sar_bootstrap` subcircuit in each
full-CDAC copied deck with the protected T28/MN9-body-to-VSS/split-GMAIN
variant and adds independent `OFF_MAIN` to **22 bottom-input switches and
two top-plate sampling switches**. It changes PHIB's reset edge to
251.3 ns. The CDAC capacitors, bridge/dummy, top clamp, reference relays,
50-ohm sources, PDK model includes, and 252-ns reference connection are
otherwise unchanged. The two `GMAIN` steering elements remain ideal relays.

## Timing and interpretation

At TT/0.9 V/27 C, five static differential inputs from -0.8 to +0.8 V
were run with the ideal top clamp. `PHI` samples from roughly 211 to
250.1 ns. The top and split clamps release at 249.5 ns; `OFF_MAIN`
closes the sample path over 250.2-250.3 ns; PHIB resets BOOT at
251.3 ns; BASE connects the bottoms to VCM at 252 ns; raw held errors
are measured at 270 ns. The physical T28 clamp was checked at both
endpoints with VIN-relative off bias and at +0.8 V with VSS off bias.
An additional +0.8-V ideal-clamp deck saved representative MN11, reference,
and source-resistor currents without changing the circuit.

Before BASE connects the CDAC bottoms to VCM, `TOPP_BP-TOPN_BP` is an
intermediate floating-node transient, **not** a valid final raw error.
After handoff the bottom-plate polarity oracle is
`-(TOPP_BP-TOPN_BP) = VINP-VINN` for ideal capacitors. All table values
below are uncorrected raw errors at 270 ns. The top-plate control's
oracle is `TOPP_TOP-TOPN_TOP = VINP-VINN`.

## Held results

| Vdiff (V) | Ideal clamp, `GMAIN=VIN`: bottom (mV) | Ideal clamp, `GMAIN=VSS`: bottom (mV) | Same VSS-off deck: top control (mV) |
| ---: | ---: | ---: | ---: |
| -0.8 | +6.261925 | +0.004218 | +8.752611 |
| -0.4 | +0.012385 | +0.001827 | +3.447584 |
| 0 | approximately 0 | approximately 0 | approximately 0 |
| +0.4 | -0.012385 | -0.001827 | -3.447584 |
| +0.8 | -6.261925 | -0.004218 | -8.752611 |

With VIN-relative off bias, the matched ideal-clamp top-plate control
had a maximum raw error of 0.174132 mV. The ideal-clamp bottom path's
maximum 6.261925 mV fails the 0.439-mV allocation by 14.26 times.
The ±0.4-V points are much smaller than linear extrapolation from the
endpoints, so this is not a simple gain fit. Replacing only `SHOLD`'s
hold terminal from VIN with **ideal VSS** lowers the five-point bottom
maximum to 0.004218 mV. It does not make the switch physical: the top
control then fails, and the endpoint runs print T28 PDK warnings.

| Full-CDAC clamp and off bias | Inputs checked | Bottom raw error (mV) | Printed CMI warnings per endpoint |
| --- | --- | ---: | ---: |
| Ideal clamp, GMAIN=VIN | ±0.8 V | ±6.261925 | 0 |
| T28 clamp, GMAIN=VIN | ±0.8 V | ±8.322532 | 15 |
| Ideal clamp, GMAIN=VSS | ±0.8 V | ±0.004218 | 10 |
| T28 clamp, GMAIN=VSS | +0.8 V only | -7.538001 | 15 |

The earlier 0.00790-mV ideal-clamp and 2.0960-mV T28-clamp results used
the **original** `sar_bootstrap` subcircuit and are context, not a
one-factor baseline for this protected-switch substitution. There is no
physical-clamp VSS-off all-input pass claim.

## Current-path evidence

At +0.8 V with ideal clamp and `GMAIN=VIN`, the acquired B9 differential
was only -0.00404 mV from target. After BASE connects its bottom plates
to VCM, the B9 differential still measures +6.25783 mV. At 270 ns:

- High-side `GMAIN-B9P = +390.30 mV`; low-side `GMAIN-B9N` is about
  -400.00 mV. Source-relative `GMAIN=VIN` does not guarantee MN11 is off
  once its B9 terminal moves toward VCM.
- One representative high-side B9 MN11 has about -6.25772 uA drain-pin
  current; its B9 reference relay carries +6.25772 uA. The 50-ohm
  high-side source path carries 68.83530 uA, consistent with 11 similar
  bottom branches at about 6.258 uA each. VINP falls to 0.846558 V,
  a 3.442-mV source drop. The low-side B9 MN11 current is negligible.
- With only the ideal SHOLD off terminal changed to VSS, B9 differential
  after reference is 0.000024 mV. Representative high-side MN11 current
  at 270 ns falls to about -0.0000218 uA and source-resistor current to
  +0.000611 uA. The bottom held raw error becomes -0.004218 mV.

This is direct evidence of a **reverse-conduction path through MN11** in
the VIN-relative candidate, not just a terminal-voltage inference. The
current probe's +0.8-V held value differs from the ordinary-save run by
less than 1e-9 mV. It does not isolate every capacitance or explain all
transient charge during the earlier switch-off event.

The real T28 top clamp remains a separate blocker. With ideal VSS off bias
at +0.8 V, its B9 differential after reference is only 0.05838 mV, yet
the comparator top-plate raw error is -7.538001 mV. Thus the residual
cannot be ascribed simply to the sustained B9/MN11 path removed above;
the physical clamp's parasitics, switching and CDAC-node interaction
require their own controlled decomposition.

## Warnings, limits and decision

Spectre 21.1 completed all fifteen deck variants (five ideal-clamp VIN,
two T28-clamp VIN, five ideal-clamp VSS including the ordinary-save run,
one T28-clamp VSS, and two current probes) with zero simulator errors.
All runs printed four existing duplicate-model `SFE-1131` warnings.
The ideal-clamp VIN cases printed zero CMI warnings, whereas ideal-clamp
VSS endpoints printed ten `CMI-2752/2753` examples on pump MP8, with
686 further warnings suppressed. The physical-clamp VSS endpoint printed
15 CMI examples involving clamp devices and 3,751 further warnings
suppressed. These counts are truncated diagnostics, not a complete SOA
audit. The ideal-relay discontinuity also produced a Spectre LTE warning
in the VSS-off endpoint. No run includes transient noise, mismatch,
PVT, extracted parasitics, dynamic-input aperture, next-cycle acquisition,
or a transistor implementation of either GMAIN relay.

**Decision:** keep bottom-plate sampling and early main-switch isolation as
an architectural direction, but reject `GMAIN=VIN` as a full-CDAC hold
strategy. A realizable off-state control must prevent MN11 conduction for
the entire range of bottom-plate voltages encountered after reference
handoff, while meeting T28 gate-terminal stress rules. Separately redesign
or replace the physical top/split clamp and verify its own coupling and
SOA. The ideal-clamp VSS-off pass is a mechanism bound, not OA promotion
or sampling-block signoff. Exact copied decks, PSF, logs, per-case JSON,
and aggregate summaries are under ignored
`output/bootstrap_full_cdac_isolation/`; the generator/analyzer is
`scripts/characterization/run_bootstrap_full_cdac_isolation.py`.
