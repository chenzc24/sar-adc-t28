# RC1/HD interface options — 2026-10-27

Owner: reference/CDAC session. Parent approved D1P25 comparison; stop drive
sweeps. Write only this interface_options/ subtree. Shared plans/logs,
management, frozen packages/results, other modules, user Obsidian and 10-bit
work are read-only. No OA ownership, remote queries/simulation, commit/push or
design adoption. Existing branch exp/cdac-flat8-device is ahead30; dirty shared
management, plan/log and Obsidian state does not overlap this subtree.

Goal: compare at most two concrete RC1/HD interface changes against actual
connections and phase currents. Cover positive injection, negative recovery,
and NAND-to-HD backflow together; expose any stress moved to core devices.
Preserve architecture, supply .81–.99V, external clocks/sample window/close edge
and real loads. Native digital library stays intact. Analog RC interfaces may
use previously evidenced PDK IO devices and passive elements; no ideal clamp
as an implementation.

Steps: read frozen topology and actual currents; calculate bounded charge/RC
and DC-level tradeoffs, with predictions separated from physical results;
compare two options; prepare at most one local controlled candidate/fixture
only if the complete interface boundary can be justified. State exact changed
leaves, not a misleading single-transistor claim for a composite topology.
If neither can meet the controlled-experiment scope, report the concrete
physical incompatibility rather than producing a nominally passing fiction.

Validation: exact source/input hashes and topology/model/node readback; all new
MOS actual six-terminal-pair screens and incident current measurements; retained
native load and external fixture equality; local syntax/config/measurement
checks proportionate to any generated candidate. No speculative PVT pass.
Artifact: concise options report, quantitative JSON evidence, and at most one
candidate package for parent-owned managed registration. No remote execution
or new model/library contents; use verified local device records only.

## Completed checkpoint

Parent reviewed the draft and explicitly accepted one composite interface
topology comparison, not single-device attribution. Parent required original
full-swing contracts retained, actual loaded HD levels/downstream logic/static
VDD currents exposed, and unknown VIH/VIL not replaced by halfVDD criteria.

Compared only two options. Rejected core-preserving passive filtering as a
complete fix because clear Vds, receiver output and downstream gate remain
exposed with no supply-to-screen headroom. Prepared option B only: IO clear and
RC1 receiver plus symmetric passive input guard; native digital logic intact.
192 other leaves and the entire exterior of HD are exact; external source,
solver, load, sample window and close edge identical. New scope is one analog
interface master, with coordinated leaf changes explicitly enumerated.

Candidate sar8audit-ref-hd-io-guard-ff-v1: final proposal
563a395e239d663a2299ba5a31189cf3039ebf2a548bdfed21d28f2a80926685,
12inputs510820B,120V666I/40KCL/738actualMOSpairs/463nativecolumns.
No equivalence-merging or changed screen limits. Original zero-rail HD reset
and both original static full-swing targets retained separately; no target
substitution. Added actual RC1/HD_RAW/HD incident-current snapshots and clipped
charge budgets, static downstream NAND/H/L levels, exact VDD ports/full energy
and per-window current/power/resistor dissipation. VIH/VIL remains unknown.

Two focused tests passed in final0.610s: frozen-source/exterior equality and
actual node/body/model/screen mapping, plus complete synthetic native-parser
execution proving old full-swing/reset failures remain visible and current/
power fields survive. Synthetic fixtures are only contract checks, not circuit
simulation or evidence of electrical correctness. No native Spectre elaboration
or remote execution occurred.

Evidence verifies original collected result hashes/receipts and records only
conditional algebra. Guard's approximate ideal-source tau97ps and bias37.54uW
at0.99V exclude finite IO Ron, NAND loading/current and PVT. Prior IO extremes
are counterexamples, not bounds on this candidate. Full-swing HD interface
contract intentionally not fulfilled by the divider; possible functional
compatibility and static-current cost must be decided from the managed FF test.
No other point/matrix prepared. Main session owns register/submit/analyze/collect
and adoption decisions. No shared-plan/log, frozen input, OA/PDK/library edit,
remote query, commit or push.
