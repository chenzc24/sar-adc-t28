# SAR ADC T28

10-bit, 10 MS/s fully differential SAR-ADC design project for the TSMC 28 nm HPC+ ULL platform.

## Project ownership

- Local Git repository: `E:\bridge-Agent-T28\projects\sar-adc-t28`
- Remote Virtuoso library: `SAR_ADC_T28`
- Remote OA path: `/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28`
- Technology library: `tsmcN28`

Text sources, specifications, automation, curated netlists, metrics, and reports are maintained locally. Schematic, symbol, layout, and Maestro OA data remain in the remote Virtuoso library. OA data must not be copied or edited as ordinary files.

## Directory map

- `config/`: design specification, PDK mapping, and corner definitions.
- `docs/`: architecture, verification plan, and engineering decisions.
- `models/`: behavioral and Verilog-A models.
- `netlist/`: curated DUT, testbench, run, and reference decks.
- `scripts/`: bridge, simulation, and analysis automation.
- `virtuoso/`: cell manifest plus downloaded snapshots and exports.
- `verification/`: unit, system, PVT, and Monte Carlo definitions.
- `artifacts/`: downloaded GDS/CDL/PEX/reports; large generated files are ignored by Git.
- `output/`: disposable simulation output; ignored by Git.

## Initial workflow

1. Establish and verify the behavioral 10-bit golden model.
2. Characterize the CDAC, comparator, sampling switch, and SAR timing independently.
3. Integrate transistor-level blocks in `SAR_ADC_T28`.
4. Run static, dynamic, PVT, and Monte Carlo verification.
5. Complete layout, DRC/LVS, extraction, and post-layout simulation.

## Agent workflow

The repository adopts a project-specific version of the
[Agent Workflow Kernel](https://github.com/chenzc24/agent-workflow-kernel).
Every bounded target follows:

```text
target plan -> implementation -> deterministic validation -> factual log -> commit
```

Create plans under `plan/<date-goal-slug>/plan.md`. Root `AGENTS.md` defines
the ownership boundary between local tracked sources, generated artifacts, and
remote Virtuoso OA cellviews. `plan/log.md` records maintenance facts;
`docs/design_log.md` records circuit decisions; reusable lessons are drafted
under `docs/experience/` only when requested by a human.

Small bounded targets may commit directly to `main` while the project remains
single-owner. Pushes require explicit user authorization; published history is
never force-rewritten without explicit authorization.
