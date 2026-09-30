# T28 GMAIN hold pull-down first-pass screen

## Goal and starting state

Replace only the ideal `SHOLD` VSS relay of the protected-bootstrap full-CDAC
fixture with a real T28 `nch_18_mac` pull-down. Determine whether a PDK MOS
device can turn MN11 off before BOOT reset, avoid the reference-handoff
reverse-current path, and preserve the ideal-clamp bottom-plate raw-error
benefit. `STRACK` remains ideal; this is a **partial transistor-level**
iteration, not a finished gate driver.

At start, branch `exp/bootstrap-protected-eval` has unrelated dirty files
under `review/`, `scripts/review/build.py`, and
`plan/2026-09-30-review-maintainability/`. Those are disjoint from this
target and are left untouched. Exact read-only OA export hashes and the
protected-bootstrap transform remain those recorded in
`docs/bootstrap_full_cdac_isolation.md`. EVAS lacks a transistor solver;
use Spectre 21.1 via `t28_io`.

## Ownership

- Local owned: this plan,
  `scripts/characterization/screen_bootstrap_t28_hold_pulldown.py`,
  `docs/bootstrap_t28_hold_pulldown.md`, bounded entries in
  `docs/design_log.md` and `plan/log.md`.
- Generated: ignored `output/bootstrap_t28_hold_pulldown/` exact decks,
  Spectre logs/PSF, and case JSON.
- Remote OA owned: none. OA, PDK, original exports, prior scripts and
  generated prior-result files are read-only.
- Shared read-only dependencies: prior exact-hash full-CDAC generator,
  protected-bootstrap transform, direct-SSH Spectre runner and PSF parser.

## Method and acceptance

1. Generate the +0.8-V ideal-clamp full-CDAC VSS-off control deck from the
   previous script. In a **copied deck only**, replace its one `SHOLD` relay
   statement inside the bootstrap subcircuit with `MN14 (GMAIN OFF_MAIN VSS
   VSS) nch_18_mac`, using the exact known MN7 1.8-V PDK geometry as a
   starting template. Sweep only `multi=4,16,64`; each subcircuit is then
   instantiated 24 times. Keep `STRACK` ideal, CDAC/clamp/reference/timing
   unchanged. Compare to the hashed prior ideal-SHOLD result.
2. Save representative B9 P/N GMAIN, bottom/top voltages, MN11 current,
   MN14 terminal current, and source-resistor current. Quantify acquisition,
   pre-reset GMAIN discharge, 270-ns raw error, B9 reference residual,
   input loading, and phase ordering. Inventory all printed CMI warnings
   and reconstruct MN14 terminal-voltage peaks; this is a diagnostic screen,
   not foundry SOA signoff.
3. Only if a candidate meets the 0.439-mV raw-error gate at +0.8 V and
   suppresses the prior 6.258-uA B9 leakage, expand to -0.8, -0.4, 0,
   and +0.4 V with that candidate. Keep the ideal-clamp limitation visible.
4. Validate source hashes and bounded deck diff, Spectre `result.ok`,
   finite/aligned PSF, Python compile, JSON parse, `git diff --check`, and
   owned-diff review. Commit locally as
   `test: screen T28 bootstrap hold pull-down`; no push without request.

## Outcome

Seven TT/0.9-V/27-C Spectre transients completed with zero errors:
`multi=4` at five static differential inputs and `multi=16/64` at
+0.8 V. The `multi=4` five-point bottom maximum raw error is
0.004223 mV, but the top-control maximum is 6.822 mV and endpoint
warnings are heavily suppressed (1,338 in each ±0.8-V run). The
representative GMAIN crossed below 0.1 V at least 0.846 ns before
BOOT reset. This validates a partial hold pull-down mechanism, not a
complete or SOA-qualified switch. No OA mutation. See
`docs/bootstrap_t28_hold_pulldown.md` for evidence and remaining blockers.
