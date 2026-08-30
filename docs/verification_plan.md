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
