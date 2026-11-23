# Layout Workflow

Use the front-end manifest for the electrical design and the layout manifest for physical planning and ownership. The migration verifies repository organization and input equivalence. Track CDAC performance fixes separately. [Front-end manifest](../../design/manifest.json) · [Layout manifest](../design/manifest.json)

## From the Top Level to Modules and Back

The revised CDAC shares TOP row wiring and uses the `layout_paired_balanced` review view. `python -m Layout generate --module cdac-paired` produces SKILL, an independent CDL, and placement coordinates. After native deployment, `python -m Layout physical UNIQUE_ID --view layout_paired_balanced --through pex` reads the saved OA view for DRC, LVS, and coupling extraction. `python -m Layout prepare-tt UNIQUE_ID RUN_ID --prefill` integrates that extraction into the current ADC. [Revised CDAC geometry, view identity, and simulation results](../results/cdac_paired.json)

For a standalone rerun, use `python -m Layout.tools.simulation.prepare_full_sim UNIQUE_ID RUN_ID --adc-solver`. It uses the current ADC solver settings and the paired CDAC pre- and post-layout stimuli, a 260 ns run, and a 5 ps maximum step. Run both physical revisions with these settings to compare bit weights and settling time.

Generate the current CDAC (`layout_paired_stacked`) with `python -m Layout generate --module cdac-paired --planned-fill --center stacked`. `--center stacked` orders the small bits by weight from the switch side so that each small-bit trunk length, and thus its TOP coupling, follows its unit count. Without `--center`, the generator reproduces the published central-inversion center of `layout_paired_balanced` and `layout_paired_planned`. The wrapper references the separate `sar8_cdac_fill_plan` cell. For acceptance, add foundry OD/PO and metal fill outside the array using the fill-exclusion layers, then run DRC, LVS, and coupling PEX on the combined stream. Add `--planned-fill` to `prepare_full_sim` for standalone testing and `prepare-tt` for ADC integration. Defer only the 125 µm metal-density rules (Mn.DN.1, Mn.DN.3, M9.DN.3) to the top level. Close OD/PO density and Mx.DN.7 within the module. For the filled netlist, use `--rss-mib 2560`. Compare ADC codes using the gain-corrected check and take k from the standalone test of the same revision. [Gain-corrected code comparison](../tools/analysis/gain_corrected_codes.py)

1. Update the floorplan, interfaces, and constraints. Set the core and module locations, orientations, signal exits, and space for power, isolation, and routing. Identify which dimensions are measured and which are reserved. [Floorplan](../design/floorplan.json) · [Interfaces](../specs/interfaces.json) · [Constraints](../specs/constraints.json)
2. Run `python -m Layout check` to check electrical identity, port order, instance coverage, boundaries, and overlap. Use `render` for the planning figure and area table. Leave unallocated parasitic and timing budgets empty.
3. Place devices for matching, read back native PCell and standard-cell parameters, and route each module. Make functional edits in the fixed core cell. Retain functional dummies, body contacts, guard rings, and shielding.
4. Complete local geometry and connectivity checks, LVS, prefill PEX, and interface measurements. Use measured bounding boxes, loads, and timing to revise the floorplan. Track deferred density and top-level context rules according to the fill policy. Base module status on current evidence. [Fill policy](../specs/fill-policy.md)
5. Complete top-level connections, power, and isolation. Assign one fill owner to each region. Use the same GDS, rule identity, and input identity for final filled PEX and ADC post-layout simulation.

The current floorplan is preliminary. Select new routing layers, vias, guard rings, and parasitic budgets based on native pin access, PDK rules, and electrical budgets.

Consult the fill policy when placing or routing a module, generating or importing fill, interpreting density DRC, preparing PEX, or integrating the top level. It defines what belongs in the core, who owns fill, how to qualify each stage, and how to show layout in review. Use the filled commands below for fill evaluation when the task calls for it. [Dummy and Density Fill Policy](../specs/fill-policy.md)

## Layout Queries

For placement, pins and routing, query the target OA cellview through Virtuoso Bridge. Read the active edit in its owning Virtuoso session to include unsaved changes. When the question explicitly concerns a saved view, use the isolated read-only OA reader. [OA query guide](layout-query.md)

For verification of an export, use the matching stream-out manifest and the native Calibre DRC, LVS or PEX evidence for that run. The T28 query and handoff workflow has retired the LayoutML importer, mapping snapshots and the LayoutQ KLayout query backend.

