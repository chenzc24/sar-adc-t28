# Main sampling MOS width only B sine sweep

## Goal and ownership

User authorizes only main sampling MOS W1x/2x/3x, with topology,L,CDAC,
clock/reference timing and simulator precision unchanged. Compare equivalent
delay,gain,nonfundamental remainder and turnoff increment in the same short
500kHz/.8Vpeak/.45VCM/10MS/s sine. Four warmup plus20observed conversions,
24total/2.4us. No full-code/FFT/PVT/mismatch/noise, no OA adoption or push.

Branch exp/cdac-flat8-device,parent00f25a6. Untracked cdac10_dualrail config,
models,plan,scripts,verification are unrelated user work; do not touch.
Own this plan; config/b_sine_main_w.yaml; scripts/integration/b_sine_main_w.py;
scripts/integration/b_sine_main_w_analyze.py;
verification/integration/b_sine_main_w_results.json;
docs/b_sine_main_w.md; docs/figures/b_sine_main_w/;
narrow project_status entry; plan/log.md. Generated output/b_sine_main_w/ only.
Remote OA owned:none. Remote writes only bridge-created unique Spectre scratch
under /tmp/virtuoso_bridge_chenzc_intern25/90590/virtuoso_bridge_spectre/.
Read-only existing B OA/library/PDK and all previous sources/results/automations.

## Method

1. Healthy bridge0.8.0/t28_io,thu-wei,chenzc_intern25,CIWllm_IO,Spectre21.1.
   Read-only verify current library/technology and top/TB against B snapshots.
   Use immutable completed B deck/includes, never an unbound latest run.
2. W1x=1um uses existing validated native24frame run and decomposition receipt,
   not another duplicate simulation. Prepare byte-identical1x deck for proof.
   New2x/3x decks alter only Mmain in sar_bootstrap_canvas_flat_8b shared by
   XBOOTP/XBOOTN. L150nm,nf1,multi1 and every other transistor unchanged.
3. Update W and only width-derived AD/AS/PD/PS: single finger diffusion155nm,
   AD=AS=W*155nm; PD=PS=2*(W+155nm). Validate against existing PDK-generated
   320nm,500nm,1um main and2um thick-oxide reference geometry; all other model,
   spacing and stress parameters identical. No stale1x parasitics or increased
   multiplicity used to impersonate a wider single-finger transistor.
4. Same native statements, sources, passives,44continuous saves, B/commit and
   passive observers, APS4/conservative/maxstep10ps, requested reltol1e-5,
   effective prior1e-6,vabstol10nV,iabstol100fA,gear2only,TT/.9V/27C.
   Preserve declared51.6us stop with existing passive finish at2.4us.
5. Two independent compute jobs, at most two concurrently. Defer PSF parsing
   and parse sequentially: previous2GBASCII run peaked~14GB locally. Use the
   inspected bridge0.8.0 remote-run/result-assembly helpers without modifying
   the bridge package; same native CLI and result.ok classification as public
   adapter, split only orchestration/parse timing. Exact per-job log/PID receipt.
   No kill/restart or interference with other native jobs.
6. Require native result.ok,24frames,8compare/write/update,90/98ns stable final
   codes, same actual source sample history and native reported solver values.
   Retain all CMI/LTE/convergence/warnings; no auto retry or circuit changes.
7. Reuse exact DC+sin/cos and5ns..-.15ns cubic preedge extrapolation mathematics
   from b_sine_decompose; verify1x reproduces committed baseline. Compare delay,
   gain,DC,held raw error,held remainder peak/RMS,tracking/turnoff remainders,
   commonmode,gate slew/overdrive and same saved comparator stress screen.
   Keep uncorrected original acceptance separate; turnoff != pure injection.
8. Review comparison/edge figures with real baselines. Hash identity/source
   before/after checks, focused geometry/math/precision/count/syntax checks,
   factual result docs/log and scoped local commit only. No OA adoption/push.

## Expected artifacts and commit policy

Immutable per-case input decks, native logs/raw/waveform/result and exact remote
receipts under output/b_sine_main_w/. Small tracked metrics/report/figures only;
no PDK content,license records or OA binaries committed. Proposed bounded
commits `test: launch main-width-only B sine sweep` then result commit.
Do not mark successful merely because execution or gain/phase correction passes.

## Status

