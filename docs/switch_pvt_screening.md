# T28 transmission-gate PVT screening

## Outcome

No screened plain transmission-gate candidate satisfies `max Ron <= 1 kOhm`
over the full SS/TT/FF, 0.81/0.90/0.99-V, -40/27/125-C grid. The result is a
bounded no-solution for a rail-to-rail plain TG under the current requirement,
not a failed simulation campaign.

The production `sar_sample_switch` schematic was therefore not created. The
next sampling-switch target should use a bootstrapped NMOS architecture (with
explicit oxide/reliability checks), while CDAC bottom-plate switches should be
sized separately for their discrete reference/ground node ranges rather than
being forced to meet a rail-to-rail sampling-switch requirement.

## Verified model and OA sources

- standard-VT OA source: `SAR_ADC_T28/tb_tg_switch_char/schematic`
- high-VT OA source: `SAR_ADC_T28/tb_tg_switch_hvt_char/schematic`
- standard devices: `tsmcN28/nch_mac`, `tsmcN28/pch_mac`
- high-VT devices: `tsmcN28/nch_hvt_mac`, `tsmcN28/pch_hvt_mac`
- MOS sections: `SSMacro_MOS_MOSCAP`, `TTMacro_MOS_MOSCAP`,
  `FFMacro_MOS_MOSCAP`

The high-VT schematic contains the same parallel NMOS/PMOS topology,
complementary controls, explicit body connections, five ideal sources, and
ground as the standard-VT fixture. API readback found eight instances, six
nets, and no floating device/source terminals. Both source netlists were
exported by the Virtuoso Spectre netlister and preserved byte-for-byte during
screening.

## Batched measurement

Every PVT deck mechanically replicates the two OA-exported device statements
into isolated fixtures. For each candidate it contains:

- an on-state TG swept from 1 mV to `VDD - 1 mV` common mode with a 1-mV
  differential probe;
- an off-state TG with both devices disabled and the full VDD across it.

All eight candidates are solved in one Spectre DC sweep per PVT condition.
This gives 27 Spectre jobs, 216 complete Ron curves, and 216 full-stress
leakage measurements. All 27 jobs completed with zero Spectre errors.

The batching was correlated against the earlier independent nominal run:

| Metric for standard-VT, Wn=Wp=2 um, L=30 nm | Earlier run | Batched run |
| --- | ---: | ---: |
| TT/0.90 V/27 C maximum Ron | 911.3891 Ohm | 911.3891 Ohm |
| TT/0.90 V/27 C off leakage | 36.02325 nA | 36.02325 nA |

## Candidate results

| Candidate | Wn/Wp | Corners meeting 1 kOhm | Worst maximum Ron | Maximum off leakage |
| --- | ---: | ---: | ---: | ---: |
| standard, L=30 nm | 2/2 um | 15/27 | 26.925 kOhm | 4.162 uA |
| standard, L=30 nm | 3/3 um | 18/27 | 17.950 kOhm | 6.243 uA |
| standard, L=30 nm | 4/4 um | 21/27 | 13.462 kOhm | 8.324 uA |
| standard, L=40 nm | 4/4 um | 17/27 | 23.081 kOhm | 1.404 uA |
| standard, L=60 nm | 6/6 um | 18/27 | 30.953 kOhm | 0.579 uA |
| high-VT, L=30 nm | 4/4 um | 10/27 | 121.187 kOhm | 0.809 uA |
| high-VT, L=30 nm | 6/6 um | 15/27 | 80.791 kOhm | 1.214 uA |
| high-VT, L=40 nm | 6/6 um | 12/27 | 115.538 kOhm | 0.427 uA |

For every candidate, the worst Ron occurs at `SS/0.81 V/-40 C` near the
middle of the signal range (about 0.431-0.441 V). The maximum off leakage
occurs at `FF/0.99 V/125 C`.

## Why width scaling is not the right fix

The best screened worst-corner resistance is 13.462 kOhm from the 4-um/4-um
minimum-length standard-VT TG. A first-order inverse-width extrapolation would
require about 54 um per device merely to reach 1 kOhm at that corner. This is
not a credible sampling-switch solution: gate/drain parasitics, charge
injection, clock load, area, and leakage would all grow sharply, and the
linear extrapolation does not guarantee the target once those effects are
included.

The root cause is voltage headroom, not insufficient nominal sizing. Near
mid-supply at low VDD and cold SS, neither device has comfortable overdrive.
High-VT and longer-channel devices reduce leakage but deepen that on-state
dead zone. Minimum-length standard-VT devices improve Ron but produce the
largest hot-FF leakage.

The simple leakage-to-droop conversion remains a screening bound. For example,
the 4-um/4-um standard candidate's 8.324-uA worst leakage would imply about
190 mV over 5 ns on the 219.5-fF effective top-plate capacitance if the entire
current acted in one error direction. Real CDAC states and cancellation change
the signed error, but not the conclusion that this candidate cannot be frozen.

## Design decision

1. Do not create or freeze a production rail-to-rail plain TG sampling switch.
2. Start a bootstrapped NMOS sampling-switch schematic and dedicated transient
   testbench next. Verify Ron flatness, acquisition settling, charge injection,
   clock feedthrough, off leakage, and device terminal-voltage reliability.
3. Treat CDAC bottom-plate switches as a separate topology/sizing problem with
   their actual VREF/VSS switching states and per-bit settling loads.
4. Keep the standard-VT 2-um/2-um result only as a nominal macro-model
   correlation point, not a production seed.

## Artifacts

- `output/switch_pvt_screening/hvt_schematic_readback.json`
- `output/switch_pvt_screening/netlist/tb_tg_switch_hvt_char/input.scs`
- `output/switch_pvt_screening/spectre/run_summary.json`
- `output/switch_pvt_screening/analysis/summary.json`
- `output/switch_pvt_screening/analysis/candidate_corner_summary.csv`
- `output/switch_pvt_screening/analysis/worst_case_ron.png`
