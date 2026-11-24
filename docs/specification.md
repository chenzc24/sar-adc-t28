# SAR8 Design Specification

This page is generated from [specs/arch.json](../specs/arch.json). The current electrical implementation is `sar8_single_edge_bitwise_v1`. The behavioral models approximate the B algorithm and protocol. Use native measurements for the single-edge SAR timing and settling. [Adoption and qualification record](../results/design/sar_single_edge_adoption_20261120.json)

## Architecture and External Interface

- An 8-bit, 10 MS/s, fully differential asynchronous SAR with a flat binary CDAC. Each side connects 255 binary-weighted unit capacitors and one unit dummy to its top plate without a bridge capacitor.
- Top-level port order is `D0 D1 D2 D3 D4 D5 D6 D7 SAMPLE VDD! VINN VINP VREFN VREFP 0`.
- Digital outputs are D0..D7. SAMPLE high samples and resets the SAR. Its falling edge ends sampling and starts the autonomous eight-bit sequence. The interface has no external bit clock, BUSY, VALID, or EOC pin.
- The code changes bit by bit during conversion. Read it after conversion and before the next sample. Positive differential voltage is VINP−VINN.

| Item | Definition |
| --- | --- |
| Core supply | 0.9 V nominal, 0.81–0.99 V verification range |
| References | VREFN=0 V and VREFP=0.9 V, independent of the core supply |
| Input | 0.45 V nominal common mode, -0.9..0.9 V differential, 0..0.9 V single-ended. Full common-mode range is unqualified. |
| Quantization | 256 codes, LSB=7.03125000 mV. Ideal boundaries are −0.9+k·LSB. Use the upper code at equality. |
| Frame timing | 100 ns total, with 45 ns high for sampling and 55 ns low for conversion. Start with 60 ns low for precharge before normal cycling. |
| Actual stimulus | Delay=60 ns, rise/fall=100/100 ps, width=44.9 ns. The first falling-edge threshold crossing is at 105.05 ns. |
| Input source | Ideal source with 50 Ω series resistance per pin |
| Reference source | Ideal source with 50 Ω series resistance and 4 pF bypass per rail. The fixture drives the reference directly. |
| Output load | 5 fF per bit. The comparator outputs and clock use native MOM model loads in pre-layout simulation only. |

## Corners

| Condition | MOS corner | Temperature (°C) | VDD (V) |
| --- | --- | ---: | ---: |
| tt | TT | 27 | 0.9 |
| ssc | SS | -40 | 0.81 |
| ssh | SS | 125 | 0.81 |
| ffc | FF | -40 | 0.99 |
| ffh | FF | 125 | 0.99 |

Read the frozen case includes for actual MOS, MOM, and passive model sections. The MOS corner name identifies MOS conditions. [Test identities](../specs/tests.json)

## Current Transistor Implementation

- Bootstrap uses 4 parallel 1 µm/150 nm `nch_18_mac` main switches per channel and a native MOM capacitor with multi=200.
- The CDAC uses 18 `cfmom_2t` instances. The unit geometry is nr=8, lr=2 µm, w=s=50 nm, stm=1, and spm=3, with multi from 1 to 128. The N and P dummies connect to VREFN and VREFP, respectively. The prior low-frequency AC characterization of this unit geometry gave about 4.00407 fF per unit and 1.02504 pF per 256-unit side at its specified bias and frequency. The older 6.86047 fF comparison and the 512-independent-unit mismatch results apply to their original models.
- Reference switches use L=90 nm, NMOS W=150 nm, PMOS W=175 nm, and multi=3·2^bit.
- The 11-MOS StrongARM comparator uses input pairs of W=1 µm and L=30 nm, a tail width of 1 µm, and N/P regeneration widths of 500/500 nm.
- The digital path uses native standard cells. The SAR uses one COMMIT write edge, a precomputed next trial word and a DEL250 settling chain with registered per-bit taps. The analog and boosted circuits remain transistor-level. The reference word uses CODE, a shared PRESET, and true and complementary drive without reference-side storage.
- Native standard-cell masters are `AN2D1BWP12T30P140`, `BUFFD1BWP12T30P140`, `BUFFD2BWP12T30P140`, `CKBD1BWP12T30P140`, `DEL200D1BWP12T30P140`, `DEL250D1BWP12T30P140`, `DFCNQD1BWP12T30P140`, `INVD1BWP12T30P140`, `INVD2BWP12T30P140`, `LHCNDQD1BWP12T30P140`, `MUX2D1BWP12T30P140`, `ND2D1BWP12T30P140`, `OR2D1BWP12T30P140`, `TIEHBWP12T30P140`, `XOR2D1BWP12T30P140`.

## Timing Contract

Each frame requires eight comparisons and eight COMMIT writes. The first comparison follows sampling once the bootstrap gates are off; each later comparison waits for its per-bit DEL250 tap. Verify reference state from actual CODE and gate control, and verify settling as the signed TOP error of all 510 switched plates against the nominal rails: at most 0.25 LSB, with a 0.125 LSB target, at every comparison. A new sample cancels unfinished events. The 55 ns conversion allocation comes from the frame. The interface exposes no timeout pin. Frozen B and its behavioral model use their own contract of eight reference updates and 16 captures.
The TT behavioral intervals below are medians of native edges across ten historical B frames, measured with a 40 ns high phase. The low phase sets the conversion budget. The 20 ps output smoothing and arithmetic regularization are model settings. The compare-to-write interval covers the comparator and digital receive pipeline. The current external high phase is 45 ns, and internal gate waveforms determine the actual Bootstrap conduction window.

