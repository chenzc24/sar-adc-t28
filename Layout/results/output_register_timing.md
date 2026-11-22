# Output Register Timing

2026-11-22, chenzc24/sar-adc-t28#12. Timing check of the chip output register `sar8_out_reg` (XOREG; `design/chip/output_register.scs`: DEL250D1 -> DFQD1 -> BUFFD4 per bit, every CP on SAMPLE_CORE without a clock buffer) on the Stage 2 all-extracted ADC. [Record with run identities, deck digests and per-edge values](output_register_timing.json) · [Chip objects](chip_objects.md)

## Bench

`Layout/tools/simulation/prepare_output_register.py` builds the deck from `prepare_all_extracted` (every frozen block extraction at the paired interconnect corner; all inputs byte-identical to the Stage 2 runs `sar8-allx-ssc-verify-a` / `sar8-allx-ffh-verify-a` except `context.json`). It adds the register on the ADC's D0-D7 with CK on the ADC's SAMPLE node, DVDD as its own source at the corner supply, and 150 fF on each Q. The stop time moves to 870 ns so the 860 ns edge captures frame 7. `Layout/tools/analysis/measure_output_register.py` runs as a managed analysis job on the native waveform: capture per edge, setup and hold at the DFQD1 D pin, hold at the ADC outputs (the margin without the delay cell), clock-to-Q at 150 fF, scored against the DFQD1 setup/hold tables of the run's corner from the foundry CCS archive at the measured slews.

## Results

| | SS cold (0.81 V, -40 C) | FF hot (0.99 V, 125 C) |
| --- | --- | --- |
| Runs (thu-wei) | `sar8-oreg-ssc-a`, `-timing` | `sar8-oreg-ffh-d`, `-timing` |
| ADC code check | all pass, 8/8 frames, read margin 7.76 ns | codes right in 8/8 frames, read margin 30.08 ns; settling target fails in frames 2 and 7 (0.162 LSB against 0.15), as in Stage 2 |
| Capture | 7/7 scored edges: Q word = ADC word at the edge = decided code, frames 1-7; no Q glitch | 7/7, the same codes; no Q glitch |
| Worst setup slack at the flop D pin | 18.31 ns, bit 0 | 40.93 ns, bit 0 |
| Worst hold slack at the flop D pin | 1.18 ns, bit 6 | 0.50 ns, bit 6 |
| Worst hold slack at the ADC outputs (no delay cell) | 0.70 ns, bit 6 | 0.30 ns, bit 6 |
| CK to Q at 150 fF | 174-192 ps (CK to flop output 77-96 ps); Q 10-90 % up to 165 ps | 87-97 ps (34-42 ps); Q 10-90 % up to 103 ps |

The setup and hold slacks are against the DFQD1 setup/hold tables of each corner at the measured slews.

Both runs match Stage 2 without the register (`sar8-allx-ssc-verify-a` / `sar8-allx-ffh-verify-a`: the same eight codes, read margins 7.77 / 30.08 ns, the same FF-hot settling result 0.162 LSB). So the delay-cell inputs add no meaningful load to D0-D7. FF hot is the hold-critical corner: the SAR clears its outputs 0.31 ns after the edge there, and the delay cell lifts the hold slack from 0.30 to 0.50 ns.

FF hot: the first attempts on thu-song (`ffh-b`, `ffh-c`) never got past the initial DC solve within their memory reservations; `ffh-b` was stopped by the runner (aggregate RSS) and `ffh-c` cancelled to move to thu-wei. `ffh-d` (6 GiB) passed the DC solve and ran 160 min at 4.0 GB peak.

## Limitations

The record lists them in full: ideal SAMPLE source and CK route, ideal wiring between the ADC and the register, the register cells as foundry cell LPE without top-level extraction, DVDD ideal and at the ADC supply, a lumped 150 fF Q load without the PRUW08SDGZ I-pin load, two deterministic corners without mismatch or noise. The register has no reset, so its word before the first SAMPLE rising edge is undefined (the warm-up edges are not scored).