## Local and Remote Layout Data

Put generated inputs, privately collected artifacts, run recipes, and migration checkpoints under the ignored `work/layout/`, `work/decks/`, and `work/output/` directories. Preserve frozen inputs. [Layout index](../README.md)

Configure `site.local.yaml:layout`. The deployment tool checks host, account ownership, and actual paths and uses the existing `layout.lock`. The runner checks configuration and execution directories. [Site configuration example](../../site.example.yaml)

```text
<configured remote_root>/
├─ runtime/        # Active scripts, SKILL/CDL, workspace.json, cds.lib
├─ state/          # Submission receipts, checkpoints, driver logs
└─ evidence/<id>/  # Frozen native inputs, GDS, manifest, and raw reports
```

Configure the OA path separately at `llm_IO/SAR_ADC_T28_LAYOUT`. Resolve historical evidence at its original location and report ambiguity if old and new IDs collide. Keep historical failures, warnings, and paths as recorded. Deployment and native operations share one lock. Leave the runtime used by a running task intact. Use the current entry points for daily work and retain the original scripts for historical reference.

## Run CDAC Verification

From the repository root, run the following commands with `.venv/Scripts/python.exe`. Use new IDs for the two evidence records.

```powershell
python -m Layout check
python -m Layout generate
python -m Layout deploy
python -m Layout physical UNIQUE_PHYSICAL_ID --through pex
python -m Layout status UNIQUE_PHYSICAL_ID
python -m Layout prepare-tt UNIQUE_PHYSICAL_ID UNIQUE_TT_ID
python -m tools.saradc register work/decks/UNIQUE_TT_ID/recipe.json
python tools/saradc/managed/execution.py submit UNIQUE_TT_ID --queue
python -m tools.saradc analyze UNIQUE_TT_ID --queue
python -m tools.saradc collect UNIQUE_TT_ID
```

`physical` verifies existing OA. It creates an immutable submission receipt before launch and rejects IDs with an existing directory or receipt. After an uncertain network response, check the exact ID and `state/<id>.driver`. Diagnose failures at the actual stage. The native flow retains DRC markers, LVS verdicts, matching GDS and PEX digests, exit codes, and warnings. Use the DRC report for the rule verdict. Spectre admission follows the managed execution policy.

`prepare-tt` substitutes actual PEX for the CDAC while retaining the current reference, SAR, and original ten-frame stimulus. This test uses a mixed hierarchy, with the other modules in their pre-layout form. Distributed PEX names internal bottom plates and branch currents differently from the schematic. The analyzer marks the affected settling and overlap-current measurements as unavailable and still measures codes, sampling edges, handshakes, and conversion time. Evaluate precision analog settling with direct evidence. `Layout.tools.analysis.compare_integrated` applies to the historical B comparison.

Use `Layout.tools.simulation.prepare_sim` for the unit or three-unit MOM and `prepare_full_sim` for the standalone full-CDAC step test. The standalone test starts at TOP = 0.45 V and measures bit weights and 0.1% settling. [Layout testbench inputs](../tb/)

## Comparator Module

`design/comparator.il` creates the 11-transistor `sar_strongarm_t28_core/layout`. `design/comparator-wrapper.il` maintains `sar_strongarm_t28/layout` and references the same core through XCORE. The wrapper holds the two native fill masters `sar8_comp_fill_odpo` and `sar8_comp_fill_metal`, built for an earlier core, and is not integrated; the top level owns the comparator's fill. [Fill owners](../specs/fill-policy.md#comparator) The seven electrical ports match the front-end `sar_strongarm_t28`. Three MOM loads on the outputs and clock model the top-level load in pre-layout simulation. Omit these model loads from the layout and top-level LVS reference and use top-level extraction for the actual load.

```powershell
python -m Layout generate --module comparator
python -m Layout deploy
python -m Layout physical UNIQUE_ID --module comparator --through pex
python -m Layout.tools.simulation.prepare_comparator UNIQUE_ID UNIQUE_TT_RUN
# For optional fill sensitivity evaluation, first refresh and verify the fill source.
python -m Layout physical UNIQUE_FILLED_ID --module comparator-filled --through pex
python -m Layout.tools.simulation.prepare_comparator UNIQUE_FILLED_ID UNIQUE_FILLED_TT_RUN
```

