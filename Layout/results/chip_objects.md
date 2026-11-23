# Chip-Level Objects and the Integrated Chip

2026-11-22, chenzc24/sar-adc-t28#12 and #18. The objects of the 9 x 9 IO ring plan that the partial chip assembly left undrawn are now their own cells in `SAR_ADC_T28_LAYOUT`, and `sar8_adc_chip/layout_full` integrates them with the remaining routes. Chip LVS against the full `chip_netlist` is CORRECT. [Record with every evidence ID, count and digest](chip_objects.json) · [Partial assembly](chip_assembly.md) · [Ring cell](io_ring_verification.json)

All object cells use die coordinates and sit at the origin, R0. Each was built under the layout lock by `Layout/design/chip_objects.py`, which guarded the ring, the core, the partial chip view and the register; every guarded `layout.oa` stayed byte-identical.

## Objects

| Cell | Content | Cell DRC (cell deck) | Cell LVS |
| --- | --- | --- | --- |
| `sar8_out_reg` (XOREG) | 8 x DEL250D1 -> DFQD1 -> BUFFD4 from `design/chip/output_register.scs`; Innovus place and route in the 40 x 40 um `output_register` region; DVDD (VDD) / VSS ring on M5/M6, 356 DCAP fillers | 6: density and the two advisory warnings | CORRECT, 19 ports |
| `sar8_esd_clamps` | Three PCLAMPC_H_G at `pclampc_analog/pair/sar`, M4 bars on VDDESD = AVDD_CORE and VSSESD = AVSS_CORE | 74: density, warnings, ESD.40.1g (40) and PO.R.5/6, PO.W.2, SR_DPO.R.4 (10), all inside the PCLAMPC_H_G master | CORRECT (the three clamps join on the chip trunks; the cell check names them with VIRTUAL CONNECT) |
| `sar8_decap_analog` | 2241 nmoscap, about 85 pF (plan 114) | 10: density, OD.S.14, warnings | CORRECT |
| `sar8_decap_pair` | 2950 nmoscap, about 112 pF (plan 114) | 3: density, warnings | CORRECT |
| `sar8_decap_sar` | 2752 nmoscap, about 105 pF (plan 132) | 30: density, OD.S.14, warnings | CORRECT |
| `sar8_decap_dvdd` | 1320 nmoscap, about 50 pF (plan 52) | 3: density, warnings | CORRECT |
| `sar8_core_vss_ring` | Four 4.0 um M7 strips, 0.5 um apart, band 113-130.5 / 629.5-647 um; M6 ties at 150 and 610 um on each side | 16: density, OD.S.14, warnings | no devices |
| `sar8_adc_guard_ring` | 2 um P+ ring (OD, PP, five contact rows, M1/M2 frames) on AVSS_CORE, outer edge on the `adc_guard_ring` outline, M1/M2 strap to the core's `0_guard` pin | 10: density, OD.S.14, warnings | no devices |

Pad decaps use the core's thin-oxide nmoscap (wr 2.5 um, lr 0.8 um; 38 fF each, from the drawn CREF of `layout_route_full`) in abutted rows, by the user's choice. An M3/M4 strap mesh, vertical M5 bars and an M6 collector per net form the series path to an M6 port pad under the trunk. Each side of a clamp keep-out joins the rest through the outermost bars.
- Capacitance: the analog and SAR regions also hold their PCLAMPC_H_G (100 x 22 um plus clearance), which the plan's 10 fF/um2 figures did not subtract. Their decaps are 85 and 105 pF against the planned 114 and 132 pF. The Stage 1 budget recommends about 100 pF per branch; the analog branch is 15 % below that.
- ESR: modelled per rail as the port neck (0.21 ohm) plus a resistor network of the collector and bars at 0.428 ohm/sq. Analog 2.4 / 2.4, pair 2.1 / 2.1, SAR 1.8 / 1.5, DVDD 1.8 / 2.3 ohm (supply / ground). The model leaves out the parallel M4 straps, so these values bound the ESR from above. Extraction is still to do.
- Core VSS ring width: DRM 9.3.4 (ESD.CD.1gU) gives 81.25 mA/um for Mx under a 100 ns TLP pulse, so the 1.3 A primary-path current needs 16 um of M7. Mx.W.3 limits a line to 4.5 um, hence four 4 um strips. The plan's 2 um placeholder band became 17.5 um, inside the 113-647 outline and 0.6 um clear of the routes' pad-landing band. The PVSS1DGZ and PVSS2AC stubs extend the pads' M1 and M2 fingers (21 um of Mx, 1.7 A) across the band, with via fields to every strip.

## Output register clocking and timing

User decision, 2026-11-22: every DFQD1 CP taps SAMPLE_CORE directly, with no clock buffer, and a DEL250D1 on each D input holds the captured word. The reason is that the SAR clears ADC_D on the same edge that clocks the register (D_i = CODE_i AND DONE, and DONE resets while SAMPLE is high). The register has no reset, so its word is undefined until the first SAMPLE rising edge. The CK pin sits on the north edge under the SAMPLE M8 route, which is tapped by a stack at x 512 um. Timing (managed runs on the Stage 2 all-extracted ADC): every code captured at SS cold and FF hot; worst setup slack 18.3 ns (SS cold), worst hold slack 0.50 ns (FF hot; 0.30 ns without the delay cell). [Register timing](output_register_timing.md)

## Integration: `sar8_adc_chip/layout_full`

Build `chip-full-b2` copies `sar8_adc_chip/layout` (left unchanged) and adds the eight object instances and these routes (`Layout/design/chip_integration.py`):
- ADC_D0-7: the core's M7 tracks continue 5.5 um over the guard ring into an M7-M3 stack beside the register's D pins.
- CK: the register's 0.05 um M4 CK pin, extended to an M4-M8 stack on SAMPLE.
- D0-D7_CORE: from the Q pins on M6 columns and M5 rows, as planned, onto the pads' M4 I pins.
- DVDD: a 3 um M6 route from the right_4 landing (inset 1.4 um from the pad edge) through the DVDD decap's port. It rises at x 524-528 um, 2-6 um west of the planned x 530, to clear the register's M6 ring, and lands on the register's VDD M5 ring.
- VSS_register: 2 um M7 from the register's VSS ring via x 540 and y 420, through the DVDD decap's VSS port, into the core VSS ring.
- VSS_digital and VSS_analog: the stubs described above.
- AVSS_guard: the left_0 landing to M9, 2 um M9 along x 116 and y 563, and a stack onto the guard ring's north-west corner.
- Decap ports and clamps: via stacks from the AVDD (M9) and AVSS (M8) trunks of the partial assembly onto the decap ports and the clamp bars. Pair clamp: M9 and M8 straps from AVDD_pair above and AVSS_pair below.

## Chip checks (`chip-full-b2-chk4`, `-chk5`)

| Check | `layout_full` | Partial assembly `layout` | Ring alone | Core alone |
| --- | --- | --- | --- | --- |
| DRC, installed chip deck (FULL_CHIP, WITH_SEALRING) | 2239 | 1234 | 1027 | 72 |
| of which density and fill (*.DN.*, OD.S.14) | 1988 | 981 | | |
| of which other rules | 251 | 253 | | |
| LVS against the full `chip_netlist` | CORRECT | CORRECT (no objects) | CORRECT (ring cell) | |
| ERC (same LVS run) | 302 | 302 | 334 (ring cell, `io_ring_verification.json`) | |

