# Native DFF usage evidence and one diagnostic contrast

Goal: measure actual U19 CP/D/CDN slew and swing from the completed FF storage
history, enumerate its exact first-hop output load, and prepare one small native
DFF comparison with MM64/MM65 currents and simultaneous internal voltages.
No full-storage rerun or library-internal modification is authorized here.

Ownership: this standard_cell_usage_v1/ directory only. Remote OA: none.
Parent owns managed registration/execution, shared plan/log, adoption and Git.
Frozen packages, collected receipts/raw, library/PDK, sibling modules, Obsidian,
10-bit sources and management remain read-only. Existing dirty changes are
outside this owned directory and are preserved.

Use the existing FF raw-derived history, library_truth/probe and exact native
load boundaries as read-only dependencies. Characterization table coverage,
recommended operating conditions and absolute terminal screening are separate;
missing characterization evidence remains unknown. Do not copy library bodies.

Steps: verify source identities; compute original-time input-edge crossings and
swings; enumerate native load pin/device connections; select one informative
input-slew/load contrast; create a small unchanged-library DFF fixture and bounded
measurement/analyzer/recipe package; record comparison limits and evidence.

Validation: exact source hashes and load/target connectivity, single-variable
deck delta, targeted current-node mapping/KCL completeness, original external
PWL/sample contract, local syntax and minimal deterministic synthetic checks.
Spectre feasibility and contrast results stay pending managed parent execution.

Artifacts: usage_evidence.json, README.md, fixture netlist, measurement and
suggested recipe(s), focused consistency receipt in this directory. No commit
or push; checkpoint delivery to parent only.

Checkpoint2026-10-27: verified original FFv2 canonical registration and all frozen
inputs, collected receipt, full30060-row lossless waveform SHA and known rawSHA.
Measured actual CP10/90 slew2.772669..2.800745ps versus16ps commands; D3.164148..
3.382142ps, CDN3.260777..3.481345ps. All threshold brackets retained. Exact three
native first-hop output loads retained; no effective load capacitance fitted.
Local metadata has filenames/CCS.db existence only, not characterization tables;
no remote library query or library-body copying. Slew/load and transient lifetime
compatibility remain explicitly unknown.

Selected CK-series-impedance contrast (direct vs ideal2kOhm) preserves original
native driver and DFF, all external PWL/sample contract, output/RC loads, FF0.99V
and-40C. Both cases58MOS/348pairs; baseline36V73I, contrast37V75I. Six exact
internal KCL incident-port sets include all MM64/MM65/MM66 native ports. Only
total terminal currents are measured; region/intrinsic split stays unknown.
Proposed baseline peak/time reproduction gates are diagnostic, not stress waivers.

Two focused consistency tests passed: leaf-level source equality/single resistor
delta and complete measurement/PWL/hash mapping; synthetic native parsing checks
simultaneous stress extrema, current signs/KCL residual visibility and slew brackets.
Synthetic data was temporary and is not circuit evidence. The local generation
check caught and removed a duplicate options statement before freezing. Final
AST/JSON/link/whitespace and scoped diff checks recorded in test_receipt.json.
No managed registration/submission, remote command, OA mutation, shared-plan/log
edit, adoption, commit or push. Parent owns the next managed serial execution.