Completed all three comparable cases; W1 reused, W2/W3 native. Current B top/TB and36
native/historical dependency surfaces unchanged by read-only preflight, library
technologytsmcN28 and CIWthu-wei/llm_IO verified. W1deck byte-identical to old
deck; W2/W3 change only W,AD,AS,PD,PS in Mmain. Single-finger geometry rule
validated against actual prior320nm/500nm/1um/2um PDK netlist statements.

Coordinator started2026-10-21 10:22:11Asia/Shanghai, launcher36104,actual44712.
Native worker localPID63664/63676 (Windows subprocess wrappers63588/63596).
W2 remote a400dc73 solver137806,parent137680; W3 remote36fde9f4 solver137807,
parent137679. Both APS4/conservative/10ps,24frames actual2.4us; immutable
input snapshots and exact log/receipt paths under output/b_sine_main_w/.
At10:26local both2/24frames,8compares/stable, no CMI/LTE observed so far.

Independent comparison analysis --baseline-only reproduces committed1x gain,
lag,DC,held/nonfundamental and turnoff remainder; no new1x simulation. Source
syntax and geometry/inputidentity checks pass. Parallel remote compute/download
and sequential local assembly/parse split uses inspected bridge0.8.0 helpers,
no bridge source or native CLI/precision changes. Analysis/status may be
refined within scope while immutable inputs/jobs remain unchanged.

At10:57 local both native logs contain24/24 valid8-compare frames and zero-error
completion. Native reported solver parameters match baseline. W2 has one
SPECTRE-16780 event at1759.41ns in nativeSAR XD_ON1.AB, after frame17 held
measurement; W3 has none. Retain this numerical caveat, no rerun or retuning.
Local download/serial parse and final analysis remain pending. Status readback
now falls back to completed local logs across remote-cleanup races; this does
not change any simulation input or active native worker.

Concurrent Obsidian_docs edits/deletions/new files and its eight-bit plan were
observed during this run; preserve as unrelated user work, alongside the
original cdac10_dualrail files. Narrow shared log/status edits only; do not stage
or amend the other task's files or commits.

Recovery boundary: full~2GB raw and zero-error native logs are downloaded,
but localSFTP sessions for optional W2spectre.ic/W3spectre.fc stalled since
10:57:30 with no payload. Bridge inherits a4h timeout for these optional files.
Permit stopping only the verified SFTP child sessions for those exact paths,
not coordinator/native workers/Spectre or any other task. Existing helper skips
nonzero optional transfer failures; continue same download/serial parse flow.
No new simulation, changed precision or changed raw data. Record skipped files.
Same bounded recovery includes the following optionalW3.ic transfer and
post-download scratch-cleanup SSH if stalled. Verify parent/native worker and
exact command each time; stopping cleanup cannot affect already finished
Spectre or the downloaded raw/log, and a scratch retention is reported rather
than expanding to other directories. No generic SSH/process kill.

Final result: nativeW2/W3 zero errors,8/7warnings, result.ok true; all24frames
8compare/write/update andstable90/98nscodes; observedcodeerrors<=1. Same
sourcehistory andsampletimes, solverparameterdiffs{}, 44continuous signals,
1326793/1326603/1326646points. W2/W3parse315.60/240.98s serially. Completed
log/raw saved; scoped interruption skipped W2.ic/W3.fc/W3.ic optional transfers
and two scratch-cleanup sessions only, no native termination/rerun/raw change.

Held lag1.781261/.881995/.574213ns,gain-.025815/-.047062/-.068613%; raw
heldpeak4.464649/2.241513/1.518989mV,14/10/0of20outside1.7578125mVbudget.
Heldnonfundpeak8.260/13.835/21.430uV,RMS5.604/9.817/15.437uV. Turnofftotal
peak.327693/.460335/.624287mV,nonfundpeak6.010/13.088/21.048uV. Tracking
remaining improves2.789/.907/.487uV while heldremaining worsens: supports
turnoff-related cost, not pure charge-injection attribution. 3x is candidate
only, not adopted or fully qualified; W2LTE numerical caveat retained.

Baseline reproduction, input/geometry/include/source hashes,24log/waveform
measurements, mathsynthetic/reconstruction/orthogonality andwindow sensitivity
<=.123uV pass. Reviewed3plots with originalsample/zero/budget baselines; curated
metrics andfigures. Corrected this report's CDAC description from actual saved
deck:18multi groups,512equivalent units, not512independent declarations.
Scoped final validation andlocalresultcommit; no OA writes,push,newautomation,
fullcode,PVT,mismatch/noise or expandedexperiment. Unrelated user work preserved.
