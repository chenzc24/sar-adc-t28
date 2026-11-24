# SAR timing with cell and routing parasitics

Calibration is in progress. The active design still uses the previous nine-stage timing source and its explicit latch MOM.

The four-vector schematic comparison uses the complete transistor ADC, one no-MOM latch, the same four other delay branches and the 40 ns external sample. All reachable standard cells use the installed typical LPE SPICE. The routed tests bind one flat Calibre coupled extraction of the SAR logic and both supplies. The other ADC blocks retain their transistor schematics and LPE standard cells. [Measured runs and source identities](sar_quiet_lpe_20261119.json)

## Delay-cell comparison

| Corner | Single DEL250 rise, plain / LPE (ps) | Nine-stage QUIET rise, plain / LPE (ns) |
| --- | ---: | ---: |
| TT | 171.4 / 273.1 | 1.544 / 2.449 |
| SSC | 292.2 / 494.6 | 2.600 / 4.355 |

## Four-vector schematic comparison

| QUIET stages | Corner | Correct at 90 / 98 ns | Eight updates by 90 ns | Minimum eighth-update margin (ns) | Max. CDAC error (LSB) |
| ---: | --- | --- | ---: | ---: | ---: |
| 9 | SSC | 2/4 · 4/4 | 0/4 | -7.392 | 0.0005 |
| 9 | FFC | 4/4 · 4/4 | 4/4 | 27.337 | 0.0122 |
| 6 | SSC | 4/4 · 4/4 | 4/4 | 4.253 | 0.0005 |
| 6 | FFC | 4/4 · 4/4 | 4/4 | 31.827 | 0.0136 |
| 5 | SSC | 4/4 · 4/4 | 4/4 | 7.997 | 0.0005 |
| 5 | FFC | 4/4 · 4/4 | 4/4 | 33.261 | 0.0202 |

Margin uses the eighth update. A frame with no observed eighth update contributes no numerical margin and still fails the completion count.

## Routed hardware

| QUIET stages | Physical rows | Core (µm²) | Logic and delay sites | All occupied sites | Connected nets | VDD / VSS resistors |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 | 13 | 450.64 | 75.60% | 84.78% | 284/284 | 7358 / 7085 |
| 5 | 13 | 450.64 | 74.67% | 83.84% | 283/283 | 7293 / 6994 |
| 6 (final DEL200) | 13 | 450.64 | 75.53% | 84.70% | 284/284 | 7530 / 7067 |

Occupied area is the union of logic, delay, decap, tap and boundary sites divided by the native core bounding-box area. The reference logic cell measures 20.190 × 14.610 µm. Its scope differs from this combined controller, sample sequencer and idle guard.

The filled wrapper dimensions are 28.415 × 16.000 µm (454.64 µm²). Across the candidates, cell sites occupy 83.11–84.03% of the filled outline and 76.64–77.49% of the 29 × 17 µm integration reservation.

The reference places eight custom data-latch slices on a 1.54 µm pitch. Its hierarchical OD drawing covers 13.78% of its native boundary. The recalibrated cores span 36.03–36.38% on the same OD layer. OD area includes active diffusion in taps and decaps. The site percentages above measure placement occupancy.

The earlier RC core occupied 2058.07 µm² with 48.65% utilization. With standard delay cells, the nine-stage core occupied 472.34 µm² with 84.40% utilization. These figures use each core’s physical boundary. [RC core area and measurement](sar_timing.md)

The four fixed branches use one DEL cell for comparison completion, three for write, ten for sample enable and twenty-nine for the idle guard. This gives 49 active DEL cells with six QUIET stages and 48 with five. The sample and guard delays continue to operate from their internal requests.

With 6 QUIET stages, the clock latch has 0.687 fF of passive QB capacitance with the other nets fixed (0.097 fF to the extraction ground and 0.590 fF coupled to other nets).
With 5 QUIET stages, the clock latch has 0.775 fF of passive QB capacitance with the other nets fixed (0.127 fF to the extraction ground and 0.649 fF coupled to other nets).
With 6 (final DEL200) QUIET stages, the clock latch has 0.687 fF of passive QB capacitance with the other nets fixed (0.096 fF to the extraction ground and 0.590 fF coupled to other nets).

