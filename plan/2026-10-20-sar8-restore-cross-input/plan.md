# SAR8 100ps restore guard across input polarity and frame history

## Goal and ownership

Test the existing 100ps ideal reference-restore timing candidate at +0.8V/+0.8V,
-0.8V/+0.8V and +0.8V/-0.8V differential inputs in two consecutive frames.
Cross-frame changes use a finite100ps PWL ramp100.8..100.9ns, before second
SAMPLE rising50% at101.05ns; thus each held sample gets the full40ns acquisition.
Reuse verified prior -0.8/-0.8V100ps waveform as context, not new evidence.
No topology, W/L, MOM,3x reference switches, reference/input impedance, clock,
solver/save/model/VA changes. No OA edits, new baseline adoption or PVT signoff.

Start branch exp/cdac-flat8-device, HEAD4b56cb6. Unrelated untracked cdac10_dualrail
config, three VA files, plan, scripts and verification remain untouched; no shared
dependency overlap. Remote preflight t28_io healthy CIW user/host/cwd and Spectre
21.1 confirmed. OA ownership:none; SAR_ADC_T28 and all foundry/other OA read-only.
Only simulator-owned unique remote job directories may be created.

Owned paths: this plan, plan/log.md append only,
scripts/integration/restore_cross_input.py, restore_cross_input_analyze.py,
verification/integration/test_restore_cross_input.py, restore_cross_input_results.json,
docs/sar8_restore_cross_input.md, docs/figures/sar8_restore_cross_input/,
ignored output/sar8_restore_cross_input/. All existing R1/R2 and previous restore
sources, decks, waveforms, manifests and model bytes remain read-only.
Local scoped commit only, no push. Intended message:
test: validate SAR8 100ps restoration across input polarity changes

## Implementation and validation

1. Verify R2 and previous restore100ps source/deck/wave/VA fingerprints. Derive
   three unique decks from exact100ps candidate. Only VDIFF parameter and two
   input source statements may differ; normalized rest must be identical.
   Native hierarchy and all16 restore_guard_s=100p additions must stay intact.
2. Reuse native APS runner with at most2 jobs, TT/.9V/27C,200ns/maxstep10ps,
   full solver output,50ohm input/side,50ohm+4pF reference/rail. Require result.ok,
   finite complete saved data. Do not strobe away peaks or change limit settings.
3. Reuse actual native decision/code/mapping/error checks (expected241/241,
   14/241,241/14), eight comparisons/writes/updates/frame, correct physical
   midpoint words and100ps gateBBM/no overlap. Preserve all warnings and suppression.
4. Scan reference32MOS/comparator11MOS six-pair envelopes globally and by first
   acquisition, cross-input edge, second restoration/acquisition and conversion.
   Record TOPP/TOPN BOTH maxima/minima; positive input can move worst node to P.
   Screen <=.99V, not whole-device/bootstrap-internal/lifetime qualification.
5. Sample errors versus actual VIN*_SRC at hold-.1ns,hold+.5ns and first compare
   minus20ps: P,N,differential/common-mode. Compare |diff|<1.7578125mV;
   all later compare errors separately. Check actual PWL edges/targets in waves.
6. Plot second restore with input targets/model screen; plot held error and
   ±.25LSB band, plus state/phase references. Inspect rendered plots.
7. Curate hashes/contexts/metrics, concise report; focused tests for patch
   boundaries, immutable dependencies, stimulus/frame sequence and measured
   function/sampling/stress. Python compile, diff-check, factual log, scoped commit.

## Progress

- Plan created before tracked edits. No remote OA mutation intended.
- Completed three fresh native APS cases,result.ok/200ns/full solver output;
  each0errors/7 existing config warnings/0CMI/0LTE. Sources/VA/previous100ps
  candidate and R2 immutable fingerprint checks pass. Only input sources changed.
  Initial-DC GminDC notices in all; extra Bad pivoting notice in p_to_n (5/5/6
  notices total) preserved in curated metadata. No solver/tolerance changes.
- Codes241/241,14/241,241/14, six fresh frames/48 compares+writes+updates pass.
  Held |diff| maxima .200474/.200461/.200462mV, first-compare maxima
  .200485/.200469/.200470mV, later worst residual<=.807895mV<1.7578125mV.
- Whole-run reference maxima .987137/.966629/.986687V; comparator .950686V
  all. No acquisition top outside0-0.9V. Positive constant and positive-to-negative
  reference N3 MP_HIGH VGD margins only2.863/3.313mV at101.2687/101.2686ns:
  bounded nominal pass, not robust reliability margin or adoption evidence.
- Actual restore edges101.16/101.26ns,100ps BBM/no overlap, zero saved-precision
  gate-edge skew. Actual PWL sources validated against full time-axis definition.
- Six PNGs visually reviewed; docs/sar8_restore_cross_input.md and curated
  verification/integration/restore_cross_input_results.json. Four focused tests,
  Python compile and final diff-check/review; scoped local commit, no push.
  OA and R2 baseline remain unchanged; unrelated cdac10_dualrail preserved.
