# Verification Results

At experiment closeout, archive compact data, figures, warnings, and run identities. The retention policy permits cleanup of eligible raw waveforms. Keep receipts and archive indexes under `results/storage/`. [Waveform Retention and Cleanup](../docs/waveform-retention.md)

On 2026-11-15, cleanup recovered 374.985 GiB of old waveforms on thu-song and retained the latest five-corner OR data. [Archive and deletion receipt](storage/20261115-song-waveform-cleanup.md)

The current single-edge SAR was adopted on 2026-11-20. With foundry cell LPE and the extracted CDAC it read every expected code at FF cold, SS cold and TT, with 7.59 ns of read margin at SS cold and at most 0.114 LSB of signed settling error. The FF-cold all-terminal scan had no rule violations. [Adoption report](design/sar_single_edge_adoption_20261120.md) · [Settling reference](design/sar_single_edge_settling_reference_20261120.md)

The designs removed after commit `c46d9d6` keep their results and source digests: the standard-delay [timing regression](design/sar_std_delay_20261119.md), the 8.5 µm RC [layout results](../Layout/results/sar_timing.md), the [routed standard-delay diagnosis](../Layout/results/sar_std_static_candidate_c_20261119.md), and the [reset-OR adoption](design/reset_data_or_adoption_20261115.json).

| Verification | Evidence |
| --- | --- |
| Current single-edge SAR adoption | [Report](design/sar_single_edge_adoption_20261120.md) · [Record](design/sar_single_edge_adoption_20261120.json) · [Bit-6 aperture of the earlier 8/6 and 9/6 taps](design/sar_bit6_reference_overlay.md) |
| Single-edge native SAR front end | [Registered 9/6 tap waveforms, bit-6 differential and 90 ns read margin](design/sar_registered_9_6.md) · [Earlier 8/6 timing gains, five PVT points, six mismatch draws and sampling restart](design/sar_single_edge_frontend.md) |
| TT full-code test, 255 transitions and 256 code centers | [Static results](static/results.json) |
| TT 1024-point FFT and ADCtoolbox | [FFT results](fft/results.json), [A/B spectra](fft/ab_spectrum.png), and [B's 12-plot panel](fft/b_toolbox_panel.png) |
| 17.13 µm reset-OR design, continuous 1024-point noisy FFT | SNR 48.576 dB, SNDR 48.554 dB, ENOB 7.773 bits, and SFDR 65.495 dBc. All 1032 frame protocols passed. The test uses one noise seed and retains terminal-voltage and LTE warnings and convergence limits. [Final results and spectrum](noise/resetor_1024_20261116/README.md) |
| 17.13 µm reset-OR design, full-circuit global-plus-local Monte Carlo | 36/36 seeds collected. All 360 frames and 2880 bit comparisons passed timing and settling screens. See the report for code shifts and measurement scope. [Final MC results](mc/resetor_global_local_36/README.md) |
| 17.13 µm reset-OR design, selective-mismatch boundary supplement | 14/16 cases collected. All 476 frames and 3808 bit comparisons passed the diagnostic. Nominal C/D are outside the completed coverage due to the budget. See the report for shifts and warnings. [Boundary results](mc/selective_boundary_results_20261116/README.md) |
| B, single-seed TT transient noise | Bandwidth and statistical convergence are open. [Noise comparison](noise/comparison.json) |
| Additional 40 PVT corners for OR | 400/400 additional frames passed within the tested scope. [45-point results](pvt/resetor_45_short_20261115.md) · [Queue record](pvt/resetor_40_launch_20261115.md) |
| Standalone modules and mixed hierarchy | [Six module tests, mixed views, and SAR stall/restart](blocks/README.md) |
| Verilog-A and Python behavioral models | [Behavioral cross-checks and scope](behav/README.md) |
| A/B key codes at five corners | [PVT results](pvt/results.json) |
| Per-device terminal voltage for the minimal-reference candidate | TT and both SS corners passed within scope. FF cold and hot had duration violations. [Rule verdict and time-step review](soa/minimal_reference_five_corner_20261115.md) |
| Comparator gate-to-drain over-limit diagnosis | The D2 candidate passed the comparator screen at five corners. The FF-cold SAR storage violation remained at that checkpoint. The user adopted D2. [Input top-plate undershoot](soa/comparator_input_undershoot_20261115.md) · [D2 trial](soa/msb_drive_d2_trial_20261115.md) |
| FF-cold SAR standard DFF internal violation | Moving the D falling edge outside the clear interval reduced over-limit duration from about 132 to 25 ps without modifying the library. [Reset feedback and MM64 source undershoot](soa/dff_reset_feedback_20261115.md) · [Peripheral timing control](soa/dff_periphery_order_20261115.md) |
| Native OR at the data DFF input | At FF cold, 18/18 frames passed function and timing, violations fell from 8 to 0, and worst cumulative duration fell from 131.527 to 52.515 ps. The user adopted the design. Other corners are included in the 45-point results above. [Native OR closed-loop test](soa/dff_reset_or_ffc_20261115.md) |
| 200 seeds each for comparator and CDAC | [Module results](mc/modules_200.json) · [Reuse audit and supplementary scope](mc/modules_200_reuse_audit_20261116.md) |
| Closed-loop cold-corner snapshots | [Progress](mc/cold_progress.json) · [Checkpoint](mc/checkpoint_snapshot.json) |
| Directory migration TT short test | [Run state and original warnings](migration/native_short.json) · [Migration receipt](migration/restructure.json) |

B's deterministic TT dynamic results were SNDR 48.788 dB, SFDR 64.768 dBc, ENOB 7.812 bits, and SNR 48.806 dB with transient noise, mismatch, and PEX disabled. Estimated power was 86.53 µW excluding external input and clock sources. The integration grid convergence is open.

The historical 200-seed comparator offset standard deviation was about 14.188 mV. Standalone CDAC weights predicted a maximum absolute DNL of 0.1617 LSB and endpoint INL of 0.0848 LSB. Use the corresponding full-circuit evidence for yield or timing conclusions. Historical cold-corner closed-loop local mismatch covered only the comparator and CDAC. The 2026-11-15 OR batch applied global and full-DUT local variation.

Use `python -m tools.saradc observe cold`, `observe refs`, and `checkpoint` for live progress. The JSON results are timestamped snapshots and retain warnings and open items.

The `sar8-tree-tt-short-v1` migration run matched the original B codes and event counts for all ten frames. The maximum difference in the three sampled close edges and conversion times was 0 ps. The first analysis failed because four internal Bootstrap nodes were missing. Independent read-only analysis of the same source completed the function and timing comparison. Precharge voltages at those four nodes remain unmeasured and the original terminal-voltage warnings are retained. [Frame comparison](migration/comparison.json) · [Run and analysis failure](migration/native_short.json) · [Original warnings](migration/native_warnings.txt)

For SS 5115, use the original q45 reference failure and q38 correction receipts. [Reference receipts](mc/reference_5115.json)
