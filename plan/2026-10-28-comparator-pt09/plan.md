# Comparator nominal-voltage PT diagnostic

User requests SS/FF at 0.9 V. Test combined M2/M4 multi=4 and 8 at
TT/27C, SS/-40C, SS/125C, FF/-40C, FF/125C. Preserve each source DUT,
input history, loads, clock timing and 200/500ps edges; change supply/clock
high to 0.9V, MOS corner and temperature only. Terminal limit stays 0.99V.
Original 0.81–0.99V specification remains; no baseline adoption.

Dirty state: extensive unrelated user/agent work on exp/cdac-flat8-device;
preserve it. Existing comparator scripts, sources and results read-only.
Owned: this plan; comparator_design/scripts/pt09_*.py;
comparator_design/testbenches/cmpdesign-pt09-*/;
comparator_design/recipes/cmpdesign-pt09-*.yaml;
comparator_design/results/cmpdesign-pt09-*/;
comparator_design/PT_09V.md, comparator_design/figures/pt09_*;
matching managed run records and output directories; append plan/log.md;
Obsidian_docs/Report/手搭ADC-过压图解.md (existing atlas clarification scope).
Remote OA owned: none. Remote managed SSD paths for these exact run IDs only.
PDK, libraries, OA, historical results and unrelated notes remain read-only.

Steps: freeze ten cases from cmpdesign-edge-b2i2-ff-hot-v1 and
cmpdesign-combo-a8-ff-hot-v1; assert exact allowed deltas and metadata;
use existing managed runner/analyzer, one case at a time within shared six-slot
policy. One thread, simulation RSS<=1024MiB, analysis<=256MiB, collection<=32MiB.
If occupied retain queue and original IDs; do not interrupt other workloads.
Validate native exit/log/400ns completeness, 32 decisions in each input mode,
all MOS terminal pairs and durations, reset, residual, kickback and power.
Report actual solver settings and any CMI alerts; no noise/mismatch/PEX signoff.
Review summary figure, scoped whitespace and input checks; record evidence.
Commit policy: no commit or push.

Status: preparing inputs.

User explicitly authorized one additional shared slot for this serial batch.
Expand ownership to the concurrency field only in AGENTS.md,
scripts/management/execution.py, management/execution_policy.json,
management/project.yaml; append management/README.md; managed storage refresh
verification/managed_execution/storage.json. Change 6->7 shared heavy slots,
retain all per-job and aggregate resource limits. Deploy through managed storage
initialization; existing queued worker rereads policy and keeps its run ID.

Progress: 10 input audits passed (DUT exact bytes, allowed deck deltas, fixed clock times/events, model sections, hashes). Seven-slot policy deployed through managed storage; original queued TT4 admitted on workload_slot=6, no duplicate submission. TT4/TT8 native+analysis collected and all diagnostic screens pass. Remaining FF/SS cases continue serially in existing runner. First TT4 legacy candidates metadata retained frozen; actual DUT/provenance correct, analyzer ignores field; remaining9 corrected before registration.

Five cases collected (TT4/8, FFcold4/8, FFhot4), all screens pass. SSH banner timeout during original FFhot8 submission stopped batch. Exact original-ID run-status confirmed registered/not_started, then resumed same ID plus four unregistered SS cases; no duplicates or changed inputs. Transport failure retained at output/managed_execution/transport/1793168901366137500.*.

2026-10-28 PT09 checkpoint:8/10 collected, all diagnostic screens pass (TT27,FF-40/125,SS-40, two sizes). SS cold worst4x/8x .957117981/.978890863V; decision540.115/670.800ps. NoCMI warnings in8logs; SFE1131 retained. SS hot4 queued: user_cgroup_headroom ~7.94GiB below8GiB aggregate admission threshold; slot6 is available, do not change gates. SShot8 not submitted; serial runner retained (local exec session8025), queue timeout600s. Summary chart visually reviewed, inputs/metrics/counts/resources and links checked; partial results written to PT_09V.md and Obsidian note. No adoption/OA/commit/push.
