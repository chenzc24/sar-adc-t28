# Frozen SAR8 staged characterization with server-side continuation

User authorizes continuing after short tests, repairing straightforward measurement/
startup issues with validation, then TT static, TT1024 FFT/power, five-point PVT
screen then static, statistical-model/unit-capacitance audit then30seed MC pilot
before100-200seed static. Laptop may power off; finite server continuation required.

Owned: scripts/sar8_campaign/, verification/sar8_campaign/, output/sar8_campaign/,
management/recipes/sar8camp-*.yaml, management/runs/sar8camp-*.yaml, this plan,
append-only plan/log.md; remote /server_local_ssd/chenzc_intern25/sar-adc-t28/
campaigns/sar8-functional-20261028 and corresponding managed runs. No OA objects.
Read-only dependencies: frozen A/B DUTs, all old recipe/input/managed agent files,
PDK/library/OA/history, unrelated dirty manualADC/comparator/10bit/Obsidian and
shared management policy. No commit/push or baseline adoption. Existing local
flows may coexist using idempotent managed launch locks; no simulator duplicated.

Preflight/readback resources, immutable registered identities, server-agent hash.
Finite coordinator uses existing managed agent status/submit/analyze APIs only;
never starts Spectre or waveform analysis directly. Bounded metadata handling,
single coordinator lock, persistent step state, conservative fail on uncertainty.
No resource-policy changes;2heavy max,4threads,1GiB sim,256MiB analysis,32MiB
collection. Register future recipes locally before dependent server submissions.
New long runs declare sufficient time budgets rather than altering live recipes.

Stage1: complete existing original A/B and phase60 A/B simulation/analysis.
Select B only if first/all codes, timing/order/count crosschecks pass; otherwise
use A only if it passes, explicitly retaining B failure. Neither pass blocks
expansion. Store selected DUT hash and source results. No automatic circuit edits.
Stage2: low boundaries1-3, then partitions4-255, clocklow60/high40, same input/
solver; offset59ns in stimulus/observer/decoder. Validate255boundary brackets,
256center codes, monotonicity; report DNL/INL/offset/gain and resolution bounds.
Stage3: coherent1024points,k461,4.501953125MHz,-1dBFS,continuous transient after
warmup; decode+observer crosscheck, power from source currents, explicit sampling/
integration limitations. No old027b951 metric attribution.
Stage4: original TT/SScold/SShot/FFcold/FFhot conditions, fixed0..0.9 references,
first short center-code screen thenstatic for that passing corner. Preserve model
corner policy (MOS corner with fixed nominal passives) in reporting, not full
process-combination signoff. Stress excluded from functional gate but retained.
Stage5: audit statistics blocks and multi/unit capacitor mapping before pilot;
no guessed mismatch distributions or blind seed multiplication. Full MC depends
on pilot coverage/runtime/covariance checks. Save unresolved prerequisites.

Validation: observer time-offset roundtrip; shifted decoder checks; native parsing
and static seam/FFT synthetic references; coordinator duplicate/failure/selection
tests with fake API; server checksum and process/status readback. No full-wave
arrays. Tests run once per changed surface. Artifacts/actual status explicit.

User update: independent scan segments and PVT cases may run in parallel. Coordinator admits groups of at most2 through existing managed policy, validates low boundaries first, then parallel pairs. Continuous FFT remains one run. No policy relaxation.

Latest user deadline: Beijing2026-10-29 evening, prioritize1024FFT and five-point
PVT key-code screens over full static. User explicitly allows more slots and
changed order. Fresh gate snapshot:48CPU quota,~29GiB account headroom,~106GiB
hostavailable,zero swap,2managed simulations using5declared threads. Own scoped
policy changes: AGENTS.md current concurrency paragraph; management/README.md
concurrency note; management/project.yaml resource counts;
management/execution_policy.json max_managed_workloads; scripts/management/
execution.py same default; targeted2slot legacy tests retained explicitly and
new6slot checks under scripts/sar8_campaign/. Only these fields may change;
all other dirty changes preserved. Also own output/verification managed storage
receipt for supported policy publication. Max6heavy,4threads each; all actual
CPU/memory/disk/unknownprocess checks unchanged. Current unmanaged/local workflow
for old frozen fullstatic may be checkpointed/stopped at exact verified local
orchestrator PID to prevent obsolete-priority follow-ons; never kill its active
managed simulation. Existing registered101ns runs remain unsubmitted.

Add solver short comparisons: same phase60 stimuli/DUT, CX moderate vs strict
CX conservative; MX moderate compared to CX moderate. Native actual settings,
code/order/close/acquisition/tail errors and elapsed times determine selection.
Require exact output codes, timing pass, aperture difference<=5ps, conversion
<=50ps, preclose error difference<=0.02LSB, tail margin difference<=50ps.
These are solver diagnostic tolerances, not revised ADC specification. No claim
of mathematical equivalence; retain strict reference and observed differences.
If no faster option passes, retain strict and report deadline risk. Future
fast recipes get new immutable IDs; do not edit any registered recipe.

