# Idle candidate ADCToolbox panels and time fit

Status: complete, 2026-10-23.

Goal: render the recovered 1024-code idle-tail candidate with the same
ADCToolbox diagnostics as R4, plus a time-domain fit with explicit timing axes.
No new simulation, circuit changes, calibration, baseline promotion or push.
Dirty state: existing Obsidian edits and cdac10_dualrail untracked work are
unrelated and preserved. Branch ahead 9 at start.

Owned: this plan; append-only plan/log.md; optional reusable configuration in
scripts/sar8_r4_performance/toolbox_panel.py; new
scripts/sar8_idle_performance/toolbox_figures.py;
docs/sar8_idle_toolbox.md; docs/figures/sar8_idle_performance/toolbox* and
time_fit.png; verification/sar8_idle_performance/toolbox*.json.
Remote OA: none. Raw waves, manifests, results, PDK, old reports/figures and
all other files read-only. Dependencies: installed ADCToolbox, numpy, scipy,
matplotlib; original panel method, recovered candidate results.

Steps: parameterize panel without changing defaults; generate candidate
12-panel and fixed-frequency sine fit; separate fitted residual from
clock-edge-referenced error and show readout latency; explain limitations.
Validate: FFT consistency, fit reconstruction, input time references, sample
counts, source hashes; inspect every new figure; git diff --check and scoped
review. Record results and commit owned files only, no push.

Results: 12-panel, four-axis timing fit and phase-fold PNG inspected. Toolbox
SNDR matches prior FFT within 5.7e-14 dB. Independent sine reconstruction and
clock-edge source checks pass. Residual 2.067754 mV RMS; clock-edge difference
28.402045 mV RMS. Equivalent single-frequency phase lag 1.766137 ns is not
claimed as physical aperture delay. All 1024 points retained. No remote work.
