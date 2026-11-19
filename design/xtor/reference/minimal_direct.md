# Minimal Reference Candidate

The default is `reference=minimal_msb_d2`. Relative to the first `minimal_direct` version, only the last MSB inverter on each side changes from D1 to D2. Logic depth, control logic, and the comparator match the original. The five-corner trial passed function and timing across 90 of 90 frames and passed the comparator terminal-voltage screen. It still found an FF-cold Vds violation in SAR storage device MM64 and increased transient current from the reference source. [Requirement](https://github.com/chenzc24/sar-adc-t28/issues/2) · [D2 verification and limitations](../../../results/soa/msb_drive_d2_trial_20261115.md) · [D2 adoption](../../../results/design/minimal_msb_d2_adoption_20261115.json)

A shared PRESET selects the initial state before the SAR's `CODE = D OR TOKEN` drives the differential reference switches. While PRESET is active, the lower seven bits are 0 and the MSB is 1. When PRESET is inactive, they follow CODE. The SAR retains its decision registers, bit sequence, handshake, and quiet/write delays. Shared idle/preset and sampling paths use B's electrical statements.

The reference uses direct drive without additional MUX or DFF stages, capture request or acknowledge, per-bit reset delay, non-overlap generator, or series gate resistors. Each bit's preset logic produces an inverted state. An inverter and a two-inverter buffer drive the P and N sides. The PMOS and NMOS gates on each side share the drive level. Dead time during switching is unguaranteed.

The original interface exposes four gate ports. Native Spectre `iprobe` ties the two gates on each side with zero differential voltage and measures current. The unused RST_DONE terminal is tied to VSS. D, PHI_U, and SAMPLE remain as compatibility inputs and are unused by the reference-state logic. The current interface generates no CAP_CLK.

The counts cover expanded instances in `XREF` only. SAR, CDAC switches, and top-level shared `XIDLE` are outside this count.

| Instance | Frozen B | Minimal candidate |
| --- | ---: | ---: |
| Native INV | 252 | 28 |
| Native NAND2 | 53 | 8 |
| Native DFF | 8 | 0 |
| rupolym netlist segments | 370 | 0 |
| MOM instances | 51 | 0 |
| Explicit nch/pch instances | 25/25 | 0/0 |
| Ideal connections and current probes | 0 | 17 |

These are expanded netlist instance counts. Use native tests with actual CDAC gate loads to evaluate drive, and separate evidence for internal standard-cell transistor count, area, and power. The first version uses the existing native D1 drive cells.

## Verification Entry Point

`python -m tools.saradc.reference_short prepare --version current --corner tt` creates a frozen package. Replace `prepare` with `submit` to register and queue through the managed flow. Use `--version b` for frozen B and `--version minimal` for the first D1 implementation. `status / analyze / collect` operate on registered IDs. Use a new `--revision` for changed inputs and preserve prior run records.

The five corners are `tt / ssc / ssh / ffc / ffh`. Each version uses 18 frames per corner, including 12 code centers, repeats, and large transitions. Keep source impedance, reference bypass, the 60 ns low and 40 ns high sampling clock, native analog subcircuits, and loads fixed. Use the same native waveform analyzer and independent public-output observer. Scale thresholds with VDD and use the current reference event contract.

The per-bit bottom-plate screen bounds residual error using nominal positive binary weights. Check floating top-plate kickback separately. The reference-switch port current includes displacement current. Use an appropriate device-current measurement for channel shoot-through. Require complete signals and waveforms and agreement with the observer. Include the first frame and retain original terminal-voltage warnings.

Submit the other four corners after TT passes native function and measurements. Diagnose wrong codes, timeouts, or settling-screen failures before proceeding. Leave the batch queued when CPU, memory, or disk admission fails. Use the existing limits and protect other tasks. Adoption as the default leaves all violations subject to the terminal-voltage rule.

The current ADC also uses SAR data-reset OR with the D2 reference described here. The adoption record shows the FF-cold pass and the corners pending at that checkpoint. [Current adoption record](../../../results/design/reset_data_or_adoption_20261115.json)
