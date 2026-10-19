# Native 0.5-um Canvas bootstrap on the historical full CDAC

## Goal and boundaries

Compare the selected native T28 1.8-V Canvas bootstrap (Mmain W/L =
0.5 um/150 nm) against the original, unisolated `sar_bootstrap` on identical
differential 5+5 `sar_cdac_macro_10b` loads. This is a sampling/hold comparison,
not full SAR conversion or sign-off. Do not change or re-size either candidate.

Initial Git state: clean `exp/top-plate-gmain-t28`, four local commits ahead
of origin. Previous plans, PDK and existing OA cells are read-only.

Owned local paths:

- This plan, `plan/log.md`, `virtuoso/cell_manifest.yaml`.
- `scripts/characterization/compare_canvas_full_cdac.py`.
- `scripts/analysis/analyze_canvas_full_cdac.py`.
- `docs/canvas_bootstrap_full_cdac.md`.
- Generated `output/canvas_full_cdac/` (ignored).

Owned new remote OA objects (SAR_ADC_T28 only):

- `sar_bootstrap_canvas_cdac_t28/{schematic,symbol}`: native candidate without
  its standalone Cs=1 pF. Preserve all MOS, Cboot, dimensions and connectivity.
- `tb_bootstrap_canvas_full_cdac/schematic`: two independent differential
  full-CDAC paths, original and candidate, sharing ideal supply/clock/reference
  boundary conditions but having separate 50-ohm input source branches.

Read-only dependencies: `sar_bootstrap_canvas_t28`, `sar_bootstrap`,
`sar_cdac_macro_10b`, historical OA exports and generated result files;
`tsmcN28`, foundry models, all other remote cells and unsaved windows.

## Method and assumptions

- TT, 27 C, 0.9-V supply/0.45-V common mode, differential input
  -0.8/-0.4/0/+0.4/+0.8 V. Equal acquisition clock and BASE handoff.
- Preserve the original delayed PHIB reset and the candidate's actual
  two-MOS inverter: internal timing is part of each topology, not secretly
  idealized to equalize them. Record edge times and avoid attributing changes
  solely to W/L. Do not claim a one-variable device experiment.
- Both CDAC copies use precisely the same existing cell. Replace Cs rather
  than adding the CDAC in parallel with 1 pF. Reference ports tied to VCM,
  as in the historical sampling test; no SAR conversion, noise or mismatch.
- Create new cells with supported bridge APIs, read back and export the full
  OA hierarchy. Simulation copies may set design variables and analysis/save
  options, but may not rewrite the circuit connectivity or device dimensions.

## Implementation / validation

1. Preflight bridge 0.8+, exact profile `t28_io`, CIW/window state and
   SAR_ADC_T28 mapping/technology. Inspect existing DUT/CDAC/reference ports.
2. Create independent native candidate and matched testbench; verify original
   candidate-minus-Cs equality, both CDAC port maps, no topology substitutions,
   no schematic markers. Preserve exact raw OA export and SHA-256 provenance.
3. Smoke +0.8 V; run the other four inputs with conservative Spectre transient
   settings, maxstep 10 ps, reltol 1e-5/vabstol 1e-7/iabstol 1e-13.
4. Require result.ok and finite complete saved waveforms. Measure differential
   acquisition at 249.9 ns, raw held error at 270 ns, 260-280 ns drift,
   branch errors/common mode, actual control timing, terminal stress and
   warnings. Acceptance reference: |held differential error| < 0.439 mV;
   failure is a valid experiment outcome and must not be hidden/calibrated.
   Because original core-device SOA warnings are heavily suppressed, also run
   candidate-only diagnostic copies at both extremes: omit only the old
   top-level branch, retain the candidate hierarchy/controls verbatim, and
   check both candidate result agreement and its independent warning log.
   These diagnostic decks are explicitly derived, not claimed as exact full
   comparison OA exports; the primary five-point comparison remains exact-OA.
   Add a five-input timing control: align original PHIB rising/falling
   50% crossings to the candidate CLKSB crossings, without changing either
   DUT or CDAC. Keep the original 100-ps ideal-source edge shape, explicitly
   distinguish crossing alignment from identical waveform replay, and record
   this stimulus-only deck change. This bounds the ~0.94-ns reset difference
   rather than attributing all improvement to the native circuit.
5. Reproduce historical original worst error (~1.532 mV) or investigate and
   explicitly qualify any deviation. Plot input sweep and +0.8-V timing with
   ideal targets, compact legends, hold interval and shared axes.
6. Inspect rendered figures, compile changed Python, check YAML/diff/ownership,
   record results/log and make one scoped local commit; no push.

## Artifacts and status

Raw OA export/readbacks, per-run decks/PSF/logs/metrics and figures in
`output/canvas_full_cdac/`. Report in `docs/canvas_bootstrap_full_cdac.md`.

Status: complete, locally committed without push.

## Results / closure

- Created only the two planned native/TB cells, with zero schematic markers;
  candidate readback exactly equals the selected source minus Cs. Fresh OA
  circuit export proves original bootstrap/CDAC unchanged from historical
  exports and native candidate unchanged except removal of Cs and cell name.
- 14 successful Spectre transients: five primary inputs, two tighter-accuracy
  extremes, two candidate-only warning checks, five reset-crossing controls.
- Primary worst held differential errors: original 1.535561 mV versus native
  0.393871 mV (74.35% reduction). All five native points pass 0.439 mV nominally,
  with only 45.13 uV worst margin. No PVT/noise/MC acceptance is claimed.
- Tight-accuracy maxima: original 1.535665 mV/native 0.393902 mV; changes under
  1 uV. Candidate-only logs: zero CMI/suppressed warnings, four inherited
  SFE-1131 each; agreement with primary within 0.0064 uV. Original logs retain
  core-device SOA warnings; sampled native terminal peak ~1.75435 V is not
  lifetime/reliability sign-off.
- Reset-crossing-aligned control gives original worst 1.632060 mV/native
  0.393861 mV. Internal clock shape/device topology still differs; improvement
  is not attributed solely to W/L or reset timing.
- Final exact export matches primary except generation date; before/after
  API readbacks prove all three read-only OA dependencies unchanged. Initial
  four unterminated CLKSB-output markers resolved in the new TB by 1-Tohm
  monitor terminations; no existing cell was repaired/overwritten.
- Figures (five-point error, turn-off timing, settled hold) rendered and
  inspected; full voltage excursions retained separately from mV zoom.
- Validation: 14 result.ok, complete finite monotonic waveforms, control-order
  and cross-run consistency assertions, YAML parsing, Python compilation and
  diff checks. Evidence under `output/canvas_full_cdac/`.

Intended commit: `feat(sampling): compare native 0.5um bootstrap on full CDAC`.
