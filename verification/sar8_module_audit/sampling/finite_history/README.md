# Finite external low-history variants

Local preparation only; parent must review/register/submit. No remote action.
All variants start at the same high SAMPLE DC state as the frozen short case.
Only the first falling transition of VSAMPLE is moved earlier.

| Variant | First fall start/ns | First fall end/ns | External low plateau/ns | Formal rise/close start/ns |
| --- | ---: | ---: | ---: | --- |
| low2 | 98.9 | 99 | 2 | 101 / 141 |
| low10 | 90.9 | 91 | 10 | 101 / 141 |
| low40 | 60.9 | 61 | 40 | 101 / 141 |

Plateau is defined from the END of the100ps falling transition to the START of
the101ns rising transition. Both formal edges retain100ps duration. The original
100.2–100.3ns input polarity reversal and all sources/devices/loads/models remain
identical. Each source.diff shows the sole changed line against frozen short.

The real SEQ_SAMPLE low interval must be measured from native crossings; it is
not the external plateau and is not prefilled as a result. The low-DC case is an
equilibrium reference, not a finite duration point. No minimum startup time or
accuracy limit follows from preparing these variants.

manifest.json freezes the short-source hash and every shared fixture/measurement
file hash. recipe_suggestions.json reuses the original common mapping, pairs,
selected/events/products and byte-identical stream.cpp, plus unmodified
loaded_remote.py. Only each recipe's test.scs path changes. Suggested run IDs:

- sar8audit-sample-v2-low2
- sar8audit-sample-v2-low10
- sar8audit-sample-v2-low40

Use the same post-collection review_stream.py and mapping to obtain actual
opening/close/low intervals, preclose error and141.8ns observation. Verify141.8ns
is after actual close and preserve unknown duration if no opening occurs.
Analysis remains<=256MiB and collection<=32MiB under the frozen stream package.

Six local tests passed: exact endpoints/plateau, single-line delta, unchanged
formal tail, measurement-input reuse, no invented results, invalid-duration
rejection and byte-for-byte regeneration. Existing compact_v2 and stream_package
files were SHA-checked and not modified. New deck syntax has not been separately
compiled by this task; native behavior remains to be measured.
