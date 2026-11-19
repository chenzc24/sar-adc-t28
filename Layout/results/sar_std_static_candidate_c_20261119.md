# Routed SAR controller with the nine-stage QUIET path

The physical candidate removes the clock latch's discrete QB-to-VSS MOM and keeps all five original standard-delay paths. Its coupled extraction misses the 90 ns interface deadline at SS cold and SS hot. The current candidate does not meet the default-change criterion. [Measurements and identities](sar_std_static_candidate_c_20261119.json)

## Latch and conversion

The NAND gates retain state by static feedback. The QB receiver has 0.197 fF of extracted capacitance to ground and 0.567 fF of coupling, in addition to intrinsic device capacitance. With the MOM removed, schematic runs at TT and SS cold both pass all eighteen words. Their minimum margins to the 90 ns read are 28.80 and 13.51 ns.

At SS cold, first-frame Q and QB continue toggling in opposite directions in the extracted circuit. Six comparisons, writes and updates have occurred at 90 ns. The seventh comparison occurs at 90.089 ns, the eighth at 97.953 ns, and the eighth update is still outstanding at 100 ns. At input code 1 in frame 2, the ADC reads 0 at both 90 and 98 ns. [SS cold analog waveforms](figures/sar_std_qb.png)

For frame 0, the interval from comparison to write changes from 0.424 to 0.712 ns, write to update from 0.698 to 1.245 ns, and update to next comparison from 2.856 to 5.163 ns. The isolated first QUIET DEL250 uses the same 20 ps input, a native inverter load and ideal supply pins for all three comparisons. Its rising propagation delay is 279.95 ps in the foundry schematic, 282.57 ps with extracted transistor geometry alone and 470.99 ps after including cell-internal interconnect. The last case excludes macro routing and external coupling. It identifies an internal-cell contribution that persists with ideal inter-cell wiring.

| Corner | Frame 0 comparisons by 90 ns | Writes by 90 ns | Updates by 90 ns | Eighth update within the frame (ns) |
| --- | ---: | ---: | ---: | ---: |
| TT | 8 | 8 | 8 | 74.405 |
| SSC | 6 | 6 | 6 | >100 or interrupted by sampling |
| SSH | 7 | 7 | 7 | 92.858 |
| FFC | 8 | 8 | 8 | 64.227 |
| FFH | 8 | 8 | 8 | 65.467 |

## Completed eighteen-frame extractions

| Corner | Correct at 90 ns | Correct at 98 ns | Eight updates by 90 ns | Functional timing |
| --- | ---: | ---: | ---: | --- |
| TT | 18/18 | 18/18 | 18/18 | Pass |
| SSC | 7/18 | 8/18 | 0/18 | Fail |
| SSH | 8/18 | 18/18 | 0/18 | Fail |
| FFC | 18/18 | 18/18 | 18/18 | Pass |
| FFH | 18/18 | 18/18 | 18/18 | Pass |

The supply measurements compare each of 18 local sites to the SAR power ports on the same waveform sample. The largest VDD drop and VSS rise can occur at different sites and times. The CDAC column gives the differential weighted bottom-plate bound at the observed comparison edges (budget 0.25 LSB).

| Corner | Peak VDD drop (mV) | Peak VSS rise (mV) | Peak local rail-span loss (mV, site) | CDAC (LSB) | Measured comparisons |
| --- | ---: | ---: | --- | ---: | ---: |
| TT | 13.33 | 15.97 | 28.26, BIT3 | 0.00817 | 144/144 |
| SSC | 9.99 | 11.61 | 21.52, BIT3 | 0.00059 | 144/144 |
| SSH | 9.01 | 10.64 | 18.87, BIT3 | 0.00693 | 144/144 |
| FFC | 19.04 | 23.40 | 40.35, BIT3 | 0.01148 | 144/144 |
| FFH | 23.68 | 25.94 | 46.68, BIT3 | 0.02168 | 144/144 |

The two-frame SS cold test using the measured DEL250 internal wiring at every DEL250 site and ideal inter-cell wires and rails completed eight updates by 90 ns in 0/2 frames. The eighth update occurs at 92.500 and 93.404 ns for input codes 0 and 128. Other standard cells use their schematic models. This is a diagnostic projection using a representative cell, with separate frozen inputs.

A matched first-frame SS cold control places the exact original CQB MOM device between the extracted QB receiver and its local VSS. The same extracted route completes 6 comparisons and 6 updates by 90 ns with the extra device. The sixth comparison shifts by 106.4 ps against the unmodified extraction. This control models the device terminals at the same location and uses an ideal connection to its receiver.

