# Full-control bootstrap turn-off current-path audit

Date: 2026-09-30. This is a read-only diagnosis of the existing
`SAR_ADC_T28/tb_sar_bootstrap_protected_full18_eval/schematic` OA export,
not a repaired switch or a new OA schematic. The exact exported deck has
SHA-256 `f466793e8655f2d81bdb7ce98d1041f00cdd90a374be3341750d2cb22a9bdd4d`.
The audit script permits no device or connection changes: it appends only a
transient analysis and voltage/terminal-current saves to a separate deck.
Run with `scripts/characterization/audit_bootstrap_current_paths.py`; the
separate deck, Spectre log/PSF, and machine-readable summary are under the
ignored `output/bootstrap_current_path_audit/`. The bridge tunnel was down
at run start; Spectre 21.1 was reached over direct SSH using the repository's
existing runner. This did not require or change remote OA.

## Test and current convention

The exact testbench uses the T28 PDK TT transistor/resistor/capacitor
sections at 27 C and 0.9 V, a differential 0.85/0.05-V input, 50-ohm source
resistance per side, and 219.5-fF output load per side. Ideal clocks drive
`PHI` low around 250 ns and `PHIB` high around 251 ns. There is no full
CDAC, input buffer, PVT sweep, layout extraction, transient noise, or
reliability qualification in this fixture.

Spectre's `save instance:currents` uses positive current **entering** each
terminal. The MOS entries `:1/:2/:3/:4` follow the exported D/G/S/B pin
order, and `RINP:1` enters the 50-ohm resistor from `VINP_SRC`. For the
high-side `MN9 (BBOT G VIN VIN)`, terminal 1 is `BBOT` (drain), terminal 3
is `VIN` (source), and terminal 4 is `VIN` (body). These are netlist-pin
currents, not a separately identified junction-only current.

## Measured sequence

All numbers below are from the saved transient and the explicitly stated
checkpoints; small interpolation differences are below the displayed
precision.

| Interval | Event | Differential output change | High-side input-source charge | High-side MN9 body charge |
| --- | --- | ---: | ---: | ---: |
| 250.1-251.0 ns | `PHI` falls; boost gate remains about 1.59 V during non-overlap | -2.939 mV | -4.545 fC | -0.002 fC |
| 251.0-251.5 ns | `PHIB` rises; gate discharges | -5.837 mV | +34.910 fC | +5.839 fC |
| 251.5-270.0 ns | output held; high-side input remains loaded | +0.022 mV | +477.236 fC | +466.961 fC |

At 250.1 ns the output differential is essentially 0.8 V. By 251.0 ns
it has lost 2.94 mV even though the boosted gate is still near 1.59 V:
the original sampling path tracks a perturbed input through the non-overlap
gap. The remaining 5.84-mV differential drop occurs during gate discharge.
Thus the loss is created at turn-off, not by subsequent output hold drift.
The high-side and low-side load-capacitor charge integrals match
`219.5 fF * delta(VOUT)` within the numerical integration error; the
`MN11` drain plus load-capacitor current has a peak KCL residual below
`4e-7 nA` across 249.8-270 ns. This validates the reported output charge
movement, but it does **not** uniquely assign the turn-off loss to one
internal parasitic or transistor mechanism.

At 270 ns, `VINP_SRC = 0.850 V`, `VINP = 0.848707 V`, and
`BBOT = 0.008707 V`: `V(body)-V(drain)` on high-side MN9 is about
`+0.840 V`. The source resistor supplies `25.858 uA`, matching the
`25.858 uA` flowing out of MN9's drain pin; MN9's body pin takes
`25.293 uA`, and its source pin takes `0.565 uA` (gate current is
negligible). Their signed sum is approximately zero. This directly
confirms a persistent current path from the high input into the low
`BBOT` node through MN9, consistent with a forward-biased body/drain
junction; the terminal-current data alone cannot split the body current
among junction and model parasitic components. The low-side input remains
essentially unloaded. At 270 ns the high-side 50-ohm drop is 1.293 mV.

The held differential output at 270 ns is `0.791245 V`, or
`-8.755 mV` against the ideal 0.8-V input (about 19.9 times the
0.439-mV allocation). Relative to the *currently loaded* input
`0.798707 V`, output-minus-input is `-7.462 mV`. These are different
metrics: the 1.293-mV source drop exists while the input is loaded,
whereas the output changes by only about +0.022 mV from 251.5 to 270 ns.
The persistent MN9 path is therefore a definite input-loading/power
problem, but should not be described as the sole cause of the already
stored -8.755-mV output error. A later distinct-topology ablation is
needed to isolate each turn-off coupling mechanism.

Spectre completed with 0 errors and 4 `SFE-1131` duplicate
`scalefactor` warnings from the supplied model include, not `CMI-275x`
overvoltage warnings. It also reported an IC-analysis bad-pivot notice;
waveform/charge/KCL checks above passed. Absence of model voltage warnings
is not foundry lifetime signoff.

## Design implication and next controlled experiment

Do not promote this mixed-voltage switch as a sampler or resize it solely
for lower `Ron`. The next independent OA variant should first remove the
off-state high-input-to-low-`BBOT` forward junction path, while preserving
valid D/G/S/B stress and a defined reset state for the bootstrap capacitor.
On that variant, repeat the same source-current/KCL audit, then separately
alter isolation/dummy/clock timing one factor at a time to measure the
2.94-mV non-overlap tracking component and 5.84-mV discharge component.
Acceptance requires the raw held error below 0.439 mV across input levels,
near-zero unintended hold input current, acquisition/Ron compliance, and
the terminal-stress screen before moving to PVT and full CDAC integration.
