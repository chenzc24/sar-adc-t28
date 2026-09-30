# Isolated main-gate diagram

Goal: retain original pre-isolation diagram; use supplied isolated-gate drawing
and exact draft netlist for isolation and later sampling nodes.
Dirty: unrelated untracked top-plate-gmain-first-device plan and screening script;
preserve. Own review/topology/isolated/, review/flows.json, review/app/app.js,
review/app/topology.js, scripts/review/build.py, verification/review/test_build.py,
this plan and bounded plan/log.md entry. No OA objects; PDK/circuit work read-only.
TRACK/OFF exist in drawing but not supplied netlist. Do not invent switches in
the electrical netlist or treat net1 as driven. Cu is a primitive capacitor;
VOUT is internal, VCM a port. Keep this abstract fixture separate from T28 DUT.

Add versioned static snapshot with netlist/image fingerprints, semantic anchors
and per-phase analysis. Bind relevant nodes explicitly; preserve earlier links.
Verify parser/anchors and variant references, focused tests, build/diff/JS syntax,
browser old/new selection and device pins. Local commit only, no push.

## Outcome
Added immutable original-image copy and exact draft netlist under isolated/,
with 16 device anchors and separate phase/topic analysis. Four sampling nodes
select the new snapshot; pre-isolation nodes retain the original. No clamp
schematic is invented for the separate clamp-design node.
23 tests pass, including original net0 vs isolated net1 and Cu VOUT/VCM checks.
Build, JS syntax and diff checks pass. Browser checked both image versions,
MN11/Cu pin readback and no console errors. Screenshot:
output/review/isolated-diagram-preview.png. No OA, simulation or push.
