# Uniform reference-switch scale: 2x, 3x, 4x

## Goal and electrical boundary

Continue the user's approved ideal-gate/no-driver CDAC experiment by increasing
both P and N integer parallel multipliers together. Run factors2/3/4 at five
static differential inputs: -.8V, -.003515625V, +.003515625V, +.453515625V,
+.8V (15 transients). Allow at most two maxstep10ps confirmations of
decision-relevant extrema. TT MOS/MOM, .9V,27C,300ns; unchanged .1ns blanking,
.02ns edge, native Bootstrap/MOM, reference50ohm/4pF, input50ohm, ideal sign
comparator and fixed-period VA SAR characterization controller. This does not
replace or qualify the separately selected sample-initialized native async SAR.

Use independent generated decks, not new OA or a baseline replacement. Retain
unit P175/30nm and N150/30nm; multiplicity changes effective width, conductance,
charge and parasitics together. More width is not a higher SOA voltage rating.
.99V remains the current core-model SOA warning threshold, not a foundry pulse
or lifetime guarantee. No PVT/noise/MC/layout/full-input/spectrum signoff.

## Ownership / dirty-state audit

Branch exp/cdac-flat8-device. Untracked cdac10_dualrail files are preserved
historical work. Untracked plan/2026-10-20-sar8-bitwise-approximation/ belongs
to concurrent async work; all async sources, readbacks, cellviews and docs are
read-only. No overlapping modifications at start. Refresh shared plan/log.md
tail immediately before a bounded append. Scoped local commit, no push.

Own this plan; scripts/cdac8_dualrail/uniform_scale_experiment.py and
uniform_scale_results.py; docs/cdac8_uniform_scale.md;
docs/figures/cdac8_uniform_scale/; bounded plan/log.md append. Generated results
output/cdac8_uniform_scale/. Remote OA owned objects: none. Old pn_ratio,
no_driver and dualrail sources/results/VA, installed OA/Canvas and PDK read-only.

## Steps and validation

1. Check t28_io bridge/CIW/Spectre and exact SAR_ADC_T28 library/technology;
   retain fresh preflight metadata. Gate current saves use documented native
   terminal2 (G; reference MOS netlist order D G S B). First2x negative-half-LSB
   run is the instrumentation smoke/control; require all32 gate currents and
   12 existing drain currents, complete finite waveforms, correct gate equations.
2. Derive every deck from hash-pinned completed pn_ratio neg_p2n2. Change only
   MP_RATIO/MN_RATIO/VDIFF values, add gate-current saves, optional fine maxstep;
   assert full reverse transformation and all subckt blocks unchanged. Stage
   pinned three VA bodies. Refuse overwrites and preserve source/deck/VA hashes.
3. Explicit two-worker native APS pool, unique run dirs and per-completion
   persistence of result/log/PSF/waves. Require result.ok for accepted complete
   runs; retain failures and warnings without rerunning unchanged failures.
4. Check all32 MOS and five terminal differences over all-time, post-startup,
   SAR and restore windows; record instance/pair/time and CMI/suppressed/LTE.
   Separately report code/residual/SOA failure instead of dropping failed
   circuit candidates. Compare eight pre-compare samples with charge oracle
   and .25LSB=1.7578125mV; expected codes14/127/128/192/241.
5. Quantify reference local-rail deviations and reference-source current;
   all32 gate peak currents and per-cycle sum integral(abs(Igate)) as an
   ideal-driver load proxy, NOT physical clock power. Use common200..300ns
   integration with interpolated exact endpoints. Integration convergence is
   checked on a fine candidate if used; do not equate terminal current to Ron.
6. Fresh 2x control versus retained PN results; up to two fine repeats for
   small margins / extrema. Curated metrics/report and common-scale summary
   and timing plots with ideal baselines; inspect images. Focused provenance,
   invariance/count/gate/current/code/residual/SOA assertions, syntax checks,
   git diff --check and ownership review. Factual log and scoped local commit.

## Outcome

17 result.ok native APS transients:15 points plus positive-full3x/4x fine
maxstep10ps repeats. All finite/complete to300ns, codes14/127/128/192/241
correct, all deterministic residual budgets pass; maximum .601917mV.
Core-model SOA passes3/5 at2x,5/5 at3x and4x; fine repeats also pass.
2x fails true CMI at-.8V/+ .8V during restore:1.026090/1.019582V, printed5/10,
suppressed322/1961. Every other run zero CMI/suppressed, all17 zero LTE.

Grouped worst2x/3x/4x ports1.026090/.982771/.959974V, maximum residuals
.439913/.521631/.601917mV. 3x/4x nominal margins only about7.2/30mV, not PVT.
Maximum absolute gate charge .560739/.841598/1.125214pC/cycle; max reference
deviation180.231/191.986/201.455mV and source peak3.605/3.840/4.029mA.
More scale helps broad input SOA but increases ideal-driver load/reference
disturbance/error. At-.5LSB3x peak .951155V vs4x .953468V: not globally
monotonic with width. 4x is only a recommended next diagnostic candidate,
not an OA/baseline adoption or a sizing freeze.

Fine3x/4x peaks .982777430/.959968403V, deltas+6.134/-5.621uV; residual
deltas+.000912/-.012373uV, gate charge relative deltas-6.44/+2.74ppm.
Fresh2x controls replay retained PN peaks within .002uV. Documented native
gate/drain current saves all succeeded; sum(abs(Igate)) integral is a load
proxy, explicitly not physical clock power. All16 ideal gate equations pass,
all32 reference MOS/five pairs and44 selected native current vectors checked.

Source reverse transformation and unchanged subckt blocks, all source/deck/
VA/wave hashes, finite data, count/gate/current/code/residual/SOA/fine assertions,
Python syntax and diff checks pass. Two shared-scale figures visually checked
including restored phase blanking and ideal/reference limits. Two scripts,
report and small curated metrics/figures; raw output/cdac8_uniform_scale/.
Concurrent bitwise-approximation work committed independently; new simple-
Canvas plan/script and all unrelated work remain untouched. No OA/Canvas/PDK/
installed-VA writes. Scoped local commit only, no push. No full-input/PVT/
noise/MC/driver/StrongARM/Bootstrap-internal/layout/lifetime qualification.