## Layout

Both core and filled macro pass transistor LVS. Calibre DRC reports zero blocking markers and two process advisories. The core has 291 connected nets, 26 ports, nine VDD-to-VSS decaps and 52 functional DEL cells. Its OA box measures 27.185 × 17.375 µm and its sites occupy 84.40% of 472.34 µm². The extracted supply networks contain 7,777 VDD and 7,828 VSS resistors. The eight bit slices repeat along y with the outputs on the west edge. The eight data latches of the 20.190 × 14.610 µm reference repeat along x. [OA floorplans and routed feedback](figures/sar_std_static.png) · [Same-scale M2–M4 comparison](figures/sar_std_reference_routing.png)

The saved project candidate is `SAR_ADC_T28_LAYOUT/sar8_sar_timing_core/layout_std_static`. The filled candidate is `SAR_ADC_T28_LAYOUT/sar8_sar_timing/layout_std_static`. Both matched the simulated private views under polygon XOR. The remaining ADC blocks use transistor schematics in these runs. Local mismatch, full-code linearity, FFT and extracted terminal stress are outside these measurements.

VDD and VSS each have three 0.40 µm M6 feeds. A 0.32 µm M5 strap crosses each shared row rail. The M1-to-M5 ladders and M5-to-M6 connections use 2 × 2 cut arrays. The three feeds join the same macro port on each supply. The extracted transient measurements resolve the drops between those ports and individual device terminals. Package and upper-level power delivery are outside the extraction.

## Rerouting the same circuit

A second placement moves the last QUIET qualifier, clock-set buffer and feedback latch together at the end of the folded chain. All 291 nets connect. The native top-cell metal half-perimeter on QUIET_D falls from 18.450 to 1.420 µm, on CLOCK_Q from 23.210 to 4.425 µm, and on Q1 from 23.905 to 5.595 µm. The total signal-metal indicator falls from 1,281.90 to 1,194.21 µm. Both layouts use the same four-gate clock latch and the same nine QUIET stages. [Three feedback and clock nets before and after rerouting](figures/sar_std_return_routes.png)

To open the rerouted native candidate in Virtuoso on `thu-wei`, use `/server_local_ssd/chenzc_intern25/sar-adc-t28/layout/state/sar-std-route-d-20261119/cds.lib`. The core is `SAR_PLACEMENT_WORK/sar8_sar_timing_core/layout_quiet_return_d` and the filled wrapper is `SAR_PLACEMENT_WORK/sar8_sar_timing/layout_static_return_d`. [GDS and verification archive index](../../results/storage/sar_std_static_candidate_c_20261119.json)

Calibre verified transistor LVS for the core and its foundry-filled wrapper. Native DRC advisories and distributed supply-network counts are recorded in the evidence.

On this shorter route the QB interconnect contributes 0.110 fF to ground and 0.569 fF to other conductors. The corresponding Q values are 0.265 fF and 0.889 fF. MOS intrinsic capacitances are modeled separately.

The extracted DC resistance from the macro power port to each of 18 selected device diffusion terminals spans 38.7–62.9 Ω on VDD and 36.2–56.8 Ω on VSS. The VDD paths to the first QUIET delay and its final qualifier measure 43.2 Ω and 43.7 Ω. These two-terminal measurements leave the other device loads open.

The maintained generator reproduces the four seed inputs byte for byte. Applying its detailed route to a fresh private OA view reproduces the verified core geometry digest. [Placement generator](../design/sar_standard.py)

In frame 0 of the SS cold extraction, the eighth comparison moves from 97.953 to 97.524 ns after rerouting. At 90 ns the rerouted macro has issued 7 comparisons, 6 writes and 6 updates out of eight.

The rerouted extracted SS cold run completes all eight updates by the 90 ns read in 0 of the first three frames. Correct code counts are 2/3 at 90 ns and 2/3 at 98 ns.

For input 1, the LSB comparison occurs at 97.821 ns. Its write occurs at 99.590 ns, after both the 90 ns and 98 ns read strobes. Update counts start at the falling sampling edge of the conversion. A previous conversion can finish just after the nominal 100 ns frame boundary, before the next rising sampling edge.

Across 18 probes in these three SS cold frames, the largest VDD drop was 8.06 mV at GUARD0, and the largest VSS rise was 10.16 mV at GUARD1. The largest simultaneous loss of local VDD–VSS span was 14.85 mV at GUARD1.