`generate --module comparator` creates an independent CDL from the current electrical source and records its SHA256. `physical` normally verifies existing OA. For a new generator-owned core or an explicit rebuild, use `--module comparator --rebuild`. The executor checks the edit lock and checkpoints the current OA cell. Incorporate manual edits into the source or save them in a checkpoint before deciding whether to rebuild. Core geometry changes invalidate earlier fill and post-layout qualification.

For native comparator fill, reuse `fill_cdac.py --module comparator --bounds x0 y0 x1 y1`. Read the bounds from the same GDS and record fill parameters and foundry tool identity in `fill_manifest.json`. Before import, `apply_comparator_fill.py FILL_ID` compares structural digests for the current core and fill source. It checkpoints the wrapper and attaches the fill to that wrapper. This flow serves standalone evaluation only; integration takes no wrapper fill.

`prepare_comparator` defaults to the native MOM and receiving-gate loads of the standalone module. Use `--schematic` for a matching pre-layout control and `--integrated` for the current ten-frame ADC interface test. Both tests default to TT. Use `--corner ssc|ssh|ffc|ffh` to select a condition in `specs/corners.json`; the standalone test moves the MOS section, supply, temperature and rail-level drives and keeps the 0.45 V input common mode. Passive devices use their TT sections. Pair each MOS corner with the matching extraction RC corner (SS: CWORST_T, FF: CBEST_T); `comparator_checks/comp_corner.py` produces them, and the same folder packages the post-layout MC offset, noise and CDAC-kickback fixtures. Run through the managed `register/submit/analyze/collect` flow and record the standalone TT and ADC interface measurement scopes in the respective result contexts. [Comparator evidence](../results/comparator.md)

## SAR and Reference Modules

The single-edge SAR macro `sar8_se_core` holds the five instances of the floorplan SAR block (`XCTRL`, `XSEQ`, `XDONE`, `XPRESET`, `XSAMPLE`). All its leaves are native standard cells, so Innovus places and routes the real netlist and the OA view is built from the routed DEF. Each revision is a new view `layout_rN` in `SAR_ADC_T28_LAYOUT`; an existing view or an edit lock stops the build.

```powershell
python -m Layout.design.sar_single_edge r3 --rows 13 --utilization 0.75
python -m Layout.tools.physical.sar_se_route r3
python -m Layout.tools.physical.sar_se_def r3
# Upload work/layout/sar-se/r3/build.txt and sar-se-leaves.cdl to <remote_root>/state/sar-se-r3, then deploy.
python -m Layout deploy
python -m Layout physical UNIQUE_ID --module sar-se --staging sar-se-r3 --view layout_r3 --rebuild --through pex
python -m Layout physical ANOTHER_ID --module sar-se --staging sar-se-r3 --view layout_r3 --rc-corner cworst_T --through pex
python -m Layout.tools.simulation.prepare_sar_se UNIQUE_ID ssc verify --cdac cworst --revision NEW_ID
```

`sar_se_def` stops if its rendered routing differs from the Innovus stream on any layer. Without `--rebuild`, `physical` verifies the saved view. The extraction runs an LVS comparison first so that the xRC netlist keeps source net names; `prepare_sar_se` saves internal SAR probes at a receiving gate and the analyzers read them under their schematic names. The extraction uses the deck's typical interconnect rules; add `--rc-corner cworst_T` or `cbest_T` to verify the saved view with the foundry corner rules instead (the new evidence ID gets its own extraction). For `verify` stimuli, frame 0 starts from the DC solution and is reported as warm-up outside the verdict. The 28-cell D2 reference sits on the south edge of the paired CDAC. [XREF integration and verification](../results/single_edge_xref.md) The SAR timing and gate-driver layout flows of the previous architecture were removed; their views and dated reports are listed in the layout index. [SAR macro results](../results/sar_se_core.md) · [Interfaces](../specs/interfaces.json) · [Previous architecture](../README.md#previous-architecture)

The XREF flow reads the saved CDAC with `oaq pins`, derives the standard-cell bindings from `single_edge_d2.scs`, and creates fresh driver and integration views. For a new revision, run the B7 pilot through physical verification and the focused transient first. Then repeat the first two commands with a new ID and view, omitting `--pilot`. The ADC short uses the current 45 ns external high phase and single-edge observer. Submit each generated recipe through the managed runner.

```powershell
python -m Layout.design.reference_driver xref-b7-example --pilot --view layout_b7_example
python -m Layout.tools.physical.submit_reference_driver xref-b7-example --default-supplies
python -m Layout.tools.simulation.prepare_reference_driver xref-b7-example xref-b7-tt-example
python -m Layout.tools.analysis.review_reference_routes xref-full-example
python -m Layout.tools.simulation.prepare_reference_driver xref-full-example xref-adc-tt-example --adc --codes 12 127 128 243
```

