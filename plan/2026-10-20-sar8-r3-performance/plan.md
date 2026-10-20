# SAR8 R3 nominal static and dynamic characterization

## Goal and ownership

Measure whole-ADC DNL, INL, SNDR and ENOB from the unchanged saved R3 native
hierarchy. TT/0.9V/27C, no mismatch or transient noise; deterministic sampled
performance, not noise-limited/PVT qualification. Keep100ps restore/50ps
ideal reference gates, native Bootstrap/StrongARM/async logic/MOM/3x switches,
input50ohm/side and reference50ohm+4pF/rail.

Branch exp/cdac-flat8-device, parent b742ed4. Preserve unrelated untracked
config/cdac10_dualrail.yaml, models/veriloga/cdac10_dualrail_*.va,
plan/2026-10-20-cdac10-dualrail/, scripts/cdac10_dualrail/ and
verification/cdac10_dualrail/. No dependency overlap.

Local owned: this plan, scripts/integration/r3_performance*.py,
models/veriloga/r3_performance/ (testbench measurement/stimulus only if needed),
config/sar8_r3_performance.yaml, verification/integration/r3_performance*.json
and test_r3_performance.py, docs/sar8_r3_performance.md,
docs/figures/sar8_r3_performance/, current R3 paragraph in docs/project_status.md,
plan/log.md. Ignored generated output/sar8_r3_performance/.

Remote OA owned: none. Read-only all SAR_ADC_T28/R3/source cells, all PDKs,
previous R3 and experiment sources/results. Export to unique generated path
only; never modify DUT netlist to accelerate the circuit. No push.

## Steps and acceptance

1. Read relevant bridge/Spectre skills and existing ADC analysis; verify bridge
   profile, exact saved R3 readback and fresh export against its manifest.
2. Pilot lean-output single-thread APS using identical strict tolerances and
  10ps maxstep. Validate strobed settled output against full-rate reference;
   benchmark any larger maxstep against strict timing/code output before use.
   No LX/VX or behavioral replacement. Keep logs and result.ok contract.
3. Full static: measure all255 transition locations, bracket and refine to
   declared sub-LSB accuracy (adaptive bisection preferred). Verify valid stable
   conversions, monotonicity and missing codes. Report raw nominal-LSB INL,
   endpoint-corrected INL, DNL width convention and endpoint exclusions.
   Code-center tests alone are not DNL/INL evidence. May use small independent
   batches with explicit warmup; validate history/settling and preserve bounds.
4. Dynamic: continuous coherent near-Nyquist sine, provisional1024 samples,
   461/1024*10MHz and -1dBFS differential amplitude, discard initial cycles.
   Rectangular FFT, exclude DC but retain harmonics in SNDR denominator.
   Report measured ENOB=(SNDR-1.76)/6.02 separately from full-scale normalized
   toolbox ENOB. Direct FFT/ideal quantizer sanity and ADCToolbox cross-check;
   no gain/INL/phase correction to samples before performance computation.
5. Validate exact grid/settled read window, non-rail output levels, conversion
   completion, no hidden retries/missing samples or silent filtering. Use
   native simulator logs to retain warning/CMI/LTE and startup issues. Output
   strobing reduces data, not solver accuracy, and does not prove transient SOA.
6. Inspect static and spectrum figures, curate source/deck/result provenance,
   smallest deterministic tests, compile, diff review/check; factual log and
   scoped local commit `test: characterize SAR8 R3 nominal linearity and spectrum`.

If pilot demonstrates long native runtime, report measured cost and leave jobs
explicitly running rather than claiming unmeasured performance. Full-scale
input or near-threshold failures are results to preserve, not reasons to resize
or change R3 in this target.

## State

In progress. Bridge and read-only R3 OA/native export match. Single/four-thread
APS lean-output pilots pass codes and settled-top delta<0.2nV vs old full-rate
R3; no CMI/LTE. Four-thread171s/2frames vs single312s, so choose4threads/job,
4jobs maximum, unchanged conservative/10ps/tolerances. Warned user native
full characterization is long (roughly day-scale), not a few-minute run.

Initial two output-strobe pilots failed because delay90ns>=period1ns; retained
and corrected to zero delay. First monitor/search compilation failed on
leading-dot real literals, retained and fixed to explicit leading zero.
Two superseded single-thread v2 measurement smokes were terminated by exact
verified child PIDs200318/200662 only; no CIW/Virtuoso/shared process touched.
v3 sources snapshot message state, preserving delayed-strobe indices/values.
Source snapshots are content-addressed and queued jobs read immutable copies.

Final observer validates8CMP edges and90/98ns settled/rail-valid output;
internal W/U pulses are NOT observed (top interface lacks those ports).
Static uses six bisections inside checked±0.25LSB brackets: width1/128LSB.
Both v3 measurement smokes result.ok: two adjacent static thresholds/9frames,
and sine4-point measurement smoke/5frames. All measured frame counts8CMP,
90/98ns stable valid rails; static brackets/search/source checks pass. Static
smoke has one SPECTRE-16780 LTE relaxation at666.991ns in native reference
control; preserved and disclosed. Numerical-quality flag/report warns on any
LTE/suppression or CMI; functional smoke pass is not numerical signoff.

The one-shot flow passed pilot/smoke analyzers and3 focused math/DUT-identity
tests; FULL batch started2026-10-20T14:59:35Z (22:59:35 local),4workers×4threads.
Queued continuous1024point sine + four255-transition ranges. Full completion
automatically runs the offline analyzer and writes ignored report/summary/
figures; failures are explicit status. No scheduling/notification or push.
Raw status output/sar8_r3_performance/flow_status.json, local flow exec session
25763 (process can outlive this turn; retain local runner/SSH availability).

No final DNL/INL/SNDR/ENOB yet. Curated setup-only manifest, source/report/
config and raw failure/supersession records retained. Compile, focused tests,
diff-check/review done for the current setup checkpoint, not the final
characterization. Plan remains incomplete until the native full batch and
resulting analysis are genuinely finished. Local scoped checkpoint commit
only, no push; unrelated user work untouched.
