# Fill of the routed ADC core (Stage 5)

The current fill is revision 4. It fills `sar8_adc_core/layout_route_boot_r2`: the final routed view `layout_route_guard` with both Bootstraps on `sar_bootstrap_flat_8b_p_filled/layout_r2`, which carries its own planned OD/PO fill. The fill hierarchy `sar8_adc_core_fill4` sits beside the core in the wrapper `sar8_adc_core_filled/layout_fill4`. The wrapper also carries copies of the core's 39 top-level texts, so an extraction names the same nets as the unfilled core. Each region has the owner given in the [fill policy](../specs/fill-policy.md#adc-core-fill-owners), and every top-level pass ran the installed foundry OD/PO and metal utilities with the same private job edits as the module fills. [Record](toplevel_fill.json) · [Builder](../design/toplevel_fill.py) · [Workflow](../docs/workflow.md)

| Fill (revision 4) | Owner and region | Evidence |
| --- | --- | --- |
| `sar8_adc_core_fill4_pair_odpo`, `_pair_metal`, `_pair_odrow` | XREF/CDAC pair, its outline outside the array | `se-xref-peripheral-routed` (utility run `se-xref-peripheral-routed-fill`) |
| `sar_bootstrap_flat_8b_p_fill/layout_r2`, inside the Bootstrap wrapper | Bootstrap, both outlines; the top level fills nothing there on any layer | `boot-fill-r2-20261122` (Bootstrap session) |
| `sar8_adc_core_fill4_core_odpo`, `_core_metal` | Top level, the rest of the core outline | `adc-core-fill4-core` |
| `sar8_adc_core_fill4_excl` | DM1EXCL–DM9EXCL, ODBLK and POBLK over every region the core pass does not fill | `adc-core-fill4-lib` |

**OA state.** Revision 4 is built (`adc-core-fill4-build`, approved by the user): `strmin` imported its 93 new cells with 0 errors, and the layout.oa files of `layout_place`, `layout_route_int` and `layout_route_boot_r2` were unchanged. The DRC and extraction below ran on a GDS assembly of the core stream `adc-core-bootr2-b1-chk`, the fill library and the wrapper texts (`adc-core-fill4-chk`). The built view's stream (`adc-core-fill4-oa-chk`) equals that assembly shape for shape on all 80 layers and in all 39 texts, and gives the same three DRC markers. Earlier revisions:

- **Revision 3** (GDS only, superseded): `layout_route_guard` with a top-level OD/PO-only fill cell in the Bootstrap outlines.
- **Revision 2** (built, superseded): `sar8_adc_core_filled/layout_fill2` on `layout_route_guard`, with top-level M1–M9 fill in the Bootstrap outlines.
- **Revision 1** (built, cross-check): `sar8_adc_core_filled/layout_fill1` on `layout_route_full`.

All OA writes created new names only, and the layout.oa files of the core views were identical before and after.

## Pair refill

The frozen stream `se-xref-peripheral-dense` was filled without the top level. Placed in the routed core, its fill overlaps drawn geometry in about 560 places: the CODE0–7/PRESET M3 tracks, the pair VDD/VSS M7–M9 stacks onto the XREF terminals, the VREF trunk landings, and the CREF corner devices below the CDAC, which sit inside the pair outline. The refill keeps the seed `se-xref-peripheral-seed`, the boundary, the utility settings and the job texts (same hashes). It adds, only as context for the utility, the routed core's geometry within 2 µm of the pair outline and DMnEXCL 1 µm around each of the 61 top-level metal shapes inside the outline. The new fill is merged into the unmodified seed, restores the pair's functional geometry (the `se-xref-full-b` hash) when removed, and overlaps no drawn core shape.

| Check | Frozen `se-xref-peripheral-dense` | Refilled `se-xref-peripheral-routed` | Limit |
| --- | --- | --- | --- |
| DRC | M8.DN.1, M9.DN.3 and the two advisories | same four markers | — |
| LVS | CORRECT | CORRECT | — |
| Fixed TOP load, TOPP / TOPN | 52.115 / 52.095 fF | 52.115 / 52.095 fF | 57 fF |
| Side imbalance | 0.020 fF | 0.020 fF | 1 fF |
| k, standalone TT weights | 0.959407 (`xref-fill-tt-after-dense`) | 0.959407 (`xref-routedfill-tt-gain-a`) | — |
| Gain error | 4.2311 % | 4.2310 % | 4.7 % |
| Max DNL / INL | 0.0984 / 0.0769 LSB | 0.0984 / 0.0768 LSB | 0.25 LSB |

