# SAR ADC layout

The review library is `SAR_ADC_T28_LAYOUT`. The 122 × 111 µm ADC core sits inside the 892 × 892 µm r8 chip. OA cell and view names below identify the layout used for each check. [Physical manifest](design/manifest.json) · [Integration record](results/current.json)

| Scope | OA cell/view | Evidence |
| --- | --- | --- |
| ADC core | `sar8_adc_core_filled/layout_fill5` | Core routing, local fill ownership and density checks. [Core fill](results/toplevel_fill.md) · [Floorplan](design/floorplan.json) |
| Chip assembly | `sar8_adc_chip/layout_full_fill5_r8_seal` | IO ring, ESD clamps, seal ring and pad connections. [Chip assembly history](results/chip_objects.md) · [Pad plan](design/io_ring.json) |
| Filled chip | `sar8_adc_chip_filled/layout_fill7` | The OA stream `chip-sfill7-oa-chk2` reproduced the assembly results. DRC 224, density markers 0, LVS CORRECT, ERC 296 and flat LUP 0. [Fill and extraction report](results/chip_fill.md) · [Waiver matrix](results/chip_drc_waivers.md#summary) |

## Items for review

- **Fill.** The OD/PO and M1–M9 checks measured zero overlap in the exclusions. The separate via-layer audit found 15 chip-level dummy vias inside the core exclusion. The project tracks their disposition and the acceptance of fill inside IO cells. [Coordinate audit](results/chip_fill7_core_dummy_vias.json) · [System review #12](https://github.com/chenzc24/sar-adc-t28/issues/12)
- **Comparator.** The normal MATCHING markers close MATCH.WARN.1. The deviation from high matching and the extracted offset measurements are documented. The ADC is uncalibrated. [Matching decision](results/chip_matching.json) · [Comparator measurements](results/comparator.md)
- **Pads.** The PAD60GU opening centres and terminal extents support the final bond-map review. [Assembly readback](results/chip_assembly.json) · [Package review #18](https://github.com/chenzc24/sar-adc-t28/issues/18)

## Block and routing evidence

| Block or interface | Design and verification |
| --- | --- |
| CDAC and reference switches | [CDAC layout and bit weights](results/cdac.md) · [Single-edge D2 XREF and CDAC routing](results/single_edge_xref.md) |
| Bootstrap and SAR control | [Sampler extraction and measurements](results/bootstrap.json) · [Routed SAR macro](results/sar_se_core.md) |
| Power and reference paths | [Rail budget](results/rail_budget.md) · [Extracted ring-feed recheck](results/chip_rail_recheck.md) |
| Floorplan and fill | [Floorplan drawing](results/floorplan.svg) · [Interfaces](specs/interfaces.json) · [Constraints](specs/constraints.json) · [Fill policy](specs/fill-policy.md) |

Use the layout workflow for OA ownership, rebuild conditions, physical verification and extraction. [Layout workflow](docs/workflow.md) · [OA query guide](docs/layout-query.md)

## Previous architecture

The earlier gate driver used `minimal_msb_d2`. The RC and standard-delay SAR implementations also predate the single-edge controller. Their reports preserve the run identities and measured failures used to select the current architecture. [Revision history](../docs/adc-iteration-history.md) · [Earlier gate driver](results/reference_driver.md) · [RC timing](results/sar_timing.md) · [Standard-delay candidate](results/sar_std_static_candidate_c_20261119.md)
