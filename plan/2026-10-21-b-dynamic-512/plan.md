# B 1x coherent 512-point dynamic acceptance

## Authorization and ownership

User approved one native B/1x run: 4warmup+512observed frames,10MS/s,
near4.5MHz,-1dBFS. Keep all DUT topology/W/L/CDAC/reference network, ideal
clock/event models and solver precision unchanged. No PVT/mismatch/noise,
static sweep, width sweep, automatic retry, circuit repair, OA write or push.
Analyze the whole capture together; monitor actual progress and interrupt only
for clear failure/stress/invalid conversion, not expected fixed sampling lag.

Starting HEAD372f182, exp/cdac-flat8-device, index empty. Existing Obsidian
notes/moves/images and untracked cdac10_dualrail work are unrelated and must
remain untouched. Read-only dependencies: old B/short/W results and sources,
all PDK/shared libraries, bridge and ADCToolbox repositories. Remote OA owned:
none. Native scratch owned only unique exact run root/PID from this launch.

Owned local paths: this plan; config/b_dynamic_512.yaml;
scripts/integration/b_dynamic_512.py, b_dynamic_512_analyze.py and
b_dynamic_512_reduce.py; output/b_dynamic_512/ generated files;
verification/integration/b_dynamic_512_results.json; docs/b_dynamic_512.md;
docs/figures/b_dynamic_512/; narrow docs/project_status.md and plan/log.md.
One thread heartbeat may be created/updated for this exact approved run, with
quiet unchanged-state checks, meaningful-change/failure/completion notices.
No other automation or task is changed. Local focused commits only.

## Frozen bench

Use current native SAR_ADC_T28/sar_adc8_join_r3 B top and its existing TB.
T28TT,.9V,27C, main1um/L150nm, native StrongARM/SAR/CDAC/3x reference MOS,
50ohm input/reference resistances and4pF each reference rail. B restore100ps,
50ps reference edges/deadtime100ps, SAMPLE unchanged. APS4,+lqtimeout60,
conservative,maxstep10ps,gear2only, requestedreltol1e-5/effective1e-6,
vabstol10nV/iabstol100fA, gmin1pS unchanged. No strobeonly or model replacement.

N512, coherentbin231 (coprime), actualfin4511718.75Hz, Fs10MHz, differential
peak .9*10**(-1/20), CM.45V, original source phases -72/+108deg.516frames,
actual/declaredstop51600ns; retain original passive stop observer and all old
passive monitor/probe VA byte-identical. Only input frequency/amplitude and
stop observer parameter change. All native subckt blocks and clock/solver
statements must match immutable B; old artifacts never overwritten.

## Implementation and gates

1. Read skill/API instructions. Check healthy exact bridge/CIW/library/tech,
   windows, current top/TB/36dependencies/currentBVA hashes. Read native process
   list and existing flow before launch, no duplicate. Record disk/CPU/local
   memory/storage budgets first: prior136-signalPSF scales to~130GiB; localE
   currently~65GiB free. Use lossless compression/streamed per-frame reduction
   if remote scratch can support full-save raw, rather than whole-file RAM or
   local uncompressed storage. If resources cannot support safe full-save,
   freeze a smaller explicitly documented save-only surface before launch;
   never silently reduce DUT, solver precision, sample grid or claimed coverage.
2. Freeze config/deck/include hashes and analysis schema before native launch.
   One job only, timeout adequate for hour-scale native compute; hidden local
   coordinator, exclusive launch guard, exact native PID/log binding. No rerun.
3. Monitor real R3MEAS/BSINE516frames and bound PID/log. Stop exact owned
   Spectre only for fatal/convergence failure, CMI stress or confirmed invalid
   count/rail/timing/gross code event. Expected ~1.78ns fixed aperture delay and
   raw sine held-error are not stop criteria. Preserve failure/raw/log data.
   LTE precision notices require notification and validity review, no hidden
   parameter change. Check disk headroom; stop safely if data cannot be retained.
4. Preserve native result.ok classification. Parse full continuous data in
   bounded chunks, not one multi-GB list. Verify parser equivalence on existing
   native data and exact finite/monotonic/end/sample records. Retain original
   compressed PSF bytes and all native logs, with hashes and parser provenance.
