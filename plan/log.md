# Maintenance Log

This file records factual project maintenance. Circuit and architecture
decisions remain in `docs/design_log.md`; reusable lessons require a separate
human-triggered note in `docs/experience/`.

## 2026-08-30 - Adopt SAR ADC Agent workflow

- Target: adapt the portable plan-log-experience kernel for a split local Git
  and remote Virtuoso OA project, then publish the repository.
- Local changed areas: root Agent rules, project README, target planning,
  maintenance-log, and experience-note templates.
- Remote OA changes: none; `SAR_ADC_T28` remained read-only for this target.
- Validation: documentation diff checks, targeted rule-presence checks, owned
  path review, Git state review, and GitHub remote verification.
- Commit status: ready to commit as `chore: adopt SAR ADC agent workflow` and
  push to the user-authorized `chenzc24/sar-adc-t28` repository.

## 2026-08-30 - Create remote Virtuoso library

- Target: create an empty remote `SAR_ADC_T28` OA library.
- Local changed areas: idempotent library creation script, cell manifest, and
  design log.
- Remote OA changes: created `/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28`
  and bound it to `tsmcN28`; no cells were created.
- Validation: bridge/API readback verified library name, path, and technology;
  filesystem inspection showed only OA library metadata.
- Commit status: committed in `f60725f`.

## 2026-08-30 - Scaffold SAR ADC project

- Target: establish the local SAR-ADC repository and default design skeleton.
- Local changed areas: configuration, architecture and verification docs,
  model/netlist/script/verification directories, artifact boundaries, and Git
  ignore policy.
- Remote OA changes: none in this target.
- Validation: Python automation compiled and the initial repository state was
  reviewed.
- Commit status: committed in `069bd7f`.
