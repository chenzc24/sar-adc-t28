# Dummy and Density Fill Policy

Use this policy for the CDAC, comparator, Bootstrap, reference switch drive, SAR and timing, and top-level integration. The 2026-11-16 decision calls for completing placement and routing first, retaining required matching dummies with the core, managing density fill separately, and closing density at the top level.

## Core and Fill Ownership

| Structure | Ownership and handling |
| --- | --- |
| Matching dummies, array boundary dummies, and required device-row end structures | Retain in the functional core. Use the PDK and actual connectivity for LVS and extraction. |
| Taps, well and body contacts, guard rings, required isolation, and functional shielding | Treat as functional or process-required structures and retain them. |
| OD, PO, and multilevel metal used only for density | Put in a hierarchy that can be hidden and regenerated independently of the core. |

Classify shapes by purpose and the native rules. Use the original definitions for required dummies and boundaries inside native standard cells and PDK PCells.

Maintain one functional core. For filled evaluation, use a fixed wrapper that references that core and separate fill. Reuse the CDAC's XCORE, FILL_ODPO, and FILL_METAL structure. For routine review, open the core or hide its fill instances so that actual devices on OD and PO remain visible.

## Module Delivery

1. Complete device placement for matching, pin access, internal routing, required isolation, and power connections. Feed the actual bounding box, pin locations and layers, and sensitive regions back into top-level planning.
2. Complete the applicable local geometry and connectivity checks, LVS, prefill PEX, and interface measurements. Record deferred density, density gradient, and top-level boundary rules by rule ID and retain the raw reports. Keep other modules progressing and report those open rules when reporting DRC status.
3. Treat module density as a feasibility check during routine iteration. If space, exclusion regions, or rules make top-level closure infeasible, raise it during placement.
4. For sensitive modules such as the comparator, run a filled parasitic sensitivity evaluation when needed. Label that evidence as standalone evaluation. Include its fill in final integration only through the agreed fill ownership and top-level flow. Use the planned-fill process below for gain-sensitive modules.

## Planned Fill for Gain-Sensitive Modules

