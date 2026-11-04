# First local driver0 reproduction fixture

Status: prepared and statically audited, **not Spectre-compiled or simulated**.
No managed registration, remote submission, OA mutation, commit or push.
Only priority1 XDRV0 advances; no L90/GNN4 or sizing experiment is included.

## Frozen source and retained circuit

Source `output/sar8_physical_repair/sar8fix-loaded-ref-ffcold/`:

- dut.scs SHA256 `a42e44613b4b1a8a74876a4c996f5bd2bf2e74bf13da6729818ab85bde5a21de`
- test.scs SHA256 `e6160bb51a25fd41cec7a196da1bdbb9a701ec88f31de13a7d8bc8608d6ddcbf`

`build_first_fixture.py` extracts source instance rows and copies selected native
leaf subcircuits unchanged; PDK model contents are neither read nor copied.
Four explicit wrapper subcircuits implement the boundary cuts.

| Retained physical content | Audit |
| --- | --- |
| Both original bootstraps, core StrongARM and comparator loads | Original devices/connections unchanged |
| Full eight-bit differential flat CDAC, fixed dummy connections and all reference switches |18 MOM statements with original multiplicities; full reference loading |
| Reference input MUX/MSB inversion, eight capture DFFs and real CAP_CLK buffer | CAP_REQ input replayed; CAP_CLK/Q remain physical outputs |
| Eight BBM blocks, all drivers and all original Rgate segments | Original dimensions, multiplicity and connection records |
| Comparator receiver/forward timing cone, eight bit registers and physical token bank | Original core cells, retained as real dynamic loads |
|50ohm input/reference resistances,4pF reference decaps,5fF output loads | Original testbench rows/values |

The source has1833 MOS wrapper instances; extracted fixture1551. Exact flattened
record equality is checked for1177 retained bootstrap/comparator/CDAC/reference
capture-output/BBM/driver devices. Eleven protected immediate terminal fanouts
match: COMP_P/N, PR/NR, DATA, PHI_W, TOPP/N, GNNDRV, GNN0 and Q0. All nested
subcircuit port arities match. Counts describe topology, not aggregate transistor
width/multiplicity or electrical equivalence of the complete cut graph.

## Boundary and load limitations

29 independently replayed voltages: PHI_U, CAP_REQ, SAMPLE_INT, SEQ_SAMPLE,
CMP_CLK, RST0..7, D0..7 and CODE0..7. No retained active output is voltage-forced.
VDD remains ideal0.99V; reference source levels remain0.9/0V, with original
shared50ohm/4pF networks driving all reference switches.

Reference MUX D/CODE inputs are replayed. Retained readout registers drive
separate LOAD_D/LOAD_CODE nodes; their generated PHI_U is shadow-only. The
physical token bank receives replayed PHI_U. Original autonomous clock/SR,
capture-request and idle-reset generators are excluded. CMP_CLK is replayed.
`connection_audit.json` records cuts and missing loads explicitly.

The protected **immediate** receiver fanout is preserved, but the downstream
register-output-to-reference feedback/load and clock feedback are cut. These
state-dependent differences may affect receiver response through transistor
parasitics. Therefore structural checks do not prove original whole-ADC loading.
Require native-wave reproduction before current attribution or circuit changes.
New5fF output loads reside inside the wrapper; original flattening excluded the
external testbench, so alias counts at D alone must not be treated as equivalence.

## Startup, numerical settings and horizon

Every replay starts at the exact recovered t=0 voltage, including nonzero
microvolt residuals. No new IC, nodeset, shifted clock, startup pulse or clamped
logic value is introduced. Normal DC operating-point solve remains enabled.
Removed clock feedback changes that DC network; compare initial stored states,
TOP/reference conditions and capture sequence before accepting reproduction.

