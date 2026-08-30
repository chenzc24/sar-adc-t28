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
- Allocated-noise experiment: enable the 0.18 LSB sampling, 0.18 LSB
  comparator, and 0.12 LSB reference/switching random-noise allocations with
  fixed seeds in a separate 16,384-sample coherent-sine deck. Require the
  project SNDR/ENOB gates and compare with the corresponding partial RSS
  prediction. Keep jitter, unmodeled distortion, offset, and settling out of
  this run because they require different error models.

EVAS 0.7.0 with its Python engine is limited to the short local timing smoke
because its optional Rust backend is unavailable on the current Windows host.
Remote Spectre 21.1 AHDL compilation and transient execution are the final
simulator gate. EVAS acceptance alone is explicitly not Spectre portability.

## Topology-aware electrical macro-model

- Exact capacitance-matrix regression: 32-Cu effective top load, unity base
  coupling, and binary weights from 1/2 through 1/1024.
- Static analytical regression: nominal zero missing codes and numerical-zero
  DNL/INL; assumed parasitic sensitivity must measurably alter the transfer.
- Closed-loop transient regression: six code centers, ten resolved MSB-first
  comparisons, correct comparator signs, exact charge-model codes, conversion
  latency below 60 ns, and every nominal pre-compare residual below 0.25 LSB.
- Negative sensitivity regression: slow reference/switch settling, assumed
  top/bridge parasitics, and elevated direct kickback must expose their
  respective timing, code, or comparator-sign failures.
- OA structural regression: exact owned cells only, instance/parameter/net
  readback, no adjacent-control-net shorts, symbol-port audit, Check and Save,
  and successful hierarchical Spectre netlist export.

This is a deterministic electrical closure gate. Do not combine its RC and
kickback errors with the prior random-noise run by simple sample-wise addition;
noise, PVT, mismatch, and extraction are introduced when replacing macros with
PDK blocks.

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
