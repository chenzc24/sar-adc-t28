# SAR8 earlier CDAC reference restoration

## Goal and ownership

Netlist-only compare restore_guard_s=0.1ns/0.5ns against immutable R2=2ns.
Keep topology, all sizes, reference50ohm/4pF, sample phase,100ps BBM,20ps edges,
200ps conversion commit and ALL VA source bytes unchanged. No OA modifications
or adoption. First bounded case: constant differential input -0.8V, TT/.9V/27C.
Use existing exact full-rate R2 nfull as2ns baseline; two fresh runs only.

Starting branch exp/cdac-flat8-device, HEAD2c723d8. Unrelated untracked
cdac10_dualrail config/three VA files/plan/scripts/verification are untouched.
Owned local paths: this plan, plan/log.md (append only),
scripts/integration/restore_guard.py, restore_guard_analyze.py,
verification/integration/test_restore_guard.py, restore_guard_results.json,
docs/sar8_restore_guard.md, docs/figures/sar8_restore_guard/,
ignored output/sar8_restore_guard/.
Remote OA ownership: none. R1/R2 sources/results/exports, all models, foundry
PDK and every OA cell are read-only. Simulator owns fresh unique job directories.
Local scoped commit only; no push. No destructive cleanup.

## Implementation and validation

1. Fresh t28_io status (healthy CIW/Spectre already checked). Read R2 frozen
   source/VA/deck/wave fingerprints and require them to match curated manifest.
2. Derive decks from exact R2 nfull deck. Add ONLY16 per-instance restore_guard_s
   assignments. Removing these must reproduce original deck byte-for-byte after
   newline normalization. No source edits or body/size/other timing changes.
3. Native APS,200ns,maxstep10ps,full solver output and same tolerances/save set.
   Require result.ok and finite complete waveforms; no strobes hiding peaks.
4. Scan reference32MOS/comparator11MOS six-pair stress, including second
   acquisition101.05..141.05ns and conversion. Preserve true CMI/suppressed/LTE
   messages and configuration warnings. Passing means <=.99V for scanned pairs,
   not whole-device/layout/lifetime/PVT qualification.
5. Report separately: pre-off acquisition errors (hold-.1ns), held error
   (hold+.5ns) and first pre-comparison error; P/N individual and differential
   against source input, not only against post-RIN nodes. Hold41.05/141.05ns.
   Require correct14 code/two frames,8 comparisons/writes/updates, correct
   mapping/token/decisions, all compare errors<1.7578125mV, BBM>=99.8ps/no overlap.
6. Measure actual restore gate edges; guard is command delay, not time of new
   rail50% crossing (guard+100ps+10ps). Compare all three on one actual-time plot
   with input targets and stress thresholds; inspect rendered figure.
7. Curate source/deck/wave identities, metrics, concise local report and tests.
   Check R2 sources intact, Python compile, focused tests, diff-check, log and
   scoped commit: test: compare earlier SAR8 reference restoration timing.

## Progress

- Plan created before tracked edits. No OA changes intended.
- Completed two native Spectre21.1 APS runs (100ps/500ps),200ns/maxstep10ps/full
  solver output. Reused exact fingerprint-checked R2 nfull as2ns control. Only16
  parameter additions; R2 sources, model bytes, deck and waveform unchanged.
- Second acquisition TOPNmax .867565/.954677/1.136126V; TOPPmin
  +.020513/-.013663/-.148911V (100ps/500ps/2ns). Both fresh cases0CMI,0LTE,
  seven existing config warnings. Comparator/reference six-pair screens pass
  .99V for fresh cases; 500ps still has small excursions outside 0-0.9V rails.
- Held differential errors .200475/.200482/.200639mV; first-compare errors
  .200486/.200495/.200696mV. All six evidence frames pass native14/14 output,
  eight compares/writes/updates, mapping/decision and1.7578125mV error checks.
  New simulation evidence is four frames; baseline contributes two reused.
- Actual new-on101.260/101.660/103.160ns, same100ps measured BBM/no overlap;
  changing-bank edge skew zero at saved precision. All native sizes unchanged.
- Two rendered plots visually reviewed; report docs/sar8_restore_guard.md and
  curated verification/integration/restore_guard_results.json. Source provenance
  test fixed to explicit UTF-8 (Windows locale differed); no fingerprint changed.
  Four focused tests and Python compile pass. Final diff review/check and scoped
  local commit; no push, no OA changes, no R2 adoption or new qualified freeze.
- Prefer100ps for subsequent cross-input/previous-code checks, not yet adopted.
  Single negative-full TT case does not qualify PVT/noise/MC/real-driver/layout
  or lifetime reliability. Unrelated cdac10_dualrail work preserved.
