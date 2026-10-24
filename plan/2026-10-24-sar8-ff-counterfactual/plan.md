# FF hot single-variable causal controls

Status: complete. Start: 33a01c9. User requested two native controls, not a redesign.
Unrelated Obsidian and 10-bit dirty paths do not overlap; preserve them.

Goal: distinguish reference-source compression from insufficient compare waiting
in the selected 2um Mmain FF/0.99V/125C static case. Existing six-frame baseline
is read-only. Main causal observation is non-startup frame 1, input -0.81V.

Owned: this plan, plan/log.md append, scripts/sar8_ff_counterfactual/,
verification/sar8_ff_counterfactual/, output/sar8_ff_counterfactual/,
docs/figures/sar8_ff_counterfactual/. Remote OA none; no CIW action.
Remote temporary runs: /tmp/virtuoso_bridge_chenzc_intern25/90590/sar8_ff_counterfactual_20261024.
Read-only: all baseline runs, curated circuits, PDK, existing scripts and OA.

Controls: RREFP/RREFN 50 -> 1 ohm together (one symmetric source resistance
parameter), all timing unchanged; separately, only C0/C1 multi 30 -> 60 in the
single instantiated sar8p_delay_quiet cell (one shared quiet-delay scale).
Keep reference resistance 50 ohm in the second control. External sampling
clock and close edge, all other cells, stimulus, save set, model and solver
settings remain unchanged. Delay is a physical RC intervention, not an assumed
exact transport delay; measure its effect and verify conversion/reset deadline.

Steps: inverse-diff/hash checks; native license/model/resource preflight via
t28_io SSH; two immutable 600ns CX/4-thread cases, at most two concurrent;
recover native-reduced data without deleting raw PSF; six-frame timing/idle/code
checks; compare reference platforms, held error, bit2 sign and resolved margin;
plot and inspect; scoped local commit, no push or baseline promotion.
Resource bound: approximately 5GiB remote, 500MiB local; no full PVT/sine sweep.

Pass criteria for evidence (not circuit qualification): native exit zero,
complete six frames and original time-step provenance, only stated variable
changed; timing and idle checks explicit; baseline effective solver settings
matched. If delay causes a deadline failure, report the confound before drawing
conclusions. Preserve and report CMI/stress failures. Source resistor current
is not proof of a particular transistor leakage path.

Artifacts: contexts, source-change proof and hashes, preflight/receipts,
per-case measurements, comparison.json, compact waveform figure(s).
Validation: Python compile/direct execution, source inverse checks, native
logs and sample counts, image inspection, scoped diff-check.
Intended commit: verify: distinguish FF reference compression from compare timing.

## Results (frame 1, -0.81 V; ideal code 12)

| Control | Reference span at 130ns (mV) | Bit2 residual (mV) | Previous update to bit2 compare (ns) | Conversion (ns) | Code |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original, R=50 ohm | 884.575169 | -9.410467 | 2.804866 | 28.545476 | 10 |
| Only R=1 ohm | 899.628718 | +4.139252 | 2.804874 | 28.542664 | 12 |
| Only quiet C x2, R=50 ohm | 884.575167 | -9.425565 | 5.254101 | 48.137131 | 10 |

All three bit2 trial words are 12. The extra wait is 2.449235ns at that bit;
the complete conversion grows by 19.591655ns. Sampling close remains
141.1058985ns, and sampling duration ~38.26865ns. Held error at 141.8ns is
+0.517682/+0.514264/+0.517682mV respectively: the intervention is not fixing
a large acquisition error. Bit2 last100ps drifts are +1.972/-0.132/-0.135uV.
All 24 inspected frame-1 writes agree with comparator polarity; 90/10 resolved
margins before write are 144.93/139.50/143.71ps (not formal setup/hold signoff).
Sampling-close here uses SEQ_SAMPLE at50%; conversion duration retains the
original monitor definition: last PHI_U rising edge minus SAMPLE_INT falling
edge, both at50% supply. These are different internal sampling nodes.

Six-frame codes: original and quiet2 [245,10,127,128,127,145]; rref1
[243,12,127,128,127,145]. Rref1 passes all six static code checks including
the separately identified startup frame. Both new cases have native exit0,
six complete frames, 8/8/8/16 events per frame, timing and idle/reset checks
passing. Delayed reset ends at198.688ns rather than179.097ns in frame1:
the delay control consumes idle margin without correcting the code.

The causal controls support reference-span compression, not inadequate
comparison waiting, as the cause of this FF-hot large-input wrong code.
Original steady reference levels are .892289/.007714V; rref1 gives
.899814/.000186V. Source-resistor current is ~154.2uA per rail originally
and ~185.6uA at1ohm: the persistent load remains, and the stiffer source
reduces its voltage drop. Its particular MOS/branch origin is still unmeasured.
Do not interpret low R as an implemented or qualified transistor buffer.

CMI remains true in both controls; failing saved terminal-pair counts are
1740 (rref1),1727 (quiet2), versus1727 originally. These are pair checks,
not a number of separate devices or a count of CMI messages. No whole-ADC
qualification, PVT clearance, noise/mismatch, FFT or full-code claim.

## Verification and disposition

Exact inverse edits, unchanged original/monitor hashes, remote uploaded deck
hashes and model/config preflight passed. Effective CX settings match baseline:
reltol1e-4, maxstep6ns, vabstol1uV, iabstol1pA, gear2only; requested stricter
deck values are overridden by CX, not claimed as effective accuracy.
Both new full native PSF hashes, all timing samples and stress summaries
retained. Raw PSF stays in isolated remote scratch, not a durable archive.
Remote footprint ~2.04GiB; no deletion. Python compilation and focused analysis
passed; final causal_comparison.png visually reviewed. Results and limitations
are in verification/sar8_ff_counterfactual/comparison.json. Scoped local commit;
no push, no OA/PDK edits, no promotion of a new circuit baseline.
Local generated footprint ~116.9MiB. Rref1/quiet2 retain79102/79519 native
time points respectively. Independent assertions confirm all six R1 codes,
unchanged wrong code in the delayed control, and preserved CMI reporting.
