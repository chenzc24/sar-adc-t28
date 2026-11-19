# Clock latch load regression

The v3 clock latch uses an explicit MOM capacitor from QB to VSS. The static candidate uses the same inverter and three NAND gates with the same connections and omits the MOM. Both ADC tops retain CL_COMP_N, CL_COMP_P and CL_CMP_CLK. The FF cold control uses byte-identical stimulus, model deck, solver settings and measurements.

Four consecutive code centers (0, 255, 128, 127), 10 MS/s, including the first conversion after precharge. The fixture reads the word at 90 and 98 ns in each frame and compares it to the independent observer. The minimum read margin is from the eighth update to the 90 ns read. Pulse widths use the half-VDD crossings at the comparator clock pin.

| Clock latch | MOS | VDD (V) | Temperature (°C) | Frames passing all short checks | Min clock high (ns) | Min read margin (ns) | Max weighted CDAC error (LSB) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Without CQB | TT | 0.90 | 27 | 4/4 | 0.733 | 28.800 | 0.0083 |
| Without CQB | SS | 0.81 | -40 | 4/4 | 1.197 | 13.532 | 0.0004 |
| Without CQB | SS | 0.81 | 125 | 4/4 | 1.160 | 17.192 | 0.0067 |
| Without CQB | FF | 0.99 | -40 | 4/4 | 0.502 | 35.062 | 0.0156 |
| Without CQB | FF | 0.99 | 125 | 4/4 | 0.557 | 33.989 | 0.0296 |
| v3 with CQB | FF | 0.99 | -40 | 4/4 | 0.509 | 35.013 | 0.0158 |

The FF cold control isolates the change in reachable devices at XCLOCK. Netlist filenames and the latch master name also change. The 5 ps saved strobes limit resolution of very short pulses. All-terminal stress, extracted parasitics, supply ramp, mismatch and noise are outside this regression. Spectre model warnings, including CMI terminal warnings, are retained with each run.

[Run identities, per-frame codes, phase counts and latch threshold crossings](sar_clock_latch_cqb_short_20261119.json) · [Earlier loaded v3 measurements](sar_std_delay_20261119.md)
