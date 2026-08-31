# Transmission-gate switch characterization

## Goal

Create the first PDK transistor-level switch fixture and use it to derive a
TT/27 C width envelope for the CDAC bottom-plate and input-sampling paths. The
target is a measured on-resistance below the current 1-kOhm macro-model
allocation across the 0-to-0.9-V signal range, while preserving enough data to
judge resistance flatness and off leakage. This target produces an initial
sizing candidate, not a PVT- or mismatch-frozen production switch.

## Dirty-state note

`main` starts clean and five commits ahead of `origin/main`. The target bridge
profile is `t28_io`; tunnel, CIW daemon, and Spectre are healthy. A separate
Virtuoso session contains an unsaved `ISCAS_IO_T28/IO_RING_T28_12x12_03`
schematic and an Edit Object Properties dialog. They are unrelated, belong to
another display/session, and are protected from all actions in this target.
The active SAR CIW is `/home/chenzc_intern25/CDS.log.2` on `thu-wei`.

## Local owned paths

- `plan/2026-08-31-transmission-gate-switch-characterization/plan.md`
- `config/switch_characterization.yaml`
- `scripts/characterization/create_switch_testbench.py`
- `scripts/characterization/export_switch_testbench.py`
- `scripts/characterization/run_switch_characterization.py`
- `scripts/characterization/analyze_switch_characterization.py`
- `docs/switch_characterization.md`
- bounded updates to `virtuoso/cell_manifest.yaml`, `docs/design_log.md`, and
  `plan/log.md`

Generated OA readback, exported netlists, Spectre PSF, CSV, JSON, and plots
under `output/switch_characterization/` are owned but ignored.

## Remote OA owned objects

- new `SAR_ADC_T28/tb_tg_switch_char/schematic`

No production switch, symbol, layout, Maestro view, or integrated ADC cellview
is owned by this target.

## Read-only areas

- all `tsmcN28` PDK/model content
- all remote libraries except the one new testbench in `SAR_ADC_T28`
- every existing `SAR_ADC_T28` cellview
- all unrelated and unsaved Virtuoso windows
- existing behavioral, macro-model, and PDK-characterization sources/results

## Shared dependencies and assumptions

- Supply/reference range is 0 to 0.9 V and the current macro-model switch
  allocation is 1 kOhm nominal.
- The verified standard-VT devices are `tsmcN28/nch_mac` and
  `tsmcN28/pch_mac`, with minimum characterized length 30 nm.
- The fixture uses parallel NMOS/PMOS devices, independent complementary gate
  sources, tied bodies, and a 1-mV differential probe around a swept common
  mode. The OA schematic owns topology; the analysis deck may parameterize
  CDF-emitted widths and source values but may not rewrite connectivity.
- Only the already verified PDK-emitted TT model sections are used in this
  first sizing pass. PVT corner names will be audited in a separate bounded
  increment before any width is frozen.

## Implementation steps

1. Verify the exact target cell is absent and re-read the two PDK masters and
   terminal/CDF surface.
2. Create `tb_tg_switch_char/schematic` with one standard-VT transmission gate,
   complementary control sources, two signal probe sources, and explicit
   VDD/VSS body connections.
3. Read back and export the OA schematic without editing the generated source
   netlist.
4. Build analysis-only Spectre decks for a bounded NMOS-width and PMOS-ratio
   sweep; measure Ron versus common mode and off leakage.
5. Select the smallest initial candidate satisfying the 1-kOhm nominal limit,
   report resistance flatness and headroom, and record why it is not yet a PVT
   sign-off size.

## Validation and pass criteria

- exact OA library/cell/view and PDK master/terminal readback match the plan
- schematic check/save and API readback show the intended two MOS devices,
  five sources, body connections, and no accidental nets
- automatic Spectre export contains the intended parallel MOS topology
- every requested TT case completes with zero Spectre errors
- extracted Ron is finite and positive at every sampled common-mode point;
  off leakage is reported for the 0.9-V stress condition
- at least one width pair meets `max Ron <= 1 kOhm`, or the target reports a
  bounded no-solution result instead of silently relaxing the requirement
- Python compile checks, focused result checks, YAML parse, `git diff --check`,
  owned-path review, and final status pass

## Expected artifacts

- `output/switch_characterization/schematic_readback.json`
- `output/switch_characterization/netlist/tb_tg_switch_char/input.scs`
- `output/switch_characterization/spectre/`
- `output/switch_characterization/analysis/summary.json`
- `output/switch_characterization/analysis/ron_vs_common_mode.csv`
- `output/switch_characterization/analysis/ron_vs_common_mode.png`

## Commit policy

Commit locally after validation as `feat: characterize T28 transmission-gate switch`.
Do not push without a separate user request.

## Completion record

- Verified `SAR_ADC_T28` remains bound to `tsmcN28`, the target cell was
  absent, and both standard-VT PDK masters retain the expected B/D/G/S and CDF
  surfaces.
- Created and read back `tb_tg_switch_char/schematic`, then exported it through
  the Virtuoso Spectre netlister. No existing SAR or unrelated OA cellview was
  modified.
- All 12 TT/27-C width cases completed with zero Spectre errors; four met the
  1-kOhm criterion. `Wn=Wp=2 um, L=30 nm` is the minimum-total-width passing
  seed with 911.4-Ohm maximum Ron.
- The selected seed measured 36.0-nA off leakage at 0.9-V stress. The width is
  therefore not frozen; PVT, realistic hold states, and transient nonidealities
  remain explicit next gates.
