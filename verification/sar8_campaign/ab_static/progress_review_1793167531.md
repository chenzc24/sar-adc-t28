# A/B static and FFT progress — 2026-10-28T14:05:31.034380+08:00

No newly completed full segment: eachversion onlys001-003complete/analyzed/collected, reuse prior hash-checked results. No redundant collection or analysis. Four s004-035/s036-067 simulations running, other12segments notstarted. Coordinator nofailure/resourcewait. All6simulations remain4threads.

|Task|Completed frames|Notes|
|---|---:|---|
|A fft1024-mm-v1|684/1024 (66.8%)|running|
|A s004-035-v1|49/325 (15.1%)|running|
|A s036-067-v1|47/325 (14.5%)|running|
|B fft1024-mm-v1|685/1024 (66.9%)|running|
|B s004-035-v1|51/325 (15.7%)|running|
|B s036-067-v1|50/325 (15.4%)|running|

Known boundaries1..7and36..39=11perversion; only1..3have finalnativewavecrosscheck. Center codes0..7and35..39=13uniquecodes, allcorrect. No bracketstatusfailure or reversal among adjacentknownboundaries, no recordedprotocolinvalidframe. Unscanned8..34and40..255center codes must not be labeledmissing orpassed.

A/B10/11reportedbracketsidentical. Boundary36(35→36) Bmidpoint−646.188354493mV vsA−646.243286133mV, B−A+54.9316405uV=+.0078125LSB. Adjacentbrackets touch; difference atsearchresolution, notyetconfirmedphysicaldifference belowuncertainty. Remainingrunningsegmentrawcrosscheckpending. No fullDNL/INL orno-missing-codeclaim. OriginalCMIwarnings retained.

TwoFFT progressvalues are outputrecordcounts, notfinishedspectralmetrics. All observed protocolvalidityflags clear; this isnotidealcodeequality. No restart/newsubmission/modelchange/cleanup/commit/push.
