# Stage 2: all-extracted closed-loop ADC, ideal top-level wiring

Stage 2 of the [top-level integration plan](https://github.com/chenzc24/sar-adc-t28/issues/12), run 2026-11-21 to 2026-11-22. Every frozen block extraction (`Layout/results/current.json` `integration.freeze`) is in one closed-loop deck, and the wiring between blocks is ideal. All three corners pass the Stage 2 criteria. At FF hot the static reference-pin offset from switch leakage is reported separately, as the issue requires. Route checks with RC wiring at the planned floorplan lengths turn the margins into three proposed route budgets. [Measurements, run identities and digests](stage2_all_extracted_20261122.json) · [Deck entry](../../Layout/tools/simulation/prepare_all_extracted.py) · [Record builder](../../Layout/tools/analysis/stage2_summary.py)

## Assembly

| Corner | Cell LPE | XREF + CDAC (filled stream `se-xref-peripheral-dense`) | Comparator v8, VDD/VSS RC | SAR macro `sar8_se_core/layout_r3` | Bootstrap, both channels | k |
| --- | --- | --- | --- | --- | --- | ---: |
| TT 0.90 V 27 °C | typical | `se-xref-peripheral-dense` | `comp-v8-20261120-pex-typical-supplies` | `sar-se-r3-lib` | `boot-core-20261121` | 0.959407 |
| SS 0.81 V −40 °C | CWORST_T | `se-xref-peripheral-dense-cworst-t` | `comp-v8-20261120-pex-cworst-t-supplies` | `sar-se-r3-cw` | `boot-core-20261121` | 0.959324 |
| FF 0.99 V 125 °C | CBEST_T | `se-xref-peripheral-dense-cbest-t` | `comp-v8-20261120-pex-cbest-t-supplies` | `sar-se-r3-cb` | `boot-core-20261121` | 0.959179 |

- **New extractions.** `se-xref-peripheral-dense-cworst-t` and `-cbest-t` re-extract the frozen filled stream with the foundry corner xRC rules. The driver ([xref_rc_corner.py](../../Layout/tools/physical/xref_rc_corner.py)) first rebuilds the frozen typical job deck byte for byte, including its density-row flatten, and only then swaps the rules include; DRC and LVS are inherited. `sar-se-r3-cb` is the saved macro view extracted at CBEST_T (LVS CORRECT). It was needed because typical-RC SAR wiring would overstate FF-hot hold slack.
- **Gain.** k for each corner comes from the standalone eight-bit weights of the same extraction at the same MOS corner (`xref-dense-ssc-gain-cw`, `xref-dense-ffh-gain-cb`). Those runs reuse the fixture and analyzer bytes of the frozen TT weight run `xref-fill-tt-after-dense`. Gain error is 4.231 / 4.240 / 4.256 % and DNL / INL 0.098 / 0.077, 0.140 / 0.095 and 0.117 / 0.082 LSB.
- **Bootstrap.** The frozen evidence `boot-core-20261121` is a typical-RC extraction and is used at every corner; no corner extraction of the Bootstrap core was made.
- **Resources.** Simulation reservations were raised to 6 GiB, then 4 GiB; the measured peak was 2.19 GB. Runs took 44 min (restart) to 2 h 03 min (SS-cold eight-frame).

## Stage 2 results

Stimuli: `verify` (full-scale steps, mid-scale, 85/170, 1; frame 0 is a warm-up from the DC solution), `extreme` (full-scale reversals, low-to-mid steps, 0.01 LSB above mid-scale), `carry` (alternating 0x7F/0x80) and `restart` (a sample that aborts a conversion, then two conversions).

| Corner | Run | Codes vs target | Compares / updates | Residual at sample close (LSB) | Signed decision error, nominal rails (LSB) | Plate error, instantaneous rails (LSB) | Read margin (ns) | Bootstrap gate screen (V) | Setup / hold (ps) |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| TT | `sar8-allx-tt-verify-c` | 7/7 exact | 8/8 | 0.006 | 0.029 | 0.040 | 24.58 | 0.000 | 246 / 57 |
| TT | `sar8-allx-tt-extreme-a` | 7/8 exact, 1 at −1 | 8/8 | 0.006 | 0.029 | 0.040 | 24.63 | 0.000 | 246 / 57 |
| TT | `sar8-allx-tt-carry-a` | 7/7 exact | 8/8 | 0.000 | 0.007 | 0.028 | 24.63 | < 0 | 246 / 57 |
| SS cold | `sar8-allx-ssc-verify-a` | 7/7 exact | 8/8 | 0.052 | 0.003 | 0.010 | **7.77** | **0.088** | 443 / 100 |
| SS cold | `sar8-allx-ssc-extreme-b` | 7/8 exact, 1 at −1 | 8/8 | 0.054 | 0.003 | 0.010 | 7.88 | 0.087 | 443 / 100 |
| SS cold | `sar8-allx-ssc-carry-a` | 7/7 exact | 8/8 | 0.000 | 0.000 | 0.007 | 8.02 | < 0 | 442 / 100 |
| FF hot | `sar8-allx-ffh-verify-a` | 7/7 exact | 8/8 | 0.005 | 0.162 (0.102 without static offset) | 0.085 | 30.08 | 0.001 | 178 / 39 |
| FF hot | `sar8-allx-ffh-extreme-b` | 7/8 exact, 1 at −1 | 8/8 | 0.006 | 0.161 (0.101 without static offset) | 0.085 | 30.10 | 0.001 | 178 / 39 |
| FF hot | `sar8-allx-ffh-carry-a` | 7/7 exact | 8/8 | 0.000 | 0.103 | 0.077 | 30.10 | < 0 | 178 / 39 |

- **Limits.** Codes within the gain-corrected target ±1, residual and plate settling ≤ 0.15 LSB, read margin ≥ 5 ns at SS cold, Bootstrap gate screen ≤ 0.1 V.
- **The −1 frames.** In each `extreme` run the one frame at −1 is the input 0.01 LSB above mid-scale; it reads 127 against a target of 128.
- **Restart** passes at every corner (`sar8-allx-{tt,ssc,ffh}-restart-a`). The aborted conversion stops after 1–2 compares, the next two conversions run 8 compares and 8 updates, nothing fires during tracking, and both reads are exact: 83 and 172 for inputs 85 and 170.
- **Bootstrap boosted gate.** At SS cold it is 0.087–0.088 V at the first comparison, against the 0.1 V screen; it was 0.090 V in `sar8-sebit-ssc-cw-verify-bootx-a`. No code moves, but it remains the Bootstrap screen with the least margin. With route RC added it falls to 0.064–0.073 V.
- **FF-hot reference offset.** The frozen analyzer scores the signed decision error against the nominal reference voltages, so it fails FF-hot `verify` and `extreme` at the input-0 frames (0.161–0.162 against 0.15). The analysis-only split ([measure_reference_split.py](../../Layout/tools/analysis/measure_reference_split.py); `-split` runs; nominal term matches the analyzer within 3e-17 LSB) separates the parts:

  | FF hot, worst decision | `verify` | `extreme-b` |
  | --- | ---: | ---: |
  | Against nominal rails | 0.162 | 0.161 |
  | Static pin offset (VREFN +0.226 mV, VREFP −0.221 mV, every frame) | 0.061 | 0.061 |
  | Plates against the instantaneous pins | 0.036 | 0.036 |
  | Without the static offset | **0.102** | **0.101** |

  The offset corresponds to about 4.5 µA of leakage per rail through the 50 Ω fixture. The remaining dynamic pin term (≤ 0.086 LSB) is plate charging current through the assumed 50 Ω / 4 pF reference source, so it moves with the Stage 1 source model.
- **Warnings.** Every run keeps the terminal-voltage (CMI) model warnings on the SAR hierarchy. Several runs have one temporary LTE relaxation in a delay-window multiplexer (SPECTRE-16780). `sar8-allx-ssc-verify-a` saw 52 kB of host swap (SPECTRE-555).

## Route checks and proposed budgets

Each check adds RC wiring to the Stage 2 deck and is scored against the routed-design limits (margin > 1 ns at every corner, settling ≤ 0.25 LSB):

- Every digital top-level route is a four-segment RC ladder between its real driver and receiver: CMP_CLK, COMP_P/COMP_N, CODE0–7 and PRESET.
- Each TOP net gets 9.8 fF to ground, plus the sampler-route resistance between the Bootstrap output and TOP.
- Lengths are the planned centrelines of `Layout/design/floorplan.json` on branch `layout/toplevel-floorplan` (93646b1, not merged), at 1× or 2×.
- Wire values are deliberately pessimistic: 0.2 fF/µm against 0.086–0.089 fF/µm measured on the SAR macro's routed nets, and 20 Ω/µm.
- Both ends of every route are saved, and [measure_route_delay.py](../../Layout/tools/analysis/measure_route_delay.py) measures the delays on the waveform.

| Check | Corner, length | Load per comparator output | Read margin (ideal wiring) | Residual at close (ideal) | Worst decision error (ideal) | One-way delay, handshake / CODE bus | Routed limits |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| `sar8-allxr-ssc-verify-s1` | SS cold, 1× | 11.4 fF | 4.16 ns (7.77) | 0.093 (0.052) | 0.003 (0.003) | 19.7 / 16.6 ps | pass |
| `sar8-allxr-ssc-verify-a` | SS cold, 2× | 22.8 fF | **0.66 ns** (7.77) | 0.148 (0.052) | 0.003 (0.003) | 52.9 / 50.7 ps | **fails margin** |
| `sar8-allxr-ffh-verify-a` | FF hot, 2× | 22.8 fF | 28.43 ns (30.08) | 0.002 (0.005) | 0.188, 0.128 without static (0.162, 0.102) | 55.3 / 51.0 ps | pass |

**Comparator-output load is what limits the SS-cold margin, not wire delay.** `COMP_P`/`COMP_N` are the StrongARM latch nodes; the comparator has no output buffer. Route capacitance on them slows regeneration:

- At 1× the worst added compare-to-update time per decision is 0.10 ns above 300 mV of input and 0.88 ns below 5 mV. At 2× it is 0.23 and 1.62 ns.
- Frames near mid-scale, whose residues are small, lose 3.1–3.4 ns (1×) and 6.3–6.8 ns (2×) per conversion; full-scale frames lose 1.6–1.7 ns and 3.4–3.7 ns.
- The cost is linear in load: 3.6 ns per planned length. The 1 ns routed floor would be reached near 1.9× (about 21.6 fF per output at 0.2 fF/µm).

| Budget (`Layout/specs/constraints.json`) | Proposed | Basis |
| --- | --- | --- |
| `sar_handshake_route_delay_s` | 20 ps one way, with `load_limit_F` COMP_P / COMP_N 11.4 fF and CMP_CLK 11.1 fF | The verified 1× point: 4.16 ns SS-cold margin, 3.16 ns above the routed floor. The load limit is the binding part; the delay follows from it. |
| `reference_gate_route_delay_s` | 100 ps one way, SAR pins to XREF pins | Binding at FF hot. The decision error rises about 0.5 mLSB per ps: 0.51 mLSB/ps from the RC check at 51 ps, 0.48 mLSB/ps from the ideal-delay diagnostic at 130 ps. At 100 ps the prediction is 0.213 LSB against nominal rails (limit 0.25) and 0.153 LSB without the static offset. The planned route measures 16.6 ps. |
| `comparator_input_route_capacitance_F` | 9.8 fF per TOP net; sampler route ≤ 800 Ω | 0.8 % of C_eff = 1.232 pF, from the 52.11 fF fixed TOP load and the 4.231 % TT gain error, is 9.85 fF. Every code stayed on target with 9.8 fF at SS cold and FF hot. The sampler route resistance sets the SS-cold residual: 0.093 LSB at 412 Ω and 0.148 LSB at 825 Ω, which uses 0.096 of the 0.10 LSB reserved for top-level parasitics. |

The values are proposals and are not adopted. They are consistent with the issue's starting points. The issue left about 4.4 ns of the 5 ns SS-cold routing reserve for top-level wiring after SAR macro wiring (0.65 ns, `Layout/results/sar_se_core.md`); the proposed 1× limits use 3.6 ns. The issue also allowed about 10 fF of TOP wiring; the derivation gives 9.85 fF. The alternative to a tight comparator-output load limit is an output buffer pair at the comparator. That changes a frozen block, so its standalone and pairwise checks would rerun first.

## Runs not used as evidence

- **`sar8-allxb-ssc-verify-a` and `sar8-allxb-ffh-verify-a` (ideal-delay budget checks)** are kept as diagnostics only. Their Verilog-A `absdelay` element draws no input current, so it removes each receiver's load from its driver: the comparator latch outputs, the SAR clock driver and the SAR CODE drivers. With 200 ps added on each handshake crossing, the SS-cold margin came out 7.84 ns, above the 7.77 ns control. Only the FF-hot CODE-bus point (0.224 LSB at 130 ps) is used, as the second slope point; the CODE drivers' unloading does not change when the plates start to move.
- **`sar8-allx-tt-verify-a`, `-b`, `sar8-allx-ssc-extreme-a` and `sar8-allx-ffh-extreme-a`** were cancelled before starting. Admission was blocked by thu-wei CPU load, by thu-sui disk space, and by the thu-song user cgroup, whose usage counts the page cache of written waveforms. Each was replaced with an identical deck under a new revision.

## Scope and open items

- **Top-level wiring is ideal in Stage 2.** The route checks model planned lengths, not drawn routes, and no top-level coupling between routes. Stage 6 re-extracts the routed design.
- **Deterministic runs only.** No noise, mismatch or terminal-voltage verdict.
- **Reference source.** Stage 2 keeps the 50 Ω / 4 pF fixture per rail, as `Layout/specs/constraints.json` `stage6_supply_model` specifies for Stage 2 tests. Stage 6 uses the Stage 1 network (15 Ω series per rail, 8 pF span decoupling, package and board model), so the FF-hot dynamic pin term is rechecked there against `reference_decision_error_LSB`.
- **Planning projection.** `Layout check` reports the planning projection stale because `constraints.json` is one of its inputs. The saved digest already differed from the committed file before this change. `Layout render` refreshes it once the budgets are adopted.
