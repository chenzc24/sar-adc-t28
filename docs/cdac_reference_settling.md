# CDAC And Reference First-Order Envelope

## Purpose and scope

This stage converts the behavioral error allocations into the first reusable
module-level electrical constraints. It does not select a production unit
capacitor, switch topology, or reference buffer. It answers two narrower
questions for the ideal 5+5 split CDAC:

1. How much comparator-side capacitance is required by the allocated sampling
   noise?
2. For a candidate capacitance and settling window, how large may the combined
   reference and switch Thevenin resistance be?

The tracked inputs are in `config/cdac_reference_settling.yaml`. Generated
tables, plots, Spectre decks, waveforms, and summaries are intentionally kept
under ignored `output/cdac_reference_settling/`.

## Split-array load model

For the ideal 5+5 partition, each subarray contains 32 unit capacitors. The
ideal attenuation capacitor is

```text
Ca = 32/31 * Cu.
```

Viewed from the comparator-side top plate, its series combination with the
32-Cu LSB subarray is exactly one Cu. Before parasitics, the effective load on
one comparator side is therefore

```text
Cside = 32*Cu + series((32/31)*Cu, 32*Cu) = 33*Cu.
```

This is a linearized load equivalence, not the physical switching schematic.
Bottom-plate parasitics, bridge ratio error, routing, comparator input
capacitance, and switch junction capacitance must be added after topology and
layout candidates exist.

## Sampling-noise lower bound

The two sampled sides are treated as independent, which gives the conservative
differential estimate

```text
sigma_ktc,diff = sqrt(2*k*T/Cside).
```

At 300.15 K, the tracked `0.18 LSB = 0.316406 mV RMS` allocation requires

```text
Cside >= 82.787 fF
Cu >= 2.509 fF       (when Cside = 33*Cu and parasitic C = 0).
```

This is only a thermal-noise floor. Capacitor matching, DNL/INL, parasitic
ratio error, PVT, routing density, and layout symmetry can force a larger Cu.
The 2.5 fF scan point is just below the floor (`0.316956 mV RMS`), whereas
3 fF gives `0.289340 mV RMS`.

## Settling-resistance upper bound

The first-order switching path is represented by `Rref + Ron` driving Cside.
For a worst-case differential step of 1.8 V, the differential residual is

```text
Esettle = 1.8*exp(-tsettle/((Rref + Ron)*Cside)).
```

Requiring the residual to stay below `0.25 LSB = 0.439453 mV` gives

```text
Rref + Ron <= tsettle /
              (Cside*ln(1.8 V / 0.439453 mV)).
```

Selected points from the generated envelope are:

| Cu | Cside | Differential kT/C | Maximum Rref + Ron at 2 ns | at 3 ns | at 4 ns |
|---:|---:|---:|---:|---:|---:|
| 3.000 fF | 99.000 fF | 0.2893 mV RMS | 2.429 kΩ | 3.643 kΩ | 4.858 kΩ |
| 4.000 fF | 132.000 fF | 0.2506 mV RMS | 1.822 kΩ | 2.732 kΩ | 3.643 kΩ |
| 6.86047 fF | 226.396 fF | 0.1913 mV RMS | 1.062 kΩ | 1.593 kΩ | 2.124 kΩ |
| 35.6304 fF | 1175.803 fF | 0.0840 mV RMS | 0.204 kΩ | 0.307 kΩ | 0.409 kΩ |

The table exposes the main tradeoff: increasing Cu improves kT/C noise and
usually matching, but tightens the reference-buffer and switch-resistance
requirements. The 35.6304 fF characterization specimen is not an attractive
default merely because it is already characterized; at 3 ns it allows only
about 307 Ω total.

## Spectre correlation

The remote `SAR_ADC_T28/tb_cdac_ref_settling/schematic` is a netlistable
single-ended half-circuit with a 0.9 V pulse, RREF, RSW, and CDAC. The measured
single-ended residual is doubled for comparison with the differential formula.
It exists to preserve the equivalent circuit in Virtuoso, while the local
runner performs the parameter sweep.

Four representative Spectre 21.1 transients completed without errors or
warnings and matched the exponential result:

| Case | Cu | Rref + Ron | Analytical residual | Spectre residual | Result |
|---|---:|---:|---:|---:|---|
| characterized default, feasible | 6.86047 fF | 1.5 kΩ | 0.14918 LSB | 0.14938 LSB | pass |
| characterized default, slow | 6.86047 fF | 2.0 kΩ | 1.35784 LSB | 1.35929 LSB | settling fail |
| small capacitor | 2.000 fF | 1.5 kΩ | effectively zero | effectively zero | kT/C fail |
| characterized specimen | 35.6304 fF | 0.3 kΩ | 0.20735 LSB | 0.20762 LSB | pass |

The first feasible point is a test vector, not a frozen design. It passes if
3 ns of the 5 ns bit cycle is reserved for CDAC settling, but fails the 2 ns
envelope because 1.5 kΩ exceeds the corresponding 1.062 kΩ limit.

## What this stage does not prove

- RREF and Ron are constant linear resistances. A MOS switch has
  signal-, common-mode-, body-, temperature-, and corner-dependent Ron.
- The reference is memoryless. CDAC code trajectories, reference decoupling,
  package/route inductance, buffer recovery, and correlated switching current
  are absent.
- The `0.211 mV RMS` reference/switching noise allocation is not simulated as
  resistor thermal noise here; its bandwidth and physical sources require the
  selected reference and switch circuits.
- Charge injection, clock feedthrough, comparator kickback, incomplete reset,
  capacitor mismatch, and layout parasitics are absent.
- The 1.8 V differential step is a conservative scalar bound, not a complete
  code-dependent switching sequence.

## Design handoff

The next implementation loop should evaluate realizable Cu candidates for
matching and layout, choose a sampling/CDAC switching scheme, and translate the
remaining `Ron` budget into MOS width using PDK transient sweeps over signal
level, common mode, PVT, and extracted parasitics. In parallel, the chosen
RREF budget becomes the reference buffer's closed-loop output-impedance and
recovery target. Only after these measurements should Cu, switch W/L, or the
reference-buffer topology be frozen.
