# Eight-bit asynchronous SAR architecture revision

## Goal and scope

User selects asynchronous SAR. Replace the current synchronous **target
proposal** with an external-frame / internal-self-timed architecture, explicit
handshake, cell boundaries and review timing. This is an architecture-review
milestone, not permission to claim implemented native logic or measured delay.
The user has deferred Virtuoso work; remote OA ownership: **none**.

## Starting state and ownership

Branch exp/cdac-flat8-device, previous synchronous milestone 5b012cd.
Untracked config/cdac10_dualrail.yaml, models/veriloga/cdac10_dualrail_*.va,
plan/2026-10-20-cdac10-dualrail/, scripts/cdac10_dualrail/ and
verification/cdac10_dualrail/ are unrelated, read-only, excluded from staging.
The active specification remains eight-bit flat CDAC; no resolution change.

Owned local files: this plan; config/design_spec.yaml (control selection and
legacy timing annotations only); config/sar8_async_timing.yaml;
docs/sar8_async_logic.md; docs/figures/sar8_async/; bounded active-status edits
to README.md, docs/architecture.md, docs/sar8_logic.md and
config/sar8_logic_timing.yaml; bounded entries in plan/log.md and
docs/design_log.md. Ignored evidence: output/sar8_async/.

Canvas: existing project project-d469b166-a782-4714-81de-7ae661fe2f45.
Create SAR8A_REVIEW, SAR8A_TIMING, SAR8A_CELLS, SAR8A_HANDSHAKE documents.
Preserve every synchronous electrical document; mark the previous review as
historical if needed. Keep the Editor open. No credentials in files/commits.
Use supported MCP operations only (not unsupported set_document_grid).

Read-only: PDK, every OA cell, old VA/controllers, prior exported synchronous
gate netlist/checker, analog evidence, unrelated experiments. The periodic
200-MHz executable testbenches remain historical comparison fixtures, not
new asynchronous evidence.

## Dependencies / architecture decisions to resolve

- Keep 10 MS/s, 40-ns acquisition and existing sample/reference frame edges.
- StrongARM reset is CLK=0, OUTP=OUTN=1; polarity OUTP>OUTN means positive.
- Completion must be fresh, eval-qualified and consumed once. Logic rail
  validity does not prove analog regeneration or absence of metastability.
- Keep CAPTURE, comparator RESET and token ADVANCE separate; token must not
  change while capturing. Reset acknowledgement plus a minimum reset guard
  must precede the next evaluation.
- DAC settling and BBM require characterized minimum delays, not a free
  analog settled detector. Start conservatively, without overlapping phases.
- Independent frame deadline aborts a stalled loop, inhibits publication and
  retains the old word. New acquisition invalidates any old local events.

## Steps / validation / acceptance

1. Inspect active spec, comparator reset/polarity and existing frame source.
2. Document selected asynchronous protocol, timeout/abort priority, cell
   interfaces, bundled-data margins and conservative illustrative timing.
3. Update active status without relabelling existing synchronous simulations.
4. Draw architecture, handshake, cell hierarchy and illustrative timeline in
   separate Canvas review documents. No drawing-only block is represented as
   an electrical netlist or working asynchronous gate implementation.
5. Parse YAML; calculate timing sum independently; targeted document checks;
   export/read back each new Canvas document and visually inspect PNGs.
   Run git diff --check and review scoped diff. No Spectre claim.
6. Record achieved and pending work; scoped local commit
   `docs: select asynchronous SAR control and define cell contracts`.
   No push requested. Stop at the reviewable proposal, before gate/OA build.

Expected artifacts: local design note/config, Canvas project backup and PNGs
under output/sar8_async/, curated review SVGs under docs/figures/sar8_async/.

## Result

Selected asynchronous control in the active spec with explicit proposal status;
retained legacy 200-MHz fields with fixture-only scope for reproducibility.
Defined conservative sequential handshake, separate CAPTURE/ADVANCE, qualified
reset/completion, independent deadline and nine module cell contracts.
No new gate circuit, VA model or remote OA cell was implemented.

Reconnected Canvas using the user's fresh private Claim after the old session
expired. Four new review documents are exported and visually inspected;
SAR8A_REVIEW is the project top/current entry, and the previous entry is now
SAR8_SYNC_REVIEW. Previous electrical documents are preserved. Function arrows
and drafting blocks are explicitly not electrical topology. A first draft
transaction with half-grid rectangle centers was rejected without mutation;
integer centers were used for the successful revisions.

YAML parse and independent arithmetic passed: reference per-bit 5.4 ns,
completion 86.9 ns, 1.1 ns before the new 88-ns deadline; the constructed
variable-comparison example ends at 79.77 ns. Neither is measured timing.
Targeted EightBitMigrationTest.test_active_and_historical_specs passed.
The first local JSON read used Windows default GBK and failed; UTF-8 readback
corrected it. All four new documents, preserved eight documents and the new
top identity were confirmed from the exported canonical project. Counts:
review 62, timing 89, cells 50, handshake 46 drafting objects and zero new
electrical instances. Exact comparison of instances, routes, contacts/nets,
junctions, annotations, drafting and no-connects against the previous export
confirms all eight old documents retain their drawing/electrical contents.

Curated SVGs and ignored PNG/project export are saved. YAML/SVG syntax,
git diff --check and scoped diff review passed. This architecture milestone
is complete with a scoped local commit; no push. Gate/receiver hazards, physical delay/PVT and native
Virtuoso implementation remain next-phase work after review.
