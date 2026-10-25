# Physical stress repair and regression

Status: repair incomplete; first managed candidate reviewed and not adopted.
Awaiting user supply-contract choice before broader architecture changes.

## Goal and boundaries

User authorizes fixing the known transistor-level faults, not just measuring them.
Close reference-switch gate overshoot, conversion/idle bottom undershoot, then
remaining driver/comparator/control stress and acquisition faults. Preserve the
external sample window and closing edge, finite 50-ohm reference/input networks,
physical internal timing, 8-bit flat architecture and original evidence.
No ideal clamps/keepers, warning suppression, relaxed model limits or PVT relabeling
may be used to claim a physical fix. Separate a useful improvement from closure.

Dirty state: user Obsidian reorganizations and independent cdac10_dualrail files
are unrelated and protected. Start HEAD de70f82, branch exp/cdac-flat8-device;
management commits b6da655/657f5b6 remain intact.

## Ownership

- Local: this plan; scripts/sar8_physical_repair/; netlist/experiments/sar8_physical_repair/;
  verification/sar8_physical_repair/; docs/sar8_physical_repair.md and matching figures;
  output/sar8_physical_repair/; management/recipes/sar8fix-*;
  management/runs/sar8fix-*; task-only appended plan/log.md.
- Managed execution may create its standard ignored output/managed_execution receipts.
- Remote OA: none. Netlist candidates are NOT synchronized schematics.
- Remote new runs: only managed SSD runs/sar8fix-*; historical runs read-only.
- Read-only: PDK, existing design sources, R3/R4, current L90/Mmain2 baseline,
  previous diagnostic and stress runs, unrelated user files, management execution code.

## Sequence

1. Audit exact original deck, PDK device parameters and native CMI limits. The
   existing 0.99/1.98 V limits remain screening criteria, not lifetime certification.
2. Build native PDK-only single-variable candidates. First evaluate passive gate
   charge buffering (MOM gate capacitance with reduced gate resistance), retaining
   slew rather than blindly accelerating all gates. Reuse verified geometry.
   Reject if new bottom/driver stress or settling failures outweigh improvements.
3. Use measured results to select subsequent bounded topology/sizing corrections;
   record each delta before running. Preserve original candidate inputs forever.
4. Full MOS-pair monitoring, independent code/timing checks and all-bottom settling
   on the 200 ns FF cold screen; then FF hot, five PVT risk points, steady-state
   acquisition, static and 1024-point dynamic regression on a viable candidate.
5. If strict stress closure requires a supply-domain/device-class architecture
   decision beyond the existing design contract, report the evidence and ask before
   silently changing voltage/reference range or adding ideal supply rails.

## Validation and resource policy

- Every new simulation and heavy remote analysis uses managed register/submit/
  run-status/analyze/collect, single job, four threads, frozen SHA256 inputs.
- Initial budget: simulation RSS 1024 MiB, virtual 8192 MiB, 3600 s; analysis
  RSS 256 MiB, virtual 1024 MiB, 1800 s; output 32 GiB for full MOS voltage
  coverage; collection <=32 MiB. SSD admission reported 557 GiB free.
- Stream every native point for device peaks; export compact min/max-preserving
  plotting data, not full raw. Never load multi-GB ASCII PSF in memory.
- Exact case-sensitive voltage/current saves; validate TRACE, END, stop time,
  native PASS/exit, effective CX conservative tolerances and all device mappings.
- Guardrails: same external sources and SEQ_SAMPLE edges (report actual deltas),
  codes 243/12, 8/8/8/16 events each frame, all 14 settling windows within
  +/-1.7578125 mV by next comparison, reset completed before acquisition.
- Final closure additionally requires no MOS terminal pair above its unchanged
  screening limit, PVT/performance regressions, and no hidden warning suppression.
  Two static frames alone cannot qualify the ADC.
- Inspect generated figures; targeted tests, git diff --check, scoped review.

## Commit policy and artifacts

Commit only task-owned reproducible inputs, scripts, reviewed metrics and reports;
no raw/PDK/OA data, no push. Keep plan active while any required closure remains.
Use factual checkpoint commits if experiments demonstrate improvement but not closure.

## Execution checkpoint

- Registered and submitted sar8fix-c1r4-ffcold via managed entry, original 1833 MOS
  unchanged, 320 gate resistors paralleled x4, 1020 existing-geometry MOM units
  added to 32 gate outputs (nominal total 4.08408 pF). Compare also to historical
  Rgate/4 run to isolate the added capacitance effect.
- Native save summary: 939 voltage +24 current traces, no invalid-save warnings.
  10998 MOS terminal-pair peaks will be measured at every native sample. Compact
  plot export has minimum 10 ps spacing, explicitly not exact timing signoff.
- An early live collect hit checksum mismatch because mutable logs changed
  during collection. Simulation is unaffected; wait for stable completion, then
  retry collection only. No resubmission.

## Reviewed result

Managed simulation and analysis both complete/exit0; no outstanding worker.
318574 native points, 10998 MOS pairs; collected 14 files /20110753 bytes with
all hashes verified. An early START log snapshot was preserved by the collector;
analysis now resolves receipt hashes to versioned logs instead of reading stale
basename snapshots. No native rerun was needed.

GNN4 peak 1.050940 ->0.999016 V; BP7 minimum -56.939 ->-40.632 mV;
reference worst pair 1.050940 ->1.030632 V, now XSP7.MP_HIGH |Vbd|.
Reference driver/comparator/digital remain 1.056952/1.043639/1.078642 V.
Codes243/12 and counts pass; compact-export settling estimates14/14, max2.293ns.
First-frame preclose acquisition error remains -1.978mV. Not repaired, not
promoted, no new supply rails or relaxed limits. Full PVT/static/FFT not started
on this known-failing candidate.

User was asked whether 0.81-0.99V must remain fixed or a new supply-domain plan
is permitted. No response yet. No claim that all in-scope circuit alternatives
are exhausted; wider supply/topology choice is intentionally not made silently.
Checkpoint preserves failed/improved evidence while overall target stays open.
