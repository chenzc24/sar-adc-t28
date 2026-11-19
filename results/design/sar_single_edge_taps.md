# QUIET tap calibration with cell LPE and the extracted CDAC

The selected chain uses **8 DEL250 stages for bits 7–5 and 6 for bits 4–0**. The 510-terminal settling minimum on the four fast-cold input histories was 7/4. Applying one guard stage to both gave 8/5, where a second issue appeared at the tap mux. Advancing the low tap by one further stage cleared the extra delivered-phase crossings on the verification frames. [Single-edge schematic verification](sar_single_edge_frontend.md) · [Per-comparison measurements and source digests](sar_single_edge_taps.json)

## Fast-cold boundary

At −40 °C and 0.99 V, each trial uses the CBEST_T standard-cell LPE library. The four scan frames drive 255, 0, 85 and 170. At each interpolated comparator clock rising edge, the analyzer checks both reference-gate words against the expected trial and sums the absolute errors of all 510 individual MOM bottom terminals relative to their commanded rails. The sum is divided by 256 and by 7.03125 mV per LSB. The limit is 0.25 LSB. Rows below report maxima for both measured polarities of the delayed phase. “Rise” and “fall” refer to DELIVERED, while every comparator aperture uses CMP_CLK rising.

| High / low taps | High rise (LSB) | High fall (LSB) | Low rise (LSB) | Low fall (LSB) | Phase and decision audit, frames |
| --- | ---: | ---: | ---: | ---: | ---: |
| 5 / 3 | 0.38930 | 0.63919 | 0.19993 | 0.34783 | 4/4 |
| 6 / 4 | 0.22415 | 0.35634 | 0.11391 | 0.19577 | 4/4 |
| 6 / 5 | 0.22415 | 0.35634 | 0.06544 | 0.11066 | 4/4 |
| 7 / 3 | 0.12916 | 0.19793 | 0.08134 | 0.34487 | 2/4 |
| 7 / 4 | 0.12916 | 0.19792 | 0.11390 | 0.19515 | 3/4 |
| 7 / 5 | 0.12916 | 0.19793 | 0.06544 | 0.11043 | 4/4 |
| 7 / 6 | 0.12916 | 0.19792 | 0.03740 | 0.06243 | 4/4 |
| 8 / 5 | 0.07444 | 0.11049 | 0.06544 | 0.11025 | 3/4 |
| 8 / 6 | 0.07444 | 0.11049 | 0.03744 | 0.06238 | 4/4 |

The 7/3 setting also produced three delivered-phase crossings in the bit-3 interval on two frames. The recorded output words still matched the comparator decisions. Those intervals fail the one-transition check. The polarity columns classify measurements with one delivered crossing, and the unfiltered per-comparison records include every aperture.

At 7/4 the worst high- and low-group errors were 0.19792 and 0.19515 LSB. With the other group fixed, one fewer high stage gives 0.35634 LSB and one fewer low stage gives 0.34487 LSB. The phase and decision audit passed 3/4 frames at 7/4 and 4/4 at 7/5.

At 8/5 the bit-3 interval in the 255 → 0 frame had one phase launch and three 50% crossings at DELIVERED. The public D word still equaled the eight comparator decisions. Five-picosecond waveform strobes establish the observed threshold excursion but do not resolve its pulse width. The selected 8/6 pair provides one additional stage in each group relative to the clean 7/5 reference. Its chain contains the same eight physical delay cells as 8/5.

## Selected pair

The eight nominal input codes at each corner are 255, 255, 0, 128, 85, 170, 127 and 1. The first three bit trials take the high tap and the remaining five take the low tap. For each frame the test checks the launched and delivered phase polarity, all eight comparator decisions, the committed word and both public reads. It also checks register setup and hold, write-high width, reference preset and sample closing. The physical converter uses the independently measured CDAC gain for the nominal-code check.

