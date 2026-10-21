# One-period native B sine transient and progress monitoring

## Goal and boundaries

Run the user-approved 500kHz differential sine, .8V peak, .45V common mode,
10MS/s, four startup frames plus twenty observed conversions (24frames,
2.4us actual simulation). Preserve current adopted B, all native transistor
topology/sizes, reference/source impedances and prior solver precision.
No full-code/FFT/PVT/mismatch/noise campaign and no OA circuit modifications.

Branch exp/cdac-flat8-device, parent f115f7f. Untracked cdac10_dualrail config,
models/scripts/verification/plan are user-owned, unrelated, left untouched.

Own: this plan; config/r3_b_sine_period.yaml;
models/veriloga/r3_b_sine_period/r3_sine_probe.va;
scripts/integration/b_sine_period.py; scripts/integration/b_sine_analyze.py;
verification/integration/b_sine_period_results.json (after results);
docs/b_sine_period.md and docs/figures/b_sine_period/ (after results);
the narrow B-sine progress entry in docs/project_status.md; plan/log.md.
Generated data owned under output/b_sine_period/ only.
Remote OA owned: none. Read-only current SAR_ADC_T28/sar_adc8_join_r3/schematic,
tb_sar_adc8_join_r3/schematic, B gate/commit and all native dependencies/PDK.
Remote work is fresh native Spectre scratch through t28_io, thu-wei/llm_IO,
user chenzc_intern25. Do not cancel or relaunch old campaigns or any other job.

## Method and validation

1. Verify healthy bridge/CIW/user/library/technology; read current top and TB
   against adoption snapshots and36native/historical dependencies. Fresh OA
   export must match all previously adopted B native subcircuit statements.
   Snapshot exact B/commit VA includes and verify hashes.
2. Only the two source equations, testbench observation/output and analysis
   wrapper change. Continuous complementary sinusoidal sources, phase -72deg
   and108deg, cross zero at400ns start of the observed2us period. Same50ohm
   inputs and50ohm+4pF reference rails. Acquisition/hold timing unchanged.
3. Reuse previous passive code/count monitor and early-finish observer.
   Add a passive (no electrical contribution) source/held-error probe at
   nominal41.05/41.65ns and98ns per100ns frame. Do not substitute ideal code
   for comparator/SAR outputs. All startup frames solved/saved.
4. Same APS4,conservative,maxstep10ps,requested reltol1e-5,vabstol1e-8,
   iabstol1e-13,gear2only,TT/.9V/27C. Preserve B12's declared51.6us stop and
   stop-dependent defaults, ending normally through existing observer at2.4us.
   Explicit continuous selected saves, no strobe-only waveform reduction.
5. Require result.ok,24final records,8comparisons/frame,90/98ns stable readout.
   Evaluate held error against.25LSB=1.7578125mV and actual source at sampling
   fall; code-vs-ideal gross errors (>1code) and input-pair VGS/VGD/VDS screen.
   Preserve CMI/LTE/all warnings. First-four startup and20measured records
   separate. A bounded functional check is not all-code or dynamic qualification.
6. Save waveform/provenance, source-vs-decoded-code timing with correctly
   aligned sampling/read times and real baselines; detailed one-frame eight
   comparison plot. Inspect figures before declaring final delivery.
7. Launch one local hidden runner, exact remote receipt/log/PID, no duplicates.
   Thread heartbeat every5minutes checks native progress/errors and local
   transfer/parse/analysis state. Notify on milestones/meaningful change/failure,
   remain quiet on unchanged state. Finish analysis/review when ready, then
   pause this monitor. No automatic circuit edits, expanded runs, or push.
8. Focused source/deck contract,syntax and diff checks. Record launch separately
   from completed results; scoped local commits, no push. Proposed messages:
   `test: launch one-period native B sine check` and later bounded result commit.

## Status

Completed bounded test and visual review; sampling/hold budget FAIL, not a
qualified ADC. Bridge0.8.0, CIW thu-wei/llm_IO and native Spectre21.1 healthy
at launch.
Only CIW window open. Current B adopt receipt f115f7f is the baseline; old R3
performance scripts/hash expectations are historical and are not reused as B.

## Launch record

Fresh API comparison of top/TB and36native/historical dependencies passed.
Fresh OA export matches adopted B subcircuit text exactly; downloaded B/commit
VA hashes match adoption. Prepared one immutable deck,44continuous saved nodes,
old count monitor/finish observer and one passive source/held-error observer.
Source/deck identity checks and Python syntax passed. No OA mutations.

