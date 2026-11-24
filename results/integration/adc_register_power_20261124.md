# Preliminary ADC power through the on-chip output register

The nine Stage 6 post-layout short cases give **57.46–393.93 µW** at 10 MS/s. The comparison with 1 mW includes Core VDD, VREF port power and the dedicated DVDD branch at the on-chip output register's supply pin. The register's input delay cells, flip-flops and Q buffers are inside this boundary, including the energy the Q buffers deliver to the pad inputs. The interface budget covers the pad cells' low-voltage supply and VDDIO. [Coverage tracker](https://github.com/chenzc24/sar-adc-t28/issues/60#issuecomment-7125313946) · [Register supply routing](../../Layout/results/chip_objects.md)

## Coverage and waveforms

The cases are verify, extreme and carry at TT, SS cold and FF hot, using the extracted Stage 6 fill5 Core. Each power estimate uses seven complete 100 ns frames after warmup. The three restart runs in the functional matrix exercise an interrupted conversion and have their own timing sequence. [Short functional matrix](https://github.com/chenzc24/sar-adc-t28/issues/12#issuecomment-7093047607)

The Core and reference terms use the original Spectre currents from 159 to 859 ns. The register term comes from a separate native Spectre replay of the measured seven output codes at the same MOS corner. The replay uses the r3 typical extracted output routing, the SAMPLE receiver, the routed register, the output pad device models and 15 pF per board output. It preserves recorded rising-threshold times for high bits and represents input clears with a grouped reset time and 100 ps rising and falling ramps. The clock and register state are primed before measurement. Register supply voltages are 0.90 V, 0.81 V and 0.99 V at the three respective corners. Corresponding VDDIO voltages are 1.80 V, 1.62 V and 1.98 V. [Output fixture and extraction](ffh_board_switching.md) · [Replay builder](../../Layout/experiment/power_hist_20261124/prepare_register_power.py)

## Power calculation

1. **Core and reference.** Integrate the signed currents from the three Core supply probes and the two reference probes to obtain total charge per frame, including static current. Multiply by the corresponding nominal rail voltages. The VREFP source is 0.9 V and the VREFN source is 0 V. Divide the total energy by the combined frame duration. [Charge-to-energy calculation](../../Layout/experiment/power_hist_20261124/frame_power.py) · [Original frame energies](power_s6_frames_20261124.json)
2. **Register.** Divide the saved `DVDD_J − DVDD_REG` voltage by the extracted 16.1 Ω feed resistance to calculate the current into the register. Multiply by `DVDD_REG − VSS` at each saved point and integrate over seven 100 ns cycles. Decode Q at 30% and 70% of the local supply span and check each captured code. Repeat the reduction on every other 5 ps strobe point. [Register pin-power reduction](../../Layout/experiment/power_hist_20261124/measure_register_power.py)
3. **Paired sum.** Add the three average terms for the matched corner and code sequence. Take energy per conversion as the average power divided by 10 MS/s. Each paired result combines the original Core waveform with the separate register replay. [Combination tool](../../Layout/experiment/power_hist_20261124/combine_register_power.py)

## Measured results

| Corner | Sequence | Core VDD (µW) | VREF (µW) | Register supply pin (µW) | Sum (µW) |
| --- | --- | ---: | ---: | ---: | ---: |
| TT | Verify | 51.66 | 21.03 | 2.93 | 75.61 |
| TT | Extreme | 51.97 | 20.78 | 2.76 | 75.51 |
| TT | Carry | 52.03 | 21.67 | 3.35 | 77.04 |
| SS cold | Verify | 36.18 | 19.53 | 1.88 | 57.58 |
| SS cold | Extreme | 36.44 | 19.29 | 1.73 | 57.46 |
| SS cold | Carry | 36.46 | 20.28 | 2.20 | 58.94 |
| FF hot | Verify | 293.10 | 30.71 | 68.22 | 392.03 |
| FF hot | Extreme | 292.63 | 30.38 | 68.34 | 391.35 |
| FF hot | Carry | 293.07 | 30.80 | 70.06 | 393.93 |

The paired sum uses unrounded values. The highest case is FF-hot carry at 393.93 µW, or 39.39 pJ per conversion. All 63 replayed captures decoded correctly. The 10 ps reduction changed the register average by at most 0.0129 µW. The TT and SS-cold replays ran on `thu-tang`. The FF-hot replay ran on `thu-ming`. [Frame data, run identities and result digests](power_with_register_20261124.json)

## Check against the archived eight-bit switching bench

The separate FF-hot output stress transient used 1.98 V VDDIO and 15 pF per output. Reconstruction of the register pin power from the saved DVDD bond current and the frozen bond and bypass network gives 67.851 µW on 0x7F → 0x80 and 71.329 µW on 0x80 → 0x7F. The two-frame register average is 69.590 µW. The original probe upstream of the pad and register branches measured 90.543 µW averaged across the same windows. Taking every other 5 ps point changed the reconstructed averages by at most 0.0057 µW per frame. [Original probe results](ffh_io_power_20261124.json) · [Branch reconstruction results](ffh_register_branch_replay_20261124.json) · [Reconstruction method](../../Layout/experiment/power_hist_20261124/branch_from_old.py)
