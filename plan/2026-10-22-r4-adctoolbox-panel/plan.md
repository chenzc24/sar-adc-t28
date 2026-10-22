# R4 ADCToolbox diagnostic panel

Status: complete.

## Goal and boundaries

Generate a reproducible 12-panel ADCToolbox analysis of the existing verified
1024 R4 sine output codes, and explain metrics and diagnostic limitations.
No simulation, circuit changes, calibration, or baseline replacement.

Dirty state: user Obsidian edits/moves/images and untracked 10-bit dual-rail
work are unrelated and preserved. Branch starts ahead of origin by two commits.

Owned local paths:
- this plan
- scripts/sar8_r4_performance/toolbox_panel.py
- verification/sar8_r4_performance/toolbox_panel.json
- docs/sar8_r4_adctoolbox_panel.md
- docs/figures/sar8_r4_performance/adctoolbox_panel.png
- plan/log.md (append only)

Remote OA owned objects: none. All OA, PDK, frozen netlists, existing performance
results, raw runs, Obsidian and other experiments are read-only.

## Method and validation

1. Inspect installed ADCToolbox 0.9.1 dashboard and calculation sources.
2. Use its 12-tool dashboard structure with explicit coherent FFT and full-scale
   settings; use library numerical analyses and readable scientific plotting.
3. Record source hash, options, metrics, and distinction between fitted residual
   diagnostics and static INL/DNL or physical noise/jitter measurements.
4. Assert 1024 codes; compare FFT to prior SNDR/SFDR, check Parseval and LSB
   scaling, compile script and execute, inspect final image, scoped diff check.
5. Explain nominal performance separately from unresolved CMI stress/noise/PVT.

Deliver figure, JSON, concise Chinese report; update plan/log and commit only
owned files as `analysis: add R4 ADCToolbox diagnostic panel`. Do not push.

## Validation outcome

- Script compiled and ran twice; 1024 codes, prior SNDR/SFDR and direct SNR
  agree within 1e-8 dB; Parseval, LSB conversion and reconstruction pass.
- SNDR 48.728620 dB, ENOB 7.802096 bit, SFDR 65.592698 dB;
  H2–H5-excluded SNR 48.799143 dB, THD -66.658370 dBc.
- Residual RMS 2.075414 mV (0.295170 LSB); ideal uniform quantization
  reference 2.029747 mV. No physical noise attribution or stress qualification.
- Final 3740×2380 panel visually inspected after fixing below-floor polar
  components and renaming an over-interpretable memory annotation.
- Source hash/options and six numerical assertions saved. Scoped diff checked;
  user edits unchanged. Local commit only; no simulation, OA mutation or push.
