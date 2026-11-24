# Chip-level fill (Stage 5)

**Current: fill revision 7** on `sar8_adc_chip/layout_full_fill5_r8_seal`, the 892 µm die. The fill hierarchy `sar8_chip_fill7` sits beside the chip in the wrapper `sar8_adc_chip_filled`, which also carries copies of the chip's 56 top-level texts. It is built in OA as `sar8_adc_chip_filled/layout_fill7` (build `chip-sfill7-build`, approved by the user). Each region has the owner given in the [fill policy](../specs/fill-policy.md#chip-fill-owners). [Record](chip_fill.json) · [Builder](../design/chip_fill.py) · [Waivers](chip_drc_waivers.md) · [Workflow](../docs/workflow.md#chip-fill)

## Result

| Check | Unfilled r8 (`chip-r8-b1-chk`) | Filled, revision 7 (`chip-sfill7-chk`) |
| --- | ---: | ---: |
| DRC | 2896 | **224** |
| of which density (M1–M9, Mx.DN.7, OD, OD.S.14, PO, SR_DOD) | 2672 | **0** |
| dummy-pattern rules (DMn, DOD, DPO, DVIAn) | 0 | 0 |
| LVS | CORRECT | CORRECT |
| ERC | 296 | 296, the same check for check |
| Flat LUP/ESD, 72 LUP and ESD checks | 978, LUP 0 | 978, LUP 0 |

