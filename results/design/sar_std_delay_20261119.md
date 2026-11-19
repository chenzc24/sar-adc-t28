# SAR standard delay cells

Five active RC delays were replaced by 52 native T28 DEL cells and 28 input-qualification AND gates. Ten polysilicon resistors and 230 MOM delay units were removed. The tested v3 DUT includes one explicit MOM load, CQB, from the internal clock latch node QB to VSS. The cross-coupled NAND gates store the logic state. An early prototype used an explicit 5 fF load at this node (commit efea0db, docs/sar8_async_implementation.md). The 5 fF value describes that prototype. The v3 measurements include the MOM device and do not establish that it is required. [Delay circuit](../../design/xtor/clock/delays_std.scs) · [Controller](../../design/xtor/sar/reset_data_or_std_delay.scs) · [Measured data, source hashes and run IDs](sar_std_delay_20261119.json)

## Clock and controller

| Path | Native DEL cells in series | Old RC rise, ns | New rise, ns |
| --- | --- | ---: | ---: |
| Comparator valid | 200 | 0.151 | 0.155 |
| Write | 250 + 250 + 075 | 0.397 | 0.403 |
| CDAC quiet | 9 × 250 | 1.420 | 1.548 |
| Sampling enable | 10 × 250 | 1.696 | 1.713 |
| Idle to reference preset | 29 × 250 | 4.933 | 4.957 |

The TT inverter-loaded fixture measured these rise delays. The first trial produced four wrong words in six conversions. After calibration, RAW_D and QUIET_D used buffers at the receiver and retained request qualification at their final taps. The revised controller produced all six expected words and 48 comparison/update pairs. The inactive CAPTURE, BBM and STEP helpers also have standard-cell implementations.

## Closed-loop schematic, 10 MS/s

Real sampler, CDAC, reference switches, comparator and SAR. The external clock gives 40 ns high per 100 ns period. The reference sources stay at 0 and 0.9 V throughout the supply sweep. Passive sections are TT. Spectre X MX uses 10 ps maximum step and 5 ps saved strobes for code, phase and settling measurements.

| MOS | °C | VDD, V | Exact words | Last update to read, ns (min) | Update to next compare, ns (min) | Receiver valid to write, ps (min) | Weighted bottom error, LSB (max) | Sample-close error, LSB (max abs) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| TT | 27 | 0.90 | 18/18 | 28.733 | 1.729 | 202.9 | 0.0083 | 0.0052 |
| SSC | -40 | 0.81 | 18/18 | 13.399 | 2.871 | 327.7 | 0.0004 | 0.0467 |
| SSH | 125 | 0.81 | 18/18 | 17.088 | 2.783 | 321.4 | 0.0067 | 0.0030 |
| FFC | -40 | 0.99 | 18/18 | 34.974 | 1.171 | 139.5 | 0.0158 | 0.0100 |
| FFH | 125 | 0.99 | 18/18 | 33.907 | 1.305 | 155.3 | 0.0287 | 0.0072 |

Read margin runs from the eighth update to the 90 ns read within the fixture frame. The 98 ns read checks retention. The weighted error compares bottom plates to the instantaneous reference rails at each decision. The 0.25 LSB screen also applies to differential sampling error at closing.

At FF cold the shortest QUIET low gap was 0.547 ns. The standalone FF-cold QUIET chain recovered at the 0.3 ns test point. All three bit-level paths produced one qualified rise per bit in the five PVT tests. The sample and guard paths produced one rise per frame. A 40 ps pulse was rejected by every active helper at TT, FF cold and SS cold.

Post-startup TT mean delivered power was 47.68 µW at VDD, 13.76 µW at VREFP and 0.0005 µW at the external clock for these input words.

## Continuous operation and fixed-corner mismatch

The SSC continuous test exercised 16 endpoint, midscale, alternating-bit and repeated words, then 48 seeded pseudo-random words. Exact matches 64/64, worst read margin 13.110 ns and maximum weighted bottom error 0.0004 LSB.

| Corner | Seed | Exact nominal words | Timing | Read margin, ns (min) | Nominal code delta (range) | Conservative settling bound, LSB (max) |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| SSC | 15206 | 1/8 | pass | 18.775 | -2 to +0 | 0.0008 |
| SSC | 15212 | 1/8 | pass | 18.387 | +0 to +3 | 0.0007 |
| FFC | 15303 | 1/8 | pass | 33.369 | +0 to +3 | 0.0289 |
| FFC | 15308 | 1/8 | pass | 33.453 | +0 to +2 | 0.0303 |

At SS cold, the largest rejected and smallest accepted trial-bit TOPP−TOPN voltages at the comparison edge were -2.67 and 2.54 mV in the deterministic short test. They were +11.61 and +17.31 mV in seed 15206. This bounds the effective decision threshold for these data. Separating comparator offset from dynamic and other mismatch effects requires a separate experiment.

These draws apply local mismatch throughout the DUT at a fixed process corner. The saved parameters have nonzero entries in all five delay paths, comparator and CDAC. A difference from a nominal code center can include comparator offset and CDAC mismatch. Four draws test operation and leave yield undetermined.

## Two-frame terminal screen

| Condition | Failing pairs | Max absolute terminal voltage, V | Worst duration above 1.10 V in 10 ns, ps |
| --- | ---: | ---: | ---: |
| FF cold, first receiver | 2 | 1.1949 | 457.8 |
| FF cold, buffered receiver | 0 | 1.1949 | 75.0 |
| FF hot, buffered receiver | 0 | 1.1462 | 74.8 |

The full-device measurements use native time points from startup through the two endpoint frames 0 and 255. The final runs checked 9,837 thin-oxide GS/GD/DS pairs with a maximum 10 ps step and interpolated crossings. Limits are 1.29 V peak and 100 ps per 10 ns above 1.10 V. Model warnings remain in the logs. Finer-step convergence, thick-oxide qualification and foundry reliability signoff remain open. [Project rule](../../specs/soa_rule.yaml)

Full-code linearity, FFT, routed area and extracted timing belong to separate measurements. The previous RC layout remains bound to its original electrical sources.

The layout checker flags the current DEL schematic against the previous RC floorplan. Its original [electrical manifest](../../design/frozen/quiet8p5_20261118/manifest.json) and [DUT entry](../../design/frozen/quiet8p5_20261118/dut.scs) remain available for reproducing the RC checks.