For standalone verification of the XREF child, submit a fresh ID with `--driver-only --from-stream xref-full-example`. The runner compares the standalone stream digest with the corresponding child in the accepted integration. Use lowercase identities and fresh lowercase view names. The physical runner streams the saved pair, checks the original CDAC geometry hash and compares it to an independent transistor CDL. Omit `--default-supplies` for distributed supply RC. To compare supply modes on identical geometry, submit a fresh physical ID with `--from-stream xref-full-example`.

## Bootstrap Module

`python -m Layout generate --module bootstrap` produces an LVS reference from the current electrical netlist. Verify the work library's existing core with `python -m Layout physical ID --module bootstrap --through pex`. An explicit `--rebuild` uses the deployed Bootstrap generator. The executor checks the OA edit lock and saves a recovery point for the existing work cell.

After LVS and prefill PEX complete, prepare the standalone test with `python -m Layout.tools.simulation.prepare_bootstrap PHYSICAL_ID RUN_ID [--corner ssc]`. Use another RUN_ID and add `--schematic` for the schematic control. Both recipes use managed registration, simulation, analysis, and collection. To run the Bootstrap extraction inside the ADC, add `--bootstrap PHYSICAL_ID` to `prepare_integrated_sim`, or to `tools.saradc.single_edge_lpe` for the cell-LPE and CWORST_T CDAC benches; one extracted channel then serves XBOOTP and XBOOTN beside the extracted CDAC. Both use `Layout/tools/simulation/bootstrap_pex.py`. [Bootstrap pins, interconnect RC, sampling results, and independent OD/PO trial fill](../results/bootstrap.json)

To extract a verified core at a foundry interconnect corner without opening the OA, run `python -m Layout.tools.physical.launch_xref_rc_corner PHYSICAL_ID cworst_T --case bootstrap` (or `cbest_T`). The remote driver `bootstrap_rc_corner.py` rebuilds the source PEX job deck, stops unless it equals the recorded one, and changes only the xRC rules include. DRC and LVS are inherited, and the evidence ID is `PHYSICAL_ID-cworst-t`. [Corner extractions and gate margin](../../results/integration/bootstrap_corner_margin_20261122.md)

The generator draws the adopted four-finger main switch into `layout`. To try a different width, register a sampler candidate `mmain<N>` in `specs/candidates.json`, run `python -m Layout generate --module bootstrap --candidate mmain<N>`, and build it with `--view layout_mmain<N>`; the published view stays untouched. `prepare_bootstrap none RUN_ID --schematic --candidate mmain<N>` simulates its schematic.

A layout revision of the selected sampler goes to its own view `layout_r<N>`, built with `python -m Layout physical ID --module bootstrap --rebuild --view layout_r2`. Its parameters live in the generator's revision table (`bsRevision` in `Layout/design/bootstrap.il`); the netlist and LVS reference are those of `layout`. The runner refuses the build if it would change any other view of the cell. `layout_r2` widens the three guard rings to 0.20 µm and lifts the PMOS row 0.40 µm, which clears the chip latch-up rules LUP.5.2.1/5.2.2 with VIN pad-connected. To check a revised block in its chip context before the chip is re-mastered, `python -m Layout.tools.physical.substitute_master CHIP.gds BLOCK.gds CELL OUT.gds` swaps the master in a chip stream at the GDS level.

