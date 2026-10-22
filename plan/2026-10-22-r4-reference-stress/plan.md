# R4 reference-switch stress timing diagnosis

## Scope and ownership

User requested the exact nodes, timing phase, and waveform explanation of
reference-switch overvoltage in the completed1024-point sine test. Diagnose
only; do not change the ADC or implement a circuit fix.

Local owned: scripts/sar8_r4_refstress/, verification/sar8_r4_refstress/,
docs/sar8_r4_reference_stress.md, docs/figures/sar8_r4_refstress/, this plan,
and factual append to plan/log.md. Generated output/sar8_r4_refstress/ ignored.
Read-only: frozen netlist/sar8_physical/, full performance cases, all PDK,
SAR_ADC_T28 OA. Remote OA mutations none. Remote task-unique simulation only.
Keep concurrent R4 static batch running unchanged; one additional short
one-thread diagnostic is scoped separately, not a duplicate production case.
User Obsidian/cdac10 work, performance work, and cleanup commits are preserved.

## Method and checks

Map CMI instance D/G/S/B to saved node names. Existing1024-point waveform
contains only1ns strobes and lacks bottom/gate voltages: cannot reconstruct
sub-ns peak. Replay same continuous sine from t=0 with same frozen DUT, TT,
0.9V,27C, external sources, initial state and observer; stop450ns. Save native
adaptive timesteps from398ns onwards, selected bottom/gate/top/reference and
reset controls. CX one thread, log effective tolerances; shorter stop changes
default maxstep, so this is a diagnostic replay, not claimed byte-identical
solver trajectory or a replacement for long-run spectral results.

Require native result.ok, full duration, first4completed output codes matching
long run, DUT hash equality, actual native CMI reproduction, inspect warnings.
Use raw samples for peak and threshold crossings, quantify saved gaps around
the peak, distinguish direct node observations from inferred charge paths.
If attribution remains ambiguous, say so; do not claim causality from a sketch.
Plot separate clock/reset, switching gates, bottom/reference/top voltages and
terminal stress, with0.99V limit and highlighted stage. View image before delivery.
Report tests/limitations and append log; scoped local commit only after review,
no push and no baseline replacement. Performance-task files are not this commit.

## Completed validation — 2026-10-22

Replay01 finished450ns with native0errors/18warnings, result.ok true; CMI reproduced.
4004 adaptive samples; DUT equality and first4codes133/46/181/108 match long run.
BN6 peak1.006685V; BP6 minimum-0.111292V, corresponding PMOS |Vbd|1.011292V.
Both occur near401.358ns during acquisition/ref reset, not comparison.
Maximum saved gap within25ps of BN6 peak3.248ps; no timestep-convergence claim.
CX effective maxstep4.5ns, not requested10ps; actual settings captured.
Two figures inspected; overview plus native-sample stress zoom. Source hashes,
metrics and Chinese report saved. Later gate-stress events remain out of scope.
Analysis helpers made independent of unfinished performance scripts. Original
production artifacts remain required inputs; no ADC/PDK/OA edits or batch restart.
Scoped compile/analysis execution/diff checks; local commit only, no push.
