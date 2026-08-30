# Experience Notes

`docs/experience/` contains reusable project lessons extracted from plans,
logs, commits, simulation reports, DRC/LVS evidence, reviews, and failed
attempts. It is not a second maintenance or design log.

## What Belongs Here

A note should explain a transferable judgment:

- the original circuit, flow, or coordination assumption
- the observed outcome and deterministic evidence
- the interpretation and rule or validation change
- where the lesson applies and where it does not

Raw changed-file lists, daily status, unanalysed simulation transcripts, and
ordinary design decisions belong in `plan/log.md`, Git, reports, or
`docs/design_log.md`.

## Human And Agent Responsibilities

Experience extraction is a human decision. A human reviews work across targets
and decides when a lesson is worth extracting. An Agent may surface candidate
signals and, when asked, draft a note citing evidence; the human accepts,
edits, or rejects it.

## Naming And Evidence

Use `lesson.template.md`. Prefer a dated filename for a concrete event:

```text
YYYY-MM-DD-short-lesson-title.md
```

Evidence may cite plan paths, commits, saved metrics, exact simulator runs,
waveforms, DRC/LVS reports, OA readback, or reviews. Do not include proprietary
PDK content or credentials in a lesson.
