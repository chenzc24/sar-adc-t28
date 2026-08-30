# Record Error-Budget Learning

## Goal

Record the human-requested learning note explaining how the first top-down SAR
ADC error budget was derived, which quantities are strict system limits, which
are provisional engineering allocations, and when the allocation must be
rebalanced using PDK evidence.

## Dirty-State Note

Start state from `git status --short --branch`:

```text
## main...origin/main [ahead 1]
```

The worktree was clean. The existing ahead commit is the completed behavioral
baseline and is a read-only dependency of this documentation target.

## Local Owned Files

- `docs/learning/error-budget-allocation.md`
- `plan/2026-08-30-record-error-budget-learning/plan.md`
- `plan/log.md`

## Remote OA Owned Objects

- none

## Read-Only State

- all behavioral model, configuration, verification, and generated output
- all remote Virtuoso OA state and PDK/shared libraries
- sibling repositories

## Shared Dependencies

- `config/design_spec.yaml`
- `docs/error_budget.md`
- `output/behavioral_baseline/summary.json`
- commit `0716c25` (`feat: add SAR ADC behavioral baseline`)

## Expected Work

1. Add one concise Chinese learning note under `docs/learning/`.
2. Distinguish formula-derived constraints from provisional allocations.
3. Record the RSS closure, interpretation limits, and PDK-driven rebalance
   triggers.
4. Update the maintenance log.

## Expected Artifacts

- `docs/learning/error-budget-allocation.md`

## Validation And Pass Criteria

- Numerical values agree with the tracked spec and behavioral summary.
- The note explicitly preserves the user's requested conclusion.
- Markdown inspection and `git diff --check` pass.
- The final diff contains only declared owned files.

## Experience Signal (for human review)

This note is explicitly human-requested learning extraction.

## Commit And Push Intent

Commit as:

```text
docs: record top-down error budget learning
```

Push policy for this target:

```text
not requested
```
