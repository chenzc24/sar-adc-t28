# ADC core on the revised filled Bootstrap (Stage 5)

`SAR_ADC_T28_LAYOUT/sar8_adc_core/layout_route_boot_r2` is `layout_route_guard` with XBOOTN and XBOOTP mastered on `sar_bootstrap_flat_8b_p_filled/layout_r2`. That wrapper holds the r2 core (latch-up spacing fixed) and its planned fill, both at R0 (0, 0). The instances keep their names, origins and orientations: XBOOTN MY at (31.175, 76.245), XBOOTP R0 at (61.055, 76.245).

`layout_place`, `layout_route_int`, `layout_route_full` and `layout_route_guard` are unchanged; the build checks their layout.oa hashes. The routed core stream is `adc-core-bootr2-b1-chk` (layout.oa `e76aa76e…`).

The revision's ADC qualification is the Bootstrap session's and is still running. If it fails, this view has to be redone. [Record](toplevel_route_boot_r2.json) · [Builder](../design/toplevel_full.py) (`--stage boot_r2`)

## Pin check before the build

From a read-only readback of the saved views (`boot-r2-mount-readback-20261122`):

- **Outline:** the wrapper, the r2 core and the old master have the same bBox, (−11.82, −0.045)–(12.7, 24.945).
- **Pins:** the same five pin figures (CLKS M2, VDD M5, VIN M5, VOUT M2, VSS M5) and the same pin labels, to the nanometre.
- **Hierarchy:** the wrapper places XCORE and XFILL at R0 (0, 0). The core's Bootstrap instances carry no instTerms, so the remaster needs no reconnection.

At stream level, the top cell's 22 520 shapes, its labels and its 881 PDK instances are identical to `layout_route_guard`. So are the CDAC/XREF, comparator and SAR masters. Only the two Bootstrap references change master, at the same transforms.

## Checks

| Check | Result |
| --- | --- |
| Core DRC (cell deck), against `layout_route_guard` | 98 against 96 markers, density windows only, no new geometry rule. The failing density area drops on every changed rule (table below). The marker count rises only because merged failing regions split where the Bootstrap centres now pass. |
| Connectivity (branch-labelled stream) | PASS. Every planned net, boundary signal and supply branch reaches exactly its block ports. All decap, CREF and RREF devices are on their nets. |
| Core LVS (`adc-core-bootr2-lvs1`) | CORRECT: ports 32/32, nets 48/48, 885 instances, the same counts as on `layout_route_guard`. |
| Flat chip LUP/ESD (72 checks), this core substituted into the partial chip stream | **LUP.5.2.1 0, LUP.5.2.2 0** (control with the `layout_route_guard` core: 1 + 6 at each Bootstrap). ESD.18g 540, ESD.19g 432, ESD.WARN.1 6, unchanged; they sit in the IO cells. |

**LVS setup.** The source is `toplevel_lvs_source.py --bootstrap-reference boot-core-r2b-20261122`; the r2 reference netlist is byte-identical to the frozen core's. The Bootstrap core stays an HCELL, and the wrapper with its fill flattens into the top: the fill is dummy OD/PO, so it adds no devices and no nets. This matches the Bootstrap's own filled check, which flattens the fill into the core.

**Connectivity setup.** The layout netlist keeps the wrapper as a pass-through subcircuit around the core. `toplevel_route_connectivity.py` now resolves a wrapper whose only instance is a block master at its origin. The `layout_route_guard` netlist still passes with the change.

| Density rule | Failing area, guard → r2 (µm²) | Of it inside the Bootstrap outlines (µm²) |
| --- | --- | --- |
| PO.DN.3 | 6362 → 5962 | 1020 → 620 |
| PO.DN.3.1 | 7647 → 7012 | 1139 → 594 |
| OD.S.14 | 1030 → 606 | 265 → 0 |
| OD.DN.3 | 8862 → 8452 | 1208 → 1114 |

What remains inside the Bootstrap outlines comes from 20 µm windows reaching into empty neighbouring core area, which the core fill covers.

## Extraction (flat xRC, typical, unlabelled stream)

Both views were extracted with the same setup: `adc-core-bootr2-b1-xtr-raw` and `adc-core-guard-g1-xtr-raw`.

| Net | `layout_route_guard` | `layout_route_boot_r2` | Change |
| --- | --- | --- | --- |
| TOPN / TOPP total | 251.003 / 250.496 fF | 250.999 / 250.492 fF | −0.004 / −0.004 fF |
| TOP imbalance (limit 1 fF) | 0.507 fF | 0.507 fF | 0 |
| COMP_P / COMP_N / CMP_CLK total | 6.602 / 6.983 / 7.531 fF | same | 0 |
| SEQ_SAMPLE total | 26.973 fF | 26.975 fF | +0.002 fF |
| VINN / VINP total | 3.563 / 3.563 fF | 3.671 / 3.671 fF | +0.108 each; mirror difference 0.0001 fF |
| Boot-cap plates to ground, XBOOTN | 27.3 / 29.5 fF | 37.8 / 40.0 fF | +10.4 / +10.5 |
| Boot-cap plates to ground, XBOOTP | 29.7 / 31.5 fF | 38.6 / 40.2 fF | +9.0 / +8.7 |

- **Boot-cap plates:** in the core they match the Bootstrap's standalone filled extraction (BTOP 37.9, BBOT 40.4 fF, `boot-fill-r2-20261122`), so the core context adds at most 0.3 fF.
- **Adopted route budgets:** all pass, with unchanged values.
  - Route loads: COMP_P 5.07, COMP_N 5.19, CMP_CLK 5.05 fF (limits 11.4 / 11.4 / 11.1).
  - Elmore bounds: 2.53 / 2.71 / 3.48 ps against 20; CODE/PRESET 3.5–4.6 ps against 100.
  - Switch to CDAC plate: 87 Ω.
  - The Stage 4a-method TOP rows (−4.63 / −3.96 fF, difference 0.67 fF) are not like-for-like; the totals above are.
  - The CMP_CLK bound is 3.48 ps on both unlabelled extractions, against 4.00 ps in the Stage 4b record's branch-labelled run. The difference comes from the extraction setup, not the Bootstrap.

## Open

- **ADC qualification:** the Bootstrap r2 ADC qualification (Bootstrap session) must pass before this view replaces `layout_route_guard` downstream.
- **Core fill:** it should exclude the Bootstrap outlines on every layer, since the Bootstrap owns its fill. PO.DN.3/3.1 and OD.DN.3 windows around the Bootstraps remain for the core fill.