User grants autonomous resource management within own account/project. Fresh observation:27.6GiB userheadroom,zero swap,4managed jobs/13threads. No cleanup needed. Permit independent B solver benchmarks to run concurrently with strict reference in the2free slots; server coordinator recognizes existing run IDs. Full FFT/PVT expansion still requires reference/solver comparisons. Never touch unrelated manualADC run or shared model/library data.

2026-10-28 recovery: all five short simulations completed. Phase60A analysis
failed because four newly saved lowercase Bootstrap internal nodes do not exist
in case-sensitive native deck; these optional precharge probes are absent.
Own scripts/sar8_campaign/recover_reduce.py and sar8camp-recover-*-v1 analysis-only
recipes/results bound to each completed source; preserve old failures and raw.
Require every original functional/timing signal, report missing precharge charge
as null/unknown, never synthesize internal values. Recover four phase60/solver
cases without resimulation. Actual CX-moderate log remains conservative; report
observed settings. Existing coordinator failed/stopped; do not claim downstream
runs submitted. Review results before a separately recorded continuation repair.

Recovered analyses all pass first/all codes and protocol. B/MX passes planned
numerical diagnostic (max closure0.021ps, conversion5.50ps, tail9.284ps); actual
6.748x speed observed, method/tolerances differ. Continue authorized B/MX priority
batch. Add four sar8camp-b-*-screen-mm-v2 recipes: only correct optional save node
case to actual XDUT.XBOOTP/BOOTN.BTOP/BBOT, electrical input unchanged. Original
v1 recipes/results remain immutable. Own continuation_v2 scripts/manifest and
remote campaigns/sar8-functional-20261028/continuation-v2 subtree. New coordinator
binds four recovery analysis IDs as result overrides, retains original simulation
identity/time, reuses existing FFT recipe and corrected PVT IDs, all managed.
Verify old coordinator dead before launch; preserve original failure status.

2026-10-28 user requests parallel A FFT. Add immutable A MX bench-v2 with only
four optional save-node names corrected to actual uppercase; same electrical
setup. Use already recovered A strictCX reference and identical solver diagnostics.
Own a_companion.py/deploy_a_companion.py, a_companion_manifest.json/launch receipt,
remote campaign/a-companion subtree. Finite managed companion runs A MX bench,
analyzes and compares, then submits existing A MX FFT if pass. If diagnostic
fails, retain failure and use existing strict A FFT for characterized reference,
explicitly record differing settings and deadline risk. No wait for B completion,
no duplicate source simulation, no ADC edits or baseline adoption.

2026-10-28 user authorizes same fivepoint A PVT parallel with B comparison.
Reuse completed A TT MX bench-v2; add A ssc/ssh/ffc/ffh screen-mm-v2 cases,
correcting optional save-node case only. Keep all B-v2 electrical conditions,
reference/input/clock/preset/resources identical except frozenA DUT. Compare10
codes, firstframe, nativeprotocol, aperture/conversion/acquisition/hold/DACtail.
CMI remains recorded and excluded from functional gate, not reliability signoff.
Own scripts/sar8_campaign/a_pvt.py,deploy_a_pvt.py, a_pvt_manifest/receipts,
verification/sar8_campaign/ab_pvt/, and remote campaign/a-pvt subtree. Existing
A/B FFT and B continuation untouched. Sixslot managed queue,4threads/maxjob,
1GiB simulation/256MiB analysis/32MiB collection remain. No commit/push.

2026-10-28 user asks for more compute. Account observation48CPU,~17GiB memory
headroom,2 FFT jobs using4threads each. Own narrowly threads_per_simulation
field in execution.py POLICY, management/project.yaml and published policyJSON;
raise allowable per-job ceiling to16, retain default4 and6heavy total plus actual
aggregateCPU/cgroup/memory/disk gates. Own thread_scaling/ evidence and recipes
sar8camp-a-mm-mt8-bench-v1, sar8camp-a-mm-mt16-bench-v1. Reuse exact immutable
A-mm-bench-v2 inputs and MX settings; change only declared/native thread count
and run identity. Compare elapsed/native actualthreads and existing functional/
timing diagnostic vs4thread reference. Keep current A/B FFTs running unchanged;
no restart until acceleration evidence and restart payback are evaluated. No
new baseline, tolerance change, cleanup, commit/push or automationchanges.
Dirty management fields outside precise ownership and all user work preserved.

