# Single-edge QUIET taps against a long-window settling reference

At FF cold the 8/6 taps leave **0.39 LSB** of TOP error at the bit-6 comparison, above the 0.25 LSB settling limit. The error comes from the **pin reference rails**, not from the bottom plates or the comparator. The 510-terminal bound used for the [tap calibration](sar_single_edge_taps.md) measures plates against the actual pin rails and therefore does not see it. [Measurements, run identities and decomposition](sar_single_edge_settling_reference_20261120.json)

## Method

FF cold (0.99 V, −40 °C), CBEST_T standard-cell LPE and the nominal-RC extracted CDAC, as in the tap calibration. Two long-window references, 16/16 and 24/24, reuse the archived 8/6 inputs byte for byte except for the DEL250 chain and one save line for the comparator tail and precharge nodes. Both four-frame histories were run: 255, 0, 85, 170 and the 63/64 boundary inputs. An analysis-only trace of every run records TOPP − TOPN, the pin rails, all 16 plate-group means and both gate words at each CMP_CLK 50% rise, and at 50 ps steps between the preceding COMMIT and that rise.

The 16/16 and 24/24 references agree within 0.032 LSB at every comparison (0.010 LSB from bit 6 down). At the 24/24 apertures the reference span is within 0.002 mV of 0.9 V.

The change between a tap run and the 24/24 reference is split with c_b, the standalone differential bit weight divided by 1.8 V:

- rail: Σ c_b · Δ(rail_P,b − rail_N,b), the pin rails selected by each group's gate word;
- settle: Σ c_b · Δ((P_b − rail_P,b) − (N_b − rail_N,b)), the plates relative to those rails;
- residual: measured − rail − settle.

## Results

| Taps (history) | bit 6 | bit 5 | bit 4 | bit 3 | bit 2 | bit 0 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 7/4 (scan) | 0.694 | 0.305 | 0.790 | 0.381 | 0.180 | 0.080 |
| 7/5 (scan) | 0.694 | 0.305 | 0.393 | 0.195 | 0.091 | 0.042 |
| 8/6 (scan) | **0.393** | 0.156 | 0.200 | 0.095 | 0.047 | 0.021 |
| 8/6 (63/64) | **0.391** | 0.189 | 0.175 | 0.090 | 0.040 | 0.019 |
| 9/6 (63/64, other session's run) | 0.218 | 0.111 | 0.162 | 0.084 | — | — |
| 12/10 (63/64) | 0.038 | 0.034 | 0.019 | 0.009 | 0.004 | 0.002 |

Maximum absolute TOP error in LSB against the 24/24 reference. At the 8/6 bit-6 worst case, the measured −0.393 LSB splits into −0.355 rail, −0.034 settle and −0.004 residual. Across all runs and comparisons the residual stays within 0.031 LSB, and every run selected the same trial words as the reference. The bit-7 comparison follows sampling without switching and stays within 0.037 LSB for every tap.

The error depends on the MSB decision. With 8/6 at bit 6 it is −0.39 LSB after an MSB of 0 (inputs 0 and 85) and +0.10 LSB after an MSB of 1 (255 and 170). The difference acts as a code-dependent transition shift near the major carry. For comparison, the layout systematic DNL allocation is 0.25 LSB.

After the bit-7 commit, VREFP falls by 107 mV and VREFN rises by 103 mV within about 0.4 ns. Both recover with **τ = 0.31 ns**, which corresponds to 50 Ω and about 6.2 pF (the 4 pF bypass plus the switched CDAC load). At the 8/6 bit-6 aperture, 1.59 ns after the commit, the span is 5.2 mV short. Resistance and capacitance set this recovery, so the required time is essentially independent of the MOS corner. The reference source model, 50 Ω and 4 pF per rail with no on-chip buffer, is part of the [specification](../../specs/arch.json).

## Required window at FF cold

The table gives the time from COMMIT to the next CMP_CLK rise at which the 24/24 TOP trajectory last leaves each band around its aperture value. Each entry is the worse of the two histories.

| Bit | ≤ 0.25 LSB | ≤ 0.125 LSB | ≤ 0.0625 LSB |
| ---: | ---: | ---: | ---: |
| 6 | 1.70 ns | 1.95 ns | 2.15 ns |
| 5 | 1.45 ns | 1.65 ns | 1.85 ns |
| 4 | 1.15 ns | 1.35 ns | 1.60 ns |
| 3 | 0.95 ns | 1.10 ns | 1.30 ns |
| 2 | 0.75 ns | 0.95 ns | 1.15 ns |
| 1 | 0.60 ns | 0.80 ns | 1.00 ns |
| 0 | 0.55 ns | 0.70 ns | 0.90 ns |

Across 5 to 12 stages the FF-cold window measures 0.155 + 0.177·N ns. Applied to the table:

- ≤ 0.25 LSB requires 9/6 with two taps. In the SS-cold LPE verification, each DEL250 added about 0.48 ns per comparison. Changing 8/6 to 9/6 therefore adds about 1.4 ns per frame and leaves roughly 9.0 ns of the measured 10.4 ns read margin.
- ≤ 0.125 LSB requires 11/7. This adds about 6.7 ns per SS-cold frame and leaves about 3.7 ns before inter-cell wiring.
- With one tap per bit at ≤ 0.125 LSB, the stages are 11, 9, 7, 6, 5, 4 and 4 for bits 6 to 0. With 8 stages kept before bit 7, the chain total equals that of the present 8/6.

## Limits

These runs use ideal SAR inter-cell wiring, the nominal-RC CDAC extraction for both MOS corners and only FF cold. The SS-cold windows of 2.9–3.9 ns exceed every requirement above. Selecting taps by per-bit index needs a hazard-free select. The combinational LOW_BITS select produced extra DELIVERED crossings when the two taps differed by three or more stages.

Preparation, traces and comparison: `work/sar-settle-ref/` (`prepare_ref.py`, `aperture_trace.py`, `follow.py`, `compare.py`).
