# Thread scaling comparison — 2026-10-28

Both new simulations and managed analyses completed. All8 small artifacts per run collected with hashes and no skips (~2.44MB each); native raw preserved.

| Request | Actual threads | Simulation seconds | Wall-time reduction vs4 |
|---|---:|---:|---:|
|4|4|302.431|reference|
|8|8|271.876|10.10%|
|16|8|272.140|10.02%|

Exact same immutable A TT10code fixture and MX settings (reltol1e-6, trap, maxstep10ps), thread count only changed. Both reproduce [0,0,12,127,128,243,255,255,0,128], startup/all codes and native protocol crosscheck pass. All reported closure/conversion/preclose/tail metrics match4threads at analyzer output precision. CMI2751/2754/2755 and numerical warnings retained, not electrical qualification.

Spectre limits requested16to8 for small circuit, recommends2or4. This is a measured~10.1% wall-time reduction, not2x acceleration. Historical4thread run had different concurrent workload; benefit is indicative, not a controlled repeated speed estimate. OnlyA was benchmarked; B8thread benefit unmeasured.

## FFT checkpoint: 2026-10-28T09:20:46.553183+08:00

|Version|Measured /1024 (excludes8warmup)|Total /1032|Elapsed min|Status|
|---|---:|---:|---:|---|
|A|81|89|44.14|running|
|B|105|113|56.87|running|

Decision: retain running4thread FFTs, no restart or duplicate. If~10.1% applies to an~8.5-9h FFT, restarting saves only~52-55min before deducting already-spent time; B is around break-even and A only a few minutes. Startup/setup, B-specific scaling and host-load uncertainty outweigh this small projected gain. No verified live-thread-change path used. Additional compute better serves independent cases; no new cases submitted in this recovery.

Early linear estimate remains roughly8hours simulation left, plus analysis; not a completion guarantee. No finalFFT metrics. No circuit/OA/library changes, automation resumed, commit/push or deletion.
