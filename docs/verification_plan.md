# Verification Plan

## Behavioral baseline

- Static ramp: missing codes, DNL, and INL.
- Coherent sine: SNDR, ENOB, SFDR, and reconstructed waveform.
- Reset, conversion latency, code stability, and boundary saturation.

The executable baseline uses eight ramp samples per code and a 16,384-sample
coherent -1 dBFS sine at near-Nyquist bin 7373. It passes when all 1024 codes
are present, ideal absolute DNL/INL are below 0.01 LSB, ENOB is at least 9.0
bit, and SNDR is at least 55.94 dB. Timing/reset checks begin with the later
clocked Verilog-A or RTL model; the present function model has no clock state.

## Clocked Verilog-A baseline

- Timing smoke: reset, held-input behavior, ten MSB-first decisions,
  `BUSY/VALID`, output stability, and conversion latency below 60 ns.
- Static correlation: 8,192 conversion results, eight samples per code, exact
  code-for-code agreement with the Python golden model, zero missing codes,
  and ideal absolute DNL/INL below 0.01 LSB.
- Dynamic correlation: 16,384 coherent samples at bin 7373 and -1 dBFS,
  exact ideal code agreement, SNDR at least 55.94 dB, ENOB at least 9.0 bit,
  and SNDR within 0.1 dB of the Python result.
- Nonideality regression: zero-valued controls preserve ideal results; fixed
  seeds reproduce noise sequences; individual errors are enabled separately
  before any combined budget run.

EVAS 0.7.0 with its Python engine is limited to the short local timing smoke
because its optional Rust backend is unavailable on the current Windows host.
Remote Spectre 21.1 AHDL compilation and transient execution are the final
simulator gate. EVAS acceptance alone is explicitly not Spectre portability.

## Unit-level transistor verification

- Comparator: offset, noise, delay, metastability, kickback, and energy/conversion.
- CDAC: transfer curve, settling, switching energy, mismatch, and parasitic sensitivity.
- Sampling switch: acquisition settling, on-resistance, charge injection, and THD.
- SAR logic: reset, bit order, timing margin, and output validity.

## Integrated verification

- TT nominal static and dynamic performance.
- Process, voltage, and temperature corners.
- Device mismatch and capacitor mismatch Monte Carlo.
- Reference impedance and clock-jitter sensitivity.
- Schematic-versus-extracted correlation.

## Sign-off

- DRC clean.
- LVS clean.
- Extracted post-layout ENOB/DNL/INL/power targets met.
