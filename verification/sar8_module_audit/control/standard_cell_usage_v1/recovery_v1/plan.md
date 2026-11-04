# Source-bound lossless streaming export recovery

Parent authorizes this recovery_v1/ subtree only. Baseline native simulation
sar8audit-ctrl-usage-baseline-ff-v1 completed19.513s/332996608B RSS/108066435B
output with PASS/zero errors. Original analysis failed18.519s at raw diagnostic
20MiB guard (misleading reused error text says30MiB); partial20970944B retained.
Do not change any original recipe/input/source derived or rerun the simulator.

Goal: stream selected diagnostic rows directly into lossless gzip and read them
likewise in separate analysis-only jobs. Preserve every original point, all348
stress pairs,73 selected baseline currents (75contrast), slew/KCL/state checks,
native source identity and strict thresholds. Keep20MiB compressed-wave guard,
32MiB collection and256MiB RSS. No relaxation, decimation or fake simulation.

Use unchanged frozen reducers/observers as source to create narrow independent
gzip writer/readers. Compare complete statistics and decoded byte stream on a
focused synthetic native fixture; separately exercise compressed guard and verify
that compressible decoded data may exceed it without truncation. Bind exact
completed baseline managed hash a4880aca396bc8ee6112e2069a7eb18579d54be2d04a1
f795f6708667f47b1a1. Contrast source already registered997693935954ebbce4f0d419
1e0a55ac1e1f391d7502bd5f5005c92c39876b3a, not submitted here; prepare its
separate binding allowing actual absent analysis after future native completion.

Parent owns registration/analyze/collect. Remote/OA ownership:none. All source
packages, raw/receipts, PDK, sibling/shared/Obsidian/10bit paths read-only. No
shared plan/log, commit/push or new simulation. Deliver recipes, proof and limits.

Checkpoint: direct gzip writer uses a bounded sink that refuses a compressed
write before crossing20MiB; all decoded bytes are hashed and independently
verified with exact row count. Existing statistic arithmetic unchanged; separate
storage/slew readers differ only in gzip.open path. Original configuration and
registered inputs remain byte-identical. Two focused tests pass for both source
configurations:348pairs/73or75currents/all native rows/sparse values/state/KCL/
slew/statistics exact, plus hard compressed-bound enforcement without decoded
truncation. Proposed source-only recipes prepared for baseline and contrast;
only parent will register/analyze. No source/native/failed-derived deletion.
