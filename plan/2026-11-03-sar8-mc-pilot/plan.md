# B SAR8 local-mismatch pilot and 30-seed key-code campaign

User authorization: B version, first 2–3 seeds to verify actual mismatch activation
and runtime, then automatically complete 30 key-code seeds. Use read-only
spectre-log-inspector commit 164dbe66391b580fe28ff73ad9fd07824644f934 to monitor.

Dirty-state audit: 840 entries (12 modified, 3 deleted, 825 untracked), branch
exp/cdac-flat8-device ahead31. Existing sources and measurements are read-only;
new unique prefixes below do not overlap earlier work. Preserve all user changes.

Ownership: this plan; scripts/sar8_mc/; verification/sar8_mc/; output/sar8_mc/;
management/recipes/sar8mc-*.yaml and management/runs/sar8mc-*.yaml; append-only
plan/log.md. Remote new managed runs sar8mc-* under verified project SSD root,
finite campaign coordinator under campaigns/sar8-mc-20261103, and isolated pinned
monitor deployment/database under that campaign. No OA ownership. No commit/push.

Dependencies: frozen B f31b66c8fb35003bf7e8ad1a23d9c230b39f1f9651ccc469953e5e52ecf493ea;
original native standard library/model includes, existing phase60 TB and reducer.
PDK/library/netlists/history/Obsidian/other projects read-only. Do not change device
sizes, external60low/40high clock, closing edge, source impedance/reference/input
range, topology, supply0.9V,27C,10MS/s. No transient noise/process variation/PEX.
Unit-CDAC expansion may exist only in separate statistical test copies and must
pass nominal equivalence and model-semantic review before random tests.

Implementation: inspect actual statistical sections and unit multiplicity; prepare
deterministic nominal control and three unique seed pilots, with saved random
parameter evidence and duplicate-seed repeat for reproducibility if needed. Validate
SPICE MC options using installed help and previous activation evidence. Freeze all
inputs. Use managed register/submit/status/analyze/collect only; preserve failures,
warnings and original IDs, never uncertain resubmission or resource-gate bypass.
After three pilots establish valid independent random samples and valid raw/native
measurements, finite coordinator admits remaining27 seeds. Circuit failures remain
results rather than stopping statistics, while configuration/activation/data/resource
faults hold dependent submissions. No automatic circuit tuning or seed replacement.

Budget: four campaign simulations concurrently, each Spectre X MX4threads, declared
RSS1GiB; analysis256MiB, collected32MiB/run. Existing global7slot policy unchanged.
Use sparse selected saves, bounded raw/output/wall budgets; observe live admission.

Monitoring: isolate pinned repository from existing E:/spectre-log-inspector dirty
workspace. Read AGENTS/README/quickstart/handoff/ssh and perform sample scan. One
collector per unique server SQLite DB. Collector read-only w.r.t simulations;
campaign orchestration is separate, uses managed controls and cannot infer pass
from monitor complete alone. Keep remote command session/checkpoint, status/wait
cursor/show/evidence JSON; no recurring automation is enabled without user request.

Validation: frozen source hashes, correct local-mismatch-only sections, nominal
unit expansion equivalence, actual random parameter dispersion and repeatability,
installed native MC seed settings; each seed retains one fixed random circuit
through all key inputs. Native decoded code vs observer, protocol counts/order,
startup, source/hold/settling/conversion metrics. Output variation near quantization
threshold is a measurement, not automatically a wrong-code failure. No full
DNL/INL/FFT/yield or electrical signoff claim from 30 key-code seeds. CMI retained
and deferred per user. Small analyzer tests, compiler check, JSON/YAML parsing and
scoped diff. Deliver exact run/seed identities, activation, runtime, measurements,
monitor evidence and continuation state.

Status (2026-11-04): completed module-v2 CDAC/comparator30each plus nominal/repeat
controls (64 managed runs); collected, independently recomputed and figures reviewed.
Final report: verification/sar8_mc/blocks/README.md. Historical checkpoints below
retain earlier decisions/failures and are superseded by the final module results.

Latest retained-run checkpoint (2026-11-04): nominal and3101 native complete,
363.49/692.80seconds,10frames each; v3 analyses complete and small files hash-collected.
Both protocol/native decode checks pass.3101 changes7center codes by−1LSB; not a
yield or root-cause conclusion.18CDAC/2input-pair random records saved. Four optional
Bootstrap charge nodes absent remain unknown. Monitor config corrected with actual
analysis/raw paths; same pinned source/DB, only collector reloaded, now complete.
Stopped3102/3103 and pending27/repeat remain untouched. Module work remains planning.

Latest user steering (2026-11-03, supersedes full-campaign continuation): prioritize
CDAC and comparator module-level mismatch characterization; do not automatically
expand integrated30 seeds. Exactly nominal +3101/3102/3103 were submitted before
this steering. Preserve these four in-flight simulations and analyze completed
evidence. Other27seeds and repeat are registered only, not submitted. No finite
simulation coordinator was deployed, so no automatic future submissions are active.
The isolated read-only inspector collector may continue observing these runs.
Prepare the smaller block characterization scope and actual interface/load needs;
do not confuse registered full-campaign inputs with launched work.

Subsequent explicit stop authorization: retain nominal and seed3101; stop exactly
seed3102/3103 if still running. Before SIGTERM verify managed source registration,
current child PID/start_ticks/UID/PGID and Spectre command path. Preserve raw and
native worker outcome plus separate user-stop receipt; no other process signals.
No automatic expansion. Plan the CDAC/comparator blocks under verification/sar8_mc.

