# Transistor-level bootstrap-driver prototype

## Goal

Create the first executable transistor-level T28 bootstrap sampling switch in
Virtuoso. Use a reliability-oriented Abo-Gray topology with real PDK MOS
devices, a finite bootstrap capacitor, explicit non-overlap clocks, the
screened DNW main switch, and a representative CDAC load. Establish nominal
operation first, then run a bounded PVT/input/capacitance screen that measures
gate tracking, acquisition error, droop, feedthrough, and commanded device
terminal stresses.

This target owns the first electrical prototype. It does not freeze a
production switch, physical capacitor, clock generator, layout, or foundry
reliability sign-off.

## Dirty-state and preflight note

`main` starts clean at `1d8a6f0`, two commits ahead of `origin/main`. Bridge
0.8.0 profile `t28_io`, the tunnel, CIW `/home/chenzc_intern25/CDS.log.2`, and
Spectre 21.1 are healthy. Existing open SAR schematics are read-only. The
target cells `sar_bootstrap` and `tb_sar_bootstrap_transient` do not exist.
The required `nch_mac`, `nch_dnw_mac`, `pch_mac`, and `analogLib/cap` masters
are present.

## Resume audit

The first OA/export/single-case attempt already exists when this target is
resumed. It is not accepted as correlated evidence: the remote/exported
charge-pump devices are `MP1/MP2/MP3`, while the local source has already been
corrected to the Abo figure-5.5 `MN1/MN2/MN3` pass-device implementation.
The old TT waveform reaches only about 0.441 V at the main gate for a 50-mV
input (`VGS` about 0.391 V), and its constant-DC input lets the floating output
settle near the target during the operating point. The resume therefore owns
an exact-cell rebuild of the two planned OA schematics and symbol, followed by
a fresh export. The testbench input must step while the main switch is off so
acquisition is measured dynamically rather than inferred from a DC initial
condition.

## Local owned paths

- `plan/2026-08-31-transistor-bootstrap-driver/plan.md`
- `config/bootstrap_driver_screening.yaml`
- `config/bootstrap_driver_sizing.yaml`
- `scripts/characterization/create_bootstrap_driver.py`
- `scripts/characterization/export_bootstrap_driver.py`
- `scripts/characterization/run_bootstrap_driver_screening.py`
- `scripts/characterization/analyze_bootstrap_driver_screening.py`
- `docs/bootstrap_driver_design.md`
- bounded updates to `virtuoso/cell_manifest.yaml`, `docs/design_log.md`, and
  `plan/log.md`

Generated readbacks, exported netlists, decks, PSF, JSON, CSV, reference
figures, and plots under `output/bootstrap_driver_design/` are owned but
ignored.

## Remote OA owned objects

- new `SAR_ADC_T28/sar_bootstrap/schematic`
- new `SAR_ADC_T28/sar_bootstrap/symbol`
- new `SAR_ADC_T28/tb_sar_bootstrap_transient/schematic`

## Read-only areas

- all PDK/model content and published reference material
- all existing `SAR_ADC_T28` cellviews
- prior bootstrap-main-switch fixtures, raw exports, and results
- all other remote libraries and user windows

## Topology and initial assumptions

- Implement the reliability-oriented Abo-Gray structure: cross-coupled clock
  multiplier, unidirectional bootstrap-capacitor precharge, protected gate
  discharge, boosted-path isolation, and the main switch.
- Use real core PDK devices for the auxiliary network. Use DNW devices with
  explicit source/body tracking for the high-swing input path and the screened
  main device.
- Main switch seed: `nch_dnw_mac`, `L=60 nm`, total `W=2 um`.
- Use ideal schematic capacitors initially: parameterized clock-pump capacitors
  and `Cboot`. A MOM implementation is deferred until the required range is
  established.
- Accept external ideal `PHI/PHIB` with explicit dead time. Integrated clock
  inversion/non-overlap generation is outside this target.
- Representative single-ended load is `219.5 fF`, matching one canonical
  split-CDAC side. Initial sample clock is 10 MS/s with at least 40 ns
  acquisition time.
- Initial device sizes are starting ratios only and may be iterated from
  transient evidence. No layout-dependent diffusion/parasitic assumption is
  treated as final.

## Implementation steps

1. Create and read back `sar_bootstrap/schematic+symbol` and the transient OA
   testbench with explicit named internal nodes and reviewable placement.
2. Automatically export the OA hierarchy through the Virtuoso Spectre
   netlister; do not edit the generated circuit netlist.
3. Run a nominal TT/0.9-V/27-C transient smoke test with an off-phase input
   step at low, mid, and high target levels. Correct topology or sizing only
   from observed waveforms.
   The resumed nominal screen showed sub-nanosecond acquisition but a
   signal-dependent hold step as large as 6.46 mV with the 2-um seed, so a
   bounded 0.25/0.5/1/2-um main-switch width screen at 200 fF is required
   before any PVT expansion.
4. Sweep a bounded `Cboot` set and PVT/input grid using wrappers mechanically
   derived from the OA export. Preserve the raw export and its hash.
5. Analyze boosted-gate tracking, acquisition error, gate droop, hold step,
   leakage/droop, settling time, and every MOS `VGS/VGD/VGB/VDS/VBS/VBD`
   waveform that the exported hierarchy exposes.
6. Record the selected next-iteration seed and all blockers. Do not declare a
   production or reliability-approved switch.

## Validation and pass criteria

- exact OA library/cell/view, instance master, pin, B/D/G/S, parameter, net,
  and symbol-port readback; zero floating transistor/capacitor terminals
- Check and Save plus automatic hierarchical Spectre export without editing
  the generated circuit
- nominal waveforms show precharge, gate discharge, and boosted tracking in
  the intended phases with no simulation errors
- acquisition residual is below `0.25 LSB = 0.439 mV` for the declared passing
  cases; the held sample at the representative comparison instant also remains
  within 0.439 mV; `VG-VIN` and bootstrap-capacitor droop are reported rather
  than hidden
- all PVT jobs either complete or remain explicit failures; no target or
  coverage relaxation is allowed silently
- model-limit warnings and peak terminal differences remain explicit; foundry
  reliability sign-off is never inferred from simulator convergence
- Python compile, YAML parse, focused result assertions, waveform plot review,
  `git diff --check`, complete owned-diff review, and clean final status

## Expected artifacts

- `output/bootstrap_driver_design/readback/`
- `output/bootstrap_driver_design/netlist/`
- `output/bootstrap_driver_design/spectre/run_summary.json`
- `output/bootstrap_driver_design/analysis/summary.json`
- `output/bootstrap_driver_design/analysis/waveforms.png`
- `output/bootstrap_driver_design/analysis/pvt_summary.csv`

## Commit policy

Commit locally after validation as `feat: prototype transistor bootstrap driver`.
Do not push without a separate user request.

## Completion record

The OA topology, symbol, dynamic testbench, export correlation, nominal
Cboot/input screen, and bounded main-switch width screen are complete. All
simulations execute, but this prototype closes as a bounded no-go result:
held-sample error reaches 6.463 mV versus 0.439 mV, and the multiplier emits
core-device SOA warnings with reconstructed terminal differences up to about
1.79 V. Global PVT is not run because the nominal acceptance and reliability
gates already fail. The retained next-iteration seed is `CBOOT=200 fF` and
`MN11 nch_dnw_mac L=60 nm, W=2 um`; it is not a frozen production design.
