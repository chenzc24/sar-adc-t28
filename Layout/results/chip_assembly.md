# Partial chip assembly (Stage 5)

`SAR_ADC_T28_LAYOUT/sar8_adc_chip/layout` holds:

- `sar8_io_ring/layout` at the origin (R0);
- the ADC core `sar8_adc_core/layout_route_guard` at (363.885, 449.0) (R0, `io_ring.json` `adc_placement`);
- the core-to-pad routes that need no undrawn chip object.

The ring and core views are unchanged; the build checks their layout.oa hashes. Chip LVS is **CORRECT**. [Record](chip_assembly.json) · [Geometry](../design/chip_routes.py) · [Builder and checks](../design/chip_assembly.py)

## Routes and landings

**Pad landings.** Every landing is taken from the placed masters' terminal polygons, read back from the saved ring.

- **What the pins look like:** each core pin is a set of M1/M2 fingers reaching 2.6–2.8 µm into its IO cell, with the cell's VSS bus on M3 about 2.4 µm behind them.
- **How the routes attach:** the M2 fingers extend out of the cell onto a 1 µm M2 bar. The route then stacks up on 2.4 µm M3–M9 plates in the band between the cell edge and the planned core VSS ring outline (113–647 µm).
- **SAMPLE:** its C pin is a 0.26 µm M1–M4 square, so it takes an M4 stub and a via stack instead.

| Routes | Layer, width | Core end |
| --- | --- | --- |
| VINN, VINP | M5 + M6, 1 µm | 0.3 µm M5 neck onto the core's M5 pins |
| VREFP_a/b, VREFN_a/b | M8, 4 µm, nested L-shapes 2 µm apart | the 4 µm M8 pins |
| AVDD_analog/pair/sar | M9, 10 µm (6 µm beside the pins) | 2 µm M9 neck |
| AVSS_analog/pair/sar | M8, 10 µm (4 µm where SAMPLE runs below) | M8 neck; analog ends on an M9 neck with VIA8, matching its M9 pin |
| SAMPLE | M8, 0.8 µm | the 0.8 µm M8 pin |

