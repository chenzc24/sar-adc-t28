# SAR and CDAC acquisition measurements

The routed DEL200 candidate meets the TOP closing-error and 90 ns read criteria at both cold extremes. At SS cold, the intended preset first reaches the bottom plates too late on the three consecutive-frame boundaries. The worst weighted error at the instant tracking begins is 25.23 LSB against the 0.25 LSB limit. Delay sweeps and long regressions are on hold for a frame-control review. The 40 ns external high time, 50 Ω input and reference sources, two transistor-level bootstraps and stacked CDAC extraction are common to the comparisons. [Measurements, thresholds and run identities](sar_cdac_aperture_results_20261119.json)

| SS at 0.81 V, −40 °C | First FF | Second FF | FF → 00 | 00 → 80 |
| --- | ---: | ---: | ---: | ---: |
| S10, routed SAR and CDAC, signed closing error (LSB) | −0.06421 | +0.00022 | +0.30984 | −0.69760 |
| S10, SAR cell LPE and extracted CDAC, signed closing error (LSB) | −0.06139 | +0.00148 | +0.29312 | −0.67338 |
| DEL200, SAR cell LPE and extracted CDAC, signed closing error (LSB) | −0.03043 | +0.00060 | +0.06962 | −0.23244 |
| DEL200, final QUIET cell changed to DEL200, same cell LPE and CDAC (LSB) | −0.03045 | +0.00057 | +0.06962 | −0.23244 |
| DEL200, routed SAR and CDAC, final QUIET cell DEL200 (LSB) | −0.03114 | +0.00004 | +0.07090 | −0.23399 |

### Dual-extracted four-frame result

| Measured over FF, FF, 00, 80 | SS cold / CWORST_T | FF cold / CBEST_T |
| --- | ---: | ---: |
| External rise to track opening | 0.724–0.731 ns | 0.291–0.294 ns |
| External fall to track closing | 0.230–0.231 ns | 0.106–0.107 ns |
| Effective tracking width | 39.499–39.507 ns | 39.812–39.816 ns |
| Max. absolute differential TOP error at closing | 0.23399 LSB | 0.03060 LSB |
| Preset lead at the three boundaries | 0.560–0.561 ns | 37.161–37.178 ns |
| Max. 510-terminal weighted error at opening | **25.22550 LSB** | 0.00112 LSB |
| Max. 510-terminal weighted error at comparison | 0.00101 LSB | **0.24928 LSB** |
| Ordered updates by 90 ns / minimum margin | 32/32 · 0.742 ns | 32/32 · 30.966 ns |
| Shortest QUIET request to qualified output | 3.000 ns | 1.116 ns |
| Minimum receiver setup / hold slack | 480 / 1,422 ps | 186 / 550 ps |

Both corners returned FF, FF, 00 and 80 at both read apertures. Every sample opening selected the intended negative and positive gate words, 0x7F and 0x80. At SS cold the opening bounds in frame order were 0.00087, 20.12447, 20.12224 and 25.22550 LSB. The largest individual bottom-terminal offset at any opening was 384 mV. All 32 decisions were valid at write in each corner, with no overlap of the sampling and comparison clocks. At FF cold the largest comparison-time bound occurred on bit 6 of the FF → 00 frame. [SS-cold waveforms and per-frame measurements](../../work/output/managed_execution/runs/sar-acq-xrc-q6d2s200-ssc-four-20261119a/collected/derived/result.json) · [FF-cold waveforms and per-frame measurements](../../work/output/managed_execution/runs/sar-acq-xrc-q6d2s200-ffc-four-20261119a/collected/derived/result.json)

Relative to the routed S10 control, the routed candidate opened 4.659–4.661 ns earlier and gained 4.637–4.639 ns of tracking. The physical geometries also differ in their final QUIET cell. The matched cell-LPE comparisons below isolate each change. [Closing tail and opening error by frame](sar_cdac_aperture_waveforms_20261119.png)

The routed S10 control opened 5.384–5.391 ns after the external rise and tracked for 34.862–34.869 ns. Its final frame read 127 at both 90 and 98 ns with an expected code of 128. The eighth update occurred 0.029 ns before the 90 ns read. The independent code tolerance is one count. The signed differential error is evaluated separately at the interpolated 50% falling crossing of SEQ_SAMPLE. [Routed control](../../work/output/managed_execution/runs/sar-acq-q6-xrc-s10-ssc-20261119c/collected/derived/result.json)

