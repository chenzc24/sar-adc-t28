# Remove unused historical home compilation caches

Status: queued behind the active loaded-reference simulation; deletion not
yet verified. One background maintenance worker, PID25034 at submission.

User authorized removing old unused compilation artifacts after the project
management review. Scope only immediate child *.ahdlSimDB directories of
/home/chenzc_intern25, first frozen from the prior317-directory metadata list.
Require a matching SAR-project .scs basename from local source/generated decks;
ambiguous generic names are retained. No other home directories/files, .srf,
logs/locks, OA/PDK, waveforms, source decks, current per-run SSD caches or other
users' data are cleanup targets. No simulations or cache-policy changes.

Start HEAD14b9446, exp/cdac-flat8-device. User Obsidian and independent10-bit
changes plus concurrent loaded-block physical-repair plans/recipes/scripts and
evidence are unrelated, protected and non-overlapping. Never kill those jobs.
Remote OA ownership none; no Bridge/CIW mutation needed for filesystem caches.

Own this plan, scripts/management/home_cache_cleanup*.py and focused tests,
verification/storage/2026-10-25-home-cache-cleanup/, ignored transport under
output/project_management/home_cache_cleanup/, appended plan/log.md and a
dated execution pointer in the previous home-inspection report. Keep previous
snapshots/receipts immutable. Remote helper/journal only in owner-verified
/server_local_ssd/chenzc_intern25/sar-adc-t28/maintenance/home-cache-20261025.

Freeze exact candidate names and local project origin references. Read-only
audit bounds:256MiB address space, no core, nice+10, max60s; inspect metadata,
not waveform contents. Require resolved immediate child paths, owner596,
regular generated files, no symlinks/special files/mount crossings/hardlinks.
Retain any tree changed within1h, active cwd/openFD/mapped-library/command refs,
ambiguous origin, inaccessible processes or unstable metadata. Audit own UID
processes; no credential/environment contents. Do not claim all caches unused
merely because no current simulation appears in one ps listing.

Process-audit refinement after diagnosis: zombies (stateZ, no live descriptors
or mappings) and recognized privilege-separated sshd transport processes
(commsshd plus exact account title) are recorded exclusions, not unknown
simulation processes. Their /proc ptrace access is normally denied. All other
live own-user processes still require inspection; no global permission bypass.
Preserve blocked audit snapshots on SSD and ignored local transport before a
fresh audit. Never loosen cache symlink/owner/current-Spectre/workload gates.

Delete only after focused safety tests and exact audit. Hold existing managed
heavy-work lock nonblocking and refuse while any account Spectre is active;
do not bypass a refused lock or interfere with queued jobs. Recheck trees and
live references before removal. Explicit child-file unlink and bottom-up rmdir,
not recursive broad rm. Journal per-directory intent/outcome; preexisting
partial outcomes require reconciliation rather than blind replay. Do not
follow symlinks. Read back every deleted path absent and preserved paths intact.

Scheduling refinement: when lock is occupied by the authorized loaded-block
simulation, queue one idempotent low-priority SSD maintenance worker for up to
2h; retry lock every5s, not the deletion itself after a partial result. Frozen
eligible list does not expand while waiting. Status and journals remain on SSD.
No recurring automation, interruption, duplicate worker or new simulation.

Report count, logical/allocated bytes and observed home-filesystem free delta
separately; removal permanent but caches regenerable from preserved sources.
Record exact retained reasons. Validation: path/type/link/source/age/change
guards, process-use recognition, mocked exact-tree removal; Python syntax,
JSON, scoped diff. Commit only owned paths, no push. No global inventory
refresh that would rewrite concurrent physical-repair registrations.

Keep full per-file audit metadata on the SSD and ignored local transport;
track only its hash, directory-level summary, source allowlist and receipts.
Do not commit multi-megabyte redundant per-file cache metadata.

Audit:317 known home caches;316 match project deck basenames.308 eligible,
3340 generated files,116.883MiB; preserve six generic names (including unknown
deck) and three recently refreshed caches. No live cache refs observed; active
Spectre and workload lock cause deferral, not override. Queue preserves this
frozen eligibility and rechecks all remaining trees/live uses at execution.
Nine focused tests and Python compile pass. Sources/raw/logs/PDK/OA untouched.
Later recovery: project .venv Python scripts/management/home_cache_cleanup.py
collect fetches status; only after remote completion does it fetch the deletion
receipt and final absence/preservation readback. Queue timeout2h is a failed/
rejected cleanup, never reported as successful. Scoped checkpoint, no push.
