# SAR ADC T28

An 8-bit, 10 MS/s, fully differential asynchronous SAR ADC. The single-edge SAR uses registered per-bit delay taps and a 45 ns high / 55 ns low external clock. The frozen chip view is `sar8_adc_chip/layout_full_fill5_r6_seal`, with the filled ADC core inside a 9 × 9 IO ring. [Design and verification history](docs/adc-iteration-history.md) · [Chip assembly](Layout/results/chip_objects.md)

**Verified through 2026-11-23 (PR #49).** The filled core with paired-corner wiring extraction and the reference/package model passed all 12 short corner runs at SS cold, TT and FF hot, including major carry and restart. Separate chip-periphery runs confirmed tracking with the VIN pads and 56.6 Ω routes, and correct codes with loaded FF-hot outputs. Both full and supply-only LVS passed on the frozen chip view. [Final corner results](https://github.com/chenzc24/sar-adc-t28/issues/12#issuecomment-7093047607) · [Periphery comparisons](Layout/results/chip_objects.md#open)

**Still open at this revision.** Chip-level fill, post-fill physical checks and waivers, the TT 1024-frame FFT, FF terminal-voltage and Bootstrap injection checks, output switching relative to sample close, selective-extraction coverage and the offset-correction specification. The frozen view has 1,911 DRC markers and 305 ERC results. [Current status](Layout/results/current.json) · [Signoff tracker](https://github.com/chenzc24/sar-adc-t28/issues/4)

| Topic | Entry point |
| --- | --- |
| Design specification | [Specification](docs/specification.md) and its machine-readable source [specs/arch.json](specs/arch.json) |
| Top level | [ADC top](design/top/adc_top.scs) and [complete DUT includes](design/dut.scs) |
| Single-edge adoption with cell LPE and extracted CDAC | [Adoption report](results/design/sar_single_edge_adoption_20261120.md) and its [record](results/design/sar_single_edge_adoption_20261120.json) |
| Modules | [Design index](design/README.md) |
| RNL schematics and hierarchy | [Offline viewer](docs/schematics/index.html) and [viewer and editing guide](docs/schematics/README.md) |
| Standalone module tests | [Block testbenches](tb/blocks/README.md) |
| Transistor-level candidates | [Candidate index](design/xtor/README.md) |
| Layout, DRC, LVS, PEX, and post-layout simulation | [Layout index](Layout/README.md) |
| Verilog-A and Python behavioral models | [Behavioral model index](design/behav/README.md) |
| Testbenches | [Testbench index](tb/README.md) |
| Simulation results | [Results index](results/README.md) |
| Architecture, corners, and acceptance | [Specifications index](specs/README.md) |
| Execution and monitoring | [Simulation guide](docs/simulation.md) |

```powershell
.venv/Scripts/python.exe -m tools.saradc check
.venv/Scripts/python.exe -m tools.saradc.single_edge_lpe ssc verify --cdac cworst --revision NEW_ID
.venv/Scripts/python.exe -m tools.saradc observe cold
```

`prepare` packages a real test case in the ignored `work/decks/` directory. The existing managed executor registers, queues, analyzes, and collects new simulations. The workspace and server hold raw waveforms and live run state.

The current transistor-level design is the default. For a mixed hierarchy, specify the view option for each module, for example `--view comparator=va --view reference=va`. To try a candidate, use `--candidate comparator=NAME`. Select frozen B explicitly for regression. Standalone module tests use `block prepare/sim/follow` and freeze the source, actual load, and measurements with the run.

Earlier designs (the data-reset OR SAR, the standard-delay v3 SAR, RC delays and the minimal reference) were removed from the tree after commit `c46d9d6`. Their dated results, including the 45-point PVT short test, stay in `results/` and `Layout/results/`, bound to their own source digests. Frozen B and its FFT, full-code and Monte Carlo results remain the behavioral baseline. [Terminal-voltage rule](specs/soa_rule.yaml) · [45-point PVT results of the reset-OR design](results/pvt/resetor_45_short_20261115.md)

Personal notes are at `E:/Learning/SAR-ADC-T28`. Use the Git commit in the provenance record for older experiments, plans, and one-off scripts. The original checkout also holds a local snapshot under its ignored `work/legacy/` directory. [Provenance](results/provenance.json)

Use the agent entry and development workflow for project work. Project skills are in `.agents/skills/`. Report terminal-voltage reliability, full-circuit local mismatch, and PEX within the scope of their evidence. [Agent entry](AGENTS.md) · [Development workflow](docs/development-workflow.md)
