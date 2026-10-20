# Design Log

## 2026-10-20 - Eight-bit SAR logic proposal for Canvas review

- Retain the active flat-CDAC phase interface: 43-ns first trial, eight
  5-ns decisions, commanded final capture at 82.5 ns, reference release at
  90 ns. Phase generation remains an external block for the first logic pass.
- Propose a one-hot MSB-to-LSB token, per-bit working and published output
  registers, reset-priority HOLD/trial latches, and low-level-latched clock
  gates. Publish the final mux input, including the just-decided LSB.
- Add explicit comparator-ready/fault handling; a failed decision keeps the
  old output and inhibits VALID. Logic-ready does not establish analog
  metastability or noise performance. BBM timing remains to be characterized.
- User deferred live CIW repair and requested Canvas topology first. The
  eight-Cell Canvas proposal and actual ideal netlist pass Boolean checks;
  no native OA implementation or T28 timing/power acceptance is claimed.

## 2026-10-20 - Reset timing and drive experiment, no promotion

- Keep input Bootstrap/PHI, capacitor geometry/count, reference pass-device
  geometry and SAR decision schedule unchanged. Create independent
  `cdac8_reset_*` OA objects, never overwrite the earlier device baseline.
- Eighteen native netlist diagnostics and six exact-OA APS runs identify
  a local improvement from 2x/4x VCM PMOS-gate inverter pull-down. The 4x
  OA sample reduces original-point reset worst terminal 1.012168 -> 0.982106 V;
  literal array and real StrongARM tests at that input have no CMI warnings.
- Do not promote: +/-0.8-V tests and joint reset-edge tests still fail
  positive/negative stress. Slowing/strengthening/adding buffers is not
  universally beneficial. Good final codes/VCM settling do not waive stress.
- Unchanged -0.8-V baseline already has 1.072523-V Vbd at 47.636 ns during
  SAR reference switching. Separate that pre-existing conversion-phase issue
  from reset and from deferred Bootstrap large-signal acquisition.
- Stop before broad PVT on a known TT cross-input failure. Keep qualified=false;
  next structural reference-reset choices require explicit design/evidence.
  Details, limitations and measured timing figures: `docs/cdac8_reset.md`.

## 2026-10-20 - First native eight-bit flat CDAC candidate

- Added an electrically selected 4.004-fF T28 MOM unit, 256 independent units
  per side, and an explicit literal hierarchy. This is a pre-layout selection,
  not DRC-qualified geometry. Preserve the earlier 6.86047-fF comparison load.
- Verified active local mismatch before statistics: default Model produced
  no actual C variation; CDF mismatch=1 did. The accepted 200-array sample
  has 512 independent random variables and worst static weight-oracle
  DNL/INL 0.1024/0.0656 LSB. No layout-gradient or yield claim.
- Built native rail PMOS/NMOS plus VCM TG and real gate inverters. Changed
  sqrt-weight sizing to constant leaf geometry with bit-weight multiplicity.
  Correlated the deterministic parallel-cap view open/closed loop; retain
  independent units for capacitor MC, never multiplier-based pseudo-randoms.
- Native switched DAC is monotonic over 256 nominal codes, raw INL about
  0.0935 LSB; all 256 ADC code-center outputs agree. Neither establishes
  exact ADC transition DNL. Checked nominal stable held/decision residuals
  pass their stated voltage gate, but full trajectories still violate
  core model Vds/Vgd/Vbd limits on reset. Switch sizes are not frozen.
- Bootstrap-before-reset, slower VCM re-enable and smaller effective TG
  multiplier diagnostics do not clear all positive/negative stress gates.
  Same-topology 1.8-V pass-device MSB has 4.54-Mohm VCM Ron at
  SS/0.81 V/-40 C with unboosted controls; stop at that gate, no array claim.
- Unchanged input Bootstrap fails the first full-swing cold/low-V sample:
  -27.4 mV vs -0.00173 mV when only that path becomes a 150-ohm ideal relay
  with the same native CDAC. A good later steady sample does not clear it.
  Low-side large-signal discharge remains slow after gate boost establishes.
- Preserve top-plate sampling and all old cells. Physical noise, native
  reference buffer/clock tree, exact ADC transition statistics and layout
  signoff remain separate gates. See the [candidate report](cdac_flat_8b_device.md).

## 2026-10-19 - Eight-bit flat mainline

- User switched the target from 10-bit 5+5 to 8-bit flat. Retain 10 MS/s,
  0.9-V supply, 0.45-V common mode, +/-0.9-V differential range and existing
  40/60-ns acquisition/conversion allocation. Provisional ENOB target is seven
  bits. Archive the original specification; preserve every ten-bit OA cell.
