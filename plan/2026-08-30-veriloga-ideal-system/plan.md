# Verilog-A Ideal System Baseline

## Goal

Implement and validate a clocked, cycle-accurate Verilog-A model for the
default 10-bit fully differential SAR ADC. Correlate its ideal transfer and
timing against the existing Python golden model, then add disabled-by-default
nonideality controls that map to the stage-1 error budget.

## Dirty-State Note

Start state from `git status --short --branch`:

```text
## main...origin/main
```

The worktree was clean and synchronized with `origin/main` at `2ff50f2`.

## Local Owned Files

- `README.md`
- `requirements.txt`
- `config/design_spec.yaml`
- `docs/architecture.md`
- `docs/design_log.md`
- `docs/verification_plan.md`
- `models/veriloga/`
- `netlist/tb/tb_sar_adc_ideal_*.scs`
- `scripts/analysis/run_veriloga_baseline.py`
- `verification/system/test_veriloga_baseline.py`
- `virtuoso/cell_manifest.yaml`
- `plan/2026-08-30-veriloga-ideal-system/plan.md`
- `plan/log.md`

## Remote OA Owned Objects

- none

Remote Spectre may be used through a unique temporary run directory after
bridge preflight. The `SAR_ADC_T28` library and every OA cellview remain
read-only in this target.

## Read-Only State

- remote `SAR_ADC_T28` OA library and all cellviews
- `tsmcN28`, PDK models, shared libraries, and active Virtuoso windows
- the Python golden-model algorithm in `models/behavioral/sar_adc.py`
- sibling `ADCToolbox` and `veriloga-skills` repositories
- generated files under `output/`

## Shared Dependencies And Assumptions

- `config/design_spec.yaml` remains the single source for resolution, voltage
  range, sample rate, SAR clock rate, error allocations, and metric gates.
- The behavioral core exposes separate sample and SAR clocks. A later
  transistor-level `sar_clock_gen` may internalize the 200 MHz bit clock.
- The sample is taken on the falling edge of the 40 ns acquisition pulse. Ten
  rising SAR-clock edges then perform MSB-first decisions in 50 ns.
- The Verilog-A model is voltage-mode and event-driven. It must avoid
  runtime-indexed electrical-bus reads and constructs that only EVAS accepts.
- EVAS is a fast behavioral smoke simulator, not evidence of Spectre
  portability. Remote Spectre AHDL compilation is the final language gate.
- Clock jitter belongs to the testbench clock source; it is not generated
  inside the ADC core.

## Implementation Steps

1. Add a single-module `sar_adc_ideal_10b.va` with explicit ports, persistent
   conversion state, one decision per SAR-clock edge, and smoothed electrical
   outputs for code, busy, and valid.
2. Add zero-default parameters for comparator offset, sampling/comparator/
   reference noise, per-bit CDAC weight error, and residual settling fraction.
3. Add timing, static-ramp, and coherent-sine Spectre-format testbenches with
   explicit saves and the AHDL include last.
4. Add one analysis/validation entry point that decodes output codes, checks
   clock behavior, computes static and dynamic metrics, and compares ideal
   results with the Python golden model.
5. Add focused regression coverage for source-contract checks, deterministic
   code correlation, timing, and generated summary metrics.
6. Update only the architecture, verification, manifest, and maintenance
   records required to describe the new executable contract.

## Validation And Pass Criteria

- Verilog-A source audit passes: declared ports/state, balanced blocks,
  continuous output contributions, no runtime-indexed electrical-bus reads,
  and no unsupported current/charge contributions.
- EVAS parses and runs the timing testbench when available.
- Reset clears the outputs; input is held through conversion; exactly ten
  rising SAR-clock edges produce an MSB-first result; conversion completes
  within 60 ns; busy/valid behavior matches the declared contract.
- Deterministic boundary and representative vectors match the Python model
  code-for-code.
- The ideal full ramp has zero missing codes and absolute DNL/INL below
  0.01 LSB.
- The ideal coherent sine meets SNDR >= 55.94 dB and ENOB >= 9.0 bit, with
  Verilog-A SNDR within 0.1 dB of the Python golden result.
- Nonideality parameters are reproducible with fixed seeds and preserve the
  ideal results when set to zero.
- Remote Spectre compiles and runs the model with `result.ok` after bridge,
  CIW, and simulator preflight. If remote execution is unavailable, record the
  target explicitly as `not Spectre-compiled`; EVAS is not a substitute.
- Python compile, focused tests, YAML parse, `git diff --check`, and final
  owned-path review pass.

## Expected Artifacts

- `output/veriloga_baseline/timing/tran.csv`
- `output/veriloga_baseline/static/tran.csv`
- `output/veriloga_baseline/dynamic/tran.csv`
- `output/veriloga_baseline/summary.json`
- compact timing, static-linearity, and dynamic-spectrum plots

Generated artifacts remain ignored by Git.

## Commit And Push Intent

Commit the completed target as:

```text
feat: add clocked Verilog-A SAR baseline
```

Push policy:

```text
not requested
```

## Outcome

- Implemented the complete clocked Verilog-A source, timing/static/dynamic
  decks, remote/local runner, waveform analysis, nonideality controls, focused
  tests, and project documentation.
- EVAS 0.7.0 compiled the source with zero lint diagnostics. The timing smoke
  produced codes 768 and 256 and two 47.5 ns conversions.
- Python source-contract, decoder, 1024-code static, and 16,384-sample dynamic
  analysis regressions passed.
- After the bridge's generic Cadence startup file was aligned with the working
  `t28_io` profile, Spectre 21.1 compiled the AHDL model and completed all
  three remote runs with zero errors. Timing decoded to codes 768 and 256 with
  47.5 ns conversion latency, matching EVAS.
- The 8,192-sample static ramp matched the expected eight samples per code,
  with zero missing codes and zero ideal DNL/INL.
- The 16,384-sample coherent sine matched the Python model code-for-code after
  the expected sample time was aligned to the midpoint of the 20 ps sampling
  edge. It achieved 60.954 dB SNDR, 82.213 dB SFDR, and 9.833 bit ENOB; the
  SNDR delta from the Python reference was 0.001 dB.
- Python compilation, three focused regressions, YAML parsing, and
  `git diff --check` passed. The target is complete.
- No remote OA objects were created or modified.
