# Bootstrapped main-switch PVT screening

## Goal

Replace the rejected rail-to-rail plain transmission gate with the first
bootstrapped-sampling increment: characterize real T28 NMOS main-switch
candidates under an ideal `Vgate = Vin + VDD` drive. Compare core, deep-N-well
body-tracking, and 1.8-V devices over the full verified PVT grid. Measure Ron
flatness, off leakage, and terminal-voltage stress before implementing the
transistor-level bootstrap driver.

This target isolates the main switch and proves or rejects the bootstrap
assumption. It does not own the production sampling switch, bootstrap clock
driver, charge pump, non-overlap generator, layout, or integrated ADC.

## Dirty-state note

`main` starts clean and one commit ahead of `origin/main` at `ea5ceba`. The
bridge profile is `t28_io`; tunnel, `/home/chenzc_intern25/CDS.log.2`, and
Spectre 21.1 are healthy. Existing SAR schematic windows contain no reported
modal dialog and remain read-only.

## Verified PDK surface

- core standard-VT: `tsmcN28/nch_mac`, default `L=30 nm`
- core standard-VT in deep N-well: `tsmcN28/nch_dnw_mac`, default `L=30 nm`
- 1.8-V nominal-VT: `tsmcN28/nch_18_mac`, default `L=150 nm`
- all expose B/D/G/S and `l`, `Wfg`, `w`, `fingers`, `nf`, `simM`
- process sections remain `SSMacro_MOS_MOSCAP`, `TTMacro_MOS_MOSCAP`, and
  `FFMacro_MOS_MOSCAP`

Foundry model contents and unpublished reliability limits remain protected and
must not be copied or inferred. This target reports terminal differences but
does not declare reliability sign-off.

## Local owned paths

- `plan/2026-08-31-bootstrap-main-switch-screening/plan.md`
- `config/bootstrap_main_switch_screening.yaml`
- `scripts/characterization/create_bootstrap_main_testbenches.py`
- `scripts/characterization/export_bootstrap_main_testbenches.py`
- `scripts/characterization/run_bootstrap_main_screening.py`
- `scripts/characterization/analyze_bootstrap_main_screening.py`
- `docs/bootstrap_main_switch_screening.md`
- bounded updates to `config/pdk_mapping.yaml`, `virtuoso/cell_manifest.yaml`,
  `docs/design_log.md`, and `plan/log.md`

Generated OA readbacks, exports, staged decks, PSF, JSON, CSV, and plots under
`output/bootstrap_main_switch_screening/` are owned but ignored.

## Remote OA owned objects

- new `SAR_ADC_T28/tb_bootstrap_core_main_char/schematic`
- new `SAR_ADC_T28/tb_bootstrap_dnw_main_char/schematic`
- new `SAR_ADC_T28/tb_bootstrap_18_main_char/schematic`

## Read-only areas

- all PDK/model content
- all existing `SAR_ADC_T28` cellviews
- prior plain-TG sources and results
- all other remote libraries and user windows

## Assumptions and bounded matrix

- Ideal bootstrap drive is `Vgate = Vin_common_mode + VDD` in the on state and
  zero in the off state. It represents the intended capacitor action but not
  its finite capacitance, droop, switch loss, or clock timing.
- Core and 1.8-V bulk candidates tie body to VSS. The DNW candidate ties body
  to the lower-potential signal terminal in the DC fixture; dynamic junction
  behavior remains a later transient gate.
- PVT is SS/TT/FF x 0.81/0.90/0.99 V x -40/27/125 C.
- Ron is measured with a 1-mV differential probe from 1 mV to `VDD-1 mV`.
- Candidate widths use each OA-exported real finger and integer multiplicity.
- Hard electrical screen: finite positive `max Ron <= 1 kOhm` at every PVT
  and common-mode point. Leakage and terminal stress are reported, not silently
  traded against this target.

## Implementation steps

1. Create, check/save, read back, and export the three one-device OA fixtures.
2. Generate one deterministic batch deck per PVT point by mechanically
   replicating the corresponding OA-exported device statements into isolated
   on/off branches for each candidate.
3. Run all PVT points with real Spectre and retain every Ron curve, off leakage,
   gate absolute voltage, and VGS/VGD/VGB/VDS bound.
4. Select the minimum-width candidate meeting the Ron gate; compare core/DNW/
   1.8-V stress tradeoffs and define the device choice for the transistor-level
   bootstrap driver target.

## Validation and pass criteria

- exact OA master, B/D/G/S, CDF, library, technology, and target absence checks
- each readback contains one MOS, three voltage sources, ground, all intended
  nets, and no floating terminals
- automatic exports preserve master and body connection
- every configured Spectre job completes with zero errors, or the failure is
  explicit without relaxing coverage
- OA source hashes remain unchanged after batch generation
- nominal core result is physically consistent with the earlier device data;
  all Ron/leakage/stress values are finite
- Python compile, YAML parse, focused result assertions, visual plot review,
  `git diff --check`, complete owned-path review, and clean final status

## Expected artifacts

- `output/bootstrap_main_switch_screening/readback/`
- `output/bootstrap_main_switch_screening/netlist/`
- `output/bootstrap_main_switch_screening/spectre/run_summary.json`
- `output/bootstrap_main_switch_screening/analysis/summary.json`
- `output/bootstrap_main_switch_screening/analysis/candidate_corner_summary.csv`
- `output/bootstrap_main_switch_screening/analysis/worst_case_ron.png`

## Commit policy

Commit locally after validation as `feat: screen bootstrapped main switch`.
Do not push without a separate user request.

## Completion record

- Created, read back, and automatically exported all three owned OA fixtures.
- Completed 27/27 Spectre jobs with zero failures: 486 Ron curves and 486
  off-state leakage points for 18 candidates.
- Fourteen candidates passed the global 1-kOhm Ron gate. DNW L60/W2 is the
  preferred electrical seed at 321.2 Ohm worst Ron and 143.8 nA maximum
  leakage; 1.8-V L150/W8.96 remains the lower-leakage fallback.
- Reliability remains intentionally unsigned until the actual transient
  bootstrap driver and foundry voltage rules are checked.