The weight run uses the frozen TT fixture, analyzer and cell library byte for byte; only the extraction differs.

## Bootstrap fill

The Bootstrap owns its fill (user decision, 2026-11-22). The reason is the boot capacitor: 200 `cfmom` M1–M3 units that cover 444 of the cell's 613 µm². Each plate's capacitance to ground (two plates per cell; XBOOTN / XBOOTP), all flat typical xRC of the same routed core:

| Fill inside the Bootstrap outlines | Evidence | Plates to ground, XBOOTN | Plates to ground, XBOOTP | Plate to plate |
| --- | --- | --- | --- | --- |
| None (unfilled core) | `adc-core-fill2-base-xtr` | 29.5 / 27.3 fF | 31.5 / 29.7 fF | 192.4 / 195.6 fF |
| None, surroundings filled (diagnostic, fails OD/PO density) | `adc-core-diag-noboot-chk` | 29.8 / 27.1 fF | 33.2 / 30.0 fF | 189.8 / 194.3 fF |
| Top-level M1–M9 and OD/PO (revision 2) | `adc-core-fill2-chk` | 127.1 / 127.1 fF | 127.4 / 126.7 fF | 170.5 / 172.2 fF |
| Top-level OD/PO only (revision 3) | `adc-core-fill3-chk` | 68.5 / 66.6 fF | 68.4 / 65.7 fF | 182.4 / 185.5 fF |
| Bootstrap's planned OD/PO, no top-level fill | `adc-core-fill4-base-xtr` | 40.0 / 37.8 fF | 40.2 / 38.6 fF | 190.0 / 192.6 fF |
| **Same, with the revision 4 top-level fill around it** | `adc-core-fill4-chk` | **41.2 / 38.4 fF** | **41.5 / 38.3 fF** | **187.6 / 191.3 fF** |

The top-level fill around the cells adds at most 1.2 fF to ground per plate. The values match the Bootstrap's standalone filled extraction (37.9 / 40.4 fF, 193.2 fF plate to plate) within 3 fF. The two placements differ by under 0.4 fF to ground.

## Core pass

The core pass fills the 122 × 111 µm outline outside the exclusion cell:

- all layers over the pair outline, both Bootstrap outlines, the four TOP exclusions, the comparator keep-out and the comparator decap strips;
- OD/PO and M1–M6 over the SAR macro;
- the drawn comparator group (COMP_P, COMP_N, CMP_CLK, SEQ_SAMPLE and the shields), on each rectangle's layer ±1, 1 µm around it;
- the VINN/VINP trunks on M4–M6, 1 µm around them.

It runs with the utility's optional dummy TCD off: the default insertion (`adc-core-fill1-core`) put one `TCD_H` monitor with drawn OD, PO and N-well at x 11.7–20.7, y 68.4–71.9, beside the CDAC array's TOPN half. Its metal fill is identical to revision 3; the OD/PO fill differs only around the Bootstrap cells, where the utility now sees their planned pattern.

`verify` checks the assembled hierarchy against the core stream: no fill overlaps a drawn shape of its layer, the core pass leaves every exclusion empty on its layers, the pair fill leaves its entry blocks empty, and the owners' fill does not overlap. Every value is 0.

## Density DRC

Calibre DRC (installed cell deck) of the revision 4 assembly (`adc-core-fill4-chk`) against the unfilled view (`adc-core-bootr2-b1-chk`):

| Rules | Unfilled `layout_route_boot_r2` | Filled |
| --- | ---: | ---: |
| M4–M7.DN.6 (low-density windows) | 71 | 0 |
| M4–M7.DN.1, M8.DN.1, M9.DN.3 (125 µm minimum density) | 6 | 0 |
| Mx.DN.7 (three consecutive layers, 30 µm) | 5 | 0 |
| OD.DN.3, OD.S.14 | 6 | 0 |
| PO.DN.3 | 5 | 0 |
| PO.DN.3.1 (10 µm windows) | 3 | 1 |
| DIODMY_L, IO_CONNECT_CORE_NET_VOLTAGE_IS_CORE (advisories) | 2 | 2 |
| Total | 98 | 3 |

