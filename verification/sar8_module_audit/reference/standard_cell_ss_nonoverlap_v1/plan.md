# Actual switch-port SS non-overlap evidence — 2026-10-27

Owner: reference/CDAC session. Write only this standard_cell_ss_nonoverlap_v1/
subtree; parent owns shared plans/logs and managed execution. Existing branch
exp/cdac-flat8-device ahead30, shared management/Obsidian/log changes protected
and nonoverlapping. No remote job, new candidate, frozen-input/result edit,
OA/library/PDK modification, commit/push or baseline adoption.

Source is completed sar8audit-ref-bbm-stdcell-sscold-v1,10956 native points,
11files22126021B, resultSHA
c61c9a71f01e9485c455ec26e0424cfbd2847fae9e10d2d1618cdebb9be8615e.
Original standard_cell_bbm_v1/comparison/report.md already reports halfVDD
ordering, opposed drain-current peaks and four reference settling times.
Reuse those findings and only add actual source-referenced Vgs/Vsg, all four
active reference switches' D/G/S/B partition, capacitor/bottom KCL and actual
reference-source exchange. Do not repeat a general review or simulation.

Scope: bit0 XSN0/MN_LOW,MP_HIGH and XSP0/MN_LOW,MP_HIGH with complete existing
physical load and ideal CODE/rails; other bits static, comparator reset. SS
0.81V/-40C with actual VREFP0.9V/VREFN0V. Exact declared source/body mappings
come from frozen netlist/metadata readback. Do not infer fixed Vth, a channel
on/off boundary, or signoff from halfVDD, terminal current or voltage alone.

Verify recipe/input/receipt/native stream SHA, PASS/END, current initialization,
timestamps and original connection mapping. Project local native rows in small
blocks; preserve all10956 timestamps. Plot one compact figure for both command
directions: actual source-referenced four gate biases, drain-vs-source opposed
current diagnostics, bottom/reference settling. Retain source/gate/body currents
and capacitor-current closure at actual peak samples in structured evidence.

Deliver concise report with confirmed facts vs unknown channel overlap/deadtime;
if no intrinsic conduction decomposition exists, state exact missing internal
observable and smallest conditional measurement rather than inventing a missing
external pin or model hierarchy. No new run preparation. Validate numeric
readbacks/KCL and reused measurements, view final image, AST/UTF8/link/whitespace
checks and scoped diff. No final PVT/non-overlap qualification.

## Completed checkpoint

Original report reused for halfVDD ordering/reference establishment; no duplicate
general design review. Verified9 frozen inputs, managed recipe
24f9e00fd4bd98704a43a6e3f5f367e7ea44810209313d366a8bae9417b9b770,
proposal f36c9d35de24675e06ee1a5a077974aeaa104d4e55c049569a2db2bdfa6cb9d4,
11file/no-skip22126021B receipt and complete uncompressed native stream hash.
PASS/END,652 initialized currents,10956 monotonic0–52ns points, actual four
switch D/G/S/B maps and all16 current ports confirmed. Local128-row projection
and final analysis2.226s; no remote operation or waveform rewrite.

Deliverables evidence.json,8-row actual_switch_bias_summary.csv, concise report
and one3x2 phase figure. Final image inspected after shortening/moving current
legends: readable real biases, drain/source distinction, bottom target and
symlog1mV band, exact fixture conditions. No time or amplitude alignment.

New evidence: high-select N source-exchange peak10.763921uA@43.344090ns;
at old D-peak43.358315ns low Vgs0.882535/high Vsg0.847107V, low D12.333303uA,
source-out10.300371uA, gate/body-out2.032931uA. P low-select old Dpeak1.203307uA
at48.495550ns instead has source-out0.009177uA and gate/body-out1.194130uA;
low Vgs0.034142V. It is not valid to call all opposed D current channel
shoot-through. Other3 phase source-exchange peaks25…44nA, not zero or proof
of safe deadtime. Full bottom KCL max1.905pA; all pointwise terminal partitions
and capacitor currents retained. Existing four1mV reference-settling results
remain true and independent from switching risk.

All external gate/source/drain/body pins are present. Missing only verified
internal dynamic conduction/state observable needed for a channel-only
overlap/deadtime judgement. No guessed Vth/threshold/internal instance used.
Report gives bounded four-macro measurement suggestion without preparing a
run; high N slow-off interface remains actionable from actual port evidence.
Other directions remain unqualified, not falsely failed from D-only peaks.

Validation: exact mapping/old peak reuse,8 unique device-phase rows, Vgs/Vsg
reconstruction, current partition/KCL, unchanged establishment flags, null
channel-on/off durations retained, AST/UTF8/link/whitespace/scoped diff checks.
No original data/input/model/OA or shared-plan/log edit; no new candidate,
simulation, commit/push or adoption. Parent owns shared status integration.
