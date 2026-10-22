# R4 staged reference initialization and gate holding

Status: completed bounded experiment; MSB-first is a candidate only. No R4/OA
promotion or full ADC/PVT qualification.

## Scope and ownership

User authorized the next round after reset-first A improved but failed stress.
Keep R4, prior experiment008c616, PDK and all OA read-only. No baseline
promotion, push, Obsidian edit, full FFT or PVT claim in this bounded round.
Dirty Obsidian moves/edits/images and10-bit dual-rail work are unrelated and
preserved. Branch starts ahead4. No parallel agents requested.
Global diff check observes pre-existing trailing whitespace in the user's
Obsidian Report line13; leave it untouched and validate only owned paths.

Own: this plan; scripts/sar8_r4_staged/; netlist/sar8_r4_staged/;
verification/sar8_r4_staged/; docs/sar8_r4_staged.md;
docs/figures/sar8_r4_staged/; plan/log.md append only.
Generated: output/sar8_r4_staged/. Remote OA owned: none.
Unique remote raw jobs under a task-specific temporary directory, downloaded
locally; never use temporary paths as source-of-truth project storage.

## Design and experiment sequence

- Start from native reset-first A. Keep analog sampling/CDAC/comparator and
  3x reference pass MOS unchanged; preserve original conversion timing.
- Clone reference-word cell with per-bit asynchronous reset taps. Test both
  LSB-first and MSB-first native RC delay chains. Keep P/N bit pairing and
  original nonoverlap. Gate delayed taps with SAMPLE for prompt release;
  start Bootstrap only after last reset plus existing A settling delay.
- Independently screen halved gate resistance (parallel resistor multiplicity)
  and doubled final native driver multiplicity. No geometry-tail rewriting.
- Begin five600ns cases: A control, two reset orders, R/2 only, drive2x only.
  First run a 1ns instrumentation smoke case to validate native current saves.
  Same sine/source history/solver settings;600ns includes known501ns failure.
  At most two jobs in parallel,4threads each, subject to remote resource check.
- Based on evidence, at most two small combined/refined600ns candidates.
  Promote the best function/stress candidate to a bounded4.6us replay; inspect
  all reset events, not only401ns. If it fails, report failure before another
  topology expansion. A promising candidate receives honored-options numerical
  checking; full-code/spectrum requalification is a separate follow-up.

Screening decision: both orders passed600ns; MSB-first reference peak0.945182V
versus LSB-first0.961044V, so select MSB-first for full0–4.6us adaptive saves.
Use a strict300ns replay covering its201.389ns short-screen worst event;
this is a bounded numerical check, not strict4.6us qualification. No combined
refinement is needed before the selected candidate replay. For large raw data,
transfer an independent gzip copy and verify the uncompressed SHA256 against
the remote native file; retain original native files and logs unchanged.
The original long gzip download timed out during an anomalous elapsed wait;
native46frames/exit0/noCMI were already complete. Recover that same archive
once using verified256MiB parts, retaining manifests and hashes. No rerun,
no overwritten raw cases, no installed bridge patch or unrelated process stop.

## Execution and validation

Use native Spectre via verified t28_io SSH; EVAS has no transistor solver.
Read-only bridge/simulator preflight; never use CIW for shell execution.
Use unique immutable cases and a launch receipt; no duplicate submissions.
Use supported SSH transfer/execution and preserve native exit/logStatus/PSF
evidence. Stream PSF data from the start rather than changing installed tools
or using the memory-heavy whole-file reader. Reuse prior verified parser;
validate any extension for branch currents before relying on it.

Before launch: frozen/candidate hash audit, allowed cell/parameter diff,
port-count/connectivity checks, compilation. No behavioral drive added.
Save all32reference MOS endpoints, comparator/Bootstrap and added sequencing
endpoints, reference-driver MOS endpoints, reset taps and frame clocks/codes.
Save representative gate-resistor branch currents if supported; direct current
sign/path attribution requires verified netlist terminals, not assumptions.
All six terminal pairs: core0.99V, IO1.98V screen. Native CMI anywhere fails
even if the saved window excludes it. Independent frame decode/8-8-8-16
timing/stability in saved whole frames; native monitor elsewhere. Check reset
order/completion/release, acquisition window and representative nonoverlap.
Code differences against R4 and A are diagnostics, not automatic pass/fail.
No noise/PVT/mismatch/PEX or whole-chip reliability qualification.

Read effective tolerances/maxstep, inspect native errors and full duration.
Plot source nodes and terminal stress with limit lines and test conditions;
view figures. Report which ideas failed, margins, sampling cost and remaining
limits. Update plan/log, scoped diff check/review, local owned-file commit:
`experiment: evaluate staged reference reset and gate holding`. No push.

## Result and validation

- Instrumentation1ns: four native resistor-current channels verified.
- Five600ns jobs complete, six independent frames each. Reference peaks:
  A0.991063V, LSB0.961044V, MSB0.945182V, R/2 1.056698V,
  driver2x0.995498V. The three failing alternatives remain documented failures.
- MSB4600:724408points,46independently decoded/timing-valid frames,45
  restart order/release/acquisition checks, selected417MOS six-pair screen
  pass, no CMI. Ref peak0.955838V at4001.388523ns, P5 PMOS Vgb.
- MSB strict300:467168points,3independent frames, no CMI, reference max
  0.945142V; actual10ps/1e-7/10nV/100fA. Covers the short201ns event,
  not the new4001ns long-run worst. Reference-driver max0.979259V.
- Long acquisition minimum33.848142ns versus A~38.288ns; falling control
  moves~27ps. Four46-frame code changes versus A, six versus R4, all +/-1;
  no FFT equivalence claim. RST_DONE is a fixed-delay command marker, not
  analog-settling feedback. Native H/L nonoverlap is logic-level only.
- Native exit0, zero-error summary, logStatus PASS, complete finite monotonic
  scalar PSF, exact saved signal sets and remote/local SHA256 confirmed.
  One long transfer timeout recovered in11hashed chunks; no native rerun.
- Frozen DUT and original sine deck hashes unchanged; script compilation,
  focused executions, figures visually inspected, scoped diff checked.
  User Obsidian/10bit changes and prior commits remain untouched.