DRC by rule against the partial assembly (`chip_objects.json` `drc.by_rule`, with each marker's area):
- Removed: PO.R.19, 12 to 0. These are the ring's floating-gate results, cleared now that the D0-D7 pads' I pins are driven.
- New: PO.R.5 (4), PO.R.6 (2), PO.W.2 (2) and SR_DPO.R.4 (2). All of them lie inside the `pclampc_pair` PCLAMPC_H_G master: hierarchical DRC reports a master's own results once, and the clamp cell alone shows the same ten. No other rule is new.
- Unchanged: ESD.18g/19g/WARN.1 in the ring, and LUP.5.2.1 (1) and LUP.5.2.2 (6) at the Bootstrap-N VIN switch (a block-core change, still open). These are hierarchical counts; see the flat check below. The whole-die advisories (DM*.R.1, WITH_SEALRING_OPTION, IO_CONNECT_CORE_NET, MATCH.WARN.1) also appear on the ring alone and the core alone.
- Density and fill: +1007, mostly M7.DN.6 (120 to 824) and M6.DN.6 (124 to 398). These are low-density (<1 %) M6/M7 fragments over the pad decaps and the VSS-ring ties, where the decaps use M1-M5 only, plus M7.DN.3 (2) at the ring's density step. They are for the fill owner (`Layout/specs/fill-policy.md`).

Flat LUP/ESD check. Hierarchical chip DRC under-reports net-based rules, as the partial assembly's session found. So the chip deck was also run flat with only its 72 LUP.* and ESD.* rule checks selected (LUP.WARN.1 sits in an inactive block). Runs `chip-full-b2-flat-lupesd4` and `chip-asm-a3-flat-lupesd4`:

| Rule | `layout_full` | `layout` |
| --- | --- | --- |
| ESD.18g | 540 | 540 |
| ESD.19g | 432 | 432 |
| ESD.WARN.1 | 6 | 6 |
| LUP.5.2.1 | 2 | 2 |
| LUP.5.2.2 | 12 | 12 |

The objects add no latch-up or ESD result. LUP.5.2.x is 1 + 6 on each Bootstrap, as in that session's flat probe. ESD.40.1g, which the clamp cell shows alone, does not appear on the chip: the three clamps share AVDD_CORE, so their total finger width meets the rule.

LVS: ports 31 / 31, nets 1536 / 1536 after transformation, 10140 nmoscap / 10140, with the core's block masters as HCELLs. With VIRTUAL CONNECT NAME limited to the eight supply nets (AVDD, AVDD_CORE, AVSS, AVSS_CORE, VSS, VSSIO, VDDIO, DVDD), the result is again CORRECT with the same ERC (`chip-full-b2-lvs-vcs2`). So ADC_D0-7, D0_CORE-D7_CORE and the CK tap on SAMPLE_CORE are physically connected, not only joined by name. The same source passes again with the decaps and the register as HCELLs too (`-chk5`). The source is `Layout/design/chip_full_source.py` on the partial assembly's source, adding XOUT_REG, XESD_CLAMPS and XDECAP_*, plus the DFQD1/BUFFD4 bodies from the foundry SPICE. The deck lines are the partial assembly's (`chip_physical.py`: VIRTUAL CONNECT NAME "?", the ring deck's power and ground names).

ERC: identical by check to the partial assembly (mnpg 280, npvss49 12, floating.nxwell_float 6, floating.psub 4), so the objects add no ERC result. Against the ring cell's 334, the difference is 32 fewer floating.nxwell_float results, as in the partial assembly. The rest are inside TSMC IO cells and depend on the net names, as recorded and waived for the ring cell.

## Chip on the r2 Bootstrap: `sar8_adc_chip/layout_full_boot_r2`

Build `chip-bootr2-b1` is the same build as `layout_full` (`chip_integration.py --view layout_full_boot_r2 --core-view layout_route_boot_r2`). The only change is the copied XADC instance, now placed at the same origin on `sar8_adc_core/layout_route_boot_r2`: `layout_route_guard` with both Bootstraps on the r2 filled Bootstrap (routing session, same interface). The build left `layout_full`, `layout` and both core views byte-identical. The LVS source comes from the same flow on that core's source (`adc-core-bootr2-lvs1`), and the flow reproduces the partial assembly's source byte for byte. Its Bootstrap reference has the same digest as before; only the evidence name differs.

| Check (`chip-bootr2-b1-chk`, `-flat-lupesd`, `-lvs-vcs`) | `layout_full_boot_r2` | `layout_full` |
| --- | --- | --- |
| DRC, installed chip deck | 2231 | 2239 |
| of which other than density and fill | 244 | 251 |
| LUP.5.2.1 / LUP.5.2.2, hierarchical | 0 / 0 | 1 / 6 |
| LUP.5.2.1 / LUP.5.2.2, flat | 0 / 0 | 2 / 12 |
| ESD.18g / 19g / WARN.1, flat | 540 / 432 / 6 | 540 / 432 / 6 |
| LVS against the full `chip_netlist` (ports, nets) | CORRECT (31, 1536) | CORRECT (31, 1536) |
| LVS joining only the supply nets by name | CORRECT | CORRECT |
| ERC | 302, identical by check | 302 |

Every other rule is unchanged, apart from two density rules: OD.S.14 23 to 21 and PO.DN.3 11 to 12. The r2 Bootstrap clears the latch-up results at both VIN switches. It is still being qualified electrically in the Bootstrap session.

## Pad decaps at plan and the filled core: `sar8_adc_chip/layout_full_dc_fill5`

Revision 2 of the decap and clamp cells (`layout_r2` views; the `layout` views are unchanged), user-approved through the coordinator session. Each decap grows in its own branch's region to its planned capacitance, with the same thin-oxide nmoscap and mesh. `io_ring.json` now shows the drawn regions. [Geometry](../design/chip_objects_geometry.py) `DECAPS_R2`, `CLAMP_ORIGIN`

| Decap | Region (die um) | Devices | Drawn | Plan | ESR per rail, supply / ground (model) |
| --- | --- | --- | --- | --- | --- |
| analog | (326, 576)-(494, 646.5), whole region | 3048 | 115.8 pF | 114.2 | 1.81 / 1.78 ohm |
| pair | (370, 300)-(452, 442) | 3050 | 115.9 pF | 113.6 | 1.87 / 1.83 ohm |
| SAR | (510, 528)-(646.5, 646.5), minus the SAR clamp | 3543 | 134.6 pF | 132.2 | 1.66 / 1.88 ohm, two ports per net |
| DVDD | (578, 340)-(640, 426) | 1380 | 52.4 pF | 51.6 | 1.87 / 2.21 ohm |