| Behavioral interval | Value (ns) |
| --- | ---: |
| `sample_buffer_s` | 0.034436181 |
| `seq_buffer_s` | 0.043999306 |
| `first_compare_s` | 2.640679072 |
| `compare_to_write_s` | 0.382557673 |
| `write_to_update_s` | 0.448310391 |
| `update_to_capture_s` | 0.040319091 |
| `capture_gap_s` | 1.018781827 |
| `capture_to_next_compare_s` | 1.758258883 |
| `comparator_tau_s` | 0.000000000 |
| `conversion_budget_s` | 60.000000000 |
| `transition_s` | 0.020000000 |

The model uses TT intervals. Use native per-bit closed-loop measurements for timing qualification, including SS, FF, and mismatch. The 0.75 ns comparator probe and the same-draw extended-hold comparison with a 0.25 LSB limit are module diagnostics. Use separate evidence for full-frame deadlines and device reliability.

## Performance Targets and Error Budget

Engineering targets are ENOB ≥7 bits (SNDR ≥43.9 dB) at −1 dBFS, monotonicity with no missing codes, absolute DNL and endpoint INL ≤1 LSB, and power ≤1 mW. Consult measured results for actual conditions and coverage. [Results](../results/README.md)

| Allocation | RMS (mV) |
| --- | ---: |
| Ideal quantization | 2.029747 |
| `sampling_noise_rms_lsb` | 1.265625 |
| `comparator_noise_rms_lsb` | 1.265625 |
| `reference_noise_rms_lsb` | 0.843750 |
| `unmodeled_distortion_rms_lsb` | 1.054688 |
| Jitter of 20 ps at 4.5 MHz | 0.320738 |

The allocated RSS is 3.041486 mV. It projects SNDR of 45.412833 dB and ENOB of 7.251301 bits. Use measured spectra for the noise of a physical run.
The CDAC settling allocation is 0.25 LSB (1.7578125 mV). Report fixed gain, offset, and delay separately from random-noise RSS.

### Full Scale and Gain Error

Nominal full scale is ±(VREFP−VREFN)=±0.9 V with ideal binary weights 2^i·LSB. Define k as the sum of measured effective bit weights divided by the sum of ideal weights. Actual full scale is ±0.9·k V. The code-domain gain error is GE=1/k−1, positive when codes exceed the ideal. Reference −1 dBFS to nominal full scale. Endpoint INL and DNL exclude offset and gain.

| Gain error | Limit |
| --- | ---: |
| TT | 6% |
| Any corner | 10% |
| Hard limit for an unclipped −1 dBFS sine | 12.2% |

At TT, allocate ≤4.7% to the CDAC including planned fill, ≤0.8% to top-level TOP routing and device layout, and 0.5% to margin. Measure the CDAC share from standalone bit weights for the same extracted view. Use gain-normalized extracted weights to check layout systematic linearity, with |DNL|≤0.25 LSB and endpoint |INL|≤0.25 LSB. Leave the rest of the budget for mismatch, noise, and the comparator.
Accept the measured gain against these limits. Digital gain correction of the 8-bit output would merge or drop codes. The 0.9 V core level already sets the upper reference.
For short ADC tests, compute the expected code as `clip(128+floor(Vin/(LSB·k)), 0, 255)`. Use k from an independent CDAC test of the same physical view, or k=1 for the schematic. The functional check allows ±1 code with `Layout/tools/analysis/gain_corrected_codes.py`. Evaluate gain, linearity, and dynamic performance against their own limits.

## Calibration, Statistics, and Open Items

- The current design is uncalibrated. Comparator extremes among 200 seeds describe the offsets observed in those samples. Calibration range, step size, and weight word length are open.
- The historical 0.25 LSB offset allocation is a provisional residual target after correction. The current comparator offset is reported as measured.
- The Monte Carlo specification defines the 200-seed module tests and the 50-seed closed-loop tests at each of SS cold and FF cold. Closed-loop local mismatch is enabled only in the comparator and CDAC. [Sampling scope](../specs/monte_carlo.json)
- The B version has one TT transient-noise seed. Bandwidth and statistical convergence are open, as are full-circuit local mismatch, PEX, full common-mode range, calibration range and accuracy, power integration convergence, and terminal-voltage reliability. [Noise comparison](../results/noise/comparison.json)
- Use the terminal-voltage rule for engineering acceptance. The FF-cold adoption-stage scan reported no violations. The subsequent Stage 6 fill5 post-layout scan found 16 VDS pairs over the duration limit. Reliability disposition remains open. [Terminal-voltage rule](../specs/soa_rule.yaml) · [Adoption record](../results/design/sar_single_edge_adoption_20261120.json) · [Post-layout measurements](../results/integration/stage6_ff_electrical_20261124.json)

## Behavioral Views and Cross-Checks

The Python and Verilog-A models share the specification and generated defaults. The default is noiseless. Both support effective bit weights, offset, finite settling, and a stalled comparator. [Python model](../design/behav/python/sar_adc.py) · [Verilog-A model](../design/behav/veriloga/sar_adc_b.va)
Compare deterministic cases individually. The models use different random streams and model noise according to their respective distributions. Use transistor-level models for physical startup charging, kickback, native PDK Monte Carlo, terminal voltages, and power.
See the model guide for view hierarchy, legacy review, and commands. [Behavioral model guide](../design/behav/README.md)
