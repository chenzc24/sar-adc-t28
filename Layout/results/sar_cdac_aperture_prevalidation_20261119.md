# SAR sampling aperture and CDAC prevalidation

The four-frame measurements, selected sample tap and new routed SAR are recorded in the [acquisition results](sar_cdac_aperture_results_20261119.md). The values below describe the budget at fixture preparation.

The next controlled change advances the rising edge of the internal bootstrap enable. The external SAMPLE input stays high for 40 ns in a 100 ns period. The pin-read apertures remain at 90 and 98 ns on the existing frame time base. The physical candidate for the conversion loop starts with six DEL250 cells in QUIET. The four acquisition recipes passed local validation through the production registrar up to the network transport boundary. They have not been submitted. Electrical selection requires waveform results. [Source measurements, calculations and frozen package identities](sar_cdac_aperture_prevalidation_20261119.json)

## Measured timing budget

All propagation delays in this table start at the 50% crossing of the external SAMPLE rising edge. At a fixed 40 ns external window, tracking width is 40 ns plus the falling-edge latency minus the rising-edge latency.

| Source | Opening latency | Closing latency relative to the external fall | Internal tracking | Load and observation |
| --- | ---: | ---: | ---: | --- |
| Original failing frame, resetor_v1 | 2.356 ns | 0.132 ns | 37.776 ns | SS 0.81 V at −40 °C, nominal-RC stacked CDAC. The differential residual at the falling edge of SEQ_SAMPLE was −0.351494 LSB on the transition from code 0 to 128. |
| Q6, SAMPLE10, IDLE29 | 5.388–5.395 ns | 0.253 ns | 34.858–34.866 ns | SS cold and CWORST_T extracted SAR, including both supplies. The CDAC used its schematic. The three inputs were 0, 255 and 1. |

The last 4 ns of the failing waveform gave a 4.258 ns apparent time constant. Continuing that tail to 0.25 LSB would take another 1.451 ns. The decimated trace identifies approximately 37.746 ns of tracking, and interpolation of both edges gives 37.776 ns. The corresponding screening target is **about 39.2 ns**. Transferring that target to Q6 suggests a rising-edge latency of about **1.0 ns** and an advance of **4.3–4.4 ns**. Initial top-plate charge, switch turn-on and the extracted loads can change the tail. The measured sample-close residual selects the design. Failing waveform (local archive: `work/output/managed_execution/runs/cdac-sampling-trace-ssc-20261118/collected/derived/result.json`) · [Q6 routed results](sar_quiet_lpe_20261119.md)

## Sampling candidates

Replace the body of `sar8r_delay` in the private candidate. Retain `SAMPLE_MATCH`, input qualification, the outer AND and the final clock buffer driving both real bootstrap inputs. A falling request still clears the qualify gate directly. For the single-cell candidates, remeasure the falling edge, delivered slew, short-pulse rejection and re-arm behavior. The default transistor netlist and external interface remain at their published settings.

| Sampling branch | Basis | Estimated advance from Q6/SAMPLE10 | Estimated opening / tracking at SS cold |
| --- | --- | ---: | ---: |
| 10 × DEL250 | Routed Q6 control | 0 | 5.39 / 34.86 ns, measured |
| 7 × DEL250 | Rough proportional screen only | ~1.4–1.5 ns | ~3.9–4.0 / ~36.3 ns |
| 1 × DEL200 + qualifier | First candidate. The same one-cell topology already serves the valid detector. | ~4.38 ns | ~1.01 / ~39.24 ns |
| 1 × DEL075 + qualifier | Faster candidate if the DEL200 leaves residual and preset is already settled | ~4.65 ns | ~0.74 / ~39.51 ns |

The isolated SS-cold, typical-cell-RC measurement gave 4.823 ns for SAMPLE10 and 0.440 ns for DEL200 plus its qualifier. The estimated DEL075 path is 0.168 ns, using the measured single-cell DEL075 rise of 0.145 ns and the 0.024 ns difference between the qualified and standalone DEL200. The estimates subtract those changes from the actual Q6 opening time. Cell RC, local routing, switching current and output slew differ between fixtures. Measured cell delays (local archive: `work/output/managed_execution/runs/delcell-lpe-ssc-20261119a/collected/derived/result.json`)

## Conversion and preset branches

