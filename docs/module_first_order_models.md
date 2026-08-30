# Module-Level First-Order Models

## Scope

This report closes the abstraction layer between the behavioral SAR ADC and
the first transistor-level block designs. A SAR ADC is periodically switched
and nonlinear, so there is no single useful whole-ADC small-signal transfer
function. The circuit is separated by operating phase:

- CDAC/reference conversion settling: first-order `Rref + Ron` driving Cside
- input acquisition: first-order `Rsource + Ron` driving Cside
- comparator decision: linearized positive-feedback `gm_eff/Cnode` regeneration
- sample clock: input-slope sensitivity to RMS timing jitter

Only the first three involve KCL/KVL. The clock calculation is deliberately
not presented as an AC simulation.

## Combined nominal constraint view

The following numbers use the characterized 6.86047 fF capacitor comparison
point, the ideal split-array equivalence `Cside = 33*Cu = 226.39551 fF`, and
the existing 10-bit/1.8 V differential range.

| Phase or block | First-order requirement | Representative result |
|---|---|---|
| sampling kT/C | `sqrt(2kT/Cside) <= 0.18 LSB` | 0.10885 LSB RMS |
| 40 ns acquisition | residual `< 0.25 LSB` | `Rsource + Ron <= 21.242 kΩ` |
| 3 ns CDAC settling | residual `< 0.25 LSB` | `Rref + Ron <= 1.593 kΩ` |
| 1.5 ns comparator decision | resolve 0.25 LSB to 0.45 V with Cnode=20 fF | `gm_eff >= 92.42 uS` |
| sample-clock jitter | 20 ps RMS, 4.5 MHz, -1 dBFS | 0.320738 mV = 0.182464 LSB RMS |

The 3 ns CDAC plus 1.5 ns comparator partition leaves 0.5 ns of the 5 ns bit
cycle for clock edge placement, switch transition, latch reset margin, and
logic handoff. It is a feasibility point, not a frozen timing plan.

## Sampling acquisition

The single-pole differential residual after acquisition is

```text
Eacq = 1.8*exp(-Tacq/((Rsource + Ron)*Cside)).
```

With `Tacq = 40 ns`, the allowed resistance decreases as Cu increases:

| Cu | Cside | Maximum Rsource + Ron |
|---:|---:|---:|
| 3.000 fF | 99.000 fF | 48.576 kΩ |
| 4.000 fF | 132.000 fF | 36.432 kΩ |
| 6.86047 fF | 226.396 fF | 21.242 kΩ |
| 8.000 fF | 264.000 fF | 18.216 kΩ |
| 16.000 fF | 528.000 fF | 9.108 kΩ |
| 35.6304 fF | 1175.803 fF | 4.090 kΩ |

Three Spectre 21.1 transients matched the analytical residual. At Cu=6.86047
fF, 6 kΩ total has essentially complete settling, 20 kΩ produces 0.14919 LSB
and passes, while 25 kΩ produces 0.87308 LSB and fails.

This envelope is the starting point for the sampling switch W/L. After the
input driver's worst-case output resistance is assigned, the remaining
resistance is the maximum allowed switch Ron. The transistor width must then
be swept with the PDK over input voltage, common mode, body bias, PVT, and
clock amplitude. A constant-R switch does not validate THD, charge injection,
clock feedthrough, leakage, or bootstrapping.

## Comparator regeneration

The comparator is modeled in its regenerative phase rather than with a static
AC gain:

```text
tau_reg = Cnode/gm_eff
tdecision = tau_reg*ln(Vresolved/Vinitial).
```

The first sweep directly maps an input-referred 0.25 LSB initial differential
to the internal regeneration state and uses `Vresolved = 0.45 V`. Under that
unit-gain sensitivity assumption, the logarithmic voltage gain is exactly
`ln(1024) = 6.93147`.

For a 20 fF regeneration node:

| Decision budget | Required gm_eff |
|---:|---:|
| 0.5 ns | 277.26 uS |
| 1.0 ns | 138.63 uS |
| 1.5 ns | 92.42 uS |
| 2.0 ns | 69.31 uS |

Three positive-feedback Spectre transients matched the analytical crossing
times within 0.02 ps:

| Cnode | gm_eff | tau_reg | Analytical decision | Spectre decision | Result |
|---:|---:|---:|---:|---:|---|
| 20 fF | 100 uS | 200 ps | 1.386294 ns | 1.386282 ns | passes 1.5 ns |
| 20 fF | 50 uS | 400 ps | 2.772589 ns | 2.772583 ns | fails 1.5 ns |
| 20 fF | 200 uS | 100 ps | 0.693147 ns | 0.693128 ns | passes 1.0 ns |

The nominal minimum-L NMOS characterization near `gm/Id=15 1/V` reports
`gm/W = 429.67 uS/um` and `Id/W = 28.66 uA/um`. If one device's gm mapped
directly to the required 92.42 uS, it would suggest about 0.215 um width and
6.17 uA. These are scale references only: a StrongARM's effective
regeneration gm combines multiple time-varying devices, and its Cnode includes
device, wiring, and following-stage capacitance. The physical latch can be
larger and consume more current.

This model does not prove the allocated 0.316 mV RMS comparator noise or
0.439 mV systematic offset. Those require transistor-level transient-noise,
input-referred noise extraction, PVT, and mismatch Monte Carlo after the
topology and device dimensions exist.

## Clock jitter sensitivity

For a differential sine with peak amplitude A and independent RMS sampling
jitter `sigma_t`, the input-referred RMS error is

```text
sigma_jitter = 2*pi*fin*A*sigma_t/sqrt(2).
```

At -1 dBFS, 4.5 MHz, and 20 ps RMS, the result is 0.320738 mV RMS or
0.182464 LSB RMS, reproducing the stage-1 error budget. A 0.18 LSB comparison
line would correspond to 19.73 ps RMS; the tracked 20 ps value remains its own
top-down clock allocation rather than being silently tightened here.

Clock buffer edge rate, aperture definition, duty cycle, inter-phase skew,
SAR-clock jitter, and coupling into the analog nodes remain implementation
questions. An AC clock model would not answer them.

## Virtuoso and Spectre evidence

The remote OA library now contains two additional equivalent schematics:

- `SAR_ADC_T28/tb_sampling_acquisition/schematic`
- `SAR_ADC_T28/tb_comparator_regeneration/schematic`

Both were read back and exported by the Virtuoso Spectre netlister. The
sampling netlist contains the intended pulse source, two resistors, and one
capacitor. The comparator netlist contains a 20 fF initialized capacitor and
a 100 uS regenerative VCCS; its negative gm sign follows the analogLib output
terminal convention. The curated local test deck uses the equivalent reversed
output terminal order with positive gm.

Generated grids, plots, decks, PSF waveforms, comparisons, readbacks, and
exported netlists remain under ignored `output/module_first_order/`.

## Handoff to transistor design

This layer now provides the constraints needed to begin real schematics:

1. Choose the sampling/CDAC switch topology and partition Rsource, Rref, and
   Ron budgets.
2. Sweep MOS W/L for Ron, nonlinear settling, charge injection, and PVT.
3. Build the StrongARM schematic and measure actual gm_eff, Cnode, decision
   time, kickback, noise, and offset.
4. Iterate the CDAC unit size and timing partition with those measured values.

No production W, L, capacitor, reference buffer, or comparator size is frozen
by this report.
