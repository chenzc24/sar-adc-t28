# SAR8 integration baseline freeze preparation

## Request and scope

User selects (1) correct the polarity mapping, (2) unify sampling/reference
initialization and (3) ideal gate voltages with 3x P/N reference switches.
First inventory and prepare one bounded integration candidate. Record a single
module/source/interface contract and pinned evidence; do not construct a new
OA top or claim a joined simulation has run. The integration adapter is a
declared next implementation step, not silently present in old cells.

## Ownership

Initial HEAD da6fc54, branch exp/cdac-flat8-device. Untracked cdac10_dualrail
config/models/scripts/tests/plan are unrelated and preserved. No agents.

Owned local: this plan; config/sar8_join_r0.yaml; docs/sar8_join_r0.md;
scripts/integration/freeze_r0.py; verification/integration/test_join_r0.py;
verification/integration/join_r0_sources.json; a bounded navigation addition to
docs/project_status.md and bounded maintenance-log entry. Raw audit and source
copies are ignored under output/sar8_join_r0/. No raw OA, PDK model text,
license data or complete native exports committed.

Remote OA owned: none. Read-only native simple controller hierarchy,
sar_strongarm_t28, sar_bootstrap_canvas_flat_8b, existing MOM/dual-rail source
array and leaves in SAR_ADC_T28. All PDK, historical and parallel work is
read-only. No save, rebuild, category, window, netlist-export or simulation.

## Selected assembly

Eight-bit/10-MSps/TT/27C/0.9-V nominal integration candidate; unchanged native
sample switch, MOM unit/array and StrongARM, simple_v2 native async control,
3x two-pass-MOS ideal-gate reference deck. No real reference driver optimization,
PVT/mismatch/power/layout closure, new EOC/status logic or spec replacement.

Mapping and sample initialization must be explicit and consistent with the
physical capacitor charge equation, preserving new controller architecture.
Define sample-high restore-to-midpoint before hold; keep current reference
state through Bootstrap turn-on before restore, retain the existing 2-ns
nominal relative restore guard and 100-ps break-before-make, prevent sample-fall
from replaying raw all-off selects. Timing numbers remain integration seeds.

## Validation

- Verify live bridge/library/tech and read relevant existing cells only.
- Match selected source-deck hashes and 3x result provenance, native exported
  controller/StrongARM body identity and fresh schematic fingerprints.
- Check every code's complementary P/N mapping/ideal charge relation and
  sample/hold state contract offline. No arithmetic result is a new Spectre run.
- Preserve native clock and digital state logic, ideal-gate scope, external
  R/C reference/source boundaries and read-window assumptions explicitly.
- Parse YAML/JSON, focused checks, Python compilation, linked artifacts and
  git diff checks. Capture chosen revisions and what remains unimplemented.

Scoped local commit per AGENTS.md; no push. Completion means prepared module
selection/contracts, not implemented or qualified full ADC.

## Outcome

Prepared SAR8_JOIN_R0_3X_IDEAL_GATE. Fresh read-only capture matches prior
topology, geometry and ports for all21 selected native control cells plus
Bootstrap/StrongARM.15 source-file fingerprints include canonical3x source,
all6 accepted existing3x cases and simple_v2 native source. No OA mutation.

Configured exact cross-bank active-high request mapping and separate PMOS/NMOS
gate polarity. Sampling contract restores physical midpoint after2ns inside
track and retains it through sample-fall/raw-init gaps; no native EOC/FSM or
ideal Vin-based conversion.100ps shared SAMPLE preserves the analog source
edge; pulse width39.9ns gives40ns between midpoints. This differs from old
20ps native-controller fixtures and explicitly requires joint validation.

Four focused contract checks pass, including all256 mapping/charge/code-center
cases, gate-off/forbidden-overlap and sample interval/midpoint agreement.
Source pin verification passes. Documentation states adapter/top unimplemented
and no joint run; no existing control/sampling/source spec was rewritten.
