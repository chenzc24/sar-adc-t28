# Eight-bit flat mainline through the current ten-bit split maturity

## Goal / assumptions

User explicitly requests transition to 8-bit and completion of prior stages
through the present 10-bit 5+5 baseline. Implement a separate, reproducible
8-bit flat line, make it the documented/default project specification, and
retain historical 10-bit models, OA cells and evidence unchanged.

Keep 10 MS/s, 0.9-V supply, 0.45-V common mode, differential range +/-0.9 V,
200-MHz bit clock and 40-ns acquisition/60-ns conversion allocation. Use a
provisional >=7-bit ENOB acceptance target (the previous one-bit resolution
margin), no missing codes, |DNL/INL| <=1 LSB. Recompute voltage budgets from
8-bit LSB; retain jitter in absolute time. Cu=6.86047 fF is an initial
comparison parameter, not a selected physical MOM unit. A flat side has
256Cu=1.75628032 pF, so the bootstrap must be requalified and may need sizing.

The parity boundary includes architecture/error allocation, Python ideal and
noise-budget regression, clocked ideal/noisy Verilog-A, first-order electrical
constraints, full closed-loop electrical macro, OA connectivity, and actual
T28 bootstrap/full-CDAC sampling tests. Reuse already characterized PDK
primitives/comparator without falsely relabeling old results as 8-bit passes.
Do not repeat retired bottom-plate/isolation experiments or claim a complete
PDK MOM/reference-switch array, fully transistorized ADC, PVT/MC/noise/PEX
closure. If feasible, add the current native bootstrap + real StrongARM
interface diagnostic on the new flat load; record limitations independently.

## Initial state and ownership

Clean `exp/top-plate-gmain-t28`, ahead five, HEAD c5d6c08. No overlapping edits.
Read-only: all existing ten-bit OA cells, historical output, foundry PDK and
shared libraries, bridge implementation/settings, unrelated work.

Owned local paths:

- This plan, `plan/log.md`, `docs/design_log.md`, README.md,
  `docs/architecture.md`, `docs/error_budget.md`, `docs/sampling_architecture_status.md`,
  `docs/eight_bit_flat_migration.md`, `virtuoso/cell_manifest.yaml`.
- `config/design_spec.yaml` (active), new `config/design_spec_10b.yaml`
  (exact historical snapshot), `config/eight_bit_flat.yaml`.
- New `scripts/eight_bit/`, `netlist/eight_bit/`, `verification/eight_bit/`,
  `models/veriloga/sar_adc_ideal_8b.va`, `sar_macro_controller_8b.va`.
- Small backwards-compatible routing/title fixes only in
  `scripts/analysis/run_behavioral_baseline.py`,
  `scripts/analysis/run_veriloga_baseline.py`,
  `verification/system/test_behavioral_baseline.py` so historical 10-bit
  checks keep their original spec rather than consuming active 8-bit budgets.
- Ignored evidence in `output/eight_bit_flat/`.
- Minimal historical-view safety fix in `review/model.yaml`,
  `review/source-lock.json`, `review/README.md`: bind the existing ten-bit
  review graphs/evidence to the archived ten-bit spec and label them historical.
  Do not mix their old 0.439-mV evidence with new eight-bit formulas or silently
  accept unrelated changed report fingerprints. An eight-bit review UI is not
  asserted by this migration; its current review entry is the new report.

New owned remote OA objects, SAR_ADC_T28 only:

- `sar_cdac_flat_8b/{schematic,symbol}`: 18 ideal capacitor groups, 52 relay
  switches; explicit eight-bit and dummy topology, no bridge/split node.
- `sar_macro_controller_8b/{symbol,veriloga}`: direct semantic symbol; no
  floating schematic placeholder. Ideal ADC remains a local VA model, just as
  the original timing contract; no extra OA ideal-model cell is necessary.
- `tb_sar_macro_flat_8b/schematic`: electrical closed-loop macro reusing
  `sar_sampling_macro` read-only and a comparator copy below.
- `sar_comparator_macro_8b/{schematic,symbol}`: exact copy of the existing
  electrical comparator with only its two kickback capacitors parameterized
  for the sensitivity test. Existing comparator remains read-only.
- `tb_bootstrap_flat_8b/schematic`: matched old / native-0.5-um bootstrap on
  independent identical new differential flat arrays.
- `sar_bootstrap_canvas_flat_8b/{schematic,symbol}`: optional independent
  copied native candidate for a narrowly bounded width screen if 0.5 um fails.
- `tb_cdac_strongarm_flat_8b/schematic`: native bootstrap + new CDAC + existing
  StrongARM interface diagnostic (not full transistor SAR conversion).

## Work / validation

1. Read skills, relevant current sources, API contracts. Preflight bridge,
   simulator, windows/library mapping; stop on unsaved/conflicting targets.
2. Snapshot original spec and source hashes; set active 8-bit flat spec and
   generate new dedicated models/decks/fixtures without global text replacing
   historical circuits. Audit scalar eight-bit ports and absence of bit 8/9.
3. Python: 256-code static ramp, coherent sine, allocated-noise budgets and
   thermal/settling/regeneration/jitter first-order calculations. Preserve
   old regression with explicit historical spec and generic plot titles.
4. Spectre clocked VA: timing, full 256-code static, coherent sine and seeded
   sample/comparator/reference noise. Require result.ok, eight decisions and
   code agreement with Python; noise is dynamically injected, not patched
   onto output codes. EVAS timing optional if supported.
5. Full macro: exact flat binary charge oracle, nominal center/transition
   cases, slow-reference/switch and parasitic/kickback sensitivities. Build
   matching OA hierarchy, zero markers for actual electrical schematics;
   export without connectivity edits and compare to curated local structure.
6. Native switch: five differential inputs, common source/clock/reference
   conditions, correct 8-bit acquisition/held limits, warning/terminal audit.
   Preserve 0.5-um measurements, screen Wmain up to 1/2 um only if needed in
   a copied candidate; retest selected full load, never overwrite old DUTs.
7. Reuse comparator characterization with explicitly recalculated thresholds;
   interface diagnostic at +/-0.25 8-bit LSB with clock-disabled control if
   available. Do not infer physical noise/mismatch qualification from limits.
8. Verify final OA/netlist identity/readbacks and unchanged dependencies.
   Focused eight-bit and directly affected legacy regression, Python compile,
   YAML parse, source hashing, figure inspection, diff check. Document stage
   parity and open failures. Scoped local commit(s); no push.

Artifacts: per-run source/deck hashes, actual Spectre version/mode/corners,
PSF/log directories, readbacks/export snapshots, gates and compact figures in
output/eight_bit_flat; concise durable results in migration report.

Status: complete; local commit is the final recording step. Seven new cells
created; all six electrical
schematics have zero markers. Six historical dependencies unchanged, three
fresh exports equal simulated hierarchy except date, controller VA byte-equal.
49 accepted Spectre runs include preserved 0.5-um acquisition failure,
selected 1-um five-point pass, tighter precision and isolated warning controls.
No full transistor ADC/PDK CDAC/PVT/MC/noise/layout closure claimed.
Validation: six eight-bit tests, two historical behavioral tests, 23 directly
affected review tests, review build check, all 49-run evidence gates and three
rendered data figures passed. Original spec text/hash verified; no push.
Commit policy: one bounded migration commit if feasible, no push.
