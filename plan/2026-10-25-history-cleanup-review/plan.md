# Historical data cleanup review

Status: complete review proposal; pending human approval, no deletion authorized.

User requests a local/server-separated list with sizes, experiments and retention
advice for human review. This task must not delete, move, compress, kill jobs,
submit simulations, modify OA/PDK or change any retention/adoption decision.

Starting HEAD01cf64b on exp/cdac-flat8-device. Existing Obsidian changes and
independent cdac10_dualrail sources are protected. Current reference-current and
physical-stress-repair evidence is protected even if a candidate was rejected.

Ownership: this plan; scripts/management/cleanup_review.py and its focused test;
management/cleanup/2026-10-25/ report and JSON manifests; appended plan/log.md;
one navigation link in management/README.md. Ignored metadata transport under
output/project_management/cleanup_review/. Everything else is read-only.
Remote OA mutation ownership: none. No remote writes, including agent deployment.

Scope: project-generated local output/artifacts/exports/snapshots, exact registered
legacy SAR8 run roots, known SAR8 task containers and managed SSD runs.
Also inspect shallow home/SSD simulation parents, recursing only into exact
project-library or actually registered project-cell names, not other ADE projects.
Exclude
environments, tools, Git databases, user data, all OA and unassociated server
directories. Report exclusions rather than claiming an entire E-drive/host census.

Steps: inspect existing registry/retention evidence; refresh bounded filesystem
metadata and live workload references without opening raw waveforms; build
non-overlapping local and remote groups plus exact file/subtree candidates;
distinguish logical size from allocated space, overlap and hardlinks; separate
safe cache suggestions, conditional raw/archive reduction and protected evidence.
Never call equal-size/name files byte-identical without full comparison. Avoid
double-counting parent/child references and avoid proposing both copies of a run
for deletion. Source/evidence availability is recorded, not assumed qualification.

Validation: focused category/parent deduplication/retention and arithmetic checks;
current complete scan timestamps, errors and live process observation; manual
review of largest paths, excluded OA and current baseline/candidate protection;
links/JSON/compile/scoped diff. If access or scan limits intervene, mark unknown,
not zero. Produce concise human Markdown and exact JSON review lists, all
approval fields pending. Local scoped commit only, no push, no deletion command.

## Result and validation

- Completed metadata census: local128 generated roots/files99.715GiB; server
  102 present non-overlapping roots205.948GiB,72 missing historical roots.
  No read/scan-budget errors. Added exact project-cell matches from known ADE
  parents, leaving unassociated entries unscanned. Excludes tools, environments,
  Git, actual OA and other projects. Source snapshots retain observation times.
- Five pending proposals,36 literal file targets. Local L-A1 transmission parts
  2.639GiB; server S-A1/S-A2 gzip/parts10.913GiB; optional local L-B1/L-B2
  old staged/idle PSF mirrors32.435GiB. Candidate groups are disjoint and cannot
  remove any required server-native retained copy. No whole-directory deletion.
- Path/case/size matching and historical transfer hashes are NOT described as
  fresh byte verification. Approval must be followed by full SHA256 and live
  usage checks; local/remote last-copy conflicts are rejected deterministically.
- Preserve90.075GiB stress four-case evidence, current-probe11.926GiB, new repair
  raw/candidates, R3/R4/final performance metrics and independent10-bit work.
  A live natscreen-sscold worker/Spectre was observed and explicitly protected.
  Keep reduced.json.gz where prior authorized cleanup removed the native PSF.
- Report separates directory footprint from conditionally removable bytes,
  excludes the72 missing roots from candidate savings, and uses client Beijing
  timestamps (server-reported clock retained separately in metadata).
- Five focused fixtures plus manifest arithmetic, no overlap/no last-copy
  conflict, metadata JSON/links, compile and scoped diff checks passed.
  No simulation, OA change, remote file write, deletion, move, recompression,
  old-process kill or push. Local scoped documentation/tooling commit only.
