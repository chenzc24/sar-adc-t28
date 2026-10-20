# CDAC reset timing and native gate-drive experiment

## Goal and boundaries

User requests another experiment round on CDAC reference reset timing/drive.
Bootstrap acquisition is explicitly deferred: do not change its geometry,
topology, pump, PHI waveform, or claim that its cold-SS failure is resolved.
Keep 8 bit, 10 MS/s, 512 physical MOM units, selected capacitance, reference
pass-device geometries, and SAR decision timing unchanged.

Initial state: clean `exp/cdac-flat8-device`, HEAD 665594d. Continue on this
experimental branch. All previous source/cell/evidence baselines are read-only.

## Owned state

Local: this plan; `scripts/cdac8_reset/`, `verification/cdac8_reset/`,
`config/cdac8_reset.yaml`, `docs/cdac8_reset.md`,
`docs/figures/cdac8_reset/`, `plan/log.md`, `docs/design_log.md`,
`virtuoso/cell_manifest.yaml`; a short cross-link/status note in
`docs/cdac_flat_8b_device.md` and README.md if supported by results.
Generated, ignored evidence: `output/cdac8_reset/` only.

Remote ownership is restricted to new `SAR_ADC_T28` objects:
`cdac8_reset_sw_b0` through `cdac8_reset_sw_b7` schematic/symbol;
`cdac8_reset_nominal` and `cdac8_reset_device` schematic/symbol;
`tb_cdac8_reset_nominal`, `tb_cdac8_reset_literal`,
`tb_cdac8_reset_strongarm` schematics. No old cell may be overwritten.
Only create the candidate family justified by diagnostic results, not every
screened variant. Preflight exact library path/technology, active windows,
target existence, and ownership before any remote mutation.

Read-only: all PDK and shared libraries; every earlier SAR_ADC_T28 cell,
particularly `sar_bootstrap_canvas_flat_8b`, capacitor banks, original CDAC,
controller/sequence VA and comparator. Snapshot/read back these dependencies
and verify their equality after candidate creation. No PDK/model contents,
raw exported DUT netlists, credentials, or OA databases enter Git.

## Experiments and implementation

1. Recheck healthy bridge/CIW/Spectre and inspect original OA state.
2. Preserve original native export. Generate uniquely named diagnostic decks
   from that export; explicitly label these as netlist-level experiments,
   not an already corresponding final schematic. Hash baseline and invariant
   Bootstrap subcircuit/PHI before/after every transformation.
3. One-variable screens: reference-release-to-VCM gap; VCM turn-on slew;
   stronger PMOS-gate pull-down; native added/detached NMOS gate buffer.
   An ideal complementary-gate case, if used, is diagnostic only.
   No reference/VCM overlap deliberately shorting the supplies is accepted.
4. Pick the best native timing/drive candidate using BOTH positive/negative
   stress, reset convergence, control-terminal stress, and conversion accuracy.
   If no candidate passes, preserve failures and report the remaining gate;
   do not waive stress or silently widen device limits.
5. Create independent OA candidate(s), supported bridge APIs and CDF callbacks,
   then simulate exact fresh OA exports. Nominal m-aggregated capacitors may
   accelerate deterministic screens; correlate selected candidate to the
   literal independent 512-unit hierarchy, never use aggregation for MC.
6. Exercise direct-risk inputs/codes and SS/TT/FF voltage/temperature endpoints;
   check real StrongARM interface separately if the native reset candidate
   merits promotion. No long FFT or new mismatch/noise campaign is required
   to determine a reset timing/drive experiment outcome.

## Validation and acceptance

- Require Spectre `result.ok`, complete final time, correct expected codes.
- Save every bottom node, TOPP/TOPN, VCM/ref rails, native gate signals and
  enough gate controls to reconstruct MOS Vgs/Vgd/Vds/Vbs/Vbd excursions.
- Assess full trace and reset window; report startup and other-phase warnings
  separately, never suppress or reinterpret warnings as passes.
- Core model's reported 0.99-V terminal boundary is an engineering screen,
  not foundry reliability signoff; no arbitrary threshold relaxation.
- Reset should return all bottoms within 1 mV of VCM before next acquisition.
- Preserve comparison-time deterministic error <=1.7578125 mV; verify a fixed
  midpoint-code sampling/hold regression separately from intentional SAR DAC
  residual changes. Recheck unchanged input-Bootstrap and PHI hashes.
- New OA cells zero markers; supported API readback, preserved dependencies,
  fresh-export identity to accepted simulated hierarchy. Identify ideal/VA
  clock/controller/comparator/reference-buffer abstractions in report.
- Python syntax/focused invariant tests, YAML parse, figure visual inspection,
  complete diff review, `git diff --check`, `git status --short --branch`.

## Artifacts and commit policy

Record per-run configuration/deck hashes, original-export provenance, simulator
version/mode, model sections, PVT, actual timing and result paths. Curate a
compact experiment table and timing/error/stress figures. Update maintenance
log and circuit decision note. Scoped local commit after evidence review;
no merge/push without user request. No learning/experience extraction.

Status: healthy bridge and immutable dependencies verified. Eleven diagnostic
decks preserve Bootstrap and PHI. The initial native pfast2/pfast4 logs clear
printed/suppressed CMI at nominal conditions, unlike baseline; provisionally
instantiate pfast4 as an independent OA validation candidate while the rest
of the screen completes. This is not PVT acceptance or final promotion.

Nominal exact-OA cross-input gate: pfast4 clears the original +453.516-mV
case but fails -0.8-V input with negative excursions, including a non-reset
phase. Do not launch a broad PVT campaign on that known-failing candidate.
Add three bounded diagnostics: pfast2 at +/-0.8 V and pfast3 at -0.8 V;
choose further work from those results. Existing candidate remains a
documented experiment, not an accepted replacement.

Cross-input diagnostics also require an unchanged negative-input baseline to
avoid mislabeling pre-existing SAR reference-transition stress as a new reset
regression. Add one such A/B and three joint drive/slew diagnostics: 2x gate
pull-down with 100/300-ps reset edge at -0.8 V, and 100 ps at +0.8 V.
These preserve the fast VCM release edge and PHI, and use one complete cycle
for screening only; any selected refined OA candidate must be rechecked over
multiple cycles. Owned new switch-cell parameters/bench reset-edge parameters
may be updated after saved-state checks, keeping unique old/new exports.

## Final outcome

Completed the bounded experiment, not circuit qualification: 24 result.ok APS
runs (18 diagnostics, six exact OA) and 13 independent zero-marker schematics.
Original-point reset terminal improves from 1.012168 V to 0.982106 V in 4x OA;
literal array and actual StrongARM fixtures agree at that point. +/-0.8-V
reset and joint slew tests remain failing; do not promote or run broad PVT.
An unchanged negative-input control also proves a pre-existing 1.072523-V
non-reset reference transition. Bootstrap and its input PHI remain unchanged.

Final remote audit preserves 14 readbacks, matches three fresh exports to
their tested originals, and verifies two unchanged VA sources. Nominal
aggregate/literal correlation <0.001 mV. Config remains qualified=false.
Curated report/figures/metrics and scoped tests are complete; final local
validation/commit recorded in maintenance log. No merge or push.
