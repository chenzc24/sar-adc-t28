# Agent Entry

Read [README.md](README.md) to find the current design, testbenches and results.
Use [docs/development-workflow.md](docs/development-workflow.md) for implementation and validation.

## Agent skills

- Use the original project skills in [.agents/skills/](.agents/skills/).
  Honor each skill's invocation policy, dependencies, human checkpoints and review separation.
- Choose the stage through [the workflow table](docs/development-workflow.md#workflow-stages-and-skills).
  Run the selected original method and its dependencies.
- Issue tracker configuration is in [docs/agents/issue-tracker.md](docs/agents/issue-tracker.md).
  Domain documentation is in [docs/agents/domain.md](docs/agents/domain.md).
- Sources, licenses and immutable skill file hashes are recorded in [.agents/skill-sources.json](.agents/skill-sources.json).

## Work on the requested change

- Check Git status and the relevant source before editing. Protect unrelated changes.
- Use the user's agreed scope and acceptance criteria. Clear small tasks go directly to implementation.
- For work that needs discussion or handoff, keep one current requirement in the conversation or an Issue.
  Split work only for real dependencies or independent deliverables.
- Make the change, verify the affected behavior, review the diff, and report the outcome.
  Use a branch or worktree when concurrent changes overlap.
- Temporary notes, generated decks and mutable run state live in ignored `work/`.
  Historical plans and experiments are available at the provenance commit.
- Record the change, validation and limitations in its commit or PR.
  Follow the user's authorized publication scope.

## Circuit and simulation work

- Identify the exact design version and use its declared top, models and testbench.
- Keep physical source, generated views and measured evidence traceable through the run manifest.
  Preserve the bytes of frozen inputs and bind comparisons to actual device draws.
- Run simulations and heavy analyses through the existing managed runner.
  Its recipe, execution policy and server state define resource admission and progress.
- Read status from the existing monitor; read electrical verdicts from waveform measurements.
  Inspect the original run identity before retrying uncertain submissions.
- At experiment closeout, before large batches, or when reclaiming disk space, follow
  [waveform retention](docs/waveform-retention.md) to archive evidence and release eligible raw files.
- Validate a circuit change through its real interface, loading and timing conditions.
  Report functionality, performance and electrical qualification at their measured scope.
- Foundry PDKs and shared libraries remain read-only. Keep proprietary model text,
  credentials and OA databases outside Git.
- For layout queries, use the [Virtuoso OA workflow](Layout/docs/workflow.md#layout-queries) for the active edit, saved views and verification reports.
- When OA work is requested, use supported Virtuoso APIs and verify the changed view.

## Documentation

- Use English for maintained documentation, workflows, handoffs, issues, and pull requests.
  Quote original tool output and preserve frozen evidence as recorded.
- Give each current rule or interface one authoritative home and link to it.
- Update documentation when requirements, interfaces, limits or design decisions change.
- Put run configuration and measurements in machine-readable manifests and results.
  Use commits and PRs for implementation history and validation notes.
- Replace obsolete current guidance in place. Consult older reports for their dated evidence.