5. After all516 frames: 8compare/write/update, MSB order, last update<60ns,
   stable90/98ns code/logic rails; report reference restore/event handling,
   selected analog terminal stress and native warnings, including initialDC
   Gmin/pivot notices. Keep core.99V vs IO1.98V engineering screens distinct.
6. Analyze exactly observed frames4..515 final codes, uniformly indexed by
   actual sample times (read latency separate). Coherent rectangular FFT with
   correct one-sided DC/Nyquist weights: SNDR/ENOB/SFDR and harmonic accounting;
   cross-check SNDR/ENOB with local ADCToolbox. Fit DC/gain/fixed delay separately;
   do not remove harmonics or re-time individual samples to improve SNDR.
   Report deterministic/no-transient-noise scope and any endpoint convention.
   SNDR>=43.9dB/ENOB>=7 per existing provisional project conventions, no claim
   of full-code DNL/INL/noise/PVT qualification.
7. Signed supply/reference/idealdriver/input source energy separated, include
   startup/warmup/observed and acquisition/conversion windows. Real drivers/
   reference-buffer overhead still missing, so do not claim physicaltotal<=1mW.
8. Whole-batch figures show ideal baselines, sample/read alignment, spectrum
   and selected frame details. Visually inspect; curate JSON/report/figures,
   update factual status/log, focused compile/math/parser/hash/diff checks,
   scoped local result commit only, no push. Mark flow complete then pause
   only this run's heartbeat; no archive and no further native experiments.

## Status

Running native. Preparation verified current B top/TB/36dependencies and
current VA byte hash match. Bridge0.8/t28_io/exactllm_IO CIW and Spectre21.1
healthy. No pre-existing native bridge jobs. Remote scratch has~409GiBfree,
localE~65GiBfree. Full136signal save is selected; old raw scales to~130GiB,
gzip1 sample ratio.2591 estimates~33.6GiB local archive. Remote raw+compressed
data remain until local gzip and complete decompressed SHA checks succeed.
After final curation, only this exact scratch root may be removed, keeping
verified full local gzip/log/receipts; no broad cleanup or other runs touched.

All native/clock/options/tran statements compare unchanged; sources fin and
amplitude plus passive stop parameter are the only bench electrical changes.
All5VA files copied byte-identical, no VA authoring or DUT behavioral rewrite.
Parser/currentPROP and arbitrary frame-boundary carryover tests pass, including
native frames0/4/8/15 power/held/CDAC cross-check against completed A16. Native
short-parser2048point equivalence passes. Actual gzip1.5/SCP/gzip/SHA fixture
roundtrip passes (small temporary data only, no extra simulation). FFT512
cross-check with local ADCToolbox, analytic DC/gain/delay/H2 alias and Nyquist
weight tests pass. Compile and frozen config/hash checks pass. One exclusive
native launch will follow a scoped preparation commit; no automatic rerun.

Preparation committed7875a3a; exactly one launch at2026-10-21 17:32:12 local.
Windows hidden launcher48804, actual coordinator62600 (launch.json), native
Spectre4639 (csh4280), exactscratchcf76d807. Live native startup verifiedAPS4,
all effective solver parameters equal B,136real finite traces match save list.
First2/516 completed frames have8compares/stablevalid output, noCMI/LTE or
grossfixed-delay code alarm. This is progress, not final performance evidence.
Small startup-query helper initially importedNumPy in the bridge-only venv;
fixed only that generated read-only helper to parse the known log format;
native job/deck/source/parameters unchanged and never restarted.

Reused only heartbeat id=b, renamed toB1x512monitor, ACTIVE readback confirms
15minute schedule on this thread; local coordinator also checks every120s.
Normal state/progress remains silent, only clear failure/action/completion
notifies. Keep desktop awake/networked for the local coordinator/SSH/result
collection. After whole batch, report actual performance including failures,
then pause b only. No other automation, oldR3 or external task changed.

After launch, offline reducer boundary review found that an intermediate
1fs-tolerance flush could omit a last point just before stop. Corrected only
the new local reducer to require reaching a boundary until EOF (roundoff
tolerance only at EOF), with close-boundary/roundoff synthetic regressions.
Native job, deck, raw data, solver and launch receipt unchanged; no data has
yet been consumed by the reducer. Preserve launch's original analysis hashes;
final reduced.json records the actually used reducer SHA. No native rerun.

