# Eight-bit StrongARM baseline characterization

## Goal and boundaries

User accepted the existing 11-MOS StrongARM topology and requests simulation
against the discussed eight-bit targets. Characterize the unchanged T28
`sar_strongarm_t28`, not Canvas's display/default SKY130 models. No sizing,
topology, calibration, or OA change is authorized by this baseline target.

Start on `exp/cdac-flat8-device`. Unrelated dirty README, CDAC report,
design/maintenance logs, cell manifest and new cdac8_reset files belong to
the reset timing/drive target; preserve them. Its candidates are not inputs
to this comparator target. Do not stage or revert that work.
During execution the separate reset target committed its files; the new dirty
`sar8_logic_timing.yaml`, `sar8_logic.md`, and native-logic plan remain unrelated.

## Ownership

Local owned: this plan; `config/strongarm8_baseline.yaml`;
`scripts/strongarm8/`; `verification/strongarm8/`;
`docs/strongarm8_baseline.md`; `docs/figures/strongarm8/`.
Generated evidence: ignored `output/strongarm8_baseline/` only.
A bounded maintenance-log append is allowed after checking concurrent edits;
do not rewrite any pre-existing entry. Commit only owned paths, no push.

Remote OA owned: none. Read-only dependencies:
`SAR_ADC_T28/{sar_strongarm_t28,tb_sar_strongarm_t28,cdac8_device_nominal,
tb_cdac8_nominal_sar}` and their existing dependency hierarchy. All PDK,
old results and sources, Bootstrap/reset projects, and unsaved windows remain
read-only. Exports and runs use unique generated directories; never modify
PDK or raw OA data.

## Targets and evidence limits

Active spec: 8 bit, span 1.8 V, LSB 7.03125 mV. Comparator random noise
allocation 1.265625 mV RMS; systematic offset allocation 1.7578125 mV;
decision window 1.5 ns at declared differential overdrive/load. Random
offset is reported separately (mean, spread and empirical bracket count),
not silently equated to a production yield requirement. No calibration.

Use an exact fresh native export, preserve the DUT subcircuit byte-for-byte
and assert 11 PDK MOS and known D/G/S/B mapping. Top-level analysis wrappers
may change stimuli, PVT, load and model-section selection, explicitly recorded.
No simulation deck is claimed to be a separately saved OA testbench.

1. Preflight bridge t28_io/CIW/library/technology and windows. Read back the
   unchanged comparator, export standalone and existing CDAC native fixture.
2. Deterministic initial smoke; input-overdrive, common-mode, output-load and
   27-point SS/TT/FF x 0.81/0.9/0.99 V x -40/27/125 C timing/stress screen
   at both input signs. Validate reset and actual clock crossing. Near-zero
   input is a metastability diagnostic, not a required fixed-polarity pass.
3. Physical transient-noise repeated decisions at several input offsets;
   multiple seeds, strobe-only outputs for statistical runs, one continuous
   waveform pilot. Fit P(positive) vs input, reporting center and effective
   input-referred sigma, seed/bandwidth sensitivity and sample limits.
4. Mismatch-only local-MC model activation check and bounded offset sweep
   inside each draw, with both sweep directions if feasible. Preserve
   sampled statistics; report finite search resolution/censoring/history,
   not an exact offset histogram or tail yield. Start small before full
   128-draw screen. Refine only if the pilot justifies it.
5. Kickback with current side capacitance, then native current CDAC fixture
   enabled/disabled comparator A/B where feasible. Check pre-edge bias,
   differential/common-mode disturbance at decision, and remaining-bit
   history. Ideal sources are not evidence of negligible kickback.
6. Keep accuracy, stress, noise, mismatch, and incomplete tests separate.
   Existing CDAC reset/Bootstrap failures are not attributed to comparator
   simply because they appear in its integrated fixture.

## Validation and outputs

Require result.ok, full expected time/sample counts, finite data, matching
source/DUT hashes, real statistical activation and explicit PVT/seed/load.
Capture all CMI warnings including suppressed counts; model ranges are not
foundry reliability signoff. Check numerical precision on a representative
border case, and noise bandwidth before any strong noise-acceptance claim.
Never replace physical noise with requested RMS values in a behavioral model.

Deliver timing/noise/offset/kickback figures with expected baselines and
phase markers, concise report and config. Targeted Python/YAML/deck tests,
git diff --check, final read-only comparator audit, factual maintenance log.
Expected local commit: `test: characterize unchanged T28 StrongARM for 8-bit ADC`.
No full ADC FFT, new reference buffer/clock tree, sizing optimization,
DRC/LVS/PEX or production-yield claim in this target.

## Bounded adaptation after the dense pilot

The four-draw dense ascending/descending offset pilot is active, monotonic
and has no observed direction difference. It takes about 130 seconds remote
execution; scaling to 128 draws is inefficient. Preserve the started long
dense run as interrupted evidence (not a completed statistical result).
Use a testbench-only Verilog-A binary-search stimulus in the owned scripts
folder: it reads the real comparator at 1.5 ns, changes input only during
reset, verifies initial +/-32 mV bounds, and records final bounds/status.
The native comparator remains byte-identical. Cross-check the first four
draws against the dense pilot before running 128 draws; retain identical seed
and validate parameter/sample identity where feasible. This is stimulus and
measurement automation, not a behavioral comparator or offset correction.

## CIW interruption and current user steering

A Spectre-help query through CIW blocked its command path. Only the exact
owned help/pager/shell processes were terminated; no Virtuoso was killed or
restarted and no OA mutation occurred. User's subsequent fresh `ic6` launch
failed because DISPLAY was unset, separately from the CDS.log lock warning.
User requested that display/connection adaptation be deferred and other
conditions investigated. Continue independent SSH/Spectre runs; defer final
live CIW readback. Assert all accepted local DUT/deck hashes and preserve the
initial fresh OA readback. Do not claim the current bridge CIW is healthy.

## Characterization outcome

Completed the bounded characterization (not circuit acceptance): 125 result.ok
jobs, comprising 94 deterministic, 19 noise, three mismatch tasks, three held-C,
and six native-CDAC A/B runs. All accepted deck/DUT hashes verified; binary
stimulus hash verified. The dense/binary/full first four threshold brackets and
saved random-parameter records are identical. The full binary screen completed
128 uncensored draws at 0.25-mV resolution; direction history is only a pilot
result, not claimed for the complete screen.

Nominal first decision 191 ps; 46/54 PVT timing runs pass, with four failing
PVT points and 18 high-supply CMI-warning runs. Random threshold sigma 12.730 mV
is the major sizing concern. Nominal physical noise estimates 0.652/0.745 mV
at 10/30 GHz remain below allocation but bandwidth convergence is open. Native
fixed-code CDAC disturbance is about 0.039 mV at decision, 0.120 mV peak.
Tighter nominal/cold-5f numerical settings change delay by 0.135/0.042 ps.

Delivered report/config and five curated plots. Five focused tests, Python
compile, YAML parse, generated-waveform finite/sample checks, hash audit and
visual inspection pass. Live final CIW readback is explicitly deferred under
the user's steering; no OA changes to reconcile. No W/L optimization, topology
change, full ADC qualification, push, or experience extraction in this target.
