# Agent Working Rules

Adapted from
[`chenzc24/agent-workflow-kernel`](https://github.com/chenzc24/agent-workflow-kernel)
at commit `9fa667772f23d4ca625680dfd4bcbf889aa38025`.

This repository uses a plan-log-experience workflow for Agent-assisted analog
and mixed-signal design. Work must be bounded, explicitly owned, validated in
proportion to risk, and recorded factually. Reusable experience is extracted
separately and only when a human requests it.

## Project Boundaries

The project has three distinct state domains:

1. **Local tracked sources** under this Git repository: specifications,
   documentation, Verilog-A, curated netlists, automation, manifests, plans,
   metrics, and concise reports.
2. **Local or downloaded generated artifacts** under `output/`, `artifacts/`,
   and `virtuoso/{snapshots,exports}/`. These are not source-of-truth OA data
   and are ignored by Git unless an explicit small report is curated.
3. **Remote Virtuoso OA state** in library `SAR_ADC_T28` at
   `/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28`. Schematic, symbol,
   layout, and Maestro cellviews are modified only through supported Virtuoso
   or bridge APIs, never by editing OA files on disk.

The following are protected and read-only unless the user explicitly changes
scope:

- `tsmcN28` and all foundry PDK content
- shared standard-cell, SRAM, IO, reference, and technology libraries
- any remote library other than `SAR_ADC_T28`
- remote cellviews not named in the active target plan
- user-owned unsaved Virtuoso windows and locked cellviews

Never commit PDK files, credentials, proprietary model contents, license data,
or raw OA databases.

## Operating Discipline

Before starting a target:

1. Run `git status --short --branch` at repository root.
2. Audit dirty state and ownership. Unrelated dirty files may remain only when
   they do not overlap the target or change a dependency; record that decision
   in the plan. Stop when ownership is unclear or overlapping.
3. Read `README.md`, the relevant design documents and manifests, and the
   active target plan.
4. Identify the goal, validation surface, local owned paths, remote OA owned
   objects, and read-only dependencies.
5. For any remote operation, verify the exact bridge profile, CIW, library,
   cell, and view before mutation.

## Before Editing

Create or update a target plan before editing tracked files or remote OA state:

```text
plan/<date-goal-slug>/plan.md
```

The plan must state:

- concrete goal
- dirty-state note
- local owned files/directories
- remote OA owned `library/cell/view` objects, or `none`
- local and remote read-only areas
- shared dependencies and assumptions
- implementation steps
- validation steps and pass criteria
- expected artifacts and result locations
- intended commit message or commit policy

Do not modify anything outside the owned set without updating the plan first.

## Remote Virtuoso And Spectre Preflight

Before mutating OA state:

1. Run `virtuoso-bridge status` and require the tunnel, daemon, and required
   simulator to be healthy.
2. Run `virtuoso-bridge windows` or the appropriate window inspection to
   confirm the intended CIW/session and detect unsaved or modal windows.
3. Verify the target library/cell/view exists or is intentionally being
   created, and inspect locks when concurrent ownership is possible.
4. Read existing design state with supported Python readers. Do not hand-write
   SKILL readers when a bridge reader exists.
5. Stop on an unrelated confirmation dialog, unexpected library mapping,
   technology mismatch, lock, or unsaved user-owned target.

Use `virtuoso-bridge` 0.8.0 or newer from the workspace virtual environment.
Never treat `/tmp/virtuoso_bridge_*` as project storage.

## During Work

- Keep one bounded target per plan and commit.
- Prefer small, reviewable changes; exclude unrelated cleanup.
- Treat shared contracts, generated artifacts, and user-owned work as
  protected unless explicitly claimed.
- Update the target plan before expanding scope or ownership.
- Use supported high-level bridge APIs before inline SKILL, and verified SKILL
  references before writing any lower-level call.
- Preserve raw exported netlists and reports; create curated copies instead of
  editing generated output in place.
- Bind Maestro and waveform reads to the exact run history. Use unique remote
  result/export paths and never infer "latest" when reproducibility matters.
- Record unresolved circuit assumptions in the plan or a design review note,
  not only in chat.
- Do not add tests or run broad suites defensively. Use the smallest
  deterministic validation that covers the changed behavior and direct risk.

## Validation Levels

Choose checks by the surface changed:

| Changed surface | Minimum deterministic validation |
| --- | --- |
| Markdown/YAML/manifests | parse or targeted inspection, `git diff --check` |
| Python automation | syntax/compile check plus focused execution or unit test |
| Verilog-A/Spectre deck | netlist checker or Spectre syntax/smoke run; require `result.ok` |
| Behavioral ADC | static ramp and coherent-sine metrics with saved configuration |
| Schematic/OA connectivity | API readback, connectivity/netlist inspection, focused simulation |
| Comparator/CDAC/sampling block | dedicated testbench with stated PVT and pass criteria |
| Integrated ADC | static, dynamic, timing, power, PVT, and mismatch validation as applicable |
| Layout | geometry/readback inspection plus DRC and LVS |
| Extracted/sign-off view | PEX provenance, DRC/LVS evidence, and post-layout regression |

Simulation records must identify cell/view or netlist revision, model include
and section, supply, temperature, simulator mode/version, saved signals, and
result directory. DRC/LVS/PEX records must identify the exact library, cell,
view, rule deck context, tool version, and report artifact.

## After Work

Before considering a target complete:

1. Run the validation and pass criteria declared in the plan.
2. Read back every remote OA mutation and confirm the intended library,
   cellview, technology binding, or connectivity state.
3. Run at minimum `git diff --check` and `git status --short --branch`.
4. Review the complete diff and ensure only owned files changed.
5. Update `plan/log.md` with the target, changed areas, remote OA changes,
   validation, artifacts, and commit status.
6. Stage only intended tracked files and commit using the target policy.
7. Push only when the user requested it or an established project policy
   authorizes it. Never force-push without explicit authorization.

A local Git commit does not prove that remote OA state or simulation results
are valid. The maintenance log must record local and remote validation
separately.

## Git And Branch Policy

This is currently a single-owner repository. Small, bounded targets may commit
directly to `main`. Use a feature branch for multi-target work, risky shared
contract changes, experiments the user wants isolated, or when collaboration
begins. Do not rewrite published history. Remote creation and ordinary pushes
use GitHub CLI or authenticated Git after explicit user authorization.

## Plan-Log-Experience Mainline

The automatic per-target loop is:

```text
target plan
-> bounded local and/or OA implementation
-> deterministic validation
-> factual maintenance log
-> commit
-> authorized push
```

The experience layer is human-triggered:

```text
human reviews plans, logs, reports, and failures
-> human requests a reusable lesson
-> Agent drafts a candidate with evidence and limits
-> human accepts, edits, or rejects
```

`plan/log.md` records what happened. `docs/design_log.md` records durable
circuit and architecture decisions. `docs/experience/` contains only reusable
judgment extracted at human request; it is not a second status log.

## Boundary And Hygiene Rules

- Do not mix unrelated targets in one plan, log entry, or commit.
- Do not mix workflow changes with circuit changes unless the plan explains
  why they must land together.
- Do not use model confidence as the only quality gate when deterministic
  simulation, readback, DRC/LVS, or human review is available.
- Do not delete unresolved or blocked plans to make the repository look clean.
- Completed detailed plans may be summarized and archived according to project
  policy. Keep failed, blocked, or unresolved plans visible until explicitly
  resolved, superseded, or abandoned.
- Before archiving a plan with a possible reusable signal, flag it for human
  review; the human decides whether experience extraction is warranted.
