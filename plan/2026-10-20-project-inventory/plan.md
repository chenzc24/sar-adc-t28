# Project progress and design inventory

## Goal

User requests a clear account of all design progress and the Virtuoso/local
files. Create a navigable project overview and exhaustive source/cell index,
distinguishing active eight-bit work, candidates, historical ten-bit material,
uncommitted parallel experiments and generated evidence. No circuit redesign,
file relocation/deletion, library categories, connection repair or new run.

## Ownership and initial state

Branch exp/cdac-flat8-device, HEAD efea0db at initial read. The existing
untracked cdac10_dualrail config/VA/scripts/tests/plan belong to another target;
preserve and describe them as work in progress, not a selected architecture.
Other targets may continue: bind the inventory to its capture time and commit.
During capture, unrelated cdac8 restore-comparison and sar8 two-cycle observation
files/report edits appeared. Preserve them; list as ongoing, do not stage them.

Owned local paths: this plan; scripts/maintenance/project_inventory.py;
docs/project_status.md; docs/inventory/2026-10-20/; a bounded README navigation
link; a bounded plan/log.md entry after checking concurrent modifications.
Generated audit data: output/project_inventory/2026-10-20/.

Remote OA owned: none. SAR_ADC_T28 is read-only. PDK, other libraries, all
schematics/symbols/VA/maestro/layouts, user windows and pending experiments are
read-only. Use existing t28_io only; no restart, kill, form dismissal or edits.

## Method

1. Inspect current spec, reports, manifest, plan/log and source directories.
2. Read-only bridge status, exact library/tech verification and full cell/view
   metadata listing using documented bridge methods. Stop repeated CIW retries
   if unavailable; explicitly label cached/manifest evidence rather than claim
   a live audit. No netlisting/simulation or schematic mutation.
3. Inventory tracked and untracked project sources with Git state, excluding
   environments/caches and per-run raw dumps. Summarize generated output roots
   separately. Compare actual OA objects with the manifest, keeping planned
   and local-only entries separate from existing views.
4. Record progress by module and modeling level; map OA cells to local source,
   config/report and evidence roots. Preserve inactive experiments.
5. Write the project entry and full local/cell lists; verify links, coverage,
   counts, syntax, JSON/CSV parsing and diff; append factual maintenance log.

## Completion

Deliver overview plus complete named source/cell lists, with evidence freshness,
selected-line boundaries and pending integration stated. All existing source
and remote design objects remain untouched. Local scoped documentation/tooling
commit per repository policy; no push, no experience extraction.

## Result

Live t28_io status and read-only library queries succeeded. Library binding is
the expected SAR_ADC_T28/tsmcN28 at its project path. Captured 170 actual cells,
159 schematic, 114 symbol and 11 veriloga views; no layout/maestro view found.
Manifest comparison: 143 entries, 42 actual cells unregistered, 15 registered
planned/local-model entries absent from remote. Eight bounded schematic reads
confirm the native-analog/VA-control versus native-async/ideal-plant split.

Added the overview, complete linked local/cell Markdown lists, CSV tables,
output roots, timestamped snapshot and reproducible read-only capture/check
tool. Source count is timestamped in snapshot.json, not assumed constant while
parallel targets continue. Read-only remote capture time is kept distinct from
later local refresh. No categories, cells, simulations or old files changed.
Focused table/count/uniqueness/link checks, compile and diff checks pass.
