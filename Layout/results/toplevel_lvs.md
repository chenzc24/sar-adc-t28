# Top-level LVS of the ADC core (Stage 5)

**CORRECT:** `SAR_ADC_T28_LAYOUT/sar8_adc_core/layout_route_guard` against the core source netlist. Every block HCELL and the top cell match. [Record](toplevel_lvs.json) · [Source generator](../design/toplevel_lvs_source.py)

## Source

The top subcircuit follows `sar_adc8_join_r4` (`design/top/adc_top.scs`) on the physical block grouping:

- **Not drawn, so left out:** the model loads CL_COMP_P, CL_COMP_N and CL_CMP_CLK.
- **Block masters:** each master is described by the reference netlist it passed block LVS with, and kept as an HCELL:

| Instance | Master | Holds | Block LVS evidence |
| --- | --- | --- | --- |
| XSAR | `sar8_se_core` | XCTRL, XSEQ, XDONE, XPRESET, XSAMPLE | `sar-se-r3-lib` |
| XCDAC | `sar8_cdac_with_xref` (children `sar8i_refword` and the CDAC as HCELLs) | XCDAC, XREF | `se-xref-full-b` |
| XCOMP | `sar_strongarm_t28_core` | XCOMP | `comp-v8-20261120-pex` |
| XBOOTN, XBOOTP | `sar_bootstrap_flat_8b_p_core` | XBOOTN, XBOOTP (supplies as ports) | `boot-core-20261121` |

- **Unused schematic ports:** the physical XREF has no D0–D7, PHI_U, SAMPLE_INT or RST_DONE ports, so PHI_U and SAMPLE_INT connect only to the SAR macro.
- **The reference wrapper** (`constraints.json` `stage6_supply_model.on_chip_reference`):
  - VREFP and VREFN each join ahead of RREFP/RREFN: 52 parallel `rupolym` w 0.5 µm l 0.5 µm per rail, into VREFP_TRUNK/VREFN_TRUNK;
  - CREF is 164 `nmoscap` (wr 2.5, lr 0.8 µm) with PLUS on VREFP_TRUNK.
- **The decoupling:** 713 `nmoscap`, PLUS on VDD!. The 12 comparator-strip devices are wr 2.0 µm, the rest 2.5 µm.
- **Well diodes:** the N-well diodes of the decaps and CREF are not listed. The installed deck filters them in the layout (`LVS FILTER D(pnwdio) LAYOUT OPEN`), as in every block LVS run: 12 in this layout.
- **Ports:** the boundary pins plus the internal nets the layout labels on pin layers (TOPN/TOPP, COMP_P/COMP_N, CMP_CLK, SEQ_SAMPLE, CODE0–7, PRESET, VREFP_TRUNK, VREFN_TRUNK). The deck makes every pin-layer text a port.

## Virtual connects

The job deck adds `VIRTUAL CONNECT NAME "VDD!" "0"`:

- **Why:** VDD! has three disjoint pieces inside the core (analog north, pair south, SAR east). `0` has four: those three, plus the SAR guard ring's own strap.
- **Where they join:** only outside the core. Each piece has its own boundary pin, and the chip routes join them on AVDD_CORE/AVSS_CORE (`io_ring.json` `chip_netlist`). Without the virtual connect, LVS would see them as separate nets.
- **What still checks the joins:** chip-level LVS, which has the real routes.
- **Separation inside the core:** the branch-labelled connectivity check (`toplevel_route_guard.md`) shows the pieces stay apart inside the core.
- **VREFP/VREFN:** they need no virtual connect. Each rail's two pins are joined inside the core by its M9.

## Result

| Object | Layout | Source |
| --- | --- | --- |
| Ports | 32 | 32 |
| Nets, after transformation | 48 | 48 |
| `rupolym`, before / after parallel reduction | 104 / 2 | 104 / 2 |
| `nmoscap` | 877 | 877 |
| pnwdio (filtered) | 12 | 0 |
| Block HCELLs | 6 | 6 |

The only warning is "Ambiguity points were found and resolved arbitrarily". The deck does not reduce `nmoscap` in parallel, so identical decaps between the same two nets are interchangeable. The block cells report the same warning in their own LVS runs.
