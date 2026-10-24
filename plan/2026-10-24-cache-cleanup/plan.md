# First-stage duplicate cleanup

Status: complete, 2026-10-24. User authorized removal after verification.
Owned: this plan, scripts/maintenance/verified_cache_cleanup.py,
verification/cache_cleanup_20261024.json, append-only plan/log.md;
scripts/maintenance/apply_verified_cleanup.ps1 and its deletion receipt
verification/cache_cleanup_20261024_deleted.json;
individual verified .gz and waveform.pickle files inside project output.
Remote ownership: none. Raw PSF, NPZ, receipts, logs, results, source decks,
final figures, user dirty Obsidian and cdac10 work remain read-only.
Initial branch synced; preserve all unrelated dirty/untracked changes.
Method: gzip decompressed SHA256 must equal retained raw file; pickle must
match existing receipt, regenerate from native PSF using existing parser,
compare every value and exact protocol-5 serialized hash. Skip ambiguity,
unsupported types or mismatch. Keep regeneration schema and source hashes.
Use bounded exact file deletion only (no recursive deletion); verify resolved
paths remain inside output and no tracked files are selected. Record original
file size/hash and survivor hashes, pre/post free space and deletion outcomes.
Validation: audit first, scoped manifest review, then apply only approved list;
verify survivors and final outputs unchanged. Local commit only, no push.

## Outcome and recovery

Deleted 4 gzip duplicates and 17 exact-regenerable pickle caches, totaling
15,204,425,361 bytes (14.16 GiB). Free-space delta 15,204,466,688 bytes;
E free immediately afterwards 95,974,932,480 bytes (89.38 GiB).
424 documents, figures and verification files passed before/after hashes.
All original PSF files, NPZs, logs, receipts, final results and user work remain.
Skipped 7 refgate caches with no unique native transient in expected location,
one passive AC cache and one gzip transport fixture. No raw deletions.
NumPy PickleBuffer hashing compatibility fixed during audit; restarted only
the owned audit helper and resumed completed checkpoints, before any deletion.
Scoped syntax checks and manifest/path review pass. No remote operation/push.

To restore a deleted cache, from project root use:

```powershell
.venv/Scripts/python.exe scripts/maintenance/verified_cache_cleanup.py restore '<absolute path from manifest>'
```

The restore action verifies retained raw and parser hashes, recreates the same
protocol-5 bytes and refuses overwrite. Old report regeneration scripts may
require this restoration first. Removed gzip files are transport copies of
the retained native files; content can be recompressed, archive bytes need not
be identical. Deletions bypass recycle bin to actually release disk capacity.
Full file-level evidence: verification/cache_cleanup_20261024.json and
verification/cache_cleanup_20261024_deleted.json.