The Bootstrap owns its fill (`Layout/design/bootstrap_fill.py`). One dummy-poly stripe sits in every gap between two capacitor units, so no dummy poly lies under a plate finger, and dummy-OD segments under the stripes give about 22 % OD. ODBLK, POBLK and DM1–DM9EXCL cover the whole outline. `bootstrap_fill launch ID SOURCE CORNER` runs DRC, LVS and PEX of the core with the fill flattened in (`bootstrap_filled.py`; the manifest packages like a core extraction, so `prepare_bootstrap` and `prepare_all_extracted --bootstrap` take it). `bootstrap_fill build ID` writes the fill cell `sar_bootstrap_flat_8b_p_fill/layout_r2` and the wrapper `sar_bootstrap_flat_8b_p_filled/layout_r2` (XCORE + XFILL, the core's ports), which the top level places instead of the core. [Revision record](../../results/integration/bootstrap_rev2_20261122.md)

## ADC Core Routing

`Layout/design/toplevel_routes.py` holds the core-internal route geometry on the floorplan centrelines. Check it on a stream of `sar8_adc_core/layout_place` before writing OA. `Layout/design/toplevel_route.py` merges the routes into that stream and runs the native checks in fresh evidence directories on the layout host; it never deploys the shared runtime. `build` creates a new view from `layout_place` under the layout lock and leaves `layout_place` unchanged. Use new IDs for every run. [Routing record](../results/toplevel_route_internal.json)

```powershell
python -m Layout.design.toplevel_route physical BASE_ID --view layout_place --through spice --hcells-from BASE_GDS
python -m Layout.tools.analysis.toplevel_route_precheck BASE_GDS
python -m Layout.design.toplevel_route generate TRIAL_ID --base BASE_GDS
python -m Layout.design.toplevel_route build-script BUILD_ID --cell sar8_adc_core --view NEW_VIEW
python -m Layout.design.toplevel_route build BUILD_ID
python -m Layout.design.toplevel_route physical CHECK_ID --view NEW_VIEW --through spice --hcells-from BASE_GDS
python -m Layout.design.toplevel_route pex-input CHECK_GDS PEX_GDS --kind routed
python -m Layout.design.toplevel_route physical PEX_ID --gds PEX_GDS --stages pex
```

Connectivity compares Calibre's hierarchical layout netlist, with every block master kept as an HCELL, against the planned (block, port) set of each net. Added capacitance is the routed extraction minus the placement extraction with `NET__BLOCK` labels on the landing pins (`pex-input --kind pins`). Resistance and Elmore delay run between the driving and receiving device terminals, so they bound the route-only values from above.

`Layout/design/toplevel_full_routes.py` holds the Stage 4b geometry on top of `layout_route_int`: boundary routes, supply branches with decoupling, the shield tie and the reference network. `Layout/design/toplevel_full.py` builds it into `layout_route_full`. The build copies `layout_route_int`, overwrites only a view that carries its own generatorOwner, and checks that `layout_place` and `layout_route_int` are unchanged. Screen the rectangles locally first. The connectivity check runs on a copy of the stream whose VDD!/0 texts are renamed per supply branch (`branch-labels`); TOP capacitance comes from an extraction of the unlabelled stream.

```powershell
python -m Layout.tools.analysis.toplevel_full_precheck BASE_GDS ROUTES_JSON
python -m Layout.design.toplevel_full build-script BUILD_ID CONTENT_JSON
python -m Layout.design.toplevel_full build BUILD_ID
python -m Layout.design.toplevel_route physical CHECK_ID --view layout_route_full --through spice --hcells-from BASE_GDS
python -m Layout.design.toplevel_full branch-labels CHECK_GDS BRANCH_GDS
python -m Layout.design.toplevel_route physical XTR_ID --gds BRANCH_GDS --stages spice,pex --hcells-from BASE_GDS
python -m Layout.design.toplevel_route physical RAW_ID --gds CHECK_GDS --stages pex
python -m Layout.tools.analysis.toplevel_full_rail --content CONTENT_JSON --series-ohm R --loop analog=OHM pair=OHM sar=OHM[,OHM] --out RAIL_JSON
python -m Layout.tools.analysis.toplevel_full_record --content CONTENT_JSON --build BUILD_ID --checks CHECK_ID --xtr XTR_ID --raw-xtr RAW_ID ...
```

[Stage 4b record](../results/toplevel_route_full.md)

The SAR guard ring (`Layout/design/toplevel_guard_routes.py`) goes into `layout_route_guard` the same way, from `layout_route_full`: `build-script BUILD_ID CONTENT_JSON --stage guard`, then the same checks. `branch-labels` names the ring's own east pin VSS_G, and `toplevel_full_connectivity --guard` expects it. [Guard ring record](../results/toplevel_route_guard.md)

`--stage boot_r2` copies `layout_route_guard` into `layout_route_boot_r2` and remasters the two Bootstrap instances (content key `remaster`: name, origin, orientation, old and new master; the old instance must match exactly). The netlist keeps the filled wrapper as a pass-through subcircuit; the connectivity check resolves a wrapper whose only instance is a block master at its origin. [Bootstrap r2 record](../results/toplevel_route_boot_r2.md)

Core LVS: `python -m Layout.design.toplevel_lvs_source --content CONTENT_JSON --out SOURCE_CDL` writes the source from the block references in their evidence directories; `python -m Layout.design.toplevel_route physical LVS_ID --view layout_route_guard --stages lvs --hcells-from BASE_GDS --source SOURCE_CDL --virtual "VDD!" 0` compares it, and `python -m Layout.tools.analysis.toplevel_lvs_record` records it. [Core LVS](../results/toplevel_lvs.md)

`Layout/design/toplevel_fill.py` fills the routed core by owner (fill policy, "ADC Core Fill Owners"). Each pass runs the foundry OD/PO and metal utilities (`Layout/tools/physical/toplevel_fill_physical.py`, with the same private job edits as every module fill) on a seed stream built locally. The seed carries the context the fill must respect: neighbouring geometry and DMnEXCL/ODBLK/POBLK blocks. Only the generated fill is kept. The passes run in this order:

1. **Pair refill.** The accepted pair seed plus the core's geometry around the pair outline and DMnEXCL over the route entries. `pair` merges the fill into the unmodified seed, repeats DRC, LVS and xRC, and writes a manifest that `prepare_all_extracted gain` accepts.
2. **Bootstrap cell.** Generated in the XBOOTP outline with the XBOOTN neighbourhood mirrored in, placed R0 and MY.
3. **Core pass.** The rest of the outline, with the pair and Bootstrap fill in place and the exclusion cell, without dummy TCD (`--no-tcd`).

`library` assembles the fill hierarchy and `verify` checks it against the routed stream. `build` streams it into OA (new cells only, `-writeMode noOverwrite`) and creates the wrapper with XCORE, FILL and copies of the core's texts. The core views are opened read only and their layout.oa digests are compared. A new core view gets a new revision (`--revision N`: hierarchy `sar8_adc_core_fill<N>`, wrapper view `layout_fill<N>`). Repeat from the pair seed, or reuse the pair and Bootstrap fill where the stream is unchanged around them. `wrapper-gds` assembles the same wrapper as a stream without OA; DRC and xRC can run on it before the OA build.

```powershell
python -m Layout.design.toplevel_fill pair-seed PAIR_FILL_ID --core-gds CORE_GDS
python -m Layout.design.toplevel_fill fill PAIR_FILL_ID --seed SEED_GDS --top sar8_cdac_with_xref --bounds -1.715 -32.465 70.515 25.86
python -m Layout.design.toplevel_fill pair PAIR_ID --fill PAIR_FILL_ID
python -m Layout.tools.simulation.prepare_all_extracted gain tt --xref PAIR_ID --run-id RUN_ID --submit HOST
python -m Layout.design.toplevel_fill boot-seed BOOT_ID --core-gds CORE_GDS
python -m Layout.design.toplevel_fill fill BOOT_ID --seed SEED_GDS --top sar8_adc_core --bounds 49.235 76.2 73.755 101.19
python -m Layout.design.toplevel_fill core-seed CORE_FILL_ID --core-gds CORE_GDS --pair-stream PAIR_GDS --boot-fill BOOT_DIR
python -m Layout.design.toplevel_fill fill CORE_FILL_ID --seed SEED_GDS --top sar8_adc_core --bounds 0 0 122 111 --turbo 8 --no-tcd
python -m Layout.design.toplevel_fill --revision N library LIB_ID --pair-stream PAIR_GDS --boot-fill BOOT_DIR --core-fill CORE_FILL_DIR
python -m Layout.design.toplevel_fill --revision N verify LIB_ID --pair-seed PAIR_FILL_ID --core-gds CORE_GDS
python -m Layout.design.toplevel_fill --revision N wrapper-gds CHECK_ID --library LIB_ID --core-gds CORE_GDS
python -m Layout.design.toplevel_route physical CHECK_ID --gds WRAPPER_GDS --top sar8_adc_core_filled --through pex --stages drc,pex
python -m Layout.design.toplevel_fill --revision N build BUILD_ID --library LIB_ID --core-view CORE_VIEW --expect-core-oa SHA256
python -m Layout.design.toplevel_route physical OA_CHECK_ID --view layout_fillN --top sar8_adc_core_filled --through drc
python -m Layout.tools.analysis.toplevel_fill_record
```

[Stage 5 fill record](../results/toplevel_fill.md)

## Chip Assembly

`Layout/design/chip_routes.py` holds the chip-level geometry in die coordinates; `Layout/design/chip_assembly.py` reads the saved ring read-only, builds `sar8_adc_chip/layout` under the layout lock (it replaces only its own build and guards the ring and core views), exports the ring schematic with si, and starts the chip checks (`Layout/tools/physical/chip_physical.py`: installed chip DRC deck, and LVS with ERC using the ring deck's additions). Status and fetch go through `toplevel_route`.

```powershell
python -m Layout.design.chip_assembly readback READBACK_ID
python -m Layout.design.chip_assembly build BUILD_ID --readback READBACK_ID
python -m Layout.design.chip_assembly ring-cdl CDL_ID
python -m Layout.design.chip_lvs_source --ring-cdl RING_CDL --core-cdl CORE_CDL --out CHIP_CDL
python -m Layout.design.chip_assembly physical CHECK_ID --hcells-from BASE_GDS --source CHIP_CDL
python -m Layout.design.chip_assembly physical RING_ID --top sar8_io_ring --view layout --stages drc
python -m Layout.tools.analysis.chip_record --build BUILD_ID --readback READBACK_ID --checks CHECK_ID --ring-baseline RING_ID --core-baseline CORE_ID
```

[Chip assembly record](../results/chip_assembly.md)

### Chip-Level Objects and the Integrated Chip

The chip-level objects of `io_ring.json` are their own cells in die coordinates, placed at the origin: the output register `sar8_out_reg`, the clamps `sar8_esd_clamps`, the pad decaps `sar8_decap_{analog,pair,sar,dvdd}`, the core VSS ring `sar8_core_vss_ring` and the ADC guard ring `sar8_adc_guard_ring`. `Layout/design/output_register.py` places and routes the register from `design/chip/output_register.scs` with Innovus and converts the routed DEF; `Layout/design/chip_objects_geometry.py` draws the other objects. `Layout/design/chip_objects.py` builds any object cell under the layout lock (it replaces only its own builds, guards named views and can start from a copy of another view), writes each cell's LVS source, and runs the cell checks (`Layout/tools/physical/cell_physical.py`: cell or chip DRC deck, LVS with ERC). `Layout/design/chip_integration.py` builds `sar8_adc_chip/layout_full`, a copy of the partial assembly `sar8_adc_chip/layout` (left unchanged) with the objects and the routes that end on them; `Layout/design/chip_full_source.py` writes its LVS source, the full `chip_netlist`. Hierarchical chip DRC under-reports net-based rules (LUP), so count LUP and ESD with the flat, rule-selected run. Prove signal connectivity with LVS that joins only the supply nets by name. Revision 2 of the clamp and decap cells (`layout_r2`, `chip_objects.py content OBJECT_r2 ...`) holds the pad decaps at their planned capacitance; revision 3 (`layout_r3`, analog decap only, with M5-M7 cfmom_2t) keeps the analog clamp in place; `chip_integration.py --objects-rev 2 --core-cell --core-view` places them with another core view in a new chip view. The register's timing check is `Layout/tools/simulation/prepare_output_register.py` through the managed runner.

```powershell
python -m Layout.design.output_register generate REV
python -m Layout.design.output_register route REV
python -m Layout.design.output_register convert REV
python -m Layout.design.chip_objects content OBJECT CONTENT_JSON
python -m Layout.design.chip_objects build-script BUILD_ID CONTENT_JSON --guard CELL/VIEW ...
python -m Layout.design.chip_objects build BUILD_ID
python -m Layout.design.chip_objects physical CHECK_ID --top CELL --view layout --stages drc,lvs --source CELL_CDL [--std-cells] [--virtual NET ...]
python -m Layout.design.chip_objects physical CHECK_ID --top sar8_adc_chip --view layout_full --stages drc --deck chip --flat --select-prefix LUP.,ESD.
python -m Layout.design.chip_objects physical CHECK_ID --top sar8_adc_chip --view layout_full --stages lvs --source CHIP_CDL --hcells CORE_MASTERS --ring-deck --virtual AVDD AVDD_CORE AVSS AVSS_CORE VSS VSSIO VDDIO DVDD
python -m Layout.design.chip_integration BUILD_ID --readback READBACK_ID
python -m Layout.design.chip_integration BUILD_ID --readback READBACK_ID --view NEW_VIEW --core-cell CELL --core-view VIEW --objects-rev 3
python -m Layout.design.chip_full_source --base PARTIAL_CHIP_CDL --register REGISTER_CDL --contents CONTENT_DIR [--objects-rev 2] --out CHIP_CDL
python -m Layout.design.chip_assembly physical CHECK_ID --view layout_full --hcells-from BASE_GDS --source CHIP_CDL
python -m Layout.tools.analysis.chip_objects_record --chip-build BUILD_ID --chip-checks CHECK_ID
python -m Layout.tools.analysis.chip_rail_recheck
python -m Layout.design.chip_seal_ring BUILD_ID
python -m Layout.tools.analysis.chip_periphery launch EXTRACTION_ID CHIP_GDS --source-evidence CHECK_ID [--flatten PCLAMPC_H_G]
python -m Layout.tools.analysis.chip_periphery fetch EXTRACTION_ID
python -m Layout.tools.analysis.chip_periphery report EXTRACTION_ID
python -m Layout.tools.analysis.chip_periphery clamp-bus EXTRACTION_ID --record VIEW
python -m Layout.design.chip_clamp_feed BUILD_ID
python -m Layout.design.chip_landing_m1 BUILD_ID
```

The die is the lab's 1 x 1 mm seal ring (`io_ring.json` `seal_ring`, from the shared `sealring` library), added by `Layout/design/chip_seal_ring.py` to a copy of the current chip view. The chip deck then runs with its seal-ring checks satisfied. `chip_periphery.py` extracts the chip-level wiring with every block, pad cell and object kept as an xcell (`Layout/tools/physical/toplevel_wiring_xcell.py` with `supplies.txt`, so AVDD/VDD are extracted too). Fetch the run's manifest and `pex/` files into `work/layout/chip-periphery/EXTRACTION_ID/`, with the stream as `candidate.gds`. `report` then gives two-point resistances and capacitance per route against `constraints.json` `stage6_supply_model`, and writes the Stage 2 VIN and output-path netlists. For wire bond, the clamp connections are checked against the DRM's ESD current density (ESD.CD.1gU, 1.3 A, as app note 8.7.3 / 10.7.3 asks): `chip_objects_record.clamp_feed_current_density` counts the drop vias and the M4 bar current. `landing_current_density` sums the pad-pin fingers each supply landing uses. `chip_landing_m1.py` adds the M1 fingers at the AVSS landings to a copy of the chip view. The note sets no pad-to-clamp resistance limit for wire bond; Table 10.1 is between IO power/ground cells. The pad-to-clamp resistance is still worth extracting for information. It needs the clamps' own metal and transistors: launch with `--flatten PCLAMPC_H_G` and run `clamp-bus`, because an xcell would tie the clamp's terminal strips into one ideal node. `chip_clamp_feed.py` adds the straps and drop stacks along the clamp bars to a copy of the chip view.

[Chip objects record](../results/chip_objects.md)

## Applicability of Results

`current.json` ties the floorplan, physical evidence, and TT runs to their limitations. `check` compares electrical source and planning dependency digests and reports stale evidence when the source changes. `render` refreshes the planning projection. Prior qualification continues to refer to its original dependencies. Stream out and repeat native verification after editing OA. Local file digests cover local inputs only. [Current evidence](../results/current.json)

A core change affects fill, PEX, and post-layout results. A fill change affects density and parasitics. A top-level routing change affects top-level extraction and electrical evidence. Retain dated results. Report DRC, LVS, function, timing, parasitics, and terminal voltages at their measured scope. Treat unallocated floorplan budgets as open items.

## Recovery and In-Place Iteration

Edit source files in place and use Git for committed history. The layout files were untracked at the start of the migration. Use `work/layout/restructure/source-before.zip` and `checkpoint.json` as the original recovery point. `relocation.json` in the same directory maps the move. Preserve the original recovery point.

OA uses native checkpoints. The backup in the manifest predates the core/fill split. Before each later OA write, check which views are open or unsaved and who owns the edit. Save a supported OA checkpoint and the cell/GDS identity. Restore only the authorized work cell and protect other modules and unsaved user edits. After restoring, check geometry, ports, and any required DRC or LVS. [Native backup record](../design/manifest.json)

The current policy is `oa_owned_current`, with `allow_regeneration: false` by default. OA owns manual edits. After accepting an edit, incorporate it into a patch or parameters and verify the rebuild, or continue with the verified OA checkpoint. Run full batch SKILL containing `exit(0)` in batch mode. Iterate in the established library and cell names.

For fill-group diagnosis, use `run_physical.py ... --source-stream ID --omit-fill metal|odpo`. It changes the stream inside the run directory. Run full DRC, LVS, and PEX, retain density failures, and label the stream as diagnostic. Bind numerical parasitic analysis to a real completed source and run it as a managed analysis-only task.
