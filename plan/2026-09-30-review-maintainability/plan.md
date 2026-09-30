# Review data and maintenance boundaries

Clean starting tree. Own review/, scripts/review/, verification/review/, this
plan and bounded plan/log.md entry. No remote/OA/simulation work. Specs and
experimental reports remain read-only. Preserve UI and existing conclusions.

Replace runtime graph composition with one declarative graph source; resolve
analysis, figure, evidence and topology references at build time. Isolate display
formatting from rendering. Separate static diagram adapter from topology analysis.
Add read-only impact reporting for evidence-source and topology terminal changes,
with an explicit reviewed connectivity baseline. Do not auto-approve changed data.
Validate reference failures, migration equivalence, evidence impact and MN11 gate
mutation in memory; browser navigation/topology smoke, then bounded local commit
refactor: separate review data rendering and impact checks. No push.

## Outcome

- Replaced runtime graph composition and obsolete flow definitions with flows.json.
  A mechanical migration comparison preserved all 31 node texts/positions and
  all edges, apart from an equivalent evidence-token substitution.
- Build resolves 24 analysis references, figure/evidence IDs and topology topic
  entries; rejects missing/orphan references. Rendering consumes compiled data.
- Display formatting is separate from rendering; static diagram coordinate data
  and rendering adapter are separate from circuit-phase/topic analysis.
- Read-only --impact reports source/evidence changes and affected nodes; reviewed
  connectivity baseline supports changed-terminal and neighboring-net analysis.
  Normal builds mark affected nodes; changed circuit/image hashes still block
  unreviewed mappings. No baseline auto-approval or live Canvas implementation.
- 22 focused tests, formula regression, JS checks and build pass. MN11 gate-change
  and fast_ab observation-change tests run in memory only; real inputs unchanged.
  Browser verified five branch entries, analysis counts, adapter/device reverse
  selection, no console errors. Screenshot output/review/refactor-preview.png.
- During work another task created untracked bootstrap-t28-hold-pulldown plan;
  preserved without inspection/modification. No new circuit conclusions imported.
- Updated maintenance guide documents exact edit locations and manual review
  responsibilities. Local commit only; no push.
