# SAR ADC T28

8-bit, 10 MS/s fully differential **flat-CDAC** SAR-ADC design project for
the TSMC 28 nm HPC+ ULL platform. Active specification:
`config/design_spec.yaml`; preserved 10-bit 5+5 specification:
`config/design_spec_10b.yaml`.

## Project progress and file navigation

For collaboratively edited, reader-facing Chinese notes, open
[`Obsidian_docs/首页.md`](Obsidian_docs/首页.md). The `Obsidian_docs/` folder
can be opened as a separate Obsidian vault. It keeps curated explanations
apart from the engineering reports below; existing reports are not moved.

Start with the [current progress and design-file map](docs/project_status.md).
It separates the active eight-bit line, candidates, historical ten-bit work,
local sources, generated results, and the actual remote Virtuoso cell/views.
The [complete inventory](docs/inventory/2026-10-20/virtuoso_cells.md) includes
actual-versus-manifest differences; a manifest entry alone is not proof that
an OA cell exists or is qualified.

## Active 8-bit line (2026-10-19)

The migration covers the Python golden model/error allocation, clocked ideal
and noisy Verilog-A, first-order settling/noise constraints, a complete
closed-loop electrical macro in Virtuoso, and native T28 bootstrap testing
on the new flat array. It does **not** mean a completed transistor ADC or
fully qualified PDK MOM/reference-switch array. See the
[migration report and evidence boundaries](docs/eight_bit_flat_migration.md).

The first [PDK CDAC device implementation](docs/cdac_flat_8b_device.md) now
exists separately: 512 independent T28 MOM units, 4.004 fF per unit, native
reference switches/drive, full-code tests and capacitor-local mismatch.
It is **not qualified**: reference-reset device-stress failures and a
SS/0.81-V/cold full-swing Bootstrap acquisition failure remain explicit.
The earlier electrical macro and all historical cells are preserved.

The next [reset timing/drive experiment](docs/cdac8_reset.md) completed 24
native APS runs and an independent OA candidate. Moderate PMOS-gate drive
clears the original nominal test point, but cross-input stress still fails;
no baseline replacement or PVT qualification is claimed. Bootstrap is unchanged.

Top-plate sampling is retained. Each CDAC side has weights
`128:64:32:16:8:4:2:1` plus one dummy; no split bridge. The selected control
is now [sample-initialized asynchronous SAR](docs/sar8_simple_async.md): one
external 10-MHz sampling phase, local compare/write/update timing, an eight-bit
position chain and SAR register, and separate P/N bottom-driver banks. There
are no independent reset/start/deadline/fault/EOC controls or output bank.
The new 21-cell native hierarchy passed 13 bounded APS functional/timing cases;
FF/0.99-V device SOA and physical analog-chain integration remain open. The
[older 26-cell handshake controller](docs/sar8_async_implementation.md) is
preserved as history, not the selected implementation. This is not a qualified
full ADC. Existing 200-MHz clocked models/OA benches remain comparison fixtures,
not relabelled or requalified as async. LSB is 7.03125 mV; the deterministic 0.25-LSB
gate is 1.7578125 mV. ENOB >=7 is the provisional design target, not a
transistor-level performance claim.

```powershell
.venv/Scripts/python.exe scripts/analysis/run_behavioral_baseline.py
.venv/Scripts/python.exe verification/eight_bit/test_migration.py -v
```

The bridge/Spectre reproduction commands, exact new OA cell names and
historical regression commands are in the migration report. New evidence is
isolated under `output/eight_bit_flat/`; prior 10-bit sources/cells/results
remain available. The sections below describe the preserved 10-bit design
history unless explicitly marked otherwise.

## Historical 10-bit sampling design line

As of 2026-09-30, the selected circuit-development line is **top-plate
sampling** with a split `GMAIN` bootstrap control and main-switch turn-off
before BOOT reset. The bottom-plate OA fixtures and netlist screens are
preserved as historical experiments, not a concurrent production topology.
The T28 bootstrap core has been simulated, but the complete GMAIN steering
and clock drive are not yet transistor-level or signed off. See
[sampling architecture status](docs/sampling_architecture_status.md).

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