At7/516frames native reported oneSPECTRE16780 at566.964ns,
XDUT.XCTRL.XBPP.XB0.X005.N. Counts/stability valid, noCMI or grosscode alarm.
Single LTE is retained and makes numerical-clean qualification unavailable;
not an automatic restart or a raw-held-error failure. Existing fixed policy
interrupts on cumulative>=3LTE or other clear errors. User informed once;
later monitors should not repeat an unchanged single notice.

At2026-10-21 10:55:21UTC the local coordinator marked flow=failed after
SSH connection reset and the subsequent compression-command assertion.
This is a transport/orchestration failure, not a confirmed native circuit
failure: an independent fresh SSH read still finds original Spectre4639
running and its raw file growing past20GB, with no normal completion footer.
The earlier compressing_native stage was premature; its existing gzip is
partial and must never be used as the complete capture. No interruption
receipt exists. Preserve native/raw/partial gzip and collect read-only
failure evidence under this plan's output and results JSON. Do not restart,
kill, alter or repair the native job, change transport source, or start a new
collector without user direction. Record the failed collection chain and
pause only heartbeatb after confirming its exact identity; ask whether to
reattach monitoring/collection to the still-running original job. No final
FFT or qualification is possible from this incomplete local capture.

## Authorized collection repair

User replied "修复" after the failure report, authorizing reattachment of
monitoring and collection to original4639/cf76d807, not another simulation.
At repair start HEAD4603dfe, index empty; existing Obsidian/cdac10 and other
plans are unrelated. Add owned scripts/integration/b_dynamic_512_recover.py,
scripts/integration/b_dynamic_512_pack.sh and focused
verification/integration/test_b_dynamic_512_recovery.py. Existing runner,
reducer/analyzer and factual reports remain owned. Shared bridge stays read
only. Remote OA none; scratch mutations limited to a separate recovery
packing control directory and a new lossless gzip, preserving old partial
gzip/raw/log/deck. Original launch receipt and failure snapshots remain intact.

Repair steps: bind exact host/profile/PID/process-start/deck/include hashes;
use short fresh SSH status queries with bounded reconnects, not a live SSH
session as the native lifetime. Require absent native process, explicit
normal zero-error footer, complete consecutive516 measurement/probe frames,
no fatal and stable raw before packing. Detach only a uniquely locked gzip/
hash worker (never Spectre); poll its atomic completion/failure marker, never
relaunch an uncertain worker. Download immutable compressed bytes in resumable
bounded ranges with per-range checkpoint hashes and final full-gzip SHA.
Original remote raw and gzip are retained until full decompressed SHA review.
Do not invent the lost original OS exit status: preserve result.ok=false if
unrecoverable; a separately identified complete recovered capture may be
analyzed from its explicit footer/frame/hash evidence, with this execution
provenance carried through metrics and no clean execution qualification.

Validate completion/active/wrongPID/fatal/partial gzip gates and simulated
interrupted-range resume offline; one small transfer fixture in the exact
owned scratch is allowed, not a circuit test. Verify frozen DUT/solver hashes,
launch one hidden local reattachment coordinator only, then read back growing
original progress and reactivate only heartbeatb with updated repair rules.
Keep previous alarm thresholds, quiet progress, no circuit changes or native
restart; finish whole-capture review under the original plan when available.
Focused local repair commit, no push.

Repair validation: five focused offline tests pass for terminal completeness/
active/fatal/duplicate history, wrong host/source/PID, disconnected execution
classification, interrupted range retries/resume, crash-tail reconciliation
and corrupt prefix rejection. One1,560,000byte fixture roundtrip in the exact
scratch matchesSHA7bfbc968e1e2f7ffbc2b93a9e1afbbc48bfb59a3e433aebbd603d4b6e259ba89;
remote sh-n validates the packing worker. Existing native-frame reducer and
FFT/ADCToolbox self-checks still pass. New stream SHA avoids reading the full
~34GiB gzip into RAM. Remote exact deck/5includes match frozen hashes; native
PID4639/startticks1449028686 still live. No native launch, termination, OA/
circuit/solver write or original scratch cleanup occurred during repair.