- New LSB=7.03125 mV and deterministic 0.25-LSB gate=1.7578125 mV. Keep
  20-ps jitter absolute, not scaled by the changed bit count. Random module
  shares remain top-down choices; physical noise/offset are not qualified.
- Implement a literal eight-bit VA pair and a real flat electrical network,
  not a ten-bit truncation. Per side 255Cu plus dummy=256Cu; no bridge or LSB
  island. Cu=6.86047 fF remains a comparison value, not a physical MOM choice.
  Its 1.75628032-pF side load demands a new sampling qualification.
- Electrical allocation: Rbottom=150 ohm, Rref=50 ohm, Cref=4 pF. Ten nominal
  macro cases pass with maximum 0.003207-LSB decision-time settling residual;
  slow-reference/high-R control fails 4.40758 LSB despite a correct final
  code. The physical reference buffer and selection switches are still open.
- Preserve the user's native T28 Canvas bootstrap topology. The old 0.5-um
  main fails the new flat load (12.91-mV acquisition error). In a separate
  eight-bit copy, Mmain W/L=1 um/150 nm passes five inputs: maximum acquisition
  0.031228 mV and held error 0.126413 mV. No further 2-um screen is needed
  for this bounded nominal gate. A new physical Cu may require resizing.
- Real StrongARM interface at +/-0.25 LSB resolves correctly within 1.5 ns;
  on/off differential kickback peaks at 0.051338 mV including the zero-input
  diagnostic. Not a transistor SAR loop, offset/noise or MC qualification.
- Results/report: `docs/eight_bit_flat_migration.md`. Next circuit task is
  physical eight-bit flat CDAC/reference implementation, followed by actual
  load requalification, not further retired bottom-plate/GMAIN experiments.

## 2026-09-30

- User provisionally froze the top-plate sampling circuit at `522aa0f`,
  retaining the multi=4 hold pair, ratio-4 PGATE driver and existing timing.
  Accept 0.605518-mV measured five-point nominal maximum for this stage;
  pause further experiments. This is an explicit provisional exception,
  not compliance with the original 0.439-mV allocation or an RMS-noise
  rebudget. PGATEB reset/well risk remains open and deferred; ideal
  STRACK/clocks remain disclosed. No OA promotion or reliability/ADC
  signoff. Reopen only on user direction or later validation review.
- Implemented the first netlist-only PGATE driver using a real 0.9-V
  inverter and dynamic-G-powered T28 thick-oxide level shifter. Kept
  the multi=4 hold devices and external timing fixed. +0.8/+0.4-V
  raw errors are +0.080368/-0.605518 mV, so successful gate switching
  does not close the accuracy target. PGATEB retains charge during
  G reset, creating approximately 0.497-V positive PMOS drain/body
  bias despite absent CMI warnings. Resolve this reset/well concern
  before promotion; STRACK and external clocks remain ideal. See
  `docs/top_plate_pgate_driver.md`; no OA modification.
- Architecture decision: return to **top-plate sampling** as the only active
  SAR input/CDAC circuit line. Preserve bottom-plate fixtures as historical
  A/B evidence, not parallel production designs. The selected top path uses
  two input bootstraps and positive comparator top-node polarity; the
  independent GMAIN-off-before-BOOT-reset concept remains, with VIN-relative
  hold bias. The prior five-point mixed T28-core/ideal-relay bound is
  0.174132 mV maximum raw error, not full transistor-level signoff.
- In a top-plate-only copied netlist, the ideal-relay +0.8-V result
  reproduced to 0.174102 mV. One T28 NMOS cannot pull GMAIN to high VIN
  (0.761917-V residual, ±6.986726-mV held error); one T28 PMOS cannot
  reach low VIN (0.246400-V residual, ∓5.610205-mV error). Parallel T28
  NMOS+PMOS removes held GMAIN bias but `multi=4` still gives
  0.842425-mV maximum five-point raw error at ±0.4 V. `multi=1/2`
  improve the measured +0.4-V case to 0.481913/0.567460 mV, still above
  0.439 mV. No printed CMI, but ideal boosted gate steering and clocks,
  dynamic-well layout, PVT and SOA remain unresolved. Do not promote OA;
  next isolate charge/timing and sizing asymmetry on the top path.


