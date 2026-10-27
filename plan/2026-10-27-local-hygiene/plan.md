# Local SAR ADC artifact and documentation hygiene

Owner: root. Date: 2026-10-27, Asia/Shanghai.

## Goal and boundaries

Respond to the user's request to clean obsolete SAR_ADC artifacts and documents.
Replace competing stale landing pages with concise dated navigation, preserve
their complete historical text, and remove reproducible ignored Python caches.
Keep exact inventories and a receipt. No circuit or qualification changes.

Initial branch: exp/cdac-flat8-device, HEAD b7cd241. Existing dirty work includes
Obsidian moves/notes, management README and execution code, the shared plan log,
manual ADC, module audits, independent cdac10 work and repair evidence. These
are unrelated and protected. Only append this target's entry to plan/log.md;
verify its original bytes remain a prefix. Do not stage other owners' changes.

Owned local paths:
- README.md; docs/README.md; docs/project_status.md;
  docs/archive/2026-10-27/{root-readme,project_status}.md.
- management/cleanup/2026-10-27/; this plan directory; append plan/log.md.
- Ignored cache leaf files under explicitly inventoried __pycache__ and
  .pytest_cache directories, excluding .git, .venv, Obsidian_docs and the dirty
  manual_adc/cdac10_dualrail/sar8_module_audit/management execution subtrees.
- output/local_hygiene_20261027/ for the initial ownership observation.

Remote OA owned objects: none. No remote operations. Read-only: all OA, PDK,
other repositories/worktrees, environments, raw waveforms, frozen inputs,
run/cell/design registries, user notes, other plans and evidence. Keep the old
review model/source locks and their document dependencies byte-identical.
No plan archival or experience extraction. No baseline adoption.

## Implementation

1. Save initial Git state and hashes of all non-owned tracked/untracked local
   sources, plus metadata for generated roots; reject reparse targets.
2. Archive the two superseded navigation documents; rebase their Markdown
   links and label their observation dates. Keep the former project_status
   path as a redirect. Repair the Obsidian link using the user's existing path.
3. Add a dated index distinguishing manual ADC work, ongoing module audits,
   preserved R3/R4 evidence, historical 10-bit 5+5 work and independent cdac10.
   List all top-level engineering documents, preserving original report paths.
4. Freeze an exact cache-file manifest (path, size, mtime, SHA256), require
   ignored/untracked regular files in this repository, recheck and remove
   only those literal files. No recursive directory deletion or raw deletion.
5. Record current local output footprints and retained categories; historical
   footprint is not removable space and old approvals are not reused.

## Validation and result

Validate archived text against original SHA256 after reversing link rebasing;
check every new/rebased local Markdown link and the document catalog coverage.
Require exact cache target absence, all non-owned source/evidence hashes
unchanged except explicitly observed concurrent work, all retained generated-file
metadata unchanged, and original log prefix intact. Record before/after hashes
of any concurrent change; do not modify or stage it. Parse JSON, run git diff
--check, review scoped diff/status.
No simulations or broad test suite for documentation/cache-only work.

Artifacts: management/cleanup/2026-10-27/{review.md,inventory.json,receipt.json};
historical navigation in docs/archive/2026-10-27/. Cache bytes removed and disk
free-space delta are distinct. Report preserved large waveform groups plainly.

Commit policy: local scoped commit, message `chore: clarify SAR ADC document
history and clear ignored caches`; include only this target's changes and its
own appended log entry. No push.

## Concurrent observation

The manual ADC owner updated its existing untracked implementation plan during
this task to add behavioral authoring scope. Its hash changed from
f324fcf427380b5bce2ca6f86dee904d6da442cfe7e1b1b7f0902f1945786f4b to
04415e9ffbe3a3927a269dbea6e60f5b985bb00f4f568824d01f1dd0c2be212d.
No cleanup operation targeted that plan. Record this concurrent edit explicitly;
do not claim all protected files remained byte-identical. Other source records
and all retained generated-file metadata are checked separately.

Global diff checking exposes pre-existing whitespace in the protected user note
Obsidian_docs/Report/Wrap-up & Experience.md:13. Preserve it; require the owned
and staged diffs to pass separately and record the global diagnostic.

Status: complete. Validation passed for 191 local links, 84-report coverage,
2 archived texts, 369 absent cache files / 4,499,577 B, 3,492 unchanged protected
source records and 53,304 retained generated-file metadata records. One concurrent
plan update is recorded above; original shared log prefix is preserved. Only
this target's paths and appended log entry enter the local commit; no push.