For each of the three repeated-frame boundaries in that routed control, the digital preset led opening by 5.220–5.222 ns. The 510 bottom terminals met the 0.25 LSB bound with the intended commands continuously for 3.684–3.770 ns before opening. No reference command crossed 50% during any of the four tracking windows. [Native preset and terminal timing](../../work/output/managed_execution/runs/sar-preset-audit-s10-xrc-ssc-v2-20261119a/collected/derived/result.json)

In the matched cell-LPE control, S10 opened in 5.183–5.192 ns and tracked for 35.012–35.021 ns. Replacing only the sample chain with the qualified DEL200 advanced opening by 4.5303–4.5305 ns and extended tracking by 4.5171–4.5173 ns across the four paired frames. The unchanged control and the candidate both used six DEL250 cells in QUIET. [Matched ten-cell control](../../work/output/managed_execution/runs/sar-acq-q6-lpe-s10-ssc-20261119c/collected/derived/result.json) · [Single-tap comparison](../../work/output/managed_execution/runs/sar-acq-q6-lpe-s200-ssc-20261119c/collected/derived/result.json)

With SAR cell LPE, DEL200 opened 0.652–0.661 ns after the external rise and closed 0.190 ns after the fall. The tracking width was 39.529–39.538 ns. On the worst frame TOPP was 0.01552 LSB below the positive input source and TOPN was 0.21692 LSB above the negative input source. All four output words were correct and stable at the two read apertures. All 32 updates occurred in order. The minimum read margin was 2.987 ns. [Four-frame DEL200 results](../../work/output/managed_execution/runs/sar-acq-q6-lpe-s200-ssc-20261119c/collected/derived/result.json) · [Per-side acquisition trace](../../work/output/managed_execution/runs/sar-acq-trace-q6-s200-ssc-20261119a/collected/derived/result.json)

At every tracking onset the negative and positive gate words selected 0x7F and 0x80 respectively. On the three frame boundaries with an observed preset edge, preset led sampling by at least 2.276 ns. Across the 510 switched MOM terminals, the largest nominal-unit weighted error was 0.02506 LSB at opening and 0.00173 LSB at comparison. Each bound uses the sum of absolute terminal errors relative to their commanded reference, divided by 256 and the nominal 7.03125 mV LSB. IDLE stays at 29 cells for the routed test. [Gate words, terminal errors and per-bit data](sar_cdac_aperture_results_20261119.json)

## Routed candidate

The prior routed SAR with a schematic CDAC established the QUIET choice. On the SS-cold six-word sequence the uniform six-cell chain missed 90 ns by 0.419 ns at code 0x55. With five DEL250 cells and a final DEL200, all six frames met the deadline with at least 0.268 ns to spare. Its minimum QUIET rise delay in the FF-cold three-frame test was 1.117 ns against a 1.03 ns limit. Both comparisons used the original S10 acquisition chain. [Timing controls and source identities](sar_cdac_aperture_results_20261119.json)

With SAMPLE fixed at DEL200 and IDLE at 29, replacing only the final QUIET cell improved the least 90 ns read margin from 2.987 ns to 3.642 ns across the four SS-cold cell-LPE frames. The worst closing residual was 0.23244 LSB in both runs. The mixed-QUIET version's largest opening and comparison bottom-plate bounds were 0.00349 and 0.00161 LSB. [Single-variable QUIET comparison](../../work/output/managed_execution/runs/sar-acq-q6f200-lpe-s200-i29-ssc-20261119d/collected/derived/result.json)

The selected private core is `SAR_PLACEMENT_WORK/sar8_sar_timing_core/layout_quiet_q6d2s200`. Saved OA shows one DEL200 on SAMPLE, its input qualifier, the outer AND and the two-inverter clock buffer. Both qualifier inputs connect directly to SAMPLE_MATCH. The final inverter drives SEQ_SAMPLE. RAW uses DEL200, WRITE uses DEL250 + DEL250 + DEL075, and the idle guard uses 29 DEL250 cells. The layout connectivity audit traced all 267 electrical nets. [Saved OA inventory](../../work/layout/sar-cdac-aperture/saved-sar-instances.json) · [Route audit](../../work/layout/sar-quiet-lpe/q6d2s200/sar-qlpe-q6d2s200-routed-20261119a/metal-audit.json)

