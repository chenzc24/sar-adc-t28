# Consolidate review into branch maps

## Scope and ownership

User requests the next iteration: consolidate entries into a global map and
module branches, with theory, progress and evidence together inside nodes.
Initial branch: exp/bootstrap-protected-eval. Untracked bootstrap-isolate-before-reset
plan and characterization script belong to concurrent circuit work; preserve.
Own review/app/, review/README.md, this plan, and a bounded plan/log.md entry.
Read-only: review graph/evidence/spec data and all circuit sources. Remote OA: none.
No simulation, Canvas connection or source-lock acknowledgment in this target.

## Implementation and checks

Reuse existing extracted facts and graph renderer. Replace separate tabs, block
map and detail panel with one overview and five module branches. Combine nodes
where useful; detail expands inside its node. Canvas placeholder belongs to the
module node. Retain allocation versus derivation and historical evidence limits.
Check build/data tests, JS parsing, graph navigation, inline expansion, browser
errors and narrow overflow. Generated artifacts stay in output/review/.
Review owned diff, log outcome and commit locally as feat: consolidate review
into module branch maps. No push.

## Outcome

Implemented one overview and five module branches using existing curated facts.
Inline details and per-module Canvas slots replace separate tabs/panels. Fixed
navigation to render immediately and preserve browser history. Thirteen data
tests and shared formula tests pass; JS parses. Browser checked all branch
entries/returns, Bootstrap explanations/Canvas expansion and 390px local diagram
scrolling without page overflow; no browser errors. No OA or evidence updates.
Concurrent isolate-before-reset target committed during this work; its new report
is outside this presentation-only snapshot and was not silently incorporated.
Local commit only. Preview remains on port 8765.
