# Adopt And Adapt Agent Workflow Kernel

## Goal

Adopt the plan-log-experience workflow kernel into the SAR-ADC repository,
adapt it for the split local-Git and remote-Virtuoso/OA workflow, validate the
rules, commit the bounded change, and publish the repository with GitHub CLI.

## Dirty-State Note

Start state from `git status --short --branch`:

```text
## main
```

The worktree was clean at target start.

## Owned Files

- `AGENTS.md`
- `README.md`
- `plan/**`
- `docs/experience/**`

## Read-Only Files

- `config/**`
- `docs/architecture.md`
- `docs/design_log.md`
- `docs/verification_plan.md`
- `models/**`
- `netlist/**`
- `scripts/**`
- `verification/**`
- `virtuoso/**`
- Remote Virtuoso library `SAR_ADC_T28/**`
- Shared and PDK libraries, including `tsmcN28/**`
- Upstream kernel repository `chenzc24/agent-workflow-kernel`

## Shared Dependencies

- Upstream kernel commit `9fa667772f23d4ca625680dfd4bcbf889aa38025`.
- Local repository and remote OA ownership boundaries documented in
  `README.md`.
- `virtuoso-bridge` 0.8.0 and the `t28_io` profile define the remote access
  and validation surface, but no remote design mutation is owned by this
  target.

## Expected Work

1. Add the portable plan, log, and experience templates.
2. Adapt root Agent rules for local tracked files, generated artifacts, remote
   OA objects, PDK protection, bridge preflight, and AMS validation levels.
3. Document project branch/push policy and the distinction between maintenance
   logs, design decisions, and experience notes.
4. Validate the documentation surface, update the maintenance log, commit, and
   publish `main` with GitHub CLI.

## Validation

- `git diff --check`
- `git status --short --branch`
- Targeted `rg` checks for kernel provenance, remote OA ownership, protected
  PDK rules, validation levels, human-triggered experience extraction, and
  branch policy.
- Review the complete diff and confirm that no files outside the owned set
  changed.
- Confirm the final GitHub repository and `origin/main` with `gh repo view` and
  `git status --short --branch` after push.

These checks match a documentation-and-governance target: deterministic text
inspection and Git/GitHub state checks cover the affected behavior without
running circuit simulations or modifying remote OA data.

## Experience Signal (for human review)


## Commit Intent

Commit as:

```text
chore: adopt SAR ADC agent workflow
```