- **125 µm windows.** M8.DN.1 and M9.DN.3 close inside the core. Mx.DN.7 over the Bootstrap cells closes too, although the cells block M6–M9 fill.
- **The remaining PO.DN.3.1 marker** merges four 10 µm windows at x 35–60, y 60–70, each at 9.894 % PO against 10 %. The array's north rows carry about 12 % PO; the 1.7 µm strip above them (y 68.3–70) is the TOP-tee exclusion, where the policy puts POBLK within 1 µm of the TOP centrelines. It needs a decision: a written waiver, a narrower POBLK inside the tee exclusion, or more array-edge PO in the pair.
- **What still needs the ring:** the 125 µm windows that straddle the core edge, the Mn.DN.3 gradient, the OD/PO windows across the core boundary, and the dummy TCD placement.

## Extraction

The flat coupled xRC (typical, installed deck) of the revision 4 assembly is compared with the unfilled view (`adc-core-fill4-base-xtr`), with the same deck and the same 39 top-level texts. The deck merges dummy metal into each conductor layer, so floating fill adds no nets and its coupling appears as capacitance to ground. At core level the TOP fixed load is TOP's capacitance to ground, VDD!, VREFP/VREFN and the two trunks.

| Net | Unfilled | Filled | Change |
| --- | ---: | ---: | ---: |
| TOPN | 250.999 fF | 250.248 fF | −0.752 fF |
| TOPP | 250.492 fF | 250.304 fF | −0.188 fF |
| COMP_P | 6.602 fF | 7.657 fF | +1.055 fF |
| COMP_N | 6.983 fF | 8.048 fF | +1.065 fF |
| CMP_CLK | 7.531 fF | 8.583 fF | +1.052 fF |
| SEQ_SAMPLE | 26.975 fF | 29.522 fF | +2.546 fF |
| VINN / VINP | 3.671 / 3.671 fF | 4.887 / 4.882 fF | +1.216 / +1.211 fF |

| Stage 5 check | Result | Limit |
| --- | --- | --- |
| Pair TOP fixed load, TOPP / TOPN (standalone, `se-xref-peripheral-routed`) | 52.115 / 52.095 fF | 57 fF |
| Pair side imbalance | 0.020 fF | 1 fF |
| Core TOP fixed load, TOPN / TOPP | 53.489 / 53.508 fF | 57 fF |
| Core TOPN − TOPP, total / fixed | 0.056 / 0.019 fF (unfilled 0.507 fF total) | 1 fF |
| COMP_P / COMP_N / CMP_CLK route load | 6.13 / 6.25 / 6.10 fF | 11.4 / 11.4 / 11.1 fF |

- **TOP.** TOPN's total falls 0.75 fF mostly through its coupling to the CDAC MSB bottom plates: the deck looks up conductor thickness against local density, so fill around the pair shifts the CDAC's internal capacitances while their geometry is unchanged (Stage 4b saw the same effect).
- **Handshake.** The route loads are the Stage 4b values on `layout_route_full` (5.04 / 5.15 / 5.03 fF) plus the change from the guard ring and the Bootstrap r2 cells and the fill's change. Most of the fill's share is metal above the SAR macro (M7–M9) and in the corridor outside the channel's ±1 layers.
- **VIN and SEQ_SAMPLE** gain 1.2 and 2.5 fF, against 6.1 and 3.3 fF with the revision 2 Bootstrap fill. VINN and VINP stay within 0.005 fF of each other.

## Open items

- **PO.DN.3.1 at the TOP tee:** waiver, narrower POBLK, or more array-edge PO in the pair.
- **The two advisories** need written waivers (issue #12).
- **Bootstrap r2** is not yet ADC-qualified; if it changes, the core view and this revision are redone.
- **Chip-level fill:** the core-to-ring gap and ring, windows across the core edge, the Mn.DN.3 gradient, and the dummy TCD placement.
- **Corner extractions** of the filled core are not part of this record; the Stage 6 session extracts the top-level wiring and the pair corners itself.
