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
- **Package:** 2 nH and 0.2 Ω per wire bond, 0.5 pF pad. VREFP and VREFN get two bonds each on adjacent pads in the order VREFP, VREFN, VREFP, VREFN, modelled as 1 nH (0.5–1.5 nH) and 0.1 Ω per rail without crediting the mutual inductance. One VDD/VSS pair per branch (analog, reference pair, digital). Double reference bonds were accepted on 2026-11-21; the 6 × 6 IO ring is a draft and needs two more pads for them.
- **On-chip reference network:** a 15 Ω series resistor per rail between the pads and the CDAC reference trunk, and 8 pF between VREFP and VREFN at the trunk.

The CDAC draws equal and opposite charge from the two rails, so decoupling between VREFP and VREFN works four times better per area than the same total split to ground. VREFN sits at 0 V, so an NMOS gate on VREFN does not invert, and no capacitor goes from VREFN to VSS. A capacitor between the rails must also keep its substrate coupling to VSS small, because VSS bounce on one rail appears as a differential reference error.

## Why the Reference Needs Damping

Each response below superposes the calibrated update charges, as 0.5 ns and 0.8 ns triangles, on the differential VREFP–VREFN loop. These two widths bracket the measured fixture droop and peak current. The error is read at each comparator edge with the shortest measured update-to-compare interval (2.14 ns at FF cold, 2.55 ns at TT, 3.63 ns at SS cold). A span error d moves the decision by d·(trial−128)/0.9 V in LSB.

| Network | Worst decision error (LSB) | Span droop (mV) |
| --- | ---: | ---: |
| 50 Ω / 4 pF fixture, TT (measured codes) | 0.001 | 333 (measured 260) |
| Single 2 nH bonds, 8 pF between the rails, no series resistor, FF cold | 3.56 | — |
| Single bonds, 20 Ω / 6 pF, FF cold / tolerance box at FF cold | 0.025 / 0.105 | 153 / ≤192 |
| Budgeted network, double bonds, 15 Ω / 8 pF, FF cold / TT / SS cold | 0.028 / 0.011 / 0.004 | 109 |
| Budgeted network, tolerance box, FF cold / TT / SS cold | 0.040 / 0.019 / 0.004 | ≤143 |

Without a series resistor, an undamped decap behind the 2 nH bonds rings at each update: 2.7–4.9 LSB with 8 pF between the rails and 3.3–7.3 LSB with the 8 pF placeholder split to ground. With 0.2 nH flip-chip pins the same undamped 8 pF would pass (0.005 LSB at FF cold), so the damping is needed for wire bonds. The series resistor makes the trunk an RC that refills within the update-to-compare interval, as the qualified fixture does. Too slow an RC also fails: with single bonds, 25 Ω with 8 pF reaches 0.35 LSB in the slow tolerance corner. The tolerance box spans series R ×0.8–1.2, decoupling ×0.75–1.25 and 0.5–1.5 nH per rail. With single bonds (1–3 nH) its worst FF-cold corner gave 0.105 LSB. The double bonds bring the worst case to 0.040 LSB, and they allow 8 pF, which lowers the span droop by about 30%.

## Limits

Stage 6 measures each quantity with the system model at every corner and frame. The allowance of 1.3 on TT charge covers FF 0.99 V and top-level extraction.

| Limit | Value | Basis |
| --- | ---: | --- |
| `reference_charge_per_conversion_C`, per rail | 3.7 pC | Model maximum 2.85 pC × 1.3; mean 2.05 pC |
| `reference_event_charge_C`, any 1 ns window | 1.9 pC | Model maximum 1.46 pC × 1.3; measured 1.31 pC |
| `reference_pin_peak_current_A`, per rail (both bond pins) | 5.1 mA | Model 3.25 mA, tolerance box 4.25 mA, × 1.2 |
| `reference_span_droop_V`, at the CDAC trunk | 0.26 V | Measured 259.8 mV in the qualified TT run; model 109 mV, box ≤143 mV |
| `reference_decision_error_LSB`, each comparator edge | 0.10 LSB | Top-level share of the 0.15 → 0.25 LSB plate-settling step; the plate-settling limit stays authoritative |
| `supply_charge_per_conversion_C`, whole core | 6.9 pC | Measured 5.26 pC × 1.3 |
| `supply_event_charge_C`, any 1 ns window | 1.1 pC | Measured 0.81 pC × 1.3 |
| `supply_pin_peak_current_A`, sum of VDD pins | 5.5 mA | Measured 3.70 mA × 1.48 (FF-cold/TT XREF supply-peak ratio) |
| `supply_droop_V`, VDD−VSS at each block | 45 mV | 5% of 0.9 V; timing and settling criteria stay authoritative |

