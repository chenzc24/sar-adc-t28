# Repair OA electrical macro-model

## Goal

Make `SAR_ADC_T28/tb_sar_macro_transient/schematic` an executable,
closed-loop Virtuoso testbench that corresponds to the topology-aware
Spectre/Verilog-A macro-model, instead of a structural skeleton with floating
control nets.

## Dirty-state note

At target start, `main` is clean and four commits ahead of `origin/main`.
Those commits are read-only inputs. The unrelated unsaved
`PLAYGROUND_AMP/canvas_test/schematic` window is protected and will not be
touched. No push is authorized.

## Local owned paths

- `plan/2026-08-30-repair-oa-electrical-macro-model/plan.md`
- `scripts/virtuoso/create_electrical_macro_model.py`
- `models/veriloga/sar_macro_controller_10b.va`
- `verification/system/test_electrical_macro_model.py`
- `docs/electrical_macro_model.md`
- bounded updates to `README.md`, `docs/design_log.md`,
  `virtuoso/cell_manifest.yaml`, and `plan/log.md`

Generated readback, export, and simulation artifacts under
`virtuoso/{snapshots,exports}/` and `output/` are owned but ignored.

## Remote OA owned objects

- new `SAR_ADC_T28/sar_macro_controller_10b/symbol`
- new `SAR_ADC_T28/sar_macro_controller_10b/veriloga`
- repaired `SAR_ADC_T28/sar_cdac_macro_10b/schematic`
- repaired `SAR_ADC_T28/sar_sampling_macro/schematic`
- repaired `SAR_ADC_T28/sar_comparator_macro/schematic`
- repaired `SAR_ADC_T28/tb_sar_macro_transient/schematic`

## Read-only areas

- all other local paths and `SAR_ADC_T28` cellviews
- `tsmcN28`, shared libraries, and PDK/model content
- remote OA files as ordinary filesystem data
- all unrelated open or unsaved Virtuoso windows

## Shared dependencies and assumptions

- `models/veriloga/sar_macro_controller_10b.va` remains the single controller
  source. Its electrical outputs are statically scalarized so the OA symbol,
  schematic nets, and curated Spectre instance have an explicit, identical
  positional order. The initial import failure was caused by omitted
  destination arguments to `schViewToView`, not evidence that IC6.1.8 lacks
  electrical-bus support.
- The nominal OA testbench uses the tracked electrical-macro configuration:
  0.9 V supply/reference, 0.45 V common mode, 100-ohm reference resistance,
  2-pF decoupling, 40-ns acquisition, and 5-ns bit cycles.
- Output observation nets receive high-impedance loads so schematic checking
  can distinguish intentional observation nodes from accidental floating pins.

## Implementation steps

1. Extend the OA builder with a repeatable Verilog-A import flow for the SAR
   controller and a scalar electrical symbol matching the source port
   contract. Do not leave a placeholder schematic that could shadow the
   `veriloga` view.
2. Rebuild the three macro schematics so their supply terminals participate in
   the electrical model and the comparator has bounded outputs.
3. Rebuild the top testbench with controller, reference RC network, complete
   clocks, output observation loads, and collision-free source names.
4. Read back every owned cell, refresh schematic checks, and export the top
   Spectre netlist without editing the generated deck.
5. Run the unmodified exported hierarchy from an analysis-only Spectre wrapper
   and compare its final code, timing, and key nodes against the curated
   reference case.

## Validation and pass criteria

- local Python compiles and focused source-contract tests pass
- controller OA views exist and parsed ports match the local Verilog-A source
- top readback contains controller-to-comparator, controller-to-CDAC, clock,
  supply, reference, and output-load connections
- no unintended floating-net/pin markers remain in the owned hierarchy
- the automatically exported top netlist contains the controller and is not
  modified after export; a separate wrapper adds only the clamp model card,
  and transient analysis
- remote Spectre returns `result.ok`, completes ten decisions within 60 ns,
  and produces the expected nominal code within 1 LSB
- `git diff --check`, owned-path diff review, and final status pass

## Expected artifacts

- `virtuoso/snapshots/electrical_macro_model_readback.json`
- `virtuoso/exports/electrical_macro_model/tb_sar_macro_transient/`
- `output/oa_electrical_macro_model/`

## Commit policy

Commit locally after validation as `fix: close OA SAR macro-model loop`.
Do not push without a separate user request.

## Completion record

- Created and parsed `sar_macro_controller_10b/veriloga` and its scalar symbol;
  no temporary schematic remains.
- Rebuilt the CDAC, sampling, comparator, and closed-loop nominal testbench.
  Check-marker readback is zero for all four schematic cellviews.
- Exported the OA hierarchy without editing it. SHA-256 remained
  `DCDD4DCBB16719CA93F109D7668542CBA141522F365D9DEE348CB123097BCDA9`
  before and after simulation.
- Spectre 21.1 returned code 768, 49.5201-ns latency, 0.08735-LSB maximum
  pre-compare residual, and ten correctly resolved decisions. Five remaining
  warnings come from the site AHDL environment and PDK scale declarations.
- Re-ran the correlated 11-case curated Spectre regression after scalarizing
  the shared controller. All six nominal codes remained exact and below
  0.25 LSB; the slow-RC, assumed-parasitic, and 1-fF kickback cases retained
  their intended failure signatures.
