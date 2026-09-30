# Refresh active top-plate baseline

Clean tree on exp/top-plate-gmain-t28. Own review/{flows.json,node-notes.yaml,
model.yaml,evidence.yaml,source-lock.json,evidence-baseline.json,figures.json},
this plan and plan/log.md. Reports, circuit files, topology diagrams, PDK and OA
are read-only. No experiment resumes or source baseline changes by inference.

Read sampling_architecture_status, top_plate_gmain_device_screen and
top_plate_pgate_driver; reconcile active top-plate line and user-approved
provisional 522aa0f freeze. Preserve 0.439 mV allocation, historical bottom-plate
evidence and 0.605518 mV measured exception. Keep PGATEB/well risk and ideal
STRACK explicit. Retain compact graph and historical figure; no claim its
earlier partial-transistor result is latest PGATE performance.

Validate data/refs/build, focused tests, diff and browser graph/detail table.
Review source fingerprint differences before acceptance. Local commit, no push.

## Outcome
Updated global, sampling and CDAC graphs to the active top-plate line; retained
bottom-plate results within history. Added hold-pair and six-device PGATE records,
five-point table and explicit freeze decision. Preserved original error allocation
as failing, not relabeled pass. Removed historical VSS-off schematic links from
current top-plate stages; retained them only in history. Earlier plot marked as
ideal-PGATE history. Accepted three new reports and full_cdac historical header.
23 focused tests, build and diff checks pass. Browser verified compact flow and
PGATE five-point table, no console errors. Screenshot:
output/review/topplate-progress-preview.png. No circuits/OA modified or run.
