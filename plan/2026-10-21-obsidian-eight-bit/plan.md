# Fill the five reader-facing eight-bit notes

## Goal

Fill the user's Head, Spec, Result, Revision and Wrap-up & Experience notes
with concise Chinese material covering only the eight-bit flat SAR line.
Keep specifications, measured results, design decisions and reusable lessons
distinct and linked. Preserve the user's filenames and five-note structure.

## Starting state and ownership

Branch exp/cdac-flat8-device, HEAD e9e92ad. The user renamed three original
notes to Head/Spec/Revision and created empty Result/Wrap-up notes. The request
authorizes filling/reorganizing these notes; their observed contents have been
read in full. Retain their restructuring, recording the old-path deletions in
the scoped commit rather than restoring obsolete copies.

Unrelated dirty work: scripts/integration/b_sine_main_w_analyze.py and untracked
docs/b_sine_main_w.md; cdac10_dualrail config, VA modules, plan, scripts and
verification. All remain read-only and excluded. Main-W experiments have a
separate owner; only finalized baseline evidence is summarized. Do not launch,
monitor, qualify or adopt those experiments as part of this documentation task.

Owned local paths:

- Obsidian_docs/Head.md, Spec.md, Result.md, Revision.md,
  Wrap-up & Experience.md, and the three superseded original note paths.
- README.md: repair the vault entry to Head.md only.
- This plan and one append to plan/log.md.

Remote OA owned objects: none. Read-only: all engineering reports, configs,
models, waveforms, verification records, PDK, OA, other plans, personal vault
and Obsidian settings. No simulator, GUI, plugin or remote operations.

## Implementation

1. Read active eight-bit specs and the reports supporting each selected result.
2. Head: architecture, current implementation/ideal boundaries, status, links.
3. Spec: goals, budget derivation, staged methods and measurement definitions.
4. Result: concise condition-bound comparisons, accepted evidence and open gates.
5. Revision: eight-bit design decisions, failed hypotheses and corrections.
6. Wrap-up: evidence-linked reusable lessons requested by the user.
7. Repair README navigation and append factual maintenance record.

## Validation and artifacts

Five existing Markdown filenames remain the only reader-facing artifacts;
no copied raw reports, new plots, scripts or template hierarchy. Read all notes
back; verify strict UTF-8/YAML, wiki filenames and heading anchors, existence
of repository-relative evidence paths, numerical consistency with sources and
eight-bit-only scope. Run git diff --check and inspect the complete staged
diff. Recheck dirty state before staging; preserve unrelated/concurrent edits.

## Commit policy

Scoped local commit: docs: organize eight-bit Obsidian design notes.
No push requested. Snapshot identifies finalized baseline evidence, not live
run progress. No new circuit qualification or OA verification claimed.

## Outcome and validation

Filled the five user-named notes. Head now holds the current implementation
and navigation; Spec contains eight-bit goals, budget arithmetic, model stages
and measurement definitions; Result separates conditions/abstraction levels;
Revision begins at eight-bit migration; Wrap-up records six evidence-linked
lessons. Repaired the README entry. Prior history remains in Git and the
unchanged engineering reports; no ten-bit narrative was carried into the vault.

Read back all five notes. Strict UTF-8 and YAML parsing pass; all 31 wiki links
including heading anchors resolve; all 19 unique source paths exist. Checked
LSB, 0.25-LSB threshold and RSS arithmetic; eight-bit-only scope and paired math
delimiters pass. git diff --check passes. Final scoped staging/diff review and
local commit follow; no simulation or GUI/remote changes.

Source nuance: b_sine_period/main-W prose says 512 independent MOM units, but
the saved B export output/b_sine_period/exports/current/input.scs contains 18
cfmom groups with multi=1..128. The notes accurately distinguish the nominal
grouped joint circuit from the earlier independent-unit mismatch test. The
engineering reports are read-only in this task and were not silently edited.

Concurrent changes also appeared in plan/2026-10-21-b-sine-main-w/plan.md and
scripts/integration/b_sine_main_w.py. They remain outside this target, along
with the previously identified analysis and cdac10_dualrail files. No main-W
candidate results, completion claims or OA adoption are introduced here.
