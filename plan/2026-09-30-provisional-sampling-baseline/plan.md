# Provisionally freeze the current sampling baseline

User decision: accept the current version provisionally and stop iterating
for now. Clean start on exp/top-plate-gmain-t28 at 522aa0f, already pushed.

Own this plan and bounded edits to docs/sampling_architecture_status.md,
docs/top_plate_pgate_driver.md, docs/design_log.md and plan/log.md.
Remote OA owned: none. All circuit scripts, decks, results, specifications,
PDK and OA remain read-only. This is a documentation-only acceptance record,
not a simulation, circuit change, production release or budget rewrite.

Record exact circuit revision, topology/size/timing retention, measured
five-point nominal error and the provisional exception to the original
0.439-mV allocation. Preserve reset/well and ideal-control limitations.
Defer further experiments until the user resumes them; do not interpret
provisional acceptance as reliability signoff or a new universal error limit.

Validate the complete scoped diff and git diff --check. Commit locally as
docs: freeze provisional top-plate sampling baseline. No push or merge.
