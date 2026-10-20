# R3 12 frame anomaly replay

## Goal and ownership

Reproduce the static_065_128 frame8 output1 anomaly and comparator MNINP VGD
warning near841.192ns with the original startup/input/search history. Preserve
all saved R3 native subcircuits, dimensions, includes, TT/0.9V/27C, APS4threads,
conservative, reltol1e-5/vabstol1e-8/iabstol1e-13/maxstep10ps. No PVT, mismatch,
transient noise, sizing, clock changes or circuit fixes. Existing full batch
continues untouched. Output selection may change; require observed input/code
history agreement before calling the anomaly reproduced.

Branch exp/cdac-flat8-device, parent615b252. Unrelated untracked cdac10_dualrail
config/models/plan/scripts/verification are user-owned, preserved and do not
overlap. Full R3 performance campaign sources/decks/results and all R3 OA/PDK
are read-only dependencies.

Local owned: this plan; scripts/integration/r3_anomaly_replay.py;
scripts/integration/r3_anomaly_analyze.py;
models/veriloga/r3_anomaly_replay/r3_replay_stop.va (testbench-only early finish);
verification/integration/test_r3_anomaly_replay.py;
verification/integration/r3_anomaly_replay_results.json;
docs/r3_anomaly_replay.md; docs/figures/r3_anomaly_replay/; plan/log.md.
Ignored generated output/r3_anomaly_replay/. No shared source modification.
Remote OA owned: none. Only an isolated Spectre scratch job, read-only SSH logs
and process diagnostics. No CIW commands, OA writes, cancellation or push.

## Execution and validation

1. Read repository/bridge skills and baseline sources/manifests; verify t28_io
   and exact immutable parent deck/include hashes. Capture parent partial logs
   and relevant PSF as diagnostic evidence without disturbing running jobs.
2. Derive a12frame1200ns deck from exact parent. Only tran stop/output controls
   and save selection may differ. Keep adaptive input source/monitor bytes and
   startup/clock/history unchanged. Verify native subckt and wrapper identity.
   Prefer full solver-point saving in an800-900ns output window, if supported,
   retaining original1ns strobe scheduling. Verify tool help outside CIW first.
   Make original stop-dependent defaults step/istep51.6ns/transres51.6fs explicit.
3. Run one standalone APS4thread job. Require result.ok, finite waveform data,
   complete output window,12monitor frames and exact parent input/code history.
   Preserve any SOA/CMI/LTE warnings; no successful-signoff claim for warnings.
4. Trace SAMPLE, comparator clock/outputs/internal nodes, TOPP/TOPN, bit6 write
   and storage/reference events; measure VGD/VGS/VDS from voltages. Establish
   time ordering of overvoltage, decision and stored-code divergence. If single
   replay does not reproduce, report sensitivity explicitly, not a guessed fix.
5. Generate concise timing figures with expected baselines, units and legends;
   inspect images. Save a small provenance/metrics record and Chinese report.
   Syntax and focused immutable-deck test, diff-check, scoped local commit
   `test: reproduce R3 near-threshold code anomaly`. No push.

## State

Completed diagnostic, not circuit qualification or repair. No circuit changes.
Parent live waveform at898ns confirms code1
for VINP_SRC-VINN_SRC=-0.442529296875V; neighboring998ns frame is65. Parent log
contains MNINP CMI-2754 near841.192ns, |VGD| above0.99V; causality not yet known.

First shortened-stop replay is retained as an instrumentation comparison: APS
still prints step1.2ns instead of parent51.6ns despite explicit step51.6ns;
early warmup output history also differs. Do not call it a bit-identical replay.
Use a second bounded run with original stop51600ns and a passive testbench timer
at1200ns invoking documented $cds_finish_current_analysis(0). Original VA
stimulus and monitor are unchanged; added observer has no electrical drive.
Cadence21.1 veriaref/chap9.html confirms the normal transient-finish interface.
Only these two short diagnostic attempts; no full-batch interruption.

Original-stop native run result.ok,0errors/12warnings/7notices;5printedCMI-2754,
suppression retained, no LTE. Normal finish at1200ns via documented timer,
662464 accepted steps. Reported solver parameters exactly match parent except
outputstart. Native compute1148.8s, transfer32.7s, parse77.7s. Wave217838points,
66signals800-1200ns; raw ASCII534.8MB. All12input/search/code/count histories
match; codes64,64,64,64,64,65,64,65,1,65,65,65. Visible4frames have8W/U each.

Confirmed electrical mechanism: frame8 MSB midpoint gates fail to restore
during acquisition801.05-841.05ns; P7/N6 old PMOS50%off841.075ns, N7/P6 on
841.175ns after sample opens. Held differential offset-442.8505mV at+0.6ns,
about-62.983LSB, consistent with inferred oldword65->midpoint128(-442.96875mV).
Only bits7/6 physical gates/bottoms saved; fullword is an inference, not direct
allbank measurement. Nextframe9 restores correctly during acquisition.
MNINP VGD peak-.99914984V at841.193394ns: TOPP-.099607V,Y.899543V,CMPclocklow;
first compare843.698ns. bit6 actual residual-435.9496mV vs+7.4707mV ideal,
DATA low/write847.628557ns; D6 never rises. Finalbit0 write870.186903ns,
read898ns1. Comparator and storage respond to shifted held charge, not late
bit6 memory loss. R3_circuit_pass=false.

Likely code trigger is level-based SAMPLE phase detection at bidirectional
crossing in shared ideal gate VA; internal sampling/restored/overridden were
not captured, so exact missed branch remains to instrument. No fix attempted.
Shortened comparison failed exact replay and has LTE; retained separately,
never substituted for primary reproduction. Analysis output-directory binding
was corrected and both offline analyses regenerated before curation; raw runs
and parent evidence unchanged.

Four actual timing figures inspected; expected output band only after conversion
completion, input/model/stress baselines and legends shown. Chinese report and
small source/deck/include/wave/log-hash record saved. Two focused identity and
outlier-detection tests plus syntax, diff-check and scoped review; no broad suite.
All OA/native R3 and full-campaign source bytes preserved; unrelated user work
excluded. Scoped local commit only, no push.
