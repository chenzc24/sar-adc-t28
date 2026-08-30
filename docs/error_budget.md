# System Error Budget

This is the stage-1 allocation for the default 10-bit, 10 MS/s fully
differential converter. The executable source values are in
`config/design_spec.yaml`; `scripts/analysis/run_behavioral_baseline.py`
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
