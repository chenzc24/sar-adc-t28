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

Launched two native cases; complete results pending. Current B top/TB and36
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
