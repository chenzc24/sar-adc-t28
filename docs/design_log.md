# Design Log

## 2026-08-30

- Completed the module-level first-order layer by adding sampling-acquisition,
  comparator-regeneration, and clock-jitter constraints to the existing
  CDAC/reference envelope. No whole-ADC linear model was created because the
  SAR signal path changes by phase.
- At Cu=6.86047 fF and Cside=226.396 fF, the 40 ns acquisition constraint is
  `Rsource + Ron <= 21.242 kΩ`. Three Spectre cases reproduced the analytical
  pass/fail boundary.
- A 20 fF comparator node requires `gm_eff >= 92.42 uS` to resolve 0.25 LSB to
  0.45 V in 1.5 ns. Three positive-feedback Spectre cases matched analytical
  decision times within 0.02 ps. This constrains later sizing but does not
  validate StrongARM noise, offset, or topology-dependent gm/C.
- Reproduced the 20 ps RMS, 4.5 MHz, -1 dBFS jitter allocation as 0.320738 mV
  RMS or 0.182464 LSB RMS. Clock behavior remains a timing sensitivity rather
  than an AC circuit model.
- Created and netlisted only
  `SAR_ADC_T28/tb_sampling_acquisition/schematic` and
  `tb_comparator_regeneration/schematic`; all production blocks remain
  planned.
- Established the first module-level CDAC/reference settling envelope without
  freezing a capacitor or switch size. The ideal 5+5 split gives
  `Cside = 33*Cu`; the differential kT/C allocation requires at least
  82.787 fF per side, or 2.509 fF per unit before parasitics.
- Converted the 0.25 LSB deterministic settling allocation into an allowed
  `Rref + Ron` envelope over Cu and 2-4 ns settling windows. At the
  characterized 6.86047 fF comparison point, the 3 ns limit is 1.593 kΩ;
  at the 35.6304 fF specimen it tightens to 306.7 Ω.
- Created and netlisted only
  `SAR_ADC_T28/tb_cdac_ref_settling/schematic`. Four ideal-RC Spectre
  transients matched the closed-form exponential result, including explicit
  feasible, settling-fail, and kT/C-fail examples.
- Kept reference memory/noise, nonlinear Ron, physical switching trajectories,
  mismatch, charge injection, kickback, and parasitics outside this first-order
  model so their later PDK results cannot be mistaken for already validated
  behavior.
- Adopted a 10-bit, 10 MS/s, 0.9 V fully differential default specification.
- Selected a 5+5 split CDAC, StrongARM comparator, and synchronous SAR baseline.
- Assigned text sources and verification automation to the local Git repository.
- Assigned all OA data to the remote `SAR_ADC_T28` Virtuoso library.
- Kept capacitor-cell selection and non-TT model section names unresolved until verified from the PDK.
- Created the empty remote `SAR_ADC_T28` OA library at `/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28` and verified its `tsmcN28` technology binding.
- Completed the stage-1 input-referred error budget. The initial allocations
  project 56.784 dB SNDR and 9.140 bit ENOB at -1 dBFS, retaining 0.844 dB
  margin over the 9-bit ENOB target.
- Established the stage-2 bit-accurate golden model using the ideal binary
  equivalent of the 5+5 split CDAC. Bridge ratio error, parasitics, switching,
  and settling remain explicit later-stage CDAC work.
- Defined the stage-3 behavioral interface with separate sample and 200 MHz
  SAR clocks, active-low reset, 10-bit output, busy, and valid. Keeping the SAR
  clock visible makes the state machine replaceable and testable before the
  clock-generator implementation is selected.
- Implemented the ideal 10-bit transfer as ten explicit MSB-first decisions
  with a falling-edge sample event. The zero-error model remains the golden
  contract; offset, noise, effective weight error, and settling parameters are
  disabled-by-default sensitivity controls rather than transistor models.
- Assigned sampling-clock jitter to the testbench instead of the ADC core so
  it perturbs the acquisition instant without being counted again as decision
  noise.
- Kept the first allocated-noise Verilog-A experiment limited to the three
  explicitly modeled random sources. Clock jitter remains a sampling-time
  perturbation, distortion remains an unspecified guard band, and comparator
  offset/CDAC settling remain deterministic checks rather than being
  relabeled as Gaussian noise.
- The fixed-seed Spectre experiment measured 58.059 dB SNDR and 9.352 bit
  ENOB, only -0.007 dB from the 58.066 dB partial RSS prediction. This
  validates the random-noise abstraction for top-down SNDR allocation while
  leaving physical bandwidth, correlation, memory, and PVT behavior to the
  transistor-level blocks.
