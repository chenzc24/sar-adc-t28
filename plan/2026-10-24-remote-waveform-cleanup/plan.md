# Remote historical waveform cleanup

Status: completed first bounded cleanup;14 historical raw waveform files removed.

User authorizes cleanup of our old stored waveforms on thu-wei after memory
pressure and login stalls. Distinguish RAM/process usage from filesystem and
tmpfs storage; do not assume deleting disk files cures process memory pressure.

Own this plan, plan/log.md, scripts/maintenance/remote_waveform_cleanup.py,
verification/storage/2026-10-24-remote-waveform-cleanup*.json and
output/remote_waveform_cleanup/. Remote OA ownership: none.
Remote deletion ownership initially none; add exact file manifest after audit.
Only prior project-generated waveform files with verified provenance, completed
jobs and retained analysis/backups may become deletion targets. Preserve sources,
logs, reports, all OA/PDK/user files, current four sar8_stress_closure cases and
final R3/R4/idle performance baselines. No running-case deletion, process kills,
cache dropping, permission changes or simulation launches.

Starting HEAD2aaea24; unrelated Obsidian and10-bit dirty paths protected.
Read-only dependencies: local README, launch/collection receipts and reports.
Steps: bounded lightweight resource/process/mount check; inventory exact prior
case paths from local manifests; validate retained evidence and unused regular
files; record explicit deletion manifest with size/path checks; delete only
approved files, verify absence and resource deltas. Stop if access unavailable
or ownership/active-use checks are inconclusive. No broad recursive delete.

Validation: resolved path containment, no symlinks, correct uid, completed native
exit marker, active/open-file checks, retained local result hash; before/after
allocated bytes and filesystem/RAM snapshots; JSON and compile/diff checks.
Report files removed, recoverability and measured space. Commit only this target;
no push. Intended commit: maintenance: reclaim verified remote historical waves.

## Approved exact deletion inventory

Remote file ownership extended only to the14 exact `rows[].path` entries in
verification/storage/2026-10-24-remote-waveform-cleanup.json, each basename
test.raw/tran_perf.tran.tran. Ten cases under sar8_ref_gate_controls_20261024,
four under sar8_ref_symmetric_hold_20261024, both below the project llm_IO path.
Audit size17,472,016,384 allocated bytes; native exit/reduction exit0, local
compressed-result SHA256, remote source-deck hash and recorded raw byte size
all verified. Exact inode/device/mtime/size must remain unchanged at deletion.
Current-account process command/cwd/fd/maps checked; no candidate in use.
Privileged sshd transports and descriptor-free zombies are explicitly excluded
and recorded; no privilege escalation or process changes. No recursive delete.

Sources/logs/results and reduced waveforms stay on local and remote storage.
Full native raw reconstruction is not guaranteed: missing signals require rerun.
User was informed before deletion. Current stress_closure and final performance
baselines remain protected. Connection recovered; home is NFS98% full rather
than tmpfs. Resource snapshot: MemAvailable22,132,304KiB, SwapFree88,892KiB;
no running Spectre in user's process list. Deletion is storage reclamation,
not a claim to resolve the server's process-memory pressure.

## Completed result

Deleted exactly14 audited regular files with os.unlink, no directories or source
files removed. Sum allocated bytes17,472,016,384 (16.272GiB); immediate shared
filesystem free-space increase17,460,887,552bytes (other users may affect df).
Independent readback confirmed all14 absent and all retained native decks,
logs, logStatus and reduced.json.gz present. Local retained results hash-checked
again before deletion. Cannot reconstruct every original signal from reduction;
source rerun required for discarded unretained detail. No automatic undo.

All four protected stress_closure native exit markers now0; raw files remain,
combined94,869,661,741bytes. This is completion-status evidence, NOT stress or
code qualification. No reduction, bulk download or new simulation started.
After snapshot MemAvailable22,227,624KiB, SwapFree88,892KiB; storage reclaim
does not substantiate any RAM-pressure fix. No remote process killed or OA edit.
Python compile, manifest integrity and scoped diff checks passed. Task-only local
commit; unrelated user changes preserved, no push.
