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

`design/comparator.il` creates the 11-transistor `sar_strongarm_t28_core/layout`. `design/comparator-wrapper.il` maintains `sar_strongarm_t28/layout` and references the same core through XCORE. The wrapper owns the two native fill masters `sar8_comp_fill_odpo` and `sar8_comp_fill_metal`. The seven electrical ports match the front-end `sar_strongarm_t28`. Three MOM loads on the outputs and clock model the top-level load in pre-layout simulation. Omit these model loads from the layout and top-level LVS reference and use top-level extraction for the actual load.

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

For native comparator fill, reuse `fill_cdac.py --module comparator --bounds x0 y0 x1 y1`. Read the bounds from the same GDS and record fill parameters and foundry tool identity in `fill_manifest.json`. Before import, `apply_comparator_fill.py FILL_ID` compares structural digests for the current core and fill source. It checkpoints the wrapper and attaches the fill to that wrapper. Resolve ownership when integrating modules and the top level.

`prepare_comparator` defaults to the native MOM and receiving-gate loads of the standalone module. Use `--schematic` for a matching pre-layout control and `--integrated` for the current ten-frame ADC interface test. The integrated test defaults to TT. Use `--corner ssc|ssh|ffc|ffh` to select a condition in `specs/corners.json`. Passive devices use their TT sections. Run through the managed `register/submit/analyze/collect` flow and record the standalone TT and ADC interface measurement scopes in the respective result contexts. [Comparator evidence](../results/comparator.md)

## SAR timing core and filled wrapper

Use `python -m Layout generate --module sar-timing --quiet-stages N` to reproduce a standard-delay placement and its independent transistor-level reference, with `N` equal to 5, 6 or 9. For five DEL250 cells followed by a DEL200, pass `--quiet-stages 6 --quiet-final-ps 200`. The five- and six-stage generators place the sample-enable cells alongside QUIET on 13 rows. Each placement gets its own Innovus routing abstract, detailed route and extracted reference. The nine-stage generator reproduces the earlier route inputs. The integrated testbench preparation reads the delay-cell variant from the native LVS reference and selects the external-cell LPE model from the macro extraction corner. [Stage comparison](../results/sar_quiet_lpe_20261119.md) · [Nine-stage baseline](../results/sar_std_static_candidate_c_20261119.md)

Generate compact placement and source-bound nets with `python -m Layout generate --module sar-timing`. The saved OA views are listed in the layout manifest. The core uses native standard cells, custom RC banks and metal added by Innovus. The wrapper adds the OD/PO and metal density cells. The signoff evidence contains the pre-ECO routing abstract, Innovus Tcl, routed DEF, metal repairs, final intent, fill inventory and audit in its `review/` directory.

For the revised bit rows, local decoupling and distributed supply network, run `python -m Layout generate --module sar-timing --array`. The generated `work/layout/sar-refinement/seed` contains the placement, independent array CDL, native helpers and electrical intent. Build the private OA seed, stream it with its terminal readback, then run `python -m Layout.tools.physical.sar_route INTENT CHECKPOINT ROUTE_DIR`. Run the SAR Innovus Tcl in that directory and use `python -m Layout.tools.physical.sar_overlay INTENT CHECKPOINT ROUTE_DIR` to check connectivity and emit the native route geometry. Run the generated `apply-route.il` with `sar_timing.il` and the staging `cds.lib` available, and set `SAR_ROUTED_VIEW` to a fresh private view. The recorded seed and route hashes identify the physical inputs. Regenerate the abstract and detailed route whenever the placement changes.

Use the array CDL for transistor LVS and request both rails in xRC. The revised flow checks that each rail contributes extracted resistors. The filled wrapper exposes the continuous M5 headers for multiple top-level connections. Keep the foundry metal fill and generate the resistor-channel diffusion fill from the verified utility output using `Layout.tools.physical.sar_resistor_fill`. The full-chip run owns the final M9 sliding windows. [Physical comparison and supply measurements](../results/sar_timing_refinement.md)

```text
python -m Layout physical UNIQUE_CORE_ID --module sar-timing --through pex
python -m Layout physical UNIQUE_FILLED_ID --module sar-timing-filled --through pex
python -m Layout.tools.analysis.check_sar_timing FINAL_INTENT_JSON CORE_CHECKPOINT --require-complete
python -m Layout.tools.simulation.prepare_sar_timing FILLED_XRC_DIR FILLED_CHECKPOINT RUN_ID --core CORE_CHECKPOINT --corner ssc
```

Use the managed runner to register, submit, analyze and collect the generated recipe at TT, SS cold/hot and FF cold/hot. For each run, its extracted netlist, raw stream digest, receiver coordinates and source hashes are bound in the receipt. Device usage is the union of legal standard-cell sites and native PCell bounds. The filled view is the interface for top-level integration. [Verified OA views, timing and scope](../results/sar_timing.md)

## Bootstrap Module

`python -m Layout generate --module bootstrap` produces an LVS reference from the current electrical netlist. Verify the work library's existing core with `python -m Layout physical ID --module bootstrap --through pex`. An explicit `--rebuild` uses the deployed Bootstrap generator. The executor checks the OA edit lock and saves a recovery point for the existing work cell.

After LVS and prefill PEX complete, prepare the standalone TT test with `python -m Layout.tools.simulation.prepare_bootstrap PHYSICAL_ID TT_ID`. Use another TT_ID and add `--schematic` for the schematic control. Both recipes use managed registration, simulation, analysis, and collection. [Bootstrap pins, interconnect RC, sampling results, and independent OD/PO trial fill](../results/bootstrap.json)

## Applicability of Results

`current.json` ties the floorplan, physical evidence, and TT runs to their limitations. `check` compares electrical source and planning dependency digests and reports stale evidence when the source changes. `render` refreshes the planning projection. Prior qualification continues to refer to its original dependencies. Stream out and repeat native verification after editing OA. Local file digests cover local inputs only. [Current evidence](../results/current.json)

A core change affects fill, PEX, and post-layout results. A fill change affects density and parasitics. A top-level routing change affects top-level extraction and electrical evidence. Retain dated results. Report DRC, LVS, function, timing, parasitics, and terminal voltages at their measured scope. Treat unallocated floorplan budgets as open items.

## Recovery and In-Place Iteration

Edit source files in place and use Git for committed history. The layout files were untracked at the start of the migration. Use `work/layout/restructure/source-before.zip` and `checkpoint.json` as the original recovery point. `relocation.json` in the same directory maps the move. Preserve the original recovery point.

OA uses native checkpoints. The backup in the manifest predates the core/fill split. Before each later OA write, check which views are open or unsaved and who owns the edit. Save a supported OA checkpoint and the cell/GDS identity. Restore only the authorized work cell and protect other modules and unsaved user edits. After restoring, check geometry, ports, and any required DRC or LVS. [Native backup record](../design/manifest.json)

The current policy is `oa_owned_current`, with `allow_regeneration: false` by default. OA owns manual edits. After accepting an edit, incorporate it into a patch or parameters and verify the rebuild, or continue with the verified OA checkpoint. Run full batch SKILL containing `exit(0)` in batch mode. Iterate in the established library and cell names.

For fill-group diagnosis, use `run_physical.py ... --source-stream ID --omit-fill metal|odpo`. It changes the stream inside the run directory. Run full DRC, LVS, and PEX, retain density failures, and label the stream as diagnostic. Bind numerical parasitic analysis to a real completed source and run it as a managed analysis-only task.