- Replaced the copied full-CDAC protected bootstrap's ideal `GMAIN`-to-VSS
  hold relay with a T28 1.8-V NMOS while leaving `STRACK` ideal. Across
  five ±0.8-V-range static inputs, `multi=4` gave at most 0.004223-mV
  bottom raw hold error and lowered representative MN11 sustained current
  from 6.25772 uA to about 0.0000218 uA. Its latest GMAIN<0.1-V
  crossing was 250.454 ns, at least 0.846 ns before BOOT reset.
  Larger `multi=16/64` barely changed terminal bottom error. The top
  control still fails at up to 6.822 mV; printed MP8 CMI warnings and
  550-11,010 suppressed warnings prevent an SOA/pass claim. Keep the
  separate-gate/off-before-reset architecture, but solve top/clamp and
  remaining ideal driver/STRACK before OA promotion or size freeze.

- Integrated the independent OFF_MAIN-before-PHIB-reset protected bootstrap
  into copied OA-exported 5+5 CDAC decks, using 22 bottom sampling switches
  and two matched top-plate controls. With the ideal top clamp, holding
  `GMAIN=VIN` produces ±6.261925-mV raw bottom error at ±0.8-V differential
  input, despite microvolt-level B9 acquisition. After reference handoff,
  the high-side `GMAIN-B9` is +390.30 mV; one MN11 carries 6.25772 uA
  against its B9 reference relay, and the 50-ohm input source carries
  68.83530 uA. Source-relative gate bias thus fails to keep MN11 off when
  the CDAC bottom plate moves toward VCM.
- In the same copied full-CDAC fixture, changing only the ideal SHOLD
  terminal to VSS removes sustained bottom-switch current and reduces the
  ideal-clamp five-point maximum raw bottom error to 0.004218 mV. It is
  only a mechanism bound: the top-plate control then reaches ±8.752611 mV,
  endpoint pump MP8 CMI warnings appear, and a T28 physical clamp with
  VSS-off remains at -7.538001 mV at +0.8 V with clamp SOA warnings.
  The prior 0.00790/2.0960-mV bottom-plate findings used a different
  bootstrap and are not one-factor baselines. Next design must provide a
  physically safe main-gate off bias over bottom-plate excursion and a
  separately corrected top/split-node clamp before OA promotion.

- A nine-case copied-netlist charge screen on the split-GMAIN bootstrap
  candidate found that the ideal hold relay switches much faster than the
  OFF_MAIN clock: 50-600-ps clock edges produced only 1.1-5.0-ps GMAIN
  90-10 transitions. Increasing the hold relay's closed resistance from
  1 ohm to 1/5/20 kohm did slow GMAIN to 20.6/74.4/293 ps, but worsened
  raw held error from -2.452 to -2.514/-2.563/-2.647 mV. This does not
  support gate-slew tuning as the cure for the remaining 2.5-mV error.
- At 109.75/219.5/439 fF ideal load, the differential MN11 drain-terminal
  charge was 0.347/0.578/0.805 fC, not a fixed injected charge, while
  load and MN11 currents satisfied output KCL. Terminal current combines
  channel and displacement effects, so the physical mechanism is not yet
  uniquely decomposed. All nine cases fail the 0.439-mV raw-error gate;
  keep off-before-reset ordering but test charge routing in a full CDAC
  and real T28 gate-control topology next.

- Separated ideal `GMAIN` turn-off from the PHIB-driven BOOT/G reset
  sequence in six copied-netlist Spectre cases. With OFF_MAIN rising at
  250.2 ns and reset delayed by 0.1-1.0 ns after its completed edge,
  MN11 drain current reaches the nA/pA range before reset. The PHIB
  sequence changes differential VOUT by only +0.080 mV, while the
  approximately -2.53-mV error is already present before reset. A
  no-reset control drifts only +0.0000026 mV over the matched window.
  Best final raw error is -2.452 mV versus the 0.439-mV allocation.
- An imposed 19.922-mV differential VIN step between isolation and reset
  still induces 0.559-mV VOUT response, despite low static MN11 drain
  current; the 10-ps input edge is a stress test, not the specified sine.
  "Turn off first, then reset" is therefore valid sequencing but not
  sufficient accuracy or perfect electrical isolation. The ideal GMAIN
  relays must not be promoted as a transistor-level design.
- Ran eight exact-export, netlist-only Spectre A/B cases of the full-control
  bootstrap at +0.8-V differential input. Changing only MN9 body VIN->VSS
  reduced hold input current from 25.858 uA to 0.00326 uA but left
  -8.806-mV raw error and introduced five printed core `Vgb` warnings.
  Replacing MN9 with a known `nch_18_mac` geometry plus B=VSS reduced
  current to 0.0000343 uA and error to -6.842 mV without CMI warnings;
  the model/geometry and body changes are confounded, and raw error fails.
