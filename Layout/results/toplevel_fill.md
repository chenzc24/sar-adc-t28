# Fill of the routed ADC core (Stage 5)

The fill of the final routed view `sar8_adc_core/layout_route_guard` is revision 2: the hierarchy `sar8_adc_core_fill2`, placed with the core in the wrapper `sar8_adc_core_filled/layout_fill2`. The wrapper also carries copies of the core's 39 top-level texts, so an extraction names the same nets as the unfilled core. Each region has the owner given in the [fill policy](../specs/fill-policy.md#adc-core-fill-owners), and every pass ran the installed foundry OD/PO and metal utilities with the same private job edits as the module fills. [Record](toplevel_fill.json) · [Builder](../design/toplevel_fill.py) · [Workflow](../docs/workflow.md)

| Fill master (revision 2) | Owner and region | Evidence |
| --- | --- | --- |
| `sar8_adc_core_fill2_pair_odpo`, `_pair_metal`, `_pair_odrow` | XREF/CDAC pair, its outline outside the array | `se-xref-peripheral-routed` (utility run `se-xref-peripheral-routed-fill`) |
| `sar8_adc_core_fill2_boot_odpo`, `_boot_metal` | Top level, one cell placed R0 on XBOOTP and MY on XBOOTN | `adc-core-fill2-boot` |
| `sar8_adc_core_fill2_core_odpo`, `_core_metal` | Top level, the rest of the core outline | `adc-core-fill2-core` |
| `sar8_adc_core_fill2_excl` | DM1EXCL–DM9EXCL, ODBLK and POBLK over every region the core pass does not fill | `adc-core-fill2-lib` |

**OA state.**

- **Revision 1** (`sar8_adc_core_filled/layout_fill1` on `layout_route_full`, fill `sar8_adc_core_fill1`) is built in OA (`adc-core-fill1-build`):
  - `strmin` imported its 130 new cells with 0 errors;
  - the layout.oa files of `layout_place`, `layout_route_int` and `layout_route_full` were identical before and after;
  - its stream reproduces the routed core exactly (polygon count and area on all 58 layers) and the fill library on every fill layer.
- **Revision 2** is verified on a GDS assembly (`toplevel_fill wrapper-gds`): the guard stream, the fill library and the wrapper top with the core's texts.
  - For revision 1, the same assembly matches the OA wrapper's stream on all 79 layers and in every text.
  - Its OA build is not done: the session's permission check stopped the second OA write, which needs the user's approval.
  - Its record entry `oa.revision2.built` says whether it has been built since.

The guard view differs from `layout_route_full` only by additions in x 91.33–122, y 51.1–69.7: the ring's OD, PP, CO, M1, M2 and VIA1, and a fourth `0` pin. Nothing was removed.

- **Pair and Bootstrap fill carry over.** The pair seed copies only geometry within 2 µm of the pair outline, so the pair refill holds unchanged. The Bootstrap pass, rerun on the guard stream, gave a fill identical polygon for polygon to revision 1.
- **The core pass reran** around the ring.

## Pair refill

The frozen stream `se-xref-peripheral-dense` was filled without the top level. Placed in the routed core, its fill overlaps drawn geometry in about 560 places: the CODE0–7/PRESET M3 tracks, the pair VDD/VSS M7–M9 stacks onto the XREF terminals, the VREF trunk landings, and the CREF corner devices below the CDAC, which sit inside the pair outline. The refill keeps everything else:

- the seed `se-xref-peripheral-seed`;
- the boundary and the utility settings;
- the job texts: the hashes are the frozen run's.

It adds two things, only as context for the utility:

- the routed core's geometry within 2 µm of the pair outline;
- DMnEXCL 1 µm around each of the 61 top-level metal shapes inside the outline.

The new fill is merged into the unmodified seed. Removing it restores the pair's functional geometry (the `se-xref-full-b` hash), and it overlaps no drawn core shape on any layer.

| Check | Frozen `se-xref-peripheral-dense` | Refilled `se-xref-peripheral-routed` | Limit |
| --- | --- | --- | --- |
| DRC | M8.DN.1, M9.DN.3 and the two advisories | same four markers | — |
| LVS | CORRECT | CORRECT | — |
| Fixed TOP load, TOPP / TOPN | 52.115 / 52.095 fF | 52.115 / 52.095 fF | 57 fF |
| Side imbalance | 0.020 fF | 0.020 fF | 1 fF |
| k, standalone TT weights | 0.959407 (`xref-fill-tt-after-dense`) | 0.959407 (`xref-routedfill-tt-gain-a`) | — |
| Gain error | 4.2311 % | 4.2310 % | 4.7 % |
| Max DNL / INL | 0.0984 / 0.0769 LSB | 0.0984 / 0.0768 LSB | 0.25 LSB |

