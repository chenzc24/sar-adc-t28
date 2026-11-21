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
python -m Layout.tools.simulation.prepare_sar_se UNIQUE_ID ssc verify --cdac cworst --revision NEW_ID
```

`sar_se_def` stops if its rendered routing differs from the Innovus stream on any layer. Without `--rebuild`, `physical` verifies the saved view. The extraction runs an LVS comparison first so that the xRC netlist keeps source net names; `prepare_sar_se` saves internal SAR probes at a receiving gate and the analyzers read them under their schematic names. The extraction currently uses the typical interconnect rules. The 28-cell D2 reference sits on the south edge of the paired CDAC. [XREF integration and verification](../results/single_edge_xref.md) The SAR timing and gate-driver layout flows of the previous architecture were removed; their views and dated reports are listed in the layout index. [SAR macro results](../results/sar_se_core.md) · [Interfaces](../specs/interfaces.json) · [Previous architecture](../README.md#previous-architecture)

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

After LVS and prefill PEX complete, prepare the standalone test with `python -m Layout.tools.simulation.prepare_bootstrap PHYSICAL_ID RUN_ID [--corner ssc]`. Use another RUN_ID and add `--schematic` for the schematic control. Both recipes use managed registration, simulation, analysis, and collection. To run the Bootstrap extraction inside the ADC, add `--bootstrap PHYSICAL_ID` to `prepare_integrated_sim`; one extracted channel then serves XBOOTP and XBOOTN beside the extracted CDAC. [Bootstrap pins, interconnect RC, sampling results, and independent OD/PO trial fill](../results/bootstrap.json)

The generator draws the adopted four-finger main switch into `layout`. To try a different width, register a sampler candidate `mmain<N>` in `specs/candidates.json`, run `python -m Layout generate --module bootstrap --candidate mmain<N>`, and build it with `--view layout_mmain<N>`; the published view stays untouched. `prepare_bootstrap none RUN_ID --schematic --candidate mmain<N>` simulates its schematic.

## Applicability of Results

`current.json` ties the floorplan, physical evidence, and TT runs to their limitations. `check` compares electrical source and planning dependency digests and reports stale evidence when the source changes. `render` refreshes the planning projection. Prior qualification continues to refer to its original dependencies. Stream out and repeat native verification after editing OA. Local file digests cover local inputs only. [Current evidence](../results/current.json)

A core change affects fill, PEX, and post-layout results. A fill change affects density and parasitics. A top-level routing change affects top-level extraction and electrical evidence. Retain dated results. Report DRC, LVS, function, timing, parasitics, and terminal voltages at their measured scope. Treat unallocated floorplan budgets as open items.

## Recovery and In-Place Iteration

Edit source files in place and use Git for committed history. The layout files were untracked at the start of the migration. Use `work/layout/restructure/source-before.zip` and `checkpoint.json` as the original recovery point. `relocation.json` in the same directory maps the move. Preserve the original recovery point.

OA uses native checkpoints. The backup in the manifest predates the core/fill split. Before each later OA write, check which views are open or unsaved and who owns the edit. Save a supported OA checkpoint and the cell/GDS identity. Restore only the authorized work cell and protect other modules and unsaved user edits. After restoring, check geometry, ports, and any required DRC or LVS. [Native backup record](../design/manifest.json)

The current policy is `oa_owned_current`, with `allow_regeneration: false` by default. OA owns manual edits. After accepting an edit, incorporate it into a patch or parameters and verify the rebuild, or continue with the verified OA checkpoint. Run full batch SKILL containing `exit(0)` in batch mode. Iterate in the established library and cell names.

For fill-group diagnosis, use `run_physical.py ... --source-stream ID --omit-fill metal|odpo`. It changes the stream inside the run directory. Run full DRC, LVS, and PEX, retain density failures, and label the stream as diagnostic. Bind numerical parasitic analysis to a real completed source and run it as a managed analysis-only task.
