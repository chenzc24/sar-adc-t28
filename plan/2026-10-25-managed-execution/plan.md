# Unified simulation execution and resource admission

Status: complete; validated implementation, scoped local commit, no push.

User requests the complete next management phase before their review. Preserve
all historical data. Own scripts/management/, management/project.yaml,
management/README.md, management/STATUS.md and generated registry observations,
new management/recipes/ and managed run records, verification/managed_execution/,
netlist/workflow/, this plan, plan/log.md and management paragraph in AGENTS.md.
Extend exact shared legacy launcher ownership after identifying its callers.
Exact additional ownership: scripts/sar8_r4_staged/flow.py launch() only.
Its sar8_r4_idle caller inherits the guard. Retain legacy status/collect and
already-uploaded batch scripts unchanged; other historical launchers remain
unsupported for new submissions rather than claiming host-wide enforcement.
User Obsidian, independent10-bit/current-probe targets, old runs and PDK/OA are
read-only. Remote OA mutation ownership: none. Starting HEAD657f5b6; user and
independent target dirty paths remain protected.

Remote new ownership: verified uid596 directory under
/server_local_ssd/chenzc_intern25/sar-adc-t28 after ancestor/path/mount checks.
No old data move/delete, old process kill, sudo or system-wide changes. Runtime
limit enforcement only addresses new managed children with verified boot ID,
PID start time and process group. Retain partial outputs on failure.

Implement immutable input packages and unique IDs, idempotent submission,
fresh host+cgroup memory/swap/CPU/disk checks, exclusive heavy-work admission,
conflicting unmanaged-job detection, nice/ionice, virtual-memory and aggregate
RSS/time/output watchdogs. Connection loss is unknown until state readback;
never auto-duplicate. Native exit/PASS, analysis and electrical verdict separate.
Collection uses bounded hashed artifacts; full raw download is not default.

Verify SSD write/read with a new retained probe file. Record real permissions
and unknown administrator retention policy. Durable sources/recipes/metrics
remain local; SSD raw stays protected scratch until explicit cleanup review.

Validate focused containment/identity/gate/race/state/transfer/streaming tests,
a bounded native Spectre RC smoke through SSD submit/analyze/collect, gate
refusal and duplicate-submit without rerun. No ADC rerun. Record measured
resources/settings. Compile/scoped diff, update registry/docs/log and commit
owned files only; no push. Do not stop at merely declaring resource defaults.

## Implementation and validation

- Unified project.py commands implemented: storage, register, submit, run-status,
  gate, analyze, collect and bounded legacy-collect. Recipes and source hashes
  immutable per ID; registration/submission refuse differing or uncertain state.
  Atomic local snapshots and remote flock protect duplicate concurrent calls.
- Created only new uid596/mode0700 project subtree on server_local_ssd. Verified
  XFS and retained write/read probe; lsblk reports sdc and mapped volume ROTA0.
  Administrator backup/purge guarantees remain unknown and documented as scratch.
- Implemented host/cgroup headroom, swapping, quota/load, output/disk admission;
  serial heavy-work lock, queue with reasons, nice/ionice, AS and file hard limits,
  RSS/time/disk watchdogs. Child cleanup verifies boot/start/group identity and
  covers controller exceptions. This is not a host-wide sandbox or root cgroup.
- Two native RC workflow-only cases kept on SSD. First observed existing
  independent Spectre242909, waited, then ran. Final case race submitted twice:
  one worker, repeat returned same child identity. Native exit0/PASS, no warning;
  159 points to10ns, final output0.999878791493376V. Peak native RSS75.59MiB,
  analysis5.93MiB. +mt4 requested, native log explicitly disables threading for
  this tiny design. No ADC rerun or precision/speed claim.
- Streamed summary and two hash-checked collections agree (15561 bytes each).
  Gate-only 1TiB memory budget refused; not launched. Legacy rg4_strict200_ff_m40
  four small evidence files60862 bytes copied to a new local location read-only.
- 15 focused fixtures pass: separate gate risks, phase runtime budgets,
  containment, PID reuse/group safety, partial/different registration, corrupted
  transfer, sparse/GROUP1 PSF, atomic local snapshots and legacy inventory semantics.
  Native smoke revision retained in validation.json; later PID-group/exception
  hardening validated with fixtures and Python2 RPC loading, not another ADC run.
- Resolved csh multiline quoting in RPC and Python2 lsblk UTF8 decoding during
  verification. Retain failed transport diagnostics ignored locally. Windows
  concurrent rename test exposed transient access denial; bounded local-file
  retry fixes it, without retrying uncertain simulation submissions.
- Updated registry observations, docs and AGENTS. Kept all old raw, OA/PDK,
  current-probe work,10-bit files and user Obsidian dirty state untouched.
  No deletions, historical moves, old-process kills or WORK-library creation.

Evidence: verification/managed_execution/{storage,storage_block_devices,
validation,checks}.json; generated transport/raw receipts stay ignored under
output/managed_execution and the new remote SSD root. Cleanup remains a later
human-led task. Completed scoped checks and local commit only; no push.