The transistor transient also includes the bias-dependent MOS terminal charge.

Each supply has three 0.40 µm M6 vertical feeds and 0.32 µm M5 straps at shared row rails. The straps connect through 2 × 2 via arrays to the local cell rails. Nine native decaps sit in the rows. The reference comparison uses the existing native standard-cell boundaries and diffusion.

| QUIET stages | Pad to sampled bit-register VDD terminal (Ω) | Pad to sampled QUIET, WRITE and RAW VDD terminals (Ω) |
| --- | ---: | ---: |
| 6 | 60.85–63.04 | 43.14–46.56 |
| 5 | 60.85–63.04 | 43.13–46.25 |
| 6 (final DEL200) | 60.85–63.04 | 43.12–46.56 |

The filled wrapper exposes continuous 0.32 µm-wide M5 supply pins spanning 24.19–25.24 µm across the candidate set. The DC solve injects current into one extracted transistor terminal with the other loads open. It includes local diffusion access, cell rails, vias and supply metal. The transient rail extrema below measure simultaneous switching with the macro supply pin driven by the testbench.

| Layout | All signal metal (µm) | QUIET (µm) | QUIET_D (µm) | CLOCK_Q (µm) | Latch QB (µm) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Nine-stage original route | 1281.90 | 33.61 | 18.45 | 23.21 | 2.43 |
| Nine-stage reroute | 1194.21 | 25.36 | 1.42 | 4.42 | 2.03 |
| 6-stage reroute | 1188.83 | 14.16 | 1.14 | 2.96 | 2.15 |
| 5-stage reroute | 1203.73 | 14.27 | 1.14 | 3.22 | 2.46 |
| 6 (final DEL200)-stage reroute | 1190.15 | 14.96 | 1.14 | 2.96 | 2.15 |

Metal is measured as half the perimeter of merged top-cell signal polygons per layer on M1–M6. This allows like-for-like route comparisons and includes the polygon end widths. Per-candidate replay identities in the JSON compare the generated placement and native route overlay against the streamed core geometry.

## Extracted ADC measurements

| Test | Corner | Stages | Frames | Correct 90 / 98 ns | Complete by 90 ns | Minimum margin (ns) | Max. CDAC error (LSB) |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: |
| pilot | SSC | 6 | 3 | 3 / 3 | 3 | 1.347 | 0.0006 |
| pilot | FFC | 6 | 3 | 3 / 3 | 3 | 30.588 | 0.0117 |
| pilot | SSC | 5 | 3 | 3 / 3 | 3 | 5.485 | 0.0007 |
| pilot | FFC | 5 | 3 | 3 / 3 | 3 | 32.157 | 0.0151 |

The native traces also record sample tracking, the final write relative to guard and preset, and the rail span at each timing detector and register terminal. Receiver tables use the actual register D, CP and CDN. The foundry TT timing table is at 25 °C and the TT transient is at 27 °C.

| QUIET, MOS, metal and test | Tracking width (ns) | Min. preset lead before next tracking (ns) | Boundaries preset by SAMPLE_INT alone / total | Min. setup / hold slack (ps) | Peak VDD drop / VSS rise (mV) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 6 · SSC · typical · pilot | 34.945–34.952 | 5.137 | 2/2 | 473.03 / 1402.16 | 8.54 / 9.45 |
| 6 · FFC · typical · pilot | 38.067–38.070 | 38.050 | 0/2 | 189.89 / 560.37 | 20.17 / 21.68 |
| 5 · SSC · typical · pilot | 34.946–34.951 | 7.401 | 0/2 | 466.50 / 1392.99 | 8.63 / 9.92 |
| 5 · FFC · typical · pilot | 38.065–38.068 | 39.606 | 0/2 | 187.70 / 556.66 | 19.80 / 21.07 |
| 6 · SSC · CWORST_T · pilot | 34.858–34.866 | 5.224 | 2/2 | 481.43 / 1427.16 | 9.16 / 11.56 |
| 5 · FFC · CBEST_T · pilot | 38.103–38.106 | 39.995 | 0/2 | 183.70 / 545.62 | 19.82 / 18.31 |

