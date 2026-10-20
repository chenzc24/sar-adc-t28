# Independent P/N reference-switch sizing experiment

## Goal and scope

Test the user's hypothesis that relatively weak PMOS / strong NMOS causes
the remaining negative-bottom SAR spike with ideal gates and no real driver.
Use native Spectre APS and the existing eight-bit dual-rail characterization
fixture. Do not replace its fixed-period behavioral control with the separate
asynchronous controller. No OA, Canvas, installed VA, baseline or PDK edits.

Run the 2x2 factorial P/N parallel multipliers (1,1), (2,1), (1,2), (2,2)
at VDIFF=-0.003515625 V and +0.453515625 V. All are TT/.9V/27C, 300ns,
unchanged Bootstrap/MOM/reference R50ohm/C4pF, 100ps blanking and 20ps gates,
ideal sign comparator, no physical transient noise. Unit W/L remain
175/30nm P and 150/30nm N; integer multiplicity is an effective-width scan,
not a re-PCell-netlisted finger-width scan. Capacitances/charges change along
with conductance, so do not identify Ron as the sole cause from this sweep.
Allow one maxstep10ps confirmation of the decision-relevant best candidate,
including the newly current-instrumented P2N2 control if it remains best.

## Ownership and dirty-state note

Branch exp/cdac-flat8-device. Untracked cdac10_dualrail paths are preserved
superseded work. Untracked config/sar8_simple.yaml,
models/behavioral/sar_async_simple.py, plan/2026-10-20-sar8-simple-async/,
scripts/sar8_simple/ and verification/sar8_simple/ are concurrent read-only
work. No overlapping owned paths. Read the maintenance-log tail again before
the bounded append. Do not stage unrelated files.

Own this plan; scripts/cdac8_dualrail/pn_ratio_experiment.py and
pn_ratio_results.py; docs/cdac8_pn_ratio.md; docs/figures/cdac8_pn_ratio/;
bounded plan/log.md append. Generated evidence: output/cdac8_pn_ratio/.
Remote OA owned objects: none. Original decks/results, all other sources,
installed VA and the foundry PDK remain read-only. Scoped local commit; no push.

## Implementation and validation

1. Check bridge profile t28_io, CIW/library SAR_ADC_T28/tsmcN28, native
   Spectre availability. Read official terminal-current save help before adding
   current observations. If unsupported, retain voltage-based diagnostics and
   explicitly report that limitation rather than invent currents.
2. Derive from hash-pinned completed direct_bad/direct_control decks and stage
   exact VA sources. Change only per-polarity multiplicity tokens in eight
   reference leaf subckts, plus observation saves and the optional fine maxstep.
   Assert all other circuit/source/control lines unchanged; keep source/deck/
   VA hashes and original evidence. Refuse to overwrite existing cases/results.
3. Run eight tasks with an explicit two-worker scoped pool, require result.ok,
   preserve native log/PSF/errors/warnings. Do not interpret numeric completion
   as SOA or ADC qualification. Model CMI logs, not a guessed breakdown value,
   establish the current .99V SOA warning threshold; no lifetime exemption is
   inferred for short pulses. No checklimit/PDK warning suppression changes.
4. Reconstruct five terminal differences across all 32 reference MOS; report
   all-time, SAR, restore maxima and offending instance/terminal/time, CMI,
   suppressed warnings and LTE. Verify all 16 ideal gate equations and expected
   codes 127/192; finite complete waveforms. Compare all eight pre-compare
   residuals against the ideal-charge oracle and .25LSB=1.7578125mV.
5. In first SAR transition, measure BN5 minimum, unchanged local gates, TOPN,
   BN7 fall / BN6 rise and sampled native pass terminal currents if available.
   Compare unchanged-ratio fresh controls with retained 1x/2x evidence and
   describe any numerical instrumentation delta. Include same-scale timing
   plots with ideal rail/zero/error/SOA references, legends and phase windows.
6. Focused source/invariant/result assertions, Python compile, figure inspection
   and git diff --check. Report limitations: two TT inputs, ideal gates/sign
   comparator, no full input/PVT/noise/MC/layout/lifetime qualification. Append
   factual log, scoped commit only. No baseline promotion or push.

## Outcome

Nine completed native APS runs: eight factorial/input points and P2N2 negative
input maxstep10ps confirmation. All result.ok, finite/complete to300ns, codes
127/192 correct, all residual budgets pass (largest .405704mV). No LTE
relaxations. Twelve documented first-terminal native current saves per run
succeeded; ideal gate equations hold below1e-10V for every bank.

Negative input P1N1/P2N1/P1N2/P2N2: first-SAR BN5 minima
-140.452/-17.866/-140.340/-83.908mV. SAR worst ports
1.040452/1.083153/1.141965/.983908V; restore worst
.925287/1.126315/1.218550/.933910V. Increasing only P improves BN5 ~87% but
the SAR worst moves to XSP6.MN_LOW and restore fails at XSN6.MN_LOW. Increasing
only N fails more severely, including a BP6 negative-restore undershoot whose
MP_HIGH Vbd is1.218550V. Thus ratio matters, but no single-polarity enlargement
solves all nodes/phases. Only P2N2 passes the present SOA checks at both inputs.

Fresh retained-control peak deltas +1.459/-0.052/+0.001uV; current observation
does not explain the changes. New P2N2 fine peak .983907740V, delta-.493uV and
residual delta+.112uV. CMI15 each on the three failing negative groups, with
suppressed counts6780/5666/8465; P2N2 and all positive groups zero. Current
limits printed by the loaded model confirm990mV; no short-pulse/lifetime
exception inferred. Physical current includes displacement; no pure-Ron claim.

Two scripts, report, three common-scale phase figures and curated metrics;
figures visually inspected. Source reversibility/circuit immutability, all
source/deck/VA/wave hashes, focused output/count/current/gate/code/error/SOA
assertions, Python compile and diff checks pass. Original OA/Canvas/PDK and
retained experiments unchanged. Unrelated simple-async files/figures remain
read-only. Scoped local commit only, no push; no size freeze or baseline move.
