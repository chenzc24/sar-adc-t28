# Project management registry implementation

Status: first-phase registry implemented and validated; live OA readback complete.

User approved the management proposal, starting with one registry of local
files, server directories and Virtuoso library/cell/view. Deliver a repeatable
read-only inventory command plus project/design/cell/run registries and a short
human entry point. Do not move, rename, delete or simulate designs or raw data.

Own management/, scripts/management/, this plan, plan/log.md, a small management
navigation paragraph in README.md and operating pointers in AGENTS.md.
Ignored diagnostics: output/project_management/. Remote OA mutation ownership:
none; read SAR_ADC_T28 and visible library metadata through supported bridge
readers and documented DD metadata example only. Preserve all other libraries.
Server filesystem access is read-only, scoped to explicit launch/result paths
and shallow lists of this project's known workspace/scratch directories.
No waveform contents, licenses, credentials, PDK or raw OA enter Git.

Starting HEAD f2862f8, branch exp/cdac-flat8-device. Existing user Obsidian and
independent10-bit dirty files remain protected. A new dirty edit to the active
stress_closure plan describes concurrent streaming recovery; treat all that
target's files and jobs as read-only. Do not overwrite its manifests or launch
analysis. Record actual source signatures and times without claiming frozen OA.

Implementation: define registry schema and responsibility/resource policy;
inventory Git-tracked/nonignored local files including missing tracked paths;
register ignored output roots and run receipts without reading large raw data;
query exact remote case paths, completion and aggregate file sizes with bounded
low-priority single-worker metadata scanning; inspect live Bridge libraries and
DD cells/views, reconcile legacy manifest and dependencies for selected tops;
produce navigation, discrepancy and unresolved ownership lists. Add planned WORK
library as planned only; do not create it in this phase. New SSD run root remains
unset until ownership/permissions/storage policy verified.

Validate unique run IDs and paths, safe containment, explicit observed versus
historical/missing/unknown states, path links, source hashes, library binding,
native exit distinct from analysis/verdict, no false baseline promotion and no
raw data copying. Focused fixture checks for registry parsing/identity and
missing-file handling, Python compile, full registry self-check and scoped diff.
Record limitations honestly if Bridge requires user load, while completing all
independent local/remote registration. Commit only owned files, no push.
Intended commit: management: register project sources, remote runs and OA cells.

User reports ic6 DISPLAY undefined while this inventory runs. Add bounded
read-only display diagnosis to this target: selected DISPLAY/XAUTHORITY values
from this uid's existing graphical processes, cwd and X socket presence only.
No full environment capture, cookie reads, xhost changes, GUI process starts or
kills. SSH shell without DISPLAY cannot establish a live OA inspection. Continue
all independent registration and clearly mark historical versus live OA state.

2026-10-25 resume: user says graphical connection restored. Previous local
inventory1180 entries,114 output roots,187 case records; server255 exact paths
plus59 shallow observations retained. Source HEAD advanced to1101428 from the
independent stress streaming task; its committed files remain read-only here.
Restore only the bridge transport, then retry live metadata. If CIW is not
loaded, independently inventory exact project OA directory names (no OA file
contents) and mark them as filesystem observations, never live DD confirmation.

## Delivered and verified

2026-10-25 restored the local tunnel with a hidden bridge-start client; live
CIW reads succeeded. No filesystem fallback was needed. Supported API returned
41 visible libraries and exact SAR_ADC_T28 path/tsmcN28 binding. Documented DD
enumeration found247 actual cells,232 schematic/183symbol/15VerilogA views;
119 actual cells absent from the legacy manifest and15 legacy-only entries.
Read-only schematic traversal covered68 unique project cells for R3/R4 and their
two testbenches, no read errors; respective closures35/41/36/42 cells. Other
libraries only have visible path/binding metadata, no content traversal.

Created management/project.yaml, designs.yaml, cells.yaml, historical run index,
four active input manifests, source/output/server CSV inventories, discrepancy
list, status page and usage guide. Each source observation keeps hash/time and
missing tracked files; generated inventories exclude their own recursive hashes.
Historical run identity follows local case path, preserving multiple remote
attempt/recovery references. Live native completion, analysis evidence and circuit
qualification are separate. Current stream analysis report registers Rgate/4 as
rejected for stress repair, without altering independent experiments or OA.

Latest server pass registered256 exact references and60 shallow directories;
144 old references not found. They remain historical records, not failed-run
claims. Ancestor paths may overlap; totals must not be summed blindly. Existing
nonproject libraries/session directories remain read-only and separately labeled.
Local source/output/run counts are in timestamped snapshot.json because the
independent current-probe task may add files while this read-only census runs.

Five focused identity/path/observation/ownership fixtures pass; scripts compile,
full registry uniqueness/recipe-hash/dependency/link checks pass, scoped diff
reviewed. No OA mutation, move, cleanup or simulation. New WORK library and SSD
root remain uncreated/unallocated; defaults are declared, not falsely presented
as an enforced legacy-job resource gate. Unified execution is the next phase.
Preserve independent current-probe files and all user dirt. Commit only owned
registration files and navigation/log pointers, no push.