CDAC gain depends on TOP capacitance to fixed potentials. Fill placement changes gain and bit weights. The CDAC therefore owns TOP-related fill inside its outline and includes it in acceptance. [Gain and linearity budgets](../../docs/specification.md#full-scale-and-gain-error) · [Layout constraints](constraints.json)

| Rule | Window | Handling |
| --- | --- | --- |
| OD ≥20% (OD.DN.3), PO ≥10% (PO.DN.3), and 10 µm maximum OD spacing (OD.S.14) | 20 × 20 µm with 10 µm steps | Windows can fit entirely in the MOM array, so meet the rules in the array. PO.DN.3.1 exempts the MOM region. PO.DN.3 still applies. |
| M1–M9 minimum density (Mn.DN.1, M9.DN.3) | 125 × 125 µm | The window is larger than the CDAC. Exclude fill above the array and meet density in surrounding regions as needed. Check the adjacent-window gradient (Mn.DN.3) at the top level. |
| Three consecutive metal layers cannot all be below 5% (Mx.DN.7) | 30 × 30 µm with 15 µm steps | A window can fit inside the array. Plan shapes on at least one of M5, M6, and M7 above the array at module level. |

ODBLK, POBLK, and DM1EXCL–DM9EXCL block placement by the fill tool. The density checks still apply.

1. **Generate OD and PO fill inside the array.** Use OD and PO dummy datatypes and align the shapes to unit pitch. Use the same pattern around every active unit and matching dummy, mirrored between the N and P sides. Target density slightly above the minimum and prefer areas clear of TOP conductors. This preserves relative bit weights while changing overall gain. Use extraction to quantify the cost of lateral spacing between dummy OD and M1 TOP fingers.
2. **Exclude tool-generated metal fill above the array and TOP leads.** Cover those areas with DM1EXCL–DM9EXCL. Floating fill, including M7–M9, can reduce coupling from wide bottom-plate trunks to TOP by different amounts for each bit and degrade DNL. Place the deterministic M7 dummy stripes needed for Mx.DN.7 above matching-dummy rows.
3. **Use default fill in the switch and bottom-plate routing regions outside the array as appropriate.** Use ODBLK and POBLK over the array and TOP regions to preserve the planned OD/PO pattern.
4. **Assign ownership.** Place planned fill and exclusion layers in a separate fill cell referenced by the fixed wrapper. Apply top-level fill outside those exclusion regions.
5. **Verify the filled module.** Close local OD/PO density inside the array. Close metal minimum-density and gradient checks at the top level as specified above. Extract with planned fill and default peripheral fill. Remove one fill category at a time to measure its TOP load and check linearity from extracted bit weights.

## Top-Level Closure

Plan top-level fill after module adjacency, main routing, power, and isolation are established. Verify the planned regions of gain-sensitive modules. Assign a single owner to each region, even when fill is hierarchical. Exclude reused, verified module fill from regeneration and check module boundaries. Retain required matching and device structures when regenerating fill. Use PDK-supported exclusions and symmetry constraints, and apply all relevant density rules.

Final delivery includes full top-level density and geometry DRC, LVS, PEX matching the final fill state, and the relevant ADC post-layout simulations. Label prefill, standalone filled, and top-level filled evidence according to its actual scope.

Bind fill provenance to core or top-level input digests, boundaries, constraints, rule and tool identity, and outputs. Reassess fill, extraction, and electrical evidence after changes to the core, its neighbors, or routing. Retain dated results.

### ADC Core Fill Owners

Each region of the ADC core has one owner. Region names are the `blocks` and `reserved_regions` ids in the [floorplan](../design/floorplan.json); coordinates are core µm. Where regions overlap, the first row that names a region wins. Where an owner holds only some layers, the row names the layer range for each owner. The owner places all fill in its region and requalifies it after a change. Other flows leave the region alone. The top level draws DM1EXCL–DM9EXCL and ODBLK/POBLK in one exclusion cell over every region it does not fill (only the listed layers where a row splits them), then runs the foundry fill utility. The core passes leave out the utility's optional dummy TCD patterns (`FILL_TCD_PATTERN`, `FILL_Mn_DTCD`). These are CD monitors with drawn OD, PO and N-well, not density fill, and the default insertion put one beside the CDAC array's TOPN half. The chip-level fill places them outside the ADC core. Each core view gets its own fill revision n: the hierarchy `sar8_adc_core_fill<n>` beside the routed core in the wrapper `sar8_adc_core_filled/layout_fill<n>`. Revision 1 is on `layout_route_full`. Revisions 2 and 3 are on `layout_route_guard`, with top-level fill in the Bootstrap cells (superseded). Revision 4, current, is on `layout_route_boot_r2`, whose Bootstrap cells carry their own filled wrapper; it leaves the Bootstrap outlines empty. Build a new revision whenever the core view changes.

| Region | Owner | Fill in the region | Status |
| --- | --- | --- | --- |
| `top_fill_exclusion_tee`, `top_fill_exclusion_inputs`, `top_fill_exclusion_n_drop`, `top_fill_exclusion_p_drop` | Top level, exclusion | None on any layer. Only the TOP routes, their declared crossings and the CMP_CLK drop. | Drawn with the Stage 4 routes |
| `comparator`, `comparator_keepout` | Top level, exclusion | None. The v8 core keeps its N+/P+ guard rings and lies inside `top_fill_exclusion_inputs`. [Comparator](#comparator) | Recommended 2026-11-22; replaces the stale wrapper |
| Top-level route entries into the XREF/CDAC pair outline | Top level, routes | No fill on the route layers along the CODE0–7/PRESET M3 tracks from the XREF ports (x 76.425) to the pair outline (x 82.23), the VDD/VSS M6 feed from y 10 to the terminals at (45.215, 13.365) and (46.915, 14.565), and the VREFP/VREFN connection to the west ends of the pair M5 rails. | Blocked in the refill: DMnEXCL 1 µm around every top-level metal shape inside the pair outline. [Stage 5 record](../results/toplevel_fill.md) |
| `cdac`, `cdac_array_keepout` | XREF/CDAC pair `sar8_cdac_with_xref/layout_se_d2_r2` | Over the array, (12.275, 39.465)–(79.955, 68.325): the planned fill cell `sar8_cdac_fill_plan` with dummy OD/PO stripes, four M7 dummy stripes, ODBLK/POBLK and DM1EXCL–DM9EXCL. Outside the array, in the switch bank and side strips: the planned cell's 74 dummy MOS bars and, from `se-xref-peripheral-routed`, the 84 OD/PO bar pairs below the array and the utility OD/PO and M1–M9 fill. No top-level routing, grid or fill. | Requalified 2026-11-22: in the filled core, the refilled stream `se-xref-peripheral-routed` replaces `se-xref-peripheral-dense` (whose fill overlaps the routed core), with unchanged TOP load, k and DNL. Stage 2 evidence stays on the frozen stream ([filled stream](../results/single_edge_xref_filled.json)). The pair view holds only the planned cell. The peripheral fill is in OA as `sar8_adc_core_fill<n>_pair_*`. [Stage 5 record](../results/toplevel_fill.md) |
| `reference` and the rest of the pair outline (10, 10)–(82.23, 68.325) | XREF/CDAC pair | The XREF's native row taps and fillers stay in the core. Around them: the utility OD/PO and M1–M9 fill of `se-xref-peripheral-routed`, which keeps clear of the top-level devices that reach into the outline (the CREF corner below the CDAC). | Same as `cdac` |
| `bootstrap_n`, `bootstrap_p` | Bootstrap, planned fill cell `sar_bootstrap_flat_8b_p_fill/layout_r2` | The wrapper `sar_bootstrap_flat_8b_p_filled/layout_r2` (XCORE `sar_bootstrap_flat_8b_p_core/layout_r2` plus XFILL at R0, the core's five ports) replaces the core master at XBOOTP (R0) and XBOOTN (MY), so both channels carry the same fill. The fill cell puts 0.12 µm dummy-poly stripes and 0.28 µm dummy-OD segments in the unit gaps, with no dummy poly under any M1 finger: about 22 % OD and 13.6 % PO. ODBLK, POBLK and DM1EXCL–DM9EXCL cover the whole outline, so the top level fills nothing inside it on any layer. Mx.DN.7 over the cells relies on the top-level M8/M9 grid. Why: with tool fill inside the cell each boot-capacitor plate rose from about 30 fF to ground to 127 fF (M1–M9 fill, revision 2) or 68 fF (OD/PO only, revision 3); the planned cell gives 37.9 / 40.4 fF (BTOP / BBOT) and 193.2 fF plate to plate. | Chosen by the user 2026-11-22. Standalone filled checks `boot-fill-r2-20261122` (and -cworst-t, -cbest-t): DRC only the two advisories, LVS CORRECT. Not yet ADC-qualified. Top-level revision 4 on `layout_route_boot_r2` leaves the outlines empty; with it the plates are 38–42 fF to ground. [Bootstrap](../results/bootstrap.json) |
| `sar` | SAR macro `sar8_se_core/layout_r3` for OD/PO and M1–M6; top level for M7–M9 | Macro: its Innovus end caps, 26 taps, DCAP16/8/4 and FILL3/FILL2 fillers, and no density fill. Top level: D0–D7/SAMPLE on M7, the M8/M9 grid and utility fill. | Macro DRC has only the two advisories. [SAR macro](../results/sar_se_core.json) |
| `output_channel` | Top level, restricted | No metal fill on the channel's signal layer or the layers directly above and below it. The VSS shields carry that layer's density. Floating fill would load COMP_P/COMP_N, whose route load is the binding handshake limit (11.4 fF each, adopted 2026-11-22), and the channel is not mirrored. Utility OD/PO and fill on other layers are allowed. | Applied as DMnEXCL 1 µm around the drawn COMP_P, COMP_N, CMP_CLK, SEQ_SAMPLE and shield rectangles, on each one's layer ±1 (M2–M5 signals). [Stage 5 record](../results/toplevel_fill.md) |
| `digital_corridor` | Top level | Utility fill, except over the comparator group (x 87.6–90.8), which follows the `output_channel` rule. | Filled |
| `sar_guard_ring` | Top level | The P+ ring is a process-required structure, not fill. Utility fill around it. | Filled around the ring in revision 2 (`layout_route_guard`) |
| `comparator_decap_west`, `comparator_decap_east` | Top level, mirrored | NMOS decap devices and straps. Any metal fill is drawn once for the west strip and mirrored about x 46.115. | No fill drawn; both strips are excluded on all layers |
| `analog_decap_slot`, `analog_decap_west`, `analog_decap_east`, `vref_decap_west`, `vref_decap_south`, `xref_decap`, `xref_decap_east`, `pair_decap_southeast`, `sar_supply_and_decap`, `sar_decap_north`, `spare_decap_northeast` | Top level | Decap devices, the two 15 Ω reference resistors with their PCell dummies, straps and grid. Utility fill goes in the remaining space and on unused layers. | Filled |
| Rest of the core: margins, gaps between regions, VIN trunks and the analog trunk (about 1,911 µm², 14% of the core) | Top level | Utility fill on all layers outside the exclusions above. None within 1 µm of the VINN/VINP M5 trunks on M4–M6, so both inputs see the same fill. | Filled |
| IO ring, pads, the core-to-ring gap and every region of the [IO ring plan](../design/io_ring.json) | Chip level | Not assigned yet. The 9 × 9 ring plan is not in OA; assign its fill owners when it is. | Pending |

### Comparator

Do not rebuild `sar_strongarm_t28/layout`. The top level owns the comparator's fill, and `top_fill_exclusion_inputs` keeps the core and its margins free of fill. The wrapper and its masters `sar8_comp_fill_odpo` and `sar8_comp_fill_metal` stay in the library as dated evidence of the earlier core (`comp-filled-20261116-pex`) and leave the integration flow.

- **Nothing to close in the module.** The 1.63 × 3.52 µm core is smaller than every density window: 20 µm for OD/PO, 30 µm for Mx.DN.7 and 125 µm for M1–M9. Its DRC reports only the two advisories. Its neighbors close the windows that contain it: the mirrored NMOS decap strips (OD/PO), the Bootstrap fill cell and the CDAC array plan.
- **The wrapper's area is already excluded.** The exclusion extends 1.285 µm past the core on the west and east and 1.64 µm below it. The output channel starts at its north edge. A wrapper fill inside these margins would give the region a second owner; a wrapper that honors the exclusion is empty.
- **Mirror sensitivity.** v8 holds mirror coupling differences to 0.0074 fF (OUT–TAIL). An unmirrored output-strap crossing of about 0.015 fF (v3) and one extra via cut near the OUTP strap (v8c) each flipped the +0.1 mV decision of the TT screen. Utility fill on an absolute grid is not symmetric about x 46.115. Electrically, a few tenths of a millivolt of systematic offset is small against the 12.05 mV σ offset that the digital code-offset correction removes (issue #12). The cost is qualification: fill near the core would invalidate the ±0.1 mV screen and the mirror limit in `decisions.cmp_clk_north_drop.verify`, and rerunning the v8 PVT, Monte Carlo, noise and kickback checks with fill would gain no density.
- **Rebuild cost.** A rebuild takes a new `fill_cdac.py --module comparator` run, an OA write into the wrapper (edit lock and checkpoint), filled PEX and the standalone checks again. The result would remain standalone evidence, superseded by the filled top-level extraction.

Verify in the Stage 5 coupled extraction: the comparator's mirror coupling differences stay at the v8 level, and the TT decision screen passes in the extracted environment. If a difference grows, extend the exclusion or mirror the fill around it; do not add fill to the core. For a standalone filled sensitivity check, cut the comparator, its exclusion and the decap strips from the filled top level instead of rebuilding the wrapper.

### Density Closure of the Core

The 122 × 111 µm core covers 86.7% of one 125 µm window, so the M1–M9 minimum-density and gradient rules (Mn.DN.1, M9.DN.3, Mn.DN.3) are decided for the whole core at once, together with at least 2,083 µm² of the core-to-ring gap. In the window that holds the CDAC:

| Area in the window | µm² | Share | M8/M9 |
| --- | ---: | ---: | --- |
| CDAC array, planned fill only | 1,953 | 12.5% | None |
| TOP exclusions, comparator inside | 88 | 0.6% | None |
| Pair switch bank, XREF and side strips | 2,260 | 14.5% | The pair's utility fill; the M8/M9 share is not recorded |
| Top-level regions in the core | 9,241 | 59.1% | Grid and utility fill |
| Outside the core | ≥ 2,083 | 13.3% | Chip level, pending |

The floorplan's 25% (`power_plan.density`) counts the whole CDAC keep-out as empty. The pair's peripheral fill already covers its switch bank, so the area without M8/M9 is between 13.1% and 24.5% of the window. The rest must average 1.15 to 1.32 times the rule minimum.

1. Record the minimum, window and step of Mn.DN.1, M9.DN.3, Mn.DN.3 and Mx.DN.7 from the deck used for module DRC in [constraints](constraints.json) `fill`.
2. After the Stage 4 routes, merge the routed core with the pair's filled stream at the GDS level (no OA write) and run density-only DRC. Record the per-layer density in the core window and in the 30 µm windows around the TOP tee and comparator.
3. Refill the pair. Regenerate its peripheral fill with the route entries above blocked, using the same settings as `se-xref-peripheral-dense` under a new evidence ID. Repeat its TOP fixed load, side imbalance, k and DNL/INL. The array plan is unchanged.
4. Use the grid for density. Place the VDD/VSS M8/M9 straps over the decap regions, the SAR macro and the Bootstrap cells (mirrored about x 46.115), densest next to the CDAC (`vref_decap_west`, `xref_decap`, `xref_decap_east`, `pair_decap_southeast`). Keep them off the array, the TOP exclusions, the comparator and the VIN trunks.
5. Fill by owner, in order: the pair refill, the Bootstrap mirrored cell, the mirrored comparator decap strips, then the utility over the rest with the exclusion cell. If density falls short, use an unused `spare_decap_northeast` as fill area, then widen the straps. Never put metal over the array. M7–M9 utility fill there raised fixed TOP load from 52.1 to 67.5 fF, gain error from 4.23% to 5.51% and DNL from 0.35 to 0.64 LSB. [CDAC planned fill](../results/cdac.md#planned-fill-view-layout_paired_planned)
6. Mx.DN.7 near TOP: the 30 µm windows around the comparator hold the exclusions, the restricted channel and the north edge of the array. If one fails, add M7 dummy stripes mirrored about x 46.115 in `analog_decap_slot` or the comparator decap strips, never inside an exclusion.
7. Gradient: the array is a 67.7 × 28.9 µm hole in M8/M9. Keep the chip-level fill of the core-to-ring gap near the core's average so adjacent windows pass Mn.DN.3. This waits for the ring's fill owners.
8. Verify the filled assembly (Stage 5): full density and geometry DRC, LVS, and coupled PEX of the final fill. The pair's TOP fixed load ≤ 57 fF per side, top-level TOP wiring within its separate 9.8 fF allowance, and imbalance ≤ 1 fF. Comparator mirror coupling at the v8 level. COMP_P/COMP_N and CMP_CLK loads within the handshake budget. [Budgets](constraints.json)

## Existing Layouts

Continue in-flight verification as planned. Existing fill can support review and diagnosis after it is isolated in its own hierarchy. Before writing OA, follow the ownership and recovery procedure. Protect other modules, unsaved user edits, and existing failure evidence. [Recovery and in-place iteration](../docs/workflow.md#recovery-and-in-place-iteration)
