# A/B TT low-end scan: complete and recovered

2026-10-28T12:29:54.599348+08:00

Both managed simulation and analysis completed, exit0. Each run35frames, first4startupframes output0/valid1; measured centers0/1/2/3allcorrect, monotonic/bracket/functional pass. Native PSF decoding matches all35observercodes; no invalid measuredframe. Each7small artifacts collected/hashchecked, no skips; raw retained.

|Boundary|A midpoint mV|B midpoint mV|Shift from nominal LSB|
|---|---:|---:|---:|
|0→1|-892.1173096|-892.1173096|+0.1210937|
|1→2|-885.0860596|-885.0860596|+0.1210937|
|2→3|-878.0548096|-878.0548096|+0.1210937|

Each bracket54.931641uV=1/128LSB; midpointuncertainty±27.4658205uV. Same bracket means no A/B difference resolved at this precision, not exactphysicalequivalence. Uniform+.12109375LSB shift in these3thresholds is measured, not zero offset. Fullcodeoffset/gain/DNL/INL remain pending.

StrictCX actualreltol1e-7,gear2only,maxstep10ps for both. A/B simulation6799.218/6576.084s; maxconversion30.04248/29.26246ns. A nativeCMI absent in thislowrun; B CMI2751..2755present. Functionalpass does not qualify endpointstress.

## Automatic continuation verified

Coordinator89555 records bothlowruns completed and nofailure. A/B each s004-035 ands036-067 are running (PIDs152424/152482 and151115/151134),4threads each. Remainingsegments wait theirturn. OriginalFFT PIDs65587/59993 unchangedrunning. No redundant submission or process mutation performed for this recovery.

FFT effectivepoints A481/1024(47.0%),B490/1024(47.9%), excludes8warmupframes; total489/498. Snapshot timestamp above. Inflight status only, nofinalFFTmetrics. Sixcurrent simulations, noresourcewait. Evidence:low_comparison.json,a_low/result.json,b_low/result.json,collectionreceipts,post_low_progress.json.
