# SAR8 Layout

The project has a CDAC layout candidate, a comparator, the functional core of the Bootstrap sampling switch, and a compact SAR timing core with complete routing and a separately filled integration view. Use readback from each OA view for module dimensions and pins. The ADC floorplan is preliminary.

The 2026-11-18 CDAC redesign is at `SAR_ADC_T28_LAYOUT / sar8j_r1_cdac_core / layout_paired_balanced`. Its core area is 3738.62 µm². In standalone prefill TT simulation, its amplitude was 96.99% of the schematic result. Eight of ten codes were correct after integrating this CDAC into the current ADC. The current view `layout_paired_stacked` adds the planned fill cell and orders the small bits by weight; its extracted gain error is 4.22% and its layout DNL/INL is 0.12/0.08 LSB. Across the SS/FF −40/125 °C corners, these stay within 4.22–4.26% and 0.12/0.08 LSB. At SS 0.81 V −40 °C, the integrated ADC shows a 0.35 LSB sampling residual, above the 0.25 LSB screen. About 0.25 pF of extra TOP capacitance per side slows the bootstrap switch, while routing resistance plays no part, so the fix belongs to the sampler or acquisition timing. [CDAC report with earlier filled results, same-condition comparisons, and trial fill](results/cdac.md)

| Topic | Entry point |
| --- | --- |
| Electrical design used by Layout | [Front-end manifest](../design/manifest.json) |
| Sample enable and SAR timing under the extracted CDAC load | [Four-frame acquisition measurements and routed candidate](results/sar_cdac_aperture_results_20261119.md) |
| Physical source, OA ownership, and recovery points | [Layout manifest](design/manifest.json) |
| Top-level placement intent | [Floorplan](design/floorplan.json), [preview](results/floorplan.svg), and [area](results/area.json) |
| CDAC redesign and proposed top-level placement | [Native layout and post-layout comparison](results/cdac_paired.json), [same-scale figures](results/figures/cdac_paired_comparison.png), and [top-level placement and TOP branch lengths](design/floorplan_paired.json) |
| Planned-fill CDAC `layout_paired_planned`, gain criteria, and gain-normalized code checks | [Planned fill record](results/cdac_planned_fill.json), [fill locations](results/figures/cdac_planned_fill.png), and [gain-normalized code check](results/gain_corrected_codes.json) |
| Current CDAC `layout_paired_stacked`: planned fill with weight-ordered small bits for DNL | [Report section](results/cdac.md#weight-ordered-small-bits-layout_paired_stacked), [small-bit placement and trunks](results/figures/cdac_small_bit_center.png), and [record](results/cdac_planned_fill.json) |
| CDAC gate driver and M6 integration | [Native XREF and CDAC integration](results/reference_driver.md) |
| Module ports, orientations, and interconnect priorities | [Interfaces](specs/interfaces.json) |
| Matching, fill, timing, and acceptance scope | [Constraints](specs/constraints.json) |
| Module dummies, independent fill, and top-level density closure | [Fill policy](specs/fill-policy.md) |
| Current evidence and open items | [Current results](results/current.json) |
| Measured single-sided Bootstrap dimensions, pins, parasitics, and sampling error | [Core layout](results/figures/bootstrap_core.png), [verification](results/bootstrap.json), and [plate-routing comparison](results/bootstrap_routing_review.json) |
| Operations, in-place iteration, and rollback | [Layout workflow](docs/workflow.md) |
| Query the active Virtuoso layout or a saved OA view | [Layout Query Guide](docs/layout-query.md) |

The preliminary core envelope is **176 × 170 µm (0.02992 mm²)**. Native readback gives **90.33 × 92.49 µm** for the CDAC and **1.63 × 3.52 µm** for the comparator core including its guard ring. Reserve **16 × 14 µm** for the comparator group and its interface routing. The three MOM loads on the comparator outputs and clock are circuit models. Their entries are in `not_drawn_instances`. The previous sampler reservation is smaller than the measured single-sided Bootstrap outline. Replan its top-level location and routing. The reference occupies reserved space. The routed SAR core measures 39.885 × 51.600 µm. The 41 × 56 µm reservation includes the filled outline and pin access. Use the remaining space for routing, power, isolation, and boundaries. Die, IO ring, and protection structure dimensions are open. Use the envelope as a floorplan estimate. Critical parasitic and routing timing budgets are still unallocated. [Interfaces](specs/interfaces.json)

All work layouts use the single library `SAR_ADC_T28_LAYOUT` under `llm_IO`. The actual host and paths are configured locally in `site.local.yaml:layout`.

| Cell view | Purpose |
| --- | --- |
| `sar_bootstrap_flat_8b_p_core/layout` | Shared single-sided sampling core for the P and N channels, 24.68 × 24.99 µm. The lower edge exposes VIN, VOUT, VDD, CLKS, and VSS. |
| `sar8j_r1_cdac_core/layout` | Functional connectivity, placement, and routing, with matching dummies, functional shielding, and devices. Density fill belongs to its own hierarchy. |
| `sar8j_r1_cdac/layout` | References the same XCORE with FILL_ODPO and FILL_METAL for full physical verification and PEX. |
| `sar_strongarm_t28_core/layout` | Functional 11-transistor comparator core with three shared-diffusion rows, one instance per finger, N+/P+ guard rings, and seven ports. This is the current review and integration view. |
| `sar8_sar_timing_core/layout_compact_eco` | Functional view for device and route review. All 208 nets are joined. [Same-scale placement and metal](results/figures/sar_timing_compact.png) |
| `sar8_sar_timing/layout_eco` | Integration view containing the verified core and its OD/PO and metal fill. [Calibre and five-corner measurements](results/sar_timing.md) |
| `sar8_sar_timing_core/layout_array_review` and `sar8_sar_timing/layout_array_review` | Revised bit rows, dedicated detector supply feeds and seven local decaps. [Geometry, dual-rail five-corner results and top-level density](results/sar_timing_refinement.md) |
| `sar8_sar_timing_core/layout_std_static` and `sar8_sar_timing/layout_std_static` | Standard-delay candidate with a four-gate static latch. Its extracted timing misses the 90 ns deadline at SS. [Physical views, latch load and routing comparison](results/sar_std_static_candidate_c_20261119.md) |
| `sar_strongarm_t28/layout` | Fill evaluation wrapper for the same core. The existing fill belongs to an earlier core and its qualification has expired. Refresh and verify the fill before integration. |

Iterate in the fixed work cells. Verify existing OA by default to protect accepted edits. The CDAC generator has yet to be requalified for rebuild. The comparator generator matches the source of the verified native run byte for byte. An explicit rebuild still requires the edit-lock check and OA checkpoint. The full top-level interface has 38 ports. The reference is `minimal_msb_d2`. The selected front-end SAR is `std_delay_qualified`. The released RC layout uses `reset_data_or`. Use their current timing contract for non-overlap behavior.

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

For the comparator, use `generate --module comparator` and `physical ID --module comparator`. The current prefill core (2026-11-18 v7) passed LVS and retained two original DRC warnings. All ten standalone TT points resolved correctly. Codes and handshakes passed all ten frames when integrated into the current ADC. See the report for the scope of these checks. [Comparator workflow](docs/workflow.md#comparator-module) · [Comparator results](results/comparator.md)

**The workflow migration passed on 2026-11-16.** For the same OA, geometry digests, LVS connectivity, and rule identities matched. DRC retained the two original warnings. The pre- and post-migration runs used the current reference/SAR configuration and agreed on ten-frame codes, handshake counts, and verdicts. The maximum conversion time difference was about 0.074 ps against a 10 ps comparison tolerance. Both runs had code failures at 12→0 and 243→255. Sampling edges and handshake timing passed. Precision analog settling and terminal voltage remained unqualified. The archive contains raw logs, frozen inputs, and measurements. Large waveforms were retained for CDAC diagnosis. [Migration archive](../results/storage/layout_migration_archive_20261116.json)

The historical CDAC post-layout result for B includes about **15.12% amplitude loss and two incorrect codes**. The parasitic breakdown assigns about 61% of added fixed-potential TOP loading to metal fill and 39% to OD/PO fill. The workflow migration checked geometry and input equivalence. Report LVS, DRC warnings, function, settling, and terminal voltage from their respective evidence. [CDAC results](results/cdac.md)

[Library migration](results/library_migration.json) · [Core and fill management](results/core_fill_management.json) · [Historical directory organization](results/organization.json) · [MOM pilot](docs/pilot-spec.md) · [Issue #3](https://github.com/chenzc24/sar-adc-t28/issues/3)
