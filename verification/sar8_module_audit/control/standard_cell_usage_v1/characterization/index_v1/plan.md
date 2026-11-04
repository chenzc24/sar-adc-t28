# Managed dependency archive index preparation

Goal: one analysis-only dependency audit bound to the real completed
sar8audit-ctrl-usage-baseline-ff-v1 source and its actual library SHA. Verify
source/registered inputs/native PASS, library and archive identities; stream only
archive member metadata. No circuit rerun, library body retention, db loading,
extraction, installation, OA change or cross-version compatibility verdict.

Own this index_v1/ subtree only. Parent owns managed registration/execution and
shared plan/log. All baseline/recovery inputs, results, library/PDK and archive
are read-only. Unrelated dirty user/Obsidian/10bit/management state is preserved.
Remote ownership:none. Optional lightweight known-tool-setup inspection may
return executable paths only, never credentials or license-environment values.

Budgets: one thread,256MiB RSS,1024MiB virtual,1800s managed wall ceiling with
earlier internal checkpoint deadline; exact compressed bound13,657,415,950B,
64GiB decoded,1MiB total run-output target and32MiB collection. Fixed64KiB
stream buffers; never read/allocate a member-sized db. Output/checkpoint guards
leave room for management/input metadata. Bounds yield explicit incomplete
results, not automatic retry/resume under another identity.

Steps: implement fixed-chunk gzip/tar metadata parser and source-bound wrapper;
freeze exact archive/source config and recipe; focused synthetic stream/bound/
integrity tests; validate syntax, metadata and frozen inputs. Parent dispatches.
May stop early after exact target FF member and relevant release metadata are
located, explicitly leaving archive index incomplete. Unknown members/conditions
stay unknown. Expected outputs: small member NDJSON, checkpoint, result proof.
No commit/push or shared edits.

Preparation checkpoint: fixed64KiB zlib/tar parser, PAX/GNU-name metadata bounds,
CRC/tar-tail checks, escaped-path output bounds, source/actual library+PDK SHA
and before/after archive identity implemented. Exact source run/host596/thu-wei
bound; no original source/raw/failed-derived changes. Metadata JSON/NDJSON only,
640KiB index/48KiBcheckpoint/64KiBresult with1MiB whole-run budget. Deliberate
incomplete/early-locator states remain distinct from complete index; no resume.
Three focused synthetic tests passed, including body skip, early267MB header,
all input/time/output guards and corrupt/truncated/end/prefix validation.

Optional known-tool-setup query first hit30candidate guard and retained failure.
Safer bounded follow-up retained first30 and stopped after one10301B known
.cshrc.synopsys file; no executable confirmed in that subset. No compiler/help/
GUI/install or credential output. Tool availability/license remains unknown.
Final runtime recipe/inputs frozen with focused receipt; parent owns execution.
