# Top-plate PGATE: first T28 local driver

Date: 2026-09-30. Netlist-only experiment; no schematic/OA changes.
This is a functional driver candidate, not an accepted sampling switch.

## Circuit and controlled comparison

Use `screen_top_plate_pgate_driver.py` on top of the exact-source-validated
`screen_top_plate_gmain_hold_device.py` generator. Retain `tg_hold_m4`,
the pump, MN11, CDAC, input sources and external timing unchanged.
Only replace the two ideal PGATE relays with six transistors per side:

| Device | D, G, S, B | Model | multi |
| --- | --- | --- | --- |
| MP15 | PGATE, PGATEB, G, G | pch_18_mac | 1 |
| MP16 | PGATEB, PGATE, G, G | pch_18_mac | 1 |
| MN15 | PGATE, OFF_MAIN, VSS, VSS | nch_18_mac | 4 |
| MN16 | PGATEB, OFFB, VSS, VSS | nch_18_mac | 4 |
| MP17 | OFFB, OFF_MAIN, VDD, VDD | pch_18_mac | 1 |
| MN17 | OFFB, OFF_MAIN, VSS, VSS | nch_18_mac | 1 |

All use the existing exported thick-oxide geometry, L=150 nm, W=320 nm,
nf=1. MP17/MN17 form a real 0.9-V inverter. MP15/MP16 and MN15/MN16
form a cross-coupled level shifter powered from the **existing dynamic G**,
not an added ideal high-voltage rail. In track, OFF_MAIN=0, OFFB is high,
PGATEB is pulled low, and MP15 raises PGATE to G. In hold, OFF_MAIN rises,
MN15 pulls PGATE low and MP16 raises PGATEB to G.

The comparison is against the prior **same multi=4 T28 hold pair with ideal
PGATE steering**, not the fully ideal SHOLD bound or the smaller multi=1
candidate. No size/timing tuning is mixed into this replacement.
The inherited source comment about ideal main-gate steering is historical;
the remaining ideal element is STRACK, not the six-device PGATE network.

## Reproducibility and scope

- Runner: existing `t28_io` SSH Spectre flow; Spectre 21.1.0.509.isr12.
- T28 model: existing crn28ull_1d8_elk_v1d8_2p2_shrink0d9_embedded_usage.scs;
  pre_simu, noise_worst, ttmacro_mos_moscap, tt_res_bip_dio_disres,
  tt_mom, tt_ind_jvar, tt_r_metal sections. No transient noise enabled.
- VDD=0.9 V, VCM=0.45 V, temperature=27 C; unchanged input history.
- Transient: 285 ns, maxstep=10 ps, conservative, reltol=1e-4.
- Oracle at 270 ns: `(TOPP_TOP - TOPN_TOP) - requested differential input`.
  These are uncalibrated deterministic errors, not noise or ENOB results.
- Original OA-export SHA256:
  `965cbc2f99712c0f5d72af0eefcf28abdf398340f31cff32d96a0e1fd36e50ac`.
- Generated copied decks, deck hashes, per-point JSON, simulator logs and
  PSF are under `output/top_plate_pgate_driver/` (ignored artifacts).
- Saved: original top/CDAC/control signals and hold-device currents, plus
  G, PGATE, PGATEB, OFFB, VDD and all six new devices' terminal currents.
  Analysis validates time monotonicity, finite/aligned vectors, phase order,
  six pairwise device voltages over the full run and warning inventory.

Example (workspace Python; run from repository root):

```powershell
E:/bridge-Agent-T28/.venv/Scripts/python.exe scripts/characterization/screen_top_plate_pgate_driver.py --vdiff 0.8
```

`--analyze-only` verifies the saved deck still matches the generator before
re-reading PSF. Ratios 1 and 8 are available for a bounded switching-failure
screen but are not evidence unless actually run. The ratio-4 candidate
switches, so no ratio sweep is justified by switching failure.

## Measured behavior and limits

Five completed nominal runs (signed raw error, mV):

| Differential input (V) | Same hold pair, ideal PGATE | T28 PGATE driver |
| --- | ---: | ---: |
| -0.8 | +0.279944 | -0.080368 |
| -0.4 | +0.842425 | +0.605518 |
| 0 | approximately 0 | approximately 0 |
| +0.4 | -0.842425 | -0.605518 |
| +0.8 | -0.279944 | +0.080368 |

Worst absolute error falls approximately 28% to **0.605518 mV**, but
still exceeds the **0.439-mV** allocation. All five completed with zero
Spectre errors, four existing SFE-1131 duplicate-scope model warnings per
run, zero printed CMI and zero suppressed warnings. The -0.4-V point
required recovery from an upload timeout and a truncated download;
only the final complete zero-error run and validated PSF enter this table.
The parser's spurious `units` vector notice is not a circuit warning;
the numeric waveform arrays pass finite/aligned checks.

At +0.8 V, PGATE at 249.7 ns follows G within 0.27 microvolt on both
sides. G is 1.615895/0.804614 V, versus the matched ideal-driver tracked
PGATE (=G) of 1.606702/0.812184 V. Thus the new circuit perturbs the pump
by approximately +9.19/-7.57 mV; it is not a load-free ideal replacement.

PGATE is below 10 mV on both sides by approximately 250.44 ns, before
the 251.3-ns nominal BOOT reset. At 251.28 ns, the +0.8-V case has
GMAIN-VIN approximately 0.287/0.041 mV. At +0.4 V, PGATE on the high
side is still 2.723 mV at this checkpoint, and GMAIN is 0.650357 V.
Settled 270-ns GMAIN is close to VIN, but that does not undo the earlier
charge disturbance at the sampled top nodes.

The largest new-device pairwise voltage in the +0.8-V full run is about
1.650 V. **Absence of CMI warnings is not reliability clearance.** In
particular, MP16's drain PGATEB remains high while its source/body G is
reset. Its positive drain-to-body voltage peaks near 0.497 V. For the
P-side in the +0.8-V case this occurs at about 251.516 ns. At 251.8 ns,
PGATEB/G are approximately 0.3925/0.0574 V; at 270 ns they are still
0.2563/0.0697 V. This is a forward-junction-bias risk and an internal
reset/memory concern, even though the output PGATE is low. It has not
been demonstrated to be the dominant cause of final sampling error.

Do not infer accuracy throughout conversion from only the final value:
at +0.4 V the pre-reset differential error is -22.838 mV, changing to
-0.606 mV after the existing reference/base transition. The oracle and
reference phase are unchanged from the baseline; this is not a newly
introduced measurement path. Full conversion and aperture tests remain due.

## Remaining ideal boundaries and next decision

STRACK (G to GMAIN), external PHI/OFF_MAIN/PHIB sources, and CDAC reference
switches are still ideal. MP14's body-at-GMAIN connection and the new
dynamic-G wells require actual well/isolation/reliability review. This is
not a fully transistorized bootstrap control or ADC.

Next isolate the PGATEB reset problem: test a reset-aware discharge path
that clears PGATEB without shorting the active boosted rail or turning
MP14 on during track. Then reassess the midrange sampling step with a
one-factor hold-pair size/edge experiment. Keep STRACK implementation as
the following separate target. Do not promote this candidate into OA or
freeze dimensions based on endpoint accuracy alone.
