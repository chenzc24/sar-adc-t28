# Chip DRC and ERC waivers (Stage 5, proposed)

This document covers every DRC and ERC result left on the filled chip. Each result is in one of three classes. Results with a **documented** basis cite TSMC's own text: an IO library release note or the deck's rule description. **Conditional** results need a written statement from the design owner. **Open** results go to TSMC as questions. The lab's IO ring skill deck is not used as a basis: it unselects checks for the IO cells, but it is not a foundry document. The user signs the document; until then every entry is a proposal.

- **Chip:** frozen view `sar8_adc_chip/layout_full_fill5_r8_seal` (892 µm die, (−66, −66)–(826, 826); clamps on `PCLAMPC_V_G`; one `PRCUTA_G` per domain boundary). The filled chip `sar8_adc_chip_filled/layout_fill7` is fill revision 7 ([fill record](chip_fill.md)): checked as the assembly `chip-sfill7-chk` and, after the OA build, as the view's stream `chip-sfill7-oa-chk2`, with the same results.
- **Decks:** DRC is the installed chip deck `drc_rule_T28_chip` (T-N28-CL-DR-002-C1 v2.3a; `FULL_CHIP`, `WITH_SEALRING`, `GUIDELINE_ESD`). LVS and ERC are the installed `calibre.lvs` with the IO ring deck's lines (`chip_physical.py`). The IO library release notes cite older deck versions (DRC C1 v1.7b, LVS C1 v1.0_3o). The rule names are the same, but whoever submits the tapeout should confirm that the waivers carry over.
- **Evidence (thu-wei, `<remote_root>/evidence/`):**
  - Filled chip `chip-sfill7-chk`: DRC 224, LVS CORRECT, ERC 296.
  - Unfilled r8 `chip-r8-b1-chk`: DRC 2896, of which 224 are non-density; LVS CORRECT; ERC 296.
  - Flat LUP/ESD: unfilled `chip-r8-b1-flat-lupesd` and filled `<remote_root>/userdrc/chip-sfill7-flat-lupesd`, both 978 (LUP 0).
- **Run it yourself:** `<remote_root>/userdrc/chip-sfill7/` holds two decks.
  - `drc_full.svrf` is the job deck of `chip-sfill7-chk`, byte for byte apart from the result file names.
  - `drc_waived.svrf` adds one line, `DRC UNSELECT CHECK ESD.18g ESD.19g`, with its basis in a comment.
  - `run_full.csh` and `run_waived.csh` run them on `fixture.gds`, the filled chip.
  - The unselect applies to the whole chip, so rerun the full deck after any change that adds MOS drivers outside the IO library.

## Summary

| Class | Rule | DRC / ERC | Where | Basis or action |
| --- | --- | ---: | --- | --- |
| Documented | ESD.18g / ESD.19g | 120 / 96 (flat 540 / 432) | PRUW08SDGZ output pads | IO library RN 170A and 170C §5a |
| Documented | IO_CONNECT_CORE_NET_VOLTAGE_IS_CORE:WARNING1 | 1 | chip-wide | Deck rule text: "not a gated item for tape-out" |
| Documented | ERC mnpg / npvss49 / floating.nxwell_float | 280 / 12 / 4 | IO library pad cells | IO library RN 170A §5b, cell by cell |
| Conditional | DIODMY_L:WARNING | 1 | Bootstrap BTOP N-well diode | Deck rule text; Bootstrap owner's written statement, or DIODMY + DIODMY_L |
| Open | ESD.WARN.1 | 6 | PDB3AC analog pads | Ask TSMC: the library master carries no SDI |
| Open (not a DRC result) | Dummy fill inside IO library cells | — | IO ring, fill revision 7 | Ask TSMC or the shuttle to accept it |
| Closed | PO.R.5, PO.R.6, PO.W.2, SR_DPO.R.4 | 0 (was 10) | ESD clamps | Fixed in r8: `PCLAMPC_V_G` |
| Closed | ERC floating.nxwell_float / floating.psub at the power cuts | 0 (was 4 / 8) | PRCUTA_G pairs | Fixed in r8: one cut per boundary |
| Closed | Density (M1–M9, Mx.DN.7, OD, PO, SR_DOD) | 0 (was 228 on fill revision 6) | IO band and corners | Fill revision 7 |
| Closed | MATCH.WARN.1 | 0 | comparator | MATCHING markers (r6) |
| Deviation | Comparator matching class: MATCHING, not ANARRAY_H/M | — | comparator | Accepted by the user |
| Confirm | WITH_SEALRING_OPTION:WARNING, DM1–DM9.R.1 | 0 | — | Cleared |

All 224 DRC results on `chip-sfill7-chk`: ESD.18g 120, ESD.19g 96, ESD.WARN.1 6, DIODMY_L 1, IO_CONNECT 1. The documented waivers cover 217. A run of `drc_waived.svrf` (`<remote_root>/userdrc/chip-sfill7/DRC_waived.rep`) reports 8: the conditional and open results. IO_CONNECT stays selected in that deck. All 296 ERC results are documented. No result lies inside the ADC core.

