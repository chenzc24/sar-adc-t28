# Clean native Canvas gate-level SAR8 controller

## Goal and authority

Explain the selected timing and build its complete, tidy hierarchical gate
circuit in the user's current Analog Canvas project. User explicitly requests
only this version, so remove old sync/handshake/review pages after a restorable
full export and a successful replacement. Do not touch Virtuoso or simulate.

## State and ownership

Start51dbf70, branch exp/cdac-flat8-device. Concurrent CDAC10 and CDAC8 uniform
scale files/plans are unrelated and preserved. Read-only: circuit.py, native
exports, PDK, all existing verification and all remote OA state.

Own current Canvas project project-d469b166-a782-4714-81de-7ae661fe2f45 and its
replacement documents; local scripts/sar8_simple/canvas.py,
verification/sar8_simple/canvas.json, docs/sar8_simple_canvas.md,
this plan and one plan/log.md entry. Generated exports/readbacks/renders and
backup in output/sar8_simple_canvas/. Remote OA owned: none.

## Approach

1. MCP exact-origin connection; snapshot/index and full Project Code backup.
2. Derive all connectivity from current21-cell simple hierarchy. Use native
   gate symbols, explicit state cells and real circuit connectivity, not boxes
   and text pretending to be an electrical schematic. Retain exact MOS/RC
   leaves where possible; no fabricated PDK qualification or hidden states.
3. Clean hierarchical top and readable timing, bit-chain, SAR-bit, P/N-bank,
   BBM and primitive pages. Shared supplies/control use labelled nets when
   full-page routes would obscure the circuit. All8 repeated slices explicit.
4. Replace the current project after checking pinned source connectivity and
   backup. No unrelated external projects or OA cells changed. Keep editor open.
5. Verify structural correspondence against generated reference netlists,
   inspect hierarchy diagnostics and formal renders, fix bounded drawing issues.

## Validation and deliverables

Require all source instances and terminal/net incidence matched or documented
abstraction; no old control state/pages. Native Canvas electrical connectivity,
render review for every cell family and top, stable source/export hashes. Python
compile and focused generator/audit execution, JSON parse, diff checks. Save
final project backup and concise mapping/evidence; a diagram is not a new SPICE
simulation. Keep qualification limits and timing seeds explicit. Local scoped
commit docs: rebuild clean SAR8 simple Canvas hierarchy; no push requested.

Native placement/model-binding prototypes are temporary parts of the owned new
cells, replaced by the generated complete project. Use canonical Project Code
replacement (same validated editor planner) for this21-cell reconstruction;
retain symbol definitions captured by native placement and generated internal
Cell symbols. This intentionally changes top to the new controller, as the old
top is one of the obsolete review pages the user asked to remove.

## Result

Completed in the same Canvas project,21 current cells only, top selected and
fit. Saved cloud yc3a7geyrf revision2. Source topology, all163 direct definition
instances, MOS/RC parameters and hierarchy pass native structural comparison
across21 cells; only port-order deliberately ignored. Every Cell reports zero
errors/warnings, all21 PNGs exported and visually inspected. PDK models not
copied, no Canvas/Spectre simulation or OA mutation. Full old/new Project
backups and render/reference artifacts remain in ignored output directory.

An initial Project Code input was atomically refused for duplicate label order,
then fixed before successful replacement. One concurrent top PNG export reported
EDITOR_DISCONNECTED; fresh status was attached and sequential read/export retry
passed, without replaying a mutation. Final Cell diagnostics and cloud Save
confirmed. Source compile/focused generator and JSON/SVG/hash checks pass.
Only target source/docs/plan/evidence staged; local commit, no push.
