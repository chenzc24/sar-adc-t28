# B comparator retained-sample physical-input validation

User authorization: execute the proposed nominal and positive/negative worst-offset
sample check using physical CDAC hold inputs and actual B comparator timing. Preserve
each sampled comparator/receiver realization; assess offset, decision and kickback,
and investigate the existing numerical warning before choosing a size change.

Dirty-state note: 1204 porcelain entries on exp/cdac-flat8-device, ahead31. Existing
dirty work is outside the unique paths below. Frozen B DUT SHA256 must remain
f31b66c8fb35003bf7e8ad1a23d9c230b39f1f9651ccc469953e5e52ecf493ea. No baseline adoption.

Owned: this plan; scripts/sar8_mc/physical_input/;
verification/sar8_mc/physical_input/; output/sar8_mc/physical_input/;
management/recipes/sar8phys-*.yaml; management/runs/sar8phys-*.yaml; append plan/log.md.
Remote new managed runs sar8phys-* under the existing project SSD root and bounded
campaign metadata under campaigns/sar8-physical-input-20261104. Remote OA: none.
PDK/libraries/OA/original netlists/historical runs/Obsidian/other tasks read-only.
No cleanup, commit, push or changes to automations. Native Spectre only; VA may
sequence external stimulus and measure, never force comparator internal state.

Reference sources: corrected module-v2 30seed results, nominal plus seed4121
(-23.9375mV) and4124(+25.3125mV); retain seed4101 DC warning separately if needed.
Use native B MOM array and relevant hold/isolation switches, supply0.9V/27C,
original physical geometries and receiver loads. Define any omitted reference/
sampling/controller boundary explicitly. Input hold must be genuinely floating
through physical capacitance/off switches during evaluation, not low-impedance VA.
Native B comparator high-time reference0.7855..1.0150ns, inputCM~0.449V. Preserve
original external60ns low/40ns high frame clock and closing edge for integrated
replay; module timing must be explicitly tied to recorded internal comparator edges.

Steps: inspect installed native mismatch replay/freeze support, retain all sampled
comparator/receiver parameters and prove identity across the new interface; inspect
native B CDAC/sampling connectivity and choose the smallest faithful fixture. One
nominal/retained-sample control validates fixture/measurement before remaining
cases. Measure effective threshold from held differential at clock-on, sample
and hold charge/kickback, raw/receiver resolution by actual budget, input history
and native numerical warnings. Recheck warning-bearing sample4124 with a focused
accuracy setting only if its warning remains relevant. Any design experiment must
follow reproduction and change one declared variable; do not presume the input
pair is the unique cause. Additional wholeADC30/FFT/PVT campaigns are not included.

Validation: immutable run/model/fixture identities, complete native results, exact
random-sample mapping for all retained physical instances, finite/correct source
and switch timing, independent native vector checks and bounded stream reducer.
Invalid sample mapping blocks claims about that sample, not unrelated preparation.
Failures and unknowns remain recorded; no seed substitution or performance waiver.
Maximum4 campaign heavy tasks, each SpectreX MX4threads/RSS1GiB, analysis256MiB,
small collections32MiB. Shared7-slot gates unchanged; use managed register/submit/
status/analyze/collect and source-bound analysis-only for old data. Never bypass.

Deliver selected sample evidence, fixture/mapping method, native measurements,
before/after comparison, concise explanation and next adjustment if justified.
Status: completed retained-sample physical-input validation, input-pair contribution
test and legal W2 candidate comparison. Report/figures/validation saved under
verification/sar8_mc/physical_input. Candidate not adopted; no further runs pending.

Fixture review before submission: installed Spectre21.1 montecarlo help documents
ignore=[XHOLD] excludes the added nominal front-end from random sampling. Original
91 comparator/receiver/load hierarchy rows and19columns are retained from each
source; analyzer requires exact equality of every old scalar, not only input pair.
Positive parser control and deliberately perturbed MNINP rejection pass. Native
clock export sar8phys-clock-reference-v1 is source-bound and complete,26.07s/~9MiB;
four small files583299bytes hash-collected. PWL reproduces original first phase60
frame (external100ps edges) and repeats its8pulse comparator burst every100ns.
First comparator rise102.7691094ns/fall103.5546085ns; threshold read103.5046085ns,
pre-kick measurement100ps before rise. Interface sourceCM0.449V. Added real native
Bootstrap/CDAC uses fixed N-low/P-high bottom word, original50ohm input/reference
sources and4pF reference bypass. Its own mismatch is intentionally nominal to
isolate the retained comparator sample; full SAR bottom-word/feedback omitted.
Paired clamp resistances1mOhm and1e18Ohm keep identical topology; held leakage of
the diagnostic clamp is negligible compared with physical off switches. Only
external sources are driven by VA.22frames/2259ns/5psmaxstep; six unique recipes,
each~6.85MiB input, simulation output512MiB. Native checks retain all176pulse
decisions, input kick/CM, actual hold/pre values and source/native crosschecks.
Start nominal-hold and4124 held/stiff pilots; remaining three follow only after
native fixture and all91-row sample identity confirmation. No circuit sizing yet.

Method reference for topology-sensitive sample reproduction:
https://community.cadence.com/cadence_technology_forums/f/custom-ic-design/35465/regarding-monte-carlo-simulations/1346084