The reference-induced decision error is the signed TOP error against nominal rails minus the same error against the instantaneous trunk rails. At these limits the core draws at most 37 µA from each reference and 69 µA from VDD, about 0.1 mW in total.

## On-Chip Decoupling

Each VDD branch sees its own events behind a 2 nH / 0.2 Ω pin pair. The largest measured 1 ns VDD event splits into about 1.9 fC per toggled unit from the XREF drivers (0.48 pC for 255 units) and about 0.31 pC from the SAR COMMIT and DONE logic. No 1 ns window at a sampling edge exceeded 0.454 pC, which bounds the Bootstrap event. The model applies the 1.3 allowance and a 0.5 ns pulse.

| Rail or branch | Earlier placeholder | Required | Floorplan regions (2026-11-21) | Feed resistance | Modelled droop (mV) |
| --- | ---: | ---: | --- | ---: | ---: |
| VREFP–VREFN | 8.03 pF, 4 pF per rail | 8 pF between the rails, ±25% | `vref_decap_west` (extended to y 75.2) + `vref_decap_south`, 8.58 pF of area including the two series resistors | 15 Ω per rail, ±20% | 109 span |
| XREF / pair VDD | 2.92 pF | 10 pF | `xref_decap` + `xref_decap_east` + `pair_decap_southeast`, 10.07 pF | 12 Ω | 40 |
| Comparator local | 2 × 0.236 pF | 0.47 pF | `comparator_decap_west`/`east`, unchanged | 30 Ω in-core straps | 24 |
| Analog bulk, Bootstrap | 1.56 pF | 9 pF (upper-bound event) | `analog_decap_slot` + `analog_decap_west` + `analog_decap_east`, 9.32 pF | 12 Ω | 40 |
| SAR VDD | 5.55 pF, optional | 8 pF, required | `sar_supply_and_decap` (extended to y 24.5) + `sar_decap_north`, 8.25 pF, plus the macro DCAP fillers | 5 Ω | 28 |

The floorplan on `layout/toplevel-floorplan` holds these regions in free core area, with the 122 × 111 µm outline, the block placement and the planned signal routes unchanged. `spare_decap_northeast` (about 12.7 pF) stays free for whichever branch Stage 2 or Stage 6 shows short. The feed resistance damps each branch against its pin inductance, and the DC drop it adds stays below 0.3 mV. [Decoupling issue](https://github.com/chenzc24/sar-adc-t28/issues/15)

## Merit of More Decoupling

Stage 6 extracts the ADC core without the IO ring, so the core meets the budget on its own. Results are at FF cold:

| Option | Result | Verdict |
| --- | --- | --- |
| Double-bonded VREFP and VREFN (0.5–1.5 nH) | Tolerance-box worst 0.105 → 0.039 LSB for 20 Ω / 6 pF; re-centred at 15 Ω / 8 pF, 0.040 LSB with 29% less span droop | Adopted. Two pads per rail, interleaved; the 6 × 6 draft ring needs two more pads, for example a 7 × 7 ring (580 → 640 µm) |
| More trunk capacitance than 8 pF between VREFP and VREFN | With single bonds, 15 Ω / 8 pF reached 0.22 LSB over the box; with double bonds, on the corners of the box, 12 Ω / 10 pF gives 0.041 LSB and 10 Ω / 12 pF 0.054 LSB (15 Ω / 8 pF: 0.028), for 18–29% less droop and 25–50% more area | No |
| Reference bulk at the pads, ahead of the series resistors | It droops by Q/C at each update and refills slowly: 0.15–0.96 LSB for 30–335 pF undamped, 0.08–0.30 LSB with 1–5 Ω ESR, against 0.025 LSB without it (single bonds) | No |
| About 100 pF AVDD bulk per branch at the pads, 2 Ω ESR, ≤6 Ω feed | Droop 40 → 25 mV (pair, analog) and 28 → 13 mV (SAR); pin peaks halved; 190 pF adds little | Yes, for the chip-level ring |

## Limitations

- The measured frames are one TT run with four codes, a schematic sampler and an ideal VDD source. Corner and extraction effects enter only through the 1.3 allowance. The Stage 2 all-extracted runs should confirm the charge at SS cold and FF hot.
- The rail responses are linear loop models with triangular charge pulses, not Spectre runs of the network. Stage 6 must simulate the extracted reference trunk, resistors and decoupling with the package.
- The Bootstrap branch event is bounded, not measured, and no VDD measurement is split by branch. Size the analog slot again when branch currents are available.
- Decoupling density, leakage and device choice need the PDK decap characterization. Thin-oxide gate leakage between the rails is a DC load: through 2 × 15 Ω it shifts gain, not linearity.
- The double-bond model halves the inductance and credits no mutual inductance. Wires sharing one pad couple strongly and give less reduction, which is why the reference uses two separate, interleaved pads per rail. Stage 6 needs the actual bond geometry.