The weight run uses the frozen TT fixture, analyzer and cell library byte for byte; only the extraction differs. The corridors that changed lie in the south XREF strip and the west and east margins, far from TOP, so TOP sees the same fill.

## Bootstrap and core passes

- **Bootstrap.** The Bootstrap cell is generated inside the XBOOTP outline, with the XBOOTN neighbourhood (±2 µm) mirrored about x 46.115 as extra context. Placed R0 and MY, it overlaps no drawn shape on either side.
- **Core pass.** It fills the 122 × 111 µm outline outside the exclusion cell:
  - all layers over the pair outline, both Bootstrap cells, the four TOP exclusions, the comparator keep-out and the comparator decap strips;
  - OD/PO and M1–M6 over the SAR macro;
  - the drawn comparator group (COMP_P, COMP_N, CMP_CLK, SEQ_SAMPLE and the shields), on each rectangle's layer ±1, 1 µm around it;
  - the VINN/VINP trunks on M4–M6, 1 µm around them.

  Around the guard ring the utility keeps its own spacing.

The first core pass, `adc-core-fill1-core`, used the utility's default dummy TCD insertion. It placed one `TCD_H` monitor with drawn OD, PO and N-well at x 11.7–20.7, y 68.4–71.9: 0.06 µm above the CDAC array and only on the TOPN side. Every later core pass runs with dummy TCD off, and TCD placement is left to the chip-level fill.

`verify` checks each revision against its own core stream:

- no fill overlaps a drawn shape of its layer, including the ring;
- the core pass leaves every exclusion empty on its layers;
- the pair fill leaves its entry blocks empty, and the Bootstrap fill the route exclusions at both placements;
- no two owners' fill overlap.

Every value is 0 in both revisions.

## Density DRC

Calibre DRC (installed cell deck) of the revision 2 assembly (`adc-core-fill2-chk`), against the unfilled guard view (`adc-core-guard-g1-chk`). Revision 1 on `layout_route_full` gives the same three markers, against 95.