Thread scaling also owns +mt allowlist in execution.py (1..16) to match declared cap. Initial registration rejected locally by old1..4allowlist, no remote runs submitted. Validate rejection of0/17/mismatched thread declaration.

2026-10-28 user authorizes parallel A/B TT fullstatic while preserving running
4thread FFTs, no mistaken process kill. Fresh preflight48CPU,15.9GiB account
headroom,zero swap; ~30.4GiB filecache and~1.7GiB anonymous RSS. No cleanup
needed. Own ab_static.py/deploy_ab_static.py, ab_static_manifest/launch/report
and verification/sar8_campaign/ab_static/, remote campaign/ab-static subtree.
Reuse all18 existing registered TTstatic IDs unchanged (CX conservative4thread),
no new duplicate recipes. Perlabel1..3low boundary must pass before atmost2
remaining independent segments concurrently; atmost4static heavy jobs plus
existing2FFTs subject to shared6slot and aggregate resource gates. Finite server
coordinator does not depend on laptop/heartbeat; existing B continuation later
reuses same completed/running IDs through managed idempotent locks. Failures
stop that label expansion, retain in-flight tasks, let other label continue.
Validate coordinator selection/failure/idempotency using synthetic metadata,
registered recipe/input hashes readback and initial process/state. No FFT
restart/priority change, no cacheflush/deletion, no circuit/solver modification,
no commit/push or automationresume. Shared-server contention cannot be promised
zero; account budget remains24declared CPU atfull6sim load vs48quota.

2026-10-28 user requests in-flightFFT code audit. Own fft_live_audit/ snapshots/report and script live_fft_audit.py. Read atmost2MiB native Spectre log per activeFFT plus small state/context; do not read growingraw or alterprocesses. Parse complete observerlines, compare counts/stability/validity and idealcodes at reported source aperture vs heldCDAC separately. Phasefit of partial sine is diagnostic only, no finalFFT or electrical verdict. Originalraw/native finalcrosscheck pending.

2026-10-28 user requests polling completed A/B FFT, final spectra/metrics and ADCToolbox analysis. Own scripts/sar8_campaign/fft_report.py and verification/sar8_campaign/fft_final/ (collected receipts, adapters, results, figures, report). Reuse read-only R4 toolbox_panel renderer with explicit current-source adapters; never change historical results. Await existing managed native streaming analyses, collect bounded derived results/logs once complete. Crosscheck all1032 native decoded frames,1024 measured codes, FFT against NumPy and ADCToolbox rectangular/DC-removed/side_bin0, Parseval and fixed-frequency fit. Inspect final figures visually. Native warnings and numerical/noise/mismatch/PEX/power limits retained. No new simulations, OA/baseline/Obsidian changes or commit/push.

FFT substage complete2026-10-28: A/B native1032frame crosscheck and1024point spectra passed; bounded results collected; NumPy/ADCtoolbox checks and3figure visual review complete. See verification/sar8_campaign/fft_final/README.md. Fullstatic stillrunning; PVTfullstatic/MC remain incomplete. This does not complete the whole campaign or electrical qualification.

2026-11-01 recovery: all static simulations complete; coordinator aggregation failed on raw effective_settings string equality. Own ab_static/recovery outputs; preserve original failure. Complete two existing A final-segment managed analyses, collect remaining small results, inspect actual settings before semantic aggregation. No simulation reruns or coordinator restart; unrelated dirty files untouched. No commit/push.

2026-11-01 — Fullstatic recovery: all18 A/B simulations complete. Original coordinator failed on string equality of maxstep logs (actual10ps identical; displayed defaults35.59/325.59/285.59ns vary with duration). Preserved failure JSON; ran only existing A196..227/228..255 managed analyses, both complete exit0, collected8 remaining small segment sets with hash checks/no skips. Local semantic aggregate preserves raw settings, validates all other settings identical, all255 ordered brackets and256 center codes/native checks perversion. A DNL +/-0.03125LSB, endpoint INL0.03666759LSB; B +/-0.0390625LSB, INL0.04448755LSB. Offset both0.85144043mV; endpoint gain -0.0953494%; bracket resolution1/128LSB.22/255 A/B boundaries differ by atmost1/128LSB. TT deterministic only, electrical deferred. Evidence verification/sar8_campaign/ab_static/fullstatic_recovered.json and recover_summary.py. No new simulation/coordinator restart/circuit/OA/automation/commit/push.

2026-11-01 plotting: own scripts/sar8_campaign/plot_static.py and ab_static/static_* outputs. Use installed ADCtoolbox plot_dnl_inl with measured transition-derived arrays, no histogram estimator for adaptive boundary search. Preserve nominal-LSB DNL and endpoint INL conventions. Produce full-scale and zoom PNG/SVG, verify arrays and inspect render; no simulation or circuit changes.
