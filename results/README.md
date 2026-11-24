# ADC verification results

## Current review

| Test object | Coverage | Recorded outcome |
| --- | --- | --- |
| Stage 6 fill5 core | Extracted wiring with the Stage 1 package and reference model. Verify, extreme, carry and restart stimuli at TT, SS cold and FF hot. | All 12 short runs passed. The SS-cold verify run had 8.73 ns of read margin and 0.0991 V at the Bootstrap gate screen against a 0.1 V limit. [Stage 6 record](../Layout/results/current.json) · [Corner results](https://github.com/chenzc24/sar-adc-t28/issues/12#issuecomment-7093047607) |
| Chip periphery | Separate VIN-path comparisons at SS cold and TT, and an output-register/pad comparison at FF hot. | Output codes matched the corresponding core controls. The chip-fill report records the subsequent VIN/VREF route capacitances. [Peripheral evidence](../Layout/results/chip_objects.md) · [Fill7 route extraction](../Layout/results/chip_fill.md#extraction-of-the-chip-routes) |
| Stage 6 TT FFT and reliability | The final spectrum, FF terminal-voltage disposition and Bootstrap FF-hot injection recheck are tracked at system level. | Final Stage 6 dynamic metrics are pending. [Open verification items](https://github.com/chenzc24/sar-adc-t28/issues/12) |

Chip DRC, ERC, LVS and pad acceptance have separate review records. [Physical verification](../Layout/README.md) · [Pad and package review](https://github.com/chenzc24/sar-adc-t28/issues/18)

## Earlier measurements and archive records

| Version or fixture | Evidence |
| --- | --- |
| Single-edge SAR adoption, 2026-11-20 | Cell LPE and extracted CDAC. [Adoption report](design/sar_single_edge_adoption_20261120.md) · [Settling reference](design/sar_single_edge_settling_reference_20261120.md) |
| Integration before final Stage 6 | [Stage 2 with ideal top-level wiring](integration/stage2_all_extracted_20261122.md) · [Bootstrap revision 2](integration/bootstrap_rev2_20261122.md) · [Early unfilled routed-core runs](integration/stage6_early_20261123.md) |
| Frozen B and the A/B comparison | [Full-code static results](static/results.json) · [A/B deterministic FFT](fft/results.json) · [B standalone 30-seed mismatch samples](mc/frozen_b_blocks_30/samples.csv) · [Complete 30-seed experiment](https://github.com/chenzc24/sar-adc-t28/blob/7477de9ba5db4008d1c6d5fbf5ce132538c1aaba/verification/sar8_mc/blocks/REVIEW.md) |
| Reset-OR and earlier driver candidates | [45-point short PVT](pvt/resetor_45_short_20261115.md) · [Noisy TT FFT](noise/resetor_1024_20261116/README.md) · [Full-circuit mismatch](mc/resetor_global_local_36/README.md) · [Five-corner terminal voltages](soa/minimal_reference_five_corner_20261115.md) |
| Block, behavioral and comparator studies | [Module tests](blocks/README.md) · [Behavioral comparisons](behav/README.md) · [200-seed reuse audit](mc/modules_200_reuse_audit_20261116.md) · [Early StrongARM sizing screen](https://github.com/chenzc24/sar-adc-t28/blob/bc6f75c45fa57ba7ceddb83d6f7dffc81f530692/docs/strongarm_input_pair_scaling.md) |

The revision history maps earlier spectra and measurements to their DUT, layout and run family. Cleanup receipts record which raw files were released and which evidence was retained. [Revision history](../docs/adc-iteration-history.md) · [Historical source identity](provenance.json) · [Retention policy](../docs/waveform-retention.md) · [Storage receipts](storage/)
