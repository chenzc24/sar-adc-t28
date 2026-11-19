# Standalone Block Tests

The block registry is the source for stimulus, loads, measurements, diagnostic limits, and coverage gaps. Each module's `acceptance.scs` is its testbench source. [Block test registry](../../specs/block_tests.json)

| Module | Testbench | Measurements |
| --- | --- | --- |
| Bootstrap | [bootstrap/acceptance.scs](bootstrap/acceptance.scs) | Normal 60 ns low and 40 ns high clock, first and subsequent sampling error, hold drift, 50 Ω input, and native MOM load |
| CDAC | [cdac/acceptance.scs](cdac/acceptance.scs) | Effective weights from unit to MSB, settling within a quarter LSB, full-scale reversals, hold, and 50 Ω / 4 pF references |
| Comparator | [comparator/acceptance.scs](comparator/acceptance.scs) | Positive and negative decisions at several amplitudes, delay, reset, native output MOM and receiving-gate loads, and differential kickback with floating MOM inputs |
| SAR | [sar/acceptance.scs](sar/acceptance.scs) | Six low, mid, and high codes, first frame, eight decisions and updates, conversion time, and cancellation on the next sample when the comparator is forced to stall. The transistor SAR runs in an electrical Verilog-A environment. |
| Reference control | [reference/acceptance.scs](reference/acceptance.scs) | Preset, two captures, stored word, and gate threshold non-overlap with the actual CDAC and switch gate loads |
| RC and clear delays | [clock/acceptance.scs](clock/acceptance.scs) | Rise and fall delays, pulse widths, and missing edges of exported delay and edge helpers with native receiving-gate loads |

Use the existing native comparator offset and CDAC static bit-weight Monte Carlo inputs and registrations. [Comparator MC](comparator/test.scs) · [CDAC MC](cdac/test.scs)

```powershell
python -m tools.saradc block list
python -m tools.saradc block prepare --module comparator --run-id sar8-comp-char-v1
python -m tools.saradc block sim --run-id NEW_ID
python -m tools.saradc block follow --run-id NEW_ID
python -m tools.saradc block sim --module reference --view behavioral --view reference=xtor --candidate reference=b --run-id NEW_ID
```

Omit `--module` to run all six cases or repeat it to select several. `prepare` packages inputs. `sim` packages and registers once. `follow` continues and collects the existing run. Use each run ID for its original registered inputs.

Each package puts `test.scs`, module fixtures, selection settings, source digests, and a managed recipe in `work/blocks/ID/`. The analyzer checks completeness of saved signals and streams the waveform measurements. [Analyzer](../../tools/saradc/measure/analyze_blocks.py) · [Block results](../../results/blocks/README.md)

For an analyzer fix, run analysis-only against the completed simulation.

```powershell
python -m tools.saradc block reanalyze --run-id NEW_ANALYSIS_ID --source-run COMPLETED_SIM_ID
python -m tools.saradc block follow --run-id NEW_ANALYSIS_ID
```

Report `pass_functional` and `diagnostic_screens_pass` independently. `pass_validation` requires both. Preserve small-signal misses, gate overlap, and unallocated timing limits. Take electrical verdicts from measurements. Measure CDAC settling against the finite, stability-checked tail of the waveform.

These cases qualify the conditions in their recipes. Full PVT, local mismatch, native noise probabilities, MOS conduction-current non-overlap, reliability, and PEX require separate evidence. [Verilog-A load and delay approximations and statistical scope](../../design/behav/README.md)
