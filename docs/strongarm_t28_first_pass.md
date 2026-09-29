# T28 StrongARM comparator — first transistor-level pass

## What was built

`SAR_ADC_T28/sar_strongarm_t28/schematic` is an 11-MOS dynamic StrongARM
using only `tsmcN28/nch_mac` and `tsmcN28/pch_mac`, not analogLib MOS devices.
It has a matching `/symbol` and a separate
`SAR_ADC_T28/tb_sar_strongarm_t28/schematic`. The previous
`sar_comparator_macro` and Analog Canvas reference were not modified. The
Analog Canvas circuit supplied only the topology; its generic 150-nm devices
and dimensions were not copied.

During `CLK=0`, four PMOS reset X, Y, OUTP, and OUTN to VDD, while the NMOS
tail is off. On the rising edge, reset turns off and the tail turns on. The
VINP/VINN differential pair first develops an X/Y difference; two
cross-coupled NMOS and two cross-coupled PMOS regenerate the output. The
explicit pin convention is `VINP>VINN -> OUTP>OUTN`. X/Y are internal
precharge/sense nodes, not externally valid digital outputs.

| Devices | Function | Wfg | L | Fingers × simM |
| --- | --- | ---: | ---: | ---: |
| `MNINP`, `MNINN` | Differential pair | 1 µm | 30 nm | 1 × 1 |
| `MNTAIL` | Clocked tail | 1 µm | 30 nm | 1 × 1 |
| `MNLATP`, `MNLATN` | NMOS regeneration | 0.5 µm | 30 nm | 1 × 1 |
| `MPLATP`, `MPLATN` | PMOS regeneration | 0.5 µm | 30 nm | 1 × 1 |
| `MPRSTX/Y/P/N` | Clock-low precharge | 0.5 µm | 30 nm | 1 × 1 |

The widths are **initial engineering seeds**, not optimized or frozen.
The preceding TT single-device data put a 1-µm NMOS at about 0.859 mS gm
near `VGS=0.455 V, VDS=0.9 V`, considerably above the macro model's
92–139 µS effective-regeneration starting bound. But a dynamic latch has
time-varying drain/source biases and a composite effective gm; the single
device point cannot prove the latch timing. It motivated the initial widths,
which were then tested with the actual PDK transient. There is no claim yet
about optimum power, kickback, noise, offset, or layout dimensions.

## Exact test condition and result

The testbench uses ideal differential DC input sources at 0.45-V common
mode, a 0-to-0.9-V clock with 20-ps edges and 5-ns period, a 0.9-V supply,
and 5-fF ideal capacitor loads on each output. Nominal model sections are
TT at 27 °C. The decision metric is the time from the first clock rising
0.45-V crossing (5.01 ns) to a **signed 0.45-V output differential**.
Reset is checked before the first edge and before the second. This isolates
the comparator; it does not include CDAC drive, SAR-logic load, supply
impedance, or a finite-impedance input network.

| Applied differential input `VINP−VINN` | Resolution time | Correct polarity and reset |
| ---: | ---: | :---: |
| +10 mV / −10 mV | 150.07 ps / 150.07 ps | yes / yes |
| +0.878906 mV / −0.878906 mV | 207.44 ps / 207.44 ps | yes / yes |
| +0.439453 mV / −0.439453 mV | 223.35 ps / 223.35 ps | yes / yes |

All six Spectre 21.1 transient runs finished with zero errors and satisfy
the nominal 1.5-ns window under these specific conditions. At +0.439453
mV, X and Y are both about 0.9 V during reset. At 5.02 ns, Y is about
1.08 mV below X (VINP is higher), establishing the correct input-pair
initial difference. The cross-coupled network then regenerates; by 5.3 ns,
OUTP/OUTN are about 0.899/0.057 V and by 6.5 ns about
0.900/0.00005 V. Both outputs return to about 0.9 V before the next
comparison. The late X/Y trajectory must not be interpreted as an output
polarity sign by itself, because the feedback network is already active.

## Source-of-truth and warnings

Bridge `t28_io` 0.8.0 exported the exact OA testbench. The final exported
`input.scs` SHA-256 is
`628f493c46c7c4df1e5e6262ab563c466958fd7ce182489515c507f3689be581`.
It includes the T28 model path and `ttmacro_mos_moscap` section. Each
simulation deck changes only the exported top-level `vinn/vinp` variable
declaration and adds transient/save statements; the DUT subcircuit is
unchanged. OA readback verified every MOS master, terminal, width, length,
clock/input/load connection, symbol port, and **zero schematic check
markers** for both owned schematics. The generated netlists, readback JSON,
PSF, and per-case metrics remain under ignored
`output/strongarm_t28_first_pass/`.

Spectre reported four PDK `SFE-1131` warnings about repeated scoped
`scalefactor` definitions; the last value was used, and all six runs
completed. The first export attempt hit a local SSH ControlMaster transport
failure; rerunning with `VB_DISABLE_CONTROL_MASTER=1` succeeded. The first
test deck placed input values before an OA-exported unassigned parameter
declaration and therefore failed elaboration; moving values onto that
declaration resolved it. One testbench schematic marker arose because an
input source instance was also named `VINN`; renaming only that instance
`VNN_SRC` cleared it, and the full sweep was repeated from the final OA
export.

## What remains open

This is a **nominal functional prototype**, not an accepted ADC comparator.
The initial 0.316-mV RMS input-referred noise and 0.439-mV systematic-offset
allocations have not been measured. Next, use transient noise and input
overdrive sweeps near zero, mismatch Monte Carlo, and PVT/voltage/load
corners to measure decision-error probability and metastability tails.
Place finite CDAC/source impedance on the input to quantify kickback and
CDAC disturbance, check supply/clock loading and energy per comparison,
then resize input, tail, latch, and reset devices based on those results.
Finally complete layout, extracted simulation, DRC, and LVS. A deterministic
±0.439-mV nominal result is not an offset or yield measurement.

## Reproduction

From the repository root, with the workspace bridge environment and the
remote `t28_io` profile active:

```powershell
uv run --project ..\..\virtuoso-bridge-lite python scripts\characterization\create_strongarm_t28.py --readback-only
$env:VB_DISABLE_CONTROL_MASTER='1'
uv run --project ..\..\virtuoso-bridge-lite python scripts\characterization\run_strongarm_t28.py
```

The creator's default mode is intentionally create-only and refuses to
overwrite the existing OA cells.
