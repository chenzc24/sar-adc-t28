# R4 reference reset in the preceding idle interval

Status: completed bounded native experiment; independent candidate only.

## Goal and boundaries

User requests moving MSB-first reference initialization after the preceding
conversion, restoring the acquisition window without moving the closing edge,
and checking terminal stress and codes. Preserve frozen R4 and prior experiments.
No OA mutation, baseline promotion, push, PDK change, FFT or PVT claim.

Initial branch exp/cdac-flat8-device is ahead 5 at 064033d. Existing user
Obsidian moves/edits/images and 10-bit dual-rail files are unrelated and preserved.
Global unstaged diff check reports pre-existing trailing whitespace in the user's
Obsidian Report line13; not changed. All owned/staged diff checks pass.
Own this plan, scripts/sar8_r4_idle/, netlist/sar8_r4_idle/,
verification/sar8_r4_idle/, docs/sar8_r4_idle.md,
docs/figures/sar8_r4_idle/, and append-only plan/log.md.
Generated artifacts: output/sar8_r4_idle/. Remote OA owned: none.
Remote unique simulation scratch only; archive evidence locally, not as OA.
Read-only dependencies: native R4, staged/reset scripts and cases, model sections,
source sine fixture, all other project files and remote libraries.

## Implementation

1. Reuse native MSB-first reset cells and analog circuitry unchanged. Export
   controller ACTIVE through a cloned controller port. After ACTIVE drops,
   delay idle qualification long enough to pass the final reference capture.
2. Reference preset request is SAMPLE OR delayed idle, so it begins in the
   previous idle tail, stays asserted through sampling, and releases before
   conversion. Only reference store resets move; SAR data resets stay on SAMPLE.
3. Separate Bootstrap enabling from reference reset completion; use the former
   AND/buffer/edge falling path driven by SAMPLE to preserve nominal closing
   delay and restore the A-width (~38.29 ns). No ideal additional clocks.
4. Startup has no preceding conversion: preserve deterministic DC initialization,
   explicitly audit the first frame rather than omit it.

## Validation

Verify t28_io SSH/profile/simulator and resources; no shell commands through CIW.
Use immutable unique cases, native Spectre X CX, at most two jobs x four threads.
Start 600 ns, then if functional proceed to 4.6 us; perform a short honored-option
recheck of a relevant event if practical. No duplicate launches. Preserve failures.
Validate netlist hierarchy/ports, unchanged analog leaf hashes and provenance.
Save native adaptive points: all selected MOS terminal pairs including added
logic, last comparison/write/update/capture, ACTIVE, reset taps, sampling controls,
Bootstrap gate, reference word, and output data.
Check native exit/logStatus, warnings/CMI, complete finite monotonic waveforms.
Independent 8/8/8/16 frame edges, native/decoded codes and stability during idle
reset, reset after last capture falls and before next acquisition, word 128 before
sampling, resets released before first compare, no H/L logic overlap.
Acquisition window target >=38.2 ns; sampling closing edge difference <=50 ps
against staged control (finite native loading/numerical variation, not exact
physical aperture equivalence). Report actual edges and gate waveform differences.
Stress gates: core <=0.99 V, IO <=1.98 V, no native CMI; selected-terminal coverage
only. Code differences vs A/staged/frozen are diagnostics; do not reuse old FFT.
If moving reset exposes a new stress or functional failure, report it rather than
claim success or expand topology without updating the plan.

## Deliverables

Curated candidate/netlist provenance, metrics, readable timing/stress/code figures
and concise report, inspected visually. Update plan/log, scoped diff check and
review, then local commit `experiment: move staged reference reset into idle`.
Do not push or replace R4. No experience extraction without user request.

## Results

- Native same-DUT runs:600ns/6frames,4600ns/46frames, honored200ns/2frames.
  Exit0, logStatus PASS, zero errors, no CMI. Native MOS/RC idle qualification;
  no additional ideal clock. All445selectedMOS six-pair checks pass.
- Long741399points,46independent8/8/8/16frames and idle resets,45post-startup
  acquisitions pass. Reference word128 at startup and each acquisition; data
  stable through reference reset until next SAMPLE rise minus50ps (last frame
  to trace end). Minimum final-capture-to-reset guard3.815363ns.
- Reset actions~76.1–80.7ns; minimum acquisition38.262366ns versus old33.848142ns;
  falling control at~41.123ns, max11.094469ps earlier than staged control.
  No intentional closing phase change; finite loading prevents exact equality.
- Long reference0.955795153V at3976.416832ns, P5PMOSVgb,34.204847mV margin;
  driver0.978546596V, comparator0.952064978V, sequencer0.959576244V,
  bootstrapIO1.751946253V. No strict replay of the3976ns long-worst event.
- Strict200:324663points, reference0.945141089V (~0.060mV from ordinary short
  worst), driver0.979259945V (~10.740mV margin). Actual10ps/1e-7/10nV/100fA;
  ordinary CX600/4600 actualmaxstep6/46ns and1e-4/1uV/1pA, not equal accuracy.
- Two+1code changes versus old staged at indices16,32; same41.8ns held
  differential changes+0.182895/+0.217379mV. Not unique cause attribution,
  no full-code/FFT equivalence claim. Versus A changes13,26; frozen R4 also9,36.
- Native9.72GB and4.25GB PSFs locally retained, uncompressed SHA256 matches
  remote. Every sample preserved, exact saved signals/finite monotonic time/end
  checks pass. No reruns, transfer recovery, model edits, OA or baseline changes.
- Three final figures visually inspected; curated netlist/metrics/report and
  focused script execution/compilation, frozen hashes and scoped diff reviewed.
  User Obsidian/10bit changes untouched. Scoped local commit; no push.
