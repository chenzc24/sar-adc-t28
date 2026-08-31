# Transistor-level bootstrap-driver prototype

## Scope and source

This target creates the first transistor-level sampling-switch prototype in
`SAR_ADC_T28/sar_bootstrap`. It is an electrical feasibility vehicle, not a
production cell or reliability-approved implementation.

The charge-pump and protected bootstrap topology follows Andrew M. Abo,
*Design for Reliability of Low-voltage, Switched-capacitor Circuits*, UC
Berkeley, 1999, Figure 5.5 (PDF page 69 / printed page 55). In particular,
`MN1`, `MN2`, and `MN3` are NMOS pass devices. The first resumed OA version
incorrectly contained PMOS devices in these positions and was rejected before
the correlated run.

The local reference copy is intentionally ignored at
`output/bootstrap_driver_design/references/SC_Dissertation.pdf`.

## Implemented electrical hierarchy

The checked OA hierarchy contains:

- `MN1/MN2` and `CP1/CP2`: cross-coupled clock multiplier;
- `MN3`: unidirectional bootstrap-capacitor precharge device;
- `CBOOT`: ideal, finite 200-fF seed capacitor;
- `MN12`: bottom-plate precharge/discharge device;
- `MP4/MN5/MN13/MP8`: phase control and boosted-path isolation;
- `MN7/MN10`: protected main-gate discharge path;
- `MN9`: DNW source/body-following path;
- `MN11`: DNW main sampling switch, `L=60 nm`, total `W=2 um`;
- a 50-ohm source and 219.5-fF representative one-side CDAC load.

`PHI` and `PHIB` are ideal external non-overlap clocks. The pump capacitors
and `CBOOT` are ideal schematic capacitors; no MOM selection, extracted
parasitics, clock generator, mismatch, or noise is included.

The input changes while the switch is off at 205 ns. The sampled output must
therefore acquire a new low, mid, or high input after `PHI` rises at 211 ns;
the operating point cannot masquerade as a successful acquisition.

## OA-to-Spectre correlation

Both `sar_bootstrap/schematic` and
`tb_sar_bootstrap_transient/schematic` have zero check markers. Readback
confirms every MOS B/D/G/S connection, all capacitor terminals, the six symbol
ports, and the dynamic input source.

Spectre decks are mechanically parameterized wrappers around the automatic OA
export. The exported circuit was not hand-edited. Its SHA-256 is:

`f3818ef606de602671beac8b6728a1f5460958d03ca0299de0fc79e28132242c`

The main nominal screen changes only `CBOOT`. The width screen changes only the
exported `MN11` multiplicity in analysis wrappers and retains the same source
hash; the OA seed remains 2 um.

## Nominal results

Nine TT / 0.9-V / 27-C cases covered three input levels and 100/200/400-fF
`CBOOT`. All Spectre jobs completed. The acquisition, gate-overdrive, and
bootstrap-droop requirements passed in every case:

| Quantity | Observed range / worst case | Target |
| --- | ---: | ---: |
| Acquisition settling time | 0.419 to 0.681 ns | 39-ns aperture |
| End-of-aperture acquisition error | 0.000113 to 0.000729 mV | <= 0.439 mV |
| Main-switch `VG-VIN` | 0.780 to 0.841 V | 0.70 to 1.05 V |
| `CBOOT` droop | <= 2.421 mV | <= 43.9 mV |
| Held-sample error at 270 ns | <= 6.463 mV absolute | <= 0.439 mV |

The held-sample criterion fails all nine nominal cases. At the 200-fF seed the
error is approximately +6.463 mV, +1.650 mV, and -5.552 mV for 0.05-V,
0.45-V, and 0.85-V inputs. The sign reversal shows that the error is
signal-dependent, not a removable common offset.

## Main-switch width screen

At `CBOOT=200 fF`, total `MN11` widths of 0.25, 0.5, 1, and 2 um were screened
at the same three input levels. All twelve runs completed and met acquisition,
gate-overdrive, and droop limits. Reducing width traded settling time for a
worse low-input held error:

| `MN11` total W | Worst settling time | Worst absolute held error |
| ---: | ---: | ---: |
| 0.25 um | 4.056 ns | 11.348 mV |
| 0.50 um | 2.108 ns | 11.296 mV |
| 1.00 um | 1.137 ns | 9.703 mV |
| 2.00 um | 0.653 ns | 6.463 mV |

Therefore 2 um remains the next-iteration seed. The failure is not explained
by main-switch channel charge alone; boosted-gate turn-off coupling, nonlinear
parasitics, the DNW follower, and the floating hold node must be separated in
the next transient fixture. A differential sampling test is also required to
measure what cancels and what becomes gain/nonlinearity error.

## Reliability gate

Spectre explicitly reports model safe-operating-area warnings. The nominal
waveforms reach approximately 1.79 V maximum absolute gate-to-bulk difference
in `MN1/MN2/MN3`; `MN7` reaches about 1.29 V `VDS`. The PDK warning threshold
shown in the logs is 0.99 V for several core-device terminal limits.
Simulation convergence is therefore not reliability evidence.

Before global PVT, the charge-pump/protection network must be redesigned with
verified foundry device classes and/or additional stacking and bias control.
The exact allowed transient duration and terminal combinations must come from
the foundry reliability rules; substituting 1.8-V devices by guess is not an
approved fix.

## Decision and next work

Keep `CBOOT=200 fF` and `MN11 nch_dnw_mac L=60 nm, W=2 um` only as an
electrical seed. Do not begin global PVT or freeze `sar_sample_switch` yet.
The next transistor-level iteration must:

1. isolate hold-step contributors with controlled ideal-gate and parasitic
   ablation fixtures, then test a differential sampling pair and bottom-plate
   timing;
2. replace or protect the clock-multiplier devices using foundry-supported
   terminal-voltage rules;
3. repeat the nominal acceptance screen; and
4. only after nominal held error and SOA warnings are resolved, expand to
   SS/TT/FF, supply, temperature, mismatch, and extracted parasitics.
