# Verification Guide

For each conclusion, record input identity, corner, stimulus, model scope, measurement method, and coverage gaps. Evaluate function, static linearity, dynamic spectra, timing, and device terminal voltages within their respective tests.

In a TT short test, report the first frame and normal cycles separately. Check codes, sampling close edges, decision, write, update and capture counts, and settling. Use conversion boundaries for TT full-code DNL and endpoint INL. Record coherent bins, warm-up frames, and noise settings for FFT.

The TT module Monte Carlo measures the comparator threshold and MOM static bit weights over 200 local-mismatch samples. The closed-loop cold tests use the actual SAR, Bootstrap, and reference driver, with local mismatch applied only to the comparator and CDAC. Each corner has 50 samples and covers that selective boundary. Full-circuit mismatch and high-sigma yield require separate evidence.

Check closed-loop timeouts by frame, bit, and actual edge. Use a same-draw extended-hold control to isolate settling effects. Record reference timeouts, invalid draws, and monitoring latency separately. The SS 5115 q45 reference failure and q38 retest have distinct run identities.

Preserve original measurements and warnings. Bind reanalysis to a completed source under a new analysis-only ID. For a directory migration, check byte and subcircuit equivalence, then verify module packaging with one new TT short test. Keep previous results attributed to their original sources.

## Terminal-Voltage Engineering Acceptance

The project adopted the engineering limits from ADC-12b-100M Issue #136 and the `44f52bc` configuration on 2026-11-15. The upstream limits are presented without device or PDK qualification. A pass qualifies the project engineering screen. Foundry reliability and lifetime require their own evidence. Use the project's existing supply and timing specifications. [Engineering rule](../specs/soa_rule.yaml) · [Upstream Issue #136](https://github.com/many-question/ADC-12b-100M/issues/136)

For every thin-oxide MOS in every module, measure `|Vgs|`, `|Vgd|`, and `|Vds|` over the full transient, including standard-cell internals and startup. For a thin-oxide MOS capacitor, check its voltage across the two terminals. Each applicable device and terminal pair passes if either condition holds.

- The peak is **at most 1.1 V**.
- The peak is **at most 1.29 V**, and the total time strictly above 1.1 V is **at most 100 ps in every sliding 10 ns window**.

The 100 ps is the sum of all over-limit intervals in the window. The peak and duration caps are inclusive. Use the literal 1.29 V from the upstream YAML. The comment's expression `0.99 × 1.3` evaluates to 1.287 V.

Report thick-oxide 1.8 V devices and `Vgb/Vbs/Vbd` separately as diagnostics or unverified where applicable. Treat unrecognized device models as unverified. Keep the original PDK model warning thresholds, including 0.99 V for core devices and 1.98 V for 1.8 V devices. Report model warnings, the engineering verdict, and reliability qualification from their respective evidence.

Use native-time terminal waveforms with interpolated threshold crossings. Check time resolution against narrow peaks and 100 ps events. Record run and frozen netlist identity, rule version and digest, per-device and per-pair peaks, the maximum duration above the limit in a sliding window, and the worst event location. Use full waveforms for measurement. Mark the terminal voltage **unverified** when waveforms are missing, execution fails, resolution review is pending, only behavioral models are present, or any required corner is missing.

For existing simulations with sufficient waveforms, create an independent managed analysis-only verdict bound to the completed source. Preserve original functional evidence and results. Collect new managed waveforms when required internal nodes are absent. Use an explicit per-device SOA analyzer for this rule.

## Adoption and Verification of the Current Design

On 2026-11-20, the user adopted the single-edge SAR with registered per-bit delay taps and the 45 ns high / 55 ns low external clock. The adoption runs use foundry cell LPE and the extracted CDAC with its 510 switched terminals; the SAR inter-cell wiring is ideal. For each frame, `single_edge_lpe` checks the gain-adjusted code at the 90 and 98 ns reads, the signed TOP settling error against the nominal rails, each tap hand-off, register setup and hold, and the COMMIT pulse width. Settling must be at most 0.25 LSB, with a 0.125 LSB target. Repeat the terminal-voltage scan after layout.

The reset-OR adoption of 2026-11-15, the B analyzer, behavioral timing, historical FFT, full-code and Monte Carlo runs, and earlier D2 five-corner results qualify their own inputs. [Adoption report](../results/design/sar_single_edge_adoption_20261120.md) · [Reset-OR adoption record](../results/design/reset_data_or_adoption_20261115.json)