- **What is left:** ESD.18g 120, ESD.19g 96, ESD.WARN.1 6, DIODMY_L 1 and IO_CONNECT 1. Every one is a non-density result of the unfilled view; the [waiver document](chip_drc_waivers.md) gives each its class.
- **The ADC core:** no result lies inside it or crosses it, apart from the two chip-wide advisories.
- **OA build** (`chip-sfill7-build`): strmin imported the 97 cells of the fill library with 0 errors and wrote new names only (`-writeMode noOverwrite`). The chip view's layout.oa was the same before and after (`8294bd77…`); the wrapper's layout.oa is `9d370f3c…`. The built view's stream (`chip-sfill7-oa-chk2`) equals the checked assembly `chip-sfill7-chk` cell for cell: the chip subtree, `sar8_chip_fill7` and all 56 texts. Its checks are the same: DRC 224 with the same rule counts, LVS CORRECT, ERC 296. The first stream attempt (`chip-sfill7-oa-chk`) failed because the check's cds.lib lacked the `sealring` library, which the 892 µm seal ring references.
- `verify chip-sfill7-lib` checked OD, PO and M1–M9 on the r8 stream. For those layers it measured 0 µm² over drawn geometry, in the exclusions and outside the seal-ring keep-in.
- A separate audit of the OA stream found 15 chip-level dummy vias inside the frozen core exclusion. V1 through V6 contributed 2, 2, 4, 3, 3 and 1 respectively (0.216 µm² summed over layers). At every cut, the r8 metal on both faces is dummy metal and there is zero overlap with an existing r8 via on that cut layer. Calibre reported zero dummy-pattern violations. The project’s all-layer exclusion still needs a disposition. The audit did not measure the electrical change. [Coordinates, layers and stream hash](chip_fill7_core_dummy_vias.json) · [System review](https://github.com/chenzc24/sar-adc-t28/issues/12)

## Revision 7

Revision 7 is one pass of the foundry OD/PO and metal utilities (`chip-sfill7-pass`, dummy TCD off). The utility ran 75 s for OD/PO and 757 s for metal. Its seed is the r8 stream plus one exclusion cell of 1,097 rectangles. Revision 7 differs from revision 6 in three ways:

1. **IO ring cells are filled.** The seed no longer excludes the IO cell outlines. The utility fills inside them with its own IO dummy types: metal inside the IO rows, OD/PO in the strip under the pads outside the rows. Revision 6 excluded every IO cell, and with it the strip under the PAD60GU bond pads; 228 density results stayed open in the IO band and the corners.
2. **A planned M9 frame along the ring.** It is added to the planned M9 band around the core. The 125 µm windows from x or y 59 to 184 µm (and 559 to 684 µm) reach onto the IO cells; utility squares fill only 23.9–25.3 % of their opening part. All planned stripes together: 980 rectangles, 73,331 µm², 3 µm wide on a 6 µm pitch, 4–28.75 µm long, 3 µm clear of drawn M9 and of every M9 exclusion. The utility's M9 keeps 3 µm away from each stripe.
3. **The clamp exclusion follows the r8 clamps** (`PCLAMPC_V_G`).

The fill library `chip-sfill7-lib` has 97 cells: the OD/PO, metal, planned M9 and exclusion masters with their children `ACH7*`.

## Extraction of the chip routes

The VINN/VINP and VREFP/VREFN chip routes, cut out with a 5 µm corridor (cell `sar8_chip_routes`), were extracted unfilled (`chip-sfill7-route-base-xtr`, from r8) and filled (`chip-sfill7-route-filled-xtr`). The deck merges floating fill into each conductor layer, so coupling to fill counts as capacitance to ground; the changes are upper bounds.

| Net | Unfilled | Filled, revision 7 | Change | Change with revision 5 (r6, 1000 µm) |
| --- | ---: | ---: | ---: | ---: |
| VINN | 56.49 fF | 65.40 fF | +8.90 fF | +8.16 fF |
| VINP | 56.49 fF | 64.64 fF | +8.15 fF | +7.95 fF |
| VREFN | 92.21 fF | 253.31 fF | +161.10 fF | +166.83 fF |
| VREFP | 85.86 fF | 222.63 fF | +136.76 fF | +140.87 fF |

- **VIN mismatch:** the two inputs now differ by 0.76 fF (0.21 fF with revision 5). The chip-level periphery check decides whether that is acceptable.
- **VREF:** almost all of the added capacitance is to ground.
- **Not extracted:** the pad capacitance as a whole.

## How revision 7 was chosen

Small GDS-only trials on `layout_full_fill5_r7_seal` came first. Each patched the revision 6 assembly locally and ran chip DRC; nothing went into OA.

| Trial | Change | Chip DRC |
| --- | --- | --- |
| `chip-se1-drc` | Planned M9 frame along the ring | No DM9 or M9 rule; every side window 20–32 % |
| `chip-se2c-drc` | Utility fill inside the west IO cells and under their pads (y 150–600) | No dummy rule; OD/PO/M8/M9 density 0 in the slice |
| `chip-se3-drc` | The same in the south-west corner and on the east side | No dummy rule; OD.S.14, M8.DN.1, Mx.DN.7 and PO.DN.3 0 there |
| `chip-clamp-vg-trial` | `PCLAMPC_V_G` in place of `PCLAMPC_H_G` | 462 to 452; the four clamp rules 0 (made permanent by chip-level in r8) |

The first west-slice merge (`chip-se2-drc`) reported 15,540 dummy-rule results. That was an artefact of the merge, not of the utility: revision 6 had filled the 4 µm gaps between the pads, and the slice fill was added next to it. Only the merges were cut at slice edges; revision 7 is one pass over the whole chip.

## Earlier revisions

| Revision | Chip view | Check | DRC unfilled → filled | Status |
| --- | --- | --- | --- | --- |
| 1–3 | r3_seal, r4_seal | `chip-sfill1-chk2` (revision 1) | 1944 → 373 | Superseded |
| 4 | `layout_full_fill5_r6_seal` (1000 µm) | `chip-sfill4b-chk` | 1911 → 379 | Superseded |
| 5 | `layout_full_fill5_r6_seal` (1000 µm) | `chip-sfill5-chk` | 1911 → 369 | Superseded by the 892 µm die |
| 6 | `layout_full_fill5_r7_seal` (892 µm) | `chip-sfill6-chk2` | 2904 → 462 | Fallback |
| 7 | `layout_full_fill5_r8_seal` (892 µm) | `chip-sfill7-chk` | 2896 → 224 | Current |

- **Revision 5** added the planned M9 band around the core, closing the M9.DN.3 windows over the core edge (15.8–19.0 % with revision 4). It also narrowed the pair clamp's feed exclusion to M7–M9.
- **Revision 6** is revision 5 clipped to the 892 µm keep-out (`chip_fill.py clip`). The clip drops whole fill elements and never reshapes them; it also drops every dummy via within 2 µm of the edge. Rewrapped on r8, minus the fill within 1 µm of the two new PFILLER20_G (SR_DPO spacing), it gives `chip-sfill6r8b-chk`: DRC 452, LVS CORRECT, ERC 296. It is the fallback if TSMC or the shuttle refuses dummy fill inside the IO library cells.

## Open items

- **Acceptance:** TSMC or the shuttle must accept dummy fill inside the IO library cells ([waivers](chip_drc_waivers.md#dummy-fill-inside-the-io-library-cells)).
- **VIN:** the chip-level periphery check reviews the 0.76 fF VINN–VINP corridor difference.
