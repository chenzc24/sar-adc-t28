# Bootstrap-driver held-error reduction screen

## Goal

Find a transistor-sizing and clock-non-overlap direction that materially
reduces the complete bootstrap driver's signal-dependent held-sample error.
Screen the protected gate-discharge devices `MN7/MN10`, boosted-path isolation
device `MP8`, and the delay from `PHI` falling to `PHIB` rising using the exact
OA-exported hierarchy as the baseline.

This is an analysis-only topology-preserving screen. It does not mutate OA,
claim raw 0.439-mV compliance, expand PVT, or waive the independent core-device
SOA blocker. A winning candidate must be confirmed over the full nominal input
set before any later OA implementation target.

## Dirty-state and preflight note

`main` starts clean at `2e3ae32`, four commits ahead of `origin/main`.
Virtuoso Bridge 0.8.0, the `t28_io` profile, CIW
`/home/chenzc_intern25/CDS.log.2`, and Spectre 21.1 are healthy. Windows 28 and
29 show the existing bootstrap DUT and testbench; both remain read-only.

The source OA export is
`output/bootstrap_driver_design/netlist/tb_sar_bootstrap_transient/input.scs`
with SHA-256
`f3818ef606de602671beac8b6728a1f5460958d03ca0299de0fc79e28132242c`.

The installed `evas-sim` guidance was checked because this target runs a
Spectre netlist. EVAS cannot solve transistors or Spectre subcircuit hierarchy,
so the only valid simulator here is the configured foundry Spectre flow.

## Local owned paths

- `plan/2026-08-31-bootstrap-driver-error-reduction/plan.md`
- `config/bootstrap_driver_error_reduction.yaml`
- `scripts/characterization/run_bootstrap_driver_error_reduction.py`
- `scripts/characterization/analyze_bootstrap_driver_error_reduction.py`
- `docs/bootstrap_driver_error_reduction.md`
- bounded updates to `docs/design_log.md` and `plan/log.md`

Generated decks, PSF, JSON, CSV, and plots under
`output/bootstrap_driver_error_reduction/` are owned but ignored.

## Remote OA owned objects

None. Every `SAR_ADC_T28` cellview is read-only in this target.

## Read-only dependencies

- exact automatic OA export and its PDK model includes
- `SAR_ADC_T28/sar_bootstrap` and `tb_sar_bootstrap_transient`
- PDK libraries, model files, and shared remote state
- previous bootstrap characterization and ablation results

## Screen structure

1. Preserve the exact exported `sar_bootstrap` subcircuit, changing only one
   audited instance multiplier or the external clock timing in each generated
   analysis deck.
2. Run one-factor screens around the baseline:
   - `MN10 multi = 2/4/8/16` for discharge pull-down strength;
   - `MN7 multi = 1/2/4/8` for the protected series device;
   - `MP8 multi = 1/2/4/8` for boosted-path isolation/feedthrough;
   - `PHI-fall -> PHIB-rise = 0.2/0.5/1/2 ns` while preserving the sample
     interval and all other source/load conditions.
3. Rank at `Vdiff=+0.8 V` by raw held error, acquisition error, turn-off step,
   hold drift, off-gate voltage, sample `VGS`, and bootstrap-node behavior.
4. Combine only the best non-conflicting directions in a small second screen.
5. Confirm the baseline and finalists over differential
   `-0.8/-0.4/0/+0.4/+0.8 V` and single-ended `0.05/0.45/0.85 V`.

Device widths are not inferred from voltage or gain alone. The screen treats
multiplier changes as simultaneous changes in drive resistance and parasitic
charge; a lower held error that breaks acquisition, gate overdrive, or worsens
reported terminal stress is not a winner.

## Validation and pass criteria

- exact source-export hash and targeted-instance statements are asserted
- every scheduled Spectre case is retained, including failures
- generated decks differ from the source subcircuit only in the declared
  `MN7`, `MN10`, or `MP8` multiplier substitutions
- baseline reproduces the prior 12.026-mV full-differential error
- finalist confirmation reports raw and best-fit differential error without
  silently applying calibration
- acquisition error remains below 0.439 mV and sample main-switch `VGS`
  remains within the previously observed useful range
- Spectre warnings and reconstructed terminal stresses are compared with the
  baseline; no reliability improvement is claimed from nominal simulation
- plots are visually inspected; Python compiles; YAML parses; focused result
  assertions, `git diff --check`, owned-diff review, and clean final status pass

The preferred outcome is raw differential held error below 0.439 mV. If no
candidate reaches it, report the bounded best direction and keep OA unchanged.

## Expected artifacts

- `output/bootstrap_driver_error_reduction/spectre/run_summary.json`
- `output/bootstrap_driver_error_reduction/analysis/summary.json`
- `output/bootstrap_driver_error_reduction/analysis/case_summary.csv`
- `output/bootstrap_driver_error_reduction/screen_analysis/screen.png`
- `output/bootstrap_driver_error_reduction/analysis/finalist_waveforms.png`

## Commit policy

Commit locally after validation as
`test: screen bootstrap driver error reduction`. Do not push without a
separate user request.

## Completion record

Completed without OA mutation. The official evidence includes 13 successful
one-factor cases, eight successful baseline/combination cases, and 24
successful full-input confirmation cases. One intermediate SSH upload failure
was retained and the exact case reran successfully.

The reasonable `MN7/MN10/MP8=8/16/1`, 0.2-ns-gap combination reduced maximum
raw differential error only from 12.026 to 10.298 mV. An extreme 16/32/1
combination reached 9.097 mV but reduced minimum sample VGS to 0.742 V. Its
post-discharge step and hold drift are effectively zero, proving that the
remaining dominant error is created at the immediate PHI turn-off edge. The
maximum reconstructed terminal difference remains 1.787 V and PDK SOA
warnings remain. No candidate meets 0.439 mV; OA was deliberately left
unchanged. The next target is independent isolation/charge-cancellation
topology rather than further discharge-device widening.