- **Analog clamp moved (superseded by revision 3 below: this place puts the clamp away from its own pads, against app note 8.7.3 step 2).** Between the VIN routes the analog decap reaches at most 87 pF with its clamp in place. Nothing outside the VINN/VINP pair can join the analog trunk without crossing VIN. So the analog PCLAMPC_H_G moved to (230, 279), beside the pair clamp, and is fed by straps from the pair trunks the same way. There are still three clamps on AVDD_CORE/AVSS_CORE. The analog pads now reach their nearest clamp, the SAR clamp, over about 3 (AVDD) and 6 (AVSS) pad pitches of the TACVDD/TACVSS bus, roughly 0.45 / 0.9 ohm at 25 C by the constraints.json bus model.
- **SAR** grows west to x 510, 9.5 um from the VINP route edge. The plan's minimum is 6 um; its earlier text said 30.
- **Ports** sit next to the ADC pins, with the ground (M8) port nearest. On the SAR side, short stubs north from the SAR trunks reach the near-pin ports, and the revision 1 ports stay in parallel. The ESR model is the one above, an upper bound. Ring feed, as a loop at 125 C rcworst_T, drawn vs the plan's 10 um M8 values:
  - pad to pin: analog 0.53 (0.73), pair 2.34 (2.85), SAR 1.61 (1.45) ohm;
  - bulk to pin: analog 0.14 (0.10), pair 0.12 (0.04), SAR 0.49 (0.63) ohm.
  
  The analog and pair excess comes from the trunks' 6 um and 2 um necks at the pins (the pair's AVSS neck alone is 0.04 ohm). The SAR pad-to-pin excess comes from the 4 um AVSS segment above SAMPLE. All feeds stay far below the 6 ohm loop limit; analog including its in-core loop is 3.65 + 0.14 ohm.
- **Cell checks:** every revision 2 cell is LVS CORRECT. DRC shows density and advisories only, apart from the results inside the PCLAMPC_H_G master. M6.DN.6 grows where the ports left the middle of the decaps, which is for the fill owner.

The chip view is built like `layout_full_boot_r2` (build `chip-dcf5-b1`): XADC is the fill session's final filled core, `sar8_adc_core_filled/layout_fill5` (wrapper with XCORE = `layout_route_boot_r2` at its origin), and the objects use their `layout_r2` views. All guarded views stayed byte-identical. Checks are by rule against `layout_full_boot_r2`:

| Check | `layout_full_dc_fill5` | `layout_full_boot_r2` |
| --- | --- | --- |
| DRC, installed chip deck (`chip-dcf5-b1-chk`) | 1623 | 2231 |
| of which other than density and fill | 236 | 244 |
| LUP.5.2.1 / 5.2.2, flat (`-flat-lupesd`) | 0 / 0 | 0 / 0 |
| ESD.18g / 19g / WARN.1, flat | 540 / 432 / 6 | 540 / 432 / 6 |
| LVS, full `chip_netlist` (`-lvs2`: ports, nets, nmoscap) | CORRECT (31, 1536, 11898) | CORRECT (31, 1536, 10140) |
| LVS, only supply nets joined by name (`-lvs-vcs2`) | CORRECT | CORRECT |
| ERC | 302, identical by check | 302 |

DRC by rule: the eight whole-die DMn.R.1 advisories clear with the filled core; no rule is new. Density falls by 600 markers, mostly M7.DN.6 (824 to 417) and M6.DN.6 (398 to 253).

The first LVS of this view (in `chip-dcf5-b1-chk`) was INCORRECT. Its source wired the revision 2 clamps and the analog and pair decaps backwards: their subcircuits list AVSS first, but the chip source connected the ports in a fixed order. `chip_full_source.py` now connects object ports by name, and the revision 1 source is byte-identical. The reruns above use the corrected source.

## Analog clamp back in place: `sar8_adc_chip/layout_full_fill5_r3`

Revision 3 fixes the ESD fault of revision 2. Revision 2 had put the analog clamp beside the pair clamp, away from its own pads, against app note 8.7.3 step 2: the clamp sits between its pad pair and the core. The analog PCLAMPC_H_G now returns to (360, 622) on the analog trunks, between top_3/top_4 and the core (the `sar8_esd_clamps/layout` view).
- **Trunk resistance from the pads to the clamp,** 125 C rcworst_T: AVDD (top_4) 0.02 ohm and AVSS (top_3) 0.06 ohm. In revision 2 it was 0.57 and 0.95 ohm over the TACVDD/TACVSS bus.
- **Correction:** this record first compared these values with 1 ohm from Table 10.1. That table limits the bus resistance between IO power/ground cells, not pad to clamp; see "Clamp feed along the bars".

With the clamp back in its region, the analog decap cannot reach its plan. The new `sar8_decap_analog/layout_r3` recovers what it can:

| Part | Drawn |
| --- | --- |
| nmoscap, wr 2.5 / lr 0.8 um | 2289 devices, 87.0 pF |
| M5-M7 MOM (cfmom_2t) between the M5 bars, 13 um pitch | 37 tiles, 2529 um2, 5.9 pF |
| total | **92.9 pF** (plan 114.2; revision 1 85.1) |
| ESR per rail, model | 2.28 / 2.21 ohm (AVDD / AVSS) |

- **MOM** is the PDK's minimum three-layer stack (M5-M7, 0.79 fF/um2 per layer by the PDK callback: 151.6 fF for nr 120, lr 5 um). It sits above the M6 collectors and below the core VSS ring's M7 band (y 629.5), and clear of the clamp and its trunk drops. Each tile spans three (or one) nmoscap rows, with its M5 bus bars on the M4 straps of the rails at its ends via VIA4. Cell LVS recognises all 37 as cfmom_2t (CORRECT).
- **A larger nmoscap unit does not fit.** lr 1.0, 0.9 and 0.85 um (pitch lr + 0.5) all break PO.DN.4.1, the 65 % local poly limit (PDK cmax 47.2 / 42.6 / 40.3 fF against 38.0 fF), and lr 0.8 is already close to it.
- **Cell DRC** shows density and the two advisories only.

The chip view is built like `layout_full_dc_fill5` (build `chip-f5r3-b1`, `chip_integration.py --objects-rev 3`): the filled core `layout_fill5`, the clamps in `layout`, the analog decap in `layout_r3`, and the other decaps in `layout_r2`. All guarded views stayed byte-identical. By rule against `layout_full_dc_fill5`:

| Check | `layout_full_fill5_r3` | `layout_full_dc_fill5` |
| --- | --- | --- |
| DRC, installed chip deck (`chip-f5r3-b1-chk`) | 1484 | 1623 |
| of which other than density and fill | 236 | 236 |
| LUP.5.2.1 / 5.2.2, flat | 0 / 0 | 0 / 0 |
| ESD.18g / 19g / WARN.1, flat | 540 / 432 / 6 | 540 / 432 / 6 |
| LVS, full `chip_netlist` (ports, nets) | CORRECT (31, 1536) | CORRECT (31, 1536) |
| LVS, only supply nets joined by name | CORRECT | CORRECT |
| ERC | 302, identical by check | 302 |

Only density counts change: M7.DN.6 417 to 303 and M6.DN.6 253 to 233, because the MOM fills M5-M7 over the analog decap.

## Seal ring: `sar8_adc_chip/layout_full_fill5_r3_seal`