- Keep RAW (one DEL200) and WRITE (DEL250 + DEL250 + DEL075) for the controlled comparison. Keep QUIET at six DEL250 cells initially. In SS cold with CWORST_T this candidate had 0.589 ns of read margin in its first three frames. Evaluate the existing `00 FF 01 80 55 AA` transition screen. If uniform Q6 misses the deadline, compare the routed six-cell alternative with a final DEL200 and repeat the selected acquisition screen on that exact combination.
- Pure five-cell QUIET measured 0.956 ns from request to qualified output under FF cold / CBEST_T. The existing fast-corner minimum is 1.03 ns. RAW and WRITE still require valid data at the receiving register and passing setup and hold at its physical terminals. FF-cold native run (local archive: `work/output/managed_execution/runs/sar-qlpe-rc-q5-ffc-cbest-pilot-20261119a/collected/derived/result.json`)
- Run IDLE29 first. In the Q6 slow-cold pilot both boundaries used the direct SAMPLE_INT path to assert PRESET. Its minimum lead was 5.224 ns. Advancing sampling by 4.38 ns would leave roughly 0.84 ns at the same boundary. Measure actual bottom-plate voltages against their preset references at tracking onset. A digital PRESET edge alone cannot establish analog readiness.
- If early sampling runs into the reference transition, hold the sampling tap and QUIET constant and compare IDLE29 with IDLE18. Check first frame after a long idle, consecutive frames, and an interrupted conversion. The idle path may assert PRESET only after the last valid update in a completed conversion. Check every active-bit transition for premature preset and the next actual track opening for settled references. If the available safe lead is insufficient, revisit the sampler drive before changing the external timing contract.

## Frozen first-stage experiments

Use SS 0.81 V at −40 °C, real bootstrap circuits on both inputs, original reference-switch network, 50 Ω sources and the same `FF FF 00 80` four-frame history in every case. This reproduces the last four input levels in the reported failure. The full original ten-frame sequence is a follow-up on the selected candidate. The CDAC is the same merged, nominal-RC `layout_paired_stacked` extraction across this comparison, with GDS and netlist identities in each recipe. The slow-cell models use CWORST_T LPE. Prepared recipes and SHA-256 identities (local archive: `work/layout/sar-cdac-aperture/prepared.json`)

| Case | SAR timing representation | Purpose |
| --- | --- | --- |
| SAMPLE10 reference | Native Q6 SAR CWORST_T xRC with distributed VDD/VSS, plus extracted CDAC | Establish the dual-extraction failure or pass and the actual available aperture. If all screens pass, retain the control for the broader verification. |
| SAMPLE10 matched control | Q6 cell LPE plus extracted CDAC | Quantify the model difference at identical circuit parameters. |
| DEL200 sample candidate | Same Q6 cell LPE and extracted CDAC | Change only the sample-delay body against the matched control. Prefer this slower tap if it passes the full set of checks. |
| DEL075 sample candidate | Same Q6 cell LPE and extracted CDAC | Use when the DEL200 still misses acquisition and the preset is ready. |

Each package saves all **510 switched unit-MOM bottom terminals** (255 on each side), bound to the extracted groups containing 1, 2, 4, 8, 16, 32, 64 and 128 units. The local preflight verifies the two fixed-reference units and 168 grounded dummy units separately. The waveform measurement uses the sum of absolute unit-terminal errors divided by 256 and by the nominal LSB. At sampling onset the gate words must select the actual preset references. The 0.25 LSB check at that instant is a proposed diagnostic for advancing the clock and for deciding whether to evaluate IDLE18. At each comparison the measurement uses the selected reference on each side. The resulting bound uses the project's nominal binary unit weighting. The independent gain-adjusted word check uses the standalone extracted bit weights from the same CDAC view (`k = 0.959355` at SS cold).

Before a long regression, route the selected combination and repeat the short cases with its own transistor LVS, signal and supply xRC plus the same extracted CDAC. Check both extreme pairs, SS cold/CWORST_T and FF cold/CBEST_T. Mismatched candidate geometries or scalar time shifts cannot substitute for the selected GDS. A change in CDAC extraction or MOM corner also needs its own standalone gain. Top-level inter-block parasitics remain a separate integration measurement.

## Selection and release checks

1. At the actual SEQ_SAMPLE falling crossing, require absolute differential TOP-minus-input error ≤ 0.25 LSB. Record per-side error, bootstrap overdrive and both tracking edges. At track opening and at each comparison, require valid reference commands and the physical weighted bottom-plate error ≤ 0.25 LSB. Check for sampling/compare overlap, gate glitches and unintended pulses. Exercise 40 ps pulse rejection and minimum low/re-arm time at the fast corner.
2. Require eight ordered compare/write/update cycles by 90 ns. Compare both 90 and 98 ns reads to the independently gain-adjusted expected code within ±1 and check output stability. Require nonnegative register setup/hold slack, valid decisions at write, and at least 1.03 ns from QUIET request to qualified output at FF cold. Check full-scale reversal, `00 → 80`, `0C → 7F`, alternating `55/AA`, first frame after idle and first recovery frame after an interrupted conversion.
3. Expand only the surviving physical combination to the five corners × 18 frames, SS cold × 64 frames and the FF-cold/hot 2 ps device-terminal screens. Repeat the slow-decision and mid-conversion abort tests on that combination. The independent mismatch offset and whole-chip routing remain on their own measured scopes.