Pilot observation: native ignore mapping exactly reproduces all91old rows in both
4124 modes; guards and first search points operate correctly. Physical sample
path lowers sourceCM by~0.887mV. Initialv1 mistakenly used desired comparatorCM
as the sourceCM(0.449V), yielding heldCM~0.448113V. Preserve its three in-flight
runs as an extra common-mode comparison, no kill/restart. Correct finalv2 source
to original0.45V in both modes, so physical heldCM reproduces original~0.449V.
Other unusedv1 cases remain unsubmitted; no new sample draw or geometry change.

Execution recovery: SSH reset during third final registration; inspected same boot
and exact registered identities after user restored network. First two final
registrations complete, third absent; reused first two and registered remaining
under original IDs, no duplicate simulation. All three initial simulations exit0.
First coordinator mistakenly set hard RLIMIT_AS256MiB, inherited by managed
analysis workers which correctly failed before child startup when setting their
declared virtual limit. Preserve those failures and failed coordinator. Three new
source-bound *-recover-v2 analyses reuse completed original waveforms through an
adapter. Recovery coordinator in recovery_v2 has no lowered inherited hard limit;
managed children still enforce their own declared budgets. Existing pinned monitor
continues unchanged, one collector/DB. It will proceed to six finalv2 paired cases
after the bound analyses prove data/91-row identities. No simulation reruns.

Final physical-input results emerging: negative extreme remains-23.92696mV vs
stiff-23.93750mV; positive initial physical remains+25.30175mV. Differences below
125uV search resolution, supporting comparator internal mismatch as main issue.
Nominal stiff case has exact-zero input repeatedly unresolved in this noiseless
symmetric circuit, leaving search bracket wide; preserve as invalid threshold,
not a wrong-code diagnosis. Add one two-frame +/-62.5uV guard to bound nominal
threshold without choosing an arbitrary sign at zero. Add two input-pair-only
nominalization diagnostics (both extremes): ignore MNINN/MNINP and usesamesequence=yes;
require exact reproduction of all89remaining source rows before causal claims.
All added controls preserve geometry, timing and physical front-end. No sizing
until this decomposition identifies a useful variable; no full30expansion.

Decomposition source data complete: ignore/input-pair control retains all89other
rows exactly and omits the2input rows. Effective held thresholds reduce from
-23.92696/+25.30174mV to approximately-7.684/+4.686mV. This implicates input pair
as a major contributor, with substantial remaining-device effects. Proceed to
one candidate variable: MNINN/MNINP W1um->4um, L30nm/nf1/multi1 unchanged; diffusion
AD/AS/PD/PS/NRD/NRS follow the same width geometry consistently. Keep original91
latent sampled parameters and require exact identity again. Three selected
samples only; no baseline adoption. Candidate output budget768MiB accommodates
changed adaptive point counts, RSS1GiB and shared gates unchanged. Add one nominal
held reltol1e-7 vs1e-6 accuracy experiment (same5psmaxstep, output budget1GiB),
because nominal held has LTE relaxation notices; do not erase original warnings.
CMI-2732 here is a resistor rcut warning, not terminal stress: the diagnostic
1e18Ohm clamp is actually clipped to1e12Ohm. Use effective1e12 in interpretation;
even a conservative1V across it for40ns into>=1pF causes<0.05uV drift. Preserve
the warning and effective value, no claim of exact infinite isolation.

Candidate W4 nominal/4121/4124 all refused natively before transient (CMI-2440):
W4um exceeds model group Wmax2.7001um, valid L at30nm. Preserve three failed IDs,
no soft-bin override. Replace only this geometry experiment with W2um within
the stated model range, same L/nf/multi and derived geometry; three original
samples, all91latent scalar identities still required. W4 is not a tested
performance candidate. Tight nominal accuracy run remains in flight separately.


Final result (2026-11-04): completed physical/stiff nominal and two preserved
extremes, targeted input-pair nominalization, finite nominal guard and tighter
nominal accuracy control.19native simulations total:16completed,3W4model-range
failures;3initial analysis-start failures preserved/recovered by source-bound
analysis-only identities, no simulation reruns.16small result sets collected;
allused results native-crosschecked, hashes checked,16searches independently
recomputed (one exact-zero nominal stiff search invalid, separately bounded by
+/-62.5uV guard). Exact retained scalar checks91rows,89for input-pair exclusion.
Physical thresholds-23.926955/+25.301739mV vsstiff-23.9375/+25.3125mV, intervals
overlap. Input-pair mismatch removed ->-7.683987/+4.685660mV. Legal W2 candidate
->-20.178584/+20.178959mV, selected amplitude reductions15.67/20.25%; tested
first-pulse speedmax0.366833->0.280478ns. Selected three-window kick including
clock-fall reset0.143624->0.243339mV; CLK-high-only probe peaks also stored.
Candidate remains~2.87inputLSB offset, not adopted; no new30seed/PVT/fullSAR/power
qualification. Original frozenB byte hash unchanged. RelTol1e-7 nominal search
bracket unchanged, speedmaxdelta0.102ps; original LTE and extra16881 warnings
retained. CMI2732effectiveclamp1e12Ohm documented with40nVconservative driftbound.
Pinned164dbe6 monitor extended to19runs, corrected original childname phys_tran
rather than MC-prefixed logStatus name; preserved prior incomplete snapshot,
reloaded only identity-verified own collector, same DB. Final16complete/3failed,
no unknown/incomplete; active monitor200049, source logs untouched. CSV/JSON,
two PNG/SVG plots reviewed; validation.json/report_qa.json saved. No OA/PDK,
original netlist/library, Obsidian, baseline, other processes, automations,
cleanup, commit/push changes. Next proposed design surface: legal input-pair
area/geometry and remaining-device contribution; not launched beyond W2.
