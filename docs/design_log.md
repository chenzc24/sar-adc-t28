# Design Log

## 2026-08-31

- Completed ideal-bootstrap main-NMOS screening with real core, deep-N-well,
  and 1.8-V T28 devices. All 27 SS/TT/FF, supply, and temperature Spectre jobs
  succeeded, yielding 486 Ron curves and 486 leakage points; 14 of 18 candidates
  met the 1-kOhm Ron target globally.
- Selected DNW `L=60 nm, W=2 um` as the preferred electrical seed: 321.2-Ohm
  worst Ron, essentially zero DC common-mode Ron variation, and 143.8-nA
  worst off leakage. It improves leakage about 14 times over the same-width
  L30 DNW device while retaining ample Ron margin.
- Kept 1.8-V `L=150 nm, W=8.96 um` as a lower-leakage fallback (65.3 nA) rather
  than the performance seed because its worst Ron is 964.5 Ohm and its
  common-mode flatness is 69.1%.
- Did not claim reliability sign-off or create a production switch. The ideal
  gate reaches 1.979 V absolute at VDD=0.99 V; foundry terminal limits and an
  actual transient bootstrap driver remain mandatory. Model-limit warnings at
  the upper commanded terminal differences remain an explicit design gate.
- Completed global-PVT screening of eight plain transmission-gate candidates
  across SS/TT/FF, 0.81/0.90/0.99 V, and -40/27/125 C. All 27 batched Spectre
  jobs succeeded, producing 216 Ron curves and 216 leakage measurements.
- No candidate met the 1-kOhm rail-to-rail target at every corner. The best
  screened worst case was 13.462 kOhm for standard-VT `Wn=Wp=4 um, L=30 nm`
  at SS/0.81 V/-40 C near mid-supply; first-order width scaling would require
  about 54 um per device and is rejected as a production approach.
- The sampling-switch path will therefore move to a bootstrapped NMOS
  architecture. CDAC bottom-plate switches will be designed separately for
  their discrete reference/ground switching states. No production plain-TG
  switch was created or frozen.
- Started transistor-level sizing with a PDK `nch_mac + pch_mac`
  transmission-gate fixture. Twelve TT/27-C width combinations were swept
  across 0.001-to-0.899-V signal common mode using a 1-mV resistance probe.
- The minimum-total-width point meeting the current 1-kOhm macro allocation is
  `Wn=2 um, Wp=2 um, L=30 nm`; its Ron spans 167.6 to 911.4 Ohm. This is a
  sizing seed, not a frozen switch, because the TT resistance margin is only
  about 9% and PVT has not been run.
- The same candidate leaks 36.0 nA in the full 0.9-V off-stress fixture. That
  result makes leakage/hold-state analysis and longer-/higher-VT device
  comparison mandatory before creating a production sampling or CDAC switch.

## 2026-08-30

- Repaired the OA electrical macro hierarchy after review found that the
  earlier top was only a structural skeleton. Added the parsed
  `sar_macro_controller_10b/veriloga` view and symbol, connected comparator
  outputs to all SAR/CDAC controls, added finite reference RC, correct phase
  clocks, comparator rail clamps, and high-impedance digital observation
  loads. All four schematics now have zero check markers.
- Made controller electrical ports statically scalar (`SEL0_9..0`,
  `SEL1_9..0`, and `D9..0`) so IC6.1.8, the OA symbol, and Spectre share one
  unambiguous port order. The automatically exported OA circuit deck was not
  edited; an analysis-only wrapper produced code 768 in 49.5201 ns with
  0.08735 LSB maximum settling residual and all ten comparisons resolved.
- Completed a topology-aware, closed-loop electrical macro-model before
  transistor replacement. The Spectre hierarchy contains both 5+5 split
  CDAC sides, 60 active bottom-plate switches plus dummy/reset paths,
  sampling impedance, reference memory, gm/C comparator regeneration,
  reset/kickback, and ten SAR decisions.
- Corrected the canonical 5+5 topology load to `32Cu`: 31 active MSB units,
  32 LSB units including the dummy, and a `(32/31)Cu` bridge reproduce exact
  binary weights. The earlier 33-Cu fixture is now explicitly historical and
  conservative rather than topology-accurate.
- Selected the nominal macro comparison point `Ron=1 kOhm`, `Rref=100 Ohm`,
  `Cdecap=2 pF`, comparator `gm_in/gm_reg=60/100 uS`, `Cdiff=20 fF`, and
  direct kickback `0.05 fF`. These are executable sensitivity parameters,
  not frozen transistor specifications.
- Six nominal Spectre code centers were exact, completed in 49.52 ns, and
  showed at most 0.102 LSB pre-compare settling error. Deliberate slow-RC,
  assumed-parasitic, and 1-fF-kickback cases exposed the expected failures.
- Created and read back `sar_cdac_macro_10b`, `sar_sampling_macro`,
  `sar_comparator_macro`, and `tb_sar_macro_transient` in `SAR_ADC_T28`.
  A wide-pitch CDAC symbol and expanded schematic placement are required to
  prevent generated OA terminal stubs from touching; the final hierarchy
  checks, saves, and exports a Spectre netlist successfully.
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
