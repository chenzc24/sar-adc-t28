# SAR8 Layout

The project has a CDAC layout candidate, a comparator, the functional core of the Bootstrap sampling switch, and the single-edge SAR macro `sar8_se_core/layout_r3` (18.495 × 16.8 µm, LVS CORRECT). The D2 reference (`design/xtor/reference/single_edge_d2.scs`) is not drawn yet. [SAR macro layout and post-layout runs](results/sar_se_core.md) Use readback from each OA view for module dimensions and pins. The ADC floorplan is preliminary. [Previous-architecture SAR and gate-driver layouts](#previous-architecture)

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
| Module dummies, independent fill, and top-level density closure | [Fill policy](specs/fill-policy.md) |
| Current evidence and open items | [Current results](results/current.json) |
| Single-edge SAR macro `sar8_se_core`: flow, views, DRC/LVS/PEX and post-layout ADC runs | [Report](results/sar_se_core.md), [record](results/sar_se_core.json), and [placement](results/figures/sar_se_core.png) |
| Measured single-sided Bootstrap dimensions, pins, parasitics, and sampling error | [Core layout](results/figures/bootstrap_core.png), [verification](results/bootstrap.json), and [plate-routing comparison](results/bootstrap_routing_review.json) |
| Operations, in-place iteration, and rollback | [Layout workflow](docs/workflow.md) |
| Query the active Virtuoso layout or a saved OA view | [Layout Query Guide](docs/layout-query.md) |

The preliminary core envelope is **176 × 170 µm (0.02992 mm²)**. Native readback gives **90.33 × 92.49 µm** for the CDAC and **1.63 × 3.52 µm** for the comparator core including its guard ring. Reserve **16 × 14 µm** for the comparator group and its interface routing. The three MOM loads on the comparator outputs and clock are circuit models. Their entries are in `not_drawn_instances`. The previous sampler reservation is smaller than the measured single-sided Bootstrap outline. Replan its top-level location and routing. The reference occupies reserved space. The 41 × 56 µm SAR reservation was sized for the previous architecture's routed SAR macro; the single-edge macro `sar8_se_core/layout_r3`, which also holds the top-level XDONE, XPRESET and XSAMPLE cells, measures 18.495 × 16.8 µm, so the reservation can shrink at top-level planning. Use the remaining space for routing, power, isolation, and boundaries. Die, IO ring, and protection structure dimensions are open. Use the envelope as a floorplan estimate. Critical parasitic and routing timing budgets are still unallocated. [Interfaces](specs/interfaces.json)

All work layouts use the single library `SAR_ADC_T28_LAYOUT` under `llm_IO`. The actual host and paths are configured locally in `site.local.yaml:layout`.

| Cell view | Purpose |
| --- | --- |
| `sar_bootstrap_flat_8b_p_core/layout` | Shared single-sided sampling core for the P and N channels, 24.52 × 24.99 µm, with four 1 µm main-switch fingers. VOUT and CLKS exit the lower edge on M2, VIN enters the north edge on M5, and VDD/VSS are M5 rails across the switch bank. One OD_18 region over the switch bank keeps 1.8 V NMOS well proximity low. Inside the ADC with the extracted CDAC it passes TT and SS 0.81 V −40 °C. `layout_mmain4` is the identical candidate build. [Report](results/bootstrap.json) |
| `sar8j_r1_cdac_core/layout` | Functional connectivity, placement, and routing, with matching dummies, functional shielding, and devices. Density fill belongs to its own hierarchy. |
| `sar8j_r1_cdac/layout` | References the same XCORE with FILL_ODPO and FILL_METAL for full physical verification and PEX. |
| `sar8_se_core/layout_r3` | Single-edge SAR macro: SAR control, acquire block and the top-level XDONE, XPRESET and XSAMPLE cells, 174 native standard cells placed and routed by Innovus. 26 ports, signal pins on the left edge in M3, VDD/VSS on M6 stripes. `layout_r2` is the earlier 21.195 × 18.0 µm revision. |
| `sar_strongarm_t28_core/layout` | Functional 11-transistor comparator core with three shared-diffusion rows, one instance per finger, N+/P+ guard rings, and seven ports. This is the current review and integration view. |
| `sar_strongarm_t28/layout` | Fill evaluation wrapper for the same core. The existing fill belongs to an earlier core and its qualification has expired. Refresh and verify the fill before integration. |

Iterate in the fixed work cells. Verify existing OA by default to protect accepted edits. The CDAC generator has yet to be requalified for rebuild. The comparator generator matches the source of the verified native run byte for byte. An explicit rebuild still requires the edit-lock check and OA checkpoint. The full top-level interface has 38 ports. The current SAR and reference sources are listed in the [interfaces](specs/interfaces.json); the SAR is drawn as `sar8_se_core` and the reference is not drawn yet. Use their current timing contract for non-overlap behavior.

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

For the comparator, use `generate --module comparator` and `physical ID --module comparator`. The current prefill core (2026-11-20 v8: v7 plus M2 supply-strap pins and redundant vias) passed LVS and retained two original DRC warnings. All ten standalone TT points resolved correctly, and the current single-edge ADC's eight-frame LPE verify fixture passed at TT and ffc with the extracted comparator. See the report for the scope of these checks. [Comparator workflow](docs/workflow.md#comparator-module) · [Comparator results](results/comparator.md)

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
