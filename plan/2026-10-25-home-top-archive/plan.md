# Archive inactive home top-level logs and simulation artifacts

Status: complete. Twelve files archived (seven logs, five historical SRFs),
all SHA256/identities verified; original protected paths and metadata unchanged.

User explicitly requests archiving confirmed inactive logs/historical simulation
artifacts, keeping active logs, locks, configuration and engineering directories
unchanged, and a final remaining list. Scope /home/chenzc_intern25 immediate
visible regular files only: recognized Cadence/Spectre logs and *.scs.*.srf.
No deletion, cache cleanup, compression, raw waveform directory migration,
configuration/startup changes, process kills or OA changes.

Start HEAD19ae72f on exp/cdac-flat8-device. Obsidian, independent10-bit and
concurrent loaded-block repair sources/recipes/results/plans are unrelated and
protected. No overlapping design edits. Remote OA ownership none; no CIW edit.

Own this plan, scripts/management/home_top_archive*.py and focused tests,
verification/storage/2026-10-25-home-top-archive/, ignored transport under
output/project_management/home_top_archive/, a factual management README
navigation line, management/cleanup/2026-10-25/home_archive.json and appended
plan/log.md. No global inventory refresh or other registry rewrites.
The human-facing remaining list is a plain generated remaining.txt, not an
additional explanatory Markdown report or a cloud Page.

Destination: /home/chenzc_intern25/archive/home-top-2026-10-25/{logs,simulation}/
on the same filesystem, account-owned0700, dedicated new batch only. This is
not a relocation into SSD scratch or an existing engineering/PDK directory.
Keep per-file original path, SHA256, metadata, archive path and recovery mapping
in an archive manifest plus SSD maintenance journal and local evidence.
Helper/journal only at owner-verified project SSD maintenance/home-top-20261025.

Eligibility requires regular owner596 file, nlink1, exact resolved home child,
recognized filename, no matching lock sidecar, no modification in the last1h,
stable metadata in two observations, and no live cwd/FD/mapping/command use.
Audit own UID; zombies and recognized privilege-separated SSH transports are
recorded non-simulation exclusions, all other inaccessible processes fail closed.
Locks including stale-looking .cdslck/.nfs, configs, caches, hidden files and
all existing directories are excluded. Unattributed logs may be archived by
tool category, never relabelled as SAR results. Stop on unexpected contents.

Use bounded small-file streaming SHA256 (<=32MiB candidate total),256MiB/core0,
nice+10 and60s operation bound, no raw analysis or simulations. This is a small
metadata/archive operation, not heavy analysis; use an independent maintenance
lock and exact-file activity checks, not bypass the simulation admission gate.
No interruption/queue reordering of concurrent physical-repair simulations.

Before moving, recheck all eligible identities, stable hashes, live use and lock
sidecars. Same-filesystem link-then-unlink prevents destination overwrite and
keeps at least one verified name throughout; journal intent/link/source removal.
After linking recheck activity and identity/hash before unlinking source. Never
overwrite an existing archive target or automatically replay a partial journal.
Read back archived hashes, source absence and protected fingerprints/paths;
record any legitimate concurrently growing active logs separately, not as a
claim that their bytes stayed fixed. Preserve original metadata where possible.

Validation: name/path/type/link/age/use/lock guards, exact move preserving
content and sibling files, collision/refusal/idempotence, final JSON/arithmetic/
hash/protected paths/scoped diff. Deliver archived filenames and location,
retained reasons, complete visible and hidden remaining metadata. Archive does
not release file data space. Commit only owned paths, no push.

Results:2,506,077 bytes (2.390MiB),12 files, no additional candidate skipped;
six active logs retained. Normal ls51 to40 entries (new archive directory
included), hidden75 unchanged, total126 to115. All original directories,
configs, locks and nine caches retained; protected_metadata_changes empty.
Same inode/content/mode/mtime preserved per archived file, nlink1 on completion.
Server archive manifest includes recovery mapping. Seven focused tests, Python
compile, JSON/name-set/hash/metadata/readback/scoped diff passed. No simulation,
process interruption, source/PDK/OA edit, compression or file-data deletion.
Concurrent physical-repair checkpoint032eb9c landed during this task; preserve
it and its plan/log entry. The remaining log diff contains only our archive
entry. No PVT submissions or simulation paths were modified by this archive.