- Advancing PHIB by 0.8 ns alone changed the baseline error only to
  -8.656 mV and did not fix input loading. An ideal shared G-to-VIN hold
  clamp improved raw error to -1.102 mV but produced 76.974-uA input
  current because MN9 reversely conducts from VIN to low BBOT when
  `G≈VIN`. Main switch and MN9 cannot share that off bias.
- An optimistic split-MN11-gate relay bound maintained near-zero hold
  input current and reduced raw error to -3.014 mV, or -2.482 mV with
  early PHIB. Both exceed the 0.439-mV budget and exclude real relay
  parasitics/stress. Do not promote any variant to OA; next physical
  candidate requires separate T28 main-gate control and stress-safe MN9
  off/reset, followed by multi-input and full-CDAC checks.
- Audited terminal currents on the exact OA-exported full-control mixed-voltage
  bootstrap differential fixture without changing its circuit. The -8.755-mV
  held error forms mainly during turn-off: -2.939 mV in the 250.1-251.0-ns
  non-overlap gap while the boosted gate remains on, then -5.837 mV while
  the gate discharges. Differential output drift from 251.5 to 270 ns is
  only +0.022 mV. Output-device/load KCL and load charge agree.
- Confirmed a separate persistent hold input-loading path in high-side MN9:
  at 270 ns its body is about 0.840 V above its `BBOT` drain; the 50-ohm
  source supplies 25.858 uA, matching its drain terminal outflow, while
  25.293 uA enters the body terminal. This is consistent with a forward
  body/drain junction and produces 1.293 mV input-source drop. The sustained
  loading is definite but is not the sole cause of the already stored output
  error. This candidate remains rejected against the 0.439-mV raw error
  budget despite no nominal `CMI-275x` warnings. Next variant must address
  the off-state junction path and independently cancel/isolate turn-off charge.

## 2026-09-29

- Built two independently named mixed-voltage bootstrap OA screening cells
  without changing the existing driver. The initial candidate moved the
  known stressed pump, MN7/MN13, and main switch to 1.8-V PDK classes; the
  remaining core MP4/MN5 then showed model overvoltage warnings. Moving
  those controls to 1.8-V classes in the second candidate eliminated nominal
  `CMI-275x` warnings and kept 144 reconstructed D/G/S/B pair metrics below
  the diagnostic levels. But the latter's +0.8-V differential raw held error
  is -8.755 mV, about 20 times the 0.439-mV allocation. Device-class
  substitution therefore is not a complete protected sampling design; a
  separate turn-off/isolation and charge-transfer topology is still needed.
  Model-warning clearance is not transient lifetime or layout signoff.
- A full per-device bootstrap terminal-stress reconstruction from the exact
  OA-exported full-driver differential transient found more than one unsafe
  path: pump MN1/MN2/MN3 reach about 1.78 V, control/discharge MN7/MN13
  about 1.67 V, and main MN11 `Vgd` 1.148 V against the logged 0.99-V
  model-warning level. Nineteen printed Spectre warnings agree with the
  saved-waveform reconstruction. This is a nominal warning screen, not a
  foundry transient SOA/lifetime rule. A protected topology must address
  pump, control, and main-edge stress together while independently reducing
  the already identified 11.692-mV immediate turn-off error; neither width
  tuning nor a pump-only device swap is sufficient.
- A one-factor T28 NMOS top/split-node clamp width screen, keeping the full
  CDAC, 22 bottom bootstrap instances, clocking, and reference handoff fixed,
  found a narrow nominal raw-error window. W500, W250, W200, and W100 gave
  1.0533, 0.53152, 0.44865, and 2.5385 mV maximum errors at three static
  inputs. W185 gave 0.43378 mV across five inputs, only 5.22 uV below the
  0.439-mV gate. W100 failed to reset the top/split nodes before clamp
  release. The width trend is compatible with a parasitic-versus-reset
  tradeoff, not proof of its unique mechanism. All variants retain T28 clamp
  and bootstrap SOA violations, and the 22-pump architecture remains
  unvalidated for clock load. The W185 nominal pass is not a transistor
  acceptance or a reason to proceed directly to PVT/full-code integration;
  resolve terminal stress and isolate clamp reset/off-parasitic behavior first.
- Built matched, full 5+5 CDAC top-plate and true bottom-plate sampling OA
  fixtures without altering the existing `sar_bootstrap` or macro cells.
  The bottom version opens the top/split-node clamp before the 22 input
  switches, then connects all bottom plates to VCM. Its ideal charge
  conservation reverses comparator polarity while preserving exact binary
  weights for the `(32/31)Cu` bridge.