- **Why AVDD on M9 and AVSS on M8:** they follow the core's supply pin layers, so the two routes of a branch may overlap.
- **Labels:** the chip cell repeats the ring's 55 pin texts, since the decks read top-level texts only. It adds `POC_dig` on the ring's M3 POC rail.
- **PSUB2:** a marker (111;0) covers the planned ADC guard-ring outline (359.885, 445)–(489.885, 564). It is the deck's isolated P-well marker, so the ADC substrate stays on AVSS_CORE apart from the ring's global VSS taps. Without it, LVS ties every block's NMOS bulk to the ring's VSS.
- **io_ring.json:**
  - Bond centres are now the PAD60GU CB opening centres, 32.66 µm outward of the earlier estimates on all 36 pads (#18).
  - Every core pin records its terminal-polygon extent. The along-edge pin centres were already exact (within 10 nm on the 0.26 µm digital pins).

## Not drawn yet, and where they land

The record's `pending_objects` gives the coordinates.

| Object | Landing points |
| --- | --- |
| Output register | the core's D0–D7 M7 pins at die (485.885, 502.4 + 1.2 k); the ring's D0_CORE–D7_CORE pins (0.26 µm M1–M4 squares); DVDD at right_4; clock from the drawn SAMPLE route |
| Core VSS ring (M7) | VSS pads left_7 and top_7 |
| ADC guard ring and AVSS_guard | the core's `0_guard` pin, M2 at die (485.485–485.885, 500.2–500.8); left_0's AVSS_CORE fingers. PSUB2 already marks this outline. |
| Pad decaps | on the AVDD/AVSS routes of each branch (`analog_pad_decap`, `pair_pad_decap`, `sar_pad_decap`) |
| PCLAMPC ×3, DVDD decap, seal ring | their `io_ring.json` regions; the seal ring has none yet |

AVSS_CORE pads top_0, top_6, top_8 and left_0 are not routed yet; LVS joins them by name, as in the ring's own LVS.

## Checks on the chip cell's stream

**DRC** uses the installed chip deck, `drc_rule_T28_chip`: the cell deck with FULL_CHIP and WITH_SEALRING, including the density, pad and ESD checks that the ring's cell-level run deselected. Each rule is compared against the same deck run on the ring alone and on the core alone:

| Group | Chip | Ring alone | Core alone |
| --- | --- | --- | --- |
| Density windows and OD.S.14 (empty-area OD), for fill | 981 | 777 | 58 |
| ESD.18g / ESD.19g / ESD.WARN.1 | 120 / 96 / 6 | 120 / 96 / 6 | 0 |
| PO.R.19 | 12 | 12 | 2 |
| Chip-wide warnings: WITH_SEALRING_OPTION, DIODMY_L, IO_CONNECT_CORE_NET, MATCH.WARN, DM1–DM9.R.1 | 1 each | 1 each | 1 each |
| **LUP.5.2.1 / LUP.5.2.2** (hierarchical; flat: 2 / 12, both channels) | **1 / 6** | 0 | 0 |
| Total | 1234 | 1027 | 72 |

- **No route-geometry rule:** the routes and landings add none. The first build's M2.A.4 holes, M2.W.3 maximum-width marks and one M8.S.3 spacing were fixed.
- **ESD.\* and PO.R.19:** these belong to the ring cell itself.
- **LUP.5.2.1 / LUP.5.2.2:** the only new rules. Now that VIN reaches its pad, the deck treats the Bootstrap main switch's VIN source/drains as pad-connected ("post-driver") devices. The rules ask for a wider guard ring or more spacing between them and the nearby PMOS N-well. Fixing them means changing the Bootstrap block core, which needs approval.
  - **Both channels are affected.** The hierarchical run above reports only XBOOTN (1 + 6 at die 393.2–398.0, 526.0–529.0). The same deck run flat on the same stream reports 1 + 6 on each channel (`chip-lup-probe-10flat`).
  - **Why the hierarchical run misses XBOOTP:** run hierarchically, the deck's pad-connectivity layers (`NSD_IOPAD_stp` and the supply-pad nets) cover no XBOOTP diffusion at all, not even its VSS source/drains. Flat, both Bootstraps match by mirror. The two instances share one master, so the hierarchical run under-reports the second instance.
  - **Not a routing error:**
    - the VINN and VINP chip routes mirror exactly about die x 410 (799 shapes each);
    - both VIN bond pads classify as signal pads (`IO_PAD`);
    - chip LVS stays CORRECT with virtual connects limited to the eight supply names (`chip-lvs-novcn-signals`), so VINN, VINP, both pads of each VREF rail and SAMPLE are physically connected.
  - **Use flat DRC for the latch-up checks** at chip level.
- **Cells behind the ring's own markers** (the same in the ring-alone run):
  - ESD.18g (120) and ESD.19g (96) sit in the eight PRUW08SDGZ output cells. They are ESD guidelines (total driver finger width per drain net), active because the installed deck sets `#DEFINE GUIDELINE_ESD`.
  - PO.R.19 (12, floating gate) also sits in the PRUW08SDGZ cells. Their I inputs float until the output register drives them.
  - ESD.WARN.1 (6) sits in the six PDB3AC cells: the SDI marker check on pad ESD devices.
  - The deck has no switch that exempts TSMC IO-library cells; only the guideline switch and the PO.R.19 text options exist.

**LVS** is CORRECT against `chip_lvs_source.py`. That source holds the ring schematic's own netlist inline (si/auCdl, so `POC_dig` is a chip net) and the core subcircuit connected as `chip_netlist` XADC for the drawn routes. The deck is the installed `calibre.lvs` with the ring deck's additions: `VIRTUAL CONNECT NAME "?"`, its power/ground name patterns, and ERC with cell names. The five block masters are HCELLs.

- **Counts:** ports 31/31; nets 543/543 and instances 1890/1890 after transformation.
- **Warnings:** the ring's two known ones (smashed MOSFETs, ambiguity points).

**ERC** (same run) against the ring cell's baseline:

| Check | Chip | Ring cell |
| --- | --- | --- |
| mnpg | 280 | 280 |
| floating.nxwell_float | 6 | 38 |
| floating.psub | 4 | 4 |
| npvss49 | 12 | 12 |
| Total | 302 | 334 |

There are no new ERC checks. The four kept categories are the ring's name-dependent results, waived in `io_ring_verification.json`.
