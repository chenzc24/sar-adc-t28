# Comparator Layout and Verification

On 2026-11-20, v8 replaced v7 as a robustness revision; see [v8 robustness revision](#v8-robustness-revision). The geometry described below is v7's, which v8 keeps apart from the supply pins and vias.

On 2026-11-18, v7 replaced the core at `SAR_ADC_T28_LAYOUT/sar_strongarm_t28_core/layout`. It uses V4's three shared-diffusion rows, with one nf=1 PCell instance per finger. Each D/G/S/B terminal connects to its schematic net and follows the schematic drain/source orientation. N+ and P+ guard rings surround the device rows. Native LVS is **CORRECT**. DRC retains two original fixture warnings. Prefill RC extraction, standalone TT post-layout simulation, and ten-frame integration with the current ADC completed. These checks qualify the stated scope. [Hashes and per-point results](comparator.json)

![Native GDS geometry of the comparator core](figures/comparator_core.png)

## Floorplan

The electrical source is `design/xtor/comparator/comparator.scs`. The layout uses its connectivity and device widths. Each layout finger has W=0.5 µm, L=30 nm, and a 0.13 µm gate pitch.

| Row | Diffusion order | Instances |
| --- | --- | --- |
| P (N-well, N+ ring to VDD) | `Y\|RSTY\|VDD\|PLATN\|OUTN\|RSTN\|VDD\|RSTP\|OUTP\|PLATP\|VDD\|RSTX\|X` | MPRSTY, MPLATN, MPRSTN, MPRSTP, MPLATP, MPRSTX |
| N1 (P+ ring to VSS) | `OUTN\|LATN\|Y\|INP\|TAIL\|INN\|X\|LATP\|OUTP` | MNLATN, MNINP_1, MNINN_1, MNLATP |
| N2 (same P+ ring) | `Y\|INP\|TAIL\|TL\|VSS\|TL\|TAIL\|INN\|X` | MNINP_2, MNTAIL_1, MNTAIL_2, MNINN_2 |

- MNINP, MNINN, and MNTAIL are schematic single-finger devices with W=1 µm. Each uses two parallel 0.5 µm instances in layout (`_1` and `_2`). Each input device has one finger in N1 and one in N2, mirrored left to right.
- Adjacent instances share diffusion through the PDK's `same` abutment shape. The generator adds the shared-diffusion contacts using the same row count and M1 width as the native PCell ends.
- The PLATN/LATN gates align at x=−0.195 and PLATP/LATP at x=+0.195. Each output has one M3 trunk.
- The two guard rings align at x=±0.70.

## Routing

- M1 carries contacts, source and drain columns, and guard rings. M2 carries horizontal tracks. M3 has five vertical trunks at x=0 (CLK), ∓0.195 (OUTP/OUTN), and ∓0.39 (Y/X). Via enclosures match the route width. Gate contact pads are 0.20 × 0.07 µm horizontal M1 strips.
- Input gates contact in the channel between N1 and N2. An L-shaped M1 segment joins each pair of fingers. One via leads to a horizontal M2 escape, west for VINP and east for VINN, clear of device rows.
- The four reset gates share an M1 bus below P. The tail gates share an M1 strip below N2. The central M3 trunk joins them and exits south, ending before the P row.
- The P-row VDD source and drain columns connect directly to the N+ ring in M1. The tail VSS source connects to both sides of the P+ ring through a horizontal M2 strip. TAIL uses central M2 from the shared N1 diffusion to both N2 TAIL diffusions.
- Each row's Y/X cross-connection or stacked via lies between its output cross-connections. The P-row OUTP cross-connection lies near the CLK bus. In N1, OUTP is closest to the input channel.

## Iteration History

- v3 and v4 grouped devices into three multifinger PCells. Virtuoso labels, S/D names, and gate assignments differed from the circuit. The v4 input route also passed over its own devices, parallel to the CLK trunk.
- v6 used one instance per schematic device and changed the inputs to single 1 µm fingers. This produced a 0.5/1 µm diffusion step, longer dummy poly, and a separate tail row.
- v7 restored the V4 floorplan with one instance per finger and redid the routing as described above.
- In the scratch library, v7b to v7c moved three N1 tracks up by 0.005–0.01 µm to meet M2.S.7. The official run's geometry digest matches scratch v7c.

## v8 Robustness Revision

v8 (`comp-v8-20261120-pex`) keeps v7's rows, instances and tracks. The executor checkpointed the v7 core before the rebuild. DRC retains only the two original warnings; LVS is CORRECT. The official structural GDS hash matches scratch run v8d.

- **Supply pins.** VDD and VSS are now 0.07 × 1.47 µm M2 straps over the top N+ and bottom P+ ring sides, with a via1 every 0.13 µm to the ring. The VSS bar from the tail source also drops on M2 along both ring sides to the strap. [interfaces.json](../specs/interfaces.json) has the new pin coordinates.
- **Redundant vias.** Two or three cuts now on the latch gate stacks (P and N1), the tail-gate CLK stack, the input gates, the N2 TAIL drops, the Y/X P-row stacks and N2 trunk, and the tail VSS source. Single cuts remain on the output cross-coupling straps, the Y/X N1/N2 strap via1, the N1 TAIL drop and the reset-gate CLK stack, where the M2 track pitch or mirror symmetry leaves no room.
- **Mirror balance.** Scratch v8c also doubled the reset-gate CLK stack. Its second cut sat nearer the OUTP strap; the TT screen failed (+0.1 mV decided wrong, fit offset −0.12 mV). v8 drops that cut and gives the Y/X P-row pads three cuts spaced so each output strap end faces one pad. The largest mirror coupling differences are back to v7's (≤0.0074 fF, OUT–TAIL).
- **Supply resistance.** With VDD extracted, VDD pin to PMOS sources is 28.5–28.7 Ω (v7 29.7–30.6) and VSS pin to the tail source is 29.4 Ω (v7 38.7). Supply diagnostics `comp-scr-v8dsup-tt/ffc-20261120` give 6.0 / 6.9 mV maximum PMOS source droop and 3.9 / 4.7 mV tail source rise at TT / ffc (v7 6.3 / 7.3 and 5.1 / 6.2).

Standalone TT in the current block fixture (standard-cell receivers), with v7 rerun in the same fixture:

| Measurement | v7 (`comp-v7b-tt-20261120`) | **v8 (`comp-v8-tt-20261120`)** |
| --- | ---: | ---: |
| Correct decisions, test and screen | 10/10, pass | **10/10, pass** |
| Maximum decision delay (ps) | 301.7 | **314.3** |
| Maximum reset time (ps) | 33.20 | **33.31** |
| Peak differential / common-mode kickback (µV) | 59.6 / 398.1 | **58.1 / 403.0** |
| Delay-fit offset diagnostic (mV) | −0.013 | **−0.050** |

**Current-ADC check.** The adopted single-edge SAR no longer has the `phi_w` node that the `prepare_comparator --integrated` analyzer reads, so those runs (`comp-*-int-*-20261120b`) simulated but could not be analyzed. Instead, `work/layout/comparator-redesign/make_lpe_comp.py` packages the design's own `single_edge_lpe` verify fixture (foundry cell LPE, nominal extracted CDAC, eight frames, 45 ns sampling) and swaps in each comparator extraction; the v8 and v7 packages differ only in the extraction files.

| Measurement | TT v7 | **TT v8** | ffc v7 | **ffc v8** |
| --- | ---: | ---: | ---: | ---: |
| All checks, all frames | pass | **pass** | pass | **pass** |
| Minimum margin (ns) | 25.084 | **25.081** | 30.883 | **30.883** |
| Max settling error (LSB) | 0.0266 | **0.0267** | 0.1100 | **0.1098** |
| Max sampling close error (LSB) | 0.0037 | **0.0037** | 0.0090 | **0.0090** |
| Comparator high pulse min (ps) | 531.3 | **531.7** | 371.4 | **371.6** |
| CCS register setup / hold slack (ps) | 232.1 / 50.0 | **232.2 / 49.9** | 157.1 / 33.6 | **157.1 / 33.6** |

Runs: `sar8-sebit-{tt,ffc}-nom-verify-{compv8,compv7b}`. At the ADC level v8 and v7 agree within 0.5 ps on pulses and slacks. The standalone fit offset moved from −0.013 to −0.050 mV, still inside the ±0.1 mV bracket; this is a fixture diagnostic, not a statistical offset.

## Pre-Merge Standalone Verification (2026-11-21)

Checks of v8 against the schematic, each pair in one fixture, for the standalone gaps listed in issue #4. Machine-readable values and run hashes: `pre_merge_verification` in [comparator.json](comparator.json). Drivers: [tools/simulation/comparator_checks](../tools/simulation/comparator_checks).

**Extractions.** `comp-v8-20261120-pex-{typical,cworst-t,cbest-t}-supplies` re-extract the frozen v8 GDS (same reference, DRC and LVS). Each first rebuilds the recorded nominal deck and checks its hash, then extracts VDD and VSS as RC (`prepare_deck(distributed_supplies=…)`; the project deck excluded only VDD). CWORST_T and CBEST_T swap in the foundry xRC rules member. Against typical, grounded interconnect capacitance is 3–5 % higher at CWORST_T and 3–5 % lower at CBEST_T. The largest mirror-pair difference stays ≤ 0.011 fF (OUTN|VDD vs OUTP|VDD).

**Comparator + CDAC, SS 0.81 V −40 °C.** `single_edge_lpe` verify fixture: CWORST_T CDAC, cell LPE `cworst_t`, eight frames. The two packages differ only in the comparator files.

| Measurement | Schematic (`…-compsch`) | **v8 CWORST_T (`…-compv8`)** |
| --- | ---: | ---: |
| All checks, all frames | pass | **pass** |
| Minimum margin (ns) | 7.591 | **8.395** |
| Last commit to next open, min (ns) | 19.325 | **20.129** |
| Max sampling close error (LSB) | 0.0738 | **0.0741** |
| Max signed settling error (LSB) | 0.0012 | **0.0012** |

**Standalone five corners.** Block acceptance fixture. MOS section, VDD, temperature and rail drives follow `specs/corners.json`; the extraction's RC corner matches each MOS corner. Input common mode 0.45 V, MOM sections and the 0.45 V edge threshold stay at TT. Every run decides 10/10 and passes validation.

| Corner (RC) | Delay at 1 mV, sch → **v8** (ps) | Max reset, v8 (ps) | Diff. kickback peak, sch → **v8** (mV) |
| --- | ---: | ---: | ---: |
| TT (typical) | 272.5 → **228.4** | 33.7 | 0.036 → **0.058** |
| SS −40 °C (CWORST_T) | 677.4 → **541.6** | 54.4 | 0.028 → **0.051** |
| SS 125 °C (CWORST_T) | 214.7 → **192.7** | 47.1 | 0.027 → **0.043** |
| FF −40 °C (CBEST_T) | 272.7 → **223.2** | 21.7 | 0.046 → **0.075** |
| FF 125 °C (CBEST_T) | 188.7 → **169.7** | 18.3 | 0.036 → **0.054** |

v8 is 10–20 % faster at 1 mV than the schematic, whose per-device diffusion parameters carry more junction capacitance than the shared diffusion. Settled kickback is +0.007 to +0.008 mV for v8 at every corner, against about 0 for the schematic.

**Kickback into the extracted CDAC TOP.** Same fixture, with the two 256-unit kickback MOM loads replaced by the extracted CDAC in a static MSB-trial state (50 Ω / 4 pF references).

| Corner | Settled diff., sch / **v8** (mV) | Diff. peak, sch / **v8** (mV) | CM peak, sch / **v8** (mV) |
| --- | ---: | ---: | ---: |
| TT | −0.0004 / **+0.0091** | 0.080 / **0.137** | 0.49 / **0.76** |
| FF −40 °C | −0.0004 / **+0.0100** | 0.212 / **0.191** | 0.54 / **0.83** |

The settled residue the SAR sees is ≤ 0.0014 LSB. The peaks are larger than with lumped MOM loads, which is consistent with the TOP wiring resistance letting the node near the comparator move first.

**Mismatch offset.** The schematic 200-seed fixture (`tb/blocks/comparator/test.scs`, seeds 4101–4300) with the comparator replaced by the typical supply-extracted netlist. A schematic packaging check reproduces seed 4101 exactly (5.3125 mV). Mismatch draws reach all four extracted input fingers. All 200 seeds give a valid threshold.

| Offset | Schematic (`results/mc/modules_200.json`) | **v8 extracted** |
| --- | ---: | ---: |
| σ (mV) | 14.19 | **12.05** |
| Mean (mV) | −0.54 | **−1.55** |
| Range (mV) | −29.9 to +37.7 | **−34.7 to +34.1** |

The σ ratio is 0.85, with a 95 % interval of 0.74–0.97 from an independent bootstrap over seeds. The draws are not paired across netlists, so only the distributions compare. The post-layout spread is smaller beyond resampling error, and the cause is not established. Candidates are the model's per-finger mismatch scaling for the split nf=1 fingers and layout-dependent instance parameters. The slowest receiver decision across all seeds is 0.33 ns. Nineteen seeds were analyzed by analysis-only reruns (`-a3`, [make_mc_reanalysis.py](../tools/simulation/comparator_checks/make_mc_reanalysis.py)) of their completed simulations, because their queued analysis workers had lost their user memory cgroup and could not pass the admission gate. Reanalyzing seed 4101 the same way reproduced its records, draws and offset exactly.

**Input-referred noise.** New fixture: nominal models, a noiseless stepped input (9 levels × 128 decisions, 0.4 mV step), Spectre transient noise (`noise_worst`, 100 kHz to fmax) and a probit maximum-likelihood fit. Budget 0.18 LSB (1.27 mV). No decision was unresolved.

| Run | σ (mV) | σ (LSB) |
| --- | ---: | ---: |
| TT schematic, 20 / 50 / 100 GHz | 0.597 / 0.503 / 0.606 (± 0.03) | 0.085 / 0.072 / 0.086 |
| **TT v8, 50 GHz** | **0.601 ± 0.029** | **0.086** |
| SS 125 °C schematic, 50 GHz | 0.836 ± 0.040 | 0.119 |
| **SS 125 °C v8, 50 GHz** | **0.797 ± 0.038** | **0.113** |

The 20 and 100 GHz values agree, so the noise is converged by 20 GHz; the low 50 GHz schematic value is single-seed scatter. v8 matches the schematic within error at both corners. The worst case, SS hot, uses 63 % of the budget.

**Attempts superseded.**
- The first kickback packages failed at read-in: the CDAC wrapper master duplicated the schematic CDAC. The `-b` packages rename it.
- `comp-v8-ffh-rc-20261121` failed on a Spectre license checkout and was rerun as `…b`.
- Four noise runs stopped at the 1024 MiB output cap and were rerun as `-b` with strobe-only output.
- The fit of `comp-v8-nz-tt-rc-f50-b` divided by a zero determinant. The corrected fit reproduces the three earlier fits to four digits and was applied by the analysis-only rerun `-fit2`.
- `comp-v8-mc-s*-a2` failed at import because the analyzer helper was not packaged; no outputs.

## Interface and Area

The native core bounding box is `(-0.815,-2.645) → (0.815,0.875) µm`, measuring **1.63 × 3.52 µm** and **5.74 µm²**. The old core measured 7.96 × 12.46 µm and v4 measured 1.66 × 3.44 µm.

| Port | Layer | Center (µm) | Size (µm) |
| --- | --- | --- | --- |
| VINP / VINN | M2 | (−0.765,−1.60) / (0.765,−1.60), west/east | 0.10 × 0.05 |
| OUTP / OUTN | M3 | (−0.195,0.825) / (0.195,0.825), north | 0.05 × 0.10 |
| CLK | M3 | (0,−2.595), south | 0.05 × 0.10 |
| VDD | M2 strap over the top N+ ring side (v8) | (0,0.76) | 1.47 × 0.07 |
| VSS | M2 strap over the bottom P+ ring side (v8) | (0,−2.53) | 1.47 × 0.07 |

The inputs now enter from the sides and CLK from the south. Strap the M2 VDD and VSS pins to the top-level power grid and place local decoupling next to the core; each comparison draws about 25 fC with 0.3–0.4 mA peaks. The core uses M1–M3. Keep top-level digital crossings away from the area above it on M4 and higher and check coupling with top-level extraction. The comparator group has a 16 × 14 µm interface-routing reservation pending actual placement. The three comparator output and clock MOM loads in the top-level netlist are pre-layout model loads, per the 2026-11-18 decision and load diagnostic below. Use top-level extraction for actual loads. [Pin access coordinates](../specs/interfaces.json)

## Verification Results

Physical evidence is `comp-v7-20261118-pex`. The executor checkpointed the v6 OA core before the rebuild. Earlier checkpoints are in `comp-v6-20261118-pex`, `comp-v4-20261117-pex`, and `comp-v3-20261117-pex`.

- LVS returned CORRECT. The initial layout has eight NMOS and six PMOS. Parallel reduction maps to five NMOS and six PMOS in the schematic. PEX completed.
- DRC retained one `DIODMY_L:WARNING` and one `IO_CONNECT_CORE_NET_VOLTAGE_IS_CORE:WARNING1`. Close density at the top level. [Fill policy](../specs/fill-policy.md)

Extracted interconnect capacitance to ground in fF, excluding device capacitance and inter-net coupling.

| Node | Old sym2 core | v4 | v6 | **v7** |
| --- | ---: | ---: | ---: | ---: |
| VINP / VINN | 0.319 / 0.319 | 0.050 / 0.050 | 0.026 / 0.026 | **0.055 / 0.055** |
| OUTP / OUTN | 1.301 / 1.293 | 0.331 / 0.334 | 0.322 / 0.327 | **0.291 / 0.300** |
| Y / X | 0.751 / 0.751 | 0.243 / 0.244 | 0.170 / 0.170 | **0.209 / 0.209** |
| TAIL | 0.628 | 0.009 | 0.005 | **0.013** |
| CLK | 1.093 | 0.377 | 0.378 | **0.373** |

Inter-net coupling in fF.

- CLK to each input is 0.0137, equal on both sides. v4 was 0.058 and v6 was 0.0027. The symmetric central CLK trunk passes between the N1 input gates.
- Output to input coupling is OUTP–VINP 0.0215, OUTN–VINN 0.0163, OUTP–VINN 0.0094, and OUTN–VINP 0.0027.
- The largest mirror differences are 0.0068 for output to opposite input, 0.0067 for output to TAIL, and 0.0053 for output to same-side input. In N1 the OUTP cross-connection is closest to the input channel. Other mirror differences are ≤0.003.

The standalone fixture uses TT, 0.9 V, 27 °C, a 2 ps maximum step, the same MOM and receiving-gate loads, and inputs of ±100, ±30, ±3.515625, ±1, and ±0.1 mV. The 750 ps diagnostic applies to this measurement scope.

| Measurement | Schematic | Old sym2 core | v4 | v6 | **v7** |
| --- | ---: | ---: | ---: | ---: | ---: |
| Correct decisions | 10/10 | 10/10 | 10/10 | 10/10 | **10/10** |
| Test and screen | Pass | Pass | Pass | Pass | **Pass** |
| Maximum decision delay (ps) | 364.73 | 517.30 | 310.95 | 342.34 | **301.72** |
| Maximum reset time (ps) | 32.83 | 37.49 | 33.12 | 33.22 | **33.20** |
| Peak differential kickback (µV) | 35.84 | 52.18 | 67.03 | 55.52 | **59.63** |
| Peak common-mode kickback (µV) | 236.49 | 409.15 | 409.72 | 359.32 | **398.10** |
| Delay-fit offset diagnostic (mV) | −0.002 | −0.041 | −0.019 | −0.037 | **−0.013** |

Among these tests, v7 had the shortest decision delay and the smallest fitted offset magnitude. Its differential kickback lies between v6 and v4. Common-mode kickback was about 11% higher than v6, consistent with CLK coupling between the input gates. These kickback values are from the floating-input fixture. The ±0.1 mV decisions cover the tested points. Use the actual ADC load for CDAC-node error and statistics for mismatch offset.

`comp-v7-int-20261118` substitutes the comparator RC netlist into the current ADC. All other modules use pre-layout views. The ten expected codes `0,0,12,127,128,243,255,255,0,128` matched. Every frame had eight compares, writes, and updates. Sampling edges and event order passed. Maximum conversion time was **28.7848 ns** versus 29.5023 ns for the old core and 28.8612 ns for v6.

**Load diagnostic.** `comp-v7-int-noload-20261118` removes `CL_COMP_N`, `CL_COMP_P`, and `CL_CMP_CLK` from the same ADC fixture, each estimated at about 10 fF. The other inputs match byte for byte. All ten frames passed codes, handshake counts, event order, and sampling edges. Maximum conversion time dropped from 28.78 to 27.71 ns. The median cmp↑→write↑ dropped from 366 to 271 ps and its range narrowed from 273–469 to 242–300 ps. Two additional `SPECTRE-16780` warnings reported temporary LTE relaxation across steep SAR-node transitions. Both affected frames passed.

The FF-cold pair used ffc (FF, 0.99 V, −40 °C, passives at TT). All ten frames passed in each run, `comp-v7-int-ffc-20261118` with loads and `comp-v7-int-ffc-noload-20261118` without them. Removing the loads reduced maximum conversion time from 25.56 to 24.70 ns and median cmp↑→write↑ from 299 to 222 ps, with its range narrowing from 219–381 to 197–244 ps. Minimum update↑→cmp↓ spacing fell from 46.6 to 35.1 ps and minimum cmp↓→write↓ from 25.5 to 23.0 ps. Event order was preserved. One additional `SPECTRE-16881` warning flagged possible Verilog-A-related convergence difficulty in frame 2, which passed.

TT and ffc passed function and handshake timing with both load settings. Open coverage includes ssc, ssh, ffh, mismatch, and the actual top-level load.

**Supply diagnostic.** The project PEX deck lists `VDD` in `PEX EXTRACT EXCLUDE`, so the v7 post-layout runs above use an ideal VDD inside the core; VSS is extracted. A scratch extraction of the frozen v7 GDS with VDD included (`scratch/v7_vddpex`) gives 30–31 Ω from the VDD pin to each PMOS source and 38.7 Ω from the VSS pin to the shared tail source, including the diffusion contacts. Bulk taps are 3.8 Ω (VDD) and 4.2 Ω (VSS) from their pins. `comp-scr-v7sup-tt-20261120` and `comp-scr-v7sup-ffc-20261120` run that extraction in the standalone fixture with 0 V sources in series with the comparator supply pins and an ideal supply at the pins. These are diagnostics, not qualification results.

| Measurement | TT | ffc |
| --- | ---: | ---: |
| Correct decisions, test and screen | 10/10, pass | 10/10, pass |
| Maximum decision delay (ps) | 300.7 | 298.4 |
| Peak differential / common-mode kickback (µV) | 59.3 / 398.1 | 77.3 / 431.4 |
| Peak VDD / VSS pin current (µA) | 301 / 128 | 378 / 157 |
| Average supply current (µA) | 2.3 | 2.6 |
| Charge per comparison from VDD (fC) | 23.1 | 25.6 |
| Maximum PMOS source droop (mV) | 6.3 | 7.3 |
| Maximum tail source rise (mV) | 5.1 | 6.2 |

At TT, delay and kickback match the ideal-VDD run within 1 ps and 0.4 µV. The largest droop is at the RSTN/RSTP sources and is equal on both sides within 0.01 mV; left/right source bounce differs by at most 0.15 mV. The core straps therefore do not limit the comparator in these conditions. The peak current, mostly reset charging of the outputs and their 10 fF fixture loads, must come from the top-level supply and local decoupling.

Full per-device terminal voltage, final fill, and full top-level parasitics still need qualification. v8 PVT, mismatch offset and noise are in [Pre-Merge Standalone Verification](#pre-merge-standalone-verification-2026-11-21). The layout splits the 1 µm input and tail devices into two fingers, with input fingers in separate rows; the post-layout MC includes this split.

## Maintenance and Handoff

`design/comparator.il` defines functional geometry. `design/comparator.py` generates the independent CDL from the electrical source. `tools/simulation/prepare_comparator.py` packages pre- and post-layout tests and the ADC interface case. `tools/simulation/comparator_checks/` holds the corner re-extraction driver, and the MC, noise, CDAC-kickback and ADC-pair packagers. Use the existing native and managed entry points. `tests/test_comparator_layout.py` verifies that each schematic device uses same-named 0.5 µm fingers, optionally with `_k` suffixes, and matches its schematic total width. [Comparator workflow](../docs/workflow.md#comparator-module)

The fixed wrapper `sar_strongarm_t28/layout` references the core through XCORE. Use the core for review and integration. Refresh and reverify the wrapper fill before qualifying it for the current core.

In `comparator.json`, see `superseded_core` (sym2), `superseded_v4`, `superseded_v6`, and `independent` for earlier results. The `SCRATCH_COMP` library and `comp-scr-*` runs document candidate exploration. Use the official physical run for layout evidence.
