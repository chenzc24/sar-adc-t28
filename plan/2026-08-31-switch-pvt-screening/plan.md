# Transmission-gate PVT screening

## Goal

Extend the nominal standard-VT transmission-gate sizing into a bounded PVT
and threshold/channel-length screening. Compare standard-VT and high-VT PDK
devices, identify whether any candidate retains `max Ron <= 1 kOhm` over the
verified SS/TT/FF, supply, and temperature grid, and quantify off leakage
before creating a production sampling-switch cell.

This target is a sizing gate. It does not own the production
`sar_sample_switch`, CDAC switch matrix, layout, or integrated ADC.

## Dirty-state note

`main` starts clean and synchronized with `origin/main` at `c333daf`. The
bridge profile is `t28_io`; tunnel, CIW daemon, and Spectre 21.1 are healthy.
The active SAR session is `/home/chenzc_intern25/CDS.log.2` on `thu-wei`, and
the existing SAR schematics are open without a modal dialog. Existing OA
cellviews are dependencies and remain read-only.

## Verified PDK surface

- standard-VT devices: `tsmcN28/nch_mac`, `tsmcN28/pch_mac`
- high-VT devices: `tsmcN28/nch_hvt_mac`, `tsmcN28/pch_hvt_mac`
- both high-VT devices expose B/D/G/S and the same relevant CDF parameters as
  the standard-VT pair; their default minimum length is 30 nm
- verified top-level MOS/MOSCAP sections:
  `SSMacro_MOS_MOSCAP`, `TTMacro_MOS_MOSCAP`, `FFMacro_MOS_MOSCAP`

Only section names and public CDF metadata are recorded. Foundry model content
is read-only, restricted, and must not be copied into the repository.

## Local owned paths

- `plan/2026-08-31-switch-pvt-screening/plan.md`
- `config/switch_pvt_screening.yaml`
- `scripts/characterization/create_hvt_switch_testbench.py`
- `scripts/characterization/export_hvt_switch_testbench.py`
- `scripts/characterization/run_switch_pvt_screening.py`
- `scripts/characterization/analyze_switch_pvt_screening.py`
- `docs/switch_pvt_screening.md`
- bounded updates to `config/corners.yaml`, `config/pdk_mapping.yaml`,
  `virtuoso/cell_manifest.yaml`, `docs/design_log.md`, and `plan/log.md`

Generated OA readback, exported netlists, Spectre PSF, CSV, JSON, and plots
under `output/switch_pvt_screening/` are owned but ignored.

## Remote OA owned objects

- new `SAR_ADC_T28/tb_tg_switch_hvt_char/schematic`

## Read-only areas

- all `tsmcN28` PDK/model content
- every remote library except the one new testbench in `SAR_ADC_T28`
- all existing `SAR_ADC_T28` cellviews, including `tb_tg_switch_char`
- existing OA-exported standard-VT source netlist
- all behavioral, macro-model, and earlier characterization artifacts

## Assumptions and bounded matrix

- Core supply range is 0.81/0.90/0.99 V; temperature points are -40/27/125 C.
- Process corners use the audited SS/TT/FF macro MOS sections. Non-MOS model
  sections stay at the OA-exported values because the fixture contains only
  MOS devices and ideal sources.
- Candidate geometries use real 0.25-um fingers and integer multiplicity.
  Channel lengths and multiplicities are bounded in the YAML configuration.
- `max Ron <= 1 kOhm` across the full signal range remains the hard screening
  target. Leakage is reported across the PVT grid and converted to a simple
  hold-droop bound; it is not assigned a sign-off limit in this target.
- The OA-exported source netlists remain immutable. To avoid one remote
  transfer per candidate, each staged PVT deck may replicate the two verified
  device statements into electrically isolated on/off fixtures with unique
  node and source names. Replication is mechanical and preserves model name,
  terminal order, body connection, and PDK-emitted geometry; only the audited
  MOS section, supply, temperature, channel length, and multiplicity vary.

## Implementation steps

1. Create and read back the high-VT transmission-gate fixture, then export its
   netlist through the Virtuoso Spectre netlister.
2. Build one deterministic batch deck per PVT condition from the standard- and
   high-VT OA exports; each deck contains isolated on/off copies of every
   candidate to reduce transport overhead without reducing coverage.
3. Run bounded candidate Ron and full-stress leakage screening across all
   configured process/voltage/temperature combinations and the full signal
   common-mode range.
5. Select the minimum-total-width robust candidate, compare leakage/channel
   length tradeoffs, and state explicitly whether a production schematic may
   be started in the next target.

## Validation and pass criteria

- exact PDK masters, B/D/G/S terminals, CDF fields, and model-section names
  match the preflight evidence
- high-VT OA readback contains exactly two MOS devices, five sources, ground,
  the intended six nets, and no floating terminals
- automatic export preserves the parallel transmission-gate topology
- every requested Spectre run completes with zero errors, or failures are
  surfaced per case without relaxing the matrix
- source netlist hashes remain unchanged after staged-deck generation
- extracted Ron values are finite and positive at every common-mode point
- selection is deterministic and reports a bounded no-solution result if no
  candidate satisfies every configured PVT point
- Python compile, YAML parse, focused result assertions, `git diff --check`,
  complete owned-path review, and final status pass

## Expected artifacts

- `output/switch_pvt_screening/hvt_schematic_readback.json`
- `output/switch_pvt_screening/netlist/tb_tg_switch_hvt_char/input.scs`
- `output/switch_pvt_screening/spectre/run_summary.json`
- `output/switch_pvt_screening/analysis/summary.json`
- `output/switch_pvt_screening/analysis/candidate_corner_summary.csv`
- `output/switch_pvt_screening/analysis/worst_case_ron.png`

## Commit policy

Commit locally after validation as `feat: screen T28 switch across PVT`.
Do not push without a separate user request.

## Completion record

- Audited and recorded the SS/TT/FF macro MOS sections and the paired high-VT
  device masters without copying restricted model contents.
- Created, checked, read back, and netlisted
  `SAR_ADC_T28/tb_tg_switch_hvt_char/schematic`; all device and source
  terminals are connected and existing SAR cellviews were untouched.
- Completed 27/27 Spectre jobs with zero errors. The batch decks produced 216
  full Ron curves and 216 full-stress leakage results and exactly reproduced
  the earlier independent TT nominal values.
- None of the eight bounded candidates met 1 kOhm at all PVT points. The best
  worst-corner result was 13.462 kOhm for standard-VT 4-um/4-um devices at
  SS/0.81 V/-40 C. The production plain-TG cell was intentionally not created;
  the next sampling-switch target must evaluate a bootstrapped architecture.