| Measurement | FF cold / CBEST_T | SS cold / CWORST_T |
| --- | ---: | ---: |
| Ordered reconstructed frames | 8 | 8 |
| High tap, rise, max plate error (LSB) | 0.07502 | 0.00130 |
| High tap, rise, measured delay range (ns) | 1.431–1.431 | 3.894–3.894 |
| High tap, fall, max plate error (LSB) | 0.11113 | 0.00136 |
| High tap, fall, measured delay range (ns) | 1.463–1.464 | 3.878–3.878 |
| Low tap, rise, max plate error (LSB) | 0.03910 | 0.00188 |
| Low tap, rise, measured delay range (ns) | 1.076–1.077 | 2.930–2.930 |
| Low tap, fall, max plate error (LSB) | 0.08171 | 0.00185 |
| Low tap, fall, measured delay range (ns) | 1.100–1.101 | 2.915–2.915 |
| Minimum public D margin at 90 ns | 34.939 ns | 10.413 ns |
| Remaining after 3 ns reserved for wiring | 31.939 ns | 7.413 ns |
| Remaining after 5 ns reserved for wiring | 29.939 ns | 5.413 ns |
| Worst absolute TOP differential error at sample closing (LSB) | 0.01243 | 0.23196 |
| Worst preset bound at track opening (LSB) | 0.00015 | 0.00004 |
| Worst DFF setup / hold slack (ps) | 153.1 / 36.5 | 412.2 / 91.2 |
| Minimum write-high / scalar requirement (ps) | 127.2 / 15.7 | 285.1 / 30.1 |

At SS cold the limiting frame is 4 (nominal input 85). The public read margin is 10.413 ns, or 21.3% of the interval from tracking close to the 90 ns read. The 5 ns wiring reserve leaves 5.413 ns. SAR inter-cell wires are ideal. Routing and full SAR extraction will determine the realized margin.

## Matched slow-cold physical gain

The earlier Q6/DEL200, SAMPLE/DEL200, IDLE29 cell-LPE controller used the same CWORST_T library, extracted CDAC, comparator, bootstrap and four initial stimulus histories. The minimum interval from the eighth SAR state update to the 90 ns read increased from **3.642 ns to 10.917 ns**, a gain of **7.275 ns** over the four matched frames. Individual gains were 7.275, 7.276, 7.281, 7.275 ns for codes 255, 255, 0 and 128. The eight-frame public-D measurement above additionally includes output propagation. [Earlier cell-LPE and CDAC evidence](../../Layout/results/sar_cdac_aperture_results_20261119.md)

On the same three inter-frame boundaries, the minimum PRESET-command lead before internal tracking increased from **2.931 ns to 24.530 ns**. Earlier conversion completion and removal of the 29-stage idle guard both contribute to this end-to-end measurement.

## Directed 63 → 64 transition

At FF cold the schematic-cell fixture read 63 on the nominal 64-center input. This additional pair of extracted-CDAC runs uses the same physical input voltages, switch histories and CBEST_T cells at 8/6 and 12/10. The first two voltages reproduce the original nominal stimulus. The second pair places the input at the physical 63 and 64 centers using the independent extracted-CDAC gain. Both output reads are checked, and the final two centers require an exact code.

| Input coordinate (nominal LSB) | Gain-adjusted expected code | 8/6 reads at 90/98 ns | 12/10 reads | Bit-6 TOPP−TOPN, 8/6 / 12/10 (mV) |
| ---: | ---: | ---: | ---: | ---: |
| 63.00000 | 60 | 60 / 60 | 60 / 60 | -24.831 / -22.332 |
| 64.00000 | 61 | 61 / 61 | 61 / 61 | -17.803 / -15.306 |
| 65.62170 | 63 | 63 / 63 | 63 / 63 | -6.407 / -3.919 |
| 66.58105 | 64 | 64 / 64 | 64 / 64 | +0.336 / +2.821 |

Both tap settings passed all four analog code checks. For the gain-corrected 64 center, the bit-6 differential at the 8/6 comparator aperture was +0.336 mV, about 0.048 nominal LSB. The longer 12/10 control measured +2.821 mV on the same history. The selected tap resolves this input correctly with a smaller input differential. The per-frame decision history, physical aperture bounds and phase crossings are included in the calibration data.

Both cold runs use the same stacked nominal-RC CDAC extraction from `sar-acq-q6-xrc-s10-ssc-20261119c`, with 255 switched unit terminals per side and the two fixed terminals excluded. The saved physical port names and extracted netlist inputs are bound to the native recipe by SHA-256. The two corners use their respective foundry cell LPE include. [Preparation](../../tools/saradc/single_edge_lpe.py) · [Waveform measurement](../../tools/saradc/measure/single_edge_lpe.py)
