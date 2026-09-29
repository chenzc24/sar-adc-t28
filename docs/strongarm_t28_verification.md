# T28 StrongARM first-pass verification screen

Date: 2026-09-29. Source: `SAR_ADC_T28/tb_sar_strongarm_t28/schematic`, exported read-only through Bridge 0.8.0. The 11-device T28 PDK StrongARM DUT subcircuit SHA-256 is `e7effa6aeeac3dd126bf9d3e062009f83138a63f01cc7779cf25a9070c2b6e82`, identical to the [first-pass baseline](strongarm_t28_first_pass.md). All modifications below are **analysis-deck wrappers**, not OA schematic changes. Simulator: remote Spectre 21.1, `t28_io` profile. Reproduce with `scripts/characterization/verify_strongarm_t28.py` and `config/strongarm_t28_verification.yaml`; ignored raw decks, logs, PSF, and JSON summaries are under `output/strongarm_t28_verification/`.

## Acceptance context

The top-down allocation is comparator random input-referred noise <0.316 mV RMS, systematic offset <0.439 mV, and decision within 1.5 ns. These are architectural starting budgets, not PDK specifications. The 0.439-mV **systematic** offset limit is reused here as a provisional *untrimmed local-mismatch bracket*; no separate mismatch yield target has yet been approved. The nominal bench uses VDD=0.9 V, 27 °C, TT, input common mode=0.45 V, 200-MHz clock, 20-ps edges, and 5-fF load per output. We test at differential inputs ±0.439453 mV (0.25 LSB). A resolved decision means signed `(OUTP−OUTN)` reaches at least 0.45 V by 1.5 ns after the clock crossing.

| Screen | Result | Classification |
| --- | --- | --- |
| Transient device noise, PDK `noise_worst` | At +0.439453 mV, 24/96 wrong; at −0.439453 mV, 27/96 wrong (51/192 pooled, 26.6%). Zero input: 48/48 positive/negative in 96 cycles. | **Fail** versus 0.316-mV allocation under the tested noise model. |
| Local mismatch, PDK `TTGlobalCorner_LocalMC_MOS_MOSCAP` | Same 32 random parameter samples paired at ±0.439453 mV: 5/32 inside the bracket, 27/32 outside (84.4%; Wilson 95% interval 68.2–93.1%). Positive test 22/32 correct; negative 15/32 correct. | **Fail** versus the provisional 0.439-mV untrimmed offset bracket. |
| Deterministic decision time | TT/0.9 V/27 °C/5 fF: 223 ps; TT/20 fF: 705 ps; SS/0.81 V/125 °C/20 fF: 1070 ps; FF/0.99 V/−40 °C/20 fF: 407 ps. Both input signs passed in all four cases. | Timing **pass** for these four points only. |
| FF high-voltage device stress | At 0.99 V, Spectre issued `CMI-2753/2755/2756` terminal-voltage limit warnings around the clock edge. | **Open reliability issue**; the FF timing pass is not an all-metrics pass. |
| Simplified held-input kickback | With 1-GΩ hold path and 219.535-fF input capacitor, peak differential kickback 0.169 mV; with 50 fF, 0.740 mV. Both signs resolved correctly. | 219.535 fF below provisional 0.439-mV guardrail; 50 fF **exceeds** it. Full CDAC/sampling integration untested. |

### Noise interpretation

Spectre transient noise used `noisefmin=1 kHz`, `noisefmax=10 GHz`, `maxstep=5 ps`, seed 271828, 96 reset/evaluate cycles per input. Separate smoke seeds changed the zero-input decision sequence, so the noise source was active. An independent +0.439-mV run with seed 271829 had 19/96 wrong; a 30-GHz bandwidth cross-check with seed 271828 had 28/96 wrong. Neither suggests that the main failure is just one lucky seed or a 10-GHz cutoff artifact; neither establishes bandwidth convergence or a final BER.

If the balanced near-threshold error probability is interpreted as a zero-offset Gaussian decision variable, `P(error)=Phi(-|Vin,diff|/sigma)`, the pooled 51/192 implies **effective** input-referred sigma ≈0.702 mV. A naive independent-Bernoulli Wilson calculation gives 20.8–33.2% for the pooled error probability and 0.541–1.013 mV for sigma, but the positive/negative runs used the same seed and repeated cycles need not be independent; these are **not** validated coverage intervals. The 0.316-mV target would predict ~8.2% wrong at this input under the same Gaussian assumptions. This is an inference from binary decisions, **not** a direct noise-spectrum integral or a proven Gaussian distribution. Noise and mismatch were simulated separately; no combined BER claim follows.

### Mismatch model correction and validity

The initial mismatch wrapper incorrectly reused `TTMacro_MOS_MOSCAP`. Spectre reported 66 random variables and 19 defined mismatch parameters, and 48 paired draws at ±0.439 mV appeared to pass. However, those output waveforms differed only at approximately `10^-12 V` numerical scale. The model's total-mode selector suppresses the local mismatch contribution there. **Those 48 draws are invalid and must not be used for yield claims.**

The corrected mismatch-only deck selects the foundry's `TTGlobalCorner_LocalMC_MOS_MOSCAP` section. It preserves the exact DUT subcircuit. A four-draw smoke run then had 73-mV early-output spread and 2/4 wrong at +0.439 mV; the full 32-draw run had ~0.38-V early-output spread. `savemismatchparams=yes` saved the sampled parameter set. Positive and negative 32-draw runs had identical sampled-parameter-file SHA-256 (`ebba37d5963969f0a99f09455af9f2f517b4c5f8148e6b92dae052c66d26d774`), establishing paired draws. This is a coarse offset **bracket**, not a measured offset histogram or a production yield estimate. The earlier 64-draw attempt under the incorrect section also suffered a Windows result-download error after Spectre completion; its output is not counted.

### Interface and PVT limits

The finite-input fixture is a capacitor to ground plus a 1-GΩ bias path. Its actual pre-edge differential input was ±0.438425 mV (within 0.24% of the requested value). An earlier 1-TΩ fixture failed this validity check because simulator `gmin` materially loaded the node; its results are retained as invalid evidence only. The reported kickback is the maximum transient differential disturbance during evaluate; a short spike above the provisional 0.439-mV guardrail does **not** directly equal conversion error. This fixture omits the actual split CDAC, sampling switch, reference network, and bottom-plate timing, so those must be connected before accepting an ADC-level kickback number.

The 5-to-20-fF output-load increase tripled TT decision time. The slow/hot/low-supply 20-fF point still left ~430 ps of the 1.5-ns window, but the four points are not a full independent P/V/T/load sweep. The FF/0.99-V run reached output polarity in time while violating reported PDK terminal-voltage limits by a small amount near the edge; inspect clock-waveform overshoot and use an allowed operating condition before treating this corner as valid. Evaluation-window supply energy ranged from ~5 fJ at nominal 5 fF to ~19 fJ at FF 20 fF; this excludes the full SAR interface and reset-cycle energy.

## Design implication and next verification

Do not freeze the current 1-µm input-pair / 0.5-µm latch-and-reset transistor sizing. First investigate the input pair's noise and local mismatch trade-off versus width, length, finger count, regeneration speed, and kickback; protect the 1.5-ns worst-case timing constraint. Check the permitted VDD/edge envelope. Then connect the real CDAC/sampling network and output logic load and rerun transient noise plus local mismatch (eventually combined), offset search, common-mode sensitivity, PVT, and post-layout checks. No layout, DRC/LVS/PEX, large-sample tail-yield, or ADC-level dynamic metrics were verified here.
