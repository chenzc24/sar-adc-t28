# SAR8 saved schematic adoption of 100 ps restore and 50 ps gates

## Goal and ownership

Adopt the user's selected timing as R3, preserving R1/R2 history. Create
`SAR_ADC_T28/sar_adc8_join_r3/{schematic,symbol}` and
`SAR_ADC_T28/tb_sar_adc8_join_r3/schematic`, with exactly the R2 connectivity,
placement, native topology, dimensions and reference network. Change only the
16 ideal reference gate instances to explicit `restore_guard_s=100p` and
`edge_s=50p`. Existing ideal gate Verilog-A bytes/defaults stay unchanged.

If those parameters are absent from the shared `sar8j_aligned_refgate` base
CDF, expose them with the existing VA defaults (2n and 20p), preserving every
existing CDF parameter/default, symbol and VA bytes. This CDF metadata surface
is owned for that narrow addition only. No PDK CDF changes.

Local owned paths: this plan; `scripts/integration/join_r3*.py`;
`config/sar8_join_r3.yaml`; `verification/integration/{join_r3_results.json,
test_join_r3.py}`; `docs/sar8_join_r3.md`; `docs/figures/sar8_join_r3/`;
the active pointer in `docs/project_status.md`; `plan/log.md`.
Generated evidence: ignored `output/sar8_join_r3/`.

Dirty state at start: unrelated untracked `config/cdac10_dualrail.yaml`,
three `models/veriloga/cdac10_dualrail_*.va`, and
`{plan/2026-10-20-cdac10-dualrail,scripts/cdac10_dualrail,
verification/cdac10_dualrail}/`. They do not overlap or alter dependencies;
preserve and exclude them. Branch `exp/cdac-flat8-device`, parent 9f93664.

Read-only: all other local sources and remote cells, foundry libraries/models,
R0/R1/R2 source/result manifests, prior edge-slew experiment. No push.

## Implementation and validation

1. Read bridge skills and relevant existing automation; verify healthy
   `t28_io` bridge, CIW, library path/technology, windows, target ownership.
2. Read back frozen native/R1/R2 surfaces and timing model/CDF. Create R3
   using the exact R2 construction with only the two explicit gate overrides.
   Save/check and demand zero markers. Compare connectivity, component params
   and positions with R2; preserve historical schematic fingerprints.
3. Export saved R3 OA, retaining raw output. Audit all native subcircuits
   unchanged and R3 top electrically identical (name normalized) to the
   tested 50 ps candidate. Never patch the exported DUT for confirmation.
4. Build four stimulus/analysis-only wrappers: -0.8/-0.8, +0.8/+0.8,
   -0.8/+0.8, +0.8/-0.8 V. Native APS TT/0.9 V/27 C, 200 ns, maxstep10 ps,
   full solver rate, no noise/mismatch; same input50 ohm/side and
   reference50 ohm +4 pF/rail. Two concurrent jobs maximum.
5. Require result.ok, complete finite traces, two frames of eight valid
   compare/write/update events, expected codes14/241, unchanged mapping,
   sample/precompare errors <1.7578125 mV, scanned reference/comparator
   six terminal-pair voltages <=0.99 V, no CMI/LTE or gate overlap.
   Compare fresh metrics/timing with the immutable prior 50 ps candidate;
   retain and explain simulator warnings/notices. This is bounded nominal
   confirmation, not PVT/noise/mismatch/full-code/FFT/layout/lifetime signoff
   or a real transistor timing driver implementation.
6. Final saved-state readback/export audit; open R3 without closing user
   windows. Update current baseline/status/report only after passing.
   Focused deterministic tests, diff review/check, factual maintenance log,
   scoped local commit `feat: adopt SAR8 R3 reference restore timing in OA`.

## State

Completed. Existing `t28_io` tunnel restored; CIW/Spectre healthy, no
Virtuoso restart. R3 top/TB/symbol saved; shared gate CDF exposed with original
defaults, VA bytes unchanged. Top112/TB26 instances, zero markers; every
non-timing parameter, connection and placement matches R2. Net connections
are compared as sorted lists because OA enumeration order differs; no
connection is excluded. Primary and independent repeat OA exports both
match the tested50ps candidate and unchanged native subcircuits. Historical
36 schematic surface checks pass before and after creation and after all
simulations. R2's16 gates also read back as original2ns/20ps. All four fresh
result.ok;8frames/64compares+writes+updates, codes14/14,241/241,14/241,241/14.
All bounded gates pass, same critical error/stress numbers as the old50ps
candidate (all compared deltas zero). Worst reference.944611V/comparator
.950686V, held error.200474mV/max compare.808021mV; noCMI/LTE,7 existing
config warnings each. InitialDC notices retained (p_to_n6, others5). Opened
R3 in Virtuoso; current status/config/report updated. Three focused tests and
Python compile pass; overlay visually reviewed, no clipping. Final diff-check
and review pass. Delivered in a local scoped commit; no push requested.