| Rules | Unfilled guard view | Filled |
| --- | ---: | ---: |
| M4–M7.DN.6 (low-density windows) | 71 | 0 |
| M4–M7.DN.1, M8.DN.1, M9.DN.3 (125 µm minimum density) | 6 | 0 |
| Mx.DN.7 (three consecutive layers, 30 µm) | 5 | 0 |
| OD.DN.3, OD.S.14 (including the ring's window x 102–122, y 50–70) | 8 | 0 |
| PO.DN.3 | 3 | 0 |
| PO.DN.3.1 (10 µm windows) | 1 | 1 |
| DIODMY_L, IO_CONNECT_CORE_NET_VOLTAGE_IS_CORE (advisories) | 2 | 2 |
| Total | 96 | 3 |

- **125 µm windows.** M8.DN.1 and M9.DN.3 close inside the core: the window backs up inside the 122 × 111 µm extent. The fill policy's M8/M9 grid (step 4) was not needed for density.
- **What still needs the ring.** The chip-level fill must keep these windows passing once they also cover the core-to-ring gap and the ring:
  - the 125 µm windows that straddle the core edge;
  - the adjacent-window gradient (Mn.DN.3);
  - the OD/PO windows across the core boundary;
  - the dummy TCD placement.
- **The remaining PO.DN.3.1 marker.** It merges four 10 µm windows at x 35–60, y 60–70, each at 9.894 % PO against a 10 % minimum. The array's north rows carry about 12 % PO. The 1.7 µm strip above them (y 68.3–70) is the TOP-tee exclusion, where the policy puts POBLK within 1 µm of the TOP centrelines, and has none. The core fill cannot reach it without entering that exclusion or the pair's qualified array plan. It needs a decision: a written waiver, a narrower POBLK inside the tee exclusion, or more array-edge PO in the pair.

## Extraction

The flat coupled xRC (typical, installed deck) of the revision 2 assembly (`adc-core-fill2-chk`) is compared with the unfilled guard view (`adc-core-fill2-base-xtr`). Both use the same deck and the same 39 top-level texts. Notes on the method:

- **Floating fill.** The deck merges dummy metal into each conductor layer, so floating fill adds no nets and its coupling appears as capacitance to ground.
- **Block-internal nets.** Their names carry the wrapper's instance prefix and unnamed nets are renumbered, so the comparison uses totals and ground.
- **TOP fixed load.** At core level this is TOP's capacitance to ground, VDD!, VREFP/VREFN and the two trunks.

| Net | Unfilled | Filled | Change | To ground | Limit |
| --- | ---: | ---: | ---: | ---: | --- |
| TOPN | 251.003 fF | 250.551 fF | −0.453 fF | +0.219 fF | — |
| TOPP | 250.496 fF | 250.637 fF | +0.141 fF | +0.276 fF | — |
| COMP_P | 6.602 fF | 7.672 fF | +1.069 fF | +1.156 fF | — |
| COMP_N | 6.983 fF | 7.967 fF | +0.984 fF | +1.256 fF | — |
| CMP_CLK | 7.531 fF | 8.583 fF | +1.052 fF | +1.240 fF | — |
| SEQ_SAMPLE | 26.973 fF | 30.321 fF | +3.348 fF | +4.280 fF | — |
| VINN / VINP | 3.563 / 3.563 fF | 9.672 / 9.670 fF | +6.109 / +6.107 fF | +6.96 / +6.95 fF | — |

| Stage 5 check | Result | Limit |
| --- | --- | --- |
| Pair TOP fixed load, TOPP / TOPN (standalone, `se-xref-peripheral-routed`) | 52.115 / 52.095 fF | 57 fF |
| Pair side imbalance | 0.020 fF | 1 fF |
| Core TOP fixed load, TOPN / TOPP (ground, VDD!, VREF nets) | 53.830 / 53.881 fF, of which fill adds 0.20 / 0.26 fF | 57 fF |
| Core TOPN − TOPP, total | 0.086 fF (unfilled 0.507 fF) | 1 fF |
| Core TOPN − TOPP, fixed | 0.052 fF | 1 fF |
| COMP_P / COMP_N / CMP_CLK route load | 6.14 / 6.17 / 6.10 fF | 11.4 / 11.4 / 11.1 fF |

- **TOP.** Fill adds 0.22 / 0.28 fF to TOP's ground capacitance. TOPN's total falls 0.45 fF because its coupling to the CDAC MSB bottom plates drops about 0.3 fF. The deck looks up conductor thickness against local density, so the fill around the pair shifts the CDAC's internal capacitances while their geometry is unchanged; Stage 4b saw the same effect. The side difference falls from 0.51 to 0.09 fF.
- **Handshake.** The route loads are the Stage 4b values on `layout_route_full` (5.04 / 5.15 / 5.03 fF) plus the ring's change (+0.03 / +0.04 / +0.01 fF) and the fill's change. Most of the fill's share is metal above the SAR macro (M7–M9) and in the corridor outside the channel's ±1 layers.
- **VIN and SEQ_SAMPLE.** These grow mainly through the Bootstrap fill around their wiring inside the Bootstrap cells. The mirrored Bootstrap cell keeps VINN and VINP within 0.002 fF of each other. SEQ_SAMPLE has no adopted load limit; the Stage 6 sampling-edge checks cover it.

Revision 1 (`adc-core-fill1-chk` against `layout_route_full`) gives the same TOP numbers and handshake changes within 0.02 fF.

## Open items

- **PO.DN.3.1 at the TOP tee** (one merged marker, 9.894 % against 10 %): a waiver, a narrower POBLK inside the tee exclusion, or more array-edge PO in the pair.
- **The two advisories** (DIODMY_L, IO_CONNECT_CORE_NET_VOLTAGE_IS_CORE) still need written waivers (issue #12).
- **The revision 2 OA build** (`sar8_adc_core_filled/layout_fill2` with `sar8_adc_core_fill2`) waits for approval. Once it is built, stream it and confirm the same three DRC markers.
- **Chip-level fill:** the core-to-ring gap and ring, windows across the core edge, the Mn.DN.3 gradient, and the dummy TCD placement.
- **Corner extractions:** the extraction here is typical only. Stage 6 at SS cold and FF hot needs CWORST_T and CBEST_T re-extractions of the same assembly.
