# PDK Primitive Characterization Baseline

## Goal

Audit the verified T28 PDK primitive/model surface and establish the first
reproducible device-characterization path between the behavioral ADC budget
and later transistor-level block design. Create only characterization
schematics whose referenced PDK cells and terminals have been verified.

## Dirty-State Note

The worktree starts clean and synchronized with `origin/main` at `dc44528`.

## Local Owned Files

- `config/pdk_mapping.yaml`
- `config/characterization.yaml`
- `docs/pdk_characterization.md`
- `scripts/characterization/`
- `virtuoso/cell_manifest.yaml`
- `plan/2026-08-30-pdk-primitive-characterization/plan.md`
- `plan/log.md`

## Remote OA Owned Objects

The following objects may be created only after their PDK masters and
terminals are verified:

- `SAR_ADC_T28/tb_nmos_char/schematic`
- `SAR_ADC_T28/tb_pmos_char/schematic`
- `SAR_ADC_T28/tb_cap_char/schematic`

No symbols, layouts, Maestro views, production ADC cells, or other OA objects
are owned by this target.

## Read-Only State

- all `tsmcN28` PDK content and model files
- every remote library other than `SAR_ADC_T28`
- existing and unrelated user windows, including unsaved cellviews
- all existing `SAR_ADC_T28` objects outside the three named characterization
  schematics
- stage-1 through stage-3 models and simulation artifacts

## Assumptions And Dependencies

- Technology: `tsmcN28`, CRN28HPC+ULL v1.8.
- The existing top-level TT include/section remain
  `/home/process/tsmc28n/PDK_mmWave/iPDK_CRN28HPC+ULL_v1.8_2p2a_20190531/models/spectre/toplevel.scs`
  and `TOP_TT`; the Virtuoso netlister is allowed to emit its PDK-managed
  embedded-usage include and verified sub-sections.
- Candidate standard devices are `nch_mac` and `pch_mac`, but their OA
  library, view, CDF parameters, and terminal order must be read back before
  instantiation.
- No capacitor cell name or non-TT section may be inferred.

## Implementation Steps

1. [completed] Preflight bridge, CIW, active windows, target library binding, and current
   target-cell existence.
2. [completed] Read the PDK library/cell/CDF surface through supported bridge APIs and
   identify verified MOS and capacitor candidates.
3. [completed] Record verified primitive mappings, parameters, and unresolved items
   locally without copying proprietary model data.
4. [completed] Create minimal NMOS/PMOS DC operating-point characterization schematics
   and, only if a capacitor master is unambiguous, a capacitor AC
   characterization schematic.
5. [completed] Read back every created schematic and netlist it before any simulation.
6. [completed] Add a local, reproducible extraction/run entry point for the verified
   characterization surface.

## Validation And Pass Criteria

- Bridge 0.8.0+, CIW, and Spectre are healthy.
- `SAR_ADC_T28` path and `tsmcN28` technology binding match the manifest.
- Every instantiated PDK master, view, terminal, and CDF parameter is recorded
  from readback rather than assumed.
- Created schematics contain only intended instances/nets and can be read
  back and netlisted without errors.
- At least the MOS TT characterization path produces deterministic operating
  point/DC evidence. Capacitor creation is allowed to remain pending if no
  candidate can be verified safely.
- Local YAML/Python checks, `git diff --check`, status review, and owned-path
  review pass.

## Expected Artifacts

- concise PDK inventory and characterization report under `docs/`
- ignored generated results under `output/pdk_characterization/`
- remote readback/netlist snapshots under ignored `virtuoso/` artifact paths

## Commit And Push Intent

Commit completed work locally as:

```text
feat: establish T28 primitive characterization
```

Push policy: not requested.