## Local design review workbench

The block-linked derivation / workflow flow diagrams are maintained in
`review/`. Build an offline snapshot with:

```powershell
.venv/Scripts/python.exe scripts/review/build.py
Start-Process output/review/index.html
```

See [review/README.md](review/README.md) for maintenance and validation.
This viewer is now explicitly frozen to the historical 10-bit spec/evidence;
the active eight-bit review entry is the migration report above. Its old
results must not be assessed using the new eight-bit voltage limits.
The panel contains extracted explanations, not document links or report viewers.
Sampling/bootstrap has a detailed branch; the ADC block diagram maps each
constraint to its circuit. Analog Canvas remains an unconnected slot. No remote
OA changes are made by the viewer.

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

## Parameterized behavioral runner

The first two design stages are executable locally: the system error budget is
documented in `docs/error_budget.md`, and `models/behavioral/sar_adc.py`
implements parameterized ideal fully differential SAR decisions (eight bits
by default; ten bits when the archived spec is explicitly selected).

On Windows PowerShell:

```powershell
uv venv .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
.venv\Scripts\python.exe scripts\analysis\run_behavioral_baseline.py
.venv\Scripts\python.exe verification\system\test_behavioral_baseline.py -v
```

The runner writes `summary.json`, the static-linearity plot, and the dynamic
spectrum under `output/eight_bit_flat/behavioral/` for the active spec, or
`output/behavioral_baseline/` for ten bits. Generated output remains ignored;
the spec, model, tests, and numerical gates are tracked.

## Historical 10-bit clocked Verilog-A baseline

`models/veriloga/sar_adc_ideal_10b.va` is the stage-3 cycle-accurate model. It
captures the differential input on the falling edge of `CLK_SAMPLE` and makes
one MSB-first decision on each rising edge of the 200 MHz `CLK_SAR`. The model
exports `DOUT<9:0>`, `BUSY`, and `VALID`; all nonideality parameters default to
zero.

Run the local timing smoke test with the project's EVAS Python backend:

```powershell
.venv\Scripts\python.exe scripts\analysis\run_veriloga_baseline.py `
    --backend evas --cases timing --analyze
```

Run the curated decks through the configured remote Spectre bridge with the
workspace bridge Python, then analyze them with the project Python:

```powershell
E:\bridge-Agent-T28\.venv\Scripts\python.exe `
    scripts\analysis\run_veriloga_baseline.py --backend spectre
.venv\Scripts\python.exe scripts\analysis\run_veriloga_baseline.py --analyze
```

EVAS is a voltage-mode event simulator and is only the local timing smoke
gate. A successful remote Spectre run remains mandatory before the model is
treated as Spectre-compiled.

## Electrical macro-model

`netlist/dut/sar_macro_10b.scs` and
`models/veriloga/sar_macro_controller_10b.va` form the topology-aware,
closed-loop pre-transistor model. It includes the explicit differential 5+5
split CDAC, sample/bottom-plate switches, finite reference network, dynamic
gm/C comparator, reset/kickback, and ten electrical decisions. See
`docs/electrical_macro_model.md` for topology, results, and scope limits.

Run the local analytical regression and the remote Spectre suite with:

```powershell
.venv\Scripts\python.exe scripts\analysis\run_electrical_macro_model.py

E:\bridge-Agent-T28\virtuoso-bridge-lite\.venv\Scripts\python.exe `
    scripts\analysis\run_electrical_macro_model.py --spectre --profile t28_io

.venv\Scripts\python.exe verification\system\test_electrical_macro_model.py -v
```

The matching OA hierarchy is `sar_sampling_macro + sar_cdac_macro_10b +
sar_comparator_macro + sar_macro_controller_10b`, with
`tb_sar_macro_transient` as an executable closed-loop nominal testbench.
Its automatically exported Spectre hierarchy is validated without editing the
generated circuit netlist.