## Documented

### ESD.18g / ESD.19g

- **Rule:** total NMOS (PMOS) finger width on one drain net above 360 (480) µm; check ESD.27g/28g. These are guidelines, active because the deck sets `#DEFINE GUIDELINE_ESD`.
- **Count:** 120 / 96 hierarchical; 540 / 432 flat. Unchanged since the partial assembly, by every fill revision and by r8.
- **Where:** inside the eight PRUW08SDGZ output pads (`PRUW08SDGZ_V_G` at die x 190–570, y 0–110; `PRUW08SDGZ_H_G` at x 650–760, y 190–330).
- **Basis:** TSMC IO library `tphn28hpcpgv18`, release note RN_TPHN28HPCPGV18_170A §5a ("The following DRC violations can be waived: ESD.18g, ESD.19g") and rn_tphn28hpcpgv18_170c §5a ("flagged by T-N28-CL-DR-002-C1 v1.7b in chip-level check of I/O can be waived: ESD.18g, ESD.19g, ESD.37g"). The drivers are the library's own cells, used unmodified.

### IO_CONNECT_CORE_NET_VOLTAGE_IS_CORE:WARNING1

- **Rule:** a net that reaches both IO and core MOS is checked with core-voltage spacing because it carries no voltage marker.
- **Count:** 1, chip-wide. **Where:** the Bootstrap's 1.8 V thick-oxide devices (`nch_18_mac`, `pch_18_mac`) on core nets.
- **Basis:** the installed deck's rule text, item 5: "This warning is just a reminder, not a gated item for tape-out." The nets stay at core voltage plus the boost. Block-level record: `bootstrap.json`.

### ERC

Source: LVS EXECUTE ERC of the chip LVS on `chip-sfill7-chk`, LVS CORRECT. The 296 results equal the unfilled r8 (`chip-r8-b1-chk`) check for check, so the fill adds no ERC result.

| Check | Count | Cells | Basis: RN_TPHN28HPCPGV18_170A §5b, rn_…_170c §5b |
| --- | ---: | --- | --- |
| mnpg | 280 | PVDD3AC_V_G 120, PVDD3AC_H_G 102, PVDD1DGZ_H_G 58 | mnpg listed for PVDD3AC_H_G/_V_G and PVDD1DGZ_H_G |
| npvss49 | 12 | sub-cells HBO850_POSTDRV_PVSS2 and HBO850_DIO_P03/P04_TPA(_WOPDIO), placed only in PVSS2AC_V_G and PVSS3AC_H_G/_V_G | npvss49 listed for PVSS2AC_V_G and PVSS3AC_H_G/_V_G |
| floating.nxwell_float | 4 | HBO850_DIO_P03/P04_TPA(_WOPDIO), the same PVSS parents | floating.nxwell_float listed for PVSS2AC_V_G and PVSS3AC_H_G/_V_G |

The parent cell of each sub-cell was found by tracing the GDS hierarchy of `inputs/chip_r8seal.gds`.

## Conditional

### DIODMY_L:WARNING

- **Rule:** each low-leakage-concern diode must be covered by DIODMY_L. The deck text adds: "If there's no low leakage diode concern cell in the chip, the violation can be ignored." DRM 4.5.35: DIODMY_L must be drawn identically to DIODMY.
- **Count:** 1, chip-wide. **Where:** the boosted BTOP N-well diode in both Bootstrap cells (`sar_bootstrap_flat_8b_p_core`).
- **Needed:** one of two things.
  - The Bootstrap owner states in writing that this diode is not a low-leakage-concern diode. Its leakage is already in the extracted hold-droop and corner checks, which pass (`bootstrap.json`, Bootstrap r2 qualification).
  - Or the diode gets DIODMY and DIODMY_L in a new Bootstrap view, which means requalifying the core.

## Open: questions for TSMC or the shuttle

### ESD.WARN.1

- **Rule:** SDI (122;0) must be found on each power, ground or I/O pad's CB/CBD/CB2/PM2.
- **Count:** 6. **Where:** the six PDB3AC analog pads: `PDB3AC_H_G` at die x 0–110, y 370–570, and `PDB3AC_V_G` at x 310–330 and 490–510, y 650–760. They carry VREFP and VREFN (two pads each), VINN and VINP.
- **Finding:** the TSMC masters `PDB3AC_H_G` and `PDB3AC_V_G` (library GDS `tphn28hpcpgv18`, 110a, 9 lm) contain no SDI shape. The other pad masters do: PRUW08SDGZ_V_G has 54, PVDD3AC_V_G 60, PVDD1DGZ_H_G 29. Neither release note lists ESD.WARN.1.
- **Action:** ask TSMC whether ESD.WARN.1 on PDB3AC is expected. Do not draw SDI over a foundry cell ourselves.

