# Single-Edge SAR Macro Layout

`SAR_ADC_T28_LAYOUT / sar8_se_core / layout_r3` is the layout of the current single-edge SAR. It holds the five top-level instances of the floorplan's SAR block: `XCTRL`, `XSEQ`, `XDONE`, `XPRESET` and `XSAMPLE`, 174 native standard cells. The 26 ports match the top-level connections. Calibre LVS is CORRECT and DRC reports only the two standard fixture advisories. [Record with hashes, run identities and measurements](sar_se_core.json)

![Placement and routing of layout_r3](figures/sar_se_core.png)

## Flow

1. `python -m Layout.design.sar_single_edge REV --rows N --utilization U` flattens the SAR group of `design/dut.scs` to native cells and writes the Innovus netlist and script under `work/layout/sar-se/REV/`.
2. `python -m Layout.tools.physical.sar_se_route REV` runs Innovus on thu-wei: rows with boundary and tap cells, pins on the left edge in M3, placement, M6 supply stripes, NanoRoute on M1–M4 and decap/fill cells. No timing library is loaded.
3. `python -m Layout.tools.physical.sar_se_def REV` converts the routed DEF into net-bound OA records and the transistor LVS reference. The rendered metal and cuts are compared with the Innovus routing stream on M1–M6 and VIA1–VIA5; any XOR difference stops the conversion.
4. Upload `build.txt` and `sar-se-leaves.cdl` to `state/sar-se-REV` and run `python -m Layout physical ID --module sar-se --staging sar-se-REV --view layout_rN --rebuild`. The view is created in `SAR_ADC_T28_LAYOUT`; an existing view or an edit lock stops the build. Later runs without `--rebuild` verify the saved view. Extraction runs an LVS comparison first, so the xRC netlist keeps the source net names.
5. `python -m Layout.tools.simulation.prepare_sar_se ID CORNER KIND --cdac nominal|cworst --revision REV` replaces the five instances in the `single_edge_lpe` deck with the extracted macro. Internal SAR probes are saved at the gate of a receiving cell and read back under their schematic names.

## Views

| View | Boundary (µm) | Rows | Physical cells | DRC | LVS | DEF to OA XOR |
| --- | --- | ---: | ---: | --- | --- | --- |
| `layout_r2` | 21.195 × 18.0 | 14 | 179 | 2 advisories | CORRECT | 0 on all 11 layers |
| **`layout_r3`** | **18.495 × 16.8** | 13 | 110 | 2 advisories | CORRECT | 0 on all 11 layers |

The OA bounding box is wider than the boundary because the standard-cell text extends past the cell outlines. `layout_r3` uses 13 % less area and is the selected view; it fits well inside the 41 × 56 µm reservation of the floorplan. Innovus `verifyGeometry` lists two (r2) and five (r3) M2 via-enclosure markers that the foundry Calibre DRC of the same geometry does not report.

## Post-layout ADC runs with layout_r3

The extracted macro replaces the SAR group. The CDAC is extracted, the reference word uses cell LPE, the comparator and bootstrap are schematic, and top-level wiring and supplies are ideal. `sar-se-r3-cw` re-extracts the same saved view with the foundry CWORST_T interconnect rules; the other runs use the deck's typical rules.

| Run | Condition | SAR macro RC | Codes | Read margin (pre-layout) | Settling | Setup / hold |
| --- | --- | --- | --- | --- | --- | --- |
| **`sar8-sepl-ssc-cw-verify-r3cw`** | SS, −40 °C, 0.81 V, CWORST_T CDAC | **CWORST_T** | 8/8 | **6.95 ns** (7.59) | 0.001 LSB | 443 / 100 ps |
| `sar8-sepl-ssc-cw-verify-r3a` | SS, −40 °C, 0.81 V, CWORST_T CDAC | typical | 8/8 | 7.60 ns (7.59) | 0.001 LSB | 433 / 97 ps |
| `sar8-sepl-ffc-cw-scan-r3a` | FF, −40 °C, 0.99 V, CWORST_T CDAC | typical | 4/4 | 30.23 ns (30.70) | 0.107 LSB | 169 / 39 ps |
| `sar8-sepl-tt-nom-verify-r3a` | TT, 27 °C, 0.9 V, nominal CDAC | typical | 8/8 | 24.42 ns (24.92) | 0.026 LSB | 246 / 57 ps |

The SS-cold run with the CWORST_T macro passes every check. Worst-case SAR wiring costs 0.65 ns of the 7.59 ns pre-layout margin, about 13 % of the 5 ns routing reserve; code 85 is the tightest frame. It also uses the four-finger Bootstrap adopted on 2026-11-21, which changes sampling only: the sampling residual drops from 0.074 to 0.001 LSB, while conversion timing is comparable with the typical-RC run.

The typical-RC SS run failed frame 0 only:

- At t = 0 the DC solution left the comparator latch balanced with its clock high: COMP_P and COMP_N sat at 0.42 and 0.70 V with 256 mV of input and did not change for 60 ns. CMP_CLK was still high 0.2 ns after the first tracking opening. This initial state is not physical. Stimuli that repeat their first code (`verify`) now treat frame 0 as warm-up and report it outside the verdict; in the CWORST_T run the DC start was idle and frame 0 passed anyway.
- The same overlap occurs in operation when a sample aborts a comparison: 71–72 ps in the pre-layout FF-cold restart runs, none at TT. No write occurs and tracking overwrites the kickback. `single_edge_lpe` now reports it as `clock_high_at_opening`; the restart analyzer does not yet.

## Corners not rerun

| Corner | Reason |
| --- | --- |
| FF cold, CBEST_T macro | Ideal to typical SAR wiring cost 0.47 ns of margin and moved settling from 0.114 to 0.107 LSB. Typical to CBEST_T is a smaller step; with the ~0.3 ns reference-recovery time constant, a few ps of shorter window adds about 1 % error, well inside the 0.125 LSB target. |
| SS hot | SS cold is the slowest corner of this design, and SS hot passed pre-layout with more margin. |
| FF hot | Its 0.165 LSB finding is a static reference offset from switch leakage, which SAR wiring cannot change. |

## Clock-latch pulse widths

The `LHCNDQD1` comparator-clock latch (E = SET, CDN = CLR_N, D tied high) is checked against the `min_pulse_width` arcs of the foundry CCS libraries. Widths are measured at 50 % at the latch's own gate in the extracted macro; the limit is interpolated at the slower edge of each pulse (30–70 %, library slew derate 0.5).

| Run | E high: shortest / limit | CDN low: shortest / limit |
| --- | --- | --- |
| SS cold, CWORST_T | 341.7 / 35.5 ps | 1969.7 / 22.6 ps |
| FF cold, typical | 149.2 / 21.6 ps | 745.0 / 14.3 ps |
| TT, typical | 208.3 / 26.2 ps | 1093.5 / 17.1 ps |

The edges are 4–6 ps on a 5 ps output strobe and may be under-resolved; even a 50 ps library slew would raise the SS-cold E limit only to about 44 ps.

## Open items

- Top-level placement and routing, fill, extraction and the terminal-voltage scan.
- Report the clock/tracking overlap in the restart analyzer.
