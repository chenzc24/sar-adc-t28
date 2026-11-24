# TSMC 28 nm SAR ADC

An 8-bit, 10 MS/s fully differential asynchronous SAR ADC in TSMC 28 nm. The single-edge SAR controller samples for 45 ns and converts for 55 ns. The physical review covers an 892 × 892 µm die with 36 bond pads. [Design specification](docs/specification.md) · [Schematic viewer](docs/schematics/index.html)

## Design review

| Review scope | Evidence and open items |
| --- | --- |
| Chip layout | The r8 assembly with chip fill revision 7 is `sar8_adc_chip_filled/layout_fill7`. Its OA stream passed LVS and reported 224 DRC results, zero density results and 296 ERC results. [Layout index](Layout/README.md) · [Waiver dispositions](Layout/results/chip_drc_waivers.md) |
| Electrical verification | Stage 6 uses the fill5 core, extracted wiring and a package/reference model. All 12 short runs passed across TT, SS cold and FF hot. The final TT FFT and remaining reliability checks are tracked in the system review. [Verification results](results/README.md) · [System review #12](https://github.com/chenzc24/sar-adc-t28/issues/12) |
| Pads and package | The 9 × 9 ring plan records all 36 bond opening centres. Final bond-map reconciliation and shuttle acceptance remain open. [Pad plan](Layout/design/io_ring.json) · [Package review #18](https://github.com/chenzc24/sar-adc-t28/issues/18) |

## Repository guide

| Task | Start here |
| --- | --- |
| Trace the circuit or its interfaces | [Circuit design](design/README.md) · [Top-level netlist](design/top/adc_top.scs) · [Specifications](specs/README.md) |
| Reproduce a measurement | [Testbenches](tb/README.md) · [Verification guide](docs/verification.md) · [Simulation workflow](docs/simulation.md) |
| Find the design behind an earlier result | [Revision history](docs/adc-iteration-history.md) · [Engineering documentation](docs/README.md) |
