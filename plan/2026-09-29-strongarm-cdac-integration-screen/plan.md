# StrongARM with full split-CDAC diagnostic integration

## Goal and ownership

Create one **new, independent** OA testbench that directly connects the existing T28 StrongARM inputs to the comparator-side top plates of the existing W185 full 5+5 split CDAC. Preserve both DUTs. Establish deterministic sample/hold/reference/compare timing, verify polarity and resolved decision, and measure top-plate disturbance caused by the comparator clock against a comparator-disabled control. This is a diagnostic interface screen, not ADC acceptance.

Starting Git state: clean `main`, ten commits ahead of `origin/main`. Active Virtuoso editing windows on prior bottom-plate CDAC and testbench cells are user-owned and remain untouched. Bridge 0.8.0 `t28_io`, CIW, and Spectre 21.1 are healthy. Source W185 clamp devices and bootstrap cells already carry SOA warnings; these remain an explicit blocker to physical acceptance.

Owned local files: this plan, new `config/strongarm_cdac_integration.yaml`, new `scripts/characterization/create_strongarm_cdac_integration.py` and `run_strongarm_cdac_integration.py`, new `docs/strongarm_cdac_integration.md`, bounded entries in `virtuoso/cell_manifest.yaml` and `plan/log.md`. Generated exports/decks/logs/PSF/metrics under ignored `output/strongarm_cdac_integration/`.

Owned remote OA object: **new only** `SAR_ADC_T28/tb_sar_cdac_strongarm_diag/schematic`. Read-only dependencies: `SAR_ADC_T28/sar_cdac_bottom_plate_clamp_w185_eval_10b/{schematic,symbol}`, `SAR_ADC_T28/sar_strongarm_t28/{schematic,symbol}`, `sar_cdac_macro_10b`, `sar_bootstrap`, all other OA cells and `tsmcN28` PDK. No existing cellviews or user windows may be modified.

## Method and gates

1. Preflight exact library mapping, CIW windows, source schematic/symbol readback and target absence. Use supported bridge create/modify APIs. Reuse existing W185 testbench construction to preserve its complete CDAC sampling path, then add StrongARM instance and independent comparator clock/output load in the **new** testbench. Check markers/readback and export exact OA netlist; verify CDAC/comparator hierarchy and top-plate-to-gate connectivity.
2. Populate only ADE design variables in derived decks. Run TT/0.9-V/27-C noise-free transient with matched positive/negative small input and zero-input control. Use comparator-disabled clock as an A/B control. Maintain clamp-before-bottom-bootstrap opening, reference handoff, and a comparator clock after settling. No component-level netlist rewrites are allowed.
3. Record pre-clock top-plate differential/common-mode, comparator-edge peak and decision-time differential changes, resolved output polarity and time, and warnings. Compare against the prior lumped-219.535-fF kickback **as a diagnostic, not an equivalence claim**. If the W185 fixture's own raw held error or SOA warnings dominate, report that limitation without declaring comparator failure or acceptance.
4. Validate YAML, Python compile, OA readback/markers, exact export hash, Spectre `result.ok`, PSF signal/time coverage, case symmetry, and `git diff --check`. Update report/log/manifest only for verified outcomes. Commit only owned files as `test: integrate T28 StrongARM with split CDAC`; do not push without request.

## Outcome

The new OA testbench was created and read back with 25 instances and zero
markers. Its exact netlist connected the unmodified W185 full CDAC to the
unmodified T28 StrongARM. Six noise-free TT transient runs (±0.439453125 mV
and zero, each with comparator clock disabled/enabled) completed with zero
errors. Both nonzero inputs resolved correctly in 224.116 ps. On/off-clock
top-plate differential disturbance peaked at 0.374181 mV and remained
0.365124 mV at the output crossing. The zero-input control showed a
similarly sized latch-dependent disturbance but has no correctness verdict.
Existing bootstrap device-limit warnings remain a physical-design blocker;
noise/mismatch and full SAR validation remain open. Exact values and
limitations are in `docs/strongarm_cdac_integration.md`.