Recovery extension: both retained simulations are native-complete (nominal363.49s,
seed3101 692.80s). Nominal analysisv2 failed on four unsaved optional Bootstrap
charge nodes; reuse the existing recover_reduce optional-signal handling in a new
bound analysis-onlyv3, preserving the failedv2 and all simulation data. Inspector
configuration omitted analysis name needed for logStatus: add actual tran_ab name
and exact PSF path, restart only its own collector to reload configuration; retain
same DB/cursor and immutable164dbe6 source. No simulation reruns/extra seeds.

Latest execution authorization: run the two module campaigns through30 seeds each
for tomorrow's review (2026-11-04), after nominal/first3 sanity checks. This replaces
the planning-only checkpoint, and does not authorize resuming integrated30. Own
additional scripts/verification under existing sar8_mc paths and new managed
sar8mc-cdac-* / sar8mc-comp-* IDs plus one finite module coordinator in the existing
campaign. Digital sequencing may be ideal/VA stimulus with explicit scope; native
MOM and comparator/receiver load remain transistor/PDK models. Preserve two complete
integrated sources as anchors. Fix missing optional bootstrap observation only in
new source-bound analysis recipe; existing failed analysis retained.
Module initial scope: CDAC18MOM AC-derived static differential weights at0.45V bias
(not switch settling); comparator loaded effective threshold/decision delay under
defined reset/clock and input history (not complete asynchronous timing or kickback
qualification). Native voltage dependence/physical held-input followups remain
separate, not fabricated from this batch. Stage3 results determine data-validity
activation, not zero performance failures. Registered30module runs continue only
after valid pilot data, with circuit failures retained. Four campaign work slots
maximum, global7 unchanged; no other processes stopped or policy relaxed.

Figure-review correction: CDACv1 ideal-source array was optimized into turbo
merged groups (8target random rows instead of18); P/N branch currents/weights
became identical. Quarantine its statistical interpretation; retain all runs and
old figures. Comparator input-pair rows remain two independent named instances,
but qualify its merging boundary separately. CDACv2 adds installed-documented
preserve_inst=all and fixes case-sensitive explicit current saves. First nominal
and seed4101 must show18separate MOM random rows and non-identical P/N physical
capacitances before the corrected30-seed batch. This is a new fixture revision,
not an uncertain resubmission. Require targeted independent-row/physical-vector
checks, not merely different whole-file random hashes. No original B changes.

Model-semantic update: direct read of actual cfmom_2t implementation confirms
local mismatch geometry normalization contains the total multi capacitance
(inverse square-root scaling), while nominal capacitance scales by multi. Keep
the original B DUT byte-identical rather than expand units unnecessarily; record
this model-dependent aggregate representation and verify saved CDAC random values.
Nominal control changes only statistical corner sections, no random iteration;
compare against existing B TT10-frame reference. Thirty independent seeds3101..3130,
one MC iteration each, plus seed3101 repeat control. Each circuit sample runs all
ten original key-code inputs. Probe activation/nominal/repeat checks are one
campaign setup validation, not extra design-approval layers.


Current module-v2 checkpoint: follow-up heartbeat cdac-30 created in this calling thread,15minute checks for recovery/report only; pause after delivery. Oldsar8/r4 unchanged. Final manifest/launch are blocks/v2_manifest.json and launch_v2.json; remote modules_v2. FirstCDACv2 sample has18named MOM rows and distinctP7/N7 native capacitances. Comparatorv2 input-pair sample remains independent. Completev1 retained, itsCDAC interpretation invalid. Retained integrated nominal363.49s/seed3101 692.80s completed; existing v3 bound analyses reused. Nominal10codes match,3101 has7center deviations of-1LSB. New boundary analysis reads CM0.449017–0.449082V and high-clock0.7855–1.0150ns; first postprocessing failed due Python2 comprehension-variable leakage, corrected analysis-onlyv2 succeeds without simulation rerun. Measurement and collection-failure receipts preserved.


Final module delivery (2026-11-04): corrected v2 completed64/64 simulations and
managed analyses;64 small sets hash-collected, no raw waveform download. CDAC and
comparator each30 independent local-mismatch draws4101..4130 plus nominal/repeat.
All18 target MOM rows independent with distinct native P/N capacitances; actual
model multi-aware mismatch retained. Independent NumPy weights/DAC metrics and
threshold-search recomputation pass, source B SHA unchanged. CDAC DAC-level max
absoluteDNL0.11426215LSB/endpointINL0.06131120LSB,30/30 monotonic; these are0.45V
linearized weight predictions, not fullSAR transition results. Comparator effective
offset mean-3.8875mV, sampleSD12.6206078mV, range[-23.9375,25.3125]mV;30/30 valid
searches at0.125mV resolution.300 tested overdrive probes resolve with correct
polarity, receiverdelay0.218029..0.376334ns; fixed ideal clock/input not wholeADC
asynchronous/kickback signoff. Seed4101 DC-tolerance and4124 LTE-relaxation warnings
retained in statistics, require targeted accuracy review before signoff. V1 CDAC
merged-instance data/figures retained and invalidated; no sample cherry-picking.
Pinned164dbe6 monitor status/wait/show/evidence saved,64complete, livecollector,
finalcursor1797.4f717ffa957b; complete is not an electrical verdict. Report and two
PNG/SVG figures under verification/sar8_mc/blocks, visually reviewed; CSV/JSON,
validation_v2.json and report_qa.json saved. No new circuit iteration, wholechip30,
OA/PDK/library/Obsidian/baseline/commit/push/deletion. Next task for user review:
comparator offset budget and a few explicitly mapped physical-input/wholechip
samples; not automatically launched. Scoped cdac-30 follow-up to pause on delivery.

2026-11-04 — Delivery follow-up cdac-30 paused through automation_update and source configuration read back PAUSED; local receipt updated. Other automations unchanged.