- With a zero-parasitic top clamp, five TT/0.9-V/27-C Spectre points gave
  0.00790-mV maximum raw bottom-plate held error versus 1.5320 mV for the
  matched top-plate baseline. This demonstrates the sequence's potential but
  is not a physical-clamp result.
- With four T28 L30/W1-um NMOS top/split clamps, five matched inputs gave
  2.0960-mV maximum bottom-plate raw error, −0.2602% fitted gain-error
  slope, and 0.0288-mV post-fit residual. The raw 0.439-mV gate fails.
  Approximately 0.74 mV of common-mode clamp release step mostly cancels
  differentially; the residual signal-dependent loss is consistent with
  clamp parasitic/off-state effects but not yet uniquely attributed.
- Both variants still use 22 complete bootstrap pumps on the CDAC bottoms,
  versus two in the top-plate fixture. Their internal nominal pump-capacitor
  inventory is 6.6 versus 0.6 pF; ideal clock sources do not validate the
  required clock energy or edges. Spectre reports millions of suppressed
  T28 bootstrap SOA warnings per run; the new NMOS clamp itself also exceeds
  its 0.990-V `Vgd` model limit. Do not promote either experimental
  fixture; separately target a low-parasitic clamp/shared pump arrangement
  and protected bootstrap terminal voltages before PVT or physical DNL/INL.

## 2026-08-31

- Rejected transistor sizing and external non-overlap as the primary fix for
  bootstrap held error. Thirteen one-factor, eight combination, and 24
  full-input confirmation Spectre cases showed that the best reasonable
  MN7/MN10/MP8/gap combination still has 10.298-mV differential error; an
  extreme MN7/MN10 multi 16/32 case still has 9.097 mV versus 0.439 mV.
- The extreme discharge candidate reduces fitted gain error from -1.510% to
  -1.132% but lowers minimum sample VGS from 0.811 V to 0.742 V. Its later
  discharge and hold drift are effectively zero; the remaining 9.097 mV is
  created at the immediate PHI turn-off edge. Do not implement it in OA.
- The next bootstrap change must target edge charge directly with independent
  boosted-path isolation timing, a complementary dummy/cancellation device,
  or bottom-plate sequencing in the differential CDAC. The approximately
  1.787-V terminal stress and PDK SOA warnings remain unchanged blockers.
- Isolated the first bootstrap prototype's held-sample error with 40/40
  successful TT/0.9-V/27-C Spectre cases from the exact OA export. The complete
  differential pair reaches 12.026 mV raw error and -1.510% fitted gain error;
  its 0.109-mV post-fit residual is below 0.439 mV, but no calibration contract
  exists, so the raw path remains failed.
- The same real DNW main switch with an ideal fixed-ground off drive reaches
  1.390 mV and -0.173% differential gain error, only 11.56% of the full
  maximum. A source-relative-off control cancels to below 1 nV in the matched
  pair. The driver network therefore adds about -1.337% gain error and is the
  dominant next correction target.
- Load and ideal-edge sweeps confirm a capacitive turn-off mechanism. Larger
  hold capacitance and slower gate edges reduce the isolated-device error, but
  neither is accepted as a production fix without acquisition, jitter, and
  linearity checks. Next inspect MN7/MN10 discharge, MP8 isolation, and
  non-overlap timing before dummy-switch or bottom-plate compensation.
- No OA object changed in this diagnostic. Global PVT and circuit freeze remain
  blocked by the held-error failure and the independent approximately 1.79-V
  core-device terminal stress.
- Created the first transistor-level `sar_bootstrap` OA prototype and dynamic
  off-phase-step testbench. Rebuild/readback corrected the clock multiplier to
  Abo Figure 5.5 NMOS `MN1/MN2/MN3`; both schematics now have zero check
  markers and the unedited OA export is the source for every Spectre wrapper.
- All nine TT/0.9-V/27-C input/Cboot runs completed. Acquisition settled in at
  most 0.681 ns with <=0.000729 mV end error, main `VGS` stayed 0.780-0.841 V,
  and Cboot droop stayed below 2.421 mV. However, held error reached 6.463 mV
  versus the 0.439-mV gate, so the prototype is not accepted.
- A 0.25/0.5/1/2-um main-switch width screen did not repair the held error;
  the 2-um seed had the best screened worst value. Keep 200 fF / DNW L60 W2
  only as the next-iteration seed.
- Spectre SOA warnings and terminal reconstruction show about 1.79 V maximum
  core-device gate-to-bulk stress in the multiplier and about 1.29 V `VDS` on
  MN7. Global PVT and production-cell freeze are blocked until the protection
  topology and signal-dependent hold error are corrected.
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
