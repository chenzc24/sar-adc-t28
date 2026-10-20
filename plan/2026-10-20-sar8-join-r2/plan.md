# SAR8 aligned reference timing in saved OA

## Goal

Adopt the validated ideal shared reference timing as a new development top
SAR_ADC_T28/sar_adc8_join_r2, not overwrite frozen R1. Preserve native circuit
connections, dimensions, sample timing and 50ohm/4pF reference networks.
This does not implement a transistor timing synchronizer or fix acquisition
restore overvoltage. It is not full ADC qualification.

## Ownership and initial state

Branch exp/cdac-flat8-device, starting HEAD7c648af. Unrelated untracked
cdac10_dualrail config/VA/plan/scripts/verification remain untouched.
Owned local paths: this plan; config/sar8_join_r2.yaml;
models/veriloga/sar8_join_r2/; .gitattributes (LF rules for two new VA files);
scripts/integration/join_r2.py, join_r2_sim.py, join_r2_analyze.py;
verification/integration/test_join_r2.py, join_r2_results.json;
docs/sar8_join_r2.md; docs/project_status.md (current R2 pointer only);
plan/log.md (append only); ignored output/sar8_join_r2/.
Remote owned NEW objects, all in SAR_ADC_T28:
sar8j_refcommit/{symbol,veriloga},
sar8j_aligned_refgate/{symbol,veriloga},
sar_adc8_join_r2/{schematic,symbol}, tb_sar_adc8_join_r2/schematic.
No existing target may be overwritten without a matching ownership receipt.
All existing OA, frozen R1, prior alignment experiment, PDK and other projects
are read-only. No GUI close/restart, no deletion. Local commit only; no push.

## Implementation

1. Reconnect t28_io; inspect status/windows/library and native frozen hashes.
2. Split the exact tested two-module VA into two cell files with no semantic
   change. Create symbols/VA through supported bridge APIs; read back bytes,
   port order and parameters. No placeholder floating-pin schematic left.
3. Recreate a new top from R1's declared circuit, reuse its native CDAC and all
   analog/controller cells. Swap only16 ideal gate masters, add shared COMMIT
   port/net and one ideal notifier observing all32 actual native requests.
4. Build identical new testbench referencing the new top. Check/save and
   require exact API connectivity/parameter readback, zero check markers.
5. Export from saved new OA, retain untouched export. Audit all native bodies
   and compare new top against tested aligned deck (allow top name only).
   Any port/parameter/order discrepancy must be corrected in OA, not patched
   into the simulation DUT netlist.

## Verification

Use native Spectre21.1 APS, TT/.9V/27C, two200ns negative-full/negative-half
cases, maxstep10ps/full solver output, unchanged R1 tolerances/stimuli/loads.
Prepare only analysis/stimulus/include wrappers around exact OA DUT. Require
result.ok, finite data, correct14/127 codes,8 native compares/writes/updates
per frame, reference mapping and compare error<1.7578125mV, no gate enable
overlap, BBM>=99.8ps and common changed-bank thresholds within.1ps.
Report six-pair reference/comparator maxima and original acquisition failure;
do not require a false whole-circuit SOA pass. Compare with prior netlist-only
aligned evidence and retain any deviation. Final OA readback/native frozen
hashes, Python compile, focused tests, diff-check, factual log, scoped commit.
Expected source/metrics/report tracked; exact export/readback/logs/PSF/waves
in output/sar8_join_r2/. No new PVT/noise/MC/full-code sweep.

## Progress

- Fresh t28_io tunnel/CIW/Spectre healthy. Correct user, host thu-wei and CIW
  cwd /home/chenzc_intern25/TSMC28/llm_IO confirmed.16 existing windows,
  none of the new targets. R1 is open and will be left untouched.
- Created only the four named cells/views. Both VA modules match the exact
  tested module bodies and remote byte readback. Top112/TB26 instances and all
  declared connections/parameters match; no check markers. R2 opened as window17;
  old windows not closed. No floating-pin placeholder schematic was created.
- Saved-OA export audited: all32 native hierarchy bodies unchanged, top112
  electrical statements equal tested alignment (top name excepted); no DUT
  patching in simulation wrapper. Postflight34 existing frozen cells unchanged.
- Two APS result.ok runs/four frames reproduce prior alignment metrics exactly:
  reference conversion peaks.951088/.951079V, max errors.807895/.560789mV,
  correct14/127 codes,8 comparisons/writes/updates per frame. BBM100ps and
  zero numerical changed-bank skew. Negative-full acquisition1.136126V remains;
  10 printed CMI and repeats retained. Half-LSB0CMI; seven config warnings each,
  zeroLTE. Active development R2 adopted, not marked qualified/frozen.