The measured 30%–70% local-rail transition time divided by the library derate gives the slew at the table index. The JSON distinguishes in-table interpolation, table-boundary estimates and intervals censored by the trace boundary. [Liberty Reference Manual, section 1.6.29](https://people.eecs.berkeley.edu/~alanmi/publications/other/liberty07_03.pdf)

PRESET is the OR of SAMPLE_INT and the delayed idle request. A short gap between conversions can cancel the pending idle request. At each recorded frame boundary, the table measures PRESET against the actual SEQ_SAMPLE track opening. The JSON also records which OR inputs were high at the PRESET transition. [Reference controller](https://github.com/chenzc24/sar-adc-t28/blob/94e6394a7a9591107f54cebf37ae395485e07e05/design/xtor/reference/minimal_msb_d2.scs)

The previous FF-cold circuit measured 1.0337 ns from QUIET request to qualified output. The branch target is approximately 1.03 ns. The update-to-comparison interval includes other gates and is measured separately.

| FF-cold test | Matched QUIET rises | Shortest QUIET branch (ns) | Shortest update to comparison (ns) |
| --- | ---: | ---: | ---: |
| 6 stages, typical, 3 frames | 24 | 1.168 | 1.414 |
| 5 stages, typical, 3 frames | 24 | 0.976 | 1.223 |
| 5 stages, CBEST_T, 3 frames | 24 | 0.956 | 1.198 |

## Cell-interconnect sensitivity

These four-frame schematic runs pair the installed CWORST_T library with SS cold and CBEST_T with FF cold. They measure cell RC sensitivity using ideal wires between cells. The routed macro uses the project xRC rule deck.

| Stages | MOS corner | Cell model | Correct at 90 ns | Eight updates by 90 ns | Minimum margin (ns) | CDAC (LSB) |
| ---: | --- | --- | ---: | ---: | ---: | ---: |
| 6 | SSC | CWORST_T | 4/4 | 4/4 | 3.016 | 0.0005 |
| 6 | FFC | CBEST_T | 4/4 | 4/4 | 32.052 | 0.0138 |
| 5 | SSC | CWORST_T | 4/4 | 4/4 | 6.877 | 0.0006 |
| 5 | FFC | CBEST_T | 4/4 | 4/4 | 33.468 | 0.0203 |

## Whole-macro capacitance corners

Calibre re-extracted the identical filled GDS, including cell internals, signal routing, local VDD and VSS. The 1P9M 6X1Z1U foundry typical rules reproduce the lab rules byte for byte after resolving the single layer-map include to its installed path. Each alternative uses the corresponding CWORST_T or CBEST_T member of that package. The GDS, LVS electrical reference, layer map, extractor settings and rail switches retain their nominal identities. External standard cells use the matching LPE library. The remaining analog circuitry uses the original transistor schematic.

| Stages | MOS / metal corner | Frames | Correct at 90 / 98 ns | Eight updates by 90 ns | Input code with latest observed eighth update | Eighth-update margin (ns) | Shortest update to compare (ns) | Max. CDAC error (LSB) |
| ---: | --- | ---: | --- | ---: | --- | ---: | ---: | ---: |
| 6 | SSC / CWORST_T | 3 | 3 / 3 | 3 | 0x01 at 89.411 ns | 0.589 | 3.630 | 0.0006 |
| 5 | FFC / CBEST_T | 3 | 3 / 3 | 3 | 0x01 at 57.528 ns | 32.472 | 1.198 | 0.0160 |

The earlier nine-stage routed control completed six updates by 90 ns in each of its eighteen SS-cold frames. [Nine-stage extracted baseline](sar_std_static_candidate_c_20261119.md)
