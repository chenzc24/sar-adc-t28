# In-flight FFT code audit

2026-10-28T09:29:56.022762+08:00

Observer logs copied read-only (A34068bytes/B42800bytes), no waveform arrays or simulator changes. Snapshot complete lines begin frame0 without gaps. All prewarm and measured frames have8comparisons/8writes/8updates/16captures, stable90ns/98ns code, valid=1 and conversion<60ns. This checks recorded protocol counts, not a new full native edge-order validation.

|Item|A|B|
|---|---:|---:|
|Total frames incl8warmup|108|131|
|Measured frames|100|123|
|Protocol/validity/timing failures|0|0|
|First frame output|231|231|
|Mismatch vs ideal source at SAMPLE_INT falling edge|88/100|110/123|
|Largest difference vs source ideal|3LSB|3LSB|
|Mismatch vs ideal quantizer of held TOPP-TOPN|11/100|18/123|
|Largest difference vs held ideal|1LSB|1LSB|
|Fitted held/source equivalent phase lag|0.845ns|0.838ns|
|Code sine-fit max residual|0.499LSB|0.529LSB|
|Conversion time|29.911–30.101ns|29.129–29.412ns|

The100common measured frames differ in2cases: frame13 A151/B152; frame37 A30/B31. Both onecode differences, no large A/B jump. All held-ideal mismatches lie within0.143LSB (~1.01mV) of an ideal transition. This suggests boundary/gain/aperture sensitivity, not confirmed random logic failures; it does not prove static transitions ideal.

Direct comparison to source voltage at internal sampling-clock falling edge produces real2–3code deviations and must not be hidden. Source-to-held phase lag is a fit-based equivalent quantity; physical root cause (tracking/input RC/effective aperture) is not established by these logs. Using the measured held quantity separates the downstream conversion discrepancy from acquisition dynamics, but is not an independent accuracy signoff. Code sinefit removes gain/DC/phase and cannot prove zero distortion or good finalFFT.

Current conclusion: no recorded protocol failure, late output instability, timeout or large isolated code outlier identified in this prefix. Cannot assert everyidealcode correct or all1024samples pass. Final native waveform-code crosscheck, completeFFT, and static transition measurements pending. Overvoltage remains recorded and unqualified. Full frame tables: a_frames.csv,b_frames.csv; detailed mismatches:comparison.json.