Hidden local launcher started2026-10-21 08:58:59 Asia/Shanghai, worker PID34600
(Windows launcher PID3332). Native scratch /tmp/virtuoso_bridge_chenzc_intern25/
90590/virtuoso_bridge_spectre/00a444e1; real Spectre PID281826, parent csh281772.
The scratch spectre.pid is the shell launcher281770, NOT the real solver PID;
status now binds solver PID by exact deck path. Legacy procps mishandles
comma-separated empty headers, so use ordinary headers and explicit parsing.

At09:02:24local:2/24frames recorded, both8comparisons and90/98ns stable.
No CMI or LTE warning yet; original7AHDL/global-terminal/PDKscalefactor warnings
retained. First startup held probe -1.71836mV is preliminary, not a statement
that all measured frames pass. Full result and waveform review pending.

Heartbeat id `b`, name B版单周期正弦仿真巡检, ACTIVE every5minutes on this thread.
Read back its automation.toml, verified target_thread_id matches this chat.
It tracks exact native logs/PID and local download/parse/analyze/review stages;
no duplicate launch, no expanded campaign, pause after completion/failure.
Source/launch commit only now; no result qualification or push.

Subsequent startup frames0..2:codes24,44,72, all8compares/valid; passive
nominal-SAMPLE-fall held differences-1.71836,-2.92038,-3.83207mV. Latter two
exceed the original1.7578125mV deterministic budget; report this early finding
without calling the20measured frames failed or applying an aperture correction.
Complete waveform needed to separate startup/dynamic tracking/aperture timing.
Native log reported reltol1e-6,10ps,10nV/100fA,gear2only and all other prior
solver values identical. Only outputstart0vs800ns differs (save startup now).

## Final result and visual review

One run only; native result.ok,0errors/7warnings/7notices, actualstop2400ns.
All24R3MEAS/BSINE records complete,8compares/write/update in every frame,
90/98ns codes stable. All24passive probes agree with continuous-waveform
source/held/error within0.1uV. Native solver parameters unchanged except the
declared output saving-start difference above. No CMI-2754 or LTE relaxation.
Original7warning lines retained (1AHDL,2global/subckt,4PDKscalefactor).

Twenty observed frames4..23: maximumcodeerror1, no >1code outlier; raw held
error-4.464648904..+4.464647226mV,14/20above1.7578125mV budget, FAIL.
Comparator inputpair VGS/VGD/VDS peak0.898006456V below0.99V screen; not
all-device/lifetime qualification. No FFT/DNL/INL/ENOB/PVT/noise/mismatch claim.

At worstframe4,440.05ns (1ns before SAMPLEfall), SAMPLE=.9V, mainG-input
P/N=.892809/.892946V; source100.391258mV,pin100.262587mV,TOP95.673304mV.
InputR contributes-.128672mV differential error, TOP-pin=-4.589283mV,
TOP-source=-4.717954mV already during tracking. Held441.65ns=98.419517mV
vs sampledsource441.05ns=102.884166mV. Main observed error predates turnoff;
one-frequency slope-equivalentlag1.780792ns, residualpeak.225487mV is
diagnostic only, no shift/correction of acceptance reference or ideal codes.

Native solver elapsed1603s (bridge execution1605.85s),download76.39s,
parse211.58s,bridge total1899.17s.44continuous signals/1326793points,
0..2400ns waveform SHA1daabea5ad11f117d9a877e0d1f52c3a2e842ea9f73f9ae7c113d6c2acdc58ef.
Raw2.01GBASCII retained unchanged in output. No duplicate jobs or OA writes.

Analysis-only refinements: actual-read-time step traces instead of misleading
linear interpolation, extend displayed final decoded hold, budget panel,
acquisition/fall legend, source/pin/TOP tracking diagnostics, passive-log crosscheck,
and reproducible --curate for small verification JSON/figure copies. Both final
figures visually inspected with ideal baselines, sampling/readout separation,
legends and worst-error frame (one-based5). Raw data/deck/includes not modified.
Report docs/b_sine_period.md; tracked metrics verification/integration/
b_sine_period_results.json; two reviewed figures docs/figures/b_sine_period/.
Focused syntax/source identity/hash/count/precision/figure checks and local
result commit; no push. Heartbeat b to be paused on delivery, no follow-on run.
