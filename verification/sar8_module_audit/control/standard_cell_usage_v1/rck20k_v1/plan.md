# Single-variable RCK20k diagnostic preparation

Authorized by parent coordination checkpoint2026-10-27. Own this rck20k_v1/
subtree only. Other dirty control/reference/comparator/sampling, Obsidian,
10bit, management, shared plan/log and frozen baseline/rck2k/liberty recovery
files are read-only. No remote/OA scope; do not register, dispatch, commit/push,
alter native-library internals or sweep values. Parent owns later admission.

Goal: clone the exact existing2k fixture, changing only RCK2000->20000Ohm in
dut.scs. Preserve test.scs, external PWL, driver/three real first-hop loads,
58MOS/348pairs,37V/75I saves, six KCL nodes and all functionality/stress checks.
Only measurement metadata case name changes; no threshold or timing-window edit.

Reuse frozen direct-gzip native reducer, writer, history/function observer and
usage observer. New wrapper uses those modules for the fresh native simulation,
not the old20MiB uncompressed export. Add only bounded native30/70 crossings,
explicit/.50 input-coordinate comparison and matching internal5ns edges/stress
comparison. Raw actual delayed clocks and internal crossings keep native brackets;
no time shifts or actual10/90 replacement. Preserve explicit unknown load/model
pairing and reliability qualifications.

Steps: source managed hash checks; exact deck/physical-leaf delta; bounded
extension and wrapper; one local consistency/synthetic test; recipe/manifest
freeze and local readback. Local tests are synthetic only, never circuit results.

Pass preparation: exactly one resistor value changed, all other physical leaves
identical; measurement thresholds/saves/PWL/model paths identical; old observer
fields intact; known nonlinear synthetic crossing correctly distinguishes raw
10/90 from derived30/70/.50; gzip export/348pair/function paths exercised once.
Python AST, JSON/recipe identities, relative links, scoped whitespace/diff checks.

Artifacts: dut.scs/test.scs/measurement.json, wrapper and transition observer,
source/basis/reference evidence, exact diff, suggested managed recipe and freeze.
No simulation or adoption conclusion; future stronger slew still screened at
strict.99V and actual delay. Stop the series-resistor repair direction if a
clear external slew change remains screened by internal regeneration.

## Completed preparation

Two focused test methods passed once in0.124s. Exact resistor-only physical
delta, unchanged deck/PWL/measurement conditions, frozen input identities,
six-node full KCL visibility and synthetic348pair gzip/functional chain checked.
Nonlinear synthetic edge gives raw30/70=3ps, coordinate=6ps, actual10/90=8ps;
these are analyzer checks, not simulated transistor results. AST/JSON/link and
scoped whitespace/diff checks passed. Source runtime inputs remained unchanged.

Final suggested recipe SHA256:
e4efbd1d98afbe366ee0f87517a63b0ca84718e1224dae069fb2357cd27bee00
17 frozen inputs230927B, manifest SHA256:
951ea084214f3d3431e4595e87b21e2045ad49d8db288e95bab43b235d9ff958
Parent reviewed the frozen runtime package and requested only test/freeze
receipt completion; no runtime input changed afterward. validation.json records
checks. No remote execution, registration, circuit result, commit or push here.

Parent subsequently notified registration/submission under the same recipe SHA,
managed hash c5e24bb1779f7a04a405799aa719a4f4b67047f7d4ac5cf7bd6cb9d563e2fea9.
All17 inputs remain immutable. This owner does not poll or duplicate submission;
await parent collection notice for paired result review. No result claimed yet.
