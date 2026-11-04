# Completed feedback v2: analysis-only waveform-export repair

No Spectre job, circuit/clock/solver change or write to the completed source.
Source sar8audit-comp-feedback-tt-v2, managed hash in source_binding.json.
Its100ns native run passed with156160 accepted steps. Earlier analysis failed
its29MiB gzip output cap; the collected partial gzip is never used as input.

Frozen feedback_analyze.py/native_support.py/measurement.json are byte-identical
to v2. Pass1 invokes the unchanged native reducer with only its waveform encoder
suppressed: every native metric, event, current integral, KCL and990 selected
stress extrema is computed. Pass2 reads the identical complete raw again; hashes,
END, point count and source file stat must match. No interpolation/resimulation.

Keep all57 waveform columns but export every8th original point for this source,
plus original event brackets, signal/KCL extrema, all990 selected stress peak
times, precompare/after-write and reset-recovery witnesses. The exact source
range, stride and native/export row counts are recorded in wave.columns.json
and result.json. Figures must label the sampled export; metrics remain all
156161 points. Witnesses are never silently dropped to satisfy a file cap.

At most20000 baseline rows +10000 witness times =>30000 rows,13,680,000 bytes
uncompressed (57x8-byte columns). Gzip cap14MiB, total derived29MiB and managed
output/collection32MiB. Source raw remains remote/read-only for later zooms.
Full1457MOS/8742-pair waveform stress still incomplete;165MOS/990 pairs only.
Original native CMI/warnings/logs are retained. Native PASS is not module signoff.

Parent alone registers and calls managed analyze on recipe_proposal.json.
It is kind=analysis_only with source_run_id, never a simulation submit.
