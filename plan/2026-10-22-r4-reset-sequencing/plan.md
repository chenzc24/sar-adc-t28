# R4 reset / acquisition sequencing experiment

Status: complete — bounded A/B experiment reviewed; overvoltage NOT resolved.

## Scope

User authorized A/B experiments to reduce reference-switch overvoltage.
Preserve frozen R4 and all historical results. Begin with all-bit observation
and short continuous-sine replay; promote only a stress/function-passing
candidate to longer checks. No automatic baseline replacement or push.

Dirty state: user Obsidian edits/moves/images and untracked 10-bit dual-rail
work remain untouched; current branch is ahead of origin by three commits.

Owned local paths: this plan; scripts/sar8_r4_reset/;
verification/sar8_r4_reset/; netlist/sar8_r4_reset/;
docs/sar8_r4_reset.md; docs/figures/sar8_r4_reset/; plan/log.md append only.
Generated cases: output/sar8_r4_reset/, immutable case names.
Remote OA owned: none. No schematic edits. Unique bridge Spectre run paths
only; downloaded results retained locally. No CIW shell execution.
Read-only: netlist/sar8_physical, existing performance/refstress results,
all PDK/OA, Obsidian, other experiments, installed tools and libraries.

## Design and method

- R4 baseline plus A (reference reset before sampling) and B (sampling before
  reference reset). Keep analog device sizing and reference 3x banks intact.
- Implement candidate sequencing with copies of existing native PDK-RC/MOS
  delay and logic cells. Prefer delayed rising / prompt falling signals;
  document real falling-edge differences rather than claim unchanged aperture.
- Keep original external SAMPLE and SAR timing. A changes only Bootstrap
  enable; B changes reference initialization input, not the SAR sample/reset.
- Capture all 16 bottoms, 32 reference gates, driver outputs, reference words,
  top/input/control voltages and output codes. Derive all six terminal-voltage
  magnitudes for all reference MOS. Extend observation to comparator/Bootstrap
  and new sequencing devices before qualifying a candidate.
- First short replay 0–500 ns covers the known 401.35-ns event. Later replay
  through at least 4.6 us covers known gate events near 2.501/4.501 us.
- Same external sine frequency/amplitude/history. Use native Spectre,
  inspect effective solver settings; CX screening is not precision signoff.
  Verify promising events with honored maxstep/tighter solver settings.

## Preflight and validation

Bridge t28_io tunnel currently down, but SSH to thu-wei succeeds. Netlist-only
simulation does not require live OA. Require Spectre executable/license check;
do not modify or claim current OA equivalence for experimental variants.

Before launch: immutable DUT hash, strict allowed-difference check, connectivity
and deck checks; compile scripts. Reject duplicate case execution.
Require native result.ok / full duration / complete monotonic waveforms.
Check frame counts and 8 compare/write/update / 16 capture events, output
stability, actual sample edges, acquisition and conversion time. Compare codes
to baseline where aperture permits; code agreement alone is not stress pass.
No CMI suppression-based success: compute peak stress on saved adaptive data,
include startup and all observed phases. Core/IO screen 0.99/1.98 V, retain
uncertainty and margin; inspect raw logs and effective timestep settings.
Visual inspection and scoped diff review before local commit. If neither A nor
B passes, report actual failure before expanding to staged reset/driver redesign.

## Deliverables

Versioned candidate netlists/provenance, run/analysis scripts, result JSON,
comparative waveforms and concise report. Factual log and scoped local commit
`experiment: compare R4 reference-reset and sampling sequencing`; no push.

## Initial evidence and next bounded runs

All three 500-ns native CX runs completed with correct five-frame codes/timing.
Reference max: baseline1.011292V, reset-first0.989420V, sample-first1.022525V.
Reset-first is only0.580mV below the screening limit, not a robust fix.
Run an honored-options 10-ps/tighter-tolerance 500-ns check and a continuous
4600-ns reset-first replay covering the known late gate events. For the latter,
save adaptive waveforms from2398ns; all preceding frames still have native
monitor records, but no independent waveform/stress pass is claimed for the
unsaved interval. Startup was observed in the separate500-ns run. Short runs
currently save voltages only; current attribution remains pending, not inferred.

Precision native simulation completed with zero errors and logStatus PASS.
Its 3.916-GB ASCII output makes the installed whole-file reader memory-heavy.
After confirming the exact owned launch PID38252 and complete downloaded native
files, stopped only that local postprocessing helper; no simulator was stopped.
Use a task-local streaming parser, cross-check it against the completed baseline
wave, retain native data/runner log and record recovery explicitly. Do not alter
the installed bridge or invent a captured original process exit code.

## Final results and disposition

All five native runs completed with zero-error native summaries. Short baseline,
A and B reference peaks1.011292/0.989420/1.022525V; all five-frame functional
checks pass. Honored-options A:10ps, reltol1e-7, reference0.989263V; five frames
pass, no observed selected-device violation. Stream recovery matches baseline
all129vectors exactly;731726 precise samples retained with native/PSF hashes.

Long A:46 native-monitor-valid frames, independently checked saved frames24–45.
Saved2.398–4.6us reference worst0.991464Vbd at4401.359312ns (P6 PMOS), plus
0.990910Vgb at4501.400121ns (N3 NMOS). First native CMI already501.359ns in
the unsaved interval. N3 gate0.990910V while driver0.902865V and Q3 stays low;
driver-side and bottom-side issues remain distinct. Original-sine code changes
only at indices9(+1) and36(-1); no FFT/linearity equivalence claimed.

Reject B; retain A only as an experimental starting point. Do not promote,
modify OA, replace R4, or launch full characterization. Next proposed target:
staged native reference initialization and bounded gate-driver/R tests, with
current evidence and all-bit stress checks. No further topology work this round.
Three figures visually inspected; scripts compiled/executed, frozen hash and
native-cell inventories checked, scoped diff reviewed. Local commit only.
