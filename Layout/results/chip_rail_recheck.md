# Chip Rail Budget with the Drawn Pad Decoupling

2026-11-23, chenzc24/sar-adc-t28#12. The Stage 1 supply models rerun on the current chip view `sar8_adc_chip/layout_full_fill5_r3`, with the drawn pad bulk in place of the planned one. [Record](chip_rail_recheck.json) · [Chip objects](chip_objects.md) · [Stage 4b rail budget](toplevel_route_full.md#rail-budget-with-the-drawn-values)

`Layout/tools/analysis/chip_rail_recheck.py` runs the per-branch model (`rail_budget.supply_check`) and the coupled-ring model (`ring_supply.chip`: shared TACVDD/TACVSS bus, all branches firing on the same FF-cold updates, 125 C rcworst). Stage 4b supplies the in-core drawn decoupling and loops; the core views since then keep the supply routing of `layout_route_full`. Inputs replaced by drawn values (`chip_objects.json`):

- pad bulk and its ESR model per rail: analog `layout_r3`, pair and SAR `layout_r2`;
- ring feed, pad to bulk and bulk to pin, at 125 C rcworst.

Both models take these through optional arguments that default to the Stage 1 values. With the planned inputs they reproduce the Stage 4b droop exactly.

**Supply droop, VDD-VSS at each block** (limit 45 mV; FF-cold timing, the 1.3 charge allowance):

| Branch | Drawn pad bulk, ESR per rail | Bulk to pin (loop) | Stage 4b, planned bulk | Drawn bulk | Drawn bulk, ESR 1 ohm per rail | Coupled ring, drawn |
| --- | --- | --- | --- | --- | --- | --- |
| Analog | 92.9 pF, 2.25 ohm | 0.14 ohm | 17.1 mV | **17.9 mV** | 15.1 mV | 16.6 mV |
| Pair | 115.9 pF, 1.85 ohm | 0.12 ohm | 15.9 mV | **15.7 mV** | 14.1 mV | 15.7 mV |
| SAR | 134.6 pF, 1.77 ohm | 0.49 ohm | 11.7 mV | **11.4 mV** | 10.7 mV | 12.5 mV |

Every branch passes with margin; the worst is 17.9 mV. The analog branch, 19 % below its planned bulk (92.9 against 114.2 pF), loses 0.8 mV against the planned case. A lower ESR than the model's upper bound reduces the droop, so no damping concern follows from it.

**With the extracted ring feeds** (`extracted_feed`). The feeds above are hand square-counts of the trunks. The periphery extraction ([chip periphery](chip_periphery.json), `chip-periph-x1`) also includes the pad landings and the via stacks onto the decap ports, and gives several times more. Each rail's star (pad, decap port, ADC pin) is scaled from 25 C typical to 125 C rcworst_T by its trunk layer. The decap arm adds to the decap's ESR.

| Branch | Pad to bulk (loop) | Bulk to pin (loop) | ESR per rail | Droop | Coupled ring |
| --- | --- | --- | --- | --- | --- |
| Analog | 1.99 ohm | 0.37 ohm | 3.35 ohm | **20.3 mV** | 18.6 mV |
| Pair | 3.73 ohm | 0.12 ohm | 2.95 ohm | **17.8 mV** | 17.6 mV |
| SAR | 2.26 ohm | 0.70 ohm | 2.26 ohm | **11.8 mV** | 13.3 mV |

Still a pass: worst 20.3 mV against 45 mV.

Limitations: the ESR and the MOM capacitance come from models, not extraction; the in-core values are the Stage 4b extraction of `layout_route_full`; the charge model keeps the Stage 1 calibration. The extracted feeds are at 25 C typical, scaled to 125 C by the trunk metal's coefficients; the via stacks may scale differently.
