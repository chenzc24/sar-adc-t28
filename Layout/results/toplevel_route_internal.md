# Core-internal routes of the ADC core (Stage 4a)

`SAR_ADC_T28_LAYOUT/sar8_adc_core/layout_route_int`, built on 2026-11-22 from the placement view `layout_place`, which is unchanged (layout.oa sha256 `62ba2e39…55b2` before and after). It holds the 21 planned paths that end only on block pins: the TOPN/TOPP tees with their comparator stubs and Bootstrap drops, COMP_P/COMP_N with both balance stubs, CMP_CLK with the M4 drop onto the comparator trunk, the SEQ_SAMPLE trunk and its mirrored arms, CODE0-7 and PRESET. It also holds the VSS shields of the output channel and the corridor. Boundary routes, supply feeds, decoupling, the SAR guard ring and fill wait for the IO ring and are not drawn. [Record](toplevel_route_internal.json) · [Route geometry](../design/toplevel_routes.py) · [Builder and native runs](../design/toplevel_route.py)

## Physical checks on the saved view's stream

| Check | Placement view | Routed view |
| --- | --- | --- |
| Calibre DRC (installed cell deck) | 48 markers, 18 rules | 47 markers, the same rules; one fewer M5.DN.6 |
| Rules present | density windows, OD.S.14, DIODMY_L and IO_CONNECT advisories | no new rule |
| Stream vs generated geometry | — | identical: 303 shapes, 15 labels, 5 block references |
| Connectivity (HCELL netlist) | — | PASS: each routed net reaches exactly its planned block ports, no text shorts; the substrate and the 17 XREF/CDAC pair nets are unchanged |

No route shape enters the CDAC array keep-out except inside the TOP pin footprints. On M4 and above, only the accepted CMP_CLK drop enters the comparator keep-out. Non-TOP nets enter the TOP fill exclusions only as right-angle crossings of the TOP drops (`floorplan_rules` in the record).

## Extraction against the adopted route budgets

Flat xRC with the installed typical deck. The capacitance a route adds is the routed net minus its pin pieces in the placement view, with every partner counted. Resistance and delay run between the driving and receiving device terminals, so they include the blocks' own wiring and bound the route-only values from above.

| Item | Limit | Measured |
| --- | --- | --- |
| TOPN / TOPP added capacitance | 9.8 fF | 1.346 / 1.371 fF |
| TOP side imbalance | 1 fF | 0.025 fF |
| Bootstrap switch to CDAC plate resistance | 800 Ω | 87 Ω |
| COMP_P / COMP_N / CMP_CLK route load | 11.4 / 11.4 / 11.1 fF | 5.05 / 5.14 / 5.05 fF |
| Handshake one-way delay, Elmore bound | 20 ps | 2.5 / 2.7 / 2.1 ps |
| CODE0-7 / PRESET one-way delay, Elmore bound | 100 ps | 3.5-4.6 ps |

The Stage 2 runs carried the ~10 fF CL_COMP_P/CL_COMP_N/CL_CMP_CLK model loads on top of their route loads, so the load limits keep about 10 fF of headroom; the routed loads use about half of each limit. The SEQ_SAMPLE arms reach the two Bootstrap CLKS gates in 4.57 and 4.60 ps.

## Comparator symmetry (decisions.cmp_clk_north_drop.verify)

CLK couples 353.7 aF to COMP_P and 316.5 aF to COMP_N. Of the 37.2 aF difference, 2.1 aF is in the comparator core, 24.4 aF is inside the SAR macro from its frozen pin order, and about 10.5 aF comes from the routes. CLK couples 23.8 aF to TOPP and 18.5 aF to TOPN; the 5.3 aF difference comes from the declared, unmirrored CMP_CLK crossing of the TOPP drop. The v8 core's own largest mirror difference is 7.4 aF. The comparator TT decision screen with this extracted environment has not been run.

## Differences from the floorplan

- An extra M3 VSS shield on y 66.9 µm separates the COMP_P and CMP_CLK stubs into the SAR pins; the plan's stubs were 0.5 µm apart over about 3.4 µm. It cut the route's CLK mirror difference from 60 aF to 10.5 aF.
- The 73.5 µm channel shield starts at x 48.215 instead of 47.3, so its 0.1 µm width stays out of `top_fill_exclusion_inputs`.
- The shields are one floating net, VSS_SHIELD (15.5 fF, no device terminals). Tie it to VSS with the supply feeds.

## Open items

- The comparator TT decision screen with this extracted environment (`decisions.cmp_clk_north_drop.verify`).
- The four planned channel shields cross the TOPP drop at right angles but are not listed in the floorplan `crossings`. The fill policy admits only TOP routes, declared crossings and the CMP_CLK drop in the TOP exclusions, so declare these crossings or move the shields. Their fixed load on TOPP is 0.016 fF.
- Fill policy step 2: merge this routed core with the pair's filled stream and run density-only DRC.

## Limits of this record

Typical extraction corner only. No transient and no ADC simulation. No fill and no drawn fill-exclusion layers. Density DRC stays deferred to the top-level fill.
