# SAR8 reference gate slew sweep at 100ps restore guard

## Goal and ownership

Keep100ps restore candidate topology/sizes/reference/input networks unchanged;
sweep existing ideal-reference gate edge_s from20ps to50ps/100ps. Both polarities
and all16 banks get the same edge. This affects restoration AND conversion;
do not interpret it as a restoration-only native driver implementation.
Four two-frame sequences: -.8/-.8,+.8/+.8,-.8/+.8,+.8/-.8V. Cross-input100ps
PWL100.8..100.9ns unchanged. Eight fresh APS runs plus four fingerprint-checked
20ps baselines reused; no new20ps simulation. No OA mutation/adoption/new freeze.

Start branch exp/cdac-flat8-device, HEADcf82d98. Only unrelated untracked
cdac10_dualrail config/three VA files/plan/scripts/verification; no dependency
overlap, preserve untouched. Bridge t28_io verified tunnel/CIW on thu-wei,
user chenzc_intern25,cwd~/TSMC28/llm_IO,Spectre21.1 healthy.
Remote OA ownership:none; SAR_ADC_T28/all foundry PDK/other OA read-only.
Unique simulator-owned job directories only; never edit database files.

Owned local: this plan, plan/log.md append only,
scripts/integration/reference_edge_slew.py, reference_edge_slew_analyze.py,
verification/integration/test_reference_edge_slew.py, reference_edge_slew_results.json,
docs/sar8_reference_edge_slew.md, docs/figures/sar8_reference_edge_slew/,
ignored output/sar8_reference_edge_slew/.
Read-only shared dependencies: all prior sources, manifests/decks/waves/VA/OA,
the native R1 functional/stress analyzer and earlier cross-input sample checker.
Scoped local commit only, no push. Intended commit:
test: sweep SAR8 reference gate slew for restoration margin

## Implementation and validation

1. Validate R2,100ps restore and cross-input provenance. Each fresh deck derives
   from exact corresponding20ps baseline with ONLY16 edge_s assignments added.
   Removing them must reproduce original normalized text. Native hierarchy,
   restore_guard_s=100p,100ps BBM,200ps stable commit,VA bytes unchanged.
2. Native Spectre21.1 APS,TT/.9V/27C,200ns,maxstep10ps,full solver output and
   exact prior save/tolerance/model set; at most2 concurrent tasks. Persist and
   release each result's waveform arrays after saving to bound batch memory.
   Require result.ok, finite complete data. No strobing or relaxed model checks.
3. Reference32/comparator11 MOS six-pair stress and all warning/DC notices;
   N3 GP/GN,BN3,VREFN,VREFP,TOPN,VGD/VDB at worst second-restoration point;
   scan all devices globally so shifted worst instance cannot escape screening.
4. Native codes14/14,241/241,14/241,241/14;8 comparisons/writes/updates/frame,
   bit/sign/token/mapping/read-window checks. Sampling errors at hold-.1ns,
   hold+.5ns,first compare-.02ns vs actual source, plus later compare residuals;
   error screen1.7578125mV. No noise/PVT/mismatch/layout/lifetime claims.
5. Measure actual restoration gate crossings: new-on101.25ns+edge/2,
   old-off101.15ns+edge/2;50% BBM100ps. Check no command-gate overlap and common
   crossing alignment. Old gate transition completes before next transition
   begins for edge<=100ps, with100-edge ps endpoint guard. This is not a direct
   transistor-branch-current shoot-through measurement. Phase displacement
   from changed ramp duration is part of experiment, not held artificially fixed.
6. Overlay N3 gate/drain/VGD and phase edges across three slews with0.99V/0V
   references; summarize all four input sequences and sample-error results.
   Inspect PNGs. Report whether minimum margin improved or worst node shifted;
   not just disappearance of warnings. No predicted improvement quoted as measured.
7. Focused source/deck/provenance/measurement tests, Python compile, diff-check,
   factual report/log and scoped commit. Do not modify active R2/OA or push.

## Progress

- Plan created before tracked edits. Native preflight healthy; no OA writes intended.
- Eight parameter-only decks prepared; removing16 edge overrides reproduces
  each baseline exactly. Focused static patch test and Python compile pass.
- Four50ps cases complete/result.ok/no CMI, native frames/function/sampling pass.
  Reference maxima for nfull/pfull/n_to_p/p_to_n:
  .944611/.936810/.942421/.938626V; comparator max.950686V each.
  Pfull N3 VGD .987137->.933042V, BN3 -87.137->-33.042mV.
  Held |diff| .200474/.200473/.200462/.200463mV.
- All four100ps cases also result.ok,0CMI/0LTE/no added config warnings,
  reference maxima .938153/.930779/.939290/.935649V. All16 fresh frames/128
  comparisons+writes+updates pass native checks;20ps adds8 reused evidence frames.
  Every held/first-compare error remains about.2005mV; worst later comparison
  error .808251mV<1.757813mV. Entire200ns reference/comparator scans pass.
- Positive N3 VGD20/50/100ps .987137/.933042/.912284V; BN3 minima
  -87.137/-33.042/-12.284mV. Reference worst shifts to other devices, not hidden.
  Worst reference across four inputs .987137/.944611/.939290V: margins
  2.863/45.389/50.710mV. Comparator .950686V dominates combined scan for both
  slower ramps. No whole-chip/Bootstrap-internal or lifetime qualification.
- Actual new-on101.260/101.275/101.300ns;50% BBM100ps,1% gate gaps80.4/51/2ps,
  no gate-envelope overlap. Recorded as gate-voltage checks, not branch currents.
  Both on/off slopes and threshold handoff timing change; no orthogonal attribution.
- Three PNGs visually checked; docs/sar8_reference_edge_slew.md and curated
  verification/integration/reference_edge_slew_results.json. Three focused tests,
  Python compile, provenance and final diff-check/review pass. Scoped local commit
  only, no push/OA/baseline adoption. Prefer50ps as subsequent candidate;100ps
  retained as lower-reference-stress comparison. Unrelated work preserved.
