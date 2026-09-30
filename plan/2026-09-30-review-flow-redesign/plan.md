# Simplify the review workbench into block-linked flow diagrams

## Goal

Respond to the user's review: remove the document-centric UI, replace flat
metric/workflow cards with explicit connected flow diagrams, and make circuit
block ownership visible. Extract explanations into self-contained panel content.
No document links, raw document viewer, hashes or source paths in the frontend.

## Initial state and ownership

- Branch `exp/bootstrap-protected-eval`, v1 committed at `879cabc`.
- Unrelated untracked bootstrap fast-A/B plan and characterization script are
  preserved and excluded; no dependency overlap with this presentation change.
- Owned: `review/`, `scripts/review/`, `verification/review/`, this plan,
  bounded README and `plan/log.md` entries.
- Generated: ignored `output/review/`, existing loopback preview port 8765.
- Remote OA owned: none. No Canvas connection, simulation or circuit change.
- Read-only inputs: existing specs, reports and circuit records. Keep source
  fingerprints behind the build-time validation boundary, not as UI content.

## Implementation

1. Replace the sidebar/dashboard with an always-visible functional ADC block
   diagram and two connected views: derivation tree and workflow tree.
2. Give graph nodes explicit block ownership, real arrows, short inline result
   text and optional compact detail. Selecting a circuit block highlights the
   relevant nodes in both views.
3. Keep the distinction between provisional allocation, conditional theory,
   measured failure and planned experiments without repeating long warnings.
4. Remove document/source UI and embedded raw documents. Keep extracted facts,
   units and assumptions in the panel; backend evidence provenance remains.
5. Preserve a small Canvas slot only. Validate edges, block associations and
   absence of repository document text/links in the generated public payload.

## Validation and commit

Focused data/formula regression; JS syntax and Python compile; browser checks
for both flow graphs, block-to-node highlight, node detail, no source links,
desktop/narrow layout and diagram edge endpoints. Update factual maintenance
log, review owned diff, local commit `feat: simplify review into block-linked
flow diagrams`. Do not push. Leave the refreshed preview open for review.

## Concurrent evidence update

During implementation, the separate bootstrap A/B target was committed as
`e0c12e7`. Its report is now an additional read-only input. Extract its completed
eight-variant findings into the panel so the new workflow does not call those
experiments unperformed. The independent real-T28 main-gate implementation
remains planned; ideal relay bounds are explicitly not transistor acceptance.
No files owned by that circuit target were edited.

## Outcome and validation

- Replaced dashboard cards/sidebar/provenance dialogs with a functional ADC
  block map, global derivation/workflow diagrams and two Bootstrap subgraphs.
  Explicit SVG arrows branch/merge; selected nodes highlight their real
  functional circuit blocks. Short extracted explanations expand in-panel.
- Public HTML/data contains no repository documents, document paths, raw
  source text or netlist hashes. Internal reviewed-source fingerprints remain
  available to the build validator only. Removed budget scenario UI for clarity.
- Thirteen Python contract tests pass, including flow block/edge validation
  and public-payload document exclusion. Shared formula regression passes;
  Python compiles and browser JS parses.
- Browser verified all four graph states, node-to-block highlighting, block
  navigation, panel explanation and both tabs. Bootstrap path geometry check
  found no edge crossing an unrelated node. The 390px layout uses bounded
  graph-local scrolling with no document overflow; no browser errors/warnings.
- OA/Canvas unmodified, no simulator executed. Refresh the existing port 8765
  preview; commit locally only, do not push.
