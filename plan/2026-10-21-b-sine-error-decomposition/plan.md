# Existing B sine waveform error decomposition

## Goal and scope

Use only the completed B500kHz/.8Vpeak/.45VCM/10MS/s24frame waveform to
separate equivalent fixed phase delay, gain, DC offset and remaining error.
Inspect acquisition versus turnoff-related changes without changing the
circuit, clock, model, dimensions, precision or saved original data. No new
simulation, remote connection, automation change, FFT qualification or push.

Branch exp/cdac-flat8-device, parent61dcdb4. Untracked cdac10_dualrail files
are unrelated user-owned work and remain untouched. Existing B run is complete;
its heartbeat remains paused. Remote OA owned:none; all remote state/PDK and
existing output/b_sine_period files are read-only.

## Ownership

This plan; scripts/integration/b_sine_decompose.py;
verification/integration/b_sine_decomposition_results.json;
docs/b_sine_decomposition.md; docs/figures/b_sine_decomposition/;
the narrow decomposition entry in docs/project_status.md; plan/log.md.
Generated output only under output/b_sine_decomposition/.
Read-only dependencies: original context/result/summary/waveform receipt and
pickle/deck/includes/native log, prior tracked B result and analysis sources.

## Method

1. Require original result.ok, complete0..2400ns44signal waveform and exact
   SHA match to tracked B receipt. Original20observedframes4..23 and nominal
   SAMPLE50%fall remain the raw acceptance reference; no corrected pass claim.
2. Fit source and held voltage with DC plus sin/cos at the known500kHz.
   Express equivalent gain and phase delay, preserve exact raw-error identity
   with delay/gain/DC/source-fit residual/nonfundamental remainder. Delay is
   single-frequency equivalent, not uniquely identified physical RC or aperture.
3. Evaluate remaining nonfundamental error peak/RMS and low harmonics as
   diagnostics only. Do not equate this20point residual to fullADC DNL/INL,
   SNDR/ENOB or purely static nonlinearity; no transient noise was enabled.
4. From uniformly time-weighted preedge windows ending before clock fall,
   extrapolate tracking TOP differential to nominal sample time. Compare held
   value to that counterfactual; label it turnoff-related increment, not pure
   charge injection. Vary prewindow length/order for sensitivity, inspect gate,
   source/pin/TOP and saved representative reference nodes. Compare posthold
   plateau before first real comparator edge. No counterfactual simulation.
5. Fit acquisition and turnoff increment separately with same sinusoidal
   basis; separate their fundamental/DC and nonfundamental terms. State that
   linear signal-dependent injection can hide in fitted gain/phase and physical
   injection versus aperture/clock-feedthrough cannot be uniquely separated.
6. Save focused metrics, sampled data, readable decomposition and edge figures;
   visual review with raw/ideal baselines. Preserve raw failed budget separately.

## Validation and artifacts

Require source/deck/include/waveform identities and original complete records,
LS orthogonality and exact decomposition reconstruction, synthetic known-delay/
gain/offset/harmonic fit recovery, window/order sensitivity and interpolation
step checks; no broad suite or circuit run. Confirm unchanged original file
hashes after analysis. Syntax,JSON parse,figure review,diff-check and scoped
local commit, proposed `analysis: decompose existing B sine sampling error`.
Report all measured outcomes, even if physical attribution is indeterminate.

## Status

Completed local-only numerical analysis, visual review and focused checks.
Source B simulation/result and heartbeat remain unchanged. Scoped local
result commit only, no push.

## Results

Held equivalentgain.99974184572(-258.154ppm),lag1.781261225ns,DC<.01uV.
Original rawpeak4464.648904uV/RMS3168.533306uV; DC+fundamental remainder
peak8.259512uV/RMS5.604440uV, H3projection7.892781uV,H5.720054uV.
Preedge tracking lag1.890314730ns,gain-15.872503ppm, remainderpeak2.789366uV.
Held minus local preedge extrapolation peaks327.692875uV/RMS237.389345uV;
afterDC/fundamental removal its remainderpeak6.009549uV/RMS4.421882uV.
Commonmode increment-.447..-.464mV. Equivalent lag difference109.0535ps;
do not call it unique physical aperture or call6uV pure injection.

Prewindow5ns ending-.15ns, cubic/uniform10ps, clockhigh andG-input.8923..8935V.
3/5/8ns quadratic/cubic window sensitivitymax.122205uV; cubicvariants<.001uV,
5/20psresampling robust. SavedMSB4gatesunchanged, bottoms~100uVedge range.
Quiet hold+.6..+2ns maxchange.014624uV~solverprecision, not fullhold leakage.
Exact pointwise decomposition difference<1e-12V; synthetic gain/delay/DC/H2/H3
recovery passed. Original ASCII/pickle/context/deck/includes/log/old result
all checked unchanged before/after. No remote calls or simulator imports.

Independent closed-form coherent sine projections reproduce LS coefficients
within2e-12V; rowwise error reconstruction and tracking+turnoff remainders
agree within1e-12V. Synthetic fit recovery, all15original-file SHA checks,
curated/source/figure hashes, JSON parse, Python compile and diff-check pass.
Both figures reviewed: distinct mV/uV scales, no residual-obscuring legend,
raw/input/predicted tracking baselines and actual SAMPLE/gate edge timing.
