# Plan Directory

The `plan/` directory stores bounded implementation intent and factual
maintenance history for both local Git work and remote Virtuoso OA work.

## Target Plans

Create a target plan before editing tracked files or remote OA state:

```text
plan/<date-goal-slug>/plan.md
```

Use `plan/target-plan.template.md`. Every plan must distinguish:

- local owned paths
- remote OA owned `library/cell/view` objects, or `none`
- protected/read-only local and remote state
- shared contracts and PDK dependencies
- expected artifacts and result destinations
- validation sized to the affected behavior and credible risk
- commit and push intent

## Dirty And Concurrent State

A dirty local worktree does not automatically block unrelated work. Proceed
only when dirty files do not overlap ownership or shared dependencies and the
decision is recorded.

Remote state has an equivalent audit. Stop when the target cellview is locked,
open with unsaved user changes, owned by another task, mapped to an unexpected
library path, or blocked by an unrelated modal dialog.

## Maintenance Log

`plan/log.md` records factual target outcomes:

- local changed areas
- remote OA changes
- validation and pass/fail status
- retained artifacts or reports
- commit and push status

Architectural reasoning belongs in `docs/design_log.md`. Transferable lessons
belong in `docs/experience/` only after a human requests extraction.

## Relationship To Git And OA

Plans and logs do not replace Git or Virtuoso readback. Git records local
tracked state; Virtuoso owns OA state. A complete target normally ends with
proportional validation, remote readback when applicable, log update, intended
staging, commit, and an authorized push.
