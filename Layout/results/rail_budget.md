# Reference and Supply Current Budget (Stage 1)

This record sets the reference and supply limits that the Stage 6 top-level checks of [chenzc24/sar-adc-t28#12](https://github.com/chenzc24/sar-adc-t28/issues/12) pass or fail against, and the on-chip decoupling those limits assume. The limits and the Stage 6 system model live in [constraints.json](../specs/constraints.json) (`electrical_budgets` and `stage6_supply_model`). [Model output](rail_budget.json) · [Budget tool](../tools/analysis/rail_budget.py) · [Rail charge analyzer](../../tools/saradc/measure/rail_charge.py)

## Measured Rail Charge

`stage1-rail-charge-adc-post-b` and `stage1-rail-window-adc-post-b` are analysis-only runs on the retained waveform of `se-xref-adc-post-b`: the four-frame TT ADC (0.9 V, 27 °C) with the coupled XREF/CDAC extraction, cell-LPE digital cells, the four-finger schematic sampler, an ideal VDD source and the 50 Ω / 4 pF reference fixture. The reference source charge is read across the fixture resistors and corrected for the change of bypass charge, so it is the die-side charge. Frame 0 starts from the DC solution and is not scored.

| Frame | Code | VREFP charge (pC) | VDD charge (pC) | Peak VREFP / VDD source current (mA) | Span droop (mV) | Largest 1 ns VREFP / VDD charge (pC) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 (DC start) | 6 | 2.598 | 5.152 | 2.134 / 3.109 | 213.7 | 1.018 / 0.613 |
| 1 | 127 | 2.799 | 5.259 | 2.601 / 3.620 | 259.8 | 1.313 / 0.812 |
| 2 | 128 | 1.427 | 4.641 | 1.195 / 3.703 | 119.4 | 0.576 / 0.454 |
| 3 | 249 | 1.251 | 4.656 | 1.354 / 2.999 | 135.3 | 0.735 / 0.560 |

VREFN returns the VREFP charge to within 0.1% in every frame. Almost none of the reference charge flows while SAMPLE is high: the eighth COMMIT registers DONE, which re-asserts PRESET while TOP still floats, and sampling then moves no bottom plate. The largest events are this PRESET after a full reversal (frame 1) and the first update after the MSB decision. The comparator draws about 25 fC per decision with 0.3–0.4 mA peaks ([comparator record](comparator.md)).

## Reference Charge over All Codes

The ideal charge of the flat binary CDAC (4.004 fF units, 60 fF fixed TOP load per side, PRESET word 0x80, complementary P/N banks) reads 1.6–1.9 times low against the measured frames. The difference scales with the number of toggled units: 2.13 fC per unit, about 1.9 fF of extracted bottom-plate, junction and switch-overlap load per 4 fF unit. With this term the model is within 5% of every measured frame and 11% above the measured largest event.

| Quantity, per rail | Value |
| --- | ---: |
| Charge per conversion, maximum (code 127) | 2.85 pC |
| Charge per conversion, minimum | 1.17 pC |
| Charge per conversion, mean over codes and for a −1 dBFS sine | 2.05 pC (20.5 µA, 18 µW at 10 MS/s) |
| Largest single event (PRESET after a full reversal) | 1.46 pC |

## Stage 6 System Model

Chosen on 2026-11-21. It replaces the reference fixture in the Stage 6 checks only; block tests and Stage 2 keep the 50 Ω / 4 pF fixture.

- **Off-chip source:** ideal 0.9 V and 0 V references and the corner VDD, each with 1 Ω output resistance and a 100 nF ceramic at the pin (10 mΩ ESR, 0.5 nH ESL).
- **Package:** 2 nH and 0.2 Ω per wire bond, 0.5 pF pad. VREFP and VREFN get two bonds each on adjacent pads in the order VREFP, VREFN, VREFP, VREFN, modelled as 1 nH (0.5–1.5 nH) and 0.1 Ω per rail without crediting the mutual inductance. Each branch (analog, reference pair, SAR) has its own AVDD/AVSS pad pair, and on the 9 × 9 ring of #23 all AVDD/AVSS pads also share the TACVDD/TACVSS bus ([Pad Ring](#pad-ring-9--9)). Double reference bonds were accepted on 2026-11-21. Both pads load each reference rail, 2 × 0.5 pF = 1.0 pF.
- **Pad-to-core reference routes (9 × 9 ring):** each rail's two routes run in parallel ahead of the series resistor: VREFP 297.9 and 317.9 µm, VREFN 263.9 and 371.9 µm, 4 µm wide. On M8 at 0.022 Ω/sq (PDK tech LEF, 25 °C) they add 0.85 Ω per rail, 0.27 pF to substrate and, scaling the earlier assumption with length, 0.17 nH. The tolerance box spans 0.14 Ω (M9, −40 °C) to 1.20 Ω (M8, 125 °C, rcworst thickness). The 7 × 7 plan had 144–252 µm routes and a 0–2 Ω bracket.
- **On-chip reference network:** on each rail both pads join ahead of a 15 Ω series resistor, which feeds the CDAC reference trunk (`VREFP_TRUNK`, `VREFN_TRUNK`). 8 pF sits between the two trunks.

The CDAC draws equal and opposite charge from the two rails, so decoupling between VREFP and VREFN works four times better per area than the same total split to ground. VREFN sits at 0 V, so an NMOS gate on VREFN does not invert, and no capacitor goes from VREFN to VSS. A capacitor between the rails must also keep its substrate coupling to VSS small, because VSS bounce on one rail appears as a differential reference error.

The network belongs in the netlist, not only in the floorplan: `design/top/adc_top.scs` takes VREFP and VREFN straight to the CDAC. A core wrapper holds `RREFP`, `RREFN` and `CREF` and instantiates the unchanged `sar_adc8_join_r4` on the trunk nets (`stage6_supply_model.on_chip_reference.netlist`). Stage 2 keeps testing the inner cell with its fixture. The Stage 6 pre-layout netlist uses ideal elements at the budget values. The extracted wrapper replaces them with the drawn resistors, decoupling and routes, and the LVS source names the PDK devices once the decap characterization picks them.

## Why the Reference Needs Damping

Each response below superposes the calibrated update charges, as 0.5 ns and 0.8 ns triangles, on the differential VREFP–VREFN loop. These two widths bracket the measured fixture droop and peak current. The error is read at each comparator edge with the shortest measured update-to-compare interval (2.14 ns at FF cold, 2.55 ns at TT, 3.63 ns at SS cold). A span error d moves the decision by d·(trial−128)/0.9 V in LSB.

| Network | Worst decision error (LSB) | Span droop (mV) |
| --- | ---: | ---: |
| 50 Ω / 4 pF fixture, TT (measured codes) | 0.001 | 333 (measured 260) |
| Single 2 nH bonds, 8 pF between the rails, no series resistor, FF cold | 3.56 | — |
| Single bonds, 20 Ω / 6 pF, FF cold / tolerance box at FF cold | 0.025 / 0.105 | 153 / ≤192 |
| Budgeted network, double bonds, 15 Ω / 8 pF, with pads and 9 × 9 routes, FF cold / TT / SS cold | 0.030 / 0.012 / 0.004 | 113 |
| Budgeted network, tolerance box, FF cold / TT / SS cold | 0.043 / 0.020 / 0.004 | ≤148 |

Without a series resistor, an undamped decap behind the 2 nH bonds rings at each update: 2.7–4.9 LSB with 8 pF between the rails and 3.3–7.3 LSB with the 8 pF placeholder split to ground. With 0.2 nH flip-chip pins the same undamped 8 pF would pass (0.005 LSB at FF cold), so the damping is needed for wire bonds. The series resistor makes the trunk an RC that refills within the update-to-compare interval, as the qualified fixture does. Too slow an RC also fails: with single bonds, 25 Ω with 8 pF reaches 0.35 LSB in the slow tolerance corner. The tolerance box spans series R ×0.8–1.2, decoupling ×0.75–1.25, 0.5–1.5 nH per rail and 0.14–1.20 Ω of route per rail. With single bonds (1–3 nH) its worst FF-cold corner gave 0.105 LSB. The double bonds bring the worst case to 0.043 LSB, and they allow 8 pF, which lowers the span droop by about 30%. Counting both pads per rail and the pad-to-core routes (#18) with a 0–2 Ω bracket had moved the worst case from 0.040 to 0.048 LSB. The 9 × 9 routes are about 120 µm longer, but the PDK sheet resistance puts them at 0.14–1.20 Ω, inside the old bracket, so the worst case falls back to 0.043 LSB. At TT and SS cold the worst corner now sits at the low end of the route range, where the RC damps least.

## Limits

Stage 6 measures each quantity with the system model at every corner and frame. The allowance of 1.3 on TT charge covers FF 0.99 V and top-level extraction.

| Limit | Value | Basis |
| --- | ---: | --- |
| `reference_charge_per_conversion_C`, per rail | 3.7 pC | Model maximum 2.85 pC × 1.3; mean 2.05 pC |
| `reference_event_charge_C`, any 1 ns window | 1.9 pC | Model maximum 1.46 pC × 1.3; measured 1.31 pC |
| `reference_pin_peak_current_A`, per rail (both bond pins) | 5.2 mA | Model 3.25 mA, tolerance box 4.33 mA, × 1.2 |
| `reference_span_droop_V`, at the CDAC trunk | 0.26 V | Measured 259.8 mV in the qualified TT run; model 113 mV, box ≤148 mV |
| `reference_decision_error_LSB`, each comparator edge | 0.10 LSB | Top-level share of the 0.15 → 0.25 LSB plate-settling step; the plate-settling limit stays authoritative |
| `supply_charge_per_conversion_C`, whole core | 6.9 pC | Measured 5.26 pC × 1.3 |
| `supply_event_charge_C`, any 1 ns window | 1.1 pC | Measured 0.81 pC × 1.3 |
| `supply_pin_peak_current_A`, sum of VDD pins | 5.5 mA | Measured 3.70 mA × 1.48 (FF-cold/TT XREF supply-peak ratio) |
| `supply_droop_V`, VDD−VSS at each block | 45 mV | 5% of 0.9 V; timing and settling criteria stay authoritative |

The reference-induced decision error is the signed TOP error against nominal rails minus the same error against the instantaneous trunk rails. At these limits the core draws at most 37 µA from each reference and 69 µA from VDD, about 0.1 mW in total.

## On-Chip Decoupling

Each VDD branch sees its own events behind a 2 nH / 0.2 Ω pin pair. The largest measured 1 ns VDD event splits into about 1.9 fC per toggled unit from the XREF drivers (0.48 pC for 255 units) and about 0.31 pC from the SAR COMMIT and DONE logic. No 1 ns window at a sampling edge exceeded 0.454 pC, which bounds the Bootstrap event. The model applies the 1.3 allowance and a 0.5 ns pulse.

| Rail or branch | Earlier placeholder | Required | Floorplan regions (2026-11-21) | Feed resistance | Modelled droop, core alone (mV) |
| --- | ---: | ---: | --- | ---: | ---: |
| VREFP–VREFN | 8.03 pF, 4 pF per rail | 8 pF between the rails, ±25% | `vref_decap_west` (extended to y 75.2) + `vref_decap_south`, 8.58 pF of area including the two series resistors | 15 Ω per rail, ±20%, plus the pad-to-core routes | 113 span |
| XREF / pair VDD | 2.92 pF | 10 pF | `xref_decap` + `xref_decap_east` + `pair_decap_southeast`, 10.07 pF | 12 Ω | 40 |
| Comparator local | 2 × 0.236 pF | 0.47 pF | `comparator_decap_west`/`east`, unchanged | 30 Ω in-core straps | 24 |
| Analog bulk, Bootstrap | 1.56 pF | 9 pF (upper-bound event) | `analog_decap_slot` + `analog_decap_west` + `analog_decap_east`, 9.32 pF | 12 Ω | 40 |
| SAR VDD | 5.55 pF, optional | 8 pF, required | `sar_supply_and_decap` (extended to y 24.5) + `sar_decap_north`, 8.25 pF, plus the macro DCAP fillers | 5 Ω | 28 |

The pair supply enters at its own M6 terminals on the XREF strip, VSS at (45.215, 13.365) and VDD at (46.915, 14.565) µm in core coordinates. It runs south into `xref_decap` and east through `xref_decap_east` to `pair_decap_southeast`. The earlier plan to extend the M5 access rails east would have put about 35 µm of metal inside the CDAC array keep-out (#18). The floorplan on `layout/toplevel-floorplan` holds these regions in free core area, with the 122 × 111 µm outline, the block placement and the planned signal routes unchanged. `spare_decap_northeast` (about 12.7 pF) stays free for whichever branch Stage 2 or Stage 6 shows short. The feed resistance damps each branch against its pin inductance, and the DC drop it adds stays below 0.3 mV. [Decoupling issue](https://github.com/chenzc24/sar-adc-t28/issues/15)

## Pad Ring (9 × 9)

The ring of #23 puts every AVDD/AVSS pad on PVDD3AC/PVSS3AC. Their pads form one TACVDD/TACVSS bus from `right_8` over the top side to `left_6`. The three branches therefore join through the bus as well as on the board (AVDD 3 bonds, AVSS 7), while their in-core meshes stay separate. In the 9-metal `tphn28hpcpgv18` LEF the bus is 33.7 µm (TACVDD) and 34.2 µm (TACVSS) wide on each of M3–M7, at 0.428 Ω/sq per layer. That gives each rail 0.15 Ω per 60 µm pad pitch at 25 °C and 0.19 Ω at 125 °C rcworst. As coplanar strips 2.2 µm apart, the pair carries about 0.4 nH/mm of loop inductance. [Ring and coupling results](rail_budget.json) (`pad_ring`) · [Model](../tools/analysis/ring_supply.py)

**Branch feeds at 10 µm on M8.** The 6 Ω limit runs from the pad bulk to the block decoupling: the ring feed below plus the in-core strap.

| Branch | Pad bulk | Pad → bulk, VDD / VSS (µm) | Bulk → ADC pin, VDD / VSS (µm) | Bulk → pin, loop (Ω), 25 °C / 125 °C rcworst | Pad → pin, loop (Ω), 125 °C rcworst | Left for the in-core strap (Ω) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Analog | 114.2 pF | 102 / 102 | 16 / 16 | 0.07 / 0.10 | 0.73 | 5.9 |
| Pair | 113.6 pF | 420 / 484 | 7 / 7 | 0.03 / 0.04 | 2.85 | 6.0 |
| SAR | 132.2 pF | 122 / 142 | 79 / 122 | 0.44 / 0.63 | 1.45 | 5.4 |

At 10 µm the ring part of the feed takes at most 0.63 Ω, so the in-core strap sets the margin. On M2–M7 (0.43 Ω/sq at 25 °C, 0.54 Ω/sq at 125 °C rcworst) the remaining 2.7 Ω per rail is only about five squares. The in-core feeds therefore stay on M8/M9 (at most 0.031 Ω/sq, about 87 squares) down to via stacks at each decap region. Even counted from the pad, the longest path (pair, 918 µm of loop) is 2.85 Ω. The minimum M8 widths at 125 °C rcworst are 4.8 µm for the pair's pad-to-pin path to stay under 6 Ω, and 6.3 µm for the SAR's bulk-to-pin feed to stay under 1 Ω (1.2 µm with M8 and M9 stacked).

**Droop and coupling.** All three branches fire on the same FF-cold updates, the worst alignment, with the 1.3 allowance. Droop at each block (mV, limit 45):

| Case | Analog | Pair | SAR |
| --- | ---: | ---: | ---: |
| Per-branch pads (no bus), 6 Ω feed | 18.6 | 19.9 | 13.7 |
| Shared bus, 6 Ω feed, 25 °C / 125 °C rcworst | 17.8 / 17.8 | 19.4 / 19.5 | 13.9 / 13.9 |
| Shared bus, 1 Ω in-core strap, 25 °C / 125 °C rcworst | 10.1 / 10.1 | 11.7 / 11.9 | 9.4 / 9.6 |

Coupling through the bus, peak / at the comparator edges (mV):
- **SAR → analog:** 1.5–2.0 / ≤0.3.
- **Pair → analog:** 1.1–1.5 / ≤0.35.
- **Analog → SAR:** 2.1–2.9 / ≤0.46.
- **SAR → pair:** 0.6–0.8 / ≤0.2.

For scale, 5–7 mV of in-core strap bounce on the comparator supply changed no decision, delay or kickback ([comparator supply diagnostic](comparator.json), `supply_diagnostic`). The SAR is idle at the sampling edge, so its coupling does not reach the Bootstrap at the instant it samples.

The reference pads see the bus through their pad capacitance. A bound puts each VREFP pad's 0.5 pF entirely on TACVDD and each VREFN pad's on TACVSS, the differential worst case. It gives 0.0002 LSB at the comparator edges, and a mismatched secondary ESD diode on the trunk adds less than 0.0001 LSB per 0.1 pF. The 15 Ω / 8 pF trunk refills in 0.24 ns, so coupled charge is gone well before the next edge.

The per-branch model still holds for each block's own droop: the bus moves it by at most 1.3 mV, mostly down. The bus term the model needs is the cross-branch coupling above. With the SAR on the analog pad domain, that coupling stays under the level the comparator already tolerated.

## Merit of More Decoupling

Stage 6 extracts the ADC core without the IO ring, so the core meets the budget on its own. Results are at FF cold:

| Option | Result | Verdict |
| --- | --- | --- |
| Double-bonded VREFP and VREFN (0.5–1.5 nH) | Tolerance-box worst 0.105 → 0.039 LSB for 20 Ω / 6 pF; re-centred at 15 Ω / 8 pF, 0.040 LSB with 29% less span droop; 0.043 LSB with the pads and the 9 × 9 routes | Adopted. Two pads per rail, interleaved (`left_1`–`left_4` of the 9 × 9 ring) |
| More trunk capacitance than 8 pF between VREFP and VREFN | With single bonds, 15 Ω / 8 pF reached 0.22 LSB over the box; with double bonds, on the corners of the box and before the pad and route terms, 12 Ω / 10 pF gives 0.041 LSB and 10 Ω / 12 pF 0.054 LSB (15 Ω / 8 pF: 0.028), for 18–29% less droop and 25–50% more area | No |
| Reference bulk at the pads, ahead of the series resistors | It droops by Q/C at each update and refills slowly: 0.15–0.96 LSB for 30–335 pF undamped, 0.08–0.30 LSB with 1–5 Ω ESR, against 0.025 LSB without it (single bonds) | No |
| About 100 pF AVDD bulk per branch at the pads, 2 Ω ESR per rail, ≤6 Ω loop feed to the block | With the 9 × 9 ring's planned 114–132 pF at the full 6 Ω feed, droop 40 → 20 mV (pair), 40 → 18 mV (analog) and 28 → 13 mV (SAR); pin peaks roughly halved; 190 pF adds little | Yes; planned on the 9 × 9 ring (`pad_bulk_decoupling`) |

## Limitations

- The measured frames are one TT run with four codes, a schematic sampler and an ideal VDD source. Corner and extraction effects enter only through the 1.3 allowance. The Stage 2 all-extracted runs should confirm the charge at SS cold and FF hot.
- The rail responses are linear loop models with triangular charge pulses, not Spectre runs of the network. Stage 6 must simulate the extracted reference trunk, resistors and decoupling with the package.
- The Bootstrap branch event is bounded, not measured, and no VDD measurement is split by branch. Size the analog slot again when branch currents are available.
- Decoupling density, leakage and device choice need the PDK decap characterization. Thin-oxide gate leakage between the rails is a DC load: through 2 × 15 Ω it shifts gain, not linearity.
- The double-bond model halves the inductance and credits no mutual inductance. Wires sharing one pad couple strongly and give less reduction, which is why the reference uses two separate, interleaved pads per rail. Stage 6 needs the actual bond geometry.
- The pad capacitance is the planning value of 0.5 pF per pad, not the PDB3AC model. The route resistance uses the tech-LEF sheet resistance at 25 °C with the iRCX temperature coefficients and rcworst thickness; vias, pin landings and the pad cell's own metal are not included. The model lumps each rail's two routes in parallel; their unequal lengths only change the current split between the two bonds.
- The pad-ring model takes the bus widths from the M3, M5 and M7 strips of the IO LEF and assumes M4 and M6 match. It places the bus centreline about 55 µm inside the die edge, assumes 10 µm M8 routes and feeds, and neglects the resistance inside each PVDD3AC/PVSS3AC cell between its pad and core port. Every branch fires on the same instants, which overstates the coupling at any single block.