Stop is exactly6.5996504234270155e-08s, the last recovered native knot;
there is no invented66ns endpoint or unsupported constant-held tail.
Original requested numerical settings are retained, including gear2only,
reltol1e-6, vabstol1e-8, iabstol1e-13, gmin1e-12, scale/scalem1,
pivrel1e-3, maxstep10ps, conservative errpreset, lteratio10 and1ns
all-native-plus-strobe output. Only obsolete sensfile output path is removed.
Spectre X may override requested tolerances; compare actual effective settings
and simulator version in future logs, not just requested values.

## Measurements and current signs

`measurement_map.json`:1100 voltage saves,275 component-terminal current saves,
9306 MOS pair screens (1551 devices times six terminal pairs). Resistor-only
Rgate junction voltages are included; no reliance on the former all-MOS-node save.

| Current group | Saved terminals |
| --- | ---: |
| Driver0:28 MOS times4,40 Rgate segments times2 |192 |
| Four LSB reference-switch MOS times4 |16 |
| Comparator input pair times4 |8 |
| Four parallel bootstrap-main MOS times4 |16 |
|18 CDAC MOM wrappers times2 |36 |
| VDD, both reference sources, RREF and CREF |7 |

MOS current saves address the PDK **wrapper ports1/2/3/4 = D/G/S/B**.
They measure total component-terminal current (conduction plus modeled dynamic
current), not an assumed intrinsic channel-only Id. Rgate saves address wrapper
ports1/2; MOM saves address wrapper ports1/2. Aggregate multiplicity is already
inside each model instance: do not multiply the measured current again.
Port naming/probe realization must be checked against actual Spectre output;
a missing current causes measurement failure, never substitution with zero.

KCL covers every incident primitive-component port at these physical nodes:

| Node | Full incident-terminal list |
| --- | --- |
| GNNDRV | GNNCN:1, GNNCP:1, RGNN0:1 |
| GNNB | GNNCN:2, GNNBN:1, GNNCP:2, GNNBP:1 |
| GNNA | GNNBN:2, GNNAN:1, GNNBP:2, GNNAP:1 |
| GNNRG | RGNN1:1, RGNN0_5__dmy0:2 |
| GNN0 | XCDAC.XSN0.MN_LOW:2, XREF.XDRV0.RGNN1_5__dmy0:2 |

Unqualified names in first four rows are below XREF.XDRV0. Currents are positive
**into each component**; sum all incident component-port currents to zero.
The sum of driver drain currents alone is not complete KCL. Gate displacement,
bulk and passive currents must retain signs. Account for numerical gmin and
report residual before deciding any dominant coupling branch.

Core0.99V / IO1.98V terminal-pair screens are diagnostic limits, not lifetime
qualification. Save all six pairs, signed extrema and duration; a node excursion
alone does not establish every transistor's actual terminal stress.

## Candidate package and proposed acceptance

`generated/first_reproduction/` retains the original local full-native template
with a deliberately missing oversized PWL include. The separately identified
`generated/approximate_replay/` has dut.scs/test.scs/approximate PWL, total
22,749,015 bytes. Hashes are in its verification.json. It is local-review-only.

Recipe suggestion is not a registered recipe. Proposed resources:4 threads,
1GiB simulation RSS,256MiB streaming-analysis RSS,16GiB raw-output ceiling,
32MiB collection. These are proposed ceilings, not measured consumption.
Only compact plots/extrema/KCL summaries should be collected; retain native raw
under managed lifecycle policy. A reviewed streaming current reducer remains
required before dispatch.

Proposed diagnostic reproduction criteria, **not yet approved module specs**:
same event/node/sign/order; four stage/gate peak voltages within1mV; corresponding
half-rail edge estimates within2ps; all14 independent capture-input words and
stored-state sequence reproduced. Check initial and loaded TOP/BN/BP/reference
waveforms, not only the worst peak. Proposed KCL bound is0.1nA plus1e-5 of local
peak incident-current magnitude, evaluated on native points and reported with
charge integration. Parent must approve exact wave/initial-state comparison
windows and tolerances before an electrical pass is asserted.

First establish reproduction and close current balance. Then identify dominant
branch charge and test a single physical change; no change is authorized here.
