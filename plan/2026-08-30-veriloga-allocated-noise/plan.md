# Verilog-A Allocated-Noise Experiment

## Goal

Enable the stage-1 allocated sampling, comparator, and reference/switching
random-noise values in the clocked Verilog-A SAR ADC, run a reproducible
16,384-sample coherent-sine Spectre experiment, and compare the measured
dynamic metrics with the corresponding partial RSS prediction.

## Dirty-State Note

The worktree starts clean and synchronized with `origin/main` at `e9f62cf`.

## Local Owned Files

- `netlist/tb/tb_sar_adc_allocated_noise_dynamic.scs`
- `scripts/analysis/run_veriloga_baseline.py`
- `verification/system/test_veriloga_baseline.py`
- `docs/verification_plan.md`
- `docs/design_log.md`
- `plan/2026-08-30-veriloga-allocated-noise/plan.md`
- `plan/log.md`

The existing `models/veriloga/sar_adc_ideal_10b.va` is read-only unless the
experiment exposes a simulator or modeling defect. Its existing zero-default
noise parameters are the interface under test.

## Remote OA Owned Objects

- none

Spectre may use a unique bridge temporary directory. All Virtuoso OA
libraries, cellviews, active windows, and PDK content remain read-only.

## Assumptions And Scope

- Use the design-spec allocations exactly: 0.18 LSB RMS sampling noise,
  0.18 LSB RMS comparator noise, and 0.12 LSB RMS reference/switching noise.
- Sampling noise is drawn once per conversion. Comparator and reference noise
  are drawn independently at each SAR decision, matching the model's current
  cycle-level interpretation.
- Fixed seeds make this regression deterministic and debuggable; they do not
  constitute Monte Carlo coverage.
- Clock jitter remains a testbench timing effect and is excluded from this
  first run. The distortion/unmodeled allocation is a guard band without a
  specified waveform and is not relabeled as white noise.
- Comparator offset and CDAC settling are deterministic guardrails and are not
  included in the random-noise RSS comparison.

## Implementation Steps

1. Add a separate coherent-sine deck that enables only the three explicitly
   modeled random-noise allocations; preserve the ideal deck unchanged.
2. Extend the runner with an allocated-noise analyzer that records spectral
   metrics, code-error statistics, the partial RSS projection, and the delta
   between predicted and simulated SNDR.
3. Add focused regression coverage for the new analyzer and its budget math.
4. Run the deck through remote Spectre 21.1 and analyze the downloaded
   waveform with the project environment.
5. Record the result and the modeling limits factually.

## Validation And Pass Criteria

- Spectre AHDL compilation and transient execution return `result.ok` with
  zero errors.
- Exactly 16,384 conversion results are decoded.
- The fixed-seed run meets the project gates of SNDR >= 55.94 dB and
  ENOB >= 9.0 bit.
- Measured SNDR is below the ideal baseline and within 1.0 dB of the partial
  RSS prediction for quantization plus the three enabled random sources.
- Python compilation, focused tests, YAML parsing, `git diff --check`, and an
  owned-path review pass.

## Expected Artifacts

- `output/veriloga_allocated_noise_spectre/allocated_noise/tran.csv`
- `output/veriloga_allocated_noise_spectre/allocated_noise/spectre_result.json`
- `output/veriloga_allocated_noise_spectre/summary.json`

Generated artifacts remain ignored by Git.

## Commit And Push Intent

Commit the completed experiment locally as:

```text
feat: validate allocated Verilog-A noise budget
```

Push policy: not requested.

## Outcome

- Reused the existing zero-default Verilog-A noise controls through a
  separate deck; the ideal deck and model defaults remain unchanged.
- Spectre 21.1 compiled and completed the 16,384-sample fixed-seed run with
  zero errors.
- The enabled sampling, comparator, and reference-noise subset measured
  58.059 dB SNDR, 87.453 dB SFDR, and 9.352 bit ENOB. The corresponding
  quantization-plus-three-source RSS prediction is 58.066 dB, a -0.007 dB
  simulation delta.
- 3,641 codes changed relative to the ideal sequence; every change was only
  one LSB, the mean code error was -0.001 LSB, and the code-error RMS was
  0.471 LSB.
- Clock jitter, unmodeled distortion, comparator offset, and CDAC settling
  remain explicitly outside this result. The experiment validates a partial
  random-noise budget, not the complete error budget or a transistor-level
  noise model.
