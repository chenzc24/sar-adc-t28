# Bootstrap MN11 turn-off charge screen

Date: 2026-09-30. This is a **copied-netlist, mixed PDK/ideal-control**
mechanism test. It does not alter Virtuoso OA, the original export, or PDK
files, and it is not a complete physical switch. The source is the exact
`SAR_ADC_T28/tb_sar_bootstrap_protected_full18_eval/schematic` export with
SHA-256 `f466793e8655f2d81bdb7ce98d1041f00cdd90a374be3341750d2cb22a9bdd4d`.
It uses the previous split-`GMAIN` topology: MN11 and the bootstrap MOS are
T28 PDK devices, while `STRACK` and `SHOLD` are ideal Spectre relays.

## Conditions and measurement

Spectre 21.1 ran nine TT/0.9-V/27-C transients at `VINP=0.85 V`,
`VINN=0.05 V`, with 50-ohm sources, ideal capacitive loads, and no transient
noise, mismatch, layout parasitics, or complete CDAC. `PHI` falls over
250.0-250.1 ns; `OFF_MAIN` begins returning high at 250.2 ns; PHIB resets
BOOT at 251.3 ns. We measure the differential VOUT change from 250.18 to
251.28 ns, before reset, and raw held error at 270 ns. Both are separate
from the acquisition error and from the +0.080-mV later reset contribution.

The clock screen changes only `VOFFMAIN`'s return-edge parameter. The load
screen changes only both ideal `CLOAD` values. After waveform inspection
showed that the ideal relay made the actual `GMAIN` edge much faster than its
clock, the driver screen changes only `SHOLD.rclosed`; `STRACK` remains 1 ohm.
The 90%-to-10% `GMAIN` timing uses its boosted pre-off voltage and the
corresponding VIN as endpoints.

## Results

All errors are differential, raw, and in mV. `Qdiff` is the difference of
integrated P/N MN11 drain-terminal currents over 250.18-251.28 ns. It
includes channel and displacement contributions; it is **not** a direct
measurement of channel charge injection alone.

| One-factor case | Load per side (fF) | SHOLD Rclosed | OFF_MAIN edge (ps) | Actual GMAIN P 90-10 (ps) | Pre-reset error (mV) | Held error (mV) | Qdiff (fC) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Clock 50 ps | 219.5 | 1 ohm | 50 | 1.14 | -2.406 | -2.326 | 0.551 |
| Baseline | 219.5 | 1 ohm | 100 | 1.64 | -2.532 | -2.452 | 0.578 |
| Clock 300 ps | 219.5 | 1 ohm | 300 | 3.18 | -2.836 | -2.756 | 0.645 |
| Clock 600 ps | 219.5 | 1 ohm | 600 | 4.98 | -2.999 | -2.919 | 0.682 |
| Load 109.75 fF | 109.75 | 1 ohm | 100 | 1.63 | -3.126 | -2.969 | 0.347 |
| Load 439 fF | 439 | 1 ohm | 100 | 1.64 | -1.742 | -1.701 | 0.805 |
| Hold 1 kohm | 219.5 | 1 kohm | 100 | 20.6 | -2.595 | -2.514 | 0.592 |
| Hold 5 kohm | 219.5 | 5 kohm | 100 | 74.4 | -2.644 | -2.563 | 0.603 |
| Hold 20 kohm | 219.5 | 20 kohm | 100 | 293 | -2.727 | -2.647 | 0.621 |

The exact values and deck hashes are in ignored
`output/bootstrap_turnoff_charge_screen/summary.json`; per-case decks,
Spectre logs and PSF are alongside it. Values in the last three `Qdiff`
entries should be read from that JSON when precision matters; the table is
rounded for comparison.

In the baseline, the pre-off raw error is +0.1015 mV, the **turn-off-window
step** is -2.6335 mV, and the pre-reset raw error is -2.5320 mV. These are
different quantities. The later reset yields approximately +0.0802 mV,
leaving -2.4518 mV at 270 ns. The best screened held error is still
-1.701 mV with a doubled ideal load, about 3.87 times the 0.439-mV
allocation; that load is not the canonical split CDAC and is not a proposed
fix by itself.

## Interpretation and limits

The 50-600-ps **clock** scan is not a comparable 50-600-ps **gate-slew**
scan. The ideal relay switches near its threshold; actual `GMAIN` 90-10 is
only 1.1-5.0 ps. Increasing `SHOLD` resistance does extend `GMAIN` 90-10
from 1.64 to 20.6, 74.4, and 293 ps, yet the held error worsens from
-2.452 to -2.514, -2.563, and -2.647 mV. The 20-kohm case still has
about +0.292 mV high-side gate-to-VIN residual just before reset. Neither
slower ideal-relay clocking nor weaker gate pull-down is an effective cure
in this bounded screen. The 1-ohm relay's picosecond gate edge is not a
plausible transistor-driver result.

Doubling the load reduces the voltage error but not in a simple `1/C`
ratio: `Qdiff` changes from 0.347 to 0.578 to 0.805 fC across half,
nominal, and double load. Thus the circuit cannot be represented as one
load-independent injected-charge source. MN11 drain current supplies the
output-load current by KCL, but its PDK terminal current combines possible
channel conduction and capacitive/displacement coupling. These runs do not
uniquely apportion those mechanisms or validate true CDAC bottom-plate
sampling.

All nine Spectre runs ended with zero errors and zero printed `CMI-275x`
warnings. Each printed four existing duplicate-model `SFE-1131` warnings.
The saved-MOS terminal screen crossed none of the previous diagnostic
0.99/1.98-V comparison levels, but that is not foundry SOA/lifetime
qualification. The output KCL peak residual stayed below `5e-6 nA`;
numerical load-current integration differed from `C*deltaV` by at most
0.0075 fC. The generated deck comparison confirms that each screen changed
only its named source/load/relay statement plus the case comment.

## Decision

Keep the independent **main-switch-off before BOOT reset** sequence as a
candidate control order, but do not promote this ideal-relay topology to OA.
The next useful topology test must change where the MN11 turn-off charge
goes, rather than merely adjusting clock slew or increasing an isolated
hold capacitor. In particular, compare a true full-CDAC bottom-plate
sequence and a realizable T28 main-gate isolation/driver, then rerun
multi-input, next-cycle, PVT, and reliability checks.
