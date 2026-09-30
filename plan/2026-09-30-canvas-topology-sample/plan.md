# Bootstrap topology review sample

Implement approved static-image/netlist linkage in the local review UI: five
functional groups, four phases, three analysis topics, device/net selection and
typed facts/conditional inference/verification questions. No live Canvas claim.
Own review/, scripts/review/, verification/review/, this plan and bounded log entry.
Untracked bootstrap-turnoff-charge-screen plan/script are unrelated and preserved.
Remote OA owned: none. Circuit reports, PDK and existing experimental sources read-only.
Input is the user-supplied SKY130-labelled example, not the T28 simulation DUT.
Preserve source netlist and screenshot; D/G/S/B interpretation is an explicit
unverified model-interface assumption. Keep body connections and external-load gap.
Use stable instance/net IDs plus normalized image anchors; no fabricated Canvas IDs.
Validate parser/anchor coverage, topic references, build and JS; browser phase,
topic/device selection, keyboard dialog close and layout. Generated screenshots in
output/review. Commit locally feat: add bootstrap topology review sample; no push.

## Outcome

Implemented 15 device hotspots, five functional groups, four phase views and
three typed analysis topics. Device selection shows parsed terminals and reverse
topic links. Original supplied PNG/netlist are preserved; hashes pin manual map
to both inputs. Net aliases are display-only. Existing sampling nodes open this
explicitly separate abstract example; other modules retain unconnected slots.
18 focused tests pass; JS syntax/build/diff checks pass. Browser keyboard checks
covered all phases/groups, topic-to-net highlights, MN11 terminals/reverse links,
Escape close and 390px/1100px no-dialog-overflow. Screenshot saved under
output/review/topology-preview.png. Pointer automation was not used as acceptance
after the previous session's input limitation. No live Canvas/OA/simulation change.
Concurrent circuit task committed independently during work; no new experiment
conclusions were folded into this abstract sample. Local commit only, no push.
