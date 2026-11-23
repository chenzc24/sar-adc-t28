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

- **Analog clamp moved (superseded by revision 3 below: this place fails the ESD bus check).** Between the VIN routes the analog decap reaches at most 87 pF with its clamp in place. Nothing outside the VINN/VINP pair can join the analog trunk without crossing VIN. So the analog PCLAMPC_H_G moved to (230, 279), beside the pair clamp, and is fed by straps from the pair trunks the same way. There are still three clamps on AVDD_CORE/AVSS_CORE. The analog pads now reach their nearest clamp, the SAR clamp, over about 3 (AVDD) and 6 (AVSS) pad pitches of the TACVDD/TACVSS bus, roughly 0.45 / 0.9 ohm at 25 C by the constraints.json bus model. The app note's pad-to-clamp bus limit is still unchecked (an existing open item).
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

Revision 3 fixes the ESD fault of revision 2. The analog PCLAMPC_H_G returns to (360, 622) on the analog trunks, between top_3/top_4 and the core (app note 8.7.3 step 2; the `sar8_esd_clamps/layout` view). Pad-to-clamp bus resistance at 125 C rcworst_T: AVDD (top_4) 0.02 ohm and AVSS (top_3) 0.06 ohm along the trunks, against 1 ohm (Table 10.1). In revision 2 they were 0.57 and 0.95 ohm over the TACVDD/TACVSS bus, before the pad cells' own resistance.

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

## Open

- `layout_full_fill5_r3` is the current chip view; `layout_full_dc_fill5` is superseded (ESD).
- Analog pad decap 92.9 pF against the planned 114.2 (Stage 1 recommends about 100 pF per branch): rerun the rail budget with the drawn values (analog 92.9, pair 115.9, SAR 134.6, DVDD 52.4 pF). Stage 2's runs at 85 pF bound it from below.
- ESR from extraction (the model above is an upper bound); MOM values from the PDK callback, not extracted.
- Fill of the pad decap and VSS-ring areas (M6/M7.DN.6), and the seal ring (the chip deck runs with WITH_SEALRING).
