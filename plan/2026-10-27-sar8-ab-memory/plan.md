# Release completed-run file cache to admit queued A/B TT work

User authorizes memory cleanup, as much obsolete storage/cache as appropriate,
then running existing A/B tests. First distinguish charged file cache from live
RSS. Prefer POSIX_FADV_DONTNEED for clean completed-run files: no deletion or
waveform loss. Do not kill unrelated processes, drop global caches, change cgroup
limits or bypass managed admission. Historical data/PDK/OA/library unchanged.

Owned: scripts/sar8_ab_short/cache_release.py;
verification/sar8_ab_short/memory_cleanup/; this plan; plan/log.md append only.
Remote mutation scope: cache advice only on UID596 regular non-symlink generated
files under /server_local_ssd/chenzc_intern25/sar-adc-t28/runs/<terminal-run>/raw
or derived. No OA objects; no directory/file deletion. Existing dirty shared
management, Obsidian/manualADC/comparator/10bit files preserved. Read-only
inventory of own /proc and memory cgroup; no model or credential reads.

Inspect exact terminal run states, active analysis source dependencies and own
open files/mappings. Freeze candidate inventory first. Immediately before advice
recheck owner/path/type/size/mtime, run state and live references. Exclude active,
queued, uncertain runs and any running analysis source; preserve failures as data.
Only advise existing bytes; verify file inode/size/mtime unchanged afterwards.
Report account used/cache/RSS before and after separately from disk space; cache
release is not disk-space recovery. If insufficient, extend investigation before
any further action. Do not label live processes obsolete by age alone.

Then query exact already-submitted sar8ab-a-tt-short-v1, allow its existing worker
to enter; do not re-submit. B remains controlled by existing finite serial flow.
No new simulations, recipe changes, auto-followup changes or commit/push.


## Completed and status ownership

Own status-only updates to verification/sar8_ab_short/README.md and plan/2026-10-27-sar8-ab-tt-short/plan.md. Two passes advised411 exactterminal-runfiles (including7 limit_exceededfailures matchingmanagedterminalenum). Allreturncodes0; inode/size/mtime unchanged. Cache reduction29.546GiB, accountused46.270->17.075GiB,headroom1.730->30.925GiB; concurrentAstartup explainsnetdifference. Diskreclaimed0bytes; nofiledeletion/processkill/globaldrop/policychange. All eligible>=1MiB raw/derivedfiles inmanagedrootcovered; active/unknown/open/mappedfiles untouched. Aexistingworkeradmittedslot1/PID180871andrunning; Bserialfollow-on. LocalWindowscommandlengthfailurebeforeSSHcreationfixedusingstdinpayload, no duplicate remoteaction. Summary/receipts memory_cleanup/. No commit/push.
