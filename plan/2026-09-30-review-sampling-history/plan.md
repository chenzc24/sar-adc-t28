# Sampling review flow update

## Goal and ownership
Show the reviewed Bootstrap causal history, distinguish lumped-load and full-CDAC
fixtures, and branch into physical GMAIN isolation and physical clamp work.
Keep theory allocations and static Canvas sample intact.

Dirty state: unrelated untracked bootstrap-t28-hold-pulldown plan and
screen_bootstrap_t28_hold_pulldown.py belong to ongoing circuit work; preserve.
Owned: review/flows.json, node-notes.yaml, evidence.yaml, model.yaml,
source-lock.json, evidence-baseline.json, app/app.js, app/style.css;
this plan and plan/log.md. Generated output/review is disposable.
Also own verification/review/test_build.py: replace positional record lookups
with stable IDs after adding records exposed order-dependent test fixtures.
Remote OA owned objects: none. Circuit sources, PDK, reports and topology sample
are read-only. No simulation, push or live Canvas connection in this target.

## Implementation and validation
Read isolate-before-reset, turnoff-charge and full-CDAC isolation reports.
Curate evidence and update only relevant baselines after review. Consolidate
sampling into key transitions with historical details and two current branches.
Update CDAC/global summaries consistently. Reuse existing figures and topology
entry points without claiming the abstract sample is the current T28 DUT.
Build/check, focused review tests, JS syntax, diff check; browser smoke of flow,
details, figures and snapshot. Confirm no fixture-to-fixture improvement claims.
Record outcome in log; local commit: feat(review): trace sampling experiments and current blockers.

## Outcome
Eight key sampling nodes now lead to parallel GMAIN and clamp work, then joint
acceptance. Historical evidence is folded into node details with condition/result
tables; lumped-load A and full-CDAC B fixtures remain distinct. Global/CDAC state
updated consistently. Added three reviewed records and source fingerprints.
22 tests, formula regression, build/check, JS syntax and diff check pass.
Browser verified the full-CDAC table, figure dialog, static topology entry and
two-branch layout; no console errors. Preview: output/review/sampling-flow-preview.png.
Concurrent circuit work added docs/design_log.md and a separate plan/log.md entry;
preserve those changes and stage only this target's log hunk. No OA writes or push.
