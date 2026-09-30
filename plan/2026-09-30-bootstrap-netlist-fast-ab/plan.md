# Bootstrap netlist-level fast A/B screening

## Goal and starting state

Rapidly test whether removing the high-input-to-reset-`BBOT` body junction
path, advancing main-switch turn-off, or combining both improves the
full-control differential bootstrap's hold current and raw held error.
These are **netlist experiments**, not OA schematic updates or approved
device topologies.

Start branch `exp/bootstrap-protected-eval` has a clean tracked index/tree.
Untracked `plan/2026-09-30-design-review-workbench/`, `review/`, and
`scripts/review/` belong to an unrelated workbench; leave them untouched.
Use only the exact existing OA-exported source whose SHA-256 is
`f466793e8655f2d81bdb7ce98d1041f00cdd90a374be3341750d2cb22a9bdd4d`.

## Ownership and boundaries

- Local owned: this plan, `scripts/characterization/screen_bootstrap_netlist_ab.py`,
  `docs/bootstrap_netlist_fast_ab.md`, and bounded entries in
  `docs/design_log.md` and `plan/log.md`.
- Generated: ignored `output/bootstrap_netlist_fast_ab/` (variant decks,
  remote Spectre PSF/log copies, and summary).
- Remote OA owned: none. All OA cellviews and PDK/model files read-only.
- Shared dependencies: exact full-control export, the bridge SSH Spectre
  runner, and PSF parser. Never edit the exported source.

## Matrix and validation

1. Baseline exact-export control with analysis-only saves.
2. `body_vss_core`: change only MN9 B from VIN to VSS. This diagnoses the
   junction hypothesis; core-oxide stress may fail and is not acceptable.
3. `body_vss_18`: use the known PDK `nch_18_mac` geometry already present
   in this OA cell for MN9, with B=VSS. This is a topology/device-class
   candidate, not a matched-width one-factor isolation test.
4. `early_phib`: leave devices alone, shorten the PHIB low pulse from 41 ns
   to 40.2 ns, moving its rising edge from 251.0 to 250.2 ns while leaving
   the initial edge unchanged.
5. `body_vss_18_early`: combine 3 and 4 to expose interaction.
6. `body_vss_18_source_off_bound`: on variant 3, remove only the existing
   MN7/MN10 G-to-ground discharge path and insert an **ideal PHIB-controlled
   relay** from G to VIN. This tests source-relative off/gate-charge steering
   as a theoretical upper bound. The relay is not a T28 transistor topology
   and any favorable result cannot be called a realizable design pass.
7. `split_main_gate_bound` and `split_main_gate_bound_early`: retain variant
   3's real MN9 reset/body fix and original G-to-ground clamp, but separate
   main MN11 gate onto `GMAIN`. Use ideal relays to couple `GMAIN` to G in
   sample and VIN in hold. The early version moves PHIB rising to 250.2 ns.
   These bound a *separate-gate* topology, not transistor implementation;
   the added ideal switches' charge injection and high-voltage stress are
   absent. This extension follows the shared-gate source-off variant's
   observed reverse MN9 channel conduction.

Run the same 0.9-V/27-C model sections, 50-ohm source and 219.5-fF hold
load, +0.8-V differential stimulus, and 285-ns transient on each. Save
input/output, internal boost nodes, RIN/MN9/MN11 currents. Compare held
raw error, input current, non-overlap/discharge edge error, gate voltage,
and peak terminal stress. If a variant is promising, repeat at additional
input levels before claiming a design improvement. Do not tune a dummy
capacitor to a single input point; net differential charge cancellation
requires a separate full-input experiment.

Pass criteria for the screening workflow: exact source hash and bounded
variant edits, Spectre `result.ok`, aligned finite PSF signals, expected
MOS pin order/current signs, output-node KCL and source-resistor balance,
Python compile, JSON parse, `git diff --check`, and owned-diff review.
Candidates pass the *circuit* only if held raw error <0.439 mV, unintended
hold input current is sharply reduced, acquisition is not degraded, and
no new CMI model warnings/terminal stress arises. A nominal pass is not
PVT/lifetime/layout signoff.

Commit this bounded target locally as `test: screen bootstrap netlist A/B`.
No push without a user request.

## Outcome

Eight independent TT transients completed with zero Spectre errors and
validated source-current/output-KCL relations. The body-only switch change
confirms leakage removal but creates core-gate stress; a known 1.8-V device
class removes printed CMI warnings but still misses raw hold accuracy. A
shared source-relative gate gives a reverse MN9 channel path and worse
leakage. Splitting the main switch gate in an ideal relay bound reaches
-2.482 mV at best, 5.65x the 0.439-mV gate, so no variant is promoted.
Full numerical evidence and remaining implementation limits are in
`docs/bootstrap_netlist_fast_ab.md` and ignored run artifacts under
`output/bootstrap_netlist_fast_ab/`. The independent design-review
workbench was committed by another task while this target ran; its files
and commit were not modified or staged by this target.
