# Bootstrap transistor terminal-stress map

## Decision

The current `sar_bootstrap` prototype is not a reliability-qualified switch.
Its SOA warnings cannot be removed by resizing the main switch or the
post-turn-off pull-down alone: the pump, control/discharge, and main-device
terminal pairs all cross the nominal 0.99-V PDK warning level. A protected
topology must address these paths together, while the held-error mechanism
remains a separate performance constraint.

## Exact source and method

This is a read-only reconstruction of the already completed
`screen_baseline_vdp800` differential transient, not a new simulation or OA
edit. The source is the automatic
`SAR_ADC_T28/tb_sar_bootstrap_transient/schematic` Spectre export containing
`sar_bootstrap`, SHA-256
`f3818ef606de602671beac8b6728a1f5460958d03ca0299de0fc79e28132242c`.
Spectre 21.1 used the T28 PDK TT MOS/passive sections at VDD=0.9 V and 27 C,
with `Vdiff=+0.8 V`, 50-ohm input sources, and 219.5-fF loads per side. The
complete waveform and warnings are retained under ignored
`output/bootstrap_driver_error_reduction/smoke_baseline/`.

The audit script reads all 12 MOS D/G/S/B connections per side from the
unaltered exported subcircuit, not a hand-maintained device map. It reconstructs
six terminal differences per device from saved internal nodes, both across
the full trace and the driven 200–285-ns cycle. This yields 144 terminal-pair
records. Nineteen retained Spectre SOA warning examples agree with the
saved-waveform peaks within 20 mV. Detailed ranked JSON and CSV are under
ignored `output/bootstrap_soa_map/`.

## Highest driven-cycle terminal differences

| Circuit path | Device / terminal | Peak magnitude | Approximate sampled time above 0.99 V | Meaning |
| --- | --- | ---: | ---: | --- |
| Cross-coupled pump | MN1 `Vgb`, MN2 `Vbs` | 1.787 V | 39.2 ns | Grounded body sees the boosted P2 node |
| Pump precharge | MN3 `Vgb` | 1.782 V | 44.0 ns | Grounded-body gate sees boosted P1 |
| Control and discharge, high-input side | MN13 `Vgb`, MN7 `Vbd` | 1.674 V | 40.1 ns | `G`/`GCLAMP` protection is incomplete |
| Discharge edge, high-input side | MN7 `Vds` | 1.272 V | 0.73 ns | Short additional drain-source overstress |
| Main sampling switch, high-input side | MN11 `Vgd` | 1.148 V | 0.05 ns | Main edge also exceeds the logged model level |

The 0.99-V comparison is a **model-warning screen**, not a foundry-approved
transient-voltage-duration rule. Durations are trapezoidal estimates from
saved waveform samples, not exact crossing-time or lifetime calculations.
The logged Spectre run completed numerically but suppressed about 400,681
additional warnings. The worst waveform magnitude is not merely a harmless
absolute node voltage: these rows are explicit differences between device
terminals. The main switch's netlisted model is `nch_mac` with body tied to
`VIN`; this audit follows that exact exported statement and does not infer
device qualification from the schematic's DNW design intent.

## Performance axis and next circuit target

The earlier full-driver screen measured up to 12.026 mV raw differential
held error against a 0.439-mV allocation. About −11.692 mV was created at
the immediate `PHI` turn-off edge, −0.335 mV during later discharge, and
+0.008 mV during subsequent hold. Making MN7/MN10 stronger mainly removed
the later term, leaving 9.097 mV even for an extreme candidate. Therefore
protecting the high-voltage pump alone would not solve sampling accuracy;
the edge-coupled boosted-gate isolation and main-switch charge path must also
change.

The next bounded transistor target should first verify permitted terminal
limits for candidate PDK device classes, then build an **independently named**
protected bootstrap experiment that addresses MN1/MN2/MN3 and MN7/MN13
stress, plus an independently controlled isolation/turn-off path. Measure
both complete terminal SOA and raw held error in the same transient. Do not
blindly swap in 1.8-V devices or modify the existing `sar_bootstrap` cell:
threshold, parasitic, drive, and body behavior must be re-evaluated. If the
foundry transient rules are unavailable, retain this target as a blocked
design constraint rather than claiming a reliable replacement.