Repair committed1e53989. Exactly one hidden local reattachment launched at
2026-10-21 19:08:29Asia/Shanghai; Windows launcher40508, actualwatch37044.
recovery_launch.json preserves original receipt and exact original native
identity. Flowrunning_native_recovered, first90/516frames/86observed legal,
same1LTE/noCMI/clearalarms, error log empty. Reused onlyb with updated repair/
lost-exit qualification rules, ACTIVE tool/TOML identity readback confirmed.
No native restart and no claim that whole-run collection has yet completed.

Post-launch local-only validation also removed the completion gate's bridge
import from the offline NumPy environment and made status writes use unique
atomic pending files with bounded Windows sharing retries. Six focused tests
now pass, including concurrent writers; three relevant cases separately pass
in projectPython without the bridge installed. Loaded watch remains the
tested1e53989 collector, no coordinator/native restart; its single writer and
fresh heartbeat unique writer do not share pending files. Future offline
subprocesses load the corrected pure gate.90->92->93 real frames confirm
ongoing progress and empty recovery error log. All frozen source checks pass.

## Remote analysis only and storage review

User now explicitly requires remote analysis, metrics/figures only returned
to PC, progress attention restored if the original run remains alive, and a
local historical cleanup-candidate list with NO deletion. This supersedes
all earlier full-gzip download/cleanup permissions. No complete waveform,
waveform pickle or raw archive may be downloaded, and no historical/local/
remote data may be deleted during this target.

Extend ownership to config/b_dynamic_512_data_policy.yaml,
scripts/integration/b_dynamic_512_remote.py,
scripts/integration/b_dynamic_512_remote_status.py,
verification/integration/test_b_dynamic_512_remote_policy.py,
docs/storage_cleanup_candidates.md and generated output/storage_audit/.
Only exact scratchcf76d807/remote_analysis_v1 helper files may be created
remotely; OA and shared bridge/PDK remain read-only. Existing Obsidian/cdac10/
other-plans dirty work atHEAD1dd1c6c is unrelated and preserved, index empty.

First independently verify original process and terminal log: local flow has
since failed at11:14:58UTC with incomplete frame history, so do not falsely
reactivate a completed/failed run or silently restart Spectre. Implement
fail-closed local bulk-transfer guards and a standard-library remote status
reducer, returning only bounded JSON metrics, not the native log or raw.
Check remote runtime capability before claiming full analysis readiness.
If native is alive, resume only b with remote-only status/analysis rules; if
it exited incomplete, preserve data, keep b paused, report the blocker and
request native rerun authorization. No full512 FFT from partial data.

Inventory only this project's generated output metadata for cleanup review;
distinguish derived caches with a same-run PSF from unique raw evidence that
requires a rerun to recover. Do not call a directory expendable solely
because Git ignores it. List exact paths/sizes/evidence constraints, not
delete commands. Validate raw-transfer refusal, small-result allowlist/size
cap, remote metric/schema/current exactidentity and audit sums; focused local
commit/no push. No new simulation or unapproved dependency installation.

Implemented and verified remote standard-library status extraction on the
existingPython2.7.5; only~2KiB JSON returned. Original4639 and all matching
native commands absent;95/516 completed records/91observed, rawlast9.556070994us,
rawbytes25,599,275,008, no normal footer,2LTE/noCMI/fatal/invalid/gross records.
No interruption receipt or exit status establishes the cause. Flow now
native_exited_incomplete; b must remainPAUSED, not falsely restored as live.
Full remote dynamic reducer/plot environment has not been implemented or
validated because the original capture cannot meet516-frame completeness.
Explicit rerun authority is required before another native launch.

New policy hard-blocks original bulk downloader, range fetch and legacy
watch/packing entries; only boundedJSON/PNG results permitted. Two focused
policy/asset-size tests pass; exact remote deck hash still frozen. Local
metadata audit finds106.947GiB output,236files>100MiB totaling81.332GiB.
One814,368,482byte JSON duplicate pair has equalSHA;10derivedpickle candidates
with a same-case PSF total5.611GiB, including a current self-check fixture.
docs/storage_cleanup_candidates.md distinguishes these from57.007GiB of
large unique/nativePSF requiring backup decisions. No data deleted or moved.