The die is the lab's 1 x 1 mm seal ring, `sealring/N28_TSMC_SRDMB_Mu/layout` from the shared seal-ring library (not drawn here), placed at die (-120, -120), R0, by `Layout/design/chip_seal_ring.py` (build `chip-seal-b1`). The view is a copy of `layout_full_fill5_r3` with only that instance added. All 16 guarded views (every chip view, the ring, the cores and the object views) stayed byte-identical. `io_ring.json` `seal_ring` and `die_bbox` (-120, -120)-(880, 880) and `floorplan.json` `die_bbox` record it.

| Clearance (die um) | |
| --- | --- |
| Seal-ring band (SEALRING_ALL 162;2) | 24 um from the die edge: -120 to -96 and 856 to 880 |
| Corner chamfers | within x + y <= 121.72 um of each die corner (seal-ring frame); the IO corner cells start at x + y = 240 |
| IO-cell outline | 0 to 760, 120 um from each die edge |
| PAD60GU metal (783.32 um envelope) | 108.34 um from the die edge, 84.34 um clear of the band |

By rule against `layout_full_fill5_r3`:

| Check | `layout_full_fill5_r3_seal` | `layout_full_fill5_r3` |
| --- | --- | --- |
| DRC, installed chip deck (`chip-seal-b1-chk`) | 1944 | 1484 |
| of which other than density and fill | 235 | 236 |
| LUP.5.2.1 / 5.2.2, flat (`chip-seal-b1-flat-lupesd`) | 0 / 0 | 0 / 0 |
| ESD.18g / 19g / WARN.1, flat | 540 / 432 / 6 | 540 / 432 / 6 |
| LVS, full `chip_netlist` (ports, nets) | CORRECT (31, 1536) | CORRECT (31, 1536) |
| LVS, only supply nets joined by name (`chip-seal-b1-lvs-vcs`) | CORRECT | CORRECT |
| ERC | 305 | 302 |

