# T28 StrongARM noise, mismatch, and interface verification screen

## Goal and boundaries

Characterize the first-pass `SAR_ADC_T28/sar_strongarm_t28` transistor-level comparator beyond nominal deterministic delay. Measure input-referred random-decision behavior with Spectre transient noise, test whether foundry mismatch statistics are actually active and screen offset/error yield, and evaluate realistic input/output loading plus selected PVT conditions. This is a pre-layout screening target, not a sign-off or production-cell freeze.

## Starting state and ownership

At start `main` is eight commits ahead of `origin/main`. Unrelated dirty files belong to an ongoing bottom-plate clamp-width screen (`scripts/characterization/{analyze,run}_bootstrap_bottom_plate_eval.py`, its new config, plan, and creator). They are not dependencies of this target and remain untouched. The existing StrongARM OA cells are saved, zero-marker, and read-only for this target. `SAR_ADC_T28` is bound to `tsmcN28`; Bridge 0.8.0 `t28_io`, CIW on `thu-wei`, and Spectre 21.1 are healthy. Other editing windows are outside this target.

Local owned files: this plan; new `config/strongarm_t28_verification.yaml`; new `scripts/characterization/verify_strongarm_t28.py`; new `docs/strongarm_t28_verification.md`; one bounded `plan/log.md` entry. All generated OA exports, derived decks, PSF, logs, and metrics belong under ignored `output/strongarm_t28_verification/`. No remote OA cellview is owned or modified. The StrongARM DUT/testbench, PDK, all other OA cells, and existing characterization scripts are read-only dependencies.

## Source and assumptions

- Automatically re-export `SAR_ADC_T28/tb_sar_strongarm_t28/schematic`, record hash, and assert exact 11-PDK-MOS DUT connectivity. The exported DUT subcircuit is preserved byte-for-byte in analysis decks. Changes to top-level stimuli, model-section selection, and analysis statements are explicitly recorded.
- Base condition: 0.9 V, 27 °C, TT, 0.45-V input common mode, 200-MHz clock, 20-ps edges, nominal 5-fF output loads. Comparator decision window is 1.5 ns. Initial input-referred random-noise target is 0.316 mV RMS, and the allocated systematic offset guardrail is 0.439 mV. These are top-down allocations, not PDK facts.
- Dynamic-latch noise cannot be inferred from a static AC noise plot. Use transient noise with declared bandwidth and seeds, repeated reset/decision cycles, binomial confidence intervals, and a probit/threshold interpretation only where data support it. Keep deterministic and noise-enabled runs separate.
- Monte Carlo counts as mismatch evidence only if the PDK's statistical model section/parameters are active and the run varies device values or decisions. A nominal `montecarlo` wrapper with inert statistics must be called inconclusive. Report sample size and confidence rather than claiming tail yield from a small screen.
- Model the held CDAC interface with a finite input capacitance and weak bias path so kickback is observable; distinguish a simplified fixture from integration with the actual CDAC/sampling switch. Sweep output load and selected PVT corners without modifying the DUT.

## Execution and validation

1. Verify the exact OA revision, export, check markers, and establish deterministic ±0.439-mV reference cases.
2. Smoke-test transient-noise syntax/PSD settings and verify the stochastic waveform/decision sequence actually changes with seed. Run a bounded number of cycles at positive and negative input overdrive; estimate error probabilities and an input-referred noise range with stated confidence. If the sample count is insufficient to certify 0.316 mV, report a bound or inconclusive result.
3. Smoke-test mismatch-only Monte Carlo. Inspect statistical activation, run a bounded reproducible seed set, and measure near-threshold decision outcomes/offset bracket if supported. Record if the foundry deck does not expose usable mismatch.
4. Run selected SS/TT/FF, supply/temperature, output-load, and finite-input-capacitor cases. Measure signed decision time, reset, input-node kickback, and supply energy where saved waveforms permit. Flag any case exceeding 1.5 ns or 0.439-mV interface guardrail; do not call the guardrail a sign-off criterion without a full CDAC integration.
   Reject a kickback fixture if its actual pre-edge differential input differs materially from the requested bias. The first 1-TΩ hold path is known to fail this check because simulator `gmin` loads the node; retain its output as invalid-fixture evidence and rerun with a 1-GΩ path (RC still far above the 5-ns bit period).
5. Retain all failed decks/logs, check Spectre `result.ok`, PSF parsing, case counts and source hash; compile Python, parse YAML, review only owned changes, `git diff --check`, and OA readback. Write a factual report with pass/fail/inconclusive classifications.

## Artifacts and commit policy

Expected artifacts are `output/strongarm_t28_verification/{netlist,decks,spectre,summary.json,...}` and the tracked concise report. Commit only owned files as `test: screen T28 StrongARM noise mismatch and loading`. Do not push without user request.

## Outcome and interpretation

The exported 11-MOS DUT hash matched the first-pass baseline; no OA cellview was changed. The initial `TTMacro_MOS_MOSCAP` mismatch run was invalid despite nonzero statistical-variable counts: its output waveforms were numerically identical because the model section suppressed local mismatch. The corrected `TTGlobalCorner_LocalMC_MOS_MOSCAP` 32-pair screen produced visibly different waveforms and matching sampled-parameter hashes across input polarities. Noise and local-mismatch budgets both failed in the first-pass sizing. Deterministic timing passed at four selected PVT/load points, but FF/0.99-V operation produced terminal-voltage limit warnings. The 1-GΩ input hold fixture passed pre-edge bias validity; its 50-fF case exceeded the provisional kickback guardrail. The full evidence and limits are recorded in `docs/strongarm_t28_verification.md`.
