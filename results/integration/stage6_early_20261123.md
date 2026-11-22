# Stage 6 early pass: extracted top-level wiring of the routed core

Early Stage 6 of the [top-level integration plan](https://github.com/chenzc24/sar-adc-t28/issues/12), run 2026-11-22 to 2026-11-23 on the routed, unfilled core with the Stage 2 Bootstrap core. It tests what stays valid when the Bootstrap and the fill change: the extracted top-level routing, the Stage 1 reference and package network at the drawn values, the comparator CLK-coupling offset and the read margin. Every Stage 6 check passes at SS cold and FF hot. The Bootstrap gate screen with the routed CMP_CLK is 0.118 V at SS cold, over the 0.1 V screen; the revised Bootstrap is being qualified against it. [Measurements, run identities and digests](stage6_early_20261123.json) · [Record spec](stage6_early_20261123.spec.json) · [Deck entry](../../Layout/tools/simulation/prepare_stage6.py) · [Record builder](../../Layout/tools/analysis/stage6_summary.py)

## Deck

- **Core wiring.** `adc-core-guard-wire-xtr2`: a Calibre xRC extraction of the branch-labelled guard stream `adc-core-guard-g1-chk` (`layout_route_guard`) with the five block masters as xcells ([launcher](../../Layout/tools/physical/launch_toplevel_wiring.py), [driver](../../Layout/tools/physical/toplevel_wiring_xcell.py)). Its 34 top-level nets keep their RC and their mutual and block coupling and end on one node per block pin; the deck binds the frozen block extractions there. This replaces the planned-length route RC and the three `CL_*` model loads.
- **Why per-net wiring, not the flat core extraction.** The flat extraction `adc-core-full-p2h-xtr` has no coordinates on its R/C elements, so routes cannot be cut out of it. It exists only at typical RC, and it would lose the corner block extractions and the probe maps (SAR source probes, the 510 CDAC plate terminals).
- **Route RC is typical at both corners** (labelled). The blocks use their paired corner extractions: CWORST_T at SS cold, CBEST_T at FF hot, with `--corner-bootstrap` semantics for the Bootstrap (`boot-core-20261121-cworst-t` / `-cbest-t`).
- **System model.** `Layout/specs/constraints.json` `stage6_supply_model` replaces the 50 Ω / 4 pF reference fixture:
  - board source and bypass;
  - two bonds and pads per reference rail;
  - one bond per supply branch (analog, pair, SAR), the planned pad bulk with ESR, and the 9 × 9 ring feed at 125 °C rcworst;
  - CREF 6.23 pF and RREF at the drawn 17.2 Ω pin-to-rail-end.

  Ideal: the VIN and SAMPLE sources at the core pins, the 5 fF D-output loads, board ground, and the shared TACVDD/TACVSS coupling, which is not modelled.
- **Comparator offset fixture.** [prepare_stage6_offset.py](../../Layout/tools/simulation/prepare_stage6_offset.py) bisects the extracted comparator's trip point with the wiring extraction's CMP_CLK/COMP_P/COMP_N coupling in three variants: as extracted, made symmetric, or removed.

## Results

| Corner | Run | Codes ±1 / events | Residual at close (LSB) | Plate settling, signed / weighted bound (LSB) | Read margin (ns) | Bootstrap gate screen (V) |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| SS cold | `sar8-s6e-ssc-verify-c` | pass / 8/8 | 0.060 | 0.008 / 0.008 | 9.11 | **0.118** |
| SS cold | `sar8-s6e-ssc-extreme-a` | pass / 8/8 | 0.062 | 0.007 / 0.008 | 9.26 | **0.119** |
| SS cold | `sar8-s6e-ssc-carry-a` | pass / 8/8 | 0.000 | 0.004 / 0.006 | 9.26 | < 0 |
| FF hot | `sar8-s6e-ffh-verify-a` | pass / 8/8 | 0.007 | 0.077 / 0.149 | 30.32 | 0.002 |
| FF hot | `sar8-s6e-ffh-extreme-a` | pass / 8/8 | 0.007 | 0.075 / 0.148 | 30.33 | 0.002 |
| FF hot | `sar8-s6e-ffh-carry-a` | pass / 8/8 | 0.000 | 0.033 / 0.148 | 30.33 | < 0 |

- **Limits** (Stage 6 column of #12): codes within the gain-corrected target ±1, residual and plate settling ≤ 0.25 LSB, read margin > 1 ns, 8 compares and updates per frame, restart passes.
- **Restart** passes at both corners (`sar8-s6e-{ssc,ffh}-restart-b`): the aborted conversion stops after 1–2 compares, the next two run 8/8, nothing fires during tracking, and the reads are exact.
- **FF-hot static reference offset**, reported separately (`-split` runs): the quiet pins sit −0.155…−0.179 mV (VREFP) and +0.154…+0.176 mV (VREFN) from nominal. That is 0.048 LSB of static error; the settling error without it is 0.029 LSB.

## Bootstrap gate screen with the routed CMP_CLK

- SS cold scores 0.118–0.119 V at the first comparison against the 0.1 V screen (`-gate` runs). Stage 2 scored 0.096 V with the ~10 fF `CL_CMP_CLK` model load, and #29 estimated 0.102–0.103 V for the routed ~5 fF.
- The first comparison is 1.296–1.298 ns after sample close, the same as in Stage 2. The excess is therefore a slower gate discharge in this deck, not an earlier clock. A likely cause, not measured: the system model's supply and ground network, or the extracted wiring of SEQ_SAMPLE, VIN and TOP.
- No code moves, and every other check passes on these runs.
- The revised Bootstrap `boot-fill-r2-20261122` is being run directly on this deck (`sar8-s6e-ssc-{extreme,verify}-r2`). Its verdict follows the rule in `Layout/results/current.json` `integration.decisions.stage6_bootstrap_gate_screen` and is **pending**.

## Comparator offset from CMP_CLK coupling

| Corner | As extracted | Symmetric coupling | No coupling | CLK mismatch (extracted − symmetric) | All routing (extracted − none) |
| --- | ---: | ---: | ---: | ---: | ---: |
| TT | +0.415 mV | −0.320 mV | −0.132 mV | **+0.735 mV** | **+0.547 mV** |
| SS cold | +0.399 mV | −0.166 mV | −0.090 mV | **+0.565 mV** | **+0.490 mV** |

- **Extracted coupling:** CMP_CLK to COMP_P 135.9 aF and to COMP_N 169.7 aF.
- **Shift size:** about 0.07–0.1 LSB, small against the 12 mV comparator offset sigma that the digital code-offset subtraction removes.
- **Search quality:** the SS-cold extracted and symmetric searches left 3–4 cycles unresolved but stay bracketed within 4 µV, and their consistency probes agree.

## Reference and supply against the Stage 1 budget

The rail analysis ([measure_stage6_rails.py](../../Layout/tools/analysis/measure_stage6_rails.py), `-rails3` runs) separates static current, measured over 88–98 ns of every frame, from switching charge. The charge budgets are scored on the switching part, and the totals are kept.

| | SS cold (verify / extreme / carry) | FF hot (verify / extreme) | Limit |
| --- | ---: | ---: | ---: |
| Static current, VDD | 0.94–0.97 µA | 226–227 µA (SAR macro branch 195 µA) | — |
| Static current, VREFP / VREFN | 0.37 µA | 7.9 µA | — |
| Reference charge per conversion, switching | 2.80–2.83 pC | 3.35 / 3.52 pC | 3.7 pC |
| Reference 1 ns event | 1.33 pC | 1.52 pC | 1.9 pC |
| Supply charge per conversion, switching | 4.62–4.66 pC | **7.54 / 7.56 pC** | 6.9 pC |
| Supply 1 ns event, switching | 0.66 pC | **1.11 pC** | 1.1 pC |
| Supply droop | 12 mV | 28 mV | 45 mV |
| Reference span droop | 0.089 V | 0.129 V | 0.26 V |
| Pin peak, reference / supply | 3.2 / 0.83 mA | 4.22 / 1.70 mA | 5.2 / 5.5 mA |

- **SS cold** passes every budget. At FF hot the supply switching charge is 1.01–1.09 × its budget. The user accepted this with a written disposition, and no limit changed: `Layout/results/current.json` `integration.decisions.stage6_ff_hot_charge_budgets`.
- An earlier window of 75–95 ns caught the conversion tail at SS cold. Those `-rails2` results are superseded; FF hot was unchanged.

## TT FFT

- **Pilot** (`sar8-s6e-tt-verify-b-fftp`): 8/8 frames valid with 8/8/8 events, and the monitor and native decode agree. It ran at 21 min per frame with 8 threads.
- **Full prefill FFT:** not run, on the coordinator's plan; it would be superseded.
- **Final TT FFT:** will be the 1024-point record split into 6–8 segments (`prepare_stage6 fft --segment`), stitched by [fft_stitch.py](../../Layout/tools/analysis/fft_stitch.py).

## Still pending

- The Bootstrap r2 gate verdict (`sar8-s6e-ssc-{extreme,verify}-r2`).
- The FF-hot carry split and rail analyses (queued).
- The final Stage 6 on `sar8_adc_core_filled/layout_fill5` at TT, SS cold and FF hot. It will use the corner wiring extractions `adc-core-fill5-wire-xtr[-cw|-cb]`, the refilled pair `se-xref-peripheral-routed` with its corner weights, `boot-fill-r2-20261122[-cworst-t|-cbest-t]`, and the drawn pad bulk (85.1 / 112.1 / 104.5 pF).
- The FF terminal-voltage scan, the Bootstrap FF-hot injection recheck, and the final TT FFT.

## Tooling changes

- **Input package cap:** `tools/saradc/managed/execution.py` caps the input package at 48 MiB in total, up from 32 MiB. The Stage 6 deck is about 37 MB; the remote 32 MiB per-file check is unchanged.
- **Reanalysis:** `prepare_all_extracted reanalyze` reruns a completed simulation's own analyzer as an analysis-only job, for runs whose analysis hit a queue timeout.
- **Bootstrap view names:** `Layout/design/bootstrap.py` accepts `layout_r<N>` revision views, the same text as the Bootstrap r2 branch.
