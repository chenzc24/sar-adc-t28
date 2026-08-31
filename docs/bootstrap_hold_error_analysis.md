# Bootstrap held-sample error ablation

## Purpose and scope

This diagnostic separates the deterministic held-sample error of the first
transistor-level bootstrap prototype into contributions from the selected main
DNW sampling device and from the complete bootstrap driver. It does not change
the OA schematic, waive the separate reliability blocker, or qualify the
sampling path across PVT, noise, mismatch, or extracted parasitics.

All 40 cases ran in Spectre 21.1 at TT, 0.9 V, and 27 C. The source is the
unedited OA export of `SAR_ADC_T28/tb_sar_bootstrap_transient`; its SHA-256 is
`f3818ef606de602671beac8b6728a1f5460958d03ca0299de0fc79e28132242c`.
Every mode uses the exact exported `nch_dnw_mac` main device statement with
`L=60 nm`, `W=2 um`, and multiplier 8. The representative load is 219.5 fF,
the ideal-gate fall time is 100 ps, and held values are measured at 270 ns.

## Fixtures

Six nominal modes are compared:

- `full_single` and `full_diff` retain the complete exported bootstrap
  hierarchy.
- `isolated_single` and `isolated_diff` retain only the main NMOS and use an
  ideal source-relative gate drive. The gate follows the input in hold, so
  `VGS=0`. This intentionally cancels signal-dependent turn-off and is a
  diagnostic control, not a realizable fixed-ground clock.
- `absolute_single` and `absolute_diff` retain only the main NMOS, use an ideal
  constant 0.9-V sample overdrive, and drive the gate to absolute 0 V in hold.
  This is the practical ideal-bootstrap reference for the main device.

The raw deterministic acceptance limit remains `0.25 LSB = 0.439 mV`.

## Nominal results

| Mode | Cases passing raw held-error limit | Maximum held error | Differential/error gain | Maximum linear-fit residual |
| --- | ---: | ---: | ---: | ---: |
| Complete single-ended driver | 0 / 3 | 6.463 mV | -1.502% | 0.796 mV |
| Relative-off isolated main | 0 / 3 | 2.946 mV | approximately 0% | 0.0000014 mV |
| Absolute-off isolated main | 0 / 3 | 4.972 mV | -0.174% | 0.033 mV |
| Complete differential pair | 1 / 5 | 12.026 mV | -1.510% | 0.109 mV |
| Relative-off isolated pair | 5 / 5 | below 1 nV | approximately 0% | below 1 nV |
| Absolute-off isolated pair | 1 / 5 | 1.390 mV | -0.173% | 0.0086 mV |

The complete differential errors at input differences of
`-0.8/-0.4/0/+0.4/+0.8 V` are approximately
`+12.026/+6.150/0/-6.150/-12.026 mV`. They are therefore dominated by gain
compression rather than random or strongly curved error. Removing the best-fit
gain leaves only 0.109 mV maximum residual, below 0.439 mV. This shows that a
future gain calibration could make the deterministic residual acceptable, but
calibration is not part of the current specification and cannot be used to
declare the raw sampling path compliant.

The practical absolute-off isolated pair has only 11.56% of the complete
pair's maximum differential error. Subtracting its fitted gain from the full
driver shows that the driver network adds `-1.337%` differential gain error.
The current dominant correction target is consequently the bootstrap driver,
not another blind main-switch width sweep.

## Turn-off evidence

At 270 ns, the complete driver discharges the main gate to approximately
80.24-80.28 mV absolute. Its resulting off-state `VGS` changes from about
`+30.28 mV` at `VIN=0.05 V`, through `-369.74 mV` at `VIN=0.45 V`, to
`-768.46 mV` at `VIN=0.85 V`. The fixed absolute gate combined with a changing
source voltage is consistent with the observed signal-dependent turn-off
error. It is evidence of the mechanism, not by itself a proof that one device
or node is solely responsible.

The source-relative control produces the same approximately `-2.946 mV`
single-ended shift at all three inputs, which cancels in a matched differential
pair. The practical absolute-off control retains a signal-dependent component,
confirming that the selected main device itself contributes a smaller
approximately `-0.173%` gain term.

## Load and ideal-edge sensitivity

The isolated-device turn-off error falls as the hold capacitance grows or the
ideal gate edge slows, consistent with capacitive charge redistribution.

| Control and input | 109.75 fF | 219.5 fF | 439 fF |
| --- | ---: | ---: | ---: |
| Relative-off, 0.05 or 0.85 V | -5.154 mV | -2.946 mV | -1.590 mV |
| Absolute-off, 0.05 V | -6.209 mV | -3.582 mV | -1.942 mV |
| Absolute-off, 0.85 V | -9.283 mV | -4.972 mV | -2.579 mV |

| Control and input | 100 ps | 500 ps | 2 ns |
| --- | ---: | ---: | ---: |
| Relative-off, 0.05 or 0.85 V | -2.946 mV | -1.971 mV | -1.214 mV |
| Absolute-off, 0.05 V | -3.582 mV | -2.311 mV | -1.365 mV |
| Absolute-off, 0.85 V | -4.972 mV | -3.975 mV | -2.819 mV |

Slowing an ideal edge is diagnostic, not yet a design recommendation: it can
increase aperture uncertainty and must eventually be checked against sampling
linearity, clock jitter, and available acquisition time.

## Decision and next circuit target

Do not freeze the current bootstrap prototype or expand it to global PVT. The
next bounded transistor iteration should first sweep the gate-discharge and
isolation path around `MN7`, `MN10`, and `MP8`, together with non-overlap
timing, while measuring the main-gate turn-off trajectory and differential
gain. After reducing the driver-added term, evaluate dummy-switch or
bottom-plate timing remedies for the remaining main-device contribution.

The earlier approximately 1.79-V core-device terminal stress remains an
independent blocker. A held-error improvement does not constitute foundry SOA
approval or reliability closure.

Generated evidence is under `output/bootstrap_hold_ablation/`: the merged run
summary, per-case CSV, numerical analysis JSON, waveforms, and sensitivity
plot. These generated files are intentionally not Git sources of truth.
