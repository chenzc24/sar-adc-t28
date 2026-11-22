# Bootstrap core revision `layout_r2`: latch-up and planned fill

Part of the [top-level integration plan](https://github.com/chenzc24/sar-adc-t28/issues/12), 2026-11-22 to 2026-11-23. The user approved one combined revision of the frozen Bootstrap core `sar_bootstrap_flat_8b_p_core`. It fixes the chip latch-up markers LUP.5.2.1/5.2.2 on both channels, and it replaces the utility fill over the boot capacitor with the Bootstrap's own planned fill. **Status: in progress.** The physical checks, standalone sampler checks and Stage 2-deck ADC runs are done and pass. The routed-CMP_CLK gate verdict and the cause of a fill-induced residual increase are pending. [Measurements, run identities and digests](bootstrap_rev2_20261122.json) · [Record builder](../../Layout/tools/analysis/bootstrap_rev2_summary.py)

## Summary

- **Latch-up.** In `layout_r2`, all three guard rings are 0.20 µm wide and the PMOS row is 0.40 µm higher, so the VIN diffusion is 2.40 µm from the nearest 1.8 V PMOS diffusion (rule 2.3 µm). The chip deck's LUP rules, run flat with the new master swapped into the chip stream, report no LUP.5.2.1 or LUP.5.2.2 marker. The frozen master reports 2 and 12 through the same swap.
- **Fill.** The Bootstrap now owns a planned OD/PO fill cell. With it, each plate sees 38–40 fF to ground, against 30–33 fF unfilled and about 68 fF with the earlier utility fill. The cell closes OD.DN.3, OD.S.14, PO.DN.3 and PO.DN.3.1 itself.
- **Stage 2-deck ADC** (paired RC corner, CL_CMP_CLK model load): every Stage 2 limit passes at SS cold, FF hot and TT, and the restarts pass. The SS-cold gate screen drops from 0.096 V to 0.077 V.
- **Cost of the fill.** At SS cold the sample-close residual rises to 0.093–0.097 LSB, against 0.039 LSB for r2 without fill and 0.054 LSB for the old core (limit 0.15). The cause is not yet proven (see [Fill and the SS-cold residual](#fill-and-the-ss-cold-residual)).
- **Pending:** the direct Stage 6 runs with the routed CMP_CLK on r2 and their gate verdict.

## Geometry and OA

| View | Content | Evidence |
| --- | --- | --- |
| `sar_bootstrap_flat_8b_p_core/layout_r2` | Guard rings 0.20 µm (substrate ring and well-ring y sides widened inward; well-ring x sides 0.075 µm in and 0.025 µm out, inside unchanged N-wells); PMOS row and wells 0.40 µm higher. Same outline (24.52 × 24.99 µm), pins, devices and OD_18 region. | `boot-core-r2b-20261122` |
| `sar_bootstrap_flat_8b_p_fill/layout_r2` | Planned fill, 234 shapes (`Layout/design/bootstrap_fill.py`). | `boot-fill-build-20261122` |
| `sar_bootstrap_flat_8b_p_filled/layout_r2` | Wrapper: XCORE (`layout_r2`) and XFILL at R0, with the core's five ports. The top level places it instead of the core (XBOOTP R0, XBOOTN MY). | `boot-fill-build-20261122` |

- **Frozen views unchanged.** `layout` (layout.oa `c23c7e3b…`) and `layout_mmain4` are byte-identical before and after both builds; both runners check this. `layout_r2` is a generator-owned revision view (`bsRevision` in `Layout/design/bootstrap.il`), built from the same netlist and LVS reference as `layout`.
- **First build superseded.** `boot-core-r2-20261122` widened the well-ring x sides inward. That put the ring within 0.02 µm of the PMOS dummy poly: PO.S.28 ×2 and SR_DPO.S.4 ×2. Those sides now widen outward.
- **Shared runtime.** `bootstrap.il` and `run_physical.py` (the `layout_r<N>` support) were uploaded to the thu-wei layout runtime on their own, with a receipt (`state/deployment-bootstrap-r2.json`). A full deploy needs CDAC build files that are not in `work/`.

**Planned fill.** Each gap between two capacitor units holds one 0.12 µm dummy-poly stripe in the 0.13 µm space between the units' M1 fingers, so no dummy poly lies under a plate finger. 0.28 µm dummy-OD segments sit under each stripe, 2.2 µm long per unit row. In the array that is 22.3 % OD and 13.6 % PO (rules 20 % and 10 %). Three columns continue into the notch beside the switch bank, clear of OD_18 and the substrate ring. ODBLK, POBLK and DM1–DM9EXCL cover the whole outline. The fill session's diagnostic (`adc-core-diag-noboot-chk` against `adc-core-fill3-chk`) had shown that the earlier +36–39 fF per plate came from in-cell OD/PO, not from the surroundings.

## Physical checks

| Evidence | Content | RC | DRC | LVS |
| --- | --- | --- | --- | --- |
| `boot-core-r2b-20261122`, `-cworst-t`, `-cbest-t` | `layout_r2` | typical, CWORST_T, CBEST_T | the frozen core's six known markers | CORRECT |
| `boot-fill-r2-20261122`, `-cworst-t`, `-cbest-t` | `layout_r2` with the planned fill flattened in | typical, CWORST_T, CBEST_T | the two advisories only | CORRECT |

- The corner extractions of the core use `bootstrap_rc_corner.py`, as for the frozen core.
- The filled extractions use `bootstrap_filled.py`, which runs DRC, LVS and PEX fresh on the filled stream. The OA wrapper's stream equals that checked assembly on all 37 layers.

**Flat chip latch-up** (chip deck `drc_rule_T28_chip`, flat, LUP.* and ESD.* checks, VIN pad-connected). The master is swapped into the chip stream `chip-asm-a3` at the GDS level (`Layout/tools/physical/substitute_master.py`; same name and pins, both instances rebound).

| Master | Evidence | LUP.5.2.1 | LUP.5.2.2 | ESD.18g / ESD.19g / ESD.WARN.1 |
| --- | --- | ---: | ---: | --- |
| `layout_r2` | `boot-r2-chip-flat-lup` | 0 | 0 | 540 / 432 / 6 (ring-inherent) |
| frozen `layout` (control) | `boot-frozen-chip-flat-lup` | 2 | 12 | 540 / 432 / 6 |

**Parasitics at typical RC** (fF; CWORST_T and CBEST_T are in the JSON):

| Net | Frozen | r2 | r2 with fill |
| --- | ---: | ---: | ---: |
| BTOP to ground | 29.8 | 29.8 | 37.9 |
| BBOT to ground | 32.8 | 32.8 | 40.4 |
| BTOP to BBOT | 196.2 | 196.2 | 193.2 |
| G (total) | 2.745 | 2.790 | 2.726 |
| VIN | 2.970 | 2.969 | 3.059 |
| VOUT | 0.667 | 0.673 | 0.681 |
| CLKS | 1.633 | 1.687 | 1.725 |

**Layout-dependent device parameters.** The wells are 0.40 µm farther from the NMOS bank. The NMOS well-proximity parameter `sca` falls by up to 0.14 (Maux 1.81 → 1.67, MRSTG 1.96 → 1.83; main-switch fingers 0.01–0.14). `sodx`/`sody` fall by about 0.1 µm from the wider rings. The PMOS devices move with their wells.

## Standalone sampler

Standalone bench (`tb/blocks/bootstrap`): 50 Ω source, 256-unit MOM load, 0.2 → 0.8 V step. Filled r2 at typical RC; limit 3.516 mV.

| Corner | Run | Sampling error (mV) | Frozen core (mV) | Margin (mV) |
| --- | --- | ---: | ---: | ---: |
| TT | `boot-r2f2-tt-20261122` | −2.491 | −2.512 | 1.03 |
| SS cold | `boot-r2f2-ssc-20261122` | −1.158 | −1.116 | 2.36 |
| SS hot | `boot-r2f2-ssh-20261122` | −2.015 | −2.033 | 1.50 |
| FF cold | `boot-r2f2-ffc-20261122` | −3.118 | −3.155 | 0.40 |
| FF hot | `boot-r2f2-ffh-20261122` | −3.351 | −3.390 | **0.165** |

All pass. FF hot remains the tightest corner; its margin was 0.13 mV with the frozen core. Startup error and hold droop change by 0.03 mV at most. Without fill (`boot-r2-ssc-20261122`) the SS-cold error is −1.135 mV.

## ADC with the extracted CDAC, Stage 2 deck

`prepare_all_extracted adc CORNER KIND --bootstrap ID`: the Bootstrap at the paired interconnect corner (TT typical, SS CWORST_T, FF CBEST_T), everything else as in Stage 2, including the CL_CMP_CLK model load. Earlier values in parentheses: `allxc` at SS cold (old core at CWORST_T), Stage 2 `allx` at FF hot and TT (old core at typical).

| Run | Bootstrap | Codes | Residual (LSB) | Settling (LSB) | Read margin (ns) | Gate screen (V) |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `sar8-bsr2-ssc-verify-a` | r2 | 7/7 | 0.039 (0.054) | 0.003 (0.003) | 7.76 (7.77) | 0.082 (0.096) |
| `sar8-bsr2-ssc-carry-a` | r2 | 7/7 | 0.000 | 0.000 | 8.02 (8.02) | < 0 |
| `sar8-bsr2-tt-verify-a` | r2 | 7/7 | 0.006 (0.006) | 0.029 (0.029) | 24.58 (24.58) | 0.000 |
| `sar8-bsr2-ssc-verify-f2` | r2 + fill | 7/7 | **0.093** (0.054) | 0.003 (0.003) | 7.76 (7.77) | **0.077** (0.096) |
| `sar8-bsr2-ssc-extreme-f2` | r2 + fill | 7/8, 1 at −1 | **0.097** (0.057) | 0.003 (0.003) | 7.87 (7.88) | **0.076** (0.095) |
| `sar8-bsr2-ssc-carry-f2` | r2 + fill | 7/7 | 0.000 | 0.000 | 8.02 (8.02) | < 0 |
| `sar8-bsr2-ffh-verify-f2` | r2 + fill | 7/7 | 0.005 (0.005) | 0.162, 0.102 without static (same) | 30.08 (30.08) | 0.001 |
| `sar8-bsr2-ffh-extreme-f2` | r2 + fill | 7/8, 1 at −1 | 0.005 (0.006) | 0.161, 0.101 without static (same) | 30.10 (30.10) | 0.001 |
| `sar8-bsr2-ffh-carry-f2` | r2 + fill | 7/7 | 0.000 | 0.103 (0.103) | 30.10 (30.10) | < 0 |
| `sar8-bsr2-tt-verify-f2` | r2 + fill | 7/7 | 0.005 (0.006) | 0.029 (0.029) | 24.58 (24.58) | 0.000 |

- **Limits** (Stage 2): codes within the gain-corrected target ±1, residual and settling ≤ 0.15 LSB, SS-cold read margin ≥ 5 ns, gate screen ≤ 0.1 V. Every collected run passes. At FF hot the settling counts without the static reference-pin offset, as in Stage 2 (VREFN +0.226 mV, VREFP −0.221 mV, unchanged; `-split` jobs).
- **The −1 frames** are the input 0.01 LSB above mid-scale, as in Stage 2.
- **Restart** passes at SS cold, FF hot and TT (`sar8-bsr2-{ssc,ffh,tt}-restart-f2`): 1–2, 8 and 8 compares, reads 83 and 172.
- **Setup and hold** are 443 / 100 ps at SS cold, 178 / 39 ps at FF hot and 246 / 57 ps at TT, the same as Stage 2.

## Gate screen

| Gate job | Bootstrap | Worst frame / channel | At the first compare (V) | Gate-attributable TOP movement (LSB) |
| --- | --- | --- | ---: | ---: |
| `sar8-bsr2-ssc-verify-a-gate` | r2 | 1 / N | 0.082 | 0.017 |
| `sar8-bsr2-ssc-verify-f2-gate` | r2 + fill | 1 / N | 0.077 | 0.017 |
| `sar8-bsr2-ssc-extreme-f2-gate` | r2 + fill | 6 / N | 0.076 | 0.015 |

r2 brings the main-switch gate below 0.1 V about 19 ps sooner than the old core (1.273 against 1.292 ns after the sample close), consistent with the weaker well proximity on Maux and MRSTG.

**Routed CMP_CLK (Stage 6 deck), pending.** With the old core, the Stage 2 session's early Stage 6 runs read 0.1182 V (`sar8-s6e-ssc-verify-c`) and 0.1185 V (`sar8-s6e-ssc-extreme-a`). In that deck the first compare comes at the same 1.297 ns, but the gate starts falling about 25 ps later (onset 0.65 ns against 0.63 ns). Two causes are possible and not separated: the package and VSS network, and the extracted SEQ_SAMPLE wiring. The same runs with the filled r2 (`sar8-s6e-ssc-extreme-r2`, `sar8-s6e-ssc-verify-r2`) are simulating. From the traces, the estimate for r2 is about 0.10 V.

**Disposition rule** (user decisions 2026-11-22; condition 4 revised 2026-11-23). The 0.1 V screen in the specification stays unchanged. The routed r2 runs pass outright if the worst gate screen is ≤ 0.1 V. Otherwise they pass with a written disposition only if all of the following hold:

1. the worst gate screen is ≤ 0.111 V;
2. the gate-attributable TOP movement is ≤ 0.05 LSB;
3. codes are equal and plate settling is within 0.01 LSB of the old-core routed runs;
4. the sample-close residual is within the Stage 6 limit, 0.25 LSB. This replaces "residual unchanged".

If any condition fails, the result goes to the user. `Layout/tools/analysis/gate_disposition.py --pair R2_GATE OLD_RUN OLD_GATE` applies the rule.

- **TOP movement.** Most TOP movement after the first comparator clock is comparator kickback: TOPP − TOPN moves 0.07–0.08 LSB in every run, including runs that pass the screen. The score is the part that follows the gate. It is the same-deck sensitivity (change in TOP movement over change in overdrive) times the run's overdrive.
- **Controls.** `sar8-s6e-ssc-verify-c-gate` and `sar8-s6e-ssc-extreme-a-gate` are the old-core controls in the same deck.
- **Verdict:** pending.

## Fill and the SS-cold residual

| | Old core | r2 | r2 + fill |
| --- | ---: | ---: | ---: |
| ADC residual, SS-cold verify (LSB) | 0.054 | 0.039 | 0.093 |
| Standalone sampling error, SS cold (mV) | −1.116 | −1.135 | −1.158 |

- **Standalone does not reproduce it.** The standalone bench shows no comparable change, so the earlier guess that 8 fF per plate slows settling is not confirmed.
- **Where it is.** In the ADC the increase sits entirely on the channel whose input is at 0.898 V in the full-scale frames, above the 0.81 V supply. There TOP − VIN at the sample close goes from −0.24 mV (r2) to −0.60 mV (r2 + fill), and the boost from 0.775 to 0.770 V. The channel near 0 V is unchanged (+0.066 → +0.056 mV). The standalone step never goes above 0.8 V.
- **Likely cause, unproven.** The added plate capacitance lowers the boost, and the switch is weakest at the top of the input range.
- **Limit.** The residual stays within the Stage 2 limit (0.15 LSB) and the Stage 6 limit (0.25 LSB).

## Runs and hosts

- **Moved to free hosts.** The thu-wei and thu-song queues were blocked on user-cgroup headroom and CPU load. Twelve unstarted runs were cancelled with a recorded reason and resubmitted unchanged under new IDs (revision `f2`) on thu-yuan, thu-tang and thu-shu. Each new deck differs from its original only in the run ID. The hosts were added to the managed runner in chenzc24/sar-adc-t28#34.
- **Rerun after a long queue.** SS-cold carry and the SS-cold and FF-cold standalone runs waited for analysis on thu-wei and were rerun elsewhere (`sar8-bsr2-ssc-carry-f2`, `boot-r2f2-{ssc,ffc}-20261122`). The originals' queued analyses were cancelled at the user's request; their simulations are complete and their waveforms are kept for retention.
- **Not used.** The other prefill runs (`sar8-bsr2-*-a` other than the three above, `boot-r2-{tt,ssh,ffc,ffh}-20261122`) were cancelled before they started, once the requalification moved to the filled configuration.

## Scope and open items

- **Pending:**
  - the routed gate verdict (`sar8-s6e-ssc-{extreme,verify}-r2`, Stage 2 session);
  - the cause of the fill's residual increase.
- **Freeze entry.** `Layout/results/current.json` `integration.freeze` still names `boot-core-20261121`. It changes to r2 once the pending items close.
- **Deterministic runs only.** No mismatch, noise or terminal-voltage verdict.
- **Gate options if the routed screen fails the disposition:** widen Maux/MRSTG (a core change; the FF-hot standalone margin is 0.165 mV), or delay the first comparator clock (a SAR timing change).
- **Waveform retention** follows at closeout.
