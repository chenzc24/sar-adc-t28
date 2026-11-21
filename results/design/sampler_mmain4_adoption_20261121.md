# Sampler main-switch adoption

On 2026-11-21 the user adopted a four-finger main switch for the Bootstrap sampler. [`bootstrap.scs`](../../design/xtor/bootstrap/bootstrap.scs) now has four parallel 1 µm/150 nm `nch_18_mac` devices (Mmain, Mmain_U1–U3) instead of two. Every other device and the 200-unit MOM capacitor are unchanged. [Record with file digests and run identities](sampler_mmain4_adoption_20261121.json)

## Why

With the extracted two-finger Bootstrap inside the ADC at SS 0.81 V −40 °C, 7 of 10 frames exceeded the 0.25 LSB sampling-residual screen, and frames 3 and 9 decoded 3 and 5 codes low. Removing the extracted well-proximity terms still left 1.52 LSB, so the switch, not the layout, was the limit.

## Sizing

| Main switch | SS-cold schematic error | Settling τ | FF-cold schematic error |
| --- | ---: | ---: | ---: |
| 2 × 1 µm | −0.73 mV | 4.6 ns | −1.36 mV |
| **4 × 1 µm** | −1.41 mV | 2.3 ns | −2.83 mV |
| 6 × 1 µm | −2.09 mV | 1.6 ns | **−4.36 mV, fails** |

The standalone limit is 3.52 mV. 4 µm halves τ, enough to absorb the roughly 2× slowdown the layout adds. 6 µm fails the FF-cold charge-injection screen.

## Verification

The layout is `SAR_ADC_T28_LAYOUT/sar_bootstrap_flat_8b_p_core/layout` (`boot-core-20261121`), 24.52 × 24.99 µm. LVS is correct and DRC shows the same six known markers. Its geometry is identical to the candidate build `layout_mmain4` (`boot-mmain4-20261121a`) used for the runs below.

| Run | Condition | Result |
| --- | --- | --- |
| `boot-m4-ext-ssc-20261121` | Standalone extracted, SS cold | −1.12 mV, τ 4.4 ns (two-finger core: −2.26 mV, τ 8.7 ns) |
| `boot-m4-ext-ffc-20261121` | Standalone extracted, FF cold | −3.16 mV, 0.36 mV margin |
| `boot-core-tt-20261121` | Standalone extracted, TT, published view | −2.51 mV (two-finger core: −1.25 mV) |
| `boot-core-ssh-20261121` | Standalone extracted, SS hot | −2.03 mV; hold drift 27 µV |
| `boot-core-ffh-20261121` | Standalone extracted, FF hot | −3.39 mV, 0.13 mV margin (tightest corner) |
| `int-m4-ssc-20261121` | ADC, extracted CDAC and Bootstrap, SS cold | All codes match the control; worst residual **0.050 LSB** (control 0.067, two-finger 4.83) |
| `int-m4-tt-20261121` | Same, TT | All codes match; worst residual 0.006 LSB |
| `int-m4-ffc-20261121` | Same, FF cold | All codes match TT; worst residual 0.015 LSB |

Codes 12→7 and 243→248 are the CDAC's 4.2% gain error and appear in the schematic-Bootstrap control as well.

At FF the single-ended injection is about 0.5 LSB, while the ADC's differential residual is 0.015 LSB, so most of it cancels. The residual is taken at sample close, and the code-centre inputs would not flip on an offset below about half an LSB. Hot leakage is small: the hold drift is largest at SS cold (about 0.1 LSB), not at 125 °C.

## Open

SS cold with the CWORST_T CDAC, the restart case, a code-boundary measurement of differential injection, terminal-voltage stress, mismatch, noise, and top-level fill and routing.
