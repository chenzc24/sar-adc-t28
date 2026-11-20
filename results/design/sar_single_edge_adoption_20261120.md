# Single-edge SAR adoption

On 2026-11-20 the user adopted the single-edge SAR with registered per-bit delay taps as the current design, `sar8_single_edge_bitwise_v1`, together with a 45 ns high / 55 ns low external clock. Superseded design versions were removed from the tree; commit `c46d9d6` is the last one that contains them. Frozen B remains the baseline of the behavioral models and the B regression. [Record with file digests, run identities and measurements](sar_single_edge_adoption_20261120.json)

## Design

[`design/dut.scs`](../../design/dut.scs) includes the bootstrap, CDAC and comparator netlists unchanged, the [SAR](../../design/xtor/sar/single_edge.scs), the [reference word](../../design/xtor/reference/single_edge_d2.scs) and the [top](../../design/top/adc_top.scs). Logic and delays use 15 native standard-cell types without wrappers.

- COMMIT is the only register clock. The next trial word is precomputed from CODE, so DATA passes three gates before the registers.
- After each commit the comparator clock waits for a DEL250 chain. The tap depends on the bit being compared: 11, 9, 7, 6, 5 and 4 stages for bits 6, 5, 4, 3 and 2–0.
- Five sticky registers select the taps. Each is set by the commit before the tap is first used and cleared by sampling, so within a frame a tap only becomes shorter.
- The first comparison does not wait for the chain. Tracking precharges every tap high, and the compare waits only until the bootstrap gates are off (two DEL250 cells with an AN2 qualifier).
- A two-flop Johnson counter generates the delay phase, PHASE = PHA XOR PHB.
- The bootstrap enable rises after a DEL200 qualifier. PRESET = DONE OR SEQ_SAMPLE, so the 29-stage idle guard is gone.
- Terminal-voltage measures: the write AND has VALID on its inner input. The sticky-select ORs and the reference MSB OR use INV+INV+ND2.

## Verification of the adopted netlist

All runs use foundry cell LPE and the extracted CDAC with 510 switched terminals. The SAR inter-cell wiring is ideal.

| Run | Condition | Result |
| --- | --- | --- |
| `sar8-sebit-ffc-cw-scan-b` | FF cold, CBEST_T cells, CWORST_T CDAC | 4/4 frames; worst signed settling 0.114 LSB |
| `sar8-sebit-ffc-cw-extreme-b` | Same, full-scale and low-to-mid steps | 8/8 frames; 0.114 LSB |
| `sar8-sebit-ssc-cw-verify-b` | SS cold, CWORST_T cells and CDAC | 8/8 frames; **7.59 ns** to the 90 ns read; sampling residual 0.074 LSB |
| `sar8-sebit-tt-nom-verify-b` | TT, nominal CDAC | 8/8 frames; 24.9 ns read margin |
| `sar8-sebit-ffc-nom-restart-b` | FF cold, accepted sample during conversion | Aborts after two writes, then two complete conversions read 83 and 172 |
| `sar8-minref-soa-ffc-song-bitwise-b` | FF cold 0.99 V, all MOS terminals | 0 rule violations in 1902 checked devices; numeric pass pending resolution review |

Every frame reads its gain-adjusted expected code at 90 and 98 ns. Every tap hand-off happens with both multiplexer inputs at the same rail, with at least 441 ps before the select switches. The worst register setup and hold slacks are 156.5 and 33.6 ps. The shortest COMMIT high pulse is 148 ps, against a 15.7 ps limit.

The settling target is the signed TOP error from all 510 plates against the nominal rails: at most 0.25 LSB, with a 0.125 LSB target. A run with every tap at 24 stages served as a fully settled reference on the predecessor netlist; there the worst measured error was 0.124 LSB, against a 0.122 LSB estimate. Before the terminal-voltage changes, the FF-cold scan found five violations, from 1.105 to 1.124 V lasting 101–310 ps.

## Predecessor netlist

These runs differ from the adopted netlist only in the four terminal-voltage changes. They all passed:

- SS hot and FF hot (nominal CDAC);
- the 63/64 boundary case and the extreme history at the cold corners (CWORST_T CDAC);
- two restart cases;
- three local-mismatch seeds each at FF cold and SS cold.

## Limits

- The layout is not drawn. About 5 ns of the SS-cold margin is reserved for routing. The previous routed SAR lost about 6 % of its conversion time to wiring.
- FF hot reads 0.165 LSB on the signed estimate. At most 0.03 LSB of that is plate settling. The rest is a static 0.3–0.9 mV offset on the reference pins from switch leakage through the 50 Ω source, so a longer window would not help.
- At the first comparison, sampling-switch charge injection offsets TOP by up to about 0.13 LSB. The offset is roughly linear in the input.
- Comparator mismatch shifted the six seeds by −1 to +3 codes; the offset is budgeted separately.
- The pulse widths of the LHCNDQD1 clock latch are recorded but not yet compared with its databook limits.
- The terminal-voltage scan must be repeated after layout.