The filled wrapper passed transistor LVS and has zero blocking DRC markers. Calibre reported one `DIODMY_L:WARNING` and one `IO_CONNECT_CORE_NET_VOLTAGE_IS_CORE:WARNING1`. The extracted power networks contain 6,603 VDD and 6,342 VSS resistors. The CWORST_T and CBEST_T extractions use the same filled stream and LVS reference. The CDAC uses its measured nominal-RC stacked stream in both cases. Inter-block routes and package parasitics are outside this measurement. [Physical manifest](../../work/layout/sar-quiet-lpe/q6d2s200/sar-qlpe-q6d2s200-fill-20261119a/manifest.json) · [Corner identities](sar_cdac_aperture_results_20261119.json)

To regenerate this candidate's placement seed and transistor-level LVS source, run `python -m Layout.design.sar_standard --quiet-stages 6 --quiet-final-ps 200 --sample-delay-ps 200` from the project root. [Placement and reference source generator](../design/sar_standard.py)

## Pulse rejection and re-arm

At FF cold and CBEST_T, the five isolated delay branches each rejected a 40 ps positive pulse with an inverter load. The qualified SAMPLE tap rose in 0.159 ns and reset in 0.008 ns. Each pair of requests produced two complete output pulses for all six tested low gaps from 0.15 through 4.8 ns. WRITE, QUIET and IDLE produced extra edges at low gaps of 0.15 and 0.30 ns. All three produced exactly two output pulses at each tested gap from 0.60 ns upward. The shortest request low in the earlier routed mixed-QUIET FF control with schematic CDAC was 0.919 ns. [Branch measurements](../../work/output/managed_execution/runs/sar-acq-q6d2s200-rearm-ffc-20261119a/collected/derived/result.json) · [Routed control timing](sar_cdac_aperture_results_20261119.json)

With both extracted blocks and both bootstraps connected, a 40.000 ps external pulse before the first frame produced zero SEQ_SAMPLE crossings. Its peak was 0.107% of VDD. A subsequent 40 ns request passed and each tested low gap from 0.15 to 4.8 ns produced two complete output pulses. The finer run had a maximum observed step of 1.9010 ps. The original 2 ps grid reached 2.0017 ps. [Loaded SAMPLE pulse and re-arm measurements](../../work/output/managed_execution/runs/sar-acq-xrc-q6d2s200-ffc-pulse-1p9-20261119a/collected/derived/result.json)

## Frame-control review

Further tap sweeps and long regressions are on hold for a frame-control review. The four-frame tests exercise the existing design. The following changes are proposed for a separate implementation.

The controller ORs the eight bit tokens to generate ACTIVE. The idle circuit derives PRESET from `SAMPLE_INT OR delayed(!ACTIVE)`. SAMPLE_MATCH comes from a buffered SAMPLE_INT path. It has no bottom-plate or preset-ready input. The reference macro ties its compatibility RST_DONE port to VSS. The qualified SEQ_SAMPLE clocks the bootstraps, while SAMPLE_INT separately drives the token and storage resets. A rejected pulse at the bootstrap input therefore establishes only one part of the short-request behavior. [Idle and reference logic](../../design/xtor/reference/minimal_msb_d2.scs) · [Controller and token storage](../../design/xtor/sar/reset_data_or_std_static.scs) · [Top-level connections](../../design/top/adc_top.scs)

1. Capture the last-token condition on the accepted eighth update, after the LSB write. Latch an internal conversion-complete state and use it to assert and hold the reference preset throughout the intervening idle and tracking time. Preserve D0–D7 through the 90 and 98 ns reads. Define the equivalent initialized state for the first sample after power-up.
2. Give sampling and cancellation one qualified request. Permit tracking when that request is still high and the preset has had sufficient time to settle after the actual reference command. Measure this allowance with the extracted reference switches, 50 Ω sources and all 510 terminal loads across the chosen corners. The external falling edge keeps a direct clear path to the bootstrap enable. If a valid request interrupts conversion, suppress pending writes, request preset and wait for readiness before opening. A rejected request must leave the active conversion intact.
3. Keep the eight-bit token sequence and receiving registers in the first structural comparison. Start the first comparison after sampling has closed, comparator precharge has completed and the trial reference has settled. Exercise the last-write/preset boundary, a slow comparator decision, an in-conversion 40 ps pulse and an accepted in-conversion sample. Use the same 40 ns window, 90 ns deadline and 0.25 LSB limits. [Interface and timing contract](../../docs/specification.md)
