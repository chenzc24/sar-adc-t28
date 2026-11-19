# Standalone Block and Mixed-Hierarchy Verification

The ten physical design source files matched byte for byte when the block simulations finished. The summary and local validation records preserve their identities. RNL drawing annotations were later added to eight active sources. Removing the annotations recovers the original bytes. Frozen B and the original receipts retain their recorded provenance. [Testbench guide](../../tb/blocks/README.md) · [Summary](summary.json) · [54 local checks](local_validation.json) · [RNL manifest](../../design/rnl/manifest.json)

| Run | Scope | Verdict |
| --- | --- | --- |
| [Transistor blocks](sar8-blocks-tt-v1-analysis-v3/result.json) · [Provenance](sar8-blocks-tt-v1-analysis-v3/provenance.json) | Six standalone TT blocks with actual source impedance, MOM, receiving gates, and CDAC gate loading | Function passed. The reference MSB gate-threshold overlap diagnostic failed. |
| [Verilog-A blocks](sar8-blocks-va-v1/result.json) · [Provenance](sar8-blocks-va-v1/provenance.json) | Matching standalone tests with the declared electrical Verilog-A DUTs and recorded environment loads | Function and diagnostics passed for the behavioral scope. |
| [Mixed-hierarchy ADC](sar8-mixed-rtcmp-va-v1/result.json) · [Provenance](sar8-mixed-rtcmp-va-v1/provenance.json) | Transistor sampler, CDAC, and SAR with Verilog-A comparator, reference, and RC delays. Original ten-frame TT stimulus. | Codes, eight decisions and updates, and public-interface timing passed. |
| [SAR stall and restart](sar8-sar-reset-tt-v1/result.json) · [Provenance](sar8-sar-reset-tt-v1/provenance.json) | Six normal frames and a second native SAR with a forced comparator stall | All six normal codes passed. All six forced stalls stopped at bit 7 without a spurious update and cleared on the next sample. |

Representative transistor-level TT measurements follow.

- Sampling error after close was −0.787 mV on the first frame and −1.061 mV on later frames. The fixture load is 256 native MOM units.
- All ten comparator decisions from ±100 mV to ±0.1 mV were valid. Maximum measured delay was about 0.365 ns. With floating inputs, differential kickback peaked at about 35.8 µV and left about −0.293 µV at the end. The common-mode peak was about 236.5 µV. Noise and mismatch were disabled.
- All eight CDAC weights were positive and had stable tails. The quarter-LSB settling measurements refer to the finite tail, with per-bit timing limits still to be allocated.
- The reference had zero stored-word errors. Its two MSB sides had about 12.86 ps cumulative threshold overlap at half-supply, first occurring near 210.366 ns. The diagnostic uses waveform thresholds. Time-step convergence and MOS conduction-current non-overlap remain open.
- The delay chain records rising delay, fast falling clear delay, and pulse width separately. The six normal SAR frames took about 29.16 ns. A null `gate_settle_s` records a same-word update whose gate voltage stayed inside the measurement band.

Bind each result to its actual inputs and record function, diagnostics, corner, Verilog-A substitutions, and reliability at their tested scope. See each run's `warnings.txt` for native CMI terminal-voltage, SFE, Spectre numerical, and Verilog-A compilation warnings. The server retains complete logs and large waveforms. See the provenance receipts for digests and collection paths.

The initial simulation completed and analysis failed on a Python 2.7 relative import on the server. A1, A2, and A3 are analysis-only runs against that completed source. They fixed imports, separated function from diagnostics, and added kickback peaks and gate settling. A1 retains the earlier, broader summary verdict. A3 is the current verdict. [Initial failure](initial_failure.json)

Use the results index for native comparator and CDAC 200-seed statistics, PVT, and ADC FFT. The runs here cover the configurations listed above. [Results index](../README.md)
