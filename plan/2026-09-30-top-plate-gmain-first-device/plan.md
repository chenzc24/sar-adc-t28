# Return to top-plate sampling: first T28 GMAIN device screen

## Goal and boundary

The selected SAR sampling architecture is now conventional **top-plate
sampling**. Correct the project status so historical bottom-plate experiments
remain evidence, not an active second design line. Begin the top-plate
GMAIN/turn-off implementation with a bounded copied-netlist screen of a
real T28 hold device. This is a first device experiment, not full gate-control
or ADC signoff.

Start state: branch `exp/bootstrap-protected-eval` was clean; new isolated
branch `exp/top-plate-gmain-t28` was created. Prior top-plate full-CDAC
`GMAIN=VIN` / ideal `SHOLD` five-point result has 0.174132-mV maximum raw
error, but both GMAIN relays and clock sources remain ideal. The bottom-plate
T28 VSS pull-down is not a top-plate solution.

## Ownership

- Local tracked: this plan; `README.md`; bounded status notes in
  `docs/architecture.md`,
  `docs/design_log.md`, `docs/bootstrap_bottom_plate_eval.md`,
  `docs/bootstrap_full_cdac_isolation.md`, and
  `docs/bootstrap_t28_hold_pulldown.md`; new top-plate status and screen reports under
  `docs/`; new generator/analyzer under `scripts/characterization/`; bounded
  `plan/log.md` entry.
- Generated and ignored: exact copied decks, Spectre PSF/logs, and JSON under
  `output/top_plate_gmain_first_device/`.
- Remote OA owned: **none**. All Virtuoso cellviews, original OA exports,
  foundry PDK, prior scripts, and prior output are read-only.
- Shared read-only dependencies: exact-hash OA-export full-CDAC generator,
  protected-bootstrap source, PDK model include, `t28_io` Spectre runner,
  PSF parser. EVAS has no transistor/KCL solver, so this target uses Spectre.

## Steps and gates

1. Build a top-plate-only copied deck by removing the unrelated `XBP`
   bottom-plate fixture from the prior full-CDAC source. Retain `XTOP`,
   `XTOPBOOT_P/N`, CDAC, sources, timing, and PDK statements. Reproduce the
   ideal `SHOLD (GMAIN VIN OFF_MAIN VSS)` top-plate +0.8-V baseline first.
2. Replace only `SHOLD` with a T28 `nch_18_mac` pass-to-VIN candidate,
   `MN14 (GMAIN OFF_MAIN VIN VIN)`, using the existing exported 1.8-V
   `MN7` geometry as a starting point. Keep `STRACK` ideal and the 0/0.9-V
   `OFF_MAIN` drive ideal. Run +0.8 and -0.8 V to expose the expected
   high-VIN NMOS headroom limitation. Do not introduce an unaccounted 1.8-V
   control rail. A failed candidate is useful evidence, not a reason to
   relabel it a validated gate driver.
   If it fails for that expected reason, screen one complementary
   `pch_18_mac` pass-to-VIN device using the existing exported MP4 geometry.
   Its gate is held at boosted `G` during track and VSS during hold by two
   explicitly **ideal** steering relays; its body follows GMAIN as a
   diagnostic well-bias hypothesis. This tests pass-device feasibility,
   not a realized level shifter or validated dynamic-well layout.
   If NMOS and PMOS fail at opposite VIN endpoints, combine those exact
   two T28 devices in parallel as one complementary transmission path,
   without changing the ideal gate controls, sizes or timing. Run both
   endpoints. This is a one-factor topology test, not a full TG design.
   If the complementary pair passes endpoints but fails a midrange point,
   screen smaller matched device multiplicities `multi=1,2` at +0.4 V
   and +0.8 V before deciding whether to expand either to five inputs.
3. Measure top-plate raw error at 270 ns, gate discharge before 251.3-ns
   BOOT reset, held `GMAIN−VIN`, MN11/MN14 and input currents, sampled
   device terminal voltages, printed CMI and suppressed warnings. Verify
   baseline and candidate circuit differences are bounded and PSF data
   finite/aligned. Expand the complementary candidate to five static inputs
   only if its +0.8-V endpoint meets the 0.439-mV raw-error gate without
   printed/suppressed CMI. Do not infer full-input/PVT signoff.
4. Document physical/ideal boundaries and next circuit decision. Validate
   Python compile, source hashes, generated deck diff, Spectre success,
   JSON values and warning inventory, `git diff --check`, and owned diff.
   Commit locally as `test: start T28 top-plate GMAIN hold device`; no push.

The 0.439-mV raw error is a first-pass functional gate, not a noise/PVT/SOA
signoff. Even a numerical pass would still require a physical `STRACK`,
realizable control drive, clock/power accounting, next-cycle acquisition,
full-input/dynamic tests, and foundry terminal-stress resolution.

## Mid-run evidence

The top-only ideal-relay +0.8-V baseline reproduced 0.174102 mV versus
0.174132 mV in the earlier mixed fixture, with no printed CMI or suppressed
warnings. The first real NMOS hold candidate failed symmetrically at
±0.8 V: ±6.986726-mV top raw error and 0.761917-V held high-side
`GMAIN−VIN`, despite zero printed CMI. This activates the bounded PMOS
feasibility screen above; no NMOS size sweep is justified yet.

The single PMOS also failed symmetrically: ±5.610205 mV; low-VIN
`GMAIN−VIN` remains +0.2464 V. Its printed CMI and suppressed warning
counts are zero. The complementary-pair screen is now activated.

At +0.8 V the complementary pair gives -0.279944 mV raw top error,
near-zero held `GMAIN−VIN`, and zero printed/suppressed CMI. This meets
the bounded expansion rule; run the remaining four static inputs.

The full `multi=4` five-point sweep fails at ±0.4 V with ±0.842425 mV
despite held `GMAIN−VIN` being within microvolts and no CMI. The error
is not simply residual DC gate bias. This activates only the stated
smaller-multiplicity screen; do not claim a top-plate pass from endpoints.

The smaller matched devices improve but still fail +0.4 V:
`multi=1` gives -0.481913 mV; `multi=2` gives -0.567460 mV. Both
+0.8-V checks are below 0.439 mV, demonstrating why midrange is the
decisive screen. Fourteen total selected runs completed with zero Spectre
errors. No CMI or suppressed warnings were printed, but `multi=2` at
+0.8 V had one additional LTE-discontinuity warning. The top-plate
architecture/status corrections and factual device report are the
handoff; full GMAIN control remains unimplemented.
