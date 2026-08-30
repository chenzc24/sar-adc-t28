# Topology-aware electrical macro-model

## Goal

Replace the isolated first-order feasibility fixtures with a topology-aware,
closed-loop pre-transistor macro-model for the default 10-bit fully
differential 5+5 split SAR ADC. The model must expose the sampled CDAC nodes,
finite switch/reference dynamics, dynamic comparator regeneration, and
explicit settle/compare/latch phases while preserving the existing behavioral
golden model as the transfer-function oracle.

This target is a pre-transistor electrical macro-model. It is not a claim of
PDK transistor closure, physical capacitor matching, PVT/Monte Carlo closure,
or post-layout accuracy.

## Dirty-state note

At target start, `main` is clean and three existing commits ahead of
`origin/main`. Those commits belong to the completed primitive,
CDAC/reference, and module first-order targets. They are read-only inputs to
this target. No push is authorized by this plan.

## Local owned paths

- `plan/2026-08-30-topology-aware-electrical-macro-model/plan.md`
- `config/electrical_macro_model.yaml`
- `models/veriloga/sar_macro_controller_10b.va`
- `netlist/dut/sar_macro_10b.scs`
- `netlist/tb/tb_sar_macro_*.scs`
- `scripts/analysis/run_electrical_macro_model.py`
- `scripts/virtuoso/create_electrical_macro_model.py`
- `verification/system/test_electrical_macro_model.py`
- `docs/electrical_macro_model.md`
- bounded updates to `docs/architecture.md`, `docs/design_log.md`,
  `docs/verification_plan.md`, `virtuoso/cell_manifest.yaml`, `plan/log.md`,
  and `README.md`

Generated simulation data under `output/electrical_macro_model/` and OA
readback/export files under ignored `virtuoso/{snapshots,exports}/` are owned
but are not tracked source artifacts.

## Remote OA owned objects

- `SAR_ADC_T28/sar_cdac_macro_10b/schematic`
- `SAR_ADC_T28/sar_cdac_macro_10b/symbol`
- `SAR_ADC_T28/sar_sampling_macro/schematic`
- `SAR_ADC_T28/sar_sampling_macro/symbol`
- `SAR_ADC_T28/sar_comparator_macro/schematic`
- `SAR_ADC_T28/sar_comparator_macro/symbol`
- `SAR_ADC_T28/tb_sar_macro_transient/schematic`

The cells are intentionally named `*_macro*` so that the planned production
cells `sar_cdac_10b`, `sar_sample_switch`, and `sar_comp_strongarm` remain
unambiguous and untouched.

## Read-only areas

- all other local repository paths except the bounded documentation updates
  listed above
- all existing `SAR_ADC_T28` cellviews
- `tsmcN28` and every other PDK/shared library
- `/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28` as ordinary filesystem
  data; OA changes use supported APIs only
- the unsaved `PLAYGROUND_AMP/canvas_test/schematic` window

## Shared dependencies and assumptions

- default design contract remains 10 bit, 10 MS/s, 0.9 V supply/reference,
  0.45 V common mode, 5+5 split CDAC, and 200 MHz bit-cycle timing
- the nominal comparison point starts from `Cu=6.86047 fF`, but remains a
  parameter rather than a production selection
- the split-array electrical topology is a 31-Cu active MSB subarray, a
  `(32/31)Cu` bridge, and a 32-Cu LSB subarray including its unit dummy;
  charge conservation therefore gives a 32-Cu comparator-side load before
  explicit parasitics. The previous 33-Cu first-order fixture remains a
  conservative historical envelope, not the topology-accurate load.
- conventional fully differential VCM-based bottom-plate sampling/switching
  is the baseline macro switching scheme; it is a reversible architecture
  assumption, not a frozen layout topology
- closed-loop decisions use an event-driven Verilog-A controller, while all
  charge redistribution, reference memory, and comparator-node dynamics are
  solved by remote Spectre
- EVAS is used only for controller syntax/event smoke checks if compatible;
  it cannot validate the electrical network because it has no KCL/KVL solver

## Implementation steps

1. Define a single configuration contract for capacitance, switch/reference
   parasitics, comparator `gm/C`, kickback, and non-overlapping timing.
2. Implement a reusable Spectre electrical DUT with two explicit 5+5 split
   arrays, relay-based bottom/sample switches, reference Thevenin networks and
   decoupling, and a resettable input-plus-regeneration comparator macro.
3. Implement a Spectre-portable, explicitly unrolled Verilog-A SAR controller
   that sequences sample, trial, compare, latch, and bit retention.
4. Add generated nominal, boundary, and static-transfer testbenches plus
   deterministic waveform/metric extraction.
5. Build the four owned OA schematics with supported bridge APIs, then read
   back connectivity and export the intended netlists without editing OA
   files directly.
6. Correlate the complete model against charge-conservation/first-order
   expectations and the existing ideal SAR transfer.
7. Document what the macro-model proves, its parameter sensitivities, and the
   effects intentionally deferred to PDK transistor design.

## Validation and pass criteria

- YAML parses; Python and Verilog-A source-contract checks pass
- controller has exactly ten MSB-first decisions, explicit port access, and
  no runtime electrical-bus indexing
- every curated Spectre run returns `result.ok` with no simulator errors
- nominal conversion finishes inside the 60 ns conversion allocation
- nominal code differs from the behavioral golden code by at most 1 LSB away
  from deliberately selected transition points
- nominal CDAC residual at every latch instant is below 0.25 LSB
- nominal comparator resolves before every latch instant and resets before
  the next decision
- reference droop, sampled-node settling, comparator waveform, and final code
  are saved and quantitatively reported
- a reduced static sweep reports missing codes, DNL, and INL; it is a macro
  regression, not a mismatch sign-off
- all four OA cells are read back with expected instance families and nets;
  exported netlists are inspected
- focused tests, `git diff --check`, owned-path diff review, and final Git
  status pass

## Expected artifacts

- `output/electrical_macro_model/summary.json`
- code/settling/reference/comparator CSV tables and waveform plots
- per-case Spectre decks, logs, and PSF-derived data below the same output root
- OA readbacks under `virtuoso/snapshots/`
- OA netlist exports under `virtuoso/exports/`

## Commit policy

Commit the bounded target locally as:

`feat: add topology-aware SAR macro-model`

Do not push unless the user separately requests it.

## Completion record

- Implemented the configuration, explicit electrical hierarchy, closed-loop
  controller, analysis runner, focused regression, OA hierarchy, and design
  documentation.
- Corrected the topology calculation from the historical 33-Cu fixture to the
  exact 32-Cu canonical split load.
- Completed eleven Spectre transients; all six nominal cases passed code,
  timing, comparator, and 0.25-LSB settling gates.
- Rebuilt the owned CDAC OA schematic and symbol at safe terminal pitch after
  readback found generated-stub shorts; final readback and hierarchical
  Spectre netlist export passed.
- The target remains a deterministic pre-transistor macro-model. PDK-device
  sizing, random noise, PVT, mismatch, and extraction are intentionally next.