### Dummy fill inside the IO library cells

Fill revision 7 lets the foundry utility fill inside the IO ring cells and under the pads, which closes every density result. This is not a DRC result; it is a question of acceptance.

- **For it:** the DRM's minimum-density rules exclude only the corner triangles, SEALRING_ALL, LOGO/INDDMY and a few device markers. They exclude neither IO cells nor bond pads (Mu.DN.4, the maximum, excludes bond pads; Mu.DN.3, the minimum, does not). The IO GDS carries no ODBLK, POBLK or DMxEXCL. The metal utility handles CB and WBDMY (CUP pads) itself and used its own IO dummy types. DRM DMx.R.6U asks for uniform dummy fill with as little DMxEXCL as possible.
- **Checked on the chip:** DRC shows no dummy rule. LVS is CORRECT, ERC unchanged, flat LUP/ESD unchanged. Fill verify finds 0 overlap with drawn geometry inside the IO cells.
- **Not covered by any document:** no release note says dummy fill inside the library cells is allowed. DRM 6.7.3 requires blockage over "pad metal area for high frequency signals". The VIN and VREF pads are treated as not high-frequency.
- **Action:** ask TSMC or the shuttle to accept dummy fill inside IO library cells. If they refuse, fill revision 6 on r8 (`chip-sfill6r8b-chk`, DRC 452) is the fallback; its 228 density results would then need their acceptance as waivers.

## Closed

- **ESD clamp poly direction (PO.R.5 4, PO.R.6 2, PO.W.2 2, SR_DPO.R.4 2).** `PCLAMPC_H_G` is the variant to rotate for the left and right ring sides; at R0 its gates ran horizontally (IO app note, chapter 16). r8 places `PCLAMPC_V_G`, which has the same outline and pins, at the same origins: chip-level build `chip-r8-b1`, clamp-cell LVS CORRECT, pad-to-clamp resistance within 0.04 Ω of before.
- **Power-cut ERC (floating.nxwell_float 4, floating.psub 8).** Each domain boundary had two abutting PRCUTA_G. r8 keeps the cut next to PVSS3AC_H_G (app note 9.8.3) and replaces the other with PFILLER20_G (`sar8_io_ring/layout_r2`). LVS CORRECT, flat LUP/ESD unchanged.
- **Density.** Fill revision 7 reports 0 for every density rule (fill revision 6 on r8: 228). [Fill record](chip_fill.md)
- **MATCH.WARN.1.** Closed in r6 by MATCHING (205;8) markers over the comparator's N and P arrays (`chip-match-b1-chk`: 1 to 0, PO.DN.16 0, PO.R.28 0; record `chip_matching.json`). The markers are in r8.

## Design deviation: comparator matching class

- **What:** the comparator (`sar_strongarm_t28_core`) is marked with normal MATCHING (205;8), not the MOS-array class ANARRAY_H / ANARRAY_M (255;20/21). So the array environment rules AN.R.79.2m, AN.R.79.5m and AN.R.80.2m are not checked on it.
- **Evidence:** `chip-match-h1`, a scratch overlay of the r5 stream with ANARRAY_H over the N array (input pair, NMOS latch, tail) and the P array (PMOS latch, resets). No OA view changed.

| Check under ANARRAY_H | Result |
| --- | --- |
| MATCH.WARN.1, PO.DN.16, PO.R.28 | 0 |
| AN.R.80.2m | 0 (no ANARRAY_M drawn) |
| AN.R.79.2m, OD density inside vs the 6 µm halo, limit 0.10 difference | **fails**: N array, die (409.74, 519.08)-(410.26, 520.94), 0.59 vs 0.24 (difference 0.348); P array, die (409.61, 521.17)-(410.39, 522.37), 0.50 vs 0.24 (difference 0.257) |
| AN.R.79.5m | not run; would likely fail, the P row is 0.23 µm from the N array |

- **Accepted risk:** per the deck's MATCH.WARN.1 text, mismatch may reach 3× the SPICE value. Against the extracted Monte Carlo of the v8 comparator (200 seeds, σ 12.05 mV, range −34.7 to +34.1 mV), that is about ±104 mV for an extreme die, 11.6 % of full scale.
- **Why it is accepted:** the offset is a static input offset, measured and subtracted off-chip (issue #12, digital correction). It costs input range, not linearity. A real fix means re-laying out the comparator inside the frozen core and rerunning all of Stage 6. The halo lies mostly where the fill policy keeps OD out on purpose, so fill cannot close it.
- **Decision:** the user, 2026-11-23 ("Add markers, write waiver").

## Cleared (confirm)

- **WITH_SEALRING_OPTION:WARNING:** 0 on every seal-ring view up to `layout_full_fill5_r8_seal` and on the filled chip.
- **DM1–DM9.R.1:** 0 since `layout_full_dc_fill5`, and 0 on the filled chip.
