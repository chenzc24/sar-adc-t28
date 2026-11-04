# A/B TT short characterization

User authorizes paired native TT short tests, low/mid/high codes and startup,
with focus on aperture, asynchronous handshake and settling. Stress warnings
are retained but excluded from functional verdict. No circuit modifications.

Owned: scripts/sar8_ab_short/, verification/sar8_ab_short/,
output/sar8_ab_short/, management/recipes/sar8ab-*.yaml,
management/runs/sar8ab-*.yaml, corresponding managed local/remote run outputs,
this plan, plan/log.md append only. OA objects:none; no commit/push/adoption.
Both frozen netlist directories, standard library/PDK, all historical results,
shared management tools/policies and unrelated dirty Obsidian/manualADC/10bit/
comparator/module tasks remain read-only. Prior frozen TT full-code flow remains
in progress; use managed admission, at most2heavy tasks total, no duplication.

A SHA41d5444c4fcc3f26b097cca609474804afde2e61616c424c8a0cb8a5b2f298c4.
B SHAf31b66c8fb35003bf7e8ad1a23d9c230b39f1f9651ccc469953e5e52ecf493ea.
Same TT0.9V27C, input/reference0..0.9V,10MS/s, source/load and external clocks.
10frames: center codes0,0,12,127,128,243,255,255,0,128. Frame0 startup is
separate; repeated endpoints and large transitions expose history dependence.
Use same native library include on both benches for equal model elaboration;
library cells are instantiated only by B. Verify installed include/model hashes.

Save all native time points for selected interfaces; no strobe interpolation of
fast handshakes. Reuse unchanged nonloading VA event observer as independent
cross-check. Stream PSF within256MiB; retained plot samples are decimated but
metrics use native points. Measure external/SAMPLE_INT/SEQ_SAMPLE falling edges,
bootstrap G-Vin0.45V downward crossings (diagnostic, not physical threshold),
8compare/write/update and16capture events, order,90/98ns code stability, input
acquisition error just before actual sequenced close and held value thereafter.
CDAC top-plate tail settling uses measured pre-next-comparison level and0.25LSB
band; explicitly diagnostic, not ideal DAC accuracy or transistor turnoff proof.
Report aperture shifts rather than force time alignment. No invented aperture
shift specification; functionality compared to expected center codes, timing
contract and original10MS/s budget. Startup failures do not hide steady failures.

Native zero-error completion plus parser/observer consistency are required before
claiming results. Request sameCX4threads/preset_override/reltol1e-6/maxstep10ps.
Sim<=1GiB/output2GiB/wall12h; analysis<=256MiB; collection<=32MiB. Serial A/B
finite runner, fail/uncertain transport recorded with no automatic retries.
Deliver result JSON, A/B timeline/settling figures and readable report under
verification/sar8_ab_short/. Review images after actual completion.

## Checkpoint
Both recipes registered. A hash496fc6b5f6be1a4ff4be87c6776b243158a336f27a0a399adba5cdde808cfcf5;
B hash1a06cfca0f92ff2fd3a0fcb050b4ba64480fb9638d1d11f897f58edb35c4b947.
A submitted, queued with user_cgroup_headroom; B registered but not submitted
until A completes simulation/analysis/collection. Finite local flowPID49752;
read output/sar8_ab_short/flow_status.json before any continuation. Do not
duplicate flow or submit under another ID. Existing original low-code run stays
running; no process kills, cache release, memory-policy relaxation or timer change.
Native library and two PDK hashes match historical evidence by fresh read-only
server checksum. Identical A/B deck/stimulus, all input hashes and Python AST
checked; synthetic correct and misordered handshake cases correctly separated.
No measured A/B verdict or reviewed plots yet. Native result/review pending.


Memory-cleanup update: user authorized completed-run cache release.411files/29.546GiB cache released with data retained; accountheadroom30.925GiB. ExistingAqueuedworker admittedslot1/PID180871 andrunning. Bserialfollow-on, no duplicates/resourcepolicy changes.

2026-10-27 partial recovery: native A log has frames0–6; expected/actual
0/2,0/0,12/12,127/127,128/128,243/243,255/255. A running, B not_started;
existing finite runner PID18748 remains responsible for serial continuation.
Saved bounded read-only log/status receipt partial_20261027.json. No incomplete
PSF analysis launched. SAMPLE_INT/count observations only; actual sequenced
close/order/settling and A/B verdict pending. Effective tran reltol1e-7 differs
from global1e-6; preserve actual settings in final comparison. No new submission.
