# T28 transmission-gate switch characterization

## Purpose and status

This is the first transistor-level sizing step for the SAR CDAC and sampling
paths. The circuit source is
`SAR_ADC_T28/tb_tg_switch_char/schematic`: one standard-VT `nch_mac` and one
standard-VT `pch_mac` in parallel, with explicit complementary gates and body
ties. It is a characterization fixture, not the production switch cell.

The current result provides a nominal TT starting point. It does not freeze a
width because process corners, temperature, supply variation, charge
injection, clock feedthrough, noise, and extracted parasitics are not yet
included.

## Measurement method

- Process/model surface: PDK sections emitted by the Virtuoso netlister, TT
- Temperature: 27 C
- Supply and control swing: 0.9 V
- Length: 30 nm
- Basic finger width: 0.25 um
- Signal common mode: 0.001 to 0.899 V in 0.01-V steps
- Differential probe across the on switch: 1 mV

At every common-mode point, Spectre solves the PDK transistor operating point
and the analysis extracts

```text
Ron = 1 mV / abs(I(VL)).
```

The OA-exported circuit netlist is preserved. Analysis decks change only the
two PDK `multi` values, source DC expressions, save statements, and analysis
statement. Using integer multiples of a real 0.25-um finger lets the PDK model
scale all device currents and parasitic terms consistently; it avoids changing
only `w` while leaving CDF-emitted junction geometry stale.

## Nominal TT results

All 12 Spectre cases completed with zero errors. Four meet the present
macro-model allocation `max Ron <= 1 kOhm`.

| Wn | Wp | Minimum Ron | Maximum Ron | Result |
| ---: | ---: | ---: | ---: | --- |
| 0.5 um | 0.5 um | 670.5 Ohm | 3645.6 Ohm | fail |
| 0.5 um | 0.75 um | 487.3 Ohm | 3000.9 Ohm | fail |
| 0.5 um | 1.0 um | 365.5 Ohm | 2659.9 Ohm | fail |
| 1.0 um | 1.0 um | 335.3 Ohm | 1822.8 Ohm | fail |
| 1.0 um | 1.5 um | 243.7 Ohm | 1500.5 Ohm | fail |
| 1.0 um | 2.0 um | 182.7 Ohm | 1329.9 Ohm | fail |
| 1.5 um | 1.5 um | 223.5 Ohm | 1215.2 Ohm | fail |
| 1.5 um | 2.25 um | 162.4 Ohm | 1000.3 Ohm | fail |
| 1.5 um | 3.0 um | 121.8 Ohm | 886.6 Ohm | pass |
| 2.0 um | 2.0 um | 167.6 Ohm | 911.4 Ohm | pass |
| 2.0 um | 3.0 um | 121.8 Ohm | 750.2 Ohm | pass |
| 2.0 um | 4.0 um | 91.4 Ohm | 665.0 Ohm | pass |

The minimum-total-width passing point is therefore

```text
nch_mac: W=2.0 um, L=30 nm
pch_mac: W=2.0 um, L=30 nm
```

Its measured resistance spans 167.6 to 911.4 Ohm and averages 392.7 Ohm. The
worst point is in the middle of the signal range, where neither device has the
large overdrive available near its preferred rail. This directly explains why
the earlier full-`VDS` single-device data could not safely determine switch
width.

## Leakage warning

For the 2-um/2-um candidate, a separate DC operating point with both devices
off and 0.9 V across the switch reports 36.0 nA absolute source current. This
is only one worst-stress fixture, not a code-dependent hold simulation, but it
is too large to ignore. If that current acted on the approximately 219.5-fF
effective CDAC top-plate capacitance for 5 ns, the simple bound would be about
0.82 mV, or 0.47 LSB. Actual error depends on the switch matrix, bottom-plate
voltages, common-mode cancellation, and leakage direction, so this estimate is
a screening warning rather than a signed ADC error prediction.

## Design decision and next gate

`Wn=Wp=2 um, L=30 nm` is retained only as the first TT sizing seed. It has
about 9% resistance headroom at TT and is not robust enough to freeze before
slow-process, low-supply, and hot-temperature checks. Minimum length also
aggravates leakage.

The next bounded iteration should compare:

1. standard-VT devices at longer channel length;
2. verified higher-VT candidates, if complementary NMOS and PMOS devices are
   available in this PDK;
3. enough width to retain `Ron <= 1 kOhm` at slow/low-voltage/hot conditions;
4. off leakage and hold error across realistic CDAC switch states;
5. transient settling, charge injection, and clock feedthrough with the
   selected CDAC/sample load.

Only after that iteration should a production `sar_sample_switch` or CDAC
bottom-plate switch cell be created.

## Artifacts

- `output/switch_characterization/schematic_readback.json`
- `output/switch_characterization/netlist/tb_tg_switch_char/input.scs`
- `output/switch_characterization/spectre/run_summary.json`
- `output/switch_characterization/analysis/summary.json`
- `output/switch_characterization/analysis/ron_vs_common_mode.csv`
- `output/switch_characterization/analysis/ron_vs_common_mode.png`
