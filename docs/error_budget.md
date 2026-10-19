# System Error Budget

## Active 8-bit allocation (2026-10-19)

At the unchanged 1.8 V differential span, LSB=7.03125 mV and
0.25 LSB=1.7578125 mV. The provisional ENOB >=7 target corresponds to
SNDR >=43.9 dB. With the unchanged -1 dBFS sine, total permitted RMS error
is 3.620158 mV. The target is an engineering choice, not a process guarantee.

| Contribution | RMS (mV) | Basis |
| --- | ---: | --- |
| Quantization | 2.029747 | LSB/sqrt(12) |
| Sampling noise | 1.265625 | 0.18 LSB allocation |
| Comparator noise | 1.265625 | 0.18 LSB allocation |
| Reference/switching noise | 0.843750 | 0.12 LSB allocation |
| Clock jitter | 0.320738 | 20 ps at 4.5 MHz, unchanged absolute value |
| Distortion/unmodeled | 1.054688 | 0.15 LSB guard band |

RSS=3.041486 mV, projected SNDR=45.412833 dB and ENOB=7.251301.
This is top-down allocation. The three explicit Gaussian noise sources in
the clocked VA simulation give 45.882836 dB / 7.329375 ENOB; jitter and
unmodeled distortion are **not injected** in that experiment. Constant offset
and settling must separately stay below 1.7578125 mV; they are not quietly
converted into random noise or double-counted.

The flat-array comparison capacitance gives differential sqrt(2kT/C)=
0.068696 mV at 27 C, excluding switch excess noise and bandwidth effects.
At 3 ns and a worst-case 1.8 V step, Rtotal must be <=246.435 ohm for
0.25 LSB first-order settling. New macro allocations are Rbottom=150 ohm,
Rref=50 ohm, Cref=4 pF. These differ from historical split-array settings
and are not measured reference-buffer specifications. Full macro transients,
not a single RC fit, determine the actual eight decisions.

Executable sources: `config/design_spec.yaml`, `config/eight_bit_flat.yaml`,
`scripts/analysis/run_behavioral_baseline.py`, `scripts/eight_bit/analyze.py`.
The [migration report](eight_bit_flat_migration.md) separates physical
measurements from allocations.

## Preserved 10-bit allocation

This is the stage-1 allocation for the default 10-bit, 10 MS/s fully
differential converter. The executable source values are in
`config/design_spec_10b.yaml`; `scripts/analysis/run_behavioral_baseline.py`
derives the numbers below.

## Derived limits

- Differential input span: 1.8 V
- LSB: 1.7578125 mV
- Dynamic test level: -1 dBFS
- Test-sine peak and RMS: 0.802126 V and 0.567189 V
- Minimum ENOB: 9.0 bit
- Equivalent minimum SNDR: 55.94 dB
- Maximum total input-referred RMS error at the test level: 0.905164 mV,
  or 0.514938 LSB

## Initial allocation

| Contribution | RMS (LSB) | RMS (mV) | Interpretation |
| --- | ---: | ---: | --- |
| Ideal quantization | 0.288675 | 0.507437 | Fixed by 10-bit resolution |
| Sampling thermal noise | 0.180000 | 0.316406 | Acquisition network allocation |
| Comparator decision noise | 0.180000 | 0.316406 | Input-referred allocation |
| Reference/switching noise | 0.120000 | 0.210938 | Reference and switch allocation |
| Clock jitter at 4.5 MHz, 20 ps RMS | 0.182464 | 0.320738 | High-input-frequency allocation |
| Distortion and unmodeled effects | 0.150000 | 0.263672 | RMS-equivalent guard band |

Treating the contributions as uncorrelated gives 0.821345 mV RMS, or
0.467254 LSB. This projects to 56.784 dB SNDR and 9.140 bit ENOB, leaving
0.844 dB SNDR margin and 0.216413 LSB of residual RSS headroom.

The RSS budget is an architecture allocation, not proof that transistor-level
errors are independent. Harmonic distortion, reference memory, CDAC mismatch,
and kickback must later be measured directly and compared with the same total
SNDR gate.

## Deterministic guardrails

- Final CDAC settling error: at most 0.25 LSB before each decision.
- Comparator systematic offset: at most 0.25 LSB input-referred before any
  optional trim.
- Static linearity: no missing codes and absolute DNL/INL below 1 LSB.

Offset is kept separate from the RMS dynamic budget because removing the mean
from a sine record hides a constant offset. Settling and static nonlinearity
are also verified directly rather than counted twice as random noise.

## Behavioral reference result

The ideal model uses 16,384 samples, coherent bin 7373 at 10 MS/s
(4.500122 MHz), and a -1 dBFS differential sine. The current golden result is
60.953 dB SNDR and 9.833 bit ENOB. An 8-sample-per-code full ramp visits all
1024 codes with zero missing codes and zero ideal DNL/INL.
