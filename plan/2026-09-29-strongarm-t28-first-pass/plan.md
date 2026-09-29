# StrongARM T28 transistor-level first pass

## Goal and scope

Create a first T28-PDK transistor-level StrongARM comparator in Virtuoso, with an independent schematic testbench. Establish correct reset, decision polarity, and nominal near-threshold decision timing before sizing optimization. This target does not integrate the full SAR ADC or claim noise, offset, PVT, or reliability closure.

## Preflight and ownership

At start, `main` is six commits ahead of `origin/main`. The working tree has unrelated, ongoing bottom-plate sampling changes in `docs/design_log.md`, `virtuoso/cell_manifest.yaml`, its plan/config/scripts/report; these remain untouched. Existing bottom-plate OA windows/cells are user-owned and out of scope. `plan/log.md` is clean at start and is owned for a bounded entry only.

Before OA mutation, recheck Bridge 0.8.0 `t28_io` tunnel/CIW/Spectre, target library/technology mapping, exact cell absence, windows, and locks. Stop on collision or unsaved target. The Analog Canvas generic StrongARM is a topology reference only; its 150-nm generic MOS dimensions are not imported.

## Owned paths and OA objects

Local: this plan; `scripts/characterization/create_strongarm_t28.py`; `scripts/characterization/run_strongarm_t28.py`; `docs/strongarm_t28_first_pass.md`; one bounded `plan/log.md` entry. Generated readback, exact OA export, run decks, waveforms, and metrics under ignored `output/strongarm_t28_first_pass/`.

Remote: `SAR_ADC_T28/sar_strongarm_t28/schematic`, `/symbol`, and `SAR_ADC_T28/tb_sar_strongarm_t28/schematic` only. All other cellviews, especially active bottom-plate work and `sar_comparator_macro`, are read-only. PDK, technology files, libraries outside `SAR_ADC_T28`, and Analog Canvas are read-only.

## Assumptions and method

- 10-bit differential ADC, 0.9-V core supply, 0.45-V input common mode, 200-MHz SAR bit clock; nominal comparison allocation 1.5 ns after the CDAC settles.
- The first circuit is a dynamic differential pair, clocked tail, cross-coupled NMOS/PMOS regeneration, and four PMOS reset devices. Internal X/Y and output nodes are separate. Inputs and outputs are explicitly labeled; output polarity is verified by simulation, not assumed.
- Initial W/L values are engineering seeds derived from the existing T28 gm/Id characterization, not final dimensions. Use actual PDK `nch_mac`/`pch_mac` and 30-nm nominal channel length; never infer noise/offset yield from the nominal run.
- The OA schematic is the circuit source of truth. Its exported circuit text remains unmodified; a simulation wrapper may add stimuli analysis/saves around the exact export.

## Implementation and validation

1. Read the exact OA state and create only absent owned cells. Set and read back each MOS CDF size and every terminal connection.
   If creation stops midway, inspect the owned partial cell and resume only after confirming its exact 11-device topology and that the uncreated views remain absent; never delete or overwrite it as a shortcut.
2. Export the testbench hierarchy automatically. Verify PDK model include, hierarchy, element counts, no floating functional pins, correct testbench clock/input/load connections, and zero schematic check markers.
   A discovered testbench HDL-syntax marker from an instance name equal to its signal name is repaired by renaming only that owned source instance, followed by OA readback and re-export.
3. Run focused Spectre nominal TT/27 C/0.9 V transient vectors: positive, negative, and near-threshold differential inputs at 0.45-V common mode. Capture reset and output trajectories. Require zero simulation errors, repeatable reset, correct polarity, and measured resolution time from clock edge. Report failure honestly if 1.5 ns is not met.
4. Record exact geometry, netlist provenance, Spectre version/mode, results, warnings, and next sizing/noise/offset/PVT tasks. Run Python compile, owned-diff review, `git diff --check`, status, and OA readback. Commit only owned files as `feat: add T28 StrongARM first-pass schematic and testbench`; no push without user request.

## Decision gate

This pass is a working transistor-level prototype only if the exported schematic and Spectre testbench agree, reset is complete, polarity is correct, and the nominal near-threshold decision meets 1.5 ns. Regardless of nominal pass, comparator noise <0.316 mV RMS, offset <0.439 mV, PVT, kickback, metastability distribution, and post-layout effects remain open.

## Outcome

The first-pass nominal gate passed on the final zero-marker OA revision. Six TT/0.9-V/27-C Spectre runs from export SHA-256 `628f493c46c7c4df1e5e6262ab563c466958fd7ce182489515c507f3689be581` had zero simulator errors; the ±0.439453-mV cases resolved in 223.35 ps. The four repeated `scalefactor` PDK warnings and all statistical, PVT, kickback, loading, and layout work remain explicitly open. See `docs/strongarm_t28_first_pass.md` for conditions and wave evidence.
