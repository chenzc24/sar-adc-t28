# SAR ADC T28

An 8-bit, 10 MS/s, fully differential asynchronous SAR ADC. The current design is the single-edge SAR with registered per-bit delay taps and a 45 ns high / 55 ns low external clock, adopted on 2026-11-20. It is qualified with foundry cell LPE and the extracted CDAC; its layout is not drawn yet. [Adoption report](results/design/sar_single_edge_adoption_20261120.md) · [Settling reference](results/design/sar_single_edge_settling_reference_20261120.md)

| Topic | Entry point |
| --- | --- |
| Design specification | [Specification](docs/specification.md) and its machine-readable source [specs/arch.json](specs/arch.json) |
| Top level | [ADC top](design/top/adc_top.scs) and [complete DUT includes](design/dut.scs) |
| Current design qualification | [Adoption report](results/design/sar_single_edge_adoption_20261120.md) and its [record](results/design/sar_single_edge_adoption_20261120.json) |
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

Personal notes are at `E:/Learning/SAR-ADC-T28`. Use the Git commit in the provenance record for older experiments, plans, and one-off scripts. The complete local working snapshot is in the ignored `work/legacy/` directory. [Provenance](results/provenance.json)

Use the agent entry and development workflow for project work. Project skills are in `.agents/skills/`. Report terminal-voltage reliability, full-circuit local mismatch, and PEX within the scope of their evidence. [Agent entry](AGENTS.md) · [Development workflow](docs/development-workflow.md)
