# Target Title

## Goal

State the concrete objective and measurable completion condition.

## Dirty-State Note

Start state from `git status --short --branch`:

```text
<paste status>
```

State whether the worktree is clean or why unrelated dirty files are safe.

## Local Owned Files

- `<tracked paths this target may edit>`

## Remote OA Owned Objects

- `<library/cell/view this target may mutate, or none>`

## Read-Only State

- `<local paths, remote libraries/cellviews, PDK, generated artifacts>`

## Shared Dependencies

- `<specifications, manifests, APIs, model sections, clocks, references>`

## Expected Work

1. `<step>`
2. `<step>`
3. `<step>`

## Expected Artifacts

- `<metrics, plots, netlists, reports, snapshots, or none>`

## Validation And Pass Criteria

- `git diff --check`
- `git status --short --branch`
- `<smallest deterministic checks for the affected circuit or automation>`

State numerical pass criteria and exact PVT/simulator context when applicable.
Justify any new test code or broad suite; otherwise use focused validation.

## Experience Signal (for human review)

Leave empty for routine work. An Agent may flag a repeated failure,
contradicted rule, unsafe shortcut, or validation gap, but only a human decides
whether to extract a reusable lesson.

## Commit And Push Intent

Commit as:

```text
<commit message>
```

Push policy for this target:

```text
<not requested | push main | push feature branch | other>
```
