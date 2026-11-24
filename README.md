# TSMC 28 nm SAR ADC

An 8-bit, 10 MS/s fully differential asynchronous SAR ADC with a binary-weighted CDAC, bootstrapped sampling switches and a StrongARM comparator. The current single-edge SAR runs without calibration. The extracted core passed all 12 short functional runs. Two electrical checks remain open, and final TT dynamic performance is pending. [Circuit design](design/README.md) · [Schematic viewer](docs/schematics/index.html) · [System review #12](https://github.com/chenzc24/sar-adc-t28/issues/12)

[**Project website**](https://chenzc24.github.io/sar-adc-t28/) · [Site build guide](site/README.md)

## Repository structure

```text
sar-adc-t28/
├── specs/           Machine-readable architecture, interfaces, test cases and acceptance limits
├── design/          Circuit source and DUT include chain
│   ├── behav/       Python and Verilog-A models of the B algorithm and protocol
│   ├── xtor/        Transistor and standard-cell implementations of the ADC blocks
│   ├── top/         Connected ADC core netlist
│   ├── chip/        Chip output-register netlist
│   ├── rnl/         Schematic symbols and drawing manifest
│   └── frozen/      Versioned inputs for historical regression
├── tb/              Behavioral, block and top-level electrical testbenches
├── Layout/          Physical design, constraints, layout generation and extraction
│   └── results/     Floorplan, fill, extracted routes and DRC/LVS/ERC evidence
├── results/         Electrical measurements by DUT and run family
│   └── integration/ Integrated ADC measurements, including Stage 6 post-layout checks
├── docs/            Design specification, verification guides, schematics and revision history
├── tools/saradc/    Simulation preparation, execution and measurement tools
├── tests/           Software regression tests
└── .agents/         Project workflows for contributors using agents
```

For an electrical review, follow the [specification](docs/specification.md), [DUT entry point](design/dut.scs), [testbench registry](specs/tests.json) and [electrical results](results/README.md). For a physical review, start with the [layout index](Layout/README.md). Git tracks the GDS stream identity and SHA-256 in the [fill manifest](Layout/results/chip_fill.json). The GDS binary is held outside Git.

## Design targets

| Quantity | Specification |
| --- | --- |
| Resolution and throughput | 8 bits, 256 codes, 10 MS/s. Each 100 ns frame allocates 45 ns to acquisition and 55 ns to conversion. |
| Input and reference | VINP − VINN spans −0.9 to +0.9 V at 0.45 V nominal common mode. VREFN = 0 V and VREFP = 0.9 V. One LSB is 7.03125 mV. |
| Dynamic performance | ENOB ≥ 7 bits and SNDR ≥ 43.9 dB at −1 dBFS. |
| Static accuracy | Monotonic, no missing codes. Absolute DNL and endpoint INL each ≤ 1 LSB. Code-domain gain error ≤ 6% at TT and ≤ 10% at any corner. |
| Power | ≤ 1 mW. |

## Simulation conditions

The nominal circuit testbench uses 0.90 V at 27 °C, 50 Ω in series with each input, 50 Ω and 4 pF bypass per reference rail, and 5 fF per output bit. SAMPLE starts low for 60 ns of precharge. Its falling edge starts eight autonomous comparisons. The reference voltages stay fixed as VDD changes. [Interface and stimulus](docs/specification.md#architecture-and-external-interface) · [Testbenches](tb/README.md)

Stage 6 uses the filled core `sar8_adc_core_filled/layout_fill5`, wiring extracted at the corresponding corner and the Stage 1 package/reference model. At each of the three corners below, the short suite exercises four stimuli: verify, extreme, carry and restart. Output codes are checked against a gain-adjusted expectation (±1 code). Separate comparisons add the VIN pads and routes at TT and SS cold, or the output register, pads and 15 pF board load per output at FF hot. [Corner and pad comparisons](https://github.com/chenzc24/sar-adc-t28/issues/12#issuecomment-7093047607) · [Peripheral extraction](Layout/results/chip_objects.md)

## Post-layout results

All 12 short functional runs passed. The table shows the **verify stimulus** at each corner. Acquisition residual is measured at sampling close. Plate settling is evaluated at comparison. The residual and settling limits are each 0.25 LSB, and the required read margin is greater than 1 ns. [Stage 6 measurements](https://github.com/chenzc24/sar-adc-t28/issues/12#issuecomment-7093047607)

| MOS corner | VDD | Temperature | Acquisition residual | Plate settling | Read margin |
| --- | ---: | ---: | ---: | ---: | ---: |
| TT | 0.90 V | 27 °C | 0.006 LSB | 0.013 LSB | 24.9 ns |
| SS cold | 0.81 V | −40 °C | 0.101 LSB | 0.008 LSB | 8.73 ns |
| FF hot | 0.99 V | 125 °C | 0.006 LSB | 0.075 LSB | 30.3 ns |

| Review item | Recorded outcome |
| --- | --- |
| Board readout at FF hot | With 0.99 V core, 1.98 V IO, a 0.2 Ω / 2 nH bond and 15 pF per output, the board word settled 2.046 ns after register capture for the scored 0xFF conversion. The slower direction of the 0x7F ↔ 0x80 eight-bit switching test settled in 2.023 ns. [Endpoint conversion](results/integration/ffh_board_conversion.md) · [Simultaneous switching](results/integration/ffh_board_switching.md) |
| CDAC gain | The standalone TT bit-weight measurement on the stacked CDAC with planned fill gave a scale factor of 0.95950 and a code-domain gain error of 4.22%, within the 4.7% CDAC allocation. [CDAC bit weights and gain](Layout/results/cdac.md#gain-error-assessment) |
| Dynamic, static and power targets | The final TT 1,024-point transient-noise FFT at −1 dBFS (bin 461, 10 MS/s) is pending. Final Stage 6 SNDR, ENOB, full-code DNL/INL and average power are unreported in the current results index. [FFT setup](Layout/tools/simulation/prepare_stage6.py) · [Electrical results by revision](results/README.md) |
| FF-cold device stress | **Open.** At 0.99 V and −40 °C, 16 VDS pairs exceeded the project duration screen over eight extreme frames. SAR bit-1 register PMOS MM79 reached 1.11185 V absolute VDS and spent 757.8 ps above 1.10 V in a sliding 10 ns window (limit 100 ps). [Terminal measurements](results/integration/stage6_ff_electrical_20261124.json) · [Project rule](specs/soa_rule.yaml) |
| FF-hot Bootstrap sampling | **Open.** At 0.99 V and 125 °C the maximum single-ended error from input at sampling close to held TOP at first comparison was 4.130 mV against a 3.515625 mV limit. Verify and extreme exceeded the limit. Carry passed. The maximum differential error was 1.689 mV. [Sampling measurements](results/integration/stage6_ff_electrical_20261124.json) |
| Chip physical verification | The 122 × 111 µm core sits in an 892 × 892 µm die. The r8 filled chip view `sar8_adc_chip_filled/layout_fill7`, streamed as `chip-sfill7-oa-chk2`, returned **LVS CORRECT**, 224 DRC markers (zero density), 296 ERC markers and zero flat latch-up markers. The waiver matrix records foundry evidence and items awaiting disposition. [Fill and extraction](Layout/results/chip_fill.md) · [Waiver matrix](Layout/results/chip_drc_waivers.md) |
| Pads and package | The 9 × 9 IO ring plan records 36 bond opening centres. Final bond-map reconciliation and shuttle acceptance remain open. [Pad plan](Layout/design/io_ring.json) · [Package review #18](https://github.com/chenzc24/sar-adc-t28/issues/18) |

## Earlier simulation results

The frozen B schematic's deterministic 1,024-point TT FFT measured 48.79 dB SNDR, 7.81-bit ENOB and 64.77 dBc SFDR. This run provides a historical baseline for the pending Stage 6 spectrum. [FFT measurements](results/fft/results.json) · [Frozen B static results](results/static/results.json) · [Revision history](docs/adc-iteration-history.md)

To reproduce a registered case, use the [verification guide](docs/verification.md) and [simulation workflow](docs/simulation.md).
