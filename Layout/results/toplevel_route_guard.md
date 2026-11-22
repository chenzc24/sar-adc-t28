# SAR guard ring of the ADC core (Stage 5)

`SAR_ADC_T28_LAYOUT/sar8_adc_core/layout_route_guard` is a copy of `layout_route_full` (dbCopyCellView) with the SAR P+ guard ring of `floorplan.json` `sar_guard_ring`. `layout_place`, `layout_route_int` and `layout_route_full` are unchanged; their layout.oa hashes are checked on every build. This is the routed view that fill builds on. [Record](toplevel_route_guard.json) · [Geometry](../design/toplevel_guard_routes.py) · [Builder](../design/toplevel_full.py) (`--stage guard`)

## Ring

- **Placement:** the ring lies in the 1 µm band between the region outline (91.23, 51.0)–(111.725, 69.8) and the macro outline (92.23, 52.0)–(110.725, 68.8).
- **Layers:**
  - OD, M1 and M2 frames are 0.6 µm wide, 0.2 µm from both outlines.
  - PP encloses the OD by 0.1 µm.
  - Contacts sit in three rows at 0.16 µm pitch (1392 in total); VIA1 in 2 × 2 clusters every 1 µm.
  - The macro's own NW, PP, NP and M1 stay at least 0.455 µm inside its outline.
- **Crossings:** the corridor M3 stubs and the D0–D7/SAMPLE via stacks (M3 and above) pass over the ring. The ring uses no layer above M2.
- **Its own VSS strap:** M1 and M2 run from the ring's south-east corner east to the core edge, y 51.2–51.8, ending in a fourth `0` pin, `0_guard`, on M2 at x 121.6–122.
  - Inside the core the strap touches no other VSS metal.
  - At chip level it lands on the ADC guard ring (`io_ring.json` `adc_guard_ring`, AVSS_CORE, 2–4 µm outside the core edge).

## Checks on the saved view's stream

| Check | Result |
| --- | --- |
| Calibre DRC | 96 markers against 95 in `layout_route_full`. The only change is one more OD.DN.3 window (minimum OD density in 20 × 20 µm, at x 102–122, y 50–70), which belongs to fill. No new geometry rule. |
| Connectivity (branch-labelled stream, guard pin as VSS_G) | PASS. VSS_G is a top port that reaches no block port; VSS_D still reaches exactly the SAR VSS. Every other net and every decap, CREF and RREF device is unchanged from `layout_route_full`. |

For LVS the ring is a fourth piece of `0`, joined to the others by the virtual connect on `0` that the core LVS already needs for the three supply branches.
