# Development and Verification Workflow

Start with the objective and acceptance criteria the user has agreed to. Carry the work through implementation, verification, review, and delivery. Execute small, clear tasks directly. Use a spec or split the work when it requires design discussion, handoff, or a real dependency. Carry confirmed decisions into later stages.

## Workflow Stages and Skills

The original skills installed under `.agents/skills/` define the methods. Once a stage applies, read the full skill and its dependencies.

| Stage | Skill | Output |
| --- | --- | --- |
| Clarify requirements | `grill-with-docs` with `grilling` and `domain-modeling` | Agreed requirements, terminology, and design decisions |
| Define acceptance | `to-spec` | Spec and test scope, with publication subject to user authorization |
| Split the work | `to-tickets` | Tasks with deliverables and dependencies |
| Implement | `implement`, which calls `tdd` and `code-review` | A verified and reviewed commit |
| Implement multiple tasks | `implement-spec` | Implementation and integration in dependency order |
| Review independently | `code-review` | Separate standards and spec findings |
| Deliver | `pr`, with `show-me` when evidence needs to be presented | PR with verification evidence |
| Improve the architecture | `improve-codebase-architecture`, `codebase-design` | Structural issues and candidate designs |
| Explore, guide, or hand off work | `prototype`, `wizard`, `handoff` | Findings or handoff information for the task |
| Run a retrospective | `retro` | Improvements derived from the specified sources |
| Maintain rules and configuration | `writing-for-agents`, `setup-matt-pocock-skills` | Documentation organization and project configuration |

Honor each skill's `disable-model-invocation` setting. The user explicitly invokes skills with this setting. Other skills apply when their descriptions match. The original methods specify user checkpoints. Prior authorizations and confirmed decisions carry across stages.

The project installs 19 skills across 55 files. Use the original `implement-spec` method to schedule implementation tasks. Simulation concurrency follows the server resource configuration. [Skill provenance and integrity](../.agents/skill-sources.json)

## Completing a Change

1. Start at the project README. Find the design and testbench in use, then confirm the behavior to change and its acceptance criteria.
2. Update the source and any affected callers. Run the smallest verification that covers the risk.
3. Check the results and the diff. Resolve reproducible failures and report the remaining issues and the scope of the evidence.
4. Record the change, rationale, verification, and limitations in the commit or PR. Follow the user's authorization for publication.

Maintain one current requirement in the conversation or issue, including during handoff. Put temporary notes in the ignored `work/` directory. Trace historical plans and aggregate logs through Git.

## Sources of Record

| Information | Source |
| --- | --- |
| Current design and test entry points | Root README with links to the source files |
| Design constraints, module interfaces, and acceptance criteria | The relevant module specification or contract |
| Current requirement and acceptance | The agreed conversation or issue |
| Simulation settings, input identity, and budgets | Run recipe and frozen-input manifest |
| Progress, failures, and actual resource usage | Managed run state, monitor, and raw logs |
| Measurements and their scope | Result files for the run, linked from the results page |
| Implementation and verification history | Git commit or PR |

Keep documentation aligned with the current rules. Link directly to the configuration or result for status, model sections, run IDs, and parameters. Keep historical dates, versions, and failures with their evidence.

## Verification by Change Type

| Change | Required verification |
| --- | --- |
| Entry point or directory reorganization | Resolve links, dependencies, and input identities |
| Tool code | Exercise the affected path or run a focused test |
| Netlist or behavioral model | Check connectivity and parameters, then simulate the affected modules with the native simulator |
| Module interface or timing | Test the module with its actual load and run the relevant closed-loop ADC test |
| Layout | Run DRC, LVS, PEX, and the affected post-layout simulations |

Repeat verification when a change, failure, or coverage gap warrants it. Define measurement budgets and yield targets before selecting corners and sample counts.

## Long-Running Tasks

Existing simulations continue under their managed queues. Check the monitor and measurement results, then handle failures by run identity. When correcting an analyzer, create an analysis-only task bound to the completed source run and retain the original result. Read the resource policy from the actual execution configuration.

The simulation guide covers managed execution, collection, and resource limits. Use this workflow for directory conventions and day-to-day engineering. [Simulation guide](simulation.md)

## References

This workflow uses the unmodified upstream skills from Analog Canvas commit `7ff62c6c22f827d2434c195ad49207fa7151c807` with this project's Spectre verification contract. The installation manifest records the upstream repository, revision, and file SHA256 digests. The MIT license text is in `.agents/licenses/`. [Analog Canvas agent entry](https://github.com/cascode-ai/analog-canvas/blob/7ff62c6c22f827d2434c195ad49207fa7151c807/AGENTS.md) · [Upstream development workflow](https://github.com/cascode-ai/analog-canvas/blob/7ff62c6c22f827d2434c195ad49207fa7151c807/docs/development-workflow.md)
