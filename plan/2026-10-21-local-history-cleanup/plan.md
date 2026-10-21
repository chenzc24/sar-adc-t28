# Authorized local historical waveform cleanup

## Goal and authorization

User approved permanent deletion ("删") of the proposed 39.93 GiB batch:
obsolete 10-bit behavioral/noise waveforms, early Bootstrap experiments,
superseded 26-cell handshake controller, R1/R2 timing experiments, and
unselected W2/W3 sampling experiments. Preserve source, exported netlists,
configuration, logs, curated metrics/reports/figures and current evidence.
Unique deleted waveforms have no verified backup; new detailed analysis may
require re-simulation. No recycle-bin or backup copy will consume disk space.

## Ownership and dirty state

Existing Obsidian edits/deletions/new notes and images, cdac10_dualrail work,
and sar8_r4_performance sources/plans are unrelated and remain untouched.
Repository started ahead25; no staged files. Do not change others' work.

Owned tracked paths:

- This plan and adjacent `cleanup.ps1`.
- `verification/storage/2026-10-21-history-cleanup.json` (generated receipt).
- `docs/storage_cleanup_candidates.md`, one cleanup-status sentence in
  `docs/project_status.md`, and an appended entry in `plan/log.md`.

Owned generated deletion set: only files >=20 MiB with extension `.json`,
`.pickle`, `.csv`, or name ending `.tran`, under these literal `output/`
subdirectories, frozen before deletion to exactly 202 files / 42,877,383,874 B:

1. `veriloga_baseline_spectre`, `veriloga_allocated_noise_spectre`.
2. `bootstrap_driver_error_reduction`, `bootstrap_hold_ablation`,
   `bootstrap_driver_design`, `bootstrap_netlist_fast_ab`,
   `bootstrap_isolate_before_reset`, `bootstrap_turnoff_charge_screen`,
   `bootstrap_t28_hold_pulldown`.
3. `sar8_async_impl`.
4. `sar8_join_r1`, `sar8_join_r2`, `sar8_reference_alignment`,
   `sar8_restore_guard`, `sar8_restore_cross_input`.
5. `b_hf_main_w/w2`, `b_hf_main_w/w3`, `b_sine_main_w/w2`,
   `b_sine_main_w/w3`.

Remote OA owned objects: none. All remote files, PDK, OA, source/netlist trees,
all unlisted output directories, B/W1 baselines, B short acceptance, anomaly
and B512 failure evidence, current R4 and cdac10 work are read-only.

## Steps

1. Inventory exact literal roots; reject reparse points, out-of-root paths,
   tracked targets, changed count/bytes, or active processes referencing targets.
2. Save a small receipt with exact absolute paths, lengths and timestamps,
   grouped totals, disk-free measurement, and protected-file hashes.
3. Recheck frozen target metadata and delete only those files, individually,
   using PowerShell `Remove-Item -LiteralPath` without recursive deletion.
4. Verify all targets absent and all other files in the listed roots unchanged;
   hash-check retained logs/netlists/metrics and explicit current baseline files.
5. Update cleanup report/status/log from actual receipt; scoped diff check and
   local commit only. No remote access, download, simulation or push.

## Validation and artifacts

Pass: 202 intended targets absent; 42,877,383,874 B of file content removed;
retained files in owned roots have identical length/time/content hashes;
protected baseline receipt checks pass; no unrelated deletion or source edit.
Free-space delta is measured separately and can reflect concurrent work.
Receipt records permanent deletion, not recoverable archival. Use only focused
PowerShell parser/dry-run/receipt checks and scoped `git diff --check`.

Expected result: `verification/storage/2026-10-21-history-cleanup.json` and
updated local cleanup report. Intended commit: `chore: purge approved historical waveform data`.

## Progress

- Planned before source changes/deletion. Exact batch re-inventoried at
  202 files / 39.932676 GiB; no matching active local run process found.
- Read-only script dry run matched approved count/bytes; no tracked deletion
  targets. Removed exactly the frozen 202 files using individual literal paths;
  all are absent. All 8,281 retained files' aggregate content/metadata digest
  matches before/after; eight explicit protected baseline SHA256 checks pass.
- Complete receipt: deleted 42,877,383,874 B / 39.932676 GiB. E free space
  53.943497->93.875572 GiB (measured delta39.932076 GiB). No remote operation,
  simulation, backup copy, source/netlist/log deletion or unrelated mutation.
- Report and project-status sentence updated. PowerShell syntax, exact dry-run
  totals, focused completion/absence/receipt checks and scoped diff checks pass.
  Local commit only; no push.
