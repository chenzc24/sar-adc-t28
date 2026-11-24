# Historical CDAC gate driver (minimal_msb_d2)

This 2026-11-19 report covers the earlier reference driver. The r8 design uses the single-edge D2 XREF. [Current XREF layout](single_edge_xref.md)

The saved eight-bit driver is `SAR_ADC_T28_LAYOUT / sar8_cdac_gate_driver / layout_gate_drive`. The integrated view is `SAR_ADC_T28_LAYOUT / sar8_cdac_with_xref / layout_gate_drive`. It references the saved CDAC `sar8j_r1_cdac / layout_paired_stacked`, including its planned fill instance. The recursive CDAC stream geometry digest is identical to the standalone source stream. Physical evidence is `xref-full-20261119-a`.

The 36 cells implement the `minimal_msb_d2` reference used in that run. The final inverters line up with their two gate landings on each side. Sixteen M6 routes split locally to reach all 32 CDAC gate terminals. Shared logic and the two continuous supply rails run below the CDAC. The ground trunk lands on an existing CDAC via pair. The OA driver bounding box including pin shapes is **63.494 × 10.425 µm**, and the combined bounding box is **72.230 × 68.315 µm**. [Native route drawing](figures/reference_driver_routes.png) · [Driver source](https://github.com/chenzc24/sar-adc-t28/blob/94e6394a7a9591107f54cebf37ae395485e07e05/design/xtor/reference/minimal_msb_d2.scs) · [Archived layout generator](https://github.com/chenzc24/sar-adc-t28/blob/94e6394a7a9591107f54cebf37ae395485e07e05/Layout/design/reference_driver.py)

| Geometry | B7 pilot | Eight-bit integration |
| --- | ---: | ---: |
| Native XREF bounding box | 40.954 × 4.925 µm | 63.494 × 10.425 µm |
| Active standard cells | 7 | 36 |
| XREF signal route centerlines | 108.225 µm | 869.02 µm |
| XREF-to-CDAC gate wire with each shared stem counted once | 26.38 µm | 212.64 µm |
| XREF output to one CDAC gate pin | 8.62 µm | 8.62–8.94 µm |
| LVS ports and nets | 36 and 60 | 15 and 75 |
| xRC extraction and format errors | 0 | 0 |

The pilot is saved as `layout_b7` in both cells. B0–B6 are available at their original gate ports in the pilot. For B7, twelve extracted MOS gate contacts were chosen from physical extremes. With the D2 output contacts clamped for the interconnect calculation, the N and P side corresponding resistances differ by approximately 0.048 Ω. The passive RC first moments are 6.00–6.22 ps with neighboring nets stationary. These probe sites include the CDAC gate distribution and contact network.

Calibre LVS matched the independent transistor reference on both builds. The pilot has nine density and context markers and two deck advisories. The eight-bit view has seven density markers and two advisories. The density rules are `OD.DN.3`, `PO.DN.3`, `PO.DN.3.1`, `M5.DN.1`, `M6.DN.1`, `M7.DN.1`, and `Mx.DN.7:M5_M6_M7`. The integrated view retains planned CDAC fill and the reference driver's functional row fillers and taps. Utility density fill closes with the ADC surroundings. The original Calibre logs retain 38 extraction warnings and five formatter warnings. [Fill policy](../specs/fill-policy.md)

## Native Transient Tests

In the B7 pilot at TT, preset and both code edges passed. The measured gate crossing delays span **228–263 ps** against the 50% CODE crossing. The sampled weighted bottom error entered the 0.25 LSB band after **1.213 ns** and **0.767 ns**. The 2 ns residuals were **0.0212 LSB** and **0.00124 LSB**. The measured differential TOP steps were −0.85872 V and +0.85872 V. Run `xref-b7-post-tt-wait-20261119` uses the pilot coupled extraction, 0.9 V, 27 °C, and the project's 50 Ω and 4 pF reference fixture.

The B7 schematic-driver control measured worst gate crossing delays of **188 ps** in each direction. Its settling times were **1.129 ns** and **0.642 ns**. With the integrated driver, the increase was about **54 ps** and **75 ps** at the latest measured gate, and about **0.084 ns** and **0.125 ns** at the sampled bottom plates. Both runs use the same CDAC geometry. The pilot extracts the distributed supply rails along with XREF. Control run `xref-b7-control-tt-lean-20261119` uses the standard CDAC-only extraction.

All eight bits were switched simultaneously in each direction on the coupled integration with distributed VDD and VSS. The table records the worse of the two transitions. The typical metal RC network is shared across these device corners. All three runs passed the preset, gate transition, and finite-hold bottom-plate checks. [Machine-readable results](reference_driver.json)

| Corner | Time to 0.25 LSB | Residual at 2 ns | Reference feed peak | Supply feed peak | Absolute differential TOP step |
| --- | ---: | ---: | ---: | ---: | ---: |
| TT, 0.90 V, 27 °C | 1.006 ns | 0.00478 LSB | 1.263 mA | 1.685 mA | 1.7118 V |
| SS, 0.81 V, −40 °C | 1.170 ns | 0.00849 LSB | 0.975 mA | 1.033 mA | 1.7115 V |
| FF, 0.99 V, −40 °C | 0.897 ns | 0.00306 LSB | 1.335 mA | 2.484 mA | 1.7115 V |

The integrated ADC fixture substitutes the coupled XREF and CDAC extraction for both schematic blocks. Its comparison uses the same CDAC geometry, the same default supply extraction treatment, and schematic XREF. Physical run `xref-full-20261119-matched` re-extracts the original integration GDS for this comparison. The monitors select actual switch gate and MOM contacts by side, device type, geometry and bit size. At each comparator edge the weighted bottom check uses the worst selected contact for each bit. The four TT stimulus centers are 12, 127, 128, and 243. [Native fixture](../tools/simulation/prepare_reference_driver.py)

| TT driver | Read codes at the four stimulus centers | Maximum decision plate residual | Maximum sample-close residual | Minimum time from eighth update to the 90 ns read |
| --- | --- | ---: | ---: | ---: |
| Schematic XREF with extracted CDAC | 7, 127, 128, 248 | 0.0790 LSB | 0.00948 LSB | 28.615 ns |
| Coupled XREF and CDAC extraction | 6, 127, 128, 249 | 0.1088 LSB | 0.01143 LSB | 28.482 ns |

Both cases passed all four sampling and handshake checks, the sampled 0.25 LSB bottom-plate screen, and the independent code observer. The two endpoint-adjacent tests gained one additional code of error with extracted XREF. Each TT comparison used native Spectre X MX, relative tolerance `1e-4`, and 10 ps saved data. The tighter `1e-6` control produced the same four codes. The tighter extracted case also produced code 6 in the first frame. The integrated tests use the project ADC schematics for the surrounding stages and cover these four deterministic TT cases. [Final measured results](reference_driver.json) · [Evidence archive index](../../results/storage/reference_driver_20261119.json)
