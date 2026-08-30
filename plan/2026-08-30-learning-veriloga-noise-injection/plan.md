# Record Verilog-A Noise-Injection Learning

## Goal

Record the reviewed method, evidence, and limitations of converting the SAR
ADC input-referred RMS allocations into event-level Verilog-A random-noise
injection.

## Dirty-State Note

The worktree starts clean. Local `main` is one commit ahead of `origin/main`
at `4e516f4`; that unpublished commit is the completed allocated-noise
experiment on which this note is based.

## Local Owned Files

- `docs/learning/veriloga-event-noise-injection.md`
- `plan/2026-08-30-learning-veriloga-noise-injection/plan.md`
- `plan/log.md`

## Remote OA Owned Objects

- none

All Virtuoso OA state, PDK content, generated simulation artifacts, and
existing source/model files are read-only for this documentation target.

## Implementation And Validation

1. Explain the distinction between an RMS parameter and a realized random
   voltage sample.
2. Record the sampling-event and per-bit decision equations and their current
   Verilog-A implementation.
3. Explain fixed seeds, `white_noise()` versus event-level random draws, the
   Spectre/RSS correlation result, and the abstraction limits.
4. Verify numerical values against the design spec and allocated-noise
   summary, inspect the Markdown, and run `git diff --check`.

## Expected Result

A self-contained learning note that can guide future noise controls without
misrepresenting behavior-level injection as transistor-level noise analysis.

## Commit And Push Intent

Commit locally as `docs: record Verilog-A noise injection learning`. Push was
not requested.
