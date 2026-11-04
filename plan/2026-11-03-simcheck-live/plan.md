# Real Spectre log-inspector tests — 2026-11-03

Goal: user-authorized native Spectre fault-injection and short ADC runs, for
E:/spectre-log-inspector validation. No ADC design adoption or performance claim.
User explicitly authorized new simulations and deliberate test faults. No OA.

Dirty state: repository has extensive prior ADC/module/notes/management changes.
Existing execution.py/remote_agent.py/execution_policy.json are read-only
dependencies; reuse their current managed API without edits. Preserve all other
unrelated dirty files and logs. No commit/push for this test task.

Own: verification/simcheck_live/20261103/**, management/recipes/simcheck-live-*.yaml,
automatically generated management/runs/simcheck-live-*.yaml and output/managed_execution
records for those IDs; this plan and one appended plan/log entry. Inputs from
frozen A/B netlists and prior TB are copied, never edited in place. Remote owned
objects: exact new /server_local_ssd/chenzc_intern25/sar-adc-t28/runs/simcheck-live-*
run directories only. Original circuits, prior runs, PDK/shared libraries/OA,
Obsidian and 10-bit work remain read-only.

Managed register -> submit --queue -> run-status -> collect; all original logs
retained. Each synthetic job 1 thread, <=512MiB RSS, <=16MiB output, <=90s;
ADC short job 4 threads, <=1GiB RSS, <=64MiB output, <=600s. Deliberate output/
wall limits are smaller and explicitly identified. Account slot/memory/disk/CPU
gates unchanged; uncertain submissions are read back under the same ID.

Validate native status, logStatus and observed diagnostics per expected case.
No assertion that every attempted numerical failure must produce a particular
vendor code. Completion is distinct from electrical/ADC qualification. Curate
only sanitized small excerpts into the tool repository with provenance; no PDK
content or original license endpoints. Do not download full ADC raw waveforms.

User reply (2026-11-03): only one 1-thread small test may temporarily relax CPU
admission. Apply this to the already queued rc-normal ID only. Suspend the other
14 owned queue workers after checking identity, queued state, and absence of
held locks; no simulation child is stopped. Temporarily own remote policy.json
only for this exception: preserve exact bytes/hash, keep all other gates, allow
one managed workload/one thread and load ratio <=3. Restore original bytes in
finally before resuming queued workers; detect external policy edits rather
than overwrite them. Record this bounded exception under the rc-normal run.
No local policy or managed source edits, no new submission ID.