- **Non-density:** the only change is that `WITH_SEALRING_OPTION:WARNING` (the chip deck's missing-seal-ring warning) is gone.
- **Density and fill:** +461, in the empty margin between the IO ring and the seal ring, which has no fill yet:
  - M1-M7.DN.1: 1 to 5 each.
  - M1-M6.DN.6: +33 to +153 each.
  - OD.S.14 (at most 10 um between OD): 16 to 27.
  - The seal ring's own dummy OD and poly lower OD.DN.3 (19 to 3) and PO.DN.3 (10 to 2).
- **ERC:** no new location. Both runs flag the same floating P-substrate and N-well pieces at the two PRCUTA_G domain cuts (die y 225-235 on the west edge, y 585-595 on the east edge). The seal-ring run also lists three of them under the ring cell's context. The seal ring adds no ERC result.

Fill keep-out, agreed with the fill session:
- No dummy fill outside die (-93, -93)-(853, 853), which is the band plus 3 um (CSR_DMu_S_1).
- No fill within x + y <= 125 um of the die corners.
- Everything else outside the IO ring is open to fill.
- The fill goes into the fill session's own wrapper `sar8_adc_chip_filled`, which places the current chip view `layout_full_fill5_r4_seal` unchanged and uses the `chip-cfeed-b1-chk` stream. Its other exclusions are the IO cells, the filled core, the clamps (the pair clamp to (120, 255)-(220, 325), with its new straps) and the VIN routes ±1 um.

## Periphery extraction ([record](chip_periphery.json))

**Extraction setup.** `Layout/tools/analysis/chip_periphery.py` runs Calibre xRC on the `layout_full_fill5_r3_seal` stream (extraction `chip-periph-x1`: typical, 25 C, coupling capacitance grounded).
- **Kept as xcells:** every IO-library cell, the core, the register, the decaps, the PCLAMPC_H_G clamps and the seal ring.
- **Extracted as RC:** the chip-level wiring, ending on the xcell pins, including the bond-pad metal and the AVDD/VDD nets the deck normally keeps ideal.
- **Analysis:** each node set's two-point resistance on the extracted network, with the other attachments floating.
- **Not covered:**
  - Inductance (xRC gives none; the L below is a straight-bar estimate).
  - The insides of the xcells.
  - Fill, of which the chip margin and pad decap areas have none yet, so wiring C will rise.

**Pad cell capacitance.** It is taken from the pad's LVS netlist (IO library SPICE: PDB3AC has 15 ndio_18 and 5 pdio_18). The PDK junction models are applied at TT and at the node voltage, with AVDD at 0.9 V.

Reference rails against `constraints.json` `stage6_supply_model` (per rail, both pads):

| Term | Model | VREFP | VREFN |
| --- | --- | --- | --- |
| Route R, both routes in parallel | 0.85 ohm (0.14-1.2) | 1.08 ohm (routes a/b 2.12 / 2.23) | 1.09 ohm (1.93 / 2.52) |
| Route R at 125 C rcworst (M8 scaling) | 1.2 ohm | about 1.53 ohm | about 1.54 ohm |
| Route L | 0.17 nH | 0.16 nH (estimate) | 0.16 nH (estimate) |
| Route C | 0.27 pF | 0.066 pF | 0.075 pF |
| Pad C, two pads | 2 x 0.5 pF | 2 x (1.02 junction + 0.075 bond metal) = 2.19 pF | 2 x (1.09 + 0.075) = 2.34 pF |

- **Route resistance:** within the model's range at 25 C and inside the 0-2 ohm bracket at 125 C.
- **Route capacitance:** a quarter of the model's (M8 over an unfilled field).
- **Pad capacitance:** more than twice the model's 0.5 pF per pad, dominated by the ESD diodes.

Supply ring feeds, loop AVDD + AVSS (pad = the pad cell's core pin, bulk = the decap port, pin = the ADC pin):

| Branch | Pad to pin, extracted 25 C (125 C scaled) | Hand count 25 C / 125 C | Bulk to pin, extracted (scaled) | Hand count 125 C | Pad to clamp, AVDD / AVSS (25 C) |
| --- | --- | --- | --- | --- | --- |
| Analog | 1.63 (2.36) ohm | 0.37 / 0.53 | 1.77 (2.58) ohm | 0.14 | 1.10 / 1.08 ohm |
| Pair | 2.68 (3.85) ohm | 1.64 / 2.34 | 1.60 (2.32) ohm | 0.12 | 1.11 / 1.11 ohm |
| SAR | 2.05 (2.95) ohm | 1.13 / 1.61 | 1.16 (1.67) ohm | 0.49 | 1.11 / 1.10 ohm |

- **Hand counts are low.** The `ring_feed()` values were trunk squares only. The extraction includes the pad landings and the via stacks (two VIA7 and two VIA8 per stack at the decap ports and the clamp drops), which carry most of the resistance.
- **Rail budget still passes** with the extracted feeds: worst 20.3 mV against 45 mV ([chip rail recheck](chip_rail_recheck.md)).
- **Pad to clamp is 1.08-1.11 ohm per rail at 25 C** in this run, and 1.19-1.79 ohm with the clamps flattened; the trunk-only estimate gave 0.02-0.06 ohm. The app note sets no resistance limit on this connection for wire bond. Its ESD current-density check, and the fix for the clamp bars, are in "Clamp feed along the bars" below.

VIN and output path (25 C typical):

| Path | R | Wiring C | Pad cell |
| --- | --- | --- | --- |
| VINP / VINN, pad AIO to core VIN pin | 56.6 ohm each (1 um M5 + M6, 0.3 um neck) | 16 fF route + 75 fF bond-pad metal | PDB3AC_V_G, 1.09 / 1.03 / 1.02 pF at 0 / 0.45 / 0.9 V |
| ADC_D0-7, core to register D | 26.4 ohm | 0.2 fF | |
| D0_CORE-D7_CORE, register Q to pad I | 249-559 ohm (0.4 um M5/M6) | 15-27 fF | PRUW08SDGZ_H/V_G |
| D0-D7, pad to bond pad | 0.02 ohm | 75 fF | |
| SAMPLE_CORE, pad C to core / register CK | 19.1 / 37.0 ohm | 16 fF | PDDW16SDGZ |
| Register DVDD from the DVDD pads | 21.7 ohm (DVDD decap tap 5.6 ohm from the pads) | | |

The register's VSS return is not resolved, because the extraction joins every xcell's VSS at one substrate node.

Stage 2 has two netlists in `work/layout/chip-periphery/chip-periph-x1/stage2/` (sha256 in the record):
- `sar8_vin_path.scs`: the PDB3AC pad cells plus the extracted VIN routes and bond-pad metal.
- `sar8_output_path.scs`: the register, the eight PRUW08SDGZ and the SAMPLE PDDW16SDGZ, their extracted routes, and the DVDD star with the DVDD decap. It also has `sar8_output_board`: 0.2 ohm + 2 nH package and a stated 15 pF board load per data pad.

## Clamp feed along the bars: `sar8_adc_chip/layout_full_fill5_r4_seal`

**The rule.** For wire bond, the IO app note (8.7.3 and 10.7.3) asks for three things:
- The clamp sits between its analog pad pair and the core.
- AVDD connects to VDDESD and AVSS to VSSESD, then on to the core rails.
- Every such connection meets the DRM's "Maximum ESD Current Density for Via, and Metal". That is DRM 9.3.4, and ESD.CD.1gU suggests 1.3 A on the primary path from the bond pad to the clamp: 81.25 mA/um of Mx, 26.2 mA per VIA4-VIA6 cut, 246.7 mA per VIA7/VIA8.

The note sets no pad-to-clamp resistance limit for wire bond.
- An earlier version of this record compared pad-to-clamp resistance with 1 ohm from Table 10.1. That table (section 10.4) limits the bus resistance between IO power/ground cells of one analog domain, cell to cell along the ring.
- The only pad-to-clamp limit, 0.1 ohm (12.3.1), is for RDL flip chip.

**The fault: three drops per rail.** Each clamp's M4 bar was fed by three stacks at one place, so about seven of the clamp's nine terminal strips per net hung on one side of the drop. With the clamp current split equally over the strips, the bar carried up to 1.0 A sideways:

| Clamp, AVDD / AVSS | M4 bar | Worst bar current, three drops | ESD.CD.1gU for the bar | With the clamp feed |
| --- | --- | --- | --- | --- |
| Analog | 3.0 um | 1.01 / 1.01 A | 0.24 A | 0.15 / 0.14 A |
| Pair | 4.4 um | 0.43 / 0.43 A | 0.36 A | 0.14 / 0.14 A |
| SAR | 4.4 um | 1.01 / 0.87 A | 0.36 A | 0.18 / 0.14 A |

- **Vias:** the three drops met the via counts with no margin: 6 VIA7 (and 6 VIA8 on AVDD) per rail against 6 needed, and 72 cuts per VIA4-VIA6 level against 50.
- **Model:** `chip_objects_record.clamp_feed_current_density`, recorded in `chip_objects.json` `esd_current_density`.

**The fix.** `Layout/design/chip_clamp_feed.py` (build `chip-clampfeed-b1`; geometry in `chip_integration.clamp_feed`) copies `layout_full_fill5_r3_seal` and adds:
- a strap on the trunk metal over every bar (AVDD on M9, AVSS on M8);
- a drop stack every 6 um along it (M4-M7 via fields, VIA7/VIA8 pairs);
- for the pair clamp, straps every 10 um to its trunks.

The stacks keep clear of the core VSS ring's M7 band and M6 ties, the other net's trunk, and the existing drops. That gives 15-19 stacks per rail instead of 3. The clamp cells and all other views are unchanged.
- **Bar current:** 0.14-0.18 A in the worst segment, within the bar's ESD.CD.1gU current.
- **Vias:** 30-38 VIA7 per rail and 360-456 cuts per VIA4-VIA6 level, five to nine times the counts.

**Resistance, for information.** No limit applies to it. The extraction with the clamps flattened (`chip-periph-x2`, `chip-periph-x3`) includes the clamp's metal and transistors (Calibre xRC typical, 25 C):
- **pin:** resistance to the clamp's transistor terminals, all shorted.
- **distributed:** the clamp current drawn by its transistors in proportion to their width; includes the clamp's own metal down to each finger.

| Clamp, rail | `layout_full_fill5_r3_seal`, pin / distributed | `layout_full_fill5_r4_seal`, pin / distributed |
| --- | --- | --- |
| Analog, AVDD (top_4) | 1.26 / 1.32 ohm | 0.76 / 0.80 ohm |
| Analog, AVSS (top_3) | 1.73 / 1.79 ohm | 0.92 / **0.94** ohm |
| Pair, AVDD (left_5) | 1.19 / 1.26 ohm | 0.77 / 0.81 ohm |
| Pair, AVSS (left_6) | 1.20 / 1.22 ohm | 0.78 / 0.80 ohm |
| SAR, AVDD (top_1) | 1.20 / 1.25 ohm | 0.75 / 0.79 ohm |
| SAR, AVSS (right_8) | 1.41 / 1.46 ohm | 0.82 / 0.84 ohm |

- **The feed cuts the resistance by about 40 %:** worst 1.79 to 0.94 ohm.
- **Bar spreading is small:** pin and distributed differ by only about 0.05 ohm.
- **What remains** is mostly the pad landing and the trunk.

**Pad landings** against ESD.CD.1gU: the AVSS landings used only the pads' M2 fingers (0.85 A). Revision 5 below adds their M1 fingers.

By rule against `layout_full_fill5_r3_seal`:

| Check | `layout_full_fill5_r4_seal` | `layout_full_fill5_r3_seal` |
| --- | --- | --- |
| DRC, installed chip deck (`chip-cfeed-b1-chk`) | 1912 | 1944 |
| of which other than density and fill | 235 | 235 |
| LUP.5.2.1 / 5.2.2, flat (`chip-cfeed-b1-flat-lupesd`) | 0 / 0 | 0 / 0 |
| ESD.18g / 19g / WARN.1, flat | 540 / 432 / 6 | 540 / 432 / 6 |
| LVS, full `chip_netlist` (ports, nets) | CORRECT (31, 1536) | CORRECT (31, 1536) |
| LVS, only supply nets joined by name (`chip-cfeed-b1-lvs-vcs`) | CORRECT | CORRECT |
| ERC | 305, identical by check | 305 |

Only density counts change: M6.DN.6 386 to 362 and M7.DN.6 287 to 279, from the new M6/M7 plates. The record is in [chip periphery](chip_periphery.json) `clamp_bus` (extractions `chip-periph-x2`, `chip-periph-x3`).

## AVSS pad landings on M1: `sar8_adc_chip/layout_full_fill5_r5_seal`

ESD current leaves each supply pad through its core-pin fingers, and the landing that joins them is the first metal of the pad-to-clamp path. ESD.CD.1gU asks 16 um of Mx for its 1.3 A (`chip_objects_record.landing_current_density`, in `chip_objects.json` `esd_current_density`):

| Pad | Core pin | Landing before | Landing in r5 |
| --- | --- | --- | --- |
| AVSS (PVSS3AC: top_3, left_6, right_8, left_0) | seven M1 + seven M2 fingers, 10.5 um each | M2 only: 10.5 um, 0.85 A | M1 + M2: 21 um, **1.71 A** |
| AVDD (PVDD3AC: top_4, left_5, top_1) | ten M2 fingers, 14.1 um, nothing on M1 | 14.1 um, 1.15 A | unchanged |

- **AVDD** stays at 1.15 A. The 14.1 um of M2 is the IO cell's own core pin, rated by the library, and lies outside our wiring; the landing already uses all of it.
- **Build:** `Layout/design/chip_landing_m1.py` (build `chip-landm1-b1`; geometry in `chip_integration.avss_landing_m1`) copies `layout_full_fill5_r4_seal`, which stays unchanged.
- **Added at each AVSS landing:** the seven M1 finger extensions over the M2 ones, an M1 bar under the landing's 1 um M2 bar, and a VIA1 grid under its VIA2 grid (78 cuts per pad, 2.0 A). That is 344 shapes, M1 and VIA1 only, in four boxes in the landing band (die um):
  - top_3: (432.14, 649.0)-(447.86, 650.2)
  - left_6: (109.8, 252.14)-(111.0, 267.86)
  - right_8: (649.0, 612.14)-(650.2, 627.86)
  - left_0: (109.8, 612.14)-(111.0, 627.86)

By rule against `layout_full_fill5_r4_seal`:

| Check | `layout_full_fill5_r5_seal` | `layout_full_fill5_r4_seal` |
| --- | --- | --- |
| DRC, installed chip deck (`chip-landm1-b1-chk`) | 1912, every rule equal | 1912 |
| of which other than density and fill | 235 | 235 |
| LUP.5.2.1 / 5.2.2, flat (`chip-landm1-b1-flat-lupesd`) | 0 / 0 | 0 / 0 |
| ESD.18g / 19g / WARN.1, flat | 540 / 432 / 6 | 540 / 432 / 6 |
| LVS, full `chip_netlist` (ports, nets) | CORRECT (31, 1536) | CORRECT (31, 1536) |
| LVS, only supply nets joined by name (`chip-landm1-b1-lvs-vcs`) | CORRECT | CORRECT |
| ERC | 305, identical by check | 305 |

Pad to clamp, for information (clamps flattened, `chip-periph-x4`; distributed): the AVSS rails fall by about 0.1 ohm, and AVDD is unchanged.

| Rail | r4_seal | r5_seal |
| --- | --- | --- |
| Analog AVSS | 0.94 ohm | 0.83 ohm |
| Pair AVSS | 0.80 ohm | 0.70 ohm |
| SAR AVSS | 0.84 ohm | 0.74 ohm |
| AVDD (all three) | 0.79-0.81 ohm | 0.79-0.81 ohm |

This is the frozen chip view for fill. Its stream is `chip-landm1-b1-chk/fixture.gds`, sha256 7b2973da…

## MOS matching check on the comparator (MATCH.WARN.1) ([record](chip_matching.json))

**Why.** The chip DRC of `layout_full_fill5_r5_seal` flags MATCH.WARN.1: the stream has no MATCHING (205;8), ANARRAY_H (255;20) or ANARRAY_M (255;21) marker. Without one, PO.DN.16, PO.R.28, AN.R.79.2m and AN.R.80.2m never run. The DRM allows that bypass only when no circuit depends on MOS matching, but the StrongARM comparator's offset does.

**Marker.** ANARRAY_H (high matching).
- **Basis:** DRM 8.3.2.3.1.1. High matching is for "MOS array with mismatch within SPICE"; medium allows 2x SPICE; normal (MATCHING) is for "two simple identical transistors". The comparator's offset is reported from native PDK Monte Carlo, i.e. at SPICE mismatch.
- **Placement:** each marker covers one MOS array. Its edge sits at the centreline between the outermost active gate and its SR_DPO dummy, or at the well-strap centreline. The matched pairs share diffusion and interleave, so the arrays are the unit (comparator frame, `Layout/design/comparator.il`):

| Array | Marker (um) | Matched groups inside |
| --- | --- | --- |
| N (rows N1/N2, P+ ring) | (-0.26, -2.53)-(0.26, -0.67) | input pair MNINP/MNINN (two cross-placed fingers each); NMOS latch MNLATN/MNLATP; the tail MNTAIL sits between the input fingers |
| P (row P, N+ ring) | (-0.39, -0.44)-(0.39, 0.76) | PMOS latch MPLATN/MPLATP; output reset MPRSTN/MPRSTP; internal-node reset MPRSTX/MPRSTY |

**Run.** `chip-match-h1` (`Layout/tools/physical/matching_overlay.py`).
- **Stream:** a scratch copy of the r5 stream (`chip-landm1-b1-chk`, sha256 7b2973da…) with the two markers in `sar_strongarm_t28_core` only. No OA view or frozen stream changed.
- **Checks:** the installed chip deck, hierarchical, with only the five checks selected.
- **Host:** thu-wei. The managed runner has no DRC job kind, so its admission rule was applied by hand: 28 GiB available against 2 GiB for this job, 8 GiB reserve and up to 16 GiB for the two running Stage 6 runs; 40 of 96 threads; load 79 against 120.

| Check | Results |
| --- | --- |
| MATCH.WARN.1 | 0 (markers present) |
| PO.DN.16 (PMET-poly density at most 50 % within 10 um) | 0 |
| PO.R.28 (high-poly-density regions at most 60 um within 10 um) | 0 |
| AN.R.79.2m (ANARRAY_H: OD and PO density within 10 % between the array and its 6 um halo) | **2** |
| AN.R.80.2m (ANARRAY_M) | 0 (no ANARRAY_M drawn) |

Both AN.R.79.2m results are OD density; PO density is within 10 % for both arrays.

| Array (die um) | OD density inside | OD density in the 6 um halo | Difference |
| --- | --- | --- | --- |
| N: (409.74, 519.08)-(410.26, 520.94), input pair, NMOS latch, tail | 0.591 | 0.243 | 0.348 |
| P: (409.61, 521.17)-(410.39, 522.37), PMOS latch, resets | 0.500 | 0.243 | 0.257 |

- **Medium class:** AN.R.80.2m uses the same formula and limits (10 %, 6 um), so ANARRAY_M markers would fail the same way.
- **Normal class:** MATCHING markers switch on only PO.DN.16 and PO.R.28, which pass.
- **Not run:** AN.R.79.5m (one MOS type in each high-matching array and its halo) was outside this run. By its wording, the P row 0.23 um above the N array puts both MOS types in either array's halo.

**Fix geometry, not drawn.** The two arrays share one halo, so its OD density must sit within 10 % of both: 0.49-0.60, against 0.24 now. That means a ring of identical dummy MOS rows around the comparator, 6 um wide per the DRM high-matching guidance, at the arrays' 0.13 um gate pitch and 0.5 um OD rows. The ring covers die x 403.6-416.4, y 513.1-528.4: inside the frozen core.

### Decision: MATCHING markers and a recorded deviation (2026-11-23)

The user chose option A: "Add markers, write waiver". The sign-off stream carries permanent MATCHING (205;8) markers. Option B (identical-dummy ring, N/P array split, comparator re-layout for ANARRAY_H) is rejected, and the comparator geometry stays as it is.

- **Class: normal matching.** MATCHING is for "two simple identical transistors" (DRM 8.3.2.3.1.1).
  - **What it switches on:** in the chip deck, PO.DN.16, PO.R.28 and AN.R.78.1m (strap width at most 0.5 um inside the marker), the marker's own geometry checks G.1-G.3, and MATCH.WARN.1.
  - **What it doesn't:** AN.R.79.x and AN.R.80.x read only ANARRAY_H / ANARRAY_M. CSR.R.1:MATCHING only runs without WITH_SEALRING.
- **Deviation from high matching:** the ANARRAY_H evidence is `chip-match-h1`.
  - AN.R.79.2m fails on OD density: 0.348 (N array) and 0.257 (P array), against 0.10.
  - AN.R.79.5m (one MOS type per array and halo) would fail as well, because the P row is 0.23 um from the N array.
- **Accepted risk:** MATCH.WARN.1 says matching may degrade "at least by 3X" when those rules are not met. The accepted figure is up to 3x the SPICE mismatch, applied to the extracted Monte Carlo ([comparator](comparator.md): sigma 12.05 mV, 200-seed range -34.7 to +34.1 mV).
  - The offset is static and corrected off-chip, so the cost is input range, not accuracy.
  - At 3x, an extreme die sits at about +/-104 mV, 11.6 % of the +/-0.9 V full scale.
- **Stage 6 is unaffected:** `calibre.lvs` and `calibre.rcx` map no 205;8 (only 205;6, PMET), so neither device recognition nor extraction reads the marker. The comparator, the cores and their streams are unchanged.

**Sign-off view: `sar8_adc_chip/layout_full_fill5_r6_seal`.**
- **Build:** `Layout/design/chip_matching_marker.py` (build `chip-match-b1`) copies `layout_full_fill5_r5_seal`, which stays unchanged.
- **Markers:** two MATCHING rectangles in the chip top cell, at the `chip-match-h1` footprints:
  - N array: (409.74, 519.08)-(410.26, 520.94)
  - P array: (409.61, 521.17)-(410.39, 522.37)
- **Layer:** they are drawn on OA PMET_CUT / drawing1, which is the PDK layer map's name for GDS 205;8. The DRC deck reads that GDS layer as MATCHING, and no deck maps it as a mask.
- **Visibility:** the hierarchical chip deck sees the top-level marker over the comparator's devices. MATCH.WARN.1 is CHIP NOT INTERACT MATCHING_ARRAY, and it now reports 0. PO.DN.16 and PO.R.28 run over the same marker grown by 10 um.

By rule against `layout_full_fill5_r5_seal`:

| Check | `layout_full_fill5_r6_seal` | `layout_full_fill5_r5_seal` |
| --- | --- | --- |
| DRC, installed chip deck (`chip-match-b1-chk`) | 1911: only MATCH.WARN.1 changes, 1 to 0 | 1912 |
| PO.DN.16 / PO.R.28 / AN.R.78.1m / MATCH.WARN.1 | 0 / 0 / 0 / 0 | not checked / not checked / not checked / 1 |
| G.1-G.3:MATCHING | 0 | (no marker) |
| LUP.5.2.1 / 5.2.2, flat (`chip-match-b1-flat-lupesd`) | 0 / 0 | 0 / 0 |
| ESD.18g / 19g / WARN.1, flat | 540 / 432 / 6 | 540 / 432 / 6 |
| LVS, full `chip_netlist` | CORRECT | CORRECT |
| LVS, only supply nets joined by name (`chip-match-b1-lvs-vcs`) | CORRECT | CORRECT |
| ERC | 305, identical by check | 305 |

## 892 um die: `sar8_adc_chip/layout_full_fill5_r7_seal`

The user adopted the 892 um die on 2026-11-23 ("Yes, plan to adopt"). The size is not yet confirmed with the shuttle provider; see Open.

**Why the seal ring can be smaller.** The seal ring of r3_seal through r6_seal is the TSMC standard sample `N28_TSMC_SRDMB_Mu` (DRM 4.5.66.2, added by the customer).
- The lab's `sealring` cell equals TSMC's `N28_TSMC_SRDMB_Mu_1P10M_002_20160711_SR_BKM.gds` layer by layer, after selecting the metals of the 1P9M 6X1Z1U stack. This holds for polygon counts and area on every kept layer.
- The sample is 1000 um square only because of its tile count. Two 185.6 um corner cells sit at each pair of opposite corners, each edge has one UCSRN_NOVIA_DPO_DOD at 182.6 um, and UCSRN_DPO_DOD tiles of 5.4 um repeat from 188 um. So the die is 373.6 + 5.4 n um, with n = 116 in the sample.
- `Layout/design/seal_ring_sized.py` keeps every relative position of the sample and changes only n. At n = 116 it reproduces all 472 placements of both the TSMC sample and the lab cell.

**Size.** CSR.R.1 keeps layout out of triangles at the prime-chip corners. The IO corner cells draw up to their outline corner, at x + y = die - 760 in the seal-ring frame, so the die must be at least 882 um.
- n = 95 (886.6 um) clears the triangles by 4.6 um.
- n = 96 (**892 um**) clears them by 10 um. This is the one adopted.
- Die area is 0.796 against 1.000 mm2, about 20 % less.

**CSR.R.1, tool-checked** (`chip-seal892-csr2`).
- **Why a separate run:** the chip deck derives the corner triangles only for a chip without a seal ring (`EMPTY_AREA_P4 = INT CHIP_NOSR_P4 < CSR_R_1 ABUT == 90`, CSR_R_1 = 74, under `#IFNDEF WITH_SEALRING`). With our own seal ring in the stream, the group would run on an empty triangle.
- **Probe stream:** the 892 scratch stream without its seal ring, plus four 0.1 um LMARK squares at the prime-chip corners (the inner edge of SEALRING_ALL, 24 um inside the die). They set the chip extent to the prime chip, as for a TSMC-added seal ring. LMARK probes sit on the lower-left diagonal at x + y = 70, 73, 75, 78, 100 and 110 um from the prime-chip corner.
- **Run:** the chip deck with WITH_SEALRING off and only the 264 CSR.R.1 checks selected.
- **Result:** CSR.R.1:LMARK flags the four corner squares and the probes at 70 and 73 um, and nothing else; every other CSR.R.1 check is 0.
- **Reading the check implements:** a right triangle with 74 um legs from the prime-chip corner (x + y < 74 there, 122 um in the seal-ring frame), not a 74 um radius. No layout of the chip enters it; the IO corner cells start 10 um outside.

**The narrower margin.** The PAD60GU metal is now 54.34 um from the die edge and 30.34 um from the inner edge of SEALRING_ALL (84.34 um at 1 mm).
- **Seal-ring enhanced zone:** the 6 um inside SEALRING_ALL (18-24 um from the die edge) is layout-free. Nothing of the chip is there.
- **PM.EN.2:** polyimide enclosure by the prime chip, 15 um. It does not apply, because the pads carry no PM (only the seal ring does), and 30.34 um would meet it anyway.
- **No other limit:** no other DRM rule limits pad or IO metal to the seal ring or die edge. The IO application note has none either.
- **AN.R.13mU** (guideline): keep matching pairs at least 3 % of the edge length from the die edge and 5 % of the diagonal from a corner, for a single-die wire-bond package. That is 27 um and 63 um at 892 um; the comparator is about 476 um from the nearest die edge.

**View.** `Layout/design/seal_ring_sized.py` builds the view in two steps:
- `SAR_ADC_T28_LAYOUT/sar8_seal_ring_892/layout` (build `sealring-892-b1`): 392 instances of the lab's `sealring` cells. Its stream (`sealring-892-drc1`) matches the generator at n = 96.
- `layout_full_fill5_r7_seal` (build `chip-seal892-b1`): a copy of `layout_full_fill5_r6_seal` whose XSEAL_RING instance becomes `sar8_seal_ring_892` at (-66, -66), R0. The die is (-66, -66)-(826, 826), with the IO ring still centred, and every chip view and object view stayed unchanged.
- **Stream** (`chip-seal892-b1-chk`, sha256 9b8a932d...): it spans exactly the die. The OA outline reaches x 831.5 only through label-text extents, and -67.381 through the seal-ring cells' 1.381 um overhang, as in the TSMC sample.

By rule against `layout_full_fill5_r6_seal`:

| Check | `layout_full_fill5_r7_seal` (892 um) | `layout_full_fill5_r6_seal` (1 mm) |
| --- | --- | --- |
| DRC, installed chip deck (`chip-seal892-b1-chk`) | 2904, identical by rule to the scratch run `chip-seal892-drc1` | 1911 |
| of which other than density and fill | 234, every rule equal | 234 |
| Seal-ring rules (SR, SLR, CSR, BiB) | equal | |
| CSR.R.1 corner triangles (`chip-seal892-csr2`) | 0 on chip layout | not tool-checked |
| LUP.5.2.1 / 5.2.2, flat (`chip-seal892-b1-flat-lupesd`) | 0 / 0 | 0 / 0 |
| ESD.18g / 19g / WARN.1, flat | 540 / 432 / 6 | 540 / 432 / 6 |
| LVS, full `chip_netlist` (ports, nets) | CORRECT (31, 1536) | CORRECT (31, 1536) |
| LVS, only supply nets joined by name (`chip-seal892-b1-lvs-vcs`) | CORRECT | CORRECT |
| ERC | 305, identical by check | 305 |

**Density** changes only in the unfilled margin, which is narrower and sits against the corners:
- Mx.DN.6: up by 124-247 per layer.
- Mx.DN.1: down from 5 to 1.
- OD.S.14: down from 27 to 20.
Fill decides these.

**Fill keep-out at the seal ring.**
- No fill outside die (-39, -39)-(799, 799): the band plus 3 um.
- No fill within x + y <= 125 um of each die corner (seal-ring frame), i.e. within the CSR triangle plus 3 um.

**Unchanged:** the periphery extraction, the clamp-feed current density, the matching check and the Stage 2/6 netlists. The seal ring connects to nothing, and no pad or route moved.

## Open

- MATCH.WARN.1 is closed by the permanent MATCHING markers in `layout_full_fill5_r6_seal`. The comparator's deviation from high matching is recorded above as an accepted risk; the waiver cites `chip-match-h1`.
- `layout_full_fill5_r7_seal` (892 um die) is the current and frozen chip view. Its sources stay unchanged: `layout_full_fill5_r6_seal` (MATCHING markers, 1 mm), `layout_full_fill5_r5_seal` (AVSS landings), `layout_full_fill5_r4_seal` (clamp feed), `layout_full_fill5_r3_seal` (seal ring) and `layout_full_fill5_r3`. `layout_full_dc_fill5` is superseded (ESD).
- Die size: confirm 892 x 892 um with the shuttle provider before tapeout.
  - **What to ask:** its die-size grid, billing blocks and scribe width, and whether it adds the seal ring itself (DRM 4.5.66.2 option 1). In that case the GDS must not carry ours.
  - **What 892 um is:** the CSR.R.1 minimum for this IO ring (882 um) plus a 10 um margin, not a confirmed die size.
- Analog pad decap 92.9 pF against the planned 114.2: the rail budget with the drawn values passes, worst droop 17.9 mV against 45 mV ([chip rail recheck](chip_rail_recheck.md)).
- ESR from extraction (the model above is an upper bound); MOM values from the PDK callback, not extracted.
- ESD connection to the clamps meets ESD.CD.1gU in `layout_full_fill5_r5_seal`: clamp bars, drop vias and AVSS landings. The exception is the AVDD pads' own core pin, 14.1 um of M2 (1.15 A), which belongs to the IO cell.
- The decap-port stacks use the same two VIA7/VIA8 recipe (decap port to ADC pin 1.2-1.8 ohm loop). The rail budget passes with them (20.3 mV); more stacks there would lower the droop further.
- Closed (Stage 6, 2026-11-23): the 56.6 ohm VIN routes with the PDB3AC pads (`sar8_vin_path.scs`) pass tracking, so no widening is needed. Against ideal VIN, codes are identical in all frames:
  - SS cold (`sar8-s6pv-ssc-verify-a` vs `sar8-s6f-ssc-verify-a`): residual at sample close 0.1085 vs 0.1015 LSB (limit 0.25), settling 0.0079 vs 0.0080 LSB, read margin 8.73 ns in both.
  - TT (`sar8-s6pv-tt-verify-a` vs `sar8-s6f-tt-verify-b`): residual 0.0066 vs 0.0061 LSB, settling 0.0125 vs 0.0126 LSB, margin 24.90 ns in both.
  - Output path, FF hot (`sar8-s6po-ffh-verify-a` vs `sar8-s6f-ffh-verify-a`, `sar8_output_path.scs`): residual 0.0055 LSB in both, settling 0.0747 vs 0.0749 LSB, read margin 29.96 vs 30.27 ns. Driver switching time against sample close is a separate Stage 6 analysis.
- Periphery extraction after fill, and at 125 C rcworst (scaled here).
- Fill (the fill session's): the pad decap and VSS-ring areas (M6/M7.DN.6) and the margin between the IO ring and the seal ring (Mx.DN.1/DN.6, OD.S.14), within the keep-out above.
