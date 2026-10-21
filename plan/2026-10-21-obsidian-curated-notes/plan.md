# Establish the reader-facing Obsidian notes

## Goal

Create `Obsidian_docs/` as a separate, human-facing Markdown vault alongside
`docs/`. Start with a reading entry, the requested design-history review and
a dated current-design snapshot. Preserve engineering reports as evidence;
do not copy them wholesale or change circuits.

## Dirty-State Note

Starting branch `exp/cdac-flat8-device`, HEAD `4958ad1`.
Only the unrelated untracked `cdac10_dualrail` configuration, VA modules,
plan, scripts and verification files are present. They are read-only and
excluded from this target. A separate main-width experiment has been launched;
its progress/results are not owned or monitored here. Shared README/log edits
will be checked again before staging to preserve concurrent work.

## Local Owned Files

- `Obsidian_docs/首页.md`
- `Obsidian_docs/设计流程复盘.md`
- `Obsidian_docs/当前设计.md`
- `.gitignore` (vault-local personal state only)
- `README.md` (one reader-facing entry)
- `plan/2026-10-21-obsidian-curated-notes/plan.md`
- `plan/log.md` (one factual append)

## Remote OA Owned Objects

None. No bridge, simulator, Obsidian GUI or vault registry mutation.

## Read-Only State

All existing `docs/`, specifications, models, scripts, verification records,
generated outputs, PDK/OA state and the user's existing personal vault.

## Shared Dependencies

Project design reports and Git history through `4958ad1`. The current source
is R3 with B reference-gate repair. The 500-kHz baseline and its offline
decomposition are recorded; 2x/3x main-width experiments have launch evidence
only. Notes must distinguish dated evidence, ideal boundaries and open gates.

## Expected Work

1. Create three concise Chinese notes with working in-vault wiki links.
2. Keep provenance as repository-relative paths, explicitly outside this vault.
   Do not promise those paths resolve as internal Obsidian links.
3. Add a repository entry and ignore only this vault's `.obsidian/` and `.trash/`.
4. Validate links, sources, UTF-8/front matter, diff and owned-file boundaries.
5. Record and commit the bounded documentation change; do not push.

## Expected Artifacts

Three Markdown notes only; no copied figures, raw results, generated tests,
plugins or application settings.

## Validation And Pass Criteria

- All three notes decode as UTF-8 and have parseable YAML front matter.
- All wiki links resolve to one of the three notes.
- All cited repository-relative source paths exist.
- No source/evidence files change; no simulator or remote calls.
- Representative `.obsidian/` and `.trash/` paths are ignored, notes are not.
- `git diff --check`, scoped staged review and final `git status` pass.

## Commit And Push Intent

Commit: `docs: establish curated Obsidian design notes`.
Push: not requested.

## Outcome

Created three Chinese notes, five valid wiki links, repository-relative source
references, one README entry and two vault-scoped ignore rules. Existing
engineering reports and the personal vault were not changed. The dated
snapshot explicitly stops at `4958ad1`; no live width-sweep result is claimed.

Strict UTF-8 decoding, YAML front matter parsing, wiki-link resolution,
source-path existence and ignore checks pass. The first YAML pipe check used
Windows' Python default input encoding and rejected otherwise valid UTF-8;
rerunning with `python -X utf8` passes without altering note contents.
`git diff --check` passes. Scoped staged review and commit follow.

During validation an unrelated `docs/b_sine_main_w.md` appeared untracked.
It and the ongoing experiment remain untouched and will not be staged here.
No Obsidian registry/settings, remote OA, simulator, automation or PDK changes.
