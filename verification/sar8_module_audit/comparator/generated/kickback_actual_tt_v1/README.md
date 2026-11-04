# Existing actual-bit intervals: local TT proposal

Run proposal: `sar8audit-comp-actual-tt-v1`. No remote submission, Spectre result
or baseline adoption is claimed.

Core scope: **固定实测时钟脉冲下的短复位/接收诊断** (short-reset/receiver
diagnostics under fixed measured clock-pulse intervals).

## Timing source

Frozen managed run `sar8fix-loaded-both-rx2-tt`, recipe
`ba8432cd1e6678c1c00f7888982b8511e29424b34c7981159be511fa3a8d3557`.
Its DUT SHA is the same frozen N4/rx2 source used by the comparator fixtures.
Source simulation/analysis are complete, with native PASS/zero-error footer.
`timing_source.json` binds the collected native event file by SHA and lists all
14 adjacent pairs from two recorded TT frames. The source has its original
warnings; its timing is evidence, not a newly qualified baseline.

The shortest **rise-to-rise** pair is second frame bit6→bit5:

| Native0.5VDD clock event | Absolute source time (ns) |
| --- | ---: |
| First rise | 147.670965402 |
| First fall | 148.850322134 |
| Second rise | 151.626808341 |
| Second fall | 152.839509730 |

| Same-pair interval | ns |
| --- | ---: |
| Rise to rise | 3.955842938 |
| First high | 1.179356732 |
| Low: fall to next rise | 2.776486207 |
| Second high | 1.212701389 |

The minimum low interval alone is2.776221297ns from a different bit1→bit0 pair.
It is recorded separately and is not spliced into this sequence. These minima
cover the observed two TT frames, not all inputs or PVT.

## Fixture and measurement

The selected half-level sequence is translated so its first rise occurs at the
existing diagnostic20.05ns. First/second falling ramps start at21.179356732ns
and25.168544327ns; the second rising ramp starts at23.955842938ns.
The **original0.1ns ideal PWL ramps remain**. This is measured0.5VDD interval
replay, not a replay of the complete native voltage/slew waveform. Fully-zero
clock time in this ideal-edge fixture is2.676486207ns; do not relabel it as a
measured native full-rail recovery interval.

Only the first two clock pulses change electrically from hold2. Both use the
same+0.25LSB target and the charge initialized before18.1ns, without an intervening
input clamp. The later four original +/-0.25LSB long-interval controls and all
other sources remain unchanged; negative short-interval behavior is not yet
claimed. Frozen MOS, MOMs, original sample guard/reset and actual ADC external
sampling contract are untouched. This local time translation does not redefine
the ADC sampling window or closing edge.

The new measurement copy uses each explicit fall-start rather than a hardcoded
12ns high window. It measures pre-comparison differential/CM residue, input-node
motion, gate charge, KCL, reset levels, resolution before reset and receiver
write phase. `missing_write_before_reset` cannot pass via an empty correctness
list; clock-fall and unassigned writes remain visible. A retained D0 value alone
is not evidence of a new accepted decision. Resource budgets and81 exact-case
save symbols are unchanged.

## Interpretation limits

The source pair used approximately−362/−138mV input residues and about0.61/0.64ns
write delays. Those voltage numbers are historical compact estimates, not the
native timing extraction. The present fixed residual is only+1.758mV, whose
previous long-window write delay was about1.608ns. The borrowed1.179/1.213ns high
windows may therefore reset this small-input comparator before it finishes.
That is a valid conditional forced-clock observation, not automatic proof that
the original asynchronous ADC actually applies those short windows to a small
residual. Its real DEC/write-driven reset would depend on the changing input.

Before interpreting comparison2's retained differential/CM residue, inspect
comparison1's `missing_write_before_reset`,
`nominal_polarity_written_before_reset` and `raw_resolution`. If comparison1 did
not complete its decision/write before reset, the measured trajectory is recovery
from an interrupted evaluation, not the history of a valid first SAR decision.
Do not describe such a result as two completed actual conversions.

Real SAR bit updates also switch CDAC references and change differential/CM
inputs. This fixture keeps bottom rails ideal and fixed, cuts clock/DEC feedback,
holds token0 and retains the existing diagnostic register loading. It cannot
establish the complete SAR conversion result, true bit-settling margin, noise,
yield, PVT or lifetime qualification. All native warnings must be retained.

Three focused local checks passed: the entire minimum native pair is preserved,
hardware/other sources/targets/budgets are unchanged, and late/absent decisions,
stale D0 and out-of-window writes are reported correctly in synthetic data.
No new simulation or parameter sweep was run by this session.
