# Node analysis and figure entries

User requests concise reasons at every module-branch node, existing simulation
figure entries and improved layout. Own review/, scripts/review/, verification/review/,
this plan and a bounded plan/log.md entry. Generated output/review remains ignored.
Initial branch exp/bootstrap-protected-eval; untracked bootstrap-turnoff-charge-screen
plan/script belong to other work and are preserved. OA owned: none. Specs, reports,
existing plot artifacts and circuit files are read-only. No new simulations.

Curate 2–3 explanatory points per branch node. Bind available reviewed plots to
specific nodes, label analytical plots versus transistor results and scope. Embed
allowlisted image artifacts only; missing files must not create broken controls.
Improve type sizes, spacing, constrained branch width and node actions. Keep graphs.
Validate data/build, missing/unsafe figure inputs, JS syntax, all node coverage,
figure opening/closing, desktop/narrow layout and browser errors. Save screenshot.
Review bounded diff and commit locally feat: add node analysis and result figures.
No push; no evidence refresh from ongoing circuit experiments.

## Outcome

- Added 24 explicitly curated node analyses (2–3 points each) and six reviewed,
  hash-pinned plots. Four are analytical envelopes/sensitivity, two are transistor
  screening/phase plots. Captions distinguish coverage; no new simulation claims.
- Available plots are embedded in the local HTML. Missing files omit controls;
  changed hashes, unsafe paths and active SVG content fail the build.
- Improved module typography, compact two-column root, aligned branch cards and
  narrow single-chain layout. Figure dialog retains context and keyboard support.
- Seventeen Python tests and formula regression pass; Python/JS syntax and diff
  checks pass. Browser verified all 24 node lists, six image loads, keyboard open/
  close/Escape/navigation and narrow overflow. Automated pointer clicks did not
  actuate even native details in this browser session; pointer acceptance remains
  unconfirmed, not claimed as passing. Viewport override reset afterward.
- Screenshots output/review/node-analysis-preview.png and figure-preview.png.
  No remote changes. Local commit only; concurrent circuit work preserved.
