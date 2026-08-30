# Complete Behavioral Baseline

## Goal

Complete the first two design stages for the default 10-bit, 10 MS/s fully
differential SAR ADC: establish a quantitative system error budget and deliver
a reproducible bit-accurate ideal SAR model with passing static-ramp and
coherent-sine verification.

## Dirty-State Note

Start state from `git status --short --branch`:

```text
## main...origin/main
```

The worktree was clean. The separately cloned `ADCToolbox` repository is a
read-only shared dependency and is outside this Git worktree.

## Local Owned Files

- `.gitignore`
- `README.md`
- `requirements.txt`
- `config/design_spec.yaml`
- `docs/architecture.md`
- `docs/design_log.md`
- `docs/error_budget.md`
- `docs/verification_plan.md`
- `models/behavioral/`
- `scripts/analysis/`
- `verification/system/`
- `plan/2026-08-30-behavioral-baseline/plan.md`
- `plan/log.md`

## Remote OA Owned Objects

- none

## Read-Only State

- remote `SAR_ADC_T28` OA library and all cellviews
- `tsmcN28`, PDK models, shared libraries, and all remote Virtuoso sessions
- sibling repositories, including `E:\bridge-Agent-T28\ADCToolbox`
- generated files under `output/`

## Shared Dependencies

- `config/design_spec.yaml` is the single source for resolution, rates, range,
  targets, behavioral stimulus, and error allocations.
- ADCToolbox is pinned to exact upstream commit
  `a8995cf4faf73dde9918589bfeb866c6a77db12d`.
- The ideal 5+5 split CDAC has the same transfer weights as an ideal binary
  10-bit DAC. Bridge capacitor ratio error, parasitics, switching trajectory,
  and settling are intentionally outside this target.
- Dynamic verification uses a coherent sine and reports metrics against the
  declared differential full-scale range.

## Expected Work

1. Add compact behavioral and error-budget settings to the existing spec.
2. Implement one bit-accurate SAR model adapter over the pinned ADCToolbox
   primitives.
3. Implement one analysis entry point that produces the derived error budget,
   ideal static ramp, coherent-sine metrics, and compact plots/JSON output.
4. Add one focused system test covering thresholds, saturation, ramp DNL/INL,
   missing codes, and coherent-sine ENOB.
5. Update only the architecture, verification, and decision records needed to
   make the baseline reviewable.

## Expected Artifacts

- `output/behavioral_baseline/summary.json`
- `output/behavioral_baseline/static_linearity.png`
- `output/behavioral_baseline/dynamic_spectrum.png`

These are reproducible generated artifacts and remain ignored by Git.

## Validation And Pass Criteria

- YAML parses and derived values match the declared 10-bit, 1.8 V differential
  span and 10 MS/s rate.
- Focused Python unit/system test passes.
- Static ramp visits all 1024 codes with zero missing codes and ideal
  `abs(DNL) < 0.01 LSB`, `abs(INL) < 0.01 LSB`.
- Coherent `-1 dBFS` sine has `ENOB >= 9.0 bit` and `SNDR >= 55.94 dB`.
- The declared random-noise allocations fit within the total error allowed by
  the ENOB target and retain positive deterministic/distortion headroom.
- Python files compile and the end-to-end runner produces all expected
  artifacts.
- `git diff --check` passes and the final diff contains only owned files.

The focused test is required because this target establishes the executable
golden-model contract used by later Verilog-A and Spectre correlation.

## Experience Signal (for human review)


## Commit And Push Intent

Commit as:

```text
feat: add SAR ADC behavioral baseline
```

Push policy for this target:

```text
not requested
```

## Outcome

- Derived LSB: 1.7578125 mV over the declared 1.8 V differential span.
- Error allocation projects 56.784 dB SNDR and 9.140 bit ENOB at -1 dBFS,
  with 0.844 dB margin over the target.
- The full ideal ramp exercised codes 0 through 1023 with zero missing codes
  and zero DNL/INL.
- The near-Nyquist coherent sine at 4.500122 MHz produced 60.953 dB SNDR,
  82.033 dB SFDR, and 9.833 bit ENOB.
- Focused tests, Python compilation, YAML parsing, artifact generation, and
  visual plot inspection passed.
- Remote OA state was not accessed or changed.
