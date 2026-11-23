# SAR8 Layout

The project has a CDAC layout candidate, a comparator, the functional core of the Bootstrap sampling switch, and the single-edge SAR macro `sar8_se_core/layout_r3` (18.495 × 16.8 µm, LVS CORRECT). The 28-cell D2 reference is routed on the south side of the CDAC. [XREF layout and short tests](results/single_edge_xref.md). [SAR macro layout and post-layout runs](results/sar_se_core.md) Use readback from each OA view for module dimensions and pins. The ADC floorplan is preliminary. [Previous-architecture SAR and gate-driver layouts](#previous-architecture)

The 2026-11-18 CDAC redesign is at `SAR_ADC_T28_LAYOUT / sar8j_r1_cdac_core / layout_paired_balanced`. Its core area is 3738.62 µm². In standalone prefill TT simulation, its amplitude was 96.99% of the schematic result. Eight of ten codes were correct after integrating this CDAC into the previous-architecture ADC. The current view `layout_paired_stacked` adds the planned fill cell and orders the small bits by weight; its extracted gain error is 4.22% and its layout DNL/INL is 0.12/0.08 LSB. Across the SS/FF −40/125 °C corners, these stay within 4.22–4.26% and 0.12/0.08 LSB. In the current single-edge ADC at SS 0.81 V −40 °C, this CDAC with the schematic Bootstrap has a worst sampling residual of 0.067 LSB, and with the extracted four-finger Bootstrap 0.050 LSB, both within the 0.25 LSB screen. [Sampler adoption](../results/design/sampler_mmain4_adoption_20261121.md) · [CDAC report with earlier filled results, same-condition comparisons, and trial fill](results/cdac.md)

| Topic | Entry point |
| --- | --- |
| Electrical design used by Layout | [Front-end manifest](../design/manifest.json) |
| Physical source, OA ownership, and recovery points | [Layout manifest](design/manifest.json) |
| Top-level placement intent | [Floorplan](design/floorplan.json), [preview](results/floorplan.svg), and [area](results/area.json) |
| CDAC redesign and proposed top-level placement | [Native layout and post-layout comparison](results/cdac_paired.json), [same-scale figures](results/figures/cdac_paired_comparison.png), and [top-level placement and TOP branch lengths](design/floorplan_paired.json) |
| Planned-fill CDAC `layout_paired_planned`, gain criteria, and gain-normalized code checks | [Planned fill record](results/cdac_planned_fill.json), [fill locations](results/figures/cdac_planned_fill.png), and [gain-normalized code check](results/gain_corrected_codes.json) |
| Current CDAC `layout_paired_stacked`: planned fill with weight-ordered small bits for DNL | [Report section](results/cdac.md#weight-ordered-small-bits-layout_paired_stacked), [small-bit placement and trunks](results/figures/cdac_small_bit_center.png), and [record](results/cdac_planned_fill.json) |
| Module ports, orientations, and interconnect priorities | [Interfaces](specs/interfaces.json) |
| Matching, fill, timing, and acceptance scope | [Constraints](specs/constraints.json) |
| Reference and supply current limits, Stage 6 package model, and required decoupling | [Budget record](results/rail_budget.md) and [model output](results/rail_budget.json) |
| Module dummies, independent fill, and top-level density closure | [Fill policy](specs/fill-policy.md) |
| Fill of the routed core by owner: pair refill, mirrored Bootstrap cell, core pass, density DRC and filled extraction | [Stage 5 record](results/toplevel_fill.md) and [data](results/toplevel_fill.json) |
| Current evidence and open items | [Current results](results/current.json) |
| Single-edge SAR macro `sar8_se_core`: flow, views, DRC/LVS/PEX and post-layout ADC runs | [Report](results/sar_se_core.md), [record](results/sar_se_core.json), and [placement](results/figures/sar_se_core.png) |
| Measured single-sided Bootstrap dimensions, pins, parasitics, and sampling error | [Core layout](results/figures/bootstrap_core.png), [verification](results/bootstrap.json), and [plate-routing comparison](results/bootstrap_routing_review.json) |
| Operations, in-place iteration, and rollback | [Layout workflow](docs/workflow.md) |
| Query the active Virtuoso layout or a saved OA view | [Layout Query Guide](docs/layout-query.md) |

The top-level floorplan places the measured blocks in a **122 × 111 µm core (0.0135 mm²)**. The XREF/CDAC pair (72.23 × 51.76 µm CDAC and 63.354 × 5.285 µm D2 reference in one coordinate frame) sits at the south-west. The 1.63 × 3.52 µm comparator sits on the CDAC TOP exits, with the two 24.52 × 24.99 µm Bootstrap cells mirrored above it. The 18.495 × 16.8 µm SAR macro `sar8_se_core/layout_r3`, which also holds the top-level XDONE, XPRESET and XSAMPLE cells, sits east of a 10 µm digital corridor. The comparator outputs, CMP_CLK and a balanced SEQ_SAMPLE tree run on separate shielded tracks in a channel below the Bootstrap cells. The frozen SAR pin order forces five crossings, which sit in the corridor; the two comparator outputs have equal wire length and the same crossings. The plan reserves reference decoupling (8 pF between VREFP and VREFN behind 15 Ω per rail, from the Stage 1 budget), comparator and XREF decoupling, TOP fill exclusions, a guard ring around the SAR macro and a keep-out over the CDAC array. `Layout check` validates the planned routes: anchored ends, one net per track, declared crossings and block intrusions, mirrored TOP paths and matched outputs. CMP_CLK lands on the comparator's clock trunk from the north on M4, an exception to the comparator's M4 keep-out accepted on 2026-11-21; top-level extraction must confirm its coupling. The floorplan lists the remaining open items. The three MOM loads on the comparator outputs and clock are circuit models. Their entries are in `not_drawn_instances`. The chip-level [IO ring plan](design/io_ring.json) puts the core in a 9 × 9 pad ring (760 × 760 µm outline) whose supply cells and counts follow the TSMC N28 I/O application note: one PVDD3AC/PVSS3AC pad pair per ADC supply branch, two interleaved pads per reference rail, a PVSS2AC and a PVSS1DGZ on the global VSS bus, and three DVDD and two VDDIO pads; the ring cell is built in OA as `SAR_ADC_T28_LAYOUT/sar8_io_ring` and passes cell-level DRC and LVS against its schematic ([verification](results/io_ring_verification.json)), while the ADC assembly inside it is not yet in OA. [Review image](results/io_ring.png) The top-level route budgets, adopted on 2026-11-22 from the Stage 2 all-extracted ADC, are in [constraints](specs/constraints.json): 9.8 fF per TOP net with at most 800 Ω of sampler route, 100 ps one way on the CODE bus, and 20 ps one way on the handshake with a load limit of 11.4 fF on each comparator output and 11.1 fF on CMP_CLK. [Floorplan](design/floorplan.json) · [Interfaces](specs/interfaces.json)

All work layouts use the single library `SAR_ADC_T28_LAYOUT` under `llm_IO`. The actual host and paths are configured locally in `site.local.yaml:layout`.

| Cell view | Purpose |
| --- | --- |
| `sar_bootstrap_flat_8b_p_core/layout` | Shared single-sided sampling core for the P and N channels, 24.52 × 24.99 µm, with four 1 µm main-switch fingers. VOUT and CLKS exit the lower edge on M2, VIN enters the north edge on M5, and VDD/VSS are M5 rails across the switch bank. One OD_18 region over the switch bank keeps 1.8 V NMOS well proximity low. Inside the ADC with the extracted CDAC it passes TT and SS 0.81 V −40 °C. `layout_mmain4` is the identical candidate build. [Report](results/bootstrap.json) |
| `sar8j_r1_cdac_core/layout` | Functional connectivity, placement, and routing, with matching dummies, functional shielding, and devices. Density fill belongs to its own hierarchy. |
| `sar8j_r1_cdac/layout` | References the same XCORE with FILL_ODPO and FILL_METAL for full physical verification and PEX. |
| `sar8i_refword/layout_se_d2_r2` | Current D2 XREF. Open `sar8_cdac_with_xref/layout_se_d2_r2` for the native M6 connections to the paired CDAC. [Routing and verification](results/single_edge_xref.md) |
| `sar8_se_core/layout_r3` | Single-edge SAR macro: SAR control, acquire block and the top-level XDONE, XPRESET and XSAMPLE cells, 174 native standard cells placed and routed by Innovus. 26 ports, signal pins on the left edge in M3, VDD/VSS on M6 stripes. `layout_r2` is the earlier 21.195 × 18.0 µm revision. |
| `sar_strongarm_t28_core/layout` | Functional 11-transistor comparator core with three shared-diffusion rows, one instance per finger, N+/P+ guard rings, and seven ports. This is the current review and integration view. |
| `sar_strongarm_t28/layout` | Fill wrapper of an earlier core, kept as dated evidence and not integrated. The top level owns the comparator's fill and keeps it out of the core's TOP exclusion. [Fill owners](specs/fill-policy.md#comparator) |
| `sar8_adc_core/layout_place` | Placement-only ADC core: the five frozen block views at their floorplan transforms inside the 122 × 111 µm boundary. Read-only. [Placement review](results/toplevel_placement.json) |
| `sar8_adc_core/layout_route_int` | `layout_place` plus the core-internal routes: TOP tee, comparator outputs, CMP_CLK, the SEQ_SAMPLE tree, CODE0-7/PRESET and the floating VSS shields, built by `Layout/design/toplevel_route.py`. No boundary routes, supply feeds or fill. [Routing record](results/toplevel_route_internal.json) |
| `sar8_adc_core/layout_route_full` | `layout_route_int` plus the boundary routes (D0-D7, SAMPLE, VINN/VINP), the analog, pair and SAR supply branches with their `nmoscap` decoupling, the shield tie to VSS, and the on-chip reference network: VREF pins, RREFP/RREFN (`rupolym`, 52 segments per rail) and CREF (164 `nmoscap`). Built by `Layout/design/toplevel_full.py`. No SAR guard ring or fill. [Record](results/toplevel_route_full.md) |
| `sar8_adc_core/layout_route_guard` | `layout_route_full` plus the SAR P+ guard ring with its own VSS strap to a fourth `0` pin on the east edge, built by `Layout/design/toplevel_full.py --stage guard`. The routed view that fill builds on. [Record](results/toplevel_route_guard.md) |
| `sar8_adc_core/layout_route_boot_r2` | `layout_route_guard` with XBOOTN and XBOOTP on the revised filled Bootstrap `sar_bootstrap_flat_8b_p_filled/layout_r2` (latch-up spacing fixed, planned fill), same origins, orientations and pins, built by `Layout/design/toplevel_full.py --stage boot_r2`. Pending the Bootstrap revision's ADC qualification. [Record](results/toplevel_route_boot_r2.md) |
| `sar8_adc_chip/layout` | Partial chip assembly: `sar8_io_ring` at the origin, the core `layout_route_guard` at (363.885, 449), and the VIN, VREF, analog/pair/SAR supply and SAMPLE routes from the pads' terminal polygons, with the ring's labels, POC_dig and a PSUB2 marker for the ADC P-well domain. No output register, clamps, pad decaps, core VSS ring, ADC guard ring or fill. Built by `Layout/design/chip_assembly.py`. [Record](results/chip_assembly.md) |
| `sar8_out_reg/layout`, `sar8_esd_clamps/layout`, `sar8_decap_{analog,pair,sar,dvdd}/layout`, `sar8_core_vss_ring/layout`, `sar8_adc_guard_ring/layout` | Chip-level objects of `io_ring.json` in die coordinates, placed at the origin: the output register (Innovus, `design/chip/output_register.scs`), the three PCLAMPC_H_G, the nmoscap pad decaps, the M7 core VSS ring and the 2 um ADC guard ring. `layout_r2` views of the clamps and pad decaps: the decaps grown to plan, the analog clamp moved. Built by `Layout/design/chip_objects.py`. [Record](results/chip_objects.md) |
| `sar8_adc_chip/layout_full` | `sar8_adc_chip/layout` plus the chip-level objects and the routes that end on them (ADC_D0-7, CK, D0-D7_CORE, DVDD, VSS_*, AVSS_guard, decap and clamp drops). Chip LVS CORRECT against the full `chip_netlist`. Built by `Layout/design/chip_integration.py`. [Record](results/chip_objects.md) |
| `sar8_adc_chip/layout_full_boot_r2`, `sar8_adc_chip/layout_full_dc_fill5` | `layout_full` on the r2 Bootstrap core `sar8_adc_core/layout_route_boot_r2` (no LUP.5.2.x); and on the final filled core `sar8_adc_core_filled/layout_fill5` with the `layout_r2` pad decaps at their planned capacitance and the analog clamp beside the pair clamp. Both chip LVS CORRECT. Built by `Layout/design/chip_integration.py --view --core-view --objects-rev`. [Record](results/chip_objects.md) |
| `sar8_adc_chip/layout_full_fill5_r4_seal` | Current chip view: `layout_full_fill5_r3_seal` with every ESD clamp bar fed along its length (M9/M8 straps, a drop stack every 6 um), so pad to clamp is at most 0.94 ohm (app note Table 10.1: 1 ohm). Chip LVS CORRECT; chip DRC unchanged apart from density. Built by `Layout/design/chip_clamp_feed.py`. [Record](results/chip_objects.md) |
| `sar8_adc_chip/layout_full_fill5_r3_seal` | `layout_full_fill5_r3` inside the lab's 1 x 1 mm seal ring (`sealring/N28_TSMC_SRDMB_Mu` at die (-120, -120)). Chip LVS CORRECT; chip DRC differs only in density and fill in the new margin. Built by `Layout/design/chip_seal_ring.py`. Periphery extraction and the Stage 2 pad-path netlists: `Layout/tools/analysis/chip_periphery.py`. [Record](results/chip_objects.md) |
| `sar8_adc_chip/layout_full_fill5_r3` | `layout_full_dc_fill5` with the analog clamp back between its pads and the core (the r2 place failed the ESD bus check) and the analog decap `sar8_decap_analog/layout_r3` (nmoscap plus M5-M7 MOM, 92.9 pF). Chip LVS CORRECT. Built by `Layout/design/chip_integration.py --objects-rev 3`. [Record](results/chip_objects.md) |
| `sar8_adc_core_filled/layout_fill1` | Filled core, revision 1: XCORE is `sar8_adc_core/layout_route_full` (read only), FILL is the fill hierarchy `sar8_adc_core_fill1` (pair refill, mirrored Bootstrap cell, core pass, exclusion cell), plus copies of the core's texts. `layout_fill2` (revision 2, on `layout_route_guard`) is superseded. The current revision 4 fills `layout_route_boot_r2`, whose Bootstrap cells own their fill; its wrapper is `layout_fill4` with `sar8_adc_core_fill4`. The current `layout_fill5` (`sar8_adc_core_fill5`) adds dummy-PO segments in the TOP-tee strip and leaves only the two DRC advisories. [Stage 5 record](results/toplevel_fill.md) |

Iterate in the fixed work cells. Verify existing OA by default to protect accepted edits. The CDAC generator has yet to be requalified for rebuild. The comparator generator matches the source of the verified native run byte for byte. An explicit rebuild still requires the edit-lock check and OA checkpoint. The full top-level interface has 38 ports. The current SAR and reference sources are listed in the [interfaces](specs/interfaces.json); the SAR is drawn as `sar8_se_core` and the reference as `sar8i_refword/layout_se_d2_r2`. Use their current timing contract for non-overlap behavior.

```text
Layout/
├─ README.md
├─ __main__.py              # python -m Layout
├─ project.py               # Site configuration and evidence resolution
├─ planning.py              # Floorplan checks and generated views
├─ design/                  # Manifests, floorplan, and native layout generators
├─ specs/                   # Interfaces, limits, and acceptance scope
├─ tb/                      # MOM fixtures and independent CDL references
├─ tools/
│  ├─ deploy.py
│  ├─ physical/             # Native OA, GDS, DRC, LVS, and PEX execution
│  ├─ simulation/           # Managed post-layout and diagnostic recipes
│  └─ analysis/             # Measurements, comparisons, and parasitic statistics
├─ results/                 # Active index, planning figures, and evidence
└─ docs/                    # Workflows and original MOM pilot scope
```

Remote layout directories are `layout/runtime/` for the current deployment, `layout/state/` for receipts and state, and `layout/evidence/<run-id>/` for frozen inputs and results. OA lives in the shared home library. Spectre uses the existing managed `runs/` directory. Read legacy pilot evidence at `layout-mom-pilot/evidence/`. Both entry points use the existing lock. A run ID identifies its evidence.

Run these commands from the repository root.

```powershell
.venv/Scripts/python.exe -m Layout check
.venv/Scripts/python.exe -m Layout render
.venv/Scripts/python.exe -m Layout generate
.venv/Scripts/python.exe -m Layout deploy
.venv/Scripts/python.exe -m Layout physical UNIQUE_ID --through pex
.venv/Scripts/python.exe -m Layout status UNIQUE_ID
.venv/Scripts/python.exe -m Layout prepare-tt PHYSICAL_ID TT_RUN_ID
```

`generate` creates inputs under `work/`. `prepare-tt` packages the recipe. Use the simulation entry point for registration, execution, analysis, and collection. Assign new IDs to new runs. [Simulation guide](../docs/simulation.md) · [Workflow migration results](results/workflow_migration.json)

For the comparator, use `generate --module comparator` and `physical ID --module comparator`. The current prefill core (2026-11-20 v8: v7 plus M2 supply-strap pins and redundant vias) passed LVS and retained two original DRC warnings. All ten standalone TT points resolved correctly, and the current single-edge ADC's eight-frame LPE verify fixture passed at TT and ffc with the extracted comparator, and at SS cold with the CWORST_T comparator and CDAC. Standalone checks cover five PVT corners with matched RC, kickback into the extracted CDAC, a 200-seed post-layout offset MC (σ 12.05 mV) and input-referred noise (worst 0.113 LSB of the 0.18 LSB budget). See the report for the scope of these checks. [Comparator workflow](docs/workflow.md#comparator-module) · [Comparator results](results/comparator.md)

**The workflow migration passed on 2026-11-16.** For the same OA, geometry digests, LVS connectivity, and rule identities matched. DRC retained the two original warnings. The pre- and post-migration runs used the then-current reference/SAR configuration and agreed on ten-frame codes, handshake counts, and verdicts. The maximum conversion time difference was about 0.074 ps against a 10 ps comparison tolerance. Both runs had code failures at 12→0 and 243→255. Sampling edges and handshake timing passed. Precision analog settling and terminal voltage remained unqualified. The archive contains raw logs, frozen inputs, and measurements. Large waveforms were retained for CDAC diagnosis. [Migration archive](../results/storage/layout_migration_archive_20261116.json)

The historical CDAC post-layout result for B includes about **15.12% amplitude loss and two incorrect codes**. The parasitic breakdown assigns about 61% of added fixed-potential TOP loading to metal fill and 39% to OD/PO fill. The workflow migration checked geometry and input equivalence. Report LVS, DRC warnings, function, settling, and terminal voltage from their respective evidence. [CDAC results](results/cdac.md)

## Previous architecture

The SAR timing and CDAC gate-driver layouts were drawn for the previous SAR and `minimal_msb_d2` reference, which the single-edge design replaced. Their generators and layout flows were removed; commit `c46d9d6` is the last to contain them. The library still holds their views: `sar8_sar_timing_core` and its filled wrapper `sar8_sar_timing` (`layout_compact_eco`/`layout_eco`, `layout_array_review`, `layout_std_static`), and `sar8_cdac_gate_driver` and `sar8_cdac_with_xref` (`layout_gate_drive`). The reports below are dated evidence for that architecture and do not apply to the current design.

| Topic | Report |
| --- | --- |
| Routed SAR timing core, filled wrapper, Calibre and five-corner timing | [SAR timing](results/sar_timing.md) and [same-scale placement](results/figures/sar_timing_compact.png) |
| Revised bit rows, detector supply feeds and local decaps | [SAR timing refinement](results/sar_timing_refinement.md) |
| Standard-delay candidate with a static latch | [Candidate C](results/sar_std_static_candidate_c_20261119.md) and [QUIET stage comparison](results/sar_quiet_lpe_20261119.md) |
| Sample enable and SAR timing under the extracted CDAC load | [Four-frame acquisition measurements and routed candidate](results/sar_cdac_aperture_results_20261119.md) |
| CDAC gate driver and M6 integration | [Native XREF and CDAC integration](results/reference_driver.md) |

[Library migration](results/library_migration.json) · [Core and fill management](results/core_fill_management.json) · [Historical directory organization](results/organization.json) · [MOM pilot](docs/pilot-spec.md) · [Issue #3](https://github.com/chenzc24/sar-adc-t28/issues/3)
