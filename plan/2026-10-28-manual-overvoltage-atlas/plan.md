# 手搭 ADC 过压图解

- Goal: draw CDAC branch, full comparator, and complete native DFCNQD1/DFQD1 internals in Analog Canvas; export and explain each stress class in Obsidian.
- Dirty state: extensive unrelated user/session edits observed (branch ahead 31); leave them untouched. Create a new note/assets directory; append only this task's log entry.
- Owned: this plan; Obsidian_docs/Report/手搭ADC-过压图解.md; Obsidian_docs/assets/manual_overvoltage/; output/manual_overvoltage_atlas/; append plan/log.md.
- Remote OA: none. Analog Canvas current empty project project-4c5068fd-24b6-4585-8939-47a2722f2382 is the drawing target; no simulation or public gallery publication.
- Read-only: original netlists, standard-cell connectivity snapshots, PDK, prior reports/waveforms, all other Obsidian notes and sessions.
- Steps: verify native terminal mappings; draw and label true connectivity; export Canvas SVG/PNG/project; visually inspect; write concise event/state/cause/evidence notes with source links.
- Validation: device counts and D/G/S/B connectivity versus sources, exported image review, note asset/link checks, scoped diff check. Drawings are explanatory, not new T28 simulation models or a new design baseline.
- Commit policy: no commit or push in this task; proprietary topology exports remain local.
`n- Resume: preserve user-edited CDAC/comparator geometry; comparator labels may be reconciled to source, DFF layout may be reorganized. Re-read current Canvas before all edits.

- Completed 2026-10-28: four editable Canvas cells, SVG/PNG exports, concise Obsidian note plus five existing waveform figures. User CDAC/comparator geometry preserved; comparator references reconciled to native netlist. DFF drawings compacted and stage-labelled.
- Validation: 15/28/24 MOS terminal partitions (60/112/96 terminals) agree with source; CDAC M12/M14/C5 and distinct supply/body nets checked. DFF diagnostics clean. Comparator retained pre-existing dangling stubs/port-label observations, with correct device connectivity. Images reviewed and note links exist. No simulation/OA/library edits; no commit/push.

- Reopened: user rejects compressed DFF layout. Redraw signal-forward stages with local feedback, separate clock block, named clock/reset stubs, explicit region boundaries. Preserve full MOS connectivity; CDAC/comparator read-only in this revision.

- Completed DFF redraw: signal-forward master/TG/slave/output regions, local feedback, independent clock block below; native SVG/PNG exports refreshed and visually reviewed. All 112/96 MOS terminals retain source connectivity; CDAC/comparator content unchanged (CDAC revision metadata advanced only). One low-confidence MM61 label-clearance observation remains visually readable. No simulation/OA/library changes.

- Highlight/condense revision: add event-specific node/branch highlights without moving user geometry or changing connectivity; condense the owned Obsidian note to test conditions, event/evidence tables and optimization conclusions. Preserve all numerical evidence and source links, moving secondary details into collapsed notes where useful. Native styling if supported; otherwise clearly identified annotated SVG derivatives of native exports. Same ownership and no commit/push.

- Completed highlight revision: four report-only SVG/PNG derivatives use red upper excursions, blue lower excursions and A–D event keys; DFF regions shaded, clocks/full buffers retained in expandable full diagrams. Preserved fresh user geometry from native Canvas exports; no Canvas topology mutation. Condensed visible note by ~26%, preserved 99/99 extracted numeric/code constraints and all source links. Chinese reviewed manually (English scanners inapplicable); all four figures visually inspected. No new simulations, commit or push.

- Comparator clarification: replace ambiguous A4/A8 shorthand with exact combination sizes; add sizing/clock tradeoff chronology from comparator_design sources, simplify event explanations and explicitly distinguish measured early TT pass from later FF-hot-only combinations. Only owned note/log/plan change; no new simulations.

Comparator clarification complete: exact sizes, four-step balancing history and three event explanations replace confusing shorthand/attribution. Early TT pass explicitly bounded to early candidates; new0.9V PT test has separate plan. All note links valid; no Canvas geometry or connectivity changes.

User requests rollback of this round's Obsidian expansion. Replace only the
comparator section with A8 results plus three concise tradeoffs (precharge
strength, clock edges, input/recovery sizing). Remove the nominal-voltage PT
update and multi-version result tables from this note. Preserve CDAC/SAR/user
formatting byte-for-byte and retain complete experiment reports outside the
vault. Existing note/plan/log ownership only; no simulations, assets, OA or
baseline changes. Validate source numbers, links and unchanged outer sections;
no commit/push.

Completed: comparator section reduced to A8-only result/event table, exact compact size definition and three tradeoffs. Removed PT update and earlier version tables from Obsidian; full reports retained. Source values/links verified, CDAC and SAR sections byte-identical. No simulation or asset change; no commit/push.

User requests reference links moved to one collapsed end section only. Preserve current user-edited note text/images verbatim; owned note plus plan/log only. Validate all links retained and non-reference content unchanged. No commit/push.

Completed: three reference-only lines (six source links) moved verbatim into one collapsed Obsidian callout at end. All other existing lines/images preserved; link set and local targets checked.

User requests a short opening summary only. Add an evidence-bounded synopsis of CDAC/comparator high-supply excursions and SAR nominal-TT internal stress; keep remaining note bytes unchanged.

Completed: one short opening paragraph added; all original note bytes retained. No new claims beyond existing report, no other content changes.

User requests concise transistor sizes/m in CDAC and comparator sections. Add two compact parameter paragraphs verified against frozen FF/L60 CDAC and combined A8 netlists. W/L are literal netlist parameters; preserve nf separately, m denotes multi. All other user content unchanged.

Completed: two concise W/L,nf,m paragraphs added. CDAC cold/hot frozen dimensions match; A8 all15MOS checked. Removing the additions reconstructs original file bytes exactly. No circuit changes or commit/push.
