# Second approved local historical waveform cleanup

## Goal and authorization

After a read-only inventory, the user explicitly replied "删" to a proposal
to permanently remove 395 historical waveforms / 33,847,727,848 B
(31.523153 GiB). Keep sources, exported netlists, logs, configuration, small
metrics, reports and figures. No verified waveform backup is assumed;
reanalysis of removed details may require re-simulation. No backup copy,
recycle-bin storage, remote operation or new simulation is authorized.

## Dirty state and ownership

Branch `exp/cdac-flat8-device`, initial HEAD3577987, ahead26, empty index.
Existing user Obsidian edits/deletions/new notes/images, cdac10 work, R4
performance sources/models/config/verification and its already-dirty appended
`plan/log.md` section belong to other work. Preserve all of them. In particular,
do not stage the existing R4 log section; stage only this target's own append,
or omit the shared log from this commit if safe partial staging is unavailable.
R4 performance execution is active and must not be interrupted.

Owned tracked paths:

- This plan and adjacent `cleanup.ps1`.
- `verification/storage/2026-10-21-history-cleanup-2.json` (generated receipt).
- `docs/storage_cleanup_candidates.md`, the cleanup-status paragraph in
  `docs/project_status.md`, and only this target's append to `plan/log.md`.

Read-only script template: the completed first cleanup's `cleanup.ps1` and
receipt; do not modify those historical records.

## Exact deletion boundary

Only files >=5 MiB named `*.tran`, `*waveform*.json`, `tran.csv` (the observed
candidate set), in the following 26 literal subdirectories of project `output/`:

- Old CDAC sweeps: `cdac8_reset`, `cdac8_dualrail`, `cdac8_uniform_scale`,
  `cdac8_pn_ratio`, `cdac8_no_driver` (148 files / 12,693,446,680 B).
- Initial CDAC: `cdac8_device` (76 files / 4,943,949,571 B).
- Pre-B timing: `sar8_reference_edge_slew`, `sar8_join_r3`
  (24 files / 10,849,663,224 B). This deliberately retires pre-B raw data,
  not the current B/W1 datasets or the R3 circuit/OA/source definition.
- Old sampling: `canvas_full_cdac`, `top_plate_gmain_first_device`,
  `top_plate_pgate_driver`, `bootstrap_full_cdac_isolation`,
  `bootstrap_bottom_plate_clamp_width_screen`, `bootstrap_bottom_plate_eval`,
  `bootstrap_current_path_audit`, `bootstrap_protected_eval`
  (96 files / 4,115,598,756 B).
- Old macros: `electrical_macro_model`, `electrical_macro_model_decap_scan`,
  `oa_electrical_macro_model`, `electrical_macro_model_probe`,
  `electrical_macro_model_probe2`, `electrical_macro_model_probe3`,
  `electrical_macro_model_probe4`, `electrical_macro_model_probe5`,
  `electrical_macro_model_probe6`, `electrical_macro_model_phase_probe`
  (51 files / 1,245,069,617 B).

Remote OA owned objects: none. All remote data, PDK/OA, sources, exported
netlists and all unlisted output paths are read-only. Explicitly exclude
B short acceptance, B/W1 two-frequency sine, B512 failure evidence, R3 anomaly
and B-event diagnostics, selected controller, R4 and cdac10 experiments.
Preserve small deck/snippet dependencies used by existing build/report tools.

## Execution and validation

1. Reuse the first script's checked path/reparse/active-process/tracked-file
   guards with this exact allowlist, 395-count and byte-total assertions.
   Narrow the large-JSON selector to waveform names; no whole-directory delete.
2. Freeze exact absolute leaf paths, sizes and timestamps in a small receipt.
   Hash all retained files in listed roots and explicit protected baselines;
   record drive-free bytes. Use streaming SHA, no waveform copy or full load.
3. Recheck target metadata; individually `Remove-Item -LiteralPath`, without
   recursive deletion. Refuse to repeat if receipt exists; record partial failure.
4. Require all 395 absent, grouped totals correct, all retained file content/
   path/size/mtime digests equal and protected baseline hashes unchanged.
   Measure free-space delta separately from removed content bytes.
5. Update actual cleanup totals and record permanent loss of old raw evidence.
   Parse script, validate receipt/paths/absence and run scoped diff checks.
   Review only owned staged changes, preserve other dirty work and commit locally.

Artifacts: receipt above, cumulative cleanup report and factual own log entry.
Intended commit: `chore: retire approved CDAC and pre-B waveform history`.
No push, circuit changes, simulation, download, remote access or process kill.

## Progress

- Re-inventory matches 395 files / 33,847,727,848 B; no mutation yet.
- PowerShell syntax and read-only dry run pass: same 395/count/bytes,
  no tracked targets/reparse points/referencing active process; 13,781 files
  to retain in the approved roots. Actual execution started with protected
  baseline and retained-file streaming SHA checks before any removal.
- Completed: 395 files / 33,847,727,848 B permanently removed. All targets
  absent, retained 13,781-file digest and eight protected-file hashes pass.
  E free93.828037->125.351818 GiB, net31.523781 GiB. No remote connection,
  process stop, simulation, download, backup copy or unrelated file deletion.
- Cumulative report now records 597 files / 71.455829 GiB across both approvals.
  Focused syntax/dry-run, receipt/path/absence and retention checks pass.
  Stage only this target's log entry, preserving the pre-existing R4 entry;
  scoped local commit only, no push.
