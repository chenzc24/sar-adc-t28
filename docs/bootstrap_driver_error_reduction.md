# Bootstrap-driver held-error reduction screen

## Decision

Do not implement the screened `MN7/MN10/MP8` resizing or non-overlap changes
in OA. They reduce the first bootstrap prototype's held error, but even an
extreme sizing combination remains more than 20 times above the raw
`0.439 mV` target and consumes useful sample-gate-overdrive margin. The next
iteration must change the turn-off or charge-compensation topology.

## Provenance and scope

The screen uses the unedited automatic OA export of
`SAR_ADC_T28/tb_sar_bootstrap_transient`, SHA-256
`f3818ef606de602671beac8b6728a1f5460958d03ca0299de0fc79e28132242c`.
Every generated deck preserves the complete `sar_bootstrap` subcircuit except
for explicitly audited multiplier substitutions on `MN7`, `MN10`, and `MP8`.
External `PHI` fall to `PHIB` rise timing is swept separately.

All electrical results are Spectre 21.1 with the T28 PDK at TT, 0.9 V, and
27 C, a 219.5-fF load per side, and the existing 50-ohm source. This is not a
PVT, mismatch, noise, extracted, power, or reliability qualification.

The installed EVAS simulation guidance was checked before execution. EVAS
does not support transistor solving or Spectre subcircuit hierarchy, so it was
not used; the foundry Spectre flow is the result source of truth.

## One-factor result

Thirteen one-factor cases completed successfully at `Vdiff=+0.8 V`.

| Change from baseline | Held differential error | Minimum sample VGS |
| --- | ---: | ---: |
| Baseline: MN7/MN10/MP8 multi 2/4/4, 1-ns gap | -12.026 mV | 0.811 V |
| MN7 multi 8 | -11.344 mV | 0.781 V |
| MN10 multi 16 | -11.572 mV | 0.794 V |
| MP8 multi 1 | -11.867 mV | 0.825 V |
| 0.2-ns non-overlap | -11.684 mV | 0.811 V |

`MN7` strength is the most effective single knob, followed by `MN10`.
Changing `MP8` has little effect, and 0.5-2-ns non-overlap changes are nearly
neutral. No single-factor direction approaches 0.439 mV.

## Combination and full-input confirmation

Eight baseline/combination cases were screened. One SSH upload reset was
retained as a transport failure and the exact case then reran successfully.
The two useful bounds were confirmed with the baseline over five differential
and three single-ended inputs, for 24/24 successful confirmation cases.

- `best_one_factor_combo`: `MN7=8`, `MN10=16`, `MP8=1`, gap `0.2 ns`.
- `discharge_extreme`: `MN7=16`, `MN10=32`, `MP8=1`, gap `0.2 ns`.

| Metric | Baseline | Reasonable combination | Extreme discharge |
| --- | ---: | ---: | ---: |
| Maximum raw differential held error | 12.026 mV | 10.298 mV | 9.097 mV |
| Fitted differential gain error | -1.510% | -1.289% | -1.132% |
| Maximum post-fit residual | 0.109 mV | 0.034 mV | 0.088 mV |
| Maximum acquisition error, all inputs | 0.721 uV | 1.621 uV | 2.808 uV |
| Sample VGS range | 0.811-0.828 V | 0.779-0.803 V | 0.742-0.775 V |
| Main gate at 270 ns | about 80.3 mV | about 23.1 mV | about 12.9 mV |
| Maximum reconstructed terminal difference | 1.787 V | 1.787 V | 1.787 V |

The extreme candidate reduces the raw endpoint error by only 24.4% while
approximately quadrupling `MN7` and octupling `MN10` relative to the baseline.
It also lowers the minimum sample `VGS` by about 70 mV. That is a poor
area/parasitic/overdrive exchange and remains far outside the raw target.

The errors remain predominantly linear gain compression. Their post-fit
residuals are below 0.439 mV, but no gain-calibration contract exists, so the
raw failures are not waived.

## Phase-resolved mechanism

The baseline `Vdiff=+0.8 V` result separates into approximately:

- `-11.692 mV` at the immediate `PHI` turn-off edge;
- `-0.335 mV` while the protected discharge path activates;
- approximately `+0.008 mV` subsequent hold drift.

For both resized finalists, the later discharge step and hold drift are
effectively zero, yet the immediate turn-off step remains `-10.298 mV` or
`-9.097 mV`. Strengthening `MN7/MN10` therefore cleans up the gate after the
error has already been sampled; it cannot remove the dominant edge event.

Single-ended confirmation supports the same conclusion. The extreme candidate
still spans about `+5.38 mV` held error at `VIN=0.05 V` to `-3.71 mV` at
`VIN=0.85 V`, rather than producing a removable common-mode-only shift.

## Reliability status

The reconstructed worst terminal difference remains about 1.787 V in every
candidate. Spectre continues to emit PDK SOA warnings on the charge-pump,
control, protected-discharge, and main-switch network. Resizing is neither a
reliability improvement nor foundry approval; the prior SOA blocker remains.

## Next topology target

The next bounded analysis should act before or at the immediate turn-off edge:

1. decouple boosted-path isolation from the existing internally generated
   `CTRL` so the transfer device can turn off under an independently controlled
   phase;
2. test a complementary dummy sampling device or equivalent charge-injection
   cancellation element and sweep its ratio;
3. evaluate bottom-plate sampling order in the actual differential CDAC
   context rather than only capacitors to ground;
4. retain phase-resolved measurements so an apparent hold improvement cannot
   hide acquisition, aperture, or SOA regressions.

Only a topology candidate that materially reduces the raw error should be
implemented in OA and then expanded to PVT.
