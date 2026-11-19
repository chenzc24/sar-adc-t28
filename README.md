# SAR ADC T28

An 8-bit, 10 MS/s, fully differential asynchronous SAR ADC. The current schematic uses input-qualified native delay cells and the minimal MSB D2 reference. The previous routed SAR uses RC delays. [Schematic tests](results/design/sar_std_delay_20261119.md) · [Previous routed SAR](Layout/results/sar_timing.md) · [Routed standard-delay candidate and slow-corner diagnosis](Layout/results/sar_std_static_candidate_c_20261119.md)

| Topic | Entry point |
| --- | --- |
| Design specification | [Specification](docs/specification.md) and its machine-readable source [specs/arch.json](specs/arch.json) |
| Top level | [ADC top](design/top/adc_top.scs) and [complete DUT includes](design/dut.scs) |
| Single-edge SAR front end | [Native-cell DUT](design/dut_single_edge.scs) and [five-corner, mismatch and restart results](results/design/sar_single_edge_frontend.md) |
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
.venv/Scripts/python.exe -m tools.saradc.reference_short prepare --version current --corner tt --revision std-delay-v3
.venv/Scripts/python.exe -m tools.saradc observe cold
```

`prepare` packages a real test case in the ignored `work/decks/` directory. The existing managed executor registers, queues, analyzes, and collects new simulations. The workspace and server hold raw waveforms and live run state.

The current transistor-level design is the default. For a mixed hierarchy, specify the view option for each module, for example `--view comparator=va --view reference=va`. To try a candidate, use `--candidate comparator=NAME`. Select frozen B explicitly for regression. Standalone module tests use `block prepare/sim/follow` and freeze the source, actual load, and measurements with the run.

On 2026-11-15, the project adopted the data-reset OR version at the user's direction. Default packaging and direct includes both use the tested native standard-cell implementation, with the standard-cell library internals intact. At FF cold (0.99 V, −40 °C), 18 of 18 frames passed function and timing. Terminal-voltage violations fell from eight to zero under the new rule, and the maximum internal sampling close-edge shift was 5.88 ps. [Adoption record](results/design/reset_data_or_adoption_20261115.json) · [Terminal-voltage rule](specs/soa_rule.yaml) · [FF-cold comparison](results/soa/dff_reset_or_ffc_20261115.md)

The prior 17.13 µm reset-OR version completed a 45-point PVT short test. Codes and functional timing passed on 90 frames at the original five corners and 400 frames across 40 additional corners. The original five corners had zero numerical terminal-voltage violations, with time-resolution review flags retained. The additional 40 corners cover code and functional timing. The earlier D2 five-corner results and historical B FFT, full-code, and Monte Carlo results belong to their respective frozen inputs. [45-point PVT results](results/pvt/resetor_45_short_20261115.md)

Personal notes are at `E:/Learning/SAR-ADC-T28`. Use the Git commit in the provenance record for older experiments, plans, and one-off scripts. The complete local working snapshot is in the ignored `work/legacy/` directory. [Provenance](results/provenance.json)

Use the agent entry and development workflow for project work. Project skills are in `.agents/skills/`. Report terminal-voltage reliability, full-circuit local mismatch, and PEX within the scope of their evidence. [Agent entry](AGENTS.md) · [Development workflow](docs/development-workflow.md)
