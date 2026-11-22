# Boundary routes, supply feeds, decoupling and reference network of the ADC core (Stage 4b)

`SAR_ADC_T28_LAYOUT/sar8_adc_core/layout_route_full` is a copy of `layout_route_int` (dbCopyCellView) with:

- **Boundary signals:** D0-D7 and SAMPLE run on M7 across the SAR macro from via stacks at x 91.9. The SAMPLE pin is on M8, and SAMPLE's VSS neighbour tracks are tied to the macro's M6 VSS stripes. VINN/VINP run on M5 straight from the north edge onto the Bootstrap VIN pins.
- **Three supply branches,** each with its own VDD!/0 boundary pins: analog from the north, pair from the south, SAR from the east.
- **713 `nmoscap` decoupling devices** in the branches' regions.
- **The shield tie:** the Stage 4a shield net now belongs to the analog VSS.
- **The on-chip reference network:** four VREF boundary pins, RREFP/RREFN (`rupolym`), CREF (164 `nmoscap`) and the trunks onto the pair's VREFP/VREFN rail west ends.

`layout_place` and `layout_route_int` are unchanged (their layout.oa hashes are checked on every build). The builder overwrites its own previous build in place (it checks the view's generatorOwner first), so a reader elsewhere keeps its cached copy. [Record](toplevel_route_full.json) · [Geometry](../design/toplevel_full_routes.py) · [Builder](../design/toplevel_full.py)

## Devices (user decisions, 2026-11-22)

- **Supply decoupling:** `nmoscap`, an N+-in-N-well accumulation varactor. The gate goes on VDD and the N-well on VSS, giving about 19 fF/µm² of gate at +0.9 V (model equations, TT).
  - Units are 2.5 × 0.8 µm (2.0 × 0.8 µm in the comparator strips), abutted on a 1.3 µm pitch, with rows alternating R0/MX so facing rows share one M2 rail.
  - The unit size follows from three rules: PO.A.3 limits a gate poly shape to 3 µm², PO.DN.4.1 limits local poly to 65 % (one dummy poly per device), and PO.S.35 requires poly within 0.8 µm on both sides of each gate (the first column keeps both dummies).
- **RREFP/RREFN:** `rupolym`, 0.5 × 0.5 µm segments in Parallel. The RF deck allows W ≤ 2 µm and L ≥ W. Each rail has 52 segments in two rows of 26.
- **CREF:** `nmoscap` with the same unit, gate on VREFP_TRUNK and N-well on VREFN_TRUNK.

## Decoupling per branch

| Branch | Devices | Gate area | Estimated C | Stage 1 requirement |
| --- | --- | --- | --- | --- |
| Analog (west, slot, east) | 220 | 440 µm² | 8.4 pF | 9 pF |
| Comparator strips | 12 | 19 µm² | 0.37 pF | 0.47 pF |
| Pair (south, east, southeast, corridor) | 241 | 482 µm² | 9.2 pF | 10 pF |
| SAR (south, north) | 240 | 480 µm² | 9.1 pF | 8 pF |

The floorplan sized the regions at 10 fF/µm² of region area. Abutted arrays with their rails reach about 8.5 fF/µm². To get closer to the requirements, three arrays use unassigned space:

- the slot array extends above its region to y 109.8, more than 6 µm from the VIN routes;
- a pair array sits in the empty corridor strip at x 86–91, y 10–52.5, below the CODE stubs;
- the SAR north array covers the south part of `spare_decap_northeast`.

## Reference network

**Layout.**

- **Pins:** four M8 pins, 4 µm tall, on the west edge at the floorplan positions: VREFP at y 67 and 55, VREFN at y 61 and 49.
- **Pad side:** each rail's two pins join on a 2 µm M9 (VREFP at x 2.2–4.2, VREFN at x 6.2–8.2). The joins run down `vref_decap_west` and turn east over the resistor rows. VREFP's M9 crosses both VREFN M8 stubs, so the pad side has two VREFP/VREFN crossings, not the one the floorplan text expects.
- **RREF:** four R90 `rupolym` rows of 26 segments in `vref_decap_south`, x 11.5–41.8: RREFP at y 1.5 and 3.3, RREFN at y 5.7 and 7.5. Each row's two M1 terminal lines run its full length and are strapped full length:
  - pad side: M2–M8 strips with 2 × 2 cuts per segment and VIA8 pairs up to the pad M9;
  - trunk side: 0.8 µm M3–M7 strips onto an M8 riser (VREFP at x 10.0–11.4, VREFN at x 8.3–9.6).
- **Trunks:**
  - **VREFP_TRUNK:** an M7 bus at y 15.4–16.5, M6 ties, and a 0.32 µm M5 line in line with the pair's VREFP rail, ending on the rail at x 12.715.
  - **VREFN_TRUNK:** an M4/M6 bus at y 17.0–18.3 and M4/M6 straps onto an in-line M5 extension of the VREFN rail, ending at x 12.055. Its M6 strap stays under the foot of the pair's VDD M6 riser.
  - The landing pieces lie inside the CDAC keep-out's bounding box but west of the rail ends, over the block margin and not over the array (floorplan power_plan.reference).
- **Labels:** VREFP_TRUNK and VREFN_TRUNK are top-level texts at the rail ends.
- **CREF:** 156 devices in `vref_decap_west` (6 columns × 26 rows) and 8 in the corner below the CDAC (x 8.8–15, y 9.2–16.3). The two trunk nets never share a layer where they cross: VREFP_TRUNK straps are on M3/M5/M7, VREFN_TRUNK straps on M4/M6.

| Item | Target | Drawn |
| --- | --- | --- |
| RREF per rail, PDK model at TT | — | 12.02 Ω at 25 °C (52 × 625.2 Ω); 11.94 Ω at −40 °C, 12.22 Ω at 125 °C |
| Series resistance, boundary pin to the pair's rail end | 15 Ω ±20 % | VREFP 17.21 Ω, VREFN 17.21 Ω |
| … pad side (pin to the RREF terminals) | — | 1.42 Ω / 1.42 Ω |
| … trunk side (RREF terminals to the rail end) | — | 3.76 Ω / 3.77 Ω |
| CREF | 8 pF ±25 % | 6.23 pF (164 devices, 328 µm² of gate) |
| CREF to the rail end | — | 3.90 Ω (gates) / 2.04 Ω (wells) |
| CREF N-well junction to the substrate (on VREFN_TRUNK) | — | 600 µm², 171 µm of perimeter |

The extracted resistances include each device's contact and M1 or gate access, which PEX books outside the device. The pair's own rail distribution, from the rail end to its 1531 switch terminals, adds 12.1 / 12.8 Ω inside the qualified pair.

**Sizing.**

- **CREF:** at the array's best density, about 10.5 fF/µm², the two reference regions and the corner hold at most about 6.3 pF. CREF is therefore at the low end of its band.
- **RREF:** the first draft used 42 segments (14.9 Ω) with thinner trunk stacks. It extracted 21.7 / 24.6 Ω from pin to rail end, and the rail budget showed it failing: 0.12 LSB at 22 Ω. So each rail has 52 segments now, with:
  - 2 × 2 cut stacks on every segment;
  - a wider VREFN riser with paired VIA7s;
  - M4/M6 straps onto the VREFN rail;
  - ties onto the VREFP rail right at its end.

## Checks on the saved view's stream

| Check | Result |
| --- | --- |
| Calibre DRC | 95 markers against 47 in `layout_route_int`. Every difference is a density window (M4–M9 DN, Mx.DN.7, PO.DN.3), deferred to top-level fill; no new geometry rule. |
| Connectivity (branch-labelled stream) | PASS. Every boundary signal, every Stage 4a net and each branch's VDD and VSS reach exactly their planned block ports. VREFP and VREFN are top ports that reach no block. VREFP_TRUNK and VREFN_TRUNK reach exactly the pair's VREFP/VREFN ports. Devices are counted flat, in model port order: the 713 decaps have their gate on their own branch's VDD; all 164 CREF devices have their gate on VREFP_TRUNK and N-well on VREFN_TRUNK; 52 + 52 RREF segments sit between each pad net and its trunk. The P-substrate soft-connects to one VSS net. |

## LVS plan (Stage 6 top-level LVS of the core)

Carried out in Stage 5 on `layout_route_guard`: CORRECT ([core LVS](toplevel_lvs.md)).

- **Layout:** the stream of `layout_route_full`. The top-level texts (TEXT DEPTH PRIMARY) name the ports D0–D7, SAMPLE, VINN, VINP, VREFP, VREFN, VDD! and 0, and the internal nets VREFP_TRUNK and VREFN_TRUNK.
  - VDD! and 0 each have one pin per supply branch, and each VREF rail has two pins. The core does not join these pieces: the IO ring does, outside. So the deck needs `VIRTUAL CONNECT NAME "VDD!" "0" "VREFP" "VREFN"` (with `VIRTUAL CONNECT COLON` left as installed).
  - The common P-substrate ties the three VSS pieces through the blocks' P+ taps. Under the single name 0 that is consistent; LVS SOFTCHK should report no conflict.
- **Source:** a new CDL subcircuit `sar8_adc_core` with ports D0–D7 SAMPLE VDD! VINN VINP VREFN VREFP 0. It holds:
  - `sar_adc8_join_r4` from `design/top/adc_top.scs`, without the three not-drawn model loads CL_COMP_P, CL_COMP_N and CL_CMP_CLK (`Layout/specs/interfaces.json` `not_drawn_instances`), with its VREFP/VREFN ports on VREFP_TRUNK/VREFN_TRUNK;
  - the reference wrapper of `stage6_supply_model.on_chip_reference.netlist`, with the drawn devices:
    - RREFP between VREFP and VREFP_TRUNK, and RREFN between VREFN and VREFN_TRUNK, each as `rupolym` w 0.5 µm, l 0.5 µm with 52 parallel segments. The layout has two 26-segment banks per rail; parallel reduction merges them, and the terminals are swappable;
    - CREF as 164 `nmoscap` (wr 2.5 µm, lr 0.8 µm), PLUS on VREFP_TRUNK and MINUS on VREFN_TRUNK;
  - the decoupling as `nmoscap` devices, PLUS on VDD! and MINUS on 0: 220 analog and 241 pair at wr 2.5/lr 0.8 µm, 12 comparator-strip at 2.0/0.8 µm, and 240 SAR at 2.5/0.8 µm (parallel reduction on).
- **Block references:** keep every block master as an HCELL against its existing LVS reference: `comparator-reference.cdl`, `bootstrap-reference.cdl`, the pair's CDAC and XREF CDLs from the `single_edge_xref` flow, and the SAR's `sar-se-leaves.cdl` with the standard-cell SPICE. The physical XREF leaves PHI_U, SAMPLE_INT and its D inputs unused, so map them as in the existing pair LVS.
- **Expected:** with the virtual connects, CORRECT at the top. Every decap and CREF well has an extracted N-well-to-substrate diode (`pnwdio`), the CREF ones on VREFN_TRUNK. The source must list these diodes, or the deck must filter them, as the block LVS setups already do.

## Extraction (flat xRC, typical)

| Item | Limit | Measured |
| --- | --- | --- |
| COMP_P / COMP_N / CMP_CLK route load | 11.4 / 11.4 / 11.1 fF | 5.04 / 5.15 / 5.03 fF (Stage 4a 5.05 / 5.14 / 5.05) |
| Handshake delay, Elmore bound | 20 ps | ≤ 4.0 ps |
| CODE0–7 / PRESET delay, Elmore bound | 100 ps | 3.5–4.6 ps |
| Bootstrap switch to CDAC plate | 800 Ω | 87 Ω |
| TOPN / TOPP total, and their difference | difference ≤ 1 fF | 251.00 / 250.50 fF, difference 0.51 fF (Stage 4a 256.97 / 255.82 fF, 1.15 fF) |
| VINN / VINP capacitance | — | 3.56 / 3.56 fF, mirror difference 0.0001 fF |
| VDD feed, boundary pin to the branch's decaps | in-core share of 6 Ω loop | analog 2.34 Ω, pair 1.30 Ω, SAR 1.27 Ω |
| VSS feed, boundary pin to the branch's decaps | in-core share of 6 Ω loop | analog 1.32 Ω; pair and SAR not separable (substrate) |

**TOP capacitance (unlabelled stream).** The TOP imbalance is the difference of the absolute totals: 0.51 fF against the 1 fF limit.

- **Why the Stage 4a values are not comparable.** In Stage 4a, and in the pins-only placement, the pair's VSS has no pin and extracts as a floating net. TOP's 29 fF to the pair's VSS is booked to that floating net, unevenly between the two sides.
- **Like-for-like baseline.** The placement was re-extracted with the pair VSS tied exactly as Stage 4b ties it: the same M8 feed and stack onto the pair's M6 VSS terminal, with a 0 pin (`adc-core-place-pairvss-pex`).
  - Tied: TOPN/TOPP 257.04 / 256.75 fF, difference 0.28 fF.
  - Pins only: 255.63 / 254.45 fF, difference 1.18 fF.
  - So the 1.15 fF Stage 4a difference was mostly that floating VSS.
- **Against the tied placement,** TOPN/TOPP change by −6.03 / −6.26 fF. This is not a physical reduction:
  - TOP's direct coupling to new Stage 4b metal is 0.20 fF to VIN and 0.03 fF to VDD per side.
  - The installed RC techfile looks up conductor thickness against local density, so the new metal changes TOP's ground term. It also shifts the CDAC's own internal MOM capacitances by 0.5 %, although their geometry is identical.
  - The reference network's metal near the CDAC's south-west corner moved TOPP by a further −0.22 fF against phase 1 (difference 0.27 → 0.51 fF).
  - The trunk names now also cover the pair's own VREF rails, which TOP already coupled to in Stage 4a as unnamed nets (0.66 fF per side).
- **What is not like-for-like.** The −4.6 / −4.0 fF "added" figures in the record's Stage 4a-method budget rows, and their 0.67 fF difference, are measured against the pins-only placement, so they are not like-for-like.
- **Authoritative check.** The Stage 5 filled extraction with the CDAC standalone fixture (TOP fixed load ≤ 57 fF per side, imbalance ≤ 1 fF) stays authoritative.

**VSS feeds.** The common P-substrate soft-connects the pair and SAR VSS into one extracted net, so those two feeds are not extracted separately. Their straps mirror the VDD topology, so each loop is estimated at about twice the VDD value: pair ≈ 2.6 Ω, SAR ≈ 2.5–3.3 Ω at 25 °C. The analog VSS extracts on its own: 1.32 Ω, for a 3.65 Ω loop.

## Rail budget with the drawn values

This reruns the Stage 1 models (`rail_budget.py`, `ring_supply.py`) through [toplevel_full_rail.py](../tools/analysis/toplevel_full_rail.py) with:

- the drawn decoupling, CREF and series resistance;
- the in-core feeds raised 25 % for 125 °C rcworst.

The charge model's calibration comes from `rail_budget.json`. Rerun at the Stage 1 values, the wrapper reproduces that record exactly (0.043 LSB box, 113 / 148 mV span droop).

**Supply droop, VDD−VSS at each block** (limit 45 mV; FF-cold timing; the 1.3 charge allowance):

| Branch | Drawn decap | In-core loop, 125 °C | Core alone | With the pad bulk | Coupled ring, 125 °C |
| --- | --- | --- | --- | --- | --- |
| Analog | 8.36 pF | 4.57 Ω (VDD 2.34 + VSS 1.32 extracted) | 40.8 mV | 17.1 mV | 16.3 mV |
| Pair | 9.16 pF | 3.25 Ω (VDD 1.30 + VSS estimate) | 40.3 mV | 15.9 mV | 15.9 mV |
| SAR | 9.12 pF | 3.1–4.1 Ω (VDD 1.27 + VSS estimate) | 26.3 mV | 11.7 mV | 12.6 mV |
| Comparator strips | 0.37 pF | 30 Ω (Stage 1 strap basis) | 26.3 mV | — | — |

Every branch passes. With the Stage 1 feed basis of 12 / 12 / 5 Ω the core-alone droop is 43.0 / 42.8 / 26.4 mV. The lower drawn feed resistance damps the pin resonance a little less, but its smaller IR drop wins.

**Reference.** CREF is 6.23 pF and the series resistance 17.21 Ω, with the tolerance box: series ×0.8–1.2, CREF ×0.75–1.25 around the drawn value, 0.5–1.5 nH per rail, and the 9 × 9 route range.

| Corner | Decision error, nominal / box | Span droop, box | Pin peak per rail, box |
| --- | --- | --- | --- |
| FF cold | 0.025 / 0.035 LSB | 177 mV | 4.64 mA |
| TT | 0.010 / 0.017 LSB | 177 mV | 4.64 mA |
| SS cold | 0.004 / 0.004 LSB | 177 mV | 4.64 mA |
| Limit | 0.10 LSB | 260 mV | 5.2 mA |

All pass. The decision error depends mostly on the RC of the series resistance and CREF:

- 8 pF at the same 17.2 Ω would give 0.088 LSB, worse than the drawn 6.23 pF;
- the first draft's 22 Ω and 25 Ω would give 0.12 and 0.23 LSB.

The span droop and the pin current grow as CREF shrinks; 3 pF would exceed the 5.2 mA pin limit.

## Open items

- **Decoupling below the Stage 1 requirement:** analog branch 93 %, comparator strips 78 %, pair 92 %. The droop budget passes anyway. Using more of `spare_decap_northeast` for the analog branch needs a strap path that crosses no VIN trunk.
- **The SAR P+ guard ring** (`sar_guard_ring`) is not in this view; it is drawn in `layout_route_guard` ([record](toplevel_route_guard.md)).
- **Density and fill:** the top-level grid density straps over the Bootstrap cells and the fill stage (fill policy steps 2–6). PO.DN.3 is now 3 windows, against 2 in `layout_route_int`.
- **VSS feeds of the pair and SAR** need a deck run without the substrate soft-connection, or a VSS-only extraction.
- **Floorplan text:** `power_plan.reference` still describes one VREFP/VREFN crossing on the pad side; the drawn pad side has two (M9 over M8 at right angles, about 8 µm² each).
- **CREF's N-well junction** on VREFN_TRUNK (600 µm²) loads VREFN_TRUNK to VSS. Its value comes with the Stage 6 extracted run.
